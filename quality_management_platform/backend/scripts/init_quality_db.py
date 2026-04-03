from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from test_platform.db import DATABASE_CONFIG, connect, ensure_database, fetch_one, md5_text
from test_platform.schema import SCHEMA_SQL


def main() -> None:
    ensure_database()
    with connect() as connection:
        with connection.cursor() as cursor:
            for sql in SCHEMA_SQL:
                cursor.execute(sql)
            connection.commit()

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

    print(f"Database ready: {DATABASE_CONFIG['database']} @ {DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}")


if __name__ == "__main__":
    main()
