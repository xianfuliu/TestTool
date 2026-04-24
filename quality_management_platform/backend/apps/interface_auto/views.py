from __future__ import annotations

import json
from datetime import datetime

from apps.common.environment_service import ensure_environment_schema_ready
from apps.common.http import api_view, get_int
from test_platform.db import connect, execute, executemany, fetch_all, fetch_one

from .execution_service import execute_case_run
from .report_service import delete_report, get_report_detail, list_report_groups, list_report_records, list_reports
from . import template_service


_CASE_SCHEMA_READY = False
_SUITE_SCHEMA_READY = False
_GLOBAL_TOOL_SCHEMA_READY = False
_VARIABLE_SCHEMA_READY = False
SUITE_SCHEDULER_SOURCE = "interface_auto.test_suite"
GLOBAL_TOOL_TYPES = {"http_request", "sql_tool", "python_script"}
GLOBAL_VARIABLE_TYPES = {"string", "int", "integer", "float", "double", "decimal", "bool", "boolean", "json"}


def _json_text(value):
    return json.dumps(value or {}, ensure_ascii=False)


def _empty_list_json(value):
    return json.dumps(value or [], ensure_ascii=False)


def _json_value(value, default):
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _json_list_value(value):
    parsed = _json_value(value, [])
    return parsed if isinstance(parsed, list) else []


