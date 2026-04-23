<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import { Delete, Plus } from "@element-plus/icons-vue";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api.js";
import MonacoEditorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import "monaco-editor/esm/vs/basic-languages/python/python.contribution.js";
import "monaco-editor/min/vs/editor/editor.main.css";

type CommonToolKind = "http_request" | "sql_tool" | "python_script";
type HttpTabKey = "headers" | "body";

type ToolConfigFormModel = {
  name: string;
  method: string;
  url: string;
  timeout: number;
  enabled?: boolean;
  useGlobalEncryption?: boolean;
  useGlobalHeaders?: boolean;
  bodyText: string;
  databaseConnectionId: number | null;
  database: string;
  sqlText: string;
  outputFieldsText: string;
  pythonScriptText: string;
  pythonTimeout: number;
};

type HeaderRow = {
  rowKey: string;
  key: string;
  value: string;
};

type ToolRow = {
  rowKey: string;
  variable: string;
  path: string;
};

type DatabaseConnectionOption = {
  id: number;
  name: string;
  host?: string;
  port?: number | string;
  database_name?: string;
};

(self as unknown as { MonacoEnvironment?: monaco.Environment }).MonacoEnvironment = {
  getWorker() {
    return new MonacoEditorWorker();
  },
};

const PYTHON_EDITOR_THEME = "testtool-python-dark";

monaco.editor.defineTheme(PYTHON_EDITOR_THEME, {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "keyword", foreground: "C586C0" },
    { token: "identifier", foreground: "9CDCFE" },
    { token: "string", foreground: "CE9178" },
    { token: "number", foreground: "B5CEA8" },
    { token: "comment", foreground: "6A9955" },
  ],
  colors: {
    "editor.background": "#111827",
    "editor.foreground": "#E5E7EB",
    "editor.lineHighlightBackground": "#1F2937",
    "editorLineNumber.foreground": "#6B7280",
    "editorLineNumber.activeForeground": "#D1D5DB",
    "editorCursor.foreground": "#F9FAFB",
    "editor.selectionBackground": "#374151",
    "editor.inactiveSelectionBackground": "#253041",
  },
});

const props = withDefaults(
  defineProps<{
    active: boolean;
    kind: CommonToolKind;
    form: ToolConfigFormModel;
    headerRows: HeaderRow[];
    rows: ToolRow[];
    databaseConnections: DatabaseConnectionOption[];
    databaseSchemas: string[];
    databaseSchemasLoading?: boolean;
    httpTab: HttpTabKey;
    showName?: boolean;
    showEnabled?: boolean;
    showHttpGlobalOptions?: boolean;
  }>(),
  {
    databaseSchemasLoading: false,
    showName: true,
    showEnabled: false,
    showHttpGlobalOptions: false,
  },
);

const emit = defineEmits<{
  "update:httpTab": [value: HttpTabKey];
  "database-change": [value: number | string | null];
  "global-encryption-change": [value: string | number | boolean];
  "global-headers-change": [value: string | number | boolean];
  "insert-header-row": [index: number];
  "remove-header-row": [index: number];
  "insert-row": [index: number];
  "remove-row": [index: number];
}>();

const editorContainer = ref<HTMLElement | null>(null);
let pythonCodeEditor: monaco.editor.IStandaloneCodeEditor | null = null;
let pythonEditorChangeDisposable: monaco.IDisposable | null = null;

function getDatabaseConnectionLabel(item: DatabaseConnectionOption) {
  const host = item.host ? `${item.host}:${item.port}` : "";
  return host ? `${item.name}（${host}）` : item.name;
}

function updateHttpTab(value: string | number) {
  emit("update:httpTab", String(value) as HttpTabKey);
}

function disposePythonEditor() {
  pythonEditorChangeDisposable?.dispose();
  pythonEditorChangeDisposable = null;
  pythonCodeEditor?.dispose();
  pythonCodeEditor = null;
}

