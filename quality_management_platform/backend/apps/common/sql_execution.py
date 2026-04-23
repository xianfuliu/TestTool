from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from apps.common.request_execution import json_dumps, render_sql_template
from test_platform.db import DATABASE_CONFIG, fetch_one


@dataclass
class SqlExecutionContext:
    variables: dict[str, Any] = field(default_factory=dict)
    allow_legacy_placeholders: bool = True
    allowed_statement_prefixes: tuple[str, ...] = ()


@dataclass
class SqlConnectionConfig:
    host: str
    port: int
    user: str
    password: str
    database: str = ""
    charset: str = "utf8mb4"
    connection_id: int | None = None
    connection_name: str = ""

    def pymysql_kwargs(self, *, include_database: bool = True) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "charset": self.charset or "utf8mb4",
            "cursorclass": DictCursor,
            "autocommit": True,
            "connect_timeout": 8,
            "read_timeout": 30,
            "write_timeout": 30,
        }
        if include_database and self.database:
            kwargs["database"] = self.database
        return kwargs


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _serialise_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _serialise_rows(rows: Any) -> list[dict[str, Any]]:
    serialised: list[dict[str, Any]] = []
    for row in rows or []:
        row_map = _as_dict(row)
        serialised.append({str(key): _serialise_value(value) for key, value in row_map.items()})
    return serialised


def _database_connection_id(config: dict[str, Any]) -> int | None:
    raw_id = config.get("database_connection_id") or config.get("database_asset_id") or config.get("connection_id")
    if raw_id in (None, ""):
        return None
    try:
        return int(raw_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("SQL 工具关联的数据库配置无效") from exc


def resolve_sql_connection_config(config: dict[str, Any]) -> SqlConnectionConfig:
    database_config = _as_dict(config.get("database"))
    connection_id = _database_connection_id(config)
    if connection_id:
        row = fetch_one("SELECT * FROM database_connections WHERE id = %s", (connection_id,))
        if not row:
            raise ValueError("SQL 工具关联的数据库配置不存在")
        if not row.get("enabled"):
            raise ValueError("SQL 工具关联的数据库配置已停用")
        if str(row.get("db_type") or "MySQL").strip().lower() != "mysql":
            raise ValueError("SQL 工具当前仅支持 MySQL 数据库")
        selected_database = (
            str(config.get("database") or config.get("database_name") or "").strip()
            if not database_config
            else str(database_config.get("database") or database_config.get("database_name") or "").strip()
        )
        return SqlConnectionConfig(
            host=str(row.get("host") or "").strip(),
            port=_int_value(row.get("port"), 3306),
            user=str(row.get("username") or "").strip(),
            password=str(row.get("password") or ""),
            database=selected_database or str(row.get("database_name") or "").strip(),
            charset=str(row.get("charset") or "utf8mb4").strip() or "utf8mb4",
            connection_id=connection_id,
            connection_name=str(row.get("name") or ""),
        )

    source = database_config or config
    return SqlConnectionConfig(
        host=str(source.get("host") or DATABASE_CONFIG["host"]),
        port=_int_value(source.get("port"), int(DATABASE_CONFIG["port"])),
        user=str(source.get("user") or source.get("username") or DATABASE_CONFIG["user"]),
        password=str(source.get("password") or DATABASE_CONFIG["password"]),
        database=str(source.get("database") or source.get("database_name") or DATABASE_CONFIG["database"]),
        charset=str(source.get("charset") or "utf8mb4") or "utf8mb4",
        connection_name=str(source.get("name") or source.get("database_connection_name") or ""),
    )


def _validate_statement(sql: str, allowed_prefixes: tuple[str, ...]) -> None:
    clean_sql = sql.strip().lstrip("(").strip()
    if not clean_sql:
        raise ValueError("SQL 工具未配置查询语句")
    if not allowed_prefixes:
        return
    allowed = tuple(prefix.upper() for prefix in allowed_prefixes)
    if not clean_sql.upper().startswith(allowed):
        raise ValueError(f"SQL 工具仅支持 {'/'.join(allowed)} 语句")


def _statement_type(sql: str) -> str:
    clean_sql = sql.strip().lstrip("(").strip()
    return clean_sql.split(None, 1)[0].upper() if clean_sql else ""


def execute_sql_query(config: dict[str, Any], context: SqlExecutionContext | None = None) -> dict[str, Any]:
    context = context or SqlExecutionContext()
    sql_text = str(config.get("sql") or config.get("query") or config.get("query_text") or "").strip()
    if not sql_text:
        raise ValueError("SQL 工具未配置查询语句")

    resolved_sql = render_sql_template(
        sql_text,
        context.variables,
        allow_legacy_placeholders=context.allow_legacy_placeholders,
    )
    _validate_statement(resolved_sql, context.allowed_statement_prefixes)

    connection_config = resolve_sql_connection_config(config)
    started_at = time.perf_counter()
    with pymysql.connect(**connection_config.pymysql_kwargs()) as connection:
        with connection.cursor() as cursor:
            affected_rows = cursor.execute(resolved_sql)
            if cursor.description:
                rows = cursor.fetchall()
                row_count = len(rows)
            else:
                rows = []
                row_count = 0
            lastrowid = cursor.lastrowid
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)

    serialised_rows = _serialise_rows(rows)
    body: Any = serialised_rows if rows else {
        "affected_rows": affected_rows,
        "row_count": row_count,
        "lastrowid": lastrowid,
    }
    return {
        "request": {
            "sql": resolved_sql,
            "database": {
                "id": connection_config.connection_id,
                "name": connection_config.connection_name,
                "host": connection_config.host,
                "port": connection_config.port,
                "database": connection_config.database,
                "user": connection_config.user,
            },
        },
        "status": "success",
        "status_code": 200,
        "headers": {},
        "statement_type": _statement_type(resolved_sql),
        "affected_rows": affected_rows,
        "row_count": row_count,
        "lastrowid": lastrowid,
        "rows": serialised_rows,
        "body": body,
        "raw_body": json_dumps(body),
        "decrypted_body": body,
        "duration_ms": duration_ms,
    }


