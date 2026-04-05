<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";

import { createToolCard, updateToolCard } from "../api";
import type {
  ToolCard,
  ToolCardDraft,
  ToolCardOption,
  ToolCardParameter,
  ToolCardPythonConfig,
  ToolCardHttpConfig,
  ToolCardSqlConfig,
} from "../types";

const props = defineProps<{
  modelValue: boolean;
  folderId: number | null;
  card?: ToolCard | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  saved: [card: ToolCard];
}>();

const saving = ref(false);
const draggingParameterIndex = ref(-1);
const draggingOptionState = ref<{ parameterIndex: number; optionIndex: number } | null>(null);

function normalizeAssociationValues(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).filter(Boolean);
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) {
      return [];
    }
    try {
      const parsed = JSON.parse(trimmed) as unknown;
      if (Array.isArray(parsed)) {
        return parsed.map((item) => String(item)).filter(Boolean);
      }
    } catch {
      return trimmed
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
    }
  }
  if (value === null || value === undefined || value === "") {
    return [];
  }
  return [String(value)];
}

function createDefaultSqlConfig(): ToolCardSqlConfig {
  return {
    host: "localhost",
    port: 3306,
    username: "root",
    password: "",
    database_name: "",
    query_text: "",
  };
}

function createDefaultHttpConfig(): ToolCardHttpConfig {
  return {
    url: "",
    method: "GET",
    headers_text: "{\n  \n}",
    body_text: "{\n  \n}",
  };
}

function createDefaultPythonConfig(): ToolCardPythonConfig {
  return {
    module_name: "",
    class_name: "",
    method_name: "",
    args_text: "[]",
  };
}

function createParameter(index = 1): ToolCardParameter {
  return {
    field_key: "",
    display_name: "",
    field_type: "input",
    default_value: "",
    required: false,
    association_enabled: false,
    association_field: "",
    association_value: [],
    sort_order: index,
    options: [],
  };
}

function sortOptions(options: ToolCardOption[]) {
  return [...options].sort((left, right) => {
    const orderDiff = left.sort_order - right.sort_order;
    if (orderDiff !== 0) {
      return orderDiff;
    }
    return (left.id ?? 0) - (right.id ?? 0);
  });
}

function cloneOption(option: ToolCardOption): ToolCardOption {
  return {
    id: option.id,
    value: option.value,
    label: option.label,
    sort_order: option.sort_order,
  };
}

function cloneParameter(parameter: ToolCardParameter): ToolCardParameter {
  return {
    id: parameter.id,
    field_key: parameter.field_key,
    display_name: parameter.display_name,
    field_type: parameter.field_type,
    default_value: parameter.default_value ?? "",
    required: parameter.required,
    association_enabled: parameter.association_enabled,
    association_field: parameter.association_field ?? "",
    association_value: normalizeAssociationValues(parameter.association_value),
    sort_order: parameter.sort_order,
    options: sortOptions(parameter.options).map(cloneOption),
  };
}

function createDraft(folderId: number | null): ToolCardDraft {
  return {
    folder_id: folderId ?? 0,
    name: "",
    description: "",
    card_type: "sql",
    sort_order: 0,
    enabled: true,
    sql_config: createDefaultSqlConfig(),
    http_config: createDefaultHttpConfig(),
    python_config: createDefaultPythonConfig(),
    parameters: [],
  };
}

function draftFromCard(card: ToolCard): ToolCardDraft {
  const parameters = [...card.parameters]
    .sort((left, right) => {
      const orderDiff = left.sort_order - right.sort_order;
      if (orderDiff !== 0) {
        return orderDiff;
      }
      return (left.id ?? 0) - (right.id ?? 0);
    })
    .map(cloneParameter);
  return {
    folder_id: card.folder_id,
    name: card.name,
    description: card.description,
    card_type: card.card_type,
    sort_order: card.sort_order,
    enabled: card.enabled,
    sql_config: { ...createDefaultSqlConfig(), ...card.sql_config },
    http_config: { ...createDefaultHttpConfig(), ...card.http_config },
    python_config: { ...createDefaultPythonConfig(), ...card.python_config },
    parameters,
  };
}

