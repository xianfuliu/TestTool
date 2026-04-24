<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  ArrowLeft,
  ArrowRight,
  Delete,
  Edit,
  Folder,
  RefreshRight,
  Search,
  Tickets,
  VideoPlay,
  View,
} from "@element-plus/icons-vue";

import { get } from "@/shared/api/client";
import AppPagination from "@/shared/components/AppPagination.vue";
import CronExpressionBuilder from "@/shared/components/CronExpressionBuilder.vue";
import { useBusinessProjectContext } from "@/shared/composables/useBusinessProjectContext";
import {
  createSchedulerTask,
  runSchedulerTask,
  updateSchedulerTask,
  updateSchedulerTaskStatus,
  type SchedulerTaskPayload,
  type SchedulerTaskRecord,
} from "@/modules/scheduler/api";
import type { CaseFolder, TestCaseRecord } from "./types";
import {
  createTestSuite,
  deleteTestSuite,
  fetchTestSuiteDetail,
  fetchTestSuites,
  TEST_SUITE_SCHEDULER_SOURCE,
  updateTestSuite,
  type TestSuitePayload,
  type TestSuiteRecord,
} from "./testSuiteApi";

const ALL_PROJECT = 0;
const DEFAULT_CRON = "0 9 * * *";

type FolderTreeNode = {
  id: string;
  rawId: number | null;
  label: string;
  children?: FolderTreeNode[];
};

type SuiteForm = {
  id: number | null;
  scheduler_task_id: number | null;
  project_id: number | null;
  name: string;
  description: string;
  case_ids: number[];
  cron_expression: string;
  enabled: boolean;
  notify_emails: string;
  notify_webhook: string;
  allow_concurrent: boolean;
  timeout_seconds: number;
  retry_count: number;
  retry_interval_seconds: number;
};

const router = useRouter();
const context = useBusinessProjectContext();

const loading = ref(false);
const saving = ref(false);
const workspaceLoading = ref(false);
const runningSuiteIds = ref<Set<number>>(new Set());
const keyword = ref("");
const selectedProjectId = ref<number>(ALL_PROJECT);
const currentPage = ref(1);
const pageSize = ref(20);
const pageSizeOptions = [10, 20, 50, 100];
const suites = ref<TestSuiteRecord[]>([]);
const folders = ref<CaseFolder[]>([]);
const cases = ref<TestCaseRecord[]>([]);
const caseKeyword = ref("");
const selectedFolderId = ref<number | null>(null);
const availableSelection = ref<TestCaseRecord[]>([]);
const selectedSelection = ref<TestCaseRecord[]>([]);
const dialogVisible = ref(false);
const dialogTab = ref("basic");
const availableCaseTableRef = ref<any>(null);
const selectedCaseTableRef = ref<any>(null);

const form = reactive<SuiteForm>({
  id: null,
  scheduler_task_id: null,
  project_id: null,
  name: "",
  description: "",
  case_ids: [],
  cron_expression: DEFAULT_CRON,
  enabled: false,
  notify_emails: "",
  notify_webhook: "",
  allow_concurrent: false,
  timeout_seconds: 1800,
  retry_count: 0,
  retry_interval_seconds: 30,
});

const businessProjectCascaderProps = {
  emitPath: true,
};

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

