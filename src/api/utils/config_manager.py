"""
配置管理器 - 管理FastAPI配置
"""

import os
import json
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """FastAPI配置管理器"""

    def __init__(self):
        self.config_file = os.path.join(os.getcwd(), "config", "api_config.json")
        self.default_config = {
            "api": {
                "title": "TestTool API",
                "version": "1.0.0",
                "description": "接口自动化平台API服务",
                "docs_url": "/docs",
                "redoc_url": "/redoc",
            },
            "server": {
                "host": "0.0.0.0",
                "reload": False,
                "workers": 1,
                "access_log": True,
            },
            "security": {
                "cors_origins": ["*"],
                "cors_methods": ["*"],
                "cors_headers": ["*"],
            },
        }
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载API配置文件失败，使用默认配置: {e}")

        return self.default_config

    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置"""
        return self.config.get("api", {})

    def get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        return self.config.get("server", {})

    def get_security_config(self) -> Dict[str, Any]:
        """获取安全配置"""
        return self.config.get("security", {})

    def save_config(self, new_config: Dict[str, Any]):
        """保存配置"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)

            # 重新加载配置
            self.config = self._load_config()
            logger.info("API配置已保存")
        except Exception as e:
            logger.error(f"保存API配置失败: {e}")
            raise
