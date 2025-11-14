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
        print(f"[DEBUG] create_case开始执行: name={data.get('name')}, steps数量={len(data.get('steps', []))}")
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
                    case_id = cursor.lastrowid
                    print(f"[DEBUG] 用例基本信息插入成功，ID: {case_id}")
                    
                    # 保存步骤数据
                    steps = data.get('steps', [])
                    print(f"[DEBUG] 开始插入步骤数据，共{len(steps)}个步骤")
                    for i, step_data in enumerate(steps):
                        print(f"[DEBUG] 处理第{i+1}个步骤: step_order={step_data.get('step_order')}, id={step_data.get('id')}")
                        step_data['case_id'] = case_id
                        self.create_case_step(step_data)
                    
                    conn.commit()
                    print(f"[DEBUG] create_case执行完成，返回ID: {case_id}")
                    return case_id
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
        print(f"[DEBUG] update_case开始执行: case_id={case_id}, name={data.get('name')}")
        
        # 检查步骤数据大小
        steps_count = len(data.get('steps', []))
        print(f"[DEBUG] 需要处理的步骤数量: {steps_count}")
        
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 更新用例基本信息
                    cursor.execute("""
                        UPDATE test_cases 
                        SET name = %s, description = %s, environment_id = %s, 
                            global_vars = %s, folder_id = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (
                        data.get('name', ''),
                        data.get('description', ''),
                        data.get('environment_id'),
                        json.dumps(data.get('global_vars', {}), ensure_ascii=False),
                        data.get('folder_id'),
                        case_id
                    ))
                    
                    # 立即提交基本信息更新
                    conn.commit()
                    print("[DEBUG] 用例基本信息更新完成")

                    # 处理步骤数据（分批处理，避免超时）
                    if steps_count > 0:
                        print(f"[DEBUG] 开始处理步骤数据，共{steps_count}个步骤")
                        
                        # 使用新的连接来删除步骤
                        with self.db.get_connection() as delete_conn:
                            with delete_conn.cursor() as delete_cursor:
                                delete_cursor.execute("DELETE FROM test_case_steps WHERE case_id = %s", (case_id,))
                                delete_conn.commit()
                                print("[DEBUG] 现有步骤删除完成")
                        
                        # 分批插入新步骤（每批5个步骤）
                        batch_size = 5
                        for batch_start in range(0, steps_count, batch_size):
                            batch_end = min(batch_start + batch_size, steps_count)
                            batch_steps = data['steps'][batch_start:batch_end]
                            
                            print(f"[DEBUG] 处理步骤批次 {batch_start+1}-{batch_end}")
                            
                            # 为每个批次创建新的数据库连接，避免长时间占用
                            with self.db.get_connection() as batch_conn:
                                with batch_conn.cursor() as batch_cursor:
                                    for i, step in enumerate(batch_steps):
                                        step_index = batch_start + i
                                        step_data = step.copy()
                                        step_data['case_id'] = case_id
                                        step_data['step_order'] = step_index + 1
                                        
                                        print(f"[DEBUG] 插入第{step_index+1}个步骤: step_order={step_data['step_order']}, id={step_data.get('id')}")
                                        
                                        # 处理JSON字段
                                        json_fields = ['pre_processing', 'post_processing', 'assertions', 'variables']
                                        for field in json_fields:
                                            if field in step_data:
                                                step_data[field] = json.dumps(step_data[field], ensure_ascii=False)
                                            else:
                                                step_data[field] = '{}'
                                        
                                        # 直接插入步骤，避免递归调用
                                        batch_cursor.execute("""
                                            INSERT INTO test_case_steps (case_id, api_template_id, step_order, name, 
                                                                       enabled, pre_processing, post_processing, assertions, variables)
                                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        """, (
                                            step_data['case_id'],
                                            step_data.get('api_template_id'),
                                            step_data.get('step_order', 0),
                                            step_data.get('name', ''),
                                            step_data.get('enabled', True),
                                            step_data.get('pre_processing', '{}'),
                                            step_data.get('post_processing', '{}'),
                                            step_data.get('assertions', '{}'),
                                            step_data.get('variables', '{}')
                                        ))
                                    
                                    # 提交当前批次
                                    batch_conn.commit()
                                    print(f"[DEBUG] 步骤批次 {batch_start+1}-{batch_end} 提交完成")
                                    
                                    # 短暂延迟，避免数据库压力
                                    import time
                                    time.sleep(0.1)

                    print("[DEBUG] update_case执行完成")
                    return True
        except Exception as e:
            print(f"更新测试用例失败: {e}")
            # 如果是超时错误，提供更详细的诊断信息
            if "timed out" in str(e) or "timeout" in str(e):
                print(f"[ERROR] 数据库操作超时，请检查：")
                print(f"[ERROR] 1. 数据库服务器是否正常运行")
                print(f"[ERROR] 2. 网络连接是否稳定")
                print(f"[ERROR] 3. 数据库配置是否正确")
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
        print(f"[DEBUG] create_case_step开始执行: case_id={data.get('case_id')}, step_order={data.get('step_order')}, id={data.get('id')}")
        
        # 检查数据大小，防止过大导致超时
        data_size = len(str(data))
        print(f"[DEBUG] 步骤数据大小: {data_size} 字符")
        if data_size > 100000:  # 超过100KB的数据可能有问题
            print(f"[WARNING] 步骤数据过大: {data_size} 字符，可能影响性能")
        
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 处理JSON字段
                    json_fields = ['pre_processing', 'post_processing', 'assertions', 'variables']
                    processed_data = data.copy()
                    
                    # 检查JSON字段大小
                    for field in json_fields:
                        if field in processed_data:
                            json_str = json.dumps(processed_data[field], ensure_ascii=False)
                            if len(json_str) > 10000:  # 单个JSON字段超过10KB
                                print(f"[WARNING] JSON字段 '{field}' 过大: {len(json_str)} 字符")
                                # 截断过大的JSON数据
                                if len(json_str) > 50000:
                                    processed_data[field] = {}
                                    json_str = '{}'
                                    print(f"[WARNING] JSON字段 '{field}' 被截断")
                            processed_data[field] = json_str
                        else:
                            processed_data[field] = '{}'

                    print(f"[DEBUG] 准备插入步骤数据，case_id={processed_data['case_id']}")
                    
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
                    
                    step_id = cursor.lastrowid
                    print(f"[DEBUG] 步骤插入成功，准备提交事务")
                    
                    # 立即提交事务，避免长时间占用连接
                    conn.commit()
                    
                    print(f"[DEBUG] create_case_step执行完成，步骤ID: {step_id}")
                    return step_id
        except Exception as e:
            print(f"创建测试用例步骤失败: {e}")
            # 如果是超时错误，提供更详细的诊断信息
            if "timed out" in str(e) or "timeout" in str(e):
                print(f"[ERROR] 数据库操作超时，请检查：")
                print(f"[ERROR] 1. 数据库服务器是否正常运行")
                print(f"[ERROR] 2. 网络连接是否稳定")
                print(f"[ERROR] 3. 数据库配置是否正确")
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

    def get_all_cases(self) -> List[Dict[str, Any]]:
        """获取所有测试用例列表"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, project_id, folder_id, name, description, 
                               environment_id, global_vars, created_by, created_at, updated_at
                        FROM test_cases 
                        ORDER BY created_at DESC
                    """)
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
            print(f"获取所有测试用例失败: {e}")
            return []

    def check_case_name_exists(self, project_id: int, name: str, folder_id: int = None, exclude_case_id: int = None) -> bool:
        """检查测试用例名称是否已存在"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    if exclude_case_id:
                        cursor.execute("""
                            SELECT id FROM test_cases 
                            WHERE project_id = %s AND name = %s AND folder_id = %s AND id != %s
                        """, (project_id, name, folder_id, exclude_case_id))
                    else:
                        cursor.execute("""
                            SELECT id FROM test_cases 
                            WHERE project_id = %s AND name = %s AND folder_id = %s
                        """, (project_id, name, folder_id))
                    
                    return cursor.fetchone() is not None
        except Exception as e:
            print(f"检查测试用例名称是否存在失败: {e}")
            return False

    def get_cases_by_folder(self, project_id: int, folder_id: int = None) -> List[Dict[str, Any]]:
        """根据文件夹获取测试用例列表"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    if folder_id is None:
                        cursor.execute("""
                            SELECT id, project_id, folder_id, name, description, 
                                   environment_id, global_vars, created_by, created_at, updated_at
                            FROM test_cases 
                            WHERE project_id = %s AND folder_id IS NULL
                            ORDER BY created_at
                        """, (project_id,))
                    else:
                        cursor.execute("""
                            SELECT id, project_id, folder_id, name, description, 
                                   environment_id, global_vars, created_by, created_at, updated_at
                            FROM test_cases 
                            WHERE project_id = %s AND folder_id = %s
                            ORDER BY created_at
                        """, (project_id, folder_id))
                    
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
            print(f"根据文件夹获取测试用例失败: {e}")
            return []

    def update_case_order(self, case_id: int, folder_id: int, order_value: int) -> bool:
        """更新测试用例的排序顺序"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE test_cases 
                        SET folder_id = %s, sort_order = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (folder_id, order_value, case_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新测试用例排序失败: {e}")
            return False
