<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Back, Delete, Document, RefreshRight, Search, View } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";

import AppPagination from "@/shared/components/AppPagination.vue";
import ExecutionLogViewer from "@/shared/components/ExecutionLogViewer.vue";
import ExecutionReportSummary from "@/shared/components/ExecutionReportSummary.vue";
import { useBusinessProjectContext } from "@/shared/composables/useBusinessProjectContext";
import {
  deleteTestReport,
  fetchTestReportDetail,
  fetchTestReportGroupRecords,
  fetchTestReportGroups,
  type ReportCaseItem,
  type ReportCaseStep,
  type TestReportDetail,
  type TestReportGroup,
  type TestReportRecord,
} from "./reportApi";

const ALL_PROJECT = 0;

const route = useRoute();
const router = useRouter();
const context = useBusinessProjectContext();

const loading = ref(false);
const detailLoading = ref(false);
const reports = ref<TestReportGroup[]>([]);
const detail = ref<TestReportDetail | null>(null);
const keyword = ref("");
const selectedProjectId = ref<number>(ALL_PROJECT);
const suiteFilterId = ref<number | null>(null);
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);
const pageSizeOptions = [10, 20, 50, 100];
const recordPageSizeOptions = [10, 20, 50];
const expandedCaseKeys = ref<string[]>([]);
const expandedGroupKeys = ref<string[]>([]);
const reportTableRef = ref<any>(null);

