<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Delete,
  Edit,
  Plus,
  RefreshRight,
  Search,
} from "@element-plus/icons-vue";

import {
  fetchDatabaseConnections,
  fetchDatabaseSchemas,
  type DatabaseConnectionRecord,
} from "@/modules/data-assets/api";
import { useBusinessProjectContext } from "@/shared/composables/useBusinessProjectContext";
import {
  createGlobalTool,
  deleteGlobalTool,
  fetchGlobalTools,
  updateGlobalTool,
  updateGlobalToolStatus,
} from "./globalToolApi";
import CommonToolConfigForm from "./CommonToolConfigForm.vue";
import type { GlobalToolPayload, GlobalToolRecord, GlobalToolType } from "./types";

type ToolOption = {
  type: GlobalToolType;
  label: string;
};

type HeaderRow = {
  rowKey: string;
  key: string;
  value: string;
};

type ExtractionRow = {
  rowKey: string;
  variable: string;
  path: string;
};

const ALL_FILTER_VALUE = 0;

const TOOL_OPTIONS: ToolOption[] = [
  { type: "http_request", label: "HTTP请求" },
  { type: "sql_tool", label: "SQL工具" },
  { type: "python_script", label: "Python脚本" },
];

const businessProjectFilterProps = {
  emitPath: true,
};

const businessProjectDialogProps = {
  emitPath: true,
};

const context = useBusinessProjectContext();
const loading = ref(false);
const saving = ref(false);
const keyword = ref("");
const typeFilter = ref<GlobalToolType | "">("");
const selectedBusinessGroupId = ref<number>(ALL_FILTER_VALUE);
const selectedProjectId = ref<number>(ALL_FILTER_VALUE);
const tools = ref<GlobalToolRecord[]>([]);
const databaseConnections = ref<DatabaseConnectionRecord[]>([]);
const sqlDatabaseSchemas = ref<string[]>([]);
const sqlDatabaseSchemasLoading = ref(false);
const dialogVisible = ref(false);
const dialogTitle = ref("");
const headerRows = ref<HeaderRow[]>([]);
const extractionRows = ref<ExtractionRow[]>([]);
const httpConfigTab = ref<"body" | "headers">("body");

let schemaRequestToken = 0;

const form = reactive({
  id: null as number | null,
  project_id: null as number | null,
  is_shared: false,
  name: "",
  tool_type: "http_request" as GlobalToolType,
  description: "",
  enabled: false,
  method: "GET",
  url: "",
  timeout: 30,
  headersText: "{}",
  bodyText: "{\n  \n}",
  databaseConnectionId: null as number | null,
  database: "",
  sqlText: "",
  pythonScriptText: "",
  pythonTimeout: 60,
  outputFieldsText: "",
});

const filteredTools = computed(() => {
  const text = keyword.value.trim().toLowerCase();
  return tools.value.filter((item) => {
    if (typeFilter.value && item.tool_type !== typeFilter.value) {
      return false;
    }
    if (!text) {
      return true;
    }
    return `${item.name} ${item.project_name ?? ""} ${item.business_group_name ?? ""} ${getToolTypeLabel(item.tool_type)}`
      .toLowerCase()
      .includes(text);
  });
});

const enabledDatabaseConnections = computed(() =>
  databaseConnections.value.filter((item) => item.enabled !== false),
);

const projectOptions = computed(() => context.projects.value);

const businessProjectOptions = computed(() =>
  context.groups.value.map((group) => ({
    value: group.id,
    label: group.name,
    children: projectOptions.value
      .filter((project) => project.business_group_id === group.id)
      .map((project) => ({
        value: project.id,
        label: project.name,
      })),
  })),
);

