from __future__ import annotations

import json
import traceback
from functools import wraps
from typing import Any, Callable

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .legacy import to_plain_data


def ok(data: Any = None, message: str = "ok", status: int = 200) -> JsonResponse:
    return JsonResponse(
        {
            "success": True,
            "message": message,
            "data": to_plain_data(data),
        },
        status=status,
        json_dumps_params={"ensure_ascii": False},
    )


def error(message: str, status: int = 400, details: Any = None) -> JsonResponse:
    payload: dict[str, Any] = {
        "success": False,
        "message": message,
    }
    if details is not None:
        payload["details"] = to_plain_data(details)
    return JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})


def parse_payload(request: HttpRequest) -> dict[str, Any]:
    if request.method in {"GET", "DELETE"}:
        return request.GET.dict()
    if not request.body:
        return {}
    if "application/json" in (request.content_type or ""):
        return json.loads(request.body.decode("utf-8"))
    return request.POST.dict()


def get_int(value: Any, default: int | None = None) -> int | None:
    if value in (None, ""):
        return default
    return int(value)


def api_view(func: Callable[..., Any]) -> Callable[..., JsonResponse]:
    @csrf_exempt
    @wraps(func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        if request.method == "OPTIONS":
            return ok()
        try:
            payload = parse_payload(request)
            result = func(request, *args, payload=payload, **kwargs)
            if isinstance(result, JsonResponse):
                return result
            if isinstance(result, tuple):
                data, status = result
                return ok(data=data, status=status)
            return ok(result)
        except ValueError as exc:
            return error(str(exc), status=400)
        except Exception as exc:  # pragma: no cover - defensive adapter
            return error(
                str(exc),
                status=500,
                details={"traceback": traceback.format_exc()},
            )

    return wrapper
