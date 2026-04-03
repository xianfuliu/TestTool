from __future__ import annotations

import re
from typing import Any

import pymysql

from apps.common.http import api_view
from apps.common.legacy import load_json_file
from .template_processor import process_template


def _replace_sql_variables(sql: str, variable_pool: dict[str, Any]) -> str:
    def replace_match(match: re.Match[str]) -> str:
        var_name = match.group(1)
        if var_name not in variable_pool:
            return match.group(0)
        value = variable_pool[var_name]
        return value if isinstance(value, str) else str(value)

    return re.sub(r"\{(\w+)\}", replace_match, sql)


@api_view
def config(_request, payload=None):
    return load_json_file("backend/config/query_config.json")


@api_view
def execute(_request, payload=None):
    query_config = load_json_file("backend/config/query_config.json")
    query_name = (payload or {}).get("query_name", "").strip()
    variables = (payload or {}).get("variables", {})
    if not query_name:
        raise ValueError("query_name 不能为空")
    if query_name not in query_config["sql_queries"]:
        raise ValueError("查询配置不存在")

    query_item = query_config["sql_queries"][query_name]
    connection_key = query_item["db_connection"]
    connection = dict(query_config["database_connections"][connection_key])
    connection["port"] = int(connection["port"])
    connection["user"] = connection.pop("username")
    connection["charset"] = "utf8mb4"

    sql = process_template(query_item["sql"])
    sql = _replace_sql_variables(sql, variables)

    with pymysql.connect(**connection) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]

    result = []
    for row in rows:
        row_dict = {}
        for index, column in enumerate(columns):
            value = row[index]
            row_dict[column] = value.isoformat() if hasattr(value, "isoformat") else value
        result.append(row_dict)

    return {
        "query_name": query_name,
        "connection": connection_key,
        "sql": sql,
        "rows": result,
        "count": len(result),
        "output_fields": query_item.get("output_fields", {}),
    }
