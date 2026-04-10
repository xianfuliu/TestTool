export type JsonMap = Record<string, string>;

export type ApiFolder = {
  id: number;
  project_id: number;
  parent_id: number | null;
  name: string;
  description?: string;
  template_count?: number;
};

export type ApiTemplate = {
  id?: number;
  tabKey?: string;
  project_id: number;
  folder_id: number | null;
  name: string;
  method: string;
  url_path: string;
  headers: JsonMap;
  params: JsonMap;
  body: unknown;
  description: string;
  timeout: number;
  retry_enabled: boolean;
  retry_count: number;
  sort_order: number;
};

export type WorkspacePayload = {
  folders: ApiFolder[];
  templates: ApiTemplate[];
};

export type KeyValueRow = {
  id: string;
  key: string;
  value: string;
};

export type TreeNode = {
  id: string;
  rawId: number | null;
  label: string;
  type: "folder" | "template";
  folderId: number | null;
  parentFolderId: number | null;
  template?: ApiTemplate;
  method?: string;
  children?: TreeNode[];
};

export type CascaderOption = {
  value: number;
  label: string;
  children?: CascaderOption[];
  disabled?: boolean;
};
