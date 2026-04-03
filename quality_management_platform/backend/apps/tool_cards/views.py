from __future__ import annotations

from apps.common.http import api_view
from test_platform.db import execute, fetch_all, fetch_one


@api_view
def overview(_request, payload=None):
    return {
        "projects": fetch_all(
            """
            SELECT id, name, description, business_group_id, created_at, updated_at
            FROM projects
            ORDER BY id ASC
            """
        ),
        "folders": fetch_all(
            """
            SELECT id, name, description, parent_id, sort_order, is_default, created_at, updated_at
            FROM tool_card_folders
            ORDER BY parent_id IS NULL DESC, created_at ASC
            """
        ),
    }


@api_view
def folders(request, payload=None):
    if request.method == "GET":
        return overview(_request=None)["folders"]
    folder = payload or {}
    folder_id = execute(
        """
        INSERT INTO tool_card_folders (name, description, parent_id, sort_order, is_default, created_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            folder.get("name"),
            folder.get("description", ""),
            folder.get("parent_id"),
            folder.get("sort_order", 0),
            folder.get("is_default", False),
            "admin",
        ),
    )
    return {"folder_id": folder_id}, 201


@api_view
def folder_detail(request, folder_id: int, payload=None):
    if request.method == "GET":
        folder = fetch_one(
            """
            SELECT id, name, description, parent_id, sort_order, is_default, created_at, updated_at
            FROM tool_card_folders
            WHERE id = %s
            """,
            (folder_id,),
        )
        if not folder:
            raise ValueError("文件夹不存在")
        return {
            "folder": folder,
            "cards": fetch_all(
                """
                SELECT id, folder_id, name, description, card_type, config, mappings, sort_order, enabled
                FROM tool_card_items
                WHERE folder_id = %s
                ORDER BY sort_order ASC, id ASC
                """,
                (folder_id,),
            ),
            "children": fetch_all(
                """
                SELECT id, name, description, parent_id, sort_order, is_default, created_at, updated_at
                FROM tool_card_folders
                WHERE parent_id = %s
                ORDER BY created_at ASC
                """,
                (folder_id,),
            ),
        }
    if request.method == "PUT":
        folder = payload or {}
        updated = execute(
            """
            UPDATE tool_card_folders
            SET name = %s, description = %s, parent_id = %s, sort_order = %s, is_default = %s
            WHERE id = %s
            """,
            (
                folder.get("name"),
                folder.get("description", ""),
                folder.get("parent_id"),
                folder.get("sort_order", 0),
                folder.get("is_default", False),
                folder_id,
            ),
        )
        return {"updated": updated > 0}
    execute("DELETE FROM tool_card_items WHERE folder_id = %s", (folder_id,))
    deleted = execute("DELETE FROM tool_card_folders WHERE id = %s", (folder_id,))
    return {"deleted": deleted > 0}


@api_view
def cards(_request, payload=None):
    folder_id = int((payload or {}).get("folder_id", 0))
    if not folder_id:
        raise ValueError("folder_id 不能为空")
    return fetch_all(
        """
        SELECT id, folder_id, name, description, card_type, config, mappings, sort_order, enabled
        FROM tool_card_items
        WHERE folder_id = %s
        ORDER BY sort_order ASC, id ASC
        """,
        (folder_id,),
    )


@api_view
def create_card(_request, payload=None):
    card = payload or {}
    card_id = execute(
        """
        INSERT INTO tool_card_items (folder_id, name, description, card_type, config, mappings, sort_order, enabled, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            card.get("folder_id"),
            card.get("name"),
            card.get("description", ""),
            card.get("card_type", "sql"),
            card.get("config", "{}"),
            card.get("mappings", "{}"),
            card.get("sort_order", 0),
            card.get("enabled", True),
            "admin",
        ),
    )
    return {"card_id": card_id}, 201


@api_view
def card_detail(request, card_id: int, payload=None):
    if request.method == "GET":
        card = fetch_one(
            """
            SELECT id, folder_id, name, description, card_type, config, mappings, sort_order, enabled
            FROM tool_card_items
            WHERE id = %s
            """,
            (card_id,),
        )
        if not card:
            raise ValueError("卡片不存在")
        return card
    if request.method == "PUT":
        card = payload or {}
        updated = execute(
            """
            UPDATE tool_card_items
            SET name = %s, description = %s, card_type = %s, config = %s, mappings = %s, sort_order = %s, enabled = %s
            WHERE id = %s
            """,
            (
                card.get("name"),
                card.get("description", ""),
                card.get("card_type", "sql"),
                card.get("config", "{}"),
                card.get("mappings", "{}"),
                card.get("sort_order", 0),
                card.get("enabled", True),
                card_id,
            ),
        )
        return {"updated": updated >= 0}
    deleted = execute("DELETE FROM tool_card_items WHERE id = %s", (card_id,))
    return {"deleted": deleted > 0}


@api_view
def initialize_defaults(_request, payload=None):
    existing = fetch_one("SELECT id FROM tool_card_folders WHERE is_default = TRUE LIMIT 1")
    if existing:
        return {"initialized": True, "folder_id": existing["id"]}
    folder_id = execute(
        """
        INSERT INTO tool_card_folders (name, description, parent_id, sort_order, is_default, created_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        ("默认工具", "系统默认工具文件夹", None, 0, True, "admin"),
    )
    return {"initialized": True, "folder_id": folder_id}
