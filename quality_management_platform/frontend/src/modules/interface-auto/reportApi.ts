import { del, get } from "@/shared/api/client";

import type { SchedulerExecutionLogLine } from "@/modules/scheduler/api";

export type ReportStatus = "success" | "failed" | "running" | "skipped" | "pending" | string;

export type ReportPagination = {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
};

export type ReportEmailDelivery = {
  status?: "sent" | "failed" | "skipped" | string;
  message?: string;
  recipients?: string[];
  sent_at?: string;
};

export type ReportCaseStep = {
  step_id?: number | null;
  step_order?: number | string | null;
  step_name?: string;
  status?: ReportStatus;
  message?: string;
  summary?: string;
  error_message?: string;
  started_at?: string;
  ended_at?: string;
  execution_time?: number;
  logs?: string[];
  [key: string]: unknown;
};

export type ReportCaseItem = {
  key: string;
  case_id?: number | null;
  case_name: string;
  status: ReportStatus;
  message?: string;
  duration?: number;
  execution_time?: number;
  duration_ms?: number;
  started_at?: string;
  ended_at?: string;
  summary?: {
    passed_steps?: number;
    failed_steps?: number;
    skipped_steps?: number;
    [key: string]: unknown;
  };
  steps: ReportCaseStep[];
  execution_log?: {
    lines?: SchedulerExecutionLogLine[];
    steps?: ReportCaseStep[];
    [key: string]: unknown;
  };
};

export type TestReportRecord = {
  id: number;
  report_type?: string;
  scheduler_id?: number | null;
  scheduler_task_id?: number | null;
  scheduler_run_id?: number | null;
  suite_id?: number | null;
  suite_name?: string | null;
  case_id?: number | null;
  case_name?: string | null;
  project_id?: number | null;
  project_name?: string | null;
  business_group_id?: number | null;
  business_group_name?: string | null;
  report_name: string;
  status: ReportStatus;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  error_cases: number;
  start_time?: string | null;
  end_time?: string | null;
  duration?: number;
  trigger_type?: string;
  summary_json?: Record<string, unknown>;
  email_delivery?: ReportEmailDelivery | null;
  created_at?: string;
};

export type TestReportDetail = TestReportRecord & {
  cases: ReportCaseItem[];
};

export type TestReportGroup = {
  key: string;
  group_type: "test_suite" | "test_case" | "unknown" | string;
  suite_id?: number | null;
  suite_name?: string | null;
  case_id?: number | null;
  case_name?: string | null;
  name: string;
  business_group_id?: number | null;
  business_group_name?: string | null;
  project_id?: number | null;
  project_name?: string | null;
  latest_report_id?: number | null;
  latest_report_name?: string | null;
  status: ReportStatus;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  error_cases: number;
  start_time?: string | null;
  end_time?: string | null;
  duration?: number;
  trigger_type?: string;
  email_delivery?: ReportEmailDelivery | null;
  created_at?: string;
  report_count: number;
  records: TestReportRecord[];
};

export type ReportListResponse = {
  data: TestReportRecord[];
  pagination: ReportPagination;
};

export type ReportGroupListResponse = {
  data: TestReportGroup[];
  pagination: ReportPagination;
};

const BASE = "/api/interface-auto/reports";

export function fetchTestReports(params?: {
  project_id?: number | null;
  suite_id?: number | null;
  status?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
}) {
  return get<ReportListResponse>(`${BASE}/`, {
    project_id: params?.project_id ?? "",
    suite_id: params?.suite_id ?? "",
    status: params?.status ?? "",
    keyword: params?.keyword ?? "",
    page: params?.page ?? 1,
    page_size: params?.page_size ?? 20,
  });
}

export function fetchTestReportGroups(params?: {
  project_id?: number | null;
  suite_id?: number | null;
  status?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
}) {
  return get<ReportGroupListResponse>(`${BASE}/`, {
    view: "suite_groups",
    project_id: params?.project_id ?? "",
    suite_id: params?.suite_id ?? "",
    status: params?.status ?? "",
    keyword: params?.keyword ?? "",
    page: params?.page ?? 1,
    page_size: params?.page_size ?? 20,
  });
}

export function fetchTestReportGroupRecords(params: {
  suite_id?: number | null;
  case_id?: number | null;
  status?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
  skip_latest?: boolean;
}) {
  return get<ReportListResponse>(`${BASE}/`, {
    view: "group_records",
    suite_id: params.suite_id ?? "",
    case_id: params.case_id ?? "",
    status: params.status ?? "",
    keyword: params.keyword ?? "",
    page: params.page ?? 1,
    page_size: params.page_size ?? 10,
    skip_latest: params.skip_latest ? "true" : "",
  });
}

export function fetchTestReportDetail(reportId: number) {
  return get<TestReportDetail>(`${BASE}/${reportId}/`);
}

export function deleteTestReport(reportId: number) {
  return del<{ deleted: boolean }>(`${BASE}/${reportId}/`);
}
