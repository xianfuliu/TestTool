from config.database import Database
from typing import List, Dict, Any


class ApiFolderService:
    """接口文件夹服务类"""

    def __init__(self):
        self.db = Database()

    def get_folders_by_project(self, project_id: int) -> List[Dict[str, Any]]:
        """根据项目获取文件夹列表"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, project_id, parent_id, name, description, sort_order, 
                               created_at, updated_at
                        FROM api_folders 
                        WHERE project_id = %s
                        ORDER BY sort_order, created_at
                    """,
                        (project_id,),
                    )
                    return cursor.fetchall()
        except Exception as e:
            print(f"获取文件夹列表失败: {e}")
            return []

    def create_folder(self, data: Dict[str, Any]) -> int:
        """创建文件夹"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO api_folders (project_id, parent_id, name, description, sort_order)
                        VALUES (%s, %s, %s, %s, %s)
                    """,
                        (
                            data["project_id"],
                            data.get("parent_id"),
                            data["name"],
                            data.get("description", ""),
                            data.get("sort_order", 0),
                        ),
                    )
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
                    cursor.execute(
                        """
                        UPDATE api_folders 
                        SET name = %s, description = %s 
                        WHERE id = %s
                    """,
                        (data["name"], data.get("description", ""), folder_id),
                    )
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
                    # 先删除文件夹下的接口模板
                    cursor.execute(
                        "DELETE FROM api_templates WHERE folder_id = %s", (folder_id,)
                    )
                    # 再删除文件夹本身
                    cursor.execute(
                        "DELETE FROM api_folders WHERE id = %s", (folder_id,)
                    )
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除文件夹失败: {e}")
            raise e

    def check_folder_name_exists(
        self, project_id: int, parent_id: int, name: str, exclude_folder_id: int = None
    ) -> bool:
        """检查同一级目录下文件夹名称是否已存在

        Args:
            project_id: 项目ID
            parent_id: 父文件夹ID（None表示根目录）
            name: 文件夹名称
            exclude_folder_id: 排除的文件夹ID（用于编辑时排除自身）

        Returns:
            如果名称已存在返回True，否则返回False
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 处理parent_id为None的情况
                    if parent_id is None:
                        query = """
                            SELECT COUNT(*) as count 
                            FROM api_folders 
                            WHERE project_id = %s AND parent_id IS NULL AND name = %s
                        """
                        params = [project_id, name]
                    else:
                        query = """
                            SELECT COUNT(*) as count 
                            FROM api_folders 
                            WHERE project_id = %s AND parent_id = %s AND name = %s
                        """
                        params = [project_id, parent_id, name]

                    # 添加排除条件（用于编辑时）
                    if exclude_folder_id is not None:
                        query += " AND id != %s"
                        params.append(exclude_folder_id)

                    cursor.execute(query, params)
                    result = cursor.fetchone()

                    return result["count"] > 0
        except Exception as e:
            print(f"检查文件夹名称是否存在失败: {e}")
            return False

    def get_folder_by_id(self, folder_id: int) -> Dict[str, Any]:
        """根据文件夹ID获取文件夹信息

        Args:
            folder_id: 文件夹ID

        Returns:
            文件夹信息字典，如果不存在返回None
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, project_id, parent_id, name, description, sort_order, 
                               created_at, updated_at
                        FROM api_folders 
                        WHERE id = %s
                    """,
                        (folder_id,),
                    )
                    result = cursor.fetchone()
                    return result if result else None
        except Exception as e:
            print(f"获取文件夹信息失败: {e}")
            return None
