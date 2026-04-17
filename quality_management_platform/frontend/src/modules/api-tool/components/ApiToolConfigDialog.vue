<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Minus, Plus } from "@element-plus/icons-vue";

import {
  buildConfigFromDrafts,
  configToDrafts,
  createConditionalCaseRow,
  createConditionalFieldRow,
  createExtractionRow,
  createInterfaceDraft,
  createKeyValueRow,
  createLayoutDraft,
  createOutputFieldRow,
  createSqlDraft,
  type DraftConditionalCaseRow,
  type DraftConditionalFieldRow,
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
const dataTypeOptions = [
  { label: "字符串", value: "string" },
  { label: "整数", value: "int" },
  { label: "浮点数", value: "float" },
];
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

const availableConditionalFields = computed(() =>
  layoutItemsDraft.value
    .filter((item) => item.type === "combo" && item.key?.trim())
    .map((item) => ({
      label: item.label?.trim() ? `${item.label.trim()} (${item.key?.trim() || ""})` : item.key?.trim() || "",
      value: item.key?.trim() || "",
      options: item.options ?? [],
    })),
);

const availableConditionTargetFields = computed(() =>
  layoutItemsDraft.value
    .filter((item) => item.type === "field" && item.key?.trim())
    .map((item) => ({
      label: item.label?.trim() ? `${item.label.trim()} (${item.key?.trim() || ""})` : item.key?.trim() || "",
      value: item.key?.trim() || "",
    })),
);

function getConditionalFieldOptions(fieldKey: string) {
  return (
    availableConditionalFields.value.find((item) => item.value === fieldKey)?.options ?? []
  );
}

function syncLayoutMappingsFromConditionField() {
  const options = getConditionalFieldOptions(layoutForm.value.condition_field ?? "");
  if (!options.length) {
    layoutMappingsForm.value = [createKeyValueRow()];
    return;
  }

  const existingMappings = mappingRowsToRecord(layoutMappingsForm.value);
  layoutMappingsForm.value = options.map((option) =>
    createKeyValueRow(option.value, existingMappings[option.value] ?? ""),
  );
}

function getConditionMappingDisplayText(conditionValue: string) {
  const options = getConditionalFieldOptions(layoutForm.value.condition_field ?? "");
  const matched = options.find((option) => option.value === conditionValue);
  if (!matched) {
    return conditionValue;
  }
  return matched.text?.trim() || matched.value;
}

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

function appendConditionalRequestBody() {
  interfaceForm.value.conditionalCases.push(createConditionalCaseRow());
}

function removeConditionalRequestBody(index: number) {
  if (interfaceForm.value.conditionalCases.length <= 1) {
    interfaceForm.value.conditionalCases = [createConditionalCaseRow()];
    return;
  }
  interfaceForm.value.conditionalCases.splice(index, 1);
}

function appendConditionalField(caseRow: DraftConditionalCaseRow) {
  caseRow.conditions.push(createConditionalFieldRow());
}

function removeConditionalField(caseRow: DraftConditionalCaseRow, index: number) {
  if (caseRow.conditions.length <= 1) {
    caseRow.conditions = [createConditionalFieldRow()];
    return;
  }
  caseRow.conditions.splice(index, 1);
}

function onConditionalFieldChange(condition: DraftConditionalFieldRow) {
  condition.values = [];
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
    layoutOptionsForm.value = cloneValue(current.options?.length ? current.options : [{ text: "", value: "" }]);
    layoutMappingsForm.value = mappingRecordToRows(current.mappings);
  } else {
    layoutForm.value = createLayoutDraft();
    layoutOptionsForm.value = [{ text: "", value: "" }];
    layoutMappingsForm.value = [createKeyValueRow()];
  }
  if (layoutForm.value.type === "condition" && layoutForm.value.condition_field) {
    syncLayoutMappingsFromConditionField();
  }
  layoutDialogVisible.value = true;
}

function appendLayoutOptionRow() {
  layoutOptionsForm.value.push({ text: "", value: "" });
}

