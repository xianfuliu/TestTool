export type ToolCardOption = {
  id?: number;
  value: string;
  label: string;
  sort_order: number;
};

export type ToolCardParameter = {
  id?: number;
  field_key: string;
  display_name: string;
  field_type: "input" | "select" | "multi_select" | "radio";
  default_value: string;
  required: boolean;
  association_enabled: boolean;
  association_field: string;
  association_value: string[];
  sort_order: number;
  options: ToolCardOption[];
};

export type ToolCardFolder = {
  id: number;
  name: string;
  description: string;
  parent_id: number | null;
  sort_order: number;
  is_default: boolean;
  card_count: number;
  created_at?: string;
  updated_at?: string;
};

export type ToolCardSqlConfig = {
  host: string;
  port: number;
  username: string;
  password: string;
  database_name: string;
  query_text: string;
};

export type ToolCardHttpConfig = {
  url: string;
  method: string;
  headers_text: string;
  body_text: string;
};

export type ToolCardPythonConfig = {
  module_name: string;
  class_name: string;
  method_name: string;
  args_text: string;
};

export type ToolCard = {
  id: number;
  folder_id: number;
  name: string;
  description: string;
  card_type: "sql" | "http" | "python";
  type: "sql" | "http" | "python";
  sort_order: number;
  enabled: boolean;
  sql_config: ToolCardSqlConfig;
  http_config: ToolCardHttpConfig;
  python_config: ToolCardPythonConfig;
  config: Record<string, unknown>;
  parameters: ToolCardParameter[];
  mappings: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
};

export type ToolCardsBootstrapPayload = {
  folders: ToolCardFolder[];
  selected_folder_id: number | null;
  cards: ToolCard[];
  imported_from_json: boolean;
  imported_from_legacy_cache: boolean;
};

export type ToolCardFolderDetail = {
  folder: ToolCardFolder;
  children: ToolCardFolder[];
  cards: ToolCard[];
};

export type ToolCardExecutionResult = {
  card_id: number;
  card_name: string;
  card_type: string;
  variables: Record<string, unknown>;
  mode: "sql" | "http" | "python";
  request: Record<string, unknown>;
  result: Record<string, unknown>;
};

export type ToolCardDraft = {
  folder_id: number;
  name: string;
  description: string;
  card_type: "sql" | "http" | "python";
  sort_order: number;
  enabled: boolean;
  sql_config: ToolCardSqlConfig;
  http_config: ToolCardHttpConfig;
  python_config: ToolCardPythonConfig;
  parameters: ToolCardParameter[];
};
