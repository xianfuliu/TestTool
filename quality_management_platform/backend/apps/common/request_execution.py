from __future__ import annotations

import json
import random
import re
import string
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable
from urllib.parse import urljoin

import requests


_DOLLAR_PLACEHOLDER_PATTERN = re.compile(r"\$\{([^}]+)\}")
_LEGACY_PLACEHOLDER_PATTERN = re.compile(r"\{(\w+)\}")
_DOLLAR_ARRAY_INDEX_PATTERN = re.compile(r"\[\$\{([^}]+)\}\]")
_LEGACY_ARRAY_INDEX_PATTERN = re.compile(r"\[(\{(\w+)\})\]")
_DOLLAR_DATETIME_PATTERN = re.compile(r"\$\{dateTime(?::([^}]+))?\}")
_LEGACY_DATETIME_PATTERN = re.compile(r"\{dateTime(?::([^}]+))?\}")
_DOLLAR_DATE_PATTERN = re.compile(r"\$\{date(?::([^}]+))?\}")
_LEGACY_DATE_PATTERN = re.compile(r"\{date(?::([^}]+))?\}")
_DOLLAR_TIME_PATTERN = re.compile(r"\$\{time\}")
_LEGACY_TIME_PATTERN = re.compile(r"\{time\}")
_DOLLAR_RANDOM_PATTERN = re.compile(r"\$\{random:(digits|string|alphanum):(\d+)\}")
_LEGACY_RANDOM_PATTERN = re.compile(r"\{random:(digits|string|alphanum):(\d+)\}")
_SQL_DOLLAR_QUOTED_SINGLE_PATTERN = re.compile(r"'(\$\{[^}]+\})'")
_SQL_DOLLAR_QUOTED_DOUBLE_PATTERN = re.compile(r'"(\$\{[^}]+\})"')
_SQL_LEGACY_QUOTED_SINGLE_PATTERN = re.compile(r"'(\{\w+\})'")
_SQL_LEGACY_QUOTED_DOUBLE_PATTERN = re.compile(r'"(\{\w+\})"')


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def json_loads(value: Any, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _stringify_placeholder_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json_dumps(value)
    return str(value)


def _replace_array_index_tokens(
    text: str,
    variables: dict[str, Any],
    allow_legacy_placeholders: bool = True,
) -> str:
    def replace_dollar(match: re.Match[str]) -> str:
        variable_name = match.group(1).strip()
        value = variables.get(variable_name)
        try:
            index = int(str(value)) - 1
        except (TypeError, ValueError):
            index = 0
        return f"[{max(index, 0)}]"

    processed = _DOLLAR_ARRAY_INDEX_PATTERN.sub(replace_dollar, text)
    if not allow_legacy_placeholders:
        return processed

    def replace_legacy(match: re.Match[str]) -> str:
        variable_name = match.group(2).strip()
        value = variables.get(variable_name)
        try:
            index = int(str(value)) - 1
        except (TypeError, ValueError):
            index = 0
        return f"[{max(index, 0)}]"

    return _LEGACY_ARRAY_INDEX_PATTERN.sub(replace_legacy, processed)


def _apply_special_tokens(text: str, allow_legacy_placeholders: bool = True) -> str:
    now = datetime.now()

    def replace_datetime(match: re.Match[str]) -> str:
        return now.strftime(match.group(1) or "%Y%m%d%H%M%S")

    def replace_date(match: re.Match[str]) -> str:
        return now.strftime(match.group(1) or "%Y%m%d")

    def replace_time(_match: re.Match[str]) -> str:
        return now.strftime("%H%M%S")

    def replace_random(match: re.Match[str]) -> str:
        kind = match.group(1)
        length = int(match.group(2))
        charset_map = {
            "digits": string.digits,
            "string": string.ascii_letters,
            "alphanum": string.ascii_letters + string.digits,
        }
        return "".join(random.choices(charset_map[kind], k=length))

    processed = _DOLLAR_DATETIME_PATTERN.sub(replace_datetime, text)
    processed = _DOLLAR_DATE_PATTERN.sub(replace_date, processed)
    processed = _DOLLAR_TIME_PATTERN.sub(replace_time, processed)
    processed = _DOLLAR_RANDOM_PATTERN.sub(replace_random, processed)

    if not allow_legacy_placeholders:
        return processed

    processed = _LEGACY_DATETIME_PATTERN.sub(replace_datetime, processed)
    processed = _LEGACY_DATE_PATTERN.sub(replace_date, processed)
    processed = _LEGACY_TIME_PATTERN.sub(replace_time, processed)
    return _LEGACY_RANDOM_PATTERN.sub(replace_random, processed)


def replace_template_text(
    text: str,
    variables: dict[str, Any],
    allow_legacy_placeholders: bool = True,
) -> str:
    if not isinstance(text, str):
        return text

    processed = _replace_array_index_tokens(
        text,
        variables,
        allow_legacy_placeholders=allow_legacy_placeholders,
    )
    processed = _apply_special_tokens(
        processed,
        allow_legacy_placeholders=allow_legacy_placeholders,
    )

    def replace_dollar(match: re.Match[str]) -> str:
        variable_name = match.group(1).strip()
        value = variables.get(variable_name)
        if value in (None, "") and variable_name.endswith(("_index", "_idx", "index", "idx")):
            return "0"
        return _stringify_placeholder_value(value)

    processed = _DOLLAR_PLACEHOLDER_PATTERN.sub(replace_dollar, processed)
    if not allow_legacy_placeholders:
        return processed

    def replace_legacy(match: re.Match[str]) -> str:
        variable_name = match.group(1).strip()
        value = variables.get(variable_name)
        if value in (None, "") and variable_name.endswith(("_index", "_idx", "index", "idx")):
            return "0"
        return _stringify_placeholder_value(value)

    return _LEGACY_PLACEHOLDER_PATTERN.sub(replace_legacy, processed)


def replace_template_data(
    value: Any,
    variables: dict[str, Any],
    allow_legacy_placeholders: bool = True,
) -> Any:
    if isinstance(value, str):
        return replace_template_text(
            value,
            variables,
            allow_legacy_placeholders=allow_legacy_placeholders,
        )
    if isinstance(value, dict):
        return {
            replace_template_text(
                str(key),
                variables,
                allow_legacy_placeholders=allow_legacy_placeholders,
            ): replace_template_data(
                item,
                variables,
                allow_legacy_placeholders=allow_legacy_placeholders,
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            replace_template_data(
                item,
                variables,
                allow_legacy_placeholders=allow_legacy_placeholders,
            )
            for item in value
        ]
    return value


def extract_template_dependencies(
    template: str,
    allow_legacy_placeholders: bool = True,
) -> list[str]:
    dependencies = [match.group(1).strip() for match in _DOLLAR_PLACEHOLDER_PATTERN.finditer(template or "")]
    if allow_legacy_placeholders:
        dependencies.extend(match.group(1).strip() for match in _LEGACY_PLACEHOLDER_PATTERN.finditer(template or ""))
    return list(dict.fromkeys(dependencies))


def _normalize_relative_url(base_url: str, url: str) -> str:
    if not base_url or not url:
        return url
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        return url
    if not base_url.endswith("/"):
        base_url = f"{base_url}/"
    if url.startswith("/"):
        url = url[1:]
    return urljoin(base_url, url)


def _merge_headers(global_headers: dict[str, Any], request_headers: dict[str, Any]) -> dict[str, Any]:
    merged = dict(request_headers or {})
    for key, value in (global_headers or {}).items():
        merged[str(key)] = value
    return merged


def _convert_sql_template(sql_text: str, allow_legacy_placeholders: bool = True) -> str:
    converted = _SQL_DOLLAR_QUOTED_SINGLE_PATTERN.sub(r"\1", sql_text)
    converted = _SQL_DOLLAR_QUOTED_DOUBLE_PATTERN.sub(r"\1", converted)
    if not allow_legacy_placeholders:
        return converted
    converted = _SQL_LEGACY_QUOTED_SINGLE_PATTERN.sub(r"\1", converted)
    return _SQL_LEGACY_QUOTED_DOUBLE_PATTERN.sub(r"\1", converted)


def render_sql_template(
    sql_text: str,
    variables: dict[str, Any],
    allow_legacy_placeholders: bool = True,
) -> str:
    converted = _convert_sql_template(sql_text, allow_legacy_placeholders=allow_legacy_placeholders)

    def replace_dollar(match: re.Match[str]) -> str:
        variable_name = match.group(1).strip()
        if variable_name not in variables:
            return match.group(0)
        value = variables.get(variable_name)
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float, Decimal)):
            return str(value)
        if isinstance(value, (dict, list)):
            return "'" + json_dumps(value).replace("'", "''") + "'"
        return "'" + str(value).replace("'", "''") + "'"

    rendered = _DOLLAR_PLACEHOLDER_PATTERN.sub(replace_dollar, converted)
    if not allow_legacy_placeholders:
        return rendered
    return _LEGACY_PLACEHOLDER_PATTERN.sub(replace_dollar, rendered)


