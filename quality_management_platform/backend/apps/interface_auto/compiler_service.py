from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any

from apps.common.request_execution import json_loads, normalize_global_request_config
from test_platform.db import fetch_all, fetch_one

from .ir_schema import CASE_IR_SCHEMA_VERSION, CompiledCaseIR, empty_case_ir


_SENSITIVE_KEYWORDS = (
    "password",
    "passwd",
    "pwd",
    "token",
    "secret",
    "authorization",
    "access_token",
    "refresh_token",
    "cookie",
    "session",
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _json_value(value: Any, fallback: Any) -> Any:
    return json_loads(value, fallback)


def _generate_request_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S%f")


def _enabled_by_default(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() not in {"false", "0", "no", "n"}
    return bool(value)


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_global_variable_value(value: Any, variable_type: str | None) -> Any:
    variable_kind = str(variable_type or "string").strip().lower()
    if variable_kind in {"int", "integer"}:
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    if variable_kind in {"float", "double", "decimal"}:
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    if variable_kind in {"bool", "boolean"}:
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y"}
        return bool(value)
    if variable_kind in {"json", "object", "array", "list"}:
        return _json_value(value, value)
    return value


def _load_project_variables(project_id: Any, environment_id: Any) -> dict[str, Any]:
    if not project_id or not environment_id:
        return {}
    rows = fetch_all(
        """
        SELECT gv.project_id, gv.name, gv.value, gv.variable_type
        FROM global_variables gv
        INNER JOIN global_variable_environments gve ON gve.variable_id = gv.id
        WHERE gv.project_id = %s AND gve.environment_id = %s
        ORDER BY gv.name ASC
        """,
        (project_id, environment_id),
    )
    result: dict[str, Any] = {}
    for row in rows:
        result[str(row.get("name") or "")] = _parse_global_variable_value(
            row.get("value"),
            row.get("variable_type"),
        )
    return result


def _load_environment(environment_id: Any) -> dict[str, Any]:
    if not environment_id:
        return {
            "id": None,
            "base_url": "",
            "headers": {},
            "variables": {},
        }
    row = fetch_one("SELECT * FROM environments WHERE id = %s", (environment_id,))
    if not row:
        return {
            "id": None,
            "base_url": "",
            "headers": {},
            "variables": {},
        }
    item = dict(row)
    return {
        **item,
        "base_url": item.get("base_url") or "",
        "headers": _json_value(item.get("headers"), {}),
        "variables": _json_value(item.get("variables"), {}),
    }


def _parse_template_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    item = dict(row)
    item["headers"] = _json_value(item.get("headers"), {})
    item["params"] = _json_value(item.get("params"), {})
    item["body"] = _json_value(item.get("body"), {})
    item["retry_enabled"] = bool(item.get("retry_enabled"))
    item["retry_count"] = int(item.get("retry_count") or 0)
    item["timeout"] = int(item.get("timeout") or 30)
    return item


def _load_templates(template_ids: list[int]) -> dict[int, dict[str, Any]]:
    unique_ids = list(dict.fromkeys(template_ids))
    if not unique_ids:
        return {}
    placeholders = ",".join(["%s"] * len(unique_ids))
    rows = fetch_all(
        f"SELECT * FROM api_templates WHERE id IN ({placeholders})",
        tuple(unique_ids),
    )
    return {
        int(row["id"]): parsed
        for row in rows
        if (parsed := _parse_template_row(row))
    }


def _hydrate_case_row(case_row: dict[str, Any] | None) -> dict[str, Any]:
    if not case_row:
        return {}
    hydrated = dict(case_row)
    hydrated["schema_version"] = _int_value(hydrated.get("schema_version"), CASE_IR_SCHEMA_VERSION) or CASE_IR_SCHEMA_VERSION
    hydrated["global_vars"] = _json_value(hydrated.get("global_vars"), {})
    hydrated["global_request_config"] = _json_value(hydrated.get("global_request_config_text"), {})
    hydrated["output_variables"] = _json_value(hydrated.get("output_variables_text"), [])
    hydrated["parameterize_config"] = _json_value(hydrated.get("parameterize_config"), None)
    return hydrated


def _hydrate_step_row(step_row: dict[str, Any]) -> dict[str, Any]:
    hydrated = dict(step_row)
    hydrated["pre_processing"] = _json_value(hydrated.get("pre_processing"), {})
    hydrated["post_processing"] = _json_value(hydrated.get("post_processing"), {})
    hydrated["assertions"] = _json_value(hydrated.get("assertions"), {})
    hydrated["variables"] = _json_value(hydrated.get("variables"), {})
    hydrated["enabled"] = hydrated.get("enabled", True) is not False
    hydrated["enable_encryption"] = bool(hydrated.get("enable_encryption"))
    hydrated["use_global_headers"] = _enabled_by_default(hydrated.get("use_global_headers", True))
    return hydrated


def _normalise_output_variables(value: Any) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw_row in _as_list(_json_value(value, [])):
        row = _as_dict(raw_row)
        name = str(row.get("name") or row.get("output_name") or "").strip()
        source = str(row.get("source") or row.get("variable") or "").strip()
        if name or source:
            rows.append(
                {
                    "name": name or source,
                    "source": source or name,
                }
            )
    return rows


def _tool_entries(tool_map: Any) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if isinstance(tool_map, list):
        iterable = [(str(index), item) for index, item in enumerate(tool_map)]
    else:
        iterable = list(_as_dict(tool_map).items())
    for tool_id, raw_tool in iterable:
        tool = _as_dict(raw_tool)
        if tool and tool.get("enabled", True) is False:
            continue
        entries.append(
            {
                "id": tool.get("id") or tool_id,
                "tool_type": str(tool.get("tool_type") or tool.get("type") or "tool"),
                "name": str(tool.get("name") or tool.get("tool_name") or tool_id),
                "summary": str(tool.get("summary") or ""),
                "priority": int(tool.get("priority") or tool.get("sort_order") or 0),
                "config": _as_dict(tool.get("config")),
                **tool,
            }
        )
    return sorted(entries, key=lambda item: (item.get("priority", 0), str(item.get("id") or "")))


def _extractors_from_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    extractors: list[dict[str, Any]] = []
    for tool in tools:
        tool_type = str(tool.get("tool_type") or tool.get("type") or "").strip().lower()
        if tool_type not in {"parameter_extract", "parameter_extraction"}:
            continue
        raw_rows = _as_list(tool.get("extractors")) or _as_list(tool.get("extractions")) or _as_list(_as_dict(tool.get("config")).get("extractors")) or _as_list(_as_dict(tool.get("config")).get("extractions"))
        for row in raw_rows:
            row_map = _as_dict(row)
            extractors.append(
                {
                    "type": row_map.get("type") or row_map.get("extractor_type") or "jsonpath",
                    "from": row_map.get("from") or row_map.get("source") or "body",
                    "expr": row_map.get("expr") or row_map.get("expression") or row_map.get("path") or "",
                    "var": row_map.get("var") or row_map.get("variable") or row_map.get("name") or "",
                    "tool_id": tool.get("id"),
                    "tool_name": tool.get("name") or tool.get("id"),
                }
            )
    return extractors


def _is_parameter_extraction_tool(tool: dict[str, Any]) -> bool:
    tool_type = str(tool.get("tool_type") or tool.get("type") or "").strip().lower()
    return tool_type in {"parameter_extract", "parameter_extraction"}


def _normalise_parameterize_config(value: Any) -> dict[str, Any]:
    config = _as_dict(_json_value(value, {}))
    source_type = str(config.get("source_type") or "inline_json").strip() or "inline_json"
    return {
        **config,
        "enabled": bool(config.get("enabled")),
        "source_type": source_type,
    }


def _parse_parameter_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    if not config.get("enabled"):
        return []
    source_type = str(config.get("source_type") or "inline_json").strip()
    if source_type == "csv_text":
        csv_text = str(config.get("csv_text") or "")
        if not csv_text.strip():
            return []
        reader = csv.DictReader(io.StringIO(csv_text))
        return [dict(row) for row in reader]
    rows = config.get("rows")
    if isinstance(rows, str):
        rows = _json_value(rows, [])
    return [_as_dict(row) for row in _as_list(rows) if isinstance(row, dict)]


def _mask_value(value: Any) -> Any:
    text = "" if value is None else str(value)
    if len(text) <= 8:
        return "***"
    return f"{text[:3]}***{text[-3:]}"


def mask_sensitive_values(values: dict[str, Any]) -> dict[str, Any]:
    masked: dict[str, Any] = {}
    for key, value in _as_dict(values).items():
        key_text = str(key).lower()
        if any(keyword in key_text for keyword in _SENSITIVE_KEYWORDS):
            masked[str(key)] = _mask_value(value)
        else:
            masked[str(key)] = value
    return masked


def build_parameter_instances(
    parameterize_config: dict[str, Any],
    *,
    run_mode: Any = None,
    parameter_limit: Any = None,
    parameter_start_index: Any = 0,
) -> list[dict[str, Any]]:
    forced_normal = str(run_mode or "").strip().lower() == "normal"
    enabled = bool(parameterize_config.get("enabled")) and not forced_normal
    rows = _parse_parameter_rows(parameterize_config) if enabled else []
    if not rows:
        return [
            {
                "enabled": False,
                "index": None,
                "label": "",
                "values": {},
                "values_masked": {},
            }
        ]

    start_index = max(_int_value(parameter_start_index, 0), 0)
    limit = _int_value(parameter_limit, 0)
    selected_rows = rows[start_index:]
    if limit > 0:
        selected_rows = selected_rows[:limit]

    instances: list[dict[str, Any]] = []
    for offset, row in enumerate(selected_rows):
        absolute_index = start_index + offset
        label = str(
            row.get("parameter_label")
            or row.get("label")
            or row.get("name")
            or f"row-{absolute_index + 1}"
        )
        values = dict(row)
        instances.append(
            {
                "enabled": True,
                "index": absolute_index,
                "label": label,
                "values": values,
                "values_masked": mask_sensitive_values(values),
            }
        )
    return instances


def merge_runtime_variables(
    project_vars: dict[str, Any] | None,
    env_vars: dict[str, Any] | None,
    case_vars: dict[str, Any] | None,
    step_vars: dict[str, Any] | None,
    row_vars: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        **_as_dict(project_vars),
        **_as_dict(env_vars),
        **_as_dict(case_vars),
        **_as_dict(step_vars),
        **_as_dict(row_vars),
    }


def build_runtime_context(case_snapshot: dict[str, Any], environment: dict[str, Any]) -> dict[str, Any]:
    project_variables = _load_project_variables(case_snapshot.get("project_id"), environment.get("id"))
    environment_variables = _as_dict(environment.get("variables"))
    case_variables = _as_dict(case_snapshot.get("global_vars"))
    request_id = str(case_snapshot.get("request_id") or _generate_request_id())
    metadata = {
        "request_id": request_id,
        "case_id": case_snapshot.get("id"),
        "case_name": case_snapshot.get("name") or "",
        "project_id": case_snapshot.get("project_id"),
        "environment_id": environment.get("id"),
        "environment_name": environment.get("name") or "",
    }
    base_variables = merge_runtime_variables(
        project_variables,
        environment_variables,
        case_variables,
        {},
        {},
    )
    base_variables.update(metadata)
    parameterize_config = _normalise_parameterize_config(case_snapshot.get("parameterize_config"))
    return {
        "request_id": request_id,
        "environment": environment,
        "project_variables": project_variables,
        "environment_variables": environment_variables,
        "case_variables": case_variables,
        "metadata": metadata,
        "base_variables": base_variables,
        "variable_precedence": [
            "project_vars",
            "environment_vars",
            "case_global_vars",
            "step_variables",
            "parameter_row",
        ],
        "parameterize_config": parameterize_config,
        "parameter_instances": build_parameter_instances(
            parameterize_config,
            run_mode=case_snapshot.get("run_mode"),
            parameter_limit=case_snapshot.get("parameter_limit"),
            parameter_start_index=case_snapshot.get("parameter_start_index"),
        ),
    }


def compile_step(
    step_row: dict[str, Any],
    case_snapshot: dict[str, Any],
    environment: dict[str, Any],
    template_map: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    step = _hydrate_step_row(step_row)
    template_id = step.get("api_template_id")
    template: dict[str, Any] | None = None
    if template_id:
        if template_map is not None:
            template = template_map.get(int(template_id))
        else:
            template = _load_templates([int(template_id)]).get(int(template_id))

    pre_tools = _tool_entries(step.get("pre_processing"))
    assert_tools = _tool_entries(step.get("assertions"))
    raw_post_tools = _tool_entries(step.get("post_processing"))
    extractors = _as_list(step.get("extractors")) + _extractors_from_tools(raw_post_tools)
    validators = _as_list(step.get("validators"))
    post_tools = [tool for tool in raw_post_tools if not _is_parameter_extraction_tool(tool)]

    request = {}
    if template:
        request = {
            "protocol": "http",
            "url": str(template.get("url_path") or ""),
            "method": str(template.get("method") or "GET").upper(),
            "headers": _as_dict(template.get("headers")),
            "params": template.get("params"),
            "body": template.get("body"),
            "timeout": int(template.get("timeout") or 30),
            "retry_enabled": bool(template.get("retry_enabled")),
            "retry_count": int(template.get("retry_count") or 0),
            "template_id": template.get("id"),
            "template_name": template.get("name") or "",
        }

    step_id = step.get("id") or step.get("step_id") or step.get("step_order") or ""
    return {
        "id": step.get("id"),
        "step_id": f"case-step-{step_id}",
        "step_order": step.get("step_order") or 0,
        "name": step.get("name") or "",
        "enabled": step.get("enabled", True) is not False,
        "api_template_id": template_id,
        "request": request,
        "pre_tools": pre_tools,
        "assert_tools": assert_tools,
        "post_tools": post_tools,
        "extractors": extractors,
        "validators": validators,
        "variables": _as_dict(step.get("variables")),
        "enable_encryption": bool(step.get("enable_encryption")),
        "use_global_headers": _enabled_by_default(step.get("use_global_headers", True)),
        "flags": {
            "enable_encryption": bool(step.get("enable_encryption")),
            "use_global_headers": _enabled_by_default(step.get("use_global_headers", True)),
        },
    }


def compile_case_snapshot_to_ir(case_snapshot: dict[str, Any], environment: dict[str, Any]) -> CompiledCaseIR:
    case_item = {
        **dict(case_snapshot or {}),
        "schema_version": _int_value(case_snapshot.get("schema_version"), CASE_IR_SCHEMA_VERSION) or CASE_IR_SCHEMA_VERSION,
        "global_vars": _json_value(case_snapshot.get("global_vars"), {}),
        "global_request_config": normalize_global_request_config(case_snapshot.get("global_request_config")),
        "output_variables": _normalise_output_variables(case_snapshot.get("output_variables")),
        "parameterize_config": _normalise_parameterize_config(case_snapshot.get("parameterize_config")),
    }
    steps = [_hydrate_step_row(step) for step in _as_list(case_snapshot.get("steps"))]
    template_ids = [
        int(step.get("api_template_id"))
        for step in steps
        if step.get("api_template_id")
    ]
    template_map = _load_templates(template_ids)
    runtime_context = build_runtime_context(case_item, environment)

    ir = empty_case_ir()
    ir.update(
        {
            "schema_version": CASE_IR_SCHEMA_VERSION,
            "case": {
                "id": case_item.get("id"),
                "project_id": case_item.get("project_id"),
                "folder_id": case_item.get("folder_id"),
                "name": case_item.get("name") or "",
                "description": case_item.get("description") or "",
                "environment_id": case_item.get("environment_id"),
                "schema_version": case_item.get("schema_version") or CASE_IR_SCHEMA_VERSION,
                "parameterize_config": case_item.get("parameterize_config"),
                "enable_encryption": bool(case_item.get("enable_encryption")),
                "encrypt_url": str(case_item.get("encrypt_url") or ""),
                "decrypt_url": str(case_item.get("decrypt_url") or ""),
                "sort_order": case_item.get("sort_order") or 0,
            },
            "runtime": runtime_context,
            "global_request_config": case_item.get("global_request_config"),
            "variables": dict(runtime_context.get("base_variables") or {}),
            "steps": [
                compile_step(step, case_item, environment, template_map=template_map)
                for step in steps
            ],
            "outputs": case_item.get("output_variables"),
        }
    )
    return ir


def compile_case_to_ir(case_id: int, environment_id: int | None = None) -> CompiledCaseIR:
    case_row = _hydrate_case_row(fetch_one("SELECT * FROM test_cases WHERE id = %s", (case_id,)))
    if not case_row:
        raise ValueError("test case not found")
    if environment_id is not None:
        case_row["environment_id"] = environment_id
    rows = fetch_all(
        """
        SELECT *
        FROM test_case_steps
        WHERE case_id = %s
        ORDER BY step_order, id
        """,
        (case_id,),
    )
    case_row["steps"] = [_hydrate_step_row(row) for row in rows]
    environment = _load_environment(case_row.get("environment_id"))
    return compile_case_snapshot_to_ir(case_row, environment)
