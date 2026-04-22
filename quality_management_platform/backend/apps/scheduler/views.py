from __future__ import annotations

import json
import time
import traceback
from datetime import datetime, timedelta
from typing import Any

from apps.common.http import api_view, get_int
from test_platform.db import execute, fetch_all, fetch_one

from .cron import CronExpressionError, get_next_cron_time, validate_cron_expression
from .executor import execute_task_target, make_log_line, normalise_log_lines, trim_scheduler_logs


TASK_TYPES = {"test_suite", "test_case", "python_script", "http_callback", "custom"}
SCHEDULE_TYPES = {"cron", "interval", "once", "manual"}
MISFIRE_POLICIES = {"fire_once", "skip", "fire_all"}
RUN_RETENTION_COUNT = 200  # 单个任务只保留最近200条执行记录
RUN_RETENTION_DAYS = 7  # 保留最近7天的执行记录


def _ensure_schema_ready() -> None:
    execute(
        """
        CREATE TABLE IF NOT EXISTS scheduler_tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            business_group_id INT NULL,
            project_id INT NULL,
            name VARCHAR(120) NOT NULL,
            task_type VARCHAR(40) DEFAULT 'test_suite',
            source_module VARCHAR(80) DEFAULT '',
            source_id INT NULL,
            description TEXT,
            schedule_type VARCHAR(30) DEFAULT 'cron',
            cron_expression VARCHAR(120) DEFAULT '',
            interval_seconds INT DEFAULT 0,
            run_at DATETIME NULL,
            timezone VARCHAR(64) DEFAULT 'Asia/Shanghai',
            target_config LONGTEXT NULL,
            notify_config LONGTEXT NULL,
            misfire_policy VARCHAR(30) DEFAULT 'fire_once',
            allow_concurrent BOOLEAN DEFAULT FALSE,
            timeout_seconds INT DEFAULT 1800,
            retry_count INT DEFAULT 0,
            retry_interval_seconds INT DEFAULT 30,
            enabled BOOLEAN DEFAULT FALSE,
            status VARCHAR(30) DEFAULT 'idle',
            last_run_status VARCHAR(30) DEFAULT '',
            last_run_message TEXT NULL,
            last_run_at DATETIME NULL,
            next_run_at DATETIME NULL,
            run_count INT DEFAULT 0,
            fail_count INT DEFAULT 0,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_scheduler_tasks_project_id (project_id),
            INDEX idx_scheduler_tasks_business_group_id (business_group_id),
            INDEX idx_scheduler_tasks_enabled_next_run (enabled, next_run_at),
            INDEX idx_scheduler_tasks_source (source_module, source_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    execute(
        """
        CREATE TABLE IF NOT EXISTS scheduler_task_runs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            task_id INT NOT NULL,
            trigger_type VARCHAR(30) DEFAULT 'manual',
            status VARCHAR(30) DEFAULT 'running',
            started_at DATETIME NULL,
            finished_at DATETIME NULL,
            duration_ms FLOAT DEFAULT 0,
            executor VARCHAR(60) DEFAULT 'web',
            retry_no INT DEFAULT 0,
            message TEXT NULL,
            request_snapshot LONGTEXT NULL,
            result_snapshot LONGTEXT NULL,
            logs LONGTEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_scheduler_task_runs_task_id (task_id),
            INDEX idx_scheduler_task_runs_status (status),
            INDEX idx_scheduler_task_runs_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )


