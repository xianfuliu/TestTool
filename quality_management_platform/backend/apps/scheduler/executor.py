from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from django.conf import settings

from apps.interface_auto.execution_service import execute_case_run
from apps.interface_auto.views import _ensure_case_schema_extensions, _get_case_detail
from test_platform.db import fetch_all, fetch_one


MAX_SCHEDULER_LOG_LINES = 500
MAX_CASE_EXECUTION_LOG_LINES = 180
MAX_SCRIPT_OUTPUT_CHARS = 5000

LogProgressCallback = Callable[[list[dict[str, Any]], dict[str, Any]], None]


def execute_task_target(task: dict[str, Any], log_callback: LogProgressCallback | None = None) -> dict[str, Any]:
    target_type = str(task.get("task_type") or "").strip()
    target_config = _json_value(task.get("target_config"), {})

    if target_type == "test_case":
        return _execute_test_cases(target_config, log_callback=log_callback)
    if target_type == "test_suite":
        return _execute_test_suite(target_config, log_callback=log_callback)
    if target_type == "python_script":
        return _execute_python_script(target_config, int(task.get("timeout_seconds") or 1800))
    logs, logs_meta = trim_scheduler_logs(
        [
            make_log_line(
                f"任务类型 {target_type or 'unknown'} 暂未接入执行器",
                level="WARN",
                scope="调度",
            )
        ]
    )
    return {
        "status": "skipped",
        "message": f"任务类型 {target_type or 'unknown'} 暂未接入执行器",
        "summary": {},
        "logs": logs,
        "logs_meta": logs_meta,
    }


def _execute_test_suite(config: dict[str, Any], log_callback: LogProgressCallback | None = None) -> dict[str, Any]:
    suite_id = _int_value(config.get("suite_id"))
    if not suite_id:
        raise ValueError("请先绑定测试集")
    suite = fetch_one("SELECT * FROM test_suites WHERE id = %s", (suite_id,))
    if not suite:
        raise ValueError("测试集不存在")

    rows = fetch_all(
        """
        SELECT case_id
        FROM test_suite_cases
        WHERE suite_id = %s
        ORDER BY sort_order ASC, id ASC
        """,
        (suite_id,),
    )
    return _execute_test_cases(
        {
            "case_ids": [row["case_id"] for row in rows],
            "suite_id": suite_id,
            "suite_name": suite.get("name"),
        },
        log_callback=log_callback,
        create_individual_reports=False,
    )


def _execute_test_cases(
    config: dict[str, Any],
    log_callback: LogProgressCallback | None = None,
    *,
    create_individual_reports: bool = True,
) -> dict[str, Any]:
    case_ids = [_int_value(item) for item in config.get("case_ids") or []]
    case_ids = [item for item in case_ids if item]
    if not case_ids:
        raise ValueError("请至少选择一个接口用例")

    _ensure_case_schema_extensions()
    started_at = time.perf_counter()
    results: list[dict[str, Any]] = []
    logs: list[dict[str, Any]] = [
        make_log_line(f"开始执行接口用例任务，共 {len(case_ids)} 个用例", scope="调度", sub_scope="接口用例")
    ]
    _emit_progress(log_callback, logs)
    for case_id in case_ids:
        case_detail = _get_case_detail(case_id)
        if not case_detail:
            result = {
                "case_id": case_id,
                "case_name": f"用例 {case_id}",
                "status": "failed",
                "message": "用例不存在",
            }
            results.append(result)
            _append_case_result_logs(logs, result)
            _emit_progress(log_callback, logs)
            continue
        result = execute_case_run(case_detail, create_report=create_individual_reports)
        results.append(result)
        _append_case_result_logs(logs, result)
        _emit_progress(log_callback, logs)

    failed = [item for item in results if item.get("status") != "success"]
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    summary_message = f"执行完成，成功 {len(results) - len(failed)} 个，失败 {len(failed)} 个"
    logs.append(
        make_log_line(
            summary_message,
            level="ERROR" if failed else "INFO",
            scope="调度",
            sub_scope="接口用例",
        )
    )
    logs, logs_meta = trim_scheduler_logs(logs)
    return {
        "status": "failed" if failed else "success",
        "message": summary_message,
        "summary": {
            "total_cases": len(results),
            "passed_cases": len(results) - len(failed),
            "failed_cases": len(failed),
            "duration_ms": duration_ms,
        },
        "results": results,
        "logs": logs,
        "logs_meta": logs_meta,
    }


