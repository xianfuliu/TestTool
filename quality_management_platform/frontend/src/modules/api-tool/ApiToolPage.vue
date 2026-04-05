<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import ApiToolConfigDialog from "./components/ApiToolConfigDialog.vue";
import {
  createApiToolProduct,
  deleteApiToolProduct,
  executeApiToolRequest,
  executeApiToolSchedule,
  executeApiToolSql,
  fetchApiToolProductDetail,
  fetchApiToolProducts,
  previewApiToolRequest,
  updateApiToolProduct,
} from "./api";
import { buildRequestId, deriveRuntimeValues, isEditableLayoutItem, isVisibleLayoutItem } from "./runtime";
import type {
  ApiToolConfig,
  ApiToolExecuteResult,
  ApiToolLayoutItem,
  ApiToolPreviewResult,
  ApiToolProduct,
  ApiToolProductDetail,
  ApiToolScheduleTask,
  ApiToolSqlExecuteResult,
} from "./types";

type SavePayload = {
  product: {
    name: string;
    legacy_config_path: string;
    locked: boolean;
    is_default: boolean;
    sort_order: number;
  };
  config: ApiToolConfig;
};

const products = ref<ApiToolProduct[]>([]);
const selectedProductId = ref<number | null>(null);
const productDetail = ref<ApiToolProductDetail | null>(null);
const configDialogVisible = ref(false);
const productDialogVisible = ref(false);
const requestId = ref(buildRequestId());
const selectedScheduleRowId = ref<number | null>(null);
const autoSendRequest = ref(true);
const currentInterfaceName = ref("");
const activeSqlName = ref("");

const loadingProducts = ref(false);
const loadingDetail = ref(false);
const previewing = ref(false);
const sending = ref(false);
const runningSql = ref(false);
const runningSchedule = ref(false);
const savingConfig = ref(false);
const runningSqlName = ref("");
const creatingProduct = ref(false);
const deletingProductId = ref<number | null>(null);

const manualValues = ref<Record<string, string>>({});
const requestPreview = ref<ApiToolPreviewResult | null>(null);
const requestResult = ref<ApiToolExecuteResult | null>(null);
const sqlResult = ref<ApiToolSqlExecuteResult | null>(null);

const requestEditor = reactive({
  url: "",
  method: "POST",
  headersText: '{\n  "Content-Type": "application/json"\n}',
  bodyText: "{\n  \n}",
});

const productEditor = reactive({
  name: "",
  is_default: false,
});

function formatText(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function parseObjectText(text: string, label: string) {
  const trimmed = text.trim();
  if (!trimmed) {
    return {};
  }
  try {
    const parsed = JSON.parse(trimmed) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error(`${label} 必须是 JSON 对象`);
    }
    return parsed as Record<string, unknown>;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`${label} 不是合法的 JSON`);
  }
}

function parseAnyText(text: string) {
  const trimmed = text.trim();
  if (!trimmed) {
    return {};
  }
  try {
    return JSON.parse(trimmed) as unknown;
  } catch {
    return text;
  }
}

const currentProduct = computed(() =>
  products.value.find((item) => item.id === selectedProductId.value) ?? null,
);

const currentConfig = computed(() => productDetail.value?.config ?? null);

const scheduleTasks = computed<ApiToolScheduleTask[]>(() => currentConfig.value?.schedule_tasks ?? []);

const visibleLayoutItems = computed<ApiToolLayoutItem[]>(() => {
  const layout = currentConfig.value?.layout ?? [];
  return [...layout]
    .filter((item) => isVisibleLayoutItem(item))
    .sort((left, right) => left.priority - right.priority);
});

const runtimeValues = computed<Record<string, string>>(() => {
  if (!currentConfig.value) {
    return {};
  }
  const values = deriveRuntimeValues(currentConfig.value, manualValues.value, requestId.value);
  const result: Record<string, string> = {};
  Object.entries(values).forEach(([key, value]) => {
    result[key] = String(value ?? "");
  });
  return result;
});

