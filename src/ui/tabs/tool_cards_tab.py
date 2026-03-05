from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QScrollArea,
    QSplitter,
    QPushButton,
    QLabel,
    QFrame,
    QMenu,
    QAction,
    QMessageBox,
    QTreeWidget,
    QTreeWidgetItem,
    QLineEdit,
    QInputDialog,
    QDialog,
    QComboBox,
    QRadioButton,
    QButtonGroup,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QIcon
import json
import os
import requests
import re
import sys
from src.ui.widgets.toast_tips import Toast
from src.ui.dialogs.tool_cards_config_dialog import ToolCardsConfigDialog
from src.utils.sql_worker import SQLWorker
from src.utils.database_config_manager import DatabaseConfigManager
from src.core.services.tool_cards_service import ToolCardsService
from src.utils.css_utils import get_combobox_style, get_card_combobox_style, get_card_multiselect_combobox_style
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelComboBox
from src.utils.field_types import FieldType
from src.ui.widgets.multi_select_combo import MultiSelectComboBox


class ToolCardWidget(QFrame):
    """单个卡片控件"""

    def __init__(self, card_data, parent=None):
        super().__init__(parent)
        self.card_data = card_data
        self.parent_tab = parent
        self.init_ui()

    def init_ui(self):
        # 设置固定宽度和高度，增加卡片尺寸
        self.setFixedSize(420, 350)  # 增加卡片宽度和高度
        
        self.setStyleSheet(
            """
            QFrame {
                background-color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 0px;
            }
            QFrame:hover {
                background-color: #f8fafc;
            }
        """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 卡片头部 - 紧凑设计，标题和类型在同一行
        header = QWidget()
        header.setStyleSheet(
            """
            QWidget {
                background-color: #adb5bd;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 6px 8px;
                min-height: 32px;
            }
        """
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        # 卡片标题
        title_label = QLabel(self.card_data.get('name', '未命名卡片'))
        title_label.setStyleSheet(
            """
            QLabel {
                color: #000000;
                font-weight: 600;
                font-size: 14px;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
        """
        )
        
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 操作按钮区域 - 编辑、复制、删除
        self.edit_btn = QPushButton()
        self.edit_btn.setIcon(self.parent_tab.get_icon("edit_card.png"))
        self.edit_btn.setIconSize(QSize(14, 14))
        self.edit_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 3px;
                padding: 2px;
                outline: none;
                min-width: 22px;
                min-height: 22px;
            }
            QPushButton:hover {
                background: #ced4da;
            }
            QPushButton:pressed {
                background: #adb5bd;
            }
        """
        )
        self.edit_btn.setCursor(Qt.PointingHandCursor)
        self.edit_btn.clicked.connect(lambda: self.parent_tab.edit_card(self.card_data))

        self.copy_btn = QPushButton()
        self.copy_btn.setIcon(self.parent_tab.get_icon("copy.png"))
        self.copy_btn.setIconSize(QSize(14, 14))
        self.copy_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 3px;
                padding: 2px;
                outline: none;
                min-width: 22px;
                min-height: 22px;
            }
            QPushButton:hover {
                background: #ced4da;
            }
            QPushButton:pressed {
                background: #adb5bd;
            }
        """
        )
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.clicked.connect(lambda: self.parent_tab.copy_card(self.card_data))

        self.delete_btn = QPushButton()
        self.delete_btn.setIcon(self.parent_tab.get_icon("delete.png"))
        self.delete_btn.setIconSize(QSize(14, 14))
        self.delete_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 3px;
                padding: 2px;
                outline: none;
                min-width: 22px;
                min-height: 22px;
            }
            QPushButton:hover {
                background: #ced4da;
            }
            QPushButton:pressed {
                background: #adb5bd;
            }
        """
        )
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.clicked.connect(lambda: self.parent_tab.delete_card(self.card_data))

        header_layout.addWidget(self.edit_btn)
        header_layout.addWidget(self.copy_btn)
        header_layout.addWidget(self.delete_btn)

        # 卡片主体 - 紧凑滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(180)  # 调整最小高度以适应新尺寸
        scroll_area.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: #fafbfc;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                margin: 0px;
                padding: 0px;
            }
            QScrollArea::viewport {
                border: none;
                margin: 0px;
                padding: 0px;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #fafbfc;
                margin: 0px;
                padding: 0px;
            }
            QScrollBar:vertical {
                background-color: #f8fafc;
                width: 6px;
                border-radius: 3px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #cbd5e1;
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #94a3b8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """
        )
        
        # 内容容器
        content_widget = QWidget()
        content_widget.setStyleSheet(
            """
            QWidget {
                background-color: #fafbfc;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
        """
        )
        body_layout = QVBoxLayout(content_widget)
        body_layout.setContentsMargins(12, 8, 12, 8)  # 紧凑间距
        body_layout.setSpacing(6)  # 紧凑间距
        body_layout.setAlignment(Qt.AlignTop)  # 设置顶部对齐，避免字段隐藏时间距拉伸

        # 根据卡片类型生成输入字段
        self.generate_input_fields(body_layout)

        body_layout.addStretch()

        # 执行按钮 - 直接在内容布局中右对齐
        execute_btn_layout = QHBoxLayout()
        execute_btn_layout.setContentsMargins(0, 0, 0, 0)
        execute_btn_layout.setSpacing(0)
        execute_btn_layout.addStretch()
        
        execute_btn = QPushButton("执行")
        execute_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #48bb78;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                min-width: 50px;
                height: 24px;
                outline: none;
            }
            QPushButton:hover {
                background-color: #38a169;
            }
            QPushButton:pressed {
                background-color: #2f855a;
            }
            QPushButton:focus {
                outline: none;
                border: none;
            }
        """
        )
        execute_btn.setCursor(Qt.PointingHandCursor)
        execute_btn.clicked.connect(self.execute_card)
        
        execute_btn_layout.addWidget(execute_btn)
        body_layout.addLayout(execute_btn_layout)

        scroll_area.setWidget(content_widget)
        layout.addWidget(header)
        layout.addWidget(scroll_area)

    def generate_input_fields(self, body_layout):
        """根据卡片类型生成输入字段"""
        print(f"[DEBUG] generate_input_fields 方法被调用！卡片名称: {self.card_data.get('name', '未知')}")
        print(f"[DEBUG] 卡片数据: {self.card_data}")
        
        config = self.card_data.get("config", {})
        mappings = self.card_data.get("mappings", {})
        
        print(f"[DEBUG] 映射配置: {mappings}")
        
        if not mappings:
            # 如果没有映射配置，显示默认信息
            no_mapping_label = QLabel("暂无输入字段配置")
            no_mapping_label.setStyleSheet("QLabel { color: #a0aec0; font-size: 11px; font-style: italic; margin-top: 8px; }")
            body_layout.addWidget(no_mapping_label)
            print("[DEBUG] 没有映射配置，显示默认信息")
            return
        
        # 创建输入字段的滚动区域 - 现代化设计
        input_scroll_area = QScrollArea()
        input_scroll_area.setWidgetResizable(True)
        input_scroll_area.setMaximumHeight(280)  # 增加高度以提供更多显示空间
        input_scroll_area.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f8fafc;
                width: 4px;
                border-radius: 2px;
                margin: 1px;
            }
            QScrollBar::handle:vertical {
                background-color: #cbd5e1;
                border-radius: 2px;
                min-height: 25px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #94a3b8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """
        )
        
        # 输入字段容器
        input_widget = QWidget()
        input_widget.setStyleSheet(
            """
            QWidget {
                background-color: white;
                border: none;
                border-radius: 0px;
                padding: 0px;
            }
            """
        )
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(8, 8, 8, 8)  # 增加内边距
        input_layout.setSpacing(12)  # 增加行间距
        input_layout.setAlignment(Qt.AlignTop)  # 设置顶部对齐，避免字段隐藏时间距拉伸
        
        # 初始化字段依赖关系跟踪
        self.field_dependencies = {}
        
        # 根据卡片类型生成不同的输入字段
        card_type = self.card_data.get("type", "sql")
        
        if card_type == "sql":
            self.generate_sql_input_fields(input_layout, config, mappings)
        elif card_type == "http":
            self.generate_http_input_fields(input_layout, config, mappings)
        elif card_type == "python":
            self.generate_python_input_fields(input_layout, config, mappings)
        else:
            # 默认处理
            self.generate_default_input_fields(input_layout, mappings)
        
        input_scroll_area.setWidget(input_widget)
        body_layout.addWidget(input_scroll_area)
        
        # 设置所有字段的依赖监听器
        self.setup_all_field_dependencies()

    def generate_sql_input_fields(self, input_layout, config, mappings):
        """生成SQL卡片的输入字段"""
        # 直接生成输入字段，不显示任何标题
        self.generate_mapping_input_fields(input_layout, mappings, "")

    def generate_http_input_fields(self, input_layout, config, mappings):
        """生成HTTP卡片的输入字段"""
        # 直接生成输入字段，不显示任何标题
        self.generate_mapping_input_fields(input_layout, mappings, "")

    def generate_python_input_fields(self, input_layout, config, mappings):
        """生成Python卡片的输入字段"""
        # 直接生成输入字段，不显示任何标题
        self.generate_mapping_input_fields(input_layout, mappings, "")

    def generate_default_input_fields(self, input_layout, mappings):
        """生成默认输入字段"""
        self.generate_mapping_input_fields(input_layout, mappings, "")

    def generate_mapping_input_fields(self, input_layout, mappings, section_title):
        """根据映射配置生成输入字段"""
        if not mappings:
            return
        
        # 按顺序字段排序参数映射
        sorted_mappings = sorted(
            mappings.items(),
            key=lambda x: x[1].get("order", 0) if isinstance(x[1], dict) else 0
        )
        
        # 首先生成所有字段
        field_widgets = {}
        for field_name, field_config in sorted_mappings:
            field_widget = self.generate_single_input_field(input_layout, field_name, field_config)
            field_widgets[field_name] = field_widget
        
        # 然后设置所有关联字段的监听器
        for field_name, field_config in sorted_mappings:
            if isinstance(field_config, dict):
                association_enabled = field_config.get("association_enabled", False)
                if association_enabled:
                    association_field = field_config.get("association_field", "")
                    association_value = field_config.get("association_value", "")
                    if association_field and field_name in field_widgets:
                        print(f"[DEBUG] 设置关联关系: 字段 '{field_name}' -> 关联字段 '{association_field}' 值='{association_value}'")
                        
                        # 记录字段依赖关系
                        if association_field not in self.field_dependencies:
                            self.field_dependencies[association_field] = []
                        self.field_dependencies[association_field].append({
                            "dependent_field": field_name,
                            "expected_value": association_value,
                            "widget": field_widgets[field_name]
                        })
                        
                        print(f"[DEBUG] 已记录依赖关系: {association_field} -> {field_name} (期望值: {association_value})")
                        # 为关联字段设置直接的切换处理
                        self._setup_direct_field_handler(association_field)
                        
                        # 初始检查关联条件
                        print(f"[DEBUG] 开始初始关联检查: 字段 '{field_name}' 关联字段 '{association_field}' 期望值='{association_value}'")
                        
                        # 直接使用数据库配置中的默认值，而不是实时获取字段值
                        current_association_value = self._get_default_field_value(association_field, sorted_mappings)
                        
                        # 使用修复后的比较逻辑
                        current_str = str(current_association_value) if current_association_value is not None else ""
                        assoc_str = str(association_value) if association_value is not None else ""
                        
                        # 清理字符串：去除前后空格
                        current_str = current_str.strip()
                        assoc_str = assoc_str.strip()
                        
                        should_show = current_str == assoc_str
                        
                        # 额外检查：如果期望值是数字2，当前值是字符串"2"，也应该显示
                        if not should_show and association_value is not None and current_association_value is not None:
                            try:
                                # 尝试将值转换为数字进行比较
                                current_num = float(current_str) if current_str else None
                                assoc_num = float(assoc_str) if assoc_str else None
                                if current_num is not None and assoc_num is not None:
                                    should_show = current_num == assoc_num
                                    print(f"[DEBUG] 数字比较结果: {current_num} == {assoc_num} -> {should_show}")
                            except (ValueError, TypeError):
                                # 转换失败，保持原比较结果
                                print(f"[DEBUG] 数字转换失败: current_str='{current_str}', assoc_str='{assoc_str}'")
                                pass
                        
                        # 调试输出比较详情
                        print(f"[DEBUG] 初始比较详情: current_str='{current_str}'({type(current_str)}), assoc_str='{assoc_str}'({type(assoc_str)}), should_show={should_show}")
                        
                        field_widgets[field_name].setVisible(should_show)
                        print(f"[DEBUG] 初始关联检查完成: 字段 '{field_name}' 关联字段 '{association_field}' 当前值='{current_association_value}'({type(current_association_value)}), 期望值='{association_value}'({type(association_value)}), 显示={should_show}")

    def generate_single_input_field(self, input_layout, field_name, field_config):
        """生成单个输入字段"""
        # 处理新旧格式兼容
        if isinstance(field_config, str):
            # 旧格式：字符串格式，如"哈哥-下拉框，枚举aaa-男,bbb-女"
            config_parts = str(field_config).split('-')
            display_name = config_parts[0] if len(config_parts) > 0 else field_name
            # 兼容旧格式：如果包含"下拉框"则认为是下拉框类型
            control_type = FieldType.SELECT_DISPLAY if "下拉框" in field_config else FieldType.INPUT_DISPLAY
            required = False  # 旧格式不支持必填
            association_enabled = False  # 旧格式不支持关联
        else:
            # 新格式：结构化JSON对象
            display_name = field_config.get("display_name", field_name)
            control_type = FieldType.get_display_from_type(field_config.get("type", FieldType.INPUT))
            required = field_config.get("required", False)
            association_enabled = field_config.get("association_enabled", False)
            
            # 调试输出：检查必填字段数据
            print(f"[DEBUG] 字段 '{field_name}': 必填={required}, 关联={association_enabled}, 显示名='{display_name}'")
        
        # 创建字段容器 - 现代化设计
        field_widget = QWidget()
        field_layout = QHBoxLayout(field_widget)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(8)  # 现代化间距
        
        # 字段标签（根据是否必填设置不同样式）
        field_label = QLabel()
        if required:
            # 必填参数：红色星号
            field_label.setText(f"<span style='color: #e53e3e;'>*</span>{display_name}:")
            field_label.setStyleSheet("QLabel { color: #2d3748; font-size: 14px; font-weight: 500; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; min-width: 80px; border: none; background: transparent; }")
        else:
            # 非必填参数：普通样式
            field_label.setText(f"{display_name}:")
            field_label.setStyleSheet("QLabel { color: #4a5568; font-size: 14px; font-weight: 500; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; min-width: 80px; border: none; background: transparent; }")
        field_layout.addWidget(field_label)
        
        # 根据控件类型生成输入控件
        if FieldType.is_select_type(control_type):
            # 单选下拉框
            combo_box = NoWheelComboBox()
            # 设置字段标识符
            combo_box.setProperty("field_name", field_name)
            
            # 为下拉框直接添加切换事件处理
            def on_combo_index_changed(index):
                current_value = combo_box.currentData() if combo_box.currentData() is not None else combo_box.currentText()
                print(f"[DEBUG] 下拉框 '{field_name}' 切换为: {current_value}")
                
                # 直接校验该字段是否被其他字段关联
                if field_name in self.field_dependencies:
                    print(f"[DEBUG] 字段 '{field_name}' 被其他字段关联，开始校验")
                    dependencies = self.field_dependencies[field_name]
                    for dependency in dependencies:
                        dependent_field = dependency["dependent_field"]
                        expected_value = dependency["expected_value"]
                        dependent_widget = dependency["widget"]
                        
                        # 直接比较逻辑
                        current_str = str(current_value) if current_value is not None else ""
                        expected_str = str(expected_value) if expected_value is not None else ""
                        
                        # 清理字符串：去除前后空格
                        current_str = current_str.strip()
                        expected_str = expected_str.strip()
                        
                        should_show = current_str == expected_str
                        
                        # 额外检查：如果期望值是数字2，当前值是字符串"2"，也应该显示
                        if not should_show and expected_value is not None and current_value is not None:
                            try:
                                # 尝试将值转换为数字进行比较
                                current_num = float(current_str) if current_str else None
                                expected_num = float(expected_str) if expected_str else None
                                if current_num is not None and expected_num is not None:
                                    should_show = current_num == expected_num
                            except (ValueError, TypeError):
                                # 转换失败，保持原比较结果
                                pass
                        
                        print(f"[DEBUG] 字段 '{dependent_field}' 显示状态: {should_show} (当前值='{current_value}', 期望值='{expected_value}')")
                        dependent_widget.setVisible(should_show)
                else:
                    print(f"[DEBUG] 字段 '{field_name}' 没有被其他字段关联")
            
            combo_box.currentIndexChanged.connect(on_combo_index_changed)
            
            # 使用卡片内部专用的下拉框样式
            combo_box.setStyleSheet(get_card_combobox_style())
            
            # 处理枚举配置
            self.setup_combo_options(combo_box, field_config)
            
            # 设置默认值（如果存在）
            if isinstance(field_config, dict) and "default_value" in field_config:
                default_value = field_config["default_value"]
                # 在下拉框中查找默认值对应的索引
                found_index = -1
                for i in range(combo_box.count()):
                    if combo_box.itemData(i) == default_value:
                        found_index = i
                        break
                if found_index >= 0:
                    combo_box.setCurrentIndex(found_index)
                elif combo_box.count() > 0:
                    combo_box.setCurrentIndex(0)
            
            field_layout.addWidget(combo_box)
            
        elif FieldType.is_multi_select_type(control_type):
            # 多选下拉框
            multi_combo = MultiSelectComboBox()
            # 设置字段标识符
            multi_combo.setProperty("field_name", field_name)
            # 使用卡片内部专用的多选下拉框样式
            multi_combo.setStyleSheet(get_card_multiselect_combobox_style())
            
            # 处理枚举配置
            self.setup_combo_options(multi_combo, field_config)
            
            # 设置默认值（如果存在）
            if isinstance(field_config, dict) and "default_value" in field_config:
                default_value = field_config["default_value"]
                # 多选框的默认值可以是数组或逗号分隔的字符串
                if isinstance(default_value, list):
                    # 基于枚举值（itemData）来匹配默认值
                    selected_descriptions = []
                    for i in range(multi_combo.count()):
                        item_data = multi_combo.itemData(i)
                        if item_data in default_value:
                            selected_descriptions.append(multi_combo.itemText(i))
                    multi_combo.set_selected_items(selected_descriptions)
                elif isinstance(default_value, str) and ',' in default_value:
                    # 逗号分隔的字符串
                    default_values = [item.strip() for item in default_value.split(',')]
                    selected_descriptions = []
                    for i in range(multi_combo.count()):
                        item_data = multi_combo.itemData(i)
                        if item_data in default_values:
                            selected_descriptions.append(multi_combo.itemText(i))
                    multi_combo.set_selected_items(selected_descriptions)
                else:
                    # 单个值
                    selected_description = ""
                    for i in range(multi_combo.count()):
                        item_data = multi_combo.itemData(i)
                        if item_data == default_value:
                            selected_description = multi_combo.itemText(i)
                            break
                    if selected_description:
                        multi_combo.set_selected_items([selected_description])
            else:
                # 如果没有配置默认值，不选中任何选项
                multi_combo.clear_selection()
            
            # 设置尺寸策略，允许多选框根据内容自适应宽度
            multi_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            
            field_layout.addWidget(multi_combo)
            
        elif FieldType.is_radio_type(control_type):
            # 点选类型（单选按钮）
            radio_widget = QWidget()
            # 为单选按钮组设置字段标识符
            radio_widget.setProperty("field_name", field_name)
            radio_layout = QHBoxLayout(radio_widget)
            radio_layout.setContentsMargins(0, 0, 0, 0)
            radio_layout.setSpacing(15)  # 单选按钮间距，参考测试数据tab
            
            # 创建按钮组确保单选
            button_group = QButtonGroup(radio_widget)
            button_group.setExclusive(True)
            
            # 获取枚举选项
            options = self.get_enum_options(field_config)
            
            # 创建单选按钮
            radio_buttons = []
            for option in options:
                radio_btn = QRadioButton(option.get("description", option.get("value", "")))
                # 为每个单选按钮设置字段标识符
                radio_btn.setProperty("field_name", field_name)
                radio_btn.setProperty("value", option.get("value", option.get("description", "")))
                
                # 为单选按钮直接添加切换事件处理
                def on_radio_toggled(checked, btn=radio_btn, fname=field_name):
                    if checked:
                        current_value = btn.property("value")
                        print(f"[DEBUG] 单选按钮 '{fname}' 切换为: {current_value}")
                        
                        # 直接校验该字段是否被其他字段关联
                        if fname in self.field_dependencies:
                            print(f"[DEBUG] 字段 '{fname}' 被其他字段关联，开始校验")
                            dependencies = self.field_dependencies[fname]
                            for dependency in dependencies:
                                dependent_field = dependency["dependent_field"]
                                expected_value = dependency["expected_value"]
                                dependent_widget = dependency["widget"]
                                
                                # 直接比较逻辑
                                current_str = str(current_value) if current_value is not None else ""
                                expected_str = str(expected_value) if expected_value is not None else ""
                                
                                # 清理字符串：去除前后空格
                                current_str = current_str.strip()
                                expected_str = expected_str.strip()
                                
                                should_show = current_str == expected_str
                                
                                # 额外检查：如果期望值是数字2，当前值是字符串"2"，也应该显示
                                if not should_show and expected_value is not None and current_value is not None:
                                    try:
                                        # 尝试将值转换为数字进行比较
                                        current_num = float(current_str) if current_str else None
                                        expected_num = float(expected_str) if expected_str else None
                                        if current_num is not None and expected_num is not None:
                                            should_show = current_num == expected_num
                                    except (ValueError, TypeError):
                                        # 转换失败，保持原比较结果
                                        pass
                                
                                print(f"[DEBUG] 字段 '{dependent_field}' 显示状态: {should_show} (当前值='{current_value}', 期望值='{expected_value}')")
                                dependent_widget.setVisible(should_show)
                        else:
                            print(f"[DEBUG] 字段 '{fname}' 没有被其他字段关联")
                
                radio_btn.toggled.connect(on_radio_toggled)
                
                # 使用简洁的默认样式，参考测试数据tab的模式和性别字段
                radio_layout.addWidget(radio_btn)
                button_group.addButton(radio_btn)
                radio_buttons.append(radio_btn)
            
            radio_layout.addStretch()
            field_layout.addWidget(radio_widget)
            
            # 设置默认值（如果存在）
            if isinstance(field_config, dict) and "default_value" in field_config:
                default_value = field_config["default_value"]
                for radio_btn in radio_buttons:
                    if radio_btn.property("value") == default_value:
                        radio_btn.setChecked(True)
                        break
            elif radio_buttons:
                # 如果没有默认值，选择第一个选项
                radio_buttons[0].setChecked(True)
            
        else:
            # 默认生成输入框
            line_edit = QLineEdit()
            # 设置字段标识符
            line_edit.setProperty("field_name", field_name)
            line_edit.setPlaceholderText(f"请输入{display_name}")
            line_edit.setStyleSheet("""
                QLineEdit {
                    height: 32px;
                    font-size: 14px;
                    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                    min-width: 200px;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 0 8px;
                    background-color: #ffffff !important;
                }
                QLineEdit:hover {
                    border-color: #cbd5e1;
                }
                QLineEdit:focus {
                    border-color: #667eea;
                    outline: none;
                }
            """)
            
            # 设置默认值（如果存在）
            if isinstance(field_config, dict) and "default_value" in field_config:
                line_edit.setText(field_config["default_value"])
            
            field_layout.addWidget(line_edit)
        
        field_layout.addStretch()
        input_layout.addWidget(field_widget)
        
        return field_widget


    def get_current_field_value(self, field_name):
        """获取指定字段的当前值"""
        # 查找当前卡片内的控件
        line_edits = self.findChildren(QLineEdit)
        combo_boxes = self.findChildren(QComboBox)
        multi_select_combos = self.findChildren(MultiSelectComboBox)
        radio_buttons = self.findChildren(QRadioButton)
        
        print(f"[DEBUG] get_current_field_value: 开始查找字段 '{field_name}'")
        print(f"[DEBUG] 找到 {len(line_edits)} 个输入框, {len(combo_boxes)} 个下拉框, {len(multi_select_combos)} 个多选框, {len(radio_buttons)} 个单选按钮")
        
        # 查找输入框
        for line_edit in line_edits:
            if line_edit.property("field_name") == field_name:
                value = line_edit.text().strip()
                print(f"[DEBUG] 在输入框中找到字段 '{field_name}', 值='{value}'")
                return value
        
        # 查找多选框
        for multi_combo in multi_select_combos:
            if multi_combo.property("field_name") == field_name:
                selected_data = multi_combo.get_selected_data()
                if selected_data:
                    value = selected_data[0] if len(selected_data) == 1 else selected_data
                    print(f"[DEBUG] 在多选框中找到字段 '{field_name}', 值='{value}'")
                    return value
                print(f"[DEBUG] 在多选框中找到字段 '{field_name}', 但无选中值")
                return ""
        
        # 查找下拉框
        for combo_box in combo_boxes:
            field_name_prop = combo_box.property("field_name")
            if field_name_prop == field_name:
                current_data = combo_box.currentData()
                current_text = combo_box.currentText()
                if current_data is not None:
                    print(f"[DEBUG] 在下拉框中找到字段 '{field_name}', currentData='{current_data}', currentText='{current_text}'")
                    return current_data
                print(f"[DEBUG] 在下拉框中找到字段 '{field_name}', currentData=None, currentText='{current_text}'")
                return current_text
            else:
                print(f"[DEBUG] 下拉框属性不匹配: property('field_name')='{field_name_prop}', 期望='{field_name}'")
        
        # 查找单选按钮
        for radio_btn in radio_buttons:
            if radio_btn.property("field_name") == field_name and radio_btn.isChecked():
                value = radio_btn.property("value")
                print(f"[DEBUG] 在单选按钮中找到字段 '{field_name}', 选中值='{value}'")
                return value
        
        print(f"[DEBUG] 未找到字段 '{field_name}'，返回空字符串")
        return ""


    def setup_association_listener(self, field_widget, field_name, association_field, association_value):
        """设置关联字段变化监听器"""
        # 查找关联字段的控件
        line_edits = self.findChildren(QLineEdit)
        combo_boxes = self.findChildren(QComboBox)
        multi_select_combos = self.findChildren(MultiSelectComboBox)
        radio_buttons = self.findChildren(QRadioButton)
        
        print(f"[DEBUG] setup_association_listener: 字段 '{field_name}' 关联到字段 '{association_field}' 值='{association_value}'")
        print(f"[DEBUG] 找到 {len(line_edits)} 个输入框, {len(combo_boxes)} 个下拉框, {len(multi_select_combos)} 个多选框, {len(radio_buttons)} 个单选按钮")
        
        # 调试：显示所有找到的下拉框的field_name属性
        print(f"[DEBUG] 检查所有下拉框的field_name属性:")
        for i, combo_box in enumerate(combo_boxes):
            field_name_prop = combo_box.property("field_name")
            print(f"[DEBUG]   下拉框 {i}: property('field_name') = '{field_name_prop}'")
            if field_name_prop == association_field:
                print(f"[DEBUG]   -> 匹配到关联字段 '{association_field}'")
        
        # 查找关联字段的输入框
        for line_edit in line_edits:
            if line_edit.property("field_name") == association_field:
                print(f"[DEBUG] 在输入框中找到关联字段 '{association_field}'，设置文本变化监听器")
                line_edit.textChanged.connect(lambda text, widget=field_widget, assoc_value=association_value: 
                    self.update_field_visibility(widget, text, assoc_value))
                return
        
        # 查找关联字段的多选框
        for multi_combo in multi_select_combos:
            if multi_combo.property("field_name") == association_field:
                print(f"[DEBUG] 在多选框中找到关联字段 '{association_field}'，设置文本变化监听器")
                # 多选框需要自定义信号监听，这里简化处理
                multi_combo.currentTextChanged.connect(lambda text, widget=field_widget, assoc_value=association_value: 
                    self.update_field_visibility(widget, text, assoc_value))
                return
        
        # 查找关联字段的下拉框
        for combo_box in combo_boxes:
            if combo_box.property("field_name") == association_field:
                print(f"[DEBUG] 在下拉框中找到关联字段 '{association_field}'，设置索引变化监听器")
                
                # 记录字段依赖关系到全局字典
                if association_field not in self.field_dependencies:
                    self.field_dependencies[association_field] = []
                self.field_dependencies[association_field].append({
                    "dependent_field": field_name,
                    "expected_value": association_value,
                    "widget": field_widget
                })
                print(f"[DEBUG] 已记录下拉框依赖关系: {association_field} -> {field_name} (期望值: {association_value})")
                
                # 监听下拉框索引变化，获取实际值
                combo_box.currentIndexChanged.connect(lambda index, field=association_field, combo=combo_box: 
                    self._handle_combo_index_changed_for_dependency(index, field, combo))
                
                # 立即触发一次初始检查，确保字段状态正确
                current_data = combo_box.currentData()
                current_value = current_data if current_data is not None else combo_box.currentText()
                print(f"[DEBUG] 关联字段 '{association_field}' 初始值检查: currentData='{current_data}', currentText='{combo_box.currentText()}', 最终值='{current_value}'")
                
                # 使用全局依赖关系更新逻辑
                self.on_field_value_changed(association_field, current_value)
                
                print(f"[DEBUG] 下拉框监听器设置完成，关联字段 '{association_field}' 已连接")
                return
        
        # 查找关联字段的单选按钮
        for radio_btn in radio_buttons:
            if radio_btn.property("field_name") == association_field:
                print(f"[DEBUG] 在单选按钮中找到关联字段 '{association_field}'，设置切换监听器")
                radio_btn.toggled.connect(lambda checked, widget=field_widget, assoc_value=association_value, btn=radio_btn: 
                    self.update_field_visibility(widget, btn.property("value") if checked else "", assoc_value))
                return
        
        print(f"[DEBUG] 警告：未找到关联字段 '{association_field}' 的控件，无法设置监听器")

    def setup_all_field_dependencies(self):
        """设置所有字段的依赖监听器"""
        print(f"[DEBUG] 开始设置所有字段依赖监听器，依赖关系: {self.field_dependencies}")
        
        # 为每个有依赖关系的字段设置监听器
        for field_name in self.field_dependencies.keys():
            print(f"[DEBUG] 为字段 '{field_name}' 设置值监听器")
            self.setup_field_value_listener(field_name)
    
    def setup_field_value_listener(self, field_name):
        """为指定字段设置值变化监听器"""
        print(f"[DEBUG] 为字段 '{field_name}' 设置值变化监听器")
        
        # 查找字段控件
        line_edits = self.findChildren(QLineEdit)
        combo_boxes = self.findChildren(QComboBox)
        multi_select_combos = self.findChildren(MultiSelectComboBox)
        radio_buttons = self.findChildren(QRadioButton)
        
        print(f"[DEBUG] 找到控件数量: 输入框={len(line_edits)}, 下拉框={len(combo_boxes)}, 多选框={len(multi_select_combos)}, 单选按钮={len(radio_buttons)}")
        
        # 查找输入框
        for line_edit in line_edits:
            if line_edit.property("field_name") == field_name:
                print(f"[DEBUG] 为输入框字段 '{field_name}' 设置文本变化监听器")
                line_edit.textChanged.connect(lambda text, field=field_name: 
                    self.on_field_value_changed(field, text))
                return
        
        # 查找多选框
        for multi_combo in multi_select_combos:
            if multi_combo.property("field_name") == field_name:
                print(f"[DEBUG] 为多选框字段 '{field_name}' 设置文本变化监听器")
                multi_combo.currentTextChanged.connect(lambda text, field=field_name: 
                    self.on_field_value_changed(field, text))
                return
        
        # 查找下拉框
        for combo_box in combo_boxes:
            field_name_prop = combo_box.property("field_name")
            print(f"[DEBUG] 检查下拉框: property('field_name')='{field_name_prop}', 期望='{field_name}'")
            if field_name_prop == field_name:
                print(f"[DEBUG] 为下拉框字段 '{field_name}' 设置索引变化监听器")
                combo_box.currentIndexChanged.connect(lambda index, field=field_name, combo=combo_box: 
                    self._handle_combo_index_changed_for_dependency(index, field, combo))
                print(f"[DEBUG] 已为下拉框字段 '{field_name}' 设置监听器")
                
                # 立即触发一次初始检查，确保字段状态正确
                current_data = combo_box.currentData()
                current_value = current_data if current_data is not None else combo_box.currentText()
                print(f"[DEBUG] 字段 '{field_name}' 初始值检查: currentData='{current_data}', currentText='{combo_box.currentText()}', 最终值='{current_value}'")
                
                # 使用全局依赖关系更新逻辑
                self.on_field_value_changed(field_name, current_value)
                
                return
        
        # 查找单选按钮
        for radio_btn in radio_buttons:
            if radio_btn.property("field_name") == field_name:
                print(f"[DEBUG] 为单选按钮字段 '{field_name}' 设置切换监听器")
                radio_btn.toggled.connect(lambda checked, field=field_name, btn=radio_btn: 
                    self.on_field_value_changed(field, btn.property("value") if checked else ""))
                return
        
        print(f"[DEBUG] 警告：未找到字段 '{field_name}' 的控件，无法设置监听器")
    
    def _handle_combo_index_changed_for_dependency(self, index, field_name, combo):
        """处理下拉框索引变化事件（用于依赖关系）"""
        current_data = combo.currentData()
        current_text = combo.currentText()
        final_value = current_data if current_data is not None else current_text
        print(f"[DEBUG] 下拉框索引变化（依赖）: 字段='{field_name}', 索引={index}, currentData='{current_data}', currentText='{current_text}', 最终值='{final_value}'")
        print(f"[DEBUG] 触发字段值变化事件: {field_name} = {final_value}")
        self.on_field_value_changed(field_name, final_value)
    
    def on_field_value_changed(self, field_name, new_value):
        """当字段值发生变化时，更新所有依赖该字段的字段可见性"""
        print(f"[DEBUG] 字段值变化: '{field_name}' = '{new_value}'")
        
        # 检查该字段是否有依赖关系
        if field_name not in self.field_dependencies:
            print(f"[DEBUG] 字段 '{field_name}' 没有依赖关系，无需更新")
            return
        
        # 更新所有依赖该字段的字段可见性
        dependencies = self.field_dependencies[field_name]
        for dependency in dependencies:
            dependent_field = dependency["dependent_field"]
            expected_value = dependency["expected_value"]
            widget = dependency["widget"]
            
            print(f"[DEBUG] 检查依赖字段 '{dependent_field}' 的可见性，期望值='{expected_value}'")
            
            # 使用修复后的比较逻辑
            current_str = str(new_value) if new_value is not None else ""
            expected_str = str(expected_value) if expected_value is not None else ""
            
            # 清理字符串：去除前后空格
            current_str = current_str.strip()
            expected_str = expected_str.strip()
            
            # 主要比较：直接字符串比较
            should_show = current_str == expected_str
            
            # 额外检查：如果期望值是数字2，当前值是字符串"2"，也应该显示
            if not should_show and expected_value is not None and new_value is not None:
                try:
                    # 尝试将值转换为数字进行比较
                    current_num = float(current_str) if current_str else None
                    expected_num = float(expected_str) if expected_str else None
                    if current_num is not None and expected_num is not None:
                        should_show = current_num == expected_num
                        print(f"[DEBUG] 数字比较结果: {current_num} == {expected_num} -> {should_show}")
                except (ValueError, TypeError):
                    # 转换失败，保持原比较结果
                    print(f"[DEBUG] 数字转换失败: current_str='{current_str}', expected_str='{expected_str}'")
                    pass
            
            # 调试输出比较详情
            print(f"[DEBUG] 比较详情: current_str='{current_str}'({type(current_str)}), expected_str='{expected_str}'({type(expected_str)}), should_show={should_show}")
            
            widget.setVisible(should_show)
            print(f"[DEBUG] 更新字段 '{dependent_field}' 可见性: {should_show} (当前值='{new_value}', 期望值='{expected_value}')")


    def _delayed_setup_association_listener(self, field_widget, field_name, association_field, association_value):
        """延迟设置关联字段监听器"""
        print(f"[DEBUG] 延迟设置关联监听器: 字段 '{field_name}' 关联字段 '{association_field}' 值='{association_value}'")
        self.setup_association_listener(field_widget, field_name, association_field, association_value)
        
        # 初始检查关联条件
        current_association_value = self.get_current_field_value(association_field)
        
        # 使用修复后的比较逻辑
        current_str = str(current_association_value) if current_association_value is not None else ""
        assoc_str = str(association_value) if association_value is not None else ""
        
        # 清理字符串：去除前后空格
        current_str = current_str.strip()
        assoc_str = assoc_str.strip()
        
        should_show = current_str == assoc_str
        
        # 额外检查：如果期望值是数字2，当前值是字符串"2"，也应该显示
        if not should_show and association_value is not None and current_association_value is not None:
            try:
                # 尝试将值转换为数字进行比较
                current_num = float(current_str) if current_str else None
                assoc_num = float(assoc_str) if assoc_str else None
                if current_num is not None and assoc_num is not None:
                    should_show = current_num == assoc_num
            except (ValueError, TypeError):
                # 转换失败，保持原比较结果
                pass
        
        field_widget.setVisible(should_show)
        print(f"[DEBUG] 延迟关联检查完成: 字段 '{field_name}' 关联字段 '{association_field}' 当前值='{current_association_value}'({type(current_association_value)}), 期望值='{association_value}'({type(association_value)}), 显示={should_show}")


    def _handle_combo_index_changed(self, index, widget, assoc_value, combo):
        """处理下拉框索引变化事件"""
        current_data = combo.currentData()
        current_text = combo.currentText()
        final_value = current_data if current_data is not None else current_text
        print(f"[DEBUG] 下拉框索引变化: 索引={index}, currentData='{current_data}', currentText='{current_text}', 最终值='{final_value}'")
        self.update_field_visibility(widget, final_value, assoc_value)


    def _setup_direct_field_handler(self, field_name):
        """为字段设置直接的切换处理"""
        print(f"[DEBUG] 为字段 '{field_name}' 设置直接切换处理")
        
        # 查找字段控件
        combo_boxes = self.findChildren(QComboBox)
        radio_buttons = self.findChildren(QRadioButton)
        
        # 为下拉框设置直接的切换处理
        for combo_box in combo_boxes:
            if combo_box.property("field_name") == field_name:
                print(f"[DEBUG] 为下拉框字段 '{field_name}' 设置直接切换处理")
                
                # 直接重写下拉框的切换事件
                original_index_changed = combo_box.currentIndexChanged
                
                def direct_combo_handler(index):
                    # 先执行原始处理
                    if original_index_changed:
                        original_index_changed.emit(index)
                    
                    # 直接校验关联字段
                    self._check_field_associations_directly(field_name, combo_box)
                
                combo_box.currentIndexChanged.disconnect()
                combo_box.currentIndexChanged.connect(direct_combo_handler)
                return
        
        # 为单选按钮设置直接的切换处理
        for radio_btn in radio_buttons:
            if radio_btn.property("field_name") == field_name:
                print(f"[DEBUG] 为单选按钮字段 '{field_name}' 设置直接切换处理")
                
                # 直接重写单选按钮的切换事件
                original_toggled = radio_btn.toggled
                
                def direct_radio_handler(checked):
                    # 先执行原始处理
                    if original_toggled:
                        original_toggled.emit(checked)
                    
                    # 直接校验关联字段
                    self._check_field_associations_directly(field_name, radio_btn)
                
                radio_btn.toggled.disconnect()
                radio_btn.toggled.connect(direct_radio_handler)
                return
        
        print(f"[DEBUG] 未找到字段 '{field_name}' 的控件，无法设置直接处理")
    
    def _check_field_associations_directly(self, field_name, widget):
        """直接校验字段关联关系"""
        print(f"[DEBUG] 直接校验字段 '{field_name}' 的关联关系")
        
        # 获取当前值
        if isinstance(widget, QComboBox):
            current_value = widget.currentData() if widget.currentData() is not None else widget.currentText()
        elif isinstance(widget, QRadioButton):
            current_value = widget.property("value") if widget.isChecked() else ""
        else:
            current_value = ""
        
        print(f"[DEBUG] 字段 '{field_name}' 当前值: '{current_value}'")
        
        # 检查该字段是否有依赖关系
        if field_name not in self.field_dependencies:
            print(f"[DEBUG] 字段 '{field_name}' 没有依赖关系，无需处理")
            return
        
        # 更新所有依赖该字段的字段可见性
        dependencies = self.field_dependencies[field_name]
        for dependency in dependencies:
            dependent_field = dependency["dependent_field"]
            expected_value = dependency["expected_value"]
            dependent_widget = dependency["widget"]
            
            print(f"[DEBUG] 检查依赖字段 '{dependent_field}' 的可见性，期望值='{expected_value}'")
            
            # 直接比较逻辑
            current_str = str(current_value) if current_value is not None else ""
            expected_str = str(expected_value) if expected_value is not None else ""
            
            # 清理字符串：去除前后空格
            current_str = current_str.strip()
            expected_str = expected_str.strip()
            
            should_show = current_str == expected_str
            
            # 额外检查：如果期望值是数字2，当前值是字符串"2"，也应该显示
            if not should_show and expected_value is not None and current_value is not None:
                try:
                    # 尝试将值转换为数字进行比较
                    current_num = float(current_str) if current_str else None
                    expected_num = float(expected_str) if expected_str else None
                    if current_num is not None and expected_num is not None:
                        should_show = current_num == expected_num
                        print(f"[DEBUG] 数字比较结果: {current_num} == {expected_num} -> {should_show}")
                except (ValueError, TypeError):
                    # 转换失败，保持原比较结果
                    pass
            
            # 调试输出比较详情
            print(f"[DEBUG] 比较详情: current_str='{current_str}'({type(current_str)}), expected_str='{expected_str}'({type(expected_str)}), should_show={should_show}")
            
            dependent_widget.setVisible(should_show)
            print(f"[DEBUG] 更新字段 '{dependent_field}' 可见性: {should_show}")

    def _get_default_field_value(self, field_name, sorted_mappings):
        """从数据库配置中获取字段的默认值"""
        print(f"[DEBUG] 获取字段 '{field_name}' 的默认值")
        
        # sorted_mappings 是一个列表，包含 (field_name, field_config) 元组
        for mapping_field_name, field_config in sorted_mappings:
            if mapping_field_name == field_name and isinstance(field_config, dict):
                default_value = field_config.get("default_value", "")
                print(f"[DEBUG] 找到字段 '{field_name}' 的默认值: '{default_value}'")
                return default_value
        
        print(f"[DEBUG] 未找到字段 '{field_name}' 的默认值，返回空字符串")
        return ""

    def update_field_visibility(self, field_widget, current_value, association_value):
        """根据关联字段值更新字段可见性"""
        # 修复值比较逻辑：处理空值、None值和字符串转换
        current_str = str(current_value) if current_value is not None else ""
        assoc_str = str(association_value) if association_value is not None else ""
        
        # 特殊处理：如果期望值是数字2，但当前值是字符串"2"，也应该匹配
        should_show = current_str == assoc_str
        
        # 额外检查：如果期望值是数字2，当前值是字符串"2"，也应该显示
        if not should_show and association_value is not None and current_value is not None:
            try:
                # 尝试将值转换为数字进行比较
                current_num = float(current_str) if current_str else None
                assoc_num = float(assoc_str) if assoc_str else None
                if current_num is not None and assoc_num is not None:
                    should_show = current_num == assoc_num
            except (ValueError, TypeError):
                # 转换失败，保持原比较结果
                pass
        
        field_widget.setVisible(should_show)
        print(f"[DEBUG] 关联字段值变化: 当前值='{current_value}'({type(current_value)}), 期望值='{association_value}'({type(association_value)}), 显示={should_show}")


    def setup_combo_options(self, combo_box, field_config):
        """设置下拉框选项"""
        if isinstance(field_config, str) and "枚举" in field_config:
            # 旧格式：字符串格式
            enum_part = field_config.split("枚举")[1].strip()
            enum_items = [item.strip() for item in enum_part.split(',')]
            for item in enum_items:
                combo_box.addItem(item, item)  # 显示文本和值都设置为item
        elif isinstance(field_config, dict) and "options" in field_config:
            # 新格式：结构化JSON对象
            enum_items = field_config.get("options", [])
            for item in enum_items:
                description = item.get("description", "")
                value = item.get("value", "")
                # 设置显示文本和实际值
                if description and value:
                    combo_box.addItem(description, value)
                elif description:
                    combo_box.addItem(description, description)
                elif value:
                    combo_box.addItem(value, value)
        else:
            # 默认选项
            combo_box.addItem("请选择", "")
            combo_box.addItem("选项1", "选项1")
            combo_box.addItem("选项2", "选项2")

    def get_enum_options(self, field_config):
        """获取枚举选项列表"""
        options = []
        
        if isinstance(field_config, str) and "枚举" in field_config:
            # 旧格式：字符串格式
            enum_part = field_config.split("枚举")[1].strip()
            enum_items = [item.strip() for item in enum_part.split(',')]
            for item in enum_items:
                options.append({"description": item, "value": item})
        elif isinstance(field_config, dict) and "options" in field_config:
            # 新格式：结构化JSON对象
            options = field_config.get("options", [])
        else:
            # 默认选项
            options = [
                {"description": "选项1", "value": "选项1"},
                {"description": "选项2", "value": "选项2"}
            ]
        
        return options

    def get_card_input_parameters(self):
        """获取当前卡片的输入参数（卡片级别，避免不同卡片间混淆）"""
        print(f"[DEBUG] 开始获取卡片级别输入参数")
        
        input_params = {}
        missing_required_fields = []
        mappings = self.card_data.get("mappings", {})
        card_type = self.card_data.get("type", "sql")  # 获取卡片类型
        print(f"[DEBUG] 卡片级别映射配置: {mappings}, 卡片类型: {card_type}")
        
        # 只查找当前卡片内的控件，避免不同卡片间混淆
        line_edits = self.findChildren(QLineEdit)
        combo_boxes = self.findChildren(QComboBox)
        multi_select_combos = self.findChildren(MultiSelectComboBox)
        radio_buttons = self.findChildren(QRadioButton)
                
        # 遍历所有字段，基于字段英文名称精确匹配对应的控件
        for field_name, field_config in mappings.items():
            # 获取显示名称和字段类型
            if isinstance(field_config, str):
                display_name = field_config.split('-')[0] if '-' in field_config else field_name
                # 兼容旧格式：如果包含"下拉框"则认为是下拉框类型
                control_type = FieldType.SELECT_DISPLAY if "下拉框" in field_config else FieldType.INPUT_DISPLAY
                required = False  # 旧格式不支持必填
                association_enabled = False  # 旧格式不支持关联
            else:
                display_name = field_config.get("display_name", field_name)
                control_type = FieldType.get_display_from_type(field_config.get("type", FieldType.INPUT))
                required = field_config.get("required", False)
                association_enabled = field_config.get("association_enabled", False)
            
            print(f"[DEBUG] 卡片级别查找字段: {field_name}, 显示名: {display_name}, 类型: {control_type}, 必填: {required}, 关联: {association_enabled}")
            
            # 检查关联字段条件，如果字段被隐藏则不参与参数收集
            if association_enabled and isinstance(field_config, dict):
                association_field = field_config.get("association_field", "")
                association_value = field_config.get("association_value", "")
                
                if association_field and association_value:
                    # 获取关联字段的当前值
                    current_association_value = self.get_current_field_value(association_field)
                    should_include_field = str(current_association_value) == str(association_value)
                    
                    if not should_include_field:
                        print(f"[DEBUG] 字段 '{field_name}' 因关联条件不满足被隐藏，不参与参数收集")
                        # 对于隐藏的字段，如果必填则跳过校验，直接提供空值
                        input_params[field_name] = ""
                        continue
            
            # 基于字段英文名称精确查找对应的控件
            field_value = None
            
            # 查找输入框
            for line_edit in line_edits:
                if line_edit.property("field_name") == field_name:
                    field_value = line_edit.text().strip()
                    print(f"[DEBUG] 卡片级别从输入框获取到字段值: {field_name} = {field_value}")
                    break
            
            # 如果输入框没找到，查找多选框
            if field_value is None:
                for multi_combo in multi_select_combos:
                    if multi_combo.property("field_name") == field_name:
                        # 获取多选框的选中值（无论是否有用户选择）
                        selected_data = multi_combo.get_selected_data()
                        if selected_data:
                            # 根据卡片类型差异化处理多选框值
                            if card_type == "http":
                                # HTTP类型：作为列表传递
                                field_value = selected_data
                            elif card_type == "sql":
                                # SQL类型：提供逗号分隔的值列表，让用户在SQL中构建IN条件
                                # 用户需要在SQL中写：method in (${method})
                                # 系统提供：POST','GET（让sql_worker添加外层引号）
                                field_value = "','".join(selected_data)
                            else:
                                # 其他类型：默认逗号分隔字符串
                                field_value = ",".join(selected_data)
                            print(f"[DEBUG] 卡片级别从多选框获取到字段值: {field_name} = {field_value} (类型: {card_type})")
                        else:
                            # 如果没有选中值，使用空列表作为默认值
                            if card_type == "http":
                                field_value = []
                            else:
                                field_value = ""
                            print(f"[DEBUG] 卡片级别多选框无选中值，使用默认值: {field_name} = {field_value}")
                        break
            
            # 如果多选框没找到，查找下拉框
            if field_value is None:
                for combo_box in combo_boxes:
                    if combo_box.property("field_name") == field_name:
                        # 检查下拉框是否有相关文本
                        current_text = combo_box.currentText()
                        if current_text and current_text != "请选择":
                            # 获取下拉框的实际值（itemData），如果没有设置itemData则使用显示文本
                            current_data = combo_box.currentData()
                            if current_data is not None:
                                field_value = current_data
                            else:
                                field_value = current_text
                            print(f"[DEBUG] 卡片级别从下拉框获取到字段值: {field_name} = {field_value} (显示文本: {current_text})")
                        break
            
            # 如果下拉框没找到，查找单选按钮
            if field_value is None:
                for radio_btn in radio_buttons:
                    if radio_btn.property("field_name") == field_name:
                        if radio_btn.isChecked():
                            # 获取单选按钮的值
                            field_value = radio_btn.property("value")
                            print(f"[DEBUG] 卡片级别从单选按钮获取到字段值: {field_name} = {field_value}")
                            break  # 找到选中的按钮后退出循环
                # 注意：这里不能在外层break，因为需要遍历所有同字段名的单选按钮来找到被选中的那个
            
            # 必填校验
            is_empty = False
            if field_value is None:
                is_empty = True
            elif isinstance(field_value, str) and field_value == "":
                is_empty = True
            elif isinstance(field_value, list) and len(field_value) == 0:
                is_empty = True
            
            if required and is_empty:
                missing_required_fields.append(display_name)
                print(f"[WARNING] 卡片级别必填字段 '{display_name}' 为空")
            
            if field_value is not None:
                input_params[field_name] = field_value
            else:
                print(f"[WARNING] 卡片级别未找到字段 '{field_name}' 的输入控件")
                # 提供默认值（空字符串）
                input_params[field_name] = ""
        
        # 如果有必填字段为空，显示错误信息
        if missing_required_fields:
            field_names = ", ".join(missing_required_fields)
            Toast.error(self, f"{field_names}必填")
            return None
        
        print(f"[DEBUG] 卡片级别最终获取到的输入参数: {input_params}")
        return input_params

    # 删除原来的菜单功能，因为操作按钮已移到顶部

    def execute_card(self):
        # 使用卡片级别的参数收集方法，避免不同卡片间混淆
        input_params = self.get_card_input_parameters()
        if input_params is None:  # 参数收集失败（如必填字段为空）
            return
        
        # 将参数传递给父Tab执行
        self.parent_tab.execute_card_with_params(self.card_data, input_params)


