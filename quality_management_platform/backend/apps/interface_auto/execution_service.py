from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import pymysql

from apps.common.request_execution import (
    EncryptionConfig,
    RequestDefinition,
    RequestExecutionContext,
    build_response_extraction_source,
    execute_request_definition,
    extract_response_value,
    json_loads,
    merge_header_maps,
    normalize_global_request_config,
    render_sql_template,
    replace_template_text,
    resolve_global_request_runtime,
)
from test_platform.db import DATABASE_CONFIG, execute, fetch_all, fetch_one


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _json_text(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _generate_request_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S%f")


def _parse_json_value(value: Any, fallback: Any) -> Any:
    return json_loads(value, fallback)


def _parse_template_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    item = dict(row)
    item["headers"] = _parse_json_value(item.get("headers"), {})
    item["params"] = _parse_json_value(item.get("params"), {})
    item["body"] = _parse_json_value(item.get("body"), {})
    item["retry_enabled"] = bool(item.get("retry_enabled"))
    item["retry_count"] = int(item.get("retry_count") or 0)
    item["timeout"] = int(item.get("timeout") or 30)
    return item


def _load_templates(template_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not template_ids:
        return {}
    placeholders = ",".join(["%s"] * len(template_ids))
    rows = fetch_all(
        f"SELECT * FROM api_templates WHERE id IN ({placeholders})",
        tuple(template_ids),
    )
    return {
        int(row["id"]): parsed
        for row in rows
        if (parsed := _parse_template_row(row))
    }


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
    return {
        **dict(row),
        "base_url": row.get("base_url") or "",
        "headers": _parse_json_value(row.get("headers"), {}),
        "variables": _parse_json_value(row.get("variables"), {}),
    }


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
        return _parse_json_value(value, value)
    return value


def _load_project_variables(project_id: Any) -> dict[str, Any]:
    if not project_id:
        return {}
    rows = fetch_all(
        """
        SELECT project_id, name, value, variable_type
        FROM global_variables
        WHERE project_id IN (0, %s)
        ORDER BY project_id ASC, name ASC
        """,
        (project_id,),
    )
    result: dict[str, Any] = {}
    for row in rows:
        result[str(row.get("name") or "")] = _parse_global_variable_value(
            row.get("value"),
            row.get("variable_type"),
        )
    return result


def _normalise_step(step: dict[str, Any]) -> dict[str, Any]:
    return {
        **dict(step),
        "pre_processing": _parse_json_value(step.get("pre_processing"), {}),
        "post_processing": _parse_json_value(step.get("post_processing"), {}),
        "assertions": _parse_json_value(step.get("assertions"), {}),
        "variables": _parse_json_value(step.get("variables"), {}),
        "enabled": step.get("enabled", True) is not False,
        "enable_encryption": bool(step.get("enable_encryption")),
    }


def _build_runtime_variables(case_snapshot: dict[str, Any], environment: dict[str, Any]) -> dict[str, Any]:
    project_variables = _load_project_variables(case_snapshot.get("project_id"))
    environment_variables = _as_dict(environment.get("variables"))
    case_variables = _as_dict(case_snapshot.get("global_vars"))
    request_id = str(case_snapshot.get("request_id") or _generate_request_id())
    return {
        **project_variables,
        **environment_variables,
        **case_variables,
        "request_id": request_id,
        "case_id": case_snapshot.get("id"),
        "case_name": case_snapshot.get("name") or "",
        "project_id": case_snapshot.get("project_id"),
    }


def _normalise_output_variables(value: Any) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw_row in _as_list(_parse_json_value(value, [])):
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


def _tool_entries(tool_map: dict[str, Any] | None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for tool_id, raw_tool in _as_dict(tool_map).items():
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


def _resolve_case_outputs(case_snapshot: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for row in _normalise_output_variables(case_snapshot.get("output_variables")):
        output_name = str(row.get("name") or "").strip()
        source_name = str(row.get("source") or "").strip()
        if not output_name or not source_name:
            continue
        if source_name in variables:
            outputs[output_name] = variables.get(source_name)
    return outputs


def _coerce_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return Decimal("1") if value else Decimal("0")
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value.strip())
        except (InvalidOperation, ValueError):
            return None
    return None


def _resolve_assertion_subject(field: str, source_data: Any, variables: dict[str, Any]) -> Any:
    resolved_field = replace_template_text(field, variables, allow_legacy_placeholders=True).strip()
    if not resolved_field:
        return None
    if resolved_field in variables:
        return variables.get(resolved_field)
    if resolved_field.startswith(
        (
            "$",
            "headers.",
            "response_headers.",
            "body.",
            "response_body.",
            "decrypted_body.",
            "response_decrypted_body.",
            "raw_body",
            "status_code",
        )
    ):
        return extract_response_value(source_data, resolved_field)
    if isinstance(source_data, dict) and resolved_field in source_data:
        return source_data.get(resolved_field)
    return variables.get(resolved_field)


def _assert_value(actual: Any, operator: str, expected: Any) -> bool:
    actual_decimal = _coerce_decimal(actual)
    expected_decimal = _coerce_decimal(expected)
    if operator == "equal":
        return actual == expected
    if operator == "not_equal":
        return actual != expected
    if operator == "contains":
        return str(expected) in str(actual)
    if operator == "not_contains":
        return str(expected) not in str(actual)
    if operator == "greater" and actual_decimal is not None and expected_decimal is not None:
        return actual_decimal > expected_decimal
    if operator == "less" and actual_decimal is not None and expected_decimal is not None:
        return actual_decimal < expected_decimal
    if operator == "greater_equal" and actual_decimal is not None and expected_decimal is not None:
        return actual_decimal >= expected_decimal
    if operator == "less_equal" and actual_decimal is not None and expected_decimal is not None:
        return actual_decimal <= expected_decimal
    return False


def _extract_response_source(result: dict[str, Any]) -> Any:
    return build_response_extraction_source(result)


def _apply_extractions(
    extractions: list[dict[str, Any]],
    source_data: Any,
    variables: dict[str, Any],
) -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    for row in extractions:
        variable_name = str(row.get("variable") or "").strip()
        response_path = replace_template_text(
            str(row.get("path") or "").strip(),
            variables,
            allow_legacy_placeholders=True,
        )
        if not variable_name or not response_path:
            continue
        value = extract_response_value(source_data, response_path)
        if value is not None:
            extracted[variable_name] = value
    variables.update(extracted)
    return extracted


def _execute_sql_tool(config: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    sql_text = str(config.get("sql") or "").strip()
    if not sql_text:
        raise ValueError("SQL 工具未配置查询语句")
    resolved_sql = render_sql_template(sql_text, variables, allow_legacy_placeholders=True)
    if not re.match(r"^\s*SELECT\b", resolved_sql, re.IGNORECASE):
        raise ValueError("SQL 工具仅支持 SELECT 查询")

    connection_config = {
        "host": config.get("host") or DATABASE_CONFIG["host"],
        "port": int(config.get("port") or DATABASE_CONFIG["port"]),
        "user": config.get("user") or config.get("username") or DATABASE_CONFIG["user"],
        "password": config.get("password") or DATABASE_CONFIG["password"],
        "database": config.get("database") or config.get("database_name") or DATABASE_CONFIG["database"],
        "charset": config.get("charset") or "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }

    with pymysql.connect(**connection_config) as connection:
        with connection.cursor() as cursor:
            cursor.execute(resolved_sql)
            rows = cursor.fetchall()

    serialised_rows: list[dict[str, Any]] = []
    for row in rows:
        serialised_row: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, datetime):
                serialised_row[key] = value.isoformat()
            else:
                serialised_row[key] = value
        serialised_rows.append(serialised_row)

    return {
        "request": {
            "sql": resolved_sql,
            "database": {
                "host": connection_config["host"],
                "port": connection_config["port"],
                "database": connection_config["database"],
                "user": connection_config["user"],
            },
        },
        "status": "success",
        "rows": serialised_rows,
        "body": serialised_rows,
        "raw_body": _json_text(serialised_rows),
        "decrypted_body": serialised_rows,
    }


def _execute_http_tool(
    config: dict[str, Any],
    variables: dict[str, Any],
    environment: dict[str, Any],
    encryption: EncryptionConfig,
    global_headers: dict[str, Any] | None,
) -> dict[str, Any]:
    result = execute_request_definition(
        RequestDefinition(
            protocol=str(config.get("protocol") or "http"),
            url=str(config.get("url") or ""),
            method=str(config.get("method") or "GET").upper(),
            headers=_as_dict(config.get("headers")),
            body=config.get("body"),
            timeout=int(config.get("timeout") or 30),
        ),
        RequestExecutionContext(
            request_id=str(variables.get("request_id") or _generate_request_id()),
            variables=variables,
            base_url=str(environment.get("base_url") or ""),
            global_headers=merge_header_maps(
                _as_dict(environment.get("headers")),
                _as_dict(global_headers),
            ),
            encryption=encryption,
            allow_legacy_placeholders=True,
        ),
    )
    if result.status_code >= 400:
        raise ValueError(f"HTTP 工具执行失败，状态码 {result.status_code}")
    return {
        "request": result.request,
        "status": "success",
        "status_code": result.status_code,
        "headers": result.headers,
        "body": result.body,
        "raw_body": result.raw_body,
        "decrypted_body": result.decrypted_body,
        "duration_ms": result.duration_ms,
    }


def _execute_parameter_extraction_tool(
    tool: dict[str, Any],
    source_data: Any,
    variables: dict[str, Any],
) -> dict[str, Any]:
    extractions = _as_list(tool.get("extractions")) or _as_list(_as_dict(tool.get("config")).get("extractions"))
    extracted = _apply_extractions(extractions, source_data, variables)
    return {
        "request": {"extractions": extractions},
        "status": "success",
        "body": extracted,
        "raw_body": _json_text(extracted),
        "decrypted_body": extracted,
        "extracted": extracted,
    }


def _execute_assertion_tool(
    tool: dict[str, Any],
    source_data: Any,
    variables: dict[str, Any],
) -> dict[str, Any]:
    assertions = _as_list(tool.get("assertions")) or _as_list(_as_dict(tool.get("config")).get("assertions"))
    results: list[dict[str, Any]] = []
    for row in assertions:
        assertion = _as_dict(row)
        field = str(assertion.get("field") or "").strip()
        operator = str(assertion.get("operator") or "equal").strip()
        expected = replace_template_text(
            str(assertion.get("expected") or ""),
            variables,
            allow_legacy_placeholders=True,
        )
        actual = _resolve_assertion_subject(field, source_data, variables)
        passed = _assert_value(actual, operator, expected)
        results.append(
            {
                "field": field,
                "operator": operator,
                "expected": expected,
                "actual": actual,
                "passed": passed,
            }
        )
    failed = [item for item in results if not item["passed"]]
    if failed:
        detail = failed[0]
        raise ValueError(
            f"断言失败: {detail['field']} {detail['operator']} 期望 {detail['expected']}，实际 {detail['actual']}"
        )
    return {
        "request": {"assertions": assertions},
        "status": "success",
        "body": {"passed": True, "results": results},
        "raw_body": _json_text(results),
        "decrypted_body": results,
    }


def _execute_tool(
    tool: dict[str, Any],
    source_data: Any,
    variables: dict[str, Any],
    environment: dict[str, Any],
    encryption: EncryptionConfig,
    global_headers: dict[str, Any] | None,
) -> tuple[dict[str, Any], Any, list[str]]:
    tool_type = str(tool.get("tool_type") or "tool").strip().lower()
    tool_name = str(tool.get("name") or tool.get("id") or tool_type)
    logs = [f"工具开始执行: {tool_name}"]

    if tool_type == "http_request":
        result = _execute_http_tool(
            _as_dict(tool.get("config")),
            variables,
            environment,
            encryption,
            global_headers,
        )
        extracted = _apply_extractions(
            _as_list(tool.get("extractions")) or _as_list(_as_dict(tool.get("config")).get("extractions")),
            _extract_response_source(result),
            variables,
        )
        if extracted:
            logs.append(f"已提取变量: {', '.join(extracted.keys())}")
        return result, _extract_response_source(result), logs

    if tool_type == "sql_tool":
        result = _execute_sql_tool(_as_dict(tool.get("config")), variables)
        output_rows = _as_list(result.get("rows"))
        if output_rows:
            variables.update(output_rows[0])
            logs.append(f"SQL 输出变量已写入上下文: {', '.join(output_rows[0].keys())}")
        return result, build_response_extraction_source(result), logs

    if tool_type in {"parameter_extract", "parameter_extraction"}:
        result = _execute_parameter_extraction_tool(tool, source_data, variables)
        extracted = _as_dict(result.get("extracted"))
        if extracted:
            logs.append(f"参数提取完成: {', '.join(extracted.keys())}")
        return result, source_data, logs

    if "assert" in tool_type:
        result = _execute_assertion_tool(tool, source_data, variables)
        logs.append("断言通过")
        return result, source_data, logs

    raise ValueError(f"暂不支持 {tool_type} 工具执行")


def _insert_step_result(
    report_id: int,
    case_id: int | None,
    step: dict[str, Any],
    status: str,
    request_data: Any,
    response_data: Any,
    execution_logs: list[str],
    error_message: str,
    start_time: datetime,
    end_time: datetime,
) -> None:
    execute(
        """
        INSERT INTO test_step_results (
            report_id,
            case_id,
            step_id,
            step_order,
            step_name,
            status,
            request_data,
            response_data,
            execution_logs,
            error_message,
            start_time,
            end_time,
            execution_time
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            report_id,
            case_id,
            step.get("id"),
            step.get("step_order") or 0,
            step.get("name") or "",
            status,
            _json_text(request_data),
            _json_text(response_data),
            "\n".join(execution_logs),
            error_message,
            start_time,
            end_time,
            round((end_time - start_time).total_seconds(), 3),
        ),
    )


def execute_case_run(case_snapshot: dict[str, Any]) -> dict[str, Any]:
    case_item = {
        **dict(case_snapshot or {}),
        "global_vars": _parse_json_value(case_snapshot.get("global_vars"), {}),
        "global_request_config": normalize_global_request_config(
            case_snapshot.get("global_request_config"),
        ),
        "output_variables": _normalise_output_variables(
            case_snapshot.get("output_variables"),
        ),
    }
    steps = [_normalise_step(step) for step in _as_list(case_snapshot.get("steps"))]
    environment = _load_environment(case_item.get("environment_id"))
    runtime_variables = _build_runtime_variables(case_item, environment)
    case_request_id = str(runtime_variables.get("request_id") or _generate_request_id())
    runtime_variables["request_id"] = case_request_id

    template_ids = [
        int(step.get("api_template_id"))
        for step in steps
        if step.get("api_template_id")
    ]
    templates = _load_templates(template_ids)

    report_start = datetime.now()
    report_name = f"{case_item.get('name') or '未命名用例'}_{report_start.strftime('%Y%m%d%H%M%S')}"
    report_id = execute(
        """
        INSERT INTO test_reports (
            case_id,
            project_id,
            report_name,
            status,
            total_cases,
            passed_cases,
            failed_cases,
            error_cases,
            start_time,
            trigger_type,
            summary_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            case_item.get("id"),
            case_item.get("project_id"),
            report_name,
            "running",
            1,
            0,
            0,
            0,
            report_start,
            "manual",
            _json_text({"request_id": case_request_id, "steps": []}),
        ),
    )

    base_encryption = EncryptionConfig(
        enabled=bool(case_item.get("enable_encryption")),
        encrypt_url=str(case_item.get("encrypt_url") or ""),
        decrypt_url=str(case_item.get("decrypt_url") or ""),
    )
    environment_headers = _as_dict(environment.get("headers"))
    combined_global_headers = dict(environment_headers)
    global_setup_logs: list[str] = []
    global_login_result: dict[str, Any] | None = None

    try:
        global_runtime = resolve_global_request_runtime(
            case_item.get("global_request_config"),
            request_id=case_request_id,
            variables=runtime_variables,
            base_url=str(environment.get("base_url") or ""),
            base_headers=environment_headers,
            encryption=base_encryption,
            allow_legacy_placeholders=True,
        )
        runtime_variables = global_runtime["variables"]
        combined_global_headers = merge_header_maps(
            environment_headers,
            _as_dict(global_runtime.get("headers")),
        )
        global_setup_logs = _as_list(global_runtime.get("logs"))
        global_login_result = _as_dict(global_runtime.get("login_result"))
    except Exception as exc:
        report_end = datetime.now()
        case_outputs = _resolve_case_outputs(case_item, runtime_variables)
        execute(
            """
            UPDATE test_reports
            SET status = %s,
                passed_cases = %s,
                failed_cases = %s,
                error_cases = %s,
                end_time = %s,
                duration = %s,
                summary_json = %s
            WHERE id = %s
            """,
            (
                "failed",
                0,
                1,
                0,
                report_end,
                round((report_end - report_start).total_seconds(), 3),
                _json_text(
                    {
                        "request_id": case_request_id,
                        "passed_steps": 0,
                        "failed_steps": 0,
                        "skipped_steps": 0,
                        "steps": [],
                        "global_setup": {
                            "logs": global_setup_logs,
                            "error": str(exc),
                        },
                        "case_outputs": case_outputs,
                    }
                ),
                report_id,
            ),
        )
        return {
            "report_id": report_id,
            "request_id": case_request_id,
            "case_id": case_item.get("id"),
            "case_name": case_item.get("name") or "未命名用例",
            "status": "failed",
            "message": f"全局配置执行失败: {exc}",
            "summary": {
                "passed_steps": 0,
                "failed_steps": 0,
                "skipped_steps": 0,
            },
            "steps": [],
            "case_outputs": case_outputs,
            "resolved_variables": runtime_variables,
        }

    step_summaries: list[dict[str, Any]] = []
    last_source_data: Any = None
    overall_status = "success"
    blocked = False

    for step in sorted(steps, key=lambda item: (int(item.get("step_order") or 0), int(item.get("id") or 0))):
        step_start = datetime.now()
        request_payload: Any = {}
        response_payload: Any = {}
        logs = [f"步骤开始: {step.get('name') or '未命名步骤'}"]
        error_message = ""
        status = "pending"

        if blocked:
            status = "skipped"
            logs.append("前序步骤失败，当前步骤已跳过")
            _insert_step_result(
                report_id,
                case_item.get("id"),
                step,
                status,
                request_payload,
                response_payload,
                logs,
                error_message,
                step_start,
                datetime.now(),
            )
            step_summaries.append(
                {
                    "step_id": step.get("id"),
                    "step_order": step.get("step_order"),
                    "step_name": step.get("name") or "",
                    "status": status,
                    "message": "前序步骤失败，已跳过",
                }
            )
            continue

        if step.get("enabled", True) is False:
            status = "skipped"
            logs.append("步骤已禁用，跳过执行")
            _insert_step_result(
                report_id,
                case_item.get("id"),
                step,
                status,
                request_payload,
                response_payload,
                logs,
                error_message,
                step_start,
                datetime.now(),
            )
            step_summaries.append(
                {
                    "step_id": step.get("id"),
                    "step_order": step.get("step_order"),
                    "step_name": step.get("name") or "",
                    "status": status,
                    "message": "步骤已禁用",
                }
            )
            continue

        try:
            runtime_variables.update(_as_dict(step.get("variables")))
            runtime_variables["current_step_order"] = step.get("step_order")
            runtime_variables["current_step_name"] = step.get("name") or ""
            current_source_data = last_source_data
            encryption = EncryptionConfig(
                enabled=bool(case_item.get("enable_encryption")) and bool(step.get("enable_encryption")),
                encrypt_url=str(case_item.get("encrypt_url") or ""),
                decrypt_url=str(case_item.get("decrypt_url") or ""),
            )

            for tool in _tool_entries(step.get("pre_processing")):
                tool_result, current_source_data, tool_logs = _execute_tool(
                    tool,
                    current_source_data,
                    runtime_variables,
                    environment,
                    encryption,
                    combined_global_headers,
                )
                logs.extend(tool_logs)
                response_payload.setdefault("pre_processing", []).append(tool_result)

            template_id = step.get("api_template_id")
            template = templates.get(int(template_id)) if template_id else None
            if not template:
                raise ValueError("步骤未绑定有效的接口模板")

            main_result = execute_request_definition(
                RequestDefinition(
                    protocol="http",
                    url=str(template.get("url_path") or ""),
                    method=str(template.get("method") or "GET").upper(),
                    headers=_as_dict(template.get("headers")),
                    params=template.get("params"),
                    body=template.get("body"),
                    timeout=int(template.get("timeout") or 30),
                    retry_enabled=bool(template.get("retry_enabled")),
                    retry_count=int(template.get("retry_count") or 0),
                    metadata={"step_id": step.get("id"), "step_order": step.get("step_order")},
                ),
                RequestExecutionContext(
                    request_id=case_request_id,
                    variables=runtime_variables,
                    base_url=str(environment.get("base_url") or ""),
                    global_headers=combined_global_headers,
                    encryption=encryption,
                    allow_legacy_placeholders=True,
                ),
            )
            request_payload = main_result.request
            if main_result.status_code >= 400:
                raise ValueError(f"接口请求失败，状态码 {main_result.status_code}")
            response_payload["main_request"] = {
                "status_code": main_result.status_code,
                "headers": main_result.headers,
                "body": main_result.body,
                "raw_body": main_result.raw_body,
                "decrypted_body": main_result.decrypted_body,
                "duration_ms": main_result.duration_ms,
            }
            logs.append(
                f"主请求完成: {main_result.request.get('method')} {main_result.request.get('url')} -> {main_result.status_code}"
            )
            current_source_data = _extract_response_source(response_payload["main_request"])

            for tool in _tool_entries(step.get("assertions")):
                tool_result, current_source_data, tool_logs = _execute_tool(
                    tool,
                    current_source_data,
                    runtime_variables,
                    environment,
                    encryption,
                    combined_global_headers,
                )
                logs.extend(tool_logs)
                response_payload.setdefault("assertions", []).append(tool_result)

            for tool in _tool_entries(step.get("post_processing")):
                tool_result, current_source_data, tool_logs = _execute_tool(
                    tool,
                    current_source_data,
                    runtime_variables,
                    environment,
                    encryption,
                    combined_global_headers,
                )
                logs.extend(tool_logs)
                response_payload.setdefault("post_processing", []).append(tool_result)

            last_source_data = current_source_data
            status = "success"
        except Exception as exc:
            status = "failed"
            overall_status = "failed"
            blocked = True
            error_message = str(exc)
            logs.append(f"步骤失败: {error_message}")

        _insert_step_result(
            report_id,
            case_item.get("id"),
            step,
            status,
            request_payload,
            response_payload,
            logs,
            error_message,
            step_start,
            datetime.now(),
        )
        step_summaries.append(
            {
                "step_id": step.get("id"),
                "step_order": step.get("step_order"),
                "step_name": step.get("name") or "",
                "status": status,
                "message": error_message or "执行成功",
            }
        )

    passed_steps = sum(1 for item in step_summaries if item["status"] == "success")
    failed_steps = sum(1 for item in step_summaries if item["status"] == "failed")
    skipped_steps = sum(1 for item in step_summaries if item["status"] == "skipped")
    report_end = datetime.now()
    case_outputs = _resolve_case_outputs(case_item, runtime_variables)
    execute(
        """
        UPDATE test_reports
        SET status = %s,
            passed_cases = %s,
            failed_cases = %s,
            error_cases = %s,
            end_time = %s,
            duration = %s,
            summary_json = %s
        WHERE id = %s
        """,
        (
            overall_status,
            1 if overall_status == "success" else 0,
            1 if overall_status == "failed" else 0,
            0,
            report_end,
            round((report_end - report_start).total_seconds(), 3),
            _json_text(
                {
                    "request_id": case_request_id,
                    "passed_steps": passed_steps,
                    "failed_steps": failed_steps,
                    "skipped_steps": skipped_steps,
                    "steps": step_summaries,
                    "global_setup": {
                        "logs": global_setup_logs,
                        "login_request": global_login_result,
                    },
                    "case_outputs": case_outputs,
                }
            ),
            report_id,
        ),
    )

    if not steps:
        overall_status = "success"

    message = (
        f"执行完成，成功 {passed_steps} 步，失败 {failed_steps} 步，跳过 {skipped_steps} 步"
        if steps
        else "当前用例没有可执行步骤"
    )
    return {
        "report_id": report_id,
        "request_id": case_request_id,
        "case_id": case_item.get("id"),
        "case_name": case_item.get("name") or "未命名用例",
        "status": overall_status,
        "message": message,
        "summary": {
            "passed_steps": passed_steps,
            "failed_steps": failed_steps,
            "skipped_steps": skipped_steps,
        },
        "steps": step_summaries,
        "case_outputs": case_outputs,
        "resolved_variables": runtime_variables,
    }
