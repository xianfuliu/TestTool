from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.common.request_execution import EncryptionConfig, normalize_global_request_config
from apps.interface_auto.execution_service import ToolExecutionError, _execute_tool


_HOOK_SPEC_CACHE: dict[str, dict[str, Any]] = {}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _json_safe(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return str(value)


def _load_hook_spec_map(hooks_file: Path) -> dict[str, Any]:
    resolved = str(hooks_file.resolve())
    cached = _HOOK_SPEC_CACHE.get(resolved)
    if cached is not None:
        return cached
    payload = json.loads(hooks_file.read_text(encoding="utf-8"))
    hooks = _as_dict(payload.get("hooks"))
    _HOOK_SPEC_CACHE[resolved] = hooks
    return hooks


def _build_encryption(case_spec: dict[str, Any]) -> EncryptionConfig:
    return EncryptionConfig(
        enabled=bool(case_spec.get("enable_encryption")),
        encrypt_url=str(case_spec.get("encrypt_url") or ""),
        decrypt_url=str(case_spec.get("decrypt_url") or ""),
    )


def _variable_changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    all_keys = set(before.keys()) | set(after.keys())
    for key in sorted(all_keys):
        before_value = before.get(key)
        after_value = after.get(key)
        if before_value == after_value:
            continue
        changes[str(key)] = _json_safe(after_value)
    return changes


def execute_compiled_hook(hooks_file: str | Path, function_name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    hook_map = _load_hook_spec_map(Path(hooks_file))
    spec = _as_dict(hook_map.get(function_name))
    if not spec:
        raise ValueError(f"hook function not found: {function_name}")

    hook_context = _as_dict(context)
    variables = {str(key): value for key, value in _as_dict(hook_context.get("variables")).items()}
    variables_before = dict(variables)
    source_data = hook_context.get("source_data")
    environment = _as_dict(spec.get("environment"))
    case_spec = _as_dict(spec.get("case"))
    global_request_config = normalize_global_request_config(spec.get("global_request_config"))
    header_config = _as_dict(_as_dict(global_request_config).get("header_config"))
    encryption = _build_encryption(case_spec)
    tool = _as_dict(spec.get("tool"))

    try:
        result, next_source_data, logs = _execute_tool(
            tool,
            source_data,
            variables,
            environment,
            encryption,
            _as_dict(header_config.get("headers")),
        )
        status = str(result.get("status") or "success")
        message = str(result.get("error_message") or "")
        success = status == "success"
    except ToolExecutionError as exc:
        result = exc.result or {}
        next_source_data = exc.source_data
        logs = exc.logs or []
        status = "failed"
        message = str(exc)
        success = False
    except Exception as exc:  # pragma: no cover - defensive adapter
        result = {}
        next_source_data = source_data
        logs = []
        status = "failed"
        message = str(exc)
        success = False

    return {
        "status": status,
        "passed": success,
        "message": message or ("ok" if success else "hook failed"),
        "hook_id": spec.get("hook_id"),
        "function_name": function_name,
        "stage": spec.get("stage") or "",
        "tool_type": spec.get("tool_type") or "",
        "tool_name": spec.get("name") or tool.get("name") or tool.get("id") or "",
        "logs": [_json_safe(item) for item in _as_list(logs)],
        "result": _json_safe(result),
        "source_data": _json_safe(next_source_data),
        "variable_changes": _variable_changes(variables_before, variables),
        "current_variables": _json_safe(variables),
    }
