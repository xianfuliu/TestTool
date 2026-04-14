from __future__ import annotations

import json
import os
import random
import re
import string
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import pymysql
import requests
from pymysql.cursors import DictCursor

from apps.common.request_execution import (
    EncryptionConfig,
    RequestDefinition,
    RequestExecutionContext,
    default_global_request_config,
    execute_request_definition,
    extract_template_dependencies,
    extract_response_value,
    normalize_global_request_config,
    prepare_request_definition,
    render_sql_template,
    replace_template_data,
    replace_template_text,
    resolve_global_request_runtime,
)
from test_platform.db import connect, ensure_database, fetch_all, fetch_one
from test_platform.schema import SCHEMA_SQL


REPO_ROOT = Path(__file__).resolve().parents[4]
_SCHEMA_READY = False
_PRODUCTS_BOOTSTRAPPED = False
LEGACY_PRODUCTS_INDEX_CANDIDATES = [
    REPO_ROOT
    / "quality_management_platform"
    / "backend"
    / "config"
    / "products_config.json",
]

SCHEDULER_BASE_URL = os.getenv(
    "API_TOOL_SCHEDULER_BASE_URL",
    "https://xj-api-test.hqrzdb.com/stage-api",
).rstrip("/")
SCHEDULER_USERNAME = os.getenv("API_TOOL_SCHEDULER_USERNAME", "admin")
SCHEDULER_PASSWORD = os.getenv("API_TOOL_SCHEDULER_PASSWORD", "admin123")


def _json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _json_loads(value: Any, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _normalise_product_global_request_config(config: dict[str, Any]) -> dict[str, Any]:
    return normalize_global_request_config(
        config.get("global_request_config"),
        legacy_headers=_as_dict(config.get("global_headers")),
    )


def generate_request_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S") + "".join(
        random.choices(string.digits, k=4)
    )


def default_product_config() -> dict[str, Any]:
    return {
        "enable_encryption": False,
        "encrypt_url": "",
        "decrypt_url": "",
        "global_request_config": default_global_request_config(),
        "global_headers": {},
        "schedule_tasks": [],
        "layout": [
            {
                "type": "field",
                "key": "name",
                "label": "姓名",
                "priority": 1,
                "default": "",
            },
            {
                "type": "field",
                "key": "id_card",
                "label": "身份证号",
                "priority": 2,
                "default": "",
            },
            {
                "type": "field",
                "key": "phone",
                "label": "手机号",
                "priority": 3,
                "default": "",
            },
            {
                "type": "interface",
                "name": "默认接口",
                "priority": 4,
            },
        ],
        "interfaces": {
            "默认接口": {
                "url": "",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body_template": {"requestId": "${request_id}"},
                "response_mapping": {},
                "field_types": {},
                "enable_encryption": True,
            }
        },
        "sqls": {},
    }


def _find_legacy_products_index() -> Path | None:
    for candidate in LEGACY_PRODUCTS_INDEX_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def _ensure_schema_ready() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    ensure_database()
    with connect() as connection:
        with connection.cursor() as cursor:
            for sql in SCHEMA_SQL:
                cursor.execute(sql)
            _ensure_api_tool_schema_extensions(cursor)
        connection.commit()
    _SCHEMA_READY = True


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (column_name,))
    return cursor.fetchone() is not None


def _ensure_api_tool_schema_extensions(cursor) -> None:
    if not _column_exists(cursor, "api_tool_products", "global_headers_text"):
        cursor.execute(
            """
            ALTER TABLE api_tool_products
            ADD COLUMN global_headers_text LONGTEXT NULL AFTER decrypt_url
            """
        )
    if not _column_exists(cursor, "api_tool_products", "global_request_config_text"):
        cursor.execute(
            """
            ALTER TABLE api_tool_products
            ADD COLUMN global_request_config_text LONGTEXT NULL AFTER global_headers_text
            """
        )


