from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pymysql
import requests

from test_platform.db import connect, ensure_database, fetch_all, fetch_one
from test_platform.schema import SCHEMA_SQL


REPO_ROOT = Path(__file__).resolve().parents[4]
LEGACY_TOOL_CARD_CONFIG_CANDIDATES = [
    REPO_ROOT / "config" / "tool_cards.json",
]

FIELD_TYPE_INPUT = "input"
FIELD_TYPE_SELECT = "select"
FIELD_TYPE_MULTI_SELECT = "multi_select"
FIELD_TYPE_RADIO = "radio"
ENUM_FIELD_TYPES = {FIELD_TYPE_SELECT, FIELD_TYPE_MULTI_SELECT, FIELD_TYPE_RADIO}


def _json_loads(value: Any, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _normalize_association_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return []
        try:
            parsed = json.loads(trimmed)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        if "," in trimmed:
            return [item.strip() for item in trimmed.split(",") if item.strip()]
        return [trimmed]
    return [str(value).strip()] if str(value).strip() else []


def _ensure_schema_ready() -> None:
    ensure_database()
    with connect() as connection:
        with connection.cursor() as cursor:
            for sql in SCHEMA_SQL:
                cursor.execute(sql)
        connection.commit()


def _legacy_tool_cards_path() -> Path | None:
    for candidate in LEGACY_TOOL_CARD_CONFIG_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def _normalize_folder_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(payload.get("name") or "").strip(),
        "description": str(payload.get("description") or "").strip(),
        "parent_id": int(payload["parent_id"]) if payload.get("parent_id") not in (None, "") else None,
        "sort_order": int(payload.get("sort_order") or 0),
        "is_default": bool(payload.get("is_default", False)),
    }


