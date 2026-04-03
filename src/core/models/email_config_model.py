"""
邮件配置数据模型
"""

from dataclasses import dataclass, field
from typing import Optional, List
import json


@dataclass
class EmailConfig:
    """邮件服务器配置"""

    smtp_server: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    use_tls: bool = True
    sender_name: str = ""
    sender_email: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "smtp_server": self.smtp_server,
            "smtp_port": self.smtp_port,
            "smtp_username": self.smtp_username,
            "smtp_password": self.smtp_password,
            "use_tls": self.use_tls,
            "sender_name": self.sender_name,
            "sender_email": self.sender_email,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EmailConfig":
        """从字典创建实例"""
        return cls(
            smtp_server=data.get("smtp_server", ""),
            smtp_port=data.get("smtp_port", 587),
            smtp_username=data.get("smtp_username", ""),
            smtp_password=data.get("smtp_password", ""),
            use_tls=data.get("use_tls", True),
            sender_name=data.get("sender_name", ""),
            sender_email=data.get("sender_email", ""),
        )
