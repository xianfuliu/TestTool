from __future__ import annotations

from django.conf import settings

from .http import api_view
from .legacy import get_fastapi_route_catalog


@api_view
def health(_request, payload=None):
    return {
        "project": "Quality Management Platform",
        "backend": "Django",
        "frontend": "Vue 3 + Element Plus",
        "repo_root": str(settings.BASE_DIR.parent),
        "modules": [
            "authentication",
            "test_data",
            "api_tool",
            "interface_auto",
            "tool_cards",
            "data_query",
            "api_management",
        ],
    }


@api_view
def legacy_routes(_request, payload=None):
    return get_fastapi_route_catalog()
