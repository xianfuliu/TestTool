import json
from config.database import Database
from typing import List, Dict, Any


class ApiTemplateService:
    """接口模板服务类"""

    def __init__(self):
        self.db = Database()
        self.database_available = self._check_database_connection()
    
    def _check_database_connection(self) -> bool:
        """检查数据库连接是否可用"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                return True
        except Exception as e:
            print(f"数据库连接检查失败: {e}")
            return False

    def get_templates_by_project(self, project_id: int) -> List[Dict[str, Any]]:
        """根据项目获取接口模板列表"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, project_id, folder_id, name, method, url_path, 
                               headers, params, body, description, sort_order, created_at, updated_at
                        FROM api_templates 
                        WHERE project_id = %s
                        ORDER BY sort_order ASC, created_at DESC
                    """, (project_id,))
                    templates = cursor.fetchall()

                    # 处理JSON字段
                    for template in templates:
                        for field in ['headers', 'params', 'body']:
                            if template.get(field):
                                template[field] = json.loads(template[field])

                    return templates
        except Exception as e:
            print(f"获取接口模板失败: {e}")
            return []

    def get_template_by_id(self, template_id: int) -> Dict[str, Any]:
        """根据ID获取接口模板"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, project_id, folder_id, name, method, url_path, 
                               headers, params, body, description, sort_order, created_at, updated_at
                        FROM api_templates 
                        WHERE id = %s
                    """, (template_id,))
                    template = cursor.fetchone()

                    if template:
                        # 处理JSON字段
                        for field in ['headers', 'params', 'body']:
                            if template.get(field):
                                template[field] = json.loads(template[field])

                    return template
        except Exception as e:
            print(f"获取接口模板失败: {e}")
            return {}

    def create_template(self, data: Dict[str, Any]) -> int:
        """创建接口模板"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 处理JSON字段
                    json_fields = ['headers', 'params', 'body']
                    processed_data = data.copy()
                    for field in json_fields:
                        if field in processed_data:
                            processed_data[field] = json.dumps(processed_data[field], ensure_ascii=False)

                    cursor.execute("""
                        INSERT INTO api_templates (project_id, folder_id, name, method, url_path, 
                                                 headers, params, body, description, sort_order)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        processed_data['project_id'],
                        processed_data.get('folder_id'),
                        processed_data['name'],
                        processed_data['method'],
                        processed_data['url_path'],
                        processed_data.get('headers', '{}'),
                        processed_data.get('params', '{}'),
                        processed_data.get('body', '{}'),
                        processed_data.get('description', ''),
                        processed_data.get('sort_order', 0)
                    ))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"创建接口模板失败: {e}")
            raise e

    def update_template(self, template_id: int, data: Dict[str, Any]) -> bool:
        """更新接口模板"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 处理JSON字段
                    json_fields = ['headers', 'params', 'body']
                    processed_data = data.copy()
                    for field in json_fields:
                        if field in processed_data:
                            processed_data[field] = json.dumps(processed_data[field], ensure_ascii=False)

                    cursor.execute("""
                        UPDATE api_templates 
                        SET name = %s, method = %s, url_path = %s, headers = %s, 
                            params = %s, body = %s, description = %s, folder_id = %s, sort_order = %s
                        WHERE id = %s
                    """, (
                        processed_data['name'],
                        processed_data['method'],
                        processed_data['url_path'],
                        processed_data.get('headers', '{}'),
                        processed_data.get('params', '{}'),
                        processed_data.get('body', '{}'),
                        processed_data.get('description', ''),
                        processed_data.get('folder_id'),
                        processed_data.get('sort_order', 0),
                        template_id
                    ))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新接口模板失败: {e}")
            raise e

    def get_templates_by_folder(self, folder_id: int) -> List[Dict[str, Any]]:
        """根据文件夹ID获取接口模板列表"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, project_id, folder_id, name, method, url_path, 
                               headers, params, body, description, sort_order, created_at, updated_at
                        FROM api_templates 
                        WHERE folder_id = %s
                        ORDER BY sort_order ASC, created_at DESC
                    """, (folder_id,))
                    templates = cursor.fetchall()

                    # 处理JSON字段
                    for template in templates:
                        for field in ['headers', 'params', 'body']:
                            if template.get(field):
                                template[field] = json.loads(template[field])

                    return templates
        except Exception as e:
            print(f"获取文件夹下的接口模板失败: {e}")
            return []

    def update_template_order(self, template_id: int, sort_order: int) -> bool:
        """更新接口模板的顺序"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE api_templates 
                        SET sort_order = %s
                        WHERE id = %s
                    """, (sort_order, template_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新接口模板顺序失败: {e}")
            raise e

    def update_template_folder(self, template_id: int, folder_id: int) -> bool:
        """更新接口模板的文件夹"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE api_templates 
                        SET folder_id = %s
                        WHERE id = %s
                    """, (folder_id, template_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新接口模板文件夹失败: {e}")
            raise e

    def delete_template(self, template_id: int) -> bool:
        """删除接口模板"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM api_templates WHERE id = %s", (template_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除接口模板失败: {e}")
            raise e

    def check_template_name_exists(self, project_id: int, folder_id: int, name: str, exclude_template_id: int = None) -> bool:
        """检查同一个目录下是否存在相同名称的接口模板
        
        Args:
            project_id: 项目ID
            folder_id: 文件夹ID
            name: 接口名称
            exclude_template_id: 要排除的模板ID（用于更新操作）
            
        Returns:
            bool: 如果存在相同名称的接口模板返回True，否则返回False
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    if exclude_template_id:
                        # 更新操作：检查除当前模板外的其他模板
                        cursor.execute("""
                            SELECT COUNT(*) as count FROM api_templates 
                            WHERE project_id = %s 
                            AND folder_id = %s 
                            AND name = %s 
                            AND id != %s
                        """, (project_id, folder_id, name, exclude_template_id))
                    else:
                        # 创建操作：检查所有模板
                        cursor.execute("""
                            SELECT COUNT(*) as count FROM api_templates 
                            WHERE project_id = %s 
                            AND folder_id = %s 
                            AND name = %s
                        """, (project_id, folder_id, name))
                    
                    result = cursor.fetchone()
                    count = result['count'] if result else 0
                    return count > 0
        except Exception as e:
            print(f"检查接口名称是否存在失败: {e}")
            return False
