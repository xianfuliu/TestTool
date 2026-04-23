from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.common.python_execution import (
    PythonExecutionContext,
    execute_python_script,
    extract_python_output_variables,
)
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
    replace_template_data,
    replace_template_text,
    resolve_global_request_runtime,
)
from apps.common.sql_execution import (
    SqlExecutionContext,
    execute_sql_query,
    extract_sql_output_variables,
)
from test_platform.db import execute, fetch_all, fetch_one

from .report_service import ensure_report_schema_ready


class ToolExecutionError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        result: dict[str, Any] | None = None,
        source_data: Any = None,
        logs: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.result = result or {}
        self.source_data = source_data
        self.logs = logs or []


class AssertionExecutionError(ToolExecutionError):
    pass


_INTERNAL_RUNTIME_VARIABLE_KEYS = {"current_step_name", "current_step_order"}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _json_text(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _log_value(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return str(value)


def _short_log_value(value: Any, limit: int = 240) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(_log_value(value), ensure_ascii=False)
    else:
        text = "" if value is None else str(value)
    return text if len(text) <= limit else f"{text[:limit]}..."


def _compact_log_value(value: Any, limit: int = 1600) -> str:
    if value in (None, ""):
        return ""
    normalised = _log_value(value)
    if isinstance(normalised, str):
        stripped = normalised.strip()
        if not stripped:
            return ""
        try:
            parsed = json.loads(stripped)
        except (TypeError, ValueError):
            text = " ".join(stripped.split())
        else:
            text = json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(normalised, ensure_ascii=False, separators=(",", ":"))
    return text if len(text) <= limit else f"{text[:limit]}..."


def _format_log_time(value: Any = None) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    if isinstance(value, str) and value.strip():
        text = value.strip()
        try:
            return datetime.fromisoformat(text).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        except ValueError:
            return text[:23] if len(text) > 19 else text[:19]
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _parse_log_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    for candidate in (text, text.replace(" ", "T", 1)):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    for pattern in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:26], pattern)
        except ValueError:
            continue
    return None