function removeLayoutOptionRow(index: number) {
  if (layoutOptionsForm.value.length <= 1) {
    layoutOptionsForm.value = [{ text: "", value: "" }];
    return;
  }
  layoutOptionsForm.value.splice(index, 1);
}

function appendLayoutMappingRow() {
  layoutMappingsForm.value.push(createKeyValueRow());
}

function removeLayoutMappingRow(index: number) {
  if (layoutMappingsForm.value.length <= 1) {
    layoutMappingsForm.value = [createKeyValueRow()];
    return;
  }
  layoutMappingsForm.value.splice(index, 1);
}

watch(
  () => layoutForm.value.condition_field,
  (nextValue, previousValue) => {
    if (!layoutDialogVisible.value || layoutForm.value.type !== "condition" || nextValue === previousValue) {
      return;
    }
    syncLayoutMappingsFromConditionField();
  },
);

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
    if (interfaceForm.value.requestType === "conditional") {
      for (const [caseIndex, caseRow] of interfaceForm.value.conditionalCases.entries()) {
        const validConditions = caseRow.conditions.filter(
          (condition) => condition.field.trim() && condition.values.length,
        );
        if (!validConditions.length) {
          throw new Error(`条件请求体${caseIndex + 1} 至少需要一个完整条件`);
        }
      }
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
  if (!sqlForm.value.outputFields.length) {
    sqlForm.value.outputFields = [createOutputFieldRow()];
  }
  sqlDialogVisible.value = true;
}

function openSqlEditorById(localId: string) {
  const index = sqlsDraft.value.findIndex((item) => item.localId === localId);
  if (index >= 0) {
    openSqlEditor(index);
  }
}

function appendSqlOutputFieldRow() {
  sqlForm.value.outputFields.push(createOutputFieldRow());
}