const responseText = computed(() => {
  if (requestResult.value) {
    return formatText(requestResult.value.decrypted_body ?? requestResult.value.body);
  }
  if (sqlResult.value) {
    return JSON.stringify(
      {
        sql_name: sqlResult.value.sql_name,
        request_id: sqlResult.value.request_id,
        resolved_sql: sqlResult.value.resolved_sql,
        output_variables: sqlResult.value.output_variables,
        rows: sqlResult.value.rows,
      },
      null,
      2,
    );
  }
  return "";
});

const responsePlaceholder = computed(() => {
  if (activeSqlName.value) {
    return "SQL 执行结果会显示在这里...";
  }
  return "响应内容会显示在这里...";
});

function syncManualValues(config: ApiToolConfig) {
  const defaults = deriveRuntimeValues(config, {}, requestId.value);
  const nextValues: Record<string, string> = {};

  config.layout.forEach((item) => {
    if (!isEditableLayoutItem(item) || !item.key) {
      return;
    }
    const value = defaults[item.key];
    nextValues[item.key] = value === undefined || value === null ? "" : String(value);
  });

  manualValues.value = nextValues;
}

function resetResultPanels() {
  currentInterfaceName.value = "";
  requestPreview.value = null;
  requestResult.value = null;
  sqlResult.value = null;
  activeSqlName.value = "";
  runningSqlName.value = "";
  requestEditor.url = "";
  requestEditor.method = "POST";
  requestEditor.headersText = '{\n  "Content-Type": "application/json"\n}';
  requestEditor.bodyText = "{\n  \n}";
}

function refreshRequestId() {
  requestId.value = buildRequestId();
  requestPreview.value = null;
  requestResult.value = null;
  sqlResult.value = null;
  activeSqlName.value = "";
  runningSqlName.value = "";
  if (currentConfig.value) {
    syncManualValues(currentConfig.value);
  }
}

function applyVariablePatch(patch: Record<string, unknown>) {
  const nextValues = { ...manualValues.value };
  const editableKeys = new Set(
    (currentConfig.value?.layout ?? [])
      .filter((item) => isEditableLayoutItem(item) && item.key)
      .map((item) => item.key as string),
  );

  Object.entries(patch).forEach(([key, value]) => {
    if (editableKeys.has(key)) {
      nextValues[key] = String(value ?? "");
    }
  });

  manualValues.value = nextValues;
}

async function loadProductDetail(productId: number) {
  loadingDetail.value = true;
  try {
    const detail = await fetchApiToolProductDetail(productId);
    productDetail.value = detail;
    selectedScheduleRowId.value = detail.config.schedule_tasks[0]?.row_id ?? null;
    syncManualValues(detail.config);
    resetResultPanels();
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loadingDetail.value = false;
  }
}

async function loadProducts(preferredProductId?: number | null) {
  loadingProducts.value = true;
  try {
    const data = await fetchApiToolProducts();
    products.value = data.products;
    const targetId = preferredProductId ?? data.default_product_id ?? data.products[0]?.id ?? null;
    selectedProductId.value = targetId;
    if (targetId) {
      await loadProductDetail(targetId);
    } else {
      productDetail.value = null;
      selectedScheduleRowId.value = null;
      resetResultPanels();
    }
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loadingProducts.value = false;
  }
}

async function handleProductChange(value: number | string) {
  const productId = Number(value);
  selectedProductId.value = Number.isFinite(productId) ? productId : null;
  if (selectedProductId.value) {
    await loadProductDetail(selectedProductId.value);
  }
}

function updateManualValue(item: ApiToolLayoutItem, value: string) {
  if (!item.key) {
    return;
  }
  manualValues.value = {
    ...manualValues.value,
    [item.key]: value,
  };
}

function buildVariablePayload() {
  return { ...runtimeValues.value };
}

