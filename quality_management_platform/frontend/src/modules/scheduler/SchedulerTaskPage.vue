<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { Delete, Edit, RefreshRight, Search, Tickets, VideoPlay } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";

import AppPagination from "@/shared/components/AppPagination.vue";
import {
  createSchedulerTask,
  deleteSchedulerTask,
  fetchSchedulerContext,
  fetchSchedulerTaskRunDetail,
  fetchSchedulerTaskRuns,
  fetchSchedulerTasks,
  runSchedulerTask,
  updateSchedulerTask,
  updateSchedulerTaskStatus,
  type SchedulerCaseRunResult,
  type SchedulerContext,
  type SchedulerExecutionLogLine,
  type SchedulerLogsMeta,
  type SchedulerRetryAttempt,
  type SchedulerRunRetention,
  type SchedulerScheduleType,
  type SchedulerTaskPayload,
  type SchedulerTaskRecord,
  type SchedulerTaskRunRecord,
  type SchedulerTaskType,
} from "./api";

const ALL_VALUE = "all";
const TASK_POLL_INTERVAL_MS = 15000;
const RUN_DETAIL_POLL_INTERVAL_MS = 3000;

type SelectValue = number | typeof ALL_VALUE;

const route = useRoute();

type SchedulerForm = {
  id: number | null;
  business_group_id: number | null;
  project_id: number | null;
  name: string;
  task_type: SchedulerTaskType;
  source_module: string;
  source_id: number | null;
  description: string;
  schedule_type: SchedulerScheduleType;
  cron_expression: string;
  interval_seconds: number;
  run_at: string | null;
  timezone: string;
  suite_id: number | null;
  case_ids: number[];
  script_path: string;
  working_dir: string;
  script_args: string;
  notify_emails: string;
  notify_webhook: string;
  misfire_policy: string;
  allow_concurrent: boolean;
  timeout_seconds: number;
  retry_count: number;
  retry_interval_seconds: number;
  enabled: boolean;
};

const taskTypeOptions: Array<{ label: string; value: SchedulerTaskType; tone: string }> = [
  { label: "测试集", value: "test_suite", tone: "blue" },
  { label: "接口用例", value: "test_case", tone: "green" },
  { label: "Python 脚本", value: "python_script", tone: "purple" },
  { label: "HTTP 回调", value: "http_callback", tone: "orange" },
  { label: "自定义", value: "custom", tone: "gray" },
];

const scheduleTypeOptions: Array<{ label: string; value: SchedulerScheduleType }> = [
  { label: "Cron", value: "cron" },
  { label: "固定间隔", value: "interval" },
  { label: "单次执行", value: "once" },
  { label: "手动触发", value: "manual" },
];

const cronPresets = [
  { label: "每 5 分钟", value: "*/5 * * * *" },
  { label: "每小时", value: "0 * * * *" },
  { label: "每天 9 点", value: "0 9 * * *" },
  { label: "工作日 9 点", value: "0 9 * * 1-5" },
];

type CronBuilderMode = "every_minutes" | "hourly" | "daily" | "weekly" | "monthly";

const minuteOptions = Array.from({ length: 60 }, (_, value) => ({
  label: `${String(value).padStart(2, "0")} 分`,
  value,
}));

const hourOptions = Array.from({ length: 24 }, (_, value) => ({
  label: `${String(value).padStart(2, "0")} 点`,
  value,
}));

const weekDayOptions = [
  { label: "周日", value: 0 },
  { label: "周一", value: 1 },
  { label: "周二", value: 2 },
  { label: "周三", value: 3 },
  { label: "周四", value: 4 },
  { label: "周五", value: 5 },
  { label: "周六", value: 6 },
];

const monthDayOptions = Array.from({ length: 31 }, (_, index) => ({
  label: `${index + 1} 日`,
  value: index + 1,
}));

const businessProjectCascaderProps = {
  checkStrictly: true,
  emitPath: true,
};

const loading = ref(false);
const saving = ref(false);
const runsLoading = ref(false);
const keyword = ref("");
const selectedBusinessGroupId = ref<SelectValue>(ALL_VALUE);
const selectedProjectId = ref<SelectValue>(ALL_VALUE);
const selectedTaskType = ref<string>(ALL_VALUE);
const selectedEnabled = ref<string>(ALL_VALUE);
const tasks = ref<SchedulerTaskRecord[]>([]);
const currentPage = ref(1);
const pageSize = ref(10);
const pageSizeOptions = [10, 20, 50, 100];
const dialogVisible = ref(false);
const dialogTab = ref("basic");
const runsDrawerVisible = ref(false);
const currentRunTask = ref<SchedulerTaskRecord | null>(null);
const runs = ref<SchedulerTaskRunRecord[]>([]);
const runCurrentPage = ref(1);
const runPageSize = ref(10);
const runTotal = ref(0);
const runPageSizeOptions = [10, 20, 50, 100];
const runRetention = ref<SchedulerRunRetention | null>(null);
const expandedRunIds = ref<number[]>([]);
const runDetailLoadingIds = ref<Set<number>>(new Set());
const scriptLogActiveTabs = reactive<Record<number, string>>({});
const runningTaskIds = ref<Set<number>>(new Set());
let taskPollingTimer: number | null = null;
let runDetailPollingTimer: number | null = null;
let taskPollingInFlight = false;
let runDetailPollingInFlight = false;
let openedTaskIdFromQuery: number | null = null;

const context = reactive<SchedulerContext>({
  business_groups: [],
  projects: [],
  test_suites: [],
  test_cases: [],
});

const form = reactive<SchedulerForm>({
  id: null,
  business_group_id: null,
  project_id: null,
  name: "",
  task_type: "test_suite",
  source_module: "",
  source_id: null,
  description: "",
  schedule_type: "cron",
  cron_expression: "0 9 * * *",
  interval_seconds: 300,
  run_at: null,
  timezone: "Asia/Shanghai",
  suite_id: null,
  case_ids: [],
  script_path: "",
  working_dir: "",
  script_args: "",
  notify_emails: "",
  notify_webhook: "",
  misfire_policy: "fire_once",
  allow_concurrent: false,
  timeout_seconds: 1800,
  retry_count: 0,
  retry_interval_seconds: 30,
  enabled: false,
});

const cronBuilder = reactive({
  mode: "daily" as CronBuilderMode,
  everyMinutes: 5,
  minute: 0,
  hour: 9,
  weekDays: [1, 2, 3, 4, 5],
  monthDay: 1,
});

const filteredProjects = computed(() => {
  if (selectedBusinessGroupId.value === ALL_VALUE) {
    return context.projects;
  }
  return context.projects.filter((item) => item.business_group_id === selectedBusinessGroupId.value);
});

const businessProjectOptions = computed(() =>
  context.business_groups.map((group) => ({
    value: group.id,
    label: group.name,
    children: context.projects
      .filter((project) => project.business_group_id === group.id)
      .map((project) => ({
        value: project.id,
        label: project.name,
      })),
  })),
);

const formBusinessProjectValue = computed<number[]>({
  get() {
    if (form.project_id) {
      const project = context.projects.find((item) => item.id === form.project_id);
      const groupId = form.business_group_id ?? project?.business_group_id ?? null;
      return groupId ? [groupId, form.project_id] : [form.project_id];
    }
    return form.business_group_id ? [form.business_group_id] : [];
  },
  set(value) {
    const [groupId, projectId] = value || [];
    form.business_group_id = groupId ?? null;
    form.project_id = projectId ?? null;
    if (form.suite_id && !formSuites.value.some((item) => item.id === form.suite_id)) {
      form.suite_id = null;
    }
    form.case_ids = form.case_ids.filter((caseId) => formCases.value.some((item) => item.id === caseId));
  },
});

const formProjects = computed(() => {
  if (!form.business_group_id) {
    return context.projects;
  }
  return context.projects.filter((item) => item.business_group_id === form.business_group_id);
});

const formSuites = computed(() => {
  if (!form.project_id) {
    return context.test_suites;
  }
  return context.test_suites.filter((item) => item.project_id === form.project_id);
});

