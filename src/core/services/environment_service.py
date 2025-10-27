import datetime
import json
from config.database import Database
from typing import List, Dict, Any


class EnvironmentService:
    """环境配置服务类"""

    def __init__(self):
        self.db = Database()

    def get_all_environments(self) -> List[Dict[str, Any]]:
        """获取所有环境配置"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, base_url, description, headers, variables, 
                               created_at, updated_at
                        FROM environments 
                        ORDER BY created_at DESC
                    """)
                    environments = cursor.fetchall()

                    # 处理JSON字段
                    for env in environments:
                        for field in ['headers', 'variables']:
                            if env.get(field):
                                try:
                                    env[field] = json.loads(env[field])
                                except (json.JSONDecodeError, TypeError):
                                    env[field] = {}

                    return environments
        except Exception as e:
            print(f"获取环境配置失败: {e}")
            return []

    def get_environment_by_id(self, environment_id: int) -> Dict[str, Any]:
        """根据ID获取环境配置"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, base_url, description, headers, variables, 
                               created_at, updated_at
                        FROM environments 
                        WHERE id = %s
                    """, (environment_id,))
                    environment = cursor.fetchone()

                    if environment:
                        # 处理JSON字段
                        for field in ['headers', 'variables']:
                            if environment.get(field):
                                try:
                                    environment[field] = json.loads(environment[field])
                                except (json.JSONDecodeError, TypeError):
                                    environment[field] = {}

                    return environment
        except Exception as e:
            print(f"获取环境配置失败: {e}")
            return {}
