from config.database import Database
from typing import List, Dict, Any


class BusinessService:
    """业务分组服务类"""

    def __init__(self):
        self.db = Database()

    def get_all_groups(self) -> List[Dict[str, Any]]:
        """获取所有业务分组"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, description, created_by, created_at, updated_at
                        FROM business_groups 
                        ORDER BY created_at DESC
                    """)
                    return cursor.fetchall()
        except Exception as e:
            print(f"获取业务分组失败: {e}")
            return []

    def get_group_by_id(self, group_id: int) -> Dict[str, Any]:
        """根据ID获取业务分组"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, description, created_by, created_at, updated_at
                        FROM business_groups 
                        WHERE id = %s
                    """, (group_id,))
                    return cursor.fetchone()
        except Exception as e:
            print(f"获取业务分组失败: {e}")
            return {}

    def create_group(self, data: Dict[str, Any]) -> int:
        """创建业务分组"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO business_groups (name, description, created_by)
                        VALUES (%s, %s, %s)
                    """, (data['name'], data['description'], 'admin'))  # 实际应该从登录用户获取
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"创建业务分组失败: {e}")
            raise e

    def update_group(self, group_id: int, data: Dict[str, Any]) -> bool:
        """更新业务分组"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE business_groups 
                        SET name = %s, description = %s 
                        WHERE id = %s
                    """, (data['name'], data['description'], group_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新业务分组失败: {e}")
            raise e

    def delete_group(self, group_id: int) -> bool:
        """删除业务分组"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 先删除关联的项目
                    cursor.execute("DELETE FROM projects WHERE group_id = %s", (group_id,))
                    # 再删除业务分组
                    cursor.execute("DELETE FROM business_groups WHERE id = %s", (group_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除业务分组失败: {e}")
            raise e

    def get_group_stats(self, group_id: int) -> Dict[str, Any]:
        """获取业务分组统计信息"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 项目数量
                    cursor.execute("SELECT COUNT(*) as count FROM projects WHERE group_id = %s", (group_id,))
                    project_count = cursor.fetchone()['count']

                    # 接口数量（通过项目关联）
                    cursor.execute("""
                        SELECT COUNT(*) as count 
                        FROM api_templates 
                        WHERE project_id IN (SELECT id FROM projects WHERE group_id = %s)
                    """, (group_id,))
                    api_count = cursor.fetchone()['count']

                    # 用例数量（通过项目关联）
                    cursor.execute("""
                        SELECT COUNT(*) as count 
                        FROM test_cases 
                        WHERE project_id IN (SELECT id FROM projects WHERE group_id = %s)
                    """, (group_id,))
                    case_count = cursor.fetchone()['count']

                    return {
                        'project_count': project_count,
                        'api_count': api_count,
                        'case_count': case_count
                    }
        except Exception as e:
            print(f"获取分组统计失败: {e}")
            return {'project_count': 0, 'api_count': 0, 'case_count': 0}
