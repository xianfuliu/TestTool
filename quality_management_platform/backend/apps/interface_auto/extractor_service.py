from __future__ import annotations

import json
import re
from http.cookies import SimpleCookie
from typing import Any

from apps.common.request_execution import (
    build_response_extraction_source,
    extract_response_value,
    replace_template_text,
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _log_value(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return str(value)


def _string_source(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _normalise_extractor(row: Any) -> dict[str, Any]:
    item = _as_dict(row)
    extractor_type = str(item.get("type") or item.get("extractor_type") or "").strip().lower()
    source = str(item.get("from") or item.get("source") or "").strip()
    expr = str(item.get("expr") or item.get("expression") or item.get("path") or "").strip()
    variable = str(item.get("var") or item.get("variable") or item.get("name") or "").strip()

    if not extractor_type:
        if source in {"header", "headers", "response_headers"}:
            extractor_type = "header"
        elif source in {"cookie", "cookies"}:
            extractor_type = "cookie"
        elif expr in {"status_code", "$.status_code"} or source == "status_code":
            extractor_type = "status_code"
        elif item.get("regex"):
            extractor_type = "regex"
        else:
            extractor_type = "jsonpath"

    if not source:
        source = {
            "header": "response_headers",
            "cookie": "cookie",
            "status_code": "status_code",
        }.get(extractor_type, "body")

    return {
        **item,
        "type": extractor_type,
        "from": source,
        "expr": expr,
        "var": variable,
        "variable": variable,
        "path": expr,
    }


def _resolve_source_value(source_data: Any, source_name: str) -> Any:
    source = build_response_extraction_source(source_data)
    key = str(source_name or "body").strip()
    if key in {"header", "headers"}:
        key = "response_headers"
    if key in {"cookie", "cookies"}:
        return _parse_cookies(source.get("response_headers"))
    if key == "status_code":
        return source.get("status_code")
    if key in source:
        return source.get(key)
    return extract_response_value(source, key)


def _parse_cookies(headers: Any) -> dict[str, str]:
    cookies: dict[str, str] = {}
    header_map = _as_dict(headers)
    raw_values: list[Any] = []
    for key, value in header_map.items():
        if str(key).lower() == "set-cookie":
            raw_values.append(value)
    for raw_value in raw_values:
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        for item in values:
            cookie = SimpleCookie()
            try:
                cookie.load(str(item or ""))
            except Exception:
                continue
            for name, morsel in cookie.items():
                cookies[name] = morsel.value
    return cookies


def _extract_jsonpath(source_data: Any, extractor: dict[str, Any], variables: dict[str, Any]) -> tuple[bool, Any, str]:
    expr = replace_template_text(str(extractor.get("expr") or ""), variables, allow_legacy_placeholders=True).strip()
    if not expr:
        return False, None, "empty expression"
    source_name = str(extractor.get("from") or "body")
    if expr.startswith(("headers.", "response_headers.", "body.", "response_body.", "decrypted_body.", "status_code", "$.")):
        value = extract_response_value(source_data, expr)
    else:
        value = extract_response_value(_resolve_source_value(source_data, source_name), expr)
    return value is not None, value, ""


def _extract_regex(source_data: Any, extractor: dict[str, Any], variables: dict[str, Any]) -> tuple[bool, Any, str]:
    expr = replace_template_text(str(extractor.get("expr") or ""), variables, allow_legacy_placeholders=True).strip()
    if not expr:
        return False, None, "empty expression"
    source_value = _resolve_source_value(source_data, str(extractor.get("from") or "body"))
    try:
        match = re.search(expr, _string_source(source_value), flags=re.S)
    except re.error as exc:
        raise ValueError(str(exc)) from exc
    if not match:
        return False, None, ""
    group = extractor.get("group", 1)
    try:
        if isinstance(group, str) and not group.isdigit():
            return True, match.group(group), ""
        group_index = int(group)
        return True, match.group(group_index), ""
    except (IndexError, KeyError, ValueError):
        return True, match.group(0), ""


def _extract_header(source_data: Any, extractor: dict[str, Any], variables: dict[str, Any]) -> tuple[bool, Any, str]:
    expr = replace_template_text(str(extractor.get("expr") or ""), variables, allow_legacy_placeholders=True).strip()
    if not expr:
        return False, None, "empty header name"
    headers = _as_dict(_resolve_source_value(source_data, "response_headers"))
    value = headers.get(expr)
    if value is None:
        value = headers.get(expr.lower())
    return value is not None, value, ""


def _extract_cookie(source_data: Any, extractor: dict[str, Any], variables: dict[str, Any]) -> tuple[bool, Any, str]:
    expr = replace_template_text(str(extractor.get("expr") or ""), variables, allow_legacy_placeholders=True).strip()
    if not expr:
        return False, None, "empty cookie name"
    cookies = _as_dict(_resolve_source_value(source_data, "cookie"))
    value = cookies.get(expr)
    return value is not None, value, ""


def _extract_status_code(source_data: Any, _extractor: dict[str, Any], _variables: dict[str, Any]) -> tuple[bool, Any, str]:
    value = _resolve_source_value(source_data, "status_code")
    return value is not None, value, ""


def run_extractors(
    extractors: list[dict[str, Any]],
    source_data: Any,
    variables: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    extracted: dict[str, Any] = {}
    details: list[dict[str, Any]] = []
    handlers = {
        "jsonpath": _extract_jsonpath,
        "regex": _extract_regex,
        "header": _extract_header,
        "cookie": _extract_cookie,
        "status_code": _extract_status_code,
    }

    for raw_row in _as_list(extractors):
        extractor = _normalise_extractor(raw_row)
        variable_name = str(extractor.get("var") or extractor.get("variable") or "").strip()
        extractor_type = str(extractor.get("type") or "jsonpath").strip().lower()
        expr = str(extractor.get("expr") or "").strip()
        detail = {
            "type": extractor_type,
            "from": extractor.get("from") or "body",
            "expr": expr,
            "variable": variable_name,
            "var": variable_name,
            "path": expr,
            "matched": False,
            "value": None,
            "error_type": "",
            "message": "",
        }
        if not variable_name:
            detail.update(
                {
                    "error_type": "config_error",
                    "message": "variable name is empty",
                }
            )
            details.append(detail)
            continue
        handler = handlers.get(extractor_type)
        if not handler:
            detail.update(
                {
                    "error_type": "config_error",
                    "message": f"unsupported extractor type: {extractor_type}",
                }
            )
            details.append(detail)
            continue
        try:
            matched, value, message = handler(source_data, extractor, variables)
        except Exception as exc:
            detail.update(
                {
                    "error_type": "expression_error",
                    "message": str(exc),
                }
            )
            details.append(detail)
            continue
        if matched:
            extracted[variable_name] = value
            detail.update(
                {
                    "matched": True,
                    "value": _log_value(value),
                    "message": message or "matched",
                }
            )
        else:
            detail.update(
                {
                    "error_type": "not_found" if not message else "config_error",
                    "message": message or "path not matched",
                }
            )
        details.append(detail)

    variables.update(extracted)
    return extracted, details