def _refine_log_line_times(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous: datetime | None = None
    for line in lines:
        current = _parse_log_time(line.get("time")) or datetime.now()
        if previous is not None and current <= previous:
            current = previous + timedelta(milliseconds=1)
        line["time"] = _format_log_time(current)
        previous = current
    return lines


def _make_log_line(
    level: str,
    scope: str,
    message: Any,
    *,
    sub_scope: str = "",
    subject: str = "",
    icon: str = "info",
    timestamp: Any = None,
) -> dict[str, Any]:
    return {
        "time": _format_log_time(timestamp),
        "level": str(level or "INFO").upper(),
        "scope": scope,
        "sub_scope": sub_scope,
        "subject": subject,
        "icon": icon,
        "message": "" if message is None else str(message),
    }


def _infer_log_level(message: Any, default: str = "INFO") -> str:
    text = str(message or "").lower()
    if any(keyword in text for keyword in ("error", "失败", "异常", "错误", "超时", "未匹配")):
        return "ERROR"
    if any(keyword in text for keyword in ("warn", "warning", "跳过")):
        return "WARN"
    if "debug" in text:
        return "DEBUG"
    return default


def _tool_type_label(tool: Any) -> str:
    tool_type = str(_as_dict(tool).get("tool_type") or _as_dict(tool).get("type") or "").strip().lower()
    if tool_type in {"http_request", "http"}:
        return "HTTP"
    if tool_type in {"sql_tool", "sql"}:
        return "SQL"
    if tool_type in {"parameter_extract", "parameter_extraction"}:
        return "参数提取"
    if tool_type == "python_script":
        return "Python"
    if tool_type == "data_prepare":
        return "数据准备"
    if tool_type == "global_tool":
        return "全局工具"
    return tool_type.upper() if tool_type else "工具"


def _append_raw_log_lines(
    lines: list[dict[str, Any]],
    raw_logs: Any,
    *,
    timestamp: Any,
    scope: str,
    sub_scope: str = "",
    subject: str = "",
    icon: str = "info",
) -> None:
    for item in _as_list(raw_logs):
        lines.append(
            _make_log_line(
                _infer_log_level(item),
                scope,
                item,
                sub_scope=sub_scope,
                subject=subject,
                icon=icon,
                timestamp=timestamp,
            )
        )


def _append_variable_change_lines(
    lines: list[dict[str, Any]],
    changes: Any,
    *,
    timestamp: Any,
    prefix: str = "",
) -> None:
    change_map = _as_dict(changes)
    if not _has_variable_changes(change_map):
        return
    label = f"{prefix} - " if prefix else ""
    for key, value in _as_dict(change_map.get("added")).items():
        if key in _INTERNAL_RUNTIME_VARIABLE_KEYS:
            continue
        lines.append(
            _make_log_line(
                "INFO",
                "变量池",
                f"{label}新增变量 {key} = {_compact_log_value(value)}",
                icon="variable",
                timestamp=timestamp,
            )
        )
    for key, value in _as_dict(change_map.get("changed")).items():
        if key in _INTERNAL_RUNTIME_VARIABLE_KEYS:
            continue
        lines.append(
            _make_log_line(
                "INFO",
                "变量池",
                f"{label}更新变量 {key}: {_compact_log_value(_as_dict(value).get('before'))} -> {_compact_log_value(_as_dict(value).get('after'))}",
                icon="variable",
                timestamp=timestamp,
            )
        )
    for key, value in _as_dict(change_map.get("removed")).items():
        if key in _INTERNAL_RUNTIME_VARIABLE_KEYS:
            continue
        lines.append(
            _make_log_line(
                "WARN",
                "变量池",
                f"{label}移除变量 {key}，原值 {_compact_log_value(value)}",
                icon="variable",
                timestamp=timestamp,
            )
        )


def _append_http_exchange_lines(
    lines: list[dict[str, Any]],
    request_data: Any,
    response_data: Any,
    *,
    timestamp: Any,
    scope: str,
    sub_scope: str = "",
    subject: str = "",
) -> None:
    request_map = _as_dict(request_data)
    response_map = _as_dict(response_data)
    method = str(request_map.get("method") or "").upper()
    url = str(request_map.get("url") or "")
    if method or url:
        lines.append(
            _make_log_line(
                "INFO",
                scope,
                f"请求: {method or '-'} {url or '-'}",
                sub_scope=sub_scope,
                subject=subject,
                icon="request",
                timestamp=timestamp,
            )
        )
    request_headers = _safe_headers_for_log(_as_dict(request_map.get("headers")))
    if request_headers:
        lines.append(
            _make_log_line(
                "INFO",
                scope,
                f"请求头: {_compact_log_value(request_headers)}",
                sub_scope=sub_scope,
                subject=subject,
                icon="header",
                timestamp=timestamp,
            )
        )
    if request_map.get("params") not in (None, "", {}, []):
        lines.append(
            _make_log_line(
                "INFO",
                scope,
                f"请求参数: {_compact_log_value(request_map.get('params'))}",
                sub_scope=sub_scope,
                subject=subject,
                icon="request",
                timestamp=timestamp,
            )
        )
    if request_map.get("body") not in (None, "", {}, []):
        lines.append(
            _make_log_line(
                "INFO",
                scope,
                f"请求体: {_compact_log_value(request_map.get('body'))}",
                sub_scope=sub_scope,
                subject=subject,
                icon="request",
                timestamp=timestamp,
            )
        )
    status_code = response_map.get("status_code")
    if status_code is not None:
        level = "ERROR" if int(status_code or 0) >= 400 else "INFO"
        lines.append(
            _make_log_line(
                level,
                scope,
                f"响应状态: {status_code}，耗时 {response_map.get('duration_ms') or 0}ms",
                sub_scope=sub_scope,
                subject=subject,
                icon="response",
                timestamp=timestamp,
            )
        )
    response_body = response_map.get("decrypted_body")
    if response_body in (None, ""):
        response_body = response_map.get("body")
    if response_body in (None, ""):
        response_body = response_map.get("raw_body")
    if response_body not in (None, ""):
        lines.append(
            _make_log_line(
                "INFO",
                scope,
                f"响应体: {_compact_log_value(response_body)}",
                sub_scope=sub_scope,
                subject=subject,
                icon="response",
                timestamp=timestamp,
            )
        )


def _append_tool_detail_lines(
    lines: list[dict[str, Any]],
    tool: Any,
    *,
    timestamp: Any,
    scope: str,
) -> None:
    tool_map = _as_dict(tool)
    tool_name = str(tool_map.get("name") or tool_map.get("tool_type") or "工具")
    sub_scope = "" if scope == "断言" else _tool_type_label(tool_map)
    subject = "" if scope == "断言" else tool_name
    level = "ERROR" if tool_map.get("status") == "failed" else "INFO"
    raw_logs = _as_list(tool_map.get("logs"))
    leading_logs = []
    deferred_logs = []
    for raw_log in raw_logs:
        log_text = str(raw_log or "")
        if any(keyword in log_text for keyword in ("响应提取", "参数提取")):
            deferred_logs.append(raw_log)
        else:
            leading_logs.append(raw_log)
    lines.append(
        _make_log_line(
            "INFO",
            scope,
            f"执行断言: {tool_name}" if scope == "断言" else f"开始执行{scope}工具: {tool_name}",
            sub_scope=sub_scope,
            subject=subject,
            icon="assert" if scope == "断言" else "tool",
            timestamp=timestamp,
        )
    )
    _append_raw_log_lines(
        lines,
        leading_logs,
        timestamp=timestamp,
        scope=scope,
        sub_scope=sub_scope,
        subject=subject,
        icon="assert" if scope == "断言" else "tool",
    )
    if scope != "断言":
        _append_http_exchange_lines(
            lines,
            tool_map.get("request"),
            tool_map.get("response"),
            timestamp=timestamp,
            scope=scope,
            sub_scope=sub_scope,
            subject=subject,
        )
    _append_raw_log_lines(
        lines,
        deferred_logs,
        timestamp=timestamp,
        scope=scope,
        sub_scope=sub_scope,
        subject=subject,
        icon="assert" if scope == "断言" else "tool",
    )
    if tool_map.get("extractions") not in (None, "", {}, []):
        lines.append(
            _make_log_line(
                "INFO",
                scope,
                f"提取结果: {_compact_log_value(tool_map.get('extractions'))}",
                sub_scope=sub_scope,
                subject=subject,
                icon="variable",
                timestamp=timestamp,
            )
        )
    if scope != "断言" and tool_map.get("assertions") not in (None, "", {}, []):
        lines.append(
            _make_log_line(
                "INFO",
                scope,
                f"断言结果: {_compact_log_value(tool_map.get('assertions'))}",
                sub_scope=sub_scope,
                subject=subject,
                icon="assert",
                timestamp=timestamp,
            )
        )
    _append_variable_change_lines(
        lines,
        tool_map.get("variable_changes"),
        timestamp=timestamp,
        prefix=tool_name,
    )
    error_message = str(tool_map.get("error_message") or "")
    log_texts = [str(item or "") for item in raw_logs]
    error_already_logged = any(error_message and error_message in log_text for log_text in log_texts)
    if str(tool_map.get("failure_type") or "") == "extraction":
        error_already_logged = error_already_logged or any("提取失败" in log_text for log_text in log_texts)
    if error_message and not error_already_logged:
        lines.append(
            _make_log_line(
                "ERROR",
                scope,
                error_message,
                sub_scope=sub_scope,
                subject=subject,
                icon="error",
                timestamp=timestamp,
            )
        )


def _build_compact_execution_log_lines(execution_log: dict[str, Any]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    started_at = execution_log.get("started_at")
    ended_at = execution_log.get("ended_at")
    case_name = execution_log.get("case_name") or "未命名用例"
    lines.append(
        _make_log_line(
            "INFO",
            "全局",
            f"开始执行用例: {case_name}",
            icon="start",
            timestamp=started_at,
        )
    )

    global_setup = _as_dict(execution_log.get("global_setup"))
    context = _as_dict(global_setup.get("context"))
    encryption = _as_dict(context.get("encryption"))
    if encryption:
        enabled = "启用" if encryption.get("enabled") else "未启用"
        lines.append(
            _make_log_line(
                "INFO",
                "全局",
                f"加解密配置: {enabled}，加密URL={encryption.get('encrypt_url') or '-'}，解密URL={encryption.get('decrypt_url') or '-'}",
                sub_scope="加解密",
                icon="lock" if encryption.get("enabled") else "unlock",
                timestamp=started_at,
            )
        )
    header_config = _as_dict(context.get("header_config"))
    if header_config.get("enabled") or header_config.get("after_replace"):
        lines.append(
            _make_log_line(
                "INFO",
                "全局",
                f"全局请求头: {_compact_log_value(header_config.get('after_replace') or header_config.get('before_replace'))}",
                sub_scope="全局请求头",
                icon="header",
                timestamp=started_at,
            )
        )
    login_request = _as_dict(global_setup.get("login_request"))
    if login_request:
        lines.append(
            _make_log_line(
                "INFO",
                "全局",
                "开始获取登录态",
                sub_scope="登录态获取",
                icon="start",
                timestamp=started_at,
            )
        )
        _append_http_exchange_lines(
            lines,
            login_request.get("request"),
            login_request,
            timestamp=started_at,
            scope="全局",
            sub_scope="登录态获取",
        )
        extracted = _as_dict(login_request.get("extracted_variables"))
        if extracted:
            lines.append(
                _make_log_line(
                    "INFO",
                    "全局",
                    f"登录态变量: {_compact_log_value(extracted)}",
                    sub_scope="登录态获取",
                    icon="variable",
                    timestamp=started_at,
                )
            )
    _append_raw_log_lines(
        lines,
        global_setup.get("logs"),
        timestamp=started_at,
        scope="全局",
        sub_scope="登录态获取" if login_request else "",
        icon="info",
    )
    _append_variable_change_lines(
        lines,
        global_setup.get("variable_changes"),
        timestamp=started_at,
        prefix="全局配置",
    )
    if global_setup.get("error"):
        lines.append(
            _make_log_line(
                "ERROR",
                "全局",
                f"全局配置执行失败: {global_setup.get('error')}",
                icon="error",
                timestamp=ended_at or started_at,
            )
        )

    for step in _as_list(execution_log.get("steps")):
        step_map = _as_dict(step)
        step_time = step_map.get("started_at") or started_at
        step_label = f"步骤 {step_map.get('step_order') or '-'}"
        step_name = step_map.get("step_name") or "未命名步骤"
        lines.append(
            _make_log_line(
                "INFO",
                "步骤",
                f"开始执行 {step_label}: {step_name}",
                icon="start",
                timestamp=step_time,
            )
        )
        for change_detail in _as_list(step_map.get("variable_changes")):
            detail = _as_dict(change_detail)
            if not str(detail.get("stage") or "").startswith("步骤变量初始化"):
                continue
            _append_variable_change_lines(
                lines,
                detail.get("changes"),
                timestamp=step_time,
                prefix=str(detail.get("stage") or ""),
            )

        for tool in _as_list(step_map.get("pre_processing")):
            _append_tool_detail_lines(lines, tool, timestamp=step_time, scope="前置")

        main_request = _as_dict(step_map.get("main_request"))
        if main_request:
            main_encryption = _as_dict(main_request.get("encryption"))
            if main_encryption:
                lines.append(
                    _make_log_line(
                        "INFO",
                        "全局",
                        f"步骤加解密: {'启用' if main_encryption.get('enabled') else '未启用'}",
                        sub_scope="加解密",
                        icon="lock" if main_encryption.get("enabled") else "unlock",
                        timestamp=step_time,
                    )
                )
            global_headers = _as_dict(main_request.get("global_headers"))
            if global_headers.get("enabled") or global_headers.get("after_replace"):
                lines.append(
                    _make_log_line(
                        "INFO",
                        "全局",
                        f"步骤全局请求头: {_compact_log_value(global_headers.get('after_replace') or global_headers.get('before_replace'))}",
                        sub_scope="全局请求头",
                        icon="header",
                        timestamp=step_time,
                    )
                )
            _append_http_exchange_lines(
                lines,
                main_request.get("after_replace"),
                main_request.get("response"),
                timestamp=step_time,
                scope="步骤",
            )

        for section_key, scope in (
            ("assertions", "断言"),
            ("post_processing", "后置"),
        ):
            for tool in _as_list(step_map.get(section_key)):
                _append_tool_detail_lines(lines, tool, timestamp=step_time, scope=scope)

        step_status = step_map.get("status")
        lines.append(
            _make_log_line(
                "ERROR" if step_status == "failed" else "WARN" if step_status == "skipped" else "INFO",
                "步骤",
                f"{step_label}执行{'失败' if step_status == 'failed' else '跳过' if step_status == 'skipped' else '成功'}: {step_map.get('summary') or ''}".strip(),
                icon="error" if step_status == "failed" else "warning" if step_status == "skipped" else "success",
                timestamp=step_map.get("ended_at") or step_time,
            )
        )

    case_outputs = execution_log.get("case_outputs")
    if case_outputs not in (None, "", {}, []):
        lines.append(
            _make_log_line(
                "INFO",
                "全局",
                f"用例出参: {_compact_log_value(case_outputs)}",
                sub_scope="用例出参",
                icon="output",
                timestamp=ended_at or started_at,
            )
        )
    return _refine_log_line_times(lines)


def _variable_changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_keys = set(before.keys()) - _INTERNAL_RUNTIME_VARIABLE_KEYS
    after_keys = set(after.keys()) - _INTERNAL_RUNTIME_VARIABLE_KEYS
    added = {key: _log_value(after[key]) for key in sorted(after_keys - before_keys)}
    removed = {key: _log_value(before[key]) for key in sorted(before_keys - after_keys)}
    changed: dict[str, Any] = {}
    for key in sorted(before_keys & after_keys):
        if _log_value(before.get(key)) != _log_value(after.get(key)):
            changed[key] = {
                "before": _log_value(before.get(key)),
                "after": _log_value(after.get(key)),
            }
    return {
        "added": added,
        "changed": changed,
        "removed": removed,
    }


def _has_variable_changes(changes: dict[str, Any]) -> bool:
    return bool(changes.get("added") or changes.get("changed") or changes.get("removed"))


def _append_variable_change_logs(logs: list[str], title: str, changes: dict[str, Any]) -> None:
    if not _has_variable_changes(changes):
        return
    prefix = f"{title} - " if title else ""
    for key, value in _as_dict(changes.get("added")).items():
        logs.append(f"{prefix}变量池新增: {key} = {_short_log_value(value)}")
    for key, value in _as_dict(changes.get("changed")).items():
        logs.append(
            f"{prefix}变量池更新: {key}: {_short_log_value(value.get('before'))} -> {_short_log_value(value.get('after'))}"
        )
    for key, value in _as_dict(changes.get("removed")).items():
        logs.append(f"{prefix}变量池移除: {key}，原值 {_short_log_value(value)}")


def _variable_change_detail(stage: str, changes: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": stage,
        "changes": changes,
        "variable_pool": _log_value(variables),
    }


def _mask_header_value(key: str, value: Any) -> Any:
    if str(key).strip().lower() in {"authorization", "token", "access-token", "x-token"}:
        text = str(value or "")
        if len(text) <= 8:
            return "***"
        return f"{text[:4]}***{text[-4:]}"
    return value


def _safe_headers_for_log(headers: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _mask_header_value(str(key), value) for key, value in _as_dict(headers).items()}


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


def _enabled_by_default(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() not in {"false", "0", "no", "n"}
    return bool(value)


def _enabled_by_config(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _config_enabled(config: dict[str, Any], snake_key: str, camel_key: str) -> bool:
    if snake_key in config:
        return _enabled_by_config(config.get(snake_key))
    if camel_key in config:
        return _enabled_by_config(config.get(camel_key))
    return False


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
        "use_global_headers": _enabled_by_default(step.get("use_global_headers", True)),
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


def _resolve_extractions(
    extractions: list[dict[str, Any]],
    source_data: Any,
    variables: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    extracted: dict[str, Any] = {}
    details: list[dict[str, Any]] = []
    for row in extractions:
        variable_name = str(row.get("variable") or "").strip()
        response_path = replace_template_text(
            str(row.get("path") or "").strip(),
            variables,
            allow_legacy_placeholders=True,
        )
        if not variable_name or not response_path:
            details.append(
                {
                    "variable": variable_name,
                    "path": str(row.get("path") or "").strip(),
                    "resolved_path": response_path,
                    "matched": False,
                    "value": None,
                    "message": "变量名称或提取路径为空",
                }
            )
            continue
        value = extract_response_value(source_data, response_path)
        if value is not None:
            extracted[variable_name] = value
        details.append(
            {
                "variable": variable_name,
                "path": str(row.get("path") or "").strip(),
                "resolved_path": response_path,
                "matched": value is not None,
                "value": _log_value(value),
            }
        )
    variables.update(extracted)
    return extracted, details


def _apply_extractions(
    extractions: list[dict[str, Any]],
    source_data: Any,
    variables: dict[str, Any],
) -> dict[str, Any]:
    extracted, _details = _resolve_extractions(extractions, source_data, variables)
    return extracted


def _execute_sql_tool(config: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    return execute_sql_query(
        config,
        SqlExecutionContext(
            variables=variables,
            allow_legacy_placeholders=True,
            allowed_statement_prefixes=(),
        ),
    )


def _execute_http_tool(
    config: dict[str, Any],
    variables: dict[str, Any],
    environment: dict[str, Any],
    encryption: EncryptionConfig,
    global_headers: dict[str, Any] | None,
) -> dict[str, Any]:
    use_global_encryption = _config_enabled(config, "use_global_encryption", "useGlobalEncryption")
    use_global_headers = _config_enabled(config, "use_global_headers", "useGlobalHeaders")
    request_encryption = (
        encryption
        if use_global_encryption
        else EncryptionConfig(
            enabled=False,
            encrypt_url=encryption.encrypt_url,
            decrypt_url=encryption.decrypt_url,
        )
    )
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
                _as_dict(global_headers) if use_global_headers else {},
            ),
            encryption=request_encryption,
            allow_legacy_placeholders=True,
        ),
    )
    return {
        "request": result.request,
        "status": "failed" if result.status_code >= 400 else "success",
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
    extracted, extraction_details = _resolve_extractions(extractions, source_data, variables)
    return {
        "request": {"extractions": extractions},
        "status": "success",
        "body": extracted,
        "raw_body": _json_text(extracted),
        "decrypted_body": extracted,
        "extracted": extracted,
        "extraction_details": extraction_details,
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
    return {
        "request": {"assertions": assertions},
        "status": "failed" if failed else "success",
        "body": {"passed": not failed, "results": results},
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
        extracted, extraction_details = _resolve_extractions(
            _as_list(tool.get("extractions")) or _as_list(_as_dict(tool.get("config")).get("extractions")),
            _extract_response_source(result),
            variables,
        )
        result["extracted"] = extracted
        result["extraction_details"] = extraction_details
        missing_extractions: list[dict[str, Any]] = []
        for detail in extraction_details:
            matched = bool(detail.get("matched"))
            status_text = "成功" if matched else "失败"
            if not matched:
                missing_extractions.append(detail)
            logs.append(
                f"响应提取{status_text}: {detail.get('variable') or '-'} <- {detail.get('resolved_path') or detail.get('path') or '-'}"
            )
        if result.get("status_code", 0) >= 400:
            raise ToolExecutionError(
                f"HTTP 工具执行失败，状态码 {result.get('status_code')}",
                result=result,
                source_data=_extract_response_source(result),
                logs=logs,
            )
        if missing_extractions:
            result["status"] = "failed"
            missing_text = "，".join(
                f"{detail.get('variable') or '-'} <- {detail.get('resolved_path') or detail.get('path') or '-'}"
                for detail in missing_extractions
            )
            result["error_message"] = f"响应提取失败: {missing_text}"
            result["failure_type"] = "extraction"
        return result, _extract_response_source(result), logs

    if tool_type == "sql_tool":
        result = _execute_sql_tool(_as_dict(tool.get("config")), variables)
        output_rows = _as_list(result.get("rows"))
        output_fields = _as_list(tool.get("output_fields")) or _as_list(_as_dict(tool.get("config")).get("output_fields"))
        extracted, extraction_details = extract_sql_output_variables(output_rows, output_fields)
        variables.update(extracted)
        if extracted:
            logs.append(f"SQL 输出变量已写入上下文: {', '.join(extracted.keys())}")
        sql_source_data = build_response_extraction_source(result)
        extractions = _as_list(tool.get("extractions")) or _as_list(_as_dict(tool.get("config")).get("extractions"))
        if extractions:
            explicit_extracted, explicit_details = _resolve_extractions(extractions, sql_source_data, variables)
            extracted.update(explicit_extracted)
            extraction_details.extend(explicit_details)
        result["extracted"] = extracted
        result["extraction_details"] = extraction_details
        missing_extractions = [detail for detail in extraction_details if not _as_dict(detail).get("matched")]
        for detail in extraction_details:
            matched = bool(_as_dict(detail).get("matched"))
            logs.append(
                f"SQL 提取{'成功' if matched else '失败'}: "
                f"{_as_dict(detail).get('variable') or '-'} <- "
                f"{_as_dict(detail).get('resolved_path') or _as_dict(detail).get('path') or '-'}"
            )
        if missing_extractions:
            result["status"] = "failed"
            result["error_message"] = "SQL 提取失败: " + "，".join(
                f"{_as_dict(detail).get('variable') or '-'} <- "
                f"{_as_dict(detail).get('resolved_path') or _as_dict(detail).get('path') or '-'}"
                for detail in missing_extractions
            )
            result["failure_type"] = "extraction"
        return result, sql_source_data, logs

    if tool_type == "python_script":
        config = _as_dict(tool.get("config"))
        result = execute_python_script(
            config,
            PythonExecutionContext(
                variables=variables,
                timeout_seconds=_int_value(config.get("timeout_seconds") or config.get("timeout"), 60),
                allow_legacy_placeholders=False,
            ),
        )
        python_source_data = build_response_extraction_source(result)
        output_fields = _as_list(tool.get("output_fields")) or _as_list(config.get("output_fields"))
        extracted, extraction_details = extract_python_output_variables(result.get("body"), output_fields)
        variables.update(extracted)
        if extracted:
            logs.append(f"Python 输出变量已写入上下文: {', '.join(extracted.keys())}")
        extractions = _as_list(tool.get("extractions")) or _as_list(config.get("extractions"))
        if extractions:
            explicit_extracted, explicit_details = _resolve_extractions(extractions, python_source_data, variables)
            extracted.update(explicit_extracted)
            extraction_details.extend(explicit_details)
        result["extracted"] = extracted
        result["extraction_details"] = extraction_details
        stdout = str(result.get("stdout") or "").strip()
        stderr = str(result.get("stderr") or "").strip()
        if stdout:
            logs.append(f"Python stdout: {_short_log_value(stdout, 1200)}")
        if stderr:
            logs.append(f"Python stderr: {_short_log_value(stderr, 1200)}")
        for detail in extraction_details:
            detail_map = _as_dict(detail)
            matched = bool(detail_map.get("matched"))
            logs.append(
                f"Python 提取{'成功' if matched else '失败'}: "
                f"{detail_map.get('variable') or '-'} <- {detail_map.get('resolved_path') or detail_map.get('path') or '-'}"
            )
        missing_extractions = [detail for detail in extraction_details if not _as_dict(detail).get("matched")]
        if missing_extractions and result.get("status") != "failed":
            result["status"] = "failed"
            result["error_message"] = "Python 提取失败: " + "，".join(
                f"{_as_dict(detail).get('variable') or '-'} <- "
                f"{_as_dict(detail).get('resolved_path') or _as_dict(detail).get('path') or '-'}"
                for detail in missing_extractions
            )
            result["failure_type"] = "extraction"
        return result, python_source_data, logs

    if tool_type in {"parameter_extract", "parameter_extraction"}:
        result = _execute_parameter_extraction_tool(tool, source_data, variables)
        extracted = _as_dict(result.get("extracted"))
        missing_extractions: list[dict[str, Any]] = []
        for detail in _as_list(result.get("extraction_details")):
            detail_map = _as_dict(detail)
            matched = bool(detail_map.get("matched"))
            status_text = "成功" if matched else "失败"
            if not matched:
                missing_extractions.append(detail_map)
            logs.append(
                f"参数提取{status_text}: {detail_map.get('variable') or '-'} <- {detail_map.get('resolved_path') or detail_map.get('path') or '-'}"
            )
        if missing_extractions:
            result["status"] = "failed"
            missing_text = "，".join(
                f"{detail.get('variable') or '-'} <- {detail.get('resolved_path') or detail.get('path') or '-'}"
                for detail in missing_extractions
            )
            result["error_message"] = f"参数提取失败: {missing_text}"
            result["failure_type"] = "extraction"
        return result, source_data, logs

    if "assert" in tool_type:
        result = _execute_assertion_tool(tool, source_data, variables)
        assertion_results = _as_list(_as_dict(result.get("body")).get("results"))
        if result.get("status") == "failed":
            failed = next((item for item in assertion_results if not _as_dict(item).get("passed")), {})
            failed_detail = _as_dict(failed)
            raise AssertionExecutionError(
                f"断言失败: {failed_detail.get('field')} {failed_detail.get('operator')} "
                f"期望 {failed_detail.get('expected')}，实际 {failed_detail.get('actual')}",
                result=result,
                source_data=source_data,
                logs=logs,
            )
        if len(assertion_results) == 1:
            passed_detail = _as_dict(assertion_results[0])
            logs.append(
                f"断言成功: {passed_detail.get('field')} {passed_detail.get('operator')} "
                f"期望 {_short_log_value(passed_detail.get('expected'))}，"
                f"实际 {_short_log_value(passed_detail.get('actual'))}"
            )
        else:
            logs.append(f"断言成功: {len(assertion_results)} 条规则全部通过")
        return result, source_data, logs

    raise ValueError(f"暂不支持 {tool_type} 工具执行")


def _build_tool_log_detail(
    section: str,
    tool: dict[str, Any],
    result: dict[str, Any],
    tool_logs: list[str],
    variable_changes: dict[str, Any],
    *,
    status: str = "success",
    error_message: str = "",
) -> dict[str, Any]:
    response_body = _as_dict(result.get("body")) if isinstance(result.get("body"), dict) else {}
    return {
        "section": section,
        "id": tool.get("id"),
        "name": tool.get("name") or tool.get("id") or tool.get("tool_type"),
        "tool_type": tool.get("tool_type") or tool.get("type"),
        "summary": tool.get("summary") or "",
        "status": status,
        "failure_type": result.get("failure_type") or "",
        "logs": tool_logs,
        "request": _log_value(result.get("request")),
        "response": {
            "status": result.get("status"),
            "status_code": result.get("status_code"),
            "headers": _log_value(result.get("headers")),
            "body": _log_value(result.get("body")),
            "raw_body": result.get("raw_body"),
            "decrypted_body": _log_value(result.get("decrypted_body")),
            "duration_ms": result.get("duration_ms"),
        },
        "extractions": _log_value(result.get("extraction_details") or result.get("extracted")),
        "assertions": _log_value(response_body.get("results")),
        "variable_changes": variable_changes,
        "error_message": error_message,
    }


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


def execute_case_run(
    case_snapshot: dict[str, Any],
    *,
    create_report: bool = True,
    trigger_type: str = "manual",
) -> dict[str, Any]:
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
    enabled_steps = [step for step in steps if step.get("enabled", True) is not False]
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
    report_id: int | None = None
    if create_report:
        ensure_report_schema_ready()
        report_id = execute(
            """
            INSERT INTO test_reports (
                report_type,
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                "test_case",
                case_item.get("id"),
                case_item.get("project_id"),
                report_name,
                "running",
                1,
                0,
                0,
                0,
                report_start,
                trigger_type,
                _json_text({"request_id": case_request_id, "steps": [], "report_type": "test_case"}),
            ),
        )

    base_encryption = EncryptionConfig(
        enabled=bool(case_item.get("enable_encryption")),
        encrypt_url=str(case_item.get("encrypt_url") or ""),
        decrypt_url=str(case_item.get("decrypt_url") or ""),
    )
    environment_headers = _as_dict(environment.get("headers"))
    combined_global_headers = dict(environment_headers)
    normalized_global_config = normalize_global_request_config(case_item.get("global_request_config"))
    login_config = _as_dict(normalized_global_config.get("login_request"))
    header_config = _as_dict(normalized_global_config.get("header_config"))
    raw_global_headers = _as_dict(header_config.get("headers"))
    global_context = {
        "initial_variable_pool": _log_value(runtime_variables),
        "global_variables": _log_value(runtime_variables),
        "encryption": {
            "enabled": base_encryption.enabled,
            "encrypt_url": base_encryption.encrypt_url,
            "decrypt_url": base_encryption.decrypt_url,
        },
        "login_request": {
            "enabled": bool(login_config.get("enabled")),
            "method": login_config.get("method"),
            "url": login_config.get("url"),
            "use_global_encryption": bool(login_config.get("use_global_encryption")),
            "extractions": _log_value(login_config.get("extractions")),
        },
        "header_config": {
            "enabled": bool(header_config.get("enabled")),
            "before_replace": _log_value(raw_global_headers),
            "after_replace": {},
        },
    }
    global_setup_logs: list[str] = []
    global_login_result: dict[str, Any] | None = None
    global_variable_changes: dict[str, Any] = {"added": {}, "changed": {}, "removed": {}}

    try:
        if enabled_steps:
            global_variables_before = dict(runtime_variables)
            global_runtime = resolve_global_request_runtime(
                normalized_global_config,
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
            global_variable_changes = _variable_changes(global_variables_before, runtime_variables)
            _append_variable_change_logs(global_setup_logs, "全局配置", global_variable_changes)
            global_context["header_config"] = {
                **_as_dict(global_context.get("header_config")),
                "after_replace": _log_value(global_runtime.get("headers")),
            }
            global_context["variable_pool_after_setup"] = _log_value(runtime_variables)
    except Exception as exc:
        report_end = datetime.now()
        case_outputs = _resolve_case_outputs(case_item, runtime_variables)
        failed_execution_log = {
            "request_id": case_request_id,
            "case_name": case_item.get("name") or "未命名用例",
            "status": "failed",
            "message": f"全局配置执行失败: {exc}",
            "started_at": _format_log_time(report_start),
            "ended_at": _format_log_time(report_end),
            "global_setup": {
                "logs": global_setup_logs,
                "login_request": global_login_result,
                "variable_changes": global_variable_changes,
                "context": global_context,
                "error": str(exc),
            },
            "steps": [],
            "case_outputs": case_outputs,
            "final_variables": _log_value(runtime_variables),
        }
        failed_execution_log["lines"] = _build_compact_execution_log_lines(failed_execution_log)
        if report_id:
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
                            "report_type": "test_case",
                            "request_id": case_request_id,
                            "passed_steps": 0,
                            "failed_steps": 0,
                            "skipped_steps": 0,
                            "steps": [],
                            "global_setup": {
                                "logs": global_setup_logs,
                                "error": str(exc),
                                "variable_changes": global_variable_changes,
                                "context": global_context,
                            },
                            "case_outputs": case_outputs,
                            "execution_log": failed_execution_log,
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
            "execution_log": failed_execution_log,
        }

    step_summaries: list[dict[str, Any]] = []
    execution_steps: list[dict[str, Any]] = []
    last_source_data: Any = None
    overall_status = "success"
    hard_stop = False
    global_setup_attached = False

    ordered_steps = sorted(steps, key=lambda item: (int(item.get("step_order") or 0), int(item.get("id") or 0)))
    for step in ordered_steps:
        step_start = datetime.now()
        request_payload: Any = {}
        response_payload: Any = {}
        logs = [f"步骤开始: {step.get('name') or '未命名步骤'}"]
        step_detail: dict[str, Any] = {
            "step_id": step.get("id"),
            "step_order": step.get("step_order"),
            "step_name": step.get("name") or "未命名步骤",
            "status": "pending",
            "summary": "",
            "started_at": _format_log_time(step_start),
            "ended_at": "",
            "logs": logs,
            "global_setup": None,
            "global_context": global_context,
            "encryption": None,
            "variable_changes": [],
            "pre_processing": [],
            "main_request": None,
            "assertions": [],
            "post_processing": [],
            "error_message": "",
        }
        error_message = ""
        status = "pending"

        if step.get("enabled", True) is False:
            continue

        if not global_setup_attached and (login_config.get("enabled") or global_setup_logs or _has_variable_changes(global_variable_changes)):
            first_step_global_setup = {
                "logs": list(global_setup_logs),
                "login_request": global_login_result,
                "variable_changes": global_variable_changes,
                "variable_pool": _log_value(runtime_variables),
            }
            step_detail["global_setup"] = first_step_global_setup
            logs.append("全局请求头-登录态获取：开始记录一次性前置调用结果")
            logs.extend(global_setup_logs)
            global_setup_attached = True

        try:
            assertion_errors: list[str] = []
            step_variables_before = dict(runtime_variables)
            runtime_variables.update(_as_dict(step.get("variables")))
            runtime_variables["current_step_order"] = step.get("step_order")
            runtime_variables["current_step_name"] = step.get("name") or ""
            step_variable_changes = _variable_changes(step_variables_before, runtime_variables)
            if _has_variable_changes(step_variable_changes):
                step_detail["variable_changes"].append(
                    _variable_change_detail("步骤变量初始化", step_variable_changes, runtime_variables)
                )
                _append_variable_change_logs(logs, "步骤变量初始化", step_variable_changes)
            current_source_data = last_source_data
            encryption = EncryptionConfig(
                enabled=bool(case_item.get("enable_encryption")) and bool(step.get("enable_encryption")),
                encrypt_url=str(case_item.get("encrypt_url") or ""),
                decrypt_url=str(case_item.get("decrypt_url") or ""),
            )
            encryption_detail = None
            if encryption.enabled:
                encryption_detail = {
                    "global_enabled": bool(case_item.get("enable_encryption")),
                    "step_enabled": bool(step.get("enable_encryption")),
                    "enabled": True,
                    "encrypt_url": encryption.encrypt_url,
                    "decrypt_url": encryption.decrypt_url,
                }
                step_detail["encryption"] = encryption_detail
                logs.append(
                    "全局加解密配置："
                    "本步骤已启用，"
                    f"加密URL={encryption.encrypt_url or '-'}，解密URL={encryption.decrypt_url or '-'}"
                )

            def resolve_global_headers_for_tool() -> tuple[dict[str, Any], dict[str, Any]]:
                if not header_config.get("enabled"):
                    return {}, dict(environment_headers)
                rendered_headers = _as_dict(
                    replace_template_data(
                        raw_global_headers,
                        runtime_variables,
                        allow_legacy_placeholders=True,
                    )
                )
                return rendered_headers, merge_header_maps(environment_headers, rendered_headers)

            def resolve_current_global_headers() -> tuple[dict[str, Any], dict[str, Any]]:
                if not _enabled_by_default(step.get("use_global_headers", True)):
                    return {}, dict(environment_headers)
                return resolve_global_headers_for_tool()

            def execute_step_tool(section: str, tool: dict[str, Any], source_data: Any) -> Any:
                variables_before_tool = dict(runtime_variables)
                try:
                    tool_result, next_source_data, tool_logs = _execute_tool(
                        tool,
                        source_data,
                        runtime_variables,
                        environment,
                        encryption,
                        resolve_global_headers_for_tool()[1],
                    )
                    result_status = str(_as_dict(tool_result).get("status") or "success").lower()
                    tool_status = "failed" if result_status == "failed" else "success"
                    tool_error = str(_as_dict(tool_result).get("error_message") or "")
                    if tool_status == "failed" and not tool_error:
                        tool_error = "工具执行失败"
                    is_assertion_failure = False
                except AssertionExecutionError as exc:
                    tool_result = exc.result
                    next_source_data = exc.source_data if exc.source_data is not None else source_data
                    tool_logs = exc.logs
                    tool_status = "failed"
                    tool_error = str(exc)
                    is_assertion_failure = True
                except ToolExecutionError as exc:
                    tool_result = exc.result
                    next_source_data = exc.source_data if exc.source_data is not None else source_data
                    tool_logs = exc.logs
                    tool_status = "failed"
                    tool_error = str(exc)
                    is_assertion_failure = False
                except Exception as exc:
                    if section not in {"pre_processing", "post_processing"}:
                        raise
                    tool_result = {
                        "status": "failed",
                        "error_message": str(exc),
                        "body": {},
                        "raw_body": "",
                        "decrypted_body": {},
                    }
                    next_source_data = source_data
                    tool_logs = [f"工具执行失败: {exc}"]
                    tool_status = "failed"
                    tool_error = str(exc)
                    is_assertion_failure = False

                variable_changes = _variable_changes(variables_before_tool, runtime_variables)
                logs.extend(tool_logs)
                _append_variable_change_logs(logs, f"{tool.get('name') or tool.get('id') or tool.get('tool_type')}", variable_changes)
                if _has_variable_changes(variable_changes):
                    step_detail["variable_changes"].append(
                        _variable_change_detail(
                            f"{section}:{tool.get('name') or tool.get('id') or tool.get('tool_type')}",
                            variable_changes,
                            runtime_variables,
                        )
                    )
                response_payload.setdefault(section, []).append(tool_result)
                step_detail[section].append(
                    _build_tool_log_detail(
                        section,
                        tool,
                        tool_result,
                        tool_logs,
                        variable_changes,
                        status=tool_status,
                        error_message=tool_error,
                    )
                )
                if tool_status == "failed":
                    if section == "assertions" and is_assertion_failure:
                        assertion_errors.append(tool_error)
                        return next_source_data
                    if section in {"pre_processing", "post_processing"}:
                        return next_source_data
                    if str(_as_dict(tool_result).get("failure_type") or "") == "extraction":
                        return next_source_data
                    raise ValueError(tool_error)
                return next_source_data

            for tool in _tool_entries(step.get("pre_processing")):
                current_source_data = execute_step_tool("pre_processing", tool, current_source_data)

            template_id = step.get("api_template_id")
            template = templates.get(int(template_id)) if template_id else None
            if not template:
                raise ValueError("步骤未绑定有效的接口模板")

            raw_main_request = {
                "protocol": "http",
                "url": str(template.get("url_path") or ""),
                "method": str(template.get("method") or "GET").upper(),
                "headers": _log_value(_as_dict(template.get("headers"))),
                "params": _log_value(template.get("params")),
                "body": _log_value(template.get("body")),
                "timeout": int(template.get("timeout") or 30),
                "retry_enabled": bool(template.get("retry_enabled")),
                "retry_count": int(template.get("retry_count") or 0),
            }
            resolved_global_headers, request_global_headers = resolve_current_global_headers()
            global_header_detail = {
                "enabled": bool(header_config.get("enabled")) and _enabled_by_default(step.get("use_global_headers", True)),
                "global_enabled": bool(header_config.get("enabled")),
                "step_enabled": _enabled_by_default(step.get("use_global_headers", True)),
                "before_replace": _log_value(raw_global_headers),
                "after_replace": _log_value(resolved_global_headers),
            }
            if header_config.get("enabled") and _enabled_by_default(step.get("use_global_headers", True)):
                logs.append("全局请求头：已按当前变量池完成变量替换")
            main_result = execute_request_definition(
                RequestDefinition(
                    protocol=raw_main_request["protocol"],
                    url=raw_main_request["url"],
                    method=raw_main_request["method"],
                    headers=_as_dict(template.get("headers")),
                    params=template.get("params"),
                    body=template.get("body"),
                    timeout=raw_main_request["timeout"],
                    retry_enabled=raw_main_request["retry_enabled"],
                    retry_count=raw_main_request["retry_count"],
                    metadata={"step_id": step.get("id"), "step_order": step.get("step_order")},
                ),
                RequestExecutionContext(
                    request_id=case_request_id,
                    variables=runtime_variables,
                    base_url=str(environment.get("base_url") or ""),
                    global_headers=request_global_headers,
                    encryption=encryption,
                    allow_legacy_placeholders=True,
                ),
            )
            request_payload = main_result.request
            response_payload["main_request"] = {
                "status_code": main_result.status_code,
                "headers": main_result.headers,
                "body": main_result.body,
                "raw_body": main_result.raw_body,
                "decrypted_body": main_result.decrypted_body,
                "duration_ms": main_result.duration_ms,
            }
            main_request_detail = {
                "template_id": template_id,
                "template_name": template.get("name") or "",
                "before_replace": raw_main_request,
                "after_replace": _log_value(main_result.request),
                "global_headers": global_header_detail,
                "response": _log_value(response_payload["main_request"]),
            }
            if encryption_detail:
                main_request_detail["encryption"] = encryption_detail
            step_detail["main_request"] = main_request_detail
            logs.append(
                f"主请求完成: {main_result.request.get('method')} {main_result.request.get('url')} -> {main_result.status_code}"
            )
            logs.append("主请求参数已记录: 变量替换前、变量替换后、响应信息")
            if main_result.status_code >= 400:
                raise ValueError(f"接口请求失败，状态码 {main_result.status_code}")
            current_source_data = _extract_response_source(response_payload["main_request"])

            for tool in _tool_entries(step.get("assertions")):
                current_source_data = execute_step_tool("assertions", tool, current_source_data)
                if assertion_errors:
                    break

            if assertion_errors:
                status = "failed"
                overall_status = "failed"
                hard_stop = True
                error_message = "；".join(assertion_errors)
                logs.append(f"步骤断言失败，已终止后续步骤: {error_message}")
            else:
                for tool in _tool_entries(step.get("post_processing")):
                    current_source_data = execute_step_tool("post_processing", tool, current_source_data)

                last_source_data = current_source_data
                status = "success"
        except Exception as exc:
            status = "failed"
            overall_status = "failed"
            hard_stop = True
            error_message = str(exc)
            logs.append(f"步骤失败: {error_message}")

        step_detail.update(
            {
                "status": status,
                "summary": error_message or "执行成功",
                "ended_at": _format_log_time(datetime.now()),
                "logs": logs,
                "error_message": error_message,
            }
        )
        response_payload["execution_log"] = step_detail
        if report_id:
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
        execution_steps.append(step_detail)
        if hard_stop:
            break

    passed_steps = sum(1 for item in step_summaries if item["status"] == "success")
    failed_steps = sum(1 for item in step_summaries if item["status"] == "failed")
    skipped_steps = sum(1 for item in step_summaries if item["status"] == "skipped")
    report_end = datetime.now()
    case_outputs = _resolve_case_outputs(case_item, runtime_variables)
    if not enabled_steps:
        overall_status = "success"
    message = (
        f"执行完成，成功 {passed_steps} 步，失败 {failed_steps} 步，跳过 {skipped_steps} 步"
        if enabled_steps
        else "当前用例没有可执行步骤"
    )
    execution_log = {
        "request_id": case_request_id,
        "case_id": case_item.get("id"),
        "case_name": case_item.get("name") or "未命名用例",
        "status": overall_status,
        "message": message,
        "started_at": _format_log_time(report_start),
        "ended_at": _format_log_time(report_end),
        "global_setup": {
            "logs": global_setup_logs,
            "login_request": global_login_result,
            "variable_changes": global_variable_changes,
            "context": global_context,
        },
        "steps": execution_steps,
        "case_outputs": _log_value(case_outputs),
        "final_variables": _log_value(runtime_variables),
    }
    execution_log["lines"] = _build_compact_execution_log_lines(execution_log)
    if report_id:
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
                        "report_type": "test_case",
                        "request_id": case_request_id,
                        "passed_steps": passed_steps,
                        "failed_steps": failed_steps,
                        "skipped_steps": skipped_steps,
                        "steps": step_summaries,
                        "global_setup": {
                            "logs": global_setup_logs,
                            "login_request": global_login_result,
                            "variable_changes": global_variable_changes,
                            "context": global_context,
                        },
                        "case_outputs": case_outputs,
                        "execution_log": execution_log,
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
        "execution_log": execution_log,
    }
