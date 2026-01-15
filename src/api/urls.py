"""
FastAPI URL路由配置 - 集成版
"""

from fastapi import APIRouter
from typing import Dict, List, Any, Callable


def create_route_config(
    method: str,
    path: str,
    controller_method: Callable,
    summary: str = "",
    tags: List[str] = None,
) -> Dict[str, Any]:
    """创建路由配置"""
    return {
        "method": method,
        "path": path,
        "controller_method": controller_method,
        "summary": summary,
        "tags": tags or [],
    }


class RouteMapper:
    """路由映射器"""

    def __init__(self, router: APIRouter):
        self.router = router

    def map_routes(self, route_configs: List[Dict[str, Any]]):
        """映射路由配置"""
        for config in route_configs:
            self._add_route(config)

    def _add_route(self, config: Dict[str, Any]):
        """添加单个路由"""
        method = config["method"]
        path = config["path"]
        controller_method = config["controller_method"]
        summary = config.get("summary", "")
        tags = config.get("tags", [])

        # 根据HTTP方法添加路由
        if method.upper() == "GET":
            self.router.get(path, summary=summary, tags=tags)(controller_method)
        elif method.upper() == "POST":
            self.router.post(path, summary=summary, tags=tags)(controller_method)
        elif method.upper() == "PUT":
            self.router.put(path, summary=summary, tags=tags)(controller_method)
        elif method.upper() == "DELETE":
            self.router.delete(path, summary=summary, tags=tags)(controller_method)
        elif method.upper() == "PATCH":
            self.router.patch(path, summary=summary, tags=tags)(controller_method)


# 导入控制器
from .controllers.data_sync_controller import DataSyncController
from .controllers.health_controller import HealthController

# 创建主路由器
api_router = APIRouter()

# 创建路由映射器
mapper = RouteMapper(api_router)

# 创建控制器实例
health_controller = HealthController()

# 路由配置 - 使用create_route_config函数
url_routes = [
    create_route_config(
        "GET", "/health", health_controller.health_check, "健康检查接口", ["健康检查"]
    ),
    create_route_config(
        "GET",
        "/health/system",
        health_controller.system_info,
        "系统信息接口",
        ["健康检查", "系统信息"],
    ),
    create_route_config(
        "GET",
        "/system/status",
        health_controller.system_status,
        "系统状态接口",
        ["健康检查", "系统状态"],
    ),
    create_route_config(
        "POST",
        "/data/data-sync",
        DataSyncController().sync_data,
        "数据同步接口",
        ["数据同步"],
    ),
]

# 映射路由
mapper.map_routes(url_routes)
