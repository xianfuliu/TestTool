import re
import json
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from urllib.parse import parse_qs, urlencode
import jwt
import hashlib
import base64


class VariableManager:
    """变量管理器"""

    def __init__(self):
        self.global_variables: Dict[str, Any] = {}
        self.local_variables: Dict[str, Any] = {}
        self.system_variables: Dict[str, Any] = {}
        self.variable_history: List[Dict[str, Any]] = []
        self.init_system_variables()

    def init_system_variables(self):
        """初始化系统变量"""
        current_time = datetime.now()
        self.system_variables = {
            # 时间相关
            '${__timestamp}': int(current_time.timestamp()),
            '${__datetime}': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            '${__date}': current_time.strftime('%Y-%m-%d'),
            '${__time}': current_time.strftime('%H:%M:%S'),
            '${__year}': current_time.year,
            '${__month}': current_time.month,
            '${__day}': current_time.day,
            '${__hour}': current_time.hour,
            '${__minute}': current_time.minute,
            '${__second}': current_time.second,

            # 随机数相关
            '${__random_int}': lambda: random.randint(1, 100),
            '${__random_float}': lambda: round(random.uniform(1, 100), 2),
            '${__random_string}': lambda: ''.join(random.choices(string.ascii_letters, k=8)),
            '${__random_number}': lambda: ''.join(random.choices(string.digits, k=6)),
            '${__random_uuid}': lambda: self._generate_uuid(),

            # 其他系统变量
            '${__project_dir}': lambda: self._get_project_dir(),
            '${__empty}': '',
            '${__null}': None
        }

    def set_global_variables(self, variables: Dict[str, Any]):
        """设置全局变量"""
        self.global_variables.update(variables)
        self._record_variable_change('global', variables)

    def set_local_variables(self, variables: Dict[str, Any]):
        """设置局部变量"""
        self.local_variables.update(variables)
        self._record_variable_change('local', variables)

    def get_variable(self, name: str) -> Any:
        """获取变量值"""
        # 移除变量标识符
        clean_name = name.strip('${}')

        # 首先查找局部变量
        if clean_name in self.local_variables:
            value = self.local_variables[clean_name]
            return self._evaluate_dynamic_value(value)

        # 然后查找全局变量
        if clean_name in self.global_variables:
            value = self.global_variables[clean_name]
            return self._evaluate_dynamic_value(value)

        # 最后查找系统变量
        if name in self.system_variables:
            value = self.system_variables[name]
            return self._evaluate_dynamic_value(value)

        # 如果变量名本身就是一个值（没有${}包装），直接返回
        if not name.startswith('${') and not name.endswith('}'):
            return name

        return None

    def _evaluate_dynamic_value(self, value: Any) -> Any:
        """评估动态值（函数或静态值）"""
        if callable(value):
            return value()
        return value

    def replace_variables(self, text: str, additional_vars: Dict[str, Any] = None) -> str:
        """替换文本中的变量"""
        if not isinstance(text, str):
            return text

        # 合并额外变量
        all_variables = {}
        all_variables.update(self.system_variables)
        all_variables.update(self.global_variables)
        all_variables.update(self.local_variables)
        if additional_vars:
            all_variables.update(additional_vars)

        # 递归替换，直到没有变量为止
        max_iterations = 10
        for _ in range(max_iterations):
            new_text = self._replace_variables_single_pass(text, all_variables)
            if new_text == text:
                break
            text = new_text

        return text

    def _replace_variables_single_pass(self, text: str, variables: Dict[str, Any]) -> str:
        """单次变量替换"""

        def replace_match(match):
            var_name = match.group(1)

            # 处理嵌套变量
            if '${' in var_name:
                var_name = self._replace_variables_single_pass(var_name, variables)

            # 查找变量值
            if var_name in variables:
                value = variables[var_name]
                value = self._evaluate_dynamic_value(value)
                return str(value) if value is not None else ''
            else:
                # 尝试在变量字典中查找（不包含${}）
                clean_name = var_name.strip('${}')
                if clean_name in variables:
                    value = variables[clean_name]
                    value = self._evaluate_dynamic_value(value)
                    return str(value) if value is not None else ''
                else:
                    # 如果找不到变量，返回原文本（保持${var}格式）
                    return match.group(0)

        # 匹配 ${var} 格式的变量
        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, replace_match, text)

    def replace_variables_in_dict(self, data: Dict[str, Any], additional_vars: Dict[str, Any] = None) -> Dict[str, Any]:
        """替换字典中的变量"""
        if not isinstance(data, dict):
            return data

        result = {}
        for key, value in data.items():
            # 替换key中的变量
            new_key = self.replace_variables(key, additional_vars)

            # 替换value中的变量
            if isinstance(value, str):
                new_value = self.replace_variables(value, additional_vars)
            elif isinstance(value, dict):
                new_value = self.replace_variables_in_dict(value, additional_vars)
            elif isinstance(value, list):
                new_value = self.replace_variables_in_list(value, additional_vars)
            else:
                new_value = value

            result[new_key] = new_value

        return result

    def replace_variables_in_list(self, data: List[Any], additional_vars: Dict[str, Any] = None) -> List[Any]:
        """替换列表中的变量"""
        if not isinstance(data, list):
            return data

        result = []
        for item in data:
            if isinstance(item, str):
                new_item = self.replace_variables(item, additional_vars)
            elif isinstance(item, dict):
                new_item = self.replace_variables_in_dict(item, additional_vars)
            elif isinstance(item, list):
                new_item = self.replace_variables_in_list(item, additional_vars)
            else:
                new_item = item

            result.append(new_item)

        return result

    def clear_local_variables(self):
        """清空局部变量"""
        self.local_variables.clear()
        self._record_variable_change('clear_local', {})

    def clear_global_variables(self):
        """清空全局变量"""
        self.global_variables.clear()
        self._record_variable_change('clear_global', {})

    def clear_all_variables(self):
        """清空所有变量"""
        self.global_variables.clear()
        self.local_variables.clear()
        self._record_variable_change('clear_all', {})

    def get_all_variables(self) -> Dict[str, Any]:
        """获取所有变量（包括系统变量）"""
        all_vars = {}

        # 系统变量（计算动态值）
        for key, value in self.system_variables.items():
            all_vars[key] = self._evaluate_dynamic_value(value)

        # 全局变量
        for key, value in self.global_variables.items():
            all_vars[f"${{{key}}}"] = value

        # 局部变量
        for key, value in self.local_variables.items():
            all_vars[f"${{{key}}}"] = value

        return all_vars

    def extract_variables_from_text(self, text: str) -> List[str]:
        """从文本中提取变量名"""
        if not isinstance(text, str):
            return []

        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, text)
        return list(set(matches))  # 去重

    def validate_variables(self, text: str) -> tuple[bool, List[str]]:
        """验证文本中的变量是否都有定义"""
        variables = self.extract_variables_from_text(text)
        missing_vars = []

        for var in variables:
            if not self.is_variable_defined(var):
                missing_vars.append(var)

        return len(missing_vars) == 0, missing_vars

    def is_variable_defined(self, var_name: str) -> bool:
        """检查变量是否已定义"""
        clean_name = var_name.strip('${}')

        if var_name in self.system_variables:
            return True
        if clean_name in self.local_variables:
            return True
        if clean_name in self.global_variables:
            return True

        return False

    def register_custom_function(self, name: str, func: callable):
        """注册自定义函数"""
        var_name = f"${{__{name}}}"
        self.system_variables[var_name] = func

    def _record_variable_change(self, action: str, variables: Dict[str, Any]):
        """记录变量变化"""
        self.variable_history.append({
            'timestamp': datetime.now(),
            'action': action,
            'variables': variables.copy(),
            'global_snapshot': self.global_variables.copy(),
            'local_snapshot': self.local_variables.copy()
        })

        # 保持历史记录不超过100条
        if len(self.variable_history) > 100:
            self.variable_history.pop(0)

    def get_variable_history(self) -> List[Dict[str, Any]]:
        """获取变量历史记录"""
        return self.variable_history.copy()

    def _generate_uuid(self) -> str:
        """生成UUID"""
        import uuid
        return str(uuid.uuid4())

    def _get_project_dir(self) -> str:
        """获取项目目录"""
        import os
        return os.getcwd()

    # 内置函数方法
    def generate_random_string(self, length: int = 8, charset: str = None) -> str:
        """生成随机字符串"""
        if charset is None:
            charset = string.ascii_letters + string.digits

        return ''.join(random.choices(charset, k=length))

    def generate_timestamp(self, offset_seconds: int = 0) -> int:
        """生成时间戳"""
        return int((datetime.now() + timedelta(seconds=offset_seconds)).timestamp())

    def generate_date(self, offset_days: int = 0, format_str: str = '%Y-%m-%d') -> str:
        """生成日期字符串"""
        return (datetime.now() + timedelta(days=offset_days)).strftime(format_str)

    def md5_hash(self, text: str) -> str:
        """生成MD5哈希"""
        return hashlib.md5(text.encode()).hexdigest()

    def base64_encode(self, text: str) -> str:
        """Base64编码"""
        return base64.b64encode(text.encode()).decode()

    def base64_decode(self, text: str) -> str:
        """Base64解码"""
        return base64.b64decode(text.encode()).decode()

    def url_encode(self, text: str) -> str:
        """URL编码"""
        from urllib.parse import quote
        return quote(text)

    def url_decode(self, text: str) -> str:
        """URL解码"""
        from urllib.parse import unquote
        return unquote(text)

    def json_stringify(self, obj: Any) -> str:
        """JSON序列化"""
        return json.dumps(obj, ensure_ascii=False)

    def json_parse(self, text: str) -> Any:
        """JSON反序列化"""
        return json.loads(text)

    def math_operation(self, expression: str) -> Any:
        """数学运算"""
        try:
            # 安全地执行数学表达式
            allowed_chars = set('0123456789+-*/(). ')
            if all(c in allowed_chars for c in expression):
                return eval(expression)
            else:
                raise ValueError("表达式包含不安全字符")
        except Exception as e:
            raise ValueError(f"数学运算失败: {str(e)}")