class ToolCardsTab(QWidget):
    """卡片工具Tab页面"""

    data_changed = pyqtSignal()  # 数据变化信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_folder_id = None
        self.folder_data = []
        
        # 初始化服务类
        self.tool_cards_service = ToolCardsService()
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：文件夹管理区域（调整宽度为200）
        left_widget = self.create_folder_panel()
        left_widget.setMinimumWidth(200)
        left_widget.setMaximumWidth(300)
        splitter.addWidget(left_widget)

        # 右侧：卡片展示区域
        right_widget = self.create_cards_panel()
        splitter.addWidget(right_widget)

        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([200, 800])

        main_layout.addWidget(splitter)

    def create_folder_panel(self):
        """创建文件夹管理面板"""
        folder_panel = QWidget()
        folder_layout = QVBoxLayout(folder_panel)
        folder_layout.setSpacing(5)
        folder_layout.setContentsMargins(5, 5, 5, 5)

        # 文件夹操作按钮区域
        button_layout = QHBoxLayout()
        
        # 添加文件夹按钮
        self.add_folder_btn = QPushButton()
        self.add_folder_btn.setIcon(self.get_icon("add_folder.png"))
        self.add_folder_btn.setIconSize(QSize(20, 20))
        self.add_folder_btn.setFixedSize(32, 32)
        self.add_folder_btn.setToolTip("添加文件夹")
        self.add_folder_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QPushButton:hover {
                background-color: rgba(66, 153, 225, 0.1);
                border-radius: 6px;
            }
            QPushButton:focus {
                outline: none;
                border: none;
            }
        """
        )
        self.add_folder_btn.clicked.connect(self.add_folder)
        button_layout.addWidget(self.add_folder_btn)

        # 删除文件夹按钮
        self.delete_folder_btn = QPushButton()
        self.delete_folder_btn.setIcon(self.get_icon("del_folder.png"))
        self.delete_folder_btn.setIconSize(QSize(20, 20))
        self.delete_folder_btn.setFixedSize(32, 32)
        self.delete_folder_btn.setToolTip("删除文件夹")
        self.delete_folder_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QPushButton:hover {
                background-color: rgba(229, 62, 62, 0.1);
                border-radius: 6px;
            }
            QPushButton:focus {
                outline: none;
                border: none;
            }
        """
        )
        self.delete_folder_btn.clicked.connect(self.delete_folder)
        self.delete_folder_btn.setEnabled(False)  # 初始禁用
        button_layout.addWidget(self.delete_folder_btn)

        # 配置按钮
        self.config_btn = QPushButton()
        self.config_btn.setIcon(self.get_icon("add_card.png"))
        self.config_btn.setIconSize(QSize(24, 24))
        self.config_btn.setFixedSize(32, 32)
        self.config_btn.setToolTip("添加卡片")
        self.config_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QPushButton:hover {
                background-color: rgba(72, 187, 120, 0.1);
                border-radius: 6px;
            }
            QPushButton:focus {
                outline: none;
                border: none;
            }
        """
        )
        self.config_btn.clicked.connect(self.open_config_dialog)
        button_layout.addWidget(self.config_btn)

        button_layout.addStretch()
        folder_layout.addLayout(button_layout)

        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_label.setStyleSheet("QLabel { font-weight: bold; }")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入文件夹名称...")
        self.search_edit.textChanged.connect(self.filter_folders)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        folder_layout.addLayout(search_layout)

        # 文件夹树形列表
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(self.show_folder_context_menu)
        self.folder_tree.setStyleSheet(
            """
            QTreeWidget {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: white;
                outline: none;
            }
            QTreeWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #f0f0f0;
                height: 30px;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #0078d4;
            }
            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }
        """
        )
        self.folder_tree.itemSelectionChanged.connect(self.on_folder_selected)
        folder_layout.addWidget(self.folder_tree)

        return folder_panel

    def create_cards_panel(self):
        """创建卡片展示面板 - 现代化设计"""
        cards_panel = QWidget()
        cards_layout = QVBoxLayout(cards_panel)
        cards_layout.setSpacing(0)
        cards_layout.setContentsMargins(0, 0, 0, 0)

        # 卡片区域滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background: #f8fafc;
            }
            QScrollBar:vertical {
                background-color: #f8fafc;
                width: 6px;
                border-radius: 3px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background-color: #cbd5e1;
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #94a3b8;
            }
        """)

        # 卡片容器 - 使用网格布局实现自动换行
        self.cards_container = QWidget()
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(16)  # 增加卡片间距
        self.cards_layout.setContentsMargins(16, 16, 16, 16)  # 增加边距
        self.cards_layout.setAlignment(Qt.AlignTop)

        scroll_area.setWidget(self.cards_container)
        cards_layout.addWidget(scroll_area, 1)

        return cards_panel

    def load_data(self):
        """加载数据"""
        try:
            # 使用数据库服务加载数据
            self.folder_data = self.tool_cards_service.get_all_folders()
            
            # 查找默认文件夹
            self.default_folder = None
            for folder in self.folder_data:
                if folder.get('is_default'):
                    self.default_folder = folder.get('id')
                    break
            
            self.load_folder_tree()
        except Exception as e:
            print(f"加载数据失败: {e}")
            Toast.error(self, "加载数据失败", f"错误: {str(e)}")

    def load_folder_tree(self):
        """加载文件夹树形结构"""
        self.folder_tree.clear()
        
        if not self.folder_data:
            return

        # 第一遍：创建所有节点映射
        item_map = {}
        for folder in self.folder_data:
            item = QTreeWidgetItem()
            item.setIcon(0, self.get_icon("folder.png"))
            item.setText(0, folder["name"])
            item.setData(0, Qt.UserRole, folder["id"])
            item_map[folder["id"]] = item

        # 第二遍：建立父子关系
        for folder in self.folder_data:
            item = item_map[folder["id"]]
            parent_id = folder.get("parent_id")
            
            if parent_id and parent_id in item_map:
                # 添加到父节点
                parent_item = item_map[parent_id]
                parent_item.addChild(item)
            else:
                # 根文件夹
                self.folder_tree.addTopLevelItem(item)

        # 展开所有节点
        self.folder_tree.expandAll()

        # 默认选择第一个文件夹
        if self.folder_tree.topLevelItemCount() > 0:
            self.folder_tree.setCurrentItem(self.folder_tree.topLevelItem(0))

    def find_tree_item_by_id(self, folder_id):
        """根据文件夹ID查找树节点"""
        def find_recursive(item):
            if item.data(0, Qt.UserRole) == folder_id:
                return item
            for i in range(item.childCount()):
                found = find_recursive(item.child(i))
                if found:
                    return found
            return None

        for i in range(self.folder_tree.topLevelItemCount()):
            found = find_recursive(self.folder_tree.topLevelItem(i))
            if found:
                return found
        return None

    def expand_folder_by_id(self, folder_id):
        """根据文件夹ID展开对应的树节点"""
        item = self.find_tree_item_by_id(folder_id)
        if item:
            item.setExpanded(True)
            # 确保父文件夹也被展开
            parent = item.parent()
            while parent:
                parent.setExpanded(True)
                parent = parent.parent()

    def check_folder_has_cards_recursive(self, folder_id):
        """递归检查文件夹及其所有子文件夹是否包含卡片"""
        # 检查当前文件夹下的卡片
        cards = self.tool_cards_service.get_cards_by_folder(folder_id)
        if cards:
            return True, folder_id, len(cards)
        
        # 获取所有子文件夹
        subfolders = self.tool_cards_service.get_subfolders_by_parent(folder_id)
        
        # 递归检查每个子文件夹
        for subfolder in subfolders:
            subfolder_id = subfolder['id']
            has_cards, problem_folder_id, card_count = self.check_folder_has_cards_recursive(subfolder_id)
            if has_cards:
                return True, problem_folder_id, card_count
        
        return False, None, 0

    def select_folder_by_id(self, folder_id):
        """根据文件夹ID选择对应的树节点"""
        item = self.find_tree_item_by_id(folder_id)
        if item:
            self.folder_tree.setCurrentItem(item)
            # 确保父文件夹也被展开
            parent = item.parent()
            while parent:
                parent.setExpanded(True)
                parent = parent.parent()

    def get_folder_depth(self, folder_id):
        """获取文件夹的层级深度"""
        def get_depth_recursive(item, current_depth):
            if item.data(0, Qt.UserRole) == folder_id:
                return current_depth
            for i in range(item.childCount()):
                found_depth = get_depth_recursive(item.child(i), current_depth + 1)
                if found_depth is not None:
                    return found_depth
            return None

        for i in range(self.folder_tree.topLevelItemCount()):
            depth = get_depth_recursive(self.folder_tree.topLevelItem(i), 1)
            if depth is not None:
                return depth
        return 1  # 默认返回1，表示根层级

    def can_add_subfolder(self, folder_id):
        """检查是否可以添加子文件夹（限制最多两级）"""
        depth = self.get_folder_depth(folder_id)
        return depth < 2  # 只有第一级（深度1）可以添加子文件夹

    def on_folder_selected(self):
        """文件夹选择事件"""
        current_item = self.folder_tree.currentItem()
        if not current_item:
            self.delete_folder_btn.setEnabled(False)
            return

        folder_id = current_item.data(0, Qt.UserRole)
        self.current_folder_id = folder_id
        self.delete_folder_btn.setEnabled(True)

        # 加载该文件夹下的卡片
        self.load_cards_for_folder(folder_id)

    def load_cards_for_folder(self, folder_id):
        """加载指定文件夹下的卡片"""
        # 清空卡片区域
        for i in reversed(range(self.cards_layout.count())):
            item = self.cards_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        # 使用数据库服务加载卡片数据
        cards = self.tool_cards_service.get_cards_by_folder(folder_id)
        
        if not cards:
            no_cards_label = QLabel("该文件夹下暂无卡片")
            no_cards_label.setStyleSheet("QLabel { color: #666; font-size: 14px; text-align: center; }")
            no_cards_label.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(no_cards_label, 0, 0)
            return

        # 使用网格布局显示卡片
        row, col = 0, 0
        max_cols = 4  # 每行最多显示4个卡片（因为卡片宽度固定为300px）
        
        for card in cards:
            # 转换卡片数据结构以兼容现有界面
            card_data = {
                "id": card.get("id"),
                "name": card.get("name"),
                "description": card.get("description", ""),
                "type": card.get("card_type", "sql"),
                "config": card.get("config", {}),
                "mappings": card.get("mappings", {})
            }
            
            # 调试输出：检查映射数据中是否包含必填字段信息
            print(f"[DEBUG] 加载卡片: {card_data.get('name')}")
            if card_data.get("mappings"):
                for field_name, field_config in card_data["mappings"].items():
                    required = field_config.get("required", False) if isinstance(field_config, dict) else False
                    print(f"[DEBUG] 字段 '{field_name}': 必填状态 = {required}")
            
            card_widget = ToolCardWidget(card_data, self)
            self.cards_layout.addWidget(card_widget, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def filter_folders(self):
        """过滤文件夹"""
        search_text = self.search_edit.text().lower()
        
        def filter_recursive(item):
            item_text = item.text(0).lower()
            visible = search_text in item_text if search_text else True
            
            # 检查子项是否可见
            child_visible = False
            for i in range(item.childCount()):
                if filter_recursive(item.child(i)):
                    child_visible = True
            
            # 如果当前项或子项可见，则显示
            item.setHidden(not (visible or child_visible))
            return visible or child_visible

        for i in range(self.folder_tree.topLevelItemCount()):
            filter_recursive(self.folder_tree.topLevelItem(i))

    def add_folder(self):
        """添加文件夹"""
        # 创建自定义输入对话框
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle("添加文件夹")
        dialog.setFixedSize(300, 140)
        
        layout = QVBoxLayout(dialog)
        
        # 提示文本
        label = QLabel("请输入文件夹名称:")
        layout.addWidget(label)
        
        # 输入框
        name_input = QLineEdit()
        layout.addWidget(name_input)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        confirm_btn = QPushButton("确认")
        cancel_btn = QPushButton("取消")
        
        confirm_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(confirm_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 设置焦点到输入框
        name_input.setFocus()
        
        # 显示对话框
        if dialog.exec_() == QDialog.Accepted:
            name = name_input.text().strip()
            if name:
                # 创建新文件夹数据
                folder_data = {
                    "name": name,
                    "description": "",
                    "parent_id": None,
                    "sort_order": 0,  # 使用默认值，排序由created_at决定
                    "is_default": False,
                    "created_by": "admin"
                }
                
                # 使用数据库服务创建文件夹
                folder_id = self.tool_cards_service.create_folder(folder_data)
                
                if folder_id:
                    # 重新加载数据
                    self.load_data()
                    # 自动定位到新增的文件夹
                    self.select_folder_by_id(folder_id)
                    Toast.success(self, f"添加成功：文件夹 '{name}' 已添加")
                else:
                    Toast.error(self, "添加失败", "无法创建文件夹，请检查数据库连接")

    def delete_folder(self):
        """删除文件夹"""
        current_item = self.folder_tree.currentItem()
        if not current_item:
            return

        folder_id = current_item.data(0, Qt.UserRole)
        folder_name = current_item.text(0)

        # 创建自定义确认对话框
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle("确认删除")
        dialog.setFixedSize(300, 120)
        
        layout = QVBoxLayout(dialog)
        
        # 统一提示文本，不显示卡片信息
        label = QLabel(f"确定要删除文件夹 '{folder_name}' 吗？")
        layout.addWidget(label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        confirm_btn = QPushButton("确认")
        cancel_btn = QPushButton("取消")
        
        confirm_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(confirm_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 显示对话框
        if dialog.exec_() != QDialog.Accepted:
            return
        
        # 确认后递归检查文件夹及其所有子文件夹下是否有卡片
        has_cards, problem_folder_id, card_count = self.check_folder_has_cards_recursive(folder_id)
        if has_cards:
            # 获取问题文件夹的名称
            problem_folder = self.tool_cards_service.get_folder_by_id(problem_folder_id)
            problem_folder_name = problem_folder['name'] if problem_folder else "未知文件夹"
            
            # 如果问题文件夹就是当前要删除的文件夹
            if problem_folder_id == folder_id:
                Toast.error(self, f"删除失败：文件夹 '{folder_name}' 下有 {card_count} 个卡片，请先删除或移动这些卡片后再删除文件夹")
            else:
                # 如果问题文件夹是子文件夹
                Toast.error(self, f"删除失败：子文件夹 '{problem_folder_name}' 下有 {card_count} 个卡片，请先删除或移动这些卡片后再删除父文件夹")
            return
        
        # 使用数据库服务删除文件夹
        # 由于数据库设计使用了CASCADE删除，我们只需要删除文件夹
        # 但需要先检查文件夹是否存在
        folder = self.tool_cards_service.get_folder_by_id(folder_id)
        if not folder:
            Toast.error(self, "删除失败：文件夹不存在或已被删除")
            return
            
        # 使用数据库服务删除文件夹
        try:
            success = self.tool_cards_service.delete_folder(folder_id)
            if success:
                # 重新加载数据
                self.load_data()
                Toast.success(self, f"删除成功：文件夹 '{folder_name}' 已删除")
            else:
                Toast.error(self, "删除失败：数据库操作失败，请检查数据库连接或联系管理员")
        except Exception as e:
            Toast.error(self, f"删除失败：删除文件夹时发生错误: {str(e)}")

    def edit_folder(self):
        """编辑文件夹"""
        current_item = self.folder_tree.currentItem()
        if not current_item:
            return
            
        folder_id = current_item.data(0, Qt.UserRole)
        folder_name = current_item.text(0)
        
        # 获取当前文件夹信息
        folder = self.tool_cards_service.get_folder_by_id(folder_id)
        if not folder:
            Toast.error(self, "编辑失败", "找不到指定的文件夹")
            return
        
        # 创建自定义输入对话框
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑文件夹")
        dialog.setFixedSize(300, 140)
        
        layout = QVBoxLayout(dialog)
        
        # 提示文本
        label = QLabel("请输入新的文件夹名称:")
        layout.addWidget(label)
        
        # 输入框
        name_input = QLineEdit(folder_name)
        layout.addWidget(name_input)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        confirm_btn = QPushButton("确认")
        cancel_btn = QPushButton("取消")
        
        confirm_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(confirm_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 设置焦点到输入框
        name_input.setFocus()
        name_input.selectAll()
        
        # 显示对话框
        if dialog.exec_() == QDialog.Accepted:
            new_name = name_input.text().strip()
            if new_name:
                # 更新文件夹数据
                folder_data = {
                    "name": new_name,
                    "description": folder.get("description", ""),
                    "parent_id": folder.get("parent_id"),
                    "sort_order": folder.get("sort_order", 0),
                    "is_default": folder.get("is_default", False),
                    "created_by": folder.get("created_by", "admin")
                }
                
                # 使用数据库服务更新文件夹
                success = self.tool_cards_service.update_folder(folder_id, folder_data)
                
                if success:
                    # 重新加载数据
                    self.folder_data = self.tool_cards_service.get_all_folders()
                    
                    # 重新构建文件夹树
                    self.load_folder_tree()
                    
                    Toast.success(self, "编辑成功", f"文件夹已重命名为 '{new_name}'")
                else:
                    Toast.error(self, "编辑失败", "无法更新文件夹，请检查数据库连接")

    def show_folder_context_menu(self, position):
        """显示文件夹右键菜单"""
        item = self.folder_tree.itemAt(position)
        if not item:
            return
            
        # 设置当前选中的文件夹
        self.folder_tree.setCurrentItem(item)
        
        # 获取当前文件夹ID
        folder_id = item.data(0, Qt.UserRole)
        
        # 创建右键菜单
        menu = QMenu(self)
        
        # 添加编辑菜单项
        edit_action = QAction("编辑", self)
        edit_action.setIcon(self.get_icon("edit.png"))
        edit_action.triggered.connect(self.edit_folder)
        menu.addAction(edit_action)
        
        # 添加新增卡片菜单项
        add_card_action = QAction("新增卡片", self)
        add_card_action.setIcon(self.get_icon("add_card.png"))
        add_card_action.triggered.connect(self.open_config_dialog)
        menu.addAction(add_card_action)
        
        # 只有第一级文件夹可以添加子文件夹（限制最多两级）
        if self.can_add_subfolder(folder_id):
            add_subfolder_action = QAction("新增子文件夹", self)
            add_subfolder_action.setIcon(self.get_icon("add_folder.png"))
            add_subfolder_action.triggered.connect(self.add_subfolder)
            menu.addAction(add_subfolder_action)
        
        # 添加删除菜单项
        delete_action = QAction("删除", self)
        delete_action.setIcon(self.get_icon("del_folder.png"))
        delete_action.triggered.connect(self.delete_folder)
        menu.addAction(delete_action)
        
        # 显示菜单
        menu.exec_(self.folder_tree.viewport().mapToGlobal(position))

    def add_subfolder(self):
        """添加子文件夹"""
        current_item = self.folder_tree.currentItem()
        if not current_item:
            return
            
        parent_folder_id = current_item.data(0, Qt.UserRole)
        parent_folder_name = current_item.text(0)
        
        # 检查是否可以添加子文件夹（限制最多两级）
        if not self.can_add_subfolder(parent_folder_id):
            Toast.warning(self, "操作受限", "最多只能有两级文件夹，无法在第二级文件夹下添加子文件夹")
            return
        
        # 创建自定义输入对话框
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle("添加子文件夹")
        dialog.setFixedSize(350, 140)
        
        layout = QVBoxLayout(dialog)
        
        # 提示文本
        label = QLabel(f"在 '{parent_folder_name}' 下添加子文件夹:\n请输入子文件夹名称:")
        layout.addWidget(label)
        
        # 输入框
        name_input = QLineEdit()
        layout.addWidget(name_input)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        confirm_btn = QPushButton("确认")
        cancel_btn = QPushButton("取消")
        
        confirm_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(confirm_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 设置焦点到输入框
        name_input.setFocus()
        
        # 显示对话框
        if dialog.exec_() == QDialog.Accepted:
            name = name_input.text().strip()
            if name:
                # 创建新子文件夹数据
                folder_data = {
                    "name": name,
                    "description": "",
                    "parent_id": parent_folder_id,
                    "sort_order": 0,  # 使用默认值，排序由created_at决定
                    "is_default": False,
                    "created_by": "admin"
                }
                
                # 使用数据库服务创建子文件夹
                folder_id = self.tool_cards_service.create_folder(folder_data)
                
                if folder_id:
                    # 强制重新从数据库加载数据
                    self.folder_data = self.tool_cards_service.get_all_folders()
                    
                    # 重新构建文件夹树
                    self.load_folder_tree()
                    
                    # 展开父文件夹以显示新添加的子文件夹
                    # 注意：重新构建文件夹树后，原来的current_item已被删除，需要重新查找
                    self.expand_folder_by_id(parent_folder_id)
                    
                    # 自动定位到新增的子文件夹
                    self.select_folder_by_id(folder_id)
                    
                    Toast.success(self, f"添加成功：子文件夹 '{name}' 已添加到 '{parent_folder_name}'")
                else:
                    Toast.error(self, "添加失败", "无法创建子文件夹，请检查数据库连接")

    def save_data(self):
        """保存数据到配置文件"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "tool_cards.json")
            config = {
                "folders": self.folder_data,
                "default_folder": self.default_folder
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.data_changed.emit()
        except Exception as e:
            print(f"保存数据失败: {e}")
            Toast.error(self, "保存数据失败", f"错误: {str(e)}")

    def open_config_dialog(self):
        """打开配置对话框"""
        if not self.current_folder_id:
            Toast.info(self, "提示", "请先选择文件夹")
            return
        
        # 打开添加卡片对话框
        dialog = ToolCardsConfigDialog(self.folder_data, self, self.current_folder_id)
        if dialog.exec_() == QDialog.Accepted:
            # 数据已直接保存到数据库，只需刷新显示
            self.load_cards_for_folder(self.current_folder_id)

    def view_card(self, card_data):
        """查看卡片"""
        Toast.info(self, "查看卡片", f"查看卡片: {card_data.get('name')}")

    def edit_card(self, card_data):
        """编辑卡片"""
        if not self.current_folder_id:
            Toast.info(self, "提示", "请先选择文件夹")
            return
        
        dialog = ToolCardsConfigDialog(self.folder_data, self, self.current_folder_id, card_data)
        if dialog.exec_() == QDialog.Accepted:
            # 数据已直接保存到数据库，只需刷新显示
            self.load_cards_for_folder(self.current_folder_id)

    def copy_card(self, card_data):
        """复制卡片"""
        try:
            # 获取当前文件夹ID
            if not self.current_folder_id:
                Toast.error(self, "复制失败", "请先选择文件夹")
                return
            
            # 创建复制后的卡片数据
            copied_card_data = {
                "folder_id": self.current_folder_id,
                "name": f"{card_data.get('name', '未命名卡片')}_副本",
                "description": card_data.get('description', ''),
                "card_type": card_data.get('type', 'sql'),
                "config": card_data.get('config', {}).copy(),
                "mappings": card_data.get('mappings', {}).copy(),
                "sort_order": 0,
                "enabled": True,
                "created_by": "admin"
            }
            
            # 使用数据库服务创建复制卡片
            new_card_id = self.tool_cards_service.create_card(copied_card_data)
            
            if new_card_id:
                # 刷新卡片显示
                self.load_cards_for_folder(self.current_folder_id)
                Toast.success(self, "复制成功", f"卡片 '{card_data.get('name')}' 已复制")
            else:
                Toast.error(self, "复制失败", "无法创建复制卡片，请检查数据库连接")
                
        except Exception as e:
            print(f"复制卡片时发生错误: {e}")
            Toast.error(self, "复制失败", f"复制过程中发生错误: {str(e)}")

    def delete_card(self, card_data):
        """删除卡片"""
        # 创建消息框对象并设置按钮文本
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认删除")
        msg_box.setText(f"确定要删除卡片 '{card_data.get('name')}' 吗？")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        
        # 正确设置按钮文本
        yes_button = msg_box.button(QMessageBox.Yes)
        no_button = msg_box.button(QMessageBox.No)
        if yes_button:
            yes_button.setText("确定")
        if no_button:
            no_button.setText("取消")
        
        if msg_box.exec_() == QMessageBox.Yes:
            # 使用数据库服务删除卡片
            success = self.tool_cards_service.delete_card(card_data["id"])
            
            if success:
                self.load_cards_for_folder(self.current_folder_id)
                Toast.success(self, "删除成功", f"卡片 '{card_data.get('name')}' 已删除")
            else:
                Toast.error(self, "删除失败", "无法删除卡片，请检查数据库连接")

    def execute_card_with_params(self, card_data, input_params):
        """执行卡片（使用卡片级别的参数）"""
        card_type = card_data.get("type", "sql")
        
        if card_type == "sql":
            self.execute_sql_card_with_params(card_data, input_params)
        elif card_type == "http":
            self.execute_http_card_with_params(card_data, input_params)
        elif card_type == "python":
            self.execute_python_card(card_data)  # 暂时保持原有逻辑
        else:
            # 修复：删除多余的QMessageBox，改为更明确的错误提示
            Toast.error(self, "执行失败", f"不支持的卡片类型: {card_type}")
    
    def execute_sql_card_with_params(self, card_data, input_params):
        """执行SQL卡片（使用卡片级别的参数）"""
        try:
            print(f"[DEBUG] 开始执行SQL卡片（卡片级别参数）: {card_data.get('name')}")
            print(f"[DEBUG] 卡片数据: {json.dumps(card_data, ensure_ascii=False, indent=2)}")
            
            config = card_data.get("config", {})
            
            # 获取SQL查询（支持sql和query字段名）
            sql_query = config.get("sql", "") or config.get("query", "")
            print(f"[DEBUG] 原始SQL查询: {sql_query}")
            
            # 转换变量格式：${variable} -> {variable}
            sql_query = self.convert_sql_variable_format(sql_query)
            
            if not sql_query:
                error_msg = "SQL查询为空，请检查配置中的'sql'或'query'字段"
                print(f"[ERROR] {error_msg}")
                Toast.error(self, "执行失败", error_msg)
                return
            
            # 获取数据库配置（支持字符串配置名和对象配置）
            db_config_data = config.get("database", {})
            print(f"[DEBUG] 数据库配置数据: {db_config_data}")
            
            if not db_config_data:
                error_msg = "数据库配置为空"
                print(f"[ERROR] {error_msg}")
                Toast.error(self, "执行失败", error_msg)
                return
            
            # 判断数据库配置类型
            if isinstance(db_config_data, str):
                # 字符串类型：从配置管理器中获取配置
                db_config_manager = DatabaseConfigManager()
                db_config = db_config_manager.get_config(db_config_data)
                if not db_config:
                    error_msg = f"数据库配置 '{db_config_data}' 不存在"
                    print(f"[ERROR] {error_msg}")
                    Toast.error(self, "执行失败", error_msg)
                    return
            else:
                # 对象类型：直接使用配置对象
                db_config = db_config_data.copy()
                # 规范化配置对象
                if "name" in db_config:
                    db_config["database"] = db_config.pop("name")
                if "port" in db_config:
                    try:
                        db_config["port"] = int(db_config["port"])
                    except (ValueError, TypeError):
                        db_config["port"] = 3306  # 默认端口
                
                print(f"[DEBUG] 规范化后的数据库配置对象: {db_config}")
            
            print(f"[DEBUG] 用户输入参数（卡片级别）: {input_params}")
            
            # 创建SQL工作线程
            self.sql_worker = SQLWorker(
                query_name=card_data.get("name", "SQL查询"),
                connection_params=db_config,
                sql=sql_query,
                variable_pool=input_params
            )
            
            # 连接信号
            self.sql_worker.finished.connect(self.on_sql_execution_finished)
            self.sql_worker.error.connect(self.on_sql_execution_error)
            
            # 启动线程
            self.sql_worker.start()
            
        except Exception as e:
            error_msg = f"执行SQL卡片时发生异常: {str(e)}"
            print(f"[ERROR] {error_msg}")
            Toast.error(self, "执行失败", error_msg)
    
    
    def on_sql_execution_finished(self, query_name, message, result_data):
        """SQL执行完成"""
        print(f"[DEBUG] SQL执行完成: {query_name}")
        print(f"[DEBUG] 执行消息: {message}")
        print(f"[DEBUG] 结果数据行数: {len(result_data)}")
        
        # 将结果转换为JSON格式
        result_json = json.dumps(result_data, ensure_ascii=False, indent=2)
        
        # 创建自定义结果对话框
        self.show_json_result_dialog(query_name, result_json, message)
        
        # 显示完整结果在控制台（便于调试）
        print(f"[DEBUG] SQL执行完整结果: {result_json}")
        
        # 注意：执行成功Toast已移除，避免在关闭弹窗时重复显示
        print(f"[DEBUG] SQL执行流程完成")
    
    def show_json_result_dialog(self, query_name, result_json, message):
        """显示JSON结果对话框"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit
        from PyQt5.QtCore import Qt
        import json
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"执行结果 - {query_name}")
        dialog.setMinimumWidth(1000)  # 增加宽度
        dialog.setMinimumHeight(800)  # 增加高度
        dialog.resize(1200, 900)  # 设置默认大小
        dialog.setModal(True)  # 设置为模态对话框
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowCloseButtonHint)  # 启用关闭按钮
        
        layout = QVBoxLayout(dialog)
        
        # 创建文本显示控件
        json_text = QTextEdit()
        json_text.setReadOnly(True)
        json_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-family: Consolas, Monaco, monospace;
                font-size: 14px;
                padding: 8px;
            }
        """)
        
        # 设置格式化后的JSON文本（使用带颜色的HTML格式）
        try:
            formatted_html = self.format_json_with_colors_interface_style(result_json)
            json_text.setHtml(formatted_html)
        except Exception as e:
            print(f"格式化JSON失败: {e}")
            # 如果格式化失败，使用普通文本显示
            try:
                data = json.loads(result_json)
                formatted_json = json.dumps(data, ensure_ascii=False, indent=2)
                json_text.setPlainText(formatted_json)
            except:
                json_text.setPlainText(result_json)
        
        # 添加文本显示控件到布局
        layout.addWidget(json_text)
        
        dialog.exec_()
    
    def format_json_with_colors_interface_style(self, data):
        """格式化JSON并使用接口工具样式（键紫色，值黑色，字体16px）"""
        import json
        
        def format_value(obj, level=0, indent=2):
            if isinstance(obj, dict):
                items = []
                for key, value in obj.items():
                    # 键使用紫色 #92278f，加粗，字体16px
                    formatted_key = f'<span style="color: #92278f; font-weight: bold; font-size: 16px;">"{key}"</span>'
                    formatted_value = format_value(value, level + 1, indent)
                    items.append(f"{formatted_key}: {formatted_value}")

                indent_str = " " * (indent * level)
                inner_indent = " " * (indent * (level + 1))
                return (
                    "{\n"
                    + inner_indent
                    + (",\n" + inner_indent).join(items)
                    + "\n"
                    + indent_str
                    + "}"
                )
            elif isinstance(obj, list):
                if len(obj) == 0:
                    return "[]"
                
                items = []
                for item in obj:
                    formatted_item = format_value(item, level + 1, indent)
                    items.append(formatted_item)

                indent_str = " " * (indent * level)
                inner_indent = " " * (indent * (level + 1))
                return (
                    "[\n"
                    + inner_indent
                    + (",\n" + inner_indent).join(items)
                    + "\n"
                    + indent_str
                    + "]"
                )
            elif isinstance(obj, str):
                # 字符串值使用绿色 #3ab54a，加粗，字体16px
                return f'<span style="color: #3ab54a; font-weight: bold; font-size: 16px;">"{obj}"</span>'
            elif obj is None:
                return '<span style="color: #3ab54a; font-weight: bold; font-size: 16px;">null</span>'
            elif isinstance(obj, bool):
                return f'<span style="color: #3ab54a; font-weight: bold; font-size: 16px;">{str(obj).lower()}</span>'
            else:
                # 数字等其他类型使用绿色 #3ab54a，加粗，字体16px
                return f'<span style="color: #3ab54a; font-weight: bold; font-size: 16px;">{obj}</span>'

        # 如果传入的是JSON字符串，先解析为Python对象
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                # 如果不是有效的JSON，直接返回原始字符串
                return f'<pre style="font-family: Consolas, Monaco, monospace; font-size: 16px; white-space: pre-wrap; line-height: 1.4;">{data}</pre>'

        formatted_json = format_value(data)
        
        # 包装在pre标签中，保持格式
        result = f'<pre style="font-family: Consolas, Monaco, monospace; font-size: 16px; white-space: pre-wrap; line-height: 1.4;">{formatted_json}</pre>'
        
        return result
    
    def on_sql_execution_error(self, query_name, error_message):
        """SQL执行错误"""
        print(f"[ERROR] SQL执行错误: {query_name}")
        print(f"[ERROR] 错误信息: {error_message}")
        
        Toast.error(self, "执行失败", 
                   f"查询: {query_name}\n错误: {error_message}")
        
        print(f"[ERROR] SQL执行错误处理完成")
    
    def get_input_parameters(self, card_data):
        """获取用户输入的参数（从Tab页面获取，可能会混淆不同卡片的控件）"""
        print(f"[DEBUG] 开始获取用户输入参数（Tab级别）")
        
        input_params = {}
        missing_required_fields = []
        mappings = card_data.get("mappings", {})
        card_type = card_data.get("type", "sql")  # 获取卡片类型
        print(f"[DEBUG] 映射配置: {mappings}, 卡片类型: {card_type}")
        
        # 简化方法：直接查找所有输入控件并匹配字段名
        # 查找所有输入控件
        line_edits = self.findChildren(QLineEdit)
        combo_boxes = self.findChildren(QComboBox)
        multi_select_combos = self.findChildren(MultiSelectComboBox)
                
        # 遍历所有字段，尝试匹配输入控件
        for field_name, field_config in mappings.items():
            # 获取显示名称用于查找
            if isinstance(field_config, str):
                display_name = field_config.split('-')[0] if '-' in field_config else field_name
                required = False  # 旧格式不支持必填
            else:
                display_name = field_config.get("display_name", field_name)
                required = field_config.get("required", False)
            
            print(f"[DEBUG] 查找字段: {field_name}, 显示名: {display_name}, 必填: {required}")
            
            # 查找对应的输入控件
            field_value = None
            
            # 查找输入框
            for line_edit in line_edits:
                placeholder = line_edit.placeholderText()
                if display_name in placeholder or field_name in placeholder:
                    field_value = line_edit.text().strip()
                    print(f"[DEBUG] 从输入框获取到字段值: {field_name} = {field_value}")
                    break
            
            # 如果输入框没找到，查找多选框
            if field_value is None:
                for multi_combo in multi_select_combos:
                    # 检查多选框是否有相关文本
                    current_text = multi_combo.lineEdit().text()
                    if current_text and current_text != "请选择":
                        # 获取多选框的选中值
                        selected_data = multi_combo.get_selected_data()
                        if selected_data:
                            # 根据卡片类型差异化处理多选框值
                            if card_type == "http":
                                # HTTP类型：作为列表传递
                                field_value = selected_data
                            elif card_type == "sql":
                                # SQL类型：生成正确的IN条件格式，如 "'POST','GET'"
                                # 用户需要在SQL中写：method in (${method})
                                # 系统提供：'POST','GET'
                                quoted_values = [f"'{value}'" for value in selected_data]
                                field_value = ",".join(quoted_values)
                            else:
                                # 其他类型：默认逗号分隔字符串
                                field_value = ",".join(selected_data)
                        print(f"[DEBUG] 从多选框获取到字段值: {field_name} = {field_value} (显示文本: {current_text}, 类型: {card_type})")
                        break
            
            # 如果多选框没找到，查找下拉框
            if field_value is None:
                for combo_box in combo_boxes:
                    # 检查下拉框是否有相关文本
                    current_text = combo_box.currentText()
                    if current_text and current_text != "请选择":
                        # 获取下拉框的实际值（itemData），如果没有设置itemData则使用显示文本
                        current_data = combo_box.currentData()
                        if current_data is not None:
                            field_value = current_data
                        else:
                            field_value = current_text
                        print(f"[DEBUG] 从下拉框获取到字段值: {field_name} = {field_value} (显示文本: {current_text})")
                        break
            
            # 必填校验
            if required and (field_value is None or field_value == ""):
                missing_required_fields.append(display_name)
                print(f"[WARNING] 必填字段 '{display_name}' 为空")
            
            if field_value is not None:
                input_params[field_name] = field_value
            else:
                print(f"[WARNING] 未找到字段 '{field_name}' 的输入控件")
                # 提供默认值（空字符串）
                input_params[field_name] = ""
        
        # 如果有必填字段为空，显示错误信息
        if missing_required_fields:
            field_names = ", ".join(missing_required_fields)
            Toast.error(self, f"{field_names}必填")
            return None
        
        print(f"[DEBUG] 最终获取到的输入参数: {input_params}")
        return input_params
    
    def convert_sql_variable_format(self, sql):
        """将SQL中的${variable}格式转换为{variable}格式"""
        import re
        
        # 匹配 ${variable} 格式并转换为 {variable}
        # 同时处理被引号包围和未被引号包围的变量
        
        # 先处理被单引号包围的变量：'${variable}' -> {variable}
        converted_sql = re.sub(r"'\$\{(\w+)\}'", r"{\1}", sql)
        
        # 再处理未被引号包围的变量：${variable} -> {variable}
        converted_sql = re.sub(r"\$\{(\w+)\}", r"{\1}", converted_sql)
        
        print(f"[DEBUG] 变量格式转换: {sql} -> {converted_sql}")
        return converted_sql
    
    def execute_http_card_with_params(self, card_data, input_params):
        """执行HTTP卡片（使用卡片级别的参数）"""
        try:
            # 获取卡片配置
            config = card_data.get("config", {})
            
            # 创建配置的深拷贝以避免修改原始数据
            import copy
            config_copy = copy.deepcopy(config)
            
            # 从拷贝中获取请求参数
            url = config_copy.get("url", "")
            method = config_copy.get("method", "GET").upper()
            headers = config_copy.get("headers", {})
            body = config_copy.get("body", {})
            
            if not url:
                Toast.error(self, "执行失败", "HTTP卡片配置错误: URL不能为空")
                return
            
            # 处理变量替换（使用传入的参数）
            mappings = card_data.get("mappings", {})
            if mappings and input_params:
                print(f"[DEBUG] HTTP卡片执行 - 使用传入的参数: {input_params}")
                
                # 替换URL中的变量
                url = self._replace_http_variables(url, input_params)
                
                # 替换请求头中的变量
                if headers:
                    headers = self._replace_http_variables_in_dict(headers, input_params)
                
                # 替换请求体中的变量
                if body:
                    body = self._replace_http_variables_in_dict(body, input_params)
            
            # 打印调试信息：变量替换后的请求信息
            print("=" * 60)
            print("HTTP卡片执行调试信息:")
            print(f"请求URL（变量替换后）: {url}")
            print(f"请求方法: {method}")
            print(f"请求头（变量替换后）: {json.dumps(headers, ensure_ascii=False, indent=2)}")
            print(f"请求体（变量替换后）: {json.dumps(body, ensure_ascii=False, indent=2)}")
            print("=" * 60)
            
            # 执行HTTP请求
            response = self._execute_http_request(method, url, headers, body)
            
            # 显示结果 - 使用与SQL卡片相同的结果弹窗
            self._show_http_response_in_json_dialog(response, card_data.get("name"))
            
        except Exception as e:
            Toast.error(self, "执行失败", f"HTTP卡片执行失败: {str(e)}")
    
    def _get_http_input_parameters(self, mappings):
        """获取HTTP参数输入"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox, QLineEdit, QComboBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("输入参数")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        input_widgets = {}
        
        # 按顺序字段排序参数映射
        sorted_mappings = sorted(
            mappings.items(),
            key=lambda x: x[1].get("order", 0) if isinstance(x[1], dict) else 0
        )
        
        for field_name, mapping_config in sorted_mappings:
            display_name = mapping_config.get("display_name", field_name)
            required = mapping_config.get("required", False)
            
            # 创建标签并添加必填标识
            label = QLabel()
            if required:
                # 必填参数：红色星号
                label.setText(f"<span style='color: red;'>*</span>{display_name}:")
                label.setStyleSheet("QLabel { color: #333333; font-weight: bold; }")
            else:
                # 非必填参数：普通样式
                label.setText(f"{display_name}:")
                label.setStyleSheet("QLabel { color: #333333; }")
            
            if mapping_config.get("type") == "select":
                # 下拉框
                combo = QComboBox()
                options = mapping_config.get("options", [])
                for option in options:
                    combo.addItem(option.get("description", ""), option.get("value", ""))
                input_widgets[field_name] = combo
                form_layout.addRow(label, combo)
            else:
                # 输入框
                edit = QLineEdit()
                edit.setPlaceholderText(mapping_config.get("default_value", ""))
                input_widgets[field_name] = edit
                form_layout.addRow(label, edit)
        
        layout.addLayout(form_layout)
        
        # 按钮区域
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec_() == QDialog.Accepted:
            # 收集输入值并进行必填校验
            params = {}
            missing_required_fields = []
            
            for field_name, widget in input_widgets.items():
                mapping_config = next((m[1] for m in sorted_mappings if m[0] == field_name), {})
                required = mapping_config.get("required", False)
                
                if isinstance(widget, QComboBox):
                    value = widget.currentData()
                else:
                    value = widget.text()
                
                # 必填校验
                is_empty = False
                if value is None:
                    is_empty = True
                elif isinstance(value, str) and value == "":
                    is_empty = True
                elif isinstance(value, list) and len(value) == 0:
                    is_empty = True
                
                if required and is_empty:
                    missing_required_fields.append(mapping_config.get("display_name", field_name))
                
                params[field_name] = value
            
            # 如果有必填字段为空，显示错误信息
            if missing_required_fields:
                field_names = ", ".join(missing_required_fields)
                Toast.error(self, f"{field_names}必填")
                return None
            
            return params
        else:
            return None
    
    def _replace_http_variables(self, text, params):
        """替换HTTP变量"""
        for key, value in params.items():
            text = text.replace(f"${{{key}}}", str(value))
        return text
    
    def _replace_http_variables_in_dict(self, data, params):
        """替换字典中的HTTP变量"""
        import copy
        
        # 创建深拷贝以避免修改原始数据
        data_copy = copy.deepcopy(data)
        
        if isinstance(data_copy, dict):
            for key, value in data_copy.items():
                data_copy[key] = self._replace_http_variables_in_dict(value, params)
        elif isinstance(data_copy, str):
            return self._replace_http_variables(data_copy, params)
        elif isinstance(data_copy, list):
            return [self._replace_http_variables_in_dict(item, params) for item in data_copy]
        return data_copy
    
    def _execute_http_request(self, method, url, headers, body):
        """执行HTTP请求"""
        session = requests.Session()
        
        # 设置默认请求头
        if not headers.get("Content-Type") and method in ["POST", "PUT", "PATCH"]:
            headers["Content-Type"] = "application/json"
        
        # 执行请求
        if method == "GET":
            response = session.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = session.post(url, json=body, headers=headers, timeout=30)
        elif method == "PUT":
            response = session.put(url, json=body, headers=headers, timeout=30)
        elif method == "DELETE":
            response = session.delete(url, headers=headers, timeout=30)
        else:
            response = session.get(url, headers=headers, timeout=30)
        
        return response
    
    def _show_http_response(self, response, card_name):
        """显示HTTP响应结果"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QLabel, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"HTTP响应 - {card_name}")
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # 状态信息
        status_label = QLabel(f"状态码: {response.status_code} - {response.reason}")
        layout.addWidget(status_label)
        
        # 响应内容
        response_edit = QTextEdit()
        response_edit.setReadOnly(True)
        
        try:
            # 尝试解析JSON
            response_json = response.json()
            response_text = json.dumps(response_json, ensure_ascii=False, indent=2)
        except:
            # 如果不是JSON，显示原始文本
            response_text = response.text
        
        response_edit.setPlainText(response_text)
        layout.addWidget(response_edit)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.exec_()
    
    def _show_http_response_in_json_dialog(self, response, card_name):
        """显示HTTP响应结果 - 使用JSON结果对话框"""
        try:
            # 构建HTTP响应结果数据
            result_data = {
                "status_code": response.status_code,
                "reason": response.reason,
                "headers": dict(response.headers),
                "elapsed": response.elapsed.total_seconds() if response.elapsed else 0
            }
            
            # 处理响应体
            try:
                # 尝试解析JSON响应体
                response_json = response.json()
                result_data["body"] = response_json
                result_data["body_type"] = "json"
            except:
                # 如果不是JSON，显示原始文本
                result_data["body"] = response.text
                result_data["body_type"] = "text"
            
            # 将结果转换为JSON格式
            result_json = json.dumps(result_data, ensure_ascii=False, indent=2)
            
            # 构建执行消息
            message = f"HTTP请求执行成功 - 状态码: {response.status_code}"
            
            # 使用与SQL卡片相同的结果对话框
            self.show_json_result_dialog(card_name, result_json, message)
            
        except Exception as e:
            # 如果出错，显示错误信息
            error_msg = f"处理HTTP响应时出错: {str(e)}"
            Toast.error(self, "错误", error_msg)
    
    def execute_python_card(self, card_data):
        """执行Python卡片"""
        pass

    def get_icon(self, icon_name):
        """获取图标"""
        try:
            # 打包后路径处理：尝试从 PyInstaller 临时解压目录加载
            if getattr(sys, "frozen", False):
                # 打包后的可执行文件路径
                base_path = sys._MEIPASS
                # 尝试从打包后的 resources/icons 目录加载
                icon_path = os.path.join(
                    base_path, "src", "resources", "icons", icon_name
                )
                if os.path.exists(icon_path):
                    return QIcon(icon_path)

                # 尝试直接加载图标文件
                icon_path = os.path.join(base_path, icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)

                # 尝试从当前目录加载
                icon_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..", "..", "resources", "icons", icon_name
                )
                if os.path.exists(icon_path):
                    return QIcon(icon_path)

            # 开发环境：使用相对路径访问图标资源
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            icon_path = os.path.join(base_dir, "resources", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
        except:
            pass
        return QIcon()