def _parse_path_tokens(path: str) -> list[Any]:
    cleaned = path.strip()
    if cleaned.startswith("$."):
        cleaned = cleaned[2:]
    elif cleaned.startswith("$"):
        cleaned = cleaned[1:]
    tokens: list[Any] = []
    for part in cleaned.split("."):
        if not part:
            continue
        position = 0
        while position < len(part):
            bracket_start = part.find("[", position)
            if bracket_start < 0:
                tokens.append(part[position:])
                break
            if bracket_start > position:
                tokens.append(part[position:bracket_start])
            bracket_end = part.find("]", bracket_start)
            if bracket_end < 0:
                break
            index_text = part[bracket_start + 1 : bracket_end]
            if index_text.isdigit():
                tokens.append(int(index_text))
            position = bracket_end + 1
    return tokens


def extract_simple_path(data: Any, path: str) -> Any:
    current = data
    for token in _parse_path_tokens(path):
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                return None
            current = current[token]
            continue
        if isinstance(current, dict):
            if token not in current:
                return None
            current = current[token]
            continue
        return None
    return current


def extract_mapping_value(data: Any, path: str) -> Any:
    if "|" in path:
        first_path, nested_path = [part.strip() for part in path.split("|", 1)]
        base_value = extract_simple_path(data, first_path)
        if isinstance(base_value, str):
            try:
                base_value = json.loads(base_value)
            except json.JSONDecodeError:
                return None
        return extract_simple_path(base_value, nested_path)
    return extract_simple_path(data, path)


