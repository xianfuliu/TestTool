import { del, get, post, put } from "@/shared/api/client";

import type { GlobalVariablePayload, GlobalVariableRecord } from "./types";

const BASE = "/api/interface-auto/variables";

export function fetchGlobalVariables(params?: {
  keyword?: string;
  business_group_id?: number | null;
  project_id?: number | null;
  environment_id?: number | null;
}) {
  return get<GlobalVariableRecord[]>(`${BASE}/`, {
    keyword: params?.keyword ?? "",
    business_group_id: params?.business_group_id ?? "",
    project_id: params?.project_id ?? "",
    environment_id: params?.environment_id ?? "",
  });
}

export function createGlobalVariable(payload: GlobalVariablePayload) {
  return post<{ variable_id: number }>(`${BASE}/`, payload as unknown as Record<string, unknown>);
}

export function updateGlobalVariable(variableId: number, payload: GlobalVariablePayload) {
  return put<{ updated: boolean }>(`${BASE}/${variableId}/`, payload as unknown as Record<string, unknown>);
}

export function deleteGlobalVariable(variableId: number) {
  return del<{ deleted: boolean }>(`${BASE}/${variableId}/`);
}
