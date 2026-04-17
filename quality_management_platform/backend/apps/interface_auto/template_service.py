from __future__ import annotations

import json
from typing import Any

from apps.common.request_execution import (
    EncryptionConfig,
    RequestDefinition,
    RequestExecutionContext,
    execute_request_definition,
    merge_header_maps,
)
from test_platform.db import connect, ensure_database, execute, fetch_all, fetch_one
from test_platform.schema import SCHEMA_SQL


METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}
_SCHEMA_READY = False


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (column_name,))
    return cursor.fetchone() is not None


def ensure_schema_ready() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    ensure_database()
    with connect() as connection:
        with connection.cursor() as cursor:
            for statement in SCHEMA_SQL:
                cursor.execute(statement)
            if not _column_exists(cursor, "api_templates", "debug_config_text"):
                cursor.execute(
                    """
                    ALTER TABLE api_templates
                    ADD COLUMN debug_config_text LONGTEXT NULL AFTER retry_count
                    """
                )
        connection.commit()
    _SCHEMA_READY = True


def parse_json_value(value: Any, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def json_text(value: Any, fallback: Any) -> str:
    if value in (None, ""):
        value = fallback
    return json.dumps(value, ensure_ascii=False)


def normalize_template(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    item = dict(row)
    item["headers"] = parse_json_value(item.get("headers"), {})
    item["params"] = parse_json_value(item.get("params"), {})
    item["body"] = parse_json_value(item.get("body"), {})
    item["retry_enabled"] = bool(item.get("retry_enabled"))
    item["timeout"] = int(item.get("timeout") or 30)
    item["retry_count"] = int(item.get("retry_count") or 3)
    item["debug_config"] = parse_json_value(item.get("debug_config_text"), {})
    return item


def normalize_folder(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["parent_id"] = item.get("parent_id") or None
    return item


def require_project(project_id: Any) -> int:
    try:
        value = int(project_id)
    except (TypeError, ValueError):
        raise ValueError("project_id 不能为空")
    if value <= 0:
        raise ValueError("project_id 不能为空")
    ensure_schema_ready()
    if not fetch_one("SELECT id FROM projects WHERE id = %s", (value,)):
        raise ValueError("项目不存在")
    return value


def list_folders(project_id: Any) -> list[dict[str, Any]]:
    project = require_project(project_id)
    rows = fetch_all(
        """
        SELECT f.*,
               (SELECT COUNT(*) FROM api_templates t WHERE t.folder_id = f.id) AS template_count
        FROM api_folders f
        WHERE f.project_id = %s
        ORDER BY f.sort_order ASC, f.created_at ASC, f.id ASC
        """,
        (project,),
    )
    return [normalize_folder(row) for row in rows]


def create_folder(payload: dict[str, Any]) -> dict[str, Any]:
    project_id = require_project(payload.get("project_id"))
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("目录名称不能为空")
    parent_id = payload.get("parent_id") or None
    if parent_id and not fetch_one("SELECT id FROM api_folders WHERE id = %s AND project_id = %s", (parent_id, project_id)):
        raise ValueError("父目录不存在")
    folder_id = execute(
        """
        INSERT INTO api_folders (project_id, parent_id, name, description, sort_order)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (project_id, parent_id, name, payload.get("description", ""), int(payload.get("sort_order") or 0)),
    )
    return {"folder_id": folder_id, "folder": fetch_one("SELECT * FROM api_folders WHERE id = %s", (folder_id,))}


def update_folder(folder_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_schema_ready()
    current = fetch_one("SELECT * FROM api_folders WHERE id = %s", (folder_id,))
    if not current:
        raise ValueError("目录不存在")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("目录名称不能为空")
    parent_id = payload.get("parent_id", current.get("parent_id")) or None
    if parent_id == folder_id:
        raise ValueError("父目录不能是自己")
    execute(
        "UPDATE api_folders SET name = %s, description = %s, parent_id = %s, sort_order = %s WHERE id = %s",
        (name, payload.get("description", ""), parent_id, int(payload.get("sort_order") or 0), folder_id),
    )
    return {"updated": True, "folder": fetch_one("SELECT * FROM api_folders WHERE id = %s", (folder_id,))}


def delete_folder(folder_id: int) -> dict[str, Any]:
    ensure_schema_ready()
    if not fetch_one("SELECT id FROM api_folders WHERE id = %s", (folder_id,)):
        raise ValueError("目录不存在")
    with connect() as connection:
        with connection.cursor() as cursor:
            pending = [folder_id]
            folder_ids: list[int] = []
            while pending:
                current = pending.pop()
                folder_ids.append(current)
                cursor.execute("SELECT id FROM api_folders WHERE parent_id = %s", (current,))
                pending.extend(row["id"] for row in cursor.fetchall())
            placeholders = ",".join(["%s"] * len(folder_ids))
            cursor.execute(f"DELETE FROM api_templates WHERE folder_id IN ({placeholders})", folder_ids)
            cursor.execute(f"DELETE FROM api_folders WHERE id IN ({placeholders})", folder_ids)
        connection.commit()
    return {"deleted": True, "folder_ids": folder_ids}


def list_templates(project_id: Any = None, folder_id: Any = None) -> list[dict[str, Any]]:
    ensure_schema_ready()
    if folder_id not in (None, ""):
        rows = fetch_all(
            "SELECT * FROM api_templates WHERE folder_id = %s ORDER BY sort_order ASC, created_at DESC, id DESC",
            (int(folder_id),),
        )
        return [normalize_template(row) for row in rows if row]
    project = require_project(project_id)
    rows = fetch_all(
        "SELECT * FROM api_templates WHERE project_id = %s ORDER BY sort_order ASC, created_at DESC, id DESC",
        (project,),
    )
    return [normalize_template(row) for row in rows if row]


def _normalize_debug_config(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else parse_json_value(value, {})
    encryption = raw.get("encryption") if isinstance(raw, dict) else {}
    header_config = raw.get("header_config") if isinstance(raw, dict) else {}
    return {
        "encryption": {
            "enabled": bool((encryption or {}).get("enabled")),
            "encrypt_url": str((encryption or {}).get("encrypt_url") or ""),
            "decrypt_url": str((encryption or {}).get("decrypt_url") or ""),
        },
        "header_config": {
            "enabled": bool((header_config or {}).get("enabled")),
            "headers": (header_config or {}).get("headers") if isinstance((header_config or {}).get("headers"), dict) else {},
        },
    }


def validate_template(payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    project_id = require_project(payload.get("project_id") or (existing or {}).get("project_id"))
    folder_id = payload.get("folder_id", (existing or {}).get("folder_id")) or None
    if folder_id and not fetch_one("SELECT id FROM api_folders WHERE id = %s AND project_id = %s", (folder_id, project_id)):
        raise ValueError("目录不存在")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("接口名称不能为空")
    method = str(payload.get("method") or "GET").upper()
    if method not in METHODS:
        raise ValueError("请求方法不支持")
    url_path = str(payload.get("url_path") or "").strip()
    if not url_path:
        raise ValueError("URL路径不能为空")
    template_id = payload.get("id") or (existing or {}).get("id")
    duplicate_sql = """
        SELECT id FROM api_templates
        WHERE project_id = %s AND name = %s AND
              ((folder_id IS NULL AND %s IS NULL) OR folder_id = %s)
    """
    duplicate_params: tuple[Any, ...] = (project_id, name, folder_id, folder_id)
    duplicate = fetch_one(duplicate_sql, duplicate_params)
    if duplicate and int(duplicate["id"]) != int(template_id or 0):
        raise ValueError("同一目录下已存在同名接口模板")
    return {
        "project_id": project_id,
        "folder_id": folder_id,
        "name": name,
        "method": method,
        "url_path": url_path,
        "headers": payload.get("headers") or {},
        "params": payload.get("params") or {},
        "body": payload.get("body") if payload.get("body") not in (None, "") else {},
        "description": payload.get("description", ""),
        "sort_order": int(payload.get("sort_order") or 0),
        "timeout": max(1, int(payload.get("timeout") or 30)),
        "retry_enabled": bool(payload.get("retry_enabled", False)),
        "retry_count": max(0, int(payload.get("retry_count") or 0)),
        "debug_config": _normalize_debug_config(payload.get("debug_config", (existing or {}).get("debug_config"))),
    }


def create_template(payload: dict[str, Any]) -> dict[str, Any]:
    item = validate_template(payload)
    template_id = execute(
        """
        INSERT INTO api_templates
        (project_id, folder_id, name, method, url_path, headers, params, body, description, sort_order, timeout, retry_enabled, retry_count, debug_config_text)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            item["project_id"],
            item["folder_id"],
            item["name"],
            item["method"],
            item["url_path"],
            json_text(item["headers"], {}),
            json_text(item["params"], {}),
            json_text(item["body"], {}),
            item["description"],
            item["sort_order"],
            item["timeout"],
            item["retry_enabled"],
            item["retry_count"],
            json_text(item["debug_config"], {}),
        ),
    )
    return {"template_id": template_id, "template": get_template(template_id)}


def get_template(template_id: int) -> dict[str, Any] | None:
    ensure_schema_ready()
    return normalize_template(fetch_one("SELECT * FROM api_templates WHERE id = %s", (template_id,)))


def update_template(template_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    current = get_template(template_id)
    if not current:
        raise ValueError("接口模板不存在")
    item = validate_template({**current, **payload}, current)
    execute(
        """
        UPDATE api_templates
        SET project_id = %s, folder_id = %s, name = %s, method = %s, url_path = %s,
            headers = %s, params = %s, body = %s, description = %s, sort_order = %s,
            timeout = %s, retry_enabled = %s, retry_count = %s, debug_config_text = %s
        WHERE id = %s
        """,
        (
            item["project_id"],
            item["folder_id"],
            item["name"],
            item["method"],
            item["url_path"],
            json_text(item["headers"], {}),
            json_text(item["params"], {}),
            json_text(item["body"], {}),
            item["description"],
            item["sort_order"],
            item["timeout"],
            item["retry_enabled"],
            item["retry_count"],
            json_text(item["debug_config"], {}),
            template_id,
        ),
    )
    return {"updated": True, "template": get_template(template_id)}


def delete_template(template_id: int) -> dict[str, Any]:
    ensure_schema_ready()
    deleted = execute("DELETE FROM api_templates WHERE id = %s", (template_id,))
    return {"deleted": deleted > 0}


def template_workspace(project_id: Any) -> dict[str, Any]:
    project = require_project(project_id)
    return {
        "folders": list_folders(project),
        "templates": list_templates(project_id=project),
    }


def execute_template_debug(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_schema_ready()
    method = str(payload.get("method") or "GET").upper()
    if method not in METHODS:
        raise ValueError("请求方法不支持")
    url_path = str(payload.get("url_path") or "").strip()
    if not url_path:
        raise ValueError("URL路径不能为空")
    timeout = max(1, int(payload.get("timeout") or 30))
    retry_enabled = bool(payload.get("retry_enabled", False))
    retry_count = max(0, int(payload.get("retry_count") or 0))
    headers = payload.get("headers") or {}
    params = payload.get("params") or {}
    body = payload.get("body") if payload.get("body") not in (None, "") else {}
    debug_config = _normalize_debug_config(payload.get("debug_config"))

    encryption_config = debug_config["encryption"]
    header_config = debug_config["header_config"]
    encryption = EncryptionConfig(
        enabled=bool(encryption_config.get("enabled")),
        encrypt_url=str(encryption_config.get("encrypt_url") or ""),
        decrypt_url=str(encryption_config.get("decrypt_url") or ""),
    )
    global_headers = merge_header_maps(header_config.get("headers")) if header_config.get("enabled") else {}

    result = execute_request_definition(
        RequestDefinition(
            protocol=str(payload.get("protocol") or "http"),
            url=url_path,
            method=method,
            headers=headers,
            params=params,
            body=body,
            timeout=timeout,
            retry_enabled=retry_enabled,
            retry_count=retry_count,
        ),
        RequestExecutionContext(
            request_id=str(payload.get("request_id") or ""),
            variables={},
            base_url="",
            global_headers=global_headers,
            encryption=encryption,
            allow_legacy_placeholders=True,
        ),
    )
    return {
        "request": result.request,
        "status_code": result.status_code,
        "headers": result.headers,
        "body": result.body,
        "raw_body": result.raw_body,
        "decrypted_body": result.decrypted_body,
        "duration_ms": result.duration_ms,
        "debug_config_applied": {
            "encryption": encryption_config,
            "header_config": {
                "enabled": bool(header_config.get("enabled")),
                "headers": global_headers,
            },
        },
    }
