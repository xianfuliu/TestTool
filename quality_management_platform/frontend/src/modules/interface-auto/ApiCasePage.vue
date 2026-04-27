<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useRoute, useRouter } from "vue-router";
import {
  ArrowRight,
  CopyDocument,
  Delete,
  Edit,
  Folder,
  FolderAdd,
  Plus,
  RefreshRight,
  Search,
} from "@element-plus/icons-vue";

import { del, get, post, put } from "@/shared/api/client";
import { fetchEnvironments } from "@/modules/common/environmentApi";
import type { EnvironmentRecord } from "@/modules/common/environmentTypes";
import ExecutionLogViewer from "@/shared/components/ExecutionLogViewer.vue";
import { useBusinessProjectContext } from "@/shared/composables/useBusinessProjectContext";
import {
  fetchDatabaseConnections,
  fetchDatabaseSchemas,
  type DatabaseConnectionRecord,
} from "@/modules/data-assets/api";
import CommonToolConfigForm from "./CommonToolConfigForm.vue";
import { fetchGlobalTools } from "./globalToolApi";
import { fetchGlobalVariables } from "./variableApi";
import apiToolIcon from "@/assets/interface-auto/tool-icons/api.png";
import assertionToolIcon from "@/assets/interface-auto/tool-icons/assrt.png";
import extractionToolIcon from "@/assets/interface-auto/tool-icons/extraction.png";
import headersToolIcon from "@/assets/interface-auto/tool-icons/headers.png";
import httpToolIcon from "@/assets/interface-auto/tool-icons/http.png";
import lockToolIcon from "@/assets/interface-auto/tool-icons/lock.png";
import logToolIcon from "@/assets/interface-auto/tool-icons/log.png";
import runningToolIcon from "@/assets/interface-auto/tool-icons/running.png";
import sqlToolIcon from "@/assets/interface-auto/tool-icons/sql.png";
import pythonToolIcon from "@/assets/interface-auto/tool-icons/python.png";
import startToolIcon from "@/assets/interface-auto/tool-icons/start.png";
import stopingToolIcon from "@/assets/interface-auto/tool-icons/stoping.png";
import stopToolIcon from "@/assets/interface-auto/tool-icons/stop.png";
import type {
  ApiFolder,
  ApiTemplate,
  CaseGlobalRequestConfig,
  CaseOutputVariable,
  CaseFolder,
  CaseStep,
  CaseToolMap,
  CaseToolRecord,
  CascaderOption,
  GlobalToolRecord,
  GlobalVariableRecord,
  JsonMap,
  TestCaseRecord,
  TreeNode,
} from "./types";

type ToolTabKey = "pre_processing" | "assertions" | "post_processing";
type ToolDialogKind = "http_request" | "sql_tool" | "python_script" | "parameter_extraction" | "assertion" | "generic";
type CommonToolDialogKind = "http_request" | "sql_tool" | "python_script";

type ToolDraftRow = {
  rowKey: string;
  field: string;
  operator: string;
  expected: string;
  fieldPrefix: string;
  fieldPath: string;
  variable: string;
  path: string;
  extractorType: string;
  source: string;
};

type ToolHeaderRow = {
  rowKey: string;
  key: string;
  value: string;
};

type CaseNavNode = {
  id: string;
  rawId: number | null;
  label: string;
  type: "folder" | "case";
  folderId: number | null;
  parentFolderId: number | null;
  caseItem?: TestCaseRecord;
  children?: CaseNavNode[];
};

type CaseTreeNodeInstance = {
  data: CaseNavNode;
  parent?: CaseTreeNodeInstance | null;
  childNodes?: CaseTreeNodeInstance[];
};

type CaseDropType = "before" | "after" | "inner";

type TemplateWorkspacePayload = {
  folders: ApiFolder[];
  templates: ApiTemplate[];
};

type VariableRow = {
  rowKey: string;
  name: string;
  value: string;
  id?: number;
  project_id?: number;
  variable_type?: string;
  description?: string;
};

type GlobalConfigTab = "encryption" | "variables" | "login_headers" | "parameterize" | "outputs";

type ParameterizeConfig = {
  enabled: boolean;
  source_type: "inline_json" | "csv_text";
  rows?: Array<Record<string, unknown>>;
  csv_text?: string;
};

const TOOL_TAB_LABELS: Record<ToolTabKey, string> = {
  pre_processing: "前置",
  assertions: "断言",
  post_processing: "后置",
};

const TOOL_TABS: ToolTabKey[] = ["pre_processing", "assertions", "post_processing"];

const TOOL_OPTIONS: Record<ToolTabKey, Array<{ type: string; label: string }>> = {
  pre_processing: [
    { type: "http_request", label: "HTTP请求" },
    { type: "sql_tool", label: "SQL工具" },
    { type: "python_script", label: "Python脚本" },
    { type: "global_tool", label: "全局工具" },
  ],
  assertions: [
    { type: "assertion", label: "断言" },
  ],
  post_processing: [
    { type: "parameter_extraction", label: "参数提取" },
    { type: "http_request", label: "HTTP请求" },
    { type: "sql_tool", label: "SQL工具" },
    { type: "python_script", label: "Python脚本" },
    { type: "global_tool", label: "全局工具" },
  ],
};

const ASSERTION_OPERATOR_OPTIONS = [
  { value: "equal", label: "=" },
  { value: "not_equal", label: "!=" },
  { value: "contains", label: "~" },
  { value: "not_contains", label: "!~" },
  { value: "greater", label: ">" },
  { value: "less", label: "<" },
  { value: "greater_equal", label: ">=" },
  { value: "less_equal", label: "<=" },
  { value: "exists", label: "exists" },
  { value: "not_exists", label: "not exists" },
  { value: "regex_match", label: "regex" },
];

type AssertionFieldMode = "variable" | "jsonpath" | "path" | "header" | "scalar";

type AssertionFieldSourceOption = {
  value: string;
  label: string;
  mode: AssertionFieldMode;
  placeholder: string;
};

const ASSERTION_FIELD_SOURCE_OPTIONS: AssertionFieldSourceOption[] = [
  { value: "", label: "变量", mode: "variable", placeholder: "变量名，例如 token" },
  { value: "$", label: "$", mode: "jsonpath", placeholder: "$.data.allow 或 data.allow" },
  { value: "headers.", label: "headers.", mode: "header", placeholder: "Header 名，例如 Authorization" },
  {
    value: "response_headers.",
    label: "response_headers.",
    mode: "header",
    placeholder: "Header 名，例如 X-Trace-Id",
  },
  { value: "body.", label: "body.", mode: "path", placeholder: "响应体路径，例如 data.allow" },
  {
    value: "response_body.",
    label: "response_body.",
    mode: "path",
    placeholder: "响应体路径，例如 data.id",
  },
  {
    value: "decrypted_body.",
    label: "decrypted_body.",
    mode: "path",
    placeholder: "解密响应路径，例如 allow",
  },
  {
    value: "response_decrypted_body.",
    label: "response_decrypted_body.",
    mode: "path",
    placeholder: "解密响应路径，例如 data.allow",
  },
  { value: "raw_body", label: "raw_body", mode: "scalar", placeholder: "该来源无需填写路径" },
  { value: "status_code", label: "status_code", mode: "scalar", placeholder: "该来源无需填写路径" },
];

const ASSERTION_FIELD_PREFIX_OPTIONS = ASSERTION_FIELD_SOURCE_OPTIONS;

const SCALAR_ASSERTION_FIELD_PREFIXES = new Set(
  ASSERTION_FIELD_SOURCE_OPTIONS.filter((option) => option.mode === "scalar").map((option) => option.value),
);

const EXTRACTOR_TYPE_OPTIONS = [
  { value: "jsonpath", label: "JSONPath" },
  { value: "regex", label: "Regex" },
  { value: "header", label: "Header" },
  { value: "cookie", label: "Cookie" },
  { value: "status_code", label: "Status" },
];

const EXTRACTOR_SOURCE_OPTIONS = [
  { value: "body", label: "Body" },
  { value: "response_headers", label: "Header" },
  { value: "cookie", label: "Cookie" },
  { value: "status_code", label: "Status" },
];

const COMMON_TOOL_DIALOG_KINDS = new Set<string>(["http_request", "sql_tool", "python_script"]);

const context = useBusinessProjectContext();
const route = useRoute();
const router = useRouter();

const loading = ref(false);
const saving = ref(false);
const running = ref(false);
const caseKeyword = ref("");
const templateKeyword = ref("");
const projectPath = ref<number[]>([]);
const folders = ref<CaseFolder[]>([]);
const cases = ref<TestCaseRecord[]>([]);
const apiFolders = ref<ApiFolder[]>([]);
const templates = ref<ApiTemplate[]>([]);
const environments = ref<EnvironmentRecord[]>([]);
const globalVariables = ref<GlobalVariableRecord[]>([]);
const globalTools = ref<GlobalToolRecord[]>([]);
const databaseConnections = ref<DatabaseConnectionRecord[]>([]);
const sqlDatabaseSchemas = ref<string[]>([]);
const sqlDatabaseSchemasLoading = ref(false);
const variableRows = ref<VariableRow[]>([]);
const globalConfigExpandedMap = reactive<Record<string, boolean>>({});
const activeGlobalConfigTab = ref<GlobalConfigTab>("encryption");
const openedTabs = ref<TestCaseRecord[]>([]);
const modifiedTabs = reactive<Record<string, boolean>>({});
const stepTabMap = reactive<Record<string, ToolTabKey>>({});
const caseContextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  node: null as CaseNavNode | null,
  blank: false,
});
const tabContextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  tabKey: "",
});

const activeTabKey = ref("");
const activeStepKey = ref("");
const selectedCaseNodeId = ref("");
const selectedTemplateNodeId = ref("");
const logDialogVisible = ref(false);
const logLines = ref<string[]>([]);
const executionLog = ref<Record<string, unknown> | null>(null);
const toolDialogVisible = ref(false);
const toolDialogSaving = ref(false);
const toolDialogKind = ref<ToolDialogKind>("generic");
const toolDialogTab = ref<ToolTabKey>("pre_processing");
const toolDialogStepKey = ref("");
const toolDialogToolId = ref("");
const toolDialogNewType = ref("");
const toolDialogTitle = ref("");
const httpToolTab = ref<"headers" | "body">("body");
const toolDialogIsNew = ref(false);
const toolDialogCommitted = ref(false);
const toolHeaderRows = ref<ToolHeaderRow[]>([]);
const toolRows = ref<ToolDraftRow[]>([]);
const toolForm = reactive({
  name: "",
  summary: "",
  method: "GET",
  url: "",
  timeout: 30,
  useGlobalEncryption: false,
  useGlobalHeaders: false,
  headersText: "{\n  \n}",
  bodyText: "{\n  \n}",
  databaseConnectionId: null as number | null,
  database: "",
  sqlText: "",
  outputFieldsText: "",
  pythonScriptPath: "",
  pythonWorkingDir: "",
  pythonScriptText: "",
  pythonTimeout: 60,
});
const caseTreeRef = ref<any>(null);
const templateTreeRef = ref<any>(null);
const draggedTemplateId = ref<number | null>(null);
const draggedStepKey = ref("");
const dragOverStepKey = ref("");
const draggedToolStepKey = ref("");
const draggedToolTabKey = ref<ToolTabKey | "">("");
const draggedToolId = ref("");
const dragOverToolId = ref("");

const form = reactive<TestCaseRecord>(createDraftCase(0, null));
let resetting = false;
let sqlDatabaseSchemasRequestToken = 0;

const parameterizeConfig = computed<ParameterizeConfig>({
  get: () => normalizeParameterizeConfig(form.parameterize_config),
  set: (value) => {
    form.parameterize_config = value;
  },
});

const cascaderProps = {
  expandTrigger: "hover" as const,
  emitPath: true,
  checkStrictly: false,
};

const currentProjectId = computed(() => context.selectedProject.value?.id ?? null);
const currentProjectName = computed(() => context.selectedProject.value?.name ?? "");
const currentEnvironmentName = computed(() =>
  environments.value.find((item) => item.id === form.environment_id)?.name ?? "",
);
const visibleGlobalVariables = computed(() => {
  if (!Array.isArray(globalVariables.value) || !form.environment_id) {
    return [];
  }
  return globalVariables.value.filter((item) =>
    Array.isArray(item.environment_ids) ? item.environment_ids.includes(form.environment_id as number) : false,
  );
});
const enabledDatabaseConnections = computed(() =>
  databaseConnections.value.filter((item) => item.enabled !== false),
);
const enabledGlobalTools = computed(() => {
  return globalTools.value
    .filter((item) => item.enabled !== false)
    .filter((item) => ["http_request", "sql_tool", "python_script"].includes(String(item.tool_type)));
});
const isCommonToolDialog = computed(() => COMMON_TOOL_DIALOG_KINDS.has(toolDialogKind.value));
const commonToolDialogKind = computed<CommonToolDialogKind>(() =>
  isCommonToolDialog.value ? (toolDialogKind.value as CommonToolDialogKind) : "http_request",
);
const outputVariableText = ref("");
const parameterizeText = ref("");
const parameterizeValidationMessage = ref("");
const globalConfigExpanded = computed({
  get: () => (activeTabKey.value ? Boolean(globalConfigExpandedMap[activeTabKey.value]) : false),
  set: (value: boolean) => {
    if (!activeTabKey.value) {
      return;
    }
    globalConfigExpandedMap[activeTabKey.value] = value;
  },
});

const projectOptions = computed<CascaderOption[]>(() =>
  context.groups.value.map((group) => ({
    value: group.id,
    label: group.name,
    disabled: !context.projects.value.some((item) => item.business_group_id === group.id),
    children: context.projects.value
      .filter((item) => item.business_group_id === group.id)
      .map((item) => ({ value: item.id, label: item.name })),
  })),
);

const currentFolder = computed(() => {
  const selected = findCaseNodeById(caseTreeData.value, selectedCaseNodeId.value);
  if (!selected || selected.type !== "folder" || selected.folderId === null) {
    return null;
  }
  return folders.value.find((item) => item.id === selected.folderId) ?? null;
});

const caseTreeData = computed<CaseNavNode[]>(() => {
  const keyword = caseKeyword.value.trim().toLowerCase();
  const visibleCases = keyword
    ? cases.value.filter((item) => {
        const content = `${item.name} ${item.description ?? ""}`.toLowerCase();
        return content.includes(keyword);
      })
    : cases.value;
  const childrenMap = new Map<number | null, CaseFolder[]>();
  folders.value.forEach((folder) => {
    const children = childrenMap.get(folder.parent_id ?? null) ?? [];
    children.push(folder);
    childrenMap.set(folder.parent_id ?? null, children);
  });
  const buildFolder = (folder: CaseFolder): CaseNavNode => ({
    id: `folder-${folder.id}`,
    rawId: folder.id,
    label: folder.name,
    type: "folder",
    folderId: folder.id,
    parentFolderId: folder.parent_id ?? null,
    children: [
      ...(childrenMap.get(folder.id) ?? []).map(buildFolder),
      ...visibleCases
        .filter((item) => item.folder_id === folder.id)
        .map((item) => ({
          id: `case-${item.id}`,
          rawId: item.id ?? null,
          label: item.name,
          type: "case" as const,
          folderId: item.folder_id ?? null,
          parentFolderId: item.folder_id ?? null,
          caseItem: item,
        })),
    ],
  });
  return [
    ...(childrenMap.get(null) ?? []).map(buildFolder),
    ...visibleCases
      .filter((item) => item.folder_id === null)
      .map((item) => ({
        id: `case-${item.id}`,
        rawId: item.id ?? null,
        label: item.name,
        type: "case" as const,
        folderId: null,
        parentFolderId: null,
        caseItem: item,
      })),
  ];
});

const templateTreeData = computed<TreeNode[]>(() => {
  const keyword = templateKeyword.value.trim().toLowerCase();
  const visibleTemplates = keyword
    ? templates.value.filter((item) => {
        const content = `${item.name} ${item.url_path} ${item.description ?? ""}`.toLowerCase();
        return content.includes(keyword);
      })
    : templates.value;
  const childrenMap = new Map<number | null, ApiFolder[]>();
  apiFolders.value.forEach((folder) => {
    const children = childrenMap.get(folder.parent_id ?? null) ?? [];
    children.push(folder);
    childrenMap.set(folder.parent_id ?? null, children);
  });
  const buildFolder = (folder: ApiFolder): TreeNode => ({
    id: `template-folder-${folder.id}`,
    rawId: folder.id,
    label: folder.name,
    type: "folder",
    folderId: folder.id,
    parentFolderId: folder.parent_id ?? null,
    children: [
      ...(childrenMap.get(folder.id) ?? []).map(buildFolder),
      ...visibleTemplates
        .filter((item) => item.folder_id === folder.id)
        .map((item) => ({
          id: `template-${item.id}`,
          rawId: item.id ?? null,
          label: item.name,
          type: "template" as const,
          folderId: item.folder_id ?? null,
          parentFolderId: item.folder_id ?? null,
          template: item,
          method: item.method,
        })),
    ],
  });
  return [
    ...(childrenMap.get(null) ?? []).map(buildFolder),
    ...visibleTemplates
      .filter((item) => item.folder_id === null)
      .map((item) => ({
        id: `template-${item.id}`,
        rawId: item.id ?? null,
        label: item.name,
        type: "template" as const,
        folderId: null,
        parentFolderId: null,
        template: item,
        method: item.method,
      })),
  ];
});

function createKey(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

function createHeaderRow(key = "", value = "") {
  return {
    rowKey: createKey("header"),
    key,
    value,
  };
}

function createExtractionRow(variable = "", path = "") {
  return {
    rowKey: createKey("extract"),
    variable,
    path,
  };
}

function createOutputVariableRow(name = "", source = ""): CaseOutputVariable {
  return {
    rowKey: createKey("output"),
    name,
    source,
  };
}

function createDefaultGlobalRequestConfig(): CaseGlobalRequestConfig {
  return {
    login_request: {
      enabled: false,
      protocol: "http",
      method: "POST",
      url: "",
      use_global_encryption: false,
      headers_rows: [createHeaderRow("Content-Type", "application/json")],
      body_text: "{\n  \n}",
      extractions: [createExtractionRow()],
    },
    header_config: {
      enabled: false,
      headers_rows: [createHeaderRow()],
    },
  };
}

function createDefaultParameterizeConfig(): ParameterizeConfig {
  return {
    enabled: false,
    source_type: "inline_json",
    rows: [],
    csv_text: "",
  };
}

function createDraftCase(projectId: number, folderId: number | null): TestCaseRecord {
  return {
    id: undefined,
    tabKey: createKey("draft"),
    project_id: projectId,
    folder_id: folderId,
    name: "",
    description: "",
    environment_id: null,
    schema_version: 1,
    parameterize_config: createDefaultParameterizeConfig(),
    global_vars: {},
    global_request_config: createDefaultGlobalRequestConfig(),
    output_variables: [],
    enable_encryption: false,
    encrypt_url: "",
    decrypt_url: "",
    sort_order: getNextCaseSortOrder(folderId),
    steps: [],
  };
}

function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function parseMap(value: unknown): JsonMap {
  if (!value) {
    return {};
  }
  if (typeof value === "string") {
    try {
      return JSON.parse(value) as JsonMap;
    } catch {
      return {};
    }
  }
  if (typeof value === "object") {
    return value as JsonMap;
  }
  return {};
}

function parseJsonRecord(value: unknown): Record<string, unknown> {
  if (!value) {
    return {};
  }
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value) as unknown;
      return parsed && typeof parsed === "object" && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : {};
    } catch {
      return {};
    }
  }
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function normalizeParameterizeConfig(value: unknown): ParameterizeConfig {
  const raw = parseJsonRecord(value);
  const sourceType = raw.source_type === "csv_text" ? "csv_text" : "inline_json";
  const rows = Array.isArray(raw.rows) ? (raw.rows as Array<Record<string, unknown>>) : [];
  return {
    enabled: Boolean(raw.enabled),
    source_type: sourceType,
    rows,
    csv_text: String(raw.csv_text ?? ""),
  };
}

