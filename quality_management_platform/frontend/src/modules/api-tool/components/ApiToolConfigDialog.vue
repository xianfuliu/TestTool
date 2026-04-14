<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Minus, Plus } from "@element-plus/icons-vue";

import {
  buildConfigFromDrafts,
  configToDrafts,
  createConditionalCaseRow,
  createExtractionRow,
  createInterfaceDraft,
  createKeyValueRow,
  createLayoutDraft,
  createOutputFieldRow,
  createSqlDraft,
  type DraftConditionalCaseRow,
  type DraftExtractionRow,
  type DraftKeyValueRow,
  type InterfaceDraft,
  type LayoutDraftItem,
  type SqlDraft,
} from "../drafts";
import type {
  ApiToolConfig,
  ApiToolGlobalRequestConfig,
  ApiToolProduct,
  ApiToolScheduleTask,
  LayoutOption,
} from "../types";

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

const props = defineProps<{
  modelValue: boolean;
  product: ApiToolProduct | null;
  config: ApiToolConfig | null;
  saving: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  save: [payload: SavePayload];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit("update:modelValue", value),
});

const activeTab = ref<"basic" | "global" | "schedule" | "layout" | "interface" | "sql">("basic");

const productForm = reactive({
  name: "",
  legacy_config_path: "",
  locked: false,
  is_default: false,
  sort_order: 1,
  enable_encryption: false,
  encrypt_url: "",
  decrypt_url: "",
});

const scheduleTasksDraft = ref<ApiToolScheduleTask[]>([]);
const layoutItemsDraft = ref<LayoutDraftItem[]>([]);
const interfacesDraft = ref<InterfaceDraft[]>([]);
const sqlsDraft = ref<SqlDraft[]>([]);
const globalLoginEnabled = ref(false);
const globalLoginMethod = ref("POST");
const globalLoginUrl = ref("");
const globalLoginBodyText = ref("{\n  \n}");
const globalLoginHeadersRows = ref<DraftKeyValueRow[]>([createKeyValueRow("Content-Type", "application/json")]);
const globalLoginExtractionRows = ref<DraftExtractionRow[]>([createExtractionRow()]);
const globalHeaderEnabled = ref(false);
const globalHeaderRows = ref<DraftKeyValueRow[]>([createKeyValueRow()]);

const scheduleDialogVisible = ref(false);
const scheduleEditIndex = ref(-1);
const scheduleForm = reactive<ApiToolScheduleTask>({
  id: "",
  jobGroup: "",
  name: "",
  row_id: 0,
});

const layoutDialogVisible = ref(false);
const layoutEditIndex = ref(-1);
const layoutForm = ref<LayoutDraftItem>(createLayoutDraft());
const layoutOptionsForm = ref<LayoutOption[]>([]);
const layoutMappingsForm = ref<DraftKeyValueRow[]>([]);
const draggingLayoutIndex = ref(-1);

const interfaceDialogVisible = ref(false);
const interfaceEditIndex = ref(-1);
const interfaceForm = ref<InterfaceDraft>(createInterfaceDraft());

const sqlDialogVisible = ref(false);
const sqlEditIndex = ref(-1);
const sqlForm = ref<SqlDraft>(createSqlDraft());

const methodOptions = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const formulaTypeOptions = [
  { label: "数值公式", value: "numeric" },
  { label: "日期差值", value: "date" },
];

function buildLayoutNameOrder(type: "interface" | "sql") {
  const orderMap = new Map<string, number>();
  layoutItemsDraft.value.forEach((item, index) => {
    if (item.type !== type) {
      return;
    }
    const name = item.name?.trim();
    if (name && !orderMap.has(name)) {
      orderMap.set(name, index);
    }
  });
  return orderMap;
}

const orderedInterfacesDraft = computed(() => {
  const orderMap = buildLayoutNameOrder("interface");
  return [...interfacesDraft.value].sort((left, right) => {
    const leftRank = orderMap.get(left.name.trim());
    const rightRank = orderMap.get(right.name.trim());
    if (leftRank === undefined && rightRank === undefined) {
      return 0;
    }
    if (leftRank === undefined) {
      return 1;
    }
    if (rightRank === undefined) {
      return -1;
    }
    return leftRank - rightRank;
  });
});

const orderedSqlsDraft = computed(() => {
  const orderMap = buildLayoutNameOrder("sql");
  return [...sqlsDraft.value].sort((left, right) => {
    const leftRank = orderMap.get(left.name.trim());
    const rightRank = orderMap.get(right.name.trim());
    if (leftRank === undefined && rightRank === undefined) {
      return 0;
    }
    if (leftRank === undefined) {
      return 1;
    }
    if (rightRank === undefined) {
      return -1;
    }
    return leftRank - rightRank;
  });
});

function cloneValue<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function normaliseLayoutPriorities() {
  layoutItemsDraft.value = layoutItemsDraft.value.map((item, index) => ({
    ...item,
    priority: index + 1,
  }));
}

function resetDialogState() {
  activeTab.value = "basic";
  scheduleDialogVisible.value = false;
  layoutDialogVisible.value = false;
  interfaceDialogVisible.value = false;
  sqlDialogVisible.value = false;
}

function mappingRecordToRows(record: Record<string, string> | undefined) {
  const entries = Object.entries(record ?? {});
  if (!entries.length) {
    return [createKeyValueRow()];
  }
  return entries.map(([key, value]) => createKeyValueRow(key, value));
}

function mappingRowsToRecord(rows: DraftKeyValueRow[]) {
  const result: Record<string, string> = {};
  rows.forEach((row) => {
    const key = row.key.trim();
    const value = row.value.trim();
    if (key && value) {
      result[key] = value;
    }
  });
  return result;
}

function extractionRowsFromConfig(rows: Array<{ variable: string; path: string }> | undefined) {
  const entries = rows ?? [];
  if (!entries.length) {
    return [createExtractionRow()];
  }
  return entries.map((row) => createExtractionRow(row.variable ?? "", row.path ?? ""));
}

function extractionRowsToConfig(rows: DraftExtractionRow[]) {
  return rows
    .map((row) => ({
      variable: row.variable.trim(),
      path: row.path.trim(),
    }))
    .filter((row) => row.variable && row.path);
}