const formCases = computed(() => {
  if (!form.project_id) {
    return context.test_cases;
  }
  return context.test_cases.filter((item) => item.project_id === form.project_id);
});

const paginatedTasks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return tasks.value.slice(start, start + pageSize.value);
});

function getRowIndex(index: number) {
  return (currentPage.value - 1) * pageSize.value + index + 1;
}

function syncCurrentPage() {
  const maxPage = Math.max(1, Math.ceil(tasks.value.length / pageSize.value));
  if (currentPage.value > maxPage) {
    currentPage.value = maxPage;
  }
}

function normalizeSwitchValue(value: boolean | string | number | null | undefined) {
  return value === true || value === "true" || value === 1 || value === "1";
}

function clampNumber(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(max, Math.max(min, value));
}

function parseCronNumber(value: string | undefined, min: number, max: number, fallback: number) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed)) {
    return fallback;
  }
  return clampNumber(parsed, min, max);
}

function parseCronWeekDays(value: string | undefined) {
  if (!value || value === "*") {
    return [1, 2, 3, 4, 5];
  }
  const days = new Set<number>();
  for (const section of value.split(",")) {
    const [startText, endText] = section.split("-");
    const start = Number(startText);
    const end = endText === undefined ? start : Number(endText);
    if (!Number.isInteger(start) || !Number.isInteger(end)) {
      continue;
    }
    const from = Math.min(start, end);
    const to = Math.max(start, end);
    for (let day = from; day <= to; day += 1) {
      const normalized = day === 7 ? 0 : day;
      if (normalized >= 0 && normalized <= 6) {
        days.add(normalized);
      }
    }
  }
  return Array.from(days).sort((a, b) => a - b);
}

function formatCronWeekDays(value: number[]) {
  const days = Array.from(new Set(value.map((item) => (item === 7 ? 0 : item))))
    .filter((item) => item >= 0 && item <= 6)
    .sort((a, b) => a - b);
  if (days.length === 0) {
    return "1";
  }
  const sections: string[] = [];
  let start = days[0];
  let previous = days[0];
  for (let index = 1; index <= days.length; index += 1) {
    const current = days[index];
    if (current === previous + 1) {
      previous = current;
      continue;
    }
    sections.push(start === previous ? `${start}` : `${start}-${previous}`);
    start = current;
    previous = current;
  }
  return sections.join(",");
}

function buildCronExpression() {
  const minute = clampNumber(cronBuilder.minute, 0, 59);
  const hour = clampNumber(cronBuilder.hour, 0, 23);
  if (cronBuilder.mode === "every_minutes") {
    return `*/${clampNumber(cronBuilder.everyMinutes, 1, 59)} * * * *`;
  }
  if (cronBuilder.mode === "hourly") {
    return `${minute} * * * *`;
  }
  if (cronBuilder.mode === "weekly") {
    return `${minute} ${hour} * * ${formatCronWeekDays(cronBuilder.weekDays)}`;
  }
  if (cronBuilder.mode === "monthly") {
    return `${minute} ${hour} ${clampNumber(cronBuilder.monthDay, 1, 31)} * *`;
  }
  return `${minute} ${hour} * * *`;
}

function syncCronBuilderFromExpression(expression: string) {
  const [minute, hour, day, month, week] = expression.trim().split(/\s+/);
  if (!minute || !hour || !day || !month || !week) {
    cronBuilder.mode = "daily";
    cronBuilder.minute = 0;
    cronBuilder.hour = 9;
    return;
  }

  if (minute.startsWith("*/") && hour === "*" && day === "*" && month === "*" && week === "*") {
    cronBuilder.mode = "every_minutes";
    cronBuilder.everyMinutes = parseCronNumber(minute.slice(2), 1, 59, 5);
    return;
  }

  if (hour === "*" && day === "*" && month === "*" && week === "*") {
    cronBuilder.mode = "hourly";
    cronBuilder.minute = parseCronNumber(minute, 0, 59, 0);
    return;
  }

  if (day === "*" && month === "*" && week !== "*") {
    cronBuilder.mode = "weekly";
    cronBuilder.minute = parseCronNumber(minute, 0, 59, 0);
    cronBuilder.hour = parseCronNumber(hour, 0, 23, 9);
    cronBuilder.weekDays = parseCronWeekDays(week);
    return;
  }

  if (day !== "*" && month === "*" && week === "*") {
    cronBuilder.mode = "monthly";
    cronBuilder.minute = parseCronNumber(minute, 0, 59, 0);
    cronBuilder.hour = parseCronNumber(hour, 0, 23, 9);
    cronBuilder.monthDay = parseCronNumber(day, 1, 31, 1);
    return;
  }

  cronBuilder.mode = "daily";
  cronBuilder.minute = parseCronNumber(minute, 0, 59, 0);
  cronBuilder.hour = parseCronNumber(hour, 0, 23, 9);
}

function applyCronPreset(expression: string) {
  form.cron_expression = expression;
  syncCronBuilderFromExpression(expression);
}

watch(
  cronBuilder,
  () => {
    form.cron_expression = buildCronExpression();
  },
  { deep: true },
);

watch(runsDrawerVisible, (visible) => {
  if (visible) {
    startRunDetailPolling();
    return;
  }
  stopRunDetailPolling();
  expandedRunIds.value = [];
});

async function loadContext() {
  const data = await fetchSchedulerContext();
  context.business_groups = data.business_groups || [];
  context.projects = data.projects || [];
  context.test_suites = data.test_suites || [];
  context.test_cases = data.test_cases || [];
}

async function loadTasks(options: { silent?: boolean } = {}) {
  const silent = options.silent === true;
  if (!silent) {
    loading.value = true;
  }
  try {
    const result = await fetchSchedulerTasks({
      keyword: keyword.value.trim(),
      business_group_id: selectedBusinessGroupId.value === ALL_VALUE ? null : selectedBusinessGroupId.value,
      project_id: selectedProjectId.value === ALL_VALUE ? null : selectedProjectId.value,
      task_type: selectedTaskType.value === ALL_VALUE ? "" : selectedTaskType.value,
      enabled: selectedEnabled.value === ALL_VALUE ? "" : selectedEnabled.value,
    });
    tasks.value = result.map((item) => ({
      ...item,
      enabled: normalizeSwitchValue(item.enabled),
      allow_concurrent: normalizeSwitchValue(item.allow_concurrent),
    }));
    syncCurrentPage();
  } catch (error) {
    if (!silent) {
      ElMessage.error((error as Error).message);
    }
  } finally {
    if (!silent) {
      loading.value = false;
    }
  }
}

function resetForm() {
  form.id = null;
  form.business_group_id = selectedBusinessGroupId.value === ALL_VALUE ? null : selectedBusinessGroupId.value;
  form.project_id = selectedProjectId.value === ALL_VALUE ? null : selectedProjectId.value;
  form.name = "";
  form.task_type = "test_suite";
  form.source_module = "";
  form.source_id = null;
  form.description = "";
  form.schedule_type = "cron";
  form.cron_expression = "0 9 * * *";
  form.interval_seconds = 300;
  form.run_at = null;
  form.timezone = "Asia/Shanghai";
  form.suite_id = null;
  form.case_ids = [];
  form.script_path = "";
  form.working_dir = "";
  form.script_args = "";
  form.notify_emails = "";
  form.notify_webhook = "";
  form.misfire_policy = "fire_once";
  form.allow_concurrent = false;
  form.timeout_seconds = 1800;
  form.retry_count = 0;
  form.retry_interval_seconds = 30;
  form.enabled = false;
  syncCronBuilderFromExpression(form.cron_expression);
}

function openCreateDialog() {
  resetForm();
  dialogTab.value = "basic";
  dialogVisible.value = true;
}

