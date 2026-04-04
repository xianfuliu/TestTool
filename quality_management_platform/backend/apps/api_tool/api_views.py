from __future__ import annotations

from apps.common.http import api_view

from .service import (
    bootstrap_from_legacy_json,
    create_product,
    delete_product,
    execute_request,
    execute_sql,
    get_product_detail,
    list_products,
    preview_request,
    run_schedule_task,
    update_product,
)


@api_view
def bootstrap(_request, payload=None):
    return bootstrap_from_legacy_json(force=bool((payload or {}).get("force", False)))


@api_view
def products(request, payload=None):
    if request.method == "GET":
        return list_products()
    return create_product(payload or {})


@api_view
def product_detail(request, product_id: int, payload=None):
    if request.method == "GET":
        return get_product_detail(product_id)
    if request.method == "PUT":
        return update_product(product_id, payload or {})
    return delete_product(product_id)


@api_view
def preview(_request, payload=None):
    payload = payload or {}
    return preview_request(
        int(payload.get("product_id") or 0),
        str(payload.get("interface_name") or "").strip(),
        payload.get("variables") or {},
        str(payload.get("request_id") or "").strip() or None,
    )


@api_view
def execute(_request, payload=None):
    payload = payload or {}
    return execute_request(
        int(payload.get("product_id") or 0),
        str(payload.get("interface_name") or "").strip(),
        payload.get("variables") or {},
        str(payload.get("request_id") or "").strip() or None,
        payload.get("request") or None,
    )


@api_view
def execute_product_sql(_request, payload=None):
    payload = payload or {}
    return execute_sql(
        int(payload.get("product_id") or 0),
        str(payload.get("sql_name") or "").strip(),
        payload.get("variables") or {},
        str(payload.get("request_id") or "").strip() or None,
    )


@api_view
def execute_schedule(_request, payload=None):
    payload = payload or {}
    return run_schedule_task(int(payload.get("schedule_row_id") or 0))
