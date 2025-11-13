"""全局变量服务"""
import json
import sys
import os
from typing import List, Dict, Any, Optional

# 添加项目根目录到Python路径，以便能够导入config模块
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from config.database import Database


class GlobalVariableService:
    """全局变量服务类"""

    def __init__(self):
        self.db = Database()

    def get_all_global_variables(self) -> List[Dict[str, Any]]:
        """获取所有全局变量"""
        return self.get_global_variables_by_project(0)

    def get_global_variables_by_project(self, project_id: int = 0) -> List[Dict[str, Any]]:
        """根据项目ID获取全局变量"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, project_id, name, value, variable_type, description, 
                               created_by, created_at, updated_at
                        FROM global_variables 
                        WHERE project_id = %s
                        ORDER BY name
                    """, (project_id,))
                    variables = cursor.fetchall()
                    
                    # 处理类型转换
                    for var in variables:
                        if var.get('value'):
                            var['value'] = self._convert_value_by_type(
                                var['value'], var.get('variable_type', 'string')
                            )
                    
                    return variables
        except Exception as e:
            print(f"获取项目 {project_id} 的全局变量失败: {e}")
            return []

    def get_global_variable_by_name(self, name: str, project_id: int = 0) -> Optional[Dict[str, Any]]:
        """根据名称和项目ID获取全局变量"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, project_id, name, value, variable_type, description, 
                               created_by, created_at, updated_at
                        FROM global_variables 
                        WHERE project_id = %s AND name = %s
                    """, (project_id, name))
                    var = cursor.fetchone()
                    
                    if var and var.get('value'):
                        var['value'] = self._convert_value_by_type(
                            var['value'], var.get('variable_type', 'string')
                        )
                    
                    return var
        except Exception as e:
            print(f"获取项目 {project_id} 的全局变量 '{name}' 失败: {e}")
            return None

    def create_global_variable(self, data: Dict[str, Any]) -> int:
        """创建全局变量"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    project_id = data.get('project_id', 0)
                    
                    # 检查变量名是否已存在（同一项目内）
                    cursor.execute("SELECT id FROM global_variables WHERE project_id = %s AND name = %s", 
                                 (project_id, data['name']))
                    if cursor.fetchone():
                        raise ValueError(f"项目 {project_id} 中全局变量 '{data['name']}' 已存在")
                    
                    # 处理值类型转换
                    value = self._convert_value_to_string(data['value'], data.get('variable_type', 'string'))
                    
                    cursor.execute("""
                        INSERT INTO global_variables (project_id, name, value, variable_type, description, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        project_id,
                        data['name'],
                        value,
                        data.get('variable_type', 'string'),
                        data.get('description', ''),
                        'admin'  # 实际应该从登录用户获取
                    ))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"创建全局变量失败: {e}")
            raise e

    def update_global_variable(self, var_id: int, data: Dict[str, Any]) -> bool:
        """更新全局变量"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    project_id = data.get('project_id', 0)
                    
                    # 检查变量名是否与其他变量冲突（同一项目内）
                    cursor.execute("SELECT id FROM global_variables WHERE project_id = %s AND name = %s AND id != %s", 
                                 (project_id, data['name'], var_id))
                    if cursor.fetchone():
                        raise ValueError(f"项目 {project_id} 中全局变量 '{data['name']}' 已存在")
                    
                    # 处理值类型转换
                    value = self._convert_value_to_string(data['value'], data.get('variable_type', 'string'))
                    
                    cursor.execute("""
                        UPDATE global_variables 
                        SET project_id = %s, name = %s, value = %s, variable_type = %s, description = %s
                        WHERE id = %s
                    """, (
                        project_id,
                        data['name'],
                        value,
                        data.get('variable_type', 'string'),
                        data.get('description', ''),
                        var_id
                    ))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新全局变量失败: {e}")
            raise e

    def delete_global_variable(self, var_id: int) -> bool:
        """删除全局变量"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM global_variables WHERE id = %s", (var_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除全局变量失败: {e}")
            raise e

    def delete_global_variable_by_name(self, name: str, project_id: int = 0) -> bool:
        """根据名称和项目ID删除全局变量"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM global_variables WHERE project_id = %s AND name = %s", 
                                 (project_id, name))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除项目 {project_id} 的全局变量 '{name}' 失败: {e}")
            raise e

    def _convert_value_by_type(self, value: str, var_type: str) -> Any:
        """根据类型转换值"""
        if var_type == 'number':
            try:
                return float(value) if '.' in value else int(value)
            except ValueError:
                return value
        elif var_type == 'boolean':
            return value.lower() in ('true', '1', 'yes', 'on')
        elif var_type == 'json':
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        else:  # string
            return value

    def _convert_value_to_string(self, value: Any, var_type: str) -> str:
        """将值转换为字符串存储"""
        if var_type == 'json':
            return json.dumps(value, ensure_ascii=False)
        else:
            return str(value)

    def sync_to_variable_manager(self, variable_manager, project_id: int = 0) -> bool:
        """将数据库中指定项目的全局变量同步到变量管理器"""
        try:
            global_vars = self.get_global_variables_by_project(project_id)
            var_dict = {}
            
            for var in global_vars:
                var_dict[var['name']] = var['value']
            
            variable_manager.set_global_variables(var_dict)
            return True
        except Exception as e:
            print(f"同步项目 {project_id} 的全局变量到变量管理器失败: {e}")
            return False

    def sync_from_variable_manager(self, variable_manager, project_id: int = 0) -> bool:
        """将变量管理器中的全局变量同步到指定项目的数据库"""
        try:
            # 获取当前内存中的全局变量
            memory_vars = variable_manager.global_variables
            
            # 获取数据库中指定项目的全局变量
            db_vars = self.get_global_variables_by_project(project_id)
            db_var_names = {var['name'] for var in db_vars}
            
            # 同步新增和更新的变量
            for name, value in memory_vars.items():
                if name in db_var_names:
                    # 更新现有变量
                    var_id = next(var['id'] for var in db_vars if var['name'] == name)
                    self.update_global_variable(var_id, {
                        'project_id': project_id,
                        'name': name,
                        'value': value,
                        'variable_type': self._detect_variable_type(value)
                    })
                else:
                    # 创建新变量
                    self.create_global_variable({
                        'project_id': project_id,
                        'name': name,
                        'value': value,
                        'variable_type': self._detect_variable_type(value)
                    })
            
            # 同步删除的变量
            memory_var_names = set(memory_vars.keys())
            for var in db_vars:
                if var['name'] not in memory_var_names:
                    self.delete_global_variable(var['id'])
            
            return True
        except Exception as e:
            print(f"从变量管理器同步项目 {project_id} 的全局变量失败: {e}")
            return False

    def _detect_variable_type(self, value: Any) -> str:
        """检测变量类型"""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, (int, float)):
            return 'number'
        elif isinstance(value, (dict, list)):
            return 'json'
        else:
            return 'string'


# 全局服务实例
_global_variable_service = None


def get_global_variable_service() -> GlobalVariableService:
    """获取全局变量服务实例"""
    global _global_variable_service
    if _global_variable_service is None:
        _global_variable_service = GlobalVariableService()
    return _global_variable_service