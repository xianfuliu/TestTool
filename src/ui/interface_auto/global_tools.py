import os
import json
import sys
import random
import string
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QGroupBox, QFormLayout,QCheckBox, QSpinBox,
                             QScrollArea, QSizePolicy,QTreeWidget, QTreeWidgetItem, QComboBox)
from src.ui.widgets.toast_tips import Toast
from PyQt5.QtCore import Qt, pyqtSignal, QThread, pyqtSignal as Signal
from PyQt5.QtGui import QIcon, QColor, QTextCursor
from src.utils.interface_utils.database_utils import DatabaseUtils
from src.utils.interface_utils.script_engine import ScriptEngine
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelComboBox, NoWheelTabWidget
from src.utils.css_utils import get_combobox_style


class ToolTestThread(QThread):
    """工具测试线程"""
    test_finished = Signal(dict)  # 测试结果信号

    def __init__(self, tool_data, test_params=None):
        super().__init__()
        self.tool_data = tool_data
        self.test_params = test_params or {}

    def run(self):
        """执行测试"""
        try:
            result = self.test_tool()
            self.test_finished.emit(result)
        except Exception as e:
            self.test_finished.emit({
                'success': False,
                'error': str(e)
            })

    def test_tool(self):
        """测试工具"""
        tool_type = self.tool_data.get('tool_type')
        config = self.tool_data.get('config', {})

        if tool_type == 'sql':
            return self.test_sql_tool(config)
        elif tool_type == 'random':
            return self.test_random_tool(config)
        elif tool_type == 'python':
            return self.test_python_tool(config)
        elif tool_type == 'timer':
            return self.test_timer_tool(config)
        elif tool_type == 'http':
            return self.test_http_tool(config)
        else:
            return {
                'success': False,
                'error': f'未知工具类型: {tool_type}'
            }

    def test_sql_tool(self, config):
        """测试SQL工具"""
        try:
            db_utils = DatabaseUtils()
            # 测试数据库连接
            connection = db_utils.get_connection(config)
            if connection:
                connection.close()
                return {
                    'success': True,
                    'message': '数据库连接测试成功'
                }
            else:
                return {
                    'success': False,
                    'error': '数据库连接失败'
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'数据库连接测试失败: {str(e)}'
            }

    def test_random_tool(self, config):
        """测试随机数工具"""
        try:
            min_val = config.get('min_value', 1)
            max_val = config.get('max_value', 100)
            rand_type = config.get('type', 'integer')

            if rand_type == 'integer':
                result = random.randint(min_val, max_val)
            elif rand_type == 'float':
                result = random.uniform(min_val, max_val)
            else:  # string
                length = random.randint(min_val, max_val)
                result = ''.join(random.choices(string.ascii_letters + string.digits, k=length))

            return {
                'success': True,
                'message': f'随机数生成测试成功: {result}',
                'data': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'随机数生成测试失败: {str(e)}'
            }

    def test_python_tool(self, config):
        """测试Python脚本工具"""
        try:
            script_engine = ScriptEngine()
            # 测试简单脚本
            test_script = "result = 1 + 1"
            result = script_engine.execute_script(test_script, {}, timeout=5)

            return {
                'success': True,
                'message': 'Python脚本执行测试成功',
                'data': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Python脚本执行测试失败: {str(e)}'
            }

    def test_timer_tool(self, config):
        """测试定时器工具"""
        try:
            max_wait = config.get('max_wait_time', 300)
            if max_wait <= 0 or max_wait > 3600:
                return {
                    'success': False,
                    'error': '等待时间必须在1-3600秒之间'
                }

            return {
                'success': True,
                'message': f'定时器配置验证成功，最大等待时间: {max_wait}秒'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'定时器配置验证失败: {str(e)}'
            }

    def test_http_tool(self, config):
        """测试HTTP工具"""
        try:
            import requests
            timeout = config.get('timeout', 30)

            # 简单的HTTP测试（访问百度）
            response = requests.get('https://www.baidu.com', timeout=timeout)
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'HTTP请求测试成功'
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP请求测试失败，状态码: {response.status_code}'
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'HTTP请求测试失败: {str(e)}'
            }


