import { del, get, post, put } from "@/shared/api/client";
import type { GlobalToolPayload, GlobalToolRecord, GlobalToolType } from "./types";

const BASE = "/api/interface-auto/global-tools";

export function fetchGlobalTools(params?: {
  tool_type?: GlobalToolType | "";
  keyword?: string;
  business_group_id?: number | null;
  project_id?: number | null;
  visible_project_id?: number | null;
}) {
  return get<GlobalToolRecord[]>(`${BASE}/`, {
    tool_type: params?.tool_type ?? "",
    keyword: params?.keyword ?? "",
    business_group_id: params?.business_group_id ?? "",
    project_id: params?.project_id ?? "",
    visible_project_id: params?.visible_project_id ?? "",
  });
}

export function createGlobalTool(payload: GlobalToolPayload) {
  return post<{ tool_id: number }>(`${BASE}/`, payload as unknown as Record<string, unknown>);
}

export function updateGlobalTool(toolId: number, payload: GlobalToolPayload) {
  return put<{ updated: boolean }>(`${BASE}/${toolId}/`, payload as unknown as Record<string, unknown>);
}

export function deleteGlobalTool(toolId: number) {
  return del<{ deleted: boolean }>(`${BASE}/${toolId}/`);
}

export function updateGlobalToolStatus(toolId: number, enabled: boolean) {
  return post<{ updated: boolean }>(`${BASE}/${toolId}/status/`, { enabled });
}
