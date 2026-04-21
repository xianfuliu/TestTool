import { del, get, post, put } from "@/shared/api/client";

export type SchedulerTaskType = "test_suite" | "test_case" | "python_script" | "http_callback" | "custom";
export type SchedulerScheduleType = "cron" | "interval" | "once" | "manual";

export type SchedulerContextProject = {
  id: number;
  business_group_id: number | null;
  business_group_name?: string | null;
  name: string;
};

export type SchedulerContextBusinessGroup = {
  id: number;
  name: string;
};

export type SchedulerContextSuite = {
  id: number;
  project_id: number;
  project_name?: string | null;
  business_group_name?: string | null;
  name: string;
};

export type SchedulerContextCase = {
  id: number;
  project_id: number;
  project_name?: string | null;
  business_group_name?: string | null;
  name: string;
};

export type SchedulerContext = {
  business_groups: SchedulerContextBusinessGroup[];
  projects: SchedulerContextProject[];
  test_suites: SchedulerContextSuite[];
  test_cases: SchedulerContextCase[];
};

export type SchedulerTaskRecord = {
  id: number;
  business_group_id: number | null;
  business_group_name?: string | null;
  project_id: number | null;
  project_name?: string | null;
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
  target_config: Record<string, unknown>;
  notify_config: Record<string, unknown>;
  misfire_policy: string;
  allow_concurrent: boolean;
  timeout_seconds: number;
  retry_count: number;
  retry_interval_seconds: number;
  enabled: boolean;
  status: string;
  last_run_status: string;
  last_run_message: string;
  last_run_at: string | null;
  next_run_at: string | null;
  run_count: number;
  fail_count: number;
  created_at?: string;
  updated_at?: string;
};

export type SchedulerTaskPayload = {
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
  target_config: Record<string, unknown>;
  notify_config: Record<string, unknown>;
  misfire_policy: string;
  allow_concurrent: boolean;
  timeout_seconds: number;
  retry_count: number;
  retry_interval_seconds: number;
  enabled: boolean;
};

export type SchedulerTaskRunRecord = {
  id: number;
  task_id: number;
  trigger_type: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number;
  executor: string;
  retry_no: number;
  message: string;
  request_snapshot: Record<string, unknown>;
  result_snapshot: Record<string, unknown>;
  logs: string[];
  created_at?: string;
};

const BASE = "/api/scheduler";

export function fetchSchedulerContext(params?: { project_id?: number | null }) {
  return get<SchedulerContext>(`${BASE}/context/`, {
    project_id: params?.project_id ?? "",
  });
}

export function fetchSchedulerTasks(params?: {
  keyword?: string;
  business_group_id?: number | null;
  project_id?: number | null;
  task_type?: string;
  enabled?: string;
}) {
  return get<SchedulerTaskRecord[]>(`${BASE}/tasks/`, {
    keyword: params?.keyword ?? "",
    business_group_id: params?.business_group_id ?? "",
    project_id: params?.project_id ?? "",
    task_type: params?.task_type ?? "",
    enabled: params?.enabled ?? "",
  });
}

export function createSchedulerTask(payload: SchedulerTaskPayload) {
  return post<{ task_id: number }>(`${BASE}/tasks/`, payload as Record<string, unknown>);
}

export function updateSchedulerTask(taskId: number, payload: SchedulerTaskPayload) {
  return put<{ updated: boolean }>(`${BASE}/tasks/${taskId}/`, payload as Record<string, unknown>);
}

export function deleteSchedulerTask(taskId: number) {
  return del<{ deleted: boolean }>(`${BASE}/tasks/${taskId}/`);
}

export function updateSchedulerTaskStatus(taskId: number, enabled: boolean) {
  return post<{ updated: boolean; enabled: boolean; next_run_at: string | null }>(
    `${BASE}/tasks/${taskId}/status/`,
    { enabled },
  );
}

export function runSchedulerTask(taskId: number) {
  return post<SchedulerTaskRunRecord>(`${BASE}/tasks/${taskId}/run/`, { trigger_type: "manual" });
}

export function fetchSchedulerTaskRuns(taskId: number, limit = 50) {
  return get<SchedulerTaskRunRecord[]>(`${BASE}/tasks/${taskId}/runs/`, { limit });
}