const draft = reactive<ToolCardDraft>(createDraft(props.folderId));

function resetDraft() {
  const source = props.card ? draftFromCard(props.card) : createDraft(props.folderId);
  draft.folder_id = source.folder_id;
  draft.name = source.name;
  draft.description = source.description;
  draft.card_type = source.card_type;
  draft.sort_order = source.sort_order;
  draft.enabled = source.enabled;
  draft.sql_config = { ...source.sql_config };
  draft.http_config = { ...source.http_config };
  draft.python_config = { ...source.python_config };
  draft.parameters = source.parameters.map(cloneParameter);
}

watch(
  () => [props.modelValue, props.folderId, props.card?.id] as const,
  ([visible]) => {
    if (visible) {
      resetDraft();
    }
  },
  { immediate: true },
);

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit("update:modelValue", value),
});

const dialogTitle = computed(() => (props.card ? "卡片配置" : "添加卡片"));

const associationFieldCandidates = computed(() =>
  draft.parameters.filter(
    (parameter) =>
      parameter.field_key &&
      (
        parameter.field_type === "select" ||
        parameter.field_type === "radio" ||
        parameter.field_type === "multi_select"
      ),
  ),
);

function closeDialog() {
  dialogVisible.value = false;
}

function normaliseOptionSortOrders(parameter: ToolCardParameter) {
  parameter.options.forEach((option, order) => {
    option.sort_order = order + 1;
  });
}

function normaliseParameterSortOrders() {
  draft.parameters.forEach((parameter, order) => {
    parameter.sort_order = order + 1;
    normaliseOptionSortOrders(parameter);
  });
}

function addParameter() {
  draft.parameters.push(createParameter(draft.parameters.length + 1));
  normaliseParameterSortOrders();
}

function removeParameter(index: number) {
  draft.parameters.splice(index, 1);
  normaliseParameterSortOrders();
}

function addOption(parameter: ToolCardParameter) {
  parameter.options.push({
    value: "",
    label: "",
    sort_order: parameter.options.length + 1,
  });
  normaliseOptionSortOrders(parameter);
}

function removeOption(parameter: ToolCardParameter, optionIndex: number) {
  parameter.options.splice(optionIndex, 1);
  normaliseOptionSortOrders(parameter);
}

function onParameterDragStart(index: number) {
  draggingParameterIndex.value = index;
}

function onParameterDrop(index: number) {
  const sourceIndex = draggingParameterIndex.value;
  draggingParameterIndex.value = -1;
  if (sourceIndex < 0 || sourceIndex === index) {
    return;
  }
  const nextParameters = [...draft.parameters];
  const [movedParameter] = nextParameters.splice(sourceIndex, 1);
  if (!movedParameter) {
    return;
  }
  nextParameters.splice(index, 0, movedParameter);
  draft.parameters = nextParameters;
  normaliseParameterSortOrders();
}

function onParameterDragEnd() {
  draggingParameterIndex.value = -1;
}

function onOptionDragStart(parameterIndex: number, optionIndex: number) {
  draggingOptionState.value = { parameterIndex, optionIndex };
}

function onOptionDrop(parameterIndex: number, optionIndex: number) {
  const dragState = draggingOptionState.value;
  draggingOptionState.value = null;
  if (!dragState || dragState.parameterIndex !== parameterIndex || dragState.optionIndex === optionIndex) {
    return;
  }
  const parameter = draft.parameters[parameterIndex];
  if (!parameter) {
    return;
  }
  const nextOptions = [...parameter.options];
  const [movedOption] = nextOptions.splice(dragState.optionIndex, 1);
  if (!movedOption) {
    return;
  }
  nextOptions.splice(optionIndex, 0, movedOption);
  parameter.options = nextOptions;
  normaliseOptionSortOrders(parameter);
}

