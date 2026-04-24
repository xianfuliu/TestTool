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

import { fetchEnvironments } from "@/modules/common/environmentApi";
import type { EnvironmentRecord } from "@/modules/common/environmentTypes";
import { useBusinessProjectContext } from "@/shared/composables/useBusinessProjectContext";
import {
  createGlobalVariable,
  deleteGlobalVariable,
  fetchGlobalVariables,
  updateGlobalVariable,
} from "./variableApi";
import type {
  GlobalVariablePayload,
  GlobalVariableRecord,
} from "./types";

type VariableTypeOption = {
  value: string;
  label: string;
};

const ALL_FILTER_VALUE = 0;

const VARIABLE_TYPE_OPTIONS: VariableTypeOption[] = [
  { value: "string", label: "字符串" },
  { value: "int", label: "整数" },
  { value: "float", label: "浮点数" },
  { value: "bool", label: "布尔值" },
  { value: "json", label: "JSON" },
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
const selectedBusinessGroupId = ref<number>(ALL_FILTER_VALUE);
const selectedProjectId = ref<number>(ALL_FILTER_VALUE);
const selectedEnvironmentId = ref<number>(ALL_FILTER_VALUE);
const variables = ref<GlobalVariableRecord[]>([]);
const environments = ref<EnvironmentRecord[]>([]);
const dialogVisible = ref(false);
const dialogTitle = ref("");

const form = reactive({
  id: null as number | null,
  project_id: null as number | null,
  environment_ids: [] as number[],
  name: "",
  value: "",
  variable_type: "string",
});

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

const environmentOptions = computed(() => environments.value);
const allEnvironmentIds = computed(() =>
  environmentOptions.value
    .map((item) => Number(item.id))
    .filter((item) => Number.isFinite(item) && item > 0),
);
const filteredVariables = computed(() => {
  const text = keyword.value.trim().toLowerCase();
  if (!text) {
    return variables.value;
  }
  return variables.value.filter((item) =>
    `${item.name} ${item.value ?? ""} ${item.project_name ?? ""} ${item.business_group_name ?? ""} ${(item.environment_names ?? []).join(" ")}`
      .toLowerCase()
      .includes(text),
  );
});

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
  set(value) {
    form.project_id = value?.length ? value[value.length - 1] : null;
  },
});

function getDefaultProjectId() {
  if (selectedProjectId.value !== ALL_FILTER_VALUE) {
    return selectedProjectId.value;
  }
  if (context.selectedProjectId.value) {
    return context.selectedProjectId.value;
  }
  return projectOptions.value[0]?.id ?? null;
}

function getDefaultEnvironmentFilterId() {
  if (selectedEnvironmentId.value !== ALL_FILTER_VALUE) {
    return selectedEnvironmentId.value;
  }
  return allEnvironmentIds.value[0] ?? ALL_FILTER_VALUE;
}

function getDefaultEnvironmentIds() {
  return [...allEnvironmentIds.value];
}

function resetForm() {
  form.id = null;
  form.project_id = getDefaultProjectId();
  form.environment_ids = getDefaultEnvironmentIds();
  form.name = "";
  form.value = "";
  form.variable_type = "string";
}

function fillForm(variable: GlobalVariableRecord) {
  resetForm();
  form.id = variable.id;
  form.project_id = variable.project_id;
  form.environment_ids = Array.isArray(variable.environment_ids) ? [...variable.environment_ids] : [];
  form.name = variable.name;
  form.value = variable.value ?? "";
  form.variable_type = variable.variable_type || "string";
}

function getVariableTypeLabel(type: string) {
  return VARIABLE_TYPE_OPTIONS.find((item) => item.value === type)?.label ?? type;
}

function formatEnvironmentNames(row: GlobalVariableRecord) {
  const names = Array.isArray(row.environment_names) ? row.environment_names.filter(Boolean) : [];
  if (!names.length) {
    return "-";
  }
  if (allEnvironmentIds.value.length > 1 && Array.isArray(row.environment_ids) && row.environment_ids.length === allEnvironmentIds.value.length) {
    return "全部环境";
  }
  return names.join(" / ");
}

function buildPayload(): GlobalVariablePayload | null {
  if (!form.project_id) {
    ElMessage.warning("请选择所属项目");
    return null;
  }
  const name = form.name.trim();
  if (!name) {
    ElMessage.warning("请输入变量名称");
    return null;
  }
  const environmentIds = form.environment_ids.length ? [...form.environment_ids] : getDefaultEnvironmentIds();
  if (!environmentIds.length) {
    ElMessage.warning("请至少选择一个所属环境");
    return null;
  }
  return {
    project_id: form.project_id,
    environment_ids: environmentIds,
    name,
    value: form.value ?? "",
    variable_type: form.variable_type,
    description: "",
  };
}

async function loadEnvironments() {
  const rows = await fetchEnvironments();
  environments.value = Array.isArray(rows) ? rows : [];
  if (selectedEnvironmentId.value === ALL_FILTER_VALUE && environments.value.length) {
    selectedEnvironmentId.value = getDefaultEnvironmentFilterId();
  }
}