def _normalize_parameter_options(payload: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for index, option in enumerate(payload or [], start=1):
        option_dict = _as_dict(option)
        value = str(option_dict.get("value") or option_dict.get("option_value") or "").strip()
        label = str(
            option_dict.get("label")
            or option_dict.get("description")
            or option_dict.get("option_label")
            or value
        ).strip()
        if not value and not label:
            continue
        options.append(
            {
                "option_value": value,
                "option_label": label or value,
                "sort_order": int(option_dict.get("sort_order") or index),
            }
        )
    return options


def _normalize_parameters(payload: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    parameters: list[dict[str, Any]] = []
    for index, item in enumerate(payload or [], start=1):
        item_dict = _as_dict(item)
        field_key = str(item_dict.get("field_key") or item_dict.get("key") or "").strip()
        display_name = str(item_dict.get("display_name") or item_dict.get("label") or "").strip()
        if not field_key or not display_name:
            continue
        field_type = str(item_dict.get("field_type") or item_dict.get("type") or FIELD_TYPE_INPUT).strip() or FIELD_TYPE_INPUT
        parameters.append(
            {
                "field_key": field_key,
                "display_name": display_name,
                "field_type": field_type,
                "default_value": item_dict.get("default_value", item_dict.get("default", "")),
                "required": bool(item_dict.get("required", False)),
                "association_enabled": bool(item_dict.get("association_enabled", False)),
                "association_field": str(item_dict.get("association_field") or "").strip(),
                "association_value": _normalize_association_values(item_dict.get("association_value")),
                "sort_order": int(item_dict.get("sort_order") or item_dict.get("order") or index),
                "options": _normalize_parameter_options(_as_list(item_dict.get("options"))),
            }
        )
    return parameters


def _normalize_card_payload(payload: dict[str, Any]) -> dict[str, Any]:
    card_type = str(payload.get("card_type") or payload.get("type") or "sql").strip().lower() or "sql"
    parameters = _normalize_parameters(_as_list(payload.get("parameters")))
    return {
        "folder_id": int(payload["folder_id"]) if payload.get("folder_id") not in (None, "") else None,
        "name": str(payload.get("name") or "").strip(),
        "description": str(payload.get("description") or "").strip(),
        "card_type": card_type,
        "sort_order": int(payload.get("sort_order") or 0),
        "enabled": bool(payload.get("enabled", True)),
        "parameters": parameters,
        "sql_config": _as_dict(payload.get("sql_config")),
        "http_config": _as_dict(payload.get("http_config")),
        "python_config": _as_dict(payload.get("python_config")),
        "config": _as_dict(payload.get("config")),
        "mappings": _as_dict(payload.get("mappings")),
    }


def _normalize_sql_config(payload: dict[str, Any]) -> dict[str, Any]:
    payload = _as_dict(payload)
    if not payload and payload != {}:
        payload = {}
    database = _as_dict(payload.get("database"))
    return {
        "host": str(database.get("host") or payload.get("host") or "").strip(),
        "port": int(database.get("port") or payload.get("port") or 3306),
        "username": str(database.get("user") or payload.get("username") or "").strip(),
        "password": str(database.get("password") or "").strip(),
        "database_name": str(database.get("name") or database.get("database") or payload.get("database_name") or "").strip(),
        "query_text": str(payload.get("query") or payload.get("sql") or payload.get("query_text") or "").strip(),
    }


def _normalize_http_config(payload: dict[str, Any]) -> dict[str, Any]:
    payload = _as_dict(payload)
    headers = payload.get("headers")
    body = payload.get("body")
    return {
        "url": str(payload.get("url") or "").strip(),
        "method": str(payload.get("method") or "GET").strip().upper() or "GET",
        "headers_text": _json_dumps(_as_dict(headers)) if headers not in (None, "") else "",
        "body_text": _json_dumps(body) if body not in (None, "") else "",
    }


def _normalize_python_config(payload: dict[str, Any]) -> dict[str, Any]:
    payload = _as_dict(payload)
    args = payload.get("args")
    return {
        "module_name": str(payload.get("module") or payload.get("module_name") or "").strip(),
        "class_name": str(payload.get("class") or payload.get("class_name") or "").strip(),
        "method_name": str(payload.get("method") or payload.get("method_name") or "").strip(),
        "args_text": _json_dumps(args) if args not in (None, "") else "",
    }


def _parameter_row_to_payload(parameter_row: dict[str, Any], options: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": parameter_row["id"],
        "field_key": parameter_row["field_key"],
        "display_name": parameter_row["display_name"],
        "field_type": parameter_row["field_type"] or FIELD_TYPE_INPUT,
        "default_value": parameter_row.get("default_value"),
        "required": bool(parameter_row.get("required", False)),
        "association_enabled": bool(parameter_row.get("association_enabled", False)),
        "association_field": parameter_row.get("association_field") or "",
        "association_value": _normalize_association_values(parameter_row.get("association_value")),
        "sort_order": int(parameter_row.get("sort_order") or 0),
        "options": [
            {
                "id": option["id"],
                "value": option.get("option_value") or "",
                "label": option.get("option_label") or option.get("option_value") or "",
                "sort_order": int(option.get("sort_order") or 0),
            }
            for option in options
        ],
    }


def _parameters_to_legacy_mappings(parameters: list[dict[str, Any]]) -> dict[str, Any]:
    mappings: dict[str, Any] = {}
    for item in parameters:
        mappings[item["field_key"]] = {
            "display_name": item["display_name"],
            "type": item["field_type"],
            "required": bool(item.get("required", False)),
            "order": int(item.get("sort_order") or 0),
            "default_value": item.get("default_value", ""),
            "association_enabled": bool(item.get("association_enabled", False)),
            "association_field": item.get("association_field", ""),
            "association_value": _normalize_association_values(item.get("association_value")),
            "options": [
                {
                    "value": option.get("value") or "",
                    "description": option.get("label") or option.get("value") or "",
                    "sort_order": int(option.get("sort_order") or 0),
                }
                for option in item.get("options", [])
            ],
        }
    return mappings


def _card_configs_to_legacy(card_type: str, sql_config: dict[str, Any], http_config: dict[str, Any], python_config: dict[str, Any]) -> dict[str, Any]:
    if card_type == "sql":
        return {
            "database": {
                "host": sql_config.get("host", ""),
                "port": sql_config.get("port", 3306),
                "name": sql_config.get("database_name", ""),
                "user": sql_config.get("username", ""),
                "password": sql_config.get("password", ""),
            },
            "query": sql_config.get("query_text", ""),
            "sql": sql_config.get("query_text", ""),
        }
    if card_type == "http":
        return {
            "url": http_config.get("url", ""),
            "method": http_config.get("method", "GET"),
            "headers": _json_loads(http_config.get("headers_text"), {}),
            "body": _json_loads(http_config.get("body_text"), {}),
        }
    return {
        "module": python_config.get("module_name", ""),
        "class": python_config.get("class_name", ""),
        "method": python_config.get("method_name", ""),
        "args": _json_loads(python_config.get("args_text"), []),
    }


def _load_card_parameters(card_id: int) -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT id, card_id, field_key, display_name, field_type, default_value, required,
               association_enabled, association_field, association_value, sort_order
        FROM tool_card_parameters
        WHERE card_id = %s
        ORDER BY sort_order ASC, id ASC
        """,
        (card_id,),
    )
    option_rows = fetch_all(
        """
        SELECT id, parameter_id, option_value, option_label, sort_order
        FROM tool_card_parameter_options
        WHERE parameter_id IN (
            SELECT id FROM tool_card_parameters WHERE card_id = %s
        )
        ORDER BY sort_order ASC, id ASC
        """,
        (card_id,),
    )
    options_map: dict[int, list[dict[str, Any]]] = {}
    for option_row in option_rows:
        options_map.setdefault(option_row["parameter_id"], []).append(option_row)
    return [
        _parameter_row_to_payload(row, options_map.get(row["id"], []))
        for row in rows
    ]


def _load_type_configs(card_id: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    sql_config = fetch_one(
        """
        SELECT host, port, username, password, database_name, query_text
        FROM tool_card_sql_configs
        WHERE card_id = %s
        """,
        (card_id,),
    ) or {}
    http_config = fetch_one(
        """
        SELECT url, method, headers_text, body_text
        FROM tool_card_http_configs
        WHERE card_id = %s
        """,
        (card_id,),
    ) or {}
    python_config = fetch_one(
        """
        SELECT module_name, class_name, method_name, args_text
        FROM tool_card_python_configs
        WHERE card_id = %s
        """,
        (card_id,),
    ) or {}
    return sql_config, http_config, python_config


def _build_card_detail(card_row: dict[str, Any]) -> dict[str, Any]:
    card_id = int(card_row["id"])
    sql_config, http_config, python_config = _load_type_configs(card_id)
    parameters = _load_card_parameters(card_id)
    return {
        "id": card_id,
        "folder_id": int(card_row["folder_id"]),
        "name": card_row["name"],
        "description": card_row.get("description") or "",
        "card_type": card_row.get("card_type") or "sql",
        "type": card_row.get("card_type") or "sql",
        "sort_order": int(card_row.get("sort_order") or 0),
        "enabled": bool(card_row.get("enabled", True)),
        "sql_config": sql_config,
        "http_config": http_config,
        "python_config": python_config,
        "config": _card_configs_to_legacy(card_row.get("card_type") or "sql", sql_config, http_config, python_config),
        "parameters": parameters,
        "mappings": _parameters_to_legacy_mappings(parameters),
        "created_at": card_row.get("created_at"),
        "updated_at": card_row.get("updated_at"),
    }


def _folder_has_cards_recursive(folder_id: int) -> tuple[bool, dict[str, Any] | None, int]:
    cards = fetch_all(
        """
        SELECT id FROM tool_card_items
        WHERE folder_id = %s AND enabled = TRUE
        """,
        (folder_id,),
    )
    if cards:
        folder = fetch_one(
            """
            SELECT id, name, description, parent_id, sort_order, is_default, created_at, updated_at
            FROM tool_card_folders
            WHERE id = %s
            """,
            (folder_id,),
        )
        return True, folder, len(cards)

    children = fetch_all(
        """
        SELECT id
        FROM tool_card_folders
        WHERE parent_id = %s
        ORDER BY sort_order ASC, id ASC
        """,
        (folder_id,),
    )
    for child in children:
        has_cards, folder, card_count = _folder_has_cards_recursive(int(child["id"]))
        if has_cards:
            return True, folder, card_count
    return False, None, 0


def _create_default_folder_if_needed() -> None:
    existing = fetch_one("SELECT id FROM tool_card_folders LIMIT 1")
    if existing:
        return
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tool_card_folders (name, description, parent_id, sort_order, is_default, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                ("默认工具", "系统默认工具文件夹", None, 0, True, "system"),
            )
        connection.commit()


def _import_legacy_tool_card_file() -> bool:
    legacy_path = _legacy_tool_cards_path()
    if not legacy_path:
        return False
    current_folder = fetch_one("SELECT id FROM tool_card_folders LIMIT 1")
    if current_folder:
        return False

    payload = _json_loads(legacy_path.read_text(encoding="utf-8"), {})
    folders = _as_list(_as_dict(payload).get("folders"))
    if not folders:
        return False

    with connect() as connection:
        with connection.cursor() as cursor:
            for folder in folders:
                folder_dict = _as_dict(folder)
                cursor.execute(
                    """
                    INSERT INTO tool_card_folders (id, name, description, parent_id, sort_order, is_default, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        description = VALUES(description),
                        parent_id = VALUES(parent_id),
                        sort_order = VALUES(sort_order),
                        is_default = VALUES(is_default)
                    """,
                    (
                        int(folder_dict.get("id") or 0),
                        str(folder_dict.get("name") or "").strip() or "未命名文件夹",
                        str(folder_dict.get("description") or "").strip(),
                        int(folder_dict["parent_id"]) if folder_dict.get("parent_id") not in (None, "") else None,
                        int(folder_dict.get("sort_order") or 0),
                        bool(folder_dict.get("is_default", False)),
                        "legacy",
                    ),
                )
        connection.commit()
    return True


def _import_legacy_card_cache(force: bool = False) -> bool:
    has_normalized = fetch_one("SELECT id FROM tool_card_parameters LIMIT 1")
    if has_normalized and not force:
        return False

    legacy_cards = fetch_all(
        """
        SELECT id, folder_id, name, description, card_type, config, mappings, sort_order, enabled, created_at, updated_at
        FROM tool_card_items
        ORDER BY sort_order ASC, id ASC
        """
    )
    if not legacy_cards:
        return False

    with connect() as connection:
        with connection.cursor() as cursor:
            if force:
                cursor.execute("DELETE FROM tool_card_parameter_options")
                cursor.execute("DELETE FROM tool_card_parameters")
                cursor.execute("DELETE FROM tool_card_python_configs")
                cursor.execute("DELETE FROM tool_card_http_configs")
                cursor.execute("DELETE FROM tool_card_sql_configs")

            for row in legacy_cards:
                card_type = str(row.get("card_type") or "sql").strip().lower()
                legacy_config = _as_dict(_json_loads(row.get("config"), {}))
                legacy_mappings = _as_dict(_json_loads(row.get("mappings"), {}))

                if card_type == "sql":
                    sql_config = _normalize_sql_config(legacy_config)
                    cursor.execute(
                        """
                        INSERT INTO tool_card_sql_configs (card_id, host, port, username, password, database_name, query_text)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            host = VALUES(host),
                            port = VALUES(port),
                            username = VALUES(username),
                            password = VALUES(password),
                            database_name = VALUES(database_name),
                            query_text = VALUES(query_text)
                        """,
                        (
                            row["id"],
                            sql_config["host"],
                            sql_config["port"],
                            sql_config["username"],
                            sql_config["password"],
                            sql_config["database_name"],
                            sql_config["query_text"],
                        ),
                    )
                elif card_type == "http":
                    http_config = _normalize_http_config(legacy_config)
                    cursor.execute(
                        """
                        INSERT INTO tool_card_http_configs (card_id, url, method, headers_text, body_text)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            url = VALUES(url),
                            method = VALUES(method),
                            headers_text = VALUES(headers_text),
                            body_text = VALUES(body_text)
                        """,
                        (
                            row["id"],
                            http_config["url"],
                            http_config["method"],
                            http_config["headers_text"],
                            http_config["body_text"],
                        ),
                    )
                else:
                    python_config = _normalize_python_config(legacy_config)
                    cursor.execute(
                        """
                        INSERT INTO tool_card_python_configs (card_id, module_name, class_name, method_name, args_text)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            module_name = VALUES(module_name),
                            class_name = VALUES(class_name),
                            method_name = VALUES(method_name),
                            args_text = VALUES(args_text)
                        """,
                        (
                            row["id"],
                            python_config["module_name"],
                            python_config["class_name"],
                            python_config["method_name"],
                            python_config["args_text"],
                        ),
                    )

                if force:
                    cursor.execute("DELETE FROM tool_card_parameters WHERE card_id = %s", (row["id"],))

                for index, (field_key, mapping) in enumerate(legacy_mappings.items(), start=1):
                    mapping_dict = _as_dict(mapping)
                    cursor.execute(
                        """
                        INSERT INTO tool_card_parameters
                        (card_id, field_key, display_name, field_type, default_value, required, association_enabled, association_field, association_value, sort_order)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            row["id"],
                            str(field_key),
                            str(mapping_dict.get("display_name") or field_key),
                            str(mapping_dict.get("type") or FIELD_TYPE_INPUT),
                            mapping_dict.get("default_value", ""),
                            bool(mapping_dict.get("required", False)),
                            bool(mapping_dict.get("association_enabled", False)),
                            str(mapping_dict.get("association_field") or ""),
                            _json_dumps(_normalize_association_values(mapping_dict.get("association_value"))),
                            int(mapping_dict.get("order") or index),
                        ),
                    )
                    parameter_id = cursor.lastrowid
                    for option_index, option in enumerate(_as_list(mapping_dict.get("options")), start=1):
                        option_dict = _as_dict(option)
                        cursor.execute(
                            """
                            INSERT INTO tool_card_parameter_options (parameter_id, option_value, option_label, sort_order)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (
                                parameter_id,
                                str(option_dict.get("value") or ""),
                                str(option_dict.get("description") or option_dict.get("label") or option_dict.get("value") or ""),
                                int(option_dict.get("sort_order") or option_index),
                            ),
                        )
        connection.commit()
    return True


def _ensure_bootstrap(force: bool = False) -> dict[str, Any]:
    _ensure_schema_ready()
    imported_file = _import_legacy_tool_card_file()
    _create_default_folder_if_needed()
    imported_cache = _import_legacy_card_cache(force=force)
    folders = list_folders()
    selected_folder_id = next((folder["id"] for folder in folders if folder.get("is_default")), None)
    if selected_folder_id is None and folders:
        selected_folder_id = folders[0]["id"]
    return {
        "folders": folders,
        "selected_folder_id": selected_folder_id,
        "imported_from_json": imported_file,
        "imported_from_legacy_cache": imported_cache,
    }


def list_folders() -> list[dict[str, Any]]:
    _ensure_schema_ready()
    rows = fetch_all(
        """
        SELECT
            f.id,
            f.name,
            f.description,
            f.parent_id,
            f.sort_order,
            f.is_default,
            f.created_at,
            f.updated_at,
            (
                SELECT COUNT(1)
                FROM tool_card_items i
                WHERE i.folder_id = f.id AND i.enabled = TRUE
            ) AS card_count
        FROM tool_card_folders f
        ORDER BY
            CASE WHEN f.parent_id IS NULL THEN 0 ELSE 1 END ASC,
            f.sort_order ASC,
            f.id ASC
        """
    )
    return [
        {
            "id": int(row["id"]),
            "name": row["name"],
            "description": row.get("description") or "",
            "parent_id": row.get("parent_id"),
            "sort_order": int(row.get("sort_order") or 0),
            "is_default": bool(row.get("is_default", False)),
            "card_count": int(row.get("card_count") or 0),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }
        for row in rows
    ]


def get_folder_detail(folder_id: int) -> dict[str, Any]:
    bootstrap = _ensure_bootstrap()
    folder = next((item for item in bootstrap["folders"] if item["id"] == folder_id), None)
    if not folder:
        raise ValueError("文件夹不存在")
    children = [item for item in bootstrap["folders"] if item.get("parent_id") == folder_id]
    cards = list_cards_by_folder(folder_id)
    return {
        "folder": folder,
        "children": children,
        "cards": cards,
    }


def list_cards_by_folder(folder_id: int) -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT id, folder_id, name, description, card_type, sort_order, enabled, created_at, updated_at
        FROM tool_card_items
        WHERE folder_id = %s
        ORDER BY sort_order ASC, id ASC
        """,
        (folder_id,),
    )
    return [_build_card_detail(row) for row in rows]


def get_card_detail(card_id: int) -> dict[str, Any]:
    _ensure_bootstrap()
    row = fetch_one(
        """
        SELECT id, folder_id, name, description, card_type, sort_order, enabled, created_at, updated_at
        FROM tool_card_items
        WHERE id = %s
        """,
        (card_id,),
    )
    if not row:
        raise ValueError("卡片不存在")
    return _build_card_detail(row)


def create_folder(payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_bootstrap()
    folder = _normalize_folder_payload(payload)
    if not folder["name"]:
        raise ValueError("文件夹名称不能为空")
    if folder["parent_id"] is not None:
        parent = fetch_one("SELECT id, parent_id FROM tool_card_folders WHERE id = %s", (folder["parent_id"],))
        if not parent:
            raise ValueError("父文件夹不存在")
        if parent.get("parent_id") is not None:
            raise ValueError("工具卡片最多支持两级文件夹")

    with connect() as connection:
        with connection.cursor() as cursor:
            if folder["is_default"]:
                cursor.execute("UPDATE tool_card_folders SET is_default = FALSE")
            cursor.execute(
                """
                INSERT INTO tool_card_folders (name, description, parent_id, sort_order, is_default, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    folder["name"],
                    folder["description"],
                    folder["parent_id"],
                    folder["sort_order"],
                    folder["is_default"],
                    "admin",
                ),
            )
            folder_id = cursor.lastrowid
        connection.commit()
    return get_folder_detail(int(folder_id))


def update_folder(folder_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_bootstrap()
    existing = fetch_one("SELECT id, parent_id FROM tool_card_folders WHERE id = %s", (folder_id,))
    if not existing:
        raise ValueError("文件夹不存在")

    folder = _normalize_folder_payload(payload)
    if not folder["name"]:
        raise ValueError("文件夹名称不能为空")
    if folder["parent_id"] == folder_id:
        raise ValueError("文件夹不能选择自己作为父级")
    if folder["parent_id"] is not None:
        parent = fetch_one("SELECT id, parent_id FROM tool_card_folders WHERE id = %s", (folder["parent_id"],))
        if not parent:
            raise ValueError("父文件夹不存在")
        if parent.get("parent_id") is not None:
            raise ValueError("工具卡片最多支持两级文件夹")

    with connect() as connection:
        with connection.cursor() as cursor:
            if folder["is_default"]:
                cursor.execute("UPDATE tool_card_folders SET is_default = FALSE")
            cursor.execute(
                """
                UPDATE tool_card_folders
                SET name = %s, description = %s, parent_id = %s, sort_order = %s, is_default = %s
                WHERE id = %s
                """,
                (
                    folder["name"],
                    folder["description"],
                    folder["parent_id"],
                    folder["sort_order"],
                    folder["is_default"],
                    folder_id,
                ),
            )
        connection.commit()
    return get_folder_detail(folder_id)


def delete_folder(folder_id: int) -> dict[str, Any]:
    _ensure_bootstrap()
    folder = fetch_one("SELECT id, name FROM tool_card_folders WHERE id = %s", (folder_id,))
    if not folder:
        raise ValueError("文件夹不存在")
    has_cards, problem_folder, card_count = _folder_has_cards_recursive(folder_id)
    if has_cards:
        folder_name = problem_folder["name"] if problem_folder else folder["name"]
        raise ValueError(f"文件夹“{folder_name}”下仍有 {card_count} 个卡片，请先删除或移动卡片")

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE copt
                FROM tool_card_parameter_options copt
                JOIN tool_card_parameters cp ON cp.id = copt.parameter_id
                JOIN tool_card_items ci ON ci.id = cp.card_id
                WHERE ci.folder_id IN (
                    SELECT id FROM (
                        SELECT id FROM tool_card_folders WHERE id = %s OR parent_id = %s
                    ) AS folder_scope
                )
                """,
                (folder_id, folder_id),
            )
            cursor.execute(
                """
                DELETE cp
                FROM tool_card_parameters cp
                JOIN tool_card_items ci ON ci.id = cp.card_id
                WHERE ci.folder_id IN (
                    SELECT id FROM (
                        SELECT id FROM tool_card_folders WHERE id = %s OR parent_id = %s
                    ) AS folder_scope
                )
                """,
                (folder_id, folder_id),
            )
            cursor.execute(
                """
                DELETE s
                FROM tool_card_sql_configs s
                JOIN tool_card_items ci ON ci.id = s.card_id
                WHERE ci.folder_id IN (
                    SELECT id FROM (
                        SELECT id FROM tool_card_folders WHERE id = %s OR parent_id = %s
                    ) AS folder_scope
                )
                """,
                (folder_id, folder_id),
            )
            cursor.execute(
                """
                DELETE h
                FROM tool_card_http_configs h
                JOIN tool_card_items ci ON ci.id = h.card_id
                WHERE ci.folder_id IN (
                    SELECT id FROM (
                        SELECT id FROM tool_card_folders WHERE id = %s OR parent_id = %s
                    ) AS folder_scope
                )
                """,
                (folder_id, folder_id),
            )
            cursor.execute(
                """
                DELETE p
                FROM tool_card_python_configs p
                JOIN tool_card_items ci ON ci.id = p.card_id
                WHERE ci.folder_id IN (
                    SELECT id FROM (
                        SELECT id FROM tool_card_folders WHERE id = %s OR parent_id = %s
                    ) AS folder_scope
                )
                """,
                (folder_id, folder_id),
            )
            cursor.execute(
                """
                DELETE FROM tool_card_items
                WHERE folder_id IN (
                    SELECT id FROM (
                        SELECT id FROM tool_card_folders WHERE id = %s OR parent_id = %s
                    ) AS folder_scope
                )
                """,
                (folder_id, folder_id),
            )
            cursor.execute("DELETE FROM tool_card_folders WHERE parent_id = %s", (folder_id,))
            cursor.execute("DELETE FROM tool_card_folders WHERE id = %s", (folder_id,))
        connection.commit()
    return {"deleted": True, "folder_id": folder_id}


def _save_card_relations(cursor, card_id: int, card_type: str, payload: dict[str, Any]) -> None:
    sql_config = _normalize_sql_config(payload["sql_config"] or payload["config"])
    http_config = _normalize_http_config(payload["http_config"] or payload["config"])
    python_config = _normalize_python_config(payload["python_config"] or payload["config"])
    parameters = payload["parameters"] or _normalize_parameters(
        [
            {"field_key": key, **_as_dict(value)}
            for key, value in payload["mappings"].items()
        ]
    )

    cursor.execute("DELETE FROM tool_card_parameter_options WHERE parameter_id IN (SELECT id FROM (SELECT id FROM tool_card_parameters WHERE card_id = %s) AS p)", (card_id,))
    cursor.execute("DELETE FROM tool_card_parameters WHERE card_id = %s", (card_id,))
    cursor.execute("DELETE FROM tool_card_sql_configs WHERE card_id = %s", (card_id,))
    cursor.execute("DELETE FROM tool_card_http_configs WHERE card_id = %s", (card_id,))
    cursor.execute("DELETE FROM tool_card_python_configs WHERE card_id = %s", (card_id,))

    if card_type == "sql":
        cursor.execute(
            """
            INSERT INTO tool_card_sql_configs (card_id, host, port, username, password, database_name, query_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                card_id,
                sql_config["host"],
                sql_config["port"],
                sql_config["username"],
                sql_config["password"],
                sql_config["database_name"],
                sql_config["query_text"],
            ),
        )
    elif card_type == "http":
        cursor.execute(
            """
            INSERT INTO tool_card_http_configs (card_id, url, method, headers_text, body_text)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                card_id,
                http_config["url"],
                http_config["method"],
                http_config["headers_text"],
                http_config["body_text"],
            ),
        )
    else:
        cursor.execute(
            """
            INSERT INTO tool_card_python_configs (card_id, module_name, class_name, method_name, args_text)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                card_id,
                python_config["module_name"],
                python_config["class_name"],
                python_config["method_name"],
                python_config["args_text"],
            ),
        )

    for param in parameters:
        cursor.execute(
            """
            INSERT INTO tool_card_parameters
            (card_id, field_key, display_name, field_type, default_value, required, association_enabled, association_field, association_value, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                card_id,
                param["field_key"],
                param["display_name"],
                param["field_type"],
                param.get("default_value", ""),
                param.get("required", False),
                param.get("association_enabled", False),
                param.get("association_field", ""),
                _json_dumps(_normalize_association_values(param.get("association_value"))),
                int(param.get("sort_order") or 0),
            ),
        )
        parameter_id = cursor.lastrowid
        for option in param.get("options", []):
            cursor.execute(
                """
                INSERT INTO tool_card_parameter_options (parameter_id, option_value, option_label, sort_order)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    parameter_id,
                    option.get("option_value") or option.get("value") or "",
                    option.get("option_label") or option.get("label") or option.get("value") or "",
                    int(option.get("sort_order") or 0),
                ),
            )

    legacy_parameters = _normalize_parameters(parameters)
    legacy_mappings = _parameters_to_legacy_mappings(
        [
            {
                "field_key": param["field_key"],
                "display_name": param["display_name"],
                "field_type": param["field_type"],
                "default_value": param.get("default_value", ""),
                "required": param.get("required", False),
                "association_enabled": param.get("association_enabled", False),
                "association_field": param.get("association_field", ""),
                "association_value": _normalize_association_values(param.get("association_value")),
                "sort_order": param.get("sort_order", 0),
                "options": [
                    {
                        "value": option.get("option_value") or option.get("value") or "",
                        "label": option.get("option_label") or option.get("label") or option.get("value") or "",
                    }
                    for option in param.get("options", [])
                ],
            }
            for param in legacy_parameters
        ]
    )
    legacy_config = _card_configs_to_legacy(card_type, sql_config, http_config, python_config)
    cursor.execute(
        """
        UPDATE tool_card_items
        SET config = %s, mappings = %s
        WHERE id = %s
        """,
        (_json_dumps(legacy_config), _json_dumps(legacy_mappings), card_id),
    )


def create_card(payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_bootstrap()
    card = _normalize_card_payload(payload)
    if not card["folder_id"]:
        raise ValueError("请先选择文件夹")
    if not card["name"]:
        raise ValueError("卡片名称不能为空")

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tool_card_items (folder_id, name, description, card_type, config, mappings, sort_order, enabled, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    card["folder_id"],
                    card["name"],
                    card["description"],
                    card["card_type"],
                    "{}",
                    "{}",
                    card["sort_order"],
                    card["enabled"],
                    "admin",
                ),
            )
            card_id = int(cursor.lastrowid)
            _save_card_relations(cursor, card_id, card["card_type"], card)
        connection.commit()
    return get_card_detail(card_id)


def update_card(card_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_bootstrap()
    existing = fetch_one("SELECT id FROM tool_card_items WHERE id = %s", (card_id,))
    if not existing:
        raise ValueError("卡片不存在")
    card = _normalize_card_payload(payload)
    if not card["name"]:
        raise ValueError("卡片名称不能为空")
    if not card["folder_id"]:
        current = fetch_one("SELECT folder_id FROM tool_card_items WHERE id = %s", (card_id,))
        card["folder_id"] = int(current["folder_id"])

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE tool_card_items
                SET folder_id = %s, name = %s, description = %s, card_type = %s, sort_order = %s, enabled = %s
                WHERE id = %s
                """,
                (
                    card["folder_id"],
                    card["name"],
                    card["description"],
                    card["card_type"],
                    card["sort_order"],
                    card["enabled"],
                    card_id,
                ),
            )
            _save_card_relations(cursor, card_id, card["card_type"], card)
        connection.commit()
    return get_card_detail(card_id)


def delete_card(card_id: int) -> dict[str, Any]:
    _ensure_bootstrap()
    existing = fetch_one("SELECT id FROM tool_card_items WHERE id = %s", (card_id,))
    if not existing:
        raise ValueError("卡片不存在")
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM tool_card_parameter_options WHERE parameter_id IN (SELECT id FROM (SELECT id FROM tool_card_parameters WHERE card_id = %s) AS p)", (card_id,))
            cursor.execute("DELETE FROM tool_card_parameters WHERE card_id = %s", (card_id,))
            cursor.execute("DELETE FROM tool_card_sql_configs WHERE card_id = %s", (card_id,))
            cursor.execute("DELETE FROM tool_card_http_configs WHERE card_id = %s", (card_id,))
            cursor.execute("DELETE FROM tool_card_python_configs WHERE card_id = %s", (card_id,))
            cursor.execute("DELETE FROM tool_card_items WHERE id = %s", (card_id,))
        connection.commit()
    return {"deleted": True, "card_id": card_id}


def copy_card(card_id: int) -> dict[str, Any]:
    card = get_card_detail(card_id)
    copied = {
        "folder_id": card["folder_id"],
        "name": f'{card["name"]}_副本',
        "description": card["description"],
        "card_type": card["card_type"],
        "sort_order": 0,
        "enabled": True,
        "sql_config": card["sql_config"],
        "http_config": card["http_config"],
        "python_config": card["python_config"],
        "parameters": card["parameters"],
    }
    return create_card(copied)


def _replace_template_text(value: str, variables: dict[str, Any]) -> str:
    if not isinstance(value, str):
        return value

    def replace_match(match: re.Match[str]) -> str:
        key = match.group(1)
        replacement = variables.get(key, match.group(0))
        if replacement is None:
            return ""
        if isinstance(replacement, (dict, list)):
            return _json_dumps(replacement)
        return str(replacement)

    return re.sub(r"\$\{([^}]+)\}", replace_match, value)


def _replace_template_data(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return _replace_template_text(value, variables)
    if isinstance(value, dict):
        return {
            _replace_template_text(str(key), variables): _replace_template_data(item, variables)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_replace_template_data(item, variables) for item in value]
    return value


def _resolve_card_variables(card: dict[str, Any], input_variables: dict[str, Any]) -> dict[str, Any]:
    values = {key: value for key, value in (input_variables or {}).items()}
    for parameter in card.get("parameters", []):
        field_key = parameter["field_key"]
        if field_key in values and values[field_key] not in (None, ""):
            continue
        default_value = parameter.get("default_value")
        if default_value not in (None, ""):
            values[field_key] = default_value
    return values


def _convert_sql_template(sql_text: str) -> str:
    sql_text = re.sub(r"'\$\{([^}]+)\}'", r"{\1}", sql_text)
    sql_text = re.sub(r'"\$\{([^}]+)\}"', r"{\1}", sql_text)
    sql_text = re.sub(r"\$\{([^}]+)\}", r"{\1}", sql_text)
    return sql_text


def _render_sql(sql_text: str, variables: dict[str, Any]) -> str:
    sql_text = _convert_sql_template(sql_text)

    def replace_match(match: re.Match[str]) -> str:
        key = match.group(1)
        value = variables.get(key)
        if value is None:
            return match.group(0)
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        return "'" + str(value).replace("'", "''") + "'"

    return re.sub(r"\{(\w+)\}", replace_match, sql_text)


def _execute_sql_card(card: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    sql_config = card["sql_config"]
    query_text = str(sql_config.get("query_text") or "").strip()
    if not query_text:
        raise ValueError("SQL 卡片未配置查询语句")
    rendered_sql = _render_sql(query_text, variables)
    connection_config = {
        "host": sql_config.get("host") or "localhost",
        "port": int(sql_config.get("port") or 3306),
        "user": sql_config.get("username") or "",
        "password": sql_config.get("password") or "",
        "database": sql_config.get("database_name") or "",
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }
    with pymysql.connect(**connection_config) as connection:
        with connection.cursor() as cursor:
            cursor.execute(rendered_sql)
            rows = cursor.fetchall()
    return {
        "mode": "sql",
        "request": {
            "sql": rendered_sql,
            "database": {
                "host": connection_config["host"],
                "port": connection_config["port"],
                "database": connection_config["database"],
                "user": connection_config["user"],
            },
        },
        "result": {
            "row_count": len(rows),
            "rows": rows,
        },
    }


def _execute_http_card(card: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    http_config = card["http_config"]
    url = _replace_template_text(str(http_config.get("url") or "").strip(), variables)
    if not url:
        raise ValueError("HTTP 卡片未配置请求地址")
    headers = _replace_template_data(_json_loads(http_config.get("headers_text"), {}), variables)
    body = _replace_template_data(_json_loads(http_config.get("body_text"), {}), variables)
    method = str(http_config.get("method") or "GET").upper()
    kwargs: dict[str, Any] = {"headers": headers or {}, "timeout": 30}
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        kwargs["json"] = body
    elif body not in ({}, None, ""):
        kwargs["params"] = body
    response = requests.request(method, url, **kwargs)
    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        try:
            response_body: Any = response.json()
        except ValueError:
            response_body = response.text
    else:
        response_body = response.text
    return {
        "mode": "http",
        "request": {
            "url": url,
            "method": method,
            "headers": headers,
            "body": body,
        },
        "result": {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response_body,
        },
    }


def _execute_python_card(card: dict[str, Any], _variables: dict[str, Any]) -> dict[str, Any]:
    python_config = card["python_config"]
    return {
        "mode": "python",
        "request": python_config,
        "result": {
            "supported": False,
            "message": "Python 卡片执行能力暂未迁移，当前仅保留配置展示。",
        },
    }


def execute_card(card_id: int, input_variables: dict[str, Any] | None = None) -> dict[str, Any]:
    card = get_card_detail(card_id)
    variables = _resolve_card_variables(card, input_variables or {})
    card_type = card["card_type"]
    if card_type == "sql":
        execution = _execute_sql_card(card, variables)
    elif card_type == "http":
        execution = _execute_http_card(card, variables)
    else:
        execution = _execute_python_card(card, variables)

    return {
        "card_id": card["id"],
        "card_name": card["name"],
        "card_type": card_type,
        "variables": variables,
        **execution,
    }


def bootstrap_from_legacy_sources(force: bool = False) -> dict[str, Any]:
    payload = _ensure_bootstrap(force=force)
    if payload["selected_folder_id"]:
        payload["cards"] = list_cards_by_folder(int(payload["selected_folder_id"]))
    else:
        payload["cards"] = []
    return payload
