import { del, get, post, put } from "@/shared/api/client";

export type BusinessGroupRecord = {
  id: number;
  name: string;
  description: string;
  created_at?: string;
  updated_at?: string;
};

export type ProjectRecord = {
  id: number;
  business_group_id: number | null;
  group_name?: string | null;
  name: string;
  description: string;
  created_at?: string;
  updated_at?: string;
};

export type BusinessGroupStats = {
  project_count: number;
  api_count: number;
  case_count: number;
};

export type ProjectStats = {
  api_count: number;
  case_count: number;
};

const BASE = "/api/common";

export function fetchBusinessGroups() {
  return get<BusinessGroupRecord[]>(`${BASE}/business-groups/`);
}

export function createBusinessGroup(payload: Partial<BusinessGroupRecord>) {
  return post<{ group_id: number }>(`${BASE}/business-groups/`, payload as Record<string, unknown>);
}

export function updateBusinessGroup(groupId: number, payload: Partial<BusinessGroupRecord>) {
  return put<{ updated: boolean }>(`${BASE}/business-groups/${groupId}/`, payload as Record<string, unknown>);
}

export function deleteBusinessGroup(groupId: number) {
  return del<{ deleted: boolean }>(`${BASE}/business-groups/${groupId}/`);
}

export function fetchBusinessGroupStats(groupId: number) {
  return get<BusinessGroupStats>(`${BASE}/business-groups/${groupId}/stats/`);
}

export function fetchProjects(groupId?: number | null) {
  return get<ProjectRecord[]>(`${BASE}/projects/`, groupId ? { business_group_id: groupId } : undefined);
}

export function createProject(payload: Partial<ProjectRecord>) {
  return post<{ project_id: number }>(`${BASE}/projects/`, payload as Record<string, unknown>);
}

export function updateProject(projectId: number, payload: Partial<ProjectRecord>) {
  return put<{ updated: boolean }>(`${BASE}/projects/${projectId}/`, payload as Record<string, unknown>);
}

export function deleteProject(projectId: number) {
  return del<{ deleted: boolean }>(`${BASE}/projects/${projectId}/`);
}

export function fetchProjectStats(projectId: number) {
  return get<ProjectStats>(`${BASE}/projects/${projectId}/stats/`);
}