function parameterizeConfigToText(config: ParameterizeConfig) {
  if (config.source_type === "csv_text") {
    return config.csv_text ?? "";
  }
  return JSON.stringify(config.rows ?? [], null, 2);
}

function syncParameterizeTextFromConfig() {
  parameterizeText.value = parameterizeConfigToText(normalizeParameterizeConfig(form.parameterize_config));
  parameterizeValidationMessage.value = "";
}

function parseParameterizeText(config: ParameterizeConfig) {
  if (config.source_type === "csv_text") {
    const lines = parameterizeText.value.split(/\r?\n/).filter((line) => line.trim());
    if (config.enabled && lines.length < 2) {
      throw new Error("CSV needs a header and at least one data row");
    }
    return {
      enabled: config.enabled,
      source_type: "csv_text" as const,
      csv_text: parameterizeText.value,
    };
  }
  const text = parameterizeText.value.trim();
  const parsed = text ? (JSON.parse(text) as unknown) : [];
  if (!Array.isArray(parsed)) {
    throw new Error("Inline JSON must be an array");
  }
  if (config.enabled && parsed.some((row) => !row || typeof row !== "object" || Array.isArray(row))) {
    throw new Error("Each parameter row must be an object");
  }
  return {
    enabled: config.enabled,
    source_type: "inline_json" as const,
    rows: parsed as Array<Record<string, unknown>>,
  };
}

function syncParameterizeConfigFromText(options?: { silent?: boolean }) {
  const config = normalizeParameterizeConfig(form.parameterize_config);
  try {
    form.parameterize_config = parseParameterizeText(config);
    parameterizeValidationMessage.value = "OK";
    if (!options?.silent) {
      ElMessage.success("Parameter data is valid");
    }
    return true;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Invalid parameter data";
    parameterizeValidationMessage.value = message;
    if (!options?.silent) {
      ElMessage.warning(message);
    }
    return false;
  }
}

function setParameterizeEnabled(event: Event) {
  const checked = Boolean((event.target as HTMLInputElement | null)?.checked);
  parameterizeConfig.value = {
    ...parameterizeConfig.value,
    enabled: checked,
  };
}

function setParameterizeSourceType(value: string) {
  parameterizeConfig.value = {
    ...parameterizeConfig.value,
    source_type: value === "csv_text" ? "csv_text" : "inline_json",
  };
  syncParameterizeTextFromConfig();
}

function handleParameterizeTextInput() {
  parameterizeValidationMessage.value = "";
  markActiveModified();
}

