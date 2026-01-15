"""
FastAPI应用主入口
"""

import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from .urls import api_router
from .utils.config_manager import ConfigManager
from .utils.instance_manager import InstanceManager


class FastAPIApp:
    """FastAPI应用类"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.instance_manager = InstanceManager()
        self.app = self._create_app()

    def _create_app(self) -> FastAPI:
        """创建FastAPI应用"""
        api_config = self.config_manager.get_api_config()
        security_config = self.config_manager.get_security_config()

        # 创建FastAPI实例
        app = FastAPI(**api_config)

        # 添加CORS中间件
        app.add_middleware(
            CORSMiddleware,
            allow_origins=security_config.get("cors_origins", ["*"]),
            allow_credentials=True,
            allow_methods=security_config.get("cors_methods", ["*"]),
            allow_headers=security_config.get("cors_headers", ["*"]),
        )

        # 添加信任主机中间件
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=security_config.get("trusted_hosts", ["*"]),
        )

        # 注册路由
        app.include_router(api_router, prefix="/api/v1")

        # 添加启动和关闭事件
        self._add_lifecycle_events(app)

        return app

    def _add_lifecycle_events(self, app: FastAPI):
        """添加生命周期事件"""

        @app.on_event("startup")
        async def startup_event():
            """应用启动事件"""
            print(f"FastAPI服务启动成功")
            print(f"实例ID: {self.instance_manager.instance_id}")
            print(f"服务地址: http://localhost:{self.instance_manager.port}")
            print(f"API文档: http://localhost:{self.instance_manager.port}/docs")

        @app.on_event("shutdown")
        async def shutdown_event():
            """应用关闭事件"""
            print("FastAPI服务正在关闭...")
            self.instance_manager.shutdown()

    def run(self):
        """运行FastAPI应用"""
        server_config = self.config_manager.get_server_config()

        uvicorn.run(
            self.app,
            host=server_config.get("host", "0.0.0.0"),
            port=self.instance_manager.port,
            reload=server_config.get("reload", False),
            workers=server_config.get("workers", 1),
            access_log=server_config.get("access_log", True),
        )


def create_app() -> FastAPI:
    """创建FastAPI应用实例（用于测试）"""
    fastapi_app = FastAPIApp()
    return fastapi_app.app


if __name__ == "__main__":
    # 直接运行时的入口
    fastapi_app = FastAPIApp()
    fastapi_app.run()
