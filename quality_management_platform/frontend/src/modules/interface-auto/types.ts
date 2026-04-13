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

export type CaseFolder = {
  id: number;
  project_id: number;
  parent_id: number | null;
  name: string;
  description?: string;
  sort_order?: number;
};

export type EnvironmentRecord = {
  id: number;
  name: string;
  base_url?: string;
  description?: string;
  headers?: JsonMap | string | null;
  variables?: JsonMap | string | null;
};

export type GlobalVariableRecord = {
  id: number;
  project_id: number;
  name: string;
  value: string;
  variable_type?: string;
  description?: string;
};

export type CaseToolRecord = {
  id?: string;
  name?: string;
  tool_type?: string;
  summary?: string;
  enabled?: boolean;
  priority?: number;
  tool_label?: string;
  assertion_type?: string;
  output_fields?: string[];
  extractions?: Array<{ variable: string; path: string }>;
  assertions?: Array<{ field: string; operator: string; expected: string }>;
  config?: Record<string, unknown>;
  [key: string]: unknown;
};

export type CaseToolMap = Record<string, CaseToolRecord>;

export type CaseStep = {
  id?: number;
  case_id?: number;
  api_template_id: number | null;
  step_order: number;
  name: string;
  enabled: boolean;
  pre_processing: CaseToolMap | string | null;
  post_processing: CaseToolMap | string | null;
  assertions: CaseToolMap | string | null;
  variables: JsonMap | string | null;
  enable_encryption: boolean;
  api_name?: string;
  api_method?: string;
  api_url_path?: string;
  api_folder_id?: number | null;
  api_project_id?: number | null;
  api_description?: string;
  api_template?: ApiTemplate | null;
  stepKey?: string;
};

export type TestCaseRecord = {
  id?: number;
  tabKey?: string;
  project_id: number;
  folder_id: number | null;
  name: string;
  description: string;
  environment_id: number | null;
  global_vars: JsonMap | string | null;
  enable_encryption: boolean;
  encrypt_url: string;
  decrypt_url: string;
  sort_order: number;
  steps: CaseStep[];
};

export type CaseTreeNode = {
  id: string;
  rawId: number | null;
  label: string;
  type: "folder" | "case";
  folderId: number | null;
  caseItem?: TestCaseRecord;
  children?: CaseTreeNode[];
};
