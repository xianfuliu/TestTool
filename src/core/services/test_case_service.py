import json
from config.database import Database
from typing import List, Dict, Any


class TestCaseService:
    """测试用例服务类"""

    def __init__(self):
        self.db = Database()

    def get_cases_by_project(self, project_id: int) -> List[Dict[str, Any]]:
        """根据项目获取测试用例列表"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, project_id, folder_id, name, description, 
                               environment_id, global_vars, created_by, created_at, updated_at
                        FROM test_cases 
                        WHERE project_id = %s
                        ORDER BY created_at DESC
                    """, (project_id,))
                    cases = cursor.fetchall()

                    # 处理JSON字段
                    for case in cases:
                        if case.get('global_vars'):
                            try:
                                case['global_vars'] = json.loads(case['global_vars'])
                            except (json.JSONDecodeError, TypeError):
                                case['global_vars'] = {}

                    return cases
        except Exception as e:
            print(f"获取测试用例失败: {e}")
            return []

    def get_case_by_id(self, case_id: int) -> Dict[str, Any]:
        """根据ID获取测试用例"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, project_id, folder_id, name, description, 
                               environment_id, global_vars, created_by, created_at, updated_at
                        FROM test_cases 
                        WHERE id = %s
                    """, (case_id,))
                    case = cursor.fetchone()

                    if case and case.get('global_vars'):
                        try:
                            case['global_vars'] = json.loads(case['global_vars'])
                        except (json.JSONDecodeError, TypeError):
                            case['global_vars'] = {}

                    return case
        except Exception as e:
            print(f"获取测试用例失败: {e}")
            return {}

    def get_case_with_steps(self, case_id: int) -> Dict[str, Any]:
        """获取测试用例及其步骤"""
        try:
            case = self.get_case_by_id(case_id)
            if not case:
                return {}

            # 获取步骤
            steps = self.get_case_steps(case_id)
            case['steps'] = steps

            return case
        except Exception as e:
            print(f"获取测试用例详情失败: {e}")
            return {}

    def get_case_steps(self, case_id: int) -> List[Dict[str, Any]]:
        """获取测试用例步骤"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT cs.*, at.name as api_name, at.method, at.url_path
                        FROM test_case_steps cs
                        LEFT JOIN api_templates at ON cs.api_template_id = at.id
                        WHERE cs.case_id = %s
                        ORDER BY cs.step_order
                    """, (case_id,))
                    steps = cursor.fetchall()

                    # 处理JSON字段
                    for step in steps:
                        json_fields = ['pre_processing', 'post_processing', 'assertions', 'variables']
                        for field in json_fields:
                            if step.get(field):
                                try:
                                    step[field] = json.loads(step[field])
                                except (json.JSONDecodeError, TypeError):
                                    step[field] = {}

                    return steps
        except Exception as e:
            print(f"获取测试用例步骤失败: {e}")
            return []

    def create_case(self, data: Dict[str, Any]) -> int:
        """创建测试用例"""
        try:
            # 检查环境ID是否存在
            environment_id = data.get('environment_id')
            if environment_id and not self._check_environment_exists(environment_id):
                raise ValueError(f"环境ID {environment_id} 不存在")

            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 处理JSON字段
                    global_vars = data.get('global_vars', {})
                    global_vars_json = json.dumps(global_vars, ensure_ascii=False)

                    cursor.execute("""
                        INSERT INTO test_cases (project_id, folder_id, name, description, 
                                              environment_id, global_vars, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        data['project_id'],
                        data.get('folder_id'),
                        data['name'],
                        data.get('description', ''),
                        environment_id,  # 可能是None
                        global_vars_json,
                        'admin'  # 实际应该从登录用户获取
                    ))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"创建测试用例失败: {e}")
            raise e

    def _check_environment_exists(self, environment_id: int) -> bool:
        """检查环境是否存在"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM environments WHERE id = %s", (environment_id,))
                    return cursor.fetchone() is not None
        except Exception as e:
            print(f"检查环境存在失败: {e}")
            return False

    def update_case(self, case_id: int, data: Dict[str, Any]) -> bool:
        """更新测试用例"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 处理JSON字段
                    global_vars = data.get('global_vars', {})
                    global_vars_json = json.dumps(global_vars, ensure_ascii=False)

                    cursor.execute("""
                        UPDATE test_cases 
                        SET name = %s, description = %s, environment_id = %s, 
                            global_vars = %s, folder_id = %s
                        WHERE id = %s
                    """, (
                        data['name'],
                        data.get('description', ''),
                        data.get('environment_id'),
                        global_vars_json,
                        data.get('folder_id'),
                        case_id
                    ))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新测试用例失败: {e}")
            raise e

    def delete_case(self, case_id: int) -> bool:
        """删除测试用例"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 先删除步骤
                    cursor.execute("DELETE FROM test_case_steps WHERE case_id = %s", (case_id,))
                    # 再删除用例
                    cursor.execute("DELETE FROM test_cases WHERE id = %s", (case_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除测试用例失败: {e}")
            raise e

    def create_case_step(self, data: Dict[str, Any]) -> int:
        """创建测试用例步骤"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 处理JSON字段
                    json_fields = ['pre_processing', 'post_processing', 'assertions', 'variables']
                    processed_data = data.copy()
                    for field in json_fields:
                        if field in processed_data:
                            processed_data[field] = json.dumps(processed_data[field], ensure_ascii=False)
                        else:
                            processed_data[field] = '{}'

                    cursor.execute("""
                        INSERT INTO test_case_steps (case_id, api_template_id, step_order, name, 
                                                   enabled, pre_processing, post_processing, assertions, variables)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        processed_data['case_id'],
                        processed_data.get('api_template_id'),
                        processed_data.get('step_order', 0),
                        processed_data.get('name', ''),
                        processed_data.get('enabled', True),
                        processed_data.get('pre_processing', '{}'),
                        processed_data.get('post_processing', '{}'),
                        processed_data.get('assertions', '{}'),
                        processed_data.get('variables', '{}')
                    ))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"创建测试用例步骤失败: {e}")
            raise e

    def update_case_step(self, step_id: int, data: Dict[str, Any]) -> bool:
        """更新测试用例步骤"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 处理JSON字段
                    json_fields = ['pre_processing', 'post_processing', 'assertions', 'variables']
                    processed_data = data.copy()
                    for field in json_fields:
                        if field in processed_data:
                            processed_data[field] = json.dumps(processed_data[field], ensure_ascii=False)
                        else:
                            processed_data[field] = '{}'

                    cursor.execute("""
                        UPDATE test_case_steps 
                        SET api_template_id = %s, step_order = %s, name = %s, enabled = %s,
                            pre_processing = %s, post_processing = %s, assertions = %s, variables = %s
                        WHERE id = %s
                    """, (
                        processed_data.get('api_template_id'),
                        processed_data.get('step_order', 0),
                        processed_data.get('name', ''),
                        processed_data.get('enabled', True),
                        processed_data.get('pre_processing', '{}'),
                        processed_data.get('post_processing', '{}'),
                        processed_data.get('assertions', '{}'),
                        processed_data.get('variables', '{}'),
                        step_id
                    ))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新测试用例步骤失败: {e}")
            raise e

    def delete_case_step(self, step_id: int) -> bool:
        """删除测试用例步骤"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM test_case_steps WHERE id = %s", (step_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除测试用例步骤失败: {e}")
            raise e

    def update_case_steps_order(self, case_id: int, step_orders: List[Dict[str, Any]]) -> bool:
        """更新测试用例步骤顺序"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    for step_order in step_orders:
                        cursor.execute("""
                            UPDATE test_case_steps 
                            SET step_order = %s 
                            WHERE id = %s AND case_id = %s
                        """, (step_order['order'], step_order['step_id'], case_id))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"更新测试用例步骤顺序失败: {e}")
            raise e