function removeSqlOutputFieldRow(index: number) {
  if (sqlForm.value.outputFields.length <= 1) {
    sqlForm.value.outputFields = [createOutputFieldRow()];
    return;
  }
  sqlForm.value.outputFields.splice(index, 1);
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
    <div class="dialog-inline-form">
      <div class="dialog-inline-row">
        <div class="dialog-inline-label">任务名称</div>
        <div class="dialog-inline-content">
          <el-input v-model="scheduleForm.name" />
        </div>
      </div>
      <div class="dialog-inline-row">
        <div class="dialog-inline-label">任务 ID</div>
        <div class="dialog-inline-content">
          <el-input v-model="scheduleForm.id" />
        </div>
      </div>
      <div class="dialog-inline-row">
        <div class="dialog-inline-label">任务组</div>
        <div class="dialog-inline-content">
          <el-input v-model="scheduleForm.jobGroup" />
        </div>
      </div>
    </div>
    <template #footer>
      <el-space>
        <el-button @click="scheduleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveScheduleEditor">确定</el-button>
      </el-space>
    </template>
  </el-dialog>

  <el-dialog v-model="layoutDialogVisible" title="布局项" width="760px">
    <div class="dialog-inline-form">
      <div class="dialog-inline-row">
        <div class="dialog-inline-label">类型</div>
        <div class="dialog-inline-content">
          <el-select v-model="layoutForm.type">
            <el-option label="输入框" value="field" />
            <el-option label="下拉框" value="combo" />
            <el-option label="接口按钮" value="interface" />
            <el-option label="SQL按钮" value="sql" />
            <el-option label="条件字段" value="condition" />
            <el-option label="公式字段" value="formula" />
          </el-select>
        </div>
      </div>

      <template v-if="layoutForm.type === 'interface' || layoutForm.type === 'sql'">
        <div class="dialog-inline-row">
          <div class="dialog-inline-label">按钮名称</div>
          <div class="dialog-inline-content">
            <el-input v-model="layoutForm.name" />
          </div>
        </div>
      </template>

      <template v-else>
        <div class="config-grid compact layout-inline-grid">
          <div class="dialog-inline-row">
            <div class="dialog-inline-label">显示名称</div>
            <div class="dialog-inline-content">
              <el-input v-model="layoutForm.label" />
            </div>
          </div>
          <div class="dialog-inline-row">
            <div class="dialog-inline-label">变量字段</div>
            <div class="dialog-inline-content">
              <el-input v-model="layoutForm.key" />
            </div>
          </div>

        </div>
        <div class="dialog-inline-row">
          <div class="dialog-inline-label">显示配置</div>
          <div class="dialog-inline-content">
            <el-checkbox v-model="layoutForm.show_in_ui">显示在左侧运行区</el-checkbox>
          </div>
        </div>
      </template>

      <template v-if="layoutForm.type === 'field' || layoutForm.type === 'combo'">
        <div class="config-grid compact layout-inline-grid">
          <div class="dialog-inline-row">
            <div class="dialog-inline-label">默认值</div>
            <div class="dialog-inline-content">
              <el-input v-model="layoutForm.default" />
            </div>
          </div>
          <div class="dialog-inline-row">
            <div class="dialog-inline-label">数据类型</div>
            <div class="dialog-inline-content">
              <el-select v-model="layoutForm.data_type" placeholder="请选择数据类型">
                <el-option
                  v-for="item in dataTypeOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </div>
          </div>
        </div>
      </template>

      <template v-if="layoutForm.type === 'combo'">
        <div class="sub-toolbar">
          <span>下拉选项</span>
        </div>
        <div class="inline-config-list">
          <div v-for="(row, index) in layoutOptionsForm" :key="`option-${index}`" class="layout-option-row">
            <div class="layout-option-text">显示文本</div>
            <el-input v-model="row.text" placeholder="文本" />
            <div class="layout-option-text">选项值</div>
            <el-input v-model="row.value" placeholder="值" />
            <div class="inline-config-actions">
              <el-button text circle @click="appendLayoutOptionRow">
                <el-icon><Plus /></el-icon>
              </el-button>
              <el-button text circle @click="removeLayoutOptionRow(index)">
                <el-icon><Minus /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </template>

      <template v-if="layoutForm.type === 'condition'">
        <div class="dialog-inline-row">
          <div class="dialog-inline-label">条件字段</div>
          <div class="dialog-inline-content">
            <el-select v-model="layoutForm.condition_field" placeholder="请选择条件字段" clearable filterable>
              <el-option
                v-for="option in availableConditionalFields"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </div>
        </div>
        <div v-if="layoutForm.condition_field" class="nested-config-panel">
          <div class="sub-toolbar nested-config-toolbar">
            <span>条件映射</span>
          </div>
          <div class="inline-config-list">
            <div v-for="row in layoutMappingsForm" :key="row.localId" class="layout-option-row layout-mapping-row">
              <div class="layout-option-text">条件值</div>
              <div class="condition-value-text">{{ getConditionMappingDisplayText(row.key) || "--" }}</div>
              <div class="layout-option-text">映射字段</div>
              <el-select v-model="row.value" placeholder="请选择映射字段" clearable filterable>
                <el-option
                  v-for="option in availableConditionTargetFields"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </div>
          </div>
        </div>
      </template>

      <template v-if="layoutForm.type === 'formula'">
        <div class="dialog-inline-row dialog-inline-row-top">
          <div class="dialog-inline-label">公式</div>
          <div class="dialog-inline-content">
            <el-input v-model="layoutForm.formula" type="textarea" :rows="3" />
          </div>
        </div>
        <div class="dialog-inline-row">
          <div class="dialog-inline-label">公式类型</div>
          <div class="dialog-inline-content">
            <el-select v-model="layoutForm.formula_type">
              <el-option
                v-for="item in formulaTypeOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </div>
        </div>
      </template>
    </div>
    <template #footer>
      <el-space>
        <el-button @click="layoutDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveLayoutEditor">确定</el-button>
      </el-space>
    </template>
  </el-dialog>

  <el-dialog v-model="interfaceDialogVisible" title="接口配置" width="920px" top="5vh">
    <div class="interface-config-form">
      <div class="interface-inline-field interface-inline-field-wide interface-name-row">
        <div class="interface-inline-label">接口名称</div>
        <div class="interface-inline-content">
          <el-input v-model="interfaceForm.name" placeholder="我是接口名称" />
        </div>
      </div>

      <div class="interface-top-grid">
        <div class="interface-inline-field interface-method-row">
          <div class="interface-inline-label">请求方法</div>
          <div class="interface-inline-content">
            <el-select v-model="interfaceForm.method">
              <el-option v-for="item in methodOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
        </div>
        <div class="interface-inline-field interface-url-row">
          <div class="interface-inline-label">URL</div>
          <div class="interface-inline-content">
            <el-input v-model="interfaceForm.url" />
          </div>
        </div>
      </div>

      <div class="interface-inline-field interface-toggle-field">
        <div class="interface-inline-label">加解密配置</div>
        <div class="interface-inline-content">
          <el-checkbox v-model="interfaceForm.enableEncryption">单接口启用加密</el-checkbox>
        </div>
      </div>

      <div class="interface-section-row">
        <div class="interface-section-label">请求头</div>
        <div class="interface-section-content">
          <div class="interface-config-panel">
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

      <div class="interface-section-row interface-section-row-top">
        <div class="interface-section-label"></div>
        <div class="interface-section-content">
          <div class="request-mode-panel">
            <template v-if="interfaceForm.requestType === 'normal'">
              <div class="request-body-inline-panel">
                <div class="request-body-inline-label">固定请求体</div>
                <div class="request-body-inline-content">
                  <el-input v-model="interfaceForm.bodyTemplateText" type="textarea" :rows="6" />
                </div>
              </div>
            </template>

            <template v-else>
              <div class="request-body-inline-panel">
                <div class="request-body-inline-label">默认请求体</div>
                <div class="request-body-inline-content">
                  <el-input v-model="interfaceForm.defaultBodyTemplateText" type="textarea" :rows="6" />
                </div>
              </div>

              <div class="request-body-group">
                <div
                  v-for="(item, index) in interfaceForm.conditionalCases"
                  :key="item.localId"
                  class="case-card-wrap"
                >
                  <div class="case-card">
                    <div class="case-card-header">
                      <div class="case-card-title">条件请求体 {{ index + 1 }}</div>
                      <div class="case-card-actions">
                        <el-button
                          class="request-body-icon-button is-add"
                          text
                          circle
                          @click="appendConditionalRequestBody"
                        >
                          <el-icon><Plus /></el-icon>
                        </el-button>
                        <el-button
                          class="request-body-icon-button is-remove"
                          text
                          circle
                          @click="removeConditionalRequestBody(index)"
                        >
                          <el-icon><Minus /></el-icon>
                        </el-button>
                      </div>
                    </div>
                    <div
                      v-for="(condition, conditionIndex) in item.conditions"
                      :key="condition.localId"
                      class="conditional-field-row"
                    >
                      <div class="conditional-field-label">条件字段</div>
                      <el-select
                        v-model="condition.field"
                        class="conditional-field-select"
                        placeholder="条件字段"
                        clearable
                        filterable
                        @change="onConditionalFieldChange(condition)"
                      >
                        <el-option
                          v-for="option in availableConditionalFields"
                          :key="option.value"
                          :label="option.label"
                          :value="option.value"
                        />
                      </el-select>
                      <el-select
                        v-model="condition.values"
                        class="conditional-field-value"
                        placeholder="条件值"
                        multiple
                        collapse-tags
                        collapse-tags-tooltip
                        clearable
                      >
                        <el-option
                          v-for="option in getConditionalFieldOptions(condition.field)"
                          :key="`${condition.localId}-${option.value}`"
                          :label="option.text"
                          :value="option.value"
                        />
                      </el-select>
                      <div class="inline-config-actions">
                        <el-button text circle @click="appendConditionalField(item)">
                          <el-icon><Plus /></el-icon>
                        </el-button>
                        <el-button text circle @click="removeConditionalField(item, conditionIndex)">
                          <el-icon><Minus /></el-icon>
                        </el-button>
                      </div>
                    </div>
                    <div class="request-body-inline-panel case-body-inline-panel">
                      <div class="request-body-inline-label">请求体</div>
                      <div class="request-body-inline-content">
                      <el-input v-model="item.bodyTemplateText" type="textarea" :rows="6" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>

      <div class="interface-section-row">
        <div class="interface-section-label">响应参数提取</div>
        <div class="interface-section-content">
          <div class="interface-config-panel">
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
      </div>

      <div class="interface-section-row">
        <div class="interface-section-label">请求字段类型</div>
        <div class="interface-section-content">
          <div class="interface-config-panel">
            <div class="inline-config-list">
              <div v-if="!interfaceForm.fieldTypeRows.length" class="inline-config-row">
                <el-input value="" placeholder="变量 key" />
                <el-select model-value="" placeholder="请选择数据类型">
                  <el-option
                    v-for="item in dataTypeOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
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
                <el-select v-model="row.value" placeholder="请选择数据类型">
                  <el-option
                    v-for="item in dataTypeOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
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
    </div>
    <template #footer>
      <el-space>
        <el-button @click="interfaceDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveInterfaceEditor">确定</el-button>
      </el-space>
    </template>
  </el-dialog>

  <el-dialog v-model="sqlDialogVisible" title="SQL 配置" width="920px" top="5vh">
    <div class="sql-config-form">
      <div class="sql-inline-row sql-inline-row-top">
        <div class="sql-inline-label">SQL 名称</div>
        <div class="sql-inline-content">
          <el-input v-model="sqlForm.name" />
        </div>
      </div>

      <div class="sql-inline-grid">
        <div class="sql-inline-row">
          <div class="sql-inline-label">主机</div>
          <div class="sql-inline-content">
            <el-input v-model="sqlForm.database.host" />
          </div>
        </div>
        <div class="sql-inline-row">
          <div class="sql-inline-label">端口</div>
          <div class="sql-inline-content">
            <el-input-number v-model="sqlForm.database.port" :min="1" class="sql-port-input" />
          </div>
        </div>
        <div class="sql-inline-row">
          <div class="sql-inline-label">数据库</div>
          <div class="sql-inline-content">
            <el-input v-model="sqlForm.database.database" />
          </div>
        </div>
        <div class="sql-inline-row">
          <div class="sql-inline-label">字符集</div>
          <div class="sql-inline-content">
            <el-input v-model="sqlForm.database.charset" />
          </div>
        </div>
        <div class="sql-inline-row">
          <div class="sql-inline-label">用户名</div>
          <div class="sql-inline-content">
            <el-input v-model="sqlForm.database.user" />
          </div>
        </div>
        <div class="sql-inline-row">
          <div class="sql-inline-label">密码</div>
          <div class="sql-inline-content">
            <el-input v-model="sqlForm.database.password" show-password />
          </div>
        </div>
      </div>

      <div class="sql-inline-row sql-inline-row-top">
        <div class="sql-inline-label">SQL 语句</div>
        <div class="sql-inline-content">
          <el-input
            v-model="sqlForm.sql"
            type="textarea"
            :rows="6"
            placeholder="请输入 SELECT 查询语句，可通过 ${变量名} 引用布局变量"
          />
        </div>
      </div>

      <div class="sql-inline-row sql-inline-row-top">
        <div class="sql-inline-label">输出字段</div>
        <div class="sql-inline-content">
          <div class="interface-config-panel sql-output-panel">
            <div class="inline-config-list sql-output-list">
              <div
                v-for="(row, index) in sqlForm.outputFields"
                :key="row.localId"
                class="sql-output-row"
              >
                <div class="sql-output-text">字段名</div>
                <el-input v-model="row.field" placeholder="请输入字段名" />
                <div class="sql-output-text">说明</div>
                <el-input v-model="row.description" placeholder="请输入字段说明" />
                <div class="inline-config-actions">
                  <el-button text circle @click="appendSqlOutputFieldRow">
                    <el-icon><Plus /></el-icon>
                  </el-button>
                  <el-button text circle @click="removeSqlOutputFieldRow(index)">
                    <el-icon><Minus /></el-icon>
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
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
  gap: 12px;
}

