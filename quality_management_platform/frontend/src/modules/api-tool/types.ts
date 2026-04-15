export type ApiToolProduct = {
  id: number;
  name: string;
  legacy_config_path: string;
  enable_encryption: boolean;
  encrypt_url: string;
  decrypt_url: string;
  locked: boolean;
  is_default: boolean;
  sort_order: number;
  created_at?: string;
  updated_at?: string;
};

export type LayoutOption = {
  text: string;
  value: string;
};

export type ApiToolLayoutItem = {
  type: "field" | "combo" | "interface" | "sql" | "condition" | "formula";
  key?: string;
  label?: string;
  name?: string;
  default?: string;
  data_type?: string;
  options?: LayoutOption[];
  show_in_ui?: boolean;
  priority: number;
  condition_field?: string;
  mappings?: Record<string, string>;
  formula?: string;
  formula_type?: string;
};

export type ApiToolInterfaceConfig = {
  url: string;
  method: string;
  headers: Record<string, unknown>;
  body_template?: unknown;
  conditional_body?: {
    field?: string;
    cases?: Record<string, unknown>;
    default_body?: unknown;
    request_bodies?: Array<{
      conditions: Array<{
        field: string;
        values: string[];
      }>;
      body_template: unknown;
    }>;
  };
  response_mapping: Record<string, string>;
  field_types: Record<string, string>;
  enable_encryption?: boolean;
};

export type ApiToolSqlConfig = {
  database: {
    host: string;
    port: number;
    user: string;
    password: string;
    database: string;
    charset?: string;
  };
  sql: string;
  output_fields: Array<{
    field: string;
    description: string;
  }>;
};

export type ApiToolScheduleTask = {
  id: string;
  jobGroup: string;
  name: string;
  row_id: number;
};

export type ApiToolGlobalExtraction = {
  variable: string;
  path: string;
};

export type ApiToolGlobalLoginRequestConfig = {
  enabled: boolean;
  protocol?: string;
  method: string;
  url: string;
  headers: Record<string, unknown>;
  params?: Record<string, unknown>;
  body: unknown;
  timeout?: number;
  retry_enabled?: boolean;
  retry_count?: number;
  extractions: ApiToolGlobalExtraction[];
};

export type ApiToolGlobalHeaderConfig = {
  enabled: boolean;
  headers: Record<string, unknown>;
};

export type ApiToolGlobalRequestConfig = {
  login_request: ApiToolGlobalLoginRequestConfig;
  header_config: ApiToolGlobalHeaderConfig;
};

export type ApiToolConfig = {
  enable_encryption: boolean;
  encrypt_url: string;
  decrypt_url: string;
  global_request_config: ApiToolGlobalRequestConfig;
  global_headers?: Record<string, unknown>;
  schedule_tasks: ApiToolScheduleTask[];
  layout: ApiToolLayoutItem[];
  interfaces: Record<string, ApiToolInterfaceConfig>;
  sqls: Record<string, ApiToolSqlConfig>;
};

export type ApiToolProductDetail = {
  product: ApiToolProduct;
  config: ApiToolConfig;
};

export type ApiToolProductsPayload = {
  default_product_id: number | null;
  default_product: string | null;
  products: ApiToolProduct[];
};

export type ApiToolPreviewResult = {
  interface_name: string;
  request_id: string;
  resolved_variables: Record<string, unknown>;
  request: {
    protocol?: string;
    url: string;
    method: string;
    headers: Record<string, unknown>;
    body: unknown;
  };
  encryption: {
    enabled: boolean;
    encrypt_url: string;
    decrypt_url: string;
  };
};

export type ApiToolExecuteResult = {
  request_id: string;
  request: {
    protocol?: string;
    url: string;
    method: string;
    headers: Record<string, unknown>;
    body: unknown;
  };
  status_code: number;
  headers: Record<string, unknown>;
  body: unknown;
  raw_body: unknown;
  decrypted_body: unknown;
  mapped_values: Record<string, unknown>;
  resolved_variables: Record<string, unknown>;
};

export type ApiToolSqlExecuteResult = {
  request_id: string;
  sql_name: string;
  resolved_sql: string;
  rows: Array<Record<string, unknown>>;
  output_variables: Record<string, unknown>;
  resolved_variables: Record<string, unknown>;
};