async function previewInterface(interfaceName: string) {
  if (!selectedProductId.value) {
    return;
  }
  previewing.value = true;
  currentInterfaceName.value = interfaceName;
  try {
    const data = await previewApiToolRequest({
      product_id: selectedProductId.value,
      interface_name: interfaceName,
      variables: buildVariablePayload(),
      request_id: requestId.value,
    });
    requestPreview.value = data;
    activeSqlName.value = "";
    requestId.value = data.request_id;
    requestEditor.url = data.request.url;
    requestEditor.method = data.request.method;
    requestEditor.headersText = formatText(data.request.headers) || "{\n  \n}";
    requestEditor.bodyText = formatText(data.request.body) || "{\n  \n}";
    if (autoSendRequest.value) {
      await sendCurrentRequest();
    } else {
      ElMessage.success(`已生成 ${interfaceName} 的请求预览`);
    }
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    previewing.value = false;
  }
}

async function sendCurrentRequest() {
  if (!selectedProductId.value || !currentInterfaceName.value) {
    ElMessage.warning("请先在左侧选择一个接口按钮");
    return;
  }
  sending.value = true;
  try {
    const data = await executeApiToolRequest({
      product_id: selectedProductId.value,
      interface_name: currentInterfaceName.value,
      variables: buildVariablePayload(),
      request_id: requestId.value,
      request: {
        url: requestEditor.url,
        method: requestEditor.method,
        headers: parseObjectText(requestEditor.headersText, "请求头"),
        body: parseAnyText(requestEditor.bodyText),
      },
    });
    requestResult.value = data;
    sqlResult.value = null;
    requestId.value = data.request_id;
    applyVariablePatch(data.mapped_values);
    activeSqlName.value = "";
    ElMessage.success("请求发送完成");
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    sending.value = false;
  }
}

async function runSql(sqlName: string) {
  if (!selectedProductId.value) {
    return;
  }
  runningSql.value = true;
  runningSqlName.value = sqlName;
  try {
    const data = await executeApiToolSql({
      product_id: selectedProductId.value,
      sql_name: sqlName,
      variables: buildVariablePayload(),
      request_id: requestId.value,
    });
    sqlResult.value = data;
    requestResult.value = null;
    requestId.value = data.request_id;
    applyVariablePatch(data.output_variables);
    activeSqlName.value = sqlName;
    ElMessage.success(`已执行 SQL：${sqlName}`);
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    runningSql.value = false;
    runningSqlName.value = "";
  }
}

async function runScheduleTask() {
  if (!selectedScheduleRowId.value) {
    ElMessage.warning("请选择一个定时任务");
    return;
  }
  runningSchedule.value = true;
  try {
    const data = await executeApiToolSchedule({
      schedule_row_id: selectedScheduleRowId.value,
    });
    ElMessage.success(data.message);
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    runningSchedule.value = false;
  }
}

async function saveConfig(payload: SavePayload) {
  if (!selectedProductId.value) {
    return;
  }
  savingConfig.value = true;
  try {
    const detail = await updateApiToolProduct(selectedProductId.value, payload);
    configDialogVisible.value = false;
    await loadProducts(detail.product.id);
    ElMessage.success("接口工具配置已保存");
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    savingConfig.value = false;
  }
}

function openProductDialog() {
  productEditor.name = "";
  productEditor.is_default = products.value.length === 0;
  productDialogVisible.value = true;
}

async function createProduct() {
  const name = productEditor.name.trim();
  if (!name) {
    ElMessage.warning("请输入产品名称");
    return;
  }

  creatingProduct.value = true;
  try {
    const detail = await createApiToolProduct({
      name,
      is_default: productEditor.is_default,
    });
    productEditor.name = "";
    productEditor.is_default = false;
    await loadProducts(detail.product.id);
    ElMessage.success(`已新增产品：${detail.product.name}`);
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    creatingProduct.value = false;
  }
}