class GlobalToolDialog(QDialog):
    """全局工具编辑对话框"""

    def __init__(self, parent=None, tool_data=None):
        super().__init__(parent)
        self.tool_data = tool_data or {}
        self.is_edit = bool(tool_data)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑全局工具" if self.is_edit else "新增全局工具")
        self.setMinimumSize(700, 600)
        
        # 设置弹窗样式，确保按钮可见
        self.setStyleSheet("""
            QDialogButtonBox QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                min-width: 80px;
            }
            QDialogButtonBox QPushButton:hover {
                background-color: #45a049;
            }
            QDialogButtonBox QPushButton:pressed {
                background-color: #3d8b40;
            }
            QDialogButtonBox QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

        layout = QVBoxLayout(self)

        # 创建Tab页
        tab_widget = NoWheelTabWidget()

        # 基本信息Tab
        basic_tab = QWidget()
        self.setup_basic_tab(basic_tab)

        # 工具配置Tab
        config_tab = QWidget()
        self.setup_config_tab(config_tab)

        # 测试Tab
        test_tab = QWidget()
        self.setup_test_tab(test_tab)

        tab_widget.addTab(basic_tab, "基本信息")
        tab_widget.addTab(config_tab, "工具配置")
        tab_widget.addTab(test_tab, "测试工具")

        # 按钮布局
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        # 将按钮文字改为中文
        ok_button = button_box.button(QDialogButtonBox.Ok)
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        if ok_button:
            ok_button.setText("确认")
        if cancel_button:
            cancel_button.setText("取消")

        layout.addWidget(tab_widget)
        layout.addWidget(button_box)

        # 加载数据
        if self.is_edit:
            self.load_tool_data()

    def setup_basic_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 基本信息表单
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入工具名称")

        self.type_combo = NoWheelComboBox()
        self.type_combo.addItems([
            "SQL工具", "随机数生成器", "Python脚本执行器",
            "等待定时器", "HTTP请求工具", "自定义工具"
        ])
        self.type_combo.currentIndexChanged.connect(self.on_tool_type_changed)

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setPlaceholderText("请输入工具描述")

        self.enabled_check = QCheckBox("启用工具")
        self.enabled_check.setChecked(True)

        form_layout.addRow("工具名称:", self.name_edit)
        form_layout.addRow("工具类型:", self.type_combo)
        form_layout.addRow("工具描述:", self.desc_edit)
        form_layout.addRow("", self.enabled_check)

        layout.addLayout(form_layout)
        layout.addStretch()

    def setup_config_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 配置区域
        self.config_scroll = QScrollArea()
        self.config_widget = QWidget()
        self.config_layout = QVBoxLayout(self.config_widget)
        self.config_scroll.setWidget(self.config_widget)
        self.config_scroll.setWidgetResizable(True)

        # 默认显示空配置
        self.default_config_group = QGroupBox("工具配置")
        default_layout = QVBoxLayout(self.default_config_group)
        default_layout.addWidget(QLabel("请选择工具类型以显示配置项"))
        self.config_layout.addWidget(self.default_config_group)

        layout.addWidget(self.config_scroll)

    def setup_test_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 测试区域
        test_group = QGroupBox("工具测试")
        test_layout = QVBoxLayout(test_group)

        # 测试按钮
        self.test_btn = QPushButton("测试工具")
        self.test_btn.clicked.connect(self.test_tool)
        # 设置测试按钮样式
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: 1px solid #218838;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
                border-color: #1e7e34;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
                border-color: #1c7430;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                border-color: #6c757d;
                color: #ced4da;
            }
        """)

        # 测试结果
        self.test_result_text = QTextEdit()
        self.test_result_text.setReadOnly(True)
        self.test_result_text.setMaximumHeight(200)

        test_layout.addWidget(QLabel("点击测试按钮验证工具配置是否正确:"))
        test_layout.addWidget(self.test_btn)
        test_layout.addWidget(QLabel("测试结果:"))
        test_layout.addWidget(self.test_result_text)

        layout.addWidget(test_group)
        layout.addStretch()

    def on_tool_type_changed(self):
        """工具类型变化"""
        self.update_config_form()

    def update_config_form(self):
        """更新配置表单"""
        # 清除现有配置
        for i in reversed(range(self.config_layout.count())):
            self.config_layout.itemAt(i).widget().setParent(None)

        tool_type = self.type_combo.currentText()

        if tool_type == "SQL工具":
            self.setup_sql_config()
        elif tool_type == "随机数生成器":
            self.setup_random_config()
        elif tool_type == "Python脚本执行器":
            self.setup_python_config()
        elif tool_type == "等待定时器":
            self.setup_timer_config()
        elif tool_type == "HTTP请求工具":
            self.setup_http_config()
        else:  # 自定义工具
            self.setup_custom_config()

    def setup_sql_config(self):
        """设置SQL工具配置"""
        group = QGroupBox("SQL查询工具配置")
        layout = QFormLayout(group)

        self.sql_database_type = NoWheelComboBox()
        self.sql_database_type.addItems(["MySQL", "PostgreSQL", "SQLite", "Oracle", "SQL Server"])

        self.sql_host = QLineEdit()
        self.sql_host.setPlaceholderText("localhost")

        self.sql_port = QLineEdit()
        self.sql_port.setPlaceholderText("3306")

        self.sql_username = QLineEdit()
        self.sql_username.setPlaceholderText("用户名")

        self.sql_password = QLineEdit()
        self.sql_password.setEchoMode(QLineEdit.Password)
        self.sql_password.setPlaceholderText("密码")

        self.sql_database = QLineEdit()
        self.sql_database.setPlaceholderText("数据库名")

        self.sql_charset = NoWheelComboBox()
        self.sql_charset.addItems(["utf8", "utf8mb4", "gbk", "latin1"])
        self.sql_charset.setCurrentText("utf8mb4")

        self.sql_result_type = NoWheelComboBox()
        self.sql_result_type.addItems(["single", "multiple", "count"])
        self.sql_result_type.setToolTip("single: 返回单条记录\nmultiple: 返回多条记录\ncount: 返回计数")

        layout.addRow("数据库类型:", self.sql_database_type)
        layout.addRow("主机:", self.sql_host)
        layout.addRow("端口:", self.sql_port)
        layout.addRow("用户名:", self.sql_username)
        layout.addRow("密码:", self.sql_password)
        layout.addRow("数据库名:", self.sql_database)
        layout.addRow("字符集:", self.sql_charset)
        layout.addRow("结果类型:", self.sql_result_type)

        self.config_layout.addWidget(group)

    def setup_random_config(self):
        """设置随机数工具配置"""
        group = QGroupBox("随机数生成器配置")
        layout = QFormLayout(group)

        self.random_type = NoWheelComboBox()
        self.random_type.addItems(["integer", "float", "string"])
        self.random_type.currentIndexChanged.connect(self.on_random_type_changed)

        self.random_min = QSpinBox()
        self.random_min.setRange(0, 1000000)
        self.random_min.setValue(1)

        self.random_max = QSpinBox()
        self.random_max.setRange(1, 1000000)
        self.random_max.setValue(100)

        self.random_length = QSpinBox()
        self.random_length.setRange(1, 1000)
        self.random_length.setValue(10)
        self.random_length.setVisible(False)  # 默认隐藏，字符串类型时显示

        self.random_charset = NoWheelComboBox()
        self.random_charset.addItems(["letters", "digits", "alphanumeric", "custom"])
        self.random_charset.setVisible(False)

        self.random_custom_chars = QLineEdit()
        self.random_custom_chars.setPlaceholderText("自定义字符集")
        self.random_custom_chars.setVisible(False)

        layout.addRow("随机数类型:", self.random_type)
        layout.addRow("最小值:", self.random_min)
        layout.addRow("最大值:", self.random_max)
        layout.addRow("生成长度:", self.random_length)
        layout.addRow("字符集:", self.random_charset)
        layout.addRow("自定义字符:", self.random_custom_chars)

        self.config_layout.addWidget(group)

    def on_random_type_changed(self):
        """随机数类型变化"""
        is_string = self.random_type.currentText() == "string"
        self.random_length.setVisible(is_string)
        self.random_charset.setVisible(is_string)
        self.random_custom_chars.setVisible(
            is_string and self.random_charset.currentText() == "custom"
        )

    def setup_python_config(self):
        """设置Python工具配置"""
        group = QGroupBox("Python脚本执行器配置")
        layout = QFormLayout(group)

        self.python_timeout = QSpinBox()
        self.python_timeout.setRange(1, 300)
        self.python_timeout.setValue(30)
        self.python_timeout.setSuffix(" 秒")

        self.python_allowed_modules = QTextEdit()
        self.python_allowed_modules.setMaximumHeight(60)
        self.python_allowed_modules.setPlaceholderText("允许导入的模块，每行一个\n例如: random, datetime, json")

        self.python_default_script = QTextEdit()
        self.python_default_script.setPlaceholderText("默认脚本代码")
        self.python_default_script.setMaximumHeight(100)

        layout.addRow("执行超时:", self.python_timeout)
        layout.addRow("允许模块:", self.python_allowed_modules)
        layout.addRow("默认脚本:", self.python_default_script)

        self.config_layout.addWidget(group)

    def setup_timer_config(self):
        """设置定时器工具配置"""
        group = QGroupBox("等待定时器配置")
        layout = QFormLayout(group)

        self.timer_max_wait = QSpinBox()
        self.timer_max_wait.setRange(1, 3600)
        self.timer_max_wait.setValue(300)
        self.timer_max_wait.setSuffix(" 秒")

        layout.addRow("最大等待时间:", self.timer_max_wait)

        self.config_layout.addWidget(group)

    def setup_http_config(self):
        """设置HTTP工具配置"""
        group = QGroupBox("HTTP请求工具配置")
        layout = QFormLayout(group)

        self.http_timeout = QSpinBox()
        self.http_timeout.setRange(1, 300)
        self.http_timeout.setValue(30)
        self.http_timeout.setSuffix(" 秒")

        self.http_max_redirects = QSpinBox()
        self.http_max_redirects.setRange(0, 10)
        self.http_max_redirects.setValue(5)

        self.http_verify_ssl = QCheckBox("验证SSL证书")
        self.http_verify_ssl.setChecked(True)

        layout.addRow("请求超时:", self.http_timeout)
        layout.addRow("最大重定向:", self.http_max_redirects)
        layout.addRow("", self.http_verify_ssl)

        self.config_layout.addWidget(group)

    def setup_custom_config(self):
        """设置自定义工具配置"""
        group = QGroupBox("自定义工具配置")
        layout = QVBoxLayout(group)

        self.custom_config_text = QTextEdit()
        self.custom_config_text.setPlaceholderText('请输入JSON格式的配置，例如: {"key": "value"}')

        layout.addWidget(QLabel("自定义配置 (JSON格式):"))
        layout.addWidget(self.custom_config_text)

        self.config_layout.addWidget(group)

    def load_tool_data(self):
        """加载工具数据到表单"""
        if not self.tool_data:
            return

        # 基本信息
        self.name_edit.setText(self.tool_data.get('name', ''))

        # 设置工具类型
        type_map = {
            'sql': 'SQL工具',
            'random': '随机数生成器',
            'python': 'Python脚本执行器',
            'timer': '等待定时器',
            'http': 'HTTP请求工具',
            'custom': '自定义工具'
        }
        tool_type = self.tool_data.get('tool_type', 'custom')
        type_text = type_map.get(tool_type, '自定义工具')
        index = self.type_combo.findText(type_text)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)

        self.desc_edit.setText(self.tool_data.get('description', ''))
        self.enabled_check.setChecked(self.tool_data.get('enabled', True))

        # 先更新配置表单，确保相关控件已创建
        self.update_config_form()
        
        # 加载配置
        config = self.tool_data.get('config', {})
        self.load_config_data(config)

    def load_config_data(self, config):
        """加载配置数据"""
        tool_type = self.type_combo.currentText()

        if tool_type == "SQL工具":
            self.sql_database_type.setCurrentText(config.get('database_type', 'MySQL'))
            self.sql_host.setText(config.get('host', ''))
            self.sql_port.setText(str(config.get('port', '')))
            self.sql_username.setText(config.get('username', ''))
            self.sql_password.setText(config.get('password', ''))
            self.sql_database.setText(config.get('database', ''))
            self.sql_charset.setCurrentText(config.get('charset', 'utf8mb4'))
            self.sql_result_type.setCurrentText(config.get('result_type', 'single'))

        elif tool_type == "随机数生成器":
            self.random_type.setCurrentText(config.get('type', 'integer'))
            self.random_min.setValue(config.get('min_value', 1))
            self.random_max.setValue(config.get('max_value', 100))
            self.random_length.setValue(config.get('length', 10))
            self.random_charset.setCurrentText(config.get('charset', 'alphanumeric'))
            self.random_custom_chars.setText(config.get('custom_chars', ''))

        elif tool_type == "Python脚本执行器":
            self.python_timeout.setValue(config.get('timeout', 30))
            modules = config.get('allowed_modules', [])
            self.python_allowed_modules.setText('\n'.join(modules))
            self.python_default_script.setText(config.get('default_script', ''))

        elif tool_type == "等待定时器":
            self.timer_max_wait.setValue(config.get('max_wait_time', 300))

        elif tool_type == "HTTP请求工具":
            self.http_timeout.setValue(config.get('timeout', 30))
            self.http_max_redirects.setValue(config.get('max_redirects', 5))
            self.http_verify_ssl.setChecked(config.get('verify_ssl', True))

        else:  # 自定义工具
            self.custom_config_text.setText(json.dumps(config, indent=2, ensure_ascii=False))

    def get_data(self):
        """获取表单数据"""
        # 基本信息
        data = {
            'name': self.name_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip(),
            'enabled': self.enabled_check.isChecked()
        }

        # 工具类型映射
        type_map = {
            'SQL查询工具': 'sql',
            '随机数生成器': 'random',
            'Python脚本执行器': 'python',
            '等待定时器': 'timer',
            'HTTP请求工具': 'http',
            '自定义工具': 'custom'
        }
        tool_type_text = self.type_combo.currentText()
        data['tool_type'] = type_map.get(tool_type_text, 'custom')

        # 配置数据
        config = self.get_config_data()
        data['config'] = config

        return data

    def get_config_data(self):
        """获取配置数据"""
        tool_type = self.type_combo.currentText()

        if tool_type == "SQL查询工具":
            return {
                'database_type': self.sql_database_type.currentText(),
                'host': self.sql_host.text().strip(),
                'port': int(self.sql_port.text()) if self.sql_port.text().strip() else 3306,
                'username': self.sql_username.text().strip(),
                'password': self.sql_password.text(),
                'database': self.sql_database.text().strip(),
                'charset': self.sql_charset.currentText(),
                'result_type': self.sql_result_type.currentText()
            }

        elif tool_type == "随机数生成器":
            config = {
                'type': self.random_type.currentText(),
                'min_value': self.random_min.value(),
                'max_value': self.random_max.value()
            }
            if self.random_type.currentText() == 'string':
                config['length'] = self.random_length.value()
                config['charset'] = self.random_charset.currentText()
                if self.random_charset.currentText() == 'custom':
                    config['custom_chars'] = self.random_custom_chars.text().strip()
            return config

        elif tool_type == "Python脚本执行器":
            modules_text = self.python_allowed_modules.toPlainText().strip()
            modules = [m.strip() for m in modules_text.split('\n') if m.strip()]

            return {
                'timeout': self.python_timeout.value(),
                'allowed_modules': modules,
                'default_script': self.python_default_script.toPlainText().strip()
            }

        elif tool_type == "等待定时器":
            return {
                'max_wait_time': self.timer_max_wait.value()
            }

        elif tool_type == "HTTP请求工具":
            return {
                'timeout': self.http_timeout.value(),
                'max_redirects': self.http_max_redirects.value(),
                'verify_ssl': self.http_verify_ssl.isChecked()
            }

        else:  # 自定义工具
            if hasattr(self, 'custom_config_text'):
                config_text = self.custom_config_text.toPlainText().strip()
                if config_text:
                    try:
                        return json.loads(config_text)
                    except json.JSONDecodeError:
                        return {}
            return {}

    def test_tool(self):
        """测试工具"""
        tool_data = self.get_data()

        # 验证基本数据
        if not tool_data['name']:
            Toast.warn(self, "工具名称不能为空")
            return

        # 禁用测试按钮，防止重复测试
        self.test_btn.setEnabled(False)
        self.test_result_text.clear()
        self.test_result_text.append("正在测试工具...")

        # 在后台线程中测试工具
        self.test_thread = ToolTestThread(tool_data)
        self.test_thread.test_finished.connect(self.on_test_finished)
        self.test_thread.start()

    def on_test_finished(self, result):
        """测试完成"""
        self.test_btn.setEnabled(True)

        if result['success']:
            self.test_result_text.append("✅ 测试成功!")
            self.test_result_text.append(result.get('message', '工具测试通过'))
            if 'data' in result:
                self.test_result_text.append(f"测试数据: {result['data']}")
        else:
            self.test_result_text.append("❌ 测试失败!")
            self.test_result_text.append(result.get('error', '未知错误'))

        # 滚动到底部
        cursor = self.test_result_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.test_result_text.setTextCursor(cursor)


