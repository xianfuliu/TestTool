from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QTextEdit, QMessageBox, QTabWidget, QListWidget,
                             QListWidgetItem, QDialog, QFormLayout, QCompleter, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import pymysql

from src.ui.widgets.no_wheel_combo_box import NoWheelComboBox
from src.ui.widgets.toast_tips import Toast
from src.utils.resource_utils import resource_path
import json
import os
import re


class DatabaseConfigDialog(QDialog):
    """数据库配置配置管理对话框"""

    # 添加刷新信号,定义保存成功的信号
    config_saved = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("配置管理")
        self.setModal(True)
        self.resize(800, 700)
        self.init_ui()
        self.load_configs()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 创建选项卡
        self.tab_widget = QTabWidget()

        # 查询条件配置选项卡 - 新增
        self.input_fields_tab = QWidget()
        self.init_input_fields_tab()
        self.tab_widget.addTab(self.input_fields_tab, "查询条件")

        # 数据库配置配置选项卡
        self.db_tab = QWidget()
        self.init_db_tab()
        self.tab_widget.addTab(self.db_tab, "数据库")

        # SQL操作配置选项卡
        self.sql_tab = QWidget()
        self.init_sql_tab()
        self.tab_widget.addTab(self.sql_tab, "查询脚本")

        layout.addWidget(self.tab_widget)

        # 按钮区域 - 修改为右对齐
        button_layout = QHBoxLayout()

        # 添加弹性空间，将按钮推到右侧
        button_layout.addStretch(1)

        # 设置按钮固定宽度
        button_width = 80

        self.save_btn = QPushButton("保存")
        self.save_btn.setFixedWidth(button_width)  # 设置固定宽度
        self.save_btn.clicked.connect(self.save_configs)
        button_layout.addWidget(self.save_btn)

        self.close_btn = QPushButton("关闭")
        self.close_btn.setFixedWidth(button_width)  # 设置固定宽度
        self.close_btn.clicked.connect(self.on_close)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def on_close(self):
        """关闭对话框"""
        # 发送配置保存信号（即使没有保存，也重新加载以确保一致性）
        self.config_saved.emit("配置保存成功")
        self.close()

    def init_input_fields_tab(self):
        """初始化查询条件配置选项卡"""
        layout = QVBoxLayout(self.input_fields_tab)
        layout.setSpacing(15)  # 增加垂直间距
        layout.setContentsMargins(15, 15, 15, 15)  # 增加边距

        # 参数选择区域 - 改为一行水平布局
        param_selection_layout = QHBoxLayout()
        param_selection_layout.setSpacing(10)  # 增加水平间距
        param_selection_layout.addWidget(QLabel("查询条件:"))

        # 将列表改为下拉框
        self.input_fields_combo = NoWheelComboBox()
        self.input_fields_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.input_fields_combo.setMinimumWidth(200)
        self.input_fields_combo.currentTextChanged.connect(self.on_input_field_selected)
        param_selection_layout.addWidget(self.input_fields_combo)
        param_selection_layout.addStretch(1)

        layout.addLayout(param_selection_layout)

        # 参数编辑区域
        input_field_edit_layout = QFormLayout()
        input_field_edit_layout.setSpacing(10)  # 增加表单项之间的间距
        input_field_edit_layout.setContentsMargins(0, 10, 0, 10)  # 增加上下边距

        self.input_field_name = QLineEdit()
        self.input_field_name.setPlaceholderText("条件字段（英文，如：mobile）")
        self.input_field_name.setMaximumWidth(200)
        self.input_field_name.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        input_field_edit_layout.addRow("条件字段:", self.input_field_name)

        self.input_field_label = QLineEdit()
        self.input_field_label.setPlaceholderText("条件名称（中文，如：手机号）")
        self.input_field_label.setMaximumWidth(200)
        self.input_field_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        input_field_edit_layout.addRow("条件名称:", self.input_field_label)

        self.input_field_placeholder = QLineEdit()
        self.input_field_placeholder.setPlaceholderText("输入提示文本（如：请输入手机号）")
        self.input_field_placeholder.setMaximumWidth(200)
        self.input_field_placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        input_field_edit_layout.addRow("输入提示:", self.input_field_placeholder)

        layout.addLayout(input_field_edit_layout)

        # 参数操作按钮
        input_field_buttons_layout = QHBoxLayout()
        input_field_buttons_layout.setSpacing(10)  # 增加按钮间距

        self.add_input_field_btn = QPushButton("新增")
        self.add_input_field_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.add_input_field_btn.clicked.connect(self.add_input_field)
        input_field_buttons_layout.addWidget(self.add_input_field_btn)

        self.update_input_field_btn = QPushButton("更新")
        self.update_input_field_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.update_input_field_btn.clicked.connect(self.update_input_field)
        input_field_buttons_layout.addWidget(self.update_input_field_btn)

        self.delete_input_field_btn = QPushButton("删除")
        self.delete_input_field_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.delete_input_field_btn.clicked.connect(self.delete_input_field)
        input_field_buttons_layout.addWidget(self.delete_input_field_btn)

        input_field_buttons_layout.addStretch(1)
        layout.addLayout(input_field_buttons_layout)

        # 添加拉伸
        layout.addStretch(1)

    def init_db_tab(self):
        layout = QVBoxLayout(self.db_tab)
        layout.setSpacing(15)  # 增加垂直间距
        layout.setContentsMargins(15, 15, 15, 15)  # 增加边距

        # 数据库配置选择 - 改为一行水平布局
        db_selection_layout = QHBoxLayout()
        db_selection_layout.setSpacing(10)  # 增加水平间距
        db_selection_layout.addWidget(QLabel("数据库配置:"))

        # 将列表改为下拉框
        self.db_combo = NoWheelComboBox()
        self.db_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.db_combo.setMinimumWidth(200)
        self.db_combo.currentTextChanged.connect(self.on_db_selected)
        db_selection_layout.addWidget(self.db_combo)
        db_selection_layout.addStretch(1)

        layout.addLayout(db_selection_layout)

        # 数据库配置配置编辑区域
        db_edit_layout = QFormLayout()
        db_edit_layout.setSpacing(10)  # 增加表单项之间的间距
        db_edit_layout.setContentsMargins(0, 10, 0, 10)  # 增加上下边距

        self.db_name = QLineEdit()
        self.db_name.setMaximumWidth(200)
        self.db_name.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        db_edit_layout.addRow("配置名称:", self.db_name)

        self.db_host = QLineEdit()
        self.db_host.setText("localhost")
        self.db_host.setMaximumWidth(200)
        self.db_host.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        db_edit_layout.addRow("主机:", self.db_host)

        self.db_port = QLineEdit()
        self.db_port.setText("3306")
        self.db_port.setMaximumWidth(200)
        self.db_port.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        db_edit_layout.addRow("端口:", self.db_port)

        self.db_username = QLineEdit()
        self.db_username.setText("root")
        self.db_username.setMaximumWidth(200)
        self.db_username.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        db_edit_layout.addRow("用户名:", self.db_username)

        self.db_password = QLineEdit()
        self.db_password.setEchoMode(QLineEdit.Password)
        self.db_password.setMaximumWidth(200)
        self.db_password.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        db_edit_layout.addRow("密码:", self.db_password)

        self.db_database = QLineEdit()
        self.db_database.setMaximumWidth(200)
        self.db_database.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        db_edit_layout.addRow("库名:", self.db_database)

        layout.addLayout(db_edit_layout)

        # 数据库配置配置操作按钮
        db_buttons_layout = QHBoxLayout()
        db_buttons_layout.setSpacing(10)  # 增加按钮间距

        self.add_db_btn = QPushButton("新增")
        self.add_db_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.add_db_btn.clicked.connect(self.add_db_config)
        db_buttons_layout.addWidget(self.add_db_btn)

        self.update_db_btn = QPushButton("更新")
        self.update_db_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.update_db_btn.clicked.connect(self.update_db_config)
        db_buttons_layout.addWidget(self.update_db_btn)

        self.delete_db_btn = QPushButton("删除")
        self.delete_db_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.delete_db_btn.clicked.connect(self.delete_db_config)
        db_buttons_layout.addWidget(self.delete_db_btn)

        self.test_db_btn = QPushButton("测试")
        self.test_db_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.test_db_btn.clicked.connect(self.test_db_connection)
        db_buttons_layout.addWidget(self.test_db_btn)

        db_buttons_layout.addStretch(1)
        layout.addLayout(db_buttons_layout)

        # 添加拉伸
        layout.addStretch(1)

    def init_sql_tab(self):
        layout = QVBoxLayout(self.sql_tab)
        layout.setSpacing(15)  # 增加整体垂直间距
        layout.setContentsMargins(15, 15, 15, 15)  # 增加边距

        # 第一行：操作配置、配置名称、按钮名称
        operation_row_layout = QHBoxLayout()
        operation_row_layout.setSpacing(10)  # 增加水平间距

        # 操作配置
        operation_row_layout.addWidget(QLabel("脚本列表:"))
        self.sql_combo = NoWheelComboBox()
        self.sql_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.sql_combo.setMinimumWidth(180)  # 增加宽度
        self.sql_combo.currentTextChanged.connect(self.on_sql_selected)
        operation_row_layout.addWidget(self.sql_combo)

        # 配置名称
        operation_row_layout.addWidget(QLabel("脚本名称:"))
        self.sql_name = QLineEdit()
        self.sql_name.setMaximumWidth(180)  # 增加宽度
        self.sql_name.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        operation_row_layout.addWidget(self.sql_name)

        # 按钮名称
        operation_row_layout.addWidget(QLabel("按钮名称:"))
        self.sql_display_name = QLineEdit()
        self.sql_display_name.setMaximumWidth(180)  # 增加宽度
        self.sql_display_name.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        operation_row_layout.addWidget(self.sql_display_name)

        operation_row_layout.addStretch(1)
        layout.addLayout(operation_row_layout)

        # 第二行：数据库配置、库名、表名
        database_row_layout = QHBoxLayout()
        database_row_layout.setSpacing(10)  # 增加水平间距

        # 数据库配置
        database_row_layout.addWidget(QLabel("配置列表:"))
        self.sql_db_connection = NoWheelComboBox()
        self.sql_db_connection.addItem("")
        self.sql_db_connection.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.sql_db_connection.setMinimumWidth(180)  # 增加宽度
        self.sql_db_connection.currentTextChanged.connect(self.on_db_connection_changed)
        database_row_layout.addWidget(self.sql_db_connection)

        # 库名
        database_row_layout.addWidget(QLabel("库名:"))
        self.database_combo = NoWheelComboBox()
        self.database_combo.setEditable(True)
        self.database_combo.setEnabled(False)
        self.database_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.database_combo.setMinimumWidth(180)  # 增加宽度
        self.database_combo.currentTextChanged.connect(self.on_database_changed)

        # 添加模糊匹配功能
        self.database_completer = QCompleter()
        self.database_combo.setCompleter(self.database_completer)
        self.database_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.database_completer.setFilterMode(Qt.MatchContains)

        self.refresh_databases_btn = QPushButton("刷新库")
        self.refresh_databases_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.refresh_databases_btn.setEnabled(False)
        self.refresh_databases_btn.clicked.connect(self.refresh_databases)

        database_row_layout.addWidget(self.database_combo)
        database_row_layout.addWidget(self.refresh_databases_btn)

        # 表名
        database_row_layout.addWidget(QLabel("表名:"))
        self.table_combo = NoWheelComboBox()
        self.table_combo.setEditable(True)
        self.table_combo.setEnabled(False)
        self.table_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.table_combo.setMinimumWidth(180)  # 增加宽度
        self.table_combo.currentTextChanged.connect(self.on_table_changed)

        # 添加模糊匹配功能
        self.table_completer = QCompleter()
        self.table_combo.setCompleter(self.table_completer)
        self.table_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.table_completer.setFilterMode(Qt.MatchContains)

        self.refresh_tables_btn = QPushButton("刷新表")
        self.refresh_tables_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.refresh_tables_btn.setEnabled(False)
        self.refresh_tables_btn.clicked.connect(self.refresh_tables)

        database_row_layout.addWidget(self.table_combo)
        database_row_layout.addWidget(self.refresh_tables_btn)

        database_row_layout.addStretch(1)
        layout.addLayout(database_row_layout)

        # 查询条件区域
        required_param_layout = QHBoxLayout()
        required_param_layout.setSpacing(10)  # 增加水平间距
        required_param_layout.addWidget(QLabel("查询条件:"))

        self.required_param_combo = NoWheelComboBox()
        self.required_param_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.required_param_combo.setMinimumWidth(220)  # 增加宽度
        required_param_layout.addWidget(self.required_param_combo)

        self.add_param_btn = QPushButton("添加")
        self.add_param_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.add_param_btn.clicked.connect(self.add_required_param)
        required_param_layout.addWidget(self.add_param_btn)
        required_param_layout.addStretch(1)

        layout.addLayout(required_param_layout)

        # 第三行：已选查询条件文案和已选查询条件展示框、移除选中
        selected_params_row_layout = QHBoxLayout()
        selected_params_row_layout.setSpacing(10)  # 增加水平间距

        # 已选查询条件文案
        selected_params_row_layout.addWidget(QLabel("已选查询条件:"))

        # 已选查询条件展示框 - 增加宽度
        self.selected_params_list = QListWidget()
        self.selected_params_list.setMaximumHeight(100)
        self.selected_params_list.setMinimumWidth(500)  # 设置最小宽度
        self.selected_params_list.setMaximumWidth(600)  # 增加最大宽度
        self.selected_params_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        selected_params_row_layout.addWidget(self.selected_params_list)

        # 移除选中按钮
        self.remove_param_btn = QPushButton("移除选中")
        self.remove_param_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.remove_param_btn.clicked.connect(self.remove_required_param)
        selected_params_row_layout.addWidget(self.remove_param_btn)

        selected_params_row_layout.addStretch(1)
        layout.addLayout(selected_params_row_layout)

        # 字段表名格
        fields_label = QLabel("字段列表:")
        layout.addWidget(fields_label)

        self.fields_table = QTableWidget()
        self.fields_table.setColumnCount(4)
        self.fields_table.setHorizontalHeaderLabels(["选择", "字段名", "类型", "注释"])
        self.fields_table.horizontalHeader().setStretchLastSection(True)
        self.fields_table.setMaximumHeight(400)
        self.fields_table.setMinimumHeight(300)

        # 设置列宽
        self.fields_table.setColumnWidth(0, 60)  # 选择列
        self.fields_table.setColumnWidth(1, 150)  # 字段名列
        self.fields_table.setColumnWidth(2, 120)  # 类型列
        # 注释列自动拉伸

        # 设置字体
        font = QFont()
        font.setPointSize(9)
        self.fields_table.setFont(font)

        layout.addWidget(self.fields_table)

        # 字段操作按钮
        field_buttons_layout = QHBoxLayout()
        field_buttons_layout.setSpacing(10)  # 增加按钮间距
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.select_all_btn.setEnabled(False)
        self.select_all_btn.clicked.connect(self.select_all_fields)
        field_buttons_layout.addWidget(self.select_all_btn)

        self.clear_all_btn = QPushButton("全不选")
        self.clear_all_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.clear_all_btn.setEnabled(False)
        self.clear_all_btn.clicked.connect(self.clear_all_fields)
        field_buttons_layout.addWidget(self.clear_all_btn)

        self.generate_sql_btn = QPushButton("生成SQL")
        self.generate_sql_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.generate_sql_btn.setEnabled(False)
        self.generate_sql_btn.clicked.connect(self.generate_sql)
        field_buttons_layout.addWidget(self.generate_sql_btn)

        field_buttons_layout.addStretch(1)
        layout.addLayout(field_buttons_layout)

        # SQL编辑器
        sql_editor_label = QLabel("SQL语句:")
        layout.addWidget(sql_editor_label)

        self.sql_editor = QTextEdit()
        self.sql_editor.setPlaceholderText("SQL语句将自动生成")
        self.sql_editor.setMinimumHeight(150)  # 设置SQL编辑器最小高度
        layout.addWidget(self.sql_editor)

        # SQL查询操作按钮
        sql_buttons_layout = QHBoxLayout()
        sql_buttons_layout.setSpacing(10)  # 增加按钮间距

        self.add_sql_btn = QPushButton("新增")
        self.add_sql_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.add_sql_btn.clicked.connect(self.add_sql_config)
        sql_buttons_layout.addWidget(self.add_sql_btn)

        self.update_sql_btn = QPushButton("更新")
        self.update_sql_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.update_sql_btn.clicked.connect(self.update_sql_config)
        sql_buttons_layout.addWidget(self.update_sql_btn)

        self.delete_sql_btn = QPushButton("删除")
        self.delete_sql_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.delete_sql_btn.clicked.connect(self.delete_sql_config)
        sql_buttons_layout.addWidget(self.delete_sql_btn)

        sql_buttons_layout.addStretch(1)
        layout.addLayout(sql_buttons_layout)

    def load_configs(self):
        """加载配置"""
        self.db_configs = {}
        self.sql_configs = {}
        self.input_fields = {}

        config_file = resource_path("config/query_config.json")

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self.db_configs = config_data.get('database_connections', {})
                    self.sql_configs = config_data.get('sql_queries', {})
                    self.input_fields = config_data.get('input_fields', {})

            self.refresh_input_fields_list()
            self.refresh_db_list()
            self.refresh_sql_combo()
            self.refresh_db_combo()
            self.refresh_required_param_combo()  # 刷新查询条件下拉框
        except Exception as e:
            Toast.critical(self, "错误", f"加载配置失败: {e}")

    def refresh_input_fields_list(self):
        """刷新查询条件下拉框"""
        self.input_fields_combo.clear()
        for name, config in self.input_fields.items():
            display_text = f"{config.get('label', name)} ({name})"
            self.input_fields_combo.addItem(display_text, name)  # 这里已经正确设置数据

    def refresh_required_param_combo(self):
        """刷新查询条件下拉框 - 从input_fields获取"""
        self.required_param_combo.clear()
        for param_name, param_config in self.input_fields.items():
            display_text = f"{param_config.get('label', param_name)} ({param_name})"
            self.required_param_combo.addItem(display_text, param_name)

    def refresh_db_list(self):
        """刷新数据库配置下拉框"""
        self.db_combo.clear()
        for name in self.db_configs.keys():
            self.db_combo.addItem(name)

    def refresh_sql_combo(self):
        """刷新SQL查询下拉框"""
        self.sql_combo.clear()
        for name in self.sql_configs.keys():
            self.sql_combo.addItem(name)

    def refresh_db_combo(self):
        """刷新数据库配置下拉框"""
        self.sql_db_connection.clear()
        self.sql_db_connection.addItem("")  # 添加空选项
        for name in self.db_configs.keys():
            self.sql_db_connection.addItem(name)

    def on_input_field_selected(self, text):
        """选中查询条件"""
        if not text:
            return

        # 获取条件字段
        param_name = self.input_fields_combo.currentData()
        if param_name and param_name in self.input_fields:
            config = self.input_fields[param_name]
            self.input_field_name.setText(param_name)
            self.input_field_label.setText(config.get('label', ''))
            self.input_field_placeholder.setText(config.get('placeholder', ''))

    def add_input_field(self):
        """新增查询条件"""
        param_name = self.input_field_name.text().strip()
        label = self.input_field_label.text().strip()
        placeholder = self.input_field_placeholder.text().strip()

        if not param_name:
            Toast.warning(self, "警告", "请输入条件字段")
            return

        if not label:
            Toast.warning(self, "警告", "请输入条件名称")
            return

        # 检查条件字段是否已存在
        if param_name in self.input_fields:
            Toast.warning(self, "警告", f"条件字段 '{param_name}' 已存在")
            return

        self.input_fields[param_name] = {
            'label': label,
            'placeholder': placeholder
        }

        self.refresh_input_fields_list()
        self.refresh_required_param_combo()  # 刷新查询条件下拉框

        # 清空输入框
        self.input_field_name.clear()
        self.input_field_label.clear()
        self.input_field_placeholder.clear()

        Toast.information(self, "成功", f"参数 '{param_name}' 已添加")

    def update_input_field(self):
        """更新查询条件"""
        if self.input_fields_combo.currentIndex() < 0:
            Toast.warning(self, "警告", "请选择要更新的参数")
            return

        # 获取当前选中的条件字段
        old_param_name = self.input_fields_combo.currentData()
        if not old_param_name:
            Toast.warning(self, "警告", "未找到选中的参数")
            return

        new_param_name = self.input_field_name.text().strip()
        label = self.input_field_label.text().strip()
        placeholder = self.input_field_placeholder.text().strip()

        if not new_param_name:
            Toast.warning(self, "警告", "请输入条件字段")
            return

        if not label:
            Toast.warning(self, "警告", "请输入条件名称")
            return

        # 如果条件字段改变，检查新名称是否已存在
        if old_param_name != new_param_name and new_param_name in self.input_fields:
            Toast.warning(self, "警告", f"条件字段 '{new_param_name}' 已存在")
            return

        # 更新参数配置
        if old_param_name != new_param_name:
            # 删除旧的，添加新的
            self.input_fields[new_param_name] = self.input_fields.pop(old_param_name)

        # 更新配置内容
        self.input_fields[new_param_name] = {
            'label': label,
            'placeholder': placeholder
        }

        self.refresh_input_fields_list()
        self.refresh_required_param_combo()

        # 设置新名称选中
        index = self.input_fields_combo.findData(new_param_name)
        if index >= 0:
            self.input_fields_combo.setCurrentIndex(index)

        Toast.information(self, "成功", f"参数 '{new_param_name}' 已更新")

    def delete_input_field(self):
        """删除查询条件"""
        if self.input_fields_combo.currentIndex() < 0:
            Toast.warning(self, "警告", "请选择要删除的参数")
            return

        param_name = self.input_fields_combo.currentData()

        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除参数 '{param_name}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            del self.input_fields[param_name]
            self.refresh_input_fields_list()
            self.refresh_required_param_combo()

            # 清空输入框
            self.input_field_name.clear()
            self.input_field_label.clear()
            self.input_field_placeholder.clear()

            Toast.information(self, "成功", f"参数 '{param_name}' 已删除")

    def on_db_connection_changed(self, connection_name):
        """数据库配置改变时启用/禁用相关控件"""
        if connection_name:
            # 启用数据库配置相关控件
            self.database_combo.setEnabled(True)
            self.refresh_databases_btn.setEnabled(True)

            # 尝试从配置中获取默认数据库配置
            if connection_name in self.db_configs:
                default_db = self.db_configs[connection_name].get('database', '')
                if default_db:
                    self.database_combo.setCurrentText(default_db)
        else:
            # 禁用相关控件
            self.database_combo.setEnabled(False)
            self.refresh_databases_btn.setEnabled(False)
            self.table_combo.setEnabled(False)
            self.refresh_tables_btn.setEnabled(False)
            self.fields_table.setRowCount(0)  # 清空字段表格
            self.select_all_btn.setEnabled(False)
            self.clear_all_btn.setEnabled(False)
            self.generate_sql_btn.setEnabled(False)

    def refresh_databases(self):
        """刷新数据库配置列表"""
        connection_name = self.sql_db_connection.currentText()
        if not connection_name or connection_name not in self.db_configs:
            return

        try:
            db_config = self.db_configs[connection_name]
            connection_params = {
                'host': db_config.get('host'),
                'port': int(db_config.get('port', 3306)),
                'user': db_config.get('username'),
                'password': db_config.get('password'),
                'charset': 'utf8mb4'
            }

            conn = pymysql.connect(**connection_params)
            cursor = conn.cursor()

            # 获取所有数据库配置
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()

            current_db = self.database_combo.currentText()  # 保存当前选中的数据库配置

            self.database_combo.clear()
            for database in databases:
                db_name = database[0]
                # 过滤掉系统数据库配置
                if db_name not in ['information_schema', 'mysql', 'performance_schema', 'sys']:
                    self.database_combo.addItem(db_name)

            # 恢复之前选中的数据库配置
            if current_db and self.database_combo.findText(current_db) >= 0:
                self.database_combo.setCurrentText(current_db)

            cursor.close()
            conn.close()

            # 启用表相关控件
            self.table_combo.setEnabled(True)
            self.refresh_tables_btn.setEnabled(True)

        except Exception as e:
            Toast.warning(self, "错误", f"加载数据库配置失败: {str(e)}")

    def on_database_changed(self, database_name):
        """数据库配置改变时"""
        if database_name:
            # 可以在这里添加数据库配置改变后的逻辑
            pass

    def refresh_tables(self):
        """刷新表列表"""
        connection_name = self.sql_db_connection.currentText()
        database_name = self.database_combo.currentText()
        if not connection_name or connection_name not in self.db_configs or not database_name:
            return

        try:
            db_config = self.db_configs[connection_name]
            connection_params = {
                'host': db_config.get('host'),
                'port': int(db_config.get('port', 3306)),
                'user': db_config.get('username'),
                'password': db_config.get('password'),
                'database': database_name,
                'charset': 'utf8mb4'
            }

            conn = pymysql.connect(**connection_params)
            cursor = conn.cursor()

            # 获取所有表
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()

            current_table = self.table_combo.currentText()  # 保存当前选中的表

            self.table_combo.clear()
            for table in tables:
                self.table_combo.addItem(table[0])

            # 恢复之前选中的表
            if current_table and self.table_combo.findText(current_table) >= 0:
                self.table_combo.setCurrentText(current_table)

            cursor.close()
            conn.close()

            # 启用字段操作按钮
            self.select_all_btn.setEnabled(True)
            self.clear_all_btn.setEnabled(True)
            self.generate_sql_btn.setEnabled(True)

        except Exception as e:
            Toast.warning(self, "错误", f"加载表失败: {str(e)}")

    def on_table_changed(self, table_name):
        """表改变时加载字段信息"""
        if not table_name:
            return

        connection_name = self.sql_db_connection.currentText()
        database_name = self.database_combo.currentText()
        if not connection_name or connection_name not in self.db_configs or not database_name:
            return

        try:
            db_config = self.db_configs[connection_name]
            connection_params = {
                'host': db_config.get('host'),
                'port': int(db_config.get('port', 3306)),
                'user': db_config.get('username'),
                'password': db_config.get('password'),
                'database': database_name,
                'charset': 'utf8mb4'
            }

            conn = pymysql.connect(**connection_params)
            cursor = conn.cursor()

            # 获取字段信息
            cursor.execute(f"SHOW FULL COLUMNS FROM {table_name}")
            fields = cursor.fetchall()

            self.fields_table.setRowCount(len(fields))
            for row, field in enumerate(fields):
                # 复选框
                check_item = QTableWidgetItem()
                check_item.setCheckState(Qt.Unchecked)
                self.fields_table.setItem(row, 0, check_item)

                # 字段名
                self.fields_table.setItem(row, 1, QTableWidgetItem(field[0]))

                # 字段类型
                self.fields_table.setItem(row, 2, QTableWidgetItem(field[1]))

                # 字段注释
                comment = field[8] if len(field) > 8 else ''
                self.fields_table.setItem(row, 3, QTableWidgetItem(comment))

            cursor.close()
            conn.close()

        except Exception as e:
            Toast.warning(self, "错误", f"加载字段失败: {str(e)}")

    def select_all_fields(self):
        """全选字段"""
        for row in range(self.fields_table.rowCount()):
            item = self.fields_table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked)

    def clear_all_fields(self):
        """全不选字段"""
        for row in range(self.fields_table.rowCount()):
            item = self.fields_table.item(row, 0)
            if item:
                item.setCheckState(Qt.Unchecked)

    def on_required_param_changed(self, param_name):
        """查询条件选择改变"""
        pass

    def add_required_param(self):
        """添加查询条件到已选查询条件列表"""
        if self.required_param_combo.currentIndex() < 0:
            return

        param_name = self.required_param_combo.currentData()
        display_text = self.required_param_combo.currentText()

        # 检查是否已存在
        for i in range(self.selected_params_list.count()):
            item = self.selected_params_list.item(i)
            if item.data(Qt.UserRole) == param_name:
                return

        # 添加到已选查询条件列表
        item = QListWidgetItem(display_text)
        item.setData(Qt.UserRole, param_name)
        self.selected_params_list.addItem(item)

    def remove_required_param(self):
        """从已选查询条件列表中移除选中参数"""
        current_row = self.selected_params_list.currentRow()
        if current_row >= 0:
            self.selected_params_list.takeItem(current_row)

    def generate_sql(self):
        """生成SQL语句"""
        database_name = self.database_combo.currentText()
        table_name = self.table_combo.currentText()
        if not table_name:
            Toast.warning(self, "警告", "请先表名")
            return

        # 获取选中的字段
        selected_fields = []
        for row in range(self.fields_table.rowCount()):
            item = self.fields_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                field_name = self.fields_table.item(row, 1).text()
                field_comment = self.fields_table.item(row, 3).text()
                selected_fields.append((field_name, field_comment))

        if not selected_fields:
            Toast.warning(self, "警告", "请至少选择一个字段")
            return

        # 生成SELECT部分
        field_names = [field[0] for field in selected_fields]
        select_clause = ", ".join(field_names)

        # 生成WHERE部分 - 从已选查询条件列表中获取
        where_conditions = []
        for i in range(self.selected_params_list.count()):
            item = self.selected_params_list.item(i)
            param_name = item.data(Qt.UserRole)
            # 修复：在参数值周围添加单引号
            where_conditions.append(f"{param_name} = {{{param_name}}}")

        where_clause = ""
        if where_conditions:
            where_clause = " WHERE " + " AND ".join(where_conditions)

        # 生成完整SQL
        sql = f"SELECT {select_clause} FROM {database_name}.{table_name}{where_clause} LIMIT 100"
        self.sql_editor.setPlainText(sql)

    def on_sql_selected(self, name):
        """选中SQL查询"""
        if not name:
            return

        if name in self.sql_configs:
            config = self.sql_configs[name]
            self.sql_name.setText(name)
            self.sql_display_name.setText(config.get('display_name', ''))

            # 设置数据库配置
            db_connection = config.get('db_connection', '')
            if db_connection:
                index = self.sql_db_connection.findText(db_connection)
                if index >= 0:
                    self.sql_db_connection.setCurrentIndex(index)

                    # 自动连接数据库配置并刷新库表
                    self.refresh_databases()

                    # 尝试从SQL中解析数据库配置和表名
                    sql = config.get('sql', '')
                    if sql:
                        # 简单的SQL解析来获取数据库配置和表名
                        from_match = re.search(r'FROM\s+([\w\.]+)', sql, re.IGNORECASE)
                        if from_match:
                            table_ref = from_match.group(1)
                            if '.' in table_ref:
                                db_name, table_name = table_ref.split('.')
                                # 设置数据库配置
                                db_index = self.database_combo.findText(db_name)
                                if db_index >= 0:
                                    self.database_combo.setCurrentIndex(db_index)
                                    # 刷新表
                                    self.refresh_tables()
                                    # 设置表
                                    table_index = self.table_combo.findText(table_name)
                                    if table_index >= 0:
                                        self.table_combo.setCurrentIndex(table_index)

            # 设置SQL语句
            self.sql_editor.setPlainText(config.get('sql', ''))

            # 设置查询条件
            self.selected_params_list.clear()
            required_params = config.get('required_params', [])
            for param in required_params:
                # 查找对应的参数项并添加到已选查询条件列表
                for i in range(self.required_param_combo.count()):
                    if self.required_param_combo.itemData(i) == param:
                        display_text = self.required_param_combo.itemText(i)
                        item = QListWidgetItem(display_text)
                        item.setData(Qt.UserRole, param)
                        self.selected_params_list.addItem(item)
                        break

    def add_sql_config(self):
        """新增SQL操作配置"""
        name = self.sql_name.text().strip()
        if not name:
            Toast.warning(self, "警告", "请输入配置名称")
            return

        # 获取选中的字段作为输出字段
        output_fields = {}
        for row in range(self.fields_table.rowCount()):
            item = self.fields_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                field_name = self.fields_table.item(row, 1).text()
                field_comment = self.fields_table.item(row, 3).text()
                # 使用注释作为按钮名称，如果没有注释则使用字段名
                display_name = field_comment if field_comment else field_name
                output_fields[field_name] = display_name

        # 从已选查询条件列表中提取查询条件
        required_params = []
        for i in range(self.selected_params_list.count()):
            item = self.selected_params_list.item(i)
            required_params.append(item.data(Qt.UserRole))

        self.sql_configs[name] = {
            'display_name': self.sql_display_name.text().strip(),
            'db_connection': self.sql_db_connection.currentText(),
            'sql': self.sql_editor.toPlainText().strip(),
            'required_params': required_params,
            'output_fields': output_fields
        }

        self.refresh_sql_combo()
        Toast.information(self, "成功", f"操作配置 '{name}' 已添加")

    def update_sql_config(self):
        """更新SQL操作配置"""
        current_name = self.sql_combo.currentText()
        if not current_name:
            Toast.warning(self, "警告", "请选择要更新的查询")
            return

        old_name = current_name
        new_name = self.sql_name.text().strip()

        if not new_name:
            Toast.warning(self, "警告", "请输入配置名称")
            return

        # 获取选中的字段作为输出字段
        output_fields = {}
        for row in range(self.fields_table.rowCount()):
            item = self.fields_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                field_name = self.fields_table.item(row, 1).text()
                field_comment = self.fields_table.item(row, 3).text()
                # 使用注释作为按钮名称，如果没有注释则使用字段名
                display_name = field_comment if field_comment else field_name
                output_fields[field_name] = display_name

        # 从已选查询条件列表中提取查询条件
        required_params = []
        for i in range(self.selected_params_list.count()):
            item = self.selected_params_list.item(i)
            required_params.append(item.data(Qt.UserRole))

        # 如果名称改变，先删除旧的
        if old_name != new_name:
            del self.sql_configs[old_name]

        self.sql_configs[new_name] = {
            'display_name': self.sql_display_name.text().strip(),
            'db_connection': self.sql_db_connection.currentText(),
            'sql': self.sql_editor.toPlainText().strip(),
            'required_params': required_params,
            'output_fields': output_fields
        }

        self.refresh_sql_combo()
        # 设置新名称选中
        index = self.sql_combo.findText(new_name)
        if index >= 0:
            self.sql_combo.setCurrentIndex(index)

        Toast.information(self, "成功", f"操作配置 '{new_name}' 已更新")

    def on_db_selected(self, name):
        """选中数据库配置"""
        if name and name in self.db_configs:
            config = self.db_configs[name]
            self.db_name.setText(name)
            self.db_host.setText(config.get('host', ''))
            self.db_port.setText(config.get('port', ''))
            self.db_username.setText(config.get('username', ''))
            self.db_password.setText(config.get('password', ''))
            self.db_database.setText(config.get('database', ''))

    def add_db_config(self):
        """新增数据库配置配置"""
        name = self.db_name.text().strip()
        if not name:
            Toast.warning(self, "警告", "请输入配置名称")
            return

        self.db_configs[name] = {
            'host': self.db_host.text().strip(),
            'port': self.db_port.text().strip(),
            'username': self.db_username.text().strip(),
            'password': self.db_password.text().strip(),
            'database': self.db_database.text().strip()
        }

        self.refresh_db_list()
        self.refresh_db_combo()
        Toast.information(self, "成功", f"数据库配置 '{name}' 已添加")

    def update_db_config(self):
        """更新数据库配置配置"""
        current_name = self.db_combo.currentText()
        if not current_name:
            Toast.warning(self, "警告", "请选择要更新的连接")
            return

        old_name = current_name
        new_name = self.db_name.text().strip()

        if not new_name:
            Toast.warning(self, "警告", "请输入配置名称")
            return

        # 如果名称改变，检查新名称是否已存在
        if old_name != new_name and new_name in self.db_configs:
            Toast.warning(self, "警告", f"配置名称 '{new_name}' 已存在")
            return

        # 更新配置
        if old_name != new_name:
            # 删除旧的，添加新的
            self.db_configs[new_name] = self.db_configs.pop(old_name)

        # 更新配置内容
        self.db_configs[new_name] = {
            'host': self.db_host.text().strip(),
            'port': self.db_port.text().strip(),
            'username': self.db_username.text().strip(),
            'password': self.db_password.text().strip(),
            'database': self.db_database.text().strip()
        }

        self.refresh_db_list()
        self.refresh_db_combo()

        # 设置新名称选中
        index = self.db_combo.findText(new_name)
        if index >= 0:
            self.db_combo.setCurrentIndex(index)

        Toast.information(self, "成功", f"数据库配置 '{new_name}' 已更新")

    def delete_db_config(self):
        """删除数据库配置配置"""
        current_name = self.db_combo.currentText()  # 改为使用 db_combo
        if not current_name:
            Toast.warning(self, "警告", "请选择要删除的连接")
            return

        name = current_name
        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除数据库配置 '{name}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            del self.db_configs[name]
            self.refresh_db_list()
            self.refresh_db_combo()

            # 清空表单
            self.db_name.clear()
            self.db_host.clear()
            self.db_port.clear()
            self.db_username.clear()
            self.db_password.clear()
            self.db_database.clear()

            Toast.information(self, "成功", f"数据库配置 '{name}' 已删除")

    def test_db_connection(self):
        """测试数据库配置"""
        name = self.db_name.text().strip()
        if not name:
            Toast.warning(self, "警告", "请先填写连接配置")
            return

        try:
            connection_params = {
                'host': self.db_host.text().strip(),
                'port': int(self.db_port.text().strip()),
                'user': self.db_username.text().strip(),
                'password': self.db_password.text().strip(),
                'database': self.db_database.text().strip(),
                'charset': 'utf8mb4'
            }

            # 测试连接
            conn = pymysql.connect(**connection_params)
            conn.close()

            Toast.information(self, "成功", "数据库配置测试成功！")
        except Exception as e:
            Toast.critical(self, "连接失败", f"数据库配置测试失败: {str(e)}")

    def delete_sql_config(self):
        """删除SQL操作配置"""
        current_name = self.sql_combo.currentText()
        if not current_name:
            Toast.warning(self, "警告", "请选择要删除的查询")
            return

        name = current_name
        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除操作配置 '{name}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            del self.sql_configs[name]
            self.refresh_sql_combo()
            self.sql_name.clear()
            self.sql_display_name.clear()
            self.sql_editor.clear()
            self.selected_params_list.clear()
            Toast.information(self, "成功", f"操作配置 '{name}' 已删除")

    def save_configs(self):
        """保存配置到文件"""
        config_file = resource_path("config/query_config.json")

        try:
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            config_data = {
                'database_connections': self.db_configs,
                'sql_queries': self.sql_configs,
                'input_fields': self.input_fields
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            # 发送配置保存信号
            self.config_saved.emit("配置保存成功")
            self.close()

        except Exception as e:
            Toast.critical(self, "错误", f"保存配置失败: {e}")
