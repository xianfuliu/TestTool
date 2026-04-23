from __future__ import annotations

import time
from typing import Any

import pymysql

from apps.common.http import api_view, get_int
from apps.common.sql_execution import list_database_schemas
from test_platform.db import execute, fetch_all, fetch_one


def _ensure_schema_ready() -> None:
    execute(
        """
        CREATE TABLE IF NOT EXISTS database_connections (
            id INT AUTO_INCREMENT PRIMARY KEY,
            business_group_id INT NOT NULL,
            name VARCHAR(120) NOT NULL,
            db_type VARCHAR(30) DEFAULT 'MySQL',
            host VARCHAR(255) DEFAULT '',
            port INT DEFAULT 3306,
            database_name VARCHAR(255) DEFAULT '',
            username VARCHAR(255) DEFAULT '',
            password VARCHAR(255) DEFAULT '',
            charset VARCHAR(50) DEFAULT 'utf8mb4',
            description TEXT,
            enabled BOOLEAN DEFAULT TRUE,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_database_connection_group_name (business_group_id, name),
            INDEX idx_database_connection_group_id (business_group_id),
            INDEX idx_database_connection_enabled (enabled)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )


def _bool_value(value: Any, default: bool = True) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _normalise_payload(payload: dict[str, Any]) -> dict[str, Any]:
    business_group_id = get_int(payload.get("business_group_id"))
    name = str(payload.get("name") or "").strip()
    if not business_group_id:
        raise ValueError("请选择所属业务")
    if not fetch_one("SELECT id FROM business_groups WHERE id = %s", (business_group_id,)):
        raise ValueError("所属业务不存在")
    if not name:
        raise ValueError("数据库名称不能为空")

    port = get_int(payload.get("port"), 3306) or 3306
    if port <= 0 or port > 65535:
        raise ValueError("端口范围应为 1-65535")

    return {
        "business_group_id": business_group_id,
        "name": name,
        "db_type": str(payload.get("db_type") or "MySQL").strip() or "MySQL",
        "host": str(payload.get("host") or "").strip(),
        "port": port,
        "database_name": str(payload.get("database_name") or "").strip(),
        "username": str(payload.get("username") or "").strip(),
        "password": str(payload.get("password") or ""),
        "charset": str(payload.get("charset") or "utf8mb4").strip() or "utf8mb4",
        "description": str(payload.get("description") or "").strip(),
        "enabled": _bool_value(payload.get("enabled"), True),
    }


def _database_query_base() -> str:
    return """
        SELECT dc.*, bg.name AS business_group_name
        FROM database_connections dc
        LEFT JOIN business_groups bg ON dc.business_group_id = bg.id
    """


def _normalise_connection_payload(payload: dict[str, Any]) -> dict[str, Any]:
    port = get_int(payload.get("port"), 3306) or 3306
    if port <= 0 or port > 65535:
        raise ValueError("端口范围应为 1-65535")
    return {
        "db_type": str(payload.get("db_type") or "MySQL").strip() or "MySQL",
        "host": str(payload.get("host") or "").strip(),
        "port": port,
        "username": str(payload.get("username") or "").strip(),
        "password": str(payload.get("password") or ""),
        "charset": str(payload.get("charset") or "utf8mb4").strip() or "utf8mb4",
    }


@api_view
def test_database_connection(_request, payload=None):
    item = _normalise_connection_payload(payload or {})
    if item["db_type"].lower() != "mysql":
        return {
            "connected": False,
            "message": "当前仅支持 MySQL 连接测试",
        }
    if not item["host"]:
        raise ValueError("请输入主机地址")

    started_at = time.perf_counter()
    try:
        with pymysql.connect(
            host=item["host"],
            port=item["port"],
            user=item["username"],
            password=item["password"],
            charset=item["charset"],
            connect_timeout=5,
            read_timeout=5,
            write_timeout=5,
            autocommit=True,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return {
            "connected": False,
            "message": str(exc),
            "duration_ms": duration_ms,
        }

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    return {
        "connected": True,
        "message": "连接成功",
        "duration_ms": duration_ms,
    }


@api_view
def databases(request, payload=None):
    _ensure_schema_ready()
    if request.method == "GET":
        keyword = str((payload or {}).get("keyword") or "").strip()
        business_group_id = get_int((payload or {}).get("business_group_id"))
        conditions: list[str] = []
        params: list[Any] = []
        if business_group_id:
            conditions.append("dc.business_group_id = %s")
            params.append(business_group_id)
        if keyword:
            conditions.append(
                "(dc.name LIKE %s OR dc.host LIKE %s OR dc.username LIKE %s)"
            )
            like_value = f"%{keyword}%"
            params.extend([like_value, like_value, like_value])

        where_sql = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        return fetch_all(
            f"""
            {_database_query_base()}
            {where_sql}
            ORDER BY dc.updated_at DESC, dc.id DESC
            """,
            params,
        )

    item = _normalise_payload(payload or {})
    existed = fetch_one(
        "SELECT id FROM database_connections WHERE business_group_id = %s AND name = %s",
        (item["business_group_id"], item["name"]),
    )
    if existed:
        raise ValueError("当前业务下已存在同名数据库")

    database_id = execute(
        """
        INSERT INTO database_connections
            (business_group_id, name, db_type, host, port, database_name, username, password, charset, description, enabled, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            item["business_group_id"],
            item["name"],
            item["db_type"],
            item["host"],
            item["port"],
            item["database_name"],
            item["username"],
            item["password"],
            item["charset"],
            item["description"],
            item["enabled"],
            "admin",
        ),
    )
    return {"database_id": database_id}, 201


@api_view
def database_detail(request, database_id: int, payload=None):
    _ensure_schema_ready()
    if request.method == "GET":
        row = fetch_one(f"{_database_query_base()} WHERE dc.id = %s", (database_id,))
        if not row:
            raise ValueError("数据库配置不存在")
        return row

    if request.method == "PUT":
        item = _normalise_payload(payload or {})
        existed = fetch_one(
            """
            SELECT id FROM database_connections
            WHERE business_group_id = %s AND name = %s AND id <> %s
            """,
            (item["business_group_id"], item["name"], database_id),
        )
        if existed:
            raise ValueError("当前业务下已存在同名数据库")

        updated = execute(
            """
            UPDATE database_connections
            SET business_group_id = %s,
                name = %s,
                db_type = %s,
                host = %s,
                port = %s,
                database_name = %s,
                username = %s,
                password = %s,
                charset = %s,
                description = %s,
                enabled = %s
            WHERE id = %s
            """,
            (
                item["business_group_id"],
                item["name"],
                item["db_type"],
                item["host"],
                item["port"],
                item["database_name"],
                item["username"],
                item["password"],
                item["charset"],
                item["description"],
                item["enabled"],
                database_id,
            ),
        )
        return {"updated": updated >= 0}

    return {"deleted": execute("DELETE FROM database_connections WHERE id = %s", (database_id,)) > 0}


@api_view
def database_schemas(_request, database_id: int, payload=None):
    _ensure_schema_ready()
    return {"schemas": list_database_schemas(database_id)}