async function mountPythonEditor() {
  await nextTick();
  if (!props.active || props.kind !== "python_script" || !editorContainer.value) {
    return;
  }
  if (!pythonCodeEditor) {
    pythonCodeEditor = monaco.editor.create(editorContainer.value, {
      value: props.form.pythonScriptText,
      language: "python",
      theme: PYTHON_EDITOR_THEME,
      automaticLayout: true,
      fontSize: 13,
      lineHeight: 20,
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      tabSize: 4,
      insertSpaces: false,
      wordWrap: "on",
    });
    pythonEditorChangeDisposable = pythonCodeEditor.onDidChangeModelContent(() => {
      const value = pythonCodeEditor?.getValue() ?? "";
      if (props.form.pythonScriptText !== value) {
        props.form.pythonScriptText = value;
      }
    });
  } else if (pythonCodeEditor.getValue() !== props.form.pythonScriptText) {
    pythonCodeEditor.setValue(props.form.pythonScriptText);
  }
  pythonCodeEditor.layout();
}

function syncPythonEditorValue(value: string) {
  if (pythonCodeEditor && pythonCodeEditor.getValue() !== value) {
    pythonCodeEditor.setValue(value);
  }
}

watch(
  [() => props.active, () => props.kind],
  ([active, kind]) => {
    if (active && kind === "python_script") {
      void mountPythonEditor();
      return;
    }
    disposePythonEditor();
  },
  { immediate: true },
);

watch(
  () => props.form.pythonScriptText,
  (value) => {
    syncPythonEditorValue(value);
  },
);

onBeforeUnmount(() => {
  disposePythonEditor();
});
</script>

