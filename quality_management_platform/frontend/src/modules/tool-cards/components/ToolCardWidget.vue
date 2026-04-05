<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import { Brush, CopyDocument, Delete, Edit, Reading } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";

import type { ToolCard, ToolCardParameter } from "../types";

const props = defineProps<{
  card: ToolCard;
}>();

const emit = defineEmits<{
  execute: [payload: { card: ToolCard; variables: Record<string, unknown> }];
  edit: [card: ToolCard];
  copy: [card: ToolCard];
  delete: [card: ToolCard];
}>();

const formValues = reactive<Record<string, unknown>>({});

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

function normalizeDefaultValue(parameter: ToolCardParameter) {
  if (parameter.field_type === "multi_select") {
    if (!parameter.default_value) {
      return [];
    }
    try {
      const parsed = JSON.parse(parameter.default_value) as unknown;
      if (Array.isArray(parsed)) {
        return parsed.map((item) => String(item));
      }
    } catch {
      return parameter.default_value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
    }
  }
  if (parameter.field_type === "radio") {
    return parameter.default_value || getSortedOptions(parameter)[0]?.value || "";
  }
  return parameter.default_value ?? "";
}

function getSortedOptions(parameter: ToolCardParameter) {
  return parameter.options
    .slice()
    .sort((left, right) => left.sort_order - right.sort_order || (left.id ?? 0) - (right.id ?? 0));
}

function resetValues() {
  Object.keys(formValues).forEach((key) => {
    delete formValues[key];
  });
  props.card.parameters.forEach((parameter) => {
    formValues[parameter.field_key] = normalizeDefaultValue(parameter);
  });
}

watch(
  () => props.card,
  () => {
    resetValues();
  },
  { immediate: true, deep: true },
);

function matchesAssociation(parameter: ToolCardParameter) {
  if (!parameter.association_enabled || !parameter.association_field) {
    return true;
  }
  const targetValues = normalizeAssociationValues(parameter.association_value);
  if (targetValues.length === 0) {
    return true;
  }
  const currentValue = formValues[parameter.association_field];
  if (Array.isArray(currentValue)) {
    const currentValues = currentValue.map((item) => String(item));
    return targetValues.some((value) => currentValues.includes(value));
  }
  return targetValues.includes(String(currentValue ?? ""));
}

const visibleParameters = computed(() =>
  props.card.parameters
    .slice()
    .sort((left, right) => left.sort_order - right.sort_order)
    .filter((parameter) => matchesAssociation(parameter)),
);

function clearInputs() {
  resetValues();
}

async function parseTextFields() {
  try {
    const { value } = await ElMessageBox.prompt("每行一组字段，格式例如：name: 张三", "文本解析", {
      inputType: "textarea",
      inputValue: "",
      inputPlaceholder: "name: 张三\nidNo: 140414199612012910\nmobile: 14546580977",
      confirmButtonText: "匹配",
      cancelButtonText: "取消",
      inputValidator: (input) => (input.trim() ? true : "请输入要解析的文本"),
    });

    const parsed: Record<string, string> = {};
    value
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .forEach((line) => {
        const delimiterIndex = line.indexOf(":");
        if (delimiterIndex < 0) {
          return;
        }
        const key = line.slice(0, delimiterIndex).trim().toLowerCase();
        const content = line.slice(delimiterIndex + 1).trim();
        if (key) {
          parsed[key] = content;
        }
      });

    const matchedFields: string[] = [];
    props.card.parameters.forEach((parameter) => {
      const lookupKey = parameter.field_key.toLowerCase();
      if (parsed[lookupKey] === undefined) {
        return;
      }
      if (parameter.field_type === "multi_select") {
        formValues[parameter.field_key] = parsed[lookupKey]
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean);
      } else {
        formValues[parameter.field_key] = parsed[lookupKey];
      }
      matchedFields.push(parameter.field_key);
    });

    if (matchedFields.length > 0) {
      ElMessage.success(`已填充字段：${matchedFields.join("、")}`);
    } else {
      ElMessage.info("没有找到可匹配的输入字段");
    }
  } catch {
    // ignore cancel
  }
}

function executeCurrentCard() {
  for (const parameter of visibleParameters.value) {
    const value = formValues[parameter.field_key];
    const isEmpty =
      value === null ||
      value === undefined ||
      value === "" ||
      (Array.isArray(value) && value.length === 0);
    if (parameter.required && isEmpty) {
      ElMessage.error(`${parameter.display_name} 为必填项`);
      return;
    }
  }
  emit("execute", {
    card: props.card,
    variables: { ...formValues },
  });
}

function setMultiSelectValue(fieldKey: string, value: string[]) {
  formValues[fieldKey] = value;
}
</script>

