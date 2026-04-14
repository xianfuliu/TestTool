from __future__ import annotations

import json
from datetime import datetime

from apps.common.http import api_view, get_int
from test_platform.db import connect, execute, fetch_all, fetch_one

from .execution_service import execute_case_run
from . import template_service


_CASE_SCHEMA_READY = False


def _json_text(value):
    return json.dumps(value or {}, ensure_ascii=False)


def _empty_list_json(value):
    return json.dumps(value or [], ensure_ascii=False)


def _json_value(value, default):
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


def _ensure_case_schema_extensions():
    global _CASE_SCHEMA_READY
    if _CASE_SCHEMA_READY:
        return
    with connect() as connection:
        with connection.cursor() as cursor:
            if not _column_exists(cursor, "test_cases", "global_request_config_text"):
                cursor.execute(
                    """
                    ALTER TABLE test_cases
                    ADD COLUMN global_request_config_text LONGTEXT NULL AFTER global_vars
                    """
                )
            if not _column_exists(cursor, "test_cases", "output_variables_text"):
                cursor.execute(
                    """
                    ALTER TABLE test_cases
                    ADD COLUMN output_variables_text LONGTEXT NULL AFTER global_request_config_text
                    """
                )
        connection.commit()
    _CASE_SCHEMA_READY = True


def _hydrate_case_row(case_row):
    if not case_row:
        return {}
    hydrated = dict(case_row)
    hydrated["global_vars"] = _json_value(hydrated.get("global_vars"), {})
    hydrated["global_request_config"] = _json_value(hydrated.get("global_request_config_text"), {})
    hydrated["output_variables"] = _json_value(hydrated.get("output_variables_text"), [])
    return hydrated


def _hydrate_step_row(step_row):
    hydrated = dict(step_row)
    hydrated["pre_processing"] = _json_value(hydrated.get("pre_processing"), {})
    hydrated["post_processing"] = _json_value(hydrated.get("post_processing"), {})
    hydrated["assertions"] = _json_value(hydrated.get("assertions"), {})
    hydrated["variables"] = _json_value(hydrated.get("variables"), {})
    return hydrated


def _list_case_steps(case_id: int):
    rows = fetch_all(
        """
        SELECT
            cs.*,
            at.project_id AS api_project_id,
            at.folder_id AS api_folder_id,
            at.name AS api_name,
            at.method AS api_method,
            at.url_path AS api_url_path,
            at.description AS api_description
        FROM test_case_steps cs
        LEFT JOIN api_templates at ON cs.api_template_id = at.id
        WHERE cs.case_id = %s
        ORDER BY cs.step_order, cs.id
        """,
        (case_id,),
    )
    return [_hydrate_step_row(row) for row in rows]


def _get_case_detail(case_id: int):
    _ensure_case_schema_extensions()
    case_row = _hydrate_case_row(fetch_one("SELECT * FROM test_cases WHERE id = %s", (case_id,)))
    if not case_row:
        return {}
    case_row["steps"] = _list_case_steps(case_id)
    return case_row


def _list_cases(where_sql: str = "", params=()):
    _ensure_case_schema_extensions()
    query = """
        SELECT *
        FROM test_cases
    """
    if where_sql:
        query = f"{query} {where_sql}"
    query = f"{query} ORDER BY sort_order, created_at"
    return [_hydrate_case_row(row) for row in fetch_all(query, params)]


