import { del, get, post, put } from "@/shared/api/client";

import type {
  ApiToolExecuteResult,
  ApiToolPreviewResult,
  ApiToolProductDetail,
  ApiToolProductsPayload,
  ApiToolSqlExecuteResult,
} from "./types";

export function fetchApiToolProducts() {
  return get<ApiToolProductsPayload>("/api/api-tool/products/");
}

export function fetchApiToolProductDetail(productId: number) {
  return get<ApiToolProductDetail>(`/api/api-tool/products/${productId}/`);
}

export function createApiToolProduct(payload: Record<string, unknown>) {
  return post<ApiToolProductDetail>("/api/api-tool/products/", payload);
}

export function updateApiToolProduct(productId: number, payload: Record<string, unknown>) {
  return put<ApiToolProductDetail>(`/api/api-tool/products/${productId}/`, payload);
}

export function deleteApiToolProduct(productId: number) {
  return del<{ deleted: boolean }>(`/api/api-tool/products/${productId}/`);
}

export function previewApiToolRequest(payload: Record<string, unknown>) {
  return post<ApiToolPreviewResult>("/api/api-tool/preview/", payload);
}

export function executeApiToolRequest(payload: Record<string, unknown>) {
  return post<ApiToolExecuteResult>("/api/api-tool/execute/", payload);
}

export function executeApiToolSql(payload: Record<string, unknown>) {
  return post<ApiToolSqlExecuteResult>("/api/api-tool/execute-sql/", payload);
}

export function executeApiToolSchedule(payload: Record<string, unknown>) {
  return post<{ task_id: number; task_name: string; product_name: string; message: string }>(
    "/api/api-tool/execute-schedule/",
    payload,
  );
}
