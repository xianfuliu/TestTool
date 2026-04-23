from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from django.conf import settings

from apps.common.request_execution import json_dumps, replace_template_text


@dataclass
class PythonExecutionContext:
    variables: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 60
    allow_legacy_placeholders: bool = False


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _resolve_script_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (Path(settings.BASE_DIR) / "scripts" / path).resolve()


def _resolve_working_dir(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((Path(settings.BASE_DIR) / path).resolve())


def _normalise_args(value: Any, context: PythonExecutionContext) -> list[str]:
    if isinstance(value, str):
        raw_args = shlex.split(value)
    elif isinstance(value, list):
        raw_args = value
    else:
        raw_args = []
    return [
        replace_template_text(
            str(item),
            context.variables,
            allow_legacy_placeholders=context.allow_legacy_placeholders,
        )
        for item in raw_args
    ]


def _normalise_output_fields(value: Any) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    raw_items = [item.strip() for item in value.split(",") if item.strip()] if isinstance(value, str) else _as_list(value)
    for item in raw_items:
        if isinstance(item, str):
            field_name = item.strip()
            variable_name = field_name
        else:
            item_map = _as_dict(item)
            field_name = str(item_map.get("field") or item_map.get("name") or item_map.get("source") or "").strip()
            variable_name = str(item_map.get("variable") or item_map.get("output") or item_map.get("name") or field_name).strip()
        if field_name or variable_name:
            fields.append({"field": field_name or variable_name, "variable": variable_name or field_name})
    return fields


def _build_inline_script(content: str, output_fields: Any) -> str:
    field_names = [item["field"] for item in _normalise_output_fields(output_fields)]
    epilogue = "\n".join(
        [
            "",
            "import json as __testtool_json",
            f"__testtool_output_fields = __testtool_json.loads({json.dumps(field_names, ensure_ascii=False)!r})",
            "if __testtool_output_fields:",
            "    __testtool_outputs = {}",
            "    for __testtool_field in __testtool_output_fields:",
            "        if __testtool_field in globals():",
            "            __testtool_outputs[__testtool_field] = globals()[__testtool_field]",
            "    print(__testtool_json.dumps(__testtool_outputs, ensure_ascii=False, default=str))",
            "",
        ]
    )
    return f"{content.rstrip()}\n{epilogue}"


def _parse_stdout_body(stdout: str) -> Any:
    text = stdout.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        pass
    for line in reversed([item.strip() for item in text.splitlines() if item.strip()]):
        try:
            return json.loads(line)
        except (TypeError, ValueError):
            continue
    return text


def _render_script_content(content: str, context: PythonExecutionContext) -> str:
    return replace_template_text(
        content,
        context.variables,
        allow_legacy_placeholders=context.allow_legacy_placeholders,
    )


def _script_content_has_template(content: str) -> bool:
    return "${" in content


def _write_temp_script(content: str) -> str:
    script_file = tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False)
    try:
        script_file.write(content)
        return script_file.name
    finally:
        script_file.close()


def execute_python_script(config: dict[str, Any], context: PythonExecutionContext | None = None) -> dict[str, Any]:
    context = context or PythonExecutionContext()
    script_path = str(config.get("script_path") or config.get("path") or "").strip()
    script_content = str(config.get("script") or config.get("script_text") or config.get("code") or "").strip()
    if not script_path and not script_content:
        raise ValueError("请配置 Python 脚本路径或脚本内容")

    raw_args = config.get("args") or []
    rendered_temp_script: str | None = None
    source_script_path = ""
    if script_path:
        resolved_script = _resolve_script_path(script_path)
        if not resolved_script.exists() or not resolved_script.is_file():
            raise ValueError(f"Python 脚本不存在：{script_path}")
        source_script_path = str(resolved_script)
        original_content = resolved_script.read_text(encoding=str(config.get("encoding") or "utf-8"))
        render_template = config.get("render_template", True) is not False
        if render_template and _script_content_has_template(original_content):
            rendered_temp_script = _write_temp_script(_render_script_content(original_content, context))
            executable_script = rendered_temp_script
        else:
            executable_script = str(resolved_script)
        default_cwd = str(resolved_script.parent)
    else:
        rendered_script = _render_script_content(script_content, context)
        rendered_temp_script = _write_temp_script(
            _build_inline_script(rendered_script, config.get("output_fields") or [])
        )
        executable_script = rendered_temp_script
        default_cwd = str(Path(settings.BASE_DIR))

    working_dir = str(config.get("working_dir") or config.get("cwd") or "").strip()
    cwd = _resolve_working_dir(working_dir) if working_dir else default_cwd
    args = _normalise_args(raw_args, context)
    timeout = max(1, min(int(config.get("timeout_seconds") or context.timeout_seconds or 60), 24 * 3600))
    env = dict(os.environ)
    env["TESTTOOL_VARIABLES"] = json_dumps(context.variables)
    env["PYTHONIOENCODING"] = "utf-8"
    if source_script_path:
        env["PYTHONPATH"] = os.pathsep.join(
            [str(Path(source_script_path).parent), env.get("PYTHONPATH", "")]
        ).strip(os.pathsep)

    command = [sys.executable, executable_script, *args]
    started_at = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return_code = completed.returncode
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        error_message = "" if return_code == 0 else f"Python 脚本退出码：{return_code}"
    except subprocess.TimeoutExpired as exc:
        return_code = -1
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        error_message = f"Python 脚本执行超时：{timeout}s"
    finally:
        if rendered_temp_script:
            try:
                Path(rendered_temp_script).unlink(missing_ok=True)
            except OSError:
                pass

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    body = _parse_stdout_body(stdout)
    return {
        "request": {
            "script_path": source_script_path or script_path,
            "working_dir": cwd,
            "args": args,
            "timeout_seconds": timeout,
            "render_template": config.get("render_template", True) is not False,
        },
        "status": "success" if return_code == 0 else "failed",
        "status_code": return_code,
        "return_code": return_code,
        "headers": {},
        "body": body,
        "raw_body": stdout,
        "decrypted_body": body,
        "stdout": stdout,
        "stderr": stderr,
        "duration_ms": duration_ms,
        "error_message": error_message,
    }


def extract_python_output_variables(body: Any, output_fields: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    body_map = _as_dict(body)
    fields = _normalise_output_fields(output_fields)
    if not body_map:
        return {}, [
            {
                "variable": item["variable"],
                "path": item["field"],
                "resolved_path": item["field"],
                "matched": False,
                "value": None,
            }
            for item in fields
        ]
    if not fields:
        fields = [{"field": key, "variable": key} for key in body_map.keys()]
    extracted: dict[str, Any] = {}
    details: list[dict[str, Any]] = []
    for item in fields:
        field_name = item["field"]
        variable_name = item["variable"]
        if not field_name or not variable_name:
            continue
        matched = field_name in body_map
        value = body_map.get(field_name)
        if matched:
            extracted[variable_name] = value
        details.append(
            {
                "variable": variable_name,
                "path": field_name,
                "resolved_path": field_name,
                "matched": matched,
                "value": value,
            }
        )
    return extracted, details