const selectedFilterPath = computed<number[]>({
  get() {
    if (selectedProjectId.value !== ALL_FILTER_VALUE) {
      const project = projectOptions.value.find((item) => item.id === selectedProjectId.value);
      return project?.business_group_id
        ? [project.business_group_id, project.id]
        : [selectedProjectId.value];
    }
    if (selectedBusinessGroupId.value !== ALL_FILTER_VALUE) {
      return [selectedBusinessGroupId.value];
    }
    return [];
  },
  set(value) {
    if (!value?.length) {
      selectedBusinessGroupId.value = ALL_FILTER_VALUE;
      selectedProjectId.value = ALL_FILTER_VALUE;
      return;
    }
    if (value.length === 1) {
      selectedBusinessGroupId.value = value[0];
      selectedProjectId.value = ALL_FILTER_VALUE;
      return;
    }
    selectedBusinessGroupId.value = value[0];
    selectedProjectId.value = value[value.length - 1];
  },
});

const formProjectPath = computed<number[]>({
  get() {
    if (!form.project_id) {
      return [];
    }
    const project = projectOptions.value.find((item) => item.id === form.project_id);
    return project?.business_group_id ? [project.business_group_id, project.id] : [form.project_id];
  },
  async set(value) {
    const projectId = value?.length ? value[value.length - 1] : null;
    form.project_id = projectId;
    await handleDialogProjectChange(projectId);
  },
});

