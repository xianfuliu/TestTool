<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";

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
import { buildRequestId, deriveRuntimeValues, isEditableLayoutItem, isVisibleLayoutItem, prettyJson } from "./runtime";
import type {
  ApiToolExecuteResult,
  ApiToolLayoutItem,
  ApiToolPreviewResult,
  ApiToolProduct,
  ApiToolProductDetail,
  ApiToolSqlExecuteResult,
} from "./types";

type EditorTab = "workspace" | "config";

const activeTab = ref<EditorTab>("workspace");
const loadingProducts = ref(false);
const loadingDetail = ref(false);
const previewLoading = ref(false);
const requestLoading = ref(false);
const sqlLoadingName = ref("");
const scheduleLoading = ref(false);
const autoExecute = ref(false);

const products = ref<ApiToolProduct[]>([]);
const selectedProductId = ref<number>();
const productDetail = ref<ApiToolProductDetail | null>(null);
const selectedInterfaceName = ref("");
const selectedScheduleRowId = ref<number>();
const requestId = ref(buildRequestId());
const previewResult = ref<ApiToolPreviewResult | null>(null);
const latestRequestResult = ref<ApiToolExecuteResult | null>(null);
const latestSqlResult = ref<ApiToolSqlExecuteResult | null>(null);

const editableValues = reactive<Record<string, string>>({});
const extraVariables = reactive<Record<string, string>>({});
const requestDraft = reactive({
  url: "",
  method: "POST",
  headersText: "{}",
  bodyText: "{}",
});
const configDraft = reactive({
  name: "",
  legacyConfigPath: "",
  locked: false,
  isDefault: false,
  enableEncryption: false,
  encryptUrl: "",
  decryptUrl: "",
  scheduleTasksText: "[]",
  layoutText: "[]",
  interfacesText: "{}",
  sqlsText: "{}",
});

let previewTimer: number | undefined;

const currentConfig = computed(() => productDetail.value?.config ?? null);
const sortedLayout = computed(() =>
  [...(currentConfig.value?.layout ?? [])].sort((left, right) => left.priority - right.priority),
);
const editableKeys = computed(() => {
  const keys = new Set<string>();
  sortedLayout.value.forEach((item) => {
    if (isEditableLayoutItem(item) && item.key) {
      keys.add(item.key);
    }
  });
  return keys;
});
const visibleLayout = computed(() => sortedLayout.value.filter((item) => isVisibleLayoutItem(item)));
const runtimeValues = computed(() => {
  if (!currentConfig.value) {
    return {} as Record<string, string>;
  }
  return deriveRuntimeValues(currentConfig.value, { ...editableValues, ...extraVariables }, requestId.value);
});
const workspaceSummary = computed(() => {
  if (latestRequestResult.value) {
    return prettyJson(latestRequestResult.value);
  }
  if (latestSqlResult.value) {
    return prettyJson(latestSqlResult.value);
  }
  return "-- 等待执行接口或 SQL --";
});
const hasProduct = computed(() => Boolean(productDetail.value));

function resetRecord(target: Record<string, string>) {
  Object.keys(target).forEach((key) => {
    delete target[key];
  });
}

function applyConfigDraft(detail: ApiToolProductDetail) {
  configDraft.name = detail.product.name;
  configDraft.legacyConfigPath = detail.product.legacy_config_path;
  configDraft.locked = detail.product.locked;
  configDraft.isDefault = detail.product.is_default;
  configDraft.enableEncryption = detail.config.enable_encryption;
  configDraft.encryptUrl = detail.config.encrypt_url;
  configDraft.decryptUrl = detail.config.decrypt_url;
  configDraft.scheduleTasksText = prettyJson(detail.config.schedule_tasks);
  configDraft.layoutText = prettyJson(detail.config.layout);
  configDraft.interfacesText = prettyJson(detail.config.interfaces);
  configDraft.sqlsText = prettyJson(detail.config.sqls);
}

function seedRuntime(detail: ApiToolProductDetail) {
  resetRecord(editableValues);
  resetRecord(extraVariables);
  previewResult.value = null;
  latestRequestResult.value = null;
  latestSqlResult.value = null;
  requestId.value = buildRequestId();

  const initialValues = deriveRuntimeValues(detail.config, {}, requestId.value);
  detail.config.layout.forEach((item) => {
    if (isEditableLayoutItem(item) && item.key) {
      editableValues[item.key] = `${initialValues[item.key] ?? ""}`;
    }
  });

  const firstInterface = detail.config.layout.find((item) => item.type === "interface")?.name;
  selectedInterfaceName.value = firstInterface || Object.keys(detail.config.interfaces)[0] || "";
  selectedScheduleRowId.value = detail.config.schedule_tasks[0]?.row_id;
}