def _resolve_legacy_relative_path(index_path: Path, relative_path: str) -> Path:
    candidates = [
        index_path.parent / relative_path,
        REPO_ROOT / relative_path,
        index_path.parents[2] / relative_path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _load_legacy_bundle() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    index_path = _find_legacy_products_index()
    if not index_path:
        raise ValueError("未找到接口工具历史 products_config.json，无法初始化 MySQL 配置")

    index_config = json.loads(index_path.read_text(encoding="utf-8"))
    products: list[dict[str, Any]] = []
    locked_products = set(index_config.get("locked_products", []))
    default_product = index_config.get("default_product")

    for sort_order, (product_name, relative_path) in enumerate(
        index_config.get("products", {}).items(),
        start=1,
    ):
        product_path = _resolve_legacy_relative_path(index_path, relative_path)
        if not product_path.exists():
            raise ValueError(f"未找到产品配置文件: {product_path}")
        product_config = json.loads(product_path.read_text(encoding="utf-8"))
        products.append(
            {
                "name": product_name,
                "legacy_config_path": relative_path,
                "sort_order": sort_order,
                "is_locked": product_name in locked_products,
                "is_default": product_name == default_product,
                "config": product_config,
            }
        )

    return index_config, products


def _insert_product_children(cursor, product_id: int, config: dict[str, Any]) -> None:
    schedule_tasks = _as_list(config.get("schedule_tasks"))
    for sort_order, task in enumerate(schedule_tasks, start=1):
        task = _as_dict(task)
        cursor.execute(
            """
            INSERT INTO api_tool_schedule_tasks
            (product_id, legacy_task_id, job_group, name, sort_order)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                product_id,
                str(task.get("id", "")),
                str(task.get("jobGroup", "")),
                str(task.get("name", "")),
                sort_order,
            ),
        )

    layout_items = _as_list(config.get("layout"))
    for sort_order, item in enumerate(layout_items, start=1):
        item = _as_dict(item)
        item_type = str(item.get("type") or "").strip()
        cursor.execute(
            """
            INSERT INTO api_tool_layout_items
            (product_id, item_type, item_key, label, item_name, data_type, default_value, show_in_ui, condition_field, formula, formula_type, priority, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                product_id,
                item_type,
                str(item.get("key", "")),
                str(item.get("label", "")),
                str(item.get("name", "")),
                str(item.get("data_type", "")),
                item.get("default", ""),
                bool(item.get("show_in_ui", True)),
                str(item.get("condition_field", "")),
                item.get("formula", ""),
                str(item.get("formula_type", "")),
                int(item.get("priority", sort_order)),
                sort_order,
            ),
        )
        layout_item_id = cursor.lastrowid

        for option_order, option in enumerate(_as_list(item.get("options")), start=1):
            option = _as_dict(option)
            cursor.execute(
                """
                INSERT INTO api_tool_layout_item_options
                (layout_item_id, option_text, option_value, sort_order)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    layout_item_id,
                    str(option.get("text", "")),
                    str(option.get("value", "")),
                    option_order,
                ),
            )

        for mapping_order, (mapping_key, mapping_value) in enumerate(
            _as_dict(item.get("mappings")).items(),
            start=1,
        ):
            cursor.execute(
                """
                INSERT INTO api_tool_layout_item_mappings
                (layout_item_id, mapping_key, mapping_value, sort_order)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    layout_item_id,
                    str(mapping_key),
                    str(mapping_value),
                    mapping_order,
                ),
            )

    interfaces = _as_dict(config.get("interfaces"))
    for sort_order, (interface_name, interface_config) in enumerate(
        interfaces.items(),
        start=1,
    ):
        interface_config = _as_dict(interface_config)
        conditional_body = _as_dict(interface_config.get("conditional_body"))
        request_type = "conditional" if conditional_body else "normal"
        cursor.execute(
            """
            INSERT INTO api_tool_interfaces
            (product_id, name, url, method, headers_text, request_type, body_template_text, condition_field, enable_encryption, timeout, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                product_id,
                interface_name,
                str(interface_config.get("url", "")),
                str(interface_config.get("method", "POST")).upper(),
                _json_dumps(_as_dict(interface_config.get("headers"))),
                request_type,
                _json_dumps(interface_config.get("body_template", {}))
                if request_type == "normal"
                else "",
                str(conditional_body.get("field", "")),
                bool(interface_config.get("enable_encryption", True)),
                int(interface_config.get("timeout", 30) or 30),
                sort_order,
            ),
        )
        interface_id = cursor.lastrowid

        for mapping_order, (field_key, response_path) in enumerate(
            _as_dict(interface_config.get("response_mapping")).items(),
            start=1,
        ):
            cursor.execute(
                """
                INSERT INTO api_tool_interface_response_mappings
                (interface_id, field_key, response_path, sort_order)
                VALUES (%s, %s, %s, %s)
                """,
                (interface_id, str(field_key), str(response_path), mapping_order),
            )

        for field_order, (field_key, field_type) in enumerate(
            _as_dict(interface_config.get("field_types")).items(),
            start=1,
        ):
            cursor.execute(
                """
                INSERT INTO api_tool_interface_field_types
                (interface_id, field_key, field_type, sort_order)
                VALUES (%s, %s, %s, %s)
                """,
                (interface_id, str(field_key), str(field_type), field_order),
            )

        if request_type == "conditional":
            for case_order, (case_value, case_body) in enumerate(
                _as_dict(conditional_body.get("cases")).items(),
                start=1,
            ):
                cursor.execute(
                    """
                    INSERT INTO api_tool_interface_condition_cases
                    (interface_id, case_value, body_template_text, sort_order)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        interface_id,
                        str(case_value),
                        _json_dumps(case_body),
                        case_order,
                    ),
                )

    sqls = _as_dict(config.get("sqls"))
    for sort_order, (sql_name, sql_config) in enumerate(sqls.items(), start=1):
        sql_config = _as_dict(sql_config)
        database = _as_dict(sql_config.get("database"))
        cursor.execute(
            """
            INSERT INTO api_tool_sql_configs
            (product_id, name, host, port, username, password, database_name, charset, sql_text, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                product_id,
                sql_name,
                str(database.get("host", "")),
                int(database.get("port", 3306) or 3306),
                str(database.get("user", "")),
                str(database.get("password", "")),
                str(database.get("database", "")),
                str(database.get("charset", "utf8mb4") or "utf8mb4"),
                str(sql_config.get("sql", "")),
                sort_order,
            ),
        )
        sql_config_id = cursor.lastrowid

        for field_order, output_field in enumerate(
            _as_list(sql_config.get("output_fields")),
            start=1,
        ):
            output_field = _as_dict(output_field)
            cursor.execute(
                """
                INSERT INTO api_tool_sql_output_fields
                (sql_config_id, field_name, description, sort_order)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    sql_config_id,
                    str(output_field.get("field", "")),
                    str(output_field.get("description", "")),
                    field_order,
                ),
            )