function createKey(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

function getToolTypeLabel(type: string) {
  return TOOL_OPTIONS.find((item) => item.type === type)?.label ?? type;
}

function getToolTypePrefix(type: string) {
  if (type === "http_request") {
    return "HTTP";
  }
  if (type === "sql_tool") {
    return "SQL";
  }
  if (type === "python_script") {
    return "Python";
  }
  return getToolTypeLabel(type);
}

function getProjectById(projectId: number | null) {
  if (!projectId) {
    return null;
  }
  return projectOptions.value.find((item) => item.id === projectId) ?? null;
}

function getDefaultProjectId() {
  if (selectedProjectId.value !== ALL_FILTER_VALUE) {
    return selectedProjectId.value;
  }
  if (selectedBusinessGroupId.value !== ALL_FILTER_VALUE) {
    return projectOptions.value.find((item) => item.business_group_id === selectedBusinessGroupId.value)?.id ?? null;
  }
  if (context.selectedProjectId.value) {
    return context.selectedProjectId.value;
  }
  return projectOptions.value[0]?.id ?? null;
}

function parseMap(value: unknown): Record<string, unknown> {
  if (!value) {
    return {};
  }
  if (typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch {
      return {};
    }
  }
  return {};
}

function parseBody(value: unknown) {
  if (value === undefined || value === null || value === "") {
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

function createHeaderRow(key = "", value = ""): HeaderRow {
  return { rowKey: createKey("header"), key, value };
}

function createExtractionRow(variable = "", path = ""): ExtractionRow {
  return { rowKey: createKey("extract"), variable, path };
}

function splitOutputFields(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeOutputFields(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item).trim()).filter(Boolean) : [];
}

function headersToRows(value: unknown) {
  const headers = parseMap(value);
  const entries = Object.entries(headers);
  return entries.length
    ? entries.map(([key, value]) => createHeaderRow(key, String(value ?? "")))
    : [createHeaderRow("Content-Type", "application/json")];
}

function rowsToHeaders() {
  return Object.fromEntries(
    headerRows.value
      .map((row) => [row.key.trim(), row.value.trim()] as const)
      .filter(([key, value]) => key || value),
  );
}

function rowsToExtractions() {
  return extractionRows.value
    .map((row) => ({
      variable: row.variable.trim(),
      path: row.path.trim(),
    }))
    .filter((row) => row.variable || row.path);
}

function getDatabaseConnectionById(databaseId: number | null) {
  if (!databaseId) {
    return null;
  }
  return databaseConnections.value.find((item) => item.id === databaseId) ?? null;
}

function normalizeDatabaseConnectionId(value: unknown) {
  const id = Number(value);
  return Number.isFinite(id) && id > 0 ? id : null;
}

async function loadDatabaseConnectionsForProject(projectId: number | null, options?: { preserveSelected?: boolean }) {
  const businessGroupId = getProjectById(projectId)?.business_group_id ?? null;
  if (!businessGroupId) {
    databaseConnections.value = [];
    sqlDatabaseSchemas.value = [];
    form.databaseConnectionId = null;
    form.database = "";
    return;
  }
  const rows = await fetchDatabaseConnections({ business_group_id: businessGroupId });
  databaseConnections.value = Array.isArray(rows) ? rows : [];
  const selectedDatabaseId = form.databaseConnectionId;
  const matched = selectedDatabaseId
    ? databaseConnections.value.find((item) => item.id === selectedDatabaseId) ?? null
    : null;
  if (!options?.preserveSelected || !matched) {
    form.databaseConnectionId = null;
    form.database = "";
    sqlDatabaseSchemas.value = [];
  }
}

async function loadSqlDatabaseSchemas(databaseId: number | null, options?: { preserveSelected?: boolean }) {
  schemaRequestToken += 1;
  const requestToken = schemaRequestToken;
  sqlDatabaseSchemas.value = [];
  if (!databaseId) {
    return;
  }
  const previousSchema = form.database.trim();
  sqlDatabaseSchemasLoading.value = true;
  try {
    const result = await fetchDatabaseSchemas(databaseId);
    if (requestToken !== schemaRequestToken) {
      return;
    }
    const schemas = Array.isArray(result.schemas) ? result.schemas : [];
    sqlDatabaseSchemas.value = schemas;
    if (options?.preserveSelected && previousSchema && schemas.includes(previousSchema)) {
      form.database = previousSchema;
      return;
    }
    const defaultSchema = getDatabaseConnectionById(databaseId)?.database_name?.trim() ?? "";
    form.database = defaultSchema && schemas.includes(defaultSchema) ? defaultSchema : "";
  } catch (error) {
    if (requestToken === schemaRequestToken) {
      ElMessage.error((error as Error).message);
    }
  } finally {
    if (requestToken === schemaRequestToken) {
      sqlDatabaseSchemasLoading.value = false;
    }
  }
}

function handleDatabaseChange(value: number | string | null) {
  form.database = "";
  void loadSqlDatabaseSchemas(normalizeDatabaseConnectionId(value));
}

async function handleDialogProjectChange(projectId: number | null, options?: { preserveSelected?: boolean }) {
  await loadDatabaseConnectionsForProject(projectId, options);
  if (options?.preserveSelected && form.databaseConnectionId) {
    await loadSqlDatabaseSchemas(form.databaseConnectionId, { preserveSelected: true });
  }
}

function resetForm(type: GlobalToolType = "http_request") {
  form.id = null;
  form.project_id = getDefaultProjectId();
  form.is_shared = false;
  form.name = "";
  form.tool_type = type;
  form.description = "";
  form.enabled = false;
  form.method = "GET";
  form.url = "";
  form.timeout = 30;
  form.headersText = "{}";
  form.bodyText = "{\n  \n}";
  form.databaseConnectionId = null;
  form.database = "";
  form.sqlText = "";
  form.pythonScriptText = "";
  form.pythonTimeout = 60;
  form.outputFieldsText = "";
  headerRows.value = [createHeaderRow("Content-Type", "application/json")];
  extractionRows.value = [createExtractionRow()];
  sqlDatabaseSchemas.value = [];
  httpConfigTab.value = "body";
}

function fillForm(tool: GlobalToolRecord) {
  resetForm(tool.tool_type);
  const config = parseMap(tool.config);
  form.id = tool.id;
  form.project_id = tool.project_id;
  form.is_shared = tool.is_shared === true;
  form.name = tool.name;
  form.description = tool.description ?? "";
  form.enabled = tool.enabled !== false;
  if (tool.tool_type === "http_request") {
    httpConfigTab.value = "body";
    form.method = String(config.method ?? "GET");
    form.url = String(config.url ?? "");
    form.timeout = Number(config.timeout ?? 30) || 30;
    headerRows.value = headersToRows(config.headers);
    form.bodyText = stringifyBody(config.body);
    const extractions = Array.isArray(config.extractions) ? config.extractions : [];
    extractionRows.value = extractions.length
      ? extractions.map((item) =>
          createExtractionRow(
            String((item as Record<string, unknown>).variable ?? ""),
            String((item as Record<string, unknown>).path ?? ""),
          ),
        )
      : [createExtractionRow()];
  } else if (tool.tool_type === "sql_tool") {
    form.databaseConnectionId = normalizeDatabaseConnectionId(config.database_connection_id ?? config.connection_id);
    form.database = String(config.database ?? "");
    form.sqlText = String(config.sql ?? "");
    form.outputFieldsText = normalizeOutputFields(config.output_fields).join(", ");
  } else if (tool.tool_type === "python_script") {
    form.pythonScriptText = String(config.script ?? config.script_text ?? config.code ?? "");
    form.pythonTimeout = Number(config.timeout_seconds ?? config.timeout ?? 60) || 60;
    form.outputFieldsText = normalizeOutputFields(config.output_fields).join(", ");
  }
  void handleDialogProjectChange(form.project_id, { preserveSelected: true });
}

async function openCreateDialog() {
  resetForm("http_request");
  await handleDialogProjectChange(form.project_id);
  dialogTitle.value = "新增全局工具";
  dialogVisible.value = true;
}

function openEditDialog(tool: GlobalToolRecord) {
  fillForm(tool);
  dialogTitle.value = `编辑${getToolTypeLabel(tool.tool_type)}`;
  dialogVisible.value = true;
}

function buildPayload(): GlobalToolPayload | null {
  if (!form.project_id) {
    ElMessage.warning("请选择所属项目");
    return null;
  }
  const name = form.name.trim();
  if (!name) {
    ElMessage.warning("请输入工具名称");
    return null;
  }
  if (form.tool_type === "http_request") {
    if (!form.url.trim()) {
      ElMessage.warning("请输入请求 URL");
      return null;
    }
    const headers = rowsToHeaders();
    const invalidHeader = Object.entries(headers).some(([key, value]) => !key || !String(value).trim());
    if (invalidHeader) {
      ElMessage.warning("请求头名称和值不能为空");
      return null;
    }
    const extractions = rowsToExtractions();
    if (extractions.some((row) => !row.variable || !row.path)) {
      ElMessage.warning("响应提取的变量名称和 JSONPath 不能为空");
      return null;
    }
    return {
      project_id: form.project_id,
      name,
      tool_type: "http_request",
      description: form.description.trim(),
      enabled: form.id ? form.enabled : false,
      is_shared: form.is_shared,
      config: {
        method: form.method,
        url: form.url.trim(),
        timeout: Number(form.timeout) || 30,
        headers,
        body: parseBody(form.bodyText),
        extractions,
      },
    };
  }
  if (form.tool_type === "sql_tool") {
    if (!form.databaseConnectionId) {
      ElMessage.warning("请选择数据库");
      return null;
    }
    if (!form.database.trim()) {
      ElMessage.warning("请选择库名");
      return null;
    }
    if (!form.sqlText.trim()) {
      ElMessage.warning("请输入 SQL 语句");
      return null;
    }
    const selectedDatabase = getDatabaseConnectionById(form.databaseConnectionId);
    return {
      project_id: form.project_id,
      name,
      tool_type: "sql_tool",
      description: form.description.trim(),
      enabled: form.id ? form.enabled : false,
      is_shared: form.is_shared,
      config: {
        database_connection_id: form.databaseConnectionId,
        database_connection_name: selectedDatabase?.name ?? "",
        database: form.database.trim(),
        sql: form.sqlText,
        output_fields: splitOutputFields(form.outputFieldsText),
      },
    };
  }
  if (!form.pythonScriptText.trim()) {
    ElMessage.warning("请输入脚本内容");
    return null;
  }
  return {
    project_id: form.project_id,
    name,
    tool_type: "python_script",
    description: form.description.trim(),
    enabled: form.id ? form.enabled : false,
    is_shared: form.is_shared,
    config: {
      script: form.pythonScriptText,
      timeout_seconds: Number(form.pythonTimeout) || 60,
      render_template: true,
      output_fields: splitOutputFields(form.outputFieldsText),
    },
  };
}

async function saveTool() {
  const payload = buildPayload();
  if (!payload) {
    return;
  }
  saving.value = true;
  try {
    if (form.id) {
      await updateGlobalTool(form.id, payload);
      ElMessage.success("全局工具已更新");
    } else {
      await createGlobalTool(payload);
      ElMessage.success("全局工具已新增");
    }
    dialogVisible.value = false;
    await loadData();
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    saving.value = false;
  }
}

async function toggleToolStatus(tool: GlobalToolRecord) {
  try {
    await updateGlobalToolStatus(tool.id, tool.enabled !== false);
  } catch (error) {
    tool.enabled = !tool.enabled;
    ElMessage.error((error as Error).message);
  }
}

async function removeTool(tool: GlobalToolRecord) {
  try {
    await ElMessageBox.confirm(`确定删除全局工具“${tool.name}”吗？`, "删除全局工具", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await deleteGlobalTool(tool.id);
    ElMessage.success("全局工具已删除");
    await loadData();
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

function insertHeaderRow(index: number) {
  headerRows.value.splice(index + 1, 0, createHeaderRow());
}

function removeHeaderRow(index: number) {
  headerRows.value.splice(index, 1);
  if (!headerRows.value.length) {
    headerRows.value = [createHeaderRow("Content-Type", "application/json")];
  }
}

function insertExtractionRow(index: number) {
  extractionRows.value.splice(index + 1, 0, createExtractionRow());
}

function removeExtractionRow(index: number) {
  extractionRows.value.splice(index, 1);
  if (!extractionRows.value.length) {
    extractionRows.value = [createExtractionRow()];
  }
}

async function loadData() {
  loading.value = true;
  try {
    const toolRows = await fetchGlobalTools({
      business_group_id:
        selectedProjectId.value === ALL_FILTER_VALUE && selectedBusinessGroupId.value !== ALL_FILTER_VALUE
          ? selectedBusinessGroupId.value
          : null,
      project_id: selectedProjectId.value !== ALL_FILTER_VALUE ? selectedProjectId.value : null,
    });
    tools.value = Array.isArray(toolRows) ? toolRows : [];
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loading.value = false;
  }
}

watch(
  () => form.tool_type,
  (type) => {
    if (type === "http_request") {
      httpConfigTab.value = "body";
    }
  },
);

watch(
  [selectedBusinessGroupId, selectedProjectId],
  () => {
    void loadData();
  },
);

onMounted(async () => {
  await context.ensureLoaded();
  selectedProjectId.value = context.selectedProjectId.value ?? ALL_FILTER_VALUE;
  selectedBusinessGroupId.value = context.selectedProjectId.value
    ? (context.selectedGroupId.value ?? ALL_FILTER_VALUE)
    : ALL_FILTER_VALUE;
  await loadData();
});
</script>

<template>
  <div class="global-tool-page" v-loading="loading">
    <section class="scheduler-toolbar">
      <div class="filter-row">
        <span class="filter-label">业务/项目</span>
        <el-cascader
          v-model="selectedFilterPath"
          class="business-project-filter"
          :options="businessProjectOptions"
          :props="businessProjectFilterProps"
          clearable
          filterable
          placeholder="全部业务 / 项目"
          popper-class="compact-select-popper"
        />

        <span class="filter-label">工具类型</span>
        <el-select v-model="typeFilter" class="type-filter" clearable placeholder="全部工具">
          <el-option v-for="option in TOOL_OPTIONS" :key="option.type" :label="option.label" :value="option.type" />
        </el-select>

        <el-input
          v-model="keyword"
          clearable
          class="keyword-input"
          placeholder="搜索工具名称"
          :prefix-icon="Search"
        />

        <el-button size="small" :icon="RefreshRight" :loading="loading" @click="loadData">刷新</el-button>
        <el-button size="small" type="primary" :icon="Plus" @click="openCreateDialog">新增工具</el-button>
      </div>
    </section>

    <section class="task-list-section">
      <el-table
        :data="filteredTools"
        class="task-table"
        height="100%"
        cell-class-name="task-table-cell"
        header-cell-class-name="task-table-header-cell"
      >
        <el-table-column label="序号" width="76" align="center" header-align="center">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column
          label="工具名称"
          min-width="360"
          align="center"
          header-align="center"
          class-name="tool-name-column"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span class="tool-name-cell" :title="`${getToolTypePrefix(row.tool_type)} ${row.name}`">
              <span class="tool-type-prefix">{{ getToolTypePrefix(row.tool_type) }}</span>
              <span class="tool-name-text">{{ row.name }}</span>
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="business_group_name" label="业务" min-width="220" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ row.business_group_name || "-" }}</template>
        </el-table-column>
        <el-table-column prop="project_name" label="项目" min-width="220" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ row.project_name || "-" }}</template>
        </el-table-column>
        <el-table-column label="共享" width="100" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_shared ? 'success' : 'info'" effect="light">
              {{ row.is_shared ? "共享" : "私有" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="96" align="center" header-align="center">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" size="small" @change="toggleToolStatus(row)" />
          </template>
        </el-table-column>
        <el-table-column label="更新时间" min-width="240" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ row.updated_at || row.created_at || "-" }}</template>
        </el-table-column>
        <el-table-column label="操作" min-width="190" align="center" header-align="center">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button size="small" text type="primary" :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" text type="danger" :icon="Delete" @click="removeTool(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无全局工具" />
        </template>
      </el-table>
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="960px"
      destroy-on-close
      class="global-tool-dialog"
    >
      <el-form label-width="74px" class="global-tool-form" @submit.prevent>
        <div class="basic-grid">
          <el-form-item label="所属项目" required>
            <el-cascader
              v-model="formProjectPath"
              class="dialog-project-cascader"
              :options="businessProjectOptions"
              :props="businessProjectDialogProps"
              clearable
              filterable
              placeholder="请选择业务 / 项目"
              popper-class="compact-select-popper"
            />
          </el-form-item>
          <el-form-item label="共享">
            <el-switch v-model="form.is_shared" size="small" />
          </el-form-item>
          <el-form-item label="工具类型" required class="basic-grid-wide">
            <el-select v-model="form.tool_type" class="dialog-control" :disabled="Boolean(form.id)">
              <el-option v-for="option in TOOL_OPTIONS" :key="option.type" :label="option.label" :value="option.type" />
            </el-select>
          </el-form-item>
          <el-form-item label="名称" required class="basic-grid-wide">
            <el-input v-model="form.name" clearable maxlength="100" placeholder="请输入工具名称" />
          </el-form-item>
        </div>

        <CommonToolConfigForm
          :active="dialogVisible"
          :kind="form.tool_type"
          :form="form"
          :header-rows="headerRows"
          :rows="extractionRows"
          :database-connections="enabledDatabaseConnections"
          :database-schemas="sqlDatabaseSchemas"
          :database-schemas-loading="sqlDatabaseSchemasLoading"
          :http-tab="httpConfigTab"
          :show-name="false"
          @update:http-tab="httpConfigTab = $event"
          @database-change="handleDatabaseChange"
          @insert-header-row="insertHeaderRow"
          @remove-header-row="removeHeaderRow"
          @insert-row="insertExtractionRow"
          @remove-row="removeExtractionRow"
        />
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveTool">确定</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.global-tool-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  font-size: 12px;
}

.global-tool-page :deep(.el-table),
.global-tool-page :deep(.el-button),
.global-tool-page :deep(.el-input__inner),
.global-tool-page :deep(.el-select__placeholder),
.global-tool-page :deep(.el-select__selected-item),
.global-tool-page :deep(.el-form-item__label),
.global-tool-page :deep(.el-textarea__inner),
.global-tool-page :deep(.el-tabs__item),
.global-tool-page :deep(.el-tag) {
  font-size: 12px;
}

.scheduler-toolbar,
.task-list-section {
  border: 1px solid #e5edf6;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(31, 35, 41, 0.04);
}

.scheduler-toolbar {
  flex: 0 0 auto;
  padding: 14px 16px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.filter-label {
  flex: 0 0 auto;
  color: #4e5969;
  font-size: 12px;
  font-weight: 500;
}

.type-filter {
  width: 160px;
}

.business-project-filter {
  width: 220px;
}

.keyword-input {
  width: min(360px, 26vw);
  min-width: 220px;
}

.task-list-section {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  padding: 16px;
  overflow: hidden;
}

.task-table {
  flex: 1 1 0;
  width: 100%;
  min-width: 0;
  min-height: 0;
  border: 1px solid #edf1f6;
  border-radius: 8px;
}

.task-table :deep(.el-table__cell) {
  padding: 7px 0;
}

.task-table :deep(.task-table-header-cell .cell),
.task-table :deep(.task-table-cell .cell) {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  white-space: nowrap;
}

.task-table :deep(.tool-name-column .cell) {
  justify-content: flex-start;
  padding-left: 14px;
  padding-right: 14px;
}

.tool-name-cell {
  display: flex;
  width: 100%;
  max-width: 100%;
  justify-content: flex-start;
  align-items: center;
  gap: 6px;
  min-width: 0;
  text-align: left;
  vertical-align: middle;
}

.tool-type-prefix {
  flex: 0 0 auto;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
}

.tool-name-text {
  min-width: 0;
  overflow: hidden;
  color: #1f2937;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
}

.table-actions :deep(.el-button) {
  margin-left: 0;
  padding-left: 3px;
  padding-right: 3px;
}

.dialog-control {
  width: 100%;
}

.basic-grid {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(140px, 0.55fr);
  gap: 0 12px;
}

.basic-grid-wide {
  grid-column: 1 / -1;
}

.dialog-project-cascader {
  width: 100%;
}

.inline-control-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  min-height: 32px;
  flex-wrap: wrap;
}

.inline-label {
  color: #4e5969;
  font-size: 12px;
}

.field-unit {
  color: #6b7280;
  font-size: 12px;
}

.http-config-tabs {
  margin-top: 2px;
}

.section-block {
  margin-top: 12px;
}

.section-title {
  margin-bottom: 8px;
  color: #1f2937;
  font-size: 12px;
  font-weight: 600;
}

.config-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-row {
  display: grid;
  grid-template-columns: minmax(160px, 0.7fr) minmax(240px, 1fr) 76px;
  gap: 8px;
  align-items: center;
}

.config-row-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.python-code-editor {
  width: 100%;
  height: 300px;
  min-width: 0;
  overflow: hidden;
  border: 1px solid #1f2937;
  border-radius: 6px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.global-tool-dialog :deep(.el-dialog__body) {
  padding-top: 12px;
}

.global-tool-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.global-tool-form :deep(.el-form-item__label) {
  justify-content: flex-start;
}

.global-tool-form :deep(.common-tool-config-form) {
  margin-top: 0;
}

.global-tool-dialog :deep(.el-tabs__content) {
  min-height: 190px;
}

@media (max-width: 960px) {
  .filter-row {
    flex-wrap: wrap;
  }

  .basic-grid {
    grid-template-columns: 1fr;
  }

  .config-row {
    grid-template-columns: 1fr;
  }

  .keyword-input,
  .type-filter,
  .business-project-filter {
    width: 100%;
  }
}
</style>
