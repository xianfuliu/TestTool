"""
CSS样式工具模块
用于生成打包环境兼容的CSS样式
"""

import os
from .resource_utils import resource_path


def get_combobox_style():
    """
    获取下拉框样式，包含正确的图标路径
    """
    # 获取combobox.png图标的正确路径
    icon_path = resource_path("src/resources/icons/combobox.png")

    # 将路径转换为文件URL格式，确保在CSS中正确使用
    # 注意：在Windows系统中，路径分隔符需要转换为正斜杠
    icon_url = icon_path.replace("\\", "/")

    # 构建CSS样式
    css_style = f"""
        QComboBox {{
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 6px 30px 6px 12px;  /* 增加左侧内边距，右侧留出下拉箭头空间 */
            background-color: white;
            min-width: 150px;
            font-size: 14px;
        }}
        QComboBox:focus {{
            border-color: #0078d4;
            outline: none;
        }}
        QComboBox:hover {{
            border-color: #adb5bd;
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 24px;
            border-left: 1px solid #ced4da;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
            background-color: #f8f9fa;
        }}
        QComboBox::down-arrow {{
            width: 12px;
            height: 12px;
            image: url({icon_url});
        }}
        QComboBox::down-arrow:hover {{
            image: url({icon_url});
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid #ced4da;
            border-radius: 4px;
            background-color: white;
            outline: none;
            margin-top: 2px;
            padding: 4px 0px;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 8px 16px;
            color: #495057;
            background-color: transparent;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: #e9ecef;
            color: #0078d4;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: #0078d4;
            color: white;
        }}
    """

    return css_style


def get_toolbar_combobox_style():
    """
    获取工具栏下拉框样式
    """
    # 获取combobox.png图标的正确路径
    icon_path = resource_path("src/resources/icons/combobox.png")
    icon_url = icon_path.replace("\\", "/")

    css_style = f"""
        QToolBar QComboBox {{
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 6px 30px 6px 8px;
            background-color: white;
            min-width: 120px;
            font-size: 13px;
        }}
        QToolBar QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 24px;
            border-left: 1px solid #ced4da;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
            background-color: #f8f9fa;
        }}
        QToolBar QComboBox::down-arrow {{
            width: 12px;
            height: 12px;
            image: url({icon_url});
        }}
        QToolBar QComboBox::down-arrow:hover {{
            image: url({icon_url});
        }}
        QToolBar QComboBox QAbstractItemView {{
            border: 1px solid #ced4da;
            border-radius: 4px;
            background-color: white;
            outline: none;
            margin-top: 2px;
            padding: 4px 0px;
        }}
        QToolBar QComboBox QAbstractItemView::item {{
            padding: 8px 12px;
            color: #495057;
            background-color: transparent;
        }}
        QToolBar QComboBox QAbstractItemView::item:hover {{
            background-color: #e9ecef;
            color: #0078d4;
        }}
        QToolBar QComboBox QAbstractItemView::item:selected {{
            background-color: #0078d4;
            color: white;
        }}
    """

    return css_style