def _append_case_result_logs(logs: list[dict[str, Any]], result: dict[str, Any]) -> None:
    case_name = str(result.get("case_name") or result.get("case_id") or "未命名用例")
    status = str(result.get("status") or "unknown")
    message = str(result.get("message") or "")
    status_label = "成功" if status == "success" else "失败" if status == "failed" else "跳过"
    logs.append(
        make_log_line(
            f"[{status_label}] {case_name}: {message or status}",
            level="ERROR" if status == "failed" else "WARN" if status == "skipped" else "INFO",
            scope="用例",
            sub_scope=case_name,
            meta={"case_id": result.get("case_id"), "status": status},
        )
    )

    if status == "success":
        return
    execution_lines = _case_execution_log_lines(result)
    if not execution_lines:
        return
    logs.append(
        make_log_line(
            f"{case_name} 失败执行日志：",
            level="ERROR",
            scope="用例",
            sub_scope=case_name,
        )
    )
    logs.extend(execution_lines[-MAX_CASE_EXECUTION_LOG_LINES:])


def _case_execution_log_lines(result: dict[str, Any]) -> list[dict[str, Any]]:
    execution_log = _as_dict(result.get("execution_log"))
    raw_lines = execution_log.get("lines")
    if not isinstance(raw_lines, list):
        return []
    case_name = str(result.get("case_name") or result.get("case_id") or "未命名用例")
    return [
        normalise_log_line(_as_dict(line), fallback_scope="用例执行", fallback_sub_scope=case_name)
        for line in raw_lines
        if isinstance(line, dict)
    ]