<template>
  <article class="tool-card-widget">
    <header class="tool-card-widget__header">
      <h3 class="tool-card-widget__title">{{ card.name }}</h3>

      <div class="tool-card-widget__actions">
        <el-tooltip content="清空输入" placement="top">
          <el-button text circle size="small" @click="clearInputs">
            <el-icon><Brush /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="文本解析" placement="top">
          <el-button text circle size="small" @click="parseTextFields">
            <el-icon><Reading /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="编辑卡片" placement="top">
          <el-button text circle size="small" @click="emit('edit', card)">
            <el-icon><Edit /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="复制卡片" placement="top">
          <el-button text circle size="small" @click="emit('copy', card)">
            <el-icon><CopyDocument /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="删除卡片" placement="top">
          <el-button text circle size="small" @click="emit('delete', card)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </header>

    <div class="tool-card-widget__body">
      <div v-if="visibleParameters.length === 0" class="tool-card-widget__empty">暂无输入字段配置</div>

      <div
        v-for="parameter in visibleParameters"
        :key="parameter.field_key"
        class="tool-card-widget__field"
      >
        <label class="tool-card-widget__label">
          {{ parameter.display_name }}
          <span v-if="parameter.required" class="tool-card-widget__required">*</span>
        </label>

        <el-input
          v-if="parameter.field_type === 'input'"
          v-model="formValues[parameter.field_key]"
          size="small"
          class="tool-card-widget__control"
          clearable
        />

        <el-select
          v-else-if="parameter.field_type === 'select'"
          v-model="formValues[parameter.field_key]"
          size="small"
          class="tool-card-widget__control"
          clearable
        >
          <el-option
            v-for="option in getSortedOptions(parameter)"
            :key="`${parameter.field_key}-${option.value}`"
            :label="option.label"
            :value="option.value"
          />
        </el-select>

        <el-select
          v-else-if="parameter.field_type === 'multi_select'"
          :model-value="Array.isArray(formValues[parameter.field_key]) ? (formValues[parameter.field_key] as string[]) : []"
          size="small"
          multiple
          collapse-tags
          collapse-tags-tooltip
          class="tool-card-widget__control"
          @update:model-value="setMultiSelectValue(parameter.field_key, $event)"
        >
          <el-option
            v-for="option in getSortedOptions(parameter)"
            :key="`${parameter.field_key}-${option.value}`"
            :label="option.label"
            :value="option.value"
          />
        </el-select>

        <el-radio-group
          v-else
          v-model="formValues[parameter.field_key]"
          class="tool-card-widget__radio-group"
        >
          <el-radio
            v-for="option in getSortedOptions(parameter)"
            :key="`${parameter.field_key}-${option.value}`"
            :value="option.value"
          >
            {{ option.label }}
          </el-radio>
        </el-radio-group>
      </div>
    </div>

    <footer class="tool-card-widget__footer">
      <el-button type="success" size="small" @click="executeCurrentCard">执行</el-button>
    </footer>
  </article>
</template>

<style scoped>
.tool-card-widget {
  display: flex;
  flex-direction: column;
  width: 360px;
  height: 284px;
  overflow: hidden;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}

.tool-card-widget:hover {
  background: #f8fafc;
}

.tool-card-widget__header {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 6px 8px;
  border-bottom: 1px solid #bfdbfe;
  background: linear-gradient(180deg, #dbeafe 0%, #cfe3ff 100%);
}

.tool-card-widget__title {
  margin: 0;
  overflow: hidden;
  color: #0f172a;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.tool-card-widget__actions {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.tool-card-widget__actions :deep(.el-button) {
  width: 22px;
  height: 22px;
  min-height: 22px;
  margin: 0;
  color: #1d4ed8;
}

.tool-card-widget__actions :deep(.el-button:hover) {
  background: rgba(37, 99, 235, 0.14);
}

.tool-card-widget__body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 10px;
  background: #fafbfc;
}

.tool-card-widget__body::-webkit-scrollbar {
  width: 6px;
}

.tool-card-widget__body::-webkit-scrollbar-thumb {
  border-radius: 3px;
  background: #cbd5e1;
}

.tool-card-widget__empty {
  padding-top: 32px;
  color: #94a3b8;
  font-size: 12px;
  text-align: center;
}

.tool-card-widget__field {
  display: grid;
  grid-template-columns: 78px minmax(0, 1fr);
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.tool-card-widget__label {
  overflow: hidden;
  color: #334155;
  font-size: 12px;
  line-height: 1.2;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.tool-card-widget__required {
  color: #dc2626;
}

.tool-card-widget__control {
  width: 100%;
  min-width: 0;
}

.tool-card-widget__control :deep(.el-input__wrapper),
.tool-card-widget__control :deep(.el-select__wrapper) {
  min-height: 28px;
  font-size: 12px;
}

.tool-card-widget__radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  min-width: 0;
}

.tool-card-widget__radio-group :deep(.el-radio) {
  margin-right: 0;
  font-size: 12px;
}

.tool-card-widget__footer {
  display: flex;
  justify-content: flex-end;
  padding: 6px 12px 10px;
  background: #fafbfc;
}

.tool-card-widget__footer :deep(.el-button--success) {
  min-width: 74px;
  border-color: #2563eb;
  background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.18);
}

.tool-card-widget__footer :deep(.el-button--success:hover),
.tool-card-widget__footer :deep(.el-button--success:focus-visible) {
  border-color: #1d4ed8;
  background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
}
</style>