.interface-top-grid {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 18px 16px;
}

.interface-inline-field,
.interface-section-row {
  display: grid;
  grid-template-columns: 110px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.interface-inline-field-wide {
  grid-template-columns: 110px minmax(0, 1fr);
}

.interface-name-row .interface-inline-content {
  max-width: 520px;
}

.interface-method-row {
  grid-template-columns: 110px minmax(0, 1fr);
}

.interface-url-row {
  grid-template-columns: 44px minmax(0, 1fr);
  gap: 10px;
}

.interface-method-row .interface-inline-content {
  max-width: 160px;
}

.interface-method-row .interface-inline-content :deep(.el-select),
.interface-url-row .interface-inline-content :deep(.el-input) {
  width: 100%;
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

.interface-config-panel {
  padding: 12px 14px;
  border: 1px solid #e5eaf3;
  border-radius: 10px;
  background: #fafcff;
}

.interface-toggle-field .interface-inline-label {
  line-height: 1;
}

.dialog-inline-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dialog-inline-row {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.dialog-inline-label {
  color: var(--qm-title);
  font-size: 14px;
  line-height: 32px;
  white-space: nowrap;
}

.dialog-inline-content {
  min-width: 0;
}

.layout-inline-grid {
  gap: 12px 20px;
}

.layout-option-row {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr) 64px minmax(0, 1fr) 72px;
  gap: 12px;
  align-items: center;
}

.layout-option-text {
  color: var(--qm-text-secondary);
  font-size: 13px;
  text-align: right;
  white-space: nowrap;
}

.layout-mapping-row {
  grid-template-columns: 64px minmax(0, 1fr) 64px minmax(0, 1fr);
}

.condition-value-text {
  min-height: 32px;
  display: flex;
  align-items: center;
  color: var(--qm-title);
  padding: 0 4px;
}

.nested-config-panel {
  margin-left: 100px;
  margin-top: 8px;
  padding: 12px 14px;
  border: 1px solid #e5eaf3;
  border-radius: 10px;
  background: #fafcff;
}

.nested-config-toolbar {
  margin-top: 0;
}

.dialog-inline-row-top {
  align-items: start;
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
  width: auto;
  min-width: 0;
  height: auto;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  font-size: 14px;
  line-height: 1;
  color: #2bb673;
}

.inline-config-actions :deep(.el-button:hover) {
  background: transparent;
}

.inline-config-actions :deep(.el-button + .el-button) {
  color: #d93025;
  margin-left: 0;
}

.sql-output-list {
  gap: 10px;
}

.sql-config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sql-inline-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 14px 20px;
}

.sql-inline-row {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.sql-inline-row-top {
  align-items: start;
}

.sql-inline-label {
  color: var(--qm-title);
  font-size: 14px;
  line-height: 32px;
  white-space: nowrap;
}

.sql-inline-content {
  min-width: 0;
}

.sql-output-panel {
  padding-top: 10px;
  padding-bottom: 10px;
}

.sql-output-row {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr) 48px minmax(0, 1fr) 72px;
  gap: 12px;
  align-items: center;
}

.sql-output-text {
  color: var(--qm-text-secondary);
  font-size: 13px;
  text-align: right;
  white-space: nowrap;
}

.sql-port-input {
  width: 100%;
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
  margin-left: 0;
  margin-bottom: 8px;
  padding: 10px 12px;
  border: 1px solid #dfe7f5;
  border-radius: 10px;
  background: #f7fbff;
}

.case-toolbar {
  margin-bottom: 8px;
}

.case-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.case-card-title {
  color: var(--qm-title);
  font-size: 14px;
  font-weight: 500;
}

.conditional-field-row {
  display: grid;
  grid-template-columns: 88px 260px 300px 72px;
  gap: 10px;
  align-items: center;
  margin-bottom: 8px;
  width: max-content;
  max-width: 100%;
}

.conditional-field-label {
  color: var(--qm-title);
  font-size: 14px;
  line-height: 32px;
  white-space: nowrap;
}

.conditional-field-select,
.conditional-field-value {
  width: 100%;
  max-width: 100%;
}

.request-mode-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.request-body-panel {
  margin-left: 0;
  padding: 12px 14px;
  border: 1px solid #e5eaf3;
  border-radius: 10px;
  background: #fafcff;
}

.request-body-inline-panel {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  padding: 10px 12px;
  border: 1px solid #e5eaf3;
  border-radius: 10px;
  background: #fafcff;
}

.request-body-inline-label {
  color: var(--qm-title);
  font-size: 14px;
  line-height: 32px;
  white-space: nowrap;
}

.request-body-inline-content {
  min-width: 0;
}

.request-body-panel-label {
  margin-bottom: 8px;
  color: var(--qm-title);
  font-size: 14px;
}

.request-body-toolbar {
  margin: 2px 0 0;
}

.case-body-panel {
  margin-left: 0;
  margin-top: 4px;
  background: #ffffff;
}

.case-body-inline-panel {
  margin-top: 4px;
  padding: 0;
  border: none;
  background: transparent;
  border-radius: 0;
}

.request-body-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.case-card-wrap {
  display: block;
}

.case-card-actions {
  display: flex;
  flex-direction: row;
  gap: 4px;
  align-items: center;
  justify-content: flex-end;
  align-self: flex-start;
}

.request-body-icon-button {
  width: auto;
  min-width: 0;
  height: auto;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  font-size: 16px;
  line-height: 1;
}

.request-body-icon-button.is-add {
  color: #2bb673;
}

.request-body-icon-button.is-remove {
  color: #d93025;
}

.request-body-icon-button :deep(.el-icon) {
  font-size: 16px;
}

.request-body-icon-button :deep(.el-icon svg) {
  display: block;
}

.section-toolbar :deep(.el-button),
.sub-toolbar :deep(.el-button),
.case-toolbar :deep(.el-button),
:deep(.el-dialog__footer .el-button) {
  min-width: 64px;
  height: 30px;
  padding: 0 12px;
  border-radius: 6px;
  font-size: 12px;
}

.section-toolbar :deep(.el-button),
.sub-toolbar :deep(.el-button),
.case-toolbar :deep(.el-button) {
  min-width: 56px;
  height: 28px;
  padding: 0 10px;
}

.section-toolbar :deep(.el-button.is-link),
.sub-toolbar :deep(.el-button.is-link),
.case-toolbar :deep(.el-button.is-link) {
  min-width: 0;
  height: auto;
  padding: 0 2px;
  border-radius: 0;
  font-size: 12px;
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
  grid-template-columns: 46px 110px minmax(140px, 1fr) minmax(140px, 1fr) 82px 120px;
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
  display: none;
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
  display: none;
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

  .sql-inline-grid {
    grid-template-columns: 1fr;
  }

  .sql-inline-row {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .sql-inline-label {
    line-height: 1.5;
  }

  .conditional-field-row {
    grid-template-columns: 1fr;
  }

  .conditional-field-label {
    line-height: 1.5;
  }

  .request-body-panel,
  .request-body-inline-panel,
  .request-body-toolbar,
  .case-card,
  .case-card-wrap {
    margin-left: 0;
  }

  .request-body-inline-panel {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .request-body-inline-label {
    line-height: 1.5;
  }

  .layout-option-row {
    grid-template-columns: 1fr;
  }

  .layout-option-text {
    text-align: left;
  }

  .sql-output-row {
    grid-template-columns: 1fr;
  }

  .sql-output-text {
    text-align: left;
  }

  .nested-config-panel {
    margin-left: 0;
    padding: 12px;
  }

  .interface-inline-field,
  .interface-section-row,
  .interface-inline-field-wide {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .dialog-inline-row {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .interface-inline-label,
  .interface-section-label,
  .dialog-inline-label {
    line-height: 1.5;
  }

  .layout-drag-header {
    display: none;
  }

  .layout-drag-item {
    grid-template-columns: 36px 1fr;
    align-items: start;
  }

  .type-cell,
  .name-cell,
  .key-cell,
  .hidden-cell {
    grid-column: 2;
  }

  .hidden-cell {
    padding-bottom: 4px;
  }
}
</style>
