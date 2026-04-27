from __future__ import annotations

import csv
import json
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .runtime import BACKEND_ROOT, JMETER_EXECUTABLE, PYTHON_EXECUTABLE


JMX_VERSION = "5.6.3"
JMX_PROPERTIES_VERSION = "5.0"
_LEGACY_PLACEHOLDER_PATTERN = re.compile(r"\{(\w+)\}")
_DOLLAR_DATETIME_PATTERN = re.compile(r"\$\{dateTime(?::([^}]+))?\}")
_LEGACY_DATETIME_PATTERN = re.compile(r"\{dateTime(?::([^}]+))?\}")
_DOLLAR_DATE_PATTERN = re.compile(r"\$\{date(?::([^}]+))?\}")
_LEGACY_DATE_PATTERN = re.compile(r"\{date(?::([^}]+))?\}")
_DOLLAR_TIME_PATTERN = re.compile(r"\$\{time\}")
_LEGACY_TIME_PATTERN = re.compile(r"\{time\}")
_DOLLAR_RANDOM_PATTERN = re.compile(r"\$\{random:(digits|string|alphanum):(\d+)\}")
_LEGACY_RANDOM_PATTERN = re.compile(r"\{random:(digits|string|alphanum):(\d+)\}")
_DOLLAR_ARRAY_INDEX_PATTERN = re.compile(r"\[\$\{([^}]+)\}\]")
_LEGACY_ARRAY_INDEX_PATTERN = re.compile(r"\[(\{(\w+)\})\]")


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _sanitize_name(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z._-]+", "_", str(value or "").strip()).strip("._")
    return cleaned or fallback


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _special_token_to_jmeter(text: str) -> str:
    processed = _DOLLAR_DATETIME_PATTERN.sub(lambda m: "${__time(" + (m.group(1) or "yyyyMMddHHmmss") + ",)}", text)
    processed = _LEGACY_DATETIME_PATTERN.sub(lambda m: "${__time(" + (m.group(1) or "yyyyMMddHHmmss") + ",)}", processed)
    processed = _DOLLAR_DATE_PATTERN.sub(lambda m: "${__time(" + (m.group(1) or "yyyyMMdd") + ",)}", processed)
    processed = _LEGACY_DATE_PATTERN.sub(lambda m: "${__time(" + (m.group(1) or "yyyyMMdd") + ",)}", processed)
    processed = _DOLLAR_TIME_PATTERN.sub("${__time(HHmmss,)}", processed)
    processed = _LEGACY_TIME_PATTERN.sub("${__time(HHmmss,)}", processed)

    def replace_random(match: re.Match[str]) -> str:
        kind = match.group(1)
        length = match.group(2)
        charset_map = {
            "digits": "0123456789",
            "string": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "alphanum": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        }
        return "${__RandomString(" + length + "," + charset_map[kind] + ",)}"

    processed = _DOLLAR_RANDOM_PATTERN.sub(replace_random, processed)
    processed = _LEGACY_RANDOM_PATTERN.sub(replace_random, processed)

    def replace_array_index(match: re.Match[str]) -> str:
        variable_name = match.group(1).strip()
        return "[${__groovy(Math.max(((vars.get('" + variable_name + "') ?: '1') as Integer) - 1, 0),)}]"

    processed = _DOLLAR_ARRAY_INDEX_PATTERN.sub(replace_array_index, processed)

    def replace_legacy_array_index(match: re.Match[str]) -> str:
        variable_name = match.group(2).strip()
        return "[${__groovy(Math.max(((vars.get('" + variable_name + "') ?: '1') as Integer) - 1, 0),)}]"

    return _LEGACY_ARRAY_INDEX_PATTERN.sub(replace_legacy_array_index, processed)