class VariableParser:
    """变量解析器"""

    @staticmethod
    def parse_variable_expression(expression: str) -> Dict[str, Any]:
        """解析变量表达式

        支持格式:
        - ${var}
        - ${func(arg1, arg2)}
        - ${var|default}
        - ${var:transform}
        """
        # 简单变量
        if re.match(r'^\$\{[^()|:]+\}$', expression):
            return {
                'type': 'variable',
                'name': expression.strip('${}'),
                'default': None,
                'transform': None
            }

        # 带默认值的变量
        match = re.match(r'^\$\{([^|]+)\|([^}]+)\}$', expression)
        if match:
            return {
                'type': 'variable',
                'name': match.group(1),
                'default': match.group(2),
                'transform': None
            }

        # 带转换的变量
        match = re.match(r'^\$\{([^:]+):([^}]+)\}$', expression)
        if match:
            return {
                'type': 'variable',
                'name': match.group(1),
                'default': None,
                'transform': match.group(2)
            }

        # 函数调用
        match = re.match(r'^\$\{([^(]+)\(([^)]*)\)\}$', expression)
        if match:
            func_name = match.group(1)
            args_str = match.group(2)
            args = [arg.strip() for arg in args_str.split(',')] if args_str else []
            return {
                'type': 'function',
                'name': func_name,
                'args': args
            }

        # 无法解析
        return {
            'type': 'unknown',
            'raw': expression
        }


