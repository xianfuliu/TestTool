from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any

from test_platform.db import execute, fetch_one, md5_text


def create_verification_code(email: str) -> str:
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    execute(
        """
        UPDATE email_verification_codes
        SET used = TRUE
        WHERE email = %s AND used = FALSE
        """,
        (email,),
    )
    execute(
        """
        INSERT INTO email_verification_codes (email, verification_code, expires_at, used)
        VALUES (%s, %s, %s, %s)
        """,
        (email, code, datetime.now() + timedelta(minutes=10), False),
    )
    return code


def verify_code(email: str, code: str) -> bool:
    row = fetch_one(
        """
        SELECT id, expires_at, used
        FROM email_verification_codes
        WHERE email = %s AND verification_code = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (email, code),
    )
    if not row or row["used"] or row["expires_at"] < datetime.now():
        return False
    execute("UPDATE email_verification_codes SET used = TRUE WHERE id = %s", (row["id"],))
    return True


def create_user(username: str, password: str, email: str, business_line: str) -> int:
    return execute(
        """
        INSERT INTO users (username, password_hash, email, business_line, is_admin)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (username, md5_text(password), email, business_line, False),
    )


def get_user_by_username(username: str) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT id, username, email, business_line, is_admin, last_login_at, created_at, updated_at, password_hash
        FROM users
        WHERE username = %s
        """,
        (username,),
    )


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT id, username, email, business_line, is_admin, last_login_at, created_at, updated_at
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    )


def get_user_by_email(email: str) -> dict[str, Any] | None:
    return fetch_one("SELECT id FROM users WHERE email = %s", (email,))


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    user = get_user_by_username(username)
    if not user or user["password_hash"] != md5_text(password):
        return None
    token = secrets.token_hex(32)
    expires_at = datetime.now() + timedelta(days=7)
    execute(
        """
        INSERT INTO user_sessions (user_id, session_token, expires_at)
        VALUES (%s, %s, %s)
        """,
        (user["id"], token, expires_at),
    )
    execute("UPDATE users SET last_login_at = %s WHERE id = %s", (datetime.now(), user["id"]))
    user.pop("password_hash", None)
    return {"user": user, "session_token": token, "expires_at": expires_at}


def get_session(token: str) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT id, user_id, session_token, expires_at, created_at
        FROM user_sessions
        WHERE session_token = %s
        """,
        (token,),
    )


def delete_session(token: str) -> bool:
    return execute("DELETE FROM user_sessions WHERE session_token = %s", (token,)) > 0
