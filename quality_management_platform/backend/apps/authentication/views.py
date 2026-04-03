from __future__ import annotations

from django.conf import settings

from apps.common.http import api_view, error, ok
from apps.common.legacy import to_plain_data
from .service import (
    authenticate,
    create_user,
    create_verification_code,
    delete_session as delete_auth_session,
    get_session,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    verify_code,
)


def _extract_token(request, payload):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return payload.get("session_token") or request.COOKIES.get("test_platform_session")


def _serialize_user(user):
    if not user:
        return None
    data = to_plain_data(user)
    data.pop("password_hash", None)
    return data


@api_view
def verification_code(_request, payload=None):
    email = (payload or {}).get("email", "").strip()
    if not email:
        raise ValueError("邮箱不能为空")

    code = create_verification_code(email)
    sent = False

    response = {
        "email": email,
        "sent": sent,
        "has_email_config": False,
    }
    if settings.DEBUG and not sent:
        response["debug_code"] = code
    return response


@api_view
def login(request, payload=None):
    username = (payload or {}).get("username", "").strip()
    password = (payload or {}).get("password", "")
    remember_me = bool((payload or {}).get("remember_me", True))
    if not username or not password:
        raise ValueError("用户名和密码不能为空")

    auth_result = authenticate(username, password)
    if not auth_result:
        return error("用户名或密码错误", status=401)

    session_token = auth_result["session_token"]
    user_data = _serialize_user(auth_result["user"])
    response = ok(
        {
            "user": user_data,
            "session_token": session_token,
            "remember_me": remember_me,
        },
        message="登录成功",
    )
    response.set_cookie(
        "test_platform_session",
        session_token,
        httponly=True,
        samesite="Lax",
        max_age=7 * 24 * 3600 if remember_me else None,
    )
    return response


@api_view
def register(_request, payload=None):
    username = (payload or {}).get("username", "").strip()
    password = (payload or {}).get("password", "")
    email = (payload or {}).get("email", "").strip()
    verification_code = (payload or {}).get("verification_code", "").strip()
    business_line = (payload or {}).get("business_line", "").strip()
    if not verify_code(email, verification_code):
        return error("验证码错误或已过期", status=400)
    if get_user_by_username(username):
        return error("用户名已存在", status=400)
    if get_user_by_email(email):
        return error("邮箱已存在", status=400)
    create_user(username, password, email, business_line)
    return {"message": f"用户 {username} 注册成功"}


@api_view
def logout(request, payload=None):
    token = _extract_token(request, payload or {})
    if not token:
        raise ValueError("缺少会话令牌")
    if not delete_auth_session(token):
        return error("退出失败，会话可能已失效", status=400)
    response = ok(message="退出成功")
    response.delete_cookie("test_platform_session")
    return response


@api_view
def session(request, payload=None):
    token = _extract_token(request, payload or {})
    if not token:
        return error("未登录", status=401)
    session_obj = get_session(token)
    if not session_obj:
        return error("会话已失效", status=401)
    user = get_user_by_id(session_obj["user_id"])
    return {
        "session": to_plain_data(session_obj),
        "user": _serialize_user(user),
    }