function onOptionDragEnd() {
  draggingOptionState.value = null;
}

function getAssociationValueOptions(fieldKey: string) {
  return sortOptions(draft.parameters.find((parameter) => parameter.field_key === fieldKey)?.options ?? []);
}

function handleAssociationFieldChange(parameter: ToolCardParameter) {
  const optionValues = new Set(getAssociationValueOptions(parameter.association_field).map((option) => option.value));
  parameter.association_value = parameter.association_value.filter((value) => optionValues.has(value));
}

function handleFieldTypeChange(parameter: ToolCardParameter) {
  if (parameter.field_type === "input") {
    parameter.options = [];
  }
  if (parameter.field_type === "radio" && !parameter.default_value && parameter.options[0]) {
    parameter.default_value = sortOptions(parameter.options)[0]?.value ?? "";
  }
}

function normalizeParametersForSave() {
  return draft.parameters
    .map((parameter, index) => ({
      ...cloneParameter(parameter),
      field_key: parameter.field_key.trim(),
      display_name: parameter.display_name.trim(),
      association_field: parameter.association_enabled ? parameter.association_field.trim() : "",
      association_value: parameter.association_enabled
        ? normalizeAssociationValues(parameter.association_value)
        : [],
      sort_order: index + 1,
      options: parameter.options
        .map((option, optionIndex) => ({
          ...cloneOption(option),
          value: option.value.trim(),
          label: option.label.trim(),
          sort_order: optionIndex + 1,
        }))
        .filter((option) => option.value || option.label),
    }))
    .filter((parameter) => parameter.field_key && parameter.display_name);
}

