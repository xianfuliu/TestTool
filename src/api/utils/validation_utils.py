"""
公共验证工具类
用于参数空值校验等通用验证功能
"""


def is_empty_value(value) -> bool:
    """
    判断值是否为空（未传、空字符串、None、null）
    
    Args:
        value: 需要判断的值
        
    Returns:
        bool: 如果值为空返回True，否则返回False
        
    Examples:
        >>> is_empty_value(None)
        True
        >>> is_empty_value("")
        True
        >>> is_empty_value("null")
        True
        >>> is_empty_value("  ")
        True
        >>> is_empty_value("hello")
        False
        >>> is_empty_value(0)
        False
        >>> is_empty_value(False)
        False
    """
    if value is None:
        return True
    if isinstance(value, str):
        # 检查空字符串、空格、null字符串
        if value.strip() == "":
            return True
        if value.lower() == "null":
            return True
    return False


def validate_required_params(params: dict, required_fields: list) -> tuple[bool, str]:
    """
    验证必需参数是否为空
    
    Args:
        params: 参数字典
        required_fields: 必需参数字段列表
        
    Returns:
        tuple: (是否通过验证, 错误消息)
        
    Examples:
        >>> params = {"term": "12", "module_type": "70016"}
        >>> validate_required_params(params, ["term", "module_type"])
        (True, "")
        >>> validate_required_params(params, ["term", "module_type", "missing_field"])
        (False, "参数missing_field为必填参数")
    """
    for field in required_fields:
        if field not in params or is_empty_value(params[field]):
            return False, f"参数{field}为必填参数"
    return True, ""


def validate_enum_value(value, allowed_values: list, field_name: str) -> tuple[bool, str]:
    """
    验证枚举值是否在允许的范围内
    
    Args:
        value: 需要验证的值
        allowed_values: 允许的值列表
        field_name: 字段名称（用于错误消息）
        
    Returns:
        tuple: (是否通过验证, 错误消息)
        
    Examples:
        >>> validate_enum_value("70016", ["70016", "70019"], "module_type")
        (True, "")
        >>> validate_enum_value("70020", ["70016", "70019"], "module_type")
        (False, "module_type必须是70016或70019")
    """
    if value not in allowed_values:
        allowed_str = "或".join(allowed_values)
        return False, f"{field_name}必须是{allowed_str}"
    return True, ""


def sanitize_string(value: str) -> str:
    """
    清理字符串，去除前后空格，处理空值
    
    Args:
        value: 需要清理的字符串
        
    Returns:
        str: 清理后的字符串，如果为空则返回空字符串
    """
    if is_empty_value(value):
        return ""
    return str(value).strip()


def validate_numeric_range(value, min_value=None, max_value=None, field_name: str = "") -> tuple[bool, str]:
    """
    验证数值范围
    
    Args:
        value: 需要验证的数值
        min_value: 最小值（可选）
        max_value: 最大值（可选）
        field_name: 字段名称（用于错误消息）
        
    Returns:
        tuple: (是否通过验证, 错误消息)
    """
    try:
        num_value = float(value)
        
        if min_value is not None and num_value < min_value:
            return False, f"{field_name}不能小于{min_value}"
        
        if max_value is not None and num_value > max_value:
            return False, f"{field_name}不能大于{max_value}"
        
        return True, ""
    except (ValueError, TypeError):
        return False, f"{field_name}必须是有效的数值"


def validate_string_length(value: str, min_length: int = 0, max_length: int = None, field_name: str = "") -> tuple[bool, str]:
    """
    验证字符串长度
    
    Args:
        value: 需要验证的字符串
        min_length: 最小长度（默认0）
        max_length: 最大长度（可选）
        field_name: 字段名称（用于错误消息）
        
    Returns:
        tuple: (是否通过验证, 错误消息)
    """
    if is_empty_value(value):
        value = ""
    
    length = len(value)
    
    if length < min_length:
        return False, f"{field_name}长度不能小于{min_length}"
    
    if max_length is not None and length > max_length:
        return False, f"{field_name}长度不能大于{max_length}"
    
    return True, ""