class GlobalToolsManager(QWidget):
    """全局工具管理页面"""
    data_changed = pyqtSignal()  # 数据变化信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.tool_service = None  # 延迟初始化，避免启动时数据库连接检查
        
        # 分页相关变量初始化
        self.current_page = 1
        self.current_page_size = 20
        self.total_pages = 0
        self.total_records = 0
        
        self.init_ui()
        # 延迟加载数据，避免启动时弹窗
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.delayed_load_data)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # 工具栏 - 简化设计，直接添加按钮
        # 使用QPushButton创建文字按钮
        self.add_button = QPushButton("新增")
        self.add_button.setFixedSize(90, 35)
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.add_button.clicked.connect(self.add_tool)

        # 直接添加按钮到主布局
        main_layout.addWidget(self.add_button)

        # 工具列表 - 使用与定时调度tab中调度任务列表相同的QTreeWidget组件和样式
        self.tree_widget = QTreeWidget()
        self.tree_widget.setColumnCount(8)  # 明确设置列数：序号、工具名称、工具类型、状态、描述、创建时间、更新时间、操作
        self.tree_widget.setHeaderLabels([
            "序号", "工具名称", "工具类型", "状态", "描述", "创建时间", "更新时间", "操作"
        ])
        
        # 设置树形控件属性 - 完全匹配定时调度tab中tree_widget配置
        header = self.tree_widget.header()
        header.setSectionsMovable(False)  # 禁止表头拖拽
        header.setDefaultAlignment(Qt.AlignCenter)  # 表头文本居中
        
        # 设置树形控件属性
        self.tree_widget.setSelectionBehavior(QTreeWidget.SelectRows)
        self.tree_widget.setContextMenuPolicy(Qt.NoContextMenu)  # 禁用右键菜单
        self.tree_widget.setRootIsDecorated(False)  # 不显示展开/折叠图标列
        self.tree_widget.setAlternatingRowColors(True)
        
        # 设置所有列文本居中
        for i in range(self.tree_widget.columnCount()):
            self.tree_widget.headerItem().setTextAlignment(i, Qt.AlignCenter)
        
        # 设置固定列宽 - 参考定时调度tab的列宽设计
        self.tree_widget.setColumnWidth(0, 100)     # 序号
        self.tree_widget.setColumnWidth(1, 450)    # 工具名称
        self.tree_widget.setColumnWidth(2, 200)    # 工具类型
        self.tree_widget.setColumnWidth(3, 150)      # 状态
        self.tree_widget.setColumnWidth(4, 350)    # 描述
        self.tree_widget.setColumnWidth(5, 300)    # 创建时间
        self.tree_widget.setColumnWidth(6, 300)    # 更新时间
        self.tree_widget.setColumnWidth(7, 300)    # 操作
        
        # 参考定时调度UI的表格样式美化
        self.tree_widget.setStyleSheet("""
            QTreeWidget {
                background-color: #f8f9fa;
                alternate-background-color: #ffffff;
                gridline-color: #e9ecef;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                outline: 0;
            }
            QTreeWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #e9ecef;
                text-align: center;
                height: 32px;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
                font-weight: bold;
            }
            QTreeWidget::item:selected:!active {
                background-color: #e3f2fd;
                color: #1976d2;
                font-weight: bold;
            }
            QTreeWidget::item:hover {
                background-color: #f8f9fa;
            }
            QTreeWidget::item:has-children {
                background-color: #f1f3f4;
                font-weight: bold;
            }
            QTreeWidget::item:has-children:hover {
                background-color: #e8eaed;
            }
            QTreeWidget::branch:has-siblings:!adjoins-item {
                border-image: url(vline.png) 0;
            }
            QTreeWidget::branch:has-siblings:adjoins-item {
                border-image: url(branch-more.png) 0;
            }
            QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {
                border-image: url(branch-end.png) 0;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                border-image: none;
                image: url(branch-closed.png);
            }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                border-image: none;
                image: url(branch-open.png);
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #495057;
                font-weight: 600;
                font-size: 13px;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid #1976d2;
                min-height: 25px;
                text-align: center;
            }
            QHeaderView::section:hover {
                background-color: #e9ecef;
            }
        """)

        # 关键设置：设置树形控件大小策略，允许充分拉伸
        self.tree_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree_widget.setMinimumHeight(400)  # 设置最小高度
        
        main_layout.addWidget(self.tree_widget, 1)

        # 分页控件
        self.pagination_widget = QWidget()
        pagination_layout = QHBoxLayout(self.pagination_widget)
        pagination_layout.setContentsMargins(10, 5, 10, 5)
        pagination_layout.setSpacing(10)
        
        # 分页信息标签
        self.pagination_label = QLabel("共 0 条记录")
        self.pagination_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        pagination_layout.addWidget(self.pagination_label)
        
        pagination_layout.addStretch()
        
        # 首页按钮
        self.first_page_btn = QPushButton("« 首页")
        self.first_page_btn.setFixedSize(70, 32)
        self.first_page_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border-radius: 6px;
                padding: 6px 8px;
                font-size: 12px;
                font-weight: 500;
                color: #495057;
                margin: 1px;
            }
            QPushButton:hover:enabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007bff, stop:1 #0056b3);
                color: white;
                border: 1px solid #007bff;
            }
            QPushButton:pressed:enabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0056b3, stop:1 #004085);
                border: 1px solid #004085;
            }
            QPushButton:disabled {
                background: #f8f9fa;
                color: #adb5bd;
            }
        """)
        pagination_layout.addWidget(self.first_page_btn)
        
        # 上一页按钮
        self.prev_page_btn = QPushButton("‹ 上一页")
        self.prev_page_btn.setFixedSize(70, 32)
        self.prev_page_btn.setStyleSheet(self.first_page_btn.styleSheet())
        pagination_layout.addWidget(self.prev_page_btn)
        
        # 页码输入框
        self.page_input = QLineEdit()
        self.page_input.setFixedSize(50, 32)
        self.page_input.setAlignment(Qt.AlignCenter)
        self.page_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
                background-color: #ffffff;
                font-weight: 500;
                margin: 1px;
            }
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
                box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
            }
            QLineEdit:hover:enabled {
                border-color: #adb5bd;
            }
        """)
        pagination_layout.addWidget(self.page_input)
        
        # 总页数标签
        self.total_pages_label = QLabel("/ 0")
        self.total_pages_label.setStyleSheet("color: #6c757d; font-size: 12px; font-weight: 500; margin: 0 4px;")
        pagination_layout.addWidget(self.total_pages_label)
        
        # 下一页按钮
        self.next_page_btn = QPushButton("下一页 ›")
        self.next_page_btn.setFixedSize(70, 32)
        self.next_page_btn.setStyleSheet(self.first_page_btn.styleSheet())
        pagination_layout.addWidget(self.next_page_btn)
        
        # 末页按钮
        self.last_page_btn = QPushButton("末页 »")
        self.last_page_btn.setFixedSize(70, 32)
        self.last_page_btn.setStyleSheet(self.first_page_btn.styleSheet())
        pagination_layout.addWidget(self.last_page_btn)
        
        # 每页显示数量选择
        self.page_size_combo = QComboBox()
        self.page_size_combo.setFixedSize(85, 32)
        self.page_size_combo.addItems(["10", "20", "50", "100"])
        self.page_size_combo.setCurrentText("20")
        self.page_size_combo.setStyleSheet(get_combobox_style())
        pagination_layout.addWidget(self.page_size_combo)
        
        main_layout.addWidget(self.pagination_widget)



        # 连接分页控件信号
        self.first_page_btn.clicked.connect(self.go_to_first_page)
        self.prev_page_btn.clicked.connect(self.go_to_prev_page)
        self.next_page_btn.clicked.connect(self.go_to_next_page)
        self.last_page_btn.clicked.connect(self.go_to_last_page)
        self.page_input.returnPressed.connect(self.go_to_specific_page)
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)

    def delayed_load_data(self):
        """延迟加载数据，避免启动时弹窗"""
        try:
            from src.core.services.global_tool_service import GlobalToolService
            self.tool_service = GlobalToolService()
            self.load_tools_with_pagination()
        except Exception as e:
            # 静默处理异常，避免启动时弹窗
            print(f"GlobalToolsManager初始化失败: {e}")

    def get_icon(self, icon_name):
        """获取图标"""
        try:
            # 打包后路径处理：尝试从 PyInstaller 临时解压目录加载
            if getattr(sys, 'frozen', False):
                # 打包后的可执行文件路径
                base_path = sys._MEIPASS
                # 尝试从打包后的 resources/icons 目录加载
                icon_path = os.path.join(base_path, "src", "resources", "icons", icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
                
                # 尝试直接加载图标文件
                icon_path = os.path.join(base_path, icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
                
                # 尝试从当前目录加载
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "icons", icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
            
            # 开发环境：尝试从 ui/interface_auto/icons 目录加载
            icon_path = os.path.join("src", "ui", "interface_auto", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
            
            # 尝试从 resources/icons 目录加载
            icon_path = os.path.join("src", "resources", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
        except:
            pass
        return QIcon()

    def edit_tool_by_id(self, tool_id):
        """根据工具ID编辑工具"""
        try:
            tool_data = self.tool_service.get_tool_by_id(tool_id)
            if not tool_data:
                Toast.warn(self, "工具不存在")
                return

            dialog = GlobalToolDialog(self, tool_data)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_data()
                if not data['name']:
                    Toast.warn(self, "工具名称不能为空")
                    return

                try:
                    self.tool_service.update_tool(tool_id, data)
                    self.load_tools_with_pagination()
                    self.data_changed.emit()
                    Toast.success(self, "工具更新成功")
                except Exception as e:
                    Toast.error(self, f"更新工具失败: {str(e)}")
        except Exception as e:
            Toast.error(self, f"编辑工具失败: {str(e)}")

    def get_selected_tool_id(self):
        """获取选中的工具ID"""
        selected_items = self.tree_widget.selectedItems()
        if selected_items:
            return selected_items[0].data(0, Qt.UserRole)
        return None

    def get_selected_tool_data(self):
        """获取选中的工具数据"""
        tool_id = self.get_selected_tool_id()
        if tool_id:
            return self.tool_service.get_tool_by_id(tool_id)
        return None

    def add_tool(self):
        """新增工具"""
        dialog = GlobalToolDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warn(self, "工具名称不能为空")
                return

            try:
                self.tool_service.create_tool(data)
                self.load_tools_with_pagination()
                self.data_changed.emit()
                Toast.success(self, "工具创建成功")
            except Exception as e:
                Toast.error(self, f"创建工具失败: {str(e)}")

    def edit_selected_tool(self):
        """编辑选中的工具"""
        tool_data = self.get_selected_tool_data()
        if not tool_data:
            Toast.warn(self, "请先选择一个工具")
            return

        dialog = GlobalToolDialog(self, tool_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warn(self, "工具名称不能为空")
                return

            try:
                self.tool_service.update_tool(tool_data['id'], data)
                self.load_tools_with_pagination()
                self.data_changed.emit()
                Toast.success(self, "工具更新成功")
            except Exception as e:
                Toast.error(self, f"更新工具失败: {str(e)}")

    def delete_selected_tool(self):
        """删除选中的工具"""
        tool_data = self.get_selected_tool_data()
        if not tool_data:
            Toast.warn(self, "请先选择一个工具")
            return

        # 创建确认对话框，手动设置按钮文本
        msg_box = QMessageBox(QMessageBox.Question, "确认删除",
                             f"确定要删除工具 '{tool_data['name']}' 吗？")
        
        # 添加确认和取消按钮
        confirm_btn = msg_box.addButton("确认", QMessageBox.YesRole)
        cancel_btn = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_btn)
        
        msg_box.exec_()
        
        if msg_box.clickedButton() == confirm_btn:
            try:
                self.tool_service.delete_tool(tool_data['id'])
                self.load_tools_with_pagination()
                self.data_changed.emit()
                Toast.success(self, "工具删除成功")
            except Exception as e:
                Toast.error(self, f"删除工具失败: {str(e)}")

    def test_selected_tool(self):
        """测试选中的工具"""
        tool_data = self.get_selected_tool_data()
        if not tool_data:
            Toast.warn(self, "请先选择一个工具")
            return

        # 打开测试对话框
        dialog = GlobalToolDialog(self, tool_data)
        # 直接切换到测试Tab
        dialog.tab_widget.setCurrentIndex(2)
        dialog.exec_()

    def toggle_selected_tool(self):
        """启用/禁用选中的工具"""
        tool_data = self.get_selected_tool_data()
        if not tool_data:
            Toast.warn(self, "请先选择一个工具")
            return

        new_status = not tool_data['enabled']
        status_text = "启用" if new_status else "禁用"

        try:
                self.tool_service.update_tool_status(tool_data['id'], new_status)
                self.load_tools_with_pagination()
                self.data_changed.emit()
                Toast.success(self, f"工具已{status_text}")
        except Exception as e:
            Toast.error(self, f"{status_text}工具失败: {str(e)}")

    def delete_tool_by_id(self, tool_id):
        """根据工具ID删除工具"""
        try:
            tool_data = self.tool_service.get_tool_by_id(tool_id)
            if not tool_data:
                Toast.warn(self, "工具不存在")
                return

            # 创建确认对话框
            msg_box = QMessageBox(QMessageBox.Question, "确认删除",
                                 f"确定要删除工具 '{tool_data['name']}' 吗？")
            
            confirm_btn = msg_box.addButton("确认", QMessageBox.YesRole)
            cancel_btn = msg_box.addButton("取消", QMessageBox.NoRole)
            msg_box.setDefaultButton(cancel_btn)
            
            msg_box.exec_()
            
            if msg_box.clickedButton() == confirm_btn:
                self.tool_service.delete_tool(tool_id)
                self.load_tools_with_pagination()
                self.data_changed.emit()
                Toast.success(self, "工具删除成功")
        except Exception as e:
            Toast.error(self, f"删除工具失败: {str(e)}")

    def toggle_tool_by_id(self, tool_id):
        """根据工具ID启用/禁用工具"""
        try:
            tool_data = self.tool_service.get_tool_by_id(tool_id)
            if not tool_data:
                Toast.warn(self, "工具不存在")
                return

            new_status = not tool_data['enabled']
            status_text = "启用" if new_status else "禁用"

            self.tool_service.update_tool_status(tool_id, new_status)
            self.load_tools_with_pagination()
            self.data_changed.emit()
            Toast.success(self, f"工具已{status_text}")
        except Exception as e:
            Toast.error(self, f"{status_text}工具失败: {str(e)}")

    def copy_tool_by_id(self, tool_id):
        """根据工具ID复制工具"""
        try:
            # 获取原始工具数据
            tool_data = self.tool_service.get_tool_by_id(tool_id)
            if not tool_data:
                Toast.warn(self, "工具不存在")
                return

            # 生成不重复的工具名称
            new_name = self.generate_unique_copy_name(tool_data['name'])
            
            # 深拷贝工具数据
            import copy
            new_tool_data = copy.deepcopy(tool_data)
            
            # 更新复制后的工具数据
            new_tool_data['name'] = new_name
            new_tool_data['id'] = None  # 清除ID以创建新记录
            new_tool_data['created_at'] = None  # 清除创建时间
            new_tool_data['updated_at'] = None  # 清除更新时间
            
            # 创建新工具
            self.tool_service.create_tool(new_tool_data)
            
            # 重新加载工具列表
            self.load_tools_with_pagination()
            self.data_changed.emit()
            
            Toast.success(self, f"工具复制成功: {new_name}")
            
        except Exception as e:
            Toast.error(self, f"复制工具失败: {str(e)}")

    def generate_unique_copy_name(self, original_name):
        """生成唯一的副本名称"""
        # 获取所有工具
        tools = self.tool_service.get_all_tools()
        
        # 查找所有以原始名称开头的副本
        copy_pattern = f"{original_name}_副本"
        existing_copies = []
        
        for tool in tools:
            name = tool['name']
            if name.startswith(copy_pattern):
                # 提取副本编号
                suffix = name[len(copy_pattern):]
                if suffix.isdigit():
                    existing_copies.append(int(suffix))
                elif suffix == "":
                    existing_copies.append(1)  # 默认第一个副本
        
        # 确定下一个副本编号
        if existing_copies:
            next_copy_num = max(existing_copies) + 1
        else:
            next_copy_num = 1
        
        # 生成副本名称
        if next_copy_num == 1:
            return f"{original_name}_副本"
        else:
            return f"{original_name}_副本{next_copy_num}"

    def load_tools_with_pagination(self):
        """使用分页加载工具列表"""
        # 检查服务对象是否已初始化
        if self.tool_service is None:
            print("GlobalToolsManager: tool_service未初始化，跳过加载")
            return
            
        try:
            # 调用分页服务方法
            tools, total_records = self.tool_service.get_tools_with_pagination(
                self.current_page, self.current_page_size
            )
            
            # 更新分页信息
            self.total_records = total_records
            self.total_pages = max(1, (total_records + self.current_page_size - 1) // self.current_page_size)
            
            # 清空树形控件
            self.tree_widget.clear()

            # 计算当前页的起始序号
            start_index = (self.current_page - 1) * self.current_page_size
            
            for index, tool in enumerate(tools):
                # 创建树形项
                tree_item = QTreeWidgetItem()
                tree_item.setData(0, Qt.UserRole, tool['id'])
                
                # 序号栏 - 使用全局序号
                tree_item.setText(0, str(start_index + index + 1))
                tree_item.setTextAlignment(0, Qt.AlignCenter)

                # 工具名称 - 确保居中显示
                tree_item.setText(1, tool['name'])
                tree_item.setTextAlignment(1, Qt.AlignCenter)

                # 工具类型
                type_map = {
                    'sql': 'SQL工具',
                    'random': '随机数生成器',
                    'python': 'Python脚本执行器',
                    'timer': '等待定时器',
                    'http': 'HTTP请求工具',
                    'custom': '自定义工具'
                }
                type_text = type_map.get(tool['tool_type'], tool['tool_type'])
                tree_item.setText(2, type_text)
                tree_item.setTextAlignment(2, Qt.AlignCenter)

                # 状态 - 使用现代化样式
                status_text = "启用" if tool['enabled'] else "禁用"
                tree_item.setText(3, status_text)
                tree_item.setTextAlignment(3, Qt.AlignCenter)
                
                # 设置状态文本的字体和样式
                font = tree_item.font(3)
                font.setBold(True)
                tree_item.setFont(3, font)
                
                # 设置状态文本的颜色样式
                if tool['enabled']:
                    # 启用状态 - 绿色
                    tree_item.setForeground(3, QColor('#28a745'))
                else:
                    # 禁用状态 - 红色
                    tree_item.setForeground(3, QColor('#dc3545'))
                
                # 描述
                desc = tool.get('description', '')
                tree_item.setText(4, desc)
                tree_item.setToolTip(4, desc)
                tree_item.setTextAlignment(4, Qt.AlignCenter)

                # 创建时间
                created_at = tool.get('created_at')
                created_text = created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else ""
                tree_item.setText(5, created_text)
                tree_item.setTextAlignment(5, Qt.AlignCenter)

                # 更新时间
                updated_at = tool.get('updated_at')
                updated_text = updated_at.strftime('%Y-%m-%d %H:%M:%S') if updated_at else ""
                tree_item.setText(6, updated_text)
                tree_item.setTextAlignment(6, Qt.AlignCenter)

                # 操作栏 - 使用图标按钮，完全匹配定时调度tab的设计
                action_widget = QWidget()
                action_widget.setStyleSheet("background-color: transparent;")
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(5, 2, 5, 2)
                action_layout.setSpacing(3)
                action_layout.setAlignment(Qt.AlignCenter)
                
                # 编辑按钮
                edit_button = QPushButton()
                edit_button.setFixedSize(25, 25)
                edit_button.setIcon(self.get_icon("edit.png"))
                edit_button.setToolTip("编辑")
                edit_button.setStyleSheet("""
                    QPushButton { 
                        border: none; 
                        background: transparent; 
                        padding: 0px; 
                    } 
                    QPushButton:hover { 
                        background: #e0e0e0; 
                    }
                    QToolTip {
                        background-color: white;
                        color: black;
                        border: 1px solid #cccccc;
                        border-radius: 3px;
                        padding: 5px;
                    }
                """)
                edit_button.clicked.connect(lambda checked, tool_id=tool['id']: self.edit_tool_by_id(tool_id))
                
                # 删除按钮
                delete_button = QPushButton()
                delete_button.setFixedSize(25, 25)
                delete_button.setIcon(self.get_icon("delete.png"))
                delete_button.setToolTip("删除")
                delete_button.setStyleSheet("""
                    QPushButton { 
                        border: none; 
                        background: transparent; 
                        padding: 0px; 
                    } 
                    QPushButton:hover { 
                        background: #e0e0e0; 
                    }
                    QToolTip {
                        background-color: white;
                        color: black;
                        border: 1px solid #cccccc;
                        border-radius: 3px;
                        padding: 5px;
                    }
                """)
                delete_button.clicked.connect(lambda checked, tool_id=tool['id']: self.delete_tool_by_id(tool_id))
                
                # 复制按钮
                copy_button = QPushButton()
                copy_button.setFixedSize(25, 25)
                copy_button.setIcon(self.get_icon("copy.png"))
                copy_button.setToolTip("复制")
                copy_button.setStyleSheet("""
                    QPushButton { 
                        border: none; 
                        background: transparent; 
                        padding: 0px; 
                    } 
                    QPushButton:hover { 
                        background: #e0e0e0; 
                    }
                    QToolTip {
                        background-color: white;
                        color: black;
                        border: 1px solid #cccccc;
                        border-radius: 3px;
                        padding: 5px;
                    }
                """)
                copy_button.clicked.connect(lambda checked, tool_id=tool['id']: self.copy_tool_by_id(tool_id))
                
                # 启用/禁用按钮
                toggle_button = QPushButton()
                toggle_button.setFixedSize(25, 25)
                if tool['enabled']:
                    toggle_button.setIcon(self.get_icon("stop.png"))
                    toggle_button.setToolTip("禁用")
                else:
                    toggle_button.setIcon(self.get_icon("start.png"))
                    toggle_button.setToolTip("启用")
                toggle_button.setStyleSheet("""
                    QPushButton { 
                        border: none; 
                        background: transparent; 
                        padding: 0px; 
                    } 
                    QPushButton:hover { 
                        background: #e0e0e0; 
                    }
                    QToolTip {
                        background-color: white;
                        color: black;
                        border: 1px solid #cccccc;
                        border-radius: 3px;
                        padding: 5px;
                    }
                """)
                toggle_button.clicked.connect(lambda checked, tool_id=tool['id']: self.toggle_tool_by_id(tool_id))
                
                action_layout.addWidget(toggle_button)
                action_layout.addWidget(edit_button)
                action_layout.addWidget(copy_button)
                action_layout.addWidget(delete_button)
                
                # 为操作列设置空文本
                tree_item.setText(7, "")
                tree_item.setTextAlignment(7, Qt.AlignCenter)
                
                # 先添加到树形控件
                self.tree_widget.addTopLevelItem(tree_item)
                
                # 然后将按钮容器添加到树形项
                self.tree_widget.setItemWidget(tree_item, 7, action_widget)

            # 更新分页控件状态
            self.update_pagination_status()

        except Exception as e:
            # 静默处理异常，避免启动时弹窗
            print(f"GlobalToolsManager加载分页工具列表失败: {e}")

    def update_pagination_status(self):
        """更新分页控件状态"""
        # 更新分页标签
        self.pagination_label.setText(f"共 {self.total_records} 条记录")
        self.total_pages_label.setText(f"/ {self.total_pages}")
        
        # 更新页码输入框
        self.page_input.setText(str(self.current_page))
        
        # 更新按钮状态
        self.first_page_btn.setEnabled(self.current_page > 1)
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages)
        self.last_page_btn.setEnabled(self.current_page < self.total_pages)

    def go_to_first_page(self):
        """跳转到首页"""
        if self.current_page != 1:
            self.current_page = 1
            self.load_tools_with_pagination()

    def go_to_prev_page(self):
        """跳转到上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_tools_with_pagination()

    def go_to_next_page(self):
        """跳转到下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_tools_with_pagination()

    def go_to_last_page(self):
        """跳转到末页"""
        if self.current_page != self.total_pages:
            self.current_page = self.total_pages
            self.load_tools_with_pagination()

    def go_to_specific_page(self):
        """跳转到指定页码"""
        try:
            page_num = int(self.page_input.text().strip())
            if 1 <= page_num <= self.total_pages:
                self.current_page = page_num
                self.load_tools_with_pagination()
            else:
                # 页码无效，恢复当前页码
                self.page_input.setText(str(self.current_page))
        except ValueError:
            # 输入无效，恢复当前页码
            self.page_input.setText(str(self.current_page))

    def on_page_size_changed(self, page_size_text):
        """每页显示数量改变"""
        try:
            new_page_size = int(page_size_text)
            if new_page_size > 0:
                self.current_page_size = new_page_size
                self.current_page = 1  # 重置到第一页
                self.load_tools_with_pagination()
        except ValueError:
            # 恢复原来的值
            self.page_size_combo.setCurrentText(str(self.current_page_size))