def _replace_all_products(products: list[dict[str, Any]]) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM api_tool_schedule_tasks")
            cursor.execute("DELETE FROM api_tool_layout_item_options")
            cursor.execute("DELETE FROM api_tool_layout_item_mappings")
            cursor.execute("DELETE FROM api_tool_layout_items")
            cursor.execute("DELETE FROM api_tool_interface_condition_cases")
            cursor.execute("DELETE FROM api_tool_interface_response_mappings")
            cursor.execute("DELETE FROM api_tool_interface_field_types")
            cursor.execute("DELETE FROM api_tool_interfaces")
            cursor.execute("DELETE FROM api_tool_sql_output_fields")
            cursor.execute("DELETE FROM api_tool_sql_configs")
            cursor.execute("DELETE FROM api_tool_products")

            for product in products:
                global_request_config = _normalise_product_global_request_config(product["config"])
                cursor.execute(
                    """
                    INSERT INTO api_tool_products
                    (name, legacy_config_path, enable_encryption, encrypt_url, decrypt_url, global_headers_text, global_request_config_text, is_locked, is_default, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        product["name"],
                        product.get("legacy_config_path", ""),
                        bool(product["config"].get("enable_encryption", False)),
                        product["config"].get("encrypt_url", ""),
                        product["config"].get("decrypt_url", ""),
                        _json_dumps(_as_dict(global_request_config.get("header_config", {}).get("headers"))),
                        _json_dumps(global_request_config),
                        bool(product.get("is_locked", False)),
                        bool(product.get("is_default", False)),
                        product.get("sort_order", 0),
                    ),
                )
                product_id = cursor.lastrowid
                _insert_product_children(cursor, product_id, product["config"])

            connection.commit()

    default_name = next(
        (product["name"] for product in products if product.get("is_default")),
        None,
    )
    return {
        "imported": True,
        "product_count": len(products),
        "default_product": default_name,
    }


def bootstrap_from_legacy_json(force: bool = False) -> dict[str, Any]:
    global _PRODUCTS_BOOTSTRAPPED
    _ensure_schema_ready()
    if _PRODUCTS_BOOTSTRAPPED and not force:
        return {"imported": False, "product_count": None}

    current = fetch_one("SELECT COUNT(*) AS count FROM api_tool_products")
    if current and current["count"] > 0 and not force:
        _PRODUCTS_BOOTSTRAPPED = True
        return {"imported": False, "product_count": current["count"]}

    _, products = _load_legacy_bundle()
    result = _replace_all_products(products)
    _PRODUCTS_BOOTSTRAPPED = True
    return result


def _product_meta(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "legacy_config_path": row.get("legacy_config_path") or "",
        "enable_encryption": bool(row.get("enable_encryption")),
        "encrypt_url": row.get("encrypt_url") or "",
        "decrypt_url": row.get("decrypt_url") or "",
        "locked": bool(row.get("is_locked")),
        "is_default": bool(row.get("is_default")),
        "sort_order": row.get("sort_order", 0),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def list_products() -> dict[str, Any]:
    bootstrap_from_legacy_json(force=False)
    rows = fetch_all(
        """
        SELECT id, name, legacy_config_path, enable_encryption, encrypt_url, decrypt_url, global_headers_text, global_request_config_text, is_locked, is_default, sort_order, created_at, updated_at
        FROM api_tool_products
        ORDER BY is_default DESC, sort_order ASC, id ASC
        """
    )
    default_row = next((row for row in rows if row.get("is_default")), None)
    return {
        "default_product_id": default_row["id"] if default_row else None,
        "default_product": default_row["name"] if default_row else None,
        "products": [_product_meta(row) for row in rows],
    }


def _get_product_row(product_id: int) -> dict[str, Any]:
    row = fetch_one(
        """
        SELECT id, name, legacy_config_path, enable_encryption, encrypt_url, decrypt_url, global_headers_text, global_request_config_text, is_locked, is_default, sort_order, created_at, updated_at
        FROM api_tool_products
        WHERE id = %s
        """,
        (product_id,),
    )
    if not row:
        raise ValueError("接口工具产品不存在")
    return row


def _build_product_config(product_id: int, product_row: dict[str, Any]) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, legacy_task_id, job_group, name, sort_order
                FROM api_tool_schedule_tasks
                WHERE product_id = %s
                ORDER BY sort_order ASC, id ASC
                """,
                (product_id,),
            )
            schedule_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT *
                FROM api_tool_layout_items
                WHERE product_id = %s
                ORDER BY priority ASC, sort_order ASC, id ASC
                """,
                (product_id,),
            )
            layout_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT o.layout_item_id, o.option_text, o.option_value, o.sort_order
                FROM api_tool_layout_item_options o
                INNER JOIN api_tool_layout_items i ON i.id = o.layout_item_id
                WHERE i.product_id = %s
                ORDER BY o.sort_order ASC, o.id ASC
                """,
                (product_id,),
            )
            option_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT m.layout_item_id, m.mapping_key, m.mapping_value, m.sort_order
                FROM api_tool_layout_item_mappings m
                INNER JOIN api_tool_layout_items i ON i.id = m.layout_item_id
                WHERE i.product_id = %s
                ORDER BY m.sort_order ASC, m.id ASC
                """,
                (product_id,),
            )
            mapping_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT *
                FROM api_tool_interfaces
                WHERE product_id = %s
                ORDER BY sort_order ASC, id ASC
                """,
                (product_id,),
            )
            interface_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT c.interface_id, c.case_value, c.body_template_text, c.sort_order
                FROM api_tool_interface_condition_cases c
                INNER JOIN api_tool_interfaces i ON i.id = c.interface_id
                WHERE i.product_id = %s
                ORDER BY c.sort_order ASC, c.id ASC
                """,
                (product_id,),
            )
            case_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT r.interface_id, r.field_key, r.response_path, r.sort_order
                FROM api_tool_interface_response_mappings r
                INNER JOIN api_tool_interfaces i ON i.id = r.interface_id
                WHERE i.product_id = %s
                ORDER BY r.sort_order ASC, r.id ASC
                """,
                (product_id,),
            )
            response_mapping_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT f.interface_id, f.field_key, f.field_type, f.sort_order
                FROM api_tool_interface_field_types f
                INNER JOIN api_tool_interfaces i ON i.id = f.interface_id
                WHERE i.product_id = %s
                ORDER BY f.sort_order ASC, f.id ASC
                """,
                (product_id,),
            )
            field_type_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT *
                FROM api_tool_sql_configs
                WHERE product_id = %s
                ORDER BY sort_order ASC, id ASC
                """,
                (product_id,),
            )
            sql_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT o.sql_config_id, o.field_name, o.description, o.sort_order
                FROM api_tool_sql_output_fields o
                INNER JOIN api_tool_sql_configs s ON s.id = o.sql_config_id
                WHERE s.product_id = %s
                ORDER BY o.sort_order ASC, o.id ASC
                """,
                (product_id,),
            )
            sql_output_rows = cursor.fetchall()

    options_by_layout: dict[int, list[dict[str, Any]]] = {}
    for row in option_rows:
        options_by_layout.setdefault(row["layout_item_id"], []).append(
            {
                "text": row["option_text"],
                "value": row["option_value"],
            }
        )

    mappings_by_layout: dict[int, dict[str, str]] = {}
    for row in mapping_rows:
        mappings_by_layout.setdefault(row["layout_item_id"], {})[row["mapping_key"]] = (
            row["mapping_value"]
        )

    layout: list[dict[str, Any]] = []
    for row in layout_rows:
        item = {
            "type": row["item_type"],
            "priority": row["priority"],
        }
        item_type = row["item_type"]
        if item_type in {"field", "combo", "condition", "formula"}:
            item["key"] = row["item_key"]
            item["label"] = row.get("label") or ""
        if item_type in {"field", "combo"}:
            item["default"] = row.get("default_value") or ""
        if item_type in {"field", "combo"} and row.get("data_type"):
            item["data_type"] = row["data_type"]
        if item_type in {"field", "combo", "condition", "formula"}:
            item["show_in_ui"] = bool(row.get("show_in_ui"))
        if item_type == "combo":
            item["options"] = options_by_layout.get(row["id"], [])
        if item_type in {"interface", "sql"}:
            item["name"] = row.get("item_name") or ""
        if item_type == "condition":
            item["condition_field"] = row.get("condition_field") or ""
            item["mappings"] = mappings_by_layout.get(row["id"], {})
        if item_type == "formula":
            item["formula"] = row.get("formula") or ""
            item["formula_type"] = row.get("formula_type") or "numeric"
        layout.append(item)

    cases_by_interface: dict[int, dict[str, Any]] = {}
    for row in case_rows:
        cases_by_interface.setdefault(row["interface_id"], {})[row["case_value"]] = _json_loads(
            row["body_template_text"],
            {},
        )

    response_mappings_by_interface: dict[int, dict[str, str]] = {}
    for row in response_mapping_rows:
        response_mappings_by_interface.setdefault(row["interface_id"], {})[
            row["field_key"]
        ] = row["response_path"]

    field_types_by_interface: dict[int, dict[str, str]] = {}
    for row in field_type_rows:
        field_types_by_interface.setdefault(row["interface_id"], {})[row["field_key"]] = (
            row["field_type"]
        )

    interfaces: dict[str, dict[str, Any]] = {}
    for row in interface_rows:
        interface_config: dict[str, Any] = {
            "url": row.get("url") or "",
            "method": row.get("method") or "POST",
            "headers": _json_loads(row.get("headers_text"), {}),
            "response_mapping": response_mappings_by_interface.get(row["id"], {}),
            "field_types": field_types_by_interface.get(row["id"], {}),
            "enable_encryption": bool(row.get("enable_encryption", True)),
        }
        if row.get("request_type") == "conditional":
            interface_config["conditional_body"] = {
                "field": row.get("condition_field") or "",
                "cases": cases_by_interface.get(row["id"], {}),
            }
        else:
            interface_config["body_template"] = _json_loads(
                row.get("body_template_text"),
                {},
            )
        interfaces[row["name"]] = interface_config

    sql_outputs_by_config: dict[int, list[dict[str, Any]]] = {}
    for row in sql_output_rows:
        sql_outputs_by_config.setdefault(row["sql_config_id"], []).append(
            {
                "field": row["field_name"],
                "description": row.get("description") or "",
            }
        )

    sqls: dict[str, dict[str, Any]] = {}
    for row in sql_rows:
        sqls[row["name"]] = {
            "database": {
                "host": row.get("host") or "",
                "port": row.get("port") or 3306,
                "user": row.get("username") or "",
                "password": row.get("password") or "",
                "database": row.get("database_name") or "",
                "charset": row.get("charset") or "utf8mb4",
            },
            "sql": row.get("sql_text") or "",
            "output_fields": sql_outputs_by_config.get(row["id"], []),
        }

    global_request_config = normalize_global_request_config(
        product_row.get("global_request_config_text"),
        legacy_headers=_json_loads(product_row.get("global_headers_text"), {}),
    )

    return {
        "enable_encryption": bool(product_row.get("enable_encryption")),
        "encrypt_url": product_row.get("encrypt_url") or "",
        "decrypt_url": product_row.get("decrypt_url") or "",
        "global_request_config": global_request_config,
        "global_headers": _as_dict(global_request_config.get("header_config", {}).get("headers")),
        "schedule_tasks": [
            {
                "id": row["legacy_task_id"],
                "jobGroup": row.get("job_group") or "",
                "name": row.get("name") or "",
                "row_id": row["id"],
            }
            for row in schedule_rows
        ],
        "layout": layout,
        "interfaces": interfaces,
        "sqls": sqls,
    }


def get_product_detail(product_id: int) -> dict[str, Any]:
    bootstrap_from_legacy_json(force=False)
    product_row = _get_product_row(product_id)
    return {
        "product": _product_meta(product_row),
        "config": _build_product_config(product_id, product_row),
    }


def _delete_product_children(cursor, product_id: int) -> None:
    cursor.execute(
        "DELETE FROM api_tool_schedule_tasks WHERE product_id = %s",
        (product_id,),
    )
    cursor.execute(
        """
        DELETE o FROM api_tool_layout_item_options o
        INNER JOIN api_tool_layout_items i ON i.id = o.layout_item_id
        WHERE i.product_id = %s
        """,
        (product_id,),
    )
    cursor.execute(
        """
        DELETE m FROM api_tool_layout_item_mappings m
        INNER JOIN api_tool_layout_items i ON i.id = m.layout_item_id
        WHERE i.product_id = %s
        """,
        (product_id,),
    )
    cursor.execute(
        "DELETE FROM api_tool_layout_items WHERE product_id = %s",
        (product_id,),
    )
    cursor.execute(
        """
        DELETE c FROM api_tool_interface_condition_cases c
        INNER JOIN api_tool_interfaces i ON i.id = c.interface_id
        WHERE i.product_id = %s
        """,
        (product_id,),
    )
    cursor.execute(
        """
        DELETE r FROM api_tool_interface_response_mappings r
        INNER JOIN api_tool_interfaces i ON i.id = r.interface_id
        WHERE i.product_id = %s
        """,
        (product_id,),
    )
    cursor.execute(
        """
        DELETE f FROM api_tool_interface_field_types f
        INNER JOIN api_tool_interfaces i ON i.id = f.interface_id
        WHERE i.product_id = %s
        """,
        (product_id,),
    )
    cursor.execute(
        "DELETE FROM api_tool_interfaces WHERE product_id = %s",
        (product_id,),
    )
    cursor.execute(
        """
        DELETE o FROM api_tool_sql_output_fields o
        INNER JOIN api_tool_sql_configs s ON s.id = o.sql_config_id
        WHERE s.product_id = %s
        """,
        (product_id,),
    )
    cursor.execute(
        "DELETE FROM api_tool_sql_configs WHERE product_id = %s",
        (product_id,),
    )


def create_product(payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_schema_ready()
    name = str((payload or {}).get("name") or "").strip()
    if not name:
        raise ValueError("产品名称不能为空")

    config = _as_dict((payload or {}).get("config")) or default_product_config()
    global_request_config = _normalise_product_global_request_config(config)

    current = fetch_one("SELECT COUNT(*) AS count FROM api_tool_products")
    is_first = not current or current["count"] == 0
    next_sort = fetch_one(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_sort FROM api_tool_products"
    )
    sort_order = int((payload or {}).get("sort_order") or next_sort["next_sort"])
    is_default = bool((payload or {}).get("is_default", is_first))

    try:
        with connect() as connection:
            with connection.cursor() as cursor:
                if is_default:
                    cursor.execute("UPDATE api_tool_products SET is_default = FALSE")
                cursor.execute(
                    """
                    INSERT INTO api_tool_products
                    (name, legacy_config_path, enable_encryption, encrypt_url, decrypt_url, global_headers_text, global_request_config_text, is_locked, is_default, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        name,
                        str((payload or {}).get("legacy_config_path") or ""),
                        bool(config.get("enable_encryption", False)),
                        str(config.get("encrypt_url", "")),
                        str(config.get("decrypt_url", "")),
                        _json_dumps(_as_dict(global_request_config.get("header_config", {}).get("headers"))),
                        _json_dumps(global_request_config),
                        bool((payload or {}).get("locked", False)),
                        is_default,
                        sort_order,
                    ),
                )
                product_id = cursor.lastrowid
                _insert_product_children(cursor, product_id, config)
                connection.commit()
    except pymysql.IntegrityError as exc:
        raise ValueError(f"产品名称已存在: {name}") from exc

    return get_product_detail(product_id)


