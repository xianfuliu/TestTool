import json
import requests
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QTextEdit, QComboBox, QPushButton, QGroupBox, QFormLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView, QDialogButtonBox,
                             QMessageBox, QTabWidget, QScrollArea, QWidget, QCheckBox,
                             QSpinBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from src.ui.widgets.toast_tips import Toast


class HttpRequestDialog(QDialog):
    """HTTP请求工具配置对话框"""
    
    request_saved = pyqtSignal(dict)  # 请求配置保存信号
    
    def __init__(self, parent=None, request_data=None):
        super().__init__(parent)
        self.request_data = request_data or {}
        self.is_edit = bool(request_data)
        self.variables = []  # 变量列表
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("编辑HTTP请求" if self.is_edit else "新增HTTP请求")
        self.setMinimumSize(800, 600)
        
        # 设置对话框样式，移除黑色边框
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 6px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
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
                selection-background-color: #e3f2fd;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # 创建Tab页
        tab_widget = QTabWidget()
        
        # 请求配置Tab
        request_tab = self.create_request_tab()
        tab_widget.addTab(request_tab, "请求配置")
        
        # 变量提取Tab
        variables_tab = self.create_variables_tab()
        tab_widget.addTab(variables_tab, "变量提取")
        
        layout.addWidget(tab_widget)
        
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
    
    def create_request_tab(self):
        """创建请求配置Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 请求基本信息组
        basic_group = QGroupBox("请求基本信息")
        basic_layout = QFormLayout(basic_group)
        
        # 名称字段
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入HTTP请求名称")
        basic_layout.addRow("名称:", self.name_edit)
        
        # 请求方式
        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE"])
        basic_layout.addRow("请求方式:", self.method_combo)
        
        # 请求URL
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("请输入完整的URL地址")
        basic_layout.addRow("请求URL:", self.url_edit)
        
        # 超时时间
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 300)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" 秒")
        basic_layout.addRow("超时时间:", self.timeout_spin)
        
        layout.addWidget(basic_group)
        
        # 请求头组
        headers_group = QGroupBox("请求头")
        headers_layout = QVBoxLayout(headers_group)
        
        self.headers_table = QTableWidget()
        self.headers_table.setColumnCount(2)
        self.headers_table.setHorizontalHeaderLabels(["Header名称", "Header值"])
        self.headers_table.horizontalHeader().setStretchLastSection(True)
        
        # 添加默认Content-Type
        self.add_table_row(self.headers_table, "Content-Type", "application/json")
        
        add_header_btn = QPushButton("添加Header")
        add_header_btn.clicked.connect(lambda: self.add_table_row(self.headers_table, "", ""))
        
        headers_layout.addWidget(self.headers_table)
        headers_layout.addWidget(add_header_btn)
        
        layout.addWidget(headers_group)
        
        # 请求体组
        body_group = QGroupBox("请求体")
        body_layout = QVBoxLayout(body_group)
        
        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText("请输入JSON格式的请求体内容")
        self.body_edit.setMaximumHeight(150)
        
        body_layout.addWidget(QLabel("请求体内容:"))
        body_layout.addWidget(self.body_edit)
        
        layout.addWidget(body_group)
        
        layout.addStretch()
        
        return tab
    
    def create_variables_tab(self):
        """创建变量提取Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 变量提取说明
        desc_label = QLabel("配置从响应中提取的变量，格式：变量名=JSONPath表达式")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 变量表格
        self.variables_table = QTableWidget()
        self.variables_table.setColumnCount(2)
        self.variables_table.setHorizontalHeaderLabels(["变量名", "JSONPath表达式"])
        self.variables_table.horizontalHeader().setStretchLastSection(True)
        
        # 添加示例行
        self.add_table_row(self.variables_table, "user_id", "$.data.userId")
        
        add_var_btn = QPushButton("添加变量")
        add_var_btn.clicked.connect(lambda: self.add_table_row(self.variables_table, "", ""))
        
        layout.addWidget(self.variables_table)
        layout.addWidget(add_var_btn)
        
        # JSONPath示例
        examples_group = QGroupBox("JSONPath表达式示例")
        examples_layout = QVBoxLayout(examples_group)
        
        examples_text = QTextEdit()
        examples_text.setReadOnly(True)
        examples_text.setMaximumHeight(120)
        examples_text.setText("""常用JSONPath表达式示例：
• $.data.userId        # 提取data对象下的userId字段
• $..name              # 提取所有name字段
• $.items[0].name      # 提取items数组第一个元素的name字段
• $.items[*].id        # 提取items数组中所有元素的id字段
• $.status             # 提取status字段
• $.data.*             # 提取data对象下的所有字段
        """)
        
        examples_layout.addWidget(examples_text)
        layout.addWidget(examples_group)
        
        layout.addStretch()
        
        return tab
    
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
        self.headers_table.setRowCount(0)
        for key, value in headers.items():
            self.add_table_row(self.headers_table, key, value)
        
        # 请求体
        body = self.request_data.get('body', {})
        if isinstance(body, dict):
            self.body_edit.setText(json.dumps(body, indent=2, ensure_ascii=False))
        else:
            self.body_edit.setText(str(body))
        
        # 变量
        variables = self.request_data.get('variables', {})
        self.variables_table.setRowCount(0)
        for var_name, json_path in variables.items():
            self.add_table_row(self.variables_table, var_name, json_path)
    
    def get_headers_from_table(self):
        """从表格获取请求头"""
        headers = {}
        for row in range(self.headers_table.rowCount()):
            key_item = self.headers_table.item(row, 0)
            value_item = self.headers_table.item(row, 1)
            
            if key_item and value_item:
                key = key_item.text().strip()
                value = value_item.text().strip()
                if key and value:
                    headers[key] = value
        return headers
    
    def get_variables_from_table(self):
        """从表格获取变量配置"""
        variables = {}
        for row in range(self.variables_table.rowCount()):
            var_item = self.variables_table.item(row, 0)
            path_item = self.variables_table.item(row, 1)
            
            if var_item and path_item:
                var_name = var_item.text().strip()
                json_path = path_item.text().strip()
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
            headers = self.get_headers_from_table()
            
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
            
            # 显示测试结果
            result_text = f"""测试结果：
状态码: {response.status_code}
响应时间: {response.elapsed.total_seconds():.2f}秒
响应头:
{json.dumps(dict(response.headers), indent=2, ensure_ascii=False)}

响应体:
{response.text}
"""
            
            # 显示结果对话框
            result_dialog = QDialog(self)
            result_dialog.setWindowTitle("HTTP请求测试结果")
            result_dialog.setMinimumSize(600, 400)
            
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
            headers = self.get_headers_from_table()
            
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
            variables = self.get_variables_from_table()
            
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