type GroupRecordState = {
  items: TestReportRecord[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
  loaded: boolean;
};

type ReportDeleteTarget = TestReportRecord | TestReportGroup;

const emptyGroupRecordState: GroupRecordState = {
  items: [],
  total: 0,
  page: 1,
  pageSize: 10,
  loading: false,
  loaded: false,
};

const groupRecordStates = ref<Record<string, GroupRecordState>>({});

const businessProjectOptions = computed(() =>
  context.groups.value.map((group) => ({
    value: group.id,
    label: group.name,
    children: context.projects.value
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
    const project = context.projects.value.find((item) => item.id === selectedProjectId.value);
    return project?.business_group_id ? [project.business_group_id, project.id] : [selectedProjectId.value];
  },
  set(value) {
    selectedProjectId.value = value?.length ? value[value.length - 1] : ALL_PROJECT;
  },
});

const detailCases = computed(() => detail.value?.cases || []);

function queryText(value: unknown) {
  if (Array.isArray(value)) {
    return value[0] === null || value[0] === undefined ? "" : String(value[0]);
  }
  return value === null || value === undefined ? "" : String(value);
}

function syncQueryFilters() {
  const rawSuiteId = Number(route.query.suiteId);
  suiteFilterId.value = Number.isFinite(rawSuiteId) && rawSuiteId > 0 ? rawSuiteId : null;
  const rawProjectId = Number(route.query.projectId);
  if (Number.isFinite(rawProjectId) && rawProjectId > 0) {
    selectedProjectId.value = rawProjectId;
  }
  keyword.value = queryText(route.query.keyword);
}

async function loadReports() {
  collapseAllReportRows();
  loading.value = true;
  try {
    const result = await fetchTestReportGroups({
      project_id: selectedProjectId.value === ALL_PROJECT ? null : selectedProjectId.value,
      suite_id: suiteFilterId.value,
      keyword: keyword.value.trim(),
      page: currentPage.value,
      page_size: pageSize.value,
    });
    reports.value = result.data;
    total.value = result.pagination.total;
    groupRecordStates.value = {};
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loading.value = false;
  }
}

async function loadReportDetail(reportId: number) {
  detailLoading.value = true;
  try {
    detail.value = await fetchTestReportDetail(reportId);
    expandedCaseKeys.value = [];
  } catch (error) {
    ElMessage.error((error as Error).message);
    detail.value = null;
  } finally {
    detailLoading.value = false;
  }
}

async function handleSearch() {
  currentPage.value = 1;
  await loadReports();
}

async function resetSearch() {
  selectedProjectId.value = ALL_PROJECT;
  keyword.value = "";
  currentPage.value = 1;
  await router.replace({ path: "/interface-auto/reports" });
  suiteFilterId.value = null;
  await loadReports();
}

async function refreshReports() {
  await loadReports();
  const reportId = Number(route.query.reportId);
  if (Number.isFinite(reportId) && reportId > 0) {
    await loadReportDetail(reportId);
  }
}

async function openDetail(row: TestReportRecord) {
  await openReportDetail(row.id);
}

async function openReportDetail(reportId: number) {
  if (Number(route.query.reportId) === reportId) {
    await loadReportDetail(reportId);
    return;
  }
  await router.push({
    path: "/interface-auto/reports",
    query: {
      ...route.query,
      reportId,
    },
  });
}

async function openLatestDetail(row: TestReportGroup) {
  if (!row.latest_report_id) {
    ElMessage.warning("当前测试集暂无执行记录");
    return;
  }
  await openReportDetail(row.latest_report_id);
}

function toggleGroupRow(row: TestReportGroup) {
  reportTableRef.value?.toggleRowExpansion?.(row);
}

function collapseAllReportRows() {
  expandedGroupKeys.value = [];
  groupRecordStates.value = {};
  reports.value.forEach((row) => reportTableRef.value?.toggleRowExpansion?.(row, false));
}

function handleGroupRowClick(row: TestReportGroup, column: { type?: string } | undefined) {
  if (column?.type === "expand") {
    return;
  }
  toggleGroupRow(row);
}

async function handleGroupExpandChange(row: TestReportGroup, expandedRows: TestReportGroup[]) {
  const expanded = expandedRows.some((item) => item.key === row.key);
  expandedGroupKeys.value = expandedRows.map((item) => item.key);
  const state = getGroupRecordState(row);
  if (expanded && !state.loaded && !state.loading) {
    await loadGroupRecords(row, { page: 1 });
  }
}

function getGroupRecordState(row: TestReportGroup) {
  return groupRecordStates.value[row.key] || emptyGroupRecordState;
}

async function loadGroupRecords(row: TestReportGroup, options: { page?: number; pageSize?: number } = {}) {
  const previous = getGroupRecordState(row);
  const page = options.page ?? previous.page;
  const pageSize = options.pageSize ?? previous.pageSize;
  if (Number(row.report_count || 0) <= 1 || (!row.suite_id && !row.case_id)) {
    groupRecordStates.value = {
      ...groupRecordStates.value,
      [row.key]: {
        items: [],
        total: 0,
        page: 1,
        pageSize,
        loading: false,
        loaded: true,
      },
    };
    return;
  }
  groupRecordStates.value = {
    ...groupRecordStates.value,
    [row.key]: {
      ...previous,
      page,
      pageSize,
      loading: true,
    },
  };
  try {
    const result = await fetchTestReportGroupRecords({
      suite_id: row.suite_id || null,
      case_id: row.suite_id ? null : row.case_id || null,
      keyword: keyword.value.trim(),
      page,
      page_size: pageSize,
      skip_latest: true,
    });
    groupRecordStates.value = {
      ...groupRecordStates.value,
      [row.key]: {
        items: result.data,
        total: result.pagination.total,
        page: result.pagination.page,
        pageSize: result.pagination.page_size,
        loading: false,
        loaded: true,
      },
    };
  } catch (error) {
    groupRecordStates.value = {
      ...groupRecordStates.value,
      [row.key]: {
        ...previous,
        page,
        pageSize,
        loading: false,
        loaded: true,
      },
    };
    ElMessage.error((error as Error).message);
  }
}

async function backToList() {
  const nextQuery = { ...route.query };
  delete nextQuery.reportId;
  await router.push({ path: "/interface-auto/reports", query: nextQuery });
  detail.value = null;
}

async function removeReport(row: TestReportRecord) {
  await removeReportTarget(row);
}

async function removeLatestReport(row: TestReportGroup) {
  await removeReportTarget(row);
}

async function removeHistoryReport(row: TestReportRecord, group: TestReportGroup) {
  await removeReportTarget(row, group);
}

async function removeReportTarget(row: ReportDeleteTarget, sourceGroup?: TestReportGroup) {
  const reportId = getReportDeleteId(row);
  if (!reportId) {
    ElMessage.warning("当前执行记录不存在");
    return;
  }
  const reportName = getReportDeleteName(row);
  try {
    await ElMessageBox.confirm(`确定删除测试报告「${reportName}」吗？`, "删除确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    await deleteTestReport(reportId);
    ElMessage.success("测试报告已删除");
    if (detail.value?.id === reportId) {
      await backToList();
    }
    if (sourceGroup) {
      const state = getGroupRecordState(sourceGroup);
      const nextTotal = Math.max(0, state.total - 1);
      const nextPage = state.page > 1 && (state.page - 1) * state.pageSize >= nextTotal ? state.page - 1 : state.page;
      await loadGroupRecords(sourceGroup, { page: nextPage, pageSize: state.pageSize });
    } else {
      await loadReports();
    }
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

function getReportDeleteId(row: ReportDeleteTarget) {
  return "id" in row ? row.id : Number(row.latest_report_id || 0);
}

function getReportDeleteName(row: ReportDeleteTarget) {
  if ("report_name" in row) {
    return row.report_name;
  }
  return row.latest_report_name || groupName(row);
}

function handlePageChange() {
  void loadReports();
}

function handlePageSizeChange() {
  currentPage.value = 1;
  void loadReports();
}

function statusType(status?: string) {
  if (status === "success") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  if (status === "running") {
    return "primary";
  }
  if (status === "skipped") {
    return "warning";
  }
  return "info";
}

function statusLabel(status?: string) {
  const map: Record<string, string> = {
    success: "成功",
    failed: "失败",
    running: "执行中",
    skipped: "跳过",
    pending: "待执行",
  };
  return status ? map[status] || status : "未知";
}

function statusEnglish(status?: string) {
  const map: Record<string, string> = {
    success: "SUCCESS",
    failed: "FAIL",
    running: "RUNNING",
    skipped: "SKIPPED",
    pending: "PENDING",
  };
  return status ? map[status] || status.toUpperCase() : "UNKNOWN";
}

function formatDate(value?: string | null) {
  if (!value) {
    return "-";
  }
  return String(value).replace("T", " ").slice(0, 19);
}

function formatDuration(value?: number) {
  const seconds = Number(value || 0);
  if (!seconds) {
    return "-";
  }
  if (seconds < 1) {
    return `${Math.round(seconds * 1000)}ms`;
  }
  if (seconds < 60) {
    return `${seconds.toFixed(2)}s`;
  }
  return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
}

function numberValue(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : null;
}

function durationFromRange(startValue: unknown, endValue: unknown) {
  if (!startValue || !endValue) {
    return null;
  }
  const start = new Date(String(startValue).replace(" ", "T"));
  const end = new Date(String(endValue).replace(" ", "T"));
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return null;
  }
  const seconds = (end.getTime() - start.getTime()) / 1000;
  return seconds >= 0 ? seconds : null;
}

function durationFromRecord(record: Record<string, unknown> | null | undefined) {
  if (!record) {
    return null;
  }
  for (const key of ["duration", "execution_time", "duration_seconds", "elapsed_seconds"]) {
    const seconds = numberValue(record[key]);
    if (seconds !== null) {
      return seconds;
    }
  }
  const milliseconds = numberValue(record.duration_ms ?? record.elapsed_ms);
  if (milliseconds !== null) {
    return milliseconds / 1000;
  }
  return durationFromRange(record.started_at ?? record.start_time, record.ended_at ?? record.end_time);
}

function passRate(row: { total_cases?: number; passed_cases?: number }) {
  const totalCases = Number(row.total_cases || 0);
  if (!totalCases) {
    return "-";
  }
  return `${Math.round((Number(row.passed_cases || 0) / totalCases) * 100)}%`;
}

function groupName(row: TestReportGroup) {
  return row.suite_name || row.name || row.case_name || "未命名测试集";
}

function recordGroupName(row: TestReportRecord, group: TestReportGroup) {
  return row.suite_name || group.suite_name || group.name || row.case_name || group.case_name || "未命名测试集";
}


function caseStepRows(caseItem: ReportCaseItem): ReportCaseStep[] {
  const structuredSteps = Array.isArray(caseItem.execution_log?.steps) ? caseItem.execution_log.steps : [];
  return (structuredSteps.length ? structuredSteps : caseItem.steps || []) as ReportCaseStep[];
}

function caseFallbackLines(caseItem: ReportCaseItem) {
  return caseStepRows(caseItem).flatMap((step) =>
    Array.isArray(step.logs) ? step.logs.map((line) => String(line)) : [],
  );
}

function caseSummaryText(caseItem: ReportCaseItem) {
  const summary = caseItem.summary || {};
  const passed = Number(summary.passed_steps || 0);
  const failed = Number(summary.failed_steps || 0);
  const skipped = Number(summary.skipped_steps || 0);
  return `成功 ${passed}，失败 ${failed}，跳过 ${skipped}`;
}

function caseParameterLabel(caseItem: ReportCaseItem) {
  const candidates = [caseItem.parameter, caseItem.execution_log?.parameter];
  for (const item of candidates) {
    const label = String(item?.parameter_label || "").trim();
    if (label) {
      return label;
    }
    const index = Number(item?.parameter_index);
    if (Number.isFinite(index) && index >= 0) {
      return `#${index + 1}`;
    }
  }
  return "";
}

function caseDurationLabel(caseItem: ReportCaseItem) {
  const direct = durationFromRecord(caseItem as unknown as Record<string, unknown>);
  if (direct) {
    return formatDuration(direct);
  }
  const logDuration = durationFromRecord((caseItem.execution_log || null) as Record<string, unknown> | null);
  if (logDuration) {
    return formatDuration(logDuration);
  }
  const total = caseStepRows(caseItem).reduce((sum, step) => {
    const seconds = durationFromRecord(step as Record<string, unknown>);
    return sum + (seconds || 0);
  }, 0);
  return total ? formatDuration(total) : "";
}

watch(
  () => route.query.reportId,
  async (value) => {
    const reportId = Number(value);
    if (Number.isFinite(reportId) && reportId > 0) {
      await loadReportDetail(reportId);
    } else {
      detail.value = null;
    }
  },
);

watch(
  () => [route.query.suiteId, route.query.projectId, route.query.keyword],
  async () => {
    syncQueryFilters();
    currentPage.value = 1;
    await loadReports();
  },
);

onMounted(async () => {
  await context.ensureLoaded();
  syncQueryFilters();
  await loadReports();
  const reportId = Number(route.query.reportId);
  if (Number.isFinite(reportId) && reportId > 0) {
    await loadReportDetail(reportId);
  }
});
</script>

<template>
  <div class="report-page" v-loading="loading && !detail">
    <template v-if="detail">
      <section class="detail-toolbar">
        <el-button size="small" type="primary" :icon="Back" @click="backToList">返回列表</el-button>
      </section>

      <div v-loading="detailLoading" class="report-detail">
        <ExecutionReportSummary
          :title="detail.suite_name || detail.case_name || detail.report_name"
          :status="detail.status"
          :total="detail.total_cases"
          :passed="detail.passed_cases"
          :failed="detail.failed_cases"
          :skipped="detail.error_cases"
          :duration="detail.duration"
          :start-time="detail.start_time"
          :end-time="detail.end_time"
        >
          <template #actions>
            <el-button size="small" :icon="RefreshRight" :loading="detailLoading" @click="refreshReports">刷新</el-button>
          </template>
        </ExecutionReportSummary>

        <section class="case-section">
          <el-collapse v-model="expandedCaseKeys" class="case-collapse">
            <el-collapse-item v-for="caseItem in detailCases" :key="caseItem.key" :name="caseItem.key" class="case-report-item">
              <template #title>
                <div class="case-title">
                  <span class="case-toggle" :class="{ expanded: expandedCaseKeys.includes(caseItem.key) }" aria-hidden="true"></span>
                  <span class="case-name">{{ caseItem.case_name }}</span>
                  <span v-if="caseParameterLabel(caseItem)" class="case-parameter">{{ caseParameterLabel(caseItem) }}</span>
                  <span class="case-summary">{{ caseSummaryText(caseItem) }}</span>
                  <span v-if="caseDurationLabel(caseItem)" class="case-duration">{{ caseDurationLabel(caseItem) }}</span>
                  <span class="case-status" :class="`status-${caseItem.status || 'pending'}`">
                    {{ statusEnglish(caseItem.status) }}
                  </span>
                </div>
              </template>

              <div class="case-detail">
                <ExecutionLogViewer
                  class="case-log-viewer"
                  :log="caseItem.execution_log || null"
                  :fallback-lines="caseFallbackLines(caseItem)"
                />
              </div>
            </el-collapse-item>
          </el-collapse>
        </section>
      </div>
    </template>

    <template v-else>
      <section class="report-toolbar">
        <div class="filter-row">
          <span class="filter-label">业务/项目</span>
          <el-cascader
            v-model="selectedProjectPath"
            class="business-project-filter"
            :options="businessProjectOptions"
            :props="{ emitPath: true }"
            clearable
            filterable
            placeholder="全部项目"
            popper-class="compact-select-popper"
            @change="handleSearch"
          />
          <el-input v-model="keyword" class="keyword-input" :prefix-icon="Search" clearable placeholder="搜索报告 / 测试集 / 用例" @keyup.enter="handleSearch" />
          <el-button size="small" :icon="RefreshRight" :loading="loading" @click="refreshReports">刷新</el-button>
          <el-button size="small" type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button size="small" @click="resetSearch">重置</el-button>
        </div>
      </section>

      <section class="report-list-section">
        <el-table
          ref="reportTableRef"
          :data="reports"
          class="report-table"
          height="100%"
          row-key="key"
          :expand-row-keys="expandedGroupKeys"
          cell-class-name="report-table-cell"
          header-cell-class-name="report-table-header-cell"
          empty-text="暂无测试报告"
          @row-click="handleGroupRowClick"
          @expand-change="handleGroupExpandChange"
        >
          <el-table-column type="expand" width="42">
            <template #default="{ row }">
              <div class="execution-records-panel" @click.stop>
                <el-table
                  v-loading="getGroupRecordState(row).loading"
                  :data="getGroupRecordState(row).items"
                  :show-header="false"
                  max-height="360"
                  size="small"
                  class="record-table"
                  empty-text="暂无历史执行记录"
                >
                  <el-table-column label="序号" width="60" align="center" header-align="center">
                    <template #default="{ $index }">
                      {{ (getGroupRecordState(row).page - 1) * getGroupRecordState(row).pageSize + $index + 1 }}
                    </template>
                  </el-table-column>
                  <el-table-column label="测试集名称" min-width="280" align="center" header-align="center" show-overflow-tooltip>
                    <template #default="{ row: record }">
                      <div class="report-name-cell report-name-cell--balanced">
                        <Document class="report-icon" />
                        <span>{{ recordGroupName(record, row) }}</span>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="业务" min-width="130" align="center" header-align="center" show-overflow-tooltip>
                    <template #default="{ row: record }">{{ record.business_group_name || row.business_group_name || "-" }}</template>
                  </el-table-column>
                  <el-table-column label="项目" min-width="150" align="center" header-align="center" show-overflow-tooltip>
                    <template #default="{ row: record }">{{ record.project_name || row.project_name || "-" }}</template>
                  </el-table-column>
                  <el-table-column label="状态" width="90" align="center" header-align="center">
                    <template #default="{ row: record }">
                      <el-tag size="small" :type="statusType(record.status)" effect="light">{{ statusLabel(record.status) }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="通过率" width="90" align="center" header-align="center">
                    <template #default="{ row: record }">{{ passRate(record) }}</template>
                  </el-table-column>
                  <el-table-column label="执行时间" min-width="170" align="center" header-align="center" show-overflow-tooltip>
                    <template #default="{ row: record }">{{ formatDate(record.start_time || record.created_at) }}</template>
                  </el-table-column>
                  <el-table-column label="耗时" width="90" align="center" header-align="center">
                    <template #default="{ row: record }">{{ formatDuration(record.duration) }}</template>
                  </el-table-column>
                  <el-table-column label="操作" width="120" fixed="right" align="center" header-align="center">
                    <template #default="{ row: record }">
                      <div class="table-actions">
                        <el-button size="small" text type="primary" :icon="View" @click.stop="openDetail(record)">详情</el-button>
                        <el-button size="small" text type="danger" :icon="Delete" @click.stop="removeHistoryReport(record, row)">删除</el-button>
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
                <AppPagination
                  :current-page="getGroupRecordState(row).page"
                  :page-size="getGroupRecordState(row).pageSize"
                  :total="getGroupRecordState(row).total"
                  :page-sizes="recordPageSizeOptions"
                  :disabled="getGroupRecordState(row).loading"
                  :hide-on-single-page="false"
                  @current-change="(page) => loadGroupRecords(row, { page })"
                  @size-change="(size) => loadGroupRecords(row, { page: 1, pageSize: size })"
                />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="序号" width="60" align="center" header-align="center">
            <template #default="{ $index }">{{ (currentPage - 1) * pageSize + $index + 1 }}</template>
          </el-table-column>
          <el-table-column label="测试集名称" min-width="280" align="center" header-align="center" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="report-name-cell report-name-cell--balanced">
                <Document class="report-icon" />
                <span>{{ groupName(row) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="业务" min-width="130" align="center" header-align="center" show-overflow-tooltip>
            <template #default="{ row }">{{ row.business_group_name || "-" }}</template>
          </el-table-column>
          <el-table-column label="项目" min-width="150" align="center" header-align="center" show-overflow-tooltip>
            <template #default="{ row }">{{ row.project_name || "-" }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center" header-align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="statusType(row.status)" effect="light">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="通过率" width="90" align="center" header-align="center">
            <template #default="{ row }">{{ passRate(row) }}</template>
          </el-table-column>
          <el-table-column label="执行时间" min-width="170" align="center" header-align="center" show-overflow-tooltip>
            <template #default="{ row }">{{ formatDate(row.start_time || row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="耗时" width="90" align="center" header-align="center">
            <template #default="{ row }">{{ formatDuration(row.duration) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right" align="center" header-align="center">
            <template #default="{ row }">
              <div class="table-actions">
                <el-button size="small" text type="primary" :icon="View" @click.stop="openLatestDetail(row)">详情</el-button>
                <el-button size="small" text type="danger" :icon="Delete" @click.stop="removeLatestReport(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <AppPagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="pageSizeOptions"
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </section>
    </template>
  </div>
</template>

<style scoped>
.report-page {
  display: flex;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

.report-page :deep(.el-table),
.report-page :deep(.el-button),
.report-page :deep(.el-input__inner),
.report-page :deep(.el-select__placeholder),
.report-page :deep(.el-select__selected-item),
.report-page :deep(.el-tag),
.report-page :deep(.el-pagination) {
  font-size: 12px;
}

.report-toolbar,
.report-list-section,
.case-section,
.detail-toolbar {
  border: 1px solid #e5edf6;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(31, 35, 41, 0.04);
}

.report-toolbar {
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
}

.business-project-filter {
  width: 250px;
}

.keyword-input {
  width: 280px;
}

.active-filter {
  margin-top: 10px;
  color: #2563eb;
  font-size: 12px;
}

.report-list-section {
  display: flex;
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  padding: 16px;
  overflow: hidden;
}

.report-table {
  flex: 1 1 0;
  width: 100%;
  min-width: 0;
  min-height: 0;
  border: 1px solid #edf1f6;
  border-radius: 8px;
}

.report-table :deep(.el-table__body .el-table__row) {
  cursor: pointer;
}

.execution-records-panel {
  display: flex;
  max-height: 440px;
  min-height: 0;
  flex-direction: column;
  padding: 10px 14px 12px 44px;
  background: #fbfdff;
  overflow: hidden;
}

.record-table {
  flex: 1 1 auto;
  min-height: 0;
  border: 1px solid #e5edf6;
  border-radius: 7px;
}

.record-table :deep(.el-table__row) {
  cursor: default;
}

.report-name-cell {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
}

.report-name-cell--balanced {
  display: inline-flex;
  width: min(220px, 100%);
  justify-content: flex-start;
  text-align: left;
  vertical-align: middle;
}

.report-icon {
  width: 15px;
  height: 15px;
  flex: 0 0 auto;
  color: #2563eb;
}

.report-name-cell span {
  min-width: 0;
  overflow: hidden;
  color: #111827;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  white-space: nowrap;
}

.table-actions :deep(.el-button) {
  margin-left: 0;
  padding-left: 3px;
  padding-right: 3px;
}

.detail-toolbar {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.detail-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.report-detail {
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 12px;
  overflow: auto;
}

.case-section {
  flex: 1 1 auto;
  min-height: 0;
  padding: 14px 16px;
}

.case-collapse {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-top: none;
}

.case-collapse :deep(.case-report-item) {
  overflow: hidden;
  border: 1px solid #e5edf6;
  border-radius: 8px;
  background: #f8fbff;
}

.case-collapse :deep(.case-report-item:nth-child(even)) {
  background: #fbfcff;
}

.case-collapse :deep(.el-collapse-item__header) {
  min-height: 44px;
  padding: 0 14px;
  border-bottom-color: transparent;
  background: transparent;
  font-size: 12px;
}

.case-collapse :deep(.case-report-item.is-active .el-collapse-item__header) {
  border-bottom-color: #e5edf6;
}

.case-collapse :deep(.el-collapse-item__arrow) {
  display: none;
}

.case-collapse :deep(.case-report-item .el-collapse-item__wrap) {
  border-bottom: 0;
  background: transparent;
}

.case-collapse :deep(.case-report-item .el-collapse-item__content) {
  padding: 12px 14px 14px;
  background: transparent;
}

.case-title {
  display: grid;
  min-width: 0;
  width: 100%;
  align-items: center;
  grid-template-columns: 20px minmax(180px, 0.75fr) max-content minmax(220px, 1.05fr) max-content max-content;
  column-gap: 8px;
}

.case-toggle {
  position: relative;
  flex: 0 0 auto;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: #eef6ff;
  color: #64748b;
  transition:
    background 0.16s ease,
    color 0.16s ease;
}

.case-toggle::before {
  position: absolute;
  top: 50%;
  left: 50%;
  box-sizing: border-box;
  width: 6px;
  height: 6px;
  border-right: 1.8px solid currentColor;
  border-bottom: 1.8px solid currentColor;
  content: "";
  transform: translate(-58%, -50%) rotate(-45deg);
  transform-origin: center;
  transition: transform 0.16s ease;
}

.case-collapse :deep(.el-collapse-item__header:hover) .case-toggle {
  background: #dbeafe;
  color: #2563eb;
}

.case-toggle.expanded::before {
  transform: translate(-50%, -58%) rotate(45deg);
}

.case-name {
  grid-column: 2;
  min-width: 0;
  overflow: hidden;
  color: #111827;
  font-size: 13px;
  font-weight: 700;
  line-height: 22px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.case-summary {
  grid-column: 4;
  justify-self: start;
  color: #64748b;
  font-weight: 600;
  text-align: left;
  white-space: nowrap;
}

.case-parameter {
  grid-column: 3;
  width: max-content;
  justify-self: start;
  border-radius: 999px;
  background: #eef6ff;
  color: #2563eb;
  font-size: 11px;
  font-weight: 700;
  line-height: 18px;
  padding: 0 8px;
  white-space: nowrap;
}

.case-duration {
  grid-column: 5;
  width: max-content;
  justify-self: end;
  border-radius: 999px;
  background: #f1f5f9;
  color: #667085;
  font-size: 11px;
  font-weight: 600;
  line-height: 18px;
  padding: 0 7px;
  white-space: nowrap;
}

.case-status {
  grid-column: 6;
  justify-self: end;
  min-width: 76px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.02em;
  line-height: 22px;
  padding: 0 12px;
  text-align: center;
}

.case-status.status-success {
  background: #e8f8ef;
  color: #168a4a;
}

.case-status.status-failed {
  background: #fff0f0;
  color: #d92d20;
}

.case-status.status-running {
  background: #eef6ff;
  color: #2563eb;
}

.case-status.status-skipped {
  background: #fff7e6;
  color: #b76e00;
}

.case-status.status-pending {
  background: #eef2f7;
  color: #64748b;
}

.case-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.case-log-viewer {
  max-height: 520px;
}
</style>