def _enabled_by_default(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() not in {"false", "0", "no", "n"}
    return bool(value)


def _bool_value(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() not in {"false", "0", "no", "n"}
    return bool(value)


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (column_name,))
    return cursor.fetchone() is not None


def _index_exists(cursor, table_name: str, index_name: str) -> bool:
    cursor.execute(f"SHOW INDEX FROM {table_name} WHERE Key_name = %s", (index_name,))
    return cursor.fetchone() is not None


def _ensure_case_schema_extensions():
    global _CASE_SCHEMA_READY
    if _CASE_SCHEMA_READY:
        return
    with connect() as connection:
        with connection.cursor() as cursor:
            if not _column_exists(cursor, "test_cases", "global_request_config_text"):
                cursor.execute(
                    """
                    ALTER TABLE test_cases
                    ADD COLUMN global_request_config_text LONGTEXT NULL AFTER global_vars
                    """
                )
            if not _column_exists(cursor, "test_cases", "output_variables_text"):
                cursor.execute(
                    """
                    ALTER TABLE test_cases
                    ADD COLUMN output_variables_text LONGTEXT NULL AFTER global_request_config_text
                    """
                )
            if not _column_exists(cursor, "test_case_steps", "use_global_headers"):
                cursor.execute(
                    """
                    ALTER TABLE test_case_steps
                    ADD COLUMN use_global_headers BOOLEAN DEFAULT TRUE AFTER enable_encryption
                    """
                )
        connection.commit()
    _CASE_SCHEMA_READY = True


def _hydrate_case_row(case_row):
    if not case_row:
        return {}
    hydrated = dict(case_row)
    hydrated["global_vars"] = _json_value(hydrated.get("global_vars"), {})
    hydrated["global_request_config"] = _json_value(hydrated.get("global_request_config_text"), {})
    hydrated["output_variables"] = _json_value(hydrated.get("output_variables_text"), [])
    return hydrated


def _hydrate_step_row(step_row):
    hydrated = dict(step_row)
    hydrated["pre_processing"] = _json_value(hydrated.get("pre_processing"), {})
    hydrated["post_processing"] = _json_value(hydrated.get("post_processing"), {})
    hydrated["assertions"] = _json_value(hydrated.get("assertions"), {})
    hydrated["variables"] = _json_value(hydrated.get("variables"), {})
    hydrated["use_global_headers"] = _enabled_by_default(hydrated.get("use_global_headers", True))
    return hydrated


def _hydrate_global_tool_row(tool_row):
    if not tool_row:
        return {}
    hydrated = dict(tool_row)
    hydrated["config"] = _json_value(hydrated.get("config"), {})
    hydrated["enabled"] = _enabled_by_default(hydrated.get("enabled", True))
    hydrated["project_id"] = get_int(hydrated.get("project_id"))
    hydrated["business_group_id"] = get_int(hydrated.get("business_group_id"))
    hydrated["is_shared"] = _bool_value(hydrated.get("is_shared"), False)
    return hydrated


def _hydrate_global_variable_row(variable_row):
    if not variable_row:
        return {}
    hydrated = dict(variable_row)
    hydrated["project_id"] = get_int(hydrated.get("project_id"))
    hydrated["business_group_id"] = get_int(hydrated.get("business_group_id"))
    hydrated["environment_ids"] = [
        get_int(item)
        for item in str(hydrated.get("environment_ids_text") or "").split(",")
        if get_int(item)
    ]
    hydrated["environment_names"] = [
        item
        for item in str(hydrated.get("environment_names_text") or "").split("||")
        if item
    ]
    return hydrated


def _normalise_global_tool_payload(item):
    tool_type = str(item.get("tool_type") or "").strip()
    if tool_type not in GLOBAL_TOOL_TYPES:
        raise ValueError("暂只支持 HTTP请求、SQL工具、Python脚本")
    name = str(item.get("name") or "").strip()
    if not name:
        raise ValueError("工具名称不能为空")
    project_id = get_int(item.get("project_id"))
    if not project_id:
        raise ValueError("请选择所属项目")
    project = fetch_one(
        """
        SELECT p.id, p.business_group_id
        FROM projects p
        WHERE p.id = %s
        """,
        (project_id,),
    )
    if not project:
        raise ValueError("所属项目不存在")
    config = _json_value(item.get("config"), {})
    if not isinstance(config, dict):
        config = {}
    if tool_type == "http_request":
        config["method"] = str(config.get("method") or "GET").upper()
        config["url"] = str(config.get("url") or "").strip()
        if not config["url"]:
            raise ValueError("HTTP 请求 URL 不能为空")
        config["timeout"] = int(config.get("timeout") or 30)
    elif tool_type == "sql_tool":
        config["database_connection_id"] = get_int(config.get("database_connection_id"))
        config["database"] = str(config.get("database") or "").strip()
        config["sql"] = str(config.get("sql") or "").strip()
        config["output_fields"] = _json_list_value(config.get("output_fields"))
        if not config["database_connection_id"]:
            raise ValueError("请选择数据库")
        if not config["database"]:
            raise ValueError("请选择库名")
        if not config["sql"]:
            raise ValueError("SQL 语句不能为空")
    elif tool_type == "python_script":
        config["script"] = str(config.get("script") or config.get("script_text") or config.get("code") or "").strip()
        config["timeout_seconds"] = int(config.get("timeout_seconds") or config.get("timeout") or 60)
        config["output_fields"] = _json_list_value(config.get("output_fields"))
        if not config["script"]:
            raise ValueError("Python 脚本内容不能为空")
    return {
        "name": name,
        "project_id": project_id,
        "tool_type": tool_type,
        "description": str(item.get("description") or "").strip(),
        "config": config,
        "enabled": _enabled_by_default(item.get("enabled", True)),
        "is_shared": _bool_value(item.get("is_shared"), False),
    }


def _normalise_global_variable_payload(item):
    project_id = get_int(item.get("project_id"))
    if not project_id:
        raise ValueError("请选择所属项目")
    project = fetch_one(
        """
        SELECT p.id, p.business_group_id
        FROM projects p
        WHERE p.id = %s
        """,
        (project_id,),
    )
    if not project:
        raise ValueError("所属项目不存在")
    environment_rows = fetch_all("SELECT id FROM environments ORDER BY id ASC")
    valid_environment_ids = [get_int(row.get("id")) for row in environment_rows if get_int(row.get("id"))]
    environment_ids = []
    for raw_id in item.get("environment_ids") or []:
        environment_id = get_int(raw_id)
        if environment_id and environment_id not in environment_ids:
            environment_ids.append(environment_id)
    if not environment_ids:
        environment_ids = list(valid_environment_ids)
    environment_ids = [environment_id for environment_id in environment_ids if environment_id in valid_environment_ids]
    if not environment_ids:
        raise ValueError("请至少选择一个所属环境")
    name = str(item.get("name") or "").strip()
    if not name:
        raise ValueError("变量名称不能为空")
    variable_type = str(item.get("variable_type") or "string").strip().lower() or "string"
    if variable_type not in GLOBAL_VARIABLE_TYPES:
        raise ValueError("变量类型不支持")
    return {
        "project_id": project_id,
        "environment_ids": environment_ids,
        "name": name,
        "value": str(item.get("value", "")),
        "variable_type": variable_type,
        "description": str(item.get("description") or "").strip(),
    }


def _ensure_global_tool_schema_ready():
    global _GLOBAL_TOOL_SCHEMA_READY
    if _GLOBAL_TOOL_SCHEMA_READY:
        return
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS global_tools (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NULL,
                    name VARCHAR(100) NOT NULL,
                    tool_type VARCHAR(50) NOT NULL,
                    description TEXT,
                    config JSON NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    is_shared BOOLEAN DEFAULT FALSE,
                    created_by VARCHAR(50) DEFAULT 'admin',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_global_tools_project_id (project_id),
                    INDEX idx_global_tools_type (tool_type),
                    INDEX idx_global_tools_enabled (enabled),
                    INDEX idx_global_tools_shared (is_shared)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            if not _column_exists(cursor, "global_tools", "project_id"):
                cursor.execute(
                    """
                    ALTER TABLE global_tools
                    ADD COLUMN project_id INT NULL AFTER id
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE global_tools
                    ADD INDEX idx_global_tools_project_id (project_id)
                    """
                )
            if not _column_exists(cursor, "global_tools", "is_shared"):
                cursor.execute(
                    """
                    ALTER TABLE global_tools
                    ADD COLUMN is_shared BOOLEAN DEFAULT FALSE AFTER enabled
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE global_tools
                    ADD INDEX idx_global_tools_shared (is_shared)
                    """
                )
        connection.commit()
    _GLOBAL_TOOL_SCHEMA_READY = True


def _ensure_global_variable_schema_ready():
    global _VARIABLE_SCHEMA_READY
    if _VARIABLE_SCHEMA_READY:
        return
    ensure_environment_schema_ready()
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS global_variables (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    value TEXT,
                    variable_type VARCHAR(30) DEFAULT 'string',
                    description TEXT,
                    created_by VARCHAR(50) DEFAULT 'admin',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uniq_project_var (project_id, name),
                    INDEX idx_global_variables_project_id (project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS global_variable_environments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    variable_id INT NOT NULL,
                    environment_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uniq_global_variable_environment (variable_id, environment_id),
                    INDEX idx_global_variable_scope_variable (variable_id),
                    INDEX idx_global_variable_scope_environment (environment_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            has_environment_column = _column_exists(cursor, "global_variables", "environment_id")
            if _index_exists(cursor, "global_variables", "uniq_project_environment_var"):
                cursor.execute("ALTER TABLE global_variables DROP INDEX uniq_project_environment_var")
            if not _index_exists(cursor, "global_variables", "uniq_project_var"):
                cursor.execute(
                    """
                    ALTER TABLE global_variables
                    ADD UNIQUE KEY uniq_project_var (project_id, name)
                    """
                )
            if not _index_exists(cursor, "global_variables", "idx_global_variables_project_id"):
                cursor.execute(
                    """
                    ALTER TABLE global_variables
                    ADD INDEX idx_global_variables_project_id (project_id)
                    """
                )
            if not _index_exists(cursor, "global_variable_environments", "idx_global_variable_scope_variable"):
                cursor.execute(
                    """
                    ALTER TABLE global_variable_environments
                    ADD INDEX idx_global_variable_scope_variable (variable_id)
                    """
                )
            if not _index_exists(cursor, "global_variable_environments", "idx_global_variable_scope_environment"):
                cursor.execute(
                    """
                    ALTER TABLE global_variable_environments
                    ADD INDEX idx_global_variable_scope_environment (environment_id)
                    """
                )
            if not _index_exists(cursor, "global_variable_environments", "uniq_global_variable_environment"):
                cursor.execute(
                    """
                    ALTER TABLE global_variable_environments
                    ADD UNIQUE KEY uniq_global_variable_environment (variable_id, environment_id)
                    """
                )
            cursor.execute("SELECT id FROM environments ORDER BY id ASC")
            environment_rows = cursor.fetchall()
            all_environment_ids = [
                get_int(row.get("id"))
                for row in environment_rows
                if get_int(row.get("id"))
            ]
            if has_environment_column:
                cursor.execute(
                    """
                    SELECT gv.id, gv.environment_id
                    FROM global_variables gv
                    LEFT JOIN global_variable_environments gve ON gve.variable_id = gv.id
                    WHERE gve.variable_id IS NULL
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT gv.id
                    FROM global_variables gv
                    LEFT JOIN global_variable_environments gve ON gve.variable_id = gv.id
                    WHERE gve.variable_id IS NULL
                    """
                )
            rows_without_scope = cursor.fetchall()
            scope_rows = []
            for row in rows_without_scope:
                variable_id = get_int(row.get("id"))
                if not variable_id:
                    continue
                raw_environment_id = get_int(row.get("environment_id")) if has_environment_column else 0
                scope_environment_ids = (
                    [raw_environment_id]
                    if raw_environment_id
                    else list(all_environment_ids)
                )
                for environment_id in scope_environment_ids:
                    scope_rows.append((variable_id, environment_id))
            if scope_rows:
                executemany(
                    """
                    INSERT IGNORE INTO global_variable_environments (variable_id, environment_id)
                    VALUES (%s, %s)
                    """,
                    scope_rows,
                )
        connection.commit()
    _VARIABLE_SCHEMA_READY = True


def _global_tools_select(where_sql: str = "", params=()):
    _ensure_global_tool_schema_ready()
    query = """
        SELECT
            gt.*,
            p.name AS project_name,
            p.business_group_id,
            bg.name AS business_group_name
        FROM global_tools gt
        LEFT JOIN projects p ON p.id = gt.project_id
        LEFT JOIN business_groups bg ON bg.id = p.business_group_id
    """
    if where_sql:
        query = f"{query} {where_sql}"
    query = f"{query} ORDER BY gt.updated_at DESC, gt.id DESC"
    return [_hydrate_global_tool_row(row) for row in fetch_all(query, params)]


def _global_variables_select(where_sql: str = "", params=()):
    _ensure_global_variable_schema_ready()
    query = """
        SELECT
            gv.*,
            p.name AS project_name,
            p.business_group_id,
            bg.name AS business_group_name,
            GROUP_CONCAT(DISTINCT env.id ORDER BY env.id) AS environment_ids_text,
            GROUP_CONCAT(DISTINCT env.name ORDER BY env.id SEPARATOR '||') AS environment_names_text
        FROM global_variables gv
        LEFT JOIN projects p ON p.id = gv.project_id
        LEFT JOIN business_groups bg ON bg.id = p.business_group_id
        LEFT JOIN global_variable_environments gve ON gve.variable_id = gv.id
        LEFT JOIN environments env ON env.id = gve.environment_id
    """
    if where_sql:
        query = f"{query} {where_sql}"
    query = f"{query} GROUP BY gv.id ORDER BY gv.updated_at DESC, gv.id DESC"
    return [_hydrate_global_variable_row(row) for row in fetch_all(query, params)]


def _list_case_steps(case_id: int):
    rows = fetch_all(
        """
        SELECT
            cs.*,
            at.project_id AS api_project_id,
            at.folder_id AS api_folder_id,
            at.name AS api_name,
            at.method AS api_method,
            at.url_path AS api_url_path,
            at.description AS api_description
        FROM test_case_steps cs
        LEFT JOIN api_templates at ON cs.api_template_id = at.id
        WHERE cs.case_id = %s
        ORDER BY cs.step_order, cs.id
        """,
        (case_id,),
    )
    return [_hydrate_step_row(row) for row in rows]


def _get_case_detail(case_id: int):
    _ensure_case_schema_extensions()
    case_row = _hydrate_case_row(fetch_one("SELECT * FROM test_cases WHERE id = %s", (case_id,)))
    if not case_row:
        return {}
    case_row["steps"] = _list_case_steps(case_id)
    return case_row


def _list_cases(where_sql: str = "", params=()):
    _ensure_case_schema_extensions()
    query = """
        SELECT *
        FROM test_cases
    """
    if where_sql:
        query = f"{query} {where_sql}"
    query = f"{query} ORDER BY sort_order, created_at"
    return [_hydrate_case_row(row) for row in fetch_all(query, params)]


def _normalize_case_name(value):
    return str(value or "").strip()


def _validate_case_folder(project_id, folder_id):
    if not project_id:
        raise ValueError("project_id 不能为空")
    if not folder_id:
        return
    folder = fetch_one(
        "SELECT id FROM case_folders WHERE id = %s AND project_id = %s",
        (folder_id, project_id),
    )
    if not folder:
        raise ValueError("目标目录不存在或不属于当前项目")


def _validate_unique_case_name(project_id, folder_id, name, exclude_id=None):
    normalized_name = _normalize_case_name(name)
    if not normalized_name:
        raise ValueError("用例名称不能为空")
    where_sql = "project_id = %s AND LOWER(name) = LOWER(%s)"
    params = [project_id, normalized_name]
    if folder_id:
        where_sql = f"{where_sql} AND folder_id = %s"
        params.append(folder_id)
    else:
        where_sql = f"{where_sql} AND folder_id IS NULL"
    if exclude_id:
        where_sql = f"{where_sql} AND id <> %s"
        params.append(exclude_id)
    duplicate = fetch_one(f"SELECT id FROM test_cases WHERE {where_sql} LIMIT 1", tuple(params))
    if duplicate:
        raise ValueError("目标同级目录下已存在同名测试用例")


def _write_case_steps(case_id: int, steps):
    execute("DELETE FROM test_case_steps WHERE case_id = %s", (case_id,))
    for index, step in enumerate(steps or [], start=1):
        execute(
            """
            INSERT INTO test_case_steps (
                case_id,
                api_template_id,
                step_order,
                name,
                enabled,
                pre_processing,
                post_processing,
                assertions,
                variables,
                enable_encryption,
                use_global_headers
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                case_id,
                step.get("api_template_id"),
                step.get("step_order") or index,
                step.get("name", ""),
                step.get("enabled", True),
                _json_text(step.get("pre_processing")),
                _json_text(step.get("post_processing")),
                _json_text(step.get("assertions")),
                _json_text(step.get("variables")),
                step.get("enable_encryption", False),
                _enabled_by_default(step.get("use_global_headers", True)),
            ),
        )


def _delete_case_with_steps(case_id: int):
    execute("DELETE FROM test_case_steps WHERE case_id = %s", (case_id,))
    return execute("DELETE FROM test_cases WHERE id = %s", (case_id,)) > 0


def _ensure_suite_schema_ready():
    global _SUITE_SCHEMA_READY
    if _SUITE_SCHEMA_READY:
        return
    execute(
        """
        CREATE TABLE IF NOT EXISTS test_suites (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            notify_emails JSON NULL,
            email_config JSON NULL,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_test_suites_project_name (project_id, name),
            INDEX idx_test_suites_project_id (project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    execute(
        """
        CREATE TABLE IF NOT EXISTS test_suite_cases (
            id INT AUTO_INCREMENT PRIMARY KEY,
            suite_id INT NOT NULL,
            case_id INT NOT NULL,
            sort_order INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_test_suite_case (suite_id, case_id),
            INDEX idx_test_suite_cases_suite_id (suite_id),
            INDEX idx_test_suite_cases_case_id (case_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    _SUITE_SCHEMA_READY = True


def _normalise_suite_name(value):
    return str(value or "").strip()


def _validate_suite_payload(item, *, current_id=None):
    project_id = get_int(item.get("project_id"))
    if not project_id:
        raise ValueError("请选择所属项目")
    if not fetch_one("SELECT id FROM projects WHERE id = %s", (project_id,)):
        raise ValueError("所属项目不存在")

    name = _normalise_suite_name(item.get("name"))
    if not name:
        raise ValueError("请输入测试集名称")

    params = [project_id, name]
    duplicate_sql = "SELECT id FROM test_suites WHERE project_id = %s AND LOWER(name) = LOWER(%s)"
    if current_id:
        duplicate_sql = f"{duplicate_sql} AND id <> %s"
        params.append(current_id)
    if fetch_one(f"{duplicate_sql} LIMIT 1", tuple(params)):
        raise ValueError("当前项目下已存在同名测试集")

    case_ids = []
    for raw_case_id in item.get("case_ids") or []:
        case_id = get_int(raw_case_id)
        if case_id and case_id not in case_ids:
            case_ids.append(case_id)
    if not case_ids:
        raise ValueError("请至少选择一个测试用例")

    if case_ids:
        placeholders = ", ".join(["%s"] * len(case_ids))
        rows = fetch_all(
            f"""
            SELECT id
            FROM test_cases
            WHERE project_id = %s AND id IN ({placeholders})
            """,
            (project_id, *case_ids),
        )
        existed_ids = {int(row["id"]) for row in rows}
        missing_ids = [case_id for case_id in case_ids if case_id not in existed_ids]
        if missing_ids:
            raise ValueError("所选测试用例不存在或不属于当前项目")

    return {
        "project_id": project_id,
        "name": name,
        "description": str(item.get("description") or "").strip(),
        "case_ids": case_ids,
        "notify_emails": item.get("notify_emails") or [],
        "email_config": item.get("email_config") or {},
    }


def _suite_case_rows(suite_id: int):
    return fetch_all(
        """
        SELECT
            tsc.case_id,
            tsc.sort_order,
            tc.name,
            tc.description,
            tc.folder_id,
            tc.project_id,
            cf.name AS folder_name
        FROM test_suite_cases tsc
        INNER JOIN test_cases tc ON tc.id = tsc.case_id
        LEFT JOIN case_folders cf ON cf.id = tc.folder_id
        WHERE tsc.suite_id = %s
        ORDER BY tsc.sort_order ASC, tsc.id ASC
        """,
        (suite_id,),
    )


def _suite_scheduler_tasks(suite_ids: list[int]):
    if not suite_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(suite_ids))
    rows = fetch_all(
        f"""
        SELECT *
        FROM scheduler_tasks
        WHERE task_type = 'test_suite'
          AND source_module = %s
          AND source_id IN ({placeholders})
        ORDER BY updated_at DESC, id DESC
        """,
        (SUITE_SCHEDULER_SOURCE, *suite_ids),
    )
    tasks_by_suite_id = {}
    for row in rows:
        source_id = get_int(row.get("source_id"))
        if source_id and source_id not in tasks_by_suite_id:
            item = dict(row)
            item["target_config"] = _json_value(item.get("target_config"), {})
            item["notify_config"] = _json_value(item.get("notify_config"), {})
            item["enabled"] = bool(item.get("enabled"))
            item["allow_concurrent"] = bool(item.get("allow_concurrent"))
            tasks_by_suite_id[source_id] = item
    return tasks_by_suite_id


def _hydrate_suite(row, scheduler_task=None, *, include_cases=False):
    item = dict(row)
    item["notify_emails"] = _json_value(item.get("notify_emails"), [])
    item["email_config"] = _json_value(item.get("email_config"), {})
    if include_cases:
        item["cases"] = _suite_case_rows(item["id"])
    else:
        item["cases"] = []
    item["case_ids"] = [case["case_id"] for case in item["cases"]]
    item["case_count"] = len(item["cases"]) if include_cases else int(item.get("case_count") or 0)
    item["scheduler_task"] = scheduler_task
    return item


def _write_suite_cases(suite_id: int, case_ids):
    execute("DELETE FROM test_suite_cases WHERE suite_id = %s", (suite_id,))
    values = [(suite_id, case_id, index) for index, case_id in enumerate(case_ids or [], start=1)]
    executemany(
        """
        INSERT INTO test_suite_cases (suite_id, case_id, sort_order)
        VALUES (%s, %s, %s)
        """,
        values,
    )


def _get_suite_detail(suite_id: int):
    _ensure_suite_schema_ready()
    row = fetch_one(
        """
        SELECT
            ts.*,
            p.name AS project_name,
            p.business_group_id,
            bg.name AS business_group_name
        FROM test_suites ts
        LEFT JOIN projects p ON p.id = ts.project_id
        LEFT JOIN business_groups bg ON bg.id = p.business_group_id
        WHERE ts.id = %s
        """,
        (suite_id,),
    )
    if not row:
        return None
    scheduler_task = _suite_scheduler_tasks([suite_id]).get(suite_id)
    return _hydrate_suite(row, scheduler_task=scheduler_task, include_cases=True)


@api_view
def test_suites(request, payload=None):
    _ensure_suite_schema_ready()
    if request.method == "GET":
        project_id = get_int((payload or {}).get("project_id"))
        keyword = str((payload or {}).get("keyword") or "").strip()
        conditions = []
        params = []
        if project_id:
            conditions.append("ts.project_id = %s")
            params.append(project_id)
        if keyword:
            like_value = f"%{keyword}%"
            conditions.append("(ts.name LIKE %s OR ts.description LIKE %s)")
            params.extend([like_value, like_value])
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = fetch_all(
            f"""
            SELECT
                ts.*,
                p.name AS project_name,
                p.business_group_id,
                bg.name AS business_group_name,
                (
                    SELECT COUNT(*)
                    FROM test_suite_cases tsc
                    WHERE tsc.suite_id = ts.id
                ) AS case_count
            FROM test_suites ts
            LEFT JOIN projects p ON p.id = ts.project_id
            LEFT JOIN business_groups bg ON bg.id = p.business_group_id
            {where_sql}
            ORDER BY ts.id DESC
            """,
            tuple(params),
        )
        tasks_by_suite_id = _suite_scheduler_tasks([int(row["id"]) for row in rows])
        return [
            _hydrate_suite(row, scheduler_task=tasks_by_suite_id.get(int(row["id"])), include_cases=False)
            for row in rows
        ]

    item = _validate_suite_payload(payload or {})
    suite_id = execute(
        """
        INSERT INTO test_suites (project_id, name, description, notify_emails, email_config, created_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            item["project_id"],
            item["name"],
            item["description"],
            _empty_list_json(item["notify_emails"]),
            _json_text(item["email_config"]),
            "admin",
        ),
    )
    _write_suite_cases(suite_id, item["case_ids"])
    return {"suite_id": suite_id}, 201


@api_view
def test_suite_detail(request, suite_id: int, payload=None):
    _ensure_suite_schema_ready()
    current = _get_suite_detail(suite_id)
    if not current:
        raise ValueError("测试集不存在")
    if request.method == "GET":
        return current
    if request.method == "PUT":
        item = _validate_suite_payload(payload or {}, current_id=suite_id)
        updated = execute(
            """
            UPDATE test_suites
            SET project_id = %s,
                name = %s,
                description = %s,
                notify_emails = %s,
                email_config = %s
            WHERE id = %s
            """,
            (
                item["project_id"],
                item["name"],
                item["description"],
                _empty_list_json(item["notify_emails"]),
                _json_text(item["email_config"]),
                suite_id,
            ),
        )
        _write_suite_cases(suite_id, item["case_ids"])
        return {"updated": updated >= 0, "suite": _get_suite_detail(suite_id)}

    task_rows = fetch_all(
        """
        SELECT id
        FROM scheduler_tasks
        WHERE task_type = 'test_suite'
          AND source_module = %s
          AND source_id = %s
        """,
        (SUITE_SCHEDULER_SOURCE, suite_id),
    )
    for task in task_rows:
        execute("DELETE FROM scheduler_task_runs WHERE task_id = %s", (task["id"],))
    execute(
        "DELETE FROM scheduler_tasks WHERE task_type = 'test_suite' AND source_module = %s AND source_id = %s",
        (SUITE_SCHEDULER_SOURCE, suite_id),
    )
    execute("DELETE FROM test_suite_cases WHERE suite_id = %s", (suite_id,))
    return {"deleted": execute("DELETE FROM test_suites WHERE id = %s", (suite_id,)) > 0}


@api_view
def overview(_request, payload=None):
    _ensure_global_tool_schema_ready()
    _ensure_global_variable_schema_ready()
    ensure_environment_schema_ready()
    return {
        "business_groups": fetch_all("SELECT * FROM business_groups ORDER BY created_at ASC"),
        "projects": fetch_all(
            """
            SELECT p.*, bg.name AS group_name
            FROM projects p
            LEFT JOIN business_groups bg ON p.business_group_id = bg.id
            ORDER BY p.created_at ASC
            """
        ),
        "global_tools": _global_tools_select(),
        "global_variables": _global_variables_select(),
        "environments": fetch_all("SELECT * FROM environments ORDER BY created_at DESC"),
        "reports": fetch_all("SELECT * FROM test_reports ORDER BY created_at DESC LIMIT 20"),
    }


@api_view
def business_groups(request, payload=None):
    if request.method == "GET":
        return fetch_all("SELECT * FROM business_groups ORDER BY created_at ASC")
    group = payload or {}
    group_id = execute(
        "INSERT INTO business_groups (name, description, created_by) VALUES (%s, %s, %s)",
        (group.get("name"), group.get("description", ""), "admin"),
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
    return {"deleted": execute("DELETE FROM business_groups WHERE id = %s", (group_id,)) > 0}


@api_view
def business_group_stats(_request, group_id: int, payload=None):
    project_count = fetch_one("SELECT COUNT(*) AS count FROM projects WHERE business_group_id = %s", (group_id,))
    api_count = fetch_one(
        """
        SELECT COUNT(*) AS count FROM api_templates
        WHERE project_id IN (SELECT id FROM projects WHERE business_group_id = %s)
        """,
        (group_id,),
    )
    case_count = fetch_one(
        """
        SELECT COUNT(*) AS count FROM test_cases
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
        group_id = get_int((payload or {}).get("group_id"))
        if group_id:
            return fetch_all("SELECT * FROM projects WHERE business_group_id = %s ORDER BY created_at ASC", (group_id,))
        return fetch_all("SELECT * FROM projects ORDER BY created_at ASC")
    project = payload or {}
    project_id = execute(
        """
        INSERT INTO projects (business_group_id, name, description, created_by)
        VALUES (%s, %s, %s, %s)
        """,
        (project.get("group_id"), project.get("name"), project.get("description", ""), "admin"),
    )
    return {"project_id": project_id}, 201


@api_view
def project_detail(request, project_id: int, payload=None):
    if request.method == "GET":
        return fetch_one("SELECT * FROM projects WHERE id = %s", (project_id,))
    if request.method == "PUT":
        updated = execute(
            "UPDATE projects SET name = %s, description = %s WHERE id = %s",
            ((payload or {}).get("name"), (payload or {}).get("description", ""), project_id),
        )
        return {"updated": updated >= 0}
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
def api_folders(request, payload=None):
    if request.method == "GET":
        return template_service.list_folders((payload or {}).get("project_id"))
    return template_service.create_folder(payload or {}), 201


@api_view
def api_folder_detail(request, folder_id: int, payload=None):
    if request.method == "GET":
        return fetch_one("SELECT * FROM api_folders WHERE id = %s", (folder_id,))
    if request.method == "PUT":
        return template_service.update_folder(folder_id, payload or {})
    return template_service.delete_folder(folder_id)


@api_view
def api_templates(request, payload=None):
    if request.method == "GET":
        return template_service.list_templates(
            project_id=(payload or {}).get("project_id"),
            folder_id=(payload or {}).get("folder_id"),
        )
    return template_service.create_template(payload or {}), 201


@api_view
def api_template_detail(request, template_id: int, payload=None):
    if request.method == "GET":
        return template_service.get_template(template_id)
    if request.method == "PUT":
        return template_service.update_template(template_id, payload or {})
    return template_service.delete_template(template_id)


@api_view
def api_template_workspace(_request, payload=None):
    return template_service.template_workspace((payload or {}).get("project_id"))


@api_view
def api_template_debug(_request, payload=None):
    return template_service.execute_template_debug(payload or {})


@api_view
def case_folders(request, payload=None):
    if request.method == "GET":
        project_id = get_int((payload or {}).get("project_id"))
        if not project_id:
            raise ValueError("project_id 不能为空")
        return fetch_all("SELECT * FROM case_folders WHERE project_id = %s ORDER BY sort_order, created_at", (project_id,))
    folder = payload or {}
    folder_id = execute(
        """
        INSERT INTO case_folders (project_id, parent_id, name, description, sort_order)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (folder.get("project_id"), folder.get("parent_id"), folder.get("name"), folder.get("description", ""), folder.get("sort_order", 0)),
    )
    return {"folder_id": folder_id}, 201


@api_view
def case_folder_detail(request, folder_id: int, payload=None):
    if request.method == "PUT":
        folder = payload or {}
        updated = execute(
            "UPDATE case_folders SET name = %s, description = %s WHERE id = %s",
            (folder.get("name"), folder.get("description", ""), folder_id),
        )
        return {"updated": updated >= 0}
    folder_ids = [folder_id]
    queue = [folder_id]
    while queue:
        current_folder_id = queue.pop()
        children = fetch_all("SELECT id FROM case_folders WHERE parent_id = %s", (current_folder_id,))
        child_ids = [item["id"] for item in children]
        folder_ids.extend(child_ids)
        queue.extend(child_ids)
    placeholders = ", ".join(["%s"] * len(folder_ids))
    case_rows = fetch_all(f"SELECT id FROM test_cases WHERE folder_id IN ({placeholders})", tuple(folder_ids))
    for row in case_rows:
        _delete_case_with_steps(row["id"])
    execute(f"DELETE FROM case_folders WHERE id IN ({placeholders})", tuple(folder_ids))
    return {"deleted": True}


@api_view
def cases(request, payload=None):
    _ensure_case_schema_extensions()
    if request.method == "GET":
        case_id = get_int((payload or {}).get("case_id"))
        folder_id = get_int((payload or {}).get("folder_id"))
        project_id = get_int((payload or {}).get("project_id"))
        if case_id:
            return _get_case_detail(case_id)
        if folder_id:
            return _list_cases("WHERE folder_id = %s", (folder_id,))
        if project_id:
            return _list_cases("WHERE project_id = %s", (project_id,))
        return _list_cases()
    item = payload or {}
    project_id = get_int(item.get("project_id"))
    folder_id = get_int(item.get("folder_id"))
    name = _normalize_case_name(item.get("name"))
    _validate_case_folder(project_id, folder_id)
    _validate_unique_case_name(project_id, folder_id, name)
    case_id = execute(
        """
        INSERT INTO test_cases (project_id, folder_id, name, description, environment_id, global_vars, global_request_config_text, output_variables_text, enable_encryption, encrypt_url, decrypt_url, sort_order, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            project_id,
            folder_id,
            name,
            item.get("description", ""),
            item.get("environment_id"),
            _json_text(item.get("global_vars")),
            _json_text(item.get("global_request_config")),
            _empty_list_json(item.get("output_variables")),
            item.get("enable_encryption", False),
            item.get("encrypt_url", ""),
            item.get("decrypt_url", ""),
            item.get("sort_order", 0),
            "admin",
        ),
    )
    _write_case_steps(case_id, item.get("steps", []))
    return {"case_id": case_id}, 201


@api_view
def case_detail(request, case_id: int, payload=None):
    _ensure_case_schema_extensions()
    if request.method == "GET":
        return _get_case_detail(case_id)
    if request.method == "PUT":
        item = payload or {}
        current = fetch_one("SELECT * FROM test_cases WHERE id = %s", (case_id,))
        if not current:
            raise ValueError("测试用例不存在")
        project_id = get_int(item.get("project_id", current.get("project_id")))
        folder_id = get_int(item.get("folder_id", current.get("folder_id")))
        name = _normalize_case_name(item.get("name", current.get("name")))
        _validate_case_folder(project_id, folder_id)
        _validate_unique_case_name(project_id, folder_id, name, case_id)
        global_vars = item.get("global_vars", _json_value(current.get("global_vars"), {}))
        global_request_config = item.get(
            "global_request_config",
            _json_value(current.get("global_request_config_text"), {}),
        )
        output_variables = item.get(
            "output_variables",
            _json_value(current.get("output_variables_text"), []),
        )
        updated = execute(
            """
            UPDATE test_cases
            SET name = %s, description = %s, folder_id = %s, environment_id = %s, global_vars = %s, global_request_config_text = %s, output_variables_text = %s, enable_encryption = %s, encrypt_url = %s, decrypt_url = %s, sort_order = %s
            WHERE id = %s
            """,
            (
                name,
                item.get("description", current.get("description", "")),
                folder_id,
                item.get("environment_id", current.get("environment_id")),
                _json_text(global_vars),
                _json_text(global_request_config),
                _empty_list_json(output_variables),
                item.get("enable_encryption", current.get("enable_encryption", False)),
                item.get("encrypt_url", current.get("encrypt_url", "")),
                item.get("decrypt_url", current.get("decrypt_url", "")),
                item.get("sort_order", current.get("sort_order", 0)),
                case_id,
            ),
        )
        if "steps" in item:
            _write_case_steps(case_id, item.get("steps", []))
        return {"updated": updated >= 0, "case": _get_case_detail(case_id)}
    return {"deleted": _delete_case_with_steps(case_id)}


@api_view
def execute_case(_request, case_id: int, payload=None):
    _ensure_case_schema_extensions()
    case = _hydrate_case_row(fetch_one("SELECT * FROM test_cases WHERE id = %s", (case_id,)))
    if not case:
        raise ValueError("测试用例不存在")

    execution_case = dict(case)
    execution_case["steps"] = _list_case_steps(case_id)
    if payload:
        execution_case.update(
            {
                "project_id": payload.get("project_id", execution_case.get("project_id")),
                "folder_id": payload.get("folder_id", execution_case.get("folder_id")),
                "name": payload.get("name", execution_case.get("name")),
                "description": payload.get("description", execution_case.get("description", "")),
                "environment_id": payload.get("environment_id", execution_case.get("environment_id")),
                "enable_encryption": payload.get("enable_encryption", execution_case.get("enable_encryption", False)),
                "encrypt_url": payload.get("encrypt_url", execution_case.get("encrypt_url", "")),
                "decrypt_url": payload.get("decrypt_url", execution_case.get("decrypt_url", "")),
                "sort_order": payload.get("sort_order", execution_case.get("sort_order", 0)),
            }
        )
        execution_case["global_vars"] = _json_value(
            payload.get("global_vars"),
            execution_case.get("global_vars", {}),
        )
        execution_case["global_request_config"] = _json_value(
            payload.get("global_request_config"),
            execution_case.get("global_request_config", {}),
        )
        execution_case["output_variables"] = _json_value(
            payload.get("output_variables"),
            execution_case.get("output_variables", []),
        )
        if "steps" in payload:
            execution_case["steps"] = [
                _hydrate_step_row(step)
                for step in (payload.get("steps") or [])
            ]
    return execute_case_run(execution_case)


@api_view
def schedulers(request, payload=None):
    if request.method == "GET":
        project_id = get_int((payload or {}).get("project_id"))
        if project_id:
            return fetch_all("SELECT * FROM test_schedulers WHERE project_id = %s ORDER BY updated_at DESC", (project_id,))
        return fetch_all("SELECT * FROM test_schedulers ORDER BY updated_at DESC")
    item = payload or {}
    created = execute(
        """
        INSERT INTO test_schedulers (project_id, name, description, cron_expression, enabled, case_ids, notify_emails, notify_wechat, email_config, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            item.get("project_id"),
            item.get("name"),
            item.get("description", ""),
            item.get("cron_expression", ""),
            item.get("enabled", False),
            _empty_list_json(item.get("case_ids")),
            _empty_list_json(item.get("notify_emails")),
            _empty_list_json(item.get("notify_wechat")),
            _json_text(item.get("email_config")),
            "system",
        ),
    )
    return {"created": True, "scheduler_id": created}


@api_view
def scheduler_detail(request, scheduler_id: int, payload=None):
    if request.method == "GET":
        return fetch_one("SELECT * FROM test_schedulers WHERE id = %s", (scheduler_id,))
    if request.method == "PUT":
        item = payload or {}
        updated = execute(
            """
            UPDATE test_schedulers
            SET project_id = %s, name = %s, description = %s, cron_expression = %s, enabled = %s, case_ids = %s, notify_emails = %s, notify_wechat = %s, email_config = %s
            WHERE id = %s
            """,
            (
                item.get("project_id"),
                item.get("name"),
                item.get("description", ""),
                item.get("cron_expression", ""),
                item.get("enabled", False),
                _empty_list_json(item.get("case_ids")),
                _empty_list_json(item.get("notify_emails")),
                _empty_list_json(item.get("notify_wechat")),
                _json_text(item.get("email_config")),
                scheduler_id,
            ),
        )
        return {"updated": updated >= 0}
    return {"deleted": execute("DELETE FROM test_schedulers WHERE id = %s", (scheduler_id,)) > 0}


@api_view
def scheduler_status(_request, scheduler_id: int, payload=None):
    updated = execute(
        "UPDATE test_schedulers SET enabled = %s, updated_at = %s WHERE id = %s",
        (bool((payload or {}).get("enabled", False)), datetime.now(), scheduler_id),
    )
    return {"updated": updated >= 0}


@api_view
def reports(_request, payload=None):
    if str((payload or {}).get("view") or "") == "suite_groups":
        return list_report_groups(payload or {})
    if str((payload or {}).get("view") or "") == "group_records":
        return list_report_records(payload or {})
    return list_reports(payload or {})


@api_view
def report_detail(request, report_id: int, payload=None):
    if request.method == "GET":
        report = get_report_detail(report_id)
        if not report:
            raise ValueError("测试报告不存在")
        return report
    return {"deleted": delete_report(report_id)}


@api_view
def report_steps(_request, report_id: int, payload=None):
    return fetch_all("SELECT * FROM test_step_results WHERE report_id = %s ORDER BY step_order", (report_id,))


@api_view
def global_tools(request, payload=None):
    _ensure_global_tool_schema_ready()
    if request.method == "GET":
        payload = payload or {}
        tool_type = str(payload.get("tool_type") or "").strip()
        keyword = str(payload.get("keyword") or "").strip()
        business_group_id = get_int(payload.get("business_group_id"))
        project_id = get_int(payload.get("project_id"))
        visible_project_id = get_int(payload.get("visible_project_id"))
        conditions = []
        params = []
        if tool_type:
            conditions.append("gt.tool_type = %s")
            params.append(tool_type)
        if keyword:
            like_value = f"%{keyword}%"
            conditions.append("(gt.name LIKE %s OR gt.description LIKE %s)")
            params.extend([like_value, like_value])
        if visible_project_id:
            conditions.append("(gt.project_id = %s OR gt.is_shared = %s)")
            params.extend([visible_project_id, True])
        else:
            if project_id:
                conditions.append("gt.project_id = %s")
                params.append(project_id)
            elif business_group_id:
                conditions.append("p.business_group_id = %s")
                params.append(business_group_id)
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return _global_tools_select(where_sql, tuple(params))
    item = _normalise_global_tool_payload(payload or {})
    tool_id = execute(
        """
        INSERT INTO global_tools (project_id, name, tool_type, description, config, enabled, is_shared, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            item["project_id"],
            item["name"],
            item["tool_type"],
            item["description"],
            _json_text(item["config"]),
            item["enabled"],
            item["is_shared"],
            "admin",
        ),
    )
    return {"tool_id": tool_id}, 201


@api_view
def global_tool_detail(request, tool_id: int, payload=None):
    _ensure_global_tool_schema_ready()
    if request.method == "GET":
        rows = _global_tools_select("WHERE gt.id = %s", (tool_id,))
        return rows[0] if rows else {}
    if request.method == "PUT":
        item = _normalise_global_tool_payload(payload or {})
        updated = execute(
            """
            UPDATE global_tools
            SET project_id = %s,
                name = %s,
                tool_type = %s,
                description = %s,
                config = %s,
                enabled = %s,
                is_shared = %s
            WHERE id = %s
            """,
            (
                item["project_id"],
                item["name"],
                item["tool_type"],
                item["description"],
                _json_text(item["config"]),
                item["enabled"],
                item["is_shared"],
                tool_id,
            ),
        )
        return {"updated": updated >= 0}
    return {"deleted": execute("DELETE FROM global_tools WHERE id = %s", (tool_id,)) > 0}


@api_view
def global_tool_status(_request, tool_id: int, payload=None):
    _ensure_global_tool_schema_ready()
    updated = execute("UPDATE global_tools SET enabled = %s WHERE id = %s", (bool((payload or {}).get("enabled", False)), tool_id))
    return {"updated": updated >= 0}


@api_view
def variables(request, payload=None):
    _ensure_global_variable_schema_ready()
    if request.method == "GET":
        payload = payload or {}
        project_id = get_int(payload.get("project_id"))
        business_group_id = get_int(payload.get("business_group_id"))
        environment_id = get_int(payload.get("environment_id"))
        keyword = str(payload.get("keyword") or "").strip()
        conditions = []
        params = []
        if project_id:
            conditions.append("gv.project_id = %s")
            params.append(project_id)
        if business_group_id:
            conditions.append("p.business_group_id = %s")
            params.append(business_group_id)
        if environment_id:
            conditions.append(
                """
                EXISTS (
                    SELECT 1
                    FROM global_variable_environments gvs
                    WHERE gvs.variable_id = gv.id AND gvs.environment_id = %s
                )
                """
            )
            params.append(environment_id)
        if keyword:
            conditions.append("(gv.name LIKE %s OR gv.value LIKE %s)")
            fuzzy = f"%{keyword}%"
            params.extend([fuzzy, fuzzy])
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return _global_variables_select(where_sql, tuple(params))
    item = _normalise_global_variable_payload(payload or {})
    variable_id = execute(
        """
        INSERT INTO global_variables (project_id, name, value, variable_type, description, created_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            item["project_id"],
            item["name"],
            item["value"],
            item["variable_type"],
            item["description"],
            "admin",
        ),
    )
    executemany(
        """
        INSERT INTO global_variable_environments (variable_id, environment_id)
        VALUES (%s, %s)
        """,
        [(variable_id, environment_id) for environment_id in item["environment_ids"]],
    )
    return {"variable_id": variable_id}, 201


@api_view
def variable_detail(request, variable_id: int, payload=None):
    _ensure_global_variable_schema_ready()
    if request.method == "GET":
        rows = _global_variables_select("WHERE gv.id = %s", (variable_id,))
        return rows[0] if rows else {}
    if request.method == "PUT":
        item = _normalise_global_variable_payload(payload or {})
        updated = execute(
            """
            UPDATE global_variables
            SET project_id = %s, name = %s, value = %s, variable_type = %s, description = %s
            WHERE id = %s
            """,
            (
                item["project_id"],
                item["name"],
                item["value"],
                item["variable_type"],
                item["description"],
                variable_id,
            ),
        )
        execute("DELETE FROM global_variable_environments WHERE variable_id = %s", (variable_id,))
        executemany(
            """
            INSERT INTO global_variable_environments (variable_id, environment_id)
            VALUES (%s, %s)
            """,
            [(variable_id, environment_id) for environment_id in item["environment_ids"]],
        )
        return {"updated": updated >= 0}
    execute("DELETE FROM global_variable_environments WHERE variable_id = %s", (variable_id,))
    return {"deleted": execute("DELETE FROM global_variables WHERE id = %s", (variable_id,)) > 0}