class VariableValidator:
    """变量验证器"""

    @staticmethod
    def validate_variable_name(name: str) -> tuple[bool, str]:
        """验证变量名格式"""
        if not name:
            return False, "变量名不能为空"

        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            return False, "变量名只能包含字母、数字和下划线，且必须以字母或下划线开头"

        if name.startswith('__'):
            return False, "变量名不能以双下划线开头（保留给系统变量）"

        return True, ""

    @staticmethod
    def validate_variable_value(value: Any) -> tuple[bool, str]:
        """验证变量值"""
        if value is None:
            return True, ""

        # 检查是否可JSON序列化
        try:
            json.dumps(value)
            return True, ""
        except (TypeError, ValueError):
            return False, "变量值必须是可JSON序列化的类型"

    @staticmethod
    def sanitize_variable_value(value: Any) -> Any:
        """清理变量值"""
        if isinstance(value, str):
            # 移除可能的危险字符
            value = value.replace('\x00', '')  # 空字符
            value = value.replace('\r', '')  # 回车
            value = value.replace('\n', '')  # 换行（在某些上下文中可能有危险）

        return value


class VariableStorage:
    """变量存储管理器"""

    def __init__(self, file_path: str = None):
        self.file_path = file_path or "variables.json"
        self.variables = {}

    def load_variables(self) -> Dict[str, Any]:
        """从文件加载变量"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.variables = json.load(f)
            return self.variables
        except FileNotFoundError:
            return {}
        except Exception as e:
            raise Exception(f"加载变量文件失败: {str(e)}")

    def save_variables(self, variables: Dict[str, Any]):
        """保存变量到文件"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(variables, f, indent=2, ensure_ascii=False)
            self.variables = variables
        except Exception as e:
            raise Exception(f"保存变量文件失败: {str(e)}")

    def export_variables(self, export_path: str, variables: Dict[str, Any]):
        """导出变量到指定文件"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(variables, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"导出变量失败: {str(e)}")

    def import_variables(self, import_path: str) -> Dict[str, Any]:
        """从文件导入变量"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_vars = json.load(f)
            return imported_vars
        except Exception as e:
            raise Exception(f"导入变量失败: {str(e)}")