def _json_text(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _json_value(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _bool_value(value: Any, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _datetime_value(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip().replace("T", " ")
    if text.endswith("Z"):
        text = text[:-1]
    for pattern, text_length in (
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d %H:%M", 16),
        ("%Y-%m-%d", 10),
    ):
        try:
            return datetime.strptime(text[:text_length], pattern)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"时间格式不正确：{value}") from exc


def _datetime_param(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


def _normalise_target_config(task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    config = _json_value(payload.get("target_config"), {})
    if not isinstance(config, dict):
        config = {}

    if task_type == "test_suite":
        suite_id = get_int(config.get("suite_id") or payload.get("suite_id"))
        if suite_id:
            if not fetch_one("SELECT id FROM test_suites WHERE id = %s", (suite_id,)):
                raise ValueError("测试集不存在")
            config["suite_id"] = suite_id
        return config

    if task_type == "test_case":
        raw_case_ids = config.get("case_ids") or payload.get("case_ids") or []
        case_ids: list[int] = []
        for item in raw_case_ids:
            case_id = get_int(item)
            if case_id:
                case_ids.append(case_id)
        if not case_ids:
            raise ValueError("接口用例任务请至少选择一个用例")
        config["case_ids"] = case_ids
        return config

    if task_type == "python_script":
        config["script_path"] = str(config.get("script_path") or payload.get("script_path") or "").strip()
        config["working_dir"] = str(config.get("working_dir") or payload.get("working_dir") or "").strip()
        args = config.get("args", payload.get("args", []))
        config["args"] = args if isinstance(args, list) else str(args or "").strip()
        return config

    if task_type == "http_callback":
        config["url"] = str(config.get("url") or payload.get("url") or "").strip()
        config["method"] = str(config.get("method") or payload.get("method") or "POST").upper()
        config["body"] = config.get("body") or payload.get("body") or {}
        return config

    return config


def _normalise_payload(payload: dict[str, Any], *, current_id: int | None = None) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("请输入任务名称")

    task_type = str(payload.get("task_type") or "test_suite").strip()
    if task_type not in TASK_TYPES:
        raise ValueError("任务类型不支持")

    schedule_type = str(payload.get("schedule_type") or "cron").strip()
    if schedule_type not in SCHEDULE_TYPES:
        raise ValueError("调度类型不支持")

    business_group_id = get_int(payload.get("business_group_id"))
    project_id = get_int(payload.get("project_id"))
    if project_id:
        project = fetch_one("SELECT id, business_group_id FROM projects WHERE id = %s", (project_id,))
        if not project:
            raise ValueError("所属项目不存在")
        business_group_id = business_group_id or project.get("business_group_id")
    if business_group_id and not fetch_one("SELECT id FROM business_groups WHERE id = %s", (business_group_id,)):
        raise ValueError("所属业务不存在")

    target_config = _normalise_target_config(task_type, payload)
    enabled = _bool_value(payload.get("enabled"), False)
    if enabled and task_type == "test_suite" and not target_config.get("suite_id"):
        raise ValueError("启用测试集任务前请先绑定测试集")
    if enabled and task_type == "python_script" and not target_config.get("script_path"):
        raise ValueError("启用 Python 脚本任务前请先配置脚本路径")

    cron_expression = str(payload.get("cron_expression") or "").strip()
    interval_seconds = get_int(payload.get("interval_seconds"), 0) or 0
    run_at = _datetime_value(payload.get("run_at"))

    if schedule_type == "cron":
        if not cron_expression:
            raise ValueError("请输入 Cron 表达式")
        try:
            validate_cron_expression(cron_expression)
        except CronExpressionError as exc:
            raise ValueError(str(exc)) from exc
    if schedule_type == "interval" and interval_seconds < 60:
        raise ValueError("固定间隔不能小于 60 秒")
    if schedule_type == "once" and not run_at:
        raise ValueError("单次执行请配置执行时间")

    existed_params: list[Any] = [name]
    existed_sql = "SELECT id FROM scheduler_tasks WHERE name = %s"
    if project_id:
        existed_sql += " AND project_id = %s"
        existed_params.append(project_id)
    else:
        existed_sql += " AND project_id IS NULL"
    if current_id:
        existed_sql += " AND id <> %s"
        existed_params.append(current_id)
    if fetch_one(existed_sql, existed_params):
        raise ValueError("当前项目下已存在同名定时任务")

    misfire_policy = str(payload.get("misfire_policy") or "fire_once").strip()
    if misfire_policy not in MISFIRE_POLICIES:
        misfire_policy = "fire_once"

    item = {
        "business_group_id": business_group_id,
        "project_id": project_id,
        "name": name,
        "task_type": task_type,
        "source_module": str(payload.get("source_module") or "").strip(),
        "source_id": get_int(payload.get("source_id")),
        "description": str(payload.get("description") or "").strip(),
        "schedule_type": schedule_type,
        "cron_expression": cron_expression,
        "interval_seconds": interval_seconds,
        "run_at": run_at,
        "timezone": str(payload.get("timezone") or "Asia/Shanghai").strip() or "Asia/Shanghai",
        "target_config": target_config,
        "notify_config": _json_value(payload.get("notify_config"), {}),
        "misfire_policy": misfire_policy,
        "allow_concurrent": _bool_value(payload.get("allow_concurrent"), False),
        "timeout_seconds": get_int(payload.get("timeout_seconds"), 1800) or 1800,
        "retry_count": get_int(payload.get("retry_count"), 0) or 0,
        "retry_interval_seconds": get_int(payload.get("retry_interval_seconds"), 30) or 30,
        "enabled": enabled,
    }
    item["next_run_at"] = _calculate_next_run(item) if enabled else None
    return item


def _calculate_next_run(item: dict[str, Any], base_time: datetime | None = None) -> datetime | None:
    schedule_type = item.get("schedule_type")
    base = base_time or datetime.now()
    if schedule_type == "manual":
        return None
    if schedule_type == "once":
        run_at = item.get("run_at")
        return run_at if isinstance(run_at, datetime) and run_at > base else None
    if schedule_type == "interval":
        seconds = int(item.get("interval_seconds") or 0)
        if seconds <= 0:
            return None
        candidate = base + timedelta(seconds=seconds)
        return candidate.replace(microsecond=0)
    if schedule_type == "cron":
        return get_next_cron_time(str(item.get("cron_expression") or ""), base)
    return None


def _task_query_base() -> str:
    return """
        SELECT
            st.*,
            bg.name AS business_group_name,
            p.name AS project_name
        FROM scheduler_tasks st
        LEFT JOIN business_groups bg ON st.business_group_id = bg.id
        LEFT JOIN projects p ON st.project_id = p.id
    """


def _hydrate_task(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    item = dict(row)
    item["target_config"] = _json_value(item.get("target_config"), {})
    item["notify_config"] = _json_value(item.get("notify_config"), {})
    item["enabled"] = bool(item.get("enabled"))
    item["allow_concurrent"] = bool(item.get("allow_concurrent"))
    return item


def _hydrate_run(row: dict[str, Any] | None, *, include_detail: bool = True) -> dict[str, Any] | None:
    if not row:
        return None
    item = dict(row)
    if include_detail:
        item["request_snapshot"] = _json_value(item.get("request_snapshot"), {})
        item["result_snapshot"] = _json_value(item.get("result_snapshot"), {})
        item["logs"] = normalise_log_lines(_json_value(item.get("logs"), []))
        item["logs_meta"] = _logs_meta_from_result(item["result_snapshot"])
        item["details_loaded"] = True
    else:
        item["request_snapshot"] = {}
        item["result_snapshot"] = {}
        item["logs"] = []
        item["logs_meta"] = {}
        item["details_loaded"] = False
    item["has_detail"] = True
    return item


def _logs_meta_from_result(result_snapshot: Any) -> dict[str, Any]:
    result = result_snapshot if isinstance(result_snapshot, dict) else {}
    meta = result.get("logs_meta")
    return meta if isinstance(meta, dict) else {}


def _run_status_label(status: str) -> str:
    if status == "success":
        return "成功"
    if status == "failed":
        return "失败"
    if status == "skipped":
        return "跳过"
    return status


def _persist_run_progress(
    run_id: int,
    logs: list[Any],
    *,
    status: str = "running",
    message: str = "",
    result_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trimmed_logs, logs_meta = trim_scheduler_logs(logs)
    result = dict(result_snapshot or {})
    result["logs_meta"] = logs_meta
    execute(
        """
        UPDATE scheduler_task_runs
        SET status = %s,
            message = %s,
            result_snapshot = %s,
            logs = %s
        WHERE id = %s
        """,
        (status, message, _json_text(result), _json_text(trimmed_logs), run_id),
    )
    return {"logs": trimmed_logs, "logs_meta": logs_meta, "result_snapshot": result}


def _prune_task_runs(task_id: int) -> None:
    cutoff = datetime.now() - timedelta(days=RUN_RETENTION_DAYS)
    execute(
        """
        DELETE FROM scheduler_task_runs
        WHERE task_id = %s
          AND status <> 'running'
          AND created_at < %s
        """,
        (task_id, _datetime_param(cutoff)),
    )
    execute(
        """
        DELETE FROM scheduler_task_runs
        WHERE task_id = %s
          AND status <> 'running'
          AND id NOT IN (
              SELECT id FROM (
                  SELECT id
                  FROM scheduler_task_runs
                  WHERE task_id = %s
                  ORDER BY created_at DESC, id DESC
                  LIMIT %s
              ) retained_runs
          )
        """,
        (task_id, task_id, RUN_RETENTION_COUNT),
    )


@api_view
def context(_request, payload=None):
    _ensure_schema_ready()
    project_id = get_int((payload or {}).get("project_id"))
    project_filter = "WHERE p.id = %s" if project_id else ""
    params = (project_id,) if project_id else ()
    return {
        "business_groups": fetch_all("SELECT * FROM business_groups ORDER BY created_at ASC"),
        "projects": fetch_all(
            """
            SELECT p.*, bg.name AS business_group_name
            FROM projects p
            LEFT JOIN business_groups bg ON p.business_group_id = bg.id
            ORDER BY p.created_at ASC
            """
        ),
        "test_suites": fetch_all(
            f"""
            SELECT ts.*, p.name AS project_name, bg.name AS business_group_name
            FROM test_suites ts
            LEFT JOIN projects p ON ts.project_id = p.id
            LEFT JOIN business_groups bg ON p.business_group_id = bg.id
            {project_filter}
            ORDER BY ts.updated_at DESC, ts.id DESC
            """,
            params,
        ),
        "test_cases": fetch_all(
            f"""
            SELECT tc.id, tc.project_id, tc.name, tc.description, tc.updated_at,
                   p.name AS project_name, bg.name AS business_group_name
            FROM test_cases tc
            LEFT JOIN projects p ON tc.project_id = p.id
            LEFT JOIN business_groups bg ON p.business_group_id = bg.id
            {project_filter.replace('p.id', 'tc.project_id')}
            ORDER BY tc.updated_at DESC, tc.id DESC
            """,
            params,
        ),
    }


@api_view
def tasks(request, payload=None):
    _ensure_schema_ready()
    if request.method == "GET":
        keyword = str((payload or {}).get("keyword") or "").strip()
        business_group_id = get_int((payload or {}).get("business_group_id"))
        project_id = get_int((payload or {}).get("project_id"))
        task_type = str((payload or {}).get("task_type") or "").strip()
        enabled = str((payload or {}).get("enabled") or "").strip()
        conditions: list[str] = []
        params: list[Any] = []
        if business_group_id:
            conditions.append("st.business_group_id = %s")
            params.append(business_group_id)
        if project_id:
            conditions.append("st.project_id = %s")
            params.append(project_id)
        if task_type:
            conditions.append("st.task_type = %s")
            params.append(task_type)
        if enabled in {"true", "false"}:
            conditions.append("st.enabled = %s")
            params.append(enabled == "true")
        if keyword:
            like_value = f"%{keyword}%"
            conditions.append("(st.name LIKE %s OR st.description LIKE %s)")
            params.extend([like_value, like_value])
        where_sql = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = fetch_all(
            f"""
            {_task_query_base()}
            {where_sql}
            ORDER BY st.updated_at DESC, st.id DESC
            """,
            params,
        )
        return [_hydrate_task(row) for row in rows]

    item = _normalise_payload(payload or {})
    task_id = execute(
        """
        INSERT INTO scheduler_tasks (
            business_group_id, project_id, name, task_type, source_module, source_id, description,
            schedule_type, cron_expression, interval_seconds, run_at, timezone, target_config, notify_config,
            misfire_policy, allow_concurrent, timeout_seconds, retry_count, retry_interval_seconds,
            enabled, next_run_at, created_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            item["business_group_id"],
            item["project_id"],
            item["name"],
            item["task_type"],
            item["source_module"],
            item["source_id"],
            item["description"],
            item["schedule_type"],
            item["cron_expression"],
            item["interval_seconds"],
            _datetime_param(item["run_at"]),
            item["timezone"],
            _json_text(item["target_config"]),
            _json_text(item["notify_config"]),
            item["misfire_policy"],
            item["allow_concurrent"],
            item["timeout_seconds"],
            item["retry_count"],
            item["retry_interval_seconds"],
            item["enabled"],
            _datetime_param(item["next_run_at"]),
            "admin",
        ),
    )
    return {"task_id": task_id}, 201


@api_view
def task_detail(request, task_id: int, payload=None):
    _ensure_schema_ready()
    row = fetch_one(f"{_task_query_base()} WHERE st.id = %s", (task_id,))
    if not row:
        raise ValueError("定时任务不存在")
    if request.method == "GET":
        return _hydrate_task(row)
    if request.method == "PUT":
        item = _normalise_payload(payload or {}, current_id=task_id)
        updated = execute(
            """
            UPDATE scheduler_tasks
            SET business_group_id = %s,
                project_id = %s,
                name = %s,
                task_type = %s,
                source_module = %s,
                source_id = %s,
                description = %s,
                schedule_type = %s,
                cron_expression = %s,
                interval_seconds = %s,
                run_at = %s,
                timezone = %s,
                target_config = %s,
                notify_config = %s,
                misfire_policy = %s,
                allow_concurrent = %s,
                timeout_seconds = %s,
                retry_count = %s,
                retry_interval_seconds = %s,
                enabled = %s,
                next_run_at = %s
            WHERE id = %s
            """,
            (
                item["business_group_id"],
                item["project_id"],
                item["name"],
                item["task_type"],
                item["source_module"],
                item["source_id"],
                item["description"],
                item["schedule_type"],
                item["cron_expression"],
                item["interval_seconds"],
                _datetime_param(item["run_at"]),
                item["timezone"],
                _json_text(item["target_config"]),
                _json_text(item["notify_config"]),
                item["misfire_policy"],
                item["allow_concurrent"],
                item["timeout_seconds"],
                item["retry_count"],
                item["retry_interval_seconds"],
                item["enabled"],
                _datetime_param(item["next_run_at"]),
                task_id,
            ),
        )
        return {"updated": updated >= 0}
    execute("DELETE FROM scheduler_task_runs WHERE task_id = %s", (task_id,))
    return {"deleted": execute("DELETE FROM scheduler_tasks WHERE id = %s", (task_id,)) > 0}


@api_view
def task_status(_request, task_id: int, payload=None):
    _ensure_schema_ready()
    task = _hydrate_task(fetch_one(f"{_task_query_base()} WHERE st.id = %s", (task_id,)))
    if not task:
        raise ValueError("定时任务不存在")
    enabled = _bool_value((payload or {}).get("enabled"), False)
    item = {**task, "enabled": enabled}
    next_run_at = _calculate_next_run(item) if enabled else None
    updated = execute(
        "UPDATE scheduler_tasks SET enabled = %s, next_run_at = %s WHERE id = %s",
        (enabled, _datetime_param(next_run_at), task_id),
    )
    return {"updated": updated >= 0, "enabled": enabled, "next_run_at": next_run_at}


@api_view
def task_runs(_request, task_id: int, payload=None):
    _ensure_schema_ready()
    page = get_int((payload or {}).get("page"), 1) or 1
    page_size = get_int((payload or {}).get("page_size") or (payload or {}).get("limit"), 20) or 20
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size
    total_row = fetch_one("SELECT COUNT(*) AS total FROM scheduler_task_runs WHERE task_id = %s", (task_id,))
    rows = fetch_all(
        """
        SELECT
            id,
            task_id,
            trigger_type,
            status,
            started_at,
            finished_at,
            duration_ms,
            executor,
            retry_no,
            message,
            created_at,
            CHAR_LENGTH(COALESCE(logs, '')) AS logs_size,
            CHAR_LENGTH(COALESCE(result_snapshot, '')) AS result_size
        FROM scheduler_task_runs
        WHERE task_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT %s OFFSET %s
        """,
        (task_id, page_size, offset),
    )
    return {
        "items": [_hydrate_run(row, include_detail=False) for row in rows],
        "total": int((total_row or {}).get("total") or 0),
        "page": page,
        "page_size": page_size,
        "retention": {
            "count": RUN_RETENTION_COUNT,
            "days": RUN_RETENTION_DAYS,
        },
    }


@api_view
def task_run_detail(_request, task_id: int, run_id: int, payload=None):
    _ensure_schema_ready()
    row = fetch_one(
        """
        SELECT *
        FROM scheduler_task_runs
        WHERE task_id = %s AND id = %s
        """,
        (task_id, run_id),
    )
    if not row:
        raise ValueError("执行记录不存在")
    return _hydrate_run(row, include_detail=True)


def execute_scheduler_task(
    task_id: int,
    *,
    trigger_type: str = "manual",
    executor: str = "web",
) -> dict[str, Any]:
    _ensure_schema_ready()
    task = _hydrate_task(fetch_one(f"{_task_query_base()} WHERE st.id = %s", (task_id,)))
    if not task:
        raise ValueError("定时任务不存在")
    if not task.get("allow_concurrent"):
        running = fetch_one(
            "SELECT id FROM scheduler_task_runs WHERE task_id = %s AND status = 'running' LIMIT 1",
            (task_id,),
        )
        if running:
            raise ValueError("当前任务正在执行，未开启并发执行")

    started_at = datetime.now()
    logs: list[dict[str, Any]] = [
        make_log_line(
            "任务开始执行",
            scope="调度",
            meta={"task_id": task_id, "task_name": task.get("name"), "task_type": task.get("task_type")},
        )
    ]
    run_id = execute(
        """
        INSERT INTO scheduler_task_runs
            (task_id, trigger_type, status, started_at, executor, request_snapshot, logs)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            task_id,
            trigger_type,
            "running",
            _datetime_param(started_at),
            executor,
            _json_text({"task_id": task_id, "task_name": task.get("name"), "task_type": task.get("task_type")}),
            _json_text(logs),
        ),
    )
    execute("UPDATE scheduler_tasks SET status = 'running' WHERE id = %s", (task_id,))

    started = time.perf_counter()
    max_retries = max(0, int(task.get("retry_count") or 0))
    retry_interval = max(0, int(task.get("retry_interval_seconds") or 0))
    attempts: list[dict[str, Any]] = []
    status = "failed"
    message = ""
    result: dict[str, Any] = {}

    for retry_no in range(max_retries + 1):
        attempt_started = datetime.now()
        attempt_timer = time.perf_counter()
        logs.append(
            make_log_line(
                f"第 {retry_no + 1} 次执行开始",
                scope="调度",
                sub_scope="重试" if retry_no else "首次执行",
                meta={"retry_no": retry_no},
            )
        )
        _persist_run_progress(run_id, logs, message=f"第 {retry_no + 1} 次执行中")
        attempt_offset = len(logs)

        def persist_attempt_progress(partial_logs: list[dict[str, Any]], _logs_meta: dict[str, Any]) -> None:
            _persist_run_progress(
                run_id,
                logs[:attempt_offset] + partial_logs,
                message=f"第 {retry_no + 1} 次执行中",
            )

        try:
            result = execute_task_target(task, log_callback=persist_attempt_progress)
            status = str(result.get("status") or "success")
            if status not in {"success", "failed", "skipped"}:
                status = "success"
            message = str(result.get("message") or "")
            logs = logs[:attempt_offset] + normalise_log_lines(
                result.get("logs") if isinstance(result.get("logs"), list) else []
            )
        except Exception as exc:
            status = "failed"
            message = str(exc)
            error_traceback = traceback.format_exc()
            logs = logs[:attempt_offset] + [
                make_log_line(
                    f"任务执行异常: {message}",
                    level="ERROR",
                    scope="调度",
                    raw=error_traceback,
                    meta={"error_type": exc.__class__.__name__},
                )
            ]
            result = {
                "status": status,
                "message": message,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": message,
                    "traceback": error_traceback,
                },
            }

        attempts.append(
            {
                "retry_no": retry_no,
                "attempt_no": retry_no + 1,
                "status": status,
                "message": message,
                "started_at": _datetime_param(attempt_started),
                "finished_at": _datetime_param(datetime.now()),
                "duration_ms": round((time.perf_counter() - attempt_timer) * 1000, 2),
            }
        )
        logs.append(
            make_log_line(
                f"第 {retry_no + 1} 次执行{_run_status_label(status)}: {message or status}",
                level="ERROR" if status == "failed" else "WARN" if status == "skipped" else "INFO",
                scope="调度",
                sub_scope="重试" if retry_no else "首次执行",
                meta={"retry_no": retry_no, "status": status},
            )
        )
        result = dict(result or {})
        result["retry_attempts"] = list(attempts)
        _persist_run_progress(run_id, logs, message=message, result_snapshot=result)

        if status != "failed" or retry_no >= max_retries:
            break

        logs.append(
            make_log_line(
                f"{retry_interval} 秒后开始第 {retry_no + 2} 次重试",
                level="WARN",
                scope="调度",
                sub_scope="重试",
                meta={"retry_no": retry_no + 1, "retry_interval_seconds": retry_interval},
            )
        )
        _persist_run_progress(run_id, logs, message=message, result_snapshot=result)
        if retry_interval:
            time.sleep(retry_interval)

    result["retry_attempts"] = attempts
    trimmed_logs, logs_meta = trim_scheduler_logs(logs)
    result["logs_meta"] = logs_meta

    finished_at = datetime.now()
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    execute(
        """
        UPDATE scheduler_task_runs
        SET status = %s,
            finished_at = %s,
            duration_ms = %s,
            retry_no = %s,
            message = %s,
            result_snapshot = %s,
            logs = %s
        WHERE id = %s
        """,
        (
            status,
            _datetime_param(finished_at),
            duration_ms,
            max(0, len(attempts) - 1),
            message,
            _json_text(result),
            _json_text(trimmed_logs),
            run_id,
        ),
    )

    next_run_at = _calculate_next_run(task, finished_at) if task.get("enabled") else None
    execute(
        """
        UPDATE scheduler_tasks
        SET status = 'idle',
            last_run_status = %s,
            last_run_message = %s,
            last_run_at = %s,
            next_run_at = %s,
            run_count = run_count + 1,
            fail_count = fail_count + %s
        WHERE id = %s
        """,
        (
            status,
            message,
            _datetime_param(finished_at),
            _datetime_param(next_run_at),
            1 if status == "failed" else 0,
            task_id,
        ),
    )
    _prune_task_runs(task_id)
    return _hydrate_run(fetch_one("SELECT * FROM scheduler_task_runs WHERE id = %s", (run_id,)))


def run_due_tasks(limit: int = 20) -> list[dict[str, Any]]:
    _ensure_schema_ready()
    now = datetime.now()
    rows = fetch_all(
        f"""
        {_task_query_base()}
        WHERE st.enabled = %s
          AND st.next_run_at IS NOT NULL
          AND st.next_run_at <= %s
          AND st.status <> 'running'
        ORDER BY st.next_run_at ASC, st.id ASC
        LIMIT %s
        """,
        (True, _datetime_param(now), max(1, min(int(limit or 20), 100))),
    )
    results: list[dict[str, Any]] = []
    for row in rows:
        task = _hydrate_task(row)
        if not task:
            continue
        try:
            results.append(execute_scheduler_task(int(task["id"]), trigger_type="schedule", executor="scheduler"))
        except ValueError as exc:
            results.append(
                {
                    "task_id": task.get("id"),
                    "task_name": task.get("name"),
                    "status": "skipped",
                    "message": str(exc),
                }
            )
    return results


@api_view
def run_task(_request, task_id: int, payload=None):
    return execute_scheduler_task(
        task_id,
        trigger_type=str((payload or {}).get("trigger_type") or "manual"),
        executor="web",
    )
