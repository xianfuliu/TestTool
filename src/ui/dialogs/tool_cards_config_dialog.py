from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QCheckBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QScrollArea,
    QGridLayout,
    QInputDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import json
import pymysql

from src.ui.widgets.no_wheel_combo_box import NoWheelComboBox
from src.ui.widgets.toast_tips import Toast
from src.utils.css_utils import get_combobox_style
from src.utils.db_config import get_db_connection
from src.ui.dialogs.database_config_dialog import DatabaseConfigDialog


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

        # 卡片配置选项卡（移除业务线配置）
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

        # 业务线和子业务管理区域已移除，现在只管理卡片

    def create_cards_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 卡片列表
        cards_group = QGroupBox("卡片列表")
        cards_layout = QVBoxLayout(cards_group)

        cards_list_layout = QHBoxLayout()

        self.cards_list = QListWidget()
        self.cards_list.currentItemChanged.connect(self.on_card_selected)
        cards_list_layout.addWidget(self.cards_list)

        # 卡片操作按钮
        cards_btn_layout = QVBoxLayout()

        # 库表配置按钮
        self.db_config_btn = QPushButton("库表配置")
        self.db_config_btn.clicked.connect(self.show_db_config_dialog)
        cards_btn_layout.addWidget(self.db_config_btn)

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

        # 刷新卡片列表
        self.refresh_cards_list()

        return widget

    def refresh_cards_list(self):
        """刷新卡片列表（基于数据库）"""
        # 清空现有卡片列表
        self.cards_list.clear()

        # 从数据库加载卡片数据
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(pymysql.cursors.DictCursor)

                # 获取当前项目ID（从父窗口传递）
                current_project_id = getattr(self.parent(), "current_project_id", None)

                if current_project_id:
                    # 查询当前项目下的所有卡片
                    query = """
                        SELECT id, title, description, card_type, configuration, 
                               timeout, locked, sort_order, created_by, created_at, updated_at
                        FROM tool_cards 
                        WHERE project_id = %s
                        ORDER BY sort_order, created_at
                    """
                    cursor.execute(query, (current_project_id,))
                    cards = cursor.fetchall()

                    # 将数据库记录转换为卡片数据格式
                    for card in cards:
                        card_data = {
                            "id": card["id"],
                            "title": card["title"],
                            "description": card["description"],
                            "type": card["card_type"],
                            "timeout": card["timeout"],
                            "locked": bool(card["locked"]),
                            "configuration": (
                                json.loads(card["configuration"])
                                if card["configuration"]
                                else {}
                            ),
                        }

                        # 根据卡片类型添加特定配置
                        if card_data["type"].startswith("sql"):
                            config = card_data["configuration"]
                            card_data.update(
                                {
                                    "database": config.get("database", ""),
                                    "sql": config.get("sql", ""),
                                }
                            )
                        elif card_data["type"] == "http":
                            config = card_data["configuration"]
                            card_data.update(
                                {
                                    "url": config.get("url", ""),
                                    "method": config.get("method", ""),
                                    "headers": config.get("headers", ""),
                                    "body": config.get("body", ""),
                                }
                            )
                        elif card_data["type"] == "python":
                            config = card_data["configuration"]
                            card_data.update(
                                {
                                    "class_name": config.get("class_name", ""),
                                    "method_name": config.get("method_name", ""),
                                    "parameters": config.get("parameters", ""),
                                }
                            )

                        item = QListWidgetItem(card_data["title"])
                        item.setData(Qt.UserRole, card_data)
                        self.cards_list.addItem(item)

                cursor.close()
            except pymysql.Error as e:
                print(f"数据库查询失败: {e}")
            finally:
                conn.close()

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

        basic_layout.addRow(
            "卡片名称:", QLabel(self.current_card_data.get("title", ""))
        )
        basic_layout.addRow("卡片类型:", QLabel(self.get_type_display()))
        basic_layout.addRow(
            "描述:", QLabel(self.current_card_data.get("description", ""))
        )
        basic_layout.addRow(
            "超时时间:", QLabel(f"{self.current_card_data.get('timeout', 5000)}ms")
        )
        basic_layout.addRow(
            "锁定状态:",
            QLabel("是" if self.current_card_data.get("locked", False) else "否"),
        )

        scroll_layout.addWidget(basic_info_group)

        # 配置信息
        config_group = QGroupBox("配置信息")
        config_layout = QFormLayout(config_group)

        card_type = self.current_card_data.get("type", "sql")
        if card_type == "sql":
            config_layout.addRow(
                "数据库连接:", QLabel(self.current_card_data.get("database", ""))
            )
            config_layout.addRow(
                "SQL语句:", QLabel(self.current_card_data.get("sql", ""))
            )
        elif card_type == "http":
            config_layout.addRow(
                "请求URL:", QLabel(self.current_card_data.get("url", ""))
            )
            config_layout.addRow(
                "请求方法:", QLabel(self.current_card_data.get("method", "GET"))
            )
        elif card_type == "python":
            config_layout.addRow(
                "Python类:", QLabel(self.current_card_data.get("class_name", ""))
            )
            config_layout.addRow(
                "方法名:", QLabel(self.current_card_data.get("method_name", ""))
            )

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
        self.card_type_combo.addItems(
            ["SQL查询", "SQL更新", "SQL删除", "HTTP接口", "Python类"]
        )
        self.card_type_combo.currentTextChanged.connect(self.on_card_type_changed)
        self.card_type_combo.setStyleSheet(get_combobox_style())
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
        self.database_combo.setStyleSheet(get_combobox_style())
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
        self.method_combo.setStyleSheet(get_combobox_style())
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
        self.parameters_edit.setPlaceholderText(
            '{"param1": "value1", "param2": "value2"}'
        )
        self.config_layout.addRow("参数:", self.parameters_edit)

    def on_card_type_changed(self, type_text):
        """卡片类型变更事件"""
        if self.view_mode:
            return

        type_map = {"SQL工具": "sql", "HTTP接口": "http", "Python类": "python"}

        card_type = type_map.get(type_text, "sql")

        if card_type == "sql":
            self.create_sql_config()
        elif card_type == "http":
            self.create_http_config()
        elif card_type == "python":
            self.create_python_config()

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
        self.card_title_edit.setText(card_data.get("title", ""))

        # 设置卡片类型
        card_type = card_data.get("type", "sql")
        type_map = {"sql": "SQL工具", "http": "HTTP接口", "python": "Python类"}
        type_text = type_map.get(card_type, "SQL工具")
        self.card_type_combo.setCurrentText(type_text)

        self.card_desc_edit.setPlainText(card_data.get("description", ""))
        self.timeout_spin.setValue(card_data.get("timeout", 5000))
        self.locked_check.setChecked(card_data.get("locked", False))

        # 填充类型特定的配置
        if card_type == "sql":
            self.database_combo.setCurrentText(card_data.get("database", ""))
            self.sql_editor.setPlainText(card_data.get("sql", ""))
        elif card_type == "http":
            self.url_edit.setText(card_data.get("url", ""))
            self.method_combo.setCurrentText(card_data.get("method", "GET"))
            self.headers_edit.setPlainText(card_data.get("headers", ""))
            self.body_edit.setPlainText(card_data.get("body", ""))
        elif card_type == "python":
            self.class_name_edit.setText(card_data.get("class_name", ""))
            self.method_name_edit.setText(card_data.get("method_name", ""))
            self.parameters_edit.setPlainText(card_data.get("parameters", ""))

    def get_type_display(self):
        """获取卡片类型显示文本"""
        if not self.current_card_data:
            return ""

        card_type = self.current_card_data.get("type", "sql")
        type_map = {"sql": "SQL工具", "http": "HTTP接口", "python": "Python类"}
        return type_map.get(card_type, card_type)

    def generate_card_id(self):
        """生成唯一的卡片ID"""
        import uuid

        return str(uuid.uuid4())

    def add_card(self):
        """新增卡片"""
        # 确保当前有选中的项目
        current_project_id = getattr(self.parent(), "current_project_id", None)
        if not current_project_id:
            Toast.warn(self, "请先选择项目")
            return

        # 创建新卡片数据
        new_card = {
            "id": self.generate_card_id(),
            "title": "新卡片",
            "type": "sql",
            "description": "",
            "timeout": 5000,
            "locked": False,
            "database": "default_db",
            "sql": "",
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
            Toast.warn(self, "请选择要编辑的卡片")
            return

        self.current_card_data = current_item.data(Qt.UserRole)
        self.create_card_details_form()

    def copy_card(self):
        """复制卡片"""
        current_item = self.cards_list.currentItem()
        if not current_item:
            Toast.warn(self, "请选择要复制的卡片")
            return

        # 确保当前有选中的项目
        current_project_id = getattr(self.parent(), "current_project_id", None)
        if not current_project_id:
            Toast.warn(self, "请先选择项目")
            return

        original_card = current_item.data(Qt.UserRole)

        # 创建副本
        new_card = original_card.copy()
        new_card["id"] = self.generate_card_id()

        # 生成副本名称
        base_name = original_card.get("title", "卡片")
        copy_count = 1
        new_title = f"{base_name}_cp{copy_count}"

        # 检查名称是否已存在
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()

                # 检查相同项目下是否有相同名称的卡片
                query = "SELECT COUNT(*) FROM tool_cards WHERE project_id = %s AND title LIKE %s"
                cursor.execute(query, (current_project_id, f"{base_name}_cp%"))
                count = cursor.fetchone()[0]

                if count > 0:
                    new_title = f"{base_name}_cp{count + 1}"

                cursor.close()
            except mysql.connector.Error as e:
                print(f"数据库查询失败: {e}")
            finally:
                conn.close()

        new_card["title"] = new_title
        new_card["locked"] = False  # 副本默认不锁定

        # 保存到数据库
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()

                # 准备配置数据
                configuration = {}
                if new_card["type"].startswith("sql"):
                    configuration = {
                        "database": new_card.get("database", ""),
                        "sql": new_card.get("sql", ""),
                    }
                elif new_card["type"] == "http":
                    configuration = {
                        "url": new_card.get("url", ""),
                        "method": new_card.get("method", ""),
                        "headers": new_card.get("headers", ""),
                        "body": new_card.get("body", ""),
                    }
                elif new_card["type"] == "python":
                    configuration = {
                        "class_name": new_card.get("class_name", ""),
                        "method_name": new_card.get("method_name", ""),
                        "parameters": new_card.get("parameters", ""),
                    }

                query = """
                    INSERT INTO tool_cards 
                    (id, project_id, title, description, card_type, configuration, timeout, locked, sort_order, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    new_card["id"],
                    current_project_id,
                    new_card["title"],
                    new_card.get("description", ""),
                    new_card["type"],
                    json.dumps(configuration),
                    new_card.get("timeout", 5000),
                    int(new_card.get("locked", False)),
                    new_card.get("sort_order", 0),
                    "admin",
                )
                cursor.execute(query, values)

                conn.commit()
                cursor.close()

                # 刷新卡片列表
                self.refresh_cards_list()

                # 选中新复制的卡片
                for i in range(self.cards_list.count()):
                    item = self.cards_list.item(i)
                    if item.data(Qt.UserRole).get("id") == new_card["id"]:
                        self.cards_list.setCurrentItem(item)
                        break

                Toast.information(self, "卡片复制成功")

            except pymysql.Error as e:
                print(f"数据库插入失败: {e}")
                Toast.warn(self, "卡片复制失败")
            finally:
                conn.close()

    def delete_card(self):
        """删除卡片"""
        current_item = self.cards_list.currentItem()
        if not current_item:
            Toast.warn(self, "请选择要删除的卡片")
            return

        card_data = current_item.data(Qt.UserRole)
        card_title = card_data.get("title", "未命名")

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除卡片 '{card_title}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # 从数据库删除卡片
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()

                    query = "DELETE FROM tool_cards WHERE id = %s"
                    cursor.execute(query, (card_data["id"],))

                    conn.commit()
                    cursor.close()

                    # 刷新卡片列表
                    self.refresh_cards_list()

                    # 清空当前卡片数据
                    self.current_card_data = None
                    self.create_card_details_form()

                    Toast.information(self, "卡片删除成功")

                except pymysql.Error as e:
                    print(f"数据库删除失败: {e}")
                    Toast.warn(self, "卡片删除失败")
                finally:
                    conn.close()

    def save_current_card(self):
        """保存当前卡片"""
        if not self.current_card_data:
            return

        # 验证必填字段
        title = self.card_title_edit.text().strip()
        if not title:
            Toast.warn(self, "请输入卡片名称")
            return

        # 更新卡片数据
        self.current_card_data["title"] = title
        self.current_card_data["description"] = self.card_desc_edit.toPlainText()
        self.current_card_data["timeout"] = self.timeout_spin.value()
        self.current_card_data["locked"] = self.locked_check.isChecked()

        # 获取卡片类型
        type_text = self.card_type_combo.currentText()
        type_map = {"SQL工具": "sql", "HTTP接口": "http", "Python类": "python"}
        self.current_card_data["type"] = type_map.get(type_text, "sql")

        # 保存类型特定的配置
        card_type = self.current_card_data["type"]
        if card_type == "sql":
            self.current_card_data["database"] = self.database_combo.currentText()
            self.current_card_data["sql"] = self.sql_editor.toPlainText()
        elif card_type == "http":
            self.current_card_data["url"] = self.url_edit.text()
            self.current_card_data["method"] = self.method_combo.currentText()
            self.current_card_data["headers"] = self.headers_edit.toPlainText()
            self.current_card_data["body"] = self.body_edit.toPlainText()
        elif card_type == "python":
            self.current_card_data["class_name"] = self.class_name_edit.text()
            self.current_card_data["method_name"] = self.method_name_edit.text()
            self.current_card_data["parameters"] = self.parameters_edit.toPlainText()

        # 获取当前项目ID
        current_project_id = getattr(self.parent(), "current_project_id", None)
        if not current_project_id:
            Toast.warn(self, "无法获取项目信息")
            return

        # 准备配置数据
        configuration = {}
        if self.current_card_data["type"].startswith("sql"):
            configuration = {
                "database": self.current_card_data.get("database", ""),
                "sql": self.current_card_data.get("sql", ""),
            }
        elif self.current_card_data["type"] == "http":
            configuration = {
                "url": self.current_card_data.get("url", ""),
                "method": self.current_card_data.get("method", ""),
                "headers": self.current_card_data.get("headers", ""),
                "body": self.current_card_data.get("body", ""),
            }
        elif self.current_card_data["type"] == "python":
            configuration = {
                "class_name": self.current_card_data.get("class_name", ""),
                "method_name": self.current_card_data.get("method_name", ""),
                "parameters": self.current_card_data.get("parameters", ""),
            }

        # 保存到数据库
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()

                if (
                    "id" not in self.current_card_data
                    or not self.current_card_data["id"]
                ):
                    # 新增卡片
                    self.current_card_data["id"] = self.generate_card_id()

                    query = """
                        INSERT INTO tool_cards 
                        (id, project_id, title, description, card_type, configuration, timeout, locked, sort_order, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    values = (
                        self.current_card_data["id"],
                        current_project_id,
                        self.current_card_data["title"],
                        self.current_card_data.get("description", ""),
                        self.current_card_data["type"],
                        json.dumps(configuration),
                        self.current_card_data.get("timeout", 5000),
                        int(self.current_card_data.get("locked", False)),
                        self.current_card_data.get("sort_order", 0),
                        "admin",
                    )
                    cursor.execute(query, values)
                else:
                    # 更新现有卡片
                    query = """
                        UPDATE tool_cards 
                        SET title = %s, description = %s, card_type = %s, configuration = %s, 
                            timeout = %s, locked = %s, sort_order = %s
                        WHERE id = %s
                    """
                    values = (
                        self.current_card_data["title"],
                        self.current_card_data.get("description", ""),
                        self.current_card_data["type"],
                        json.dumps(configuration),
                        self.current_card_data.get("timeout", 5000),
                        int(self.current_card_data.get("locked", False)),
                        self.current_card_data.get("sort_order", 0),
                        self.current_card_data["id"],
                    )
                    cursor.execute(query, values)

                conn.commit()
                cursor.close()

                # 刷新卡片列表
                self.refresh_cards_list()
                Toast.information(self, "卡片保存成功")

            except pymysql.Error as e:
                print(f"数据库操作失败: {e}")
                Toast.warn(self, "卡片保存失败")
            finally:
                conn.close()

    def show_db_config_dialog(self):
        """显示数据库配置对话框"""
        dialog = DatabaseConfigDialog(self)
        dialog.config_updated.connect(self.on_db_config_updated)
        dialog.exec_()

    def on_db_config_updated(self):
        """数据库配置更新后的回调"""
        # 可以在这里添加刷新逻辑，比如重新加载数据库配置相关的数据
        Toast.information(self, "数据库配置已更新")

    def generate_card_id(self):
        """生成卡片ID"""
        import time

        return f"card_{int(time.time() * 1000)}"

    def get_config_data(self):
        """获取配置数据"""
        return self.config_data


# 需要导入的额外组件
from PyQt5.QtWidgets import QInputDialog
