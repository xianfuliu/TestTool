import type {
  ApiToolConfig,
  ApiToolGlobalRequestConfig,
  ApiToolInterfaceConfig,
  ApiToolLayoutItem,
  ApiToolScheduleTask,
  ApiToolSqlConfig,
  LayoutOption,
} from "./types";

let draftSeed = 0;

function nextId(prefix: string) {
  draftSeed += 1;
  return `${prefix}_${draftSeed}`;
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function parseJsonText(text: string, label: string) {
  const trimmed = text.trim();
  if (!trimmed) {
    return {};
  }
  try {
    return JSON.parse(trimmed) as unknown;
  } catch (error) {
    throw new Error(`${label} 不是合法的 JSON`);
  }
}

function stringifyJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

export type DraftKeyValueRow = {
  localId: string;
  key: string;
  value: string;
};

export type DraftConditionalCaseRow = {
  localId: string;
  caseValue: string;
  bodyTemplateText: string;
};

export type DraftExtractionRow = {
  localId: string;
  variable: string;
  path: string;
};

export type DraftOutputFieldRow = {
  localId: string;
  field: string;
  description: string;
};

export type LayoutDraftItem = ApiToolLayoutItem & {
  localId: string;
};

export type InterfaceDraft = {
  localId: string;
  name: string;
  url: string;
  method: string;
  headersRows: DraftKeyValueRow[];
  requestType: "normal" | "conditional";
  bodyTemplateText: string;
  conditionalField: string;
  conditionalCases: DraftConditionalCaseRow[];
  responseMappingRows: DraftKeyValueRow[];
  fieldTypeRows: DraftKeyValueRow[];
  enableEncryption: boolean;
};

export type SqlDraft = {
  localId: string;
  name: string;
  database: {
    host: string;
    port: number;
    user: string;
    password: string;
    database: string;
    charset: string;
  };
  sql: string;
  outputFields: DraftOutputFieldRow[];
};

function buildLayoutNameOrder(
  layoutItems: LayoutDraftItem[],
  type: "interface" | "sql",
) {
  const orderMap = new Map<string, number>();
  layoutItems.forEach((item, index) => {
    if (item.type !== type) {
      return;
    }
    const name = item.name?.trim();
    if (name && !orderMap.has(name)) {
      orderMap.set(name, index);
    }
  });
  return orderMap;
}

function sortNamedDraftsByLayout<T extends { name: string }>(
  drafts: T[],
  layoutItems: LayoutDraftItem[],
  type: "interface" | "sql",
) {
  const orderMap = buildLayoutNameOrder(layoutItems, type);
  return [...drafts].sort((left, right) => {
    const leftRank = orderMap.get(left.name.trim());
    const rightRank = orderMap.get(right.name.trim());
    if (leftRank === undefined && rightRank === undefined) {
      return 0;
    }
    if (leftRank === undefined) {
      return 1;
    }
    if (rightRank === undefined) {
      return -1;
    }
    return leftRank - rightRank;
  });
}

export function createKeyValueRow(key = "", value = ""): DraftKeyValueRow {
  return {
    localId: nextId("kv"),
    key,
    value,
  };
}

export function createConditionalCaseRow(
  caseValue = "",
  bodyTemplateText = "{\n  \n}",
): DraftConditionalCaseRow {
  return {
    localId: nextId("case"),
    caseValue,
    bodyTemplateText,
  };
}

export function createExtractionRow(variable = "", path = ""): DraftExtractionRow {
  return {
    localId: nextId("extract"),
    variable,
    path,
  };
}

export function createOutputFieldRow(field = "", description = ""): DraftOutputFieldRow {
  return {
    localId: nextId("output"),
    field,
    description,
  };
}

export function createLayoutDraft(type: ApiToolLayoutItem["type"] = "field"): LayoutDraftItem {
  return {
    localId: nextId("layout"),
    type,
    key: "",
    label: "",
    name: "",
    default: "",
    data_type: "",
    options: [],
    show_in_ui: true,
    priority: 1,
    condition_field: "",
    mappings: {},
    formula: "",
    formula_type: "numeric",
  };
}

export function createInterfaceDraft(): InterfaceDraft {
  return {
    localId: nextId("interface"),
    name: "",
    url: "",
    method: "POST",
    headersRows: [createKeyValueRow("Content-Type", "application/json")],
    requestType: "normal",
    bodyTemplateText: "{\n  \"requestId\": \"${request_id}\"\n}",
    conditionalField: "",
    conditionalCases: [createConditionalCaseRow()],
    responseMappingRows: [],
    fieldTypeRows: [],
    enableEncryption: false,
  };
}

export function createSqlDraft(): SqlDraft {
  return {
    localId: nextId("sql"),
    name: "",
    database: {
      host: "",
      port: 3306,
      user: "",
      password: "",
      database: "",
      charset: "utf8mb4",
    },
    sql: "",
    outputFields: [],
  };
}

function recordToRows(record: Record<string, unknown>) {
  const entries = Object.entries(record);
  if (!entries.length) {
    return [createKeyValueRow()];
  }
  return entries.map(([key, value]) => createKeyValueRow(key, String(value ?? "")));
}

function rowsToRecord(rows: DraftKeyValueRow[]) {
  const result: Record<string, string> = {};
  rows.forEach((row) => {
    const key = row.key.trim();
    if (!key) {
      return;
    }
    result[key] = row.value;
  });
  return result;
}

function layoutToDraft(item: ApiToolLayoutItem): LayoutDraftItem {
  return {
    ...cloneJson(item),
    localId: nextId("layout"),
    priority: Number(item.priority || 0),
    options: cloneJson(item.options ?? []),
    mappings: cloneJson(item.mappings ?? {}),
  };
}

function interfaceToDraft(name: string, config: ApiToolInterfaceConfig): InterfaceDraft {
  const conditionalBody = config.conditional_body;
  return {
    localId: nextId("interface"),
    name,
    url: config.url ?? "",
    method: config.method ?? "POST",
    headersRows: recordToRows(config.headers ?? {}),
    requestType: conditionalBody ? "conditional" : "normal",
    bodyTemplateText: stringifyJson(config.body_template ?? {}),
    conditionalField: conditionalBody?.field ?? "",
    conditionalCases: conditionalBody
      ? Object.entries(conditionalBody.cases ?? {}).map(([caseValue, body]) =>
          createConditionalCaseRow(caseValue, stringifyJson(body)),
        )
      : [createConditionalCaseRow()],
    responseMappingRows: recordToRows(config.response_mapping ?? {}),
    fieldTypeRows: recordToRows(config.field_types ?? {}),
    enableEncryption: config.enable_encryption !== false,
  };
}

function sqlToDraft(name: string, config: ApiToolSqlConfig): SqlDraft {
  return {
    localId: nextId("sql"),
    name,
    database: {
      host: config.database.host ?? "",
      port: Number(config.database.port ?? 3306),
      user: config.database.user ?? "",
      password: config.database.password ?? "",
      database: config.database.database ?? "",
      charset: config.database.charset ?? "utf8mb4",
    },
    sql: config.sql ?? "",
    outputFields: (config.output_fields ?? []).map((item) =>
      createOutputFieldRow(item.field, item.description),
    ),
  };
}

export function configToDrafts(config: ApiToolConfig) {
  const layoutItems = (config.layout ?? []).map(layoutToDraft);
  return {
    scheduleTasks: cloneJson(config.schedule_tasks ?? []) as ApiToolScheduleTask[],
    layoutItems: layoutItems.map((item, index) => ({
      ...item,
      priority: index + 1,
    })),
    interfaces: Object.entries(config.interfaces ?? {}).map(([name, value]) =>
      interfaceToDraft(name, value),
    ),
    sqls: Object.entries(config.sqls ?? {}).map(([name, value]) => sqlToDraft(name, value)),
  };
}

function sanitiseOptions(options: LayoutOption[] | undefined) {
  return (options ?? [])
    .map((option) => ({
      text: option.text.trim(),
      value: option.value.trim(),
    }))
    .filter((option) => option.text || option.value);
}

function sanitiseMappings(mappings: Record<string, string> | undefined) {
  const result: Record<string, string> = {};
  Object.entries(mappings ?? {}).forEach(([key, value]) => {
    const mappingKey = key.trim();
    const mappingValue = value.trim();
    if (mappingKey && mappingValue) {
      result[mappingKey] = mappingValue;
    }
  });
  return result;
}

function layoutDraftToConfig(item: LayoutDraftItem): ApiToolLayoutItem {
  const base: ApiToolLayoutItem = {
    type: item.type,
    priority: Number(item.priority || 0),
  };

  if (item.type === "field" || item.type === "combo" || item.type === "condition" || item.type === "formula") {
    base.key = item.key?.trim() ?? "";
    base.label = item.label?.trim() ?? "";
    base.show_in_ui = item.show_in_ui !== false;
  }

  if (item.type === "field" || item.type === "combo") {
    base.default = item.default ?? "";
    if (item.data_type?.trim()) {
      base.data_type = item.data_type.trim();
    }
  }

  if (item.type === "combo") {
    base.options = sanitiseOptions(item.options);
  }

  if (item.type === "interface" || item.type === "sql") {
    base.name = item.name?.trim() ?? "";
  }

  if (item.type === "condition") {
    base.condition_field = item.condition_field?.trim() ?? "";
    base.mappings = sanitiseMappings(item.mappings);
  }

  if (item.type === "formula") {
    base.formula = item.formula ?? "";
    base.formula_type = item.formula_type?.trim() || "numeric";
  }

  return base;
}

function interfaceDraftToConfig(draft: InterfaceDraft): ApiToolInterfaceConfig {
  const base: ApiToolInterfaceConfig = {
    url: draft.url.trim(),
    method: draft.method.trim().toUpperCase() || "POST",
    headers: rowsToRecord(draft.headersRows),
    response_mapping: rowsToRecord(draft.responseMappingRows),
    field_types: rowsToRecord(draft.fieldTypeRows),
    enable_encryption: draft.enableEncryption,
  };

  if (draft.requestType === "conditional") {
    const cases: Record<string, unknown> = {};
    draft.conditionalCases.forEach((row) => {
      const caseValue = row.caseValue.trim();
      if (!caseValue) {
        return;
      }
      cases[caseValue] = parseJsonText(row.bodyTemplateText, `接口 ${draft.name} 条件请求体`);
    });
    base.conditional_body = {
      field: draft.conditionalField.trim(),
      cases,
    };
    return base;
  }

  base.body_template = parseJsonText(draft.bodyTemplateText, `接口 ${draft.name} 请求体`);
  return base;
}

function sqlDraftToConfig(draft: SqlDraft): ApiToolSqlConfig {
  return {
    database: {
      host: draft.database.host.trim(),
      port: Number(draft.database.port || 3306),
      user: draft.database.user.trim(),
      password: draft.database.password,
      database: draft.database.database.trim(),
      charset: draft.database.charset.trim() || "utf8mb4",
    },
    sql: draft.sql,
    output_fields: draft.outputFields
      .map((item) => ({
        field: item.field.trim(),
        description: item.description.trim(),
      }))
      .filter((item) => item.field),
  };
}

export function buildConfigFromDrafts(args: {
  enableEncryption: boolean;
  encryptUrl: string;
  decryptUrl: string;
  globalRequestConfig: ApiToolGlobalRequestConfig;
  scheduleTasks: ApiToolScheduleTask[];
  layoutItems: LayoutDraftItem[];
  interfaces: InterfaceDraft[];
  sqls: SqlDraft[];
}) {
  const normalisedLayoutItems = args.layoutItems.map((item, index) => ({
    ...item,
    priority: index + 1,
  }));
  const sortedInterfaces = sortNamedDraftsByLayout(
    args.interfaces,
    normalisedLayoutItems,
    "interface",
  );
  const sortedSqls = sortNamedDraftsByLayout(args.sqls, normalisedLayoutItems, "sql");

  const interfaces: Record<string, ApiToolInterfaceConfig> = {};
  sortedInterfaces.forEach((draft) => {
    const name = draft.name.trim();
    if (!name) {
      return;
    }
    interfaces[name] = interfaceDraftToConfig(draft);
  });

  const sqls: Record<string, ApiToolSqlConfig> = {};
  sortedSqls.forEach((draft) => {
    const name = draft.name.trim();
    if (!name) {
      return;
    }
    sqls[name] = sqlDraftToConfig(draft);
  });

  return {
    enable_encryption: args.enableEncryption,
    encrypt_url: args.encryptUrl.trim(),
    decrypt_url: args.decryptUrl.trim(),
    global_request_config: args.globalRequestConfig,
    global_headers:
      args.globalRequestConfig.header_config.enabled
        ? args.globalRequestConfig.header_config.headers
        : {},
    schedule_tasks: args.scheduleTasks.map((task) => ({
      id: String(task.id ?? "").trim(),
      jobGroup: String(task.jobGroup ?? "").trim(),
      name: String(task.name ?? "").trim(),
      row_id: Number(task.row_id ?? 0),
    })),
    layout: normalisedLayoutItems.map(layoutDraftToConfig),
    interfaces,
    sqls,
  } satisfies ApiToolConfig;
}
