import re
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFormLayout,
    QTextEdit,
    QComboBox,
    QMessageBox,
)
from PyQt5.QtCore import pyqtSignal
from src.ui.widgets.toast_tips import Toast
from src.utils.sql_worker import SQLWorker
from src.utils.css_utils import get_combobox_style


class SQLToolDialog(QDialog):
    """SQL工具配置对话框"""

    # 定义保存信号
    sql_tool_saved = pyqtSignal(dict)

    def __init__(self, parent=None, sql_config=None):
        super().__init__(parent)
        self.sql_config = sql_config or {}
        self.setWindowTitle("SQL工具配置")
        self.setModal(True)
        self.setFixedSize(600, 500)

        # 设置对话框样式，避免黑色背景
        self.setStyleSheet(
            """
            QDialog {
                background-color: white;
            }
            QLabel {
                color: black;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: white;
                color: black;
                border: 1px solid #ccc;
                padding: 4px;
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
        """
        )

        # 写死的数据库连接信息
        self.connection_params = {
            "host": "47.106.192.83",
            "port": 3306,
            "user": "xvdba",
            "password": "xvdba@2022",
            "database": "",
            "charset": "utf8mb4",
        }

        self.init_ui()
        self.load_existing_config()

        # 自动连接数据库
        self.auto_connect_database()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)  # 增加整体间距，让字段之间有合适间距
        layout.setContentsMargins(12, 12, 12, 12)

        # 名称配置
        name_layout = QHBoxLayout()
        name_layout.setSpacing(10)  # 设置标签和输入框之间的间距
        name_layout.addWidget(QLabel("名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入工具名称")
        self.name_edit.setText("sql工具")  # 默认名称
        self.name_edit.setFixedWidth(200)  # 设置固定宽度，避免过长
        self.name_edit.setStyleSheet(
            """
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 6px;  /* 添加圆角 */
                padding: 6px 8px;
                background-color: white;
                color: black;
                font-family: 'Microsoft YaHei', sans-serif;
            }
            QLineEdit:focus {
                border-color: #0078d4;
                outline: none;
            }
        """
        )
        name_layout.addWidget(self.name_edit)
        name_layout.addStretch()  # 添加拉伸，使输入框左对齐
        layout.addLayout(name_layout)

        # 库名配置和连接状态（合并到一行）
        db_conn_layout = QHBoxLayout()

        # 库名标题和下拉框（左对齐）
        db_left_layout = QHBoxLayout()
        db_left_layout.addWidget(QLabel("库名:"))
        self.db_combo = QComboBox()
        # 添加一些常见的数据库名称
        self.db_combo.addItem("performance_schema")
        self.db_combo.setEditable(False)  # 不允许编辑，设置为只读下拉框
        self.db_combo.setEnabled(True)  # 启用选择功能
        self.db_combo.currentTextChanged.connect(
            self.on_database_changed
        )  # 监听数据库选择变化
        self.db_combo.setStyleSheet(get_combobox_style())
        db_left_layout.addWidget(self.db_combo)

        # 连接状态
        self.conn_status_label = QLabel("未连接")
        self.conn_status_label.setStyleSheet(
            "color: gray; font-size: 12px; margin-left: 10px;"
        )

        db_conn_layout.addLayout(db_left_layout)
        db_conn_layout.addWidget(self.conn_status_label)
        db_conn_layout.addStretch()
        layout.addLayout(db_conn_layout)

        # SQL语句配置（紧挨着库名字段下方）
        sql_layout = QVBoxLayout()
        sql_layout.setSpacing(6)  # 增加内部间距
        sql_layout.setContentsMargins(0, 8, 0, 0)  # 增加上边距
        sql_label = QLabel("SQL语句:")
        sql_layout.addWidget(sql_label)
        self.sql_edit = QTextEdit()
        self.sql_edit.setPlaceholderText(
            "请输入SELECT查询语句，支持${变量名}格式引用变量"
        )
        self.sql_edit.setFixedHeight(150)  # 增加高度，让输入框更美观
        self.sql_edit.setStyleSheet(
            """
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 6px;  /* 添加圆角 */
                padding: 8px;
                background-color: white;
                color: black;
                font-family: 'Microsoft YaHei', sans-serif;
            }
            QTextEdit:focus {
                border-color: #0078d4;
                outline: none;
            }
        """
        )
        sql_layout.addWidget(self.sql_edit)
        layout.addLayout(sql_layout)

        # SQL校验按钮
        validate_layout = QHBoxLayout()
        validate_layout.setContentsMargins(0, 5, 0, 0)  # 增加上边距
        self.validate_btn = QPushButton("SQL校验")
        self.validate_btn.clicked.connect(self.validate_sql)
        self.validate_btn.setFixedWidth(100)
        validate_layout.addWidget(self.validate_btn)
        validate_layout.addStretch()
        layout.addLayout(validate_layout)

        # 输出字段配置（紧挨着SQL语句下方）
        output_layout = QVBoxLayout()
        output_layout.setSpacing(6)  # 增加内部间距
        output_layout.setContentsMargins(0, 5, 0, 0)  # 增加上边距
        output_label = QLabel("输出字段:")
        output_layout.addWidget(output_label)
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("多个字段以英文逗号分隔，例如：id,name,age")
        self.output_edit.setStyleSheet(
            """
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 6px;  /* 添加圆角 */
                padding: 6px 8px;
                background-color: white;
                color: black;
                font-family: 'Microsoft YaHei', sans-serif;
            }
            QLineEdit:focus {
                border-color: #0078d4;
                outline: none;
            }
        """
        )
        output_layout.addWidget(self.output_edit)
        layout.addLayout(output_layout)

        # 添加拉伸，让内容居上展示，避免被拉伸撑满弹窗
        layout.addStretch()

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

    def auto_connect_database(self):
        """自动连接数据库并获取数据库列表"""
        try:
            # 使用写死的连接信息进行测试连接
            test_sql = "SELECT 1 as test_result"

            self.test_worker = SQLWorker(
                "auto_connect", self.connection_params, test_sql
            )
            self.test_worker.finished.connect(self.on_auto_connect_success)
            self.test_worker.error.connect(self.on_auto_connect_error)
            self.test_worker.start()

            self.conn_status_label.setText("连接中...")
            self.conn_status_label.setStyleSheet("color: orange;")

        except Exception as e:
            self.conn_status_label.setText(f"连接失败 - {str(e)}")
            self.conn_status_label.setStyleSheet("color: red;")

    def on_auto_connect_success(self, query_name, message, result_data):
        """自动连接成功"""
        self.conn_status_label.setText("已连接")
        self.conn_status_label.setStyleSheet("color: green;")
        print("数据库自动连接成功")

        # 连接成功后查询数据库列表
        self.load_database_list()

    def on_auto_connect_error(self, query_name, error_message):
        """自动连接失败"""
        error_msg = (
            error_message.split(":")[0] if ":" in error_message else error_message
        )
        self.conn_status_label.setText(f"连接失败 - {error_msg}")
        self.conn_status_label.setStyleSheet("color: red;")
        print(f"数据库自动连接失败: {error_message}")

    def load_database_list(self):
        """查询数据库列表并填充到下拉框"""
        try:
            # 查询所有数据库的SQL语句
            db_list_sql = "SHOW DATABASES"

            # 创建新的SQLWorker来查询数据库列表
            self.db_list_worker = SQLWorker(
                "get_databases", self.connection_params, db_list_sql
            )
            self.db_list_worker.finished.connect(self.on_database_list_loaded)
            self.db_list_worker.error.connect(self.on_database_list_error)
            self.db_list_worker.start()

            print("正在查询数据库列表...")

        except Exception as e:
            print(f"查询数据库列表失败: {str(e)}")
            # 如果查询失败，使用默认的数据库列表
            self.set_default_databases()

    def on_database_list_loaded(self, query_name, message, result_data):
        """数据库列表加载成功"""
        try:
            # 清空当前下拉框
            self.db_combo.clear()

            # 添加数据库列表到下拉框
            if result_data and len(result_data) > 0:
                databases = []
                for row in result_data:
                    # 处理字典格式的结果（包含'Database'键）
                    if isinstance(row, dict) and "Database" in row:
                        db_name = row["Database"]
                    # 处理列表格式的结果
                    elif isinstance(row, (list, tuple)) and len(row) > 0:
                        db_name = row[0]
                    else:
                        continue

                    # 过滤掉系统数据库（可选）
                    if db_name not in [
                        "information_schema",
                        "performance_schema",
                        "mysql",
                        "sys",
                    ]:
                        databases.append(db_name)

                # 按字母顺序排序
                databases.sort()

                # 添加到下拉框
                for db_name in databases:
                    self.db_combo.addItem(db_name)

                print(f"成功加载 {len(databases)} 个数据库")

                # 如果有现有配置，尝试设置选中的数据库
                if self.sql_config and "database" in self.sql_config:
                    config_db = self.sql_config["database"]
                    # 如果config_db是字典类型，尝试从中提取数据库名
                    if isinstance(config_db, dict) and "database" in config_db:
                        config_db = config_db["database"]
                    elif isinstance(config_db, dict):
                        # 如果字典中没有database键，使用第一个值
                        config_db = next(iter(config_db.values())) if config_db else ""

                    # 确保config_db是字符串类型
                    if isinstance(config_db, str):
                        index = self.db_combo.findText(config_db)
                        if index >= 0:
                            self.db_combo.setCurrentIndex(index)

                # 如果没有选中项，选择第一个数据库
                if self.db_combo.currentIndex() == -1 and self.db_combo.count() > 0:
                    self.db_combo.setCurrentIndex(0)

                # 更新连接参数中的数据库名
                selected_db = self.db_combo.currentText().strip()
                if selected_db:
                    self.connection_params["database"] = selected_db
                    print(f"已更新连接参数中的数据库为: {selected_db}")

            else:
                # 如果没有查询到数据库，使用默认列表
                self.set_default_databases()

        except Exception as e:
            print(f"处理数据库列表失败: {str(e)}")
            self.set_default_databases()

    def on_database_list_error(self, query_name, error_message):
        """数据库列表查询失败"""
        print(f"查询数据库列表失败: {error_message}")
        # 查询失败时使用默认数据库列表
        self.set_default_databases()

    def set_default_databases(self):
        """设置默认数据库列表"""
        self.db_combo.clear()
        default_databases = [
            "test_db",
            "mysql",
            "information_schema",
            "performance_schema",
        ]
        for db_name in default_databases:
            self.db_combo.addItem(db_name)
        print("使用默认数据库列表")

        # 更新连接参数中的数据库名
        selected_db = self.db_combo.currentText().strip()
        if selected_db:
            self.connection_params["database"] = selected_db
            print(f"已更新连接参数中的数据库为: {selected_db}")

    def on_database_changed(self, db_name):
        """数据库选择变化事件"""
        if db_name and db_name.strip():
            self.connection_params["database"] = db_name.strip()
            print(f"数据库选择已更新为: {db_name.strip()}")

    def load_existing_config(self):
        """加载现有配置"""
        if self.sql_config:
            # 名称配置
            self.name_edit.setText(self.sql_config.get("name", "sql工具"))

            # SQL配置
            self.sql_edit.setPlainText(self.sql_config.get("sql", ""))

            # 输出字段
            output_fields = self.sql_config.get("output_fields", [])
            if output_fields:
                output_str = ",".join(
                    [field.get("field", "") for field in output_fields]
                )
                self.output_edit.setText(output_str)

            # 数据库配置 - 这里不直接设置下拉框，因为数据库列表会在连接成功后自动加载
            # 数据库选择会在on_database_list_loaded方法中处理

    def validate_sql(self):
        """校验SQL语句"""
        # 确保焦点不会意外转移到输出字段
        self.validate_btn.setFocus()

        # 清除输出字段输入框的选中状态
        self.output_edit.deselect()

        sql = self.sql_edit.toPlainText().strip()

        if not sql:
            Toast.warning(self, "警告", "请输入SQL语句")
            return

        # 检查是否是SELECT语句
        if not re.match(r"^\s*SELECT\s", sql, re.IGNORECASE):
            Toast.warning(self, "警告", "仅支持SELECT查询语句")
            return

        # 检查是否有危险的SQL操作
        dangerous_keywords = [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "ALTER",
            "CREATE",
            "TRUNCATE",
        ]
        for keyword in dangerous_keywords:
            if re.search(r"\b" + keyword + r"\b", sql, re.IGNORECASE):
                Toast.warning(self, "警告", f"检测到不允许的SQL操作: {keyword}")
                return

        # 测试SQL执行
        try:
            self.test_worker = SQLWorker("validate_sql", self.connection_params, sql)
            self.test_worker.finished.connect(self.on_validate_success)
            self.test_worker.error.connect(self.on_validate_error)
            self.test_worker.start()

            self.validate_btn.setEnabled(False)
            self.validate_btn.setText("校验中...")

        except Exception as e:
            Toast.critical(self, "错误", f"SQL校验失败: {str(e)}")

    def on_validate_success(self, query_name, message, result_data):
        """SQL校验成功"""
        self.validate_btn.setEnabled(True)
        self.validate_btn.setText("SQL校验")
        Toast.information(
            self, "成功", f"SQL语句校验通过，返回 {len(result_data)} 行数据"
        )

    def on_validate_error(self, query_name, error_message):
        """SQL校验失败"""
        self.validate_btn.setEnabled(True)
        self.validate_btn.setText("SQL校验")
        error_msg = (
            error_message.split(":")[0] if ":" in error_message else error_message
        )
        Toast.critical(self, "错误", f"SQL校验失败: {error_msg}")

    def save_config(self):
        """保存配置"""
        # 验证名称
        name = self.name_edit.text().strip()
        if not name:
            Toast.warning(self, "警告", "请输入工具名称")
            return

        # 验证SQL语句
        sql = self.sql_edit.toPlainText().strip()
        if not sql:
            Toast.warning(self, "警告", "请输入SQL语句")
            return

        if not re.match(r"^\s*SELECT\s", sql, re.IGNORECASE):
            Toast.warning(self, "警告", "仅支持SELECT查询语句")
            return

        # 验证输出字段
        output_str = self.output_edit.text().strip()
        if not output_str:
            Toast.warning(self, "警告", "请输入输出字段")
            return

        # 解析输出字段
        output_fields = []
        for field in output_str.split(","):
            field_name = field.strip()
            if field_name:
                output_fields.append({"field": field_name, "description": field_name})

        if not output_fields:
            Toast.warning(self, "警告", "请至少输入一个有效的输出字段")
            return

        # 获取选中的数据库名
        selected_db = self.db_combo.currentText().strip()
        if not selected_db:
            Toast.warning(self, "警告", "请选择数据库")
            return

        # 构建连接参数，包含选中的数据库
        connection_params = self.connection_params.copy()
        connection_params["database"] = selected_db

        # 构建配置
        config_data = {
            "name": name,
            "database": connection_params,
            "sql": sql,
            "output_fields": output_fields,
        }

        # 断开所有数据库连接
        self.disconnect_all_workers()

        # 发送保存信号
        self.sql_tool_saved.emit(config_data)
        self.accept()

    def disconnect_all_workers(self):
        """断开所有数据库工作线程的连接"""
        try:
            # 终止可能正在运行的worker线程
            if hasattr(self, "test_worker") and self.test_worker.isRunning():
                self.test_worker.terminate()
                self.test_worker.wait()
                print("已终止自动连接测试worker")

            if hasattr(self, "db_list_worker") and self.db_list_worker.isRunning():
                self.db_list_worker.terminate()
                self.db_list_worker.wait()
                print("已终止数据库列表查询worker")

            if hasattr(self, "validate_worker") and self.validate_worker.isRunning():
                self.validate_worker.terminate()
                self.validate_worker.wait()
                print("已终止SQL校验worker")

            print("所有数据库连接已断开")
            self.conn_status_label.setText("已断开")
            self.conn_status_label.setStyleSheet("color: gray;")

        except Exception as e:
            print(f"断开连接时发生错误: {str(e)}")

    def reject(self):
        """取消按钮点击事件 - 断开连接并关闭对话框"""
        # 断开所有数据库连接
        self.disconnect_all_workers()
        super().reject()

    def closeEvent(self, event):
        """关闭事件 - 断开连接"""
        # 断开所有数据库连接
        self.disconnect_all_workers()
        print("SQL工具弹窗关闭，连接已断开")
        super().closeEvent(event)
