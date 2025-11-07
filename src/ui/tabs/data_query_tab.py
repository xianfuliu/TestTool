from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QLineEdit, QPushButton, QGroupBox, QScrollArea, QPlainTextEdit, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from src.ui.widgets.toast_tips import Toast
from src.utils.resource_utils import resource_path
from src.utils.sql_worker import SQLWorker
from src.ui.dialogs.data_query_database_config_dialog import DatabaseConfigDialog
import json
import os
import re
import traceback


class DataQueryTab(QWidget):
    """重构后的数据查询Tab - 每个按钮对应一个输出框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.db_configs = {}
        self.sql_configs = {}
        self.input_fields_config = {}  # 输入字段配置
        self.input_widgets = {}  # 存储输入控件
        self.output_textedits = {}  # 存储每个查询对应的输出框
        self.query_buttons = {}  # 存储查询按钮
        self.query_config_path = "config/query_config.json"

        # 先加载配置，再初始化UI
        self.load_configs()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 第一行：查询条件
        input_panel = self.create_input_panel()
        main_layout.addWidget(input_panel)

        # 第二行：查询按钮和结果区域
        content_layout = QHBoxLayout()

        # 左侧：查询按钮区域
        button_panel = self.create_button_panel()
        content_layout.addWidget(button_panel, 1)

        # 右侧：结果展示区域
        result_panel = self.create_result_panel()
        content_layout.addWidget(result_panel, 2)

        main_layout.addLayout(content_layout, 1)

        # 刷新查询按钮（确保配置已加载）
        self.refresh_query_buttons()

    def create_input_panel(self):
        """创建输入面板"""
        panel = QGroupBox()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # 创建输入字段的网格布局
        input_grid_layout = QGridLayout()
        input_grid_layout.setHorizontalSpacing(5)  # 进一步减少水平间距
        input_grid_layout.setVerticalSpacing(8)

        # 动态创建输入字段
        self.create_input_fields(input_grid_layout)

        # 将输入字段网格添加到主布局
        layout.addLayout(input_grid_layout)

        # 按钮区域 - 单独一行，右对齐
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)  # 添加拉伸，使按钮右对齐

        # 数据库配置按钮
        self.db_config_btn = QPushButton("配置")
        self.db_config_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.db_config_btn.clicked.connect(self.manage_configs)
        button_layout.addWidget(self.db_config_btn)

        # 清空按钮
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.clear_btn.clicked.connect(self.clear_inputs)
        button_layout.addWidget(self.clear_btn)

        layout.addLayout(button_layout)

        panel.setLayout(layout)
        return panel

    def create_input_fields(self, layout):
        """根据配置动态创建输入字段"""
        self.input_widgets.clear()

        if not self.input_fields_config:
            print("警告：input_fields_config 为空，将显示无输入字段")
            return

        # 创建输入字段
        row, col = 0, 0
        max_cols = 4  # 每行最多3个字段

        for field_name, field_config in self.input_fields_config.items():
            # 创建水平布局容器，将标签和输入框组合在一起
            field_container = QHBoxLayout()
            field_container.setSpacing(5)  # 标签和输入框之间的小间距
            field_container.setContentsMargins(0, 0, 0, 0)

            # 创建标签
            label = QLabel(field_config['label'] + "：")
            label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            label.setMinimumWidth(30)  # 设置标签最小宽度
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 左对齐

            # 创建输入框
            input_widget = QLineEdit()
            input_widget.setPlaceholderText(field_config.get('placeholder', ''))
            input_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            input_widget.setFixedWidth(250)  # 固定宽度

            # 将标签和输入框添加到容器
            field_container.addWidget(label)
            field_container.addWidget(input_widget)
            field_container.addStretch(1)  # 添加拉伸，确保内容左对齐

            # 将容器添加到网格布局
            layout.addLayout(field_container, row, col)

            # 保存引用
            self.input_widgets[field_name] = input_widget

            # 更新位置
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def create_default_input_fields_config(self):
        """创建默认的输入字段配置"""
        self.input_fields_config = {
            "mobile": {
                "label": "手机号",
                "placeholder": "请输入手机号"
            },
            "id_card": {
                "label": "身份证号",
                "placeholder": "请输入身份证号"
            },
            "guarantor_loan_no": {
                "label": "授信单号",
                "placeholder": "请输入授信单号"
            },
            "loan_no": {
                "label": "借款单号",
                "placeholder": "请输入借款单号"
            },
            "repay_no": {
                "label": "还款单号",
                "placeholder": "请输入还款单号"
            }
        }

    def create_button_panel(self):
        panel = QGroupBox("查询操作")
        layout = QVBoxLayout(panel)

        # 创建一个滚动区域用于按钮
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.buttons_layout = QVBoxLayout(scroll_content)
        self.buttons_layout.setAlignment(Qt.AlignTop)

        # 初始提示
        initial_label = QLabel("加载操作配置中...")
        initial_label.setAlignment(Qt.AlignCenter)
        self.buttons_layout.addWidget(initial_label)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        return panel

    def create_result_panel(self):
        panel = QGroupBox("查询结果")
        layout = QVBoxLayout()

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.results_layout = QVBoxLayout(scroll_content)

        # 初始提示
        initial_label = QLabel("请点击左侧按钮执行查询，结果将显示在这里")
        initial_label.setAlignment(Qt.AlignCenter)
        self.results_layout.addWidget(initial_label)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        panel.setLayout(layout)
        return panel

    def load_configs(self):
        """加载配置"""
        self.db_configs = {}
        self.sql_configs = {}
        self.input_fields_config = {}

        config_file = resource_path(self.query_config_path)

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self.db_configs = config_data.get('database_connections', {})
                    self.sql_configs = config_data.get('sql_queries', {})
                    self.input_fields_config = config_data.get('input_fields', {})

                    print(f"已加载数据库配置配置: {list(self.db_configs.keys())}")
                    print(f"已加载SQL操作配置: {list(self.sql_configs.keys())}")
                    print(f"已加载输入字段配置: {list(self.input_fields_config.keys())}")
            else:
                print(f"配置文件不存在: {config_file}")
                # 如果配置文件不存在，创建默认配置
                self.create_default_configs()

        except Exception as e:
            print(f"加载配置失败: {e}")
            Toast.critical(self, "错误", f"加载配置失败: {e}")
            # 如果配置文件损坏，创建默认配置
            self.create_default_configs()

    def recreate_input_fields(self):
        """重新创建输入字段 - 完全替换版本"""
        print("开始重新创建输入字段...")

        # 查找并移除旧的输入面板
        old_input_panel = None
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QGroupBox) and item.widget().title() == "":
                old_input_panel = item.widget()
                break

        if old_input_panel:
            # 从布局中移除并删除旧面板
            self.layout().removeWidget(old_input_panel)
            old_input_panel.deleteLater()
            print("已移除旧输入面板")

        # 创建新的输入面板
        new_input_panel = self.create_input_panel()
        # 插入到布局的第一个位置
        self.layout().insertWidget(0, new_input_panel)
        print("已添加新输入面板")

        # 强制刷新界面
        self.update()
        self.repaint()

    def create_default_configs(self):
        """创建默认配置"""
        self.db_configs = {
            "default_db": {
                "host": "localhost",
                "port": "3306",
                "username": "root",
                "password": "",
                "database": "test_db"
            }
        }

        self.sql_configs = {
            "query_user_info": {
                "display_name": "查询用户信息",
                "db_connection": "default_db",
                "sql": "SELECT * FROM user_info WHERE mobile = '{mobile}' OR id_card = '{id_card}' LIMIT 100",
                "required_params": [],
                "output_fields": {
                    "user_id": "用户ID",
                    "user_name": "用户名",
                    "mobile": "手机号",
                    "id_card": "身份证号",
                    "create_time": "创建时间"
                }
            }
        }

        self.input_fields_config = {
            "mobile": {
                "label": "手机号",
                "placeholder": "请输入手机号"
            },
            "id_card": {
                "label": "身份证号",
                "placeholder": "请输入身份证号"
            },
            "guarantor_loan_no": {
                "label": "授信单号",
                "placeholder": "请输入授信单号"
            },
            "loan_no": {
                "label": "借款单号",
                "placeholder": "请输入借款单号"
            },
            "repay_no": {
                "label": "还款单号",
                "placeholder": "请输入还款单号"
            }
        }

        # 保存默认配置
        config_file = resource_path(self.query_config_path)
        try:
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            config_data = {
                'database_connections': self.db_configs,
                'sql_queries': self.sql_configs,
                'input_fields': self.input_fields_config
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存默认配置失败: {e}")

    def refresh_query_buttons(self):
        """刷新查询按钮"""
        # 清空现有按钮
        while self.buttons_layout.count():
            item = self.buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 清空按钮字典
        self.query_buttons.clear()

        # 动态生成按钮
        if not self.sql_configs:
            no_config_label = QLabel("没有可用的操作配置")
            no_config_label.setAlignment(Qt.AlignCenter)
            self.buttons_layout.addWidget(no_config_label)
        else:
            for config_name, config in self.sql_configs.items():
                btn = QPushButton(config['display_name'])
                btn.setProperty('config_name', config_name)
                btn.clicked.connect(self.on_query_button_clicked)
                self.buttons_layout.addWidget(btn)
                self.query_buttons[config_name] = btn

        # 添加拉伸 - 确保按钮始终在顶部
        self.buttons_layout.addStretch(1)

    def on_query_button_clicked(self):
        """查询按钮点击事件"""
        try:
            button = self.sender()
            config_name = button.property('config_name')
            config = self.sql_configs[config_name]

            print(f"执行查询: {config_name}")

            # 检查查询条件
            required_params = config.get('required_params', [])
            missing_params = []
            for param in required_params:
                if param in self.input_widgets:
                    value = self.input_widgets[param].text().strip()
                    if not value:
                        # 获取字段按钮名称
                        field_label = self.input_fields_config.get(param, {}).get('label', param)
                        missing_params.append(field_label)

            if missing_params:
                Toast.warning(self, "警告", f"请填写以下查询条件: {', '.join(missing_params)}")
                return

            # 获取数据库配置配置
            db_connection_name = config.get('db_connection')
            if db_connection_name not in self.db_configs:
                Toast.warning(self, "警告", f"数据库配置 '{db_connection_name}' 未配置")
                return

            db_config = self.db_configs[db_connection_name]
            connection_params = {
                'host': db_config.get('host'),
                'port': int(db_config.get('port', 3306)),
                'user': db_config.get('username'),
                'password': db_config.get('password'),
                'database': db_config.get('database'),
                'charset': 'utf8mb4',
                'connect_timeout': 10,  # 添加连接超时
                'read_timeout': 30,  # 添加读取超时
            }

            # 构建SQL
            sql_template = config['sql']

            # 安全地构建SQL参数
            sql_params = {}
            for field_name, widget in self.input_widgets.items():
                sql_params[field_name] = widget.text().strip()

            # 安全替换参数
            sql = sql_template
            for param, value in sql_params.items():
                placeholder = '{' + param + '}'
                if placeholder in sql:
                    # 对值进行基本的SQL注入防护
                    if value:
                        # 移除可能的SQL注入字符
                        value = re.sub(r'[\'\";]', '', value)
                    # 修复：在参数值周围添加单引号
                    sql = sql.replace(placeholder, f"'{value}'")

            print(f"构建的SQL: {sql}")

            # 创建或获取输出框
            if config_name not in self.output_textedits:
                self.create_output_area(config_name, config['display_name'])

            # 更新输出框状态
            output_textedit = self.output_textedits[config_name]
            output_textedit.setPlainText("查询中...")
            button.setEnabled(False)

            # 在工作线程中执行 SQL
            self.worker = SQLWorker(config_name, connection_params, sql)
            self.worker.finished.connect(self.on_sql_finished)
            self.worker.error.connect(self.on_sql_error)
            self.worker.start()

        except Exception as e:
            error_msg = f"执行查询时发生错误: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            Toast.critical(self, "错误", error_msg)

    def create_output_area(self, config_name, display_name):
        """为查询创建输出区域"""
        # 移除初始提示（如果存在）
        if self.results_layout.count() == 1:
            widget = self.results_layout.itemAt(0).widget()
            if isinstance(widget, QLabel):
                widget.deleteLater()

        # 创建输出区域组
        output_group = QGroupBox(display_name)
        output_layout = QVBoxLayout()

        # 创建输出文本框
        output_textedit = QPlainTextEdit()
        output_textedit.setReadOnly(True)
        output_textedit.setFont(QFont("Consolas", 9))  # 使用等宽字体便于查看JSON
        output_textedit.setMinimumHeight(200)  # 设置最小高度
        output_layout.addWidget(output_textedit)

        output_group.setLayout(output_layout)
        self.results_layout.addWidget(output_group)

        # 保存引用
        self.output_textedits[config_name] = output_textedit

    def on_sql_finished(self, query_name, message, result_data):
        """SQL 执行完成"""
        try:
            print(f"查询完成: {query_name}")
            # 找到对应的按钮并启用
            if query_name in self.query_buttons:
                self.query_buttons[query_name].setEnabled(True)

            # 更新输出框
            if query_name in self.output_textedits:
                output_textedit = self.output_textedits[query_name]

                # 获取输出字段配置
                output_fields = self.sql_configs[query_name].get('output_fields', {})

                # 格式化输出
                if result_data:
                    # 如果有输出字段配置，则只显示配置的字段
                    if output_fields:
                        formatted_data = []
                        for row in result_data:
                            formatted_row = {}
                            for field, display_name in output_fields.items():
                                if field in row:
                                    formatted_row[display_name] = row[field]
                                else:
                                    formatted_row[display_name] = None
                            formatted_data.append(formatted_row)
                    else:
                        formatted_data = result_data

                    # 转换为格式化的JSON字符串
                    try:
                        json_output = json.dumps(formatted_data, ensure_ascii=False, indent=2, default=str)
                        output_textedit.setPlainText(json_output)
                    except Exception as e:
                        output_textedit.setPlainText(f"JSON格式化错误: {str(e)}\n原始数据: {formatted_data}")
                else:
                    output_textedit.setPlainText("[]\n\n# 未查询到数据")

        except Exception as e:
            error_msg = f"处理查询结果时发生错误: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            if query_name in self.output_textedits:
                self.output_textedits[query_name].setPlainText(error_msg)

    def on_sql_error(self, query_name, error_message):
        """SQL 执行错误"""
        try:
            print(f"查询错误: {query_name} - {error_message}")
            # 找到对应的按钮并启用
            if query_name in self.query_buttons:
                self.query_buttons[query_name].setEnabled(True)

            # 更新输出框
            if query_name in self.output_textedits:
                output_textedit = self.output_textedits[query_name]
                # 只显示关键错误信息，避免过长的堆栈跟踪
                if "pymysql" in error_message or "MySQL" in error_message:
                    # 提取主要的错误信息
                    lines = error_message.split('\n')
                    main_error = lines[0] if lines else error_message
                    output_textedit.setPlainText(f"数据库配置错误: {main_error}")
                else:
                    output_textedit.setPlainText(f"错误: {error_message}")

        except Exception as e:
            print(f"处理错误时发生异常: {str(e)}")

    def clear_inputs(self):
        """清空输入条件"""
        for widget in self.input_widgets.values():
            widget.clear()

    def manage_configs(self):
        """打开配置管理对话框"""
        try:
            self.config_dialog = DatabaseConfigDialog(self)
            # 连接配置保存信号
            self.config_dialog.config_saved.connect(self.on_config_saved)
            self.config_dialog.show()
        except Exception as e:
            Toast.critical(self, "错误", f"打开配置管理对话框失败: {str(e)}")

    def on_config_saved(self, message):
        """配置保存后的处理"""
        # 重新加载配置
        self.load_configs()
        # 重新创建输入字段
        self.recreate_input_fields()
        # 刷新查询按钮
        self.refresh_query_buttons()
        # 清空现有结果
        self.clear_results()
        Toast.success(self, message)

    def clear_results(self):
        """清空查询结果"""
        # 清空输出文本框
        for textedit in self.output_textedits.values():
            textedit.clear()

        # 如果所有结果都清空了，显示初始提示
        if self.results_layout.count() == 0:
            initial_label = QLabel("请点击左侧按钮执行查询，结果将显示在这里")
            initial_label.setAlignment(Qt.AlignCenter)
            self.results_layout.addWidget(initial_label)