def _write_case_steps(case_id: int, steps):
    execute("DELETE FROM test_case_steps WHERE case_id = %s", (case_id,))
    for index, step in enumerate(steps or [], start=1):
        execute(
            """
            INSERT INTO test_case_steps (
                case_id,
                api_template_id,
                step_order,
                name,
                enabled,
                pre_processing,
                post_processing,
                assertions,
                variables,
                enable_encryption
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                case_id,
                step.get("api_template_id"),
                step.get("step_order") or index,
                step.get("name", ""),
                step.get("enabled", True),
                _json_text(step.get("pre_processing")),
                _json_text(step.get("post_processing")),
                _json_text(step.get("assertions")),
                _json_text(step.get("variables")),
                step.get("enable_encryption", False),
            ),
        )


def _delete_case_with_steps(case_id: int):
    execute("DELETE FROM test_case_steps WHERE case_id = %s", (case_id,))
    return execute("DELETE FROM test_cases WHERE id = %s", (case_id,)) > 0


@api_view
def overview(_request, payload=None):
    return {
        "business_groups": fetch_all("SELECT * FROM business_groups ORDER BY created_at ASC"),
        "projects": fetch_all(
            """
            SELECT p.*, bg.name AS group_name
            FROM projects p
            LEFT JOIN business_groups bg ON p.business_group_id = bg.id
            ORDER BY p.created_at ASC
            """
        ),
        "global_tools": fetch_all("SELECT * FROM global_tools ORDER BY created_at DESC"),
        "global_variables": fetch_all("SELECT * FROM global_variables ORDER BY name ASC"),
        "environments": fetch_all("SELECT * FROM environments ORDER BY created_at DESC"),
        "reports": fetch_all("SELECT * FROM test_reports ORDER BY created_at DESC LIMIT 20"),
    }


@api_view
def business_groups(request, payload=None):
    if request.method == "GET":
        return fetch_all("SELECT * FROM business_groups ORDER BY created_at ASC")
    group = payload or {}
    group_id = execute(
        "INSERT INTO business_groups (name, description, created_by) VALUES (%s, %s, %s)",
        (group.get("name"), group.get("description", ""), "admin"),
    )
    return {"group_id": group_id}, 201


@api_view
def business_group_detail(request, group_id: int, payload=None):
    if request.method == "GET":
        return fetch_one("SELECT * FROM business_groups WHERE id = %s", (group_id,))
    if request.method == "PUT":
        updated = execute(
            "UPDATE business_groups SET name = %s, description = %s WHERE id = %s",
            ((payload or {}).get("name"), (payload or {}).get("description", ""), group_id),
        )
        return {"updated": updated >= 0}
    return {"deleted": execute("DELETE FROM business_groups WHERE id = %s", (group_id,)) > 0}


@api_view
def business_group_stats(_request, group_id: int, payload=None):
    project_count = fetch_one("SELECT COUNT(*) AS count FROM projects WHERE business_group_id = %s", (group_id,))
    api_count = fetch_one(
        """
        SELECT COUNT(*) AS count FROM api_templates
        WHERE project_id IN (SELECT id FROM projects WHERE business_group_id = %s)
        """,
        (group_id,),
    )
    case_count = fetch_one(
        """
        SELECT COUNT(*) AS count FROM test_cases
        WHERE project_id IN (SELECT id FROM projects WHERE business_group_id = %s)
        """,
        (group_id,),
    )
    return {
        "project_count": project_count["count"] if project_count else 0,
        "api_count": api_count["count"] if api_count else 0,
        "case_count": case_count["count"] if case_count else 0,
    }


@api_view
def projects(request, payload=None):
    if request.method == "GET":
        group_id = get_int((payload or {}).get("group_id"))
        if group_id:
            return fetch_all("SELECT * FROM projects WHERE business_group_id = %s ORDER BY created_at ASC", (group_id,))
        return fetch_all("SELECT * FROM projects ORDER BY created_at ASC")
    project = payload or {}
    project_id = execute(
        """
        INSERT INTO projects (business_group_id, name, description, created_by)
        VALUES (%s, %s, %s, %s)
        """,
        (project.get("group_id"), project.get("name"), project.get("description", ""), "admin"),
    )
    return {"project_id": project_id}, 201


@api_view
def project_detail(request, project_id: int, payload=None):
    if request.method == "GET":
        return fetch_one("SELECT * FROM projects WHERE id = %s", (project_id,))
    if request.method == "PUT":
        updated = execute(
            "UPDATE projects SET name = %s, description = %s WHERE id = %s",
            ((payload or {}).get("name"), (payload or {}).get("description", ""), project_id),
        )
        return {"updated": updated >= 0}
    return {"deleted": execute("DELETE FROM projects WHERE id = %s", (project_id,)) > 0}


@api_view
def project_stats(_request, project_id: int, payload=None):
    api_count = fetch_one("SELECT COUNT(*) AS count FROM api_templates WHERE project_id = %s", (project_id,))
    case_count = fetch_one("SELECT COUNT(*) AS count FROM test_cases WHERE project_id = %s", (project_id,))
    return {
        "api_count": api_count["count"] if api_count else 0,
        "case_count": case_count["count"] if case_count else 0,
    }


@api_view
def api_folders(request, payload=None):
    if request.method == "GET":
        return template_service.list_folders((payload or {}).get("project_id"))
    return template_service.create_folder(payload or {}), 201


@api_view
def api_folder_detail(request, folder_id: int, payload=None):
    if request.method == "GET":
        return fetch_one("SELECT * FROM api_folders WHERE id = %s", (folder_id,))
    if request.method == "PUT":
        return template_service.update_folder(folder_id, payload or {})
    return template_service.delete_folder(folder_id)


@api_view
def api_templates(request, payload=None):
    if request.method == "GET":
        return template_service.list_templates(
            project_id=(payload or {}).get("project_id"),
            folder_id=(payload or {}).get("folder_id"),
        )
    return template_service.create_template(payload or {}), 201


@api_view
def api_template_detail(request, template_id: int, payload=None):
    if request.method == "GET":
        return template_service.get_template(template_id)
    if request.method == "PUT":
        return template_service.update_template(template_id, payload or {})
    return template_service.delete_template(template_id)


@api_view
def api_template_workspace(_request, payload=None):
    return template_service.template_workspace((payload or {}).get("project_id"))


@api_view
def case_folders(request, payload=None):
    if request.method == "GET":
        project_id = get_int((payload or {}).get("project_id"))
        if not project_id:
            raise ValueError("project_id 不能为空")
        return fetch_all("SELECT * FROM case_folders WHERE project_id = %s ORDER BY sort_order, created_at", (project_id,))
    folder = payload or {}
    folder_id = execute(
        """
        INSERT INTO case_folders (project_id, parent_id, name, description, sort_order)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (folder.get("project_id"), folder.get("parent_id"), folder.get("name"), folder.get("description", ""), folder.get("sort_order", 0)),
    )
    return {"folder_id": folder_id}, 201