async function loadData() {
  loading.value = true;
  try {
    const rows = await fetchGlobalVariables({
      business_group_id: selectedBusinessGroupId.value === ALL_FILTER_VALUE ? null : selectedBusinessGroupId.value,
      project_id: selectedProjectId.value === ALL_FILTER_VALUE ? null : selectedProjectId.value,
      environment_id: selectedEnvironmentId.value === ALL_FILTER_VALUE ? null : selectedEnvironmentId.value,
    });
    variables.value = Array.isArray(rows) ? rows : [];
  } finally {
    loading.value = false;
  }
}

async function openCreateDialog() {
  resetForm();
  dialogTitle.value = "新增全局变量";
  dialogVisible.value = true;
}

function openEditDialog(variable: GlobalVariableRecord) {
  fillForm(variable);
  dialogTitle.value = "编辑全局变量";
  dialogVisible.value = true;
}

async function saveVariable() {
  const payload = buildPayload();
  if (!payload) {
    return;
  }
  saving.value = true;
  try {
    if (form.id) {
      await updateGlobalVariable(form.id, payload);
      ElMessage.success("全局变量已更新");
    } else {
      await createGlobalVariable(payload);
      ElMessage.success("全局变量已创建");
    }
    dialogVisible.value = false;
    await loadData();
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    saving.value = false;
  }
}

async function removeVariable(variable: GlobalVariableRecord) {
  try {
    await ElMessageBox.confirm(`确认删除变量“${variable.name}”吗？`, "删除全局变量", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
    await deleteGlobalVariable(variable.id);
    ElMessage.success("全局变量已删除");
    await loadData();
  } catch (error) {
    if (error !== "cancel") {
      ElMessage.error((error as Error).message);
    }
  }
}

watch(
  [selectedBusinessGroupId, selectedProjectId, selectedEnvironmentId],
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
  await loadEnvironments();
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

        <span class="filter-label">环境</span>
        <el-select v-model="selectedEnvironmentId" class="environment-filter" clearable placeholder="全部环境">
          <el-option
            v-for="item in environmentOptions"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>

        <el-input
          v-model="keyword"
          clearable
          class="keyword-input"
          placeholder="搜索变量名称"
          :prefix-icon="Search"
        />

        <el-button size="small" :icon="RefreshRight" :loading="loading" @click="loadData">刷新</el-button>
        <el-button size="small" type="primary" :icon="Plus" @click="openCreateDialog">新增变量</el-button>
      </div>
    </section>

    <section class="task-list-section">
      <el-table
        :data="filteredVariables"
        class="task-table"
        height="100%"
        cell-class-name="task-table-cell"
        header-cell-class-name="task-table-header-cell"
      >
        <el-table-column label="序号" width="76" align="center" header-align="center">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column
          label="变量名称"
          min-width="220"
          align="center"
          header-align="center"
          class-name="name-column"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span class="name-cell" :title="row.name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="变量值" min-width="280" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="value-cell" :title="row.value">{{ row.value || "-" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="light">{{ getVariableTypeLabel(row.variable_type || "string") }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="business_group_name" label="业务" min-width="160" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ row.business_group_name || "-" }}</template>
        </el-table-column>
        <el-table-column prop="project_name" label="项目" min-width="160" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ row.project_name || "-" }}</template>
        </el-table-column>
        <el-table-column label="环境" min-width="220" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ formatEnvironmentNames(row) }}</template>
        </el-table-column>
        <el-table-column label="更新时间" min-width="180" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ row.updated_at || row.created_at || "-" }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center" header-align="center">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button size="small" text type="primary" :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" text type="danger" :icon="Delete" @click="removeVariable(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无全局变量" />
        </template>
      </el-table>
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="720px"
      destroy-on-close
      class="global-tool-dialog"
    >
      <el-form label-width="74px" class="global-tool-form" @submit.prevent>
        <div class="basic-grid">
          <el-form-item label="所属项目" required class="basic-grid-wide">
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
          <el-form-item label="所属环境" required class="basic-grid-wide">
            <el-select
              v-model="form.environment_ids"
              class="dialog-control"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="默认关联全部环境"
            >
              <el-option
                v-for="item in environmentOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="名称" required>
            <el-input v-model="form.name" clearable maxlength="100" placeholder="请输入变量名称" />
          </el-form-item>
          <el-form-item label="类型" required>
            <el-select v-model="form.variable_type" class="dialog-control">
              <el-option
                v-for="option in VARIABLE_TYPE_OPTIONS"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="变量值" required class="basic-grid-wide">
            <el-input
              v-model="form.value"
              type="textarea"
              :rows="6"
              resize="none"
              placeholder="请输入变量值"
            />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveVariable">确定</el-button>
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

.business-project-filter {
  width: 220px;
}

.environment-filter {
  width: 160px;
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

.task-table :deep(.name-column .cell) {
  justify-content: flex-start;
  padding-left: 14px;
  padding-right: 14px;
}

.name-cell,
.value-cell {
  display: inline-flex;
  width: 100%;
  min-width: 0;
  overflow: hidden;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.name-cell {
  color: #1f2937;
  font-weight: 600;
}

.value-cell {
  color: #475569;
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

.dialog-control,
.dialog-project-cascader {
  width: 100%;
}

.basic-grid {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(180px, 0.7fr);
  gap: 0 12px;
}

.basic-grid-wide {
  grid-column: 1 / -1;
}
</style>
