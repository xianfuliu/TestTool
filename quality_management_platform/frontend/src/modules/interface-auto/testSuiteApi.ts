import { del, get, post, put } from "@/shared/api/client";

import type { SchedulerTaskRecord } from "@/modules/scheduler/api";

export const TEST_SUITE_SCHEDULER_SOURCE = "interface_auto.test_suite";

export type TestSuiteCase = {
  case_id: number;
  sort_order: number;
  name: string;
  description?: string;
  folder_id: number | null;
  folder_name?: string | null;
  project_id: number;
};

export type TestSuiteRecord = {
  id: number;
  project_id: number;
  project_name?: string | null;
  business_group_id?: number | null;
  business_group_name?: string | null;
  name: string;
  description: string;
  notify_emails: string[];
  email_config: Record<string, unknown>;
  case_count: number;
  case_ids: number[];
  cases: TestSuiteCase[];
  scheduler_task: SchedulerTaskRecord | null;
  created_at?: string;
  updated_at?: string;
};

export type TestSuitePayload = {
  project_id: number;
  name: string;
  description: string;
  case_ids: number[];
  notify_emails: string[];
  email_config: Record<string, unknown>;
};

const BASE = "/api/interface-auto/test-suites";

export function fetchTestSuites(params?: { project_id?: number | null; keyword?: string }) {
  return get<TestSuiteRecord[]>(`${BASE}/`, {
    project_id: params?.project_id ?? "",
    keyword: params?.keyword ?? "",
  });
}

export function fetchTestSuiteDetail(suiteId: number) {
  return get<TestSuiteRecord>(`${BASE}/${suiteId}/`);
}

export function createTestSuite(payload: TestSuitePayload) {
  return post<{ suite_id: number }>(`${BASE}/`, payload as unknown as Record<string, unknown>);
}

export function updateTestSuite(suiteId: number, payload: TestSuitePayload) {
  return put<{ updated: boolean; suite: TestSuiteRecord }>(
    `${BASE}/${suiteId}/`,
    payload as unknown as Record<string, unknown>,
  );
}

export function deleteTestSuite(suiteId: number) {
  return del<{ deleted: boolean }>(`${BASE}/${suiteId}/`);
}
