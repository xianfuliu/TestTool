import { del, get, post, put } from "@/shared/api/client";

import type { EnvironmentPayload, EnvironmentRecord } from "./environmentTypes";

const BASE = "/api/common/environments";

export function fetchEnvironments() {
  return get<EnvironmentRecord[]>(`${BASE}/`);
}

export function createEnvironment(payload: EnvironmentPayload) {
  return post<{ environment_id: number }>(`${BASE}/`, payload as unknown as Record<string, unknown>);
}

export function updateEnvironment(environmentId: number, payload: EnvironmentPayload) {
  return put<{ updated: boolean }>(`${BASE}/${environmentId}/`, payload as unknown as Record<string, unknown>);
}

export function deleteEnvironment(environmentId: number) {
  return del<{ deleted: boolean }>(`${BASE}/${environmentId}/`);
}