def trim_scheduler_logs(logs: list[Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalised = normalise_log_lines(logs)
    if len(logs) <= MAX_SCHEDULER_LOG_LINES:
        return normalised, {
            "truncated": False,
            "omitted": 0,
            "limit": MAX_SCHEDULER_LOG_LINES,
            "total": len(normalised),
        }
    omitted = len(normalised) - MAX_SCHEDULER_LOG_LINES
    marker = make_log_line(
        f"... 已省略 {omitted} 行日志 ...",
        level="WARN",
        scope="调度",
        meta={"omitted": omitted},
    )
    return normalised[:40] + [marker] + normalised[-(MAX_SCHEDULER_LOG_LINES - 41):], {
        "truncated": True,
        "omitted": omitted,
        "limit": MAX_SCHEDULER_LOG_LINES,
        "total": len(normalised),
    }


def _execute_python_script(config: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    script_path = str(config.get("script_path") or "").strip()
    if not script_path:
        raise ValueError("请配置 Python 脚本路径")

    resolved_script = _resolve_script_path(script_path)
    if not resolved_script.exists() or not resolved_script.is_file():
        raise ValueError(f"Python 脚本不存在：{script_path}")

    args = config.get("args") or []
    if isinstance(args, str):
        args = [item for item in args.split() if item]
    if not isinstance(args, list):
        args = []

    working_dir = str(config.get("working_dir") or "").strip()
    cwd = _resolve_working_dir(working_dir) if working_dir else str(resolved_script.parent)
    timeout = max(1, min(timeout_seconds or 1800, 24 * 3600))
    started_at = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, str(resolved_script), *[str(item) for item in args]],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    output = (completed.stdout or "").strip()
    error_output = (completed.stderr or "").strip()
    logs: list[dict[str, Any]] = [
        make_log_line(
            f"Python 脚本执行完成，退出码 {completed.returncode}",
            level="INFO" if completed.returncode == 0 else "ERROR",
            scope="Python",
            meta={"return_code": completed.returncode, "script_path": str(resolved_script)},
        )
    ]
    logs.extend(
        _text_block_to_log_lines(
            output[-MAX_SCRIPT_OUTPUT_CHARS:],
            level="INFO",
            scope="Python",
            sub_scope="stdout",
        )
    )
    logs.extend(
        _text_block_to_log_lines(
            error_output[-MAX_SCRIPT_OUTPUT_CHARS:],
            level="ERROR",
            scope="Python",
            sub_scope="stderr",
        )
    )
    logs, logs_meta = trim_scheduler_logs(logs)
    return {
        "status": "success" if completed.returncode == 0 else "failed",
        "message": "脚本执行成功" if completed.returncode == 0 else f"脚本退出码：{completed.returncode}",
        "summary": {
            "return_code": completed.returncode,
            "duration_ms": duration_ms,
        },
        "stdout": output[-MAX_SCRIPT_OUTPUT_CHARS:],
        "stderr": error_output[-MAX_SCRIPT_OUTPUT_CHARS:],
        "logs": logs,
        "logs_meta": logs_meta,
    }


def _emit_progress(callback: LogProgressCallback | None, logs: list[dict[str, Any]]) -> None:
    if not callback:
        return
    trimmed, logs_meta = trim_scheduler_logs(logs)
    callback(trimmed, logs_meta)


def _text_block_to_log_lines(
    value: str,
    *,
    level: str,
    scope: str,
    sub_scope: str = "",
) -> list[dict[str, Any]]:
    if not value:
        return []
    return [
        make_log_line(line, level=level, scope=scope, sub_scope=sub_scope, raw=line)
        for line in value.splitlines()
        if line.strip()
    ]


def make_log_line(
    message: Any,
    *,
    level: str = "INFO",
    scope: str = "调度",
    sub_scope: str = "",
    subject: str = "",
    raw: Any = None,
    meta: dict[str, Any] | None = None,
    time_value: Any = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "time": str(time_value or datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "level": str(level or "INFO").upper(),
        "scope": str(scope or "调度"),
        "sub_scope": str(sub_scope or ""),
        "subject": str(subject or ""),
        "message": str(message or ""),
    }
    if raw not in (None, ""):
        item["raw"] = raw
    if meta:
        item["meta"] = meta
    return item


def normalise_log_lines(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [normalise_log_line(item) for item in value if item not in (None, "")]


def normalise_log_line(
    value: Any,
    *,
    fallback_scope: str = "调度",
    fallback_sub_scope: str = "",
) -> dict[str, Any]:
    if isinstance(value, dict):
        level = str(value.get("level") or _infer_log_level(value.get("message") or value.get("content"))).upper()
        return make_log_line(
            value.get("message") or value.get("content") or value.get("description") or "",
            level=level,
            scope=str(value.get("scope") or value.get("category") or fallback_scope),
            sub_scope=str(value.get("sub_scope") or value.get("subScope") or fallback_sub_scope),
            subject=str(value.get("subject") or value.get("tool_name") or value.get("toolName") or ""),
            raw=value.get("raw"),
            meta=_as_dict(value.get("meta")) or None,
            time_value=value.get("time") or value.get("timestamp") or value.get("created_at"),
        )
    text = str(value)
    return make_log_line(text, level=_infer_log_level(text), scope=fallback_scope, sub_scope=fallback_sub_scope, raw=text)


def _infer_log_level(value: Any) -> str:
    text = str(value or "").lower()
    if any(keyword in text for keyword in ("error", "exception", "traceback", "失败", "异常", "错误", "超时")):
        return "ERROR"
    if any(keyword in text for keyword in ("warn", "warning", "跳过", "省略")):
        return "WARN"
    if "debug" in text:
        return "DEBUG"
    return "INFO"


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


def _json_value(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int_value(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
