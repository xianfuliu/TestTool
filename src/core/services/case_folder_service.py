from config.database import Database
from typing import List, Dict, Any


class CaseFolderService:
    """用例文件夹服务类"""

    def __init__(self):
        self.db = Database()

    def get_folders_by_project(self, project_id: int) -> List[Dict[str, Any]]:
        """根据项目获取文件夹列表"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, project_id, parent_id, name, description, sort_order, 
                               created_at, updated_at
                        FROM case_folders 
                        WHERE project_id = %s
                        ORDER BY sort_order, created_at
                    """, (project_id,))
                    return cursor.fetchall()
        except Exception as e:
            print(f"获取文件夹列表失败: {e}")
            return []

    def create_folder(self, data: Dict[str, Any]) -> int:
        """创建文件夹"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO case_folders (project_id, parent_id, name, description, sort_order)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        data['project_id'],
                        data.get('parent_id'),
                        data['name'],
                        data.get('description', ''),
                        data.get('sort_order', 0)
                    ))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"创建文件夹失败: {e}")
            raise e

    def update_folder(self, folder_id: int, data: Dict[str, Any]) -> bool:
        """更新文件夹"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE case_folders 
                        SET name = %s, description = %s 
                        WHERE id = %s
                    """, (
                        data['name'],
                        data.get('description', ''),
                        folder_id
                    ))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新文件夹失败: {e}")
            raise e

    def delete_folder(self, folder_id: int) -> bool:
        """删除文件夹"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 先删除文件夹下的测试用例
                    cursor.execute("DELETE FROM test_cases WHERE folder_id = %s", (folder_id,))
                    # 再删除文件夹本身
                    cursor.execute("DELETE FROM case_folders WHERE id = %s", (folder_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除文件夹失败: {e}")
            raise e