async function saveCard() {
  if (!props.folderId && !props.card?.folder_id) {
    ElMessage.error("请先选择文件夹");
    return;
  }
  if (!draft.name.trim()) {
    ElMessage.error("请输入卡片名称");
    return;
  }
  if (draft.card_type === "sql" && !draft.sql_config.query_text.trim()) {
    ElMessage.error("请输入 SQL 查询语句");
    return;
  }
  if (draft.card_type === "http" && !draft.http_config.url.trim()) {
    ElMessage.error("请输入 HTTP 请求地址");
    return;
  }

  const payload = {
    folder_id: props.card?.folder_id ?? props.folderId ?? draft.folder_id,
    name: draft.name.trim(),
    description: draft.description.trim(),
    card_type: draft.card_type,
    sort_order: draft.sort_order,
    enabled: draft.enabled,
    sql_config: draft.sql_config,
    http_config: draft.http_config,
    python_config: draft.python_config,
    parameters: normalizeParametersForSave(),
  };

  saving.value = true;
  try {
    const card = props.card
      ? await updateToolCard(props.card.id, payload)
      : await createToolCard(payload);
    ElMessage.success(props.card ? "卡片已更新" : "卡片已添加");
    emit("saved", card);
    closeDialog();
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="dialogTitle"
    width="1120px"
    top="5vh"
    class="tool-card-config-dialog"
    destroy-on-close
  >
    <div class="tool-card-config-dialog__body">
      <section class="tool-card-config-dialog__section tool-card-config-dialog__section--basic">
        <div class="tool-card-config-dialog__grid tool-card-config-dialog__grid--basic">
          <label class="tool-card-config-dialog__field">
            <span>类型</span>
            <el-select v-model="draft.card_type" size="small" :disabled="Boolean(card)">
              <el-option label="SQL工具" value="sql" />
              <el-option label="HTTP接口" value="http" />
              <el-option label="Python类" value="python" />
            </el-select>
          </label>

          <label class="tool-card-config-dialog__field">
            <span>名称</span>
            <el-input v-model="draft.name" size="small" />
          </label>

          <label class="tool-card-config-dialog__field tool-card-config-dialog__field--full">
            <span>描述</span>
            <el-input v-model="draft.description" type="textarea" :rows="2" />
          </label>
        </div>
      </section>

      <section v-if="draft.card_type === 'sql'" class="tool-card-config-dialog__section">
        <h4 class="tool-card-config-dialog__section-title">SQL 配置</h4>
        <div class="tool-card-config-dialog__grid tool-card-config-dialog__grid--sql">
          <label class="tool-card-config-dialog__field">
            <span>主机</span>
            <el-input v-model="draft.sql_config.host" size="small" />
          </label>
          <label class="tool-card-config-dialog__field">
            <span>端口</span>
            <el-input-number v-model="draft.sql_config.port" :min="1" :max="65535" size="small" />
          </label>
          <label class="tool-card-config-dialog__field">
            <span>库名</span>
            <el-input v-model="draft.sql_config.database_name" size="small" />
          </label>
          <label class="tool-card-config-dialog__field">
            <span>用户</span>
            <el-input v-model="draft.sql_config.username" size="small" />
          </label>
          <label class="tool-card-config-dialog__field">
            <span>密码</span>
            <el-input v-model="draft.sql_config.password" type="password" show-password size="small" />
          </label>
          <label class="tool-card-config-dialog__field tool-card-config-dialog__field--full">
            <span>SQL</span>
            <el-input v-model="draft.sql_config.query_text" type="textarea" :rows="5" />
          </label>
        </div>
      </section>

      <section v-else-if="draft.card_type === 'http'" class="tool-card-config-dialog__section">
        <h4 class="tool-card-config-dialog__section-title">HTTP 配置</h4>
        <div class="tool-card-config-dialog__grid tool-card-config-dialog__grid--http">
          <label class="tool-card-config-dialog__field tool-card-config-dialog__field--wide">
            <span>URL</span>
            <el-input v-model="draft.http_config.url" size="small" />
          </label>
          <label class="tool-card-config-dialog__field">
            <span>方法</span>
            <el-select v-model="draft.http_config.method" size="small">
              <el-option label="GET" value="GET" />
              <el-option label="POST" value="POST" />
              <el-option label="PUT" value="PUT" />
              <el-option label="PATCH" value="PATCH" />
              <el-option label="DELETE" value="DELETE" />
            </el-select>
          </label>
          <label class="tool-card-config-dialog__field tool-card-config-dialog__field--full">
            <span>Headers</span>
            <el-input v-model="draft.http_config.headers_text" type="textarea" :rows="4" />
          </label>
          <label class="tool-card-config-dialog__field tool-card-config-dialog__field--full">
            <span>Body</span>
            <el-input v-model="draft.http_config.body_text" type="textarea" :rows="5" />
          </label>
        </div>
      </section>

      <section v-else class="tool-card-config-dialog__section">
        <h4 class="tool-card-config-dialog__section-title">Python 配置</h4>
        <div class="tool-card-config-dialog__grid tool-card-config-dialog__grid--python">
          <label class="tool-card-config-dialog__field">
            <span>模块</span>
            <el-input v-model="draft.python_config.module_name" size="small" />
          </label>
          <label class="tool-card-config-dialog__field">
            <span>类名</span>
            <el-input v-model="draft.python_config.class_name" size="small" />
          </label>
          <label class="tool-card-config-dialog__field">
            <span>方法</span>
            <el-input v-model="draft.python_config.method_name" size="small" />
          </label>
          <label class="tool-card-config-dialog__field tool-card-config-dialog__field--full">
            <span>参数</span>
            <el-input v-model="draft.python_config.args_text" type="textarea" :rows="5" />
          </label>
        </div>
      </section>

      <section class="tool-card-config-dialog__section">
        <div class="tool-card-config-dialog__section-toolbar">
          <h4 class="tool-card-config-dialog__section-title">参数配置</h4>
          <el-button size="small" @click="addParameter">新增参数</el-button>
        </div>

        <div class="tool-card-config-dialog__param-header">
          <span>字段 key</span>
          <span>显示名称</span>
          <span>默认值</span>
          <span>类型</span>
          <span>关联</span>
          <span>关联字段</span>
          <span>关联值</span>
          <span>必填</span>
          <span>枚举</span>
          <span>操作</span>
        </div>

        <div v-if="draft.parameters.length === 0" class="tool-card-config-dialog__param-empty">
          暂无参数配置
        </div>

        <div
          v-for="(parameter, index) in draft.parameters"
          :key="parameter.id ?? `parameter-${index}`"
          class="tool-card-config-dialog__param-row"
          :class="{ 'is-dragging': draggingParameterIndex === index }"
          draggable="true"
          @dragstart="onParameterDragStart(index)"
          @dragover.prevent
          @drop="onParameterDrop(index)"
          @dragend="onParameterDragEnd"
        >
          <el-input v-model="parameter.field_key" size="small" />
          <el-input v-model="parameter.display_name" size="small" />
          <el-input v-model="parameter.default_value" size="small" />
          <el-select v-model="parameter.field_type" size="small" @change="handleFieldTypeChange(parameter)">
            <el-option label="输入框" value="input" />
            <el-option label="下拉框-单选" value="select" />
            <el-option label="下拉框-多选" value="multi_select" />
            <el-option label="单选框" value="radio" />
          </el-select>
          <el-checkbox v-model="parameter.association_enabled" />
          <el-select
            v-model="parameter.association_field"
            size="small"
            clearable
            :disabled="!parameter.association_enabled"
            @change="handleAssociationFieldChange(parameter)"
          >
            <el-option
              v-for="field in associationFieldCandidates"
              :key="field.field_key"
              :label="`${field.display_name} (${field.field_key})`"
              :value="field.field_key"
            />
          </el-select>
          <el-select
            v-model="parameter.association_value"
            size="small"
            multiple
            collapse-tags
            collapse-tags-tooltip
            :disabled="!parameter.association_enabled || !parameter.association_field"
          >
            <el-option
              v-for="option in getAssociationValueOptions(parameter.association_field)"
              :key="`${parameter.field_key}-${option.value}`"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
          <el-checkbox v-model="parameter.required" />

          <div class="tool-card-config-dialog__enum-actions">
            <el-button
              v-if="parameter.field_type !== 'input'"
              size="small"
              @click="addOption(parameter)"
            >
              +枚举
            </el-button>
          </div>

          <div class="tool-card-config-dialog__row-actions">
            <el-button size="small" type="danger" text @click="removeParameter(index)">删除</el-button>
          </div>

          <div
            v-if="parameter.field_type !== 'input' && parameter.options.length > 0"
            class="tool-card-config-dialog__enum-list"
          >
            <div
              v-for="(option, optionIndex) in parameter.options"
              :key="option.id ?? `option-${parameter.field_key}-${optionIndex}`"
              class="tool-card-config-dialog__enum-row"
              :class="{ 'is-dragging': draggingOptionState?.parameterIndex === index && draggingOptionState?.optionIndex === optionIndex }"
              draggable="true"
              @dragstart.stop="onOptionDragStart(index, optionIndex)"
              @dragover.prevent.stop
              @drop.stop="onOptionDrop(index, optionIndex)"
              @dragend.stop="onOptionDragEnd"
            >
              <el-input v-model="option.value" size="small" placeholder="值" />
              <el-input v-model="option.label" size="small" placeholder="显示名称" />
              <el-button size="small" type="danger" text @click="removeOption(parameter, optionIndex)">
                删除
              </el-button>
            </div>
          </div>
        </div>
      </section>
    </div>

    <template #footer>
      <div class="tool-card-config-dialog__footer">
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveCard">保存</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.tool-card-config-dialog :deep(.el-dialog) {
  border-radius: 8px;
}

.tool-card-config-dialog :deep(.el-dialog__header) {
  padding: 12px 16px 8px;
}

.tool-card-config-dialog :deep(.el-dialog__body) {
  padding: 0 16px 10px;
}

.tool-card-config-dialog :deep(.el-dialog__footer) {
  padding: 8px 16px 14px;
}

.tool-card-config-dialog__body {
  max-height: 72vh;
  overflow-y: auto;
  padding-right: 2px;
}

.tool-card-config-dialog__section {
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: #f8fafc;
}

.tool-card-config-dialog__section--basic {
  padding-bottom: 8px;
}

.tool-card-config-dialog__section-title {
  margin: 0;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

.tool-card-config-dialog__section-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.tool-card-config-dialog__section-toolbar :deep(.el-button) {
  border-color: #2563eb;
  color: #ffffff;
  background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.16);
}

.tool-card-config-dialog__section-toolbar :deep(.el-button:hover),
.tool-card-config-dialog__section-toolbar :deep(.el-button:focus-visible) {
  border-color: #1d4ed8;
  background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
}

.tool-card-config-dialog__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.tool-card-config-dialog__grid--basic {
  grid-template-columns: minmax(0, 1fr);
}

.tool-card-config-dialog__grid--sql {
  grid-template-columns: 1.1fr 0.7fr 1fr 1fr 1fr;
}

.tool-card-config-dialog__field {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr);
  align-items: center;
  gap: 6px;
}