async function removeProduct(product: ApiToolProduct) {
  try {
    await ElMessageBox.confirm(`确定删除产品“${product.name}”吗？`, "删除产品", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }

  deletingProductId.value = product.id;
  try {
    await deleteApiToolProduct(product.id);
    await loadProducts(product.id === selectedProductId.value ? null : selectedProductId.value);
    ElMessage.success(`已删除产品：${product.name}`);
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    deletingProductId.value = null;
  }
}

onMounted(() => {
  void loadProducts();
});
</script>

<template>
  <div class="page-shell api-tool-page">
    <div class="top-panel panel-shell">
      <div class="toolbar compact-ui">
        <div class="toolbar-group">
          <span class="toolbar-label">产品:</span>
          <el-select
            v-model="selectedProductId"
            class="toolbar-select product-select"
            placeholder="请选择产品"
            :loading="loadingProducts"
            @change="handleProductChange"
          >
            <el-option
              v-for="item in products"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </div>

        <div class="toolbar-spacer" />

        <div class="toolbar-group">
          <span class="toolbar-label">请求流水:</span>
          <el-input v-model="requestId" class="toolbar-input request-id-input" />
          <el-button class="mini-btn" @click="refreshRequestId">更新</el-button>
        </div>

        <div class="toolbar-spacer" />

        <div class="toolbar-group">
          <span class="toolbar-label">定时任务:</span>
          <el-select
            v-model="selectedScheduleRowId"
            class="toolbar-select schedule-select"
            placeholder="选择任务"
          >
            <el-option
              v-for="item in scheduleTasks"
              :key="item.row_id"
              :label="item.name"
              :value="item.row_id"
            />
          </el-select>
          <el-button class="mini-btn" :loading="runningSchedule" @click="runScheduleTask">执行</el-button>
        </div>

        <div class="toolbar-grow" />

        <el-button class="mini-btn" @click="openProductDialog">产品管理</el-button>
        <el-checkbox v-model="autoSendRequest" class="request-check">发送请求</el-checkbox>
        <el-button class="mini-btn" @click="configDialogVisible = true">配置</el-button>
      </div>
    </div>

    <div class="workbench">
      <div class="left-panel panel-shell compact-ui">
        <div v-if="loadingDetail" class="panel-loading">正在加载产品配置...</div>
        <div v-else-if="!currentConfig" class="panel-empty">暂无可用的接口工具配置</div>
        <div v-else class="left-scroll">
          <div class="layout-list">
            <div
              v-for="item in visibleLayoutItems"
              :key="`${item.type}-${item.key || item.name}-${item.priority}`"
              :class="[
                'layout-item',
                item.type === 'interface' || item.type === 'sql' ? 'layout-button-item' : 'layout-control-item',
              ]"
            >
              <template v-if="item.type === 'field' && item.key">
                <label class="layout-label">{{ item.label || item.key }}</label>
                <el-input
                  :model-value="manualValues[item.key]"
                  class="field-input"
                  size="small"
                  @update:model-value="updateManualValue(item, $event)"
                />
              </template>

              <template v-else-if="item.type === 'combo' && item.key">
                <label class="layout-label">{{ item.label || item.key }}</label>
                <el-select
                  :model-value="manualValues[item.key]"
                  class="field-input combo-input"
                  size="small"
                  @update:model-value="updateManualValue(item, $event)"
                >
                  <el-option
                    v-for="option in item.options || []"
                    :key="`${item.key}-${option.value}`"
                    :label="option.text"
                    :value="option.value"
                  />
                </el-select>
              </template>

              <template v-else-if="item.type === 'condition' && item.key">
                <label class="layout-label">{{ item.label || item.key }}</label>
                <el-input
                  :model-value="runtimeValues[item.key]"
                  class="field-input readonly-input"
                  size="small"
                  readonly
                />
              </template>

              <template v-else-if="item.type === 'formula' && item.key">
                <label class="layout-label">{{ item.label || item.key }}</label>
                <el-input
                  :model-value="runtimeValues[item.key]"
                  class="field-input readonly-input"
                  size="small"
                  readonly
                />
              </template>

              <template v-else-if="item.type === 'interface' && item.name">
                <el-button
                  class="action-button compact-btn"
                  size="small"
                  :loading="previewing && currentInterfaceName === item.name"
                  @click="previewInterface(item.name)"
                >
                  {{ item.name }}
                </el-button>
              </template>

              <template v-else-if="item.type === 'sql' && item.name">
                <el-button
                  class="action-button compact-btn sql-button"
                  size="small"
                  :loading="runningSql && runningSqlName === item.name"
                  @click="runSql(item.name)"
                >
                  {{ item.name }}
                </el-button>
              </template>
            </div>
          </div>
        </div>
      </div>

      <div class="right-panel panel-shell compact-ui">
        <div class="url-row">
          <span class="section-label">URL:</span>
          <el-input
            v-model="requestEditor.url"
            class="url-input"
            placeholder="请输入请求 URL，或从左侧点击接口按钮自动填充"
          />
        </div>

        <div class="section-block">
          <div class="section-label">请求体</div>
          <el-input
            v-model="requestEditor.bodyText"
            class="body-editor request-editor legacy-textarea"
            type="textarea"
            :rows="8"
          />
        </div>

        <div class="send-row">
          <el-button class="send-btn" type="primary" :loading="sending" @click="sendCurrentRequest">
            发送请求
          </el-button>
        </div>

        <div class="section-block response-block">
          <div class="section-label">响应体</div>
          <el-input
            :model-value="responseText"
            class="body-editor response-editor legacy-textarea"
            type="textarea"
            :placeholder="responsePlaceholder"
            :rows="12"
            readonly
          />
        </div>
      </div>
    </div>

    <ApiToolConfigDialog
      v-model="configDialogVisible"
      :product="currentProduct"
      :config="currentConfig"
      :saving="savingConfig"
      @save="saveConfig"
    />

    <el-dialog
      v-model="productDialogVisible"
      title="产品管理"
      width="640px"
      class="compact-ui product-dialog"
      destroy-on-close
    >
      <div class="product-dialog-body">
        <div class="product-create-row">
          <el-input
            v-model="productEditor.name"
            class="product-create-input"
            placeholder="请输入产品名称"
            @keyup.enter="createProduct"
          />
          <el-checkbox v-model="productEditor.is_default">设为默认</el-checkbox>
          <el-button type="primary" :loading="creatingProduct" @click="createProduct">新增产品</el-button>
        </div>

        <div class="product-list">
          <div
            v-for="item in products"
            :key="item.id"
            :class="['product-row', { active: item.id === selectedProductId }]"
          >
            <div class="product-meta">
              <span class="product-name">{{ item.name }}</span>
              <span v-if="item.is_default" class="product-tag">默认</span>
              <span v-if="item.id === selectedProductId" class="product-tag current">当前</span>
            </div>
            <el-button
              type="danger"
              text
              size="small"
              :loading="deletingProductId === item.id"
              @click="removeProduct(item)"
            >
              删除
            </el-button>
          </div>

          <div v-if="!products.length" class="product-empty">暂无产品</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.api-tool-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  gap: 8px;
  font-size: 12px;
  overflow: hidden;
}