function openEditDialog(row: SchedulerTaskRecord) {
  const target = row.target_config || {};
  const notify = row.notify_config || {};
  form.id = row.id;
  form.business_group_id = row.business_group_id;
  form.project_id = row.project_id;
  form.name = row.name;
  form.task_type = row.task_type;
  form.source_module = row.source_module || "";
  form.source_id = row.source_id;
  form.description = row.description || "";
  form.schedule_type = row.schedule_type;
  form.cron_expression = row.cron_expression || "0 9 * * *";
  form.interval_seconds = Number(row.interval_seconds) || 300;
  form.run_at = row.run_at;
  form.timezone = row.timezone || "Asia/Shanghai";
  form.suite_id = Number(target.suite_id) || null;
  form.case_ids = Array.isArray(target.case_ids) ? target.case_ids.map((item) => Number(item)).filter(Boolean) : [];
  form.script_path = String(target.script_path || "");
  form.working_dir = String(target.working_dir || "");
  form.script_args = Array.isArray(target.args) ? target.args.join(" ") : String(target.args || "");
  form.notify_emails = Array.isArray(notify.emails) ? notify.emails.join(",") : String(notify.emails || "");
  form.notify_webhook = String(notify.webhook_url || "");
  form.misfire_policy = row.misfire_policy || "fire_once";
  form.allow_concurrent = row.allow_concurrent;
  form.timeout_seconds = Number(row.timeout_seconds) || 1800;
  form.retry_count = Number(row.retry_count) || 0;
  form.retry_interval_seconds = Number(row.retry_interval_seconds) || 30;
  form.enabled = row.enabled;
  syncCronBuilderFromExpression(form.cron_expression);
  dialogTab.value = "basic";
  dialogVisible.value = true;
}

function buildPayload(): SchedulerTaskPayload | null {
  if (!form.name.trim()) {
    ElMessage.warning("请输入任务名称");
    return null;
  }
  if (form.enabled && form.task_type === "test_suite" && !form.suite_id) {
    ElMessage.warning("启用测试集任务前请先选择测试集");
    return null;
  }
  if (form.task_type === "test_case" && form.case_ids.length === 0) {
    ElMessage.warning("接口用例任务请至少选择一个用例");
    return null;
  }
  if (form.enabled && form.task_type === "python_script" && !form.script_path.trim()) {
    ElMessage.warning("启用 Python 脚本任务前请先配置脚本路径");
    return null;
  }

  const targetConfig: Record<string, unknown> = {};
  if (form.task_type === "test_suite") {
    targetConfig.suite_id = form.suite_id;
  } else if (form.task_type === "test_case") {
    targetConfig.case_ids = form.case_ids;
  } else if (form.task_type === "python_script") {
    targetConfig.script_path = form.script_path.trim();
    targetConfig.working_dir = form.working_dir.trim();
    targetConfig.args = form.script_args.trim();
  }

  return {
    business_group_id: form.business_group_id,
    project_id: form.project_id,
    name: form.name.trim(),
    task_type: form.task_type,
    source_module: form.source_module,
    source_id: form.source_id,
    description: form.description.trim(),
    schedule_type: form.schedule_type,
    cron_expression: form.cron_expression.trim(),
    interval_seconds: Number(form.interval_seconds) || 0,
    run_at: form.run_at,
    timezone: form.timezone,
    target_config: targetConfig,
    notify_config: {
      emails: form.notify_emails
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      webhook_url: form.notify_webhook.trim(),
    },
    misfire_policy: form.misfire_policy,
    allow_concurrent: form.allow_concurrent,
    timeout_seconds: Number(form.timeout_seconds) || 1800,
    retry_count: Number(form.retry_count) || 0,
    retry_interval_seconds: Number(form.retry_interval_seconds) || 30,
    enabled: form.enabled,
  };
}

async function saveTask() {
  const payload = buildPayload();
  if (!payload) {
    return;
  }
  saving.value = true;
  try {
    if (form.id) {
      await updateSchedulerTask(form.id, payload);
      ElMessage.success("定时任务已更新");
    } else {
      await createSchedulerTask(payload);
      ElMessage.success("定时任务已新增");
    }
    dialogVisible.value = false;
    await loadTasks();
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    saving.value = false;
  }
}