.tool-card-config-dialog__field > span {
  color: #475569;
  font-size: 12px;
  text-align: right;
  white-space: nowrap;
}

.tool-card-config-dialog__grid--basic > :nth-child(1) {
  order: 1;
  justify-self: start;
  grid-template-columns: 46px auto;
}

.tool-card-config-dialog__grid--basic > :nth-child(1) :deep(.el-select) {
  width: fit-content;
  min-width: 108px;
}

.tool-card-config-dialog__grid--basic > :nth-child(1) :deep(.el-select__wrapper) {
  min-width: 108px;
}

.tool-card-config-dialog__grid--basic > :nth-child(2) {
  order: 2;
  justify-self: start;
  grid-template-columns: 46px minmax(0, 320px);
}

.tool-card-config-dialog__grid--basic > :nth-child(3) {
  order: 3;
  justify-self: start;
  grid-template-columns: 46px minmax(0, 420px);
}

.tool-card-config-dialog__grid--basic > :nth-child(3),
.tool-card-config-dialog__grid--sql > :last-child,
.tool-card-config-dialog__grid--http > :nth-child(3),
.tool-card-config-dialog__grid--http > :nth-child(4),
.tool-card-config-dialog__grid--python > :last-child {
  align-items: start;
}

.tool-card-config-dialog__grid--basic > :nth-child(3) > span,
.tool-card-config-dialog__grid--sql > :last-child > span,
.tool-card-config-dialog__grid--http > :nth-child(3) > span,
.tool-card-config-dialog__grid--http > :nth-child(4) > span,
.tool-card-config-dialog__grid--python > :last-child > span {
  align-self: start;
  padding-top: 6px;
}

