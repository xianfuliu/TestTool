"""
健康检查控制器
"""

from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import psutil
import platform
import time


class HealthResponse(BaseModel):
    """健康检查响应模型"""

    status: str
    message: str
    timestamp: str


class SystemInfoResponse(BaseModel):
    """系统信息响应模型"""

    status: str
    system_info: Dict[str, Any]
    timestamp: str


class SystemStatusResponse(BaseModel):
    """系统状态响应模型"""

    status: str
    system_status: Dict[str, Any]
    timestamp: str


class HealthController:
    """健康检查控制器"""

    def __init__(self):
        self.start_time = time.time()

    async def health_check(self) -> HealthResponse:
        """基础健康检查接口"""
        return HealthResponse(
            status="healthy",
            message="服务运行正常",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

    async def system_info(self) -> SystemInfoResponse:
        """系统信息接口"""
        try:
            system_info = {
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "uptime": round(time.time() - self.start_time, 2),
            }

            return SystemInfoResponse(
                status="success",
                system_info=system_info,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")

    async def system_status(self) -> SystemStatusResponse:
        """系统状态接口"""
        try:
            # 获取CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # 获取内存信息
            memory = psutil.virtual_memory()

            # 获取磁盘使用情况
            disk = psutil.disk_usage("/")

            system_status = {
                "cpu_usage_percent": cpu_percent,
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "memory_usage_percent": memory.percent,
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_used_gb": round(disk.used / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "disk_usage_percent": round((disk.used / disk.total) * 100, 2),
                "uptime": round(time.time() - self.start_time, 2),
            }

            return SystemStatusResponse(
                status="success",
                system_status=system_status,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")
