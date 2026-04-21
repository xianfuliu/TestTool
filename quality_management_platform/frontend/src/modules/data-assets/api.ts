import { del, get, post, put } from "@/shared/api/client";

export type DatabaseConnectionRecord = {
  id: number;
  business_group_id: number;
  business_group_name?: string | null;
  name: string;
  db_type: string;
  host: string;
  port: number;
  database_name: string;
  username: string;
  password: string;
  charset: string;
  description: string;
  enabled: boolean;
  created_at?: string;
  updated_at?: string;
};

export type DatabaseConnectionPayload = {
  business_group_id: number | null;
  name: string;
  db_type: string;
  host: string;
  port: number;
  database_name: string;
  username: string;
  password: string;
  charset: string;
  description: string;
  enabled: boolean;
};

const BASE = "/api/data-assets/databases";

export function fetchDatabaseConnections(params?: {
  keyword?: string;
  business_group_id?: number | null;
}) {
  return get<DatabaseConnectionRecord[]>(`${BASE}/`, {
    keyword: params?.keyword ?? "",
    business_group_id: params?.business_group_id ?? "",
  });
}

export function createDatabaseConnection(payload: DatabaseConnectionPayload) {
  return post<{ database_id: number }>(`${BASE}/`, payload as Record<string, unknown>);
}

export function updateDatabaseConnection(databaseId: number, payload: DatabaseConnectionPayload) {
  return put<{ updated: boolean }>(`${BASE}/${databaseId}/`, payload as Record<string, unknown>);
}

export function deleteDatabaseConnection(databaseId: number) {
  return del<{ deleted: boolean }>(`${BASE}/${databaseId}/`);
}

export function testDatabaseConnection(payload: DatabaseConnectionPayload) {
  return post<{ connected: boolean; message: string; duration_ms?: number }>(
    `${BASE}/test-connection/`,
    payload as Record<string, unknown>,
  );
}
