from __future__ import annotations

import dataclasses
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def load_json_file(relative_path: str) -> Any:
    path = PROJECT_ROOT / relative_path
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json_file(relative_path: str, payload: Any) -> None:
    path = PROJECT_ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def to_plain_data(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return to_plain_data(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {key: to_plain_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_plain_data(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "to_dict"):
        return to_plain_data(value.to_dict())
    if hasattr(value, "__dict__") and not isinstance(value, (str, int, float, bool)):
        return to_plain_data(vars(value))
    return value


def get_fastapi_route_catalog() -> list[dict[str, Any]]:
    return [
        {"method": "GET", "path": "/api/common/health/", "summary": "健康检查", "tags": ["common"]},
        {"method": "POST", "path": "/api/auth/login/", "summary": "登录", "tags": ["auth"]},
        {"method": "POST", "path": "/api/auth/register/", "summary": "注册", "tags": ["auth"]},
        {"method": "POST", "path": "/api/test-data/id-card/", "summary": "身份证测试数据", "tags": ["test-data"]},
        {"method": "POST", "path": "/api/test-data/business-license/", "summary": "营业执照测试数据", "tags": ["test-data"]},
        {"method": "GET", "path": "/api/interface-auto/overview/", "summary": "接口自动化总览", "tags": ["interface-auto"]},
        {"method": "GET", "path": "/api/tool-cards/overview/", "summary": "工具卡片总览", "tags": ["tool-cards"]},
        {"method": "GET", "path": "/api/data-query/config/", "summary": "查询配置", "tags": ["data-query"]},
        {"method": "POST", "path": "/api/api-tool/execute/", "summary": "接口执行", "tags": ["api-tool"]},
        {"method": "GET", "path": "/api/api-management/routes/", "summary": "平台路由目录", "tags": ["api-management"]},
    ]
