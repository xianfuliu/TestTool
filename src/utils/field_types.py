"""
字段类型常量定义
用于替代硬编码的中文字符串判断
"""

# 字段类型枚举
class FieldType:
    """字段类型常量"""
    
    # 显示名称（用于UI显示）
    INPUT_DISPLAY = "输入框"
    SELECT_DISPLAY = "下拉框-单选"
    MULTI_SELECT_DISPLAY = "下拉框-多选"
    RADIO_DISPLAY = "点选"
    
    # 内部类型标识（用于逻辑判断和存储）
    INPUT = "input"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    RADIO = "radio"
    
    # 类型映射关系
    DISPLAY_TO_TYPE = {
        INPUT_DISPLAY: INPUT,
        SELECT_DISPLAY: SELECT,
        MULTI_SELECT_DISPLAY: MULTI_SELECT,
        RADIO_DISPLAY: RADIO
    }
    
    TYPE_TO_DISPLAY = {
        INPUT: INPUT_DISPLAY,
        SELECT: SELECT_DISPLAY,
        MULTI_SELECT: MULTI_SELECT_DISPLAY,
        RADIO: RADIO_DISPLAY
    }
    
    # 所有可用的显示类型列表
    DISPLAY_TYPES = [INPUT_DISPLAY, SELECT_DISPLAY, MULTI_SELECT_DISPLAY, RADIO_DISPLAY]
    
    @classmethod
    def get_type_from_display(cls, display_name):
        """根据显示名称获取内部类型"""
        return cls.DISPLAY_TO_TYPE.get(display_name, cls.INPUT)
    
    @classmethod
    def get_display_from_type(cls, type_name):
        """根据内部类型获取显示名称"""
        return cls.TYPE_TO_DISPLAY.get(type_name, cls.INPUT_DISPLAY)
    
    @classmethod
    def is_select_type(cls, display_or_type):
        """判断是否为下拉框类型（单选）"""
        if display_or_type in cls.DISPLAY_TO_TYPE:
            return cls.DISPLAY_TO_TYPE[display_or_type] == cls.SELECT
        return display_or_type == cls.SELECT
    
    @classmethod
    def is_multi_select_type(cls, display_or_type):
        """判断是否为下拉框类型（多选）"""
        if display_or_type in cls.DISPLAY_TO_TYPE:
            return cls.DISPLAY_TO_TYPE[display_or_type] == cls.MULTI_SELECT
        return display_or_type == cls.MULTI_SELECT
    
    @classmethod
    def is_input_type(cls, display_or_type):
        """判断是否为输入框类型"""
        if display_or_type in cls.DISPLAY_TO_TYPE:
            return cls.DISPLAY_TO_TYPE[display_or_type] == cls.INPUT
        return display_or_type == cls.INPUT
    
    @classmethod
    def is_any_select_type(cls, display_or_type):
        """判断是否为任何下拉框类型（单选或多选）"""
        if display_or_type in cls.DISPLAY_TO_TYPE:
            return cls.DISPLAY_TO_TYPE[display_or_type] in [cls.SELECT, cls.MULTI_SELECT]
        return display_or_type in [cls.SELECT, cls.MULTI_SELECT]
    
    @classmethod
    def is_radio_type(cls, display_or_type):
        """判断是否为点选类型"""
        if display_or_type in cls.DISPLAY_TO_TYPE:
            return cls.DISPLAY_TO_TYPE[display_or_type] == cls.RADIO
        return display_or_type == cls.RADIO
    
    @classmethod
    def is_any_enum_type(cls, display_or_type):
        """判断是否为任何枚举类型（下拉框或点选）"""
        if display_or_type in cls.DISPLAY_TO_TYPE:
            return cls.DISPLAY_TO_TYPE[display_or_type] in [cls.SELECT, cls.MULTI_SELECT, cls.RADIO]
        return display_or_type in [cls.SELECT, cls.MULTI_SELECT, cls.RADIO]