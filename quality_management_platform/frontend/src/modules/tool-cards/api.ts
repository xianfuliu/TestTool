import { del, get, post, put } from "@/shared/api/client";

import type {
  ToolCard,
  ToolCardExecutionResult,
  ToolCardFolder,
  ToolCardFolderDetail,
  ToolCardsBootstrapPayload,
} from "./types";

export function fetchToolCardsBootstrap(force = false) {
  return post<ToolCardsBootstrapPayload>("/api/tool-cards/bootstrap/", { force });
}

export function fetchToolCardFolders() {
  return get<ToolCardFolder[]>("/api/tool-cards/folders/");
}

export function createToolCardFolder(payload: Record<string, unknown>) {
  return post<ToolCardFolderDetail>("/api/tool-cards/folders/", payload);
}

export function updateToolCardFolder(folderId: number, payload: Record<string, unknown>) {
  return put<ToolCardFolderDetail>(`/api/tool-cards/folders/${folderId}/`, payload);
}

export function deleteToolCardFolder(folderId: number) {
  return del<{ deleted: boolean; folder_id: number }>(`/api/tool-cards/folders/${folderId}/`);
}

export function fetchToolCardFolderDetail(folderId: number) {
  return get<ToolCardFolderDetail>(`/api/tool-cards/folders/${folderId}/`);
}

export function fetchToolCardsByFolder(folderId: number) {
  return get<ToolCard[]>("/api/tool-cards/cards/", { folder_id: folderId });
}

export function createToolCard(payload: Record<string, unknown>) {
  return post<ToolCard>("/api/tool-cards/cards/", payload);
}

export function updateToolCard(cardId: number, payload: Record<string, unknown>) {
  return put<ToolCard>(`/api/tool-cards/cards/${cardId}/`, payload);
}

export function deleteToolCard(cardId: number) {
  return del<{ deleted: boolean; card_id: number }>(`/api/tool-cards/cards/${cardId}/`);
}

export function copyToolCard(cardId: number) {
  return post<ToolCard>(`/api/tool-cards/cards/${cardId}/copy/`);
}

export function executeToolCard(cardId: number, variables: Record<string, unknown>) {
  return post<ToolCardExecutionResult>(`/api/tool-cards/cards/${cardId}/execute/`, { variables });
}