@api_view
def case_folder_detail(request, folder_id: int, payload=None):
    if request.method == "PUT":
        folder = payload or {}
        updated = execute(
            "UPDATE case_folders SET name = %s, description = %s WHERE id = %s",
            (folder.get("name"), folder.get("description", ""), folder_id),
        )
        return {"updated": updated >= 0}
    folder_ids = [folder_id]
    queue = [folder_id]
    while queue:
        current_folder_id = queue.pop()
        children = fetch_all("SELECT id FROM case_folders WHERE parent_id = %s", (current_folder_id,))
        child_ids = [item["id"] for item in children]
        folder_ids.extend(child_ids)
        queue.extend(child_ids)
    placeholders = ", ".join(["%s"] * len(folder_ids))
    case_rows = fetch_all(f"SELECT id FROM test_cases WHERE folder_id IN ({placeholders})", tuple(folder_ids))
    for row in case_rows:
        _delete_case_with_steps(row["id"])
    execute(f"DELETE FROM case_folders WHERE id IN ({placeholders})", tuple(folder_ids))
    return {"deleted": True}


@api_view
def cases(request, payload=None):
    _ensure_case_schema_extensions()
    if request.method == "GET":
        case_id = get_int((payload or {}).get("case_id"))
        folder_id = get_int((payload or {}).get("folder_id"))
        project_id = get_int((payload or {}).get("project_id"))
        if case_id:
            return _get_case_detail(case_id)
        if folder_id:
            return _list_cases("WHERE folder_id = %s", (folder_id,))
        if project_id:
            return _list_cases("WHERE project_id = %s", (project_id,))
        return _list_cases()
    item = payload or {}
    case_id = execute(
        """
        INSERT INTO test_cases (project_id, folder_id, name, description, environment_id, global_vars, global_request_config_text, output_variables_text, enable_encryption, encrypt_url, decrypt_url, sort_order, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            item.get("project_id"),
            item.get("folder_id"),
            item.get("name"),
            item.get("description", ""),
            item.get("environment_id"),
            _json_text(item.get("global_vars")),
            _json_text(item.get("global_request_config")),
            _empty_list_json(item.get("output_variables")),
            item.get("enable_encryption", False),
            item.get("encrypt_url", ""),
            item.get("decrypt_url", ""),
            item.get("sort_order", 0),
            "admin",
        ),
    )
    _write_case_steps(case_id, item.get("steps", []))
    return {"case_id": case_id}, 201


@api_view
def case_detail(request, case_id: int, payload=None):
    _ensure_case_schema_extensions()
    if request.method == "GET":
        return _get_case_detail(case_id)
    if request.method == "PUT":
        item = payload or {}
        updated = execute(
            """
            UPDATE test_cases
            SET name = %s, description = %s, folder_id = %s, environment_id = %s, global_vars = %s, global_request_config_text = %s, output_variables_text = %s, enable_encryption = %s, encrypt_url = %s, decrypt_url = %s, sort_order = %s
            WHERE id = %s
            """,
            (
                item.get("name"),
                item.get("description", ""),
                item.get("folder_id"),
                item.get("environment_id"),
                _json_text(item.get("global_vars")),
                _json_text(item.get("global_request_config")),
                _empty_list_json(item.get("output_variables")),
                item.get("enable_encryption", False),
                item.get("encrypt_url", ""),
                item.get("decrypt_url", ""),
                item.get("sort_order", 0),
                case_id,
            ),
        )
        if "steps" in item:
            _write_case_steps(case_id, item.get("steps", []))
        return {"updated": updated >= 0, "case": _get_case_detail(case_id)}
    return {"deleted": _delete_case_with_steps(case_id)}


@api_view
def execute_case(_request, case_id: int, payload=None):
    _ensure_case_schema_extensions()
    case = _hydrate_case_row(fetch_one("SELECT * FROM test_cases WHERE id = %s", (case_id,)))
    if not case:
        raise ValueError("测试用例不存在")

    execution_case = dict(case)
    execution_case["steps"] = _list_case_steps(case_id)
    if payload:
        execution_case.update(
            {
                "project_id": payload.get("project_id", execution_case.get("project_id")),
                "folder_id": payload.get("folder_id", execution_case.get("folder_id")),
                "name": payload.get("name", execution_case.get("name")),
                "description": payload.get("description", execution_case.get("description", "")),
                "environment_id": payload.get("environment_id", execution_case.get("environment_id")),
                "enable_encryption": payload.get("enable_encryption", execution_case.get("enable_encryption", False)),
                "encrypt_url": payload.get("encrypt_url", execution_case.get("encrypt_url", "")),
                "decrypt_url": payload.get("decrypt_url", execution_case.get("decrypt_url", "")),
                "sort_order": payload.get("sort_order", execution_case.get("sort_order", 0)),
            }
        )
        execution_case["global_vars"] = _json_value(
            payload.get("global_vars"),
            execution_case.get("global_vars", {}),
        )
        execution_case["global_request_config"] = _json_value(
            payload.get("global_request_config"),
            execution_case.get("global_request_config", {}),
        )
        execution_case["output_variables"] = _json_value(
            payload.get("output_variables"),
            execution_case.get("output_variables", []),
        )
        if "steps" in payload:
            execution_case["steps"] = [
                _hydrate_step_row(step)
                for step in (payload.get("steps") or [])
            ]
    return execute_case_run(execution_case)


@api_view
def schedulers(request, payload=None):
    if request.method == "GET":
        project_id = get_int((payload or {}).get("project_id"))
        if project_id:
            return fetch_all("SELECT * FROM test_schedulers WHERE project_id = %s ORDER BY updated_at DESC", (project_id,))
        return fetch_all("SELECT * FROM test_schedulers ORDER BY updated_at DESC")
    item = payload or {}
    created = execute(
        """
        INSERT INTO test_schedulers (project_id, name, description, cron_expression, enabled, case_ids, notify_emails, notify_wechat, email_config, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            item.get("project_id"),
            item.get("name"),
            item.get("description", ""),
            item.get("cron_expression", ""),
            item.get("enabled", False),
            _empty_list_json(item.get("case_ids")),
            _empty_list_json(item.get("notify_emails")),
            _empty_list_json(item.get("notify_wechat")),
            _json_text(item.get("email_config")),
            "system",
        ),
    )
    return {"created": True, "scheduler_id": created}