def _normalise_output_fields(value: Any) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for item in _as_list(value):
        if isinstance(item, str):
            field_name = item.strip()
            variable_name = field_name
        else:
            item_map = _as_dict(item)
            field_name = str(item_map.get("field") or item_map.get("name") or item_map.get("source") or "").strip()
            variable_name = str(item_map.get("variable") or item_map.get("output") or item_map.get("name") or field_name).strip()
        if field_name or variable_name:
            fields.append({"field": field_name or variable_name, "variable": variable_name or field_name})
    return fields


def extract_sql_output_variables(
    rows: list[dict[str, Any]],
    output_fields: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    configured_fields = _normalise_output_fields(output_fields)
    if not rows:
        return {}, [
            {
                "variable": item["variable"],
                "path": f"rows[0].{item['field']}",
                "resolved_path": f"rows[0].{item['field']}",
                "matched": False,
                "value": None,
            }
            for item in configured_fields
        ]
    first_row = _as_dict(rows[0])
    if not configured_fields:
        configured_fields = [{"field": key, "variable": key} for key in first_row.keys()]

    extracted: dict[str, Any] = {}
    details: list[dict[str, Any]] = []
    for item in configured_fields:
        field_name = item["field"]
        variable_name = item["variable"]
        matched = field_name in first_row
        value = first_row.get(field_name)
        if matched:
            extracted[variable_name] = value
        details.append(
            {
                "variable": variable_name,
                "path": f"rows[0].{field_name}",
                "resolved_path": f"rows[0].{field_name}",
                "matched": matched,
                "value": _serialise_value(value),
            }
        )
    return extracted, details


def list_database_schemas(database_id: int) -> list[str]:
    connection_config = resolve_sql_connection_config({"database_connection_id": database_id, "database": ""})
    with pymysql.connect(**connection_config.pymysql_kwargs(include_database=False)) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SHOW DATABASES")
            rows = cursor.fetchall()
    schemas: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            value = next(iter(row.values()), "")
        else:
            value = row[0] if row else ""
        schema = str(value or "").strip()
        if schema:
            schemas.append(schema)
    return sorted(schemas)
