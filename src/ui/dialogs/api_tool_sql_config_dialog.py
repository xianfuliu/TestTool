import re
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QGroupBox, QFormLayout, QTextEdit,
                             QTableWidget, QTableWidgetItem, QScrollArea, QWidget)
from src.ui.widgets.toast_tips import Toast
from src.utils.sql_worker import SQLWorker


class SQLConfigDialog(QDialog):
    """SQL配置对话框"""

    def __init__(self, sql_name="", sql_config=None, parent=None):
        super().__init__(parent)
        self.sql_name = sql_name
        self.sql_config = sql_config or {}
        self.setWindowTitle(f"SQL配置 - {sql_name}" if sql_name else "新增SQL配置")
        self.setModal(True)
        self.setFixedSize(700, 700)

        self.init_ui()
        self.load_existing_config()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(8)
        scroll_layout.setContentsMargins(5, 5, 5, 5)

        # 数据库基础配置
        db_group = QGroupBox("数据库")
        db_group.setContentsMargins(8, 12, 8, 8)
        db_layout = QFormLayout(db_group)
        db_layout.setSpacing(8)
        db_layout.setVerticalSpacing(8)

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("数据库主机地址")
        db_layout.addRow("主机:", self.host_edit)

        self.port_edit = QLineEdit()
        self.port_edit.setPlaceholderText("端口号")
        self.port_edit.setText("3306")
        db_layout.addRow("端口:", self.port_edit)

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("用户名")
        db_layout.addRow("用户名:", self.user_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        db_layout.addRow("密码:", self.password_edit)

        self.database_edit = QLineEdit()
        self.database_edit.setPlaceholderText("数据库名")
        db_layout.addRow("数据库:", self.database_edit)

        # 测试连接按钮
        test_btn_layout = QHBoxLayout()
        self.test_conn_btn = QPushButton("测试")
        self.test_conn_btn.clicked.connect(self.test_connection)
        self.test_conn_btn.setFixedWidth(100)
        test_btn_layout.addWidget(self.test_conn_btn)
        test_btn_layout.addStretch()
        db_layout.addRow("", test_btn_layout)

        scroll_layout.addWidget(db_group)

        # SQL配置
        sql_group = QGroupBox("SQL配置")
        sql_group.setContentsMargins(8, 12, 8, 8)
        sql_layout = QVBoxLayout(sql_group)
        sql_layout.setSpacing(8)

        self.sql_edit = QTextEdit()
        self.sql_edit.setPlaceholderText("请输入SELECT查询语句，支持使用{变量名}格式引用变量")
        self.sql_edit.setFixedHeight(120)
        sql_layout.addWidget(QLabel("SQL语句:"))
        sql_layout.addWidget(self.sql_edit)

        # SQL校验按钮
        sql_btn_layout = QHBoxLayout()
        self.validate_sql_btn = QPushButton("校验")
        self.validate_sql_btn.clicked.connect(self.validate_sql)
        self.validate_sql_btn.setFixedWidth(100)
        sql_btn_layout.addWidget(self.validate_sql_btn)
        sql_btn_layout.addStretch()
        sql_layout.addLayout(sql_btn_layout)

        scroll_layout.addWidget(sql_group)

        # 输出字段配置
        output_group = QGroupBox("输出字段")
        output_group.setContentsMargins(8, 12, 8, 8)
        output_layout = QVBoxLayout(output_group)
        output_layout.setSpacing(8)

        self.output_table = QTableWidget()
        self.output_table.setColumnCount(2)
        self.output_table.setHorizontalHeaderLabels(["字段", "描述"])
        self.output_table.horizontalHeader().setStretchLastSection(True)
        self.output_table.setFixedHeight(150)

        # 设置列宽
        self.output_table.setColumnWidth(0, 200)
        self.output_table.setColumnWidth(1, 300)

        output_layout.addWidget(self.output_table)

        # 输出字段操作按钮
        output_btn_layout = QHBoxLayout()
        output_btn_layout.setSpacing(8)

        self.add_output_btn = QPushButton("添加")
        self.add_output_btn.clicked.connect(self.add_output_field)
        self.add_output_btn.setFixedWidth(70)

        self.edit_output_btn = QPushButton("编辑")
        self.edit_output_btn.clicked.connect(self.edit_output_field)
        self.edit_output_btn.setFixedWidth(70)

        self.remove_output_btn = QPushButton("删除")
        self.remove_output_btn.clicked.connect(self.remove_output_field)
        self.remove_output_btn.setFixedWidth(70)

        output_btn_layout.addWidget(self.add_output_btn)
        output_btn_layout.addWidget(self.edit_output_btn)
        output_btn_layout.addWidget(self.remove_output_btn)
        output_btn_layout.addStretch()

        output_layout.addLayout(output_btn_layout)
        scroll_layout.addWidget(output_group)

        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

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

        layout.addLayout(button_layout)

    def load_existing_config(self):
        """加载现有配置"""
        if self.sql_config:
            # 数据库配置
            db_config = self.sql_config.get("database", {})
            self.host_edit.setText(db_config.get("host", ""))
            self.port_edit.setText(str(db_config.get("port", "3306")))
            self.user_edit.setText(db_config.get("user", ""))
            self.password_edit.setText(db_config.get("password", ""))
            self.database_edit.setText(db_config.get("database", ""))

            # SQL配置
            self.sql_edit.setPlainText(self.sql_config.get("sql", ""))

            # 输出字段
            output_fields = self.sql_config.get("output_fields", [])
            for field in output_fields:
                self.add_output_table_row(field.get("field", ""), field.get("description", ""))

    def add_output_table_row(self, field_name="", description=""):
        """添加输出字段表格行"""
        row = self.output_table.rowCount()
        self.output_table.insertRow(row)
        self.output_table.setItem(row, 0, QTableWidgetItem(field_name))
        self.output_table.setItem(row, 1, QTableWidgetItem(description))

    def add_output_field(self):
        """添加输出字段"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加输出字段")
        dialog.setModal(True)
        dialog.setFixedSize(300, 150)
        layout = QFormLayout(dialog)

        field_edit = QLineEdit()
        field_edit.setPlaceholderText("字段名")
        layout.addRow("输出字段:", field_edit)

        desc_edit = QLineEdit()
        desc_edit.setPlaceholderText("字段描述")
        layout.addRow("字段描述:", desc_edit)

        button_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)

        def on_ok():
            field = field_edit.text().strip()
            desc = desc_edit.text().strip()

            if not field:
                Toast.warning(dialog, "警告", "请输入输出字段名")
                return

            self.add_output_table_row(field, desc)
            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)

        dialog.exec_()

    def edit_output_field(self):
        """编辑输出字段"""
        current_row = self.output_table.currentRow()
        if current_row < 0:
            Toast.warning(self, "警告", "请先选择要编辑的输出字段")
            return

        current_field = self.output_table.item(current_row, 0).text()
        current_desc = self.output_table.item(current_row, 1).text()

        dialog = QDialog(self)
        dialog.setWindowTitle("编辑输出字段")
        dialog.setModal(True)
        dialog.setFixedSize(300, 150)
        layout = QFormLayout(dialog)

        field_edit = QLineEdit()
        field_edit.setText(current_field)
        layout.addRow("输出字段:", field_edit)

        desc_edit = QLineEdit()
        desc_edit.setText(current_desc)
        layout.addRow("字段描述:", desc_edit)

        button_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)

        def on_ok():
            field = field_edit.text().strip()
            desc = desc_edit.text().strip()

            if not field:
                Toast.warning(dialog, "警告", "请输入输出字段名")
                return

            self.output_table.setItem(current_row, 0, QTableWidgetItem(field))
            self.output_table.setItem(current_row, 1, QTableWidgetItem(desc))
            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)

        dialog.exec_()

    def remove_output_field(self):
        """删除输出字段"""
        current_row = self.output_table.currentRow()
        if current_row >= 0:
            self.output_table.removeRow(current_row)

    def test_connection(self):
        """测试数据库连接"""
        host = self.host_edit.text().strip()
        port = self.port_edit.text().strip()
        user = self.user_edit.text().strip()
        password = self.password_edit.text()
        database = self.database_edit.text().strip()

        if not all([host, port, user, database]):
            Toast.warning(self, "警告", "请填写完整的数据库连接信息")
            return

        try:
            port_int = int(port)
        except ValueError:
            Toast.warning(self, "警告", "端口号必须是数字")
            return

        # 这里可以添加实际的数据库连接测试
        # 由于SQLWorker需要SQL语句，我们用一个简单的测试查询
        test_sql = "SELECT 1 as test_result"

        connection_params = {
            'host': host,
            'port': port_int,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4'
        }

        # 使用SQLWorker测试连接
        self.test_worker = SQLWorker("test_connection", connection_params, test_sql)
        self.test_worker.finished.connect(self.on_test_success)
        self.test_worker.error.connect(self.on_test_error)
        self.test_worker.start()

        self.test_conn_btn.setEnabled(False)
        self.test_conn_btn.setText("测试中...")

    def on_test_success(self, query_name, message, result_data):
        """测试连接成功"""
        self.test_conn_btn.setEnabled(True)
        self.test_conn_btn.setText("测试连接")
        Toast.information(self, "成功", "数据库连接测试成功")

    def on_test_error(self, query_name, error_message):
        """测试连接失败"""
        self.test_conn_btn.setEnabled(True)
        self.test_conn_btn.setText("测试连接")
        Toast.critical(self, "失败", f"数据库连接测试失败: {error_message.split(':')[0]}")

    def validate_sql(self):
        """校验SQL语句"""
        sql = self.sql_edit.toPlainText().strip()

        if not sql:
            Toast.warning(self, "警告", "请输入SQL语句")
            return

        # 检查是否是SELECT语句
        if not re.match(r'^\s*SELECT\s', sql, re.IGNORECASE):
            Toast.warning(self, "警告", "仅支持SELECT查询语句")
            return

        # 检查是否有危险的SQL操作
        dangerous_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE']
        for keyword in dangerous_keywords:
            if re.search(r'\b' + keyword + r'\b', sql, re.IGNORECASE):
                Toast.warning(self, "警告", f"检测到不允许的SQL操作: {keyword}")
                return

        Toast.information(self, "成功", "SQL语句格式校验通过")

    def save_config(self):
        """保存配置"""
        # 验证数据库配置
        host = self.host_edit.text().strip()
        port = self.port_edit.text().strip()
        user = self.user_edit.text().strip()
        password = self.password_edit.text()
        database = self.database_edit.text().strip()

        if not all([host, port, user, database]):
            Toast.warning(self, "警告", "请填写完整的数据库连接信息")
            return

        try:
            port_int = int(port)
        except ValueError:
            Toast.warning(self, "警告", "端口号必须是数字")
            return

        # 验证SQL语句
        sql = self.sql_edit.toPlainText().strip()
        if not sql:
            Toast.warning(self, "警告", "请输入SQL语句")
            return

        if not re.match(r'^\s*SELECT\s', sql, re.IGNORECASE):
            Toast.warning(self, "警告", "仅支持SELECT查询语句")
            return

        # 收集输出字段
        output_fields = []
        for row in range(self.output_table.rowCount()):
            field_item = self.output_table.item(row, 0)
            desc_item = self.output_table.item(row, 1)

            if field_item and field_item.text().strip():
                output_fields.append({
                    "field": field_item.text().strip(),
                    "description": desc_item.text().strip() if desc_item else ""
                })

        if not output_fields:
            Toast.warning(self, "警告", "请至少配置一个输出字段")
            return

        # 构建配置
        self.sql_config = {
            "database": {
                "host": host,
                "port": port_int,
                "user": user,
                "password": password,
                "database": database
            },
            "sql": sql,
            "output_fields": output_fields
        }

        self.accept()

    def get_config(self):
        """获取配置"""
        return self.sql_config