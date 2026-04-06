from __future__ import annotations

from apps.common.http import api_view

from .toolkit import toolkit


@api_view
def meta(_request, payload=None):
    return toolkit.generator.get_meta()


@api_view
def workspace(_request, payload=None):
    config = (payload or {}).get("config") or {}
    return toolkit.generate_workspace(config)


@api_view
def user_workspace(_request, payload=None):
    config = (payload or {}).get("config") or {}
    return toolkit.generate_user_workspace(config)


@api_view
def enterprise_workspace(_request, payload=None):
    config = (payload or {}).get("config") or {}
    return toolkit.generate_enterprise_workspace(config)


@api_view
def refresh_field(_request, payload=None):
    payload = payload or {}
    field = str(payload.get("field") or "").strip()
    if not field:
        raise ValueError("刷新字段不能为空")
    return toolkit.generator.refresh_field(
        payload.get("config") or {},
        payload.get("state") or {},
        field,
    )


@api_view
def refresh_user_field(_request, payload=None):
    payload = payload or {}
    field = str(payload.get("field") or "").strip()
    if not field:
        raise ValueError("刷新字段不能为空")
    return toolkit.generator.refresh_user_field(
        payload.get("config") or {},
        payload.get("state") or {},
        field,
    )


@api_view
def refresh_enterprise_field(_request, payload=None):
    payload = payload or {}
    field = str(payload.get("field") or "").strip()
    if not field:
        raise ValueError("刷新字段不能为空")
    return toolkit.generator.refresh_enterprise_field(
        payload.get("config") or {},
        payload.get("state") or {},
        field,
    )


@api_view
def id_card(_request, payload=None):
    return toolkit.generate_user_workspace((payload or {}).get("config") or {})


@api_view
def business_license(_request, payload=None):
    return toolkit.generate_enterprise_workspace((payload or {}).get("config") or {})


@api_view
def bundle(_request, payload=None):
    return toolkit.generate_workspace((payload or {}).get("config") or {})


@api_view
def runtime_variables(_request, payload=None):
    config = (payload or {}).get("config") or {}
    return {
        "variables": toolkit.build_runtime_variables(config),
    }
