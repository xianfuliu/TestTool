from __future__ import annotations

import json
from datetime import datetime

from apps.common.http import api_view, get_int
from test_platform.db import execute, fetch_all, fetch_one

from . import template_service


def _json_text(value):
    return json.dumps(value or {}, ensure_ascii=False)


def _empty_list_json(value):
    return json.dumps(value or [], ensure_ascii=False)


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
    execute("DELETE FROM test_cases WHERE folder_id = %s", (folder_id,))
    return {"deleted": execute("DELETE FROM case_folders WHERE id = %s", (folder_id,)) > 0}


@api_view
def cases(request, payload=None):
    if request.method == "GET":
        case_id = get_int((payload or {}).get("case_id"))
        folder_id = get_int((payload or {}).get("folder_id"))
        project_id = get_int((payload or {}).get("project_id"))
        if case_id:
            case = fetch_one("SELECT * FROM test_cases WHERE id = %s", (case_id,))
            steps = fetch_all("SELECT * FROM test_case_steps WHERE case_id = %s ORDER BY step_order", (case_id,))
            return {**(case or {}), "steps": steps}
        if folder_id:
            return fetch_all("SELECT * FROM test_cases WHERE folder_id = %s ORDER BY sort_order, created_at", (folder_id,))
        if project_id:
            return fetch_all("SELECT * FROM test_cases WHERE project_id = %s ORDER BY sort_order, created_at", (project_id,))
        return fetch_all("SELECT * FROM test_cases ORDER BY created_at DESC")
    item = payload or {}
    case_id = execute(
        """
        INSERT INTO test_cases (project_id, folder_id, name, description, environment_id, global_vars, enable_encryption, encrypt_url, decrypt_url, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            item.get("project_id"),
            item.get("folder_id"),
            item.get("name"),
            item.get("description", ""),
            item.get("environment_id"),
            _json_text(item.get("global_vars")),
            item.get("enable_encryption", False),
            item.get("encrypt_url", ""),
            item.get("decrypt_url", ""),
            "admin",
        ),
    )
    for index, step in enumerate(item.get("steps", []), start=1):
        execute(
            """
            INSERT INTO test_case_steps (case_id, api_template_id, step_order, name, enabled, pre_processing, post_processing, assertions, variables, enable_encryption)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                case_id,
                step.get("api_template_id"),
                index,
                step.get("name", ""),
                step.get("enabled", True),
                _json_text(step.get("pre_processing")),
                _json_text(step.get("post_processing")),
                _json_text(step.get("assertions")),
                _json_text(step.get("variables")),
                step.get("enable_encryption", False),
            ),
        )
    return {"case_id": case_id}, 201


@api_view
def case_detail(request, case_id: int, payload=None):
    if request.method == "GET":
        return cases(_request=None, payload={"case_id": case_id})
    if request.method == "PUT":
        item = payload or {}
        updated = execute(
            """
            UPDATE test_cases
            SET name = %s, description = %s, folder_id = %s, environment_id = %s, global_vars = %s, enable_encryption = %s, encrypt_url = %s, decrypt_url = %s
            WHERE id = %s
            """,
            (
                item.get("name"),
                item.get("description", ""),
                item.get("folder_id"),
                item.get("environment_id"),
                _json_text(item.get("global_vars")),
                item.get("enable_encryption", False),
                item.get("encrypt_url", ""),
                item.get("decrypt_url", ""),
                case_id,
            ),
        )
        return {"updated": updated >= 0}
    execute("DELETE FROM test_case_steps WHERE case_id = %s", (case_id,))
    return {"deleted": execute("DELETE FROM test_cases WHERE id = %s", (case_id,)) > 0}


@api_view
def execute_case(_request, case_id: int, payload=None):
    case = fetch_one("SELECT * FROM test_cases WHERE id = %s", (case_id,))
    steps = fetch_all("SELECT * FROM test_case_steps WHERE case_id = %s ORDER BY step_order", (case_id,))
    return {
        "case_id": case_id,
        "case_name": case["name"] if case else "未知用例",
        "status": "success",
        "message": "质量管理平台新版执行引擎待迁移，当前返回结构化占位结果",
        "steps": [
            {
                "step_id": step["id"],
                "step_order": step["step_order"],
                "step_name": step["name"],
                "status": "pending",
            }
            for step in steps
        ],
    }


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
