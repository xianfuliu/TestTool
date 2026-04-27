from __future__ import annotations

from copy import deepcopy
from typing import Any

from apps.common.http import get_int
from apps.interface_auto.compiler_service import compile_case_to_ir
from test_platform.db import fetch_all, fetch_one


SUITE_LOAD_IR_SCHEMA_VERSION = 1
SUPPORTED_VALIDATOR_OPERATORS = {
    "equal",
    "not_equal",
    "contains",
    "not_contains",
    "greater",
    "less",
    "greater_equal",
    "less_equal",
    "exists",
    "not_exists",
    "regex_match",
}
SUPPORTED_EXTRACTOR_TYPES = {
    "jsonpath",
    "regex",
    "header",
    "cookie",
    "status_code",
}
SUPPORTED_HOOK_TOOL_TYPES = {
    "http_request",
    "sql_tool",
    "python_script",
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_suite_row(suite_id: int) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT
            ts.*,
            p.name AS project_name,
            p.business_group_id,
            bg.name AS business_group_name
        FROM test_suites ts
        LEFT JOIN projects p ON p.id = ts.project_id
        LEFT JOIN business_groups bg ON bg.id = p.business_group_id
        WHERE ts.id = %s
        """,
        (suite_id,),
    )


def _suite_case_rows(suite_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT
            tsc.case_id,
            tsc.sort_order,
            tc.name,
            tc.description,
            tc.folder_id,
            tc.project_id,
            tc.environment_id,
            cf.name AS folder_name
        FROM test_suite_cases tsc
        INNER JOIN test_cases tc ON tc.id = tsc.case_id
        LEFT JOIN case_folders cf ON cf.id = tc.folder_id
        WHERE tsc.suite_id = %s
        ORDER BY tsc.sort_order ASC, tsc.id ASC
        """,
        (suite_id,),
    )


def normalize_load_profile(value: Any) -> dict[str, Any]:
    raw = _as_dict(value)
    threads = max(1, _int_value(raw.get("threads"), 1))
    ramp_up_seconds = max(1, _int_value(raw.get("ramp_up_seconds"), 1))
    loops = max(1, _int_value(raw.get("loops"), 1))
    duration_seconds = max(0, _int_value(raw.get("duration_seconds"), 0))
    target_tps = max(0.0, _float_value(raw.get("target_tps"), 0.0))
    return {
        "threads": threads,
        "ramp_up_seconds": ramp_up_seconds,
        "loops": loops,
        "duration_seconds": duration_seconds,
        "target_tps": target_tps,
    }


def _tool_type(tool: Any) -> str:
    item = _as_dict(tool)
    return str(item.get("tool_type") or item.get("type") or "").strip().lower()


def _legacy_tool_assertions(tool: Any) -> list[dict[str, Any]]:
    item = _as_dict(tool)
    direct_rows = _as_list(item.get("assertions"))
    if direct_rows:
        return [_as_dict(row) for row in direct_rows if isinstance(row, dict)]
    config = _as_dict(item.get("config"))
    return [_as_dict(row) for row in _as_list(config.get("assertions")) if isinstance(row, dict)]


def _validator_from_legacy_assertion(row: Any) -> dict[str, Any]:
    item = _as_dict(row)
    return {
        "field": str(item.get("field") or item.get("target") or "").strip(),
        "operator": str(item.get("operator") or "equal").strip().lower(),
        "expected": item.get("expected"),
    }


def _hook_function_name(case_id: Any, step_map: dict[str, Any], stage: str, index: int) -> str:
    step_order = _int_value(step_map.get("step_order"), 0)
    step_id = str(step_map.get("step_id") or step_map.get("id") or step_order or "step")
    safe_step_id = "".join(ch if ch.isalnum() else "_" for ch in step_id).strip("_") or "step"
    return f"{stage}_case_{case_id}_step_{step_order or safe_step_id}_hook_{index}"