async function loadProducts(preferredProductId?: number) {
  loadingProducts.value = true;
  try {
    const payload = await fetchApiToolProducts();
    products.value = payload.products;
    const nextProductId =
      preferredProductId ??
      selectedProductId.value ??
      payload.default_product_id ??
      payload.products[0]?.id;

    if (nextProductId) {
      selectedProductId.value = nextProductId;
      await loadProductDetail(nextProductId);
    } else {
      selectedProductId.value = undefined;
      productDetail.value = null;
    }
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loadingProducts.value = false;
  }
}

async function loadProductDetail(productId: number) {
  loadingDetail.value = true;
  try {
    const detail = await fetchApiToolProductDetail(productId);
    productDetail.value = detail;
    applyConfigDraft(detail);
    seedRuntime(detail);
    if (selectedInterfaceName.value) {
      await refreshPreview();
    }
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loadingDetail.value = false;
  }
}

function mergedRuntimeVariables() {
  return {
    ...editableValues,
    ...extraVariables,
  };
}

function updateRequestDraft(preview: ApiToolPreviewResult) {
  requestDraft.url = preview.request.url;
  requestDraft.method = preview.request.method;
  requestDraft.headersText = prettyJson(preview.request.headers);
  requestDraft.bodyText = prettyJson(preview.request.body);
}

async function refreshPreview() {
  if (!productDetail.value || !selectedInterfaceName.value) {
    return;
  }
  previewLoading.value = true;
  try {
    const preview = await previewApiToolRequest({
      product_id: productDetail.value.product.id,
      interface_name: selectedInterfaceName.value,
      request_id: requestId.value,
      variables: mergedRuntimeVariables(),
    });
    previewResult.value = preview;
    updateRequestDraft(preview);
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    previewLoading.value = false;
  }
}

function schedulePreviewRefresh() {
  if (!selectedInterfaceName.value || !productDetail.value) {
    return;
  }
  if (previewTimer) {
    window.clearTimeout(previewTimer);
  }
  previewTimer = window.setTimeout(() => {
    refreshPreview();
  }, 200);
}

function mergeIncomingVariables(values: Record<string, unknown>) {
  Object.entries(values).forEach(([key, value]) => {
    if (!key || key === "request_id") {
      return;
    }
    const nextValue = value == null ? "" : String(value);
    if (editableKeys.value.has(key)) {
      editableValues[key] = nextValue;
    } else {
      extraVariables[key] = nextValue;
    }
  });
}

async function handleInterfaceClick(interfaceName: string) {
  selectedInterfaceName.value = interfaceName;
  await refreshPreview();
  if (autoExecute.value) {
    await sendRequest();
  }
}

async function sendRequest() {
  if (!productDetail.value || !selectedInterfaceName.value) {
    ElMessage.warning("请先选择一个接口");
    return;
  }

  requestLoading.value = true;
  try {
    const result = await executeApiToolRequest({
      product_id: productDetail.value.product.id,
      interface_name: selectedInterfaceName.value,
      request_id: requestId.value,
      variables: mergedRuntimeVariables(),
      request: {
        url: requestDraft.url,
        method: requestDraft.method,
        headers: JSON.parse(requestDraft.headersText || "{}"),
        body: JSON.parse(requestDraft.bodyText || "{}"),
      },
    });
    latestRequestResult.value = result;
    mergeIncomingVariables(result.mapped_values);
    ElMessage.success("接口请求执行完成");
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    requestLoading.value = false;
  }
}

async function runSql(sqlName: string) {
  if (!productDetail.value) {
    return;
  }
  sqlLoadingName.value = sqlName;
  try {
    const result = await executeApiToolSql({
      product_id: productDetail.value.product.id,
      sql_name: sqlName,
      request_id: requestId.value,
      variables: mergedRuntimeVariables(),
    });
    latestSqlResult.value = result;
    mergeIncomingVariables(result.output_variables);
    ElMessage.success(`SQL ${sqlName} 执行完成`);
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    sqlLoadingName.value = "";
  }
}

async function runSchedule() {
  if (!selectedScheduleRowId.value) {
    ElMessage.warning("请先选择一个定时任务");
    return;
  }

  scheduleLoading.value = true;
  try {
    const result = await executeApiToolSchedule({ schedule_row_id: selectedScheduleRowId.value });
    ElMessage.success(result.message);
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    scheduleLoading.value = false;
  }
}