function parseBodyText(value: unknown) {
  if (value === undefined || value === null || value === "") {
    return "{\n  \n}";
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function parseRequestBody(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return {};
  }
  try {
    return JSON.parse(trimmed);
  } catch {
    return value;
  }
}

function removeGlobalHeaderRow(index: number) {
  if (globalHeaderRows.value.length <= 1) {
    globalHeaderRows.value = [createKeyValueRow()];
    return;
  }
  globalHeaderRows.value.splice(index, 1);
}

function appendGlobalLoginHeaderRow() {
  globalLoginHeadersRows.value.push(createKeyValueRow());
}

function removeGlobalLoginHeaderRow(index: number) {
  if (globalLoginHeadersRows.value.length <= 1) {
    globalLoginHeadersRows.value = [createKeyValueRow("Content-Type", "application/json")];
    return;
  }
  globalLoginHeadersRows.value.splice(index, 1);
}

function appendGlobalLoginExtractionRow() {
  globalLoginExtractionRows.value.push(createExtractionRow());
}

function removeGlobalLoginExtractionRow(index: number) {
  if (globalLoginExtractionRows.value.length <= 1) {
    globalLoginExtractionRows.value = [createExtractionRow()];
    return;
  }
  globalLoginExtractionRows.value.splice(index, 1);
}

function appendGlobalHeaderRow() {
  globalHeaderRows.value.push(createKeyValueRow());
}

function appendInterfaceHeaderRow() {
  interfaceForm.value.headersRows.push(createKeyValueRow());
}

function removeInterfaceHeaderRow(index: number) {
  if (interfaceForm.value.headersRows.length <= 1) {
    interfaceForm.value.headersRows = [createKeyValueRow("", "")];
    return;
  }
  interfaceForm.value.headersRows.splice(index, 1);
}

function appendInterfaceResponseMappingRow() {
  interfaceForm.value.responseMappingRows.push(createKeyValueRow());
}

function removeInterfaceResponseMappingRow(index: number) {
  if (interfaceForm.value.responseMappingRows.length <= 1) {
    interfaceForm.value.responseMappingRows = [createKeyValueRow("", "")];
    return;
  }
  interfaceForm.value.responseMappingRows.splice(index, 1);
}

function appendInterfaceFieldTypeRow() {
  interfaceForm.value.fieldTypeRows.push(createKeyValueRow());
}

function removeInterfaceFieldTypeRow(index: number) {
  if (interfaceForm.value.fieldTypeRows.length <= 1) {
    interfaceForm.value.fieldTypeRows = [createKeyValueRow("", "")];
    return;
  }
  interfaceForm.value.fieldTypeRows.splice(index, 1);
}

function syncGlobalRequestConfig(config: ApiToolConfig) {
  const globalConfig = config.global_request_config;
  globalLoginEnabled.value = globalConfig?.login_request?.enabled ?? false;
  globalLoginMethod.value = globalConfig?.login_request?.method ?? "POST";
  globalLoginUrl.value = globalConfig?.login_request?.url ?? "";
  globalLoginBodyText.value = parseBodyText(globalConfig?.login_request?.body);
  globalLoginHeadersRows.value = mappingRecordToRows(
    (globalConfig?.login_request?.headers ?? { "Content-Type": "application/json" }) as Record<string, string>,
  );
  globalLoginExtractionRows.value = extractionRowsFromConfig(globalConfig?.login_request?.extractions);
  globalHeaderEnabled.value = globalConfig?.header_config?.enabled ?? false;
  globalHeaderRows.value = mappingRecordToRows(
    (globalConfig?.header_config?.headers ?? config.global_headers ?? {}) as Record<string, string>,
  );
}

function syncFromProps() {
  if (!props.product || !props.config) {
    return;
  }
  productForm.name = props.product.name;
  productForm.legacy_config_path = props.product.legacy_config_path ?? "";
  productForm.locked = props.product.locked;
  productForm.is_default = props.product.is_default;
  productForm.sort_order = props.product.sort_order;
  productForm.enable_encryption = props.config.enable_encryption;
  productForm.encrypt_url = props.config.encrypt_url;
  productForm.decrypt_url = props.config.decrypt_url;
  syncGlobalRequestConfig(props.config);

  const drafts = configToDrafts(props.config);
  scheduleTasksDraft.value = drafts.scheduleTasks;
  layoutItemsDraft.value = drafts.layoutItems;
  interfacesDraft.value = drafts.interfaces;
  sqlsDraft.value = drafts.sqls;
  normaliseLayoutPriorities();
}

watch(
  () => [props.modelValue, props.product?.id, props.config?.layout.length],
  ([modelValue]) => {
    if (modelValue) {
      syncFromProps();
    } else {
      resetDialogState();
    }
  },
  { immediate: true },
);

function openScheduleEditor(index = -1) {
  scheduleEditIndex.value = index;
  if (index >= 0) {
    Object.assign(scheduleForm, cloneValue(scheduleTasksDraft.value[index]));
  } else {
    Object.assign(scheduleForm, {
      id: "",
      jobGroup: "",
      name: "",
      row_id: 0,
    });
  }
  scheduleDialogVisible.value = true;
}

function saveScheduleEditor() {
  try {
    const nextItem = cloneValue(scheduleForm);
    if (!String(nextItem.name).trim()) {
      throw new Error("定时任务名称不能为空");
    }
    if (scheduleEditIndex.value >= 0) {
      scheduleTasksDraft.value.splice(scheduleEditIndex.value, 1, nextItem);
    } else {
      scheduleTasksDraft.value.push(nextItem);
    }
    scheduleDialogVisible.value = false;
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function removeSchedule(index: number) {
  await ElMessageBox.confirm("确认删除这个定时任务吗？", "提示", { type: "warning" });
  scheduleTasksDraft.value.splice(index, 1);
}

function openLayoutEditor(index = -1) {
  layoutEditIndex.value = index;
  if (index >= 0) {
    const current = cloneValue(layoutItemsDraft.value[index]);
    layoutForm.value = current;
    layoutOptionsForm.value = cloneValue(current.options ?? []);
    layoutMappingsForm.value = mappingRecordToRows(current.mappings);
  } else {
    layoutForm.value = createLayoutDraft();
    layoutOptionsForm.value = [];
    layoutMappingsForm.value = [createKeyValueRow()];
  }
  layoutDialogVisible.value = true;
}

function saveLayoutEditor() {
  try {
    const nextItem = cloneValue(layoutForm.value);
    const previousItem = layoutEditIndex.value >= 0 ? cloneValue(layoutItemsDraft.value[layoutEditIndex.value]) : null;
    if (nextItem.type === "interface" || nextItem.type === "sql") {
      if (!nextItem.name?.trim()) {
        throw new Error("按钮名称不能为空");
      }
    } else {
      if (!nextItem.key?.trim()) {
        throw new Error("变量 key 不能为空");
      }
      if (!nextItem.label?.trim()) {
        throw new Error("显示名称不能为空");
      }
    }
    nextItem.options = cloneValue(layoutOptionsForm.value);
    nextItem.mappings = mappingRowsToRecord(layoutMappingsForm.value);
    if (layoutEditIndex.value >= 0) {
      layoutItemsDraft.value.splice(layoutEditIndex.value, 1, nextItem);
    } else {
      layoutItemsDraft.value.push(nextItem);
    }

    if (nextItem.type === "interface") {
      const targetName = nextItem.name?.trim() ?? "";
      const existingInterface = interfacesDraft.value.find((item) => item.name.trim() === targetName);
      if (!existingInterface) {
        const newInterface = createInterfaceDraft();
        newInterface.name = targetName;
        interfacesDraft.value.push(newInterface);
      }
    }

    if (nextItem.type === "sql") {
      const targetName = nextItem.name?.trim() ?? "";
      const existingSql = sqlsDraft.value.find((item) => item.name.trim() === targetName);
      if (!existingSql) {
        const newSql = createSqlDraft();
        newSql.name = targetName;
        sqlsDraft.value.push(newSql);
      }
    }

    if (previousItem?.type === "interface") {
      const previousName = previousItem.name?.trim() ?? "";
      const targetInterface = interfacesDraft.value.find((item) => item.name.trim() === previousName);
      if (targetInterface) {
        targetInterface.name = nextItem.type === "interface" ? (nextItem.name?.trim() ?? "") : previousName;
      }
    }

    if (previousItem?.type === "sql") {
      const previousName = previousItem.name?.trim() ?? "";
      const targetSql = sqlsDraft.value.find((item) => item.name.trim() === previousName);
      if (targetSql) {
        targetSql.name = nextItem.type === "sql" ? (nextItem.name?.trim() ?? "") : previousName;
      }
    }

    normaliseLayoutPriorities();
    layoutDialogVisible.value = false;
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function removeLayout(index: number) {
  await ElMessageBox.confirm("确认删除这个布局项吗？", "提示", { type: "warning" });
  const removedItem = layoutItemsDraft.value[index];
  layoutItemsDraft.value.splice(index, 1);
  if (removedItem?.type === "interface" && removedItem.name?.trim()) {
    const interfaceIndex = interfacesDraft.value.findIndex((item) => item.name.trim() === removedItem.name?.trim());
    if (interfaceIndex >= 0) {
      interfacesDraft.value.splice(interfaceIndex, 1);
    }
  }
  if (removedItem?.type === "sql" && removedItem.name?.trim()) {
    const sqlIndex = sqlsDraft.value.findIndex((item) => item.name.trim() === removedItem.name?.trim());
    if (sqlIndex >= 0) {
      sqlsDraft.value.splice(sqlIndex, 1);
    }
  }
  normaliseLayoutPriorities();
}

function layoutTypeLabel(type: LayoutDraftItem["type"]) {
  const labels: Record<LayoutDraftItem["type"], string> = {
    field: "输入框",
    combo: "下拉框",
    interface: "接口按钮",
    sql: "SQL按钮",
    condition: "条件字段",
    formula: "公式字段",
  };
  return labels[type];
}

function onLayoutDragStart(index: number) {
  draggingLayoutIndex.value = index;
}

function onLayoutDrop(index: number) {
  const sourceIndex = draggingLayoutIndex.value;
  draggingLayoutIndex.value = -1;
  if (sourceIndex < 0 || sourceIndex === index) {
    return;
  }
  const nextItems = [...layoutItemsDraft.value];
  const [movedItem] = nextItems.splice(sourceIndex, 1);
  if (!movedItem) {
    return;
  }
  nextItems.splice(index, 0, movedItem);
  layoutItemsDraft.value = nextItems;
  normaliseLayoutPriorities();
}

function onLayoutDragEnd() {
  draggingLayoutIndex.value = -1;
}

function openInterfaceEditor(index = -1) {
  interfaceEditIndex.value = index;
  interfaceForm.value = index >= 0 ? cloneValue(interfacesDraft.value[index]) : createInterfaceDraft();
  interfaceDialogVisible.value = true;
}

function openInterfaceEditorById(localId: string) {
  const index = interfacesDraft.value.findIndex((item) => item.localId === localId);
  if (index >= 0) {
    openInterfaceEditor(index);
  }
}

function saveInterfaceEditor() {
  try {
    if (!interfaceForm.value.name.trim()) {
      throw new Error("接口名称不能为空");
    }
    if (!interfaceForm.value.url.trim()) {
      throw new Error("接口 URL 不能为空");
    }
    const nextItem = cloneValue(interfaceForm.value);
    if (interfaceEditIndex.value >= 0) {
      interfacesDraft.value.splice(interfaceEditIndex.value, 1, nextItem);
    } else {
      interfacesDraft.value.push(nextItem);
    }
    interfaceDialogVisible.value = false;
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function removeInterface(index: number) {
  await ElMessageBox.confirm("确认删除这个接口配置吗？", "提示", { type: "warning" });
  interfacesDraft.value.splice(index, 1);
}

async function removeInterfaceById(localId: string) {
  const index = interfacesDraft.value.findIndex((item) => item.localId === localId);
  if (index >= 0) {
    await removeInterface(index);
  }
}

function openSqlEditor(index = -1) {
  sqlEditIndex.value = index;
  sqlForm.value = index >= 0 ? cloneValue(sqlsDraft.value[index]) : createSqlDraft();
  sqlDialogVisible.value = true;
}

function openSqlEditorById(localId: string) {
  const index = sqlsDraft.value.findIndex((item) => item.localId === localId);
  if (index >= 0) {
    openSqlEditor(index);
  }
}

function saveSqlEditor() {
  try {
    if (!sqlForm.value.name.trim()) {
      throw new Error("SQL 名称不能为空");
    }
    if (!sqlForm.value.sql.trim()) {
      throw new Error("SQL 不能为空");
    }
    const nextItem = cloneValue(sqlForm.value);
    if (sqlEditIndex.value >= 0) {
      sqlsDraft.value.splice(sqlEditIndex.value, 1, nextItem);
    } else {
      sqlsDraft.value.push(nextItem);
    }
    sqlDialogVisible.value = false;
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function removeSql(index: number) {
  await ElMessageBox.confirm("确认删除这个 SQL 配置吗？", "提示", { type: "warning" });
  sqlsDraft.value.splice(index, 1);
}

async function removeSqlById(localId: string) {
  const index = sqlsDraft.value.findIndex((item) => item.localId === localId);
  if (index >= 0) {
    await removeSql(index);
  }
}

function ensureUnique(values: string[], label: string) {
  const seen = new Set<string>();
  for (const value of values) {
    const trimmed = value.trim();
    if (!trimmed) {
      continue;
    }
    if (seen.has(trimmed)) {
      throw new Error(`${label}存在重复名称：${trimmed}`);
    }
    seen.add(trimmed);
  }
}

function validateLayoutTargets() {
  const interfaceNames = new Set(interfacesDraft.value.map((item) => item.name.trim()).filter(Boolean));
  const sqlNames = new Set(sqlsDraft.value.map((item) => item.name.trim()).filter(Boolean));

  layoutItemsDraft.value.forEach((item) => {
    if (item.type === "interface" && item.name?.trim() && !interfaceNames.has(item.name.trim())) {
      throw new Error(`布局按钮 ${item.name} 没有对应的接口配置`);
    }
    if (item.type === "sql" && item.name?.trim() && !sqlNames.has(item.name.trim())) {
      throw new Error(`布局按钮 ${item.name} 没有对应的 SQL 配置`);
    }
  });
}

function submit() {
  try {
    if (!props.product) {
      return;
    }
    if (!productForm.name.trim()) {
      throw new Error("产品名称不能为空");
    }

    ensureUnique(layoutItemsDraft.value.map((item) => item.key ?? ""), "布局变量");
    ensureUnique(interfacesDraft.value.map((item) => item.name), "接口");
    ensureUnique(sqlsDraft.value.map((item) => item.name), "SQL");
    validateLayoutTargets();

    if (globalLoginEnabled.value && !globalLoginUrl.value.trim()) {
      throw new Error("请填写登录接口 URL");
    }

    const globalRequestConfig: ApiToolGlobalRequestConfig = {
      login_request: {
        enabled: globalLoginEnabled.value,
        protocol: "http",
        method: globalLoginMethod.value,
        url: globalLoginUrl.value.trim(),
        headers: mappingRowsToRecord(globalLoginHeadersRows.value),
        body: parseRequestBody(globalLoginBodyText.value),
        extractions: extractionRowsToConfig(globalLoginExtractionRows.value),
      },
      header_config: {
        enabled: globalHeaderEnabled.value,
        headers: mappingRowsToRecord(globalHeaderRows.value),
      },
    };

    const config = buildConfigFromDrafts({
      enableEncryption: productForm.enable_encryption,
      encryptUrl: productForm.encrypt_url,
      decryptUrl: productForm.decrypt_url,
      globalRequestConfig,
      scheduleTasks: scheduleTasksDraft.value,
      layoutItems: layoutItemsDraft.value,
      interfaces: interfacesDraft.value,
      sqls: sqlsDraft.value,
    });

    emit("save", {
      product: {
        name: productForm.name.trim(),
        legacy_config_path: productForm.legacy_config_path.trim(),
        locked: productForm.locked,
        is_default: productForm.is_default,
        sort_order: Number(productForm.sort_order || 0),
      },
      config,
    });
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}
</script>

<template>
  <el-dialog v-model="visible" title="接口工具配置" width="1180px" top="4vh">
    <el-tabs v-model="activeTab" class="config-tabs">
      <el-tab-pane label="基础配置" name="basic">
        <el-form class="basic-config-form" label-width="110px">
          <el-form-item label="产品名称" class="basic-config-item basic-config-item-wide">
            <el-input v-model="productForm.name" />
          </el-form-item>
          <el-form-item label="历史路径" class="basic-config-item basic-config-item-wide">
            <el-input v-model="productForm.legacy_config_path" />
          </el-form-item>
          <el-form-item label="排序" class="basic-config-item basic-config-item-sort">
            <el-input-number v-model="productForm.sort_order" :min="1" />
          </el-form-item>
          <el-form-item class="basic-config-check">
            <el-checkbox v-model="productForm.locked">锁定配置</el-checkbox>
          </el-form-item>
          <el-form-item class="basic-config-check">
            <el-checkbox v-model="productForm.is_default">设为默认产品</el-checkbox>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="全局配置" name="global">
        <el-form class="basic-config-form global-config-form" label-width="110px">
          <el-form-item label="加解密：" class="basic-config-item basic-config-toggle-item">
            <el-checkbox v-model="productForm.enable_encryption">启用加解密</el-checkbox>
          </el-form-item>
          <template v-if="productForm.enable_encryption">
            <div class="global-config-panel">
              <div class="global-panel-row">
                <div class="global-panel-label">加密接口 URL</div>
                <div class="global-panel-content">
                  <el-input v-model="productForm.encrypt_url" />
                </div>
              </div>
              <div class="global-panel-row">
                <div class="global-panel-label">解密接口 URL</div>
                <div class="global-panel-content">
                  <el-input v-model="productForm.decrypt_url" />
                </div>
              </div>
            </div>
          </template>

          <el-form-item label="登录态获取：" class="basic-config-item basic-config-toggle-item">
            <el-checkbox v-model="globalLoginEnabled">启用登录接口配置</el-checkbox>
          </el-form-item>
          <template v-if="globalLoginEnabled">
            <div class="global-config-panel">
              <div class="global-panel-grid">
                <div class="global-panel-row">
                  <div class="global-panel-label">请求方式</div>
                  <div class="global-panel-content">
                    <el-select v-model="globalLoginMethod">
                      <el-option v-for="item in methodOptions" :key="item" :label="item" :value="item" />
                    </el-select>
                  </div>
                </div>
                <div class="global-panel-row">
                  <div class="global-panel-label">登录 URL</div>
                  <div class="global-panel-content">
                    <el-input v-model="globalLoginUrl" placeholder="请输入登录接口地址" />
                  </div>
                </div>
              </div>

              <div class="global-panel-row global-panel-row-top">
                <div class="global-panel-label">请求头</div>
                <div class="global-panel-content">
                  <div class="inline-config-list">
                    <div v-for="(row, index) in globalLoginHeadersRows" :key="row.localId" class="inline-config-row">
                      <el-input v-model="row.key" placeholder="例如 Content-Type" />
                      <el-input v-model="row.value" placeholder="例如 application/json" />
                      <div class="inline-config-actions">
                        <el-button text circle @click="appendGlobalLoginHeaderRow">
                          <el-icon><Plus /></el-icon>
                        </el-button>
                        <el-button text circle @click="removeGlobalLoginHeaderRow(index)">
                          <el-icon><Minus /></el-icon>
                        </el-button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="global-panel-row global-panel-row-top">
                <div class="global-panel-label">请求体</div>
                <div class="global-panel-content">
                  <el-input v-model="globalLoginBodyText" type="textarea" :rows="6" />
                </div>
              </div>

              <div class="global-panel-row global-panel-row-top">
                <div class="global-panel-label">参数提取</div>
                <div class="global-panel-content">
                  <div class="inline-config-list">
                    <div
                      v-for="(row, index) in globalLoginExtractionRows"
                      :key="row.localId"
                      class="inline-config-row"
                    >
                      <el-input v-model="row.variable" placeholder="例如 token" />
                      <el-input v-model="row.path" placeholder="支持 headers.Authorization 或 body.data.token" />
                      <div class="inline-config-actions">
                        <el-button text circle @click="appendGlobalLoginExtractionRow">
                          <el-icon><Plus /></el-icon>
                        </el-button>
                        <el-button text circle @click="removeGlobalLoginExtractionRow(index)">
                          <el-icon><Minus /></el-icon>
                        </el-button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <el-form-item label="全局请求头：" class="basic-config-item basic-config-toggle-item">
            <el-checkbox v-model="globalHeaderEnabled">启用请求头配置</el-checkbox>
          </el-form-item>
          <template v-if="globalHeaderEnabled">
            <div class="global-config-panel">
              <div class="global-panel-row global-panel-row-top">
                <div class="global-panel-label">请求头</div>
                <div class="global-panel-content">
                  <div class="inline-config-list">
                    <div v-for="(row, index) in globalHeaderRows" :key="row.localId" class="inline-config-row">
                      <el-input v-model="row.key" placeholder="例如 Authorization" />
                      <el-input v-model="row.value" placeholder="支持 ${token} 变量" />
                      <div class="inline-config-actions">
                        <el-button text circle @click="appendGlobalHeaderRow">
                          <el-icon><Plus /></el-icon>
                        </el-button>
                        <el-button text circle @click="removeGlobalHeaderRow(index)">
                          <el-icon><Minus /></el-icon>
                        </el-button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="定时任务" name="schedule">
        <div class="section-toolbar">
          <span>按旧版配置方式维护任务列表</span>
          <el-button type="primary" @click="openScheduleEditor()">新增任务</el-button>
        </div>
        <el-table :data="scheduleTasksDraft" border height="360">
          <el-table-column prop="name" label="任务名称" min-width="180" />
          <el-table-column prop="id" label="任务 ID" min-width="140" />
          <el-table-column prop="jobGroup" label="任务组" min-width="160" />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ $index }">
              <el-space>
                <el-button link type="primary" @click="openScheduleEditor($index)">编辑</el-button>
                <el-button link type="danger" @click="removeSchedule($index)">删除</el-button>
              </el-space>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="布局项" name="layout">
        <div class="section-toolbar">
          <span>拖动列表即可调整首页显示顺序，保存后会按这里的顺序生效</span>
          <el-button type="primary" @click="openLayoutEditor()">新增布局项</el-button>
        </div>
        <div class="layout-drag-panel">
          <div class="layout-drag-header">
            <span class="layout-drag-header-placeholder" aria-hidden="true"></span>
            <span class="layout-drag-header-order">序号</span>
            <span>类型</span>
            <span>名称</span>
            <span>key/name</span>
            <span>首页隐藏</span>
            <span class="layout-drag-header-actions">操作</span>
          </div>
          <div
            v-for="(row, index) in layoutItemsDraft"
            :key="row.localId"
            class="layout-drag-item"
            :class="{ 'is-dragging': draggingLayoutIndex === index }"
            draggable="true"
            @dragstart="onLayoutDragStart(index)"
            @dragover.prevent
            @drop="onLayoutDrop(index)"
            @dragend="onLayoutDragEnd"
          >
            <div class="layout-drag-handle">⋮⋮</div>
            <div class="layout-drag-order">{{ index + 1 }}</div>
            <div class="layout-drag-cell type-cell">{{ layoutTypeLabel(row.type) }}</div>
            <div class="layout-drag-cell name-cell">{{ row.label || row.name || "--" }}</div>
            <div class="layout-drag-cell key-cell">{{ row.key || row.name || "--" }}</div>
            <div class="layout-drag-cell hidden-cell">{{ row.show_in_ui === false ? "是" : "否" }}</div>
            <div class="layout-drag-actions">
              <el-space>
                <el-button link type="primary" @click="openLayoutEditor(index)">编辑</el-button>
                <el-button link type="danger" @click="removeLayout(index)">删除</el-button>
              </el-space>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="接口" name="interface">
        <div class="section-toolbar">
          <span>每个接口单独维护，不再用整块 JSON 覆盖</span>
        </div>
        <el-table :data="orderedInterfacesDraft" border height="420">
          <el-table-column prop="name" label="接口名称" min-width="180" />
          <el-table-column prop="method" label="方法" width="110" />
          <el-table-column prop="url" label="URL" min-width="320" show-overflow-tooltip />
          <el-table-column label="加密" width="90">
            <template #default="{ row }">
              {{ row.enableEncryption ? "是" : "否" }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-space>
                <el-button link type="primary" @click="openInterfaceEditorById(row.localId)">编辑</el-button>
                <el-button link type="danger" @click="removeInterfaceById(row.localId)">删除</el-button>
              </el-space>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="SQL" name="sql">
        <div class="section-toolbar">
          <span>数据库连接和输出字段都按表单维护</span>
        </div>
        <el-table :data="orderedSqlsDraft" border height="420">
          <el-table-column prop="name" label="SQL 名称" min-width="180" />
          <el-table-column prop="database.host" label="主机" min-width="180" />
          <el-table-column prop="database.database" label="数据库" min-width="160" />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-space>
                <el-button link type="primary" @click="openSqlEditorById(row.localId)">编辑</el-button>
                <el-button link type="danger" @click="removeSqlById(row.localId)">删除</el-button>
              </el-space>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-space>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存配置</el-button>
      </el-space>
    </template>
  </el-dialog>

  <el-dialog v-model="scheduleDialogVisible" title="定时任务" width="560px">
    <el-form label-position="top">
      <el-form-item label="任务名称">
        <el-input v-model="scheduleForm.name" />
      </el-form-item>
      <el-form-item label="任务 ID">
        <el-input v-model="scheduleForm.id" />
      </el-form-item>
      <el-form-item label="任务组">
        <el-input v-model="scheduleForm.jobGroup" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-space>
        <el-button @click="scheduleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveScheduleEditor">确定</el-button>
      </el-space>
    </template>
  </el-dialog>

  <el-dialog v-model="layoutDialogVisible" title="布局项" width="760px">
    <el-form label-position="top">
      <el-form-item label="类型">
        <el-select v-model="layoutForm.type">
          <el-option label="输入框" value="field" />
          <el-option label="下拉框" value="combo" />
          <el-option label="接口按钮" value="interface" />
          <el-option label="SQL按钮" value="sql" />
          <el-option label="条件字段" value="condition" />
          <el-option label="公式字段" value="formula" />
        </el-select>
      </el-form-item>

      <template v-if="layoutForm.type === 'interface' || layoutForm.type === 'sql'">
        <el-form-item label="按钮名称">
          <el-input v-model="layoutForm.name" />
        </el-form-item>
      </template>

      <template v-else>
        <div class="config-grid compact">
          <el-form-item label="变量 key">
            <el-input v-model="layoutForm.key" />
          </el-form-item>
          <el-form-item label="显示名称">
            <el-input v-model="layoutForm.label" />
          </el-form-item>
        </div>
        <el-form-item>
          <el-checkbox v-model="layoutForm.show_in_ui">显示在左侧运行区</el-checkbox>
        </el-form-item>
      </template>

      <template v-if="layoutForm.type === 'field' || layoutForm.type === 'combo'">
        <div class="config-grid compact">
          <el-form-item label="默认值">
            <el-input v-model="layoutForm.default" />
          </el-form-item>
          <el-form-item label="数据类型">
            <el-input v-model="layoutForm.data_type" placeholder="string / int / float" />
          </el-form-item>
        </div>
      </template>

      <template v-if="layoutForm.type === 'combo'">
        <div class="sub-toolbar">
          <span>下拉选项</span>
          <el-button link type="primary" @click="layoutOptionsForm.push({ text: '', value: '' })">新增选项</el-button>
        </div>
        <el-table :data="layoutOptionsForm" border>
          <el-table-column label="文本">
            <template #default="{ row }">
              <el-input v-model="row.text" />
            </template>
          </el-table-column>
          <el-table-column label="值">
            <template #default="{ row }">
              <el-input v-model="row.value" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ $index }">
              <el-button link type="danger" @click="layoutOptionsForm.splice($index, 1)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>

      <template v-if="layoutForm.type === 'condition'">
        <el-form-item label="条件字段 key">
          <el-input v-model="layoutForm.condition_field" />
        </el-form-item>
        <div class="sub-toolbar">
          <span>条件映射</span>
          <el-button link type="primary" @click="layoutMappingsForm.push(createKeyValueRow())">新增映射</el-button>
        </div>
        <el-table :data="layoutMappingsForm" border>
          <el-table-column label="条件值">
            <template #default="{ row }">
              <el-input v-model="row.key" />
            </template>
          </el-table-column>
          <el-table-column label="映射字段 key">
            <template #default="{ row }">
              <el-input v-model="row.value" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ $index }">
              <el-button link type="danger" @click="layoutMappingsForm.splice($index, 1)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>

      <template v-if="layoutForm.type === 'formula'">
        <el-form-item label="公式">
          <el-input v-model="layoutForm.formula" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="公式类型">
          <el-select v-model="layoutForm.formula_type">
            <el-option
              v-for="item in formulaTypeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
      </template>
    </el-form>
    <template #footer>
      <el-space>
        <el-button @click="layoutDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveLayoutEditor">确定</el-button>
      </el-space>
    </template>
  </el-dialog>

  <el-dialog v-model="interfaceDialogVisible" title="接口配置" width="920px" top="5vh">
    <div class="interface-config-form">
      <div class="interface-top-grid">
        <div class="interface-inline-field">
          <div class="interface-inline-label">接口名称</div>
          <div class="interface-inline-content">
            <el-input v-model="interfaceForm.name" placeholder="我是接口名称" />
          </div>
        </div>
        <div class="interface-inline-field">
          <div class="interface-inline-label">请求方法</div>
          <div class="interface-inline-content">
            <el-select v-model="interfaceForm.method">
              <el-option v-for="item in methodOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
        </div>
      </div>

      <div class="interface-inline-field interface-inline-field-wide">
        <div class="interface-inline-label">URL</div>
        <div class="interface-inline-content">
          <el-input v-model="interfaceForm.url" />
        </div>
      </div>

      <div class="interface-inline-field interface-toggle-field">
        <div class="interface-inline-label"></div>
        <div class="interface-inline-content">
          <el-checkbox v-model="interfaceForm.enableEncryption">单接口启用加密</el-checkbox>
        </div>
      </div>

      <div class="interface-section-row">
        <div class="interface-section-label">请求头</div>
        <div class="interface-section-content">
          <div class="inline-config-list">
            <div v-for="(row, index) in interfaceForm.headersRows" :key="row.localId" class="inline-config-row">
              <el-input v-model="row.key" placeholder="Header" />
              <el-input v-model="row.value" placeholder="Value" />
              <div class="inline-config-actions">
                <el-button text circle @click="appendInterfaceHeaderRow">
                  <el-icon><Plus /></el-icon>
                </el-button>
                <el-button text circle @click="removeInterfaceHeaderRow(index)">
                  <el-icon><Minus /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="interface-section-row">
        <div class="interface-section-label">请求体模式</div>
        <div class="interface-section-content">
          <el-radio-group v-model="interfaceForm.requestType">
            <el-radio-button label="normal">固定请求体</el-radio-button>
            <el-radio-button label="conditional">条件请求体</el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <template v-if="interfaceForm.requestType === 'normal'">
        <div class="interface-section-row interface-section-row-top">
          <div class="interface-section-label">请求体模板</div>
          <div class="interface-section-content">
            <el-input v-model="interfaceForm.bodyTemplateText" type="textarea" :rows="8" />
          </div>
        </div>
      </template>

      <template v-else>
        <el-form-item label="条件字段">
          <el-input v-model="interfaceForm.conditionalField" />
        </el-form-item>
        <div class="sub-toolbar">
          <span>条件请求体</span>
          <el-button
            link
            type="primary"
            @click="interfaceForm.conditionalCases.push(createConditionalCaseRow())"
          >
            新增条件
          </el-button>
        </div>
        <div
          v-for="(item, index) in interfaceForm.conditionalCases"
          :key="item.localId"
          class="case-card"
        >
          <div class="case-toolbar">
            <el-input v-model="item.caseValue" placeholder="条件值" />
            <el-button link type="danger" @click="interfaceForm.conditionalCases.splice(index, 1)">删除</el-button>
          </div>
          <el-input v-model="item.bodyTemplateText" type="textarea" :rows="5" />
        </div>
      </template>

      <div class="interface-section-row">
        <div class="interface-section-label">响应参数提取</div>
        <div class="interface-section-content">
          <div class="inline-config-list">
            <div v-if="!interfaceForm.responseMappingRows.length" class="inline-config-row">
              <el-input value="" placeholder="变量 key" />
              <el-input value="" placeholder="响应路径" />
              <div class="inline-config-actions">
                <el-button text circle @click="appendInterfaceResponseMappingRow">
                  <el-icon><Plus /></el-icon>
                </el-button>
                <el-button text circle disabled>
                  <el-icon><Minus /></el-icon>
                </el-button>
              </div>
            </div>
            <div
              v-for="(row, index) in interfaceForm.responseMappingRows"
              v-else
              :key="row.localId"
              class="inline-config-row"
            >
              <el-input v-model="row.key" placeholder="变量 key" />
              <el-input v-model="row.value" placeholder="响应路径" />
              <div class="inline-config-actions">
                <el-button text circle @click="appendInterfaceResponseMappingRow">
                  <el-icon><Plus /></el-icon>
                </el-button>
                <el-button text circle @click="removeInterfaceResponseMappingRow(index)">
                  <el-icon><Minus /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="interface-section-row">
        <div class="interface-section-label">请求字段类型</div>
        <div class="interface-section-content">
          <div class="inline-config-list">
            <div v-if="!interfaceForm.fieldTypeRows.length" class="inline-config-row">
              <el-input value="" placeholder="变量 key" />
              <el-input value="" placeholder="string / int / float" />
              <div class="inline-config-actions">
                <el-button text circle @click="appendInterfaceFieldTypeRow">
                  <el-icon><Plus /></el-icon>
                </el-button>
                <el-button text circle disabled>
                  <el-icon><Minus /></el-icon>
                </el-button>
              </div>
            </div>
            <div
              v-for="(row, index) in interfaceForm.fieldTypeRows"
              v-else
              :key="row.localId"
              class="inline-config-row"
            >
              <el-input v-model="row.key" placeholder="变量 key" />
              <el-input v-model="row.value" placeholder="string / int / float" />
              <div class="inline-config-actions">
                <el-button text circle @click="appendInterfaceFieldTypeRow">
                  <el-icon><Plus /></el-icon>
                </el-button>
                <el-button text circle @click="removeInterfaceFieldTypeRow(index)">
                  <el-icon><Minus /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <template #footer>
      <el-space>
        <el-button @click="interfaceDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveInterfaceEditor">确定</el-button>
      </el-space>
    </template>
  </el-dialog>

  <el-dialog v-model="sqlDialogVisible" title="SQL 配置" width="920px" top="5vh">
    <el-form label-position="top">
      <el-form-item label="SQL 名称">
        <el-input v-model="sqlForm.name" />
      </el-form-item>
      <div class="config-grid compact">
        <el-form-item label="主机">
          <el-input v-model="sqlForm.database.host" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input-number v-model="sqlForm.database.port" :min="1" />
        </el-form-item>
        <el-form-item label="数据库">
          <el-input v-model="sqlForm.database.database" />
        </el-form-item>
        <el-form-item label="字符集">
          <el-input v-model="sqlForm.database.charset" />
        </el-form-item>
      </div>
      <div class="config-grid compact">
        <el-form-item label="用户名">
          <el-input v-model="sqlForm.database.user" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="sqlForm.database.password" show-password />
        </el-form-item>
      </div>
      <el-form-item label="SQL">
        <el-input v-model="sqlForm.sql" type="textarea" :rows="8" />
      </el-form-item>

      <div class="sub-toolbar">
        <span>输出字段</span>
        <el-button link type="primary" @click="sqlForm.outputFields.push(createOutputFieldRow())">新增字段</el-button>
      </div>
      <el-table :data="sqlForm.outputFields" border>
        <el-table-column label="字段名">
          <template #default="{ row }">
            <el-input v-model="row.field" />
          </template>
        </el-table-column>
        <el-table-column label="说明">
          <template #default="{ row }">
            <el-input v-model="row.description" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ $index }">
            <el-button link type="danger" @click="sqlForm.outputFields.splice($index, 1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-form>
    <template #footer>
      <el-space>
        <el-button @click="sqlDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSqlEditor">确定</el-button>
      </el-space>
    </template>
  </el-dialog>
</template>

<style scoped>
.config-tabs {
  min-height: 520px;
}

.config-grid {
  display: grid;
  gap: 20px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.config-grid.compact {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.basic-config-form {
  max-width: 760px;
}

.global-config-form {
  max-width: 980px;
}

.basic-config-item,
.basic-config-check {
  margin-bottom: 12px;
}

.basic-config-block {
  margin-bottom: 12px;
}

.basic-config-form :deep(.el-form-item__label) {
  padding-right: 14px;
  color: var(--qm-title);
  line-height: 32px;
}

.basic-config-form :deep(.el-form-item__content) {
  min-width: 0;
}

.basic-config-item-wide :deep(.el-input),
.basic-config-item-wide :deep(.el-input-number) {
  width: 520px;
  max-width: 100%;
}

.basic-config-item-sort :deep(.el-input-number) {
  width: 180px;
}

.basic-config-check :deep(.el-form-item__content) {
  margin-left: 110px;
}

.basic-config-toggle-item {
  margin-bottom: 10px;
}

.global-config-panel {
  margin: 0 0 18px 110px;
  padding: 14px 16px;
  border: 1px solid #e5eaf3;
  border-radius: 10px;
  background: #f8fbff;
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: calc(100% - 110px);
  max-width: 860px;
  box-sizing: border-box;
}

.global-panel-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px 20px;
}

.global-panel-row {
  display: grid;
  grid-template-columns: 116px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
}

.global-panel-row + .global-panel-row {
  margin-top: 2px;
}

.global-panel-row-top {
  align-items: start;
}

.global-panel-label {
  color: var(--qm-title);
  font-size: 14px;
  line-height: 32px;
  text-align: right;
  white-space: nowrap;
}

.global-panel-content {
  min-width: 0;
}

.interface-config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.interface-top-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px 24px;
}

.interface-inline-field,
.interface-section-row {
  display: grid;
  grid-template-columns: 110px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.interface-inline-field-wide {
  grid-template-columns: 110px minmax(0, 1fr);
}

.interface-section-row-top {
  align-items: start;
}

.interface-inline-label,
.interface-section-label {
  color: var(--qm-title);
  font-size: 14px;
  line-height: 32px;
  text-align: left;
  white-space: nowrap;
}

.interface-inline-content,
.interface-section-content {
  min-width: 0;
}

.interface-toggle-field .interface-inline-label {
  line-height: 1;
}

.inline-config-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.inline-config-row {
  display: grid;
  grid-template-columns: minmax(180px, 0.8fr) minmax(320px, 1.2fr) 72px;
  gap: 12px;
  align-items: center;
}

.inline-config-actions {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 4px;
}

.inline-config-actions :deep(.el-button) {
  width: 28px;
  height: 28px;
  color: #5b6472;
  border: 1px solid #d7deea;
  border-radius: 50%;
  background: #ffffff;
}

.inline-config-actions :deep(.el-button:hover) {
  color: var(--el-color-primary);
  border-color: #b9cbff;
  background: #f3f7ff;
}

.section-toolbar,
.sub-toolbar,
.case-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-toolbar {
  margin-bottom: 14px;
  color: var(--qm-text-secondary);
}

.sub-toolbar {
  margin: 14px 0 8px;
}

.stack-space {
  margin-top: 16px;
}

.case-card {
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: #fafafa;
}

.case-toolbar {
  margin-bottom: 8px;
}

.layout-drag-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 420px;
  padding-right: 4px;
  overflow-y: auto;
}

.layout-drag-header,
.layout-drag-item {
  display: grid;
  align-items: center;
  grid-template-columns: 18px 46px 110px minmax(140px, 1fr) minmax(140px, 1fr) 82px 120px;
  gap: 10px;
}

.layout-drag-header {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: 0 14px 6px;
  color: var(--qm-text-secondary);
  font-size: 12px;
  background: #ffffff;
}

.layout-drag-header > span {
  min-width: 0;
}

.layout-drag-header-placeholder {
  display: block;
}

.layout-drag-header-order {
  text-align: center;
}

.layout-drag-header-actions {
  justify-self: center;
}

.layout-drag-actions {
  justify-self: center;
}

.layout-drag-item {
  padding: 10px 14px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: #ffffff;
  cursor: move;
}

.layout-drag-item.is-dragging {
  opacity: 0.55;
  border-color: var(--el-color-primary);
  background: #f5f9ff;
}

.layout-drag-handle {
  color: #909399;
  font-size: 16px;
  line-height: 1;
  letter-spacing: -1px;
}

.layout-drag-order {
  color: #909399;
  font-size: 12px;
  text-align: center;
}

.layout-drag-cell {
  min-width: 0;
  color: var(--qm-title);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.type-cell,
.hidden-cell {
  color: var(--qm-text-secondary);
}

@media (max-width: 900px) {
  .config-grid,
  .config-grid.compact {
    grid-template-columns: 1fr;
  }

  .global-config-panel {
    margin-left: 0;
    padding: 12px;
  }

  .global-panel-grid {
    grid-template-columns: 1fr;
  }

  .interface-top-grid {
    grid-template-columns: 1fr;
  }

  .global-panel-row {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .global-panel-label {
    text-align: left;
    line-height: 1.5;
  }

  .inline-config-row {
    grid-template-columns: 1fr;
  }

  .interface-inline-field,
  .interface-section-row,
  .interface-inline-field-wide {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .interface-inline-label,
  .interface-section-label {
    line-height: 1.5;
  }

  .layout-drag-header {
    display: none;
  }

  .layout-drag-item {
    grid-template-columns: 18px 36px 1fr;
    align-items: start;
  }

  .type-cell,
  .name-cell,
  .key-cell,
  .hidden-cell {
    grid-column: 3;
  }

  .hidden-cell {
    padding-bottom: 4px;
  }
}
</style>
