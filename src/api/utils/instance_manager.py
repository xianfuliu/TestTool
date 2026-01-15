"""
实例管理器 - 处理多实例运行
"""

import os
import socket
import uuid
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class InstanceManager:
    """实例管理器，处理多实例运行和端口分配"""

    _instances_file = os.path.join(os.getcwd(), "config", "active_instances.json")
    _lock = threading.Lock()

    def __init__(self):
        self.instance_id = str(uuid.uuid4())
        self.port = self._find_available_port()
        self.start_time = datetime.now()
        self._register_instance()

    def _find_available_port(self, start_port: int = 8000) -> int:
        """查找可用端口"""
        port = start_port
        max_port = 9000

        # 首先检查已注册的实例，避免端口冲突
        active_instances = self._load_active_instances()
        used_ports = {instance.get("port") for instance in active_instances}

        while port <= max_port:
            if port not in used_ports and self._is_port_available(port):
                return port
            port += 1

        # 如果找不到可用端口，使用随机端口
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("", 0))
        available_port = sock.getsockname()[1]
        sock.close()
        return available_port

    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(("localhost", port))
                return result != 0
        except Exception:
            return False

    def _load_active_instances(self) -> List[Dict]:
        """加载活跃实例列表"""
        try:
            if os.path.exists(self._instances_file):
                with open(self._instances_file, "r", encoding="utf-8") as f:
                    instances = json.load(f)
                    # 清理过期的实例（超过1小时）
                    current_time = datetime.now()
                    valid_instances = []
                    for instance in instances:
                        start_time = datetime.fromisoformat(instance["start_time"])
                        if (current_time - start_time).total_seconds() < 3600:  # 1小时
                            valid_instances.append(instance)
                    return valid_instances
        except Exception as e:
            logger.warning(f"加载活跃实例列表失败: {e}")
        return []

    def _save_active_instances(self, instances: List[Dict]):
        """保存活跃实例列表"""
        try:
            os.makedirs(os.path.dirname(self._instances_file), exist_ok=True)
            with open(self._instances_file, "w", encoding="utf-8") as f:
                json.dump(instances, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存活跃实例列表失败: {e}")

    def _register_instance(self):
        """注册当前实例"""
        with self._lock:
            instances = self._load_active_instances()
            instances.append(self.get_instance_info())
            self._save_active_instances(instances)
            logger.info(f"实例 {self.instance_id} 已注册，端口: {self.port}")

    def _unregister_instance(self):
        """注销当前实例"""
        with self._lock:
            instances = self._load_active_instances()
            instances = [
                inst for inst in instances if inst["instance_id"] != self.instance_id
            ]
            self._save_active_instances(instances)
            logger.info(f"实例 {self.instance_id} 已注销")

    def get_instance_info(self) -> Dict:
        """获取当前实例信息"""
        return {
            "instance_id": self.instance_id,
            "port": self.port,
            "status": "running",
            "start_time": self.start_time.isoformat(),
            "active_connections": 0,
            "hostname": socket.gethostname(),
            "pid": os.getpid(),
        }

    def get_all_instances(self) -> List[Dict]:
        """获取所有运行中的实例"""
        return self._load_active_instances()

    def get_instance_by_id(self, instance_id: str) -> Optional[Dict]:
        """根据ID获取实例信息"""
        instances = self._load_active_instances()
        for instance in instances:
            if instance["instance_id"] == instance_id:
                return instance
        return None

    def shutdown(self):
        """安全关闭实例"""
        self._unregister_instance()
        logger.info(f"实例 {self.instance_id} 已安全关闭")