<template>
  <div class="common-tool-config-form">
    <div v-if="showName" class="tool-dialog-row name-row">
      <label>名称:</label>
      <input v-model="form.name" class="tool-input dialog-input" placeholder="请输入工具名称" />
    </div>

    <template v-if="kind === 'http_request'">
      <div v-if="showEnabled" class="tool-dialog-row timeout-row">
        <label>启用:</label>
        <div class="inline-option-group">
          <el-switch v-model="form.enabled" />
          <span class="inline-field-label">超时时间:</span>
          <el-input-number v-model="form.timeout" :min="1" :max="300" />
        </div>
      </div>
      <div v-else class="tool-dialog-row timeout-row">
        <label>超时时间:</label>
        <el-input-number v-model="form.timeout" :min="1" :max="300" />
      </div>

      <div class="tool-dialog-grid http-request-grid">
        <div class="tool-dialog-row compact">
          <label>请求方式:</label>
          <el-select v-model="form.method" class="tool-dialog-select">
            <el-option
              v-for="method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']"
              :key="method"
              :label="method"
              :value="method"
            />
          </el-select>
        </div>
        <div class="tool-dialog-row">
          <label>请求URL:</label>
          <input v-model="form.url" class="tool-input dialog-input" placeholder="请输入完整请求地址" />
        </div>
      </div>

      <div v-if="showHttpGlobalOptions" class="tool-dialog-row tool-dialog-switch-row global-option-row">
        <label>全局配置:</label>
        <div class="global-option-checks">
          <el-checkbox v-model="form.useGlobalEncryption" @change="emit('global-encryption-change', $event)">
            使用全局加解密
          </el-checkbox>
          <el-checkbox v-model="form.useGlobalHeaders" @change="emit('global-headers-change', $event)">
            使用全局请求头
          </el-checkbox>
        </div>
      </div>

      <el-tabs :model-value="httpTab" class="tool-inner-tabs" @update:model-value="updateHttpTab">
        <el-tab-pane label="请求头" name="headers">
          <div class="tool-dialog-section embedded flat-row-section http-config-panel">
            <div v-for="(row, index) in headerRows" :key="row.rowKey" class="tool-config-row flat-row">
              <input v-model="row.key" class="tool-input config-input" placeholder="Header名称" />
              <input v-model="row.value" class="tool-input config-input wide" placeholder="Header值" />
              <button class="row-icon add" title="新增" @click="emit('insert-header-row', index)">+</button>
              <button class="row-icon remove" title="删除" @click="emit('remove-header-row', index)">-</button>
            </div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="请求体" name="body">
          <el-input v-model="form.bodyText" class="http-body-input" type="textarea" :rows="9" resize="none" />
        </el-tab-pane>
      </el-tabs>

      <div class="tool-dialog-labeled-section">
        <div class="tool-dialog-section-title side-title">响应提取</div>
        <div class="tool-dialog-section flat-row-section">
          <div v-for="(row, index) in rows" :key="row.rowKey" class="tool-config-row flat-row">
            <input v-model="row.variable" class="tool-input config-input" placeholder="变量名称" />
            <input v-model="row.path" class="tool-input config-input wide" placeholder="JSONPath表达式" />
            <button class="row-icon add" title="新增" @click="emit('insert-row', index)">+</button>
            <button class="row-icon remove" title="删除" @click="emit('remove-row', index)">-</button>
          </div>
        </div>
      </div>
    </template>

    <template v-else-if="kind === 'sql_tool'">
      <div v-if="showEnabled" class="tool-dialog-row">
        <label>启用:</label>
        <el-switch v-model="form.enabled" />
      </div>
      <div class="tool-dialog-row">
        <label>数据库:</label>
        <el-select
          v-model="form.databaseConnectionId"
          class="tool-dialog-select"
          clearable
          filterable
          placeholder="请选择资产数据库"
          @change="emit('database-change', $event)"
        >
          <el-option
            v-for="database in databaseConnections"
            :key="database.id"
            :label="getDatabaseConnectionLabel(database)"
            :value="database.id"
          />
        </el-select>
      </div>
      <div class="tool-dialog-row">
        <label>库名:</label>
        <el-select
          v-model="form.database"
          class="tool-dialog-select"
          clearable
          filterable
          :disabled="!form.databaseConnectionId"
          :loading="databaseSchemasLoading"
          placeholder="请选择库名"
        >
          <el-option v-for="schema in databaseSchemas" :key="schema" :label="schema" :value="schema" />
        </el-select>
      </div>
      <div class="tool-dialog-row textarea">
        <label>SQL语句:</label>
        <el-input v-model="form.sqlText" type="textarea" :rows="8" resize="none" />
      </div>
      <div class="tool-dialog-row">
        <label>输出字段:</label>
        <input v-model="form.outputFieldsText" class="tool-input dialog-input" placeholder="多个字段用英文逗号分隔" />
      </div>
    </template>

    <template v-else>
      <div v-if="showEnabled" class="tool-dialog-row timeout-row">
        <label>启用:</label>
        <div class="inline-option-group">
          <el-switch v-model="form.enabled" />
          <span class="inline-field-label">超时时间:</span>
          <el-input-number v-model="form.pythonTimeout" :min="1" :max="86400" />
        </div>
      </div>
      <div v-else class="tool-dialog-row timeout-row">
        <label>超时时间:</label>
        <el-input-number v-model="form.pythonTimeout" :min="1" :max="86400" />
      </div>
      <div class="tool-dialog-row textarea">
        <label>脚本内容:</label>
        <div ref="editorContainer" class="python-code-editor" />
      </div>
      <div class="tool-dialog-row">
        <label>输出字段:</label>
        <input v-model="form.outputFieldsText" class="tool-input dialog-input" placeholder="large_name,userPhone,sex" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.common-tool-config-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.tool-dialog-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.tool-dialog-grid.http-request-grid {
  grid-template-columns: minmax(210px, 240px) minmax(0, 1fr);
}

.tool-dialog-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tool-dialog-row.textarea {
  align-items: flex-start;
}

.tool-dialog-row > label {
  width: 74px;
  flex: 0 0 74px;
  color: #334155;
  font-size: 13px;
}

.tool-dialog-switch-row :deep(.el-checkbox) {
  height: 32px;
}

.global-option-row {
  align-items: center;
}

.global-option-checks,
.inline-option-group {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 18px;
  min-height: 32px;
}

.inline-option-group {
  gap: 10px;
}

.global-option-checks :deep(.el-checkbox) {
  flex: 0 0 auto;
  height: 32px;
  margin-right: 0;
}

.global-option-checks :deep(.el-checkbox__input) {
  flex: 0 0 auto;
}