@api_view
def scheduler_detail(request, scheduler_id: int, payload=None):
    if request.method == "GET":
        return fetch_one("SELECT * FROM test_schedulers WHERE id = %s", (scheduler_id,))
    if request.method == "PUT":
        item = payload or {}
        updated = execute(
            """
            UPDATE test_schedulers
            SET project_id = %s, name = %s, description = %s, cron_expression = %s, enabled = %s, case_ids = %s, notify_emails = %s, notify_wechat = %s, email_config = %s
            WHERE id = %s
            """,
            (
                item.get("project_id"),
                item.get("name"),
                item.get("description", ""),
                item.get("cron_expression", ""),
                item.get("enabled", False),
                _empty_list_json(item.get("case_ids")),
                _empty_list_json(item.get("notify_emails")),
                _empty_list_json(item.get("notify_wechat")),
                _json_text(item.get("email_config")),
                scheduler_id,
            ),
        )
        return {"updated": updated >= 0}
    return {"deleted": execute("DELETE FROM test_schedulers WHERE id = %s", (scheduler_id,)) > 0}


@api_view
def scheduler_status(_request, scheduler_id: int, payload=None):
    updated = execute(
        "UPDATE test_schedulers SET enabled = %s, updated_at = %s WHERE id = %s",
        (bool((payload or {}).get("enabled", False)), datetime.now(), scheduler_id),
    )
    return {"updated": updated >= 0}