def _convert_tools_to_hooks(
    tools: list[Any],
    *,
    case_id: Any,
    step_map: dict[str, Any],
    stage: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], list[str]]:
    hooks: list[dict[str, Any]] = []
    remaining_tools: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []
    step_name = str(step_map.get("name") or step_map.get("step_id") or "unnamed-step")

    for index, tool in enumerate(_as_list(tools), start=1):
        tool_map = _as_dict(tool)
        if tool_map.get("enabled") is False:
            continue
        tool_type = _tool_type(tool_map)
        if tool_type not in SUPPORTED_HOOK_TOOL_TYPES:
            remaining_tools.append(tool_map)
            continue
        function_name = _hook_function_name(case_id, step_map, stage, index)
        hooks.append(
            {
                "hook_id": f"{function_name}",
                "function_name": function_name,
                "stage": stage,
                "tool_type": tool_type,
                "name": str(tool_map.get("name") or tool_map.get("id") or tool_type),
                "tool": deepcopy(tool_map),
            }
        )
    if hooks:
        warnings.append(
            f"case {case_id} step {step_name} converted {len(hooks)} {stage} tool(s) to httprunner hooks"
        )
        warnings.append(
            f"case {case_id} step {step_name} {stage} hooks run through Python bridge during JMeter execution"
        )
    return hooks, remaining_tools, warnings, errors


