import json
import requests
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QTextEdit, QComboBox, QPushButton, QGroupBox, QFormLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView, QDialogButtonBox,
                             QMessageBox, QTabWidget, QScrollArea, QWidget, QCheckBox,
                             QSpinBox, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon
import os
import sys
from src.ui.widgets.toast_tips import Toast


class HttpRequestDialog(QDialog):
    """HTTP请求工具配置对话框"""
    
    request_saved = pyqtSignal(dict)  # 请求配置保存信号
    
    def __init__(self, parent=None, request_data=None):
        super().__init__(parent)
        self.request_data = request_data or {}
        self.is_edit = bool(request_data)
        self.variables = []  # 变量列表
        self.original_data = {}  # 初始化原始数据
        self.init_ui()
        # 在UI初始化后保存原始数据
        self.original_data = self._get_current_data()
        
    def init_ui(self):
        """初始化界面 - 重构版本"""
        self.setWindowTitle("编辑HTTP请求" if self.is_edit else "新增HTTP请求")
        self.setMinimumSize(800, 600)
        
        # 设置对话框样式，按钮背景色改为#4CAF50
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 6px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QDialogButtonBox QPushButton {
                min-width: 80px;
            }
            QComboBox {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 4px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #ccc;
                selection-background-color: #4CAF50;
                selection-color: white;
            }
            QLineEdit, QTextEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 4px;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #ddd;
                border-bottom: none;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #333333;
                border-bottom-color: white;
            }
            QTabBar::tab:hover {
                background-color: #e8f5e8;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # 创建主内容区域
        content_widget = self.create_content_widget()
        layout.addWidget(content_widget)
        
        # 按钮布局
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_save)
        button_box.rejected.connect(self.reject)
        
        # 修改按钮文本
        button_box.button(QDialogButtonBox.Ok).setText("确认")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        
        # 测试按钮
        test_btn = QPushButton("测试请求")
        test_btn.clicked.connect(self.on_test_request)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(test_btn)
        button_layout.addStretch()
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
        
        # 加载数据
        if self.is_edit:
            self.load_request_data()
    
    def create_content_widget(self):
        """创建主内容区域 - 简化容器版本"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)  # 设置整体间距
        
        # 名称字段 - 直接添加到主布局
        name_layout = QHBoxLayout()
        name_label = QLabel("名称:")
        name_label.setFixedWidth(60)
        name_layout.addWidget(name_label)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入HTTP请求名称（必填）")
        name_layout.addWidget(self.name_edit)
        name_layout.addStretch()
        layout.addLayout(name_layout)
        
        # 请求方式和URL在同一行
        method_url_layout = QHBoxLayout()
        
        # 请求方式
        method_layout = QHBoxLayout()
        method_label = QLabel("请求方式:")
        method_label.setFixedWidth(60)
        method_layout.addWidget(method_label)
        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE"])
        self.method_combo.setFixedWidth(120)
        method_layout.addWidget(self.method_combo)
        method_layout.addStretch()
        
        # 请求URL
        url_layout = QHBoxLayout()
        url_label = QLabel("请求URL:")
        url_label.setFixedWidth(60)
        url_layout.addWidget(url_label)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("请输入完整的URL地址（必填）")
        self.url_edit.setMinimumWidth(400)
        url_layout.addWidget(self.url_edit)
        url_layout.addStretch()
        
        method_url_layout.addLayout(method_layout)
        method_url_layout.addSpacing(10)
        method_url_layout.addLayout(url_layout)
        method_url_layout.addStretch()
        
        layout.addLayout(method_url_layout)
        
        # 超时时间
        timeout_layout = QHBoxLayout()
        timeout_label = QLabel("超时时间:")
        timeout_label.setFixedWidth(60)
        timeout_layout.addWidget(timeout_label)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 300)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" 秒")
        self.timeout_spin.setFixedWidth(120)
        timeout_layout.addWidget(self.timeout_spin)
        timeout_layout.addStretch()
        layout.addLayout(timeout_layout)
        
        # 创建Tab页用于请求头和请求体
        tab_widget = QTabWidget()
        
        # 设置Tab样式 - 只有选中的Tab使用绿色
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: white;
            }
            QTabBar::tab {
                background: #e2e8f0;
                border: 1px solid #cbd5e0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                margin-right: 2px;
                color: #4a5568;
            }
            QTabBar::tab:selected {
                background: #4CAF50;
                color: white;
                border-color: #4CAF50;
            }
            QTabBar::tab:hover:!selected {
                background: #cbd5e0;
            }
        """)
        
        # 请求头Tab（放在前面）
        headers_tab = self.create_headers_tab()
        tab_widget.addTab(headers_tab, "请求头")
        
        # 请求体Tab（放在后面，默认选中）
        body_tab = self.create_body_tab()
        tab_widget.addTab(body_tab, "请求体")
        
        # 设置默认选中请求体Tab（索引1）
        tab_widget.setCurrentIndex(1)
        
        layout.addWidget(tab_widget)
        
        # 变量提取区域 - 简化容器结构
        # 添加标题
        variable_title_label = QLabel("响应提取")
        variable_title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 13px;
                color: #333333;
                padding: 8px 0px;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        layout.addWidget(variable_title_label)
        
        # 创建滚动区域
        self.variable_scroll_area = QScrollArea()
        self.variable_scroll_area.setWidgetResizable(True)
        self.variable_scroll_area.setMinimumHeight(150)
        self.variable_scroll_area.setFrameShape(QFrame.Box)  # 保留边框
        self.variable_scroll_area.setStyleSheet("QScrollArea { border: 1px solid #d0d0d0; border-radius: 4px; }")  # 保留外边框
        
        # 滚动区域内容
        scroll_content = QWidget()
        self.variable_scroll_layout = QVBoxLayout(scroll_content)
        self.variable_scroll_layout.setSpacing(8)
        self.variable_scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        self.variable_scroll_area.setWidget(scroll_content)
        layout.addWidget(self.variable_scroll_area)
        
        # 初始化时不添加默认行，保持空白
        self.variable_rows = []
        
        # 确保第一行从顶部开始显示，不居中
        self.variable_scroll_layout.addStretch()
        
        return widget
    
    def add_variable_row(self, insert_after_row=None):
        """添加一行变量提取配置 - 参考断言弹窗样式"""
        row_widget = QWidget()
        row_widget.setObjectName("variable-row")
        row_widget.setStyleSheet("""
            QWidget#variable-row {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px;
                margin: 4px 0;
                background-color: #fafafa;
            }
            QWidget#variable-row:hover {
                background-color: #f0f0f0;
            }
        """)
        
        row_layout = QHBoxLayout(row_widget)
        row_layout.setSpacing(10)
        
        # 变量名输入框
        var_name_edit = QLineEdit()
        var_name_edit.setPlaceholderText("变量名")
        var_name_edit.setMinimumWidth(120)
        
        # 提取路径输入框
        path_edit = QLineEdit()
        path_edit.setPlaceholderText("JSONPath表达式（如$.data.id）")
        path_edit.setMinimumWidth(250)
        
        # 添加按钮 - 使用图标
        add_button = QPushButton()
        add_button.setFixedSize(22, 22)
        add_button.setIcon(self.get_icon("add.png"))
        add_button.setIconSize(QSize(14, 14))
        add_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #e8f5e8;
                border-radius: 3px;
            }
        """)
        
        # 删除按钮 - 使用图标
        delete_button = QPushButton()
        delete_button.setFixedSize(22, 22)
        delete_button.setIcon(self.get_icon("sub.png"))
        delete_button.setIconSize(QSize(14, 14))
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #ffebee;
                border-radius: 3px;
            }
        """)
        
        # 存储行信息
        row_data = {
            'widget': row_widget,
            'var_name_edit': var_name_edit,
            'path_edit': path_edit,
            'add_button': add_button,
            'delete_button': delete_button
        }
        
        # 连接按钮事件
        add_button.clicked.connect(lambda checked, row=row_data: self.add_variable_row(row))
        delete_button.clicked.connect(lambda: self.remove_variable_row(row_data))
        
        # 添加到布局
        row_layout.addWidget(var_name_edit)
        row_layout.addWidget(path_edit)
        row_layout.addWidget(add_button)
        row_layout.addWidget(delete_button)
        
        # 确定插入位置
        if insert_after_row is None:
            # 默认插入到开头（从上往下添加）
            self.variable_scroll_layout.insertWidget(0, row_widget)
            self.variable_rows.insert(0, row_data)
        else:
            # 在当前行下方插入新行
            insert_index = self.variable_rows.index(insert_after_row) + 1
            self.variable_scroll_layout.insertWidget(insert_index, row_widget)
            self.variable_rows.insert(insert_index, row_data)
    
    def remove_variable_row(self, row_data):
        """删除一行变量提取配置"""
        if len(self.variable_rows) <= 1:
            # 至少保留一行
            return
            
        # 从布局中移除
        self.variable_scroll_layout.removeWidget(row_data['widget'])
        row_data['widget'].deleteLater()
        
        # 从列表中移除
        self.variable_rows.remove(row_data)
    
    def get_icon(self, icon_name):
        """获取图标，支持PyInstaller打包路径处理"""
        try:
            # 尝试从开发环境路径加载
            dev_path = os.path.join("src", "resources", "icons", icon_name)
            if os.path.exists(dev_path):
                return QIcon(dev_path)
            
            # 尝试从exe打包后路径加载
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            exe_path = os.path.join(exe_dir, "src", "resources", "icons", icon_name)
            if os.path.exists(exe_path):
                return QIcon(exe_path)
            
            # 尝试相对路径
            relative_path = os.path.join("src", "resources", "icons", icon_name)
            if os.path.exists(relative_path):
                return QIcon(relative_path)
            
            # 尝试sys._MEIPASS临时解压路径（PyInstaller打包时）
            if getattr(sys, 'frozen', False):
                meipass_path = os.path.join(sys._MEIPASS, "src", "resources", "icons", icon_name)
                if os.path.exists(meipass_path):
                    return QIcon(meipass_path)
            
            # 如果所有路径都失败，返回空图标
            print(f"图标加载失败: {icon_name}")
            return QIcon()
            
        except Exception as e:
            print(f"图标加载异常 {icon_name}: {e}")
            return QIcon()
    
    def create_body_tab(self):
        """创建请求体Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)  # 减小边距
        layout.setSpacing(5)  # 减小间距
        
        # 请求体编辑框 - 去除标题，直接显示编辑框
        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText("请输入JSON格式的请求体内容")
        self.body_edit.setMinimumHeight(200)
        
        layout.addWidget(self.body_edit)
        
        return tab
    
    def create_headers_tab(self):
        """创建请求头Tab - 完全参考断言弹窗样式"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 创建滚动区域 - 完全参考断言弹窗实现
        self.headers_scroll_area = QScrollArea()
        self.headers_scroll_area.setWidgetResizable(True)
        self.headers_scroll_area.setMinimumHeight(250)  # 最小高度
        self.headers_scroll_area.setFrameShape(QFrame.NoFrame)  # 移除边框
        self.headers_scroll_area.setStyleSheet("QScrollArea { border: none; }")  # 确保无边框
        
        # 滚动区域内容
        scroll_content = QWidget()
        self.headers_scroll_layout = QVBoxLayout(scroll_content)
        self.headers_scroll_layout.setSpacing(8)
        self.headers_scroll_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        self.headers_scroll_area.setWidget(scroll_content)
        layout.addWidget(self.headers_scroll_area)
        
        # 初始化时不添加默认行，保持空白
        self.header_rows = []
        
        # 确保第一行从顶部开始显示，不居中
        self.headers_scroll_layout.addStretch()
        
        return tab
    
    def add_header_row(self, insert_after_row=None):
        """添加一行请求头配置 - 参考断言弹窗样式"""
        row_widget = QWidget()
        row_widget.setObjectName("header-row")
        row_widget.setStyleSheet("""
            QWidget#header-row {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px;
                margin: 4px 0;
                background-color: #fafafa;
            }
            QWidget#header-row:hover {
                background-color: #f0f0f0;
            }
        """)
        
        row_layout = QHBoxLayout(row_widget)
        row_layout.setSpacing(10)
        
        # Header名称输入框
        header_name_edit = QLineEdit()
        header_name_edit.setPlaceholderText("Header名称")
        header_name_edit.setMinimumWidth(120)
        
        # Header值输入框
        header_value_edit = QLineEdit()
        header_value_edit.setPlaceholderText("Header值")
        header_value_edit.setMinimumWidth(250)
        
        # 添加按钮 - 使用图标
        add_button = QPushButton()
        add_button.setFixedSize(22, 22)
        add_button.setIcon(self.get_icon("add.png"))
        add_button.setIconSize(QSize(14, 14))
        add_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #e8f5e8;
                border-radius: 3px;
            }
        """)
        
        # 删除按钮 - 使用图标
        delete_button = QPushButton()
        delete_button.setFixedSize(22, 22)
        delete_button.setIcon(self.get_icon("sub.png"))
        delete_button.setIconSize(QSize(14, 14))
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #ffebee;
                border-radius: 3px;
            }
        """)
        
        # 存储行信息
        row_data = {
            'widget': row_widget,
            'header_name_edit': header_name_edit,
            'header_value_edit': header_value_edit,
            'add_button': add_button,
            'delete_button': delete_button
        }
        
        # 连接按钮事件
        add_button.clicked.connect(lambda checked, row=row_data: self.add_header_row(row))
        delete_button.clicked.connect(lambda: self.remove_header_row(row_data))
        
        # 添加到布局
        row_layout.addWidget(header_name_edit)
        row_layout.addWidget(header_value_edit)
        row_layout.addWidget(add_button)
        row_layout.addWidget(delete_button)
        
        # 确定插入位置
        if insert_after_row is None:
            # 默认插入到开头（从上往下添加）
            self.headers_scroll_layout.insertWidget(0, row_widget)
            self.header_rows.insert(0, row_data)
        else:
            # 在当前行下方插入新行
            insert_index = self.header_rows.index(insert_after_row) + 1
            self.headers_scroll_layout.insertWidget(insert_index, row_widget)
            self.header_rows.insert(insert_index, row_data)
    
    def remove_header_row(self, row_data):
        """删除一行请求头配置"""
        if len(self.header_rows) <= 1:
            # 至少保留一行
            return
            
        # 从布局中移除
        self.headers_scroll_layout.removeWidget(row_data['widget'])
        row_data['widget'].deleteLater()
        self.header_rows.remove(row_data)
    
    def show_help(self):
        """显示表达式示例帮助"""
        help_text = """JSONPath表达式示例：

• $.data.user.name - 获取data对象下user对象的name属性
• $.data.users[0].name - 获取data对象下users数组第一个元素的name属性
• $.data.users[*].name - 获取data对象下users数组中所有元素的name属性
• $.data.users[?(@.age > 18)].name - 获取data对象下users数组中年龄大于18的元素的name属性

常用表达式：
• $.code - 获取响应状态码
• $.message - 获取响应消息
• $.data - 获取响应数据对象
• $.data.id - 获取数据中的ID字段

注意：表达式必须以$开头，使用点号.访问对象属性，使用方括号[]访问数组元素。"""
        
        QMessageBox.information(self, "JSONPath表达式帮助", help_text)
    
    def add_table_row(self, table, key="", value=""):
        """为表格添加一行"""
        row = table.rowCount()
        table.insertRow(row)
        
        key_item = QTableWidgetItem(key)
        value_item = QTableWidgetItem(value)
        
        table.setItem(row, 0, key_item)
        table.setItem(row, 1, value_item)
    
    def load_request_data(self):
        """加载请求数据"""
        if not self.request_data:
            return
            
        # 基本信息
        self.name_edit.setText(self.request_data.get('name', 'HTTP请求'))
        self.method_combo.setCurrentText(self.request_data.get('method', 'GET'))
        self.url_edit.setText(self.request_data.get('url', ''))
        self.timeout_spin.setValue(self.request_data.get('timeout', 30))
        
        # 请求头
        headers = self.request_data.get('headers', {})
        # 清除现有行
        for row_data in self.header_rows:
            self.headers_scroll_layout.removeWidget(row_data['widget'])
            row_data['widget'].deleteLater()
        self.header_rows.clear()
        
        # 加载请求头数据
        if headers:
            # 先添加默认的Content-Type行在第一行
            self.add_header_row()
            self.header_rows[0]['header_name_edit'].setText("Content-Type")
            self.header_rows[0]['header_value_edit'].setText("application/json")
            
            # 然后按顺序添加其他headers数据
            last_row = self.header_rows[0]
            for key, value in headers.items():
                # 跳过Content-Type，因为已经添加了
                if key.lower() == "content-type":
                    continue
                self.add_header_row(last_row)
                last_row = self.header_rows[-1]  # 获取最新添加的行
                last_row['header_name_edit'].setText(key)
                last_row['header_value_edit'].setText(str(value))
        else:
            # 至少保留一行
            self.add_header_row()
            # 设置默认Content-Type
            self.header_rows[0]['header_name_edit'].setText("Content-Type")
            self.header_rows[0]['header_value_edit'].setText("application/json")
        
        # 请求体
        body = self.request_data.get('body', {})
        if isinstance(body, dict):
            self.body_edit.setText(json.dumps(body, indent=2, ensure_ascii=False))
        else:
            self.body_edit.setText(str(body))
        
        # 变量
        variables = self.request_data.get('variables', {})
        # 清除现有行
        for row_data in self.variable_rows:
            self.variable_scroll_layout.removeWidget(row_data['widget'])
            row_data['widget'].deleteLater()
        self.variable_rows.clear()
        
        # 加载变量数据
        if variables:
            # 按顺序添加行并设置数据
            last_row = None
            for var_name, json_path in variables.items():
                self.add_variable_row(last_row)
                last_row = self.variable_rows[-1]  # 获取最新添加的行
                last_row['var_name_edit'].setText(var_name)
                last_row['path_edit'].setText(json_path)
        else:
            # 至少保留一行
            self.add_variable_row()
    
    def get_headers_from_rows(self):
        """从请求头行获取请求头配置"""
        headers = {}
        for row_data in self.header_rows:
            header_name = row_data['header_name_edit'].text().strip()
            header_value = row_data['header_value_edit'].text().strip()
            if header_name and header_value:
                headers[header_name] = header_value
        return headers
    
    def get_variables_from_rows(self):
        """从变量提取行获取变量配置"""
        variables = {}
        for row_data in self.variable_rows:
            var_name = row_data['var_name_edit'].text().strip()
            json_path = row_data['path_edit'].text().strip()
            if var_name and json_path:
                variables[var_name] = json_path
        return variables
    
    def on_test_request(self):
        """测试HTTP请求"""
        try:
            # 获取请求配置
            method = self.method_combo.currentText()
            url = self.url_edit.text().strip()
            timeout = self.timeout_spin.value()
            headers = self.get_headers_from_rows()
            
            if not url:
                QMessageBox.warning(self, "警告", "请输入请求URL")
                return
            
            # 获取请求体
            body_text = self.body_edit.toPlainText().strip()
            body = {}
            if body_text:
                try:
                    body = json.loads(body_text)
                except json.JSONDecodeError:
                    QMessageBox.warning(self, "警告", "请求体不是有效的JSON格式")
                    return
            
            # 执行测试请求
            session = requests.Session()
            
            if method == 'GET':
                response = session.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = session.post(url, json=body, headers=headers, timeout=timeout)
            elif method == 'PUT':
                response = session.put(url, json=body, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = session.delete(url, headers=headers, timeout=timeout)
            else:
                response = session.get(url, headers=headers, timeout=timeout)
            
            # 变量提取处理
            variables_config = self.get_variables_from_rows()
            extracted_variables = {}
            
            if variables_config:
                try:
                    # 尝试解析响应体为JSON
                    response_data = response.json()
                except:
                    response_data = response.text
                
                # 提取变量
                for var_name, json_path in variables_config.items():
                    try:
                        # 简单的JSON路径提取（支持点分隔的路径）
                        if isinstance(response_data, dict):
                            value = response_data
                            for key in json_path.split('.'):
                                if isinstance(value, dict) and key in value:
                                    value = value[key]
                                else:
                                    value = None
                                    break
                            
                            if value is not None:
                                extracted_variables[var_name] = value
                            else:
                                extracted_variables[var_name] = "未找到路径"
                        else:
                            extracted_variables[var_name] = "响应体不是JSON格式"
                    except Exception as e:
                        extracted_variables[var_name] = f"提取失败: {str(e)}"
            
            # 构建测试结果文本
            result_text = f"""测试结果：
状态码: {response.status_code}
响应时间: {response.elapsed.total_seconds():.2f}秒
响应头:
{json.dumps(dict(response.headers), indent=2, ensure_ascii=False)}

响应体:
{response.text}
"""
            
            # 添加变量提取情况
            if extracted_variables:
                result_text += f"""

变量提取情况:
{json.dumps(extracted_variables, indent=2, ensure_ascii=False)}
"""
            else:
                result_text += """

变量提取情况: 未配置变量提取或未提取到变量
"""
            
            # 显示结果对话框
            result_dialog = QDialog(self)
            result_dialog.setWindowTitle("HTTP请求测试结果")
            result_dialog.setMinimumSize(700, 600)
            
            layout = QVBoxLayout(result_dialog)
            
            result_edit = QTextEdit()
            result_edit.setReadOnly(True)
            result_edit.setText(result_text)
            
            ok_btn = QPushButton("确定")
            ok_btn.clicked.connect(result_dialog.accept)
            
            layout.addWidget(result_edit)
            layout.addWidget(ok_btn)
            
            result_dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"请求测试失败: {str(e)}")
    
    def _get_current_data(self):
        """获取当前对话框的数据状态"""
        try:
            # 获取请求配置
            name = self.name_edit.text().strip() if hasattr(self, 'name_edit') else ''
            method = self.method_combo.currentText() if hasattr(self, 'method_combo') else 'GET'
            url = self.url_edit.text().strip() if hasattr(self, 'url_edit') else ''
            timeout = self.timeout_spin.value() if hasattr(self, 'timeout_spin') else 30
            
            # 获取请求头和变量配置
            headers = self.get_headers_from_rows() if hasattr(self, 'get_headers_from_rows') else {}
            variables = self.get_variables_from_rows() if hasattr(self, 'get_variables_from_rows') else {}
            
            # 获取请求体
            body_text = self.body_edit.toPlainText().strip() if hasattr(self, 'body_edit') else ''
            body = {}
            if body_text:
                try:
                    body = json.loads(body_text)
                except json.JSONDecodeError:
                    body = body_text
            
            return {
                'type': 'http_request',
                'name': name,
                'method': method,
                'url': url,
                'timeout': timeout,
                'headers': headers,
                'body': body,
                'variables': variables
            }
        except Exception:
            return {}
    
    def _has_unsaved_changes(self):
        """检查是否有未保存的修改"""
        current_data = self._get_current_data()
        return current_data != self.original_data
    
    def closeEvent(self, event):
        """处理对话框关闭事件"""
        if self._has_unsaved_changes():
            # 创建确认对话框，手动设置按钮文本
            msg_box = QMessageBox(QMessageBox.Question, "未保存的修改",
                                 "您有未保存的修改，是否保存？")
            
            # 添加保存、放弃和取消按钮
            save_btn = msg_box.addButton("保存", QMessageBox.YesRole)
            discard_btn = msg_box.addButton("放弃", QMessageBox.NoRole)
            cancel_btn = msg_box.addButton("取消", QMessageBox.RejectRole)
            msg_box.setDefaultButton(save_btn)
            
            msg_box.exec_()
            
            clicked_btn = msg_box.clickedButton()
            if clicked_btn == save_btn:
                # 保存修改
                self.on_save()
                event.accept()
            elif clicked_btn == discard_btn:
                # 放弃修改
                event.accept()
            else:
                # 取消关闭
                event.ignore()
                return
        else:
            event.accept()
    
    def on_save(self):
        """保存请求配置"""
        try:
            # 验证必填字段
            name = self.name_edit.text().strip()
            method = self.method_combo.currentText()
            url = self.url_edit.text().strip()
            
            if not name:
                QMessageBox.warning(self, "警告", "请输入HTTP请求名称")
                return
                
            if not url:
                QMessageBox.warning(self, "警告", "请输入请求URL")
                return
            
            # 获取请求配置
            timeout = self.timeout_spin.value()
            headers = self.get_headers_from_rows()
            
            # 获取请求体
            body_text = self.body_edit.toPlainText().strip()
            body = {}
            if body_text:
                try:
                    body = json.loads(body_text)
                except json.JSONDecodeError:
                    QMessageBox.warning(self, "警告", "请求体不是有效的JSON格式")
                    return
            
            # 获取变量配置
            variables = self.get_variables_from_rows()
            
            # 构建请求配置
            request_config = {
                'type': 'http_request',
                'name': name,
                'method': method,
                'url': url,
                'timeout': timeout,
                'headers': headers,
                'body': body,
                'variables': variables
            }
            
            # 发出保存信号
            self.request_saved.emit(request_config)
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")