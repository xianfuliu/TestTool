import type { ApiToolConfig, ApiToolLayoutItem } from "./types";

function formatDate(value: Date) {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}${month}${day}`;
}

export function buildRequestId() {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = `${now.getMonth() + 1}`.padStart(2, "0");
  const dd = `${now.getDate()}`.padStart(2, "0");
  const hh = `${now.getHours()}`.padStart(2, "0");
  const mi = `${now.getMinutes()}`.padStart(2, "0");
  const ss = `${now.getSeconds()}`.padStart(2, "0");
  return `${yyyy}${mm}${dd}${hh}${mi}${ss}`;
}

function replacePlaceholders(template: string, values: Record<string, string>, requestId: string) {
  return template.replace(/\$\{(\w+)\}|\{(\w+)\}/g, (_, dollarKey: string, legacyKey: string) => {
    const key = dollarKey || legacyKey;
    if (key === "request_id") {
      return requestId;
    }
    if (key === "date") {
      return formatDate(new Date());
    }
    return values[key] ?? "";
  });
}

function parseDate(value: string) {
  const compact = value.replace(/[-/]/g, "");
  if (!/^\d{8}$/.test(compact)) {
    throw new Error("invalid date");
  }
  const year = Number(compact.slice(0, 4));
  const month = Number(compact.slice(4, 6)) - 1;
  const day = Number(compact.slice(6, 8));
  return new Date(year, month, day);
}

function evaluateNumericFormula(expression: string) {
  const cleaned = expression.replace(/\s+/g, "");
  if (!/^[0-9+\-*/().%]+$/.test(cleaned)) {
    return "";
  }
  const result = Function(`"use strict"; return (${cleaned.replace(/%/g, "/100")});`)() as number;
  if (!Number.isFinite(result)) {
    return "";
  }
  const rounded = Math.round(result * 100) / 100;
  return Number.isInteger(rounded) ? `${rounded}` : `${rounded}`;
}

function evaluateDateFormula(expression: string) {
  const matches = expression.match(/(\d{4}[-/]?\d{2}[-/]?\d{2})/g);
  if (!matches || matches.length !== 2 || !expression.includes("-")) {
    return "";
  }
  const left = parseDate(matches[0]);
  const right = parseDate(matches[1]);
  const diff = left.getTime() - right.getTime();
  return `${Math.floor(diff / (1000 * 60 * 60 * 24))}`;
}

export function deriveRuntimeValues(
  config: ApiToolConfig,
  seedValues: Record<string, string>,
  requestId: string,
) {
  const values: Record<string, string> = { ...seedValues, request_id: requestId };
  const providedKeys = new Set(Object.keys(seedValues));
  const layout = [...config.layout].sort((left, right) => left.priority - right.priority);

  for (let round = 0; round < 6; round += 1) {
    let changed = false;

    layout.forEach((item) => {
      if ((item.type === "field" || item.type === "combo") && item.key && !providedKeys.has(item.key)) {
        let nextValue = "";
        if (item.default) {
          nextValue = replacePlaceholders(item.default, values, requestId);
        } else if (item.type === "combo" && item.options?.length) {
          nextValue = item.options[0].value;
        }
        if (values[item.key] !== nextValue) {
          values[item.key] = nextValue;
          changed = true;
        }
      }

      if (item.type === "condition" && item.key) {
        const conditionFieldValue = values[item.condition_field ?? ""] ?? "";
        const mappedKey = item.mappings?.[conditionFieldValue] ?? "";
        const nextValue = mappedKey ? values[mappedKey] ?? "" : "";
        if (values[item.key] !== nextValue) {
          values[item.key] = nextValue;
          changed = true;
        }
      }

      if (item.type === "formula" && item.key) {
        const formula = item.formula ?? "";
        const dependencies = [...formula.matchAll(/\$\{(\w+)\}|\{(\w+)\}/g)].map(
          (match) => match[1] || match[2],
        );
        const hasMissingDependency = dependencies.some((dependency) => !values[dependency]);
        let nextValue = "";
        if (!hasMissingDependency) {
          const expression = replacePlaceholders(formula, values, requestId);
          nextValue =
            item.formula_type === "date"
              ? evaluateDateFormula(expression)
              : evaluateNumericFormula(expression);
        }
        if (values[item.key] !== nextValue) {
          values[item.key] = nextValue;
          changed = true;
        }
      }
    });

    if (!changed) {
      break;
    }
  }

  return values;
}

export function isEditableLayoutItem(item: ApiToolLayoutItem) {
  return item.type === "field" || item.type === "combo";
}

export function isVisibleLayoutItem(item: ApiToolLayoutItem) {
  if (item.type === "interface" || item.type === "sql") {
    return true;
  }
  return item.show_in_ui !== false;
}

export function prettyJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}
