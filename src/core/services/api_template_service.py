import json
from config.database import Database
from typing import List, Dict, Any


class ApiTemplateService:
    """接口模板服务类"""

    def __init__(self):
        self.db = Database()

    def get_templates_by_project(self, project_id: int) -> List[Dict[str, Any]]:
        """根据项目获取接口模板列表"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, project_id, folder_id, name, method, url_path, 
                               headers, params, body, description, created_at, updated_at
                        FROM api_templates 
                        WHERE project_id = %s
                        ORDER BY created_at DESC
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
                               headers, params, body, description, created_at, updated_at
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
                                                 headers, params, body, description)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        processed_data['project_id'],
                        processed_data.get('folder_id'),
                        processed_data['name'],
                        processed_data['method'],
                        processed_data['url_path'],
                        processed_data.get('headers', '{}'),
                        processed_data.get('params', '{}'),
                        processed_data.get('body', '{}'),
                        processed_data.get('description', '')
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
                            params = %s, body = %s, description = %s, folder_id = %s
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
                        template_id
                    ))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新接口模板失败: {e}")
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
