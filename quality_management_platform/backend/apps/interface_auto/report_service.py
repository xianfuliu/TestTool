from __future__ import annotations

import json
import os
import smtplib
import ssl
from copy import deepcopy
from datetime import datetime
from email.message import EmailMessage
from html import escape
from typing import Any

from apps.common.http import get_int
from test_platform.db import connect, execute, fetch_all, fetch_one


_REPORT_SCHEMA_READY = False


def _json_text(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)


def _json_value(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (column_name,))
    return cursor.fetchone() is not None


def _index_exists(cursor, table_name: str, index_name: str) -> bool:
    cursor.execute(f"SHOW INDEX FROM {table_name} WHERE Key_name = %s", (index_name,))
    return cursor.fetchone() is not None


def _datetime_param(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


def _format_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if value in (None, ""):
        return ""
    return str(value).replace("T", " ")[:19]


def _status_label(status: str) -> str:
    return {
        "success": "成功",
        "failed": "失败",
        "running": "执行中",
        "skipped": "跳过",
        "pending": "待执行",
    }.get(str(status or ""), str(status or "未知"))


def _recipient_list(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_items = value.replace(";", ",").split(",")
    elif isinstance(value, list):
        raw_items = value
    else:
        raw_items = []
    recipients: list[str] = []
    for item in raw_items:
        text = str(item or "").strip()
        if text and "@" in text and text not in recipients:
            recipients.append(text)
    return recipients


def ensure_report_schema_ready() -> None:
    global _REPORT_SCHEMA_READY
    if _REPORT_SCHEMA_READY:
        return
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS test_reports (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    report_type VARCHAR(30) DEFAULT 'test_case',
                    scheduler_id INT NULL,
                    scheduler_task_id INT NULL,
                    scheduler_run_id INT NULL,
                    suite_id INT NULL,
                    case_id INT NULL,
                    project_id INT NULL,
                    report_name VARCHAR(255) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    total_cases INT DEFAULT 0,
                    passed_cases INT DEFAULT 0,
                    failed_cases INT DEFAULT 0,
                    error_cases INT DEFAULT 0,
                    start_time DATETIME NULL,
                    end_time DATETIME NULL,
                    duration FLOAT DEFAULT 0,
                    log_path VARCHAR(500) DEFAULT '',
                    trigger_type VARCHAR(50) DEFAULT 'manual',
                    summary_json JSON NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_test_reports_suite_id (suite_id),
                    INDEX idx_test_reports_project_id (project_id),
                    INDEX idx_test_reports_type_created_at (report_type, created_at),
                    INDEX idx_test_reports_scheduler_run_id (scheduler_run_id),
                    INDEX idx_test_reports_suite_created_id (suite_id, created_at, id),
                    INDEX idx_test_reports_case_created_id (case_id, created_at, id),
                    INDEX idx_test_reports_project_created_id (project_id, created_at, id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            if not _column_exists(cursor, "test_reports", "report_type"):
                cursor.execute("ALTER TABLE test_reports ADD COLUMN report_type VARCHAR(30) DEFAULT 'test_case' AFTER id")
            if not _column_exists(cursor, "test_reports", "scheduler_task_id"):
                cursor.execute("ALTER TABLE test_reports ADD COLUMN scheduler_task_id INT NULL AFTER scheduler_id")
            if not _column_exists(cursor, "test_reports", "scheduler_run_id"):
                cursor.execute("ALTER TABLE test_reports ADD COLUMN scheduler_run_id INT NULL AFTER scheduler_task_id")
            if not _index_exists(cursor, "test_reports", "idx_test_reports_suite_created_id"):
                cursor.execute(
                    """
                    ALTER TABLE test_reports
                    ADD INDEX idx_test_reports_suite_created_id (suite_id, created_at, id)
                    """
                )
            if not _index_exists(cursor, "test_reports", "idx_test_reports_case_created_id"):
                cursor.execute(
                    """
                    ALTER TABLE test_reports
                    ADD INDEX idx_test_reports_case_created_id (case_id, created_at, id)
                    """
                )
            if not _index_exists(cursor, "test_reports", "idx_test_reports_project_created_id"):
                cursor.execute(
                    """
                    ALTER TABLE test_reports
                    ADD INDEX idx_test_reports_project_created_id (project_id, created_at, id)
                    """
                )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS test_step_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    report_id INT NOT NULL,
                    scheduler_id INT NULL,
                    suite_id INT NULL,
                    case_id INT NULL,
                    step_id INT NULL,
                    step_order INT DEFAULT 1,
                    step_name VARCHAR(255) DEFAULT '',
                    status VARCHAR(50) DEFAULT 'pending',
                    request_data JSON NULL,
                    response_data JSON NULL,
                    execution_logs TEXT,
                    error_message TEXT,
                    start_time DATETIME NULL,
                    end_time DATETIME NULL,
                    execution_time FLOAT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_report_id (report_id),
                    INDEX idx_test_step_results_case_id (case_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
        connection.commit()
    _REPORT_SCHEMA_READY = True


def hydrate_report_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    item = dict(row)
    summary = _json_value(item.get("summary_json"), {})
    item["summary_json"] = summary
    item["email_delivery"] = summary.get("email_delivery") if isinstance(summary, dict) else None
    if not item.get("report_type"):
        item["report_type"] = "test_suite" if item.get("suite_id") else "test_case"
    return item


def _report_query_base() -> str:
    return """
        SELECT
            tr.*,
            ts.name AS suite_name,
            tc.name AS case_name,
            p.name AS project_name,
            p.business_group_id,
            bg.name AS business_group_name
        FROM test_reports tr
        LEFT JOIN test_suites ts ON ts.id = tr.suite_id
        LEFT JOIN test_cases tc ON tc.id = tr.case_id
        LEFT JOIN projects p ON p.id = tr.project_id
        LEFT JOIN business_groups bg ON bg.id = p.business_group_id
    """


def list_reports(params: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_report_schema_ready()
    payload = params or {}
    page = max(1, get_int(payload.get("page"), 1) or 1)
    page_size = max(1, min(get_int(payload.get("page_size"), 20) or 20, 100))
    project_id = get_int(payload.get("project_id"))
    suite_id = get_int(payload.get("suite_id"))
    case_id = get_int(payload.get("case_id"))
    status = str(payload.get("status") or "").strip()
    keyword = str(payload.get("keyword") or "").strip()
    skip = max(0, get_int(payload.get("skip"), 0) or 0)

    conditions: list[str] = []
    values: list[Any] = []
    if project_id:
        conditions.append("tr.project_id = %s")
        values.append(project_id)
    if suite_id:
        conditions.append("tr.suite_id = %s")
        values.append(suite_id)
    if case_id:
        conditions.append("tr.case_id = %s")
        values.append(case_id)
    if status:
        conditions.append("tr.status = %s")
        values.append(status)
    if keyword:
        like_value = f"%{keyword}%"
        conditions.append("(tr.report_name LIKE %s OR ts.name LIKE %s OR tc.name LIKE %s)")
        values.extend([like_value, like_value, like_value])
    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    total_row = fetch_one(
        f"""
        SELECT COUNT(*) AS count
        FROM test_reports tr
        LEFT JOIN test_suites ts ON ts.id = tr.suite_id
        LEFT JOIN test_cases tc ON tc.id = tr.case_id
        {where_sql}
        """,
        values,
    )
    id_rows = fetch_all(
        f"""
        SELECT tr.id
        FROM test_reports tr
        LEFT JOIN test_suites ts ON ts.id = tr.suite_id
        LEFT JOIN test_cases tc ON tc.id = tr.case_id
        {where_sql}
        ORDER BY tr.created_at DESC, tr.id DESC
        LIMIT %s OFFSET %s
        """,
        (*values, page_size, (page - 1) * page_size + skip),
    )
    report_ids = [int(row["id"]) for row in id_rows if row.get("id")]
    rows: list[dict[str, Any]] = []
    if report_ids:
        placeholders = ", ".join(["%s"] * len(report_ids))
        fetched_rows = fetch_all(
            f"""
            {_report_query_base()}
            WHERE tr.id IN ({placeholders})
            """,
            report_ids,
        )
        rows_by_id = {int(row["id"]): row for row in fetched_rows if row.get("id")}
        rows = [rows_by_id[report_id] for report_id in report_ids if report_id in rows_by_id]
    total = max(0, int((total_row or {}).get("count") or 0) - skip)
    return {
        "data": [hydrate_report_row(row) for row in rows],
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total else 1,
            "has_prev": page > 1,
            "has_next": page * page_size < total,
        },
    }


def list_report_records(params: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(params or {})
    payload["skip"] = 1 if str(payload.get("skip_latest") or "").lower() in {"1", "true", "yes"} else 0
    return list_reports(payload)


def list_report_groups(params: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_report_schema_ready()
    payload = params or {}
    page = max(1, get_int(payload.get("page"), 1) or 1)
    page_size = max(1, min(get_int(payload.get("page_size"), 20) or 20, 100))
    project_id = get_int(payload.get("project_id"))
    suite_id = get_int(payload.get("suite_id"))
    status = str(payload.get("status") or "").strip()
    keyword = str(payload.get("keyword") or "").strip()

    conditions: list[str] = []
    values: list[Any] = []
    if project_id:
        conditions.append("tr.project_id = %s")
        values.append(project_id)
    if suite_id:
        conditions.append("tr.suite_id = %s")
        values.append(suite_id)
    if status:
        conditions.append("tr.status = %s")
        values.append(status)
    if keyword:
        like_value = f"%{keyword}%"
        conditions.append("(tr.report_name LIKE %s OR ts.name LIKE %s OR tc.name LIKE %s)")
        values.extend([like_value, like_value, like_value])
    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    group_key_sql = """
        CASE
            WHEN tr.suite_id IS NOT NULL THEN CONCAT('suite:', tr.suite_id)
            WHEN tr.case_id IS NOT NULL THEN CONCAT('case:', tr.case_id)
            ELSE CONCAT('report:', tr.id)
        END
    """
    total_row = fetch_one(
        f"""
        SELECT COUNT(*) AS count
        FROM (
            SELECT {group_key_sql} AS group_key
            FROM test_reports tr
            LEFT JOIN test_suites ts ON ts.id = tr.suite_id
            LEFT JOIN test_cases tc ON tc.id = tr.case_id
            {where_sql}
            GROUP BY group_key
        ) grouped_reports
        """,
        values,
    )
    grouped_rows = fetch_all(
        f"""
        SELECT
            {group_key_sql} AS group_key,
            MAX(tr.id) AS latest_report_id,
            COUNT(*) AS report_count,
            MAX(tr.created_at) AS latest_created_at
        FROM test_reports tr
        LEFT JOIN test_suites ts ON ts.id = tr.suite_id
        LEFT JOIN test_cases tc ON tc.id = tr.case_id
        {where_sql}
        GROUP BY group_key
        ORDER BY latest_created_at DESC, latest_report_id DESC
        LIMIT %s OFFSET %s
        """,
        (*values, page_size, (page - 1) * page_size),
    )
    latest_ids = [row["latest_report_id"] for row in grouped_rows if row.get("latest_report_id")]
    reports_by_id: dict[int, dict[str, Any]] = {}
    if latest_ids:
        placeholders = ", ".join(["%s"] * len(latest_ids))
        latest_rows = fetch_all(
            f"""
            {_report_query_base()}
            WHERE tr.id IN ({placeholders})
            """,
            latest_ids,
        )
        reports_by_id = {int(row["id"]): hydrate_report_row(row) for row in latest_rows if row.get("id")}
    current_items: list[dict[str, Any]] = []
    for group_row in grouped_rows:
        report = reports_by_id.get(int(group_row["latest_report_id"]))
        if not report:
            continue
        current_items.append(
            _create_report_group(
                report,
                str(group_row.get("group_key") or _report_group_key(report)),
                report_count=int(group_row.get("report_count") or 0),
            )
        )
    total = int((total_row or {}).get("count") or 0)
    return {
        "data": current_items,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total else 1,
            "has_prev": page > 1,
            "has_next": page * page_size < total,
        },
    }


def _report_group_key(row: dict[str, Any]) -> str:
    suite_id = get_int(row.get("suite_id"))
    if suite_id:
        return f"suite:{suite_id}"
    case_id = get_int(row.get("case_id"))
    if case_id:
        return f"case:{case_id}"
    return f"report:{row.get('id')}"


def _create_report_group(row: dict[str, Any], group_key: str, *, report_count: int = 0) -> dict[str, Any]:
    suite_id = get_int(row.get("suite_id"))
    case_id = get_int(row.get("case_id"))
    group_type = "test_suite" if suite_id else "test_case" if case_id else "unknown"
    group_name = row.get("suite_name") or row.get("case_name") or row.get("report_name")
    return {
        "key": group_key,
        "group_type": group_type,
        "suite_id": suite_id,
        "suite_name": row.get("suite_name"),
        "case_id": case_id,
        "case_name": row.get("case_name"),
        "name": group_name,
        "business_group_id": row.get("business_group_id"),
        "business_group_name": row.get("business_group_name"),
        "project_id": row.get("project_id"),
        "project_name": row.get("project_name"),
        "latest_report_id": row.get("id"),
        "latest_report_name": row.get("report_name"),
        "status": row.get("status"),
        "total_cases": row.get("total_cases") or 0,
        "passed_cases": row.get("passed_cases") or 0,
        "failed_cases": row.get("failed_cases") or 0,
        "error_cases": row.get("error_cases") or 0,
        "start_time": row.get("start_time"),
        "end_time": row.get("end_time"),
        "duration": row.get("duration") or 0,
        "trigger_type": row.get("trigger_type"),
        "email_delivery": row.get("email_delivery"),
        "created_at": row.get("created_at"),
        "report_count": report_count,
        "records": [],
    }


def get_report_detail(report_id: int) -> dict[str, Any] | None:
    ensure_report_schema_ready()
    report = hydrate_report_row(fetch_one(f"{_report_query_base()} WHERE tr.id = %s", (report_id,)))
    if not report:
        return None
    report["cases"] = build_report_cases(report)
    return report


def delete_report(report_id: int) -> bool:
    ensure_report_schema_ready()
    execute("DELETE FROM test_step_results WHERE report_id = %s", (report_id,))
    return execute("DELETE FROM test_reports WHERE id = %s", (report_id,)) > 0


def build_report_cases(report: dict[str, Any]) -> list[dict[str, Any]]:
    summary = _json_value(report.get("summary_json"), {})
    case_results = summary.get("case_results") if isinstance(summary, dict) else None
    if not isinstance(case_results, list):
        result_snapshot = summary.get("result_snapshot") if isinstance(summary, dict) else {}
        case_results = result_snapshot.get("results") if isinstance(result_snapshot, dict) else []
    if isinstance(case_results, list) and case_results:
        return [_case_from_result(item, index) for index, item in enumerate(case_results)]

    execution_log = summary.get("execution_log") if isinstance(summary, dict) else None
    if isinstance(execution_log, dict):
        return [
            _case_from_result(
                {
                    "case_id": report.get("case_id") or execution_log.get("case_id"),
                    "case_name": report.get("case_name") or execution_log.get("case_name"),
                    "status": report.get("status") or execution_log.get("status"),
                    "message": execution_log.get("message"),
                    "summary": {
                        "passed_steps": summary.get("passed_steps", 0),
                        "failed_steps": summary.get("failed_steps", 0),
                        "skipped_steps": summary.get("skipped_steps", 0),
                    },
                    "steps": summary.get("steps", []),
                    "execution_log": execution_log,
                },
                0,
            )
        ]

    rows = fetch_all("SELECT * FROM test_step_results WHERE report_id = %s ORDER BY step_order, id", (report["id"],))
    return [
        {
            "key": f"case-{report.get('case_id') or report.get('id')}",
            "case_id": report.get("case_id"),
            "case_name": report.get("case_name") or report.get("report_name"),
            "status": report.get("status"),
            "message": report.get("report_name"),
            "duration": _case_duration_seconds(report, {}, rows),
            "summary": _step_summary(rows),
            "steps": [_step_from_row(row) for row in rows],
            "execution_log": {"lines": []},
        }
    ]


def create_scheduler_execution_report(
    task: dict[str, Any],
    result: dict[str, Any],
    *,
    run_id: int,
    trigger_type: str,
    started_at: datetime,
    finished_at: datetime,
    duration_ms: float,
) -> dict[str, Any] | None:
    ensure_report_schema_ready()
    task_type = str(task.get("task_type") or "")
    if task_type not in {"test_suite", "test_case"}:
        return None

    target_config = _json_value(task.get("target_config"), {})
    suite_id = get_int(target_config.get("suite_id")) if task_type == "test_suite" else None
    suite = fetch_one("SELECT * FROM test_suites WHERE id = %s", (suite_id,)) if suite_id else None
    report_type = "test_suite" if suite_id else "test_case_batch"
    results = result.get("results") if isinstance(result.get("results"), list) else []
    status = str(result.get("status") or "success")
    total_cases = len(results) if results else int(_json_value(result.get("summary"), {}).get("total_cases") or 0)
    passed_cases = len([item for item in results if str(_json_value(item, {}).get("status")) == "success"])
    failed_cases = len([item for item in results if str(_json_value(item, {}).get("status")) == "failed"])
    skipped_cases = len([item for item in results if str(_json_value(item, {}).get("status")) == "skipped"])
    if not results and status == "failed":
        failed_cases = max(failed_cases, 1 if total_cases else 0)
    source_name = (suite or {}).get("name") or task.get("name") or "接口自动化任务"
    report_name = f"{source_name}_{started_at.strftime('%Y%m%d%H%M%S')}"
    notify_config = _json_value(task.get("notify_config"), {})
    summary = {
        "report_type": report_type,
        "source": "scheduler",
        "scheduler_task_id": task.get("id"),
        "scheduler_run_id": run_id,
        "trigger_type": trigger_type,
        "suite_id": suite_id,
        "suite_name": (suite or {}).get("name"),
        "task_name": task.get("name"),
        "status": status,
        "message": result.get("message") or "",
        "summary": result.get("summary") or {},
        "case_results": results,
        "logs_meta": result.get("logs_meta") or {},
        "retry_attempts": result.get("retry_attempts") or [],
        "duration_ms": duration_ms,
    }
    report_id = execute(
        """
        INSERT INTO test_reports (
            report_type,
            scheduler_id,
            scheduler_task_id,
            scheduler_run_id,
            suite_id,
            case_id,
            project_id,
            report_name,
            status,
            total_cases,
            passed_cases,
            failed_cases,
            error_cases,
            start_time,
            end_time,
            duration,
            trigger_type,
            summary_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            report_type,
            task.get("id"),
            task.get("id"),
            run_id,
            suite_id,
            None,
            task.get("project_id") or (suite or {}).get("project_id"),
            report_name,
            status,
            total_cases,
            passed_cases,
            failed_cases,
            skipped_cases,
            _datetime_param(started_at),
            _datetime_param(finished_at),
            round(duration_ms / 1000, 3),
            trigger_type,
            _json_text(summary),
        ),
    )
    email_delivery = send_report_email(
        {
            "id": report_id,
            "report_name": report_name,
            "status": status,
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "error_cases": skipped_cases,
            "start_time": started_at,
            "end_time": finished_at,
            "duration": round(duration_ms / 1000, 3),
            "suite_name": (suite or {}).get("name"),
            "project_name": task.get("project_name"),
            "trigger_type": trigger_type,
            "summary_json": summary,
        },
        _recipient_list(notify_config.get("emails")),
    )
    summary["email_delivery"] = email_delivery
    execute("UPDATE test_reports SET summary_json = %s WHERE id = %s", (_json_text(summary), report_id))
    return {
        "report_id": report_id,
        "report_name": report_name,
        "email_delivery": email_delivery,
    }


def send_report_email(report: dict[str, Any], recipients: list[str]) -> dict[str, Any]:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not recipients:
        return {"status": "skipped", "message": "未配置收件人", "recipients": [], "sent_at": now}
    smtp_host = os.getenv("QUALITY_REPORT_SMTP_HOST") or os.getenv("SMTP_HOST") or ""
    smtp_port = int(os.getenv("QUALITY_REPORT_SMTP_PORT") or os.getenv("SMTP_PORT") or "465")
    smtp_user = os.getenv("QUALITY_REPORT_SMTP_USER") or os.getenv("SMTP_USER") or ""
    smtp_password = os.getenv("QUALITY_REPORT_SMTP_PASSWORD") or os.getenv("SMTP_PASSWORD") or ""
    sender = os.getenv("QUALITY_REPORT_SMTP_FROM") or os.getenv("SMTP_FROM") or smtp_user
    use_ssl = str(os.getenv("QUALITY_REPORT_SMTP_SSL") or os.getenv("SMTP_SSL") or "true").lower() not in {"0", "false", "no"}
    use_tls = str(os.getenv("QUALITY_REPORT_SMTP_TLS") or os.getenv("SMTP_TLS") or "false").lower() in {"1", "true", "yes"}
    if not smtp_host or not sender:
        return {"status": "skipped", "message": "未配置 SMTP_HOST/SMTP_FROM", "recipients": recipients, "sent_at": now}

    message = EmailMessage()
    subject_status = _status_label(str(report.get("status") or ""))
    message["Subject"] = f"接口自动化测试报告 - {report.get('report_name')} - {subject_status}"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    plain_text = _build_email_plain_text(report)
    html_text = _build_email_html(report)
    message.set_content(plain_text)
    message.add_alternative(html_text, subtype="html")

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ssl.create_default_context(), timeout=20) as smtp:
                if smtp_user:
                    smtp.login(smtp_user, smtp_password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
                if use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                if smtp_user:
                    smtp.login(smtp_user, smtp_password)
                smtp.send_message(message)
    except Exception as exc:
        return {"status": "failed", "message": str(exc), "recipients": recipients, "sent_at": now}
    return {"status": "sent", "message": "测试报告邮件已发送", "recipients": recipients, "sent_at": now}


def _case_from_result(value: Any, index: int) -> dict[str, Any]:
    result = _json_value(value, {})
    execution_log = _json_value(result.get("execution_log"), {})
    steps = execution_log.get("steps") if isinstance(execution_log.get("steps"), list) else result.get("steps", [])
    return {
        "key": f"case-{result.get('case_id') or index}",
        "case_id": result.get("case_id"),
        "case_name": result.get("case_name") or execution_log.get("case_name") or f"用例 {index + 1}",
        "status": result.get("status") or execution_log.get("status") or "pending",
        "message": result.get("message") or execution_log.get("message") or "",
        "duration": _case_duration_seconds(result, execution_log, steps),
        "summary": result.get("summary") or _step_summary(steps),
        "steps": steps,
        "execution_log": execution_log,
    }


def _float_value(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _parse_datetime_value(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    for pattern in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw[:26] if "%f" in pattern else raw[:19], pattern)
        except ValueError:
            continue
    return None


def _duration_seconds_from_range(start_value: Any, end_value: Any) -> float | None:
    start = _parse_datetime_value(start_value)
    end = _parse_datetime_value(end_value)
    if not start or not end:
        return None
    seconds = (end - start).total_seconds()
    return round(seconds, 3) if seconds >= 0 else None


def _duration_seconds_from_item(item: Any) -> float | None:
    record = _json_value(item, {})
    for key in ("duration", "execution_time", "duration_seconds", "elapsed_seconds"):
        seconds = _float_value(record.get(key))
        if seconds is not None:
            return round(seconds, 3)
    milliseconds = _float_value(record.get("duration_ms") or record.get("elapsed_ms"))
    if milliseconds is not None:
        return round(milliseconds / 1000, 3)
    return _duration_seconds_from_range(
        record.get("started_at") or record.get("start_time"),
        record.get("ended_at") or record.get("end_time"),
    )


def _case_duration_seconds(result: Any, execution_log: Any, steps: Any) -> float:
    for source in (_json_value(result, {}), _json_value(execution_log, {})):
        direct = _duration_seconds_from_item(source)
        if direct is not None:
            return direct
    step_items = steps if isinstance(steps, list) else []
    step_duration = sum((_duration_seconds_from_item(step) or 0) for step in step_items)
    return round(step_duration, 3) if step_duration else 0


def _step_summary(steps: Any) -> dict[str, int]:
    step_items = steps if isinstance(steps, list) else []
    return {
        "passed_steps": len([item for item in step_items if _json_value(item, {}).get("status") == "success"]),
        "failed_steps": len([item for item in step_items if _json_value(item, {}).get("status") == "failed"]),
        "skipped_steps": len([item for item in step_items if _json_value(item, {}).get("status") == "skipped"]),
    }


def _step_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "step_id": row.get("step_id"),
        "step_order": row.get("step_order"),
        "step_name": row.get("step_name"),
        "status": row.get("status"),
        "summary": row.get("error_message") or row.get("status"),
        "request_data": _json_value(row.get("request_data"), {}),
        "response_data": _json_value(row.get("response_data"), {}),
        "logs": str(row.get("execution_logs") or "").splitlines(),
        "error_message": row.get("error_message") or "",
        "started_at": _format_datetime(row.get("start_time")),
        "ended_at": _format_datetime(row.get("end_time")),
        "execution_time": row.get("execution_time"),
    }


def _build_email_plain_text(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"报告名称：{report.get('report_name')}",
            f"执行状态：{_status_label(str(report.get('status') or ''))}",
            f"所属项目：{report.get('project_name') or '-'}",
            f"测试集：{report.get('suite_name') or '-'}",
            f"触发方式：{report.get('trigger_type') or '-'}",
            f"开始时间：{_format_datetime(report.get('start_time'))}",
            f"结束时间：{_format_datetime(report.get('end_time'))}",
            f"耗时：{report.get('duration') or 0}s",
            f"用例统计：共 {report.get('total_cases') or 0}，成功 {report.get('passed_cases') or 0}，失败 {report.get('failed_cases') or 0}，跳过 {report.get('error_cases') or 0}",
        ]
    )


def _build_email_html(report: dict[str, Any]) -> str:
    summary = _json_value(deepcopy(report.get("summary_json")), {})
    case_results = summary.get("case_results") if isinstance(summary.get("case_results"), list) else []
    rows = "".join(
        f"<tr><td>{escape(str(item.get('case_name') or item.get('case_id') or '-'))}</td>"
        f"<td>{escape(_status_label(str(item.get('status') or '')))}</td>"
        f"<td>{escape(str(item.get('message') or ''))}</td></tr>"
        for item in case_results[:50]
        if isinstance(item, dict)
    )
    if not rows:
        rows = "<tr><td colspan='3'>暂无用例明细</td></tr>"
    return f"""
    <html>
      <body style="font-family:Arial,'Microsoft YaHei',sans-serif;color:#1f2937;">
        <h2>接口自动化测试报告</h2>
        <p><strong>{escape(str(report.get('report_name') or ''))}</strong></p>
        <table cellpadding="6" cellspacing="0" style="border-collapse:collapse;border:1px solid #d8dee9;">
          <tr><td>执行状态</td><td>{escape(_status_label(str(report.get('status') or '')))}</td></tr>
          <tr><td>所属项目</td><td>{escape(str(report.get('project_name') or '-'))}</td></tr>
          <tr><td>测试集</td><td>{escape(str(report.get('suite_name') or '-'))}</td></tr>
          <tr><td>触发方式</td><td>{escape(str(report.get('trigger_type') or '-'))}</td></tr>
          <tr><td>执行时间</td><td>{escape(_format_datetime(report.get('start_time')))} - {escape(_format_datetime(report.get('end_time')))}</td></tr>
          <tr><td>用例统计</td><td>共 {report.get('total_cases') or 0}，成功 {report.get('passed_cases') or 0}，失败 {report.get('failed_cases') or 0}，跳过 {report.get('error_cases') or 0}</td></tr>
        </table>
        <h3>用例明细</h3>
        <table cellpadding="6" cellspacing="0" style="width:100%;border-collapse:collapse;border:1px solid #d8dee9;">
          <thead><tr style="background:#f6f8fb;"><th align="left">用例</th><th align="left">状态</th><th align="left">摘要</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </body>
    </html>
    """
