import json
from config.database import Database
from typing import List, Dict, Any


class GlobalToolService:
    """全局工具服务类"""

    def __init__(self):
        self.db = Database()

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """获取所有全局工具"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, tool_type, description, config, enabled, 
                               created_by, created_at, updated_at
                        FROM global_tools 
                        ORDER BY created_at DESC
                    """)
                    tools = cursor.fetchall()

                    # 处理JSON字段
                    for tool in tools:
                        if tool.get('config'):
                            try:
                                tool['config'] = json.loads(tool['config'])
                            except (json.JSONDecodeError, TypeError):
                                tool['config'] = {}

                    return tools
        except Exception as e:
            print(f"获取全局工具失败: {e}")
            return []

    def get_tool_by_id(self, tool_id: int) -> Dict[str, Any]:
        """根据ID获取工具"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, tool_type, description, config, enabled, 
                               created_by, created_at, updated_at
                        FROM global_tools 
                        WHERE id = %s
                    """, (tool_id,))
                    tool = cursor.fetchone()

                    if tool and tool.get('config'):
                        try:
                            tool['config'] = json.loads(tool['config'])
                        except (json.JSONDecodeError, TypeError):
                            tool['config'] = {}

                    return tool
        except Exception as e:
            print(f"获取工具失败: {e}")
            return {}

    def get_tools_by_type(self, tool_type: str) -> List[Dict[str, Any]]:
        """根据类型获取工具"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, tool_type, description, config, enabled, 
                               created_by, created_at, updated_at
                        FROM global_tools 
                        WHERE tool_type = %s AND enabled = TRUE
                        ORDER BY created_at DESC
                    """, (tool_type,))
                    tools = cursor.fetchall()

                    # 处理JSON字段
                    for tool in tools:
                        if tool.get('config'):
                            try:
                                tool['config'] = json.loads(tool['config'])
                            except (json.JSONDecodeError, TypeError):
                                tool['config'] = {}

                    return tools
        except Exception as e:
            print(f"获取工具失败: {e}")
            return []

    def create_tool(self, data: Dict[str, Any]) -> int:
        """创建工具"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 处理JSON字段
                    config = data.get('config', {})
                    config_json = json.dumps(config, ensure_ascii=False)

                    cursor.execute("""
                        INSERT INTO global_tools (name, tool_type, description, config, enabled, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        data['name'],
                        data['tool_type'],
                        data.get('description', ''),
                        config_json,
                        data.get('enabled', True),
                        'admin'  # 实际应该从登录用户获取
                    ))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"创建工具失败: {e}")
            raise e

    def update_tool(self, tool_id: int, data: Dict[str, Any]) -> bool:
        """更新工具"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 处理JSON字段
                    config = data.get('config', {})
                    config_json = json.dumps(config, ensure_ascii=False)

                    cursor.execute("""
                        UPDATE global_tools 
                        SET name = %s, tool_type = %s, description = %s, config = %s, enabled = %s
                        WHERE id = %s
                    """, (
                        data['name'],
                        data['tool_type'],
                        data.get('description', ''),
                        config_json,
                        data.get('enabled', True),
                        tool_id
                    ))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新工具失败: {e}")
            raise e

    def delete_tool(self, tool_id: int) -> bool:
        """删除工具"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM global_tools WHERE id = %s", (tool_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除工具失败: {e}")
            raise e

    def update_tool_status(self, tool_id: int, enabled: bool) -> bool:
        """更新工具状态"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE global_tools 
                        SET enabled = %s 
                        WHERE id = %s
                    """, (enabled, tool_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新工具状态失败: {e}")
            raise e
