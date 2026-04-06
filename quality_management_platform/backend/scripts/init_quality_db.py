from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from test_platform.db import DATABASE_CONFIG, connect, ensure_database, fetch_one, md5_text
from test_platform.schema import SCHEMA_SQL
from apps.api_tool.service import bootstrap_from_legacy_json
from apps.interface_auto.bootstrap import bootstrap_legacy_json as bootstrap_interface_auto_legacy_json
from apps.interface_auto.bootstrap import ensure_interface_auto_schema_ready


def main() -> None:
    ensure_database()
    with connect() as connection:
        with connection.cursor() as cursor:
            for sql in SCHEMA_SQL:
                cursor.execute(sql)
            connection.commit()

    ensure_interface_auto_schema_ready()

    admin_user = fetch_one("SELECT id FROM users WHERE username = %s", ("admin",))
    if not admin_user:
        with connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (username, password_hash, email, business_line, is_admin)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    ("admin", md5_text("admin123"), "admin@example.com", "质量管理", True),
                )
                connection.commit()

    bootstrap_summary = bootstrap_from_legacy_json(force=False)
    interface_auto_bootstrap_summary = bootstrap_interface_auto_legacy_json(force=False)

    print(f"Database ready: {DATABASE_CONFIG['database']} @ {DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}")
    print(
        "API tool bootstrap:",
        f"imported={bootstrap_summary.get('imported')}",
        f"products={bootstrap_summary.get('product_count')}",
    )
    print(
        "Interface auto bootstrap:",
        f"imported={interface_auto_bootstrap_summary.get('imported')}",
        f"files={interface_auto_bootstrap_summary.get('file_count')}",
        f"skipped={interface_auto_bootstrap_summary.get('skipped')}",
    )


if __name__ == "__main__":
    main()