async function removeTask(row: SchedulerTaskRecord) {
  try {
    await ElMessageBox.confirm(`确定删除定时任务「${row.name}」吗？`, "删除确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    await deleteSchedulerTask(row.id);
    ElMessage.success("定时任务已删除");
    await loadTasks();
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function toggleTask(row: SchedulerTaskRecord, enabled: boolean) {
  const previous = normalizeSwitchValue(row.enabled);
  if (previous === enabled) {
    row.enabled = previous;
    return;
  }
  row.enabled = enabled;
  try {
    const result = await updateSchedulerTaskStatus(row.id, enabled);
    row.enabled = result.enabled;
    row.next_run_at = result.next_run_at;
    ElMessage.success(enabled ? "定时任务已启用" : "定时任务已停用");
  } catch (error) {
    row.enabled = previous;
    ElMessage.error((error as Error).message);
  }
}

function handleToggleTask(row: SchedulerTaskRecord, value: boolean | string | number) {
  void toggleTask(row, normalizeSwitchValue(value));
}

async function runTaskNow(row: SchedulerTaskRecord) {
  runningTaskIds.value = new Set(runningTaskIds.value).add(row.id);
  try {
    const result = await runSchedulerTask(row.id);
    if (result.status === "success") {
      ElMessage.success(result.message || "任务执行成功");
    } else {
      ElMessage.warning(result.message || "任务执行完成，请查看执行记录");
    }
    await loadTasks();
    if (runsDrawerVisible.value && currentRunTask.value?.id === row.id) {
      await loadRuns({ silent: true });
    }
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    const next = new Set(runningTaskIds.value);
    next.delete(row.id);
    runningTaskIds.value = next;
  }
}

async function openRunsDrawer(row: SchedulerTaskRecord) {
  currentRunTask.value = row;
  runsDrawerVisible.value = true;
  runCurrentPage.value = 1;
  expandedRunIds.value = [];
  runs.value = [];
  await loadRuns();
  startRunDetailPolling();
}

async function openRunsDrawerFromQuery() {
  const rawTaskId = Number(route.query.taskId);
  if (!Number.isFinite(rawTaskId) || rawTaskId <= 0 || openedTaskIdFromQuery === rawTaskId) {
    return;
  }
  const targetTask = tasks.value.find((item) => item.id === rawTaskId);
  if (!targetTask) {
    return;
  }
  openedTaskIdFromQuery = rawTaskId;
  await openRunsDrawer(targetTask);
}

async function loadRuns(options: { silent?: boolean } = {}) {
  if (!currentRunTask.value) {
    return;
  }
  const silent = options.silent === true;
  if (!silent) {
    runsLoading.value = true;
  }
  try {
    const detailById = new Map(runs.value.filter((item) => item.details_loaded).map((item) => [item.id, item]));
    const page = await fetchSchedulerTaskRuns(currentRunTask.value.id, {
      page: runCurrentPage.value,
      page_size: runPageSize.value,
    });
    runs.value = (page.items || []).map((item) => {
      const detail = detailById.get(item.id);
      if (!detail) {
        return item;
      }
      return item.status === detail.status
        ? { ...item, ...detail, status: item.status, message: item.message, duration_ms: item.duration_ms }
        : item;
    });
    runTotal.value = Number(page.total) || 0;
    runRetention.value = page.retention ?? null;
    await Promise.all(
      runs.value
        .filter((item) => expandedRunIds.value.includes(item.id) && !item.details_loaded)
        .map((item) => refreshRunDetail(item, { silent: true })),
    );
  } catch (error) {
    if (!silent) {
      ElMessage.error((error as Error).message);
    }
  } finally {
    if (!silent) {
      runsLoading.value = false;
    }
  }
}

async function refreshRunDetail(row: SchedulerTaskRunRecord, options: { silent?: boolean } = {}) {
  if (!currentRunTask.value) {
    return;
  }
  const silent = options.silent === true;
  if (!silent) {
    setRunDetailLoading(row.id, true);
  }
  try {
    const detail = await fetchSchedulerTaskRunDetail(currentRunTask.value.id, row.id);
    runs.value = runs.value.map((item) => (item.id === detail.id ? { ...item, ...detail, details_loaded: true } : item));
  } catch (error) {
    if (!silent) {
      ElMessage.error((error as Error).message);
    }
  } finally {
    if (!silent) {
      setRunDetailLoading(row.id, false);
    }
  }
}

async function ensureRunDetail(row: SchedulerTaskRunRecord) {
  if (row.details_loaded || runDetailLoadingIds.value.has(row.id)) {
    return;
  }
  await refreshRunDetail(row);
}

function setRunDetailLoading(runId: number, loading: boolean) {
  const next = new Set(runDetailLoadingIds.value);
  if (loading) {
    next.add(runId);
  } else {
    next.delete(runId);
  }
  runDetailLoadingIds.value = next;
}

function handleRunExpandChange(row: SchedulerTaskRunRecord, expandedRows: SchedulerTaskRunRecord[]) {
  expandedRunIds.value = expandedRows.map((item) => item.id);
  if (expandedRunIds.value.includes(row.id)) {
    void ensureRunDetail(row);
  }
}

async function handleRunPageChange(page: number) {
  runCurrentPage.value = page;
  expandedRunIds.value = [];
  await loadRuns();
}

async function handleRunPageSizeChange(size: number) {
  runPageSize.value = size;
  runCurrentPage.value = 1;
  expandedRunIds.value = [];
  await loadRuns();
}

async function pollTasks() {
  if (taskPollingInFlight || loading.value || saving.value || document.hidden) {
    return;
  }
  taskPollingInFlight = true;
  try {
    await loadTasks({ silent: true });
    if (runsDrawerVisible.value && currentRunTask.value) {
      try {
        await loadRuns({ silent: true });
      } catch {
        // Keep scheduled polling quiet; manual refresh actions still show errors.
      }
    }
  } finally {
    taskPollingInFlight = false;
  }
}

function startTaskPolling() {
  stopTaskPolling();
  taskPollingTimer = window.setInterval(() => {
    void pollTasks();
  }, TASK_POLL_INTERVAL_MS);
}

function stopTaskPolling() {
  if (taskPollingTimer !== null) {
    window.clearInterval(taskPollingTimer);
    taskPollingTimer = null;
  }
}

async function pollRunDetails() {
  if (runDetailPollingInFlight || document.hidden || !runsDrawerVisible.value || !currentRunTask.value) {
    return;
  }
  const runningRows = runs.value.filter((row) => row.status === "running");
  if (!runningRows.length) {
    return;
  }
  runDetailPollingInFlight = true;
  try {
    for (const row of runningRows) {
      if (expandedRunIds.value.includes(row.id)) {
        await refreshRunDetail(row, { silent: true });
      }
    }
  } finally {
    runDetailPollingInFlight = false;
  }
}

function startRunDetailPolling() {
  stopRunDetailPolling();
  runDetailPollingTimer = window.setInterval(() => {
    void pollRunDetails();
  }, RUN_DETAIL_POLL_INTERVAL_MS);
}

function stopRunDetailPolling() {
  if (runDetailPollingTimer !== null) {
    window.clearInterval(runDetailPollingTimer);
    runDetailPollingTimer = null;
  }
}

function handleVisibilityChange() {
  if (!document.hidden) {
    void pollTasks();
    void pollRunDetails();
  }
}

async function handleSearch() {
  currentPage.value = 1;
  await loadTasks();
}

async function resetFilters() {
  keyword.value = "";
  selectedBusinessGroupId.value = ALL_VALUE;
  selectedProjectId.value = ALL_VALUE;
  selectedTaskType.value = ALL_VALUE;
  selectedEnabled.value = ALL_VALUE;
  currentPage.value = 1;
  await loadTasks();
}

function handleBusinessFilterChange() {
  if (
    selectedProjectId.value !== ALL_VALUE &&
    !filteredProjects.value.some((item) => item.id === selectedProjectId.value)
  ) {
    selectedProjectId.value = ALL_VALUE;
  }
  void handleSearch();
}

function handleFormBusinessChange() {
  if (form.project_id && !formProjects.value.some((item) => item.id === form.project_id)) {
    form.project_id = null;
  }
}

function handleFormProjectChange(projectId: number | null) {
  const project = context.projects.find((item) => item.id === projectId);
  form.business_group_id = project?.business_group_id ?? form.business_group_id;
  if (form.suite_id && !formSuites.value.some((item) => item.id === form.suite_id)) {
    form.suite_id = null;
  }
  form.case_ids = form.case_ids.filter((caseId) => formCases.value.some((item) => item.id === caseId));
}

function handlePageSizeChange(size: number) {
  pageSize.value = size;
  currentPage.value = 1;
  syncCurrentPage();
}

function handlePageChange(page: number) {
  currentPage.value = page;
}

function taskTypeMeta(type: string) {
  return taskTypeOptions.find((item) => item.value === type) || taskTypeOptions[4];
}

function taskTypeLabel(type: string) {
  return taskTypeMeta(type).label;
}

function optionLabel(item: { name: string; project_name?: string | null }) {
  return item.project_name ? `${item.name} / ${item.project_name}` : item.name;
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "-";
  }
  return String(value).replace("T", " ").replace(/\.\d+$/, "").replace(/Z$/, "");
}

function runStatusRank(status: string | undefined) {
  if (status === "failed") {
    return 0;
  }
  if (status === "running") {
    return 1;
  }
  if (status === "skipped") {
    return 2;
  }
  return 3;
}

function getRunCaseResults(row: SchedulerTaskRunRecord): SchedulerCaseRunResult[] {
  const results = row.result_snapshot?.results;
  return Array.isArray(results)
    ? [...results].sort((left, right) => runStatusRank(left.status) - runStatusRank(right.status))
    : [];
}

function normalizeLogLine(line: SchedulerExecutionLogLine | string | unknown): SchedulerExecutionLogLine {
  if (typeof line === "string") {
    return {
      level: inferLogLevel(line),
      scope: "调度",
      message: line,
    };
  }
  if (line && typeof line === "object") {
    const record = line as SchedulerExecutionLogLine;
    return {
      ...record,
      level: String(record.level || inferLogLevel(record.message)).toUpperCase(),
      scope: record.scope || "调度",
      sub_scope: record.sub_scope || record.subScope || "",
      message: String(record.message ?? ""),
    };
  }
  return {
    level: "INFO",
    scope: "调度",
    message: String(line ?? ""),
  };
}

function getRunLogs(row: SchedulerTaskRunRecord) {
  return Array.isArray(row.logs) ? row.logs.filter(Boolean).map((item) => normalizeLogLine(item)) : [];
}

function getCaseExecutionLines(result: SchedulerCaseRunResult) {
  const lines = result.execution_log?.lines;
  return Array.isArray(lines) ? lines.slice(-220).map((line) => normalizeLogLine(line)) : [];
}

function formatExecutionLine(line: SchedulerExecutionLogLine) {
  const subScope = line.sub_scope || line.subScope;
  const sections = [
    line.time ? `[${formatDateTime(line.time)}]` : "",
    line.level ? `[${line.level}]` : "",
    line.scope ? `[${line.scope}]` : "",
    subScope ? `[${subScope}]` : "",
    line.subject ? `[${line.subject}]` : "",
  ].filter(Boolean);
  return `${sections.join(" ")} ${line.message ?? ""}`.trim();
}

function executionLineClass(line: SchedulerExecutionLogLine) {
  return String(line.level || "INFO").toLowerCase();
}

function inferLogLevel(value: unknown) {
  const text = String(value || "").toLowerCase();
  if (/(error|exception|traceback|失败|异常|错误|超时)/i.test(text)) {
    return "ERROR";
  }
  if (/(warn|warning|跳过|省略)/i.test(text)) {
    return "WARN";
  }
  return "INFO";
}

function getRunLogsMeta(row: SchedulerTaskRunRecord): SchedulerLogsMeta {
  return row.logs_meta || row.result_snapshot?.logs_meta || {};
}

function getLogTruncationText(row: SchedulerTaskRunRecord) {
  const meta = getRunLogsMeta(row);
  if (!meta.truncated) {
    return "";
  }
  return `日志已截断，当前保留 ${meta.limit || "-"} 行，省略 ${meta.omitted || 0} 行`;
}

function getRunFailureSummary(row: SchedulerTaskRunRecord) {
  const result = row.result_snapshot || {};
  const error = result.error && typeof result.error === "object" ? (result.error as Record<string, unknown>) : {};
  const failedCases = getRunCaseResults(row).filter((item) => item.status === "failed");
  const firstFailed = failedCases[0];
  const reason =
    row.message ||
    String(result.message || "") ||
    String(firstFailed?.message || "") ||
    String(error.message || "") ||
    "-";
  return [
    { label: "失败原因", value: reason },
    { label: "失败用例", value: failedCases.length ? `${failedCases.length} 个` : "-" },
    {
      label: "首个失败",
      value: firstFailed ? firstFailed.case_name || `用例 ${firstFailed.case_id || "-"}` : "-",
    },
    { label: "错误类型", value: String(error.type || "-") },
    { label: "耗时", value: row.duration_ms ? `${row.duration_ms}ms` : "-" },
  ];
}

function getRetryAttempts(row: SchedulerTaskRunRecord): SchedulerRetryAttempt[] {
  const attempts = row.result_snapshot?.retry_attempts;
  return Array.isArray(attempts) ? attempts : [];
}

function hasRetryInfo(row: SchedulerTaskRunRecord) {
  return row.retry_no > 0 || getRetryAttempts(row).length > 1;
}

function getPythonOutput(row: SchedulerTaskRunRecord, key: "stdout" | "stderr") {
  return String(row.result_snapshot?.[key] || "");
}

function getPythonTraceback(row: SchedulerTaskRunRecord) {
  const error = row.result_snapshot?.error;
  return error && typeof error === "object" ? String((error as Record<string, unknown>).traceback || "") : "";
}

function hasPythonLogSections(row: SchedulerTaskRunRecord) {
  return Boolean(getPythonOutput(row, "stdout") || getPythonOutput(row, "stderr") || getPythonTraceback(row));
}

function getScriptActiveTab(row: SchedulerTaskRunRecord) {
  if (!scriptLogActiveTabs[row.id]) {
    scriptLogActiveTabs[row.id] = row.status === "failed" && getPythonOutput(row, "stderr") ? "stderr" : "stdout";
  }
  return scriptLogActiveTabs[row.id];
}

function setScriptActiveTab(runId: number, tabName: string | number) {
  scriptLogActiveTabs[runId] = String(tabName);
}

function handleScriptTabChange(row: SchedulerTaskRunRecord, tabName: string | number) {
  setScriptActiveTab(row.id, tabName);
}

function formatRunSummary(row: SchedulerTaskRunRecord) {
  const summary = row.result_snapshot?.summary;
  if (!summary || typeof summary !== "object") {
    return "";
  }
  const parts = Object.entries(summary)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => `${key}: ${value}`);
  return parts.join("，");
}

function formatRunRetention() {
  if (!runRetention.value) {
    return "";
  }
  return `仅保留每个任务最近 ${runRetention.value.count} 条 / ${runRetention.value.days} 天执行记录`;
}

function formatRunPayloadSize(row: SchedulerTaskRunRecord) {
  const size = Number(row.logs_size || 0) + Number(row.result_size || 0);
  if (!size) {
    return "";
  }
  if (size >= 1024 * 1024) {
    return `${(size / 1024 / 1024).toFixed(1)}MB`;
  }
  if (size >= 1024) {
    return `${(size / 1024).toFixed(1)}KB`;
  }
  return `${size}B`;
}

function formatSnapshot(value: unknown) {
  if (!value || (typeof value === "object" && Object.keys(value as Record<string, unknown>).length === 0)) {
    return "";
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function formatSchedule(row: SchedulerTaskRecord) {
  if (row.schedule_type === "cron") {
    return row.cron_expression || "-";
  }
  if (row.schedule_type === "interval") {
    return `每 ${formatDuration(row.interval_seconds)} 执行`;
  }
  if (row.schedule_type === "once") {
    return formatDateTime(row.run_at);
  }
  return "手动触发";
}

function formatDuration(seconds: number) {
  const value = Number(seconds) || 0;
  if (value >= 3600 && value % 3600 === 0) {
    return `${value / 3600} 小时`;
  }
  if (value >= 60 && value % 60 === 0) {
    return `${value / 60} 分钟`;
  }
  return `${value} 秒`;
}

function runStatusType(status: string) {
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

function runStatusLabel(status: string) {
  const map: Record<string, string> = {
    success: "成功",
    failed: "失败",
    running: "执行中",
    skipped: "跳过",
  };
  return map[status] || "未执行";
}

onMounted(async () => {
  await loadContext();
  await loadTasks();
  await openRunsDrawerFromQuery();
  document.addEventListener("visibilitychange", handleVisibilityChange);
  startTaskPolling();
});

watch(
  () => route.query.taskId,
  async () => {
    await openRunsDrawerFromQuery();
  },
);

onBeforeUnmount(() => {
  stopTaskPolling();
  stopRunDetailPolling();
  document.removeEventListener("visibilitychange", handleVisibilityChange);
});
</script>

<template>
  <div class="scheduler-page" v-loading="loading">
    <section class="scheduler-toolbar">
      <div class="filter-row">
        <span class="filter-label">业务</span>
        <el-select
          v-model="selectedBusinessGroupId"
          class="filter-select"
          placeholder="全部业务"
          popper-class="compact-select-popper"
          @change="handleBusinessFilterChange"
        >
          <el-option label="全部业务" :value="ALL_VALUE" />
          <el-option v-for="item in context.business_groups" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>

        <span class="filter-label">项目</span>
        <el-select
          v-model="selectedProjectId"
          class="filter-select"
          placeholder="全部项目"
          popper-class="compact-select-popper"
          @change="handleSearch"
        >
          <el-option label="全部项目" :value="ALL_VALUE" />
          <el-option v-for="item in filteredProjects" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>

        <el-select
          v-model="selectedTaskType"
          class="type-filter"
          placeholder="任务类型"
          popper-class="compact-select-popper"
          @change="handleSearch"
        >
          <el-option label="全部类型" :value="ALL_VALUE" />
          <el-option v-for="item in taskTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>

        <el-select
          v-model="selectedEnabled"
          class="status-filter"
          placeholder="状态"
          popper-class="compact-select-popper"
          @change="handleSearch"
        >
          <el-option label="全部状态" :value="ALL_VALUE" />
          <el-option label="启用" value="true" />
          <el-option label="停用" value="false" />
        </el-select>

        <el-input
          v-model="keyword"
          class="keyword-input"
          clearable
          placeholder="搜索任务名称 / 描述"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-button size="small" :icon="RefreshRight" @click="handleSearch">刷新</el-button>
        <el-button size="small" @click="resetFilters">重置</el-button>
        <el-button size="small" type="primary" @click="openCreateDialog">新增</el-button>
      </div>
    </section>

    <section class="task-list-section">
      <el-table
        :data="paginatedTasks"
        class="task-table"
        height="100%"
        cell-class-name="task-table-cell"
        header-cell-class-name="task-table-header-cell"
      >
        <el-table-column label="序号" width="70" align="center" header-align="center">
          <template #default="{ $index }">
            {{ getRowIndex($index) }}
          </template>
        </el-table-column>
        <el-table-column label="业务" width="92" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.business_group_name || "-" }}
          </template>
        </el-table-column>
        <el-table-column label="项目" width="104" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.project_name || "-" }}
          </template>
        </el-table-column>
        <el-table-column label="任务名称" min-width="190" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="task-name-cell">
              <span class="task-type-badge" :class="`task-type-badge--${taskTypeMeta(row.task_type).tone}`">
                {{ taskTypeLabel(row.task_type) }}
              </span>
              <span class="task-name-label">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="调度规则" min-width="150" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mono-text">{{ formatSchedule(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="下次执行时间" min-width="160" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.enabled ? formatDateTime(row.next_run_at) : "已停用" }}
          </template>
        </el-table-column>
        <el-table-column label="最近一次执行时间" min-width="170" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">
            {{ formatDateTime(row.last_run_at) }}
          </template>
        </el-table-column>
        <el-table-column label="上次结果" width="96" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="runStatusType(row.last_run_status)" effect="light">
              {{ runStatusLabel(row.last_run_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="执行统计" width="110" align="center" header-align="center">
          <template #default="{ row }">
            <span class="stat-text">{{ row.run_count || 0 }} 次 / 失败 {{ row.fail_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="92" align="center" header-align="center">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" size="small" @change="handleToggleTask(row, $event)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" align="center" header-align="center">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button
                size="small"
                text
                type="primary"
                :icon="VideoPlay"
                :loading="runningTaskIds.has(row.id)"
                @click="runTaskNow(row)"
              >
                执行
              </el-button>
              <el-button size="small" text :icon="Tickets" @click="openRunsDrawer(row)">记录</el-button>
              <el-button size="small" text type="primary" :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" text type="danger" :icon="Delete" @click="removeTask(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无定时任务" />
        </template>
      </el-table>

      <AppPagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="pageSizeOptions"
        :total="tasks.length"
        @current-change="handlePageChange"
        @size-change="handlePageSizeChange"
      />
    </section>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑定时任务' : '新增定时任务'" width="920px" destroy-on-close>
      <el-tabs v-model="dialogTab" class="task-dialog-tabs">
        <el-tab-pane label="基本信息" name="basic">
          <el-form label-position="left" label-width="92px" size="small" class="task-form">
            <div class="form-grid">
              <el-form-item label="任务名称">
                <el-input v-model="form.name" placeholder="例如：每日冒烟测试" />
              </el-form-item>
              <el-form-item label="任务类型">
                <el-select v-model="form.task_type" popper-class="compact-select-popper">
                  <el-option v-for="item in taskTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="业务/项目">
                <el-cascader
                  v-model="formBusinessProjectValue"
                  class="business-project-cascader"
                  :options="businessProjectOptions"
                  :props="businessProjectCascaderProps"
                  clearable
                  filterable
                  placeholder="选择业务 / 项目"
                  popper-class="compact-select-popper"
                />
              </el-form-item>
            </div>
            <el-form-item label="任务描述">
              <el-input v-model="form.description" type="textarea" :rows="3" resize="none" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="调度配置" name="schedule">
          <el-form label-position="left" label-width="92px" size="small" class="task-form">
            <div class="form-grid">
              <el-form-item label="调度类型">
                <el-select v-model="form.schedule_type" popper-class="compact-select-popper">
                  <el-option v-for="item in scheduleTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="启用状态">
                <el-switch v-model="form.enabled" active-text="启用" inactive-text="停用" />
              </el-form-item>
              <el-form-item v-if="form.schedule_type === 'cron'" label="快捷规则" class="full-row">
                <div class="preset-row">
                  <el-button
                    v-for="item in cronPresets"
                    :key="item.value"
                    size="small"
                    :type="form.cron_expression === item.value ? 'primary' : 'default'"
                    plain
                    @click="applyCronPreset(item.value)"
                  >
                    {{ item.label }}
                  </el-button>
                </div>
              </el-form-item>
              <el-form-item v-if="form.schedule_type === 'cron'" label="Cron 规则" class="full-row">
                <div class="cron-builder">
                  <el-radio-group v-model="cronBuilder.mode" size="small" class="cron-mode-group">
                    <el-radio-button label="every_minutes">每 N 分钟</el-radio-button>
                    <el-radio-button label="hourly">每小时</el-radio-button>
                    <el-radio-button label="daily">每天</el-radio-button>
                    <el-radio-button label="weekly">每周</el-radio-button>
                    <el-radio-button label="monthly">每月</el-radio-button>
                  </el-radio-group>

                  <div class="cron-row" v-if="cronBuilder.mode === 'every_minutes'">
                    <span>每</span>
                    <el-input-number
                      v-model="cronBuilder.everyMinutes"
                      :min="1"
                      :max="59"
                      controls-position="right"
                    />
                    <span>分钟执行</span>
                  </div>

                  <div class="cron-row" v-else-if="cronBuilder.mode === 'hourly'">
                    <span>每小时的</span>
                    <el-select
                      v-model="cronBuilder.minute"
                      class="cron-select"
                      popper-class="compact-select-popper"
                    >
                      <el-option v-for="item in minuteOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                    <span>执行</span>
                  </div>

                  <div class="cron-row" v-else-if="cronBuilder.mode === 'daily'">
                    <span>每天</span>
                    <el-select v-model="cronBuilder.hour" class="cron-select" popper-class="compact-select-popper">
                      <el-option v-for="item in hourOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                    <el-select v-model="cronBuilder.minute" class="cron-select" popper-class="compact-select-popper">
                      <el-option v-for="item in minuteOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                    <span>执行</span>
                  </div>

                  <div class="cron-row" v-else-if="cronBuilder.mode === 'weekly'">
                    <span>每周</span>
                    <el-select
                      v-model="cronBuilder.weekDays"
                      class="cron-select cron-select--wide"
                      multiple
                      collapse-tags
                      collapse-tags-tooltip
                      popper-class="compact-select-popper"
                    >
                      <el-option v-for="item in weekDayOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                    <el-select v-model="cronBuilder.hour" class="cron-select" popper-class="compact-select-popper">
                      <el-option v-for="item in hourOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                    <el-select v-model="cronBuilder.minute" class="cron-select" popper-class="compact-select-popper">
                      <el-option v-for="item in minuteOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                    <span>执行</span>
                  </div>

                  <div class="cron-row" v-else>
                    <span>每月</span>
                    <el-select v-model="cronBuilder.monthDay" class="cron-select" popper-class="compact-select-popper">
                      <el-option v-for="item in monthDayOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                    <el-select v-model="cronBuilder.hour" class="cron-select" popper-class="compact-select-popper">
                      <el-option v-for="item in hourOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                    <el-select v-model="cronBuilder.minute" class="cron-select" popper-class="compact-select-popper">
                      <el-option v-for="item in minuteOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                    <span>执行</span>
                  </div>

                  <div class="cron-preview">
                    <span>Cron</span>
                    <code>{{ form.cron_expression }}</code>
                  </div>
                </div>
              </el-form-item>
              <el-form-item v-if="form.schedule_type === 'interval'" label="间隔秒数">
                <el-input-number v-model="form.interval_seconds" :min="60" :step="60" controls-position="right" />
              </el-form-item>
              <el-form-item v-if="form.schedule_type === 'once'" label="执行时间">
                <el-date-picker
                  v-model="form.run_at"
                  type="datetime"
                  value-format="YYYY-MM-DD HH:mm:ss"
                  placeholder="选择执行时间"
                  popper-class="compact-select-popper"
                />
              </el-form-item>
            </div>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="执行目标" name="target">
          <el-form label-position="left" label-width="96px" size="small" class="task-form">
            <template v-if="form.task_type === 'test_suite'">
              <el-form-item label="测试集">
                <el-select v-model="form.suite_id" clearable filterable placeholder="选择测试集" popper-class="compact-select-popper">
                  <el-option
                    v-for="item in formSuites"
                    :key="item.id"
                    :label="optionLabel(item)"
                    :value="item.id"
                  />
                </el-select>
              </el-form-item>
            </template>

            <template v-else-if="form.task_type === 'test_case'">
              <el-form-item label="接口用例">
                <el-select
                  v-model="form.case_ids"
                  multiple
                  filterable
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="选择接口用例"
                  popper-class="compact-select-popper"
                >
                  <el-option
                    v-for="item in formCases"
                    :key="item.id"
                    :label="optionLabel(item)"
                    :value="item.id"
                  />
                </el-select>
              </el-form-item>
            </template>

            <template v-else-if="form.task_type === 'python_script'">
              <div class="form-grid">
                <el-form-item label="脚本路径">
                  <el-input v-model="form.script_path" placeholder="scripts/demo.py 或绝对路径" />
                </el-form-item>
                <el-form-item label="工作目录">
                  <el-input v-model="form.working_dir" placeholder="默认脚本所在目录" />
                </el-form-item>
                <el-form-item label="脚本参数" class="full-row">
                  <el-input v-model="form.script_args" placeholder="多个参数用空格隔开" />
                </el-form-item>
              </div>
            </template>

            <template v-else>
              <el-empty description="该任务类型暂未配置专属执行目标" />
            </template>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="高级配置" name="advanced">
          <el-form label-position="left" label-width="112px" size="small" class="task-form">
            <div class="form-grid">
              <el-form-item label="错过策略">
                <el-select v-model="form.misfire_policy" popper-class="compact-select-popper">
                  <el-option label="补偿执行一次" value="fire_once" />
                  <el-option label="跳过本次" value="skip" />
                  <el-option label="全部补偿" value="fire_all" />
                </el-select>
              </el-form-item>
              <el-form-item label="允许并发">
                <el-switch v-model="form.allow_concurrent" active-text="允许" inactive-text="禁止" />
              </el-form-item>
              <el-form-item label="超时秒数">
                <el-input-number v-model="form.timeout_seconds" :min="1" :max="86400" controls-position="right" />
              </el-form-item>
              <el-form-item label="失败重试">
                <el-input-number v-model="form.retry_count" :min="0" :max="10" controls-position="right" />
              </el-form-item>
              <el-form-item label="重试间隔">
                <el-input-number v-model="form.retry_interval_seconds" :min="1" :max="3600" controls-position="right" />
              </el-form-item>
              <el-form-item label="通知邮箱">
                <el-input v-model="form.notify_emails" placeholder="多个邮箱用英文逗号隔开" />
              </el-form-item>
              <el-form-item label="Webhook" class="full-row">
                <el-input v-model="form.notify_webhook" placeholder="企业微信 / 飞书 / 自定义 Webhook" />
              </el-form-item>
            </div>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <div class="dialog-footer">
          <el-button size="small" @click="dialogVisible = false">取消</el-button>
          <el-button size="small" type="primary" :loading="saving" @click="saveTask">确认</el-button>
        </div>
      </template>
    </el-dialog>

    <el-drawer v-model="runsDrawerVisible" :title="currentRunTask ? `${currentRunTask.name} - 执行记录` : '执行记录'" size="920px">
      <div class="runs-drawer" v-loading="runsLoading">
        <div class="runs-toolbar">
          <span>{{ formatRunRetention() || "执行记录按最新时间倒序展示" }}</span>
          <el-button size="small" :icon="RefreshRight" @click="loadRuns()">刷新记录</el-button>
        </div>
        <el-table
          :data="runs"
          class="runs-table"
          height="100%"
          empty-text="暂无执行记录"
          row-key="id"
          @expand-change="handleRunExpandChange"
        >
          <el-table-column type="expand" width="42">
            <template #default="{ row }">
              <div class="run-detail-panel" v-loading="runDetailLoadingIds.has(row.id)">
                <template v-if="row.details_loaded">
                  <div class="run-detail-summary">
                    <span class="run-detail-label">结果</span>
                    <span :class="['run-detail-message', row.status === 'failed' ? 'failed' : '']">
                      {{ row.message || row.result_snapshot?.message || "-" }}
                    </span>
                  </div>
                  <div v-if="formatRunSummary(row)" class="run-detail-summary">
                    <span class="run-detail-label">统计</span>
                    <span class="run-detail-message">{{ formatRunSummary(row) }}</span>
                  </div>

                  <div v-if="row.status === 'failed'" class="failure-summary">
                    <div v-for="item in getRunFailureSummary(row)" :key="item.label" class="failure-summary-item">
                      <span>{{ item.label }}</span>
                      <strong>{{ item.value }}</strong>
                    </div>
                  </div>

                  <div v-if="getLogTruncationText(row)" class="run-log-alert">
                    {{ getLogTruncationText(row) }}
                  </div>

                  <div v-if="hasRetryInfo(row)" class="retry-attempts">
                    <div class="run-detail-label">重试记录</div>
                    <div class="retry-attempt-list">
                      <div v-for="attempt in getRetryAttempts(row)" :key="`${row.id}-retry-${attempt.retry_no}`" class="retry-attempt-item">
                        <el-tag size="small" :type="runStatusType(attempt.status)" effect="light">
                          {{ runStatusLabel(attempt.status) }}
                        </el-tag>
                        <span>第 {{ attempt.attempt_no || attempt.retry_no + 1 }} 次</span>
                        <span>{{ attempt.duration_ms ? `${attempt.duration_ms}ms` : "-" }}</span>
                        <strong>{{ attempt.message || "-" }}</strong>
                      </div>
                    </div>
                  </div>

                  <div v-if="hasPythonLogSections(row)" class="script-log-block">
                    <div class="run-detail-label">脚本输出</div>
                    <el-tabs
                      class="script-log-tabs"
                      :model-value="getScriptActiveTab(row)"
                      @tab-change="handleScriptTabChange(row, $event)"
                    >
                      <el-tab-pane label="stdout" name="stdout">
                        <pre class="run-snapshot">{{ getPythonOutput(row, "stdout") || "无 stdout 输出" }}</pre>
                      </el-tab-pane>
                      <el-tab-pane label="stderr" name="stderr">
                        <pre class="run-snapshot">{{ getPythonOutput(row, "stderr") || "无 stderr 输出" }}</pre>
                      </el-tab-pane>
                      <el-tab-pane v-if="getPythonTraceback(row)" label="traceback" name="traceback">
                        <pre class="run-snapshot">{{ getPythonTraceback(row) }}</pre>
                      </el-tab-pane>
                    </el-tabs>
                  </div>

                  <div v-if="getRunCaseResults(row).length" class="case-run-list">
                    <div
                      v-for="caseResult in getRunCaseResults(row)"
                      :key="`${row.id}-${caseResult.case_id || caseResult.request_id}`"
                      class="case-run-card"
                    >
                      <div class="case-run-head">
                        <div class="case-run-title">
                          <el-tag size="small" :type="runStatusType(caseResult.status || '')" effect="light">
                            {{ runStatusLabel(caseResult.status || '') }}
                          </el-tag>
                          <span>{{ caseResult.case_name || `用例 ${caseResult.case_id || "-"}` }}</span>
                        </div>
                        <span class="case-run-id">{{ caseResult.request_id || "" }}</span>
                      </div>
                      <div v-if="caseResult.message" :class="['case-run-message', caseResult.status === 'failed' ? 'failed' : '']">
                        {{ caseResult.message }}
                      </div>
                      <div v-if="getCaseExecutionLines(caseResult).length" class="run-log-list">
                        <div
                          v-for="(line, lineIndex) in getCaseExecutionLines(caseResult)"
                          :key="`${row.id}-${caseResult.case_id || caseResult.request_id}-${lineIndex}`"
                          :class="['run-log-line', executionLineClass(line)]"
                        >
                          {{ formatExecutionLine(line) }}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div v-if="getRunLogs(row).length" class="run-log-block">
                    <div class="run-detail-label">调度日志</div>
                    <div class="run-log-list">
                      <div
                        v-for="(line, index) in getRunLogs(row)"
                        :key="`${row.id}-log-${index}`"
                        :class="['run-log-line', executionLineClass(line)]"
                      >
                        {{ formatExecutionLine(line) }}
                      </div>
                    </div>
                  </div>

                  <pre
                    v-if="!getRunCaseResults(row).length && !getRunLogs(row).length && formatSnapshot(row.result_snapshot)"
                    class="run-snapshot"
                  >{{ formatSnapshot(row.result_snapshot) }}</pre>
                </template>
                <el-empty v-else description="展开后正在加载日志详情" />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="runStatusType(row.status)" effect="light">
                {{ runStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="重试" width="74" align="center">
            <template #default="{ row }">
              {{ row.retry_no ? `${row.retry_no} 次` : "-" }}
            </template>
          </el-table-column>
          <el-table-column prop="trigger_type" label="触发方式" width="92" align="center" />
          <el-table-column label="开始时间" min-width="150" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              {{ formatDateTime(row.started_at) }}
            </template>
          </el-table-column>
          <el-table-column label="耗时" width="92" align="center">
            <template #default="{ row }">
              {{ row.duration_ms ? `${row.duration_ms}ms` : "-" }}
            </template>
          </el-table-column>
          <el-table-column label="详情大小" width="88" align="center">
            <template #default="{ row }">
              {{ formatRunPayloadSize(row) || "-" }}
            </template>
          </el-table-column>
          <el-table-column prop="message" label="结果描述" min-width="180" align="center" show-overflow-tooltip />
        </el-table>
        <AppPagination
          v-model:current-page="runCurrentPage"
          v-model:page-size="runPageSize"
          :page-sizes="runPageSizeOptions"
          :total="runTotal"
          :disabled="runsLoading"
          @current-change="handleRunPageChange"
          @size-change="handleRunPageSizeChange"
        />
      </div>
    </el-drawer>
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
  overflow: hidden;
}

.scheduler-page :deep(.el-table),
.scheduler-page :deep(.el-button),
.scheduler-page :deep(.el-input__inner),
.scheduler-page :deep(.el-input-number__decrease),
.scheduler-page :deep(.el-input-number__increase),
.scheduler-page :deep(.el-select__placeholder),
.scheduler-page :deep(.el-select__selected-item),
.scheduler-page :deep(.el-form-item__label),
.scheduler-page :deep(.el-textarea__inner),
.scheduler-page :deep(.el-tabs__item),
.scheduler-page :deep(.el-tag),
.scheduler-page :deep(.el-pagination) {
  font-size: 12px;
}

.scheduler-page :deep(.el-dialog__title),
.scheduler-page :deep(.el-drawer__title) {
  font-size: 16px;
}

.scheduler-page :deep(.el-drawer__header) {
  align-items: center;
  min-height: 48px;
  margin-bottom: 0;
  padding: 14px 18px 10px;
}

.scheduler-page :deep(.el-drawer__body) {
  padding: 0 18px 12px;
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
  color: #334155;
  font-size: 12px;
  font-weight: 600;
}

.filter-select {
  width: 160px;
}

.type-filter {
  width: 128px;
}

.status-filter {
  width: 112px;
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

.task-name-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-width: 0;
  width: 100%;
  white-space: nowrap;
}

.task-type-badge {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  min-width: 58px;
  height: 22px;
  padding: 0 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
}

.task-type-badge--blue {
  background: #eff6ff;
  color: #1d4ed8;
}

.task-type-badge--green {
  background: #ecfdf5;
  color: #047857;
}

.task-type-badge--purple {
  background: #f5f3ff;
  color: #6d28d9;
}

.task-type-badge--orange {
  background: #fff7ed;
  color: #c2410c;
}

.task-type-badge--gray {
  background: #f1f5f9;
  color: #475569;
}

.task-name-label {
  display: inline-block;
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #111827;
  font-size: 12px;
  font-weight: 600;
}

.mono-text {
  color: #334155;
  font-family: Consolas, "Liberation Mono", monospace;
  font-size: 12px;
}

.stat-text {
  color: #64748b;
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

.task-dialog-tabs {
  min-height: 420px;
}

.task-form {
  padding: 4px 2px 0;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 24px;
}

.full-row {
  grid-column: 1 / -1;
}

.task-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.task-form :deep(.el-form-item__label) {
  align-items: center;
  justify-content: flex-start;
  height: 32px;
  color: #4e5969;
  font-size: 12px;
  line-height: 32px;
}

.task-form :deep(.el-input),
.task-form :deep(.el-select),
.task-form :deep(.el-cascader),
.task-form :deep(.el-date-editor),
.task-form :deep(.el-input-number) {
  width: 100%;
}

.task-form :deep(.el-input__wrapper),
.task-form :deep(.el-select__wrapper) {
  min-height: 32px;
  border-radius: 6px;
}

.task-form :deep(.el-textarea__inner) {
  min-height: 84px !important;
  border-radius: 6px;
}

.business-project-cascader {
  width: 100%;
}

.preset-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.cron-builder {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  padding: 12px;
  border: 1px solid #e5edf6;
  border-radius: 8px;
  background: #fbfdff;
}

.cron-mode-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
}

.cron-builder :deep(.el-radio-button__inner) {
  min-width: 74px;
  padding: 7px 12px;
  font-size: 12px;
}

.cron-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  color: #4e5969;
  font-size: 12px;
}

.cron-row :deep(.el-input-number) {
  width: 120px;
}

.cron-select {
  width: 104px !important;
}

.cron-select--wide {
  width: 210px !important;
}

.cron-preview {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: fit-content;
  max-width: 100%;
  padding: 5px 10px;
  border-radius: 6px;
  background: #eef4ff;
  color: #64748b;
  font-size: 12px;
}

.cron-preview code {
  color: #1d4ed8;
  font-family: Consolas, "Liberation Mono", monospace;
  font-size: 12px;
  font-weight: 700;
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.dialog-footer :deep(.el-button) {
  min-width: 64px;
}

.runs-drawer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  gap: 6px;
}

.runs-toolbar {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 30px;
  color: #64748b;
  font-size: 12px;
}

.runs-table {
  flex: 1 1 auto;
  min-height: 0;
}

.run-detail-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 14px 14px;
  background: #f8fafc;
  border: 1px solid #e5edf6;
  border-radius: 6px;
  text-align: left;
}

.run-detail-summary {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
}

.run-detail-label {
  flex: 0 0 auto;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.run-detail-message {
  min-width: 0;
  color: #334155;
  line-height: 1.6;
  word-break: break-all;
}

.run-detail-message.failed,
.case-run-message.failed {
  color: #dc2626;
  font-weight: 600;
}

.failure-summary {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}

.failure-summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid #fecaca;
  border-radius: 6px;
  background: #fff7f7;
}

.failure-summary-item span {
  color: #991b1b;
  font-size: 11px;
  font-weight: 600;
}

.failure-summary-item strong {
  overflow: hidden;
  color: #7f1d1d;
  font-size: 12px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.run-log-alert {
  padding: 8px 10px;
  border: 1px solid #fde68a;
  border-radius: 6px;
  background: #fffbeb;
  color: #92400e;
  font-size: 12px;
}

.retry-attempts,
.script-log-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.retry-attempt-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.retry-attempt-item {
  display: grid;
  grid-template-columns: 72px 72px 86px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  min-height: 30px;
  padding: 6px 8px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #ffffff;
  color: #475569;
}

.retry-attempt-item strong {
  overflow: hidden;
  color: #334155;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.script-log-tabs {
  padding: 0 10px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #ffffff;
}

.script-log-tabs :deep(.el-tabs__header) {
  margin-bottom: 8px;
}

.case-run-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.case-run-card {
  padding: 10px 12px;
  border: 1px solid #e5edf6;
  border-radius: 6px;
  background: #ffffff;
}

.case-run-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.case-run-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  color: #1f2937;
  font-weight: 600;
}

.case-run-title span:last-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.case-run-id {
  flex: 0 0 auto;
  color: #94a3b8;
  font-family: Consolas, "Courier New", monospace;
  font-size: 11px;
}

.case-run-message {
  margin-top: 8px;
  color: #475569;
  line-height: 1.6;
  word-break: break-all;
}

.run-log-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.run-log-list {
  max-height: 320px;
  padding: 8px 10px;
  overflow: auto;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #ffffff;
}

.run-log-line {
  color: #334155;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
}

.run-log-line.error {
  color: #dc2626;
  font-weight: 600;
}

.run-log-line.warn {
  color: #d97706;
}

.run-log-line.debug {
  color: #6b7280;
}

.run-snapshot {
  max-height: 320px;
  margin: 0;
  padding: 10px 12px;
  overflow: auto;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #ffffff;
  color: #334155;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

@media (max-width: 1180px) {
  .filter-row {
    align-items: stretch;
    flex-wrap: wrap;
  }

  .keyword-input {
    width: 100%;
    min-width: 0;
  }

  .failure-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .failure-summary,
  .retry-attempt-item {
    grid-template-columns: 1fr;
  }
}
</style>
