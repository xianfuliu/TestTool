import json
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QWidget, QGroupBox, QFormLayout, QLineEdit, \
    QTextEdit, QHBoxLayout, QLabel, QPushButton, QMessageBox

from src.ui.widgets.no_wheel_combo_box import NoWheelComboBox
from src.ui.widgets.toast_tips import Toast


class InterfaceConfigDialog(QDialog):
    """接口配置对话框"""

    def __init__(self, interface_name, interface_config, parent=None):
        super().__init__(parent)
        self.interface_name = interface_name
        self.interface_config = interface_config.copy() if interface_config else {}
        self.setWindowTitle(f"编辑接口 - {interface_name}")
        self.setModal(True)
        self.setFixedSize(800, 700)
        self.init_ui()
        self.load_interface_config()

    def init_ui(self):
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setContentsMargins(5, 5, 5, 5)

        # 基础配置
        basic_group = QGroupBox("基础信息")
        basic_group.setContentsMargins(8, 12, 8, 8)
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(8)
        basic_layout.setVerticalSpacing(8)

        # 接口名称（只读，移到基础信息中）
        self.interface_name_edit = QLineEdit()
        self.interface_name_edit.setText(self.interface_name)
        self.interface_name_edit.setReadOnly(True)  # 设置为只读
        self.interface_name_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")
        self.interface_name_edit.setFixedWidth(300)
        basic_layout.addRow("接口名称:", self.interface_name_edit)

        # 接口地址
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("请输入接口URL")
        self.url_edit.setFixedWidth(500)
        basic_layout.addRow("接口地址:", self.url_edit)

        # 请求方式
        self.method_combo = NoWheelComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE"])
        self.method_combo.setFixedWidth(120)
        basic_layout.addRow("请求方式:", self.method_combo)

        # 请求头配置
        self.headers_edit = QTextEdit()
        self.headers_edit.setPlaceholderText('{"Content-Type": "application/json"}')
        self.headers_edit.setFixedHeight(80)
        basic_layout.addRow("请求头:", self.headers_edit)

        self.scroll_layout.addWidget(basic_group)

        # 请求类型选择
        request_type_group = QGroupBox("请求体")
        request_type_group.setContentsMargins(8, 12, 8, 8)
        request_type_layout = QVBoxLayout(request_type_group)
        request_type_layout.setSpacing(8)

        # 请求体类型选择
        request_type_row_layout = QHBoxLayout()
        request_type_row_layout.setSpacing(5)
        type_label = QLabel("类型:")
        type_label.setFixedWidth(70)
        request_type_row_layout.addWidget(type_label)
        self.request_type_combo = NoWheelComboBox()
        self.request_type_combo.addItems(["普通", "条件"])
        self.request_type_combo.setFixedWidth(100)
        self.request_type_combo.currentTextChanged.connect(self.on_request_type_changed)
        request_type_row_layout.addWidget(self.request_type_combo)
        request_type_row_layout.addStretch()
        request_type_layout.addLayout(request_type_row_layout)

        # 普通请求体
        self.normal_body_group = QGroupBox("普通请求体")
        self.normal_body_group.setContentsMargins(5, 10, 5, 5)
        normal_body_layout = QVBoxLayout(self.normal_body_group)
        self.normal_body_edit = QTextEdit()
        self.normal_body_edit.setPlaceholderText('{"key": "value", "param": "{field_name}"}')
        self.normal_body_edit.setFixedHeight(150)
        normal_body_layout.addWidget(self.normal_body_edit)
        request_type_layout.addWidget(self.normal_body_group)

        # 条件请求体
        self.conditional_body_group = QGroupBox("条件请求体")
        self.conditional_body_group.setContentsMargins(5, 10, 5, 5)
        conditional_body_layout = QVBoxLayout(self.conditional_body_group)
        conditional_body_layout.setSpacing(8)

        # 条件字段选择
        condition_field_layout = QHBoxLayout()
        condition_field_layout.setSpacing(5)
        field_label = QLabel("条件字段:")
        field_label.setFixedWidth(60)
        condition_field_layout.addWidget(field_label)
        self.condition_field_combo = NoWheelComboBox()
        self.condition_field_combo.setFixedWidth(200)
        condition_field_layout.addWidget(self.condition_field_combo)
        condition_field_layout.addStretch()
        conditional_body_layout.addLayout(condition_field_layout)

        # 条件cases配置
        cases_label = QLabel("条件Cases:")
        conditional_body_layout.addWidget(cases_label)
        self.conditional_cases_edit = QTextEdit()
        self.conditional_cases_edit.setPlaceholderText(
            '{\n  "case1_value": {\n    "field1": "value1"\n  },\n  "case2_value": {\n    "field1": "value2"\n  }\n}'
        )
        self.conditional_cases_edit.setFixedHeight(120)
        conditional_body_layout.addWidget(self.conditional_cases_edit)

        request_type_layout.addWidget(self.conditional_body_group)
        self.scroll_layout.addWidget(request_type_group)

        # 响应映射配置
        response_mapping_group = QGroupBox("响应映射")
        response_mapping_group.setContentsMargins(8, 12, 8, 8)
        response_mapping_layout = QVBoxLayout(response_mapping_group)
        self.response_mapping_edit = QTextEdit()
        self.response_mapping_edit.setPlaceholderText('{"field_key": "response.path", "amount": "data.amount"}')
        self.response_mapping_edit.setFixedHeight(80)
        response_mapping_layout.addWidget(self.response_mapping_edit)
        self.scroll_layout.addWidget(response_mapping_group)

        # 字段类型配置
        field_types_group = QGroupBox("字段类型")
        field_types_group.setContentsMargins(8, 12, 8, 8)
        field_types_layout = QVBoxLayout(field_types_group)
        self.field_types_edit = QTextEdit()
        self.field_types_edit.setPlaceholderText('{"amount": "int", "rate": "float", "is_valid": "bool"}')
        self.field_types_edit.setFixedHeight(80)
        field_types_layout.addWidget(self.field_types_edit)
        self.scroll_layout.addWidget(field_types_group)

        # 添加弹性空间
        self.scroll_layout.addStretch()

        # 设置滚动区域
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_config)
        self.save_btn.setFixedWidth(80)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setFixedWidth(80)

        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(button_layout)

        # 初始显示状态
        self.on_request_type_changed("普通")

    def on_request_type_changed(self, request_type):
        """请求类型改变事件"""
        if request_type == "普通":
            self.normal_body_group.setVisible(True)
            self.conditional_body_group.setVisible(False)
        else:
            self.normal_body_group.setVisible(False)
            self.conditional_body_group.setVisible(True)

    def load_interface_config(self):
        """加载接口配置"""
        try:
            # 基本配置
            self.url_edit.setText(self.interface_config.get("url", ""))
            self.method_combo.setCurrentText(self.interface_config.get("method", "POST"))

            # 请求头
            headers = self.interface_config.get("headers", {})
            if headers:
                self.headers_edit.setPlainText(json.dumps(headers, ensure_ascii=False, indent=2))
            else:
                # 设置默认请求头
                default_headers = {"Content-Type": "application/json"}
                self.headers_edit.setPlainText(json.dumps(default_headers, ensure_ascii=False, indent=2))

            # 加载条件字段选项（仅限下拉框字段）
            self.condition_field_combo.clear()
            self.condition_field_combo.addItem("")  # 空选项

            # 从父窗口的布局列表中获取仅限下拉框字段
            if hasattr(self.parent(), 'layout_list'):
                for i in range(self.parent().layout_list.count()):
                    item = self.parent().layout_list.item(i)
                    layout_data = item.data(Qt.UserRole)
                    # 只添加类型为"combo"的下拉框字段
                    if layout_data and layout_data.get("type") == "combo":
                        field_key = layout_data.get("key")
                        field_label = layout_data.get("label", field_key)
                        display_text = f"{field_label} ({field_key})"
                        self.condition_field_combo.addItem(display_text, field_key)

            # 判断请求类型并加载相应配置
            if "conditional_body" in self.interface_config:
                # 条件请求模板
                self.request_type_combo.setCurrentText("条件")
                conditional_body = self.interface_config["conditional_body"]

                # 条件字段
                field = conditional_body.get("field", "")
                # 在条件字段下拉框中查找对应的项
                index = self.condition_field_combo.findData(field)
                if index >= 0:
                    self.condition_field_combo.setCurrentIndex(index)
                else:
                    # 如果没有找到，检查是否为下拉框字段
                    if field:
                        # 如果不是下拉框字段，清空选择
                        self.condition_field_combo.setCurrentIndex(0)
                        # 提示用户
                        Toast.warning(self, f"条件字段 '{field}' 不是下拉框字段，已清空选择")

                # 条件cases
                cases = conditional_body.get("cases", {})
                if cases:
                    self.conditional_cases_edit.setPlainText(json.dumps(cases, ensure_ascii=False, indent=2))
                else:
                    self.conditional_cases_edit.setPlainText("")

                # 设置普通请求体为空
                self.normal_body_edit.setPlainText("")
            else:
                # 普通请求模板
                self.request_type_combo.setCurrentText("普通")
                body_template = self.interface_config.get("body_template", {})
                if body_template:
                    self.normal_body_edit.setPlainText(json.dumps(body_template, ensure_ascii=False, indent=2))
                else:
                    # 设置默认请求体
                    default_body = {}
                    self.normal_body_edit.setPlainText(json.dumps(default_body, ensure_ascii=False, indent=2))

                # 设置条件请求体为空
                self.conditional_cases_edit.setPlainText("")

            # 响应映射
            response_mapping = self.interface_config.get("response_mapping", {})
            if response_mapping:
                self.response_mapping_edit.setPlainText(json.dumps(response_mapping, ensure_ascii=False, indent=2))
            else:
                self.response_mapping_edit.setPlainText("")

            # 字段类型配置
            field_types = self.interface_config.get("field_types", {})
            if field_types:
                self.field_types_edit.setPlainText(json.dumps(field_types, ensure_ascii=False, indent=2))
            else:
                self.field_types_edit.setPlainText("")

            # 初始显示状态
            current_request_type = self.request_type_combo.currentText()
            self.on_request_type_changed(current_request_type)

        except Exception as e:
            Toast.warning(self, f"加载接口配置失败: {str(e)}")
            # 设置默认值以防出错
            self.url_edit.setText("")
            self.method_combo.setCurrentText("POST")
            self.headers_edit.setPlainText('{"Content-Type": "application/json"}')
            self.normal_body_edit.setPlainText("")
            self.conditional_cases_edit.setPlainText("")
            self.response_mapping_edit.setPlainText("")
            self.field_types_edit.setPlainText("")
            self.request_type_combo.setCurrentText("普通")

    def save_config(self):
        """保存接口配置"""
        try:
            # 基本配置
            self.interface_config["url"] = self.url_edit.text().strip()
            self.interface_config["method"] = self.method_combo.currentText()

            # 请求头
            try:
                headers_text = self.headers_edit.toPlainText().strip()
                if headers_text:
                    self.interface_config["headers"] = json.loads(headers_text)
                else:
                    self.interface_config["headers"] = {"Content-Type": "application/json"}
            except json.JSONDecodeError:
                Toast.warning(self, "请求头格式错误，必须是有效的JSON")
                return

            # 根据请求类型保存请求体配置
            if self.request_type_combo.currentText() == "普通":
                # 移除条件请求配置
                if "conditional_body" in self.interface_config:
                    del self.interface_config["conditional_body"]

                # 保存普通请求体
                try:
                    body_text = self.normal_body_edit.toPlainText().strip()
                    if body_text:
                        self.interface_config["body_template"] = json.loads(body_text)
                    else:
                        self.interface_config["body_template"] = {}
                except json.JSONDecodeError:
                    Toast.warning(self, "请求体格式错误，必须是有效的JSON")
                    return
            else:
                # 条件请求模板
                # 获取条件字段的实际值
                selected_data = self.condition_field_combo.currentData()
                field_value = selected_data if selected_data else self.condition_field_combo.currentText()

                # 验证条件字段是否为空
                if not field_value:
                    Toast.warning(self, "请选择条件字段")
                    return

                # 验证条件字段是否为下拉框字段
                if hasattr(self.parent(), 'layout_list'):
                    is_combo_field = False
                    for i in range(self.parent().layout_list.count()):
                        item = self.parent().layout_list.item(i)
                        layout_data = item.data(Qt.UserRole)
                        if (layout_data and layout_data.get("type") == "combo" and
                                layout_data.get("key") == field_value):
                            is_combo_field = True
                            break

                    if not is_combo_field:
                        Toast.warning(self, "条件字段必须是下拉框字段")
                        return

                conditional_body = {
                    "field": field_value,
                    "cases": {}
                }

                try:
                    cases_text = self.conditional_cases_edit.toPlainText().strip()
                    if cases_text:
                        conditional_body["cases"] = json.loads(cases_text)

                    self.interface_config["conditional_body"] = conditional_body
                    # 移除普通请求体
                    if "body_template" in self.interface_config:
                        del self.interface_config["body_template"]
                except json.JSONDecodeError:
                    Toast.warning(self, "条件Cases格式错误，必须是有效的JSON")
                    return

            # 响应映射
            try:
                mapping_text = self.response_mapping_edit.toPlainText().strip()
                if mapping_text:
                    self.interface_config["response_mapping"] = json.loads(mapping_text)
                else:
                    self.interface_config["response_mapping"] = {}
            except json.JSONDecodeError:
                Toast.warning(self, "响应映射格式错误，必须是有效的JSON")
                return

            # 字段类型
            try:
                field_types_text = self.field_types_edit.toPlainText().strip()
                if field_types_text:
                    self.interface_config["field_types"] = json.loads(field_types_text)
                else:
                    self.interface_config["field_types"] = {}
            except json.JSONDecodeError:
                Toast.warning(self, "字段类型格式错误，必须是有效的JSON")
                return

            self.accept()

        except Exception as e:
            Toast.error(self, f"保存配置失败: {str(e)}")
