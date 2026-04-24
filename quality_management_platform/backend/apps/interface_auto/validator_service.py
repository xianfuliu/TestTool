from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.common.request_execution import (
    extract_response_value,
    replace_template_text,
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "yes", "y", "on"}:
            return True
        if text in {"false", "no", "n", "off"}:
            return False
    return None


def _log_value(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return str(value)


def resolve_validator_target(field: str, source_data: Any, variables: dict[str, Any]) -> Any:
    resolved_field = replace_template_text(str(field or ""), variables, allow_legacy_placeholders=True).strip()
    if not resolved_field:
        return None
    if resolved_field.startswith(("runtime_vars.", "variables.")):
        return variables.get(resolved_field.split(".", 1)[1])
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


def _assert_value(actual: Any, operator: str, expected: Any) -> tuple[bool, str]:
    actual_bool = _coerce_bool(actual)
    expected_bool = _coerce_bool(expected)
    actual_decimal = _coerce_decimal(actual)
    expected_decimal = _coerce_decimal(expected)
    if operator == "equal":
        if actual_bool is not None and expected_bool is not None:
            return actual_bool == expected_bool, ""
        if actual_decimal is not None and expected_decimal is not None:
            return actual_decimal == expected_decimal, ""
        return actual == expected, ""
    if operator == "not_equal":
        if actual_bool is not None and expected_bool is not None:
            return actual_bool != expected_bool, ""
        if actual_decimal is not None and expected_decimal is not None:
            return actual_decimal != expected_decimal, ""
        return actual != expected, ""
    if operator == "contains":
        return str(expected) in str(actual), ""
    if operator == "not_contains":
        return str(expected) not in str(actual), ""
    if operator == "greater" and actual_decimal is not None and expected_decimal is not None:
        return actual_decimal > expected_decimal, ""
    if operator == "less" and actual_decimal is not None and expected_decimal is not None:
        return actual_decimal < expected_decimal, ""
    if operator == "greater_equal" and actual_decimal is not None and expected_decimal is not None:
        return actual_decimal >= expected_decimal, ""
    if operator == "less_equal" and actual_decimal is not None and expected_decimal is not None:
        return actual_decimal <= expected_decimal, ""
    if operator == "exists":
        return actual is not None, ""
    if operator == "not_exists":
        return actual is None, ""
    if operator == "regex_match":
        try:
            return re.search(str(expected), "" if actual is None else str(actual)) is not None, ""
        except re.error as exc:
            return False, f"invalid regex: {exc}"
    return False, f"unsupported operator: {operator}"


def validate_assertions(
    assertions: list[dict[str, Any]],
    source_data: Any,
    variables: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for raw_row in _as_list(assertions):
        assertion = _as_dict(raw_row)
        field = str(assertion.get("field") or assertion.get("target") or "").strip()
        operator = str(assertion.get("operator") or "equal").strip()
        expected_raw = assertion.get("expected")
        expected = (
            replace_template_text(str(expected_raw), variables, allow_legacy_placeholders=True)
            if expected_raw is not None
            else ""
        )
        actual = resolve_validator_target(field, source_data, variables)
        passed, error_message = _assert_value(actual, operator, expected)
        if error_message:
            message = error_message
        elif passed:
            message = f"{field} {operator} passed"
        else:
            message = f"{field} expected {expected} but got {actual}"
        results.append(
            {
                "field": field,
                "operator": operator,
                "expected": expected,
                "actual": _log_value(actual),
                "passed": passed,
                "message": message,
            }
        )
    return results
