from __future__ import annotations

from django.conf import settings

from .http import api_view, get_int
from .environment_service import (
    create_environment,
    delete_environment,
    get_environment,
    list_environments,
    update_environment,
)
from .legacy import get_fastapi_route_catalog
from test_platform.db import execute, fetch_all, fetch_one


@api_view
def health(_request, payload=None):
    return {
        "project": "Quality Management Platform",
        "backend": "Django",
        "frontend": "Vue 3 + Element Plus",
        "repo_root": str(settings.BASE_DIR.parent),
        "modules": [
            "authentication",
            "test_data",
            "api_tool",
            "interface_auto",
            "tool_cards",
            "data_query",
            "api_management",
        ],
    }


@api_view
def legacy_routes(_request, payload=None):
    return get_fastapi_route_catalog()


@api_view
def business_groups(request, payload=None):
    if request.method == "GET":
        return fetch_all("SELECT * FROM business_groups ORDER BY created_at ASC")

    item = payload or {}
    group_id = execute(
        "INSERT INTO business_groups (name, description, created_by) VALUES (%s, %s, %s)",
        (item.get("name"), item.get("description", ""), "admin"),
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

    linked_projects = fetch_one("SELECT COUNT(*) AS count FROM projects WHERE business_group_id = %s", (group_id,))
    if linked_projects and linked_projects["count"]:
        raise ValueError("当前业务组下仍有关联项目，请先调整项目归属后再删除业务组")

    return {"deleted": execute("DELETE FROM business_groups WHERE id = %s", (group_id,)) > 0}


@api_view
def business_group_stats(_request, group_id: int, payload=None):
    project_count = fetch_one("SELECT COUNT(*) AS count FROM projects WHERE business_group_id = %s", (group_id,))
    api_count = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM api_templates
        WHERE project_id IN (SELECT id FROM projects WHERE business_group_id = %s)
        """,
        (group_id,),
    )
    case_count = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM test_cases
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
        group_id = get_int((payload or {}).get("group_id") or (payload or {}).get("business_group_id"))
        if group_id:
            return fetch_all(
                """
                SELECT p.*, bg.name AS group_name
                FROM projects p
                LEFT JOIN business_groups bg ON p.business_group_id = bg.id
                WHERE p.business_group_id = %s
                ORDER BY p.created_at ASC
                """,
                (group_id,),
            )
        return fetch_all(
            """
            SELECT p.*, bg.name AS group_name
            FROM projects p
            LEFT JOIN business_groups bg ON p.business_group_id = bg.id
            ORDER BY p.created_at ASC
            """
        )

    item = payload or {}
    project_id = execute(
        """
        INSERT INTO projects (business_group_id, name, description, created_by)
        VALUES (%s, %s, %s, %s)
        """,
        (
            item.get("business_group_id") or item.get("group_id"),
            item.get("name"),
            item.get("description", ""),
            "admin",
        ),
    )
    return {"project_id": project_id}, 201


@api_view
def project_detail(request, project_id: int, payload=None):
    if request.method == "GET":
        return fetch_one(
            """
            SELECT p.*, bg.name AS group_name
            FROM projects p
            LEFT JOIN business_groups bg ON p.business_group_id = bg.id
            WHERE p.id = %s
            """,
            (project_id,),
        )

    if request.method == "PUT":
        updated = execute(
            "UPDATE projects SET business_group_id = %s, name = %s, description = %s WHERE id = %s",
            (
                (payload or {}).get("business_group_id") or (payload or {}).get("group_id"),
                (payload or {}).get("name"),
                (payload or {}).get("description", ""),
                project_id,
            ),
        )
        return {"updated": updated >= 0}

    relation_checks = [
        ("api_folders", "接口目录"),
        ("api_templates", "接口模板"),
        ("case_folders", "用例目录"),
        ("test_cases", "测试用例"),
        ("test_suites", "测试集"),
        ("global_variables", "项目变量"),
        ("test_schedulers", "定时任务"),
        ("test_reports", "测试报告"),
    ]
    blocked_by: list[str] = []
    for table_name, label in relation_checks:
        count_row = fetch_one(f"SELECT COUNT(*) AS count FROM {table_name} WHERE project_id = %s", (project_id,))
        if count_row and count_row["count"]:
            blocked_by.append(label)
    if blocked_by:
        raise ValueError(f"当前项目下仍有关联数据：{'、'.join(blocked_by)}，请先清理后再删除项目")

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
def environments(request, payload=None):
    if request.method == "GET":
        return list_environments()
    return create_environment(payload or {})


@api_view
def environment_detail(request, environment_id: int, payload=None):
    if request.method == "GET":
        return get_environment(environment_id)
    if request.method == "PUT":
        return update_environment(environment_id, payload or {})
    return delete_environment(environment_id)