.tool-card-config-dialog__field--full {
  grid-column: 1 / -1;
}

.tool-card-config-dialog__field--wide {
  grid-column: span 2;
}

.tool-card-config-dialog__field :deep(.el-input__wrapper),
.tool-card-config-dialog__field :deep(.el-select__wrapper),
.tool-card-config-dialog__field :deep(.el-textarea__inner),
.tool-card-config-dialog__field :deep(.el-input-number) {
  font-size: 12px;
}

.tool-card-config-dialog__field :deep(.el-input__wrapper),
.tool-card-config-dialog__field :deep(.el-select__wrapper) {
  min-height: 30px;
}

.tool-card-config-dialog__field :deep(.el-input),
.tool-card-config-dialog__field :deep(.el-select),
.tool-card-config-dialog__field :deep(.el-input-number),
.tool-card-config-dialog__field :deep(.el-textarea) {
  width: 100%;
}

.tool-card-config-dialog__grid--basic > :nth-child(1) :deep(.el-select),
.tool-card-config-dialog__grid--basic > :nth-child(1) :deep(.el-select__wrapper) {
  width: auto;
}

.tool-card-config-dialog__param-header,
.tool-card-config-dialog__param-row {
  display: grid;
  grid-template-columns: 1.1fr 1.1fr 1fr 1fr 56px 1.1fr 1fr 56px 88px 62px;
  gap: 6px;
  align-items: center;
  justify-items: center;
}