def merge_header_maps(*header_groups: dict[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for headers in header_groups:
        for key, value in _as_dict(headers).items():
            key_text = str(key).strip()
            if key_text:
                merged[key_text] = value
    return merged


def default_global_request_config() -> dict[str, Any]:
    return {
        "login_request": {
            "enabled": False,
            "protocol": "http",
            "method": "POST",
            "url": "",
            "headers": {
                "Content-Type": "application/json",
            },
            "params": {},
            "body": {},
            "timeout": 30,
            "retry_enabled": False,
            "retry_count": 0,
            "extractions": [],
        },
        "header_config": {
            "enabled": False,
            "headers": {},
        },
    }


def _normalise_extraction_rows(value: Any) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw_row in _as_list(value):
        row = _as_dict(raw_row)
        variable = str(row.get("variable") or row.get("name") or "").strip()
        path = str(row.get("path") or row.get("source") or "").strip()
        if variable or path:
            rows.append(
                {
                    "variable": variable,
                    "path": path,
                }
            )
    return rows


def normalize_global_request_config(
    value: Any,
    legacy_headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = default_global_request_config()
    raw = _as_dict(json_loads(value, {}))

    raw_login = _as_dict(raw.get("login_request") or raw.get("login"))
    raw_login_request = _as_dict(raw_login.get("request"))
    login_headers = _as_dict(raw_login.get("headers"))
    if raw_login_request and not login_headers:
        login_headers = _as_dict(raw_login_request.get("headers"))
    login_params = raw_login.get("params")
    if raw_login_request and login_params in (None, ""):
        login_params = raw_login_request.get("params")
    login_body = raw_login.get("body")
    if raw_login_request and login_body in (None, ""):
        login_body = raw_login_request.get("body")

    login_request = {
        **base["login_request"],
        "enabled": bool(raw_login.get("enabled", base["login_request"]["enabled"])),
        "protocol": str(
            raw_login.get("protocol")
            or raw_login_request.get("protocol")
            or base["login_request"]["protocol"]
        ).strip()
        or "http",
        "method": str(
            raw_login.get("method")
            or raw_login_request.get("method")
            or base["login_request"]["method"]
        ).strip()
        or "POST",
        "url": str(
            raw_login.get("url")
            or raw_login_request.get("url")
            or base["login_request"]["url"]
        ).strip(),
        "headers": login_headers or dict(base["login_request"]["headers"]),
        "params": login_params if login_params not in (None, "") else {},
        "body": login_body if login_body not in (None, "") else {},
        "timeout": int(
            raw_login.get("timeout")
            or raw_login_request.get("timeout")
            or base["login_request"]["timeout"]
            or 30
        ),
        "retry_enabled": bool(
            raw_login.get("retry_enabled")
            or raw_login_request.get("retry_enabled")
            or False
        ),
        "retry_count": int(
            raw_login.get("retry_count")
            or raw_login_request.get("retry_count")
            or 0
        ),
        "extractions": _normalise_extraction_rows(
            raw_login.get("extractions") or raw_login.get("extracts"),
        ),
    }

    raw_header_config = _as_dict(
        raw.get("header_config")
        or raw.get("headers")
        or raw.get("global_headers")
    )
    header_values = _as_dict(raw_header_config.get("headers") or raw_header_config.get("values"))
    if not header_values and not {"enabled", "headers", "values"} & set(raw_header_config.keys()):
        header_values = raw_header_config
    if not header_values:
        header_values = _as_dict(legacy_headers)

    header_config = {
        **base["header_config"],
        "enabled": bool(raw_header_config.get("enabled", bool(header_values))),
        "headers": header_values,
    }

    return {
        "login_request": login_request,
        "header_config": header_config,
    }


def _parse_response_body(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _normalize_response_headers(headers: Any) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in _as_dict(headers).items():
        key_text = str(key)
        normalized[key_text] = value
        lower_key = key_text.lower()
        if lower_key not in normalized:
            normalized[lower_key] = value
    return normalized


def build_response_extraction_source(data: Any) -> dict[str, Any]:
    if isinstance(data, RequestExecutionResult):
        headers = data.headers
        body = data.body
        decrypted_body = data.decrypted_body
        raw_body = data.raw_body
        status_code = data.status_code
    elif isinstance(data, dict) and (
        "headers" in data
        or "body" in data
        or "decrypted_body" in data
        or "raw_body" in data
        or "status_code" in data
    ):
        headers = data.get("headers")
        body = data.get("body")
        decrypted_body = data.get("decrypted_body")
        raw_body = data.get("raw_body")
        status_code = data.get("status_code")
    else:
        parsed = _parse_response_body(data)
        return {
            "headers": {},
            "response_headers": {},
            "body": parsed,
            "response_body": parsed,
            "decrypted_body": parsed,
            "response_decrypted_body": parsed,
            "raw_body": data,
            "status_code": None,
        }

    parsed_body = _parse_response_body(body)
    parsed_decrypted_body = _parse_response_body(decrypted_body)
    preferred_body = (
        parsed_decrypted_body
        if parsed_decrypted_body not in (None, "")
        else parsed_body
    )
    normalized_headers = _normalize_response_headers(headers)

    return {
        "headers": normalized_headers,
        "response_headers": normalized_headers,
        "body": preferred_body,
        "response_body": preferred_body,
        "decrypted_body": parsed_decrypted_body,
        "response_decrypted_body": parsed_decrypted_body,
        "raw_body": raw_body,
        "status_code": status_code,
    }


def extract_response_value(data: Any, path: str) -> Any:
    clean_path = str(path or "").strip()
    if not clean_path:
        return None

    extraction_source = build_response_extraction_source(data)
    explicit_prefixes = (
        "headers",
        "$.headers",
        "response_headers",
        "$.response_headers",
        "body",
        "$.body",
        "response_body",
        "$.response_body",
        "decrypted_body",
        "$.decrypted_body",
        "response_decrypted_body",
        "$.response_decrypted_body",
        "raw_body",
        "$.raw_body",
        "status_code",
        "$.status_code",
    )
    if clean_path.startswith(explicit_prefixes):
        return extract_mapping_value(extraction_source, clean_path)

    for candidate in (
        extraction_source.get("body"),
        extraction_source.get("decrypted_body"),
    ):
        if candidate in (None, ""):
            continue
        value = extract_mapping_value(candidate, clean_path)
        if value is not None:
            return value
    return extract_mapping_value(extraction_source, clean_path)


@dataclass
class EncryptionConfig:
    enabled: bool = False
    encrypt_url: str = ""
    decrypt_url: str = ""


@dataclass
class RequestDefinition:
    protocol: str = "http"
    url: str = ""
    method: str = "GET"
    headers: dict[str, Any] = field(default_factory=dict)
    params: Any = field(default_factory=dict)
    body: Any = None
    timeout: int = 30
    retry_enabled: bool = False
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PreparedRequest:
    protocol: str
    url: str
    method: str
    headers: dict[str, Any]
    params: Any
    body: Any
    timeout: int
    retry_enabled: bool
    retry_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestExecutionContext:
    request_id: str = ""
    variables: dict[str, Any] = field(default_factory=dict)
    base_url: str = ""
    global_headers: dict[str, Any] = field(default_factory=dict)
    encryption: EncryptionConfig = field(default_factory=EncryptionConfig)
    allow_legacy_placeholders: bool = True


@dataclass
class RequestExecutionResult:
    request: dict[str, Any]
    status_code: int
    headers: dict[str, Any]
    body: Any
    raw_body: str
    decrypted_body: Any
    duration_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


ProtocolExecutor = Callable[[PreparedRequest, RequestExecutionContext], RequestExecutionResult]

_PROTOCOL_EXECUTORS: dict[str, ProtocolExecutor] = {}


def register_protocol_executor(protocol: str, executor: ProtocolExecutor) -> None:
    _PROTOCOL_EXECUTORS[str(protocol or "http").strip().lower()] = executor


def prepare_request_definition(
    request_definition: RequestDefinition,
    context: RequestExecutionContext,
) -> PreparedRequest:
    allow_legacy_placeholders = context.allow_legacy_placeholders
    rendered_url = replace_template_text(
        request_definition.url or "",
        context.variables,
        allow_legacy_placeholders=allow_legacy_placeholders,
    )
    rendered_base_url = replace_template_text(
        context.base_url or "",
        context.variables,
        allow_legacy_placeholders=allow_legacy_placeholders,
    )
    rendered_headers = replace_template_data(
        request_definition.headers or {},
        context.variables,
        allow_legacy_placeholders=allow_legacy_placeholders,
    )
    rendered_global_headers = replace_template_data(
        context.global_headers or {},
        context.variables,
        allow_legacy_placeholders=allow_legacy_placeholders,
    )
    rendered_params = replace_template_data(
        request_definition.params,
        context.variables,
        allow_legacy_placeholders=allow_legacy_placeholders,
    )
    rendered_body = replace_template_data(
        request_definition.body,
        context.variables,
        allow_legacy_placeholders=allow_legacy_placeholders,
    )

    return PreparedRequest(
        protocol=str(request_definition.protocol or "http").strip().lower() or "http",
        url=_normalize_relative_url(rendered_base_url, rendered_url),
        method=str(request_definition.method or "GET").upper(),
        headers=_merge_headers(rendered_global_headers, rendered_headers),
        params=rendered_params,
        body=rendered_body,
        timeout=max(1, int(request_definition.timeout or 30)),
        retry_enabled=bool(request_definition.retry_enabled),
        retry_count=max(0, int(request_definition.retry_count or 0)),
        metadata=dict(request_definition.metadata or {}),
    )


def _request_payload_for_encryption(request: PreparedRequest) -> Any:
    if request.body not in (None, "", {}, []):
        return request.body
    return request.params


def _encode_request_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return payload


def _perform_http_request(
    request: PreparedRequest,
    context: RequestExecutionContext,
) -> RequestExecutionResult:
    if not request.url.strip():
        raise ValueError("请求 URL 不能为空")

    start = time.perf_counter()
    method = request.method.upper()
    encryption = context.encryption
    encrypted_payload: Any = None

    if encryption.enabled and encryption.encrypt_url:
        encrypt_response = requests.post(
            encryption.encrypt_url,
            data=_encode_request_payload(
                json_dumps(_request_payload_for_encryption(request))
            ),
            headers=request.headers,
            timeout=request.timeout,
        )
        if encrypt_response.status_code != 200:
            raise ValueError(f"加密接口调用失败: {encrypt_response.status_code}")
        encrypted_payload = encrypt_response.text

    request_kwargs: dict[str, Any] = {
        "headers": request.headers,
        "timeout": request.timeout,
    }
    if request.params not in (None, "", {}, []):
        request_kwargs["params"] = encrypted_payload if method == "GET" and encrypted_payload else request.params

    if method == "GET":
        if "params" not in request_kwargs and encrypted_payload is not None:
            request_kwargs["params"] = encrypted_payload
        response = requests.get(request.url, **request_kwargs)
    else:
        if encrypted_payload is not None:
            request_kwargs["data"] = _encode_request_payload(encrypted_payload)
        else:
            if isinstance(request.body, (dict, list)):
                request_kwargs["json"] = request.body
            elif request.body not in (None, ""):
                request_kwargs["data"] = _encode_request_payload(request.body)
        response = requests.request(method, request.url, **request_kwargs)

    raw_body = response.text
    decrypted_body: Any = raw_body
    if encryption.enabled and encryption.decrypt_url and response.status_code == 200:
        decrypt_response = requests.post(
            encryption.decrypt_url,
            data=_encode_request_payload(response.text),
            headers=request.headers,
            timeout=request.timeout,
        )
        if decrypt_response.status_code != 200:
            raise ValueError(f"解密接口调用失败: {decrypt_response.status_code}")
        try:
            decrypt_json = decrypt_response.json()
            decrypted_body = (
                decrypt_json.get("decrypted_data")
                or decrypt_json.get("data")
                or decrypt_json
            )
        except Exception:
            decrypted_body = decrypt_response.text

    try:
        parsed_body = response.json()
    except Exception:
        parsed_body = raw_body

    return RequestExecutionResult(
        request={
            "protocol": request.protocol,
            "url": request.url,
            "method": method,
            "headers": request.headers,
            "params": request.params,
            "body": request.body,
        },
        status_code=response.status_code,
        headers=dict(response.headers),
        body=parsed_body,
        raw_body=raw_body,
        decrypted_body=decrypted_body,
        duration_ms=round((time.perf_counter() - start) * 1000, 2),
        metadata=dict(request.metadata or {}),
    )


def execute_request_definition(
    request_definition: RequestDefinition,
    context: RequestExecutionContext,
) -> RequestExecutionResult:
    prepared = prepare_request_definition(request_definition, context)
    executor = _PROTOCOL_EXECUTORS.get(prepared.protocol)
    if executor is None:
        raise ValueError(f"暂不支持 {prepared.protocol} 协议，请扩展对应执行器后再使用")

    attempts = 1 + (prepared.retry_count if prepared.retry_enabled else 0)
    last_result: RequestExecutionResult | None = None
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            last_result = executor(prepared, context)
            if last_result.status_code >= 500 and attempt < attempts - 1:
                continue
            return last_result
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= attempts - 1:
                break
        except ValueError as exc:
            last_error = exc
            if attempt >= attempts - 1:
                break

    if last_result is not None:
        return last_result
    if last_error is not None:
        raise ValueError(f"请求执行失败: {last_error}") from last_error
    raise ValueError("请求执行失败")


def resolve_global_request_runtime(
    global_request_config: Any,
    *,
    request_id: str,
    variables: dict[str, Any],
    base_url: str = "",
    base_headers: dict[str, Any] | None = None,
    encryption: EncryptionConfig | None = None,
    allow_legacy_placeholders: bool = True,
) -> dict[str, Any]:
    normalized_config = normalize_global_request_config(
        global_request_config,
        legacy_headers=base_headers,
    )
    runtime_variables = dict(variables or {})
    logs: list[str] = []
    login_summary: dict[str, Any] | None = None
    resolved_headers: dict[str, Any] = {}

    login_request = _as_dict(normalized_config.get("login_request"))
    if login_request.get("enabled"):
        login_result = execute_request_definition(
            RequestDefinition(
                protocol=str(login_request.get("protocol") or "http"),
                url=str(login_request.get("url") or ""),
                method=str(login_request.get("method") or "POST").upper(),
                headers=_as_dict(login_request.get("headers")),
                params=login_request.get("params"),
                body=login_request.get("body"),
                timeout=int(login_request.get("timeout") or 30),
                retry_enabled=bool(login_request.get("retry_enabled")),
                retry_count=int(login_request.get("retry_count") or 0),
            ),
            RequestExecutionContext(
                request_id=request_id,
                variables=runtime_variables,
                base_url=base_url,
                global_headers=_as_dict(base_headers),
                encryption=encryption or EncryptionConfig(),
                allow_legacy_placeholders=allow_legacy_placeholders,
            ),
        )
        if login_result.status_code >= 400:
            raise ValueError(f"全局登录请求失败，状态码 {login_result.status_code}")

        extracted_variables: dict[str, Any] = {}
        for row in _normalise_extraction_rows(login_request.get("extractions")):
            variable_name = str(row.get("variable") or "").strip()
            response_path = replace_template_text(
                str(row.get("path") or ""),
                runtime_variables,
                allow_legacy_placeholders=allow_legacy_placeholders,
            ).strip()
            if not variable_name or not response_path:
                continue
            value = extract_response_value(login_result, response_path)
            if value is not None:
                extracted_variables[variable_name] = value

        if extracted_variables:
            runtime_variables.update(extracted_variables)
            logs.append(f"全局登录变量已更新: {', '.join(extracted_variables.keys())}")
        else:
            logs.append("全局登录请求已执行，但未提取到变量")

        login_summary = {
            "request": login_result.request,
            "status_code": login_result.status_code,
            "headers": login_result.headers,
            "body": login_result.body,
            "raw_body": login_result.raw_body,
            "decrypted_body": login_result.decrypted_body,
            "duration_ms": login_result.duration_ms,
            "extracted_variables": extracted_variables,
        }

    header_config = _as_dict(normalized_config.get("header_config"))
    if header_config.get("enabled"):
        resolved_headers = _as_dict(
            replace_template_data(
                _as_dict(header_config.get("headers")),
                runtime_variables,
                allow_legacy_placeholders=allow_legacy_placeholders,
            )
        )
        if resolved_headers:
            logs.append(f"全局请求头已生效: {', '.join(resolved_headers.keys())}")

    return {
        "config": normalized_config,
        "variables": runtime_variables,
        "headers": resolved_headers,
        "login_result": login_summary,
        "logs": logs,
    }


register_protocol_executor("http", _perform_http_request)