@api_view
def reports(_request, payload=None):
    return {
        "data": fetch_all("SELECT * FROM test_reports ORDER BY created_at DESC LIMIT 100"),
        "pagination": {
            "total": fetch_one("SELECT COUNT(*) AS count FROM test_reports")["count"],
            "page": 1,
            "page_size": 100,
            "total_pages": 1,
            "has_prev": False,
            "has_next": False,
        },
    }


@api_view
def report_detail(request, report_id: int, payload=None):
    if request.method == "GET":
        return fetch_one("SELECT * FROM test_reports WHERE id = %s", (report_id,))
    return {"deleted": execute("DELETE FROM test_reports WHERE id = %s", (report_id,)) > 0}


@api_view
def report_steps(_request, report_id: int, payload=None):
    return fetch_all("SELECT * FROM test_step_results WHERE report_id = %s ORDER BY step_order", (report_id,))


@api_view
def global_tools(request, payload=None):
    if request.method == "GET":
        tool_type = (payload or {}).get("tool_type")
        if tool_type:
            return fetch_all("SELECT * FROM global_tools WHERE tool_type = %s ORDER BY created_at DESC", (tool_type,))
        return fetch_all("SELECT * FROM global_tools ORDER BY created_at DESC")
    item = payload or {}
    tool_id = execute(
        """
        INSERT INTO global_tools (name, tool_type, description, config, enabled, created_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (item.get("name"), item.get("tool_type"), item.get("description", ""), _json_text(item.get("config")), item.get("enabled", True), "admin"),
    )
    return {"tool_id": tool_id}, 201


@api_view
def global_tool_detail(request, tool_id: int, payload=None):
    if request.method == "GET":
        return fetch_one("SELECT * FROM global_tools WHERE id = %s", (tool_id,))
    if request.method == "PUT":
        item = payload or {}
        updated = execute(
            "UPDATE global_tools SET name = %s, tool_type = %s, description = %s, config = %s, enabled = %s WHERE id = %s",
            (item.get("name"), item.get("tool_type"), item.get("description", ""), _json_text(item.get("config")), item.get("enabled", True), tool_id),
        )
        return {"updated": updated >= 0}
    return {"deleted": execute("DELETE FROM global_tools WHERE id = %s", (tool_id,)) > 0}


@api_view
def global_tool_status(_request, tool_id: int, payload=None):
    updated = execute("UPDATE global_tools SET enabled = %s WHERE id = %s", (bool((payload or {}).get("enabled", False)), tool_id))
    return {"updated": updated >= 0}


@api_view
def variables(request, payload=None):
    if request.method == "GET":
        project_id = get_int((payload or {}).get("project_id"), 0)
        return fetch_all("SELECT * FROM global_variables WHERE project_id = %s ORDER BY name ASC", (project_id,))
    item = payload or {}
    variable_id = execute(
        """
        INSERT INTO global_variables (project_id, name, value, variable_type, description, created_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (item.get("project_id", 0), item.get("name"), str(item.get("value", "")), item.get("variable_type", "string"), item.get("description", ""), "admin"),
    )
    return {"variable_id": variable_id}, 201


@api_view
def variable_detail(request, variable_id: int, payload=None):
    if request.method == "PUT":
        item = payload or {}
        updated = execute(
            "UPDATE global_variables SET project_id = %s, name = %s, value = %s, variable_type = %s, description = %s WHERE id = %s",
            (item.get("project_id", 0), item.get("name"), str(item.get("value", "")), item.get("variable_type", "string"), item.get("description", ""), variable_id),
        )
        return {"updated": updated >= 0}
    return {"deleted": execute("DELETE FROM global_variables WHERE id = %s", (variable_id,)) > 0}


@api_view
def environments(_request, payload=None):
    return fetch_all("SELECT * FROM environments ORDER BY created_at DESC")


@api_view
def environment_detail(_request, environment_id: int, payload=None):
    return fetch_one("SELECT * FROM environments WHERE id = %s", (environment_id,))