function regenerateRequestId() {
  requestId.value = buildRequestId();
}

async function createProduct() {
  try {
    const prompt = await ElMessageBox.prompt("请输入新产品名称", "新建产品", {
      confirmButtonText: "创建",
      cancelButtonText: "取消",
      inputPattern: /\S+/,
      inputErrorMessage: "产品名称不能为空",
    });
    const created = await createApiToolProduct({ name: prompt.value.trim() });
    await loadProducts(created.product.id);
    ElMessage.success("产品已创建");
  } catch (error) {
    if (error instanceof Error) {
      ElMessage.error(error.message);
    }
  }
}

async function removeCurrentProduct() {
  if (!productDetail.value) {
    return;
  }
  try {
    await ElMessageBox.confirm(`确认删除产品 “${productDetail.value.product.name}” 吗？`, "删除确认", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
    const deletingId = productDetail.value.product.id;
    await deleteApiToolProduct(deletingId);
    const nextProduct = products.value.find((item) => item.id !== deletingId)?.id;
    await loadProducts(nextProduct);
    ElMessage.success("产品已删除");
  } catch (error) {
    if (error instanceof Error) {
      ElMessage.error(error.message);
    }
  }
}

async function saveConfig() {
  if (!productDetail.value) {
    return;
  }

  try {
    const saved = await updateApiToolProduct(productDetail.value.product.id, {
      product: {
        name: configDraft.name.trim(),
        legacy_config_path: configDraft.legacyConfigPath.trim(),
        locked: configDraft.locked,
        is_default: configDraft.isDefault,
        sort_order: productDetail.value.product.sort_order,
      },
      config: {
        enable_encryption: configDraft.enableEncryption,
        encrypt_url: configDraft.encryptUrl.trim(),
        decrypt_url: configDraft.decryptUrl.trim(),
        schedule_tasks: JSON.parse(configDraft.scheduleTasksText || "[]"),
        layout: JSON.parse(configDraft.layoutText || "[]"),
        interfaces: JSON.parse(configDraft.interfacesText || "{}"),
        sqls: JSON.parse(configDraft.sqlsText || "{}"),
      },
    });
    productDetail.value = saved;
    applyConfigDraft(saved);
    seedRuntime(saved);
    await loadProducts(saved.product.id);
    ElMessage.success("接口工具配置已保存");
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

watch(
  () =>
    JSON.stringify({
      requestId: requestId.value,
      interfaceName: selectedInterfaceName.value,
      editableValues: { ...editableValues },
      extraVariables: { ...extraVariables },
    }),
  () => {
    schedulePreviewRefresh();
  },
);

onMounted(() => {
  loadProducts();
});
</script>

<template>
  <div class="page-shell">
    <div class="page-actions">
      <el-space wrap>
        <el-select
          v-model="selectedProductId"
          placeholder="选择产品"
          style="width: 240px"
          :loading="loadingProducts"
          @change="loadProductDetail"
        >
          <el-option v-for="item in products" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-button @click="loadProducts(selectedProductId)" :loading="loadingProducts">刷新</el-button>
        <el-button type="primary" @click="createProduct">新建产品</el-button>
        <el-button type="danger" plain :disabled="!hasProduct" @click="removeCurrentProduct">删除产品</el-button>
      </el-space>
    </div>

    <el-tabs v-model="activeTab" class="surface-card api-tool-tabs">
      <el-tab-pane label="运行调试" name="workspace">
        <div class="page-shell">
          <el-card class="surface-card" shadow="never">
            <div class="page-toolbar">
              <el-space wrap>
                <el-input v-model="requestId" style="width: 220px" placeholder="请求流水" />
                <el-button @click="regenerateRequestId">重置流水</el-button>
                <el-switch v-model="autoExecute" active-text="选中接口自动发送" />
              </el-space>
              <el-space wrap>
                <el-select
                  v-model="selectedScheduleRowId"
                  placeholder="选择定时任务"
                  style="width: 220px"
                  :disabled="!(currentConfig?.schedule_tasks.length)"
                >
                  <el-option
                    v-for="task in currentConfig?.schedule_tasks ?? []"
                    :key="task.row_id"
                    :label="task.name"
                    :value="task.row_id"
                  />
                </el-select>
                <el-button type="primary" plain :loading="scheduleLoading" @click="runSchedule">
                  执行定时任务
                </el-button>
              </el-space>
            </div>
          </el-card>

          <div class="grid-two">
            <el-card class="surface-card" shadow="never">
              <template #header>
                <div>
                  <p class="section-title">运行参数</p>
                  <p class="section-caption">按旧 layout 顺序生成字段、条件、公式、接口按钮和 SQL 按钮。</p>
                </div>
              </template>

              <div v-if="loadingDetail" class="empty-block">
                <el-skeleton :rows="8" animated />
              </div>

              <div v-else-if="currentConfig" class="runtime-grid">
                <template v-for="item in visibleLayout" :key="`${item.type}-${item.key ?? item.name}`">
                  <div v-if="item.type === 'field'" class="runtime-item">
                    <span class="runtime-label">{{ item.label }}</span>
                    <el-input v-model="editableValues[item.key!]" />
                  </div>

                  <div v-else-if="item.type === 'combo'" class="runtime-item">
                    <span class="runtime-label">{{ item.label }}</span>
                    <el-select v-model="editableValues[item.key!]" style="width: 100%">
                      <el-option
                        v-for="option in item.options ?? []"
                        :key="`${item.key}-${option.value}`"
                        :label="option.text"
                        :value="option.value"
                      />
                    </el-select>
                  </div>

                  <div v-else-if="item.type === 'condition' || item.type === 'formula'" class="runtime-item">
                    <span class="runtime-label">{{ item.label }}</span>
                    <el-input :model-value="runtimeValues[item.key!]" readonly />
                  </div>

                  <div v-else-if="item.type === 'interface'" class="runtime-item runtime-item--action">
                    <span class="runtime-label">接口</span>
                    <el-button
                      :type="selectedInterfaceName === item.name ? 'primary' : 'default'"
                      @click="handleInterfaceClick(item.name!)"
                    >
                      {{ item.name }}
                    </el-button>
                  </div>

                  <div v-else-if="item.type === 'sql'" class="runtime-item runtime-item--action">
                    <span class="runtime-label">SQL</span>
                    <el-button
                      plain
                      :loading="sqlLoadingName === item.name"
                      @click="runSql(item.name!)"
                    >
                      {{ item.name }}
                    </el-button>
                  </div>
                </template>
              </div>

              <div v-else class="empty-block">
                <el-empty description="暂无可用产品配置" />
              </div>
            </el-card>

            <el-card class="surface-card" shadow="never">
              <template #header>
                <div class="table-toolbar">
                  <div>
                    <p class="section-title">请求预览与发送</p>
                    <p class="section-caption">后端按 MySQL 配置解析变量、条件请求体和字段类型转换。</p>
                  </div>
                  <el-space>
                    <el-button :loading="previewLoading" @click="refreshPreview">刷新预览</el-button>
                    <el-button type="primary" :loading="requestLoading" @click="sendRequest">发送请求</el-button>
                  </el-space>
                </div>
              </template>

              <div v-if="previewResult" class="request-editor">
                <div class="request-row">
                  <el-select v-model="requestDraft.method" style="width: 120px">
                    <el-option label="GET" value="GET" />
                    <el-option label="POST" value="POST" />
                    <el-option label="PUT" value="PUT" />
                    <el-option label="PATCH" value="PATCH" />
                    <el-option label="DELETE" value="DELETE" />
                  </el-select>
                  <el-input v-model="requestDraft.url" placeholder="请求地址" />
                </div>

                <div class="request-panel">
                  <span class="runtime-label">Headers JSON</span>
                  <el-input v-model="requestDraft.headersText" type="textarea" :rows="7" />
                </div>

                <div class="request-panel">
                  <span class="runtime-label">Body JSON</span>
                  <el-input v-model="requestDraft.bodyText" type="textarea" :rows="12" />
                </div>

                <div class="request-panel">
                  <span class="runtime-label">解析变量</span>
                  <pre class="json-box">{{ prettyJson(previewResult.resolved_variables) }}</pre>
                </div>
              </div>

              <div v-else class="empty-block">
                <el-empty description="选择接口后可预览请求体" />
              </div>
            </el-card>
          </div>

          <el-card class="surface-card" shadow="never">
            <template #header>
              <div>
                <p class="section-title">执行输出</p>
                <p class="section-caption">保留接口响应、SQL 结果和变量回填结果，方便继续联动下一步调试。</p>
              </div>
            </template>
            <pre class="json-box output-box">{{ workspaceSummary }}</pre>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="配置管理" name="config">
        <div class="page-shell">
          <div class="grid-two">
            <el-card class="surface-card" shadow="never">
              <template #header>
                <div>
                  <p class="section-title">产品基础配置</p>
                  <p class="section-caption">这里保存到 MySQL，后端不再直接读取旧 json 文件。</p>
                </div>
              </template>

              <el-form label-position="top">
                <el-form-item label="产品名称">
                  <el-input v-model="configDraft.name" />
                </el-form-item>
                <el-form-item label="历史配置路径">
                  <el-input v-model="configDraft.legacyConfigPath" />
                </el-form-item>
                <el-space wrap class="switch-row">
                  <el-switch v-model="configDraft.locked" active-text="锁定产品" />
                  <el-switch v-model="configDraft.isDefault" active-text="设为默认产品" />
                  <el-switch v-model="configDraft.enableEncryption" active-text="启用产品级加解密" />
                </el-space>
                <el-form-item label="加密接口 URL">
                  <el-input v-model="configDraft.encryptUrl" />
                </el-form-item>
                <el-form-item label="解密接口 URL">
                  <el-input v-model="configDraft.decryptUrl" />
                </el-form-item>
                <el-button type="primary" :disabled="!hasProduct" @click="saveConfig">保存配置</el-button>
              </el-form>
            </el-card>

            <el-card class="surface-card" shadow="never">
              <template #header>
                <div>
                  <p class="section-title">当前迁移状态</p>
                  <p class="section-caption">接口工具的结构化数据已经拆分为产品、布局、接口、SQL、定时任务等多张表。</p>
                </div>
              </template>
              <div class="summary-list">
                <div class="summary-item">
                  <div>
                    <strong>布局项</strong>
                    <p>{{ currentConfig?.layout.length ?? 0 }} 个布局元素已从 json 导入 MySQL。</p>
                  </div>
                </div>
                <div class="summary-item">
                  <div>
                    <strong>接口配置</strong>
                    <p>{{ Object.keys(currentConfig?.interfaces ?? {}).length }} 个接口可直接用于请求预览和发送。</p>
                  </div>
                </div>
                <div class="summary-item">
                  <div>
                    <strong>SQL 配置</strong>
                    <p>{{ Object.keys(currentConfig?.sqls ?? {}).length }} 个 SQL 配置已支持数据库执行和变量回填。</p>
                  </div>
                </div>
                <div class="summary-item">
                  <div>
                    <strong>定时任务</strong>
                    <p>{{ currentConfig?.schedule_tasks.length ?? 0 }} 个任务保留了历史 job 信息。</p>
                  </div>
                </div>
              </div>
            </el-card>
          </div>

          <div class="grid-two">
            <el-card class="surface-card" shadow="never">
              <template #header><p class="section-title">Schedule Tasks / Layout JSON</p></template>
              <div class="editor-stack">
                <div>
                  <span class="runtime-label">schedule_tasks</span>
                  <el-input v-model="configDraft.scheduleTasksText" type="textarea" :rows="10" />
                </div>
                <div>
                  <span class="runtime-label">layout</span>
                  <el-input v-model="configDraft.layoutText" type="textarea" :rows="20" />
                </div>
              </div>
            </el-card>

            <el-card class="surface-card" shadow="never">
              <template #header><p class="section-title">Interfaces / SQLs JSON</p></template>
              <div class="editor-stack">
                <div>
                  <span class="runtime-label">interfaces</span>
                  <el-input v-model="configDraft.interfacesText" type="textarea" :rows="16" />
                </div>
                <div>
                  <span class="runtime-label">sqls</span>
                  <el-input v-model="configDraft.sqlsText" type="textarea" :rows="14" />
                </div>
              </div>
            </el-card>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.page-actions {
  display: flex;
  justify-content: flex-end;
  padding: 4px;
}

.api-tool-tabs {
  padding: 8px;
}

.runtime-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.runtime-item {
  display: grid;
  gap: 8px;
}

.runtime-item--action {
  align-content: start;
}

.runtime-label {
  color: var(--qm-text-secondary);
  font-size: 12px;
  font-weight: 600;
}

.request-editor {
  display: grid;
  gap: 16px;
}

.request-row {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: 12px;
}

.request-panel {
  display: grid;
  gap: 8px;
}

.output-box {
  max-height: 520px;
}

.switch-row {
  margin-bottom: 16px;
}

.editor-stack {
  display: grid;
  gap: 16px;
}

@media (max-width: 960px) {
  .runtime-grid,
  .request-row {
    grid-template-columns: 1fr;
  }
}
</style>
