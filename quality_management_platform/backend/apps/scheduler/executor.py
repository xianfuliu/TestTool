from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from django.conf import settings

from apps.interface_auto.execution_service import execute_case_run
from apps.interface_auto.views import _ensure_case_schema_extensions, _get_case_detail
from test_platform.db import fetch_all, fetch_one


def execute_task_target(task: dict[str, Any]) -> dict[str, Any]:
    target_type = str(task.get("task_type") or "").strip()
    target_config = _json_value(task.get("target_config"), {})

    if target_type == "test_case":
        return _execute_test_cases(target_config)
    if target_type == "test_suite":
        return _execute_test_suite(target_config)
    if target_type == "python_script":
        return _execute_python_script(target_config, int(task.get("timeout_seconds") or 1800))
    return {
        "status": "skipped",
        "message": f"任务类型 {target_type or 'unknown'} 暂未接入执行器",
        "summary": {},
        "logs": [],
    }


def _execute_test_suite(config: dict[str, Any]) -> dict[str, Any]:
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
        }
    )


def _execute_test_cases(config: dict[str, Any]) -> dict[str, Any]:
    case_ids = [_int_value(item) for item in config.get("case_ids") or []]
    case_ids = [item for item in case_ids if item]
    if not case_ids:
        raise ValueError("请至少选择一个接口用例")

    _ensure_case_schema_extensions()
    started_at = time.perf_counter()
    results: list[dict[str, Any]] = []
    for case_id in case_ids:
        case_detail = _get_case_detail(case_id)
        if not case_detail:
            results.append(
                {
                    "case_id": case_id,
                    "status": "failed",
                    "message": "用例不存在",
                }
            )
            continue
        results.append(execute_case_run(case_detail))

    failed = [item for item in results if item.get("status") != "success"]
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    return {
        "status": "failed" if failed else "success",
        "message": f"执行完成，成功 {len(results) - len(failed)} 个，失败 {len(failed)} 个",
        "summary": {
            "total_cases": len(results),
            "passed_cases": len(results) - len(failed),
            "failed_cases": len(failed),
            "duration_ms": duration_ms,
        },
        "results": results,
        "logs": [f"测试用例执行数量：{len(results)}"],
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
    return {
        "status": "success" if completed.returncode == 0 else "failed",
        "message": "脚本执行成功" if completed.returncode == 0 else f"脚本退出码：{completed.returncode}",
        "summary": {
            "return_code": completed.returncode,
            "duration_ms": duration_ms,
        },
        "stdout": output[-5000:],
        "stderr": error_output[-5000:],
        "logs": [line for line in [output[-5000:], error_output[-5000:]] if line],
    }


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


def _int_value(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
