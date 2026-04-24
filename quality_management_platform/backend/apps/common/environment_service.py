from __future__ import annotations

from apps.common.http import get_int
from test_platform.db import connect, execute, fetch_all, fetch_one


_ENVIRONMENT_SCHEMA_READY = False
DEFAULT_ENVIRONMENT_NAME = "默认环境"


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (column_name,))
    return cursor.fetchone() is not None


def _table_exists(table_name: str) -> bool:
    row = fetch_one("SHOW TABLES LIKE %s", (table_name,))
    return row is not None


def hydrate_environment_row(environment_row):
    return dict(environment_row or {})


def normalise_environment_payload(item):
    name = str(item.get("name") or "").strip()
    if not name:
        raise ValueError("环境名称不能为空")
    return {
        "name": name,
        "base_url": str(item.get("base_url") or "").strip(),
        "description": str(item.get("description") or "").strip(),
    }


def ensure_environment_schema_ready():
    global _ENVIRONMENT_SCHEMA_READY
    if _ENVIRONMENT_SCHEMA_READY:
        return
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS environments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    base_url VARCHAR(500) DEFAULT '',
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            if _column_exists(cursor, "environments", "headers"):
                cursor.execute("ALTER TABLE environments DROP COLUMN headers")
            if _column_exists(cursor, "environments", "variables"):
                cursor.execute("ALTER TABLE environments DROP COLUMN variables")
            if not _column_exists(cursor, "environments", "updated_at"):
                cursor.execute(
                    """
                    ALTER TABLE environments
                    ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
                    """
                )
            cursor.execute("SELECT id FROM environments ORDER BY id ASC LIMIT 1")
            if cursor.fetchone() is None:
                cursor.execute(
                    """
                    INSERT INTO environments (name, base_url, description)
                    VALUES (%s, %s, %s)
                    """,
                    (DEFAULT_ENVIRONMENT_NAME, "", ""),
                )
        connection.commit()
    _ENVIRONMENT_SCHEMA_READY = True


def list_environments():
    ensure_environment_schema_ready()
    return [
        hydrate_environment_row(row)
        for row in fetch_all("SELECT * FROM environments ORDER BY created_at DESC, id DESC")
    ]


def get_environment(environment_id: int):
    ensure_environment_schema_ready()
    return hydrate_environment_row(fetch_one("SELECT * FROM environments WHERE id = %s", (environment_id,)))


def create_environment(payload):
    ensure_environment_schema_ready()
    item = normalise_environment_payload(payload or {})
    existing = fetch_one("SELECT id FROM environments WHERE name = %s", (item["name"],))
    if existing:
        raise ValueError("环境名称已存在")
    environment_id = execute(
        """
        INSERT INTO environments (name, base_url, description)
        VALUES (%s, %s, %s)
        """,
        (
            item["name"],
            item["base_url"],
            item["description"],
        ),
    )
    return {"environment_id": environment_id}, 201


def update_environment(environment_id: int, payload):
    ensure_environment_schema_ready()
    item = normalise_environment_payload(payload or {})
    existing = fetch_one("SELECT id FROM environments WHERE name = %s AND id <> %s", (item["name"], environment_id))
    if existing:
        raise ValueError("环境名称已存在")
    updated = execute(
        """
        UPDATE environments
        SET name = %s, base_url = %s, description = %s
        WHERE id = %s
        """,
        (
            item["name"],
            item["base_url"],
            item["description"],
            environment_id,
        ),
    )
    return {"updated": updated >= 0}


def delete_environment(environment_id: int):
    ensure_environment_schema_ready()
    total_row = fetch_one("SELECT COUNT(*) AS total FROM environments")
    total = get_int((total_row or {}).get("total"))
    if total <= 1:
        raise ValueError("至少需要保留一个环境")
    if _table_exists("test_cases"):
        case_row = fetch_one("SELECT COUNT(*) AS total FROM test_cases WHERE environment_id = %s", (environment_id,))
        if get_int((case_row or {}).get("total")) > 0:
            raise ValueError("当前环境已被测试用例使用，请先调整用例环境")
    if _table_exists("global_variable_environments"):
        variable_row = fetch_one(
            "SELECT COUNT(*) AS total FROM global_variable_environments WHERE environment_id = %s",
            (environment_id,),
        )
        if get_int((variable_row or {}).get("total")) > 0:
            raise ValueError("当前环境已被全局变量关联，请先调整变量所属环境")
    return {"deleted": execute("DELETE FROM environments WHERE id = %s", (environment_id,)) > 0}