def _normalize_case_ir_for_jmeter(case_ir: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    normalized = deepcopy(case_ir)
    warnings: list[str] = []
    errors: list[str] = []
    case_info = _as_dict(normalized.get("case"))

    for step in _as_list(normalized.get("steps")):
        step_map = _as_dict(step)
        step_name = str(step_map.get("name") or step_map.get("step_id") or "unnamed-step")
        base_validators = [_as_dict(row) for row in _as_list(step_map.get("validators")) if isinstance(row, dict)]
        converted_validators = list(base_validators)
        remaining_assert_tools: list[dict[str, Any]] = []
        converted_tool_count = 0
        setup_hooks, remaining_pre_tools, setup_warnings, setup_errors = _convert_tools_to_hooks(
            _as_list(step_map.get("pre_tools")),
            case_id=case_info.get("id"),
            step_map=step_map,
            stage="setup",
        )
        teardown_hooks, remaining_post_tools, teardown_warnings, teardown_errors = _convert_tools_to_hooks(
            _as_list(step_map.get("post_tools")),
            case_id=case_info.get("id"),
            step_map=step_map,
            stage="teardown",
        )
        warnings.extend(setup_warnings)
        warnings.extend(teardown_warnings)
        errors.extend(setup_errors)
        errors.extend(teardown_errors)

        for tool in _as_list(step_map.get("assert_tools")):
            tool_map = _as_dict(tool)
            if tool_map.get("enabled") is False:
                continue
            tool_type = _tool_type(tool_map)
            if tool_type != "assertion":
                remaining_assert_tools.append(tool_map)
                continue
            legacy_assertions = _legacy_tool_assertions(tool_map)
            if not legacy_assertions:
                errors.append(
                    f"step {step_name} legacy assertion tool {tool_map.get('name') or tool_map.get('id') or '-'} has no assertions"
                )
                continue
            converted_tool_count += 1
            for raw_assertion in legacy_assertions:
                validator = _validator_from_legacy_assertion(raw_assertion)
                field = validator["field"]
                operator = validator["operator"]
                if not field:
                    errors.append(f"step {step_name} contains a legacy assertion without field")
                    continue
                if operator not in SUPPORTED_VALIDATOR_OPERATORS:
                    errors.append(
                        f"step {step_name} legacy assertion {field} uses unsupported operator {operator}"
                    )
                    continue
                converted_validators.append(validator)

        step_map["validators"] = converted_validators
        step_map["assert_tools"] = remaining_assert_tools
        step_map["setup_hooks"] = setup_hooks
        step_map["teardown_hooks"] = teardown_hooks
        step_map["pre_tools"] = remaining_pre_tools
        step_map["post_tools"] = remaining_post_tools
        if converted_tool_count:
            warnings.append(
                f"case {case_info.get('id')} step {step_name} converted {converted_tool_count} legacy assertion tool(s) to validators"
            )

    return normalized, warnings, errors


def _validate_case_ir(case_ir: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    case_info = _as_dict(case_ir.get("case"))
    global_config = _as_dict(case_ir.get("global_request_config"))
    login_request = _as_dict(global_config.get("login_request"))
    if case_info.get("enable_encryption"):
        errors.append(f"case {case_info.get('id')} enabled encryption, which is not supported in JMeter compilation")
    if login_request.get("use_global_encryption"):
        errors.append(
            f"case {case_info.get('id')} login_request.use_global_encryption is not supported in JMeter compilation"
        )
    if _float_value(normalize_load_profile({}).get("target_tps"), 0.0):
        warnings.append("target_tps is currently not translated into a JMeter timer")
    for step in _as_list(case_ir.get("steps")):
        step_map = _as_dict(step)
        step_name = str(step_map.get("name") or step_map.get("step_id") or "unnamed-step")
        if step_map.get("enable_encryption") or _as_dict(step_map.get("flags")).get("enable_encryption"):
            errors.append(f"step {step_name} enabled encryption, which is not supported in JMeter compilation")
        if _as_list(step_map.get("pre_tools")):
            errors.append(f"step {step_name} contains pre_tools, which are not supported in JMeter compilation")
        if _as_list(step_map.get("assert_tools")):
            errors.append(f"step {step_name} contains assert_tools, which are not supported in JMeter compilation")
        if _as_list(step_map.get("post_tools")):
            errors.append(f"step {step_name} contains post_tools, which are not supported in JMeter compilation")
        for extractor in _as_list(step_map.get("extractors")):
            extractor_map = _as_dict(extractor)
            extractor_type = str(extractor_map.get("type") or "jsonpath").strip().lower()
            variable_name = str(extractor_map.get("var") or extractor_map.get("variable") or "").strip()
            expr = str(extractor_map.get("expr") or extractor_map.get("path") or "").strip()
            if extractor_type not in SUPPORTED_EXTRACTOR_TYPES:
                errors.append(
                    f"step {step_name} extractor {variable_name or expr or '-'} uses unsupported type {extractor_type}"
                )
            if not variable_name:
                errors.append(f"step {step_name} contains an extractor without target variable")
            if extractor_type != "status_code" and not expr:
                errors.append(f"step {step_name} extractor {variable_name or '-'} has empty expression")
        for validator in _as_list(step_map.get("validators")):
            validator_map = _as_dict(validator)
            field = str(validator_map.get("field") or validator_map.get("target") or "").strip()
            operator = str(validator_map.get("operator") or "equal").strip().lower()
            if not field:
                errors.append(f"step {step_name} contains a validator without field")
            if operator not in SUPPORTED_VALIDATOR_OPERATORS:
                errors.append(f"step {step_name} validator {field or '-'} uses unsupported operator {operator}")
        request = _as_dict(step_map.get("request"))
        if not request.get("url"):
            errors.append(f"step {step_name} has no request url after compilation")
    return errors, warnings


def compile_suite_to_load_ir(
    suite_id: int,
    *,
    environment_id: int | None = None,
    load_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    suite_row = _load_suite_row(suite_id)
    if not suite_row:
        raise ValueError("测试集不存在")
    case_rows = _suite_case_rows(suite_id)
    if not case_rows:
        raise ValueError("测试集下没有测试用例")

    cases: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []
    for row in case_rows:
        case_id = get_int(row.get("case_id"))
        if not case_id:
            continue
        case_ir = compile_case_to_ir(case_id, environment_id=environment_id)
        case_ir, normalize_warnings, normalize_errors = _normalize_case_ir_for_jmeter(case_ir)
        warnings.extend(normalize_warnings)
        errors.extend(normalize_errors)
        case_errors, case_warnings = _validate_case_ir(case_ir)
        errors.extend(case_errors)
        warnings.extend(case_warnings)
        cases.append(
            {
                "order": _int_value(row.get("sort_order"), len(cases) + 1) or (len(cases) + 1),
                "case_id": case_id,
                "case_name": str(row.get("name") or _as_dict(case_ir.get("case")).get("name") or ""),
                "folder_id": row.get("folder_id"),
                "folder_name": row.get("folder_name") or "",
                "case_ir": case_ir,
            }
        )
    if errors:
        raise ValueError("；".join(errors))

    profile = normalize_load_profile(load_profile)
    if profile.get("target_tps"):
        warnings.append("target_tps 尚未转换为 JMeter Timer，当前生成的 JMX 不会限流")

    return {
        "schema_version": SUITE_LOAD_IR_SCHEMA_VERSION,
        "suite": {
            "id": suite_row.get("id"),
            "name": suite_row.get("name") or "",
            "description": suite_row.get("description") or "",
            "project_id": suite_row.get("project_id"),
            "project_name": suite_row.get("project_name") or "",
            "business_group_id": suite_row.get("business_group_id"),
            "business_group_name": suite_row.get("business_group_name") or "",
            "environment_override_id": environment_id,
            "case_count": len(cases),
        },
        "load_profile": profile,
        "cases": cases,
        "warnings": warnings,
    }
