from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QWidget, QLabel, QLineEdit, QTextEdit,
                             QSpinBox, QCheckBox, QPushButton, QGroupBox,
                             QFormLayout, QListWidget, QListWidgetItem,
                             QMessageBox, QScrollArea, QGridLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import json

from src.ui.widgets.no_wheel_combo_box import NoWheelComboBox


class ToolCardsConfigDialog(QDialog):
    def __init__(self, config_data, parent=None, edit_card_data=None, view_mode=False):
        super().__init__(parent)
        self.config_data = json.loads(json.dumps(config_data))  # 深拷贝
        self.edit_card_data = edit_card_data
        self.view_mode = view_mode
        self.current_card_data = None

        self.setWindowTitle("卡片工具配置")
        self.setModal(True)
        self.resize(900, 700)

        self.init_ui()

        if edit_card_data:
            self.load_card_data(edit_card_data)

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 创建选项卡
        tab_widget = QTabWidget()

        # 业务线配置选项卡
        business_tab = self.create_business_tab()
        tab_widget.addTab(business_tab, "业务线配置")

        # 卡片配置选项卡
        cards_tab = self.create_cards_tab()
        tab_widget.addTab(cards_tab, "卡片配置")

        layout.addWidget(tab_widget)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        if not self.view_mode:
            self.save_btn = QPushButton("保存")
            self.save_btn.clicked.connect(self.accept)
            button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("关闭")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def create_business_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 业务线管理区域
        business_group = QGroupBox("业务线管理")
        business_layout = QVBoxLayout(business_group)

        # 业务线列表
        business_list_layout = QHBoxLayout()

        self.business_list = QListWidget()
        self.business_list.currentItemChanged.connect(self.on_business_selected)
        business_list_layout.addWidget(self.business_list)

        # 业务线操作按钮
        business_btn_layout = QVBoxLayout()

        self.add_business_btn = QPushButton("新增业务线")
        self.add_business_btn.clicked.connect(self.add_business_line)
        business_btn_layout.addWidget(self.add_business_btn)

        self.edit_business_btn = QPushButton("编辑业务线")
        self.edit_business_btn.clicked.connect(self.edit_business_line)
        business_btn_layout.addWidget(self.edit_business_btn)

        self.delete_business_btn = QPushButton("删除业务线")
        self.delete_business_btn.clicked.connect(self.delete_business_line)
        business_btn_layout.addWidget(self.delete_business_btn)

        business_btn_layout.addStretch()
        business_list_layout.addLayout(business_btn_layout)

        business_layout.addLayout(business_list_layout)

        # 子业务模块管理
        sub_business_group = QGroupBox("子业务模块管理")
        sub_business_layout = QVBoxLayout(sub_business_group)

        sub_business_list_layout = QHBoxLayout()

        self.sub_business_list = QListWidget()
        sub_business_list_layout.addWidget(self.sub_business_list)

        # 子业务操作按钮
        sub_business_btn_layout = QVBoxLayout()

        self.add_sub_business_btn = QPushButton("新增子模块")
        self.add_sub_business_btn.clicked.connect(self.add_sub_business)
        sub_business_btn_layout.addWidget(self.add_sub_business_btn)

        self.edit_sub_business_btn = QPushButton("编辑子模块")
        self.edit_sub_business_btn.clicked.connect(self.edit_sub_business)
        sub_business_btn_layout.addWidget(self.edit_sub_business_btn)

        self.delete_sub_business_btn = QPushButton("删除子模块")
        self.delete_sub_business_btn.clicked.connect(self.delete_sub_business)
        sub_business_btn_layout.addWidget(self.delete_sub_business_btn)

        sub_business_btn_layout.addStretch()
        sub_business_list_layout.addLayout(sub_business_btn_layout)

        sub_business_layout.addLayout(sub_business_list_layout)

        layout.addWidget(business_group)
        layout.addWidget(sub_business_group)

        # 刷新业务线列表
        self.refresh_business_list()

        return widget

    def create_cards_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 卡片选择区域
        card_selection_layout = QHBoxLayout()

        card_selection_layout.addWidget(QLabel("选择业务线:"))
        self.business_combo = NoWheelComboBox()
        self.business_combo.currentTextChanged.connect(self.on_business_combo_changed)
        card_selection_layout.addWidget(self.business_combo)

        card_selection_layout.addWidget(QLabel("选择子模块:"))
        self.sub_business_combo = NoWheelComboBox()
        self.sub_business_combo.currentTextChanged.connect(self.on_sub_business_combo_changed)
        card_selection_layout.addWidget(self.sub_business_combo)

        card_selection_layout.addStretch()

        layout.addLayout(card_selection_layout)

        # 卡片列表
        cards_group = QGroupBox("卡片列表")
        cards_layout = QVBoxLayout(cards_group)

        cards_list_layout = QHBoxLayout()

        self.cards_list = QListWidget()
        self.cards_list.currentItemChanged.connect(self.on_card_selected)
        cards_list_layout.addWidget(self.cards_list)

        # 卡片操作按钮
        cards_btn_layout = QVBoxLayout()

        self.add_card_btn = QPushButton("新增卡片")
        self.add_card_btn.clicked.connect(self.add_card)
        cards_btn_layout.addWidget(self.add_card_btn)

        self.edit_card_btn = QPushButton("编辑卡片")
        self.edit_card_btn.clicked.connect(self.edit_card)
        cards_btn_layout.addWidget(self.edit_card_btn)

        self.copy_card_btn = QPushButton("复制卡片")
        self.copy_card_btn.clicked.connect(self.copy_card)
        cards_btn_layout.addWidget(self.copy_card_btn)

        self.delete_card_btn = QPushButton("删除卡片")
        self.delete_card_btn.clicked.connect(self.delete_card)
        cards_btn_layout.addWidget(self.delete_card_btn)

        cards_btn_layout.addStretch()
        cards_list_layout.addLayout(cards_btn_layout)

        cards_layout.addLayout(cards_list_layout)

        layout.addWidget(cards_group)

        # 卡片详情区域
        self.card_details_group = QGroupBox("卡片详情")
        self.card_details_layout = QVBoxLayout(self.card_details_group)

        # 创建卡片详情表单
        self.create_card_details_form()

        layout.addWidget(self.card_details_group)

        # 刷新业务线下拉框
        self.refresh_business_combo()

        return widget

    def create_card_details_form(self):
        # 清空现有布局
        for i in reversed(range(self.card_details_layout.count())):
            self.card_details_layout.itemAt(i).widget().setParent(None)

        if self.view_mode:
            # 查看模式 - 只读显示
            self.create_card_details_view()
        else:
            # 编辑模式 - 可编辑表单
            self.create_card_details_edit()

    def create_card_details_view(self):
        """创建卡片详情查看界面"""
        if not self.current_card_data:
            return

        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # 基本信息
        basic_info_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_info_group)

        basic_layout.addRow("卡片名称:", QLabel(self.current_card_data.get('title', '')))
        basic_layout.addRow("卡片类型:", QLabel(self.get_type_display()))
        basic_layout.addRow("描述:", QLabel(self.current_card_data.get('description', '')))
        basic_layout.addRow("超时时间:", QLabel(f"{self.current_card_data.get('timeout', 5000)}ms"))
        basic_layout.addRow("锁定状态:", QLabel("是" if self.current_card_data.get('locked', False) else "否"))

        scroll_layout.addWidget(basic_info_group)

        # 配置信息
        config_group = QGroupBox("配置信息")
        config_layout = QFormLayout(config_group)

        card_type = self.current_card_data.get('type', 'sql')
        if card_type.startswith('sql'):
            config_layout.addRow("数据库连接:", QLabel(self.current_card_data.get('database', '')))
            config_layout.addRow("SQL语句:", QLabel(self.current_card_data.get('sql', '')))
        elif card_type == 'http':
            config_layout.addRow("请求URL:", QLabel(self.current_card_data.get('url', '')))
            config_layout.addRow("请求方法:", QLabel(self.current_card_data.get('method', 'GET')))
        elif card_type == 'python':
            config_layout.addRow("Python类:", QLabel(self.current_card_data.get('class_name', '')))
            config_layout.addRow("方法名:", QLabel(self.current_card_data.get('method_name', '')))

        scroll_layout.addWidget(config_group)
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        self.card_details_layout.addWidget(scroll_area)

    def create_card_details_edit(self):
        """创建卡片详情编辑界面"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # 基本信息
        basic_info_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_info_group)

        self.card_title_edit = QLineEdit()
        basic_layout.addRow("卡片名称:", self.card_title_edit)

        self.card_type_combo = NoWheelComboBox()
        self.card_type_combo.addItems(["SQL查询", "SQL更新", "SQL删除", "HTTP接口", "Python类"])
        self.card_type_combo.currentTextChanged.connect(self.on_card_type_changed)
        basic_layout.addRow("卡片类型:", self.card_type_combo)

        self.card_desc_edit = QTextEdit()
        self.card_desc_edit.setMaximumHeight(80)
        basic_layout.addRow("描述:", self.card_desc_edit)

        timeout_layout = QHBoxLayout()
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(100, 60000)
        self.timeout_spin.setValue(5000)
        self.timeout_spin.setSuffix("ms")
        timeout_layout.addWidget(self.timeout_spin)
        timeout_layout.addStretch()
        basic_layout.addRow("超时时间:", timeout_layout)

        self.locked_check = QCheckBox("锁定卡片（锁定后首页不可删除编辑）")
        basic_layout.addRow("锁定状态:", self.locked_check)

        scroll_layout.addWidget(basic_info_group)

        # 配置信息
        self.config_group = QGroupBox("配置信息")
        self.config_layout = QFormLayout(self.config_group)

        # 初始创建SQL配置
        self.create_sql_config()

        scroll_layout.addWidget(self.config_group)
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        self.card_details_layout.addWidget(scroll_area)

        # 保存按钮
        if self.current_card_data:
            save_btn_layout = QHBoxLayout()
            save_btn_layout.addStretch()
            self.save_card_btn = QPushButton("保存卡片")
            self.save_card_btn.clicked.connect(self.save_current_card)
            save_btn_layout.addWidget(self.save_card_btn)
            scroll_layout.addLayout(save_btn_layout)

    def create_sql_config(self):
        """创建SQL配置表单"""
        # 清空现有配置
        for i in reversed(range(self.config_layout.count())):
            self.config_layout.itemAt(i).widget().setParent(None)

        self.database_combo = NoWheelComboBox()
        # TODO: 从数据库配置中加载可用的数据库连接
        self.database_combo.addItems(["default_db", "test_db"])
        self.config_layout.addRow("数据库连接:", self.database_combo)

        self.sql_editor = QTextEdit()
        self.sql_editor.setMaximumHeight(120)
        self.config_layout.addRow("SQL语句:", self.sql_editor)

    def create_http_config(self):
        """创建HTTP配置表单"""
        # 清空现有配置
        for i in reversed(range(self.config_layout.count())):
            self.config_layout.itemAt(i).widget().setParent(None)

        self.url_edit = QLineEdit()
        self.config_layout.addRow("请求URL:", self.url_edit)

        self.method_combo = NoWheelComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE"])
        self.config_layout.addRow("请求方法:", self.method_combo)

        self.headers_edit = QTextEdit()
        self.headers_edit.setMaximumHeight(80)
        self.headers_edit.setPlaceholderText('{"Content-Type": "application/json"}')
        self.config_layout.addRow("请求头:", self.headers_edit)

        self.body_edit = QTextEdit()
        self.body_edit.setMaximumHeight(80)
        self.body_edit.setPlaceholderText('{"key": "value"}')
        self.config_layout.addRow("请求体:", self.body_edit)

    def create_python_config(self):
        """创建Python配置表单"""
        # 清空现有配置
        for i in reversed(range(self.config_layout.count())):
            self.config_layout.itemAt(i).widget().setParent(None)

        self.class_name_edit = QLineEdit()
        self.config_layout.addRow("Python类:", self.class_name_edit)

        self.method_name_edit = QLineEdit()
        self.config_layout.addRow("方法名:", self.method_name_edit)

        self.parameters_edit = QTextEdit()
        self.parameters_edit.setMaximumHeight(80)
        self.parameters_edit.setPlaceholderText('{"param1": "value1", "param2": "value2"}')
        self.config_layout.addRow("参数:", self.parameters_edit)

    def on_card_type_changed(self, type_text):
        """卡片类型变更事件"""
        if self.view_mode:
            return

        type_map = {
            "SQL查询": "sql",
            "SQL更新": "sql_update",
            "SQL删除": "sql_delete",
            "HTTP接口": "http",
            "Python类": "python"
        }

        card_type = type_map.get(type_text, "sql")

        if card_type.startswith('sql'):
            self.create_sql_config()
        elif card_type == 'http':
            self.create_http_config()
        elif card_type == 'python':
            self.create_python_config()

    def refresh_business_list(self):
        """刷新业务线列表"""
        self.business_list.clear()
        business_lines = self.config_data.get('business_lines', [])
        for business in business_lines:
            item = QListWidgetItem(business.get('name', '未命名'))
            item.setData(Qt.UserRole, business)
            self.business_list.addItem(item)

    def refresh_business_combo(self):
        """刷新业务线下拉框"""
        self.business_combo.clear()
        business_lines = self.config_data.get('business_lines', [])
        for business in business_lines:
            self.business_combo.addItem(business.get('name', '未命名'))

    def on_business_selected(self, current, previous):
        """业务线选择事件"""
        if current:
            business_data = current.data(Qt.UserRole)
            self.refresh_sub_business_list(business_data)

    def refresh_sub_business_list(self, business_data):
        """刷新子业务列表"""
        self.sub_business_list.clear()
        sub_businesses = business_data.get('sub_business', [])
        for sub_business in sub_businesses:
            item = QListWidgetItem(sub_business.get('name', '未命名'))
            item.setData(Qt.UserRole, sub_business)
            self.sub_business_list.addItem(item)

    def on_business_combo_changed(self, business_name):
        """业务线下拉框变更事件"""
        if business_name:
            # 刷新子业务下拉框
            self.refresh_sub_business_combo(business_name)

    def refresh_sub_business_combo(self, business_name):
        """刷新子业务下拉框"""
        self.sub_business_combo.clear()

        business_lines = self.config_data.get('business_lines', [])
        for business in business_lines:
            if business.get('name') == business_name:
                sub_businesses = business.get('sub_business', [])
                for sub_business in sub_businesses:
                    self.sub_business_combo.addItem(sub_business.get('name', '未命名'))
                break

    def on_sub_business_combo_changed(self, sub_business_name):
        """子业务下拉框变更事件"""
        if sub_business_name and self.business_combo.currentText():
            # 刷新卡片列表
            self.refresh_cards_list(self.business_combo.currentText(), sub_business_name)

    def refresh_cards_list(self, business_name, sub_business_name):
        """刷新卡片列表"""
        self.cards_list.clear()

        business_lines = self.config_data.get('business_lines', [])
        for business in business_lines:
            if business.get('name') == business_name:
                sub_businesses = business.get('sub_business', [])
                for sub_business in sub_businesses:
                    if sub_business.get('name') == sub_business_name:
                        cards = sub_business.get('cards', [])
                        for card in cards:
                            item = QListWidgetItem(card.get('title', '未命名'))
                            item.setData(Qt.UserRole, card)
                            self.cards_list.addItem(item)
                        break
                break

    def on_card_selected(self, current, previous):
        """卡片选择事件"""
        if current:
            self.current_card_data = current.data(Qt.UserRole)
            self.load_card_data(self.current_card_data)
        else:
            self.current_card_data = None
            self.create_card_details_form()

    def load_card_data(self, card_data):
        """加载卡片数据到表单"""
        self.current_card_data = card_data
        self.create_card_details_form()

        if self.view_mode:
            return

        # 填充表单数据
        self.card_title_edit.setText(card_data.get('title', ''))

        # 设置卡片类型
        card_type = card_data.get('type', 'sql')
        type_map = {
            'sql': 'SQL查询',
            'sql_update': 'SQL更新',
            'sql_delete': 'SQL删除',
            'http': 'HTTP接口',
            'python': 'Python类'
        }
        type_text = type_map.get(card_type, 'SQL查询')
        self.card_type_combo.setCurrentText(type_text)

        self.card_desc_edit.setPlainText(card_data.get('description', ''))
        self.timeout_spin.setValue(card_data.get('timeout', 5000))
        self.locked_check.setChecked(card_data.get('locked', False))

        # 填充类型特定的配置
        if card_type.startswith('sql'):
            self.database_combo.setCurrentText(card_data.get('database', ''))
            self.sql_editor.setPlainText(card_data.get('sql', ''))
        elif card_type == 'http':
            self.url_edit.setText(card_data.get('url', ''))
            self.method_combo.setCurrentText(card_data.get('method', 'GET'))
            self.headers_edit.setPlainText(card_data.get('headers', ''))
            self.body_edit.setPlainText(card_data.get('body', ''))
        elif card_type == 'python':
            self.class_name_edit.setText(card_data.get('class_name', ''))
            self.method_name_edit.setText(card_data.get('method_name', ''))
            self.parameters_edit.setPlainText(card_data.get('parameters', ''))

    def get_type_display(self):
        """获取卡片类型显示文本"""
        if not self.current_card_data:
            return ""

        card_type = self.current_card_data.get('type', 'sql')
        type_map = {
            'sql': 'SQL查询',
            'sql_update': 'SQL更新',
            'sql_delete': 'SQL删除',
            'http': 'HTTP接口',
            'python': 'Python类'
        }
        return type_map.get(card_type, card_type)

    def add_business_line(self):
        """新增业务线"""
        name, ok = QInputDialog.getText(self, "新增业务线", "请输入业务线名称:")
        if ok and name:
            # 检查名称是否已存在
            business_lines = self.config_data.get('business_lines', [])
            if any(business.get('name') == name for business in business_lines):
                QMessageBox.warning(self, "新增失败", "业务线名称已存在")
                return

            new_business = {
                'name': name,
                'sub_business': []
            }
            business_lines.append(new_business)

            # 如果是第一个业务线，设置为默认
            if len(business_lines) == 1:
                self.config_data['default_business_line'] = name

            self.refresh_business_list()
            self.refresh_business_combo()

    def edit_business_line(self):
        """编辑业务线"""
        current_item = self.business_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "编辑失败", "请选择要编辑的业务线")
            return

        old_name = current_item.text()
        new_name, ok = QInputDialog.getText(self, "编辑业务线", "请输入新的业务线名称:", text=old_name)

        if ok and new_name and new_name != old_name:
            # 检查名称是否已存在
            business_lines = self.config_data.get('business_lines', [])
            if any(business.get('name') == new_name for business in business_lines):
                QMessageBox.warning(self, "编辑失败", "业务线名称已存在")
                return

            # 更新业务线名称
            for business in business_lines:
                if business.get('name') == old_name:
                    business['name'] = new_name

                    # 如果这是默认业务线，也更新默认值
                    if self.config_data.get('default_business_line') == old_name:
                        self.config_data['default_business_line'] = new_name
                    break

            self.refresh_business_list()
            self.refresh_business_combo()

    def delete_business_line(self):
        """删除业务线"""
        current_item = self.business_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "删除失败", "请选择要删除的业务线")
            return

        business_name = current_item.text()
        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除业务线 '{business_name}' 吗？\n此操作将删除该业务线下所有子模块和卡片！",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            business_lines = self.config_data.get('business_lines', [])
            for i, business in enumerate(business_lines):
                if business.get('name') == business_name:
                    business_lines.pop(i)

                    # 如果删除的是默认业务线，重新设置默认值
                    if self.config_data.get('default_business_line') == business_name:
                        if business_lines:
                            self.config_data['default_business_line'] = business_lines[0].get('name')
                        else:
                            self.config_data['default_business_line'] = ""
                    break

            self.refresh_business_list()
            self.refresh_business_combo()

    def add_sub_business(self):
        """新增子业务模块"""
        current_item = self.business_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "新增失败", "请先选择业务线")
            return

        business_data = current_item.data(Qt.UserRole)
        name, ok = QInputDialog.getText(self, "新增子模块", "请输入子模块名称:")

        if ok and name:
            sub_businesses = business_data.get('sub_business', [])

            # 检查名称是否已存在
            if any(sub.get('name') == name for sub in sub_businesses):
                QMessageBox.warning(self, "新增失败", "子模块名称已存在")
                return

            new_sub_business = {
                'name': name,
                'cards': []
            }
            sub_businesses.append(new_sub_business)

            self.refresh_sub_business_list(business_data)

    def edit_sub_business(self):
        """编辑子业务模块"""
        current_item = self.sub_business_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "编辑失败", "请选择要编辑的子模块")
            return

        business_item = self.business_list.currentItem()
        if not business_item:
            return

        business_data = business_item.data(Qt.UserRole)
        old_name = current_item.text()

        new_name, ok = QInputDialog.getText(self, "编辑子模块", "请输入新的子模块名称:", text=old_name)

        if ok and new_name and new_name != old_name:
            sub_businesses = business_data.get('sub_business', [])

            # 检查名称是否已存在
            if any(sub.get('name') == new_name for sub in sub_businesses):
                QMessageBox.warning(self, "编辑失败", "子模块名称已存在")
                return

            # 更新子模块名称
            for sub_business in sub_businesses:
                if sub_business.get('name') == old_name:
                    sub_business['name'] = new_name
                    break

            self.refresh_sub_business_list(business_data)

    def delete_sub_business(self):
        """删除子业务模块"""
        current_item = self.sub_business_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "删除失败", "请选择要删除的子模块")
            return

        business_item = self.business_list.currentItem()
        if not business_item:
            return

        business_data = business_item.data(Qt.UserRole)
        sub_business_name = current_item.text()

        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除子模块 '{sub_business_name}' 吗？\n此操作将删除该子模块下所有卡片！",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            sub_businesses = business_data.get('sub_business', [])
            for i, sub_business in enumerate(sub_businesses):
                if sub_business.get('name') == sub_business_name:
                    sub_businesses.pop(i)
                    break

            self.refresh_sub_business_list(business_data)

    def add_card(self):
        """新增卡片"""
        if not self.business_combo.currentText() or not self.sub_business_combo.currentText():
            QMessageBox.warning(self, "新增失败", "请先选择业务线和子模块")
            return

        # 创建新卡片数据
        new_card = {
            'id': self.generate_card_id(),
            'title': '新卡片',
            'type': 'sql',
            'description': '',
            'timeout': 5000,
            'locked': False,
            'database': 'default_db',
            'sql': ''
        }

        self.current_card_data = new_card
        self.create_card_details_form()

        # 自动聚焦到标题输入框
        self.card_title_edit.setFocus()
        self.card_title_edit.selectAll()

    def edit_card(self):
        """编辑卡片"""
        current_item = self.cards_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "编辑失败", "请选择要编辑的卡片")
            return

        self.current_card_data = current_item.data(Qt.UserRole)
        self.create_card_details_form()

    def copy_card(self):
        """复制卡片"""
        current_item = self.cards_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "复制失败", "请选择要复制的卡片")
            return

        original_card = current_item.data(Qt.UserRole)

        # 创建副本
        new_card = original_card.copy()
        new_card['id'] = self.generate_card_id()

        # 生成副本名称
        base_name = original_card.get('title', '卡片')
        copy_count = 1
        new_title = f"{base_name}_cp{copy_count}"

        # 检查名称是否已存在
        business_lines = self.config_data.get('business_lines', [])
        for business in business_lines:
            if business.get('name') == self.business_combo.currentText():
                for sub_business in business.get('sub_business', []):
                    if sub_business.get('name') == self.sub_business_combo.currentText():
                        cards = sub_business.get('cards', [])
                        while any(card.get('title') == new_title for card in cards):
                            copy_count += 1
                            new_title = f"{base_name}_cp{copy_count}"
                        break
                break

        new_card['title'] = new_title
        new_card['locked'] = False  # 副本默认不锁定

        # 添加到当前子业务模块
        business_lines = self.config_data.get('business_lines', [])
        for business in business_lines:
            if business.get('name') == self.business_combo.currentText():
                for sub_business in business.get('sub_business', []):
                    if sub_business.get('name') == self.sub_business_combo.currentText():
                        sub_business['cards'].append(new_card)
                        break
                break

        self.refresh_cards_list(self.business_combo.currentText(), self.sub_business_combo.currentText())

        # 选中新复制的卡片
        for i in range(self.cards_list.count()):
            item = self.cards_list.item(i)
            if item.data(Qt.UserRole).get('id') == new_card['id']:
                self.cards_list.setCurrentItem(item)
                break

    def delete_card(self):
        """删除卡片"""
        current_item = self.cards_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "删除失败", "请选择要删除的卡片")
            return

        card_data = current_item.data(Qt.UserRole)
        card_title = card_data.get('title', '未命名')

        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除卡片 '{card_title}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            business_lines = self.config_data.get('business_lines', [])
            for business in business_lines:
                if business.get('name') == self.business_combo.currentText():
                    for sub_business in business.get('sub_business', []):
                        if sub_business.get('name') == self.sub_business_combo.currentText():
                            cards = sub_business.get('cards', [])
                            for i, card in enumerate(cards):
                                if card.get('id') == card_data.get('id'):
                                    cards.pop(i)
                                    break
                            break
                    break

            self.refresh_cards_list(self.business_combo.currentText(), self.sub_business_combo.currentText())
            self.current_card_data = None
            self.create_card_details_form()

    def save_current_card(self):
        """保存当前卡片"""
        if not self.current_card_data:
            return

        # 验证必填字段
        title = self.card_title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "保存失败", "请输入卡片名称")
            return

        # 更新卡片数据
        self.current_card_data['title'] = title
        self.current_card_data['description'] = self.card_desc_edit.toPlainText()
        self.current_card_data['timeout'] = self.timeout_spin.value()
        self.current_card_data['locked'] = self.locked_check.isChecked()

        # 获取卡片类型
        type_text = self.card_type_combo.currentText()
        type_map = {
            'SQL查询': 'sql',
            'SQL更新': 'sql_update',
            'SQL删除': 'sql_delete',
            'HTTP接口': 'http',
            'Python类': 'python'
        }
        self.current_card_data['type'] = type_map.get(type_text, 'sql')

        # 保存类型特定的配置
        card_type = self.current_card_data['type']
        if card_type.startswith('sql'):
            self.current_card_data['database'] = self.database_combo.currentText()
            self.current_card_data['sql'] = self.sql_editor.toPlainText()
        elif card_type == 'http':
            self.current_card_data['url'] = self.url_edit.text()
            self.current_card_data['method'] = self.method_combo.currentText()
            self.current_card_data['headers'] = self.headers_edit.toPlainText()
            self.current_card_data['body'] = self.body_edit.toPlainText()
        elif card_type == 'python':
            self.current_card_data['class_name'] = self.class_name_edit.text()
            self.current_card_data['method_name'] = self.method_name_edit.text()
            self.current_card_data['parameters'] = self.parameters_edit.toPlainText()

        # 如果是新卡片，添加到当前子业务模块
        if 'id' not in self.current_card_data or not self.current_card_data['id']:
            self.current_card_data['id'] = self.generate_card_id()

            business_lines = self.config_data.get('business_lines', [])
            for business in business_lines:
                if business.get('name') == self.business_combo.currentText():
                    for sub_business in business.get('sub_business', []):
                        if sub_business.get('name') == self.sub_business_combo.currentText():
                            sub_business['cards'].append(self.current_card_data)
                            break
                    break

        self.refresh_cards_list(self.business_combo.currentText(), self.sub_business_combo.currentText())
        QMessageBox.information(self, "保存成功", "卡片保存成功")

    def generate_card_id(self):
        """生成卡片ID"""
        import time
        return f"card_{int(time.time() * 1000)}"

    def get_config_data(self):
        """获取配置数据"""
        return self.config_data


# 需要导入的额外组件
from PyQt5.QtWidgets import QInputDialog