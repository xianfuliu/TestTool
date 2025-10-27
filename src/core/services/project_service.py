from config.database import Database
from typing import List, Dict, Any


class ProjectService:
    """项目服务类"""

    def __init__(self):
        self.db = Database()

    def get_projects_by_group(self, group_id: int) -> List[Dict[str, Any]]:
        """根据业务分组获取项目列表"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, group_id, name, description, created_at, updated_at
                        FROM projects 
                        WHERE group_id = %s
                        ORDER BY created_at DESC
                    """, (group_id,))
                    return cursor.fetchall()
        except Exception as e:
            print(f"获取项目列表失败: {e}")
            return []

    def get_project_by_id(self, project_id: int) -> Dict[str, Any]:
        """根据ID获取项目"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, group_id, name, description, created_at, updated_at
                        FROM projects 
                        WHERE id = %s
                    """, (project_id,))
                    return cursor.fetchone()
        except Exception as e:
            print(f"获取项目失败: {e}")
            return {}

    def create_project(self, data: Dict[str, Any]) -> int:
        """创建项目"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO projects (group_id, name, description)
                        VALUES (%s, %s, %s)
                    """, (data['group_id'], data['name'], data['description']))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"创建项目失败: {e}")
            raise e

    def update_project(self, project_id: int, data: Dict[str, Any]) -> bool:
        """更新项目"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE projects 
                        SET name = %s, description = %s 
                        WHERE id = %s
                    """, (data['name'], data['description'], project_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新项目失败: {e}")
            raise e

    def delete_project(self, project_id: int) -> bool:
        """删除项目"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM projects WHERE id = %s", (project_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除项目失败: {e}")
            raise e

    def get_project_stats(self, project_id: int) -> Dict[str, Any]:
        """获取项目统计信息"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 接口数量
                    cursor.execute("SELECT COUNT(*) as count FROM api_templates WHERE project_id = %s", (project_id,))
                    api_count = cursor.fetchone()['count']

                    # 用例数量
                    cursor.execute("SELECT COUNT(*) as count FROM test_cases WHERE project_id = %s", (project_id,))
                    case_count = cursor.fetchone()['count']

                    return {
                        'api_count': api_count,
                        'case_count': case_count
                    }
        except Exception as e:
            print(f"获取项目统计失败: {e}")
            return {'api_count': 0, 'case_count': 0}

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """获取所有项目（包含业务分组信息）"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT p.id, p.group_id, p.name, p.description, 
                               p.created_at, p.updated_at,
                               bg.name as group_name
                        FROM projects p
                        LEFT JOIN business_groups bg ON p.group_id = bg.id
                        ORDER BY p.created_at DESC
                    """)
                    return cursor.fetchall()
        except Exception as e:
            print(f"获取所有项目失败: {e}")
            return []
