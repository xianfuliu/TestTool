from __future__ import annotations

import hashlib
import os
from typing import Any, Iterable

import pymysql
from pymysql.cursors import DictCursor


DATABASE_CONFIG = {
    "host": os.getenv("QUALITY_DB_HOST", "localhost"),
    "port": int(os.getenv("QUALITY_DB_PORT", "3306")),
    "user": os.getenv("QUALITY_DB_USER", "root"),
    "password": os.getenv("QUALITY_DB_PASSWORD", "root"),
    "database": os.getenv("QUALITY_DB_NAME", "quality_management_platform"),
    "charset": "utf8mb4",
}


def server_config() -> dict[str, Any]:
    config = DATABASE_CONFIG.copy()
    config.pop("database")
    return config


def connect(database: str | None = None):
    config = DATABASE_CONFIG.copy()
    if database is not None:
        config["database"] = database
    return pymysql.connect(**config, cursorclass=DictCursor, autocommit=False)


def ensure_database() -> None:
    config = server_config()
    db_name = DATABASE_CONFIG["database"]
    with pymysql.connect(**config, cursorclass=DictCursor, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )


def fetch_all(sql: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()


def fetch_one(sql: str, params: Iterable[Any] | None = None) -> dict[str, Any] | None:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchone()


def execute(sql: str, params: Iterable[Any] | None = None) -> int:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or ())
            connection.commit()
            return cursor.lastrowid or cursor.rowcount


def executemany(sql: str, values: list[tuple[Any, ...]]) -> None:
    if not values:
        return
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(sql, values)
            connection.commit()


def md5_text(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()