.panel-shell {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.top-panel {
  background: #ffffff;
  padding: 8px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 34px;
  flex-wrap: wrap;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-label {
  color: #606266;
  font-size: 12px;
  line-height: 1;
}

.toolbar-select {
  width: 150px;
}

.product-select {
  width: 150px;
}

.schedule-select {
  width: 250px;
}

.request-id-input {
  width: 150px;
}

.toolbar-spacer {
  width: 22px;
}

.toolbar-grow {
  flex: 1 1 auto;
}

.product-create-input {
  width: 240px;
}

.mini-btn {
  min-width: 56px;
  padding: 0 10px;
}

.mini-btn,
.action-button {
  border-color: #2563eb;
  color: #ffffff;
  background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.16);
}

.mini-btn:hover,
.mini-btn:focus-visible,
.action-button:hover,
.action-button:focus-visible {
  border-color: #1d4ed8;
  color: #ffffff;
  background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
}

.workbench {
  display: grid;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
  gap: 8px;
  grid-template-columns: minmax(500px, 56%) minmax(400px, 44%);
}

.left-panel,
.right-panel {
  background: #ffffff;
  min-height: 0;
  overflow: hidden;
}

.left-panel {
  display: flex;
  flex-direction: column;
  padding: 8px;
  background: #f6f9ff;
}

.right-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  gap: 8px;
  padding: 8px;
  background: #f8fbff;
}