def _to_jmeter_template(value: Any) -> Any:
    if isinstance(value, str):
        processed = _special_token_to_jmeter(value)
        return _LEGACY_PLACEHOLDER_PATTERN.sub(lambda m: "${" + m.group(1).strip() + "}", processed)
    if isinstance(value, list):
        return [_to_jmeter_template(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_jmeter_template(item) for key, item in value.items()}
    return value


def _bool_prop(parent: ET.Element, name: str, value: bool) -> ET.Element:
    element = ET.SubElement(parent, "boolProp", name=name)
    element.text = "true" if value else "false"
    return element


def _string_prop(parent: ET.Element, name: str, value: Any) -> ET.Element:
    element = ET.SubElement(parent, "stringProp", name=name)
    element.text = _stringify_value(value)
    return element


def _int_prop(parent: ET.Element, name: str, value: Any) -> ET.Element:
    return _string_prop(parent, name, int(value))


def _new_test_element(tag: str, *, guiclass: str, testclass: str, testname: str, enabled: bool = True) -> ET.Element:
    return ET.Element(
        tag,
        {
            "guiclass": guiclass,
            "testclass": testclass,
            "testname": testname,
            "enabled": "true" if enabled else "false",
        },
    )


def _append_element(parent_hash_tree: ET.Element, element: ET.Element) -> ET.Element:
    parent_hash_tree.append(element)
    child_hash_tree = ET.SubElement(parent_hash_tree, "hashTree")
    return child_hash_tree


def _arguments_element(name: str, values: dict[str, Any]) -> ET.Element:
    arguments = _new_test_element("Arguments", guiclass="ArgumentsPanel", testclass="Arguments", testname=name)
    collection = ET.SubElement(arguments, "collectionProp", name="Arguments.arguments")
    for key, value in values.items():
        item = ET.SubElement(collection, "elementProp", name=str(key), elementType="Argument")
        _string_prop(item, "Argument.name", key)
        _string_prop(item, "Argument.value", value)
        _string_prop(item, "Argument.metadata", "=")
    return arguments


def _test_plan_user_variables(values: dict[str, Any]) -> ET.Element:
    element = ET.Element(
        "elementProp",
        {
            "name": "TestPlan.user_defined_variables",
            "elementType": "Arguments",
            "guiclass": "ArgumentsPanel",
            "testclass": "Arguments",
            "testname": "User Defined Variables",
            "enabled": "true",
        },
    )
    collection = ET.SubElement(element, "collectionProp", name="Arguments.arguments")
    for key, value in values.items():
        item = ET.SubElement(collection, "elementProp", name=str(key), elementType="Argument")
        _string_prop(item, "Argument.name", key)
        _string_prop(item, "Argument.value", value)
        _string_prop(item, "Argument.metadata", "=")
    return element


def _header_manager(name: str, headers: dict[str, Any]) -> ET.Element | None:
    normalized = {str(key): _stringify_value(value) for key, value in _as_dict(headers).items() if str(key).strip()}
    if not normalized:
        return None
    manager = _new_test_element("HeaderManager", guiclass="HeaderPanel", testclass="HeaderManager", testname=name)
    collection = ET.SubElement(manager, "collectionProp", name="HeaderManager.headers")
    for key, value in normalized.items():
        item = ET.SubElement(collection, "elementProp", name="", elementType="Header")
        _string_prop(item, "Header.name", key)
        _string_prop(item, "Header.value", value)
    return manager


def _csv_dataset_element(filename: str, variable_names: list[str], testname: str) -> ET.Element:
    dataset = _new_test_element("CSVDataSet", guiclass="TestBeanGUI", testclass="CSVDataSet", testname=testname)
    _string_prop(dataset, "delimiter", ",")
    _bool_prop(dataset, "quotedData", True)
    _bool_prop(dataset, "recycle", True)
    _bool_prop(dataset, "stopThread", False)
    _string_prop(dataset, "shareMode", "shareMode.all")
    _bool_prop(dataset, "ignoreFirstLine", True)
    _string_prop(dataset, "filename", filename)
    _string_prop(dataset, "fileEncoding", "UTF-8")
    _string_prop(dataset, "variableNames", ",".join(variable_names))
    return dataset


def _http_arguments_element(params: list[tuple[str, Any]] | None = None, *, raw_body: str | None = None) -> ET.Element:
    args = ET.Element("elementProp", name="HTTPsampler.Arguments", elementType="Arguments")
    collection = ET.SubElement(args, "collectionProp", name="Arguments.arguments")
    if raw_body is not None:
        item = ET.SubElement(collection, "elementProp", name="", elementType="HTTPArgument")
        _bool_prop(item, "HTTPArgument.always_encode", False)
        _string_prop(item, "Argument.value", raw_body)
        _string_prop(item, "Argument.metadata", "=")
        _bool_prop(item, "HTTPArgument.use_equals", True)
        return args
    for key, value in params or []:
        item = ET.SubElement(collection, "elementProp", name=str(key), elementType="HTTPArgument")
        _bool_prop(item, "HTTPArgument.always_encode", False)
        _string_prop(item, "Argument.name", key)
        _string_prop(item, "Argument.value", value)
        _string_prop(item, "Argument.metadata", "=")
        _bool_prop(item, "HTTPArgument.use_equals", True)
    return args


def _request_body_text(body: Any) -> str | None:
    if body in (None, "", {}):
        return None
    converted = _to_jmeter_template(body)
    if isinstance(converted, (dict, list)):
        return json.dumps(converted, ensure_ascii=False)
    return _stringify_value(converted)


def _timeout_ms(value: Any) -> str:
    try:
        timeout = int(value)
    except (TypeError, ValueError):
        return ""
    if timeout <= 0:
        return ""
    return str(timeout if timeout >= 1000 else timeout * 1000)


def _request_param_items(url_parts, params: Any) -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = []
    if url_parts.query:
        for raw_pair in url_parts.query.split("&"):
            if not raw_pair:
                continue
            if "=" in raw_pair:
                key, value = raw_pair.split("=", 1)
            else:
                key, value = raw_pair, ""
            items.append((key, _to_jmeter_template(value)))
    param_map = _to_jmeter_template(params)
    if isinstance(param_map, dict):
        items.extend((str(key), value) for key, value in param_map.items())
    return items


def _http_sampler_element(name: str, request: dict[str, Any], base_url: str = "") -> ET.Element:
    request_map = _as_dict(request)
    raw_url = str(request_map.get("url") or "").strip()
    if not raw_url:
        raise ValueError(f"{name} request url is empty")
    full_url = raw_url if raw_url.startswith(("http://", "https://")) else str(base_url or "").rstrip("/") + "/" + raw_url.lstrip("/")
    parsed = urlsplit(full_url)
    sampler = _new_test_element("HTTPSamplerProxy", guiclass="HttpTestSampleGui", testclass="HTTPSamplerProxy", testname=name)
    params = _request_param_items(parsed, request_map.get("params"))
    method = str(request_map.get("method") or "GET").upper()
    body_text = _request_body_text(request_map.get("body")) if method in {"POST", "PUT", "PATCH"} else None
    sampler.append(_http_arguments_element(params if body_text is None else None, raw_body=body_text))
    _string_prop(sampler, "HTTPSampler.domain", parsed.hostname or "")
    _string_prop(sampler, "HTTPSampler.port", parsed.port or "")
    _string_prop(sampler, "HTTPSampler.protocol", parsed.scheme or str(request_map.get("protocol") or "http"))
    _string_prop(sampler, "HTTPSampler.contentEncoding", "UTF-8")
    _string_prop(sampler, "HTTPSampler.path", parsed.path or "/")
    _string_prop(sampler, "HTTPSampler.method", method)
    _bool_prop(sampler, "HTTPSampler.follow_redirects", True)
    _bool_prop(sampler, "HTTPSampler.auto_redirects", False)
    _bool_prop(sampler, "HTTPSampler.use_keepalive", True)
    _bool_prop(sampler, "HTTPSampler.DO_MULTIPART_POST", False)
    _bool_prop(sampler, "HTTPSampler.monitor", False)
    _string_prop(sampler, "HTTPSampler.embedded_url_re", "")
    _bool_prop(sampler, "HTTPSampler.postBodyRaw", body_text is not None)
    _string_prop(sampler, "HTTPSampler.connect_timeout", _timeout_ms(request_map.get("timeout")))
    _string_prop(sampler, "HTTPSampler.response_timeout", _timeout_ms(request_map.get("timeout")))
    return sampler


def _extractor_script(extractors: list[dict[str, Any]]) -> str:
    config_text = json.dumps(extractors, ensure_ascii=False)
    return f"""
import groovy.json.JsonSlurper

def rows = new JsonSlurper().parseText('''{config_text}''')
def bodyText = prev.getResponseDataAsString() ?: ''
def bodyObject = null
try {{
    bodyObject = new JsonSlurper().parseText(bodyText)
}} catch (ignored) {{
    bodyObject = null
}}
def headers = [:]
(prev.getResponseHeaders() ?: '').split(/\\r?\\n/).each {{ line ->
    def idx = line.indexOf(':')
    if (idx > 0) {{
        def name = line.substring(0, idx).trim()
        def value = line.substring(idx + 1).trim()
        headers[name] = value
        headers[name.toLowerCase()] = value
    }}
}}
def cookies = [:]
(prev.getResponseHeaders() ?: '').split(/\\r?\\n/).each {{ line ->
    if (!line.toLowerCase().startsWith('set-cookie:')) {{
        return
    }}
    def value = line.substring(line.indexOf(':') + 1).trim()
    def cookiePair = value.tokenize(';')[0]
    def eq = cookiePair.indexOf('=')
    if (eq > 0) {{
        cookies[cookiePair.substring(0, eq).trim()] = cookiePair.substring(eq + 1).trim()
    }}
}}
def pathTokens = {{ String path ->
    def cleaned = (path ?: '').trim()
    if (cleaned.startsWith('$.')) {{
        cleaned = cleaned.substring(2)
    }} else if (cleaned.startsWith('$')) {{
        cleaned = cleaned.substring(1)
    }}
    ['body.', 'response_body.', 'decrypted_body.', 'response_decrypted_body.'].each {{ prefix ->
        if (cleaned.startsWith(prefix)) {{
            cleaned = cleaned.substring(prefix.length())
        }}
    }}
    def tokens = []
    cleaned.split(/\\./).each {{ part ->
        if (!part) {{
            return
        }}
        def matcher = (part =~ /([^\\[]+)|(\\[(\\d+)\\])/)
        matcher.findAll().each {{ groups ->
            if (groups[1]) {{
                tokens << groups[1]
            }} else if (groups[3]) {{
                tokens << Integer.parseInt(groups[3])
            }}
        }}
    }}
    tokens
}}
def extractPath
extractPath = {{ data, String path ->
    def current = data
    for (token in pathTokens(path)) {{
        if (token instanceof Integer) {{
            if (!(current instanceof List) || token >= current.size()) {{
                return null
            }}
            current = current[token]
        }} else {{
            if (!(current instanceof Map) || !current.containsKey(token)) {{
                return null
            }}
            current = current[token]
        }}
    }}
    current
}}
def failed = []
rows.each {{ row ->
    def variableName = ((row.var ?: row.variable ?: '').toString()).trim()
    if (!variableName) {{
        return
    }}
    def extractorType = ((row.type ?: '').toString()).trim().toLowerCase()
    def source = ((row.from ?: row.source ?: '').toString()).trim().toLowerCase()
    def expr = ((row.expr ?: row.path ?: '').toString())
    def value = null
    if (extractorType == 'status_code' || expr == 'status_code') {{
        value = prev.getResponseCode()
    }} else if (extractorType == 'header' || source in ['header', 'headers', 'response_headers']) {{
        value = headers[expr] ?: headers[expr.toLowerCase()]
    }} else if (extractorType == 'cookie' || source == 'cookie') {{
        value = cookies[expr]
    }} else if (extractorType == 'regex') {{
        def matcher = (bodyText =~ expr)
        if (matcher.find()) {{
            value = matcher.groupCount() >= 1 ? matcher.group(1) : matcher.group(0)
        }}
    }} else {{
        value = extractPath(bodyObject, expr)
    }}
    if (value == null || value == '') {{
        failed << variableName
    }} else {{
        vars.put(variableName, String.valueOf(value))
    }}
}}
if (!failed.isEmpty()) {{
    prev.setSuccessful(false)
    prev.setResponseMessage(((prev.getResponseMessage() ?: '') + ' | extractor failed: ' + failed.join(', ')).trim())
}}
""".strip()


def _validator_script(validators: list[dict[str, Any]]) -> str:
    config_text = json.dumps(validators, ensure_ascii=False)
    return f"""
import groovy.json.JsonSlurper

def rows = new JsonSlurper().parseText('''{config_text}''')
def bodyText = prev.getResponseDataAsString() ?: ''
def bodyObject = null
try {{
    bodyObject = new JsonSlurper().parseText(bodyText)
}} catch (ignored) {{
    bodyObject = null
}}
def headers = [:]
(prev.getResponseHeaders() ?: '').split(/\\r?\\n/).each {{ line ->
    def idx = line.indexOf(':')
    if (idx > 0) {{
        def name = line.substring(0, idx).trim()
        def value = line.substring(idx + 1).trim()
        headers[name] = value
        headers[name.toLowerCase()] = value
    }}
}}
def pathTokens = {{ String path ->
    def cleaned = (path ?: '').trim()
    if (cleaned.startsWith('$.')) {{
        cleaned = cleaned.substring(2)
    }} else if (cleaned.startsWith('$')) {{
        cleaned = cleaned.substring(1)
    }}
    ['body.', 'response_body.', 'decrypted_body.', 'response_decrypted_body.'].each {{ prefix ->
        if (cleaned.startsWith(prefix)) {{
            cleaned = cleaned.substring(prefix.length())
        }}
    }}
    def tokens = []
    cleaned.split(/\\./).each {{ part ->
        if (!part) {{
            return
        }}
        def matcher = (part =~ /([^\\[]+)|(\\[(\\d+)\\])/)
        matcher.findAll().each {{ groups ->
            if (groups[1]) {{
                tokens << groups[1]
            }} else if (groups[3]) {{
                tokens << Integer.parseInt(groups[3])
            }}
        }}
    }}
    tokens
}}
def extractPath
extractPath = {{ data, String path ->
    def current = data
    for (token in pathTokens(path)) {{
        if (token instanceof Integer) {{
            if (!(current instanceof List) || token >= current.size()) {{
                return null
            }}
            current = current[token]
        }} else {{
            if (!(current instanceof Map) || !current.containsKey(token)) {{
                return null
            }}
            current = current[token]
        }}
    }}
    current
}}
def coerceBool = {{ value ->
    if (value == null) {{
        return null
    }}
    if (value instanceof Boolean) {{
        return value
    }}
    def text = String.valueOf(value).trim().toLowerCase()
    if (['true', '1', 'yes', 'y'].contains(text)) {{
        return true
    }}
    if (['false', '0', 'no', 'n'].contains(text)) {{
        return false
    }}
    return null
}}
def coerceNumber = {{ value ->
    if (value == null || value == '') {{
        return null
    }}
    try {{
        return new BigDecimal(String.valueOf(value).trim())
    }} catch (ignored) {{
        return null
    }}
}}
def resolveField = {{ String field ->
    if (!field) {{
        return null
    }}
    if (field == 'status_code') {{
        return prev.getResponseCode()
    }}
    if (field == 'raw_body') {{
        return bodyText
    }}
    if (field.startsWith('headers.') || field.startsWith('response_headers.')) {{
        def key = field.substring(field.indexOf('.') + 1)
        return headers[key] ?: headers[key.toLowerCase()]
    }}
    if (field.startsWith('runtime_vars.')) {{
        return vars.get(field.substring('runtime_vars.'.length()))
    }}
    if (field.startsWith('$') || field.startsWith('body.') || field.startsWith('response_body.') || field.startsWith('decrypted_body.') || field.startsWith('response_decrypted_body.')) {{
        return extractPath(bodyObject, field)
    }}
    return vars.get(field)
}}
def compare = {{ operator, actual, expected ->
    def actualBool = coerceBool(actual)
    def expectedBool = coerceBool(expected)
    if (operator == 'equal') {{
        if (actualBool != null && expectedBool != null) {{
            return actualBool == expectedBool
        }}
        return String.valueOf(actual) == String.valueOf(expected)
    }}
    if (operator == 'not_equal') {{
        if (actualBool != null && expectedBool != null) {{
            return actualBool != expectedBool
        }}
        return String.valueOf(actual) != String.valueOf(expected)
    }}
    if (operator == 'contains') {{
        return String.valueOf(actual).contains(String.valueOf(expected))
    }}
    if (operator == 'not_contains') {{
        return !String.valueOf(actual).contains(String.valueOf(expected))
    }}
    if (operator == 'regex_match') {{
        return (String.valueOf(actual) ==~ String.valueOf(expected))
    }}
    if (operator == 'exists') {{
        return actual != null && String.valueOf(actual) != ''
    }}
    if (operator == 'not_exists') {{
        return actual == null || String.valueOf(actual) == ''
    }}
    def actualNumber = coerceNumber(actual)
    def expectedNumber = coerceNumber(expected)
    if (actualNumber == null || expectedNumber == null) {{
        return false
    }}
    if (operator == 'greater') {{
        return actualNumber > expectedNumber
    }}
    if (operator == 'less') {{
        return actualNumber < expectedNumber
    }}
    if (operator == 'greater_equal') {{
        return actualNumber >= expectedNumber
    }}
    if (operator == 'less_equal') {{
        return actualNumber <= expectedNumber
    }}
    return false
}}
for (row in rows) {{
    def field = (row.field ?: '').toString()
    def operator = (row.operator ?: 'equal').toString()
    def expected = row.expected
    def actual = resolveField(field)
    def passed = compare(operator, actual, expected)
    if (!passed) {{
        AssertionResult.setFailure(true)
        AssertionResult.setFailureMessage(field + ' ' + operator + ' failed, expected=' + expected + ', actual=' + actual)
        return
    }}
}}
AssertionResult.setFailure(false)
""".strip()


def _jsr223_postprocessor(name: str, script: str) -> ET.Element:
    element = _new_test_element("JSR223PostProcessor", guiclass="TestBeanGUI", testclass="JSR223PostProcessor", testname=name)
    _string_prop(element, "cacheKey", name)
    _string_prop(element, "filename", "")
    _string_prop(element, "parameters", "")
    _string_prop(element, "scriptLanguage", "groovy")
    _string_prop(element, "script", script)
    return element


def _jsr223_preprocessor(name: str, script: str) -> ET.Element:
    element = _new_test_element("JSR223PreProcessor", guiclass="TestBeanGUI", testclass="JSR223PreProcessor", testname=name)
    _string_prop(element, "cacheKey", name)
    _string_prop(element, "filename", "")
    _string_prop(element, "parameters", "")
    _string_prop(element, "scriptLanguage", "groovy")
    _string_prop(element, "script", script)
    return element


def _jsr223_assertion(name: str, script: str) -> ET.Element:
    element = _new_test_element("JSR223Assertion", guiclass="TestBeanGUI", testclass="JSR223Assertion", testname=name)
    _string_prop(element, "cacheKey", name)
    _string_prop(element, "filename", "")
    _string_prop(element, "parameters", "")
    _string_prop(element, "scriptLanguage", "groovy")
    _string_prop(element, "script", script)
    return element


def _jsr223_sampler(name: str, script: str) -> ET.Element:
    element = _new_test_element("JSR223Sampler", guiclass="TestBeanGUI", testclass="JSR223Sampler", testname=name)
    _string_prop(element, "cacheKey", name)
    _string_prop(element, "filename", "")
    _string_prop(element, "parameters", "")
    _string_prop(element, "scriptLanguage", "groovy")
    _string_prop(element, "script", script)
    return element


def _beanshell_sampler(name: str, script: str) -> ET.Element:
    element = _new_test_element("BeanShellSampler", guiclass="BeanShellSamplerGui", testclass="BeanShellSampler", testname=name)
    _string_prop(element, "BeanShellSampler.query", script)
    _string_prop(element, "BeanShellSampler.filename", "")
    _string_prop(element, "BeanShellSampler.parameters", "")
    _bool_prop(element, "BeanShellSampler.resetInterpreter", False)
    return element


def _beanshell_preprocessor(name: str, script: str) -> ET.Element:
    element = _new_test_element("BeanShellPreProcessor", guiclass="BeanShellPreProcessorGui", testclass="BeanShellPreProcessor", testname=name)
    _string_prop(element, "BeanShellPreProcessor.query", script)
    _string_prop(element, "BeanShellPreProcessor.filename", "")
    _string_prop(element, "BeanShellPreProcessor.parameters", "")
    _bool_prop(element, "BeanShellPreProcessor.resetInterpreter", False)
    return element


def _if_controller(name: str, condition: str) -> ET.Element:
    element = _new_test_element("IfController", guiclass="IfControllerPanel", testclass="IfController", testname=name)
    _string_prop(element, "IfController.condition", condition)
    _bool_prop(element, "IfController.evaluateAll", False)
    _bool_prop(element, "IfController.useExpression", True)
    return element


def _step_hook_block_var(step: dict[str, Any]) -> str:
    step_id = str(step.get("step_id") or step.get("id") or step.get("step_order") or "step")
    safe = _sanitize_name(step_id, "step")
    return f"__tt_hook_block_{safe}"


def _write_httprunner_hook_assets(suite_ir: dict[str, Any], output_dir: Path) -> dict[str, Any] | None:
    hook_specs: dict[str, Any] = {}

    for case_entry in _as_list(suite_ir.get("cases")):
        case_map = _as_dict(case_entry)
        case_ir = _as_dict(case_map.get("case_ir"))
        case_info = _as_dict(case_ir.get("case"))
        environment = _as_dict(_as_dict(case_ir.get("runtime")).get("environment"))
        global_request_config = _as_dict(case_ir.get("global_request_config"))
        for step in _as_list(case_ir.get("steps")):
            step_map = _as_dict(step)
            for hook in _as_list(step_map.get("setup_hooks")) + _as_list(step_map.get("teardown_hooks")):
                hook_map = _as_dict(hook)
                function_name = str(hook_map.get("function_name") or "").strip()
                if not function_name:
                    continue
                hook_specs[function_name] = {
                    "hook_id": hook_map.get("hook_id") or function_name,
                    "function_name": function_name,
                    "stage": hook_map.get("stage") or "",
                    "tool_type": hook_map.get("tool_type") or "",
                    "name": hook_map.get("name") or "",
                    "tool": hook_map.get("tool") or {},
                    "case": {
                        "id": case_info.get("id"),
                        "name": case_info.get("name") or "",
                        "enable_encryption": bool(case_info.get("enable_encryption")),
                        "encrypt_url": str(case_info.get("encrypt_url") or ""),
                        "decrypt_url": str(case_info.get("decrypt_url") or ""),
                    },
                    "step": {
                        "id": step_map.get("id"),
                        "step_id": step_map.get("step_id"),
                        "step_order": step_map.get("step_order"),
                        "name": step_map.get("name") or "",
                    },
                    "environment": environment,
                    "global_request_config": global_request_config,
                }

    if not hook_specs:
        return None

    hooks_json_path = output_dir / "httprunner_hooks.json"
    hooks_json_path.write_text(
        json.dumps({"schema_version": 1, "hooks": hook_specs}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "from __future__ import annotations",
        "",
        "from pathlib import Path",
        "",
        "from apps.performance.hook_runtime import execute_compiled_hook",
        "",
        "_HOOK_SPEC_PATH = Path(__file__).with_name('httprunner_hooks.json')",
        "",
    ]
    for function_name in sorted(hook_specs):
        lines.extend(
            [
                f"def {function_name}(context):",
                f"    return execute_compiled_hook(_HOOK_SPEC_PATH, {function_name!r}, context)",
                "",
            ]
        )
    hooks_py_path = output_dir / "httprunner_hooks.py"
    hooks_py_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {
        "module_path": str(hooks_py_path),
        "spec_path": str(hooks_json_path),
        "functions": sorted(hook_specs),
    }


def _hook_beanshell_sampler_script(
    *,
    sampler_name: str,
    module_path: str,
    function_names: list[str],
    stage: str,
    block_var: str,
) -> str:
    python_executable = str(PYTHON_EXECUTABLE if PYTHON_EXECUTABLE else Path(sys.executable))
    hook_cli_path = str((BACKEND_ROOT / "apps" / "performance" / "hook_cli.py").resolve())
    backend_root = str(BACKEND_ROOT.resolve())
    module_file = str(Path(module_path).resolve())
    functions_csv = ",".join(function_names)
    return f"""
String samplerName = {json.dumps(sampler_name)};
String stage = {json.dumps(stage)};
String blockVar = {json.dumps(block_var)};
if ("teardown".equals(stage) && prev != null && !prev.isSuccessful()) {{
    SampleResult.setSampleLabel(samplerName);
    SampleResult.setSuccessful(true);
    SampleResult.setResponseCode("204");
    SampleResult.setResponseMessage("skipped teardown hooks because previous sample failed");
    SampleResult.setResponseData("{{}}", "UTF-8");
    return;
}}
java.io.File variablesFile = java.io.File.createTempFile("tt-hook-vars-", ".tsv");
java.io.File resultFile = java.io.File.createTempFile("tt-hook-result-", ".tsv");
java.io.BufferedWriter writer = null;
try {{
    writer = new java.io.BufferedWriter(new java.io.OutputStreamWriter(new java.io.FileOutputStream(variablesFile), "UTF-8"));
    java.util.Iterator iterator = vars.entrySet().iterator();
    while (iterator.hasNext()) {{
        java.util.Map.Entry entry = (java.util.Map.Entry) iterator.next();
        String key = String.valueOf(entry.getKey());
        if (key.startsWith("__jm__")) {{
            continue;
        }}
        String value = vars.get(key);
        writer.write(key);
        writer.write("\\t");
        writer.write(java.net.URLEncoder.encode(value == null ? "" : value, "UTF-8"));
        writer.newLine();
    }}
    writer.flush();
    writer.close();
    writer = null;

    String[] command = new String[] {{
        {json.dumps(python_executable)},
        {json.dumps(hook_cli_path)},
        "--module-file",
        {json.dumps(module_file)},
        "--functions",
        {json.dumps(functions_csv)},
        "--variables-file",
        variablesFile.getAbsolutePath(),
        "--result-flat-file",
        resultFile.getAbsolutePath()
    }};
    String[] envp = new String[] {{
        "PYTHONIOENCODING=UTF-8",
        "PYTHONPATH=" + {json.dumps(backend_root)}
    }};
    Process process = Runtime.getRuntime().exec(command, envp);
    int exitCode = process.waitFor();

    String status = "failed";
    String message = "";
    java.io.BufferedReader reader = new java.io.BufferedReader(new java.io.InputStreamReader(new java.io.FileInputStream(resultFile), "UTF-8"));
    String line = null;
    while ((line = reader.readLine()) != null) {{
        String[] parts = line.split("\\\\t", 3);
        if (parts.length >= 2 && "status".equals(parts[0])) {{
            status = java.net.URLDecoder.decode(parts[1], "UTF-8");
        }} else if (parts.length >= 2 && "message".equals(parts[0])) {{
            message = java.net.URLDecoder.decode(parts[1], "UTF-8");
        }} else if (parts.length >= 3 && "variable".equals(parts[0])) {{
            String variableName = parts[1];
            String variableValue = java.net.URLDecoder.decode(parts[2], "UTF-8");
            if ("__TESTTOOL_NULL__".equals(variableValue)) {{
                vars.remove(variableName);
            }} else {{
                vars.put(variableName, variableValue);
            }}
        }}
    }}
    reader.close();

    if ("setup".equals(stage)) {{
        vars.put(blockVar, "success".equals(status) ? "false" : "true");
    }}
    SampleResult.setSampleLabel(samplerName);
    SampleResult.setSuccessful(exitCode == 0 && "success".equals(status));
    SampleResult.setResponseCode(exitCode == 0 && "success".equals(status) ? "200" : "500");
    SampleResult.setResponseMessage(message == null || message.length() == 0 ? (exitCode == 0 ? "ok" : "hook process failed") : message);
    SampleResult.setResponseData("status=" + status, "UTF-8");
}} finally {{
    if (writer != null) {{
        writer.close();
    }}
    variablesFile.delete();
    resultFile.delete();
}}
""".strip()


def _hook_sampler_script(
    *,
    sampler_name: str,
    module_path: str,
    function_names: list[str],
    stage: str,
    block_var: str,
) -> str:
    python_executable = str(PYTHON_EXECUTABLE if PYTHON_EXECUTABLE else Path(sys.executable))
    hook_cli_path = str((BACKEND_ROOT / "apps" / "performance" / "hook_cli.py").resolve())
    backend_root = str(BACKEND_ROOT.resolve())
    module_file = str(Path(module_path).resolve())
    function_names_json = json.dumps(function_names, ensure_ascii=False)
    stage_json = json.dumps(stage, ensure_ascii=False)
    sampler_name_json = json.dumps(sampler_name, ensure_ascii=False)
    block_var_json = json.dumps(block_var, ensure_ascii=False)
    return f"""
import groovy.json.JsonOutput
import groovy.json.JsonSlurper

def samplerName = {sampler_name_json}
def stage = {stage_json}
def blockVar = {block_var_json}
if (stage == 'teardown' && prev != null && !prev.isSuccessful()) {{
    SampleResult.setSampleLabel(samplerName)
    SampleResult.setSuccessful(true)
    SampleResult.setResponseCode('204')
    SampleResult.setResponseMessage('skipped teardown hooks because previous sample failed')
    SampleResult.setResponseData('{{}}', 'UTF-8')
    return
}}

def collectVars = {{
    def collected = [:]
    def iterator = vars.entrySet().iterator()
    while (iterator.hasNext()) {{
        def entry = iterator.next()
        def key = String.valueOf(entry.getKey())
        if (!key.startsWith('__jm__')) {{
            collected[key] = vars.get(key)
        }}
    }}
    collected
}}

def parseHeaders = {{ String headerText ->
    def headers = [:]
    (headerText ?: '').split(/\\r?\\n/).each {{ line ->
        def idx = line.indexOf(':')
        if (idx > 0) {{
            def name = line.substring(0, idx).trim()
            def value = line.substring(idx + 1).trim()
            headers[name] = value
            headers[name.toLowerCase()] = value
        }}
    }}
    headers
}}

def parseBody = {{ String bodyText ->
    def text = bodyText ?: ''
    if (!text) {{
        return null
    }}
    try {{
        return new JsonSlurper().parseText(text)
    }} catch (ignored) {{
        return text
    }}
}}

def context = [
    variables: collectVars(),
    source_data: null,
]
if (stage == 'teardown' && prev != null) {{
    def rawBody = prev.getResponseDataAsString() ?: ''
    def parsedHeaders = parseHeaders(prev.getResponseHeaders())
    def parsedBody = parseBody(rawBody)
    context.source_data = [
        status_code: prev.getResponseCode(),
        headers: parsedHeaders,
        response_headers: parsedHeaders,
        body: parsedBody,
        response_body: parsedBody,
        decrypted_body: parsedBody,
        response_decrypted_body: parsedBody,
        raw_body: rawBody,
    ]
}}

def contextFile = File.createTempFile('tt-hook-context-', '.json')
def resultFile = File.createTempFile('tt-hook-result-', '.json')
try {{
    contextFile.setText(JsonOutput.toJson(context), 'UTF-8')
    def command = [
        {json.dumps(python_executable)},
        {json.dumps(hook_cli_path)},
        '--module-file',
        {json.dumps(module_file)},
        '--functions',
        ({function_names_json} as List).join(','),
        '--context-file',
        contextFile.getAbsolutePath(),
        '--result-file',
        resultFile.getAbsolutePath(),
    ]
    def envp = [
        'PYTHONIOENCODING=UTF-8',
        'PYTHONPATH=' + {json.dumps(backend_root)},
    ] as String[]
    def process = command.execute(envp, null)
    def exitCode = process.waitFor()
    def stdoutText = process.inputStream.getText('UTF-8')
    def stderrText = process.errorStream.getText('UTF-8')
    def consoleOutput = [stdoutText, stderrText].findAll {{ it != null && it.trim() }}.join('\\n')
    def result = resultFile.exists() ? new JsonSlurper().parseText(resultFile.getText('UTF-8')) : [:]
    def variableChanges = result.variable_changes instanceof Map ? result.variable_changes : [:]
    variableChanges.each {{ key, value ->
        def keyText = String.valueOf(key)
        if (value == null) {{
            vars.remove(keyText)
        }} else if (value instanceof Map || value instanceof List) {{
            vars.put(keyText, JsonOutput.toJson(value))
        }} else {{
            vars.put(keyText, String.valueOf(value))
        }}
    }}
    if (stage == 'setup') {{
        vars.put(blockVar, String.valueOf(!(result.status == 'success')))
    }}
    SampleResult.setSampleLabel(samplerName)
    SampleResult.setSuccessful(exitCode == 0 && result.status == 'success')
    SampleResult.setResponseCode(exitCode == 0 && result.status == 'success' ? '200' : '500')
    def responseMessage = String.valueOf(result.message ?: (exitCode == 0 ? 'ok' : 'hook process failed'))
    if (consoleOutput?.trim()) {{
        responseMessage = responseMessage + ' | ' + consoleOutput.trim()
    }}
    SampleResult.setResponseMessage(responseMessage)
    SampleResult.setResponseData(JsonOutput.prettyPrint(JsonOutput.toJson(result)), 'UTF-8')
}} finally {{
    contextFile.delete()
    resultFile.delete()
}}
""".strip()

def _thread_group_element(load_profile: dict[str, Any], suite_name: str) -> ET.Element:
    loops = int(load_profile.get("loops") or 1)
    if int(load_profile.get("duration_seconds") or 0) > 0 and loops <= 0:
        loops = 999999999
    thread_group = _new_test_element("ThreadGroup", guiclass="ThreadGroupGui", testclass="ThreadGroup", testname=f"Thread Group - {suite_name}")
    controller = ET.SubElement(
        thread_group,
        "elementProp",
        name="ThreadGroup.main_controller",
        elementType="LoopController",
        guiclass="LoopControlPanel",
        testclass="LoopController",
        testname="Loop Controller",
        enabled="true",
    )
    _bool_prop(controller, "LoopController.continue_forever", False)
    _string_prop(controller, "LoopController.loops", loops)
    _string_prop(thread_group, "ThreadGroup.on_sample_error", "continue")
    _string_prop(thread_group, "ThreadGroup.num_threads", int(load_profile.get("threads") or 1))
    _string_prop(thread_group, "ThreadGroup.ramp_time", int(load_profile.get("ramp_up_seconds") or 1))
    _bool_prop(thread_group, "ThreadGroup.same_user_on_next_iteration", True)
    _string_prop(thread_group, "ThreadGroup.delay", "")
    duration = int(load_profile.get("duration_seconds") or 0)
    _bool_prop(thread_group, "ThreadGroup.scheduler", duration > 0)
    _string_prop(thread_group, "ThreadGroup.duration", duration if duration > 0 else "")
    return thread_group


def _cookie_manager_element() -> ET.Element:
    element = _new_test_element("CookieManager", guiclass="CookiePanel", testclass="CookieManager", testname="HTTP Cookie Manager")
    ET.SubElement(element, "collectionProp", name="CookieManager.cookies")
    _bool_prop(element, "CookieManager.clearEachIteration", False)
    _bool_prop(element, "CookieManager.controlledByThreadGroup", False)
    return element


def _request_definition_from_step(step: dict[str, Any], case_ir: dict[str, Any]) -> dict[str, Any]:
    request = _as_dict(step.get("request"))
    case_global_config = _as_dict(case_ir.get("global_request_config"))
    header_config = _as_dict(case_global_config.get("header_config"))
    merged_headers = dict(_as_dict(request.get("headers")))
    if _as_dict(step.get("flags")).get("use_global_headers", True):
        merged_headers.update(_to_jmeter_template(_as_dict(header_config.get("headers"))))
    return {
        **request,
        "url": _to_jmeter_template(request.get("url")),
        "headers": _to_jmeter_template(merged_headers),
        "params": _to_jmeter_template(request.get("params")),
        "body": _to_jmeter_template(request.get("body")),
    }


def _render_path_preprocessor_script(raw_path: str) -> str:
    return f"""
String rendered = {json.dumps(str(raw_path or '/'))};
java.util.Iterator iterator = vars.entrySet().iterator();
while (iterator.hasNext()) {{
    java.util.Map.Entry entry = (java.util.Map.Entry) iterator.next();
    String key = String.valueOf(entry.getKey());
    String value = vars.get(key);
    if (value == null) {{
        value = "";
    }}
    rendered = rendered.replace("${{" + key + "}}", value);
    rendered = rendered.replace("{{" + key + "}}", value);
}}
sampler.setPath(rendered);
""".strip()


def _login_request_definition(case_ir: dict[str, Any]) -> dict[str, Any] | None:
    global_config = _as_dict(case_ir.get("global_request_config"))
    login_request = _as_dict(global_config.get("login_request"))
    if not login_request.get("enabled"):
        return None
    return {
        **login_request,
        "url": _to_jmeter_template(login_request.get("url")),
        "headers": _to_jmeter_template(_as_dict(login_request.get("headers"))),
        "params": _to_jmeter_template(login_request.get("params")),
        "body": _to_jmeter_template(login_request.get("body")),
    }


def _declared_tool_variable_names(tool: dict[str, Any]) -> list[str]:
    tool_map = _as_dict(tool)
    config = _as_dict(tool_map.get("config"))
    names: list[str] = []
    tool_type = str(tool_map.get("tool_type") or tool_map.get("type") or "").strip().lower()

    if tool_type == "python_script":
        raw_items = _as_list(tool_map.get("output_fields")) or _as_list(config.get("output_fields"))
        for item in raw_items:
            if isinstance(item, str):
                name = item.strip()
            else:
                item_map = _as_dict(item)
                name = str(item_map.get("variable") or item_map.get("output") or item_map.get("name") or item_map.get("field") or "").strip()
            if name and name not in names:
                names.append(name)
    if tool_type == "sql_tool":
        raw_items = _as_list(tool_map.get("output_fields")) or _as_list(config.get("output_fields"))
        for item in raw_items:
            if isinstance(item, str):
                name = item.strip()
            else:
                item_map = _as_dict(item)
                name = str(item_map.get("variable") or item_map.get("output") or item_map.get("name") or item_map.get("field") or "").strip()
            if name and name not in names:
                names.append(name)

    for extraction in _as_list(tool_map.get("extractions")) + _as_list(config.get("extractions")):
        extraction_map = _as_dict(extraction)
        name = str(extraction_map.get("variable") or extraction_map.get("var") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def _declared_case_variable_names(case_ir: dict[str, Any]) -> list[str]:
    names: list[str] = []

    def append_name(value: str) -> None:
        if value and value not in names:
            names.append(value)

    login_request = _login_request_definition(case_ir)
    if login_request:
        for extraction in _as_list(login_request.get("extractions")):
            append_name(str(_as_dict(extraction).get("variable") or _as_dict(extraction).get("var") or "").strip())

    for output in _as_list(case_ir.get("outputs")):
        output_map = _as_dict(output)
        append_name(str(output_map.get("name") or output_map.get("variable") or output_map.get("source") or "").strip())

    for step in _as_list(case_ir.get("steps")):
        step_map = _as_dict(step)
        for extractor in _as_list(step_map.get("extractors")):
            append_name(str(_as_dict(extractor).get("var") or _as_dict(extractor).get("variable") or "").strip())
        for hook in _as_list(step_map.get("setup_hooks")) + _as_list(step_map.get("teardown_hooks")):
            tool_map = _as_dict(_as_dict(hook).get("tool"))
            for name in _declared_tool_variable_names(tool_map):
                append_name(name)
    return names


def _case_variable_map(case_ir: dict[str, Any]) -> dict[str, Any]:
    variables = dict(_as_dict(case_ir.get("variables")))
    for name in _declared_case_variable_names(case_ir):
        variables.setdefault(name, "")
    if variables.get("request_id"):
        variables["request_id"] = "${__UUID()}"
    return _to_jmeter_template(variables)


def _parameter_csv_columns(parameter_instances: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    for instance in parameter_instances:
        for key in _as_dict(instance.get("values")).keys():
            key_text = str(key)
            if key_text not in columns:
                columns.append(key_text)
    return columns


def _write_parameter_csv(case_entry: dict[str, Any], output_dir: Path) -> dict[str, Any] | None:
    case_ir = _as_dict(case_entry.get("case_ir"))
    runtime = _as_dict(case_ir.get("runtime"))
    parameter_instances = [item for item in _as_list(runtime.get("parameter_instances")) if _as_dict(item).get("enabled")]
    if not parameter_instances:
        return None
    columns = _parameter_csv_columns(parameter_instances)
    if not columns:
        return None
    filename = f"{_sanitize_name(str(case_entry.get('case_name') or case_entry.get('case_id')), 'case')}_params.csv"
    csv_path = output_dir / filename
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for instance in parameter_instances:
            writer.writerow({column: _stringify_value(_as_dict(instance.get("values")).get(column)) for column in columns})
    return {
        "case_id": case_entry.get("case_id"),
        "case_name": case_entry.get("case_name"),
        "filename": filename,
        "path": str(csv_path),
        "variable_names": columns,
    }


def _build_case_tree(
    parent_hash_tree: ET.Element,
    case_entry: dict[str, Any],
    csv_asset: dict[str, Any] | None,
    hooks_asset: dict[str, Any] | None,
) -> None:
    case_ir = _as_dict(case_entry.get("case_ir"))
    case_info = _as_dict(case_ir.get("case"))
    runtime = _as_dict(case_ir.get("runtime"))
    environment = _as_dict(runtime.get("environment"))
    base_url = str(environment.get("base_url") or "")
    transaction = _new_test_element(
        "TransactionController",
        guiclass="TransactionControllerGui",
        testclass="TransactionController",
        testname=f"Case - {case_info.get('name') or case_entry.get('case_name')}",
    )
    _bool_prop(transaction, "TransactionController.parent", True)
    _bool_prop(transaction, "TransactionController.includeTimers", False)
    case_hash_tree = _append_element(parent_hash_tree, transaction)

    case_args = _arguments_element("Case Variables", _case_variable_map(case_ir))
    _append_element(case_hash_tree, case_args)
    if csv_asset:
        csv_element = _csv_dataset_element(csv_asset["filename"], csv_asset["variable_names"], f"CSV - {case_entry.get('case_name')}")
        _append_element(case_hash_tree, csv_element)

    login_request = _login_request_definition(case_ir)
    if login_request:
        login_sampler = _http_sampler_element(f"Login - {case_entry.get('case_name')}", login_request, base_url=base_url)
        login_hash_tree = _append_element(case_hash_tree, login_sampler)
        header_manager = _header_manager("Headers - Login", login_request.get("headers"))
        if header_manager is not None:
            _append_element(login_hash_tree, header_manager)
        login_extractors = _as_list(login_request.get("extractions"))
        if login_extractors:
            _append_element(login_hash_tree, _jsr223_postprocessor("Extract - Login", _extractor_script(login_extractors)))

    for step in _as_list(case_ir.get("steps")):
        step_map = _as_dict(step)
        if step_map.get("enabled") is False:
            continue
        hook_block_var = _step_hook_block_var(step_map)
        setup_hooks = [str(_as_dict(item).get("function_name") or "").strip() for item in _as_list(step_map.get("setup_hooks"))]
        setup_hooks = [item for item in setup_hooks if item]
        teardown_hooks = [str(_as_dict(item).get("function_name") or "").strip() for item in _as_list(step_map.get("teardown_hooks"))]
        teardown_hooks = [item for item in teardown_hooks if item]
        if setup_hooks and hooks_asset:
            _append_element(
                case_hash_tree,
                _beanshell_sampler(
                    f"Setup Hooks - {step_map.get('name') or step_map.get('step_id')}",
                    _hook_beanshell_sampler_script(
                        sampler_name=f"Setup Hooks - {step_map.get('name') or step_map.get('step_id')}",
                        module_path=str(hooks_asset.get("module_path") or ""),
                        function_names=setup_hooks,
                        stage="setup",
                        block_var=hook_block_var,
                    ),
                ),
            )
        request_definition = _request_definition_from_step(step_map, case_ir)
        sampler = _http_sampler_element(
            f"Step {step_map.get('step_order') or ''} - {step_map.get('name') or step_map.get('step_id')}",
            request_definition,
            base_url=base_url,
        )
        sampler_hash_tree = _append_element(case_hash_tree, sampler)
        _append_element(
            sampler_hash_tree,
            _beanshell_preprocessor(
                f"Render Path - {step_map.get('name') or step_map.get('step_id')}",
                _render_path_preprocessor_script(str(request_definition.get("url") or "/")),
            ),
        )
        header_manager = _header_manager(
            f"Headers - {step_map.get('name') or step_map.get('step_id')}",
            request_definition.get("headers"),
        )
        if header_manager is not None:
            _append_element(sampler_hash_tree, header_manager)
        extractors = _as_list(step_map.get("extractors"))
        if extractors:
            _append_element(
                sampler_hash_tree,
                _jsr223_postprocessor(
                    f"Extract - {step_map.get('name') or step_map.get('step_id')}",
                    _extractor_script(extractors),
                ),
            )
        validators = _as_list(step_map.get("validators"))
        if validators:
            _append_element(
                sampler_hash_tree,
                _jsr223_assertion(
                    f"Validate - {step_map.get('name') or step_map.get('step_id')}",
                    _validator_script(validators),
                ),
            )
        if teardown_hooks and hooks_asset:
            _append_element(
                case_hash_tree,
                _beanshell_sampler(
                    f"Teardown Hooks - {step_map.get('name') or step_map.get('step_id')}",
                    _hook_beanshell_sampler_script(
                        sampler_name=f"Teardown Hooks - {step_map.get('name') or step_map.get('step_id')}",
                        module_path=str(hooks_asset.get("module_path") or ""),
                        function_names=teardown_hooks,
                        stage="teardown",
                        block_var=hook_block_var,
                    ),
                ),
            )


def build_jmx_from_suite_ir(suite_ir: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    suite_info = _as_dict(suite_ir.get("suite"))
    load_profile = _as_dict(suite_ir.get("load_profile"))
    hooks_asset = _write_httprunner_hook_assets(suite_ir, output_dir)

    csv_assets = []
    for case_entry in _as_list(suite_ir.get("cases")):
        asset = _write_parameter_csv(_as_dict(case_entry), output_dir)
        if asset:
            csv_assets.append(asset)

    root = ET.Element(
        "jmeterTestPlan",
        {
            "version": "1.2",
            "properties": JMX_PROPERTIES_VERSION,
            "jmeter": JMX_VERSION,
        },
    )
    root_hash_tree = ET.SubElement(root, "hashTree")
    test_plan = _new_test_element("TestPlan", guiclass="TestPlanGui", testclass="TestPlan", testname=suite_info.get("name") or "Performance Suite")
    _string_prop(test_plan, "TestPlan.comments", suite_info.get("description") or "")
    _bool_prop(test_plan, "TestPlan.functional_mode", False)
    _bool_prop(test_plan, "TestPlan.serialize_threadgroups", False)
    test_plan.append(_test_plan_user_variables({}))
    _string_prop(test_plan, "TestPlan.user_define_classpath", "")
    test_plan_hash_tree = _append_element(root_hash_tree, test_plan)

    _append_element(test_plan_hash_tree, _cookie_manager_element())
    thread_group_hash_tree = _append_element(
        test_plan_hash_tree,
        _thread_group_element(load_profile, str(suite_info.get("name") or "Performance Suite")),
    )

    for case_entry in _as_list(suite_ir.get("cases")):
        case_map = _as_dict(case_entry)
        csv_asset = next((item for item in csv_assets if item.get("case_id") == case_map.get("case_id")), None)
        _build_case_tree(thread_group_hash_tree, case_map, csv_asset, hooks_asset)

    ET.indent(root)
    jmx_path = output_dir / f"{_sanitize_name(str(suite_info.get('name') or 'suite'), 'suite')}.jmx"
    tree = ET.ElementTree(root)
    tree.write(jmx_path, encoding="utf-8", xml_declaration=True)
    return {
        "jmx_path": str(jmx_path),
        "csv_files": csv_assets,
        "hooks_asset": hooks_asset or {},
    }


def validate_jmx_file(jmx_path: Path) -> dict[str, Any]:
    if not JMETER_EXECUTABLE.exists():
        return {
            "passed": False,
            "message": "JMeter executable not found",
        }

    with tempfile.TemporaryDirectory(prefix="jmeter-validate-") as temp_dir:
        temp_path = Path(temp_dir) / jmx_path.name
        temp_log_path = Path(temp_dir) / "jmeter-validate.log"
        shutil.copy2(jmx_path, temp_path)
        tree = ET.parse(temp_path)
        for element in tree.iter():
            if element.tag == "ThreadGroup":
                element.set("enabled", "false")
        ET.indent(tree.getroot())
        tree.write(temp_path, encoding="utf-8", xml_declaration=True)
        import subprocess

        completed = subprocess.run(
            [str(JMETER_EXECUTABLE), "-n", "-t", str(temp_path), "-j", str(temp_log_path)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part)
        failed_markers = ["Error in NonGUIDriver", "ConversionException", "errorlevel=1"]
        success = completed.returncode == 0 and not any(marker in output for marker in failed_markers)
        return {
            "passed": success,
            "return_code": completed.returncode,
            "message": "ok" if success else "jmeter validation failed",
            "output": output,
        }


def artifact_directory(base_dir: Path, suite_id: Any) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return base_dir / f"suite-{suite_id}" / timestamp