.global-option-checks :deep(.el-checkbox__label) {
  padding-left: 6px;
  white-space: nowrap;
}

.inline-field-label {
  color: #334155;
  font-size: 13px;
}

.name-row .dialog-input {
  width: 260px;
  flex: 0 0 260px;
}

.timeout-row {
  width: fit-content;
}

.timeout-row :deep(.el-input-number) {
  width: 160px;
  flex: 0 0 auto;
}

.timeout-row :deep(.el-input-number .el-input) {
  width: 160px;
}

.tool-input {
  width: 100%;
  min-width: 0;
  height: 34px;
  border: 1px solid #d7e1ec;
  border-radius: 6px;
  padding: 0 10px;
  box-sizing: border-box;
  color: #1f2937;
  font-size: 13px;
  outline: none;
}

.dialog-input {
  margin-top: 0;
  height: 34px;
}

.common-tool-config-form :deep(.el-input__wrapper),
.common-tool-config-form :deep(.el-select__wrapper),
.common-tool-config-form :deep(.el-textarea__inner),
.common-tool-config-form :deep(.el-input-number .el-input__inner) {
  font-family: var(--qm-form-font-family);
  font-size: var(--qm-form-font-size);
  line-height: var(--qm-form-line-height);
}

.tool-dialog-row :deep(.el-textarea),
.tool-dialog-row :deep(.el-select),
.tool-dialog-row :deep(.el-input-number) {
  flex: 1 1 auto;
}

.python-code-editor {
  flex: 1 1 auto;
  height: 280px;
  min-width: 0;
  overflow: hidden;
  border: 1px solid #1f2937;
  border-radius: 6px;
}

.tool-dialog-select {
  min-width: 120px;
}

.tool-dialog-section {
  border: 1px solid #dbe3ed;
  border-radius: 8px;
  padding: 12px;
  background: #fbfdff;
}

.tool-dialog-section.embedded {
  padding: 0;
  border: none;
  background: transparent;
}

.tool-dialog-section.embedded.flat-row-section {
  padding: 12px;
  border: 1px solid #dbe3ed;
  border-radius: 10px;
  background: #f7fbff;
}

.http-config-panel {
  height: 220px;
  overflow-y: auto;
  box-sizing: border-box;
}

.http-body-input :deep(.el-textarea__inner) {
  height: 220px;
  min-height: 220px;
}

.tool-inner-tabs {
  margin-top: -2px;
}

.tool-inner-tabs :deep(.el-tabs__header) {
  margin: 0 0 10px;
}

.tool-inner-tabs :deep(.el-tabs__nav-wrap::after) {
  background: #dbe3ed;
}

.tool-inner-tabs :deep(.el-tabs__item) {
  height: 34px;
  color: #64748b;
  font-size: 13px;
}

.tool-inner-tabs :deep(.el-tabs__item.is-active) {
  color: #2f7df6;
  font-weight: 600;
}

.tool-dialog-labeled-section {
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
}

.tool-dialog-section-title {
  margin-bottom: 10px;
  color: #1e293b;
  font-size: 13px;
  font-weight: 700;
}

.tool-dialog-section-title.side-title {
  display: flex;
  align-items: center;
  min-height: 34px;
  margin-bottom: 0;
}

.flat-row-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tool-config-row.flat-row {
  display: grid;
  grid-template-columns: minmax(150px, 0.45fr) minmax(220px, 1fr) 30px 30px;
  gap: 10px;
  align-items: center;
}

.config-input {
  height: 32px;
}

.row-icon {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}

.row-icon.add {
  color: #2bb673;
}

.row-icon.remove {
  color: #d93025;
}

@media (max-width: 860px) {
  .tool-dialog-grid,
  .tool-dialog-grid.http-request-grid,
  .tool-dialog-labeled-section,
  .tool-config-row.flat-row {
    grid-template-columns: 1fr;
  }

  .tool-dialog-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .tool-dialog-row > label {
    width: auto;
    flex-basis: auto;
  }

  .timeout-row {
    width: 100%;
  }
}
</style>