# 全局变量管理器实例
_global_variable_manager = None


def get_global_variable_manager() -> VariableManager:
    """获取全局变量管理器实例"""
    global _global_variable_manager
    if _global_variable_manager is None:
        _global_variable_manager = VariableManager()
        # 初始化时从数据库加载全局变量
        try:
            from src.core.services.global_variable_service import get_global_variable_service
            service = get_global_variable_service()
            service.sync_to_variable_manager(_global_variable_manager)
        except Exception as e:
            print(f"从数据库加载全局变量失败: {e}")
    return _global_variable_manager


# 使用示例和测试
if __name__ == "__main__":
    # 创建变量管理器
    vm = VariableManager()

    # 设置变量
    vm.set_global_variables({
        'base_url': 'https://api.example.com',
        'user_id': 12345,
        'api_key': 'secret_key_123'
    })

    vm.set_local_variables({
        'token': 'temp_token_abc',
        'page': 1
    })

    # 测试变量替换
    test_cases = [
        "请求URL: ${base_url}/v1/users/${user_id}",
        "Token: ${token}",
        "页码: ${page}",
        "时间戳: ${__timestamp}",
        "随机字符串: ${__random_string}",
        "未定义变量: ${undefined_var}",
        "嵌套变量: ${base_url}/v${version}",
        "带默认值: ${undefined_var|default_value}"
    ]

    print("=== 变量替换测试 ===")
    for test_case in test_cases:
        result = vm.replace_variables(test_case)
        print(f"原文本: {test_case}")
        print(f"结果: {result}")
        print()

    # 测试字典变量替换
    test_dict = {
        "url": "${base_url}/api",
        "headers": {
            "Authorization": "Bearer ${token}",
            "X-User-Id": "${user_id}"
        },
        "body": {
            "action": "get_user",
            "params": {
                "user_id": "${user_id}",
                "page": "${page}"
            }
        }
    }

    print("=== 字典变量替换测试 ===")
    result_dict = vm.replace_variables_in_dict(test_dict)
    print("原字典:", json.dumps(test_dict, indent=2, ensure_ascii=False))
    print("结果字典:", json.dumps(result_dict, indent=2, ensure_ascii=False))

    # 测试变量验证
    print("\n=== 变量验证测试 ===")
    test_text = "URL: ${base_url}/v1/${undefined_var}/list"
    is_valid, missing = vm.validate_variables(test_text)
    print(f"文本: {test_text}")
    print(f"验证结果: {'通过' if is_valid else '失败'}")
    print(f"缺失变量: {missing}")

    # 测试自定义函数
    print("\n=== 自定义函数测试 ===")
    vm.register_custom_function('md5', lambda: vm.md5_hash('test'))
    result = vm.replace_variables("MD5哈希: ${__md5}")
    print(result)