function parseBody(value: unknown) {
  if (!value) {
    return {};
  }
  if (typeof value !== "string") {
    return value;
  }
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

function stringifyBody(value: unknown) {
  if (value === undefined || value === null || value === "") {
    return "{\n  \n}";
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function mapToVariableRows(value: JsonMap | string | null | undefined): VariableRow[] {
  const entries = Object.entries(parseMap(value));
  if (!entries.length) {
    return [createVariableRow()];
  }
  return entries.map(([name, rawValue]) => createVariableRow(name, String(rawValue ?? "")));
}

function variableRowsToMap(rows: VariableRow[]): JsonMap {
  const result: JsonMap = {};
  rows.forEach((row) => {
    const name = row.name.trim();
    if (name) {
      result[name] = row.value;
    }
  });
  return result;
}

function mapToHeaderRows(value: unknown, fallback?: Array<{ key: string; value: string }>) {
  const source = parseMap(value);
  const entries = Object.entries(source);
  if (!entries.length) {
    if (fallback?.length) {
      return fallback.map((row) => createHeaderRow(row.key, row.value));
    }
    return [createHeaderRow()];
  }
  return entries.map(([key, rawValue]) => createHeaderRow(key, String(rawValue ?? "")));
}

function normalizeHeaderRows(value: unknown, fallback?: Array<{ key: string; value: string }>) {
  if (Array.isArray(value)) {
    const rows = value.map((item) => {
      const row = item && typeof item === "object" ? (item as Record<string, unknown>) : {};
      return createHeaderRow(String(row.key ?? ""), String(row.value ?? ""));
    });
    if (rows.length) {
      return rows;
    }
  }
  return mapToHeaderRows(value, fallback);
}

function headerRowsToMap(rows: Array<{ key: string; value: string }>): JsonMap {
  const result: JsonMap = {};
  rows.forEach((row) => {
    const key = row.key.trim();
    if (key) {
      result[key] = row.value;
    }
  });
  return result;
}

function normalizeExtractionRows(value: unknown) {
  if (!Array.isArray(value) || !value.length) {
    return [createExtractionRow()];
  }
  return value.map((item) =>
    createExtractionRow(
      String((item as Record<string, unknown>).variable ?? ""),
      String((item as Record<string, unknown>).path ?? ""),
    ),
  );
}

function extractionRowsToPayload(rows: Array<{ variable: string; path: string }>) {
  return rows
    .map((row) => ({
      variable: row.variable.trim(),
      path: row.path.trim(),
    }))
    .filter((row) => row.variable && row.path);
}

function normalizeOutputVariables(value: unknown): CaseOutputVariable[] {
  if (!Array.isArray(value) || !value.length) {
    return [];
  }
  return value.map((item) =>
    createOutputVariableRow(
      String((item as Record<string, unknown>).name ?? ""),
      String((item as Record<string, unknown>).source ?? ""),
    ),
  );
}

function outputVariablesToText(rows: CaseOutputVariable[]) {
  return (Array.isArray(rows) ? rows : [])
    .map((item) => String(item.name || item.source || "").trim())
    .filter(Boolean)
    .join(",");
}

function syncOutputVariablesFromText() {
  const names = Array.from(
    new Set(
      outputVariableText.value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  );
  form.output_variables = names.map((name) => createOutputVariableRow(name, name));
}

function outputVariablesToPayload(rows: CaseOutputVariable[]) {
  return rows
    .map((row) => ({
      name: String(row.name ?? "").trim(),
      source: String(row.source ?? "").trim(),
    }))
    .filter((row) => row.name && row.source);
}

function normalizeGlobalRequestConfig(value: unknown): CaseGlobalRequestConfig {
  const fallback = createDefaultGlobalRequestConfig();
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const loginRequest =
    raw.login_request && typeof raw.login_request === "object"
      ? (raw.login_request as Record<string, unknown>)
      : {};
  const headerConfig =
    raw.header_config && typeof raw.header_config === "object"
      ? (raw.header_config as Record<string, unknown>)
      : {};
  return {
    login_request: {
      enabled: Boolean(loginRequest.enabled),
      protocol: String(loginRequest.protocol ?? "http"),
      method: String(loginRequest.method ?? "POST"),
      url: String(loginRequest.url ?? ""),
      use_global_encryption: Boolean(loginRequest.use_global_encryption ?? loginRequest.useGlobalEncryption ?? false),
      headers_rows: normalizeHeaderRows(loginRequest.headers_rows ?? loginRequest.headers, [
        { key: "Content-Type", value: "application/json" },
      ]),
      body_text:
        "body_text" in loginRequest
          ? String(loginRequest.body_text ?? "{\n  \n}")
          : stringifyBody(loginRequest.body),
      extractions: normalizeExtractionRows(loginRequest.extractions),
    },
    header_config: {
      enabled: Boolean(headerConfig.enabled),
      headers_rows: normalizeHeaderRows(headerConfig.headers_rows ?? headerConfig.headers),
    },
  };
}

function serializeGlobalRequestConfig(config: CaseGlobalRequestConfig) {
  return {
    login_request: {
      enabled: config.login_request.enabled,
      protocol: config.login_request.protocol || "http",
      method: config.login_request.method || "POST",
      url: config.login_request.url.trim(),
      use_global_encryption: Boolean(config.login_request.use_global_encryption),
      headers: headerRowsToMap(config.login_request.headers_rows),
      body: parseBody(config.login_request.body_text),
      extractions: extractionRowsToPayload(config.login_request.extractions),
    },
    header_config: {
      enabled: config.header_config.enabled,
      headers: headerRowsToMap(config.header_config.headers_rows),
    },
  };
}

function createVariableRow(name = "", value = ""): VariableRow {
  return {
    rowKey: createKey("variable"),
    name,
    value,
  };
}

function normalizeTemplate(item: ApiTemplate): ApiTemplate {
  return {
    ...item,
    headers: parseMap(item.headers),
    params: parseMap(item.params),
    body: parseBody(item.body),
    description: item.description ?? "",
    timeout: item.timeout ?? 60,
    retry_enabled: Boolean(item.retry_enabled),
    retry_count: item.retry_count ?? 0,
    sort_order: item.sort_order ?? 0,
  };
}

function normalizeToolMap(value: unknown): CaseToolMap {
  if (!value) {
    return {};
  }
  let parsed: Record<string, unknown> = {};
  if (typeof value === "string") {
    try {
      parsed = JSON.parse(value) as Record<string, unknown>;
    } catch {
      parsed = {};
    }
  } else if (typeof value === "object") {
    parsed = value as Record<string, unknown>;
  }
  const result: CaseToolMap = {};
  Object.entries(parsed).forEach(([toolId, rawValue]) => {
    if (rawValue && typeof rawValue === "object" && !Array.isArray(rawValue)) {
      const rawTool = rawValue as Record<string, unknown>;
      result[toolId] = {
        id: toolId,
        name: String(rawTool.name ?? rawTool.tool_name ?? rawTool.label ?? toolId),
        tool_type: String(rawTool.tool_type ?? rawTool.type ?? "tool"),
        summary: String(rawTool.summary ?? rawTool.description ?? ""),
        enabled: rawTool.enabled !== false,
        priority: Number(rawTool.priority ?? rawTool.sort_order ?? 0) || 0,
        config:
          rawTool.config && typeof rawTool.config === "object" && !Array.isArray(rawTool.config)
            ? (rawTool.config as Record<string, unknown>)
            : {},
        ...rawTool,
      };
      return;
    }
    result[toolId] = {
      id: toolId,
      name: toolId,
      tool_type: "tool",
      summary: String(rawValue ?? ""),
      enabled: true,
      priority: 0,
      config: {},
    };
  });
  return result;
}

function resolveTemplate(templateId: number | null | undefined) {
  return templates.value.find((item) => item.id === templateId) ?? null;
}

function normalizeStep(step: Partial<CaseStep>): CaseStep {
  const template = resolveTemplate(step.api_template_id ?? null);
  return {
    id: step.id,
    case_id: step.case_id,
    api_template_id: step.api_template_id ?? null,
    step_order: step.step_order ?? 1,
    name: step.name ?? step.api_name ?? template?.name ?? "未命名步骤",
    enabled: step.enabled ?? true,
    pre_processing: normalizeToolMap(step.pre_processing),
    assertions: normalizeToolMap(step.assertions),
    post_processing: normalizeToolMap(step.post_processing),
    variables: parseMap(step.variables),
    enable_encryption: Boolean(step.enable_encryption),
    use_global_headers: step.use_global_headers !== false,
    api_name: step.api_name ?? template?.name ?? step.name ?? "未命名接口",
    api_method: step.api_method ?? template?.method ?? "GET",
    api_url_path: step.api_url_path ?? template?.url_path ?? "",
    api_folder_id: step.api_folder_id ?? template?.folder_id ?? null,
    api_project_id: step.api_project_id ?? template?.project_id ?? currentProjectId.value ?? null,
    api_description: step.api_description ?? template?.description ?? "",
    api_template: template,
    stepKey: step.stepKey ?? createKey("step"),
  };
}

function normalizeCase(item?: Partial<TestCaseRecord>): TestCaseRecord {
  const draft = createDraftCase(item?.project_id ?? currentProjectId.value ?? 0, item?.folder_id ?? null);
  return {
    ...draft,
    ...item,
    tabKey: item?.tabKey ?? (item?.id ? `case-${item.id}` : draft.tabKey),
    project_id: item?.project_id ?? draft.project_id,
    folder_id: item?.folder_id ?? null,
    name: item?.name ?? "",
    description: item?.description ?? "",
    environment_id: item?.environment_id ?? null,
    schema_version: item?.schema_version ?? 1,
    parameterize_config: normalizeParameterizeConfig(item?.parameterize_config),
    global_vars: parseMap(item?.global_vars),
    global_request_config: normalizeGlobalRequestConfig(item?.global_request_config),
    output_variables: normalizeOutputVariables(item?.output_variables),
    enable_encryption: Boolean(item?.enable_encryption),
    encrypt_url: item?.encrypt_url ?? "",
    decrypt_url: item?.decrypt_url ?? "",
    sort_order: item?.sort_order ?? draft.sort_order,
    steps: (item?.steps ?? []).map(normalizeStep),
  };
}

function getNextCaseSortOrder(folderId: number | null) {
  const siblingSortOrders = cases.value
    .filter((item) => item.folder_id === folderId)
    .map((item) => item.sort_order ?? 0);
  return (siblingSortOrders.length ? Math.max(...siblingSortOrders) : 0) + 1;
}

function getTabKey(item: TestCaseRecord) {
  return item.tabKey ?? (item.id ? `case-${item.id}` : createKey("draft"));
}

function getTabTitle(item: TestCaseRecord) {
  const title = item.id ? item.name || "未命名用例" : item.name || "新建用例";
  return modifiedTabs[getTabKey(item)] ? `*${title}` : title;
}

function getStepKey(step: CaseStep) {
  if (!step.stepKey) {
    step.stepKey = createKey("step");
  }
  return step.stepKey;
}

function getStepTab(step: CaseStep) {
  const key = getStepKey(step);
  if (!stepTabMap[key]) {
    stepTabMap[key] = "pre_processing";
  }
  return stepTabMap[key];
}

function setStepTab(step: CaseStep, tab: ToolTabKey) {
  stepTabMap[getStepKey(step)] = tab;
}

function usesAddToolDropdown(tab: ToolTabKey) {
  return tab !== "assertions";
}

function getAddToolButtonTitle(tab: ToolTabKey) {
  if (tab === "assertions") {
    return "添加断言";
  }
  return "添加处理工具";
}

function handleAddToolButton(step: CaseStep) {
  const tab = getStepTab(step);
  if (usesAddToolDropdown(tab)) {
    return;
  }
  if (tab === "assertions") {
    addToolToStep(step, tab, "assertion");
  }
}

function ensureToolMap(step: CaseStep, tab: ToolTabKey) {
  if (typeof step[tab] === "string" || !step[tab]) {
    step[tab] = normalizeToolMap(step[tab]);
  }
  return step[tab] as CaseToolMap;
}

function normalizeToolPriority(tool: CaseToolRecord, fallbackIndex: number) {
  const priority = Number(tool.priority ?? tool.sort_order ?? 0);
  return Number.isFinite(priority) && priority > 0 ? priority : fallbackIndex + 1;
}

function getToolEntries(step: CaseStep, tab: ToolTabKey) {
  return Object.entries(ensureToolMap(step, tab))
    .map(([toolId, tool], index) => ({
      toolId,
      orderIndex: index,
      tool: {
        ...tool,
        priority: normalizeToolPriority(tool, index),
      },
    }))
    .sort(
      (left, right) =>
        Number(left.tool.priority ?? 0) - Number(right.tool.priority ?? 0) || left.orderIndex - right.orderIndex,
    );
}

function getStepMethod(step: CaseStep) {
  return step.api_method ?? step.api_template?.method ?? "GET";
}

function getStepLabel(step: CaseStep) {
  return step.api_name ?? step.name ?? "未命名接口";
}

function getStepPlaceholder(tab: ToolTabKey) {
  return {
    pre_processing: "暂无前置处理工具",
    assertions: "暂无断言处理工具",
    post_processing: "暂无后置处理工具",
  }[tab];
}

function getToolLabel(tool: CaseToolRecord) {
  const toolType = String(tool.tool_type ?? "tool");
  if (toolType === "parameter_extract" || toolType === "parameter_extraction") {
    return "参数提取";
  }
  const option = Object.values(TOOL_OPTIONS)
    .flat()
    .find((item) => item.type === toolType);
  if (toolType === "assertion" || toolType.includes("assert")) {
    return "断言";
  }
  return String(tool.tool_label ?? option?.label ?? toolType);
}

function getToolSummary(tool: CaseToolRecord) {
  const config = (tool.config ?? {}) as Record<string, unknown>;
  if (tool.tool_type === "http_request") {
    const method = String(config.method ?? "GET");
    const url = String(config.url ?? "");
    return `${method} ${url}`.trim() || "未配置请求地址";
  }
  if (tool.tool_type === "sql_tool") {
    const connectionName = String(config.database_connection_name ?? "");
    const database = String(config.database ?? "");
    if (connectionName && database) {
      return `${connectionName} / ${database}`;
    }
    if (connectionName) {
      return `数据库：${connectionName}`;
    }
    return database ? `库名：${database}` : "未配置数据库";
  }
  if (tool.tool_type === "python_script") {
    return "Python 脚本";
  }
  if (tool.tool_type === "parameter_extraction") {
    const extractions = Array.isArray(tool.extractions) ? tool.extractions : [];
    return extractions.length ? `提取 ${extractions.length} 个变量` : "未配置提取规则";
  }
  if (tool.tool_type === "assertion") {
    const assertions = Array.isArray(tool.assertions) ? tool.assertions : [];
    return assertions.length ? `断言 ${assertions.length} 条规则` : "未配置断言规则";
  }
  return String(tool.summary ?? "未配置工具说明");
}

function getToolRowText(tool: CaseToolRecord) {
  const label = getToolLabel(tool);
  const name = String(tool.name ?? "").trim();
  const summary = getToolSummary(tool).trim();
  if (!name) {
    return summary || label;
  }
  if (!summary || summary === name) {
    return name;
  }
  if (name === label) {
    return summary;
  }
  return `${name} · ${summary}`;
}

function getToolDisplayName(tool: CaseToolRecord) {
  return String(tool.name ?? "").trim() || getToolLabel(tool);
}

function getToolTypeIcon(tool: CaseToolRecord) {
  const toolType = String(tool.tool_type ?? "");
  if (toolType === "http_request") {
    return httpToolIcon;
  }
  if (toolType === "sql_tool") {
    return sqlToolIcon;
  }
  if (toolType === "python_script") {
    return pythonToolIcon;
  }
  if (toolType === "parameter_extract" || toolType === "parameter_extraction") {
    return extractionToolIcon;
  }
  if (toolType === "assertion" || toolType.includes("assert")) {
    return assertionToolIcon;
  }
  return apiToolIcon;
}

function toCaseToolPreviewFromGlobalTool(globalTool: GlobalToolRecord): CaseToolRecord {
  return {
    id: String(globalTool.id),
    name: globalTool.name,
    tool_type: globalTool.tool_type,
    summary: globalTool.description,
    enabled: globalTool.enabled,
    config: (globalTool.config ?? {}) as Record<string, unknown>,
  };
}

function getGlobalToolLabel(globalTool: GlobalToolRecord) {
  return getToolLabel(toCaseToolPreviewFromGlobalTool(globalTool));
}

function getGlobalToolTypeIcon(globalTool: GlobalToolRecord) {
  return getToolTypeIcon(toCaseToolPreviewFromGlobalTool(globalTool));
}

function getToolPreviewRows(tool: CaseToolRecord) {
  const config = (tool.config ?? {}) as Record<string, unknown>;
  if (tool.tool_type === "http_request") {
    return [
      String(config.url ?? ""),
      String(config.body ?? ""),
    ].filter(Boolean).slice(0, 2);
  }
  if (tool.tool_type === "sql_tool") {
    return [
      String(config.sql ?? ""),
      Array.isArray(tool.output_fields) ? tool.output_fields.join(", ") : "",
    ].filter(Boolean).slice(0, 2);
  }
  if (tool.tool_type === "python_script") {
    return [
      String(config.script ?? config.script_text ?? config.code ?? "").split("\n").find(Boolean) ?? "",
      Array.isArray(tool.output_fields) ? tool.output_fields.join(", ") : "",
    ].filter(Boolean).slice(0, 2);
  }
  if (tool.tool_type === "parameter_extraction") {
    return (Array.isArray(tool.extractions) ? tool.extractions : [])
      .slice(0, 2)
      .map((item) => `${item.variable || "变量"} <- ${item.path || "路径"}`);
  }
  if (tool.tool_type === "assertion") {
    return (Array.isArray(tool.assertions) ? tool.assertions : [])
      .slice(0, 2)
      .map((item) => `${item.field || "字段"} ${formatAssertionOperator(item.operator)} ${item.expected || "空"}`);
  }
  return [String(tool.summary ?? "")].filter(Boolean);
}

function formatAssertionOperator(operator?: string) {
  return ASSERTION_OPERATOR_OPTIONS.find((item) => item.value === operator)?.label ?? "=";
}

function splitAssertionField(value: unknown) {
  const field = String(value ?? "").trim();
  if (!field) {
    return {
      prefix: "body.",
      path: "",
    };
  }
  const exactPrefix = ASSERTION_FIELD_PREFIX_OPTIONS.find(
    (option) => option.value && !option.value.endsWith(".") && field === option.value,
  );
  if (exactPrefix) {
    return {
      prefix: exactPrefix.value,
      path: "",
    };
  }
  const dottedPrefix = ASSERTION_FIELD_PREFIX_OPTIONS
    .filter((option) => option.value.endsWith("."))
    .sort((left, right) => right.value.length - left.value.length)
    .find((option) => field.startsWith(option.value));
  if (dottedPrefix) {
    return {
      prefix: dottedPrefix.value,
      path: field.slice(dottedPrefix.value.length),
    };
  }
  if (field.startsWith("$")) {
    return {
      prefix: "$",
      path: field.slice(1),
    };
  }
  return {
    prefix: "",
    path: field,
  };
}

function getAssertionFieldSourceOption(prefix: string) {
  return ASSERTION_FIELD_SOURCE_OPTIONS.find((option) => option.value === prefix) ?? ASSERTION_FIELD_SOURCE_OPTIONS[0];
}

function isScalarAssertionPrefix(prefix: string) {
  return SCALAR_ASSERTION_FIELD_PREFIXES.has(prefix);
}

function isAssertionPathDisabled(prefix: string) {
  return getAssertionFieldSourceOption(prefix).mode === "scalar";
}

function getAssertionFieldPlaceholder(prefix: string) {
  return getAssertionFieldSourceOption(prefix).placeholder;
}

function buildAssertionField(row: ToolDraftRow) {
  const prefix = row.fieldPrefix || "";
  const path = row.fieldPath.trim();
  if (!prefix) {
    return path;
  }
  if (isScalarAssertionPrefix(prefix)) {
    return prefix;
  }
  if (prefix === "$") {
    if (!path) {
      return "$";
    }
    if (path === "$" || path.startsWith("$")) {
      return path;
    }
    return path.startsWith(".") || path.startsWith("[") ? `$${path}` : `$.${path}`;
  }
  if (!path) {
    return "";
  }
  const normalizedPath = path.replace(/^\.+/, "");
  if (!normalizedPath) {
    return "";
  }
  return normalizedPath.startsWith(prefix) ? normalizedPath : `${prefix}${normalizedPath}`;
}

function handleAssertionPrefixChange(row: ToolDraftRow) {
  if (isAssertionPathDisabled(row.fieldPrefix)) {
    row.fieldPath = "";
  }
}

function createToolRow(): ToolDraftRow {
  return {
    rowKey: createKey("tool-row"),
    field: "",
    operator: "equal",
    expected: "",
    fieldPrefix: "body.",
    fieldPath: "",
    variable: "",
    path: "",
    extractorType: "jsonpath",
    source: "body",
  };
}

function createToolHeaderRow(key = "", value = ""): ToolHeaderRow {
  return {
    rowKey: createKey("tool-header"),
    key,
    value,
  };
}

function normalizeDatabaseConnectionId(value: unknown): number | null {
  const id = Number(value);
  return Number.isFinite(id) && id > 0 ? id : null;
}

function getDatabaseConnectionById(databaseId: number | null) {
  if (!databaseId) {
    return null;
  }
  return databaseConnections.value.find((item) => item.id === databaseId) ?? null;
}

function getDatabaseConnectionLabel(item: DatabaseConnectionRecord) {
  const host = item.host ? `${item.host}:${item.port}` : "";
  return host ? `${item.name}（${host}）` : item.name;
}

async function loadSqlDatabaseSchemas(databaseId: number | null, options?: { preserveSelected?: boolean }) {
  sqlDatabaseSchemasRequestToken += 1;
  const requestToken = sqlDatabaseSchemasRequestToken;
  sqlDatabaseSchemas.value = [];
  if (!databaseId) {
    return;
  }

  const previousSchema = toolForm.database.trim();
  sqlDatabaseSchemasLoading.value = true;
  try {
    const result = await fetchDatabaseSchemas(databaseId);
    if (requestToken !== sqlDatabaseSchemasRequestToken) {
      return;
    }
    const schemas = Array.isArray(result.schemas) ? result.schemas : [];
    sqlDatabaseSchemas.value = schemas;
    if (options?.preserveSelected && previousSchema && schemas.includes(previousSchema)) {
      toolForm.database = previousSchema;
      return;
    }
    const defaultSchema = getDatabaseConnectionById(databaseId)?.database_name?.trim() ?? "";
    toolForm.database = defaultSchema && schemas.includes(defaultSchema) ? defaultSchema : "";
  } catch (error) {
    if (requestToken === sqlDatabaseSchemasRequestToken) {
      toolForm.database = "";
      ElMessage.error((error as Error).message);
    }
  } finally {
    if (requestToken === sqlDatabaseSchemasRequestToken) {
      sqlDatabaseSchemasLoading.value = false;
    }
  }
}

function handleSqlDatabaseConnectionChange(value: number | string | null) {
  toolForm.database = "";
  void loadSqlDatabaseSchemas(normalizeDatabaseConnectionId(value));
}

function resetToolForm() {
  toolForm.name = "";
  toolForm.summary = "";
  toolForm.method = "GET";
  toolForm.url = "";
  toolForm.timeout = 30;
  toolForm.useGlobalEncryption = false;
  toolForm.useGlobalHeaders = false;
  toolForm.headersText = "{}";
  toolForm.bodyText = "{}";
  toolForm.databaseConnectionId = null;
  toolForm.database = "";
  toolForm.sqlText = "";
  toolForm.outputFieldsText = "";
  toolForm.pythonScriptPath = "";
  toolForm.pythonWorkingDir = "";
  toolForm.pythonScriptText = "";
  toolForm.pythonTimeout = 60;
  sqlDatabaseSchemas.value = [];
  sqlDatabaseSchemasLoading.value = false;
  httpToolTab.value = "body";
  toolHeaderRows.value = [];
  toolRows.value = [];
}

function getStepByKey(stepKey: string) {
  return form.steps.find((item) => getStepKey(item) === stepKey) ?? null;
}

function getToolByContext(stepKey: string, tab: ToolTabKey, toolId: string) {
  const step = getStepByKey(stepKey);
  if (!step) {
    return null;
  }
  return ensureToolMap(step, tab)[toolId] ?? null;
}

function inferToolDialogKind(toolType: string, tab: ToolTabKey): ToolDialogKind {
  if (toolType === "http_request") {
    return "http_request";
  }
  if (toolType === "sql_tool") {
    return "sql_tool";
  }
  if (toolType === "python_script") {
    return "python_script";
  }
  if (toolType === "parameter_extract" || toolType === "parameter_extraction") {
    return "parameter_extraction";
  }
  if (tab === "assertions" || toolType.includes("assert")) {
    return "assertion";
  }
  return "generic";
}

function fillToolDialogFromRecord(tool: CaseToolRecord, tab: ToolTabKey) {
  resetToolForm();
  toolDialogKind.value = inferToolDialogKind(String(tool.tool_type ?? "tool"), tab);
  const config = (tool.config ?? {}) as Record<string, unknown>;
  toolForm.name = String(tool.name ?? "");
  toolForm.summary = String(tool.summary ?? "");
  if (toolDialogKind.value === "http_request") {
    toolForm.method = String(config.method ?? "GET");
    toolForm.url = String(config.url ?? "");
    toolForm.timeout = Number(config.timeout ?? 30) || 30;
    toolForm.useGlobalEncryption = Boolean(config.use_global_encryption ?? config.useGlobalEncryption ?? false);
    toolForm.useGlobalHeaders = Boolean(config.use_global_headers ?? config.useGlobalHeaders ?? false);
    const rawHeaders =
      typeof config.headers === "string"
        ? (() => {
            try {
              return JSON.parse(String(config.headers));
            } catch {
              return {};
            }
          })()
        : ((config.headers ?? {}) as Record<string, unknown>);
    const headerEntries = Object.entries(rawHeaders ?? {});
    toolHeaderRows.value = headerEntries.length
      ? headerEntries.map(([key, value]) => ({
          rowKey: createKey("header"),
          key,
          value: String(value ?? ""),
        }))
      : [createToolHeaderRow("Content-Type", "application/json")];
    if (typeof config.body === "string") {
      toolForm.bodyText = String(config.body).trim() || "{}";
    } else {
      toolForm.bodyText = JSON.stringify(config.body ?? {}, null, 2);
    }
    const rows = Array.isArray(config.extractions) ? config.extractions : [];
    toolRows.value = rows.length
      ? rows.map((item) => ({
          rowKey: createKey("extract"),
          field: "",
          operator: "equal",
          expected: "",
          fieldPrefix: "body.",
          fieldPath: "",
          variable: String((item as Record<string, unknown>).variable ?? ""),
          path: String((item as Record<string, unknown>).path ?? ""),
          extractorType: String((item as Record<string, unknown>).type ?? "jsonpath"),
          source: String((item as Record<string, unknown>).from ?? (item as Record<string, unknown>).source ?? "body"),
        }))
      : [createToolRow()];
    return;
  }
  if (toolDialogKind.value === "sql_tool") {
    toolForm.databaseConnectionId = normalizeDatabaseConnectionId(
      config.database_connection_id ?? config.database_asset_id ?? config.connection_id,
    );
    toolForm.database = String(config.database ?? config.database_name ?? "");
    toolForm.sqlText = String(config.sql ?? "");
    toolForm.outputFieldsText = Array.isArray(tool.output_fields)
      ? tool.output_fields.join(", ")
      : String(config.output_fields ?? "");
    if (toolForm.databaseConnectionId) {
      void loadSqlDatabaseSchemas(toolForm.databaseConnectionId, { preserveSelected: true });
    }
    return;
  }
  if (toolDialogKind.value === "python_script") {
    toolForm.pythonScriptPath = String(config.script_path ?? config.path ?? "");
    toolForm.pythonWorkingDir = String(config.working_dir ?? config.cwd ?? "");
    toolForm.pythonScriptText = String(config.script ?? config.script_text ?? config.code ?? "");
    toolForm.pythonTimeout = Number(config.timeout_seconds ?? config.timeout ?? 60) || 60;
    toolForm.outputFieldsText = Array.isArray(tool.output_fields)
      ? tool.output_fields.join(", ")
      : String(config.output_fields ?? "");
    return;
  }
  if (toolDialogKind.value === "parameter_extraction") {
    const rows = Array.isArray(tool.extractions)
      ? tool.extractions
      : Array.isArray(config.extractions)
        ? config.extractions
        : [];
    toolRows.value = rows.length
      ? rows.map((item) => ({
          rowKey: createKey("extract"),
          field: "",
          operator: "equal",
          expected: "",
          fieldPrefix: "body.",
          fieldPath: "",
          variable: String((item as Record<string, unknown>).variable ?? ""),
          path: String((item as Record<string, unknown>).path ?? ""),
          extractorType: String((item as Record<string, unknown>).type ?? "jsonpath"),
          source: String((item as Record<string, unknown>).from ?? (item as Record<string, unknown>).source ?? "body"),
        }))
      : [createToolRow()];
    return;
  }
  if (toolDialogKind.value === "assertion") {
    const rows = Array.isArray(tool.assertions)
      ? tool.assertions
      : Array.isArray(config.assertions)
        ? config.assertions
        : [];
    toolRows.value = rows.length
      ? rows.map((item) => {
          const field = String((item as Record<string, unknown>).field ?? "");
          const parsedField = splitAssertionField(field);
          return {
            rowKey: createKey("assert"),
            field,
            operator: String((item as Record<string, unknown>).operator ?? "equal"),
            expected: String((item as Record<string, unknown>).expected ?? ""),
            fieldPrefix: parsedField.prefix,
            fieldPath: parsedField.path,
            variable: "",
            path: "",
            extractorType: "jsonpath",
            source: "body",
          };
        })
      : [createToolRow()];
  }
}

function openNewToolDialog(step: CaseStep, tab: ToolTabKey, toolType: string) {
  const defaults = createDefaultToolConfig(toolType, tab);
  toolDialogStepKey.value = getStepKey(step);
  toolDialogTab.value = tab;
  toolDialogToolId.value = "";
  toolDialogNewType.value = toolType;
  toolDialogIsNew.value = true;
  toolDialogCommitted.value = false;
  fillToolDialogFromRecord(
    {
      id: "",
      name: String(defaults.name ?? getToolLabel({ tool_type: toolType })),
      summary: String(defaults.summary ?? ""),
      enabled: true,
      tool_type: String(defaults.tool_type ?? toolType),
      tool_label: getToolLabel({ tool_type: String(defaults.tool_type ?? toolType) }),
      config: ((defaults.config as Record<string, unknown>) ?? {}) as Record<string, unknown>,
      ...(defaults as Record<string, unknown>),
    },
    tab,
  );
  toolDialogTitle.value = `新增${getToolLabel({ tool_type: String(defaults.tool_type ?? toolType) })}`;
  toolDialogVisible.value = true;
}

function openToolDialog(step: CaseStep, tab: ToolTabKey, toolId: string, options?: { isNew?: boolean }) {
  const tool = ensureToolMap(step, tab)[toolId];
  if (!tool) {
    return;
  }
  toolDialogStepKey.value = getStepKey(step);
  toolDialogTab.value = tab;
  toolDialogToolId.value = toolId;
  toolDialogNewType.value = "";
  toolDialogIsNew.value = Boolean(options?.isNew);
  toolDialogCommitted.value = false;
  toolDialogTitle.value = `${toolDialogIsNew.value ? "新增" : "编辑"}${getToolLabel(tool)}`;
  fillToolDialogFromRecord(tool, tab);
  toolDialogVisible.value = true;
}

function handleToolDialogClosed() {
  toolDialogIsNew.value = false;
  toolDialogCommitted.value = false;
  toolDialogNewType.value = "";
  toolDialogToolId.value = "";
  toolDialogStepKey.value = "";
  toolDialogTitle.value = "";
  httpToolTab.value = "body";
  toolHeaderRows.value = [];
  toolRows.value = [];
}

function addToolRow() {
  toolRows.value.push(createToolRow());
}

function addHeaderRow() {
  toolHeaderRows.value.push(createToolHeaderRow());
}

function insertHeaderRow(index: number) {
  toolHeaderRows.value.splice(index + 1, 0, createToolHeaderRow());
}

function removeHeaderRow(index: number) {
  if (toolHeaderRows.value.length <= 1) {
    toolHeaderRows.value = [createToolHeaderRow("Content-Type", "application/json")];
    return;
  }
  toolHeaderRows.value.splice(index, 1);
}

function insertToolRow(index: number) {
  toolRows.value.splice(index + 1, 0, createToolRow());
}

function removeToolRow(index: number) {
  if (toolRows.value.length <= 1) {
    toolRows.value = [createToolRow()];
    return;
  }
  toolRows.value.splice(index, 1);
}

function getNextToolPriority(map: CaseToolMap) {
  const priorities = Object.values(map).map((tool, index) => normalizeToolPriority(tool, index));
  return priorities.length ? Math.max(...priorities) + 1 : 1;
}

function updateToolPriorities(map: CaseToolMap) {
  Object.entries(map)
    .map(([toolId, tool], index) => ({
      toolId,
      orderIndex: index,
      priority: normalizeToolPriority(tool, index),
    }))
    .sort((left, right) => left.priority - right.priority || left.orderIndex - right.orderIndex)
    .forEach(({ toolId }, index) => {
      map[toolId].priority = index + 1;
    });
}

function appendToolToMap(map: CaseToolMap, toolId: string, tool: CaseToolRecord) {
  tool.id = toolId;
  tool.priority = getNextToolPriority(map);
  map[toolId] = tool;
}

function buildToolFromGlobalTool(globalTool: GlobalToolRecord): CaseToolRecord {
  const config = deepClone((globalTool.config ?? {}) as Record<string, unknown>);
  const outputFields = Array.isArray(config.output_fields) ? config.output_fields.map((item) => String(item)) : [];
  return {
    id: "",
    name: globalTool.name,
    summary: globalTool.description || getToolSummary({ tool_type: globalTool.tool_type, config }),
    enabled: true,
    tool_type: globalTool.tool_type,
    tool_label: getToolLabel({ tool_type: globalTool.tool_type }),
    source_global_tool_id: globalTool.id,
    source_global_tool_name: globalTool.name,
    output_fields: outputFields,
    config,
  };
}

function addGlobalToolToStep(step: CaseStep, tab: ToolTabKey, globalTool: GlobalToolRecord) {
  const map = ensureToolMap(step, tab);
  const tool = buildToolFromGlobalTool(globalTool);
  const toolId = createKey(globalTool.tool_type);
  appendToolToMap(map, toolId, tool);
  markActiveModified();
  ElMessage.success(`已添加全局工具：${globalTool.name}`);
}

function getGlobalEncryptionConfigIssue() {
  if (!form.enable_encryption) {
    return "请先启用用例全局加解密配置";
  }
  if (!form.encrypt_url.trim() || !form.decrypt_url.trim()) {
    return "请先完整配置全局加密URL和解密URL";
  }
  return "";
}

function validateGlobalEncryptionForHttpTool() {
  const issue = getGlobalEncryptionConfigIssue();
  if (issue) {
    ElMessage.warning(issue);
    return false;
  }
  return true;
}

function handleToolGlobalEncryptionChange(value: string | number | boolean) {
  if (!Boolean(value)) {
    return;
  }
  if (!validateGlobalEncryptionForHttpTool()) {
    toolForm.useGlobalEncryption = false;
  }
}

function handleToolGlobalHeadersChange(value: string | number | boolean) {
  if (!Boolean(value)) {
    return;
  }
  if (!form.global_request_config.header_config.enabled) {
    ElMessage.warning("全局请求头未启用，请先启用");
    toolForm.useGlobalHeaders = false;
  }
}

function handleLoginGlobalEncryptionChange(event: Event) {
  const checked = (event.target as HTMLInputElement).checked;
  if (!checked) {
    return;
  }
  if (!validateGlobalEncryptionForHttpTool()) {
    form.global_request_config.login_request.use_global_encryption = false;
  }
}

function createDefaultToolConfig(toolType: string, tab: ToolTabKey) {
  if (toolType === "http_request") {
    return {
      name: "HTTP请求",
      summary: "",
      config: {
        method: "GET",
        url: "",
        timeout: 30,
        use_global_encryption: false,
        use_global_headers: false,
        headers: {},
        body: {},
        extractions: [{ variable: "", path: "" }],
      },
    };
  }
  if (toolType === "sql_tool") {
    return {
      name: "SQL工具",
      summary: "",
      output_fields: [],
      config: {
        database: "",
        sql: "",
      },
    };
  }
  if (toolType === "python_script") {
    return {
      name: "Python脚本",
      summary: "",
      output_fields: [],
      config: {
        script: "",
        timeout_seconds: 60,
        render_template: true,
        output_fields: [],
      },
    };
  }
  if (toolType === "parameter_extract" || toolType === "parameter_extraction") {
    return {
      name: "参数提取",
      summary: "",
      tool_type: "parameter_extraction",
      extractions: [{ variable: "", path: "" }],
      config: {
        extractions: [{ variable: "", path: "" }],
      },
    };
  }
  if (tab === "assertions") {
    return {
      name: "断言",
      summary: "",
      tool_type: "assertion",
      assertions: [{ field: "", operator: "equal", expected: "" }],
      config: {
        assertions: [{ field: "", operator: "equal", expected: "" }],
      },
    };
  }
  return {
    name: getToolLabel({ tool_type: toolType }),
    summary: "",
    config: {},
  };
}

function saveToolDialog() {
  const step = getStepByKey(toolDialogStepKey.value);
  if (!step) {
    toolDialogVisible.value = false;
    return;
  }
  const map = ensureToolMap(step, toolDialogTab.value);
  const existingTool = toolDialogToolId.value ? map[toolDialogToolId.value] : null;
  const toolId = toolDialogToolId.value || createKey(toolDialogNewType.value || toolDialogKind.value);
  const tool =
    existingTool ??
    ({
      id: toolId,
      name: "",
      summary: "",
      enabled: true,
      priority: getNextToolPriority(map),
      tool_type: toolDialogNewType.value || toolDialogKind.value,
      tool_label: getToolLabel({ tool_type: toolDialogNewType.value || toolDialogKind.value }),
      config: {},
    } as CaseToolRecord);
  toolDialogSaving.value = true;
  try {
    tool.name = toolForm.name.trim() || getToolLabel(tool);
    tool.summary = toolForm.summary.trim();
    if (toolDialogKind.value === "http_request") {
      if (!toolForm.url.trim()) {
        ElMessage.warning("请输入请求 URL");
        return;
      }
      if (toolForm.useGlobalEncryption && !validateGlobalEncryptionForHttpTool()) {
        return;
      }
      if (toolForm.useGlobalHeaders && !form.global_request_config.header_config.enabled) {
        ElMessage.warning("全局请求头未启用，请先启用");
        return;
      }
      const headerEntries = toolHeaderRows.value
        .map((row) => ({ key: row.key.trim(), value: row.value.trim() }))
        .filter((row) => row.key || row.value);
      if (headerEntries.some((row) => !row.key || !row.value)) {
        ElMessage.warning("请求头名称和值不能为空");
        return;
      }
      const headers = Object.fromEntries(headerEntries.map((row) => [row.key, row.value]));
      let body: unknown = toolForm.bodyText;
      try {
        body = toolForm.bodyText.trim() ? JSON.parse(toolForm.bodyText) : {};
      } catch {
        body = toolForm.bodyText;
      }
      const extractionRows = toolRows.value
        .map((row) => ({
          variable: row.variable.trim(),
          path: row.path.trim(),
          type: row.extractorType || "jsonpath",
          from: row.source || "body",
          expr: row.path.trim(),
        }))
        .filter((row) => row.variable || row.path);
      if (extractionRows.some((row) => !row.variable || !row.path)) {
        ElMessage.warning("响应提取的变量名称和 JSONPath 不能为空");
        return;
      }
      tool.config = {
        method: toolForm.method,
        url: toolForm.url.trim(),
        timeout: Number(toolForm.timeout) || 30,
        use_global_encryption: toolForm.useGlobalEncryption,
        use_global_headers: toolForm.useGlobalHeaders,
        headers,
        body,
        extractions: extractionRows,
      };
      tool.summary = toolForm.summary.trim() || `${toolForm.method} ${toolForm.url.trim()}`.trim();
      tool.tool_type = "http_request";
    } else if (toolDialogKind.value === "sql_tool") {
      if (!toolForm.databaseConnectionId) {
        ElMessage.warning("请选择数据库");
        return;
      }
      if (!toolForm.database.trim()) {
        ElMessage.warning("请选择库名");
        return;
      }
      if (!toolForm.sqlText.trim()) {
        ElMessage.warning("请输入 SQL 语句");
        return;
      }
      const outputFields = toolForm.outputFieldsText
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      const selectedDatabaseConnection = getDatabaseConnectionById(toolForm.databaseConnectionId);
      tool.output_fields = outputFields;
      tool.config = {
        database_connection_id: toolForm.databaseConnectionId,
        database_connection_name: selectedDatabaseConnection?.name ?? "",
        database: toolForm.database.trim(),
        sql: toolForm.sqlText,
      };
      tool.summary =
        toolForm.summary.trim() ||
        [
          selectedDatabaseConnection?.name ? `数据库：${selectedDatabaseConnection.name}` : "",
          toolForm.database.trim() ? `库名：${toolForm.database.trim()}` : "",
        ]
          .filter(Boolean)
          .join(" / ");
      tool.tool_type = "sql_tool";
    } else if (toolDialogKind.value === "python_script") {
      if (!toolForm.pythonScriptText.trim()) {
        ElMessage.warning("请输入脚本内容");
        return;
      }
      const outputFields = toolForm.outputFieldsText
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      tool.output_fields = outputFields;
      tool.config = {
        script: toolForm.pythonScriptText,
        timeout_seconds: Number(toolForm.pythonTimeout) || 60,
        render_template: true,
        output_fields: outputFields,
      };
      tool.summary = toolForm.summary.trim() || "Python 脚本";
      tool.tool_type = "python_script";
    } else if (toolDialogKind.value === "parameter_extraction") {
      const extractions = toolRows.value
        .map((row) => ({
          variable: row.variable.trim(),
          path: row.path.trim(),
          type: row.extractorType || "jsonpath",
          from: row.source || "body",
          expr: row.path.trim(),
        }))
        .filter((row) => row.variable || row.path);
      if (!extractions.length) {
        ElMessage.warning("请至少配置一条参数提取规则");
        return;
      }
      if (extractions.some((row) => !row.variable || !row.path)) {
        ElMessage.warning("参数提取的变量名称和 JSONPath 不能为空");
        return;
      }
      tool.extractions = extractions;
      tool.config = { extractions };
      tool.tool_type = "parameter_extraction";
      tool.summary = toolForm.summary.trim() || (extractions.length ? `提取 ${extractions.length} 个变量` : "");
    } else if (toolDialogKind.value === "assertion") {
      const assertions = toolRows.value
        .map((row) => ({
          field: buildAssertionField(row),
          operator: row.operator,
          expected: row.expected.trim(),
        }))
        .filter((row) => row.field || row.expected);
      if (!assertions.length) {
        ElMessage.warning("请至少配置一条断言规则");
        return;
      }
      if (assertions.some((row) => !row.field)) {
        ElMessage.warning("断言字段不能为空");
        return;
      }
      tool.assertions = assertions;
      tool.config = { assertions };
      tool.tool_type = "assertion";
      tool.summary = toolForm.summary.trim() || (assertions.length ? `断言 ${assertions.length} 条规则` : "");
    } else {
      tool.summary = toolForm.summary.trim();
    }
    if (!existingTool) {
      appendToolToMap(map, toolId, tool);
      toolDialogToolId.value = toolId;
    }
    toolDialogCommitted.value = true;
    markActiveModified();
    toolDialogVisible.value = false;
  } finally {
    toolDialogSaving.value = false;
  }
}

function getTemplateMethodClass(method: string) {
  const normalized = method.toUpperCase();
  if (normalized === "POST") return "post";
  if (normalized === "DELETE") return "delete";
  if (normalized === "PUT") return "put";
  if (normalized === "PATCH") return "patch";
  return "get";
}

function findCaseNodeById(nodes: CaseNavNode[], targetId: string): CaseNavNode | null {
  for (const node of nodes) {
    if (node.id === targetId) {
      return node;
    }
    if (node.children?.length) {
      const match = findCaseNodeById(node.children, targetId);
      if (match) {
        return match;
      }
    }
  }
  return null;
}

function getFolderById(folderId: number | null | undefined) {
  if (folderId === null || folderId === undefined) {
    return null;
  }
  return folders.value.find((item) => item.id === folderId) ?? null;
}

function getTopLevelFolderId(folderId: number | null | undefined): number | null {
  let current = getFolderById(folderId);
  if (!current) {
    return null;
  }
  while (current.parent_id !== null) {
    current = getFolderById(current.parent_id);
    if (!current) {
      return null;
    }
  }
  return current.id;
}

function getCaseFolderDepth(folderId: number | null | undefined): number {
  let depth = 0;
  let current = getFolderById(folderId);
  while (current) {
    depth += 1;
    current = current.parent_id !== null ? getFolderById(current.parent_id) : null;
  }
  return depth;
}

function canCreateCaseChildFolder(folderId: number | null | undefined): boolean {
  return getCaseFolderDepth(folderId) < 3;
}

function getCaseCreateFolderIdFromNode(node: CaseNavNode | null, blank = false) {
  if (blank || !node) {
    return null;
  }
  if (node.type === "folder") {
    const folder = getFolderById(node.folderId);
    if (!folder || folder.parent_id !== null) {
      return null;
    }
    return folder.id;
  }
  return getTopLevelFolderId(node.folderId);
}

function syncProjectPath() {
  const groupId = context.selectedGroupId.value;
  const projectId = context.selectedProjectId.value;
  projectPath.value = groupId && projectId ? [groupId, projectId] : [];
}

function ensureGlobalConfigState(tabKey: string) {
  if (!(tabKey in globalConfigExpandedMap)) {
    globalConfigExpandedMap[tabKey] = false;
  }
}

function resetForm(caseItem?: TestCaseRecord) {
  resetting = true;
  const next = normalizeCase(caseItem);
  Object.assign(form, {
    id: next.id ?? undefined,
    tabKey: next.tabKey,
    ...next,
  });
  if (activeTabKey.value) {
    ensureGlobalConfigState(activeTabKey.value);
  }
  outputVariableText.value = outputVariablesToText(form.output_variables);
  syncParameterizeTextFromConfig();
  variableRows.value = mapToVariableRows(form.global_vars);
  form.steps.forEach((step) => getStepTab(step));
  activeStepKey.value = form.steps[0] ? getStepKey(form.steps[0]) : "";
  nextTick(() => {
    resetting = false;
  });
}

function syncActiveTabSnapshot() {
  if (!activeTabKey.value) {
    return;
  }
  const index = openedTabs.value.findIndex((item) => getTabKey(item) === activeTabKey.value);
  if (index === -1) {
    return;
  }
  openedTabs.value[index] = normalizeCase({
    ...deepClone(form),
    tabKey: activeTabKey.value,
  });
}

function markActiveModified() {
  if (resetting || !activeTabKey.value) {
    return;
  }
  syncActiveTabSnapshot();
  modifiedTabs[activeTabKey.value] = true;
}

async function loadWorkspace() {
  if (!currentProjectId.value) {
    folders.value = [];
    cases.value = [];
    apiFolders.value = [];
    templates.value = [];
    environments.value = [];
    globalVariables.value = [];
    globalTools.value = [];
    databaseConnections.value = [];
    variableRows.value = [];
    openedTabs.value = [];
    activeTabKey.value = "";
    selectedCaseNodeId.value = "";
    selectedTemplateNodeId.value = "";
    resetForm(createDraftCase(0, null));
    return;
  }
  loading.value = true;
  try {
    const [
      folderRows,
      caseRows,
      templateWorkspace,
      environmentRows,
      globalVariableRows,
      globalToolRows,
      databaseConnectionRows,
    ] = await Promise.all([
      get<CaseFolder[]>("/api/interface-auto/case-folders/", { project_id: currentProjectId.value }),
      get<Array<Partial<TestCaseRecord>>>("/api/interface-auto/cases/", { project_id: currentProjectId.value }),
      get<TemplateWorkspacePayload>("/api/interface-auto/api-template-workspace/", {
        project_id: currentProjectId.value,
      }),
      fetchEnvironments(),
      fetchGlobalVariables({ project_id: currentProjectId.value }),
      currentProjectId.value
        ? fetchGlobalTools({ visible_project_id: currentProjectId.value })
        : Promise.resolve([] as GlobalToolRecord[]),
      fetchDatabaseConnections({ business_group_id: context.selectedGroupId.value ?? null }),
    ]);
    folders.value = folderRows;
    cases.value = caseRows.map((item) => normalizeCase(item));
    apiFolders.value = templateWorkspace.folders;
    templates.value = templateWorkspace.templates.map(normalizeTemplate);
    environments.value = Array.isArray(environmentRows) ? environmentRows : [];
    globalVariables.value = Array.isArray(globalVariableRows) ? globalVariableRows : [];
    globalTools.value = Array.isArray(globalToolRows) ? globalToolRows : [];
    databaseConnections.value = Array.isArray(databaseConnectionRows) ? databaseConnectionRows : [];
  } finally {
    loading.value = false;
  }
}

async function openCase(caseId: number) {
  const detail = normalizeCase(await get<Partial<TestCaseRecord>>(`/api/interface-auto/cases/${caseId}/`));
  const draftIndex = openedTabs.value.findIndex((item) => item.id === detail.id);
  const currentTab = draftIndex === -1 ? null : openedTabs.value[draftIndex];
  const tabKey = currentTab?.tabKey ?? getTabKey(detail);
  const index = openedTabs.value.findIndex((item) => item.id === detail.id || getTabKey(item) === tabKey);
  const existingTab = index === -1 ? currentTab : openedTabs.value[index];
  const mergedDetail =
    existingTab && modifiedTabs[getTabKey(existingTab)]
      ? normalizeCase({
          ...detail,
          ...deepClone(existingTab),
          id: detail.id,
          tabKey,
        })
      : detail;
  if (index === -1) {
    openedTabs.value.push({ ...mergedDetail, tabKey });
  } else {
    openedTabs.value[index] = { ...mergedDetail, tabKey };
  }
  activeTabKey.value = tabKey;
  ensureGlobalConfigState(tabKey);
  selectedCaseNodeId.value = `case-${caseId}`;
  resetForm({ ...mergedDetail, tabKey });
  nextTick(() => {
    caseTreeRef.value?.setCurrentKey?.(selectedCaseNodeId.value);
  });
}

function openDraftCase(folderId: number | null) {
  if (!currentProjectId.value) {
    ElMessage.warning("请先选择项目");
    return;
  }
  const topLevelFolderId = getTopLevelFolderId(folderId);
  if (!topLevelFolderId) {
    ElMessage.warning("请先选择一级目录，然后在该目录下创建测试用例");
    return;
  }
  const draft = createDraftCase(currentProjectId.value, folderId);
  openedTabs.value.push(draft);
  activeTabKey.value = getTabKey(draft);
  ensureGlobalConfigState(activeTabKey.value);
  resetForm(draft);
}

function focusTab(tabKey: string) {
  const next = openedTabs.value.find((item) => getTabKey(item) === tabKey);
  if (!next) {
    return;
  }
  activeTabKey.value = tabKey;
  ensureGlobalConfigState(tabKey);
  if (next.id && !modifiedTabs[tabKey]) {
    void openCase(next.id);
    return;
  }
  resetForm(next);
}

async function closeTabsWithConfirm(tabKeys: string[]) {
  const targets = tabKeys.filter(Boolean);
  if (!targets.length) {
    return;
  }
  syncActiveTabSnapshot();

  const removeTabWithoutConfirm = (tabKey: string) => {
    const remaining = openedTabs.value.filter((item) => getTabKey(item) !== tabKey);
    delete modifiedTabs[tabKey];
    delete globalConfigExpandedMap[tabKey];
    openedTabs.value = remaining;
    tabContextMenu.visible = false;
    if (!remaining.length) {
      activeTabKey.value = "";
      activeStepKey.value = "";
      resetForm(createDraftCase(currentProjectId.value ?? 0, null));
      return;
    }
    if (activeTabKey.value === tabKey || !remaining.some((item) => getTabKey(item) === activeTabKey.value)) {
      focusTab(getTabKey(remaining[remaining.length - 1]));
    }
  };

  for (const tabKey of targets) {
    if (modifiedTabs[tabKey]) {
      try {
        await ElMessageBox.confirm(`标签页「${getTabTitle(openedTabs.value.find((item) => getTabKey(item) === tabKey) ?? form)}」有未保存的修改，请选择操作。`, "保存确认", {
          distinguishCancelAndClose: true,
          confirmButtonText: "保存",
          cancelButtonText: "忽略",
          type: "warning",
        });
        const target = openedTabs.value.find((item) => getTabKey(item) === tabKey);
        if (!target) {
          continue;
        }
        activeTabKey.value = tabKey;
        resetForm(target);
        const saved = await saveCase({ silent: true });
        if (!saved) {
          return;
        }
      } catch (action) {
        if (action !== "cancel") {
          return;
        }
      }
    }
    removeTabWithoutConfirm(tabKey);
  }
}

function closeCurrentTab() {
  void closeTabsWithConfirm(tabContextMenu.tabKey ? [tabContextMenu.tabKey] : []);
}

function closeOtherTabs() {
  const targets = openedTabs.value
    .map((item) => getTabKey(item))
    .filter((key) => key !== tabContextMenu.tabKey);
  void closeTabsWithConfirm(targets);
}

function closeAllTabs() {
  void closeTabsWithConfirm(openedTabs.value.map((item) => getTabKey(item)));
}

async function createFolder(parentId: number | null) {
  if (!currentProjectId.value) {
    ElMessage.warning("请先选择项目");
    return;
  }
  const { value } = await ElMessageBox.prompt("请输入目录名称", "新建用例目录", {
    inputPlaceholder: "例如：订单列表查询",
    confirmButtonText: "创建",
    cancelButtonText: "取消",
    inputValidator: (input) => Boolean(input.trim()) || "目录名称不能为空",
  });
  await post("/api/interface-auto/case-folders/", {
    project_id: currentProjectId.value,
    parent_id: parentId,
    name: value.trim(),
    sort_order: 0,
  });
  ElMessage.success("目录已创建");
  await loadWorkspace();
}

async function renameFolder(node: CaseNavNode | null) {
  if (!node?.folderId) {
    return;
  }
  const { value } = await ElMessageBox.prompt("请输入新的目录名称", "重命名目录", {
    inputValue: node.label,
    confirmButtonText: "保存",
    cancelButtonText: "取消",
    inputValidator: (input) => Boolean(input.trim()) || "目录名称不能为空",
  });
  await put(`/api/interface-auto/case-folders/${node.folderId}/`, {
    name: value.trim(),
    description: "",
  });
  ElMessage.success("目录已更新");
  await loadWorkspace();
}

async function deleteFolder(node: CaseNavNode | null) {
  if (!node?.folderId) {
    return;
  }
  await ElMessageBox.confirm("删除目录会同时删除目录内的测试用例，确认继续吗？", "删除目录", {
    confirmButtonText: "删除",
    cancelButtonText: "取消",
    type: "warning",
  });
  await del(`/api/interface-auto/case-folders/${node.folderId}/`);
  if (selectedCaseNodeId.value === node.id) {
    selectedCaseNodeId.value = "";
  }
  ElMessage.success("目录已删除");
  hideContextMenus();
  await loadWorkspace();
}

async function duplicateCase(caseItem?: TestCaseRecord) {
  if (!caseItem?.id) {
    return;
  }
  const detail = normalizeCase(await get<Partial<TestCaseRecord>>(`/api/interface-auto/cases/${caseItem.id}/`));
  const payload = buildCasePayload({
    ...detail,
    id: undefined,
    tabKey: createKey("draft"),
    name: createDuplicateCaseName(detail.name, detail.folder_id, detail.id),
    sort_order: getNextCaseSortOrder(detail.folder_id),
  });
  const result = await post<{ case_id: number }>("/api/interface-auto/cases/", payload);
  ElMessage.success("测试用例已复制");
  hideContextMenus();
  await loadWorkspace();
  await openCase(result.case_id);
}

async function deleteCase(caseItem?: TestCaseRecord) {
  if (!caseItem?.id) {
    return;
  }
  await ElMessageBox.confirm(`确认删除测试用例“${caseItem.name}”吗？`, "删除测试用例", {
    confirmButtonText: "删除",
    cancelButtonText: "取消",
    type: "warning",
  });
  await del(`/api/interface-auto/cases/${caseItem.id}/`);
  const relatedTab = openedTabs.value.find((item) => item.id === caseItem.id);
  if (relatedTab) {
    await closeTabsWithConfirm([getTabKey(relatedTab)]);
  }
  selectedCaseNodeId.value = "";
  ElMessage.success("测试用例已删除");
  hideContextMenus();
  await loadWorkspace();
}

function createDuplicateCaseName(baseName: string, folderId: number | null, excludeId?: number) {
  let index = 1;
  let nextName = `${baseName}-副本`;
  const exists = (name: string) =>
    cases.value.some(
      (item) =>
        item.id !== excludeId &&
        item.folder_id === folderId &&
        item.name.trim().toLowerCase() === name.trim().toLowerCase(),
    );
  while (exists(nextName)) {
    index += 1;
    nextName = `${baseName}-副本${index}`;
  }
  return nextName;
}

function buildCasePayload(caseItem: TestCaseRecord) {
  return {
    ...buildCaseMetaPayload(caseItem),
    steps: caseItem.steps.map((step, index) => ({
      id: step.id,
      api_template_id: step.api_template_id,
      step_order: index + 1,
      name: step.name ?? step.api_name ?? "未命名步骤",
      enabled: step.enabled ?? true,
      pre_processing: ensureToolMap(step, "pre_processing"),
      assertions: ensureToolMap(step, "assertions"),
      post_processing: ensureToolMap(step, "post_processing"),
      variables: parseMap(step.variables),
      enable_encryption: Boolean(step.enable_encryption),
      use_global_headers: step.use_global_headers !== false,
    })),
  };
}

function buildCaseMetaPayload(caseItem: TestCaseRecord) {
  return {
    project_id: caseItem.project_id,
    folder_id: caseItem.folder_id,
    name: caseItem.name.trim(),
    description: caseItem.description ?? "",
    environment_id: caseItem.environment_id,
    schema_version: caseItem.schema_version ?? 1,
    parameterize_config: normalizeParameterizeConfig(caseItem.parameterize_config),
    global_vars: parseMap(caseItem.global_vars),
    global_request_config: serializeGlobalRequestConfig(caseItem.global_request_config),
    output_variables: outputVariablesToPayload(caseItem.output_variables),
    enable_encryption: Boolean(caseItem.enable_encryption),
    encrypt_url: caseItem.encrypt_url ?? "",
    decrypt_url: caseItem.decrypt_url ?? "",
    sort_order: caseItem.sort_order ?? getNextCaseSortOrder(caseItem.folder_id),
  };
}

async function saveCase(options?: { silent?: boolean }) {
  if (!currentProjectId.value) {
    ElMessage.warning("请先选择项目");
    return null;
  }
  if (!activeTabKey.value) {
    ElMessage.warning("请先新建或打开测试用例");
    return null;
  }
  const name = form.name.trim();
  if (!name) {
    ElMessage.warning("请输入用例名称");
    return null;
  }
  const duplicate = cases.value.some(
    (item) =>
      item.id !== form.id &&
      item.folder_id === form.folder_id &&
      item.name.trim().toLowerCase() === name.toLowerCase(),
  );
  if (duplicate) {
    ElMessage.warning("目标同级目录下已存在同名测试用例");
    return null;
  }
  if (form.enable_encryption && (!form.encrypt_url.trim() || !form.decrypt_url.trim())) {
    ElMessage.warning("启用加解密功能必须配置加密URL和解密URL");
    return null;
  }
  if (form.global_request_config.login_request.use_global_encryption && !validateGlobalEncryptionForHttpTool()) {
    return null;
  }

  syncOutputVariablesFromText();
  if (!syncParameterizeConfigFromText({ silent: true })) {
    ElMessage.warning(parameterizeValidationMessage.value || "Invalid parameter data");
    return null;
  }
  saving.value = true;
  try {
    form.project_id = currentProjectId.value;
    form.sort_order = form.sort_order || getNextCaseSortOrder(form.folder_id);
    const payload = buildCasePayload(normalizeCase(form));
    const previousTabKey = activeTabKey.value;
    let caseId = form.id ?? null;
    if (form.id) {
      const result = await put<{ updated: boolean; case?: Partial<TestCaseRecord> }>(
        `/api/interface-auto/cases/${form.id}/`,
        payload,
      );
      caseId = result.case?.id ?? form.id;
    } else {
      const previousTabIndex = openedTabs.value.findIndex((item) => getTabKey(item) === previousTabKey);
      const result = await post<{ case_id: number }>("/api/interface-auto/cases/", payload);
      caseId = result.case_id;
      if (previousTabIndex !== -1) {
        openedTabs.value[previousTabIndex] = normalizeCase({
          ...deepClone(form),
          id: caseId,
          tabKey: previousTabKey,
        });
      } else {
        openedTabs.value = openedTabs.value.filter((item) => getTabKey(item) !== previousTabKey);
      }
      delete modifiedTabs[previousTabKey];
      delete globalConfigExpandedMap[previousTabKey];
    }
    if (!caseId) {
      return null;
    }
    const savedTabKey = previousTabKey || `case-${caseId}`;
    activeTabKey.value = savedTabKey;
    form.id = caseId;
    form.tabKey = savedTabKey;
    await loadWorkspace();
    await openCase(caseId);
    delete modifiedTabs[previousTabKey];
    modifiedTabs[savedTabKey] = false;
    if (!options?.silent) {
      ElMessage.success("测试用例已保存");
    }
    return caseId;
  } finally {
    saving.value = false;
  }
}

function triggerSaveCase() {
  void saveCase();
}

async function runCase() {
  if (running.value) {
    return;
  }
  let caseId = form.id ?? null;
  if (!caseId) {
    caseId = await saveCase({ silent: true });
  }
  if (!caseId) {
    return;
  }
  running.value = true;
  try {
    const result = await post<{
      case_name: string;
      message: string;
      steps: Array<{ step_order: number; step_name: string; status: string; message?: string }>;
      execution_log?: Record<string, unknown>;
    }>(`/api/interface-auto/cases/${caseId}/execute/`, buildCasePayload(normalizeCase(form)));
    executionLog.value = result.execution_log ?? null;
    logLines.value = [
      `用例：${result.case_name}`,
      result.message,
      ...result.steps.map((step) =>
        `step${step.step_order} ${step.step_name} - ${step.status}${step.message ? ` - ${step.message}` : ""}`,
      ),
    ];
    logDialogVisible.value = true;
  } finally {
    running.value = false;
  }
}

async function refreshWorkspace() {
  await loadWorkspace();
}

function createCaseFromSelection() {
  const selected = findCaseNodeById(caseTreeData.value, selectedCaseNodeId.value);
  const folderId = getCaseCreateFolderIdFromNode(selected);
  openDraftCase(folderId ?? null);
}

async function createCaseViaContext(node: CaseNavNode | null, blank = false) {
  const folderId = getCaseCreateFolderIdFromNode(node, blank);
  hideContextMenus();
  openDraftCase(folderId ?? null);
}

function onCaseTreeClick(node: CaseNavNode) {
  hideContextMenus();
  selectedCaseNodeId.value = node.id;
  if (node.type === "case" && node.caseItem?.id) {
    void openCase(node.caseItem.id);
  }
}

function onTemplateTreeClick(node: TreeNode) {
  selectedTemplateNodeId.value = node.id;
  templateTreeRef.value?.setCurrentKey?.(node.id);
}

function showCaseContextMenu(event: MouseEvent, node: CaseNavNode | null, blank = false) {
  event.preventDefault();
  caseContextMenu.visible = true;
  caseContextMenu.x = event.clientX;
  caseContextMenu.y = event.clientY;
  caseContextMenu.node = node;
  caseContextMenu.blank = blank;
}

function showTabContextMenu(event: MouseEvent, tabKey: string) {
  event.preventDefault();
  tabContextMenu.visible = true;
  tabContextMenu.x = event.clientX;
  tabContextMenu.y = event.clientY;
  tabContextMenu.tabKey = tabKey;
}

function hideContextMenus() {
  caseContextMenu.visible = false;
  tabContextMenu.visible = false;
}

function handleGlobalPointer() {
  hideContextMenus();
}

function handleSaveShortcut() {
  if (route.name !== "interface-auto-cases") {
    return;
  }
  void saveCase();
}

function handleCloseShortcut() {
  if (route.name !== "interface-auto-cases") {
    return;
  }
  if (activeTabKey.value) {
    void closeTabsWithConfirm([activeTabKey.value]);
  }
}

function handleProjectPathChange(value: number[]) {
  const [groupId, projectId] = value;
  context.setGroup(groupId ?? null);
  if (projectId !== undefined) {
    context.setProject(projectId);
    return;
  }
  context.setProject(null);
}

function allowCaseDrop(draggingNode: CaseTreeNodeInstance, dropNode: CaseTreeNodeInstance, dropType: "prev" | "inner" | "next") {
  const draggedCase = draggingNode.data.caseItem;
  if (draggingNode.data.type !== "case" || !draggedCase) {
    return false;
  }
  if (dropType === "inner") {
    return dropNode.data.type === "folder" && Boolean(dropNode.data.folderId);
  }
  return dropNode.data.type === "case" || dropNode.data.type === "folder";
}

function allowCaseDrag(node: CaseTreeNodeInstance) {
  return node.data.type === "case";
}

function getCaseDropTargetFolderId(dropNode: CaseTreeNodeInstance, dropType: CaseDropType) {
  if (dropType === "inner") {
    return dropNode.data.type === "folder" ? dropNode.data.folderId ?? null : null;
  }
  if (dropNode.data.type === "folder") {
    return dropNode.data.parentFolderId ?? null;
  }
  return dropNode.data.caseItem?.folder_id ?? null;
}

function getDroppedSiblingCaseIds(dropNode: CaseTreeNodeInstance, dropType: CaseDropType) {
  const siblingNodes = dropType === "inner" ? dropNode.childNodes ?? [] : dropNode.parent?.childNodes ?? [];
  return siblingNodes
    .filter((node) => node.data.type === "case" && node.data.caseItem?.id)
    .map((node) => node.data.caseItem!.id!);
}

function hasSameLevelCaseName(caseItem: TestCaseRecord, targetFolderId: number | null) {
  const targetName = caseItem.name.trim().toLowerCase();
  return cases.value.some(
    (item) =>
      item.id !== caseItem.id &&
      item.project_id === caseItem.project_id &&
      item.folder_id === targetFolderId &&
      item.name.trim().toLowerCase() === targetName,
  );
}

function buildDroppedCaseOrder(
  draggedCase: TestCaseRecord,
  targetFolderId: number | null,
  dropNode: CaseTreeNodeInstance,
  dropType: CaseDropType,
) {
  const movedCase = normalizeCase({ ...draggedCase, folder_id: targetFolderId });
  const existingCases = cases.value
    .filter((item) => item.folder_id === targetFolderId && item.id !== draggedCase.id)
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  const caseMap = new Map<number, TestCaseRecord>();
  [...existingCases, movedCase].forEach((item) => {
    if (item.id) {
      caseMap.set(item.id, item);
    }
  });

  const droppedIds = getDroppedSiblingCaseIds(dropNode, dropType);
  if (draggedCase.id && droppedIds.includes(draggedCase.id)) {
    const ordered = droppedIds.map((id) => caseMap.get(id)).filter((item): item is TestCaseRecord => Boolean(item));
    const missing = [...caseMap.values()].filter((item) => !ordered.some((orderedItem) => orderedItem.id === item.id));
    return [...ordered, ...missing];
  }

  if (dropType !== "inner" && dropNode.data.caseItem?.id) {
    const targetIndex = existingCases.findIndex((item) => item.id === dropNode.data.caseItem?.id);
    existingCases.splice(targetIndex === -1 ? existingCases.length : targetIndex + (dropType === "after" ? 1 : 0), 0, movedCase);
    return existingCases;
  }
  if (dropType !== "inner" && dropNode.data.type === "folder" && dropType === "before") {
    return [movedCase, ...existingCases];
  }
  return [...existingCases, movedCase];
}

async function persistCaseOrder(folderId: number | null, orderedCases: TestCaseRecord[]) {
  await Promise.all(
    orderedCases.map((item, index) => {
      if (!item.id) {
        return Promise.resolve();
      }
      const nextCase = normalizeCase({ ...item, folder_id: folderId, sort_order: index + 1 });
      return put(`/api/interface-auto/cases/${item.id}/`, buildCaseMetaPayload(nextCase));
    }),
  );
}

async function onCaseTreeDrop(draggingNode: CaseTreeNodeInstance, dropNode: CaseTreeNodeInstance, dropType: CaseDropType) {
  const draggedCase = draggingNode.data.caseItem;
  if (!draggedCase?.id) {
    await loadWorkspace();
    return;
  }

  const sourceFolderId = draggedCase.folder_id ?? null;
  const targetFolderId = getCaseDropTargetFolderId(dropNode, dropType);
  if (dropType === "inner" && targetFolderId === null) {
    await loadWorkspace();
    return;
  }

  if (hasSameLevelCaseName(draggedCase, targetFolderId)) {
    ElMessage.warning("目标同级目录下已存在同名测试用例");
    await loadWorkspace();
    return;
  }

  const targetOrderedCases = buildDroppedCaseOrder(draggedCase, targetFolderId, dropNode, dropType);
  await persistCaseOrder(targetFolderId, targetOrderedCases);
  if (sourceFolderId !== targetFolderId) {
    const sourceOrderedCases = cases.value
      .filter((item) => item.folder_id === sourceFolderId && item.id !== draggedCase.id)
      .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    await persistCaseOrder(sourceFolderId, sourceOrderedCases);
  }

  if (form.id === draggedCase.id) {
    form.folder_id = targetFolderId;
    form.sort_order = targetOrderedCases.findIndex((item) => item.id === draggedCase.id) + 1;
  }
  openedTabs.value = openedTabs.value.map((item) =>
    item.id === draggedCase.id
      ? normalizeCase({
          ...item,
          folder_id: targetFolderId,
          sort_order: targetOrderedCases.findIndex((caseItem) => caseItem.id === draggedCase.id) + 1,
        })
      : item,
  );
  await loadWorkspace();
  selectedCaseNodeId.value = `case-${draggedCase.id}`;
}

function onTemplateDragStart(node: TreeNode) {
  draggedTemplateId.value = node.template?.id ?? null;
  selectedTemplateNodeId.value = node.id;
}

function onTemplateDragEnd() {
  draggedTemplateId.value = null;
}

function createStepFromTemplate(template: ApiTemplate): CaseStep {
  return normalizeStep({
    api_template_id: template.id ?? null,
    step_order: form.steps.length + 1,
    name: template.name,
    enabled: true,
    pre_processing: {},
    assertions: {},
    post_processing: {},
    variables: {},
    enable_encryption: false,
    use_global_headers: form.global_request_config.header_config.enabled,
    api_name: template.name,
    api_method: template.method,
    api_url_path: template.url_path,
    api_folder_id: template.folder_id ?? null,
    api_project_id: template.project_id,
    api_description: template.description,
  });
}

function reindexSteps() {
  form.steps.forEach((step, index) => {
    step.step_order = index + 1;
  });
}

function selectStep(step: CaseStep) {
  activeStepKey.value = getStepKey(step);
}

function addTemplateToActiveCase(template?: ApiTemplate, insertAfterStepKey?: string) {
  if (!template) {
    return;
  }
  if (!activeTabKey.value) {
    ElMessage.warning("请先在左侧新建或打开测试用例");
    return;
  }
  const newStep = createStepFromTemplate(template);
  const insertIndex =
    insertAfterStepKey === undefined
      ? form.steps.length
      : Math.max(
          0,
          form.steps.findIndex((item) => getStepKey(item) === insertAfterStepKey) + 1,
        );
  form.steps.splice(insertIndex, 0, newStep);
  reindexSteps();
  selectStep(newStep);
  markActiveModified();
}

function appendDroppedTemplate() {
  if (!draggedTemplateId.value) {
    return;
  }
  const template = templates.value.find((item) => item.id === draggedTemplateId.value);
  addTemplateToActiveCase(template);
  draggedTemplateId.value = null;
}

function handleStepCardDrop(step: CaseStep) {
  if (draggedTemplateId.value) {
    const template = templates.value.find((item) => item.id === draggedTemplateId.value);
    addTemplateToActiveCase(template, getStepKey(step));
    draggedTemplateId.value = null;
    return;
  }
  if (!draggedStepKey.value) {
    return;
  }
  const sourceIndex = form.steps.findIndex((item) => getStepKey(item) === draggedStepKey.value);
  const targetIndex = form.steps.findIndex((item) => getStepKey(item) === getStepKey(step));
  if (sourceIndex === -1 || targetIndex === -1 || sourceIndex === targetIndex) {
    draggedStepKey.value = "";
    dragOverStepKey.value = "";
    return;
  }
  const [moved] = form.steps.splice(sourceIndex, 1);
  const nextIndex = sourceIndex < targetIndex ? targetIndex - 1 : targetIndex;
  form.steps.splice(nextIndex, 0, moved);
  reindexSteps();
  draggedStepKey.value = "";
  dragOverStepKey.value = "";
  markActiveModified();
}

function onStepDragStart(step: CaseStep) {
  draggedStepKey.value = getStepKey(step);
}

function onStepDragOver(step: CaseStep) {
  dragOverStepKey.value = getStepKey(step);
}

function onStepDragEnd() {
  draggedStepKey.value = "";
  dragOverStepKey.value = "";
}

function deleteStep(step: CaseStep) {
  const index = form.steps.findIndex((item) => getStepKey(item) === getStepKey(step));
  if (index === -1) {
    return;
  }
  form.steps.splice(index, 1);
  reindexSteps();
  if (activeStepKey.value === getStepKey(step)) {
    activeStepKey.value = form.steps[0] ? getStepKey(form.steps[0]) : "";
  }
  markActiveModified();
}

function duplicateStep(step: CaseStep) {
  const index = form.steps.findIndex((item) => getStepKey(item) === getStepKey(step));
  if (index === -1) {
    return;
  }
  const clone = normalizeStep({
    ...deepClone(step),
    id: undefined,
    case_id: undefined,
    stepKey: createKey("step"),
  });
  form.steps.splice(index + 1, 0, clone);
  reindexSteps();
  selectStep(clone);
  markActiveModified();
}

function toggleStepEnabled(step: CaseStep) {
  step.enabled = !step.enabled;
  markActiveModified();
}

function syncAllStepEncryptionStatus(enabled: boolean) {
  form.steps.forEach((item) => {
    item.enable_encryption = enabled;
  });
}

function syncAllStepGlobalHeadersStatus(enabled: boolean) {
  form.steps.forEach((item) => {
    item.use_global_headers = enabled;
  });
}

function handleGlobalEncryptionChange(event: Event) {
  const checked = (event.target as HTMLInputElement).checked;
  form.enable_encryption = checked;
  if (!checked) {
    form.global_request_config.login_request.use_global_encryption = false;
    if (toolDialogVisible.value && toolDialogKind.value === "http_request") {
      toolForm.useGlobalEncryption = false;
    }
  }
  syncAllStepEncryptionStatus(checked);
  markActiveModified();
}

function handleGlobalHeaderConfigChange(event: Event) {
  const checked = (event.target as HTMLInputElement).checked;
  form.global_request_config.header_config.enabled = checked;
  syncAllStepGlobalHeadersStatus(checked);
  markActiveModified();
}

function toggleStepEncryption(step: CaseStep) {
  const nextState = !step.enable_encryption;
  if (nextState && !form.enable_encryption) {
    ElMessage.warning("启用失败，全局加解密配置未启用");
    return;
  }
  step.enable_encryption = nextState;
  markActiveModified();
}

function isStepGlobalHeadersEnabled(step: CaseStep) {
  return Boolean(form.global_request_config.header_config.enabled) && step.use_global_headers !== false;
}

function toggleStepGlobalHeaders(step: CaseStep) {
  const nextState = !isStepGlobalHeadersEnabled(step);
  if (nextState && !form.global_request_config.header_config.enabled) {
    ElMessage.warning("全局请求头未启用，请先启用");
    return;
  }
  step.use_global_headers = nextState;
  markActiveModified();
}

async function focusTemplateFromStep(step: CaseStep) {
  if (!step.api_template_id) {
    return;
  }
  selectedTemplateNodeId.value = `template-${step.api_template_id}`;
  nextTick(() => {
    templateTreeRef.value?.setCurrentKey?.(selectedTemplateNodeId.value);
  });
  await router.push({
    name: "interface-auto-templates",
    query: {
      openTemplateId: String(step.api_template_id),
    },
  });
}


function addToolToStep(step: CaseStep, tab: ToolTabKey, toolType: string) {
  openNewToolDialog(step, tab, toolType);
}

function handleToolCommand(step: CaseStep, command: string | number | object) {
  const tab = getStepTab(step);
  if (typeof command === "object" && command !== null) {
    const payload = command as { kind?: string; toolId?: number | string };
    if (payload.kind === "global_tool") {
      const tool = enabledGlobalTools.value.find((item) => String(item.id) === String(payload.toolId));
      if (!tool) {
        ElMessage.warning("全局工具不存在或未启用");
        return;
      }
      addGlobalToolToStep(step, tab, tool);
      return;
    }
  }
  if (tab === "assertions") {
    addToolToStep(step, tab, "assertion");
    return;
  }
  if (String(command) === "global_tool") {
    return;
  }
  addToolToStep(step, tab, String(command));
}

function copyTool(step: CaseStep, tab: ToolTabKey, toolId: string) {
  const map = ensureToolMap(step, tab);
  const source = map[toolId];
  if (!source) {
    return;
  }
  const cloneId = createKey(source.tool_type ?? "tool");
  map[cloneId] = {
    ...deepClone(source),
    id: cloneId,
    name: `${source.name ?? "工具"} 副本`,
    priority: getNextToolPriority(map),
  };
  markActiveModified();
}

function removeTool(step: CaseStep, tab: ToolTabKey, toolId: string) {
  const map = ensureToolMap(step, tab);
  delete map[toolId];
  updateToolPriorities(map);
  markActiveModified();
}

function resetToolDragState() {
  draggedToolStepKey.value = "";
  draggedToolTabKey.value = "";
  draggedToolId.value = "";
  dragOverToolId.value = "";
}

function onToolDragStart(step: CaseStep, tab: ToolTabKey, toolId: string) {
  draggedToolStepKey.value = getStepKey(step);
  draggedToolTabKey.value = tab;
  draggedToolId.value = toolId;
  dragOverToolId.value = toolId;
}

function onToolDragOver(step: CaseStep, tab: ToolTabKey, toolId: string) {
  if (draggedToolStepKey.value !== getStepKey(step) || draggedToolTabKey.value !== tab) {
    return;
  }
  dragOverToolId.value = toolId;
}

function onToolDrop(step: CaseStep, tab: ToolTabKey, targetToolId: string) {
  if (
    !draggedToolId.value ||
    draggedToolId.value === targetToolId ||
    draggedToolStepKey.value !== getStepKey(step) ||
    draggedToolTabKey.value !== tab
  ) {
    resetToolDragState();
    return;
  }
  const entries = getToolEntries(step, tab);
  const orderedToolIds = entries.map((entry) => entry.toolId);
  const sourceIndex = orderedToolIds.indexOf(draggedToolId.value);
  const targetIndex = orderedToolIds.indexOf(targetToolId);
  if (sourceIndex === -1 || targetIndex === -1) {
    resetToolDragState();
    return;
  }
  const [movedToolId] = orderedToolIds.splice(sourceIndex, 1);
  orderedToolIds.splice(targetIndex, 0, movedToolId);
  const map = ensureToolMap(step, tab);
  orderedToolIds.forEach((toolId, index) => {
    if (map[toolId]) {
      map[toolId].priority = index + 1;
    }
  });
  markActiveModified();
  resetToolDragState();
}

function onToolDragEnd() {
  resetToolDragState();
}

function addVariableRow() {
  variableRows.value.unshift(createVariableRow());
}

async function loadVariableRows() {
  variableRows.value = mapToVariableRows(form.global_vars);
}

async function saveVariableRow(row: VariableRow) {
  if (!row.name.trim()) {
    ElMessage.warning("Variable name is required");
    return;
  }
  form.global_vars = variableRowsToMap(variableRows.value);
  ElMessage.success("Case variables updated");
}

async function deleteVariableRow(row: VariableRow) {
  variableRows.value = variableRows.value.filter((item) => item.rowKey !== row.rowKey);
  if (!variableRows.value.length) {
    variableRows.value = [createVariableRow()];
  }
  form.global_vars = variableRowsToMap(variableRows.value);
}

function removeVariableRow(index: number) {
  variableRows.value.splice(index, 1);
  if (!variableRows.value.length) {
    variableRows.value = [createVariableRow()];
  }
  form.global_vars = variableRowsToMap(variableRows.value);
}

function toggleGlobalConfigPanel() {
  globalConfigExpanded.value = !globalConfigExpanded.value;
}

function addLoginHeaderRow() {
  form.global_request_config.login_request.headers_rows.push(createHeaderRow());
}

function removeLoginHeaderRow(index: number) {
  form.global_request_config.login_request.headers_rows.splice(index, 1);
  if (!form.global_request_config.login_request.headers_rows.length) {
    form.global_request_config.login_request.headers_rows.push(createHeaderRow());
  }
}

function addLoginExtractionRow() {
  form.global_request_config.login_request.extractions.push(createExtractionRow());
}

function removeLoginExtractionRow(index: number) {
  form.global_request_config.login_request.extractions.splice(index, 1);
  if (!form.global_request_config.login_request.extractions.length) {
    form.global_request_config.login_request.extractions.push(createExtractionRow());
  }
}

function addGlobalHeaderConfigRow() {
  form.global_request_config.header_config.headers_rows.push(createHeaderRow());
}

function removeGlobalHeaderConfigRow(index: number) {
  form.global_request_config.header_config.headers_rows.splice(index, 1);
  if (!form.global_request_config.header_config.headers_rows.length) {
    form.global_request_config.header_config.headers_rows.push(createHeaderRow());
  }
}

function addOutputVariableRowToCase() {
  form.output_variables.push(createOutputVariableRow());
}

function removeOutputVariableRowFromCase(index: number) {
  form.output_variables.splice(index, 1);
}

watch(currentProjectId, () => {
  syncProjectPath();
  openedTabs.value = [];
  activeTabKey.value = "";
  activeStepKey.value = "";
  selectedCaseNodeId.value = "";
  selectedTemplateNodeId.value = "";
  void loadWorkspace();
});

watch(
  form,
  () => {
    markActiveModified();
  },
  { deep: true },
);

onMounted(async () => {
  window.addEventListener("click", handleGlobalPointer);
  window.addEventListener("contextmenu", handleGlobalPointer);
  window.addEventListener("interface-auto:save-cases", handleSaveShortcut as EventListener);
  window.addEventListener("interface-auto:close-case-tab", handleCloseShortcut as EventListener);
  await context.ensureLoaded();
  if (!context.selectedProject.value && context.projects.value.length) {
    context.setProject(context.projects.value[0].id);
  }
  syncProjectPath();
  await loadWorkspace();
});

onBeforeUnmount(() => {
  window.removeEventListener("click", handleGlobalPointer);
  window.removeEventListener("contextmenu", handleGlobalPointer);
  window.removeEventListener("interface-auto:save-cases", handleSaveShortcut as EventListener);
  window.removeEventListener("interface-auto:close-case-tab", handleCloseShortcut as EventListener);
});
</script>

<template>
  <div ref="pageRootRef" class="interface-auto-desktop case-desktop" v-loading="loading" @click="hideContextMenus">
    <div class="case-workbench">
      <section class="pane pane-left" @contextmenu.prevent="showCaseContextMenu($event, null, true)">
        <div class="project-toolbar">
          <span class="toolbar-label">项目：</span>
          <el-cascader
            v-model="projectPath"
            :options="projectOptions"
            :props="cascaderProps"
            size="small"
            class="project-cascader"
            placeholder="选择业务 / 项目"
            :show-all-levels="true"
            @change="handleProjectPathChange"
          />
          <button class="icon-button" title="新建目录" @click.stop="createFolder(null)">
            <el-icon><FolderAdd /></el-icon>
          </button>
          <button
            class="icon-button"
            :class="{ disabled: !currentFolder }"
            title="删除目录"
            :disabled="!currentFolder"
            @click.stop="deleteFolder(findCaseNodeById(caseTreeData, selectedCaseNodeId))"
          >
            <el-icon><Delete /></el-icon>
          </button>
          <button class="icon-button" title="刷新" @click.stop="refreshWorkspace">
            <el-icon><RefreshRight /></el-icon>
          </button>
          <button class="icon-button" title="新建测试用例" @click.stop="createCaseFromSelection">
            +
          </button>
        </div>

        <div class="search-line">
          <el-icon><Search /></el-icon>
          <input v-model="caseKeyword" class="search-input" placeholder="搜索测试用例名称..." />
        </div>

        <el-tree
          ref="caseTreeRef"
          class="case-tree"
          node-key="id"
          :data="caseTreeData"
          :props="{ label: 'label', children: 'children' }"
          highlight-current
          default-expand-all
          draggable
          :allow-drag="allowCaseDrag"
          :allow-drop="allowCaseDrop"
          @node-click="onCaseTreeClick"
          @node-drop="onCaseTreeDrop"
        >
          <template #default="{ data }">
            <span class="tree-node" :class="data.type" @contextmenu.stop.prevent="showCaseContextMenu($event, data)">
              <el-icon v-if="data.type === 'folder'" class="tree-folder-icon"><Folder /></el-icon>
              <span v-else class="case-badge">CASE</span>
              <span class="tree-label">{{ data.label }}</span>
            </span>
          </template>
        </el-tree>

        <div v-if="!caseTreeData.length" class="pane-empty">No Data</div>
      </section>

      <section class="pane pane-middle">
        <div class="project-toolbar pane-heading">
          <span class="pane-heading-text">接口模板</span>
        </div>

        <div class="search-line">
          <el-icon><Search /></el-icon>
          <input v-model="templateKeyword" class="search-input" placeholder="搜索接口模板名称..." />
        </div>

        <el-tree
          ref="templateTreeRef"
          class="template-tree"
          node-key="id"
          :data="templateTreeData"
          :props="{ label: 'label', children: 'children' }"
          highlight-current
          default-expand-all
          @node-click="onTemplateTreeClick"
        >
          <template #default="{ data }">
            <span
              class="tree-node template"
              :class="{ 'is-template': data.type === 'template' }"
              :draggable="Boolean(data.template)"
              @dragstart.stop="onTemplateDragStart(data)"
              @dragend.stop="onTemplateDragEnd"
              @dblclick.stop="data.template && addTemplateToActiveCase(data.template)"
            >
              <template v-if="data.type === 'template'">
                <b class="method-badge" :class="getTemplateMethodClass(data.method || 'GET')">{{ data.method }}</b>
                <span class="tree-label">{{ data.label }}</span>
              </template>
              <template v-else>
                <el-icon class="tree-folder-icon"><Folder /></el-icon>
                <span class="tree-label">{{ data.label }}</span>
              </template>
            </span>
          </template>
        </el-tree>
      </section>

      <section class="pane pane-right">
        <div class="opened-tabs" @contextmenu.prevent>
          <el-tag
            v-for="item in openedTabs"
            :key="getTabKey(item)"
            closable
            type="primary"
            :effect="activeTabKey === getTabKey(item) ? 'light' : 'plain'"
            class="open-tag case-open-tag"
            :class="{ inactive: activeTabKey !== getTabKey(item), modified: modifiedTabs[getTabKey(item)] }"
            @click="focusTab(getTabKey(item))"
            @close="closeTabsWithConfirm([getTabKey(item)])"
            @contextmenu.stop.prevent="showTabContextMenu($event, getTabKey(item))"
          >
            {{ getTabTitle(item) }}
          </el-tag>
        </div>

        <div v-if="openedTabs.length" class="editor-shell">
          <div class="editor-header">
            <div class="header-row header-row-main">
              <div class="header-field header-field-name">
                <span class="header-label">名称:</span>
                <input v-model="form.name" class="text-field" placeholder="请输入用例名称" />
              </div>
              <div class="header-field header-field-desc">
                <span class="header-label">描述:</span>
                <input v-model="form.description" class="text-field" placeholder="请输入用例描述" />
              </div>
            </div>

            <div class="header-row">
              <div class="header-field header-field-env">
                <span class="header-label">环境:</span>
                <el-select v-model="form.environment_id" class="env-select" size="small" placeholder="不使用环境" clearable>
                  <el-option label="不使用环境" :value="null" />
                  <el-option v-for="item in environments" :key="item.id" :label="item.name" :value="item.id" />
                </el-select>
              </div>
            </div>
            <div class="header-row actions-row">
              <button class="action-icon legacy-icon" :disabled="running" @click="runCase">
                <img
                  class="toolbar-action-image"
                  :src="running ? stopingToolIcon : runningToolIcon"
                  :alt="running ? 'Running' : 'Run Case'"
                />
              </button>
              <button class="action-icon legacy-icon" @click="logDialogVisible = true">
                <img class="toolbar-action-image" :src="logToolIcon" alt="View Logs" />
              </button>
              <button class="action-button solid compact" :disabled="saving" @click="triggerSaveCase">Save</button>
            </div>

            <div class="global-config-shell">
              <button class="global-config-toggle" type="button" @click="toggleGlobalConfigPanel">
                <span>全局配置</span>
                <span class="global-config-toggle-icon" :class="{ expanded: globalConfigExpanded }">
                  <el-icon><ArrowRight /></el-icon>
                </span>
              </button>

              <div v-if="globalConfigExpanded" class="global-config-panel">
                <div class="global-config-tabs" role="tablist" aria-label="Global configuration tabs">
                  <button
                    class="global-config-tab"
                    :class="{ active: activeGlobalConfigTab === 'encryption' }"
                    type="button"
                    @click="activeGlobalConfigTab = 'encryption'"
                  >
                    加解密
                  </button>
                  <button
                    class="global-config-tab"
                    :class="{ active: activeGlobalConfigTab === 'variables' }"
                    type="button"
                    @click="activeGlobalConfigTab = 'variables'"
                  >
                    全局变量
                  </button>
                  <button
                    class="global-config-tab"
                    :class="{ active: activeGlobalConfigTab === 'login_headers' }"
                    type="button"
                    @click="activeGlobalConfigTab = 'login_headers'"
                  >
                    全局请求头
                  </button>
                  <button
                    class="global-config-tab"
                    :class="{ active: activeGlobalConfigTab === 'parameterize' }"
                    type="button"
                    @click="activeGlobalConfigTab = 'parameterize'"
                  >
                    参数化
                  </button>
                  <button
                    class="global-config-tab"
                    :class="{ active: activeGlobalConfigTab === 'outputs' }"
                    type="button"
                    @click="activeGlobalConfigTab = 'outputs'"
                  >
                    出参
                  </button>
                </div>

                <div class="global-config-content">
                  <div v-if="activeGlobalConfigTab === 'encryption'" class="global-config-tab-panel">
                    <label class="encryption-check">
                      <input :checked="form.enable_encryption" type="checkbox" @change="handleGlobalEncryptionChange" />
                      <span>启用加解密</span>
                    </label>
                    <div v-if="form.enable_encryption" class="global-config-inline-grid two-columns">
                      <div class="global-config-inline-field">
                        <span class="global-config-inline-label">加密URL</span>
                        <input v-model="form.encrypt_url" class="text-field" placeholder="请输入加密URL" />
                      </div>
                      <div class="global-config-inline-field">
                        <span class="global-config-inline-label">解密URL</span>
                        <input v-model="form.decrypt_url" class="text-field" placeholder="请输入解密URL" />
                      </div>
                    </div>
                  </div>

                  <div v-else-if="activeGlobalConfigTab === 'variables'" class="global-config-tab-panel">
                    <div v-if="form.environment_id && currentEnvironmentName" class="global-variable-caption">
                      当前环境：{{ currentEnvironmentName }}
                    </div>
                    <div v-if="visibleGlobalVariables.length" class="global-variable-view">
                      <div
                        v-for="row in visibleGlobalVariables"
                        :key="row.id"
                        class="global-variable-item"
                      >
                        <span class="global-variable-name">{{ row.name }}</span>
                        <span class="global-variable-value">{{ row.value }}</span>
                        <span class="global-variable-type">{{ row.variable_type || "string" }}</span>
                      </div>
                    </div>
                    <div v-else-if="!form.environment_id" class="global-config-empty">请先选择环境后查看全局变量。</div>
                    <div v-else class="global-config-empty">当前项目 / 环境下暂无全局变量，请在变量管理中配置。</div>
                  </div>

                  <div v-else-if="activeGlobalConfigTab === 'login_headers'" class="global-config-tab-panel global-config-stack">
                    <div class="global-config-section-card">
                      <div class="global-config-toolbar align-left">
                        <label class="encryption-check compact-check">
                          <input v-model="form.global_request_config.login_request.enabled" type="checkbox" />
                          <span class="global-config-section-title">登录态获取</span>
                        </label>
                      </div>
                      <div v-if="form.global_request_config.login_request.enabled" class="global-config-section-panel">
                        <div class="global-config-stack">
                          <div class="global-config-inline-grid method-url-grid">
                            <div class="global-config-inline-field compact-inline-field">
                              <span class="global-config-inline-label">请求方式</span>
                              <el-select v-model="form.global_request_config.login_request.method" class="env-select" size="small">
                                <el-option v-for="method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']" :key="method" :label="method" :value="method" />
                              </el-select>
                            </div>
                            <div class="global-config-inline-field">
                              <span class="global-config-inline-label">URL</span>
                              <input v-model="form.global_request_config.login_request.url" class="text-field" placeholder="请输入登录URL" />
                            </div>
                          </div>

                          <div class="global-config-inline-field">
                            <span class="global-config-inline-label">加解密</span>
                            <label class="encryption-check compact-check">
                              <input
                                v-model="form.global_request_config.login_request.use_global_encryption"
                                type="checkbox"
                                @change="handleLoginGlobalEncryptionChange"
                              />
                              <span>使用全局加解密</span>
                            </label>
                          </div>

                          <div class="global-config-inline-field body-inline-field config-list-inline-field">
                            <span class="global-config-inline-label body-label">请求头</span>
                            <div class="global-config-list-content">
                              <div
                                v-for="(row, index) in form.global_request_config.login_request.headers_rows"
                                :key="row.rowKey || `login-header-${index}`"
                                class="global-config-kv-row"
                              >
                                <input v-model="row.key" class="tool-input config-input" placeholder="Header Name" />
                                <input v-model="row.value" class="tool-input config-input" placeholder="Header Value" />
                                <div class="global-config-row-actions">
                                  <button class="row-icon add" type="button" @click="addLoginHeaderRow">+</button>
                                  <button class="row-icon remove" type="button" @click="removeLoginHeaderRow(index)">-</button>
                                </div>
                              </div>
                            </div>
                          </div>

                          <div class="global-config-inline-field body-inline-field">
                            <span class="global-config-inline-label body-label">请求体</span>
                            <el-input v-model="form.global_request_config.login_request.body_text" type="textarea" :rows="4" resize="none" />
                          </div>

                          <div class="global-config-inline-field body-inline-field config-list-inline-field">
                            <span class="global-config-inline-label body-label">参数提取</span>
                            <div class="global-config-list-content">
                              <div
                                v-for="(row, index) in form.global_request_config.login_request.extractions"
                                :key="row.rowKey || `login-extract-${index}`"
                                class="global-config-kv-row"
                              >
                                <input v-model="row.variable" class="tool-input config-input" placeholder="token" />
                                <input v-model="row.path" class="tool-input config-input" placeholder="headers.Authorization or body.data.token" />
                                <div class="global-config-row-actions">
                                  <button class="row-icon add" type="button" @click="addLoginExtractionRow">+</button>
                                  <button class="row-icon remove" type="button" @click="removeLoginExtractionRow(index)">-</button>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div class="global-config-section-card">
                      <div class="global-config-toolbar align-left">
                        <label class="encryption-check compact-check">
                          <input
                            :checked="form.global_request_config.header_config.enabled"
                            type="checkbox"
                            @change="handleGlobalHeaderConfigChange"
                          />
                          <span class="global-config-section-title">全局请求头</span>
                        </label>
                      </div>
                      <div v-if="form.global_request_config.header_config.enabled" class="global-config-section-panel">
                        <div class="global-config-stack">
                          <div
                            v-for="(row, index) in form.global_request_config.header_config.headers_rows"
                            :key="row.rowKey || `global-header-${index}`"
                            class="global-config-kv-row"
                          >
                            <input v-model="row.key" class="tool-input config-input" placeholder="Header Name" />
                            <input v-model="row.value" class="tool-input config-input" placeholder="可引用变量 例：${token}" />
                            <div class="global-config-row-actions">
                              <button class="row-icon add" type="button" @click="addGlobalHeaderConfigRow">+</button>
                              <button class="row-icon remove" type="button" @click="removeGlobalHeaderConfigRow(index)">-</button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div v-else-if="activeGlobalConfigTab === 'parameterize'" class="global-config-tab-panel global-config-stack">
                    <div class="global-config-section-card">
                      <div class="global-config-toolbar align-left">
                        <label class="encryption-check compact-check">
                          <input
                            :checked="parameterizeConfig.enabled"
                            type="checkbox"
                            @change="setParameterizeEnabled"
                          />
                          <span class="global-config-section-title">参数化</span>
                        </label>
                      </div>
                      <div class="global-config-section-panel parameterize-panel">
                        <div class="global-config-inline-grid two-columns parameterize-toolbar">
                          <div class="global-config-inline-field compact-inline-field">
                            <span class="global-config-inline-label">来源</span>
                            <el-select
                              :model-value="parameterizeConfig.source_type"
                              class="env-select"
                              size="small"
                              @update:model-value="setParameterizeSourceType"
                            >
                              <el-option label="Inline JSON" value="inline_json" />
                              <el-option label="CSV Text" value="csv_text" />
                            </el-select>
                          </div>
                          <div class="global-config-inline-field compact-inline-field">
                            <button class="action-button compact" type="button" @click="syncParameterizeConfigFromText()">
                              校验数据
                            </button>
                            <span
                              v-if="parameterizeValidationMessage"
                              class="parameterize-validation"
                              :class="{ ok: parameterizeValidationMessage === 'OK' }"
                            >
                              {{ parameterizeValidationMessage }}
                            </span>
                          </div>
                        </div>
                        <el-input
                          v-model="parameterizeText"
                          class="parameterize-editor"
                          type="textarea"
                          :rows="8"
                          resize="none"
                          @input="handleParameterizeTextInput"
                        />
                      </div>
                    </div>
                  </div>

                  <div v-else class="global-config-tab-panel">
                    <div class="global-output-config">
                      <span class="global-config-inline-label">用例变量输出</span>
                      <input
                        v-model="outputVariableText"
                        class="text-field global-output-input"
                        placeholder="例如：token,userId,orderNo"
                        @input="syncOutputVariablesFromText"
                      />
                    </div>
                    <div class="global-config-hint">多个变量使用英文逗号隔开；执行完成后会从变量池取同名变量作为用例出参，供后续测试用例使用。</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="steps-board" @dragover.prevent @drop.prevent="appendDroppedTemplate">
            <div v-if="form.steps.length" class="steps-scroller">
              <article
                v-for="step in form.steps"
                :key="getStepKey(step)"
                class="step-card"
                :class="{
                  active: activeStepKey === getStepKey(step),
                  disabled: !step.enabled,
                  dragover: dragOverStepKey === getStepKey(step),
                }"
                draggable="true"
                @click="selectStep(step)"
                @dragstart="onStepDragStart(step)"
                @dragover.prevent="onStepDragOver(step)"
                @drop.prevent="handleStepCardDrop(step)"
                @dragend="onStepDragEnd"
              >
                <div class="step-card-header">
                  <span class="step-title">step{{ step.step_order }}</span>
                  <div class="step-header-actions">
                    <el-tooltip
                      :content="step.enable_encryption ? '使用全局加解密' : '未使用全局加解密'"
                      placement="top"
                      popper-class="qm-app-tooltip"
                      :show-after="180"
                    >
                      <button
                        class="step-icon"
                        :class="{ muted: !step.enable_encryption }"
                        @click.stop="toggleStepEncryption(step)"
                      >
                        <img
                          class="step-icon-image"
                          :src="lockToolIcon"
                          :alt="step.enable_encryption ? '已启用加解密' : '未启用加解密'"
                        />
                      </button>
                    </el-tooltip>
                    <el-tooltip
                      :content="isStepGlobalHeadersEnabled(step) ? '使用全局请求头' : '未使用全局请求头'"
                      placement="top"
                      popper-class="qm-app-tooltip"
                      :show-after="180"
                    >
                      <button
                        class="step-icon"
                        :class="{ muted: !isStepGlobalHeadersEnabled(step) }"
                        @click.stop="toggleStepGlobalHeaders(step)"
                      >
                        <img
                          class="step-icon-image step-headers-icon-image"
                          :src="headersToolIcon"
                          :alt="isStepGlobalHeadersEnabled(step) ? '已启用全局请求头' : '未启用全局请求头'"
                        />
                      </button>
                    </el-tooltip>
                    <el-tooltip content="复制步骤" placement="top" popper-class="qm-app-tooltip" :show-after="180">
                      <button class="step-icon" @click.stop="duplicateStep(step)">
                        <el-icon><CopyDocument /></el-icon>
                      </button>
                    </el-tooltip>
                    <el-tooltip
                      :content="step.enabled ? '停用步骤' : '启用步骤'"
                      placement="top"
                      popper-class="qm-app-tooltip"
                      :show-after="180"
                    >
                      <button class="step-icon" @click.stop="toggleStepEnabled(step)">
                        <img
                          class="step-icon-image"
                          :src="step.enabled ? stopToolIcon : startToolIcon"
                          :alt="step.enabled ? '停用步骤' : '启用步骤'"
                        />
                      </button>
                    </el-tooltip>
                    <el-tooltip content="删除步骤" placement="top" popper-class="qm-app-tooltip" :show-after="180">
                      <button class="step-icon danger" @click.stop="deleteStep(step)">
                        <el-icon><Delete /></el-icon>
                      </button>
                    </el-tooltip>
                  </div>
                </div>

                <div class="step-interface-pill">
                  <span class="request-badge" :class="getTemplateMethodClass(getStepMethod(step))">
                    {{ getStepMethod(step) }}
                  </span>
                  <button
                    class="api-link"
                    :title="getStepLabel(step)"
                    @click.stop="focusTemplateFromStep(step)"
                  >
                    {{ getStepLabel(step) }}
                  </button>
                  <el-dropdown
                    v-if="usesAddToolDropdown(getStepTab(step))"
                    trigger="click"
                    @command="handleToolCommand(step, $event)"
                  >
                    <button class="step-add-tool" :title="getAddToolButtonTitle(getStepTab(step))">
                      <el-icon><Plus /></el-icon>
                    </button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <template v-for="option in TOOL_OPTIONS[getStepTab(step)]" :key="option.type">
                          <div v-if="option.type === 'global_tool'" class="tool-dropdown-submenu">
                            <el-popover
                              placement="right-start"
                              trigger="hover"
                              :width="200"
                              :show-arrow="false"
                              :offset="0"
                              :show-after="0"
                              :hide-after="0"
                              transition="none"
                              popper-class="global-tool-cascade-popper"
                              teleported
                            >
                              <template #reference>
                                <div class="tool-dropdown-submenu-trigger">
                                  <span>{{ option.label }}</span>
                                  <el-icon><ArrowRight /></el-icon>
                                </div>
                              </template>
                              <div class="global-tool-cascade-menu">
                                <button
                                  v-for="globalTool in enabledGlobalTools"
                                  :key="globalTool.id"
                                  class="global-tool-cascade-item"
                                  type="button"
                                  @click="addGlobalToolToStep(step, getStepTab(step), globalTool)"
                                >
                                  <img
                                    class="tool-type-icon"
                                    :src="getGlobalToolTypeIcon(globalTool)"
                                    :alt="getGlobalToolLabel(globalTool)"
                                  />
                                  <span class="global-tool-cascade-name">{{ globalTool.name }}</span>
                                </button>
                                <div v-if="!enabledGlobalTools.length" class="global-tool-cascade-empty">
                                  暂无可用全局工具
                                </div>
                              </div>
                            </el-popover>
                          </div>
                          <el-dropdown-item v-else :command="option.type">
                            {{ option.label }}
                          </el-dropdown-item>
                        </template>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                  <button
                    v-else
                    class="step-add-tool"
                    :title="getAddToolButtonTitle(getStepTab(step))"
                    @click.stop="handleAddToolButton(step)"
                  >
                    <el-icon><Plus /></el-icon>
                  </button>
                </div>

                <div class="step-tabs">
                  <button
                    v-for="tab in TOOL_TABS"
                    :key="tab"
                    class="step-tab"
                    :class="{ active: getStepTab(step) === tab }"
                    @click.stop="setStepTab(step, tab)"
                  >
                    {{ TOOL_TAB_LABELS[tab] }}
                  </button>
                </div>
                <div class="tool-panel">
                  <template v-if="getToolEntries(step, getStepTab(step)).length">
                    <div
                      v-for="entry in getToolEntries(step, getStepTab(step))"
                      :key="entry.toolId"
                      class="tool-item"
                      :class="{
                        disabled: entry.tool.enabled === false,
                        dragging: draggedToolId === entry.toolId,
                        dragover:
                          draggedToolId !== entry.toolId &&
                          draggedToolStepKey === getStepKey(step) &&
                          draggedToolTabKey === getStepTab(step) &&
                          dragOverToolId === entry.toolId,
                      }"
                      draggable="true"
                      @dragstart="onToolDragStart(step, getStepTab(step), entry.toolId)"
                      @dragover.prevent="onToolDragOver(step, getStepTab(step), entry.toolId)"
                      @drop.prevent="onToolDrop(step, getStepTab(step), entry.toolId)"
                      @dragend="onToolDragEnd"
                    >
                      <img class="tool-type-icon" :src="getToolTypeIcon(entry.tool)" :alt="getToolLabel(entry.tool)" />
                      <span class="tool-name-text" :title="getToolDisplayName(entry.tool)">
                        {{ getToolDisplayName(entry.tool) }}
                      </span>
                      <div class="tool-actions">
                        <button class="tool-action" title="编辑工具" @click.stop="openToolDialog(step, getStepTab(step), entry.toolId)">
                          <el-icon><Edit /></el-icon>
                        </button>
                        <button class="tool-action" title="复制工具" @click.stop="copyTool(step, getStepTab(step), entry.toolId)">
                          <el-icon><CopyDocument /></el-icon>
                        </button>
                        <button class="tool-action danger" title="删除工具" @click.stop="removeTool(step, getStepTab(step), entry.toolId)">
                          <el-icon><Delete /></el-icon>
                        </button>
                      </div>
                    </div>
                  </template>
                  <div v-else class="tool-empty">{{ getStepPlaceholder(getStepTab(step)) }}</div>
                </div>
              </article>
            </div>
            <div v-else class="steps-empty">
              <p>{{ currentProjectName || "当前项目" }} / {{ form.environment_id ? "已选择环境" : "不使用环境" }}</p>
              <span>暂无测试步骤，请添加步骤或从左侧拖拽接口</span>
            </div>
          </div>
        </div>

        <div v-else class="editor-empty">
          <div class="editor-empty-box">
            <p>请先在左侧新增测试用例或选择对应测试用例</p>
          </div>
        </div>
      </section>
    </div>

    <div
      v-if="caseContextMenu.visible"
      class="context-menu"
      :style="{ left: `${caseContextMenu.x}px`, top: `${caseContextMenu.y}px` }"
      @click.stop
    >
      <template v-if="caseContextMenu.blank">
        <button @click="createFolder(null); hideContextMenus()">新增一级目录</button>
        <button @click="createCaseViaContext(null, true); hideContextMenus()">新建测试用例</button>
        <button @click="refreshWorkspace(); hideContextMenus()">刷新</button>
      </template>
      <template v-else-if="caseContextMenu.node?.type === 'folder'">
        <button
          v-if="canCreateCaseChildFolder(caseContextMenu.node.folderId)"
          @click="createFolder(caseContextMenu.node.folderId); hideContextMenus()"
        >
          新增子目录
        </button>
        <button @click="createCaseViaContext(caseContextMenu.node); hideContextMenus()">新建测试用例</button>
        <button @click="renameFolder(caseContextMenu.node); hideContextMenus()">重命名目录</button>
        <button class="danger" @click="deleteFolder(caseContextMenu.node); hideContextMenus()">删除目录</button>
      </template>
      <template v-else>
        <button @click="duplicateCase(caseContextMenu.node?.caseItem); hideContextMenus()">复制用例</button>
        <button class="danger" @click="deleteCase(caseContextMenu.node?.caseItem); hideContextMenus()">删除用例</button>
      </template>
    </div>

    <div
      v-if="tabContextMenu.visible"
      class="context-menu"
      :style="{ left: `${tabContextMenu.x}px`, top: `${tabContextMenu.y}px` }"
      @click.stop
    >
      <button @click="closeCurrentTab(); hideContextMenus()">关闭当前</button>
      <button @click="closeOtherTabs(); hideContextMenus()">关闭其他</button>
      <button @click="closeAllTabs(); hideContextMenus()">关闭全部</button>
    </div>

    <el-dialog
      v-model="toolDialogVisible"
      :title="toolDialogTitle"
      width="820px"
      class="step-tool-dialog"
      @closed="handleToolDialogClosed"
    >
      <div class="step-tool-dialog-body">
        <CommonToolConfigForm
          v-if="isCommonToolDialog"
          :active="toolDialogVisible"
          :kind="commonToolDialogKind"
          :form="toolForm"
          :header-rows="toolHeaderRows"
          :rows="toolRows"
          :database-connections="enabledDatabaseConnections"
          :database-schemas="sqlDatabaseSchemas"
          :database-schemas-loading="sqlDatabaseSchemasLoading"
          :http-tab="httpToolTab"
          show-name
          show-http-global-options
          @update:http-tab="httpToolTab = $event"
          @database-change="handleSqlDatabaseConnectionChange"
          @global-encryption-change="handleToolGlobalEncryptionChange"
          @global-headers-change="handleToolGlobalHeadersChange"
          @insert-header-row="insertHeaderRow"
          @remove-header-row="removeHeaderRow"
          @insert-row="insertToolRow"
          @remove-row="removeToolRow"
        />

        <template v-else>
          <div class="tool-dialog-row name-row">
            <label>名称:</label>
            <input v-model="toolForm.name" class="tool-input dialog-input" placeholder="请输入工具名称" />
          </div>

          <template v-if="toolDialogKind === 'parameter_extraction'">
          <div class="tool-dialog-section">
            <div class="tool-dialog-section-title">参数提取</div>
            <div v-for="(row, index) in toolRows" :key="row.rowKey" class="tool-config-row parameter-row flat-row">
              <el-select v-model="row.source" class="tool-dialog-select">
                <el-option
                  v-for="option in EXTRACTOR_SOURCE_OPTIONS"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
              <el-select v-model="row.extractorType" class="tool-dialog-select">
                <el-option
                  v-for="option in EXTRACTOR_TYPE_OPTIONS"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
              <input v-model="row.variable" class="tool-input config-input" placeholder="变量名称" />
              <input v-model="row.path" class="tool-input config-input wide" placeholder="JSONPath表达式" />
              <button class="row-icon add" title="新增" @click="insertToolRow(index)">+</button>
              <button class="row-icon remove" title="删除" @click="removeToolRow(index)">-</button>
            </div>
          </div>
          </template>

          <template v-else-if="toolDialogKind === 'assertion'">
          <div class="tool-dialog-section">
            <div class="tool-dialog-section-title">断言配置</div>
            <div v-for="(row, index) in toolRows" :key="row.rowKey" class="tool-config-row assertion-row flat-row">
              <el-select
                v-model="row.fieldPrefix"
                class="assertion-source-select"
                @change="handleAssertionPrefixChange(row)"
              >
                <el-option
                  v-for="option in ASSERTION_FIELD_SOURCE_OPTIONS"
                  :key="option.value || 'runtime-variable'"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
              <input
                v-model="row.fieldPath"
                class="tool-input config-input wide"
                :disabled="isAssertionPathDisabled(row.fieldPrefix)"
                :placeholder="getAssertionFieldPlaceholder(row.fieldPrefix)"
              />
              <el-select v-model="row.operator" class="tool-dialog-operator">
                <el-option
                  v-for="option in ASSERTION_OPERATOR_OPTIONS"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
              <input v-model="row.expected" class="tool-input config-input" placeholder="预期值" />
              <button class="row-icon add" title="新增" @click="insertToolRow(index)">+</button>
              <button class="row-icon remove" title="删除" @click="removeToolRow(index)">-</button>
            </div>
          </div>
          </template>

          <template v-else>
          <div class="tool-dialog-row textarea">
            <label>工具说明:</label>
            <el-input v-model="toolForm.summary" type="textarea" :rows="6" resize="none" />
          </div>
          </template>
        </template>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <button class="action-button ghost" @click="toolDialogVisible = false">取消</button>
          <button class="action-button solid" :disabled="toolDialogSaving" @click="saveToolDialog">确认</button>
        </span>
      </template>
    </el-dialog>

    <el-dialog v-model="logDialogVisible" title="执行日志" width="980px" class="execution-log-dialog">
      <ExecutionLogViewer :log="executionLog" :fallback-lines="logLines" />
    </el-dialog>
  </div>
</template>

<style scoped>
.interface-auto-desktop.case-desktop {
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: #f4f8fc;
}

.case-workbench {
  display: grid;
  grid-template-columns: 336px 336px minmax(760px, 1fr);
  min-width: 1440px;
  height: 100%;
  min-height: 0;
  padding: 0;
  gap: 10px;
  box-sizing: border-box;
}

.pane {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  background: #fff;
}

.pane-left,
.pane-middle {
  padding: 8px;
}

.pane-right {
  overflow: hidden;
}

.project-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  margin-bottom: 6px;
  color: #2d3a4b;
  font-size: 12px;
}

.toolbar-label {
  flex: 0 0 auto;
  font-weight: 600;
}

.project-cascader {
  width: 160px;
}

.icon-button,
.mini-action,
.action-icon,
.step-icon,
.step-add-tool,
.tool-action,
.action-button,
.case-tab-close {
  border: 1px solid #ccd7e3;
  background: #fff;
  cursor: pointer;
}

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  color: #506176;
}

.icon-button:disabled,
.icon-button.disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.search-line {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  margin-bottom: 4px;
  color: #4d5d71;
}

.pane-heading {
  margin-bottom: 4px;
}

.pane-heading-text {
  color: #111827;
  font-size: 14px;
  font-weight: 700;
}

.search-input {
  width: 100%;
  height: 28px;
  border: 1px solid #d7e1ec;
  border-radius: 6px;
  padding: 0 10px;
  box-sizing: border-box;
  color: #2d3a4b;
  outline: none;
}

.search-input:focus,
.text-field:focus,
.tool-input:focus {
  border-color: #75a7ff;
}

.mini-action {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  color: #4d5d71;
}

.case-tree,
.template-tree {
  flex: 1;
  min-height: 0;
  overflow: auto;
  border: 1px solid #dfe6ef;
}

.tree-node {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  min-width: 0;
  height: 24px;
  padding-right: 6px;
  color: #1f2937;
  font-size: 13px;
}

.tree-node.is-template {
  cursor: grab;
}

.tree-folder-icon {
  color: #3d7ee8;
}

.tree-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.case-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 42px;
  height: 18px;
  border-radius: 4px;
  padding: 0 6px;
  border: 1px solid #d5dae3;
  background: #eef1f5;
  color: #2f343d;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.2px;
  text-transform: uppercase;
  box-sizing: border-box;
}