def update_product(product_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_schema_ready()
    existing = _get_product_row(product_id)
    product_payload = _as_dict((payload or {}).get("product")) or (payload or {})
    config = _as_dict((payload or {}).get("config")) or default_product_config()
    global_request_config = _normalise_product_global_request_config(config)
    name = str(product_payload.get("name") or existing["name"]).strip()
    if not name:
        raise ValueError("产品名称不能为空")

    locked = bool(product_payload.get("locked", existing.get("is_locked")))
    is_default = bool(product_payload.get("is_default", existing.get("is_default")))
    sort_order = int(product_payload.get("sort_order", existing.get("sort_order", 0)) or 0)
    legacy_config_path = str(
        product_payload.get("legacy_config_path", existing.get("legacy_config_path") or "")
    )

    try:
        with connect() as connection:
            with connection.cursor() as cursor:
                if is_default:
                    cursor.execute(
                        "UPDATE api_tool_products SET is_default = FALSE WHERE id != %s",
                        (product_id,),
                    )
                cursor.execute(
                    """
                    UPDATE api_tool_products
                    SET name = %s,
                        legacy_config_path = %s,
                        enable_encryption = %s,
                        encrypt_url = %s,
                        decrypt_url = %s,
                        global_headers_text = %s,
                        global_request_config_text = %s,
                        is_locked = %s,
                        is_default = %s,
                        sort_order = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        name,
                        legacy_config_path,
                        bool(config.get("enable_encryption", False)),
                        str(config.get("encrypt_url", "")),
                        str(config.get("decrypt_url", "")),
                        _json_dumps(_as_dict(global_request_config.get("header_config", {}).get("headers"))),
                        _json_dumps(global_request_config),
                        locked,
                        is_default,
                        sort_order,
                        product_id,
                    ),
                )
                _delete_product_children(cursor, product_id)
                _insert_product_children(cursor, product_id, config)
                connection.commit()
    except pymysql.IntegrityError as exc:
        raise ValueError(f"产品名称已存在: {name}") from exc

    return get_product_detail(product_id)


def delete_product(product_id: int) -> dict[str, Any]:
    _ensure_schema_ready()
    product = _get_product_row(product_id)
    with connect() as connection:
        with connection.cursor() as cursor:
            _delete_product_children(cursor, product_id)
            cursor.execute("DELETE FROM api_tool_products WHERE id = %s", (product_id,))
            if product.get("is_default"):
                cursor.execute(
                    """
                    UPDATE api_tool_products
                    SET is_default = TRUE
                    ORDER BY sort_order ASC, id ASC
                    LIMIT 1
                    """
                )
            connection.commit()
    return {"deleted": True}


def _array_index_replacer(text: str, variables: dict[str, Any]) -> str:
    pattern = re.compile(r"\[(\{(\w+)\})\]")

    def replace(match: re.Match[str]) -> str:
        var_name = match.group(2)
        value = variables.get(var_name)
        try:
            index = int(str(value)) - 1
        except (TypeError, ValueError):
            index = 0
        return f"[{max(index, 0)}]"

    return pattern.sub(replace, text)


def _apply_special_tokens(text: str) -> str:
    now = datetime.now()

    def replace_datetime(match: re.Match[str]) -> str:
        format_hint = match.group(1)
        return now.strftime(format_hint or "%Y%m%d%H%M%S")

    def replace_date(match: re.Match[str]) -> str:
        format_hint = match.group(1)
        return now.strftime(format_hint or "%Y%m%d")

    def replace_time(_match: re.Match[str]) -> str:
        return now.strftime("%H%M%S")

    def replace_random(match: re.Match[str]) -> str:
        kind = match.group(1)
        length = int(match.group(2))
        charset_map = {
            "digits": string.digits,
            "string": string.ascii_letters,
            "alphanum": string.ascii_letters + string.digits,
        }
        return "".join(random.choices(charset_map[kind], k=length))

    text = re.sub(r"\{dateTime(?::([^}]+))?\}", replace_datetime, text)
    text = re.sub(r"\{date(?::([^}]+))?\}", replace_date, text)
    text = re.sub(r"\{time\}", replace_time, text)
    text = re.sub(r"\{random:(digits|string|alphanum):(\d+)\}", replace_random, text)
    return text


def _replace_placeholders(text: str, variables: dict[str, Any]) -> str:
    return replace_template_text(
        text,
        variables,
        allow_legacy_placeholders=True,
    )


def _extract_formula_dependencies(formula: str) -> list[str]:
    return extract_template_dependencies(
        formula or "",
        allow_legacy_placeholders=True,
    )


def _evaluate_numeric_expression(expression: str) -> str:
    clean = expression.replace(" ", "")
    if not clean:
        return ""
    allowed_chars = set("0123456789+-*/().% ")
    if not all(char in allowed_chars for char in clean):
        raise ValueError("数值公式包含非法字符")
    if not any(operator in clean for operator in ["+", "-", "*", "/"]):
        raise ValueError("数值公式至少需要一个运算符")
    value = eval(clean.replace("%", "/100"), {"__builtins__": {}}, {})
    decimal_value = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if decimal_value == decimal_value.to_integral():
        return str(int(decimal_value))
    return format(decimal_value.normalize(), "f")


def _parse_formula_date(value: str) -> datetime:
    clean = re.sub(r"[-/]", "", value.strip())
    if len(clean) == 8:
        return datetime.strptime(clean, "%Y%m%d")
    if len(clean) == 14:
        return datetime.strptime(clean, "%Y%m%d%H%M%S")
    return datetime.strptime(value.strip(), "%Y%m%d %H:%M:%S")


def _evaluate_date_expression(expression: str) -> str:
    clean = expression.replace(" ", "")
    dates = re.findall(r"(\d{4}[-/]?\d{2}[-/]?\d{2}(?:\d{6})?)", clean)
    if len(dates) != 2 or "-" not in clean:
        raise ValueError("日期公式格式应为 日期1-日期2")
    delta = _parse_formula_date(dates[0]) - _parse_formula_date(dates[1])
    return str(delta.days)


def _resolve_runtime_values(
    config: dict[str, Any],
    input_variables: dict[str, Any] | None,
    request_id: str,
) -> dict[str, Any]:
    variables = dict(input_variables or {})
    variables["request_id"] = request_id
    provided_keys = set((input_variables or {}).keys())
    layout = _as_list(config.get("layout"))

    for _ in range(6):
        changed = False
        for raw_item in layout:
            item = _as_dict(raw_item)
            item_type = item.get("type")
            key = item.get("key")
            if item_type == "field" and key and key not in provided_keys:
                default_value = item.get("default", "")
                resolved_value = (
                    _replace_placeholders(str(default_value), variables)
                    if default_value not in (None, "")
                    else ""
                )
                if variables.get(key) != resolved_value:
                    variables[key] = resolved_value
                    changed = True
            elif item_type == "combo" and key and key not in provided_keys:
                default_value = item.get("default", "")
                if default_value not in (None, ""):
                    resolved_value = _replace_placeholders(str(default_value), variables)
                else:
                    options = _as_list(item.get("options"))
                    resolved_value = options[0].get("value", "") if options else ""
                if variables.get(key) != resolved_value:
                    variables[key] = resolved_value
                    changed = True
            elif item_type == "condition" and key:
                condition_field = item.get("condition_field")
                mappings = _as_dict(item.get("mappings"))
                source_value = str(variables.get(condition_field, ""))
                mapped_field = mappings.get(source_value)
                condition_value = variables.get(mapped_field, "") if mapped_field else ""
                if variables.get(key) != condition_value:
                    variables[key] = condition_value
                    changed = True
            elif item_type == "formula" and key:
                formula = str(item.get("formula", ""))
                dependencies = _extract_formula_dependencies(formula)
                if any(variables.get(dep, "") in (None, "") for dep in dependencies):
                    result = ""
                else:
                    expression = replace_template_text(
                        formula,
                        variables,
                        allow_legacy_placeholders=True,
                    )
                    try:
                        if item.get("formula_type") == "date":
                            result = _evaluate_date_expression(expression)
                        else:
                            result = _evaluate_numeric_expression(expression)
                    except Exception:
                        result = ""
                if variables.get(key) != result:
                    variables[key] = result
                    changed = True

        if not changed:
            break

    for key in provided_keys:
        variables[key] = input_variables.get(key)

    return variables


def _resolve_template_value(template: Any, variables: dict[str, Any]) -> Any:
    return replace_template_data(
        template,
        variables,
        allow_legacy_placeholders=True,
    )


def _convert_value_type(value: Any, field_type: str) -> Any:
    if field_type == "int":
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    if field_type == "float":
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    if field_type == "bool":
        if isinstance(value, str):
            return value.lower() in {"true", "1", "yes", "y"}
        return bool(value)
    return value


def _convert_field_types(data: Any, field_types: dict[str, str]) -> Any:
    if isinstance(data, dict):
        converted: dict[str, Any] = {}
        for key, value in data.items():
            if key in field_types:
                converted[key] = _convert_value_type(value, field_types[key])
            else:
                converted[key] = _convert_field_types(value, field_types)
        return converted
    if isinstance(data, list):
        return [_convert_field_types(item, field_types) for item in data]
    return data


def _resolve_interface_body_template(
    interface_config: dict[str, Any],
    variables: dict[str, Any],
) -> Any:
    if "conditional_body" in interface_config:
        conditional_body = _as_dict(interface_config.get("conditional_body"))
        condition_field = str(conditional_body.get("field", ""))
        condition_value = str(variables.get(condition_field, ""))
        cases = _as_dict(conditional_body.get("cases"))
        body_template = cases.get(condition_value)
        if body_template is None and cases:
            body_template = next(iter(cases.values()))
    else:
        body_template = interface_config.get("body_template", {})
    return _convert_field_types(
        _resolve_template_value(body_template, variables),
        _as_dict(interface_config.get("field_types")),
    )


def _resolve_preview_global_headers(
    config: dict[str, Any],
    variables: dict[str, Any],
) -> dict[str, Any]:
    global_request_config = normalize_global_request_config(
        config.get("global_request_config"),
        legacy_headers=_as_dict(config.get("global_headers")),
    )
    header_config = _as_dict(global_request_config.get("header_config"))
    if not header_config.get("enabled"):
        return {}
    return _as_dict(
        replace_template_data(
            _as_dict(header_config.get("headers")),
            variables,
            allow_legacy_placeholders=True,
        )
    )


def _build_request_preview(
    config: dict[str, Any],
    interface_name: str,
    variables: dict[str, Any] | None,
    request_id: str | None = None,
) -> dict[str, Any]:
    if interface_name not in _as_dict(config.get("interfaces")):
        raise ValueError(f"接口不存在: {interface_name}")

    resolved_request_id = request_id or str((variables or {}).get("request_id") or generate_request_id())
    resolved_variables = _resolve_runtime_values(config, variables or {}, resolved_request_id)
    interface_config = _as_dict(config.get("interfaces", {}).get(interface_name))
    request_body = _resolve_interface_body_template(interface_config, resolved_variables)
    prepared_request = prepare_request_definition(
        RequestDefinition(
            protocol=str(interface_config.get("protocol") or "http"),
            url=str(interface_config.get("url", "")),
            method=str(interface_config.get("method", "POST")).upper(),
            headers=_as_dict(interface_config.get("headers")),
            body=request_body,
            timeout=int(interface_config.get("timeout", 30) or 30),
        ),
        RequestExecutionContext(
            request_id=resolved_request_id,
            variables=resolved_variables,
            global_headers=_resolve_preview_global_headers(config, resolved_variables),
            allow_legacy_placeholders=True,
        ),
    )

    return {
        "interface_name": interface_name,
        "request_id": resolved_request_id,
        "resolved_variables": resolved_variables,
        "request": {
            "protocol": prepared_request.protocol,
            "url": prepared_request.url,
            "method": prepared_request.method,
            "headers": prepared_request.headers,
            "body": prepared_request.body,
        },
        "encryption": {
            "enabled": bool(config.get("enable_encryption", False))
            and bool(interface_config.get("enable_encryption", True)),
            "encrypt_url": str(config.get("encrypt_url", "")),
            "decrypt_url": str(config.get("decrypt_url", "")),
        },
    }


def preview_request(
    product_id: int,
    interface_name: str,
    variables: dict[str, Any] | None,
    request_id: str | None = None,
) -> dict[str, Any]:
    detail = get_product_detail(product_id)
    return _build_request_preview(detail["config"], interface_name, variables, request_id)


def _parse_path_tokens(path: str) -> list[Any]:
    clean = path.strip()
    if clean.startswith("$."):
        clean = clean[2:]
    elif clean.startswith("$"):
        clean = clean[1:]
    tokens: list[Any] = []
    for part in clean.split("."):
        if not part:
            continue
        position = 0
        while position < len(part):
            bracket_start = part.find("[", position)
            if bracket_start < 0:
                tokens.append(part[position:])
                break
            if bracket_start > position:
                tokens.append(part[position:bracket_start])
            bracket_end = part.find("]", bracket_start)
            index_text = part[bracket_start + 1 : bracket_end]
            if index_text.isdigit():
                tokens.append(int(index_text))
            position = bracket_end + 1
    return tokens


def _extract_simple_path(data: Any, path: str) -> Any:
    current = data
    for token in _parse_path_tokens(path):
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                return None
            current = current[token]
            continue
        if isinstance(current, dict):
            if token not in current:
                return None
            current = current[token]
            continue
        return None
    return current


def _extract_mapping_value(data: Any, path: str) -> Any:
    if "|" in path:
        first_path, nested_path = [part.strip() for part in path.split("|", 1)]
        base_value = _extract_simple_path(data, first_path)
        if isinstance(base_value, str):
            try:
                base_value = json.loads(base_value)
            except json.JSONDecodeError:
                return None
        return _extract_simple_path(base_value, nested_path)
    return _extract_simple_path(data, path)


def execute_request(
    product_id: int,
    interface_name: str,
    variables: dict[str, Any] | None,
    request_id: str | None = None,
    request_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    detail = get_product_detail(product_id)
    config = detail["config"]
    if interface_name not in _as_dict(config.get("interfaces")):
        raise ValueError(f"接口不存在: {interface_name}")

    resolved_request_id = request_id or str((variables or {}).get("request_id") or generate_request_id())
    resolved_variables = _resolve_runtime_values(config, variables or {}, resolved_request_id)
    interface_config = _as_dict(config.get("interfaces", {}).get(interface_name))
    encryption = {
        "enabled": bool(config.get("enable_encryption", False))
        and bool(interface_config.get("enable_encryption", True)),
        "encrypt_url": str(config.get("encrypt_url", "")),
        "decrypt_url": str(config.get("decrypt_url", "")),
    }
    global_runtime = resolve_global_request_runtime(
        config.get("global_request_config"),
        request_id=resolved_request_id,
        variables=resolved_variables,
        encryption=EncryptionConfig(
            enabled=bool(encryption["enabled"]),
            encrypt_url=str(encryption.get("encrypt_url") or ""),
            decrypt_url=str(encryption.get("decrypt_url") or ""),
        ),
        allow_legacy_placeholders=True,
    )
    runtime_variables = global_runtime["variables"]
    prepared_request = prepare_request_definition(
        RequestDefinition(
            protocol=str(interface_config.get("protocol") or "http"),
            url=str(interface_config.get("url", "")),
            method=str(interface_config.get("method", "POST")).upper(),
            headers=_as_dict(interface_config.get("headers")),
            body=_resolve_interface_body_template(interface_config, runtime_variables),
            timeout=int(interface_config.get("timeout", 30) or 30),
        ),
        RequestExecutionContext(
            request_id=resolved_request_id,
            variables=runtime_variables,
            global_headers=_as_dict(global_runtime.get("headers")),
            allow_legacy_placeholders=True,
        ),
    )
    outgoing_request = {
        "protocol": prepared_request.protocol,
        "url": prepared_request.url,
        "method": prepared_request.method,
        "headers": prepared_request.headers,
        "body": prepared_request.body,
    }

    if request_override:
        if "url" in request_override:
            outgoing_request["url"] = str(request_override.get("url") or "")
        if "method" in request_override:
            outgoing_request["method"] = str(request_override.get("method") or "POST").upper()
        if "headers" in request_override:
            outgoing_request["headers"] = _as_dict(request_override.get("headers"))
        if "body" in request_override:
            outgoing_request["body"] = request_override.get("body")

    request_result = execute_request_definition(
        RequestDefinition(
            protocol=str(outgoing_request.get("protocol") or interface_config.get("protocol") or "http"),
            url=str(outgoing_request.get("url") or ""),
            method=str(outgoing_request.get("method") or interface_config.get("method") or "POST").upper(),
            headers=_as_dict(outgoing_request.get("headers")),
            body=outgoing_request.get("body"),
            timeout=int(interface_config.get("timeout", 30) or 30),
        ),
        RequestExecutionContext(
            request_id=resolved_request_id,
            variables=runtime_variables,
            global_headers=_as_dict(global_runtime.get("headers")),
            encryption=EncryptionConfig(
                enabled=bool(encryption["enabled"]),
                encrypt_url=str(encryption.get("encrypt_url") or ""),
                decrypt_url=str(encryption.get("decrypt_url") or ""),
            ),
            allow_legacy_placeholders=True,
        ),
    )

    mapped_values: dict[str, Any] = {}
    for field_key, response_path in _as_dict(interface_config.get("response_mapping")).items():
        resolved_path = _replace_placeholders(str(response_path), runtime_variables)
        value = extract_response_value(request_result, resolved_path)
        if value is not None:
            mapped_values[str(field_key)] = value

    resolved_variables = _resolve_runtime_values(
        config,
        {**runtime_variables, **mapped_values},
        resolved_request_id,
    )

    return {
        "request_id": resolved_request_id,
        "request": request_result.request,
        "status_code": request_result.status_code,
        "headers": request_result.headers,
        "body": request_result.body,
        "raw_body": request_result.raw_body,
        "decrypted_body": request_result.decrypted_body,
        "mapped_values": mapped_values,
        "resolved_variables": resolved_variables,
    }


def execute_sql(
    product_id: int,
    sql_name: str,
    variables: dict[str, Any] | None,
    request_id: str | None = None,
) -> dict[str, Any]:
    detail = get_product_detail(product_id)
    config = detail["config"]
    sql_config = _as_dict(config.get("sqls", {}).get(sql_name))
    if not sql_config:
        raise ValueError(f"SQL 配置不存在: {sql_name}")

    resolved_request_id = request_id or str((variables or {}).get("request_id") or generate_request_id())
    resolved_variables = _resolve_runtime_values(config, variables or {}, resolved_request_id)
    resolved_sql = render_sql_template(
        str(sql_config.get("sql", "")),
        resolved_variables,
        allow_legacy_placeholders=True,
    )
    if not re.match(r"^\s*SELECT\b", resolved_sql, re.IGNORECASE):
        raise ValueError("仅支持 SELECT 查询语句")

    dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
    for keyword in dangerous_keywords:
        if re.search(rf"\b{keyword}\b", resolved_sql, re.IGNORECASE):
            raise ValueError(f"检测到不允许的 SQL 关键字: {keyword}")

    database = _as_dict(sql_config.get("database"))
    connection = pymysql.connect(
        host=str(database.get("host", "")),
        port=int(database.get("port", 3306) or 3306),
        user=str(database.get("user", "")),
        password=str(database.get("password", "")),
        database=str(database.get("database", "")),
        charset=str(database.get("charset", "utf8mb4") or "utf8mb4"),
        cursorclass=DictCursor,
        autocommit=True,
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(resolved_sql)
            rows = cursor.fetchall()
    finally:
        connection.close()

    serialised_rows: list[dict[str, Any]] = []
    for row in rows:
        serialised_row: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, (datetime, date)):
                serialised_row[key] = value.isoformat()
            else:
                serialised_row[key] = value
        serialised_rows.append(serialised_row)

    output_variables: dict[str, Any] = {}
    if serialised_rows:
        first_row = serialised_rows[0]
        for output_field in _as_list(sql_config.get("output_fields")):
            output_field = _as_dict(output_field)
            field_name = str(output_field.get("field", ""))
            if field_name and field_name in first_row:
                output_variables[field_name] = first_row[field_name]

    merged_variables = _resolve_runtime_values(
        config,
        {**(variables or {}), **output_variables},
        resolved_request_id,
    )

    return {
        "request_id": resolved_request_id,
        "sql_name": sql_name,
        "resolved_sql": resolved_sql,
        "rows": serialised_rows,
        "output_variables": output_variables,
        "resolved_variables": merged_variables,
    }


def run_schedule_task(schedule_row_id: int) -> dict[str, Any]:
    _ensure_schema_ready()
    task = fetch_one(
        """
        SELECT t.id, t.legacy_task_id, t.job_group, t.name, p.name AS product_name
        FROM api_tool_schedule_tasks t
        INNER JOIN api_tool_products p ON p.id = t.product_id
        WHERE t.id = %s
        """,
        (schedule_row_id,),
    )
    if not task:
        raise ValueError("定时任务不存在")

    login_response = requests.post(
        f"{SCHEDULER_BASE_URL}/auth/login",
        json={"username": SCHEDULER_USERNAME, "password": SCHEDULER_PASSWORD},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    if login_response.status_code != 200:
        raise ValueError("登录定时任务平台失败")

    login_payload = login_response.json()
    token = (
        _as_dict(login_payload.get("data")).get("access_token")
        or login_payload.get("access_token")
    )
    if not token:
        raise ValueError("定时任务平台未返回 access_token")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    run_response = requests.put(
        f"{SCHEDULER_BASE_URL}/schedule/job/run",
        json={"jobId": task["legacy_task_id"], "jobGroup": task["job_group"]},
        headers=headers,
        timeout=30,
    )
    if run_response.status_code != 200:
        raise ValueError(f"执行定时任务失败: {run_response.status_code}")

    try:
        requests.delete(
            f"{SCHEDULER_BASE_URL}/auth/logout",
            headers=headers,
            timeout=30,
        )
    except Exception:
        pass

    return {
        "task_id": task["id"],
        "task_name": task["name"],
        "product_name": task["product_name"],
        "message": f"任务 {task['name']} 已触发执行",
    }