const selectedProjectPath = computed<number[]>({
  get() {
    if (selectedProjectId.value === ALL_PROJECT) {
      return [];
    }
    const project = projectOptions.value.find((item) => item.id === selectedProjectId.value);
    return project?.business_group_id ? [project.business_group_id, project.id] : [selectedProjectId.value];
  },
  set(value) {
    selectedProjectId.value = value?.length ? value[value.length - 1] : ALL_PROJECT;
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

const selectedProject = computed(() => {
  if (!form.project_id) {
    return null;
  }
  return projectOptions.value.find((item) => item.id === form.project_id) ?? null;
});

const paginatedSuites = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return suites.value.slice(start, start + pageSize.value);
});

const folderTreeData = computed<FolderTreeNode[]>(() => [
  {
    id: "all",
    rawId: null,
    label: "全部用例",
    children: buildFolderTree(null),
  },
]);

const selectedCaseRows = computed(() => {
  const byId = new Map(cases.value.map((item) => [Number(item.id), item]));
  return form.case_ids.map((caseId) => byId.get(caseId)).filter(Boolean) as TestCaseRecord[];
});

const availableCases = computed(() => {
  const selectedIds = new Set(form.case_ids);
  const keywordText = caseKeyword.value.trim().toLowerCase();
  const folderIds = selectedFolderId.value === null ? null : collectFolderIds(selectedFolderId.value);
  return cases.value.filter((item) => {
    if (!item.id || selectedIds.has(item.id)) {
      return false;
    }
    if (folderIds && !folderIds.has(Number(item.folder_id))) {
      return false;
    }
    if (!keywordText) {
      return true;
    }
    return `${item.name} ${item.description || ""}`.toLowerCase().includes(keywordText);
  });
});

function buildFolderTree(parentId: number | null): FolderTreeNode[] {
  return folders.value
    .filter((item) => (item.parent_id ?? null) === parentId)
    .map((item) => {
      const children = buildFolderTree(item.id);
      return {
        id: `folder-${item.id}`,
        rawId: item.id,
        label: item.name,
        children: children.length ? children : undefined,
      };
    });
}

function collectFolderIds(folderId: number) {
  const ids = new Set<number>([folderId]);
  const queue = [folderId];
  while (queue.length) {
    const currentId = queue.shift();
    folders.value
      .filter((item) => item.parent_id === currentId)
      .forEach((item) => {
        ids.add(item.id);
        queue.push(item.id);
      });
  }
  return ids;
}

function resetForm() {
  const defaultProjectId =
    selectedProjectId.value !== ALL_PROJECT
      ? selectedProjectId.value
      : context.selectedProjectId.value ?? projectOptions.value[0]?.id ?? null;
  form.id = null;
  form.scheduler_task_id = null;
  form.project_id = defaultProjectId;
  form.name = "";
  form.description = "";
  form.case_ids = [];
  form.cron_expression = DEFAULT_CRON;
  form.enabled = false;
  form.notify_emails = "";
  form.notify_webhook = "";
  form.allow_concurrent = false;
  form.timeout_seconds = 1800;
  form.retry_count = 0;
  form.retry_interval_seconds = 30;
  caseKeyword.value = "";
  selectedFolderId.value = null;
  availableSelection.value = [];
  selectedSelection.value = [];
}

async function loadSuites() {
  loading.value = true;
  try {
    suites.value = await fetchTestSuites({
      project_id: selectedProjectId.value === ALL_PROJECT ? null : selectedProjectId.value,
      keyword: keyword.value.trim(),
    });
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loading.value = false;
  }
}

async function loadCaseWorkspace(projectId: number | null) {
  if (!projectId) {
    folders.value = [];
    cases.value = [];
    return;
  }
  workspaceLoading.value = true;
  try {
    const [folderRows, caseRows] = await Promise.all([
      get<CaseFolder[]>("/api/interface-auto/case-folders/", { project_id: projectId }),
      get<TestCaseRecord[]>("/api/interface-auto/cases/", { project_id: projectId }),
    ]);
    folders.value = folderRows;
    cases.value = caseRows;
    form.case_ids = form.case_ids.filter((caseId) => cases.value.some((item) => item.id === caseId));
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    workspaceLoading.value = false;
  }
}

async function handleSearch() {
  currentPage.value = 1;
  await loadSuites();
}

async function resetSearch() {
  keyword.value = "";
  selectedProjectId.value = context.selectedProjectId.value ?? ALL_PROJECT;
  currentPage.value = 1;
  await loadSuites();
}

async function openCreateDialog() {
  resetForm();
  if (!form.project_id) {
    ElMessage.warning("请先创建或选择项目");
    return;
  }
  dialogTab.value = "basic";
  dialogVisible.value = true;
  await loadCaseWorkspace(form.project_id);
}

async function openEditDialog(row: TestSuiteRecord) {
  saving.value = true;
  try {
    const detail = await fetchTestSuiteDetail(row.id);
    resetForm();
    form.id = detail.id;
    form.project_id = detail.project_id;
    form.name = detail.name;
    form.description = detail.description || "";
    form.case_ids = (detail.cases || []).map((item) => item.case_id);
    applySchedulerTaskToForm(detail.scheduler_task);
    const emails = Array.isArray(detail.scheduler_task?.notify_config?.emails)
      ? (detail.scheduler_task.notify_config.emails as unknown[]).join(",")
      : detail.notify_emails.join(",");
    form.notify_emails = emails;
    form.notify_webhook = String(detail.scheduler_task?.notify_config?.webhook_url || "");
    dialogTab.value = "basic";
    dialogVisible.value = true;
    await loadCaseWorkspace(detail.project_id);
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    saving.value = false;
  }
}

function applySchedulerTaskToForm(task: SchedulerTaskRecord | null) {
  form.scheduler_task_id = task?.id ?? null;
  form.cron_expression = task?.cron_expression || DEFAULT_CRON;
  form.enabled = Boolean(task?.enabled);
  form.allow_concurrent = Boolean(task?.allow_concurrent);
  form.timeout_seconds = Number(task?.timeout_seconds) || 1800;
  form.retry_count = Number(task?.retry_count) || 0;
  form.retry_interval_seconds = Number(task?.retry_interval_seconds) || 30;
}

function buildSuitePayload(): TestSuitePayload | null {
  if (!form.project_id) {
    ElMessage.warning("请选择所属项目");
    return null;
  }
  if (!form.name.trim()) {
    ElMessage.warning("请输入测试集名称");
    return null;
  }
  if (!form.case_ids.length) {
    ElMessage.warning("请至少选择一个测试用例");
    return null;
  }
  return {
    project_id: form.project_id,
    name: form.name.trim(),
    description: form.description.trim(),
    case_ids: [...form.case_ids],
    notify_emails: parseCommaList(form.notify_emails),
    email_config: {},
  };
}

function buildSchedulerPayload(suiteId: number): SchedulerTaskPayload {
  const project = selectedProject.value ?? projectOptions.value.find((item) => item.id === form.project_id);
  return {
    business_group_id: project?.business_group_id ?? null,
    project_id: form.project_id,
    name: form.name.trim(),
    task_type: "test_suite",
    source_module: TEST_SUITE_SCHEDULER_SOURCE,
    source_id: suiteId,
    description: form.description.trim(),
    schedule_type: "cron",
    cron_expression: form.cron_expression.trim() || DEFAULT_CRON,
    interval_seconds: 0,
    run_at: null,
    timezone: "Asia/Shanghai",
    target_config: { suite_id: suiteId },
    notify_config: {
      emails: parseCommaList(form.notify_emails),
      webhook_url: form.notify_webhook.trim(),
    },
    misfire_policy: "fire_once",
    allow_concurrent: form.allow_concurrent,
    timeout_seconds: Number(form.timeout_seconds) || 1800,
    retry_count: Number(form.retry_count) || 0,
    retry_interval_seconds: Number(form.retry_interval_seconds) || 30,
    enabled: form.enabled,
  };
}

function buildRowSchedulerPayload(row: TestSuiteRecord, enabled = false): SchedulerTaskPayload {
  return {
    business_group_id: row.business_group_id ?? null,
    project_id: row.project_id,
    name: row.name,
    task_type: "test_suite",
    source_module: TEST_SUITE_SCHEDULER_SOURCE,
    source_id: row.id,
    description: row.description || "",
    schedule_type: "cron",
    cron_expression: row.scheduler_task?.cron_expression || DEFAULT_CRON,
    interval_seconds: 0,
    run_at: null,
    timezone: row.scheduler_task?.timezone || "Asia/Shanghai",
    target_config: { suite_id: row.id },
    notify_config: row.scheduler_task?.notify_config || {
      emails: row.notify_emails || [],
      webhook_url: "",
    },
    misfire_policy: row.scheduler_task?.misfire_policy || "fire_once",
    allow_concurrent: Boolean(row.scheduler_task?.allow_concurrent),
    timeout_seconds: Number(row.scheduler_task?.timeout_seconds) || 1800,
    retry_count: Number(row.scheduler_task?.retry_count) || 0,
    retry_interval_seconds: Number(row.scheduler_task?.retry_interval_seconds) || 30,
    enabled,
  };
}

async function saveSuite() {
  const suitePayload = buildSuitePayload();
  if (!suitePayload) {
    return;
  }
  saving.value = true;
  const wasEditing = Boolean(form.id);
  try {
    let suiteId = form.id;
    if (suiteId) {
      await updateTestSuite(suiteId, suitePayload);
    } else {
      const created = await createTestSuite(suitePayload);
      suiteId = created.suite_id;
      form.id = suiteId;
    }

    const schedulerPayload = buildSchedulerPayload(suiteId);
    if (form.scheduler_task_id) {
      await updateSchedulerTask(form.scheduler_task_id, schedulerPayload);
    } else {
      await createSchedulerTask(schedulerPayload);
    }

    ElMessage.success(wasEditing ? "测试集已更新" : "测试集已新增");
    dialogVisible.value = false;
    await loadSuites();
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    saving.value = false;
  }
}

async function removeSuite(row: TestSuiteRecord) {
  try {
    await ElMessageBox.confirm(`确定删除测试集「${row.name}」吗？关联的定时任务和执行记录也会一并清理。`, "删除确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    await deleteTestSuite(row.id);
    ElMessage.success("测试集已删除");
    await loadSuites();
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function ensureSchedulerTask(row: TestSuiteRecord, enabled = Boolean(row.scheduler_task?.enabled)) {
  if (row.scheduler_task?.id) {
    return row.scheduler_task.id;
  }
  const created = await createSchedulerTask(buildRowSchedulerPayload(row, enabled));
  await loadSuites();
  return created.task_id;
}

async function toggleSchedule(row: TestSuiteRecord, value: boolean | string | number) {
  const enabled = value === true || value === "true" || value === 1;
  const previous = Boolean(row.scheduler_task?.enabled);
  if (row.scheduler_task) {
    row.scheduler_task.enabled = enabled;
  }
  try {
    const taskId = await ensureSchedulerTask(row, enabled);
    const result = await updateSchedulerTaskStatus(taskId, enabled);
    const task = suites.value.find((item) => item.id === row.id)?.scheduler_task;
    if (task) {
      task.enabled = result.enabled;
      task.next_run_at = result.next_run_at;
    }
    ElMessage.success(enabled ? "调度已启用" : "调度已停用");
  } catch (error) {
    if (row.scheduler_task) {
      row.scheduler_task.enabled = previous;
    }
    ElMessage.error((error as Error).message);
  }
}

function handleToggleSchedule(row: TestSuiteRecord, value: boolean | string | number) {
  void toggleSchedule(row, value);
}

async function runSuiteNow(row: TestSuiteRecord) {
  runningSuiteIds.value = new Set(runningSuiteIds.value).add(row.id);
  try {
    const taskId = await ensureSchedulerTask(row);
    const result = await runSchedulerTask(taskId);
    ElMessage.success(result.message || "测试集已提交后台异步执行，请稍后在测试报告查看结果");
    await loadSuites();
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    const next = new Set(runningSuiteIds.value);
    next.delete(row.id);
    runningSuiteIds.value = next;
  }
}

async function openExecutionRecords(row: TestSuiteRecord) {
  await router.push({
    path: "/interface-auto/reports",
    query: { suiteId: row.id, projectId: row.project_id, keyword: row.name },
  });
}

function handleFolderNodeClick(node: FolderTreeNode) {
  selectedFolderId.value = node.rawId;
  availableSelection.value = [];
  availableCaseTableRef.value?.clearSelection?.();
}

function importSelectedCases() {
  if (!availableSelection.value.length) {
    ElMessage.warning("请选择需要导入的用例");
    return;
  }
  const next = [...form.case_ids];
  availableSelection.value.forEach((item) => {
    if (item.id && !next.includes(item.id)) {
      next.push(item.id);
    }
  });
  form.case_ids = next;
  availableSelection.value = [];
  availableCaseTableRef.value?.clearSelection?.();
}

function removeSelectedCases() {
  if (!selectedSelection.value.length) {
    ElMessage.warning("请选择需要移除的用例");
    return;
  }
  const removedIds = new Set(selectedSelection.value.map((item) => item.id).filter(Boolean));
  form.case_ids = form.case_ids.filter((caseId) => !removedIds.has(caseId));
  selectedSelection.value = [];
  selectedCaseTableRef.value?.clearSelection?.();
}

function handleAvailableSelectionChange(rows: TestCaseRecord[]) {
  availableSelection.value = rows;
}

function handleSelectedSelectionChange(rows: TestCaseRecord[]) {
  selectedSelection.value = rows;
}

async function handleDialogProjectChange(projectId: number | null) {
  form.case_ids = [];
  selectedFolderId.value = null;
  caseKeyword.value = "";
  await loadCaseWorkspace(projectId);
}

function parseCommaList(value: string) {
  return value
    .split(/[,，;\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatDate(value?: string | null) {
  if (!value) {
    return "-";
  }
  return String(value).replace("T", " ").slice(0, 19);
}

function schedulerEnabled(row: TestSuiteRecord) {
  return Boolean(row.scheduler_task?.enabled);
}

function runStatusType(status?: string) {
  if (status === "success") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  if (status === "running") {
    return "warning";
  }
  return "info";
}

function runStatusLabel(status?: string) {
  const map: Record<string, string> = {
    success: "成功",
    failed: "失败",
    running: "执行中",
    skipped: "跳过",
  };
  return status ? map[status] || status : "未执行";
}

function handlePageChange(page: number) {
  currentPage.value = page;
}

function handlePageSizeChange(size: number) {
  pageSize.value = size;
  currentPage.value = 1;
}

watch(selectedProjectId, async () => {
  currentPage.value = 1;
  await loadSuites();
});

onMounted(async () => {
  await context.ensureLoaded();
  selectedProjectId.value = context.selectedProjectId.value ?? ALL_PROJECT;
  await loadSuites();
});
</script>

<template>
  <div class="scheduler-page suite-page" v-loading="loading">
    <section class="scheduler-toolbar">
      <div class="filter-row">
        <span class="filter-label">业务/项目</span>
        <el-cascader
          v-model="selectedProjectPath"
          class="business-project-filter"
          :options="businessProjectOptions"
          :props="businessProjectCascaderProps"
          clearable
          filterable
          placeholder="全部业务 / 项目"
          popper-class="compact-select-popper"
        />

        <el-input
          v-model="keyword"
          clearable
          class="keyword-input"
          placeholder="搜索测试集名称 / 描述"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-button size="small" :icon="RefreshRight" :loading="loading" @click="loadSuites">刷新</el-button>
        <el-button size="small" type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button size="small" @click="resetSearch">重置</el-button>
        <el-button size="small" type="primary" :icon="Tickets" @click="openCreateDialog">新增测试集</el-button>
      </div>
    </section>

    <section class="task-list-section">
      <el-table
        :data="paginatedSuites"
        class="task-table"
        height="100%"
        cell-class-name="task-table-cell"
        header-cell-class-name="task-table-header-cell"
      >
        <el-table-column label="序号" width="70" align="center" header-align="center">
          <template #default="{ $index }">{{ (currentPage - 1) * pageSize + $index + 1 }}</template>
        </el-table-column>
        <el-table-column label="测试集名称" min-width="210" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="suite-name-cell" :title="row.name">
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="project_name" label="项目" width="120" align="center" header-align="center" show-overflow-tooltip />
        <el-table-column label="调度规则" width="150" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mono-text">{{ row.scheduler_task?.cron_expression || "-" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="用例数量" width="92" align="center" header-align="center">
          <template #default="{ row }">{{ row.case_count || 0 }}</template>
        </el-table-column>
        <el-table-column label="上次执行" width="160" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ formatDate(row.scheduler_task?.last_run_at) }}</template>
        </el-table-column>
        <el-table-column label="下次执行" width="160" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ formatDate(row.scheduler_task?.next_run_at) }}</template>
        </el-table-column>
        <el-table-column label="更新时间" width="160" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="上次结果" width="96" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="runStatusType(row.scheduler_task?.last_run_status)" effect="light">
              {{ runStatusLabel(row.scheduler_task?.last_run_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="92" align="center" header-align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="schedulerEnabled(row)"
              size="small"
              @change="handleToggleSchedule(row, $event)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right" align="center" header-align="center">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button
                size="small"
                text
                type="primary"
                :icon="VideoPlay"
                :loading="runningSuiteIds.has(row.id)"
                @click="runSuiteNow(row)"
              >
                执行
              </el-button>
              <el-button size="small" text :icon="View" @click="openExecutionRecords(row)">记录</el-button>
              <el-button size="small" text type="primary" :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" text type="danger" :icon="Delete" @click="removeSuite(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无测试集" />
        </template>
      </el-table>

      <AppPagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="suites.length"
        :page-sizes="pageSizeOptions"
        @current-change="handlePageChange"
        @size-change="handlePageSizeChange"
      />
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '编辑测试集' : '新增测试集'"
      width="1120px"
      destroy-on-close
      class="suite-dialog"
    >
      <el-tabs v-model="dialogTab">
        <el-tab-pane label="基本信息" name="basic">
          <el-form label-width="86px" class="suite-form" @submit.prevent>
            <div class="basic-grid">
              <el-form-item label="所属项目" required>
                <el-cascader
                  v-model="formProjectPath"
                  class="dialog-project-cascader"
                  :options="businessProjectOptions"
                  :props="businessProjectCascaderProps"
                  clearable
                  filterable
                  placeholder="请选择业务 / 项目"
                  popper-class="compact-select-popper"
                  :disabled="Boolean(form.id)"
                />
              </el-form-item>
              <el-form-item label="测试集名称" required>
                <el-input v-model="form.name" clearable maxlength="100" placeholder="请输入测试集名称" />
              </el-form-item>
            </div>
            <el-form-item label="测试集描述">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="2"
                maxlength="500"
                show-word-limit
                placeholder="请输入测试集描述（可选）"
              />
            </el-form-item>
          </el-form>

          <div class="case-picker" v-loading="workspaceLoading">
            <section class="case-column folder-column">
              <div class="column-title">目录</div>
              <el-tree
                class="folder-tree"
                node-key="id"
                :data="folderTreeData"
                :default-expanded-keys="['all']"
                default-expand-all
                highlight-current
                @node-click="handleFolderNodeClick"
              >
                <template #default="{ data }">
                  <span class="folder-tree-node">
                    <el-icon class="folder-tree-icon"><Folder /></el-icon>
                    <span class="folder-tree-label">{{ data.label }}</span>
                  </span>
                </template>
              </el-tree>
            </section>

            <section class="case-column available-column">
              <div class="column-head">
                <span class="column-title">选择用例</span>
                <el-input
                  v-model="caseKeyword"
                  clearable
                  size="small"
                  class="case-search"
                  placeholder="搜索用例"
                  :prefix-icon="Search"
                />
              </div>
              <el-table
                ref="availableCaseTableRef"
                :data="availableCases"
                height="360"
                size="small"
                empty-text="暂无可选用例"
                @selection-change="handleAvailableSelectionChange"
              >
                <el-table-column type="selection" width="38" />
                <el-table-column prop="name" label="用例名称" min-width="160" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span class="case-name-cell">
                      <el-icon class="case-mark-icon"><Tickets /></el-icon>
                      <span class="case-name-text">{{ row.name }}</span>
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </section>

            <div class="case-transfer">
              <el-button circle :icon="ArrowRight" @click="importSelectedCases" />
              <el-button circle :icon="ArrowLeft" @click="removeSelectedCases" />
            </div>

            <section class="case-column selected-column">
              <div class="column-title">已选用例（{{ selectedCaseRows.length }}）</div>
              <el-table
                ref="selectedCaseTableRef"
                :data="selectedCaseRows"
                height="360"
                size="small"
                empty-text="暂无已选用例"
                @selection-change="handleSelectedSelectionChange"
              >
                <el-table-column type="selection" width="38" />
                <el-table-column prop="name" label="用例名称" min-width="170" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span class="case-name-cell">
                      <el-icon class="case-mark-icon"><Tickets /></el-icon>
                      <span class="case-name-text">{{ row.name }}</span>
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </section>
          </div>
        </el-tab-pane>

        <el-tab-pane label="调度配置" name="schedule">
          <div class="schedule-panel">
            <el-form label-width="112px" class="suite-form">
              <el-form-item label="Cron表达式" required>
                <CronExpressionBuilder v-model="form.cron_expression" />
              </el-form-item>
              <div class="advanced-grid">
                <el-form-item label="超时时间">
                  <el-input-number v-model="form.timeout_seconds" :min="60" :max="86400" :step="60" />
                  <span class="field-unit">秒</span>
                </el-form-item>
                <el-form-item label="失败重试">
                  <el-input-number v-model="form.retry_count" :min="0" :max="10" />
                  <span class="field-unit">次</span>
                </el-form-item>
                <el-form-item label="重试间隔">
                  <el-input-number v-model="form.retry_interval_seconds" :min="0" :max="3600" :step="5" />
                  <span class="field-unit">秒</span>
                </el-form-item>
                <el-form-item label="并发执行">
                  <el-switch v-model="form.allow_concurrent" inline-prompt active-text="允许" inactive-text="禁止" />
                </el-form-item>
              </div>
            </el-form>
          </div>
        </el-tab-pane>

        <el-tab-pane label="通知配置" name="notify">
          <el-form label-width="112px" class="suite-form notify-form">
            <el-form-item label="通知邮箱">
              <el-input
                v-model="form.notify_emails"
                type="textarea"
                :rows="4"
                placeholder="多个邮箱可用逗号、分号或换行分隔"
              />
            </el-form-item>
            <el-form-item label="Webhook">
              <el-input v-model="form.notify_webhook" clearable placeholder="请输入通知 Webhook 地址（可选）" />
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveSuite">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.scheduler-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  font-size: 12px;
}

.suite-page {
  min-height: 0;
}

.scheduler-page :deep(.el-table),
.scheduler-page :deep(.el-button),
.scheduler-page :deep(.el-input__inner),
.scheduler-page :deep(.el-select__placeholder),
.scheduler-page :deep(.el-select__selected-item),
.scheduler-page :deep(.el-form-item__label),
.scheduler-page :deep(.el-textarea__inner),
.scheduler-page :deep(.el-tabs__item),
.scheduler-page :deep(.el-tag),
.scheduler-page :deep(.el-pagination) {
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

.filter-row,
.column-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-row {
  min-width: 0;
}

.filter-label {
  flex: 0 0 auto;
  color: #4e5969;
  font-size: 12px;
  font-weight: 500;
}

.filter-select {
  width: 180px;
}

.business-project-filter {
  width: 220px;
}

.dialog-project-cascader {
  width: 100%;
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

.suite-name-cell {
  display: inline-flex;
  width: min(220px, 100%);
  justify-content: flex-start;
  min-width: 0;
  text-align: left;
  vertical-align: middle;
}

.suite-name-cell span {
  min-width: 0;
  overflow: hidden;
  color: #111827;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mono-text {
  color: #334155;
  font-family: Consolas, "Liberation Mono", monospace;
  font-size: 12px;
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

.basic-grid,
.advanced-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 18px;
}

.case-picker {
  display: grid;
  grid-template-columns: minmax(210px, 0.9fr) minmax(260px, 1.1fr) 48px minmax(280px, 1fr);
  gap: 12px;
  min-height: 420px;
  margin-top: 8px;
}

.case-column {
  min-width: 0;
}

.column-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  color: #303133;
  font-size: 13px;
  font-weight: 600;
  line-height: 28px;
}

.column-head {
  justify-content: flex-start;
}

.case-search {
  width: 150px;
}

.folder-tree {
  height: 360px;
  padding: 8px 0;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: auto;
}

.folder-tree-node,
.case-name-cell {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  max-width: 100%;
  gap: 6px;
}

.folder-tree-icon {
  flex: 0 0 auto;
  color: #8a97a8;
  font-size: 14px;
}

.folder-tree-label,
.case-name-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.case-mark-icon {
  flex: 0 0 auto;
  color: #1677ff;
  font-size: 14px;
}

.case-transfer {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
}

.case-transfer .el-button + .el-button {
  margin-left: 0;
}

.schedule-panel {
  padding: 4px 0 8px;
}

.field-unit {
  margin-left: 8px;
  color: #697586;
  font-size: 13px;
}

.notify-form {
  max-width: 720px;
}

@media (max-width: 1080px) {
  .filter-row {
    align-items: stretch;
    flex-wrap: wrap;
  }

  .keyword-input {
    width: 100%;
    min-width: 0;
  }

  .basic-grid,
  .advanced-grid,
  .case-picker {
    grid-template-columns: 1fr;
  }

  .case-transfer {
    flex-direction: row;
  }
}
</style>