.method-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 38px;
  height: 18px;
  border-radius: 4px;
  padding: 0 6px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}

.method-badge.get,
.request-badge.get {
  background: #e8faf6;
  color: #0f8a6c;
}

.method-badge.post,
.request-badge.post {
  background: #fff0dc;
  color: #d26f00;
}

.method-badge.delete,
.request-badge.delete {
  background: #fff1f0;
  color: #cf1322;
}

.method-badge.put,
.request-badge.put {
  background: #f0f9eb;
  color: #4a9f2e;
}

.method-badge.patch,
.request-badge.patch {
  background: #f4edff;
  color: #7c3aed;
}

.pane-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 180px;
  color: #98a2b3;
  font-size: 14px;
}

.opened-tabs {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 44px;
  margin: 8px 12px 0;
  border: 1px solid #dce8f5;
  border-radius: 6px;
  padding: 0 10px;
  overflow-x: auto;
  background: linear-gradient(180deg, #fbfdff 0%, #f4f8fd 100%);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 80%);
}

.case-open-tag {
  flex: 0 0 auto;
}

.open-tag.inactive {
  border-color: transparent;
  background: rgb(255 255 255 / 64%);
  color: #4f6277;
}

.open-tag.inactive:hover {
  background: #eef6ff;
  color: #1677ff;
}

.open-tag:not(.inactive) {
  border-color: #bcd7ff;
  background: #edf5ff;
  color: #1677ff;
  box-shadow: 0 4px 12px rgb(22 119 255 / 10%);
}

.open-tag.modified {
  border-color: #bcd7ff;
  color: #1677ff;
}

.open-tag.modified.inactive {
  border-color: #d6e4ff;
  background: #f7fbff;
  color: #6b85a3;
}

.open-tag.modified:not(.inactive) {
  border-color: #7fb0ff;
  background: #e7f1ff;
  color: #145ecc;
  box-shadow: 0 0 0 1px rgb(64 158 255 / 18%), 0 4px 12px rgb(22 119 255 / 12%);
}

.editor-shell {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: calc(100% - 52px);
  background: #f6f9fd;
}

.editor-header {
  flex: 0 0 auto;
  padding: 10px 14px 8px;
  border-bottom: 1px solid #dbe4ef;
  background: #fff;
}

.header-row {
  display: flex;
  align-items: center;
  gap: 18px;
  min-height: 30px;
  margin-bottom: 8px;
}

.header-row:last-child {
  margin-bottom: 0;
}

.header-field {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.header-field-name {
  flex: 0 0 420px;
}

.header-field-desc {
  flex: 1 1 auto;
}

.header-field-env {
  width: 100%;
}

.header-label {
  flex: 0 0 auto;
  color: #1f2937;
  font-size: 13px;
}

.text-field {
  width: 100%;
  height: 30px;
  border: 1px solid #d7e1ec;
  border-radius: 8px;
  padding: 0 10px;
  box-sizing: border-box;
  font-family: var(--qm-form-font-family);
  font-size: var(--qm-form-font-size);
  line-height: var(--qm-form-line-height);
  color: #1f2937;
  outline: none;
}

.env-select {
  flex: 1 1 auto;
}

.actions-row {
  justify-content: flex-start;
  gap: 10px;
}

.encryption-check {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #334155;
  font-size: 13px;
}

.global-config-shell {
  margin-top: 10px;
  background: #fff;
}

.global-config-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  border: none;
  padding: 8px 0;
  background: transparent;
  color: #111827;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.global-config-toggle-icon {
  color: #6b7280;
  font-size: 14px;
  line-height: 1;
  transition: transform 0.2s ease;
}

.global-config-toggle-icon.expanded {
  transform: rotate(90deg);
}

.global-config-panel {
  padding: 4px 0 8px;
}

.global-config-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.global-config-tabs {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 0 2px;
}

.global-config-tab {
  position: relative;
  height: 38px;
  padding: 0 2px;
  border: none;
  background: transparent;
  color: #6b7380;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.global-config-tab::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, #1677ff 0%, #4aa2ff 100%);
  opacity: 0;
  transform: scaleX(0.45);
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.global-config-tab.active {
  color: #135bd8;
  font-weight: 600;
}

.global-config-tab.active::after {
  opacity: 1;
  transform: scaleX(1);
}

.global-config-content {
  border-radius: 14px;
  background: transparent;
  padding: 8px 0 0;
}

.global-config-tab-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.global-config-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.global-config-hint {
  color: #5b6b7d;
  font-size: 12px;
  line-height: 1.6;
}

.global-config-kv-table {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.global-variable-view {
  display: grid;
  gap: 6px;
}

.global-variable-caption {
  margin-bottom: 8px;
  color: #64748b;
  font-size: 12px;
}

.global-variable-item {
  display: grid;
  grid-template-columns: minmax(140px, 0.8fr) minmax(220px, 1.4fr) 88px;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  border: 1px solid #e5edf7;
  border-radius: 8px;
  background: #f8fbff;
  padding: 0 10px;
  color: #334155;
  font-size: 12px;
}

.global-variable-name {
  font-weight: 700;
}

.global-variable-value {
  min-width: 0;
  overflow: hidden;
  color: #475569;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.global-variable-type {
  justify-self: end;
  border-radius: 999px;
  background: #eef4ff;
  color: #3b5b8f;
  font-size: 11px;
  line-height: 20px;
  padding: 0 8px;
}

.global-config-empty {
  min-height: 42px;
  display: flex;
  align-items: center;
  color: #7b8ba0;
  font-size: 12px;
}

.global-output-config {
  display: flex;
  align-items: center;
  gap: 8px;
}

.global-output-input {
  flex: 1 1 auto;
  min-width: 0;
}

.global-config-kv-row {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr) 96px;
  gap: 6px;
  align-items: center;
}

.global-config-list-content {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.global-config-row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.variable-kv-row {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 96px;
}

.global-config-grid {
  display: grid;
  gap: 10px;
}

.global-config-grid.two-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.global-config-inline-grid {
  display: grid;
  gap: 8px;
}

.global-config-inline-grid.two-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.method-url-grid {
  grid-template-columns: 220px minmax(0, 1fr);
}

.global-config-grid.three-columns {
  grid-template-columns: 160px 180px minmax(0, 1fr);
}

.global-config-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.global-config-inline-field {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.global-config-inline-field .text-field,
.global-config-inline-field .el-select,
.global-config-inline-field :deep(.el-textarea) {
  flex: 1 1 auto;
}

.compact-inline-field :deep(.el-select) {
  width: 100%;
}

.body-inline-field {
  align-items: flex-start;
}

.body-label {
  padding-top: 6px;
}

.body-inline-field :deep(.el-textarea) {
  flex: 1 1 auto;
}

.config-list-inline-field {
  align-items: flex-start;
}

.global-config-inline-label {
  flex: 0 0 auto;
  min-width: 88px;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

.global-config-label,
.global-config-section-title {
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

.global-config-section-card {
  border: none;
  border-radius: 0;
  padding: 4px 0;
  background: transparent;
}

.global-config-section-panel {
  margin: 6px 0 2px 26px;
  padding: 12px 14px;
  border: 1px solid #e5edf7;
  border-radius: 10px;
  background: #f8fbff;
}

.global-config-section-card.inner-card {
  padding: 2px 0;
  border-radius: 0;
  background: transparent;
}

.compact-check {
  gap: 8px;
}

.align-left {
  justify-content: flex-start;
}

.action-button {
  height: 28px;
  border-radius: 4px;
  padding: 0 12px;
  color: #334155;
  font-size: 13px;
}

.action-button.compact {
  height: 24px;
  padding: 0 10px;
  font-size: 12px;
}

.action-button.solid {
  border-color: #61b741;
  background: #61b741;
  color: #fff;
}

.action-button.ghost {
  border: 1px solid #d7e1ec;
  background: #fff;
  color: #334155;
}

.action-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 14px;
  color: #36597e;
}

.action-icon.legacy-icon {
  border: none;
  background: transparent;
  border-radius: 4px;
}

.toolbar-action-image {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.steps-board {
  flex: 1 1 auto;
  min-height: 0;
  margin: 8px;
  border: 1px solid #d7e1ec;
  border-radius: 8px;
  background: #fff;
  overflow: auto;
}

.steps-scroller {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  min-width: 0;
  padding: 8px;
  box-sizing: border-box;
  align-content: start;
}

.steps-empty,
.editor-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.steps-empty {
  flex-direction: column;
  gap: 8px;
  min-height: 300px;
  color: #7b8ba0;
  font-size: 14px;
}

.steps-empty p {
  margin: 0;
  color: #415469;
}

.editor-empty-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: calc(100% - 24px);
  height: calc(100% - 24px);
  margin: 12px;
  border: 1px dashed #d6dce5;
  background: #fff;
  color: #7c8ea3;
  font-size: 14px;
}

.step-card {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  max-width: none;
  min-height: 262px;
  border: 1px solid #d6dce5;
  border-radius: 10px;
  padding: 8px 8px 4px;
  box-sizing: border-box;
  background: #fff;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, opacity 0.16s ease;
}

@media (max-width: 1580px) {
  .steps-scroller {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1320px) {
  .steps-scroller {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 980px) {
  .steps-scroller {
    grid-template-columns: minmax(0, 1fr);
  }
}

.step-card.active {
  border-color: #8bb4ff;
  box-shadow: 0 0 0 1px rgb(94 150 255 / 35%);
}

.step-card.dragover {
  border-color: #3d7ee8;
}

.step-card.disabled {
  opacity: 0.6;
}

.step-card-header,
.tool-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.step-title {
  color: #16202d;
  font-size: 12px;
  font-weight: 700;
}

.step-header-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.step-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border: none;
  background: transparent;
  color: #5d6b7d;
  font-size: 11px;
}

.step-icon-image {
  width: 14px;
  height: 14px;
  object-fit: contain;
}

.step-headers-icon-image {
  width: 12px;
  height: 12px;
}

.step-icon.muted .step-icon-image {
  opacity: 0.32;
  filter: grayscale(1);
}

.step-icon.danger,
.tool-action.danger {
  color: #e25555;
}

.step-interface-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  margin-top: 8px;
  border-radius: 16px;
  padding: 0 8px;
  border: 1px solid #e2eaf4;
  background: #f8fbff;
}

.request-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 22px;
  border-radius: 7px;
  padding: 0 7px;
  font-size: 11px;
  font-weight: 700;
}

.api-link {
  flex: 1 1 auto;
  overflow: hidden;
  border: none;
  background: transparent;
  color: #202c3a;
  font-size: 12px;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.step-add-tool {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 4px;
  color: #475569;
  font-size: 13px;
}

.step-tabs {
  display: flex;
  gap: 18px;
  margin-top: 8px;
  padding: 2px 4px 0;
  flex: 0 0 auto;
}

.step-tab {
  position: relative;
  border: none;
  background: transparent;
  padding: 2px 2px 7px;
  color: #66768a;
  font-size: 13px;
  line-height: 1.2;
  cursor: pointer;
}

.step-tab.active {
  color: #2f7df6;
  font-weight: 600;
}

.step-tab.active::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2px;
  border-radius: 999px;
  background: #2f7df6;
}

.tool-panel {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 0 0 auto;
  height: 186px;
  margin-top: 6px;
  border: 1px solid #dbe3ed;
  border-radius: 6px;
  padding: 6px 4px 6px 6px;
  overflow-x: hidden;
  overflow-y: auto;
}

.tool-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1 1 auto;
  min-height: 100%;
  color: #c1c7cf;
  font-size: 12px;
}

.tool-item {
  display: flex;
  align-items: center;
  gap: 5px;
  min-height: 26px;
  border: none;
  border-radius: 0;
  padding: 0 2px;
  background: transparent;
  cursor: grab;
  transition: background-color 0.16s ease, opacity 0.16s ease;
}

.tool-item:hover {
  background: rgb(47 125 246 / 4%);
}

.tool-item.disabled {
  opacity: 0.55;
}

.tool-item.dragging {
  opacity: 0.45;
}

.tool-item.dragover {
  border-radius: 4px;
  background: #edf4ff;
}

.tool-type-icon {
  display: inline-flex;
  width: 16px;
  height: 16px;
  object-fit: contain;
  flex: 0 0 auto;
}

.tool-actions,
.variable-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.tool-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 2px;
  padding: 0;
  background: transparent;
  color: #475569;
  font-size: 11px;
  cursor: pointer;
}

.tool-action:hover {
  background: rgb(37 99 235 / 9%);
}

.tool-action.danger:hover {
  background: rgb(226 85 85 / 10%);
}

.tool-action .el-icon {
  font-size: 12px;
}

.tool-name-text {
  flex: 1 1 auto;
  min-width: 0;
  font-family: "Microsoft YaHei UI", "PingFang SC", sans-serif;
  font-size: 11px;
  line-height: 1.3;
  color: #304255;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tool-input {
  width: 100%;
  height: 28px;
  margin-top: 8px;
  border: 1px solid #d7e1ec;
  border-radius: 6px;
  padding: 0 10px;
  box-sizing: border-box;
  font-family: var(--qm-form-font-family);
  font-size: var(--qm-form-font-size);
  line-height: var(--qm-form-line-height);
  color: #1f2937;
  outline: none;
}

.context-menu {
  position: fixed;
  z-index: 4000;
  min-width: 140px;
  border: 1px solid #ccd6e0;
  border-radius: 8px;
  padding: 4px;
  background: #fff;
  box-shadow: 0 10px 24px rgb(15 23 42 / 18%);
}

.context-menu button {
  display: block;
  width: 100%;
  border: none;
  border-radius: 6px;
  padding: 8px 10px;
  background: transparent;
  color: #263445;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}

.context-menu button:hover {
  background: #edf5ff;
  color: #2f7df6;
}

.context-menu button.danger:hover {
  background: #fff1f0;
  color: #cf1322;
}

.tool-dropdown-submenu {
  position: relative;
  min-width: 156px;
}

.tool-dropdown-submenu-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  box-sizing: border-box;
  width: 100%;
  height: 32px;
  padding: 5px 16px;
  color: #344256;
  font-size: 13px;
  font-weight: 400;
  line-height: 22px;
  white-space: nowrap;
  cursor: default;
  user-select: none;
}

.tool-dropdown-submenu-trigger .el-icon {
  color: #8a96a8;
  font-size: 12px;
}

.tool-dropdown-submenu:hover .tool-dropdown-submenu-trigger {
  background: #edf5ff;
  color: #2f7df6;
}

:global(.global-tool-cascade-popper) {
  border: 1px solid #dfe7f1 !important;
  border-radius: 4px !important;
  margin-top: -6px !important;
  padding: 6px !important;
  box-shadow: 0 8px 24px rgb(15 23 42 / 16%) !important;
}

:global(.global-tool-cascade-menu) {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 320px;
  overflow-y: auto;
}

:global(.global-tool-cascade-item) {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-width: 0;
  height: 32px;
  border: none;
  border-radius: 4px;
  padding: 5px 8px;
  background: transparent;
  color: #263445;
  font-size: 13px;
  font-weight: 400;
  line-height: 22px;
  text-align: left;
  cursor: pointer;
}

:global(.global-tool-cascade-item .tool-type-icon) {
  flex: 0 0 auto;
}

:global(.global-tool-cascade-item:hover) {
  background: #edf5ff;
  color: #2f7df6;
}

:global(.global-tool-cascade-name) {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  font-size: inherit;
  font-weight: 400;
  line-height: inherit;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:global(.global-tool-cascade-empty) {
  padding: 8px 10px;
  color: #94a3b8;
  font-size: 13px;
  white-space: nowrap;
}

.variable-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.variable-table {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.variable-head,
.variable-row {
  display: grid;
  grid-template-columns: 1.2fr 1.4fr 0.8fr 1.2fr 132px;
  gap: 8px;
  align-items: center;
}

.variable-head {
  color: #344256;
  font-size: 13px;
  font-weight: 700;
}

.log-panel {
  border: 1px solid #d7e1ec;
  border-radius: 8px;
  background: #fbfdff;
  padding: 12px;
}

.log-panel pre {
  margin: 0;
  min-height: 260px;
  color: #263445;
  font-family: Consolas, "Courier New", monospace;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
}

.step-tool-dialog-body {
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

.global-option-checks {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 18px;
  min-height: 32px;
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

.dialog-input {
  margin-top: 0;
  height: 34px;
}

.editor-shell :deep(.el-input__wrapper),
.editor-shell :deep(.el-select__wrapper),
.editor-shell :deep(.el-textarea__inner),
.editor-shell :deep(.el-input-number .el-input__inner),
.step-tool-dialog :deep(.el-input__wrapper),
.step-tool-dialog :deep(.el-select__wrapper),
.step-tool-dialog :deep(.el-textarea__inner),
.step-tool-dialog :deep(.el-input-number .el-input__inner) {
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

.tool-dialog-operator {
  min-width: 88px;
}

.assertion-source-select {
  min-width: 180px;
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
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.tool-dialog-section-title {
  margin-bottom: 10px;
  color: #1e293b;
  font-size: 13px;
  font-weight: 700;
}

.tool-dialog-section-title.side-title {
  flex: 0 0 74px;
  margin-bottom: 0;
  line-height: 32px;
  padding-top: 10px;
}

.tool-dialog-labeled-section > .tool-dialog-section {
  flex: 1 1 auto;
  min-width: 0;
}

.tool-config-row {
  display: grid;
  grid-template-columns: 180px minmax(220px, 1fr) 30px 30px;
  gap: 10px;
  align-items: center;
  margin-top: 8px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  padding: 8px;
  background: #fff;
}

.tool-config-row.flat-row {
  margin-top: 0;
  border: none;
  border-radius: 0;
  padding: 0;
  background: transparent;
}

.tool-config-row.flat-row + .tool-config-row.flat-row {
  margin-top: 10px;
}

.tool-config-row.assertion-row {
  grid-template-columns: 180px minmax(220px, 1fr) 88px minmax(140px, 1fr) 30px 30px;
}

.tool-config-row.parameter-row {
  grid-template-columns: 120px 120px 160px minmax(220px, 1fr) 30px 30px;
}

.parameterize-editor {
  width: 100%;
}

.parameterize-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

.parameterize-toolbar {
  align-items: end;
}

.parameterize-toolbar .global-config-inline-field {
  min-height: 32px;
}

.parameterize-editor :deep(.el-textarea__inner) {
  padding: 12px 14px;
  border-radius: 10px;
  background: #fff;
}

.parameterize-validation {
  color: #b45309;
  font-size: 12px;
}

.parameterize-validation.ok {
  color: #15803d;
}

.row-icon {
  border: 0;
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

.tool-action.text-action {
  width: 30px;
  min-width: 30px;
  height: 30px;
  border: 1px solid #d7e1ec;
  border-radius: 6px;
  padding: 0;
  background: #fff;
  color: #475569;
  font-size: 16px;
  line-height: 1;
  font-weight: 500;
}

.config-input {
  margin-top: 0;
}

.config-input.wide {
  min-width: 0;
}

.dialog-footer {
  display: inline-flex;
  gap: 8px;
}
</style>