.tool-card-config-dialog__param-header {
  margin-bottom: 6px;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
}

.tool-card-config-dialog__param-row {
  margin-bottom: 8px;
  padding: 8px;
  border-radius: 6px;
  background: #ffffff;
  text-align: center;
  cursor: grab;
  transition: background-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.tool-card-config-dialog__param-row.is-dragging {
  background: #eef6ff;
  box-shadow: inset 0 0 0 1px #93c5fd;
  opacity: 0.85;
}

.tool-card-config-dialog__param-row > * {
  width: auto;
  min-width: 0;
  justify-self: center;
}

.tool-card-config-dialog__param-row > :nth-child(5),
.tool-card-config-dialog__param-row > :nth-child(8) {
  width: 100%;
  display: grid;
  place-items: center;
  justify-self: stretch;
}

.tool-card-config-dialog__param-empty {
  padding: 24px 0;
  color: #94a3b8;
  font-size: 12px;
  text-align: center;
}

.tool-card-config-dialog__enum-actions,
.tool-card-config-dialog__row-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
}

.tool-card-config-dialog__enum-actions :deep(.el-button) {
  border-color: #2563eb;
  color: #ffffff;
  background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.14);
}

.tool-card-config-dialog__enum-actions :deep(.el-button:hover),
.tool-card-config-dialog__enum-actions :deep(.el-button:focus-visible) {
  border-color: #1d4ed8;
  background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
}

.tool-card-config-dialog__enum-list {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  width: 100%;
  gap: 6px;
  margin-left: 24px;
  padding-top: 4px;
  padding-left: 6px;
  border-left: 1px solid #dbe3ea;
  align-items: flex-start;
  justify-self: stretch;
}

.tool-card-config-dialog__enum-row {
  display: grid;
  grid-template-columns: 180px 250px 52px;
  gap: 6px;
  align-items: center;
  justify-content: start;
  cursor: grab;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.tool-card-config-dialog__enum-row.is-dragging {
  opacity: 0.7;
}

.tool-card-config-dialog__param-row :deep(.el-input__wrapper),
.tool-card-config-dialog__param-row :deep(.el-select__wrapper),
.tool-card-config-dialog__param-row :deep(.el-input-number) {
  min-height: 30px;
}

.tool-card-config-dialog__param-row > :deep(.el-input),
.tool-card-config-dialog__param-row > :deep(.el-select),
.tool-card-config-dialog__param-row > :deep(.el-input-number) {
  width: 100%;
  max-width: 150px;
}

.tool-card-config-dialog__param-row :deep(.el-checkbox) {
  margin: 0;
  margin-right: 0;
  justify-content: center;
}

.tool-card-config-dialog__param-row > :nth-child(5) :deep(.el-checkbox__input),
.tool-card-config-dialog__param-row > :nth-child(8) :deep(.el-checkbox__input) {
  margin: 0;
}

.tool-card-config-dialog__enum-row > :deep(.el-input) {
  width: 100%;
}

.tool-card-config-dialog__footer {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 1400px) {
  .tool-card-config-dialog__param-header,
  .tool-card-config-dialog__param-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .tool-card-config-dialog__enum-list {
    grid-column: 1 / -1;
  }
}
</style>