.panel-loading,
.panel-empty {
  color: #909399;
  font-size: 12px;
  padding: 10px 0;
}

.layout-list {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 18px 20px;
  padding: 6px 4px;
}

.left-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  background: transparent;
}

.layout-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.layout-control-item {
  min-width: 0;
}

.layout-button-item {
  flex: 0 0 auto;
}

.layout-label {
  color: #606266;
  font-size: 12px;
  white-space: nowrap;
}

.action-button {
  min-width: 80px;
  justify-content: center;
}

.sql-button {
  border-color: #2563eb;
  color: #ffffff;
}

.field-input {
  width: 138px;
}

.combo-input {
  width: 160px;
}

.readonly-input {
  width: 138px;
}

.url-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.response-block {
  flex: 1 1 auto;
  min-height: 0;
}

.section-label {
  color: #606266;
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
}

.url-input {
  flex: 1 1 auto;
}

.send-row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.send-btn {
  min-width: 74px;
  padding: 0 14px;
}

.legacy-textarea {
  flex: 1 1 auto;
}

.request-editor :deep(.el-textarea__inner) {
  min-height: 164px !important;
  max-height: 164px;
}

.response-editor {
  flex: 1 1 auto;
  min-height: 0;
}

.response-editor :deep(.el-textarea),
.response-editor :deep(.el-textarea__inner) {
  height: 100%;
}

.response-editor :deep(.el-textarea__inner) {
  min-height: 240px !important;
}

.compact-ui :deep(.el-input__wrapper),
.compact-ui :deep(.el-select__wrapper) {
  min-height: 28px;
  padding: 1px 8px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
}

.compact-ui :deep(.el-input__inner),
.compact-ui :deep(.el-select__selected-item),
.compact-ui :deep(.el-checkbox__label),
.compact-ui :deep(.el-button),
.compact-ui :deep(.el-textarea__inner) {
  font-size: 12px;
}

.compact-ui :deep(.el-button) {
  min-height: 28px;
}

.legacy-textarea :deep(.el-textarea__inner) {
  padding: 8px 10px;
  color: #303133;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.45;
}

.url-input :deep(.el-input__inner) {
  color: #1f5fbf;
  font-size: 12px;
  font-weight: 600;
}

.product-dialog :deep(.el-dialog__body) {
  padding-top: 14px;
}

.product-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.product-create-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.product-list {
  border: 1px solid #dcdfe6;
  background: #ffffff;
  max-height: 360px;
  overflow-y: auto;
}

.product-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid #ebeef5;
}

.product-row:last-child {
  border-bottom: none;
}

.product-row.active {
  background: #f5f7fa;
}

.product-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.product-name {
  font-size: 12px;
  color: #303133;
}

.product-tag {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background: #ecf5ff;
  color: #409eff;
  font-size: 11px;
}

.product-tag.current {
  background: #f0f9eb;
  color: #67c23a;
}

.product-empty {
  padding: 18px 12px;
  color: #909399;
  font-size: 12px;
}

@media (max-width: 1180px) {
  .workbench {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .toolbar,
  .toolbar-group {
    align-items: flex-start;
  }

  .toolbar-group {
    flex-wrap: wrap;
  }

  .toolbar-spacer,
  .toolbar-grow {
    display: none;
  }

  .toolbar-select,
  .request-id-input,
  .field-input,
  .combo-input,
  .readonly-input {
    width: 100%;
  }

  .layout-list {
    gap: 10px;
  }

  .product-create-row {
    flex-wrap: wrap;
  }

  .product-create-input {
    width: 100%;
  }

  .layout-item,
  .url-row {
    flex-direction: column;
    align-items: stretch;
  }

  .request-editor :deep(.el-textarea__inner),
  .response-editor :deep(.el-textarea__inner) {
    max-height: none;
  }
}
</style>
