from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QMessageBox,
    QScrollArea,
    QCheckBox,
    QComboBox,
)
from PyQt5.QtCore import Qt
import json

from src.ui.widgets.toast_tips import Toast
from src.core.services.tool_cards_service import ToolCardsService
from src.utils.css_utils import get_combobox_style
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelComboBox
from src.utils.field_types import FieldType


class ToolCardsConfigDialog(QDialog):
    def __init__(self, folder_data, parent=None, current_folder_id=None, card_data=None):
        super().__init__(parent)
        self.folder_data = folder_data  # 不再需要深拷贝，数据来自数据库
        self.current_folder_id = current_folder_id
        self.card_data = card_data
        self.is_edit = bool(card_data)
        self.updated_folder_data = None  # 存储更新后的数据
        
        # 初始化服务类
        self.tool_cards_service = ToolCardsService()

        # 设置窗口标题，包含当前文件夹信息
        folder_name = self.get_folder_name()
        base_title = "卡片配置" if self.is_edit else "添加卡片"
        self.setWindowTitle(f"{base_title} - {folder_name}")
        self.setModal(True)
        self.setMinimumWidth(1200)
        self.setMinimumHeight(400)

        self.init_ui()

        if self.is_edit:
            self.load_card_data()
    
    def get_updated_data(self):
        """获取更新后的数据（已弃用，数据直接保存到数据库）"""
        return None

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)



        # 配置表单
        self.config_form = QWidget()
        self.config_form.setStyleSheet(
            """
            QWidget {
                background-color: #f8fafc;
            }
        """
        )
        
        self.form_layout = QFormLayout(self.config_form)
        
        # 类型选择（放在第一个）
        self.type_combo = NoWheelComboBox()
        self.type_combo.addItems(["SQL工具", "HTTP接口", "Python类"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        # 使用紧凑的下拉框样式，适合配置弹窗
        self.type_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 20px 6px 12px;
                background-color: white;
                min-width: 150px;
                max-width: 150px;
                font-size: 14px;
            }
            QComboBox:focus {
                border-color: #0078d4;
                outline: none;
            }
            QComboBox:hover {
                border-color: #adb5bd;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid #ced4da;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background-color: #f8f9fa;
            }
            QComboBox::down-arrow {
                image: url(D:/workspace/TestTool/src/resources/icons/combobox.png);
                width: 12px;
                height: 12px;
            }
        """)
        
        # 编辑模式下不允许修改类型
        if self.is_edit:
            self.type_combo.setEnabled(False)
        
        self.form_layout.addRow("类型:", self.type_combo)
        
        # 基本信息字段
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入卡片名称")
        self.name_edit.setMaximumWidth(300)  # 限制最大宽度
        self.name_edit.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                padding: 6px 8px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: #ffffff;
                min-width: 200px;
                max-width: 300px;
            }
            QLineEdit:focus {
                border-color: #4299e1;
                outline: none;
            }
        """)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setMaximumWidth(300)  # 限制最大宽度
        self.description_edit.setPlaceholderText("请输入卡片描述")
        self.description_edit.setStyleSheet("""
            QTextEdit {
                font-size: 14px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                padding: 6px 8px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: #ffffff;
                min-width: 200px;
                max-width: 300px;
            }
            QTextEdit:focus {
                border-color: #4299e1;
                outline: none;
            }
            QTextEdit QScrollBar:vertical {
                background-color: #f3f4f6;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QTextEdit QScrollBar::handle:vertical {
                background-color: #9ca3af;
                border-radius: 6px;
                min-height: 20px;
            }
            QTextEdit QScrollBar::handle:vertical:hover {
                background-color: #6b7280;
            }
        """)
        
        self.form_layout.addRow("名称:", self.name_edit)
        self.form_layout.addRow("描述:", self.description_edit)
        
        # 动态配置区域
        self.dynamic_config_widget = QWidget()
        self.dynamic_config_layout = QVBoxLayout(self.dynamic_config_widget)
        self.dynamic_config_layout.setContentsMargins(0, 0, 0, 0)
        
        self.form_layout.addRow(self.dynamic_config_widget)
        
        # 初始化动态配置界面
        self.init_dynamic_config_ui()
        
        layout.addWidget(self.config_form)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_config)
        self.save_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4299e1;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 10px;
                font-weight: normal;
                min-width: 60px;
                height: 22px;
                padding: 0px 8px;
            }
            QPushButton:hover {
                background-color: #3182ce;
            }
        """
        )
        button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #a0aec0;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 10px;
                font-weight: normal;
                min-width: 60px;
                height: 22px;
                padding: 0px 8px;
            }
            QPushButton:hover {
                background-color: #718096;
            }
        """
        )
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def center_on_screen(self):
        """将对话框居中显示在屏幕上"""
        screen_geometry = self.screen().availableGeometry()
        dialog_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        dialog_geometry.moveCenter(center_point)
        self.move(dialog_geometry.topLeft())

    def init_dynamic_config_ui(self):
        """初始化动态配置界面"""
        # 完全清空动态配置区域的所有内容
        while self.dynamic_config_layout.count():
            item = self.dynamic_config_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 重置所有配置字段变量，避免类型切换时数据残留
        self.reset_config_fields()
        
        # 重置参数配置相关变量
        if hasattr(self, 'param_scroll_area'):
            self.param_scroll_area = None
        if hasattr(self, 'param_container'):
            self.param_container = None
        if hasattr(self, 'param_container_layout'):
            self.param_container_layout = None
        
        # 根据当前类型创建对应的配置界面
        current_type = self.type_combo.currentText()
        
        if current_type == "SQL工具":
            self.init_sql_config_ui()
        elif current_type == "HTTP接口":
            self.init_http_config_ui()
        elif current_type == "Python类":
            self.init_python_config_ui()

    def on_type_changed(self, new_type):
        """类型改变时的处理"""
        self.init_dynamic_config_ui()

    def reset_config_fields(self):
        """重置所有配置字段变量，避免类型切换时数据残留"""
        # SQL配置字段
        sql_fields = ['db_host_edit', 'db_port_edit', 'db_name_edit', 'db_user_edit', 'db_password_edit', 'sql_query_edit']
        for field in sql_fields:
            if hasattr(self, field):
                widget = getattr(self, field)
                if widget and widget.parent():
                    widget.setParent(None)
                    widget.deleteLater()
                setattr(self, field, None)
        
        # HTTP配置字段
        http_fields = ['http_url_edit', 'http_method_combo', 'http_headers_edit', 'http_body_edit']
        for field in http_fields:
            if hasattr(self, field):
                widget = getattr(self, field)
                if widget and widget.parent():
                    widget.setParent(None)
                    widget.deleteLater()
                setattr(self, field, None)
        
        # Python配置字段
        python_fields = ['python_module_edit', 'python_class_edit', 'python_method_edit', 'python_args_edit']
        for field in python_fields:
            if hasattr(self, field):
                widget = getattr(self, field)
                if widget and widget.parent():
                    widget.setParent(None)
                    widget.deleteLater()
                setattr(self, field, None)

    def init_sql_config_ui(self):
        """初始化SQL工具配置界面"""
        # 数据库连接配置 - 紧凑布局
        db_widget = QWidget()
        db_layout = QVBoxLayout(db_widget)
        db_layout.setContentsMargins(0, 0, 0, 0)
        db_layout.setSpacing(2)  # 减少行间距
        
        # 第一行：主机和端口
        row1_widget = QWidget()
        row1_layout = QHBoxLayout(row1_widget)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(6)
        
        db_host_edit = QLineEdit()
        db_host_edit.setPlaceholderText("localhost")
        db_host_edit.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                padding: 6px 8px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: #ffffff;
                min-width: 120px;
                max-width: 200px;
            }
            QLineEdit:focus {
                border-color: #4299e1;
                outline: none;
            }
        """)
        
        db_port_edit = QLineEdit()
        db_port_edit.setPlaceholderText("5432")
        db_port_edit.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                padding: 6px 8px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: #ffffff;
                min-width: 80px;
                max-width: 100px;
            }
            QLineEdit:focus {
                border-color: #4299e1;
                outline: none;
            }
        """)
        
        row1_layout.addWidget(QLabel("主机:"))
        row1_layout.addWidget(db_host_edit)
        row1_layout.addWidget(QLabel("端口:"))
        row1_layout.addWidget(db_port_edit)
        row1_layout.addStretch()
        
        # 第二行：库名和用户名
        row2_widget = QWidget()
        row2_layout = QHBoxLayout(row2_widget)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(6)
        
        db_name_edit = QLineEdit()
        db_name_edit.setPlaceholderText("库名")
        db_name_edit.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                padding: 6px 8px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: #ffffff;
                min-width: 120px;
                max-width: 200px;
            }
            QLineEdit:focus {
                border-color: #4299e1;
                outline: none;
            }
        """)
        
        db_user_edit = QLineEdit()
        db_user_edit.setPlaceholderText("用户")
        db_user_edit.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                padding: 6px 8px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: #ffffff;
                min-width: 120px;
                max-width: 200px;
            }
            QLineEdit:focus {
                border-color: #4299e1;
                outline: none;
            }
        """)
        
        row2_layout.addWidget(QLabel("库名:"))
        row2_layout.addWidget(db_name_edit)
        row2_layout.addWidget(QLabel("用户:"))
        row2_layout.addWidget(db_user_edit)
        row2_layout.addStretch()
        
        # 第三行：密码
        row3_widget = QWidget()
        row3_layout = QHBoxLayout(row3_widget)
        row3_layout.setContentsMargins(0, 0, 0, 0)
        row3_layout.setSpacing(6)
        
        db_password_edit = QLineEdit()
        db_password_edit.setEchoMode(QLineEdit.Password)
        db_password_edit.setPlaceholderText("密码")
        db_password_edit.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                padding: 6px 8px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: #ffffff;
                min-width: 120px;
                max-width: 200px;
            }
            QLineEdit:focus {
                border-color: #4299e1;
                outline: none;
            }
        """)
        
        row3_layout.addWidget(QLabel("密码:"))
        row3_layout.addWidget(db_password_edit)
        row3_layout.addStretch()
        
        db_layout.addWidget(row1_widget)
        db_layout.addWidget(row2_widget)
        db_layout.addWidget(row3_widget)
        
        # SQL查询配置
        sql_widget = QWidget()
        sql_layout = QVBoxLayout(sql_widget)
        sql_layout.setContentsMargins(0, 0, 0, 0)
        sql_layout.setSpacing(2)  # 减少间距
        
        sql_query_edit = QTextEdit()
        sql_query_edit.setMaximumHeight(100)
        sql_query_edit.setPlaceholderText("请输入SQL查询语句...")
        sql_query_edit.setStyleSheet("""
            QTextEdit {
                font-size: 14px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                padding: 6px 8px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QTextEdit:focus {
                border-color: #4299e1;
                outline: none;
            }
            QTextEdit QScrollBar:vertical {
                background-color: #f3f4f6;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QTextEdit QScrollBar::handle:vertical {
                background-color: #9ca3af;
                border-radius: 6px;
                min-height: 20px;
            }
            QTextEdit QScrollBar::handle:vertical:hover {
                background-color: #6b7280;
            }
        """)
        sql_layout.addWidget(QLabel("SQL:"))
        sql_layout.addWidget(sql_query_edit)
        
        # 将控件保存为实例变量，供后续使用
        self.db_host_edit = db_host_edit
        self.db_port_edit = db_port_edit
        self.db_name_edit = db_name_edit
        self.db_user_edit = db_user_edit
        self.db_password_edit = db_password_edit
        self.sql_query_edit = sql_query_edit
        
        # 参数配置
        param_widget = QWidget()
        param_layout = QVBoxLayout(param_widget)
        param_layout.setContentsMargins(0, 0, 0, 0)
        param_layout.setSpacing(2)  # 减少间距
        
        # 参数配置标题
        param_title = QLabel("参数配置")
        param_title.setStyleSheet("QLabel { font-weight: bold; color: #2d3748; font-size: 12px; margin-bottom: 0px; }")
        param_layout.addWidget(param_title)
        
        # 参数配置容器
        param_scroll_area = QScrollArea()
        param_scroll_area.setWidgetResizable(True)
        param_scroll_area.setFixedHeight(300)  # 增加固定高度
        param_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        param_scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QScrollArea QScrollBar:vertical {
                background-color: #f3f4f6;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollArea QScrollBar::handle:vertical {
                background-color: #9ca3af;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollArea QScrollBar::handle:vertical:hover {
                background-color: #6b7280;
            }
            QScrollArea QScrollBar::add-line:vertical, QScrollArea QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        param_container = QWidget()
        param_container_layout = QVBoxLayout(param_container)
        param_container_layout.setSpacing(4)  # 减少参数行间距
        param_container_layout.setAlignment(Qt.AlignTop)  # 确保内容从顶部开始排列
        
        param_scroll_area.setWidget(param_container)
        param_layout.addWidget(param_scroll_area)
        
        # 添加参数按钮
        add_param_btn = QPushButton("+ 添加参数")
        add_param_btn.clicked.connect(self.add_sql_parameter)
        add_param_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #48bb78;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 10px;
                font-weight: normal;
                min-width: 70px;
                height: 22px;
                padding: 0px 6px;
                max-width: 70px;
                text-align: left;
                padding-left: 8px;
            }
            QPushButton:hover {
                background-color: #38a169;
            }
        """
        )
        param_layout.addWidget(add_param_btn)
        
        # 将参数配置控件保存为实例变量，供后续使用
        self.param_scroll_area = param_scroll_area
        self.param_container = param_container
        self.param_container_layout = param_container_layout
        
        self.dynamic_config_layout.addWidget(db_widget)
        self.dynamic_config_layout.addWidget(sql_widget)
        self.dynamic_config_layout.addWidget(param_widget)

    def init_http_config_ui(self):
        """初始化HTTP接口配置界面"""
        # 请求配置 - 紧凑布局
        request_widget = QWidget()
        request_layout = QVBoxLayout(request_widget)
        request_layout.setContentsMargins(0, 0, 0, 0)
        request_layout.setSpacing(4)
        
        # 第一行：URL和方法
        row1_widget = QWidget()
        row1_layout = QHBoxLayout(row1_widget)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(6)
        
        http_url_edit = QLineEdit()
        http_url_edit.setPlaceholderText("https://api.example.com/endpoint")
        http_url_edit.setMinimumWidth(400)  # 增加最小宽度
        # 设置文本显示开始部分而不是末尾
        http_url_edit.textChanged.connect(lambda: http_url_edit.setCursorPosition(0))
        http_url_edit.setStyleSheet("""
            QLineEdit {
                height: 22px;
                font-size: 14px;
                min-width: 600px;
                max-width: 1000px;
                text-align: left;
            }
        """)
        
        http_method_combo = NoWheelComboBox()
        http_method_combo.addItems(["GET", "POST", "PUT", "DELETE", "PATCH"])
        # 使用紧凑的下拉框样式
        http_method_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 20px 6px 12px;
                background-color: white;
                min-width: 100px;
                max-width: 100px;
                font-size: 12px;
            }
            QComboBox:focus {
                border-color: #0078d4;
                outline: none;
            }
            QComboBox:hover {
                border-color: #adb5bd;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid #ced4da;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background-color: #f8f9fa;
            }
            QComboBox::down-arrow {
                image: url(D:/workspace/TestTool/src/resources/icons/combobox.png);
                width: 12px;
                height: 12px;
            }
        """)
        
        row1_layout.addWidget(QLabel("方法:"))
        row1_layout.addWidget(http_method_combo)
        row1_layout.addWidget(QLabel("URL:"))
        row1_layout.addWidget(http_url_edit)
        row1_layout.addStretch()
        
        # 第二行：请求头
        row2_widget = QWidget()
        row2_layout = QHBoxLayout(row2_widget)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(6)
        row2_layout.setAlignment(Qt.AlignTop)  # 设置顶部对齐
        
        http_headers_edit = QTextEdit()
        http_headers_edit.setMaximumHeight(40)  # 减少高度
        http_headers_edit.setPlaceholderText('{"Content-Type": "application/json"}')
        http_headers_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px;
                font-size: 14px;
                background-color: #ffffff;
            }
            QTextEdit QScrollBar:vertical {
                background-color: #f3f4f6;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QTextEdit QScrollBar::handle:vertical {
                background-color: #9ca3af;
                border-radius: 6px;
                min-height: 20px;
            }
            QTextEdit QScrollBar::handle:vertical:hover {
                background-color: #6b7280;
            }
            QTextEdit QScrollBar::add-line:vertical, QTextEdit QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        # 创建标签并设置顶部对齐
        headers_label = QLabel("请求头:")
        headers_label.setAlignment(Qt.AlignTop)
        
        row2_layout.addWidget(headers_label)
        row2_layout.addWidget(http_headers_edit)
        row2_layout.addStretch()
        
        request_layout.addWidget(row1_widget)
        request_layout.addWidget(row2_widget)
        
        # 请求体配置
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(6)
        body_layout.setAlignment(Qt.AlignTop)  # 设置顶部对齐
        
        http_body_edit = QTextEdit()
        http_body_edit.setMaximumHeight(150)
        http_body_edit.setPlaceholderText('{"key": "value"}')
        http_body_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px;
                font-size: 14px;
                background-color: #ffffff;
            }
            QTextEdit QScrollBar:vertical {
                background-color: #f3f4f6;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QTextEdit QScrollBar::handle:vertical {
                background-color: #9ca3af;
                border-radius: 6px;
                min-height: 20px;
            }
            QTextEdit QScrollBar::handle:vertical:hover {
                background-color: #6b7280;
            }
            QTextEdit QScrollBar::add-line:vertical, QTextEdit QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        # 创建标签并设置顶部对齐
        body_label = QLabel("请求体:")
        body_label.setAlignment(Qt.AlignTop)
        
        body_layout.addWidget(body_label)
        body_layout.addWidget(http_body_edit)
        body_layout.addStretch()
        
        # 将控件保存为实例变量，供后续使用
        self.http_url_edit = http_url_edit
        self.http_method_combo = http_method_combo
        self.http_headers_edit = http_headers_edit
        self.http_body_edit = http_body_edit
        
        # 参数配置
        param_widget = QWidget()
        param_layout = QVBoxLayout(param_widget)
        param_layout.setContentsMargins(0, 0, 0, 0)
        param_layout.setSpacing(2)  # 减少间距
        
        # 参数配置标题
        param_title = QLabel("参数配置")
        param_title.setStyleSheet("QLabel { font-weight: bold; color: #2d3748; font-size: 12px; margin-bottom: 0px; }")
        param_layout.addWidget(param_title)
        
        # 参数配置容器
        param_scroll_area = QScrollArea()
        param_scroll_area.setWidgetResizable(True)
        param_scroll_area.setFixedHeight(300)  # 增加固定高度
        param_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        param_scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QScrollArea QScrollBar:vertical {
                background-color: #f3f4f6;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollArea QScrollBar::handle:vertical {
                background-color: #9ca3af;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollArea QScrollBar::handle:vertical:hover {
                background-color: #6b7280;
            }
            QScrollArea QScrollBar::add-line:vertical, QScrollArea QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        param_container = QWidget()
        param_container_layout = QVBoxLayout(param_container)
        param_container_layout.setSpacing(8)
        param_container_layout.setAlignment(Qt.AlignTop)  # 确保内容从顶部开始排列
        
        param_scroll_area.setWidget(param_container)
        param_layout.addWidget(param_scroll_area)
        
        # 添加参数按钮
        add_param_btn = QPushButton("+ 添加参数")
        add_param_btn.clicked.connect(self.add_http_parameter)
        add_param_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #48bb78;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 10px;
                font-weight: normal;
                min-width: 70px;
                height: 22px;
                padding: 0px 6px;
                max-width: 70px;
                text-align: left;
                padding-left: 8px;
            }
            QPushButton:hover {
                background-color: #38a169;
            }
        """
        )
        param_layout.addWidget(add_param_btn)
        
        # 将参数配置控件保存为实例变量，供后续使用
        self.param_scroll_area = param_scroll_area
        self.param_container = param_container
        self.param_container_layout = param_container_layout
        
        self.dynamic_config_layout.addWidget(request_widget)
        self.dynamic_config_layout.addWidget(body_widget)
        self.dynamic_config_layout.addWidget(param_widget)

    def init_python_config_ui(self):
        """初始化Python类配置界面"""
        # 类配置
        class_group = QGroupBox("Python类配置")
        class_layout = QFormLayout(class_group)
        
        python_module_edit = QLineEdit()
        python_module_edit.setPlaceholderText("my_module")
        python_class_edit = QLineEdit()
        python_class_edit.setPlaceholderText("MyClass")
        
        class_layout.addRow("模块名:", python_module_edit)
        class_layout.addRow("类名:", python_class_edit)
        
        # 方法配置
        method_group = QGroupBox("方法配置")
        method_layout = QFormLayout(method_group)
        
        python_method_edit = QLineEdit()
        python_method_edit.setPlaceholderText("my_method")
        python_args_edit = QTextEdit()
        python_args_edit.setMaximumHeight(60)
        python_args_edit.setPlaceholderText('["arg1", "arg2"]')
        
        method_layout.addRow("方法名:", python_method_edit)
        method_layout.addRow("参数:", python_args_edit)
        
        # 将控件保存为实例变量，供后续使用
        self.python_module_edit = python_module_edit
        self.python_class_edit = python_class_edit
        self.python_method_edit = python_method_edit
        self.python_args_edit = python_args_edit
        
        self.dynamic_config_layout.addWidget(class_group)
        self.dynamic_config_layout.addWidget(method_group)
        
        # 参数配置
        param_widget = QWidget()
        param_layout = QVBoxLayout(param_widget)
        param_layout.setContentsMargins(0, 0, 0, 0)
        param_layout.setSpacing(2)  # 减少间距
        
        # 参数配置标题
        param_title = QLabel("参数配置")
        param_title.setStyleSheet("QLabel { font-weight: bold; color: #2d3748; font-size: 12px; margin-bottom: 0px; }")
        param_layout.addWidget(param_title)
        
        # 参数配置容器
        param_scroll_area = QScrollArea()
        param_scroll_area.setWidgetResizable(True)
        param_scroll_area.setFixedHeight(300)  # 增加固定高度
        param_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        param_scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QScrollArea QScrollBar:vertical {
                background-color: #f3f4f6;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollArea QScrollBar::handle:vertical {
                background-color: #9ca3af;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollArea QScrollBar::handle:vertical:hover {
                background-color: #6b7280;
            }
            QScrollArea QScrollBar::add-line:vertical, QScrollArea QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        param_container = QWidget()
        param_container_layout = QVBoxLayout(param_container)
        param_container_layout.setSpacing(4)  # 减少参数行间距
        param_container_layout.setAlignment(Qt.AlignTop)  # 确保内容从顶部开始排列
        
        param_scroll_area.setWidget(param_container)
        param_layout.addWidget(param_scroll_area)
        
        # 添加参数按钮
        add_param_btn = QPushButton("+ 添加参数")
        add_param_btn.clicked.connect(self.add_python_parameter)
        add_param_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #48bb78;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 10px;
                font-weight: normal;
                min-width: 70px;
                height: 22px;
                padding: 0px 6px;
                max-width: 70px;
                text-align: left;
                padding-left: 8px;
            }
            QPushButton:hover {
                background-color: #38a169;
            }
        """
        )
        param_layout.addWidget(add_param_btn)
        
        # 将参数配置控件保存为实例变量，供后续使用
        self.param_scroll_area = param_scroll_area
        self.param_container = param_container
        self.param_container_layout = param_container_layout
        
        self.dynamic_config_layout.addWidget(param_widget)

    def add_sql_parameter(self):
        """添加SQL参数配置"""
        self.add_parameter_row("SQL")

    def add_http_parameter(self):
        """添加HTTP参数配置"""
        self.add_parameter_row("HTTP")

    def add_python_parameter(self):
        """添加Python参数配置"""
        self.add_parameter_row("Python")

    def add_parameter_row(self, param_type):
        """添加参数配置行"""
        # 主参数行容器
        param_widget = QWidget()
        param_layout = QVBoxLayout(param_widget)
        param_layout.setContentsMargins(0, 0, 0, 0)
        param_layout.setSpacing(4)  # 减少间距实现紧凑布局
        
        # 参数基本信息行
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(6)  # 减少水平间距

        # 统一按钮样式
        button_style = """
            QPushButton {
                background-color: #4299e1;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
                min-width: 60px;
                height: 28px;
            }
            QPushButton:hover {
                background-color: #3182ce;
            }
        """
        
        # 英文字段输入框
        field_name_edit = QLineEdit()
        field_name_edit.setPlaceholderText("英文字段名")
        field_name_edit.setStyleSheet("QLineEdit { height: 22px; font-size: 14px; min-width: 120px; max-width: 120px; }")
        field_name_edit.setFixedWidth(120)
        
        # 中文字段输入框
        display_name_edit = QLineEdit()
        display_name_edit.setPlaceholderText("中文显示名")
        display_name_edit.setStyleSheet("QLineEdit { height: 22px; font-size: 14px; min-width: 120px; max-width: 120px; }")
        display_name_edit.setFixedWidth(120)
        
        # 类型选择下拉框
        type_combo = NoWheelComboBox()
        type_combo.addItems(FieldType.DISPLAY_TYPES)
        # 使用紧凑的下拉框样式
        type_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 20px 6px 12px;
                background-color: white;
                min-width: 120px;
                max-width: 120px;
                font-size: 14px;
            }
            QComboBox:focus {
                border-color: #0078d4;
                outline: none;
            }
            QComboBox:hover {
                border-color: #adb5bd;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid #ced4da;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background-color: #f8f9fa;
            }
            QComboBox::down-arrow {
                image: url(D:/workspace/TestTool/src/resources/icons/combobox.png);
                width: 12px;
                height: 12px;
            }
        """)
        
        # 默认值输入框
        default_value_edit = QLineEdit()
        default_value_edit.setPlaceholderText("默认值")
        default_value_edit.setStyleSheet("QLineEdit { height: 22px; font-size: 14px; min-width: 100px; max-width: 100px; }")
        default_value_edit.setFixedWidth(100)
        
        # 必填复选框
        required_checkbox = QCheckBox()
        required_checkbox.setStyleSheet("QCheckBox { font-size: 10px; }")
        required_checkbox.setToolTip("必填")
        
        # 删除参数按钮
        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f56565;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 10px;
                font-weight: normal;
                min-width: 40px;
                height: 22px;
                padding: 0px 4px;
            }
            QPushButton:hover {
                background-color: #e53e3e;
            }
        """
        )
        delete_btn.clicked.connect(lambda: self.delete_parameter_row(param_widget))
        
        # 枚举配置添加按钮（紧贴删除按钮）
        add_enum_btn = QPushButton("+枚举")
        add_enum_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #48bb78;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 10px;
                font-weight: normal;
                min-width: 40px;
                height: 22px;
                padding: 0px 4px;
            }
            QPushButton:hover {
                background-color: #38a169;
            }
        """
        )
        add_enum_btn.clicked.connect(lambda: self.add_enum_row(enum_container_layout))
        add_enum_btn.hide()
        
        info_layout.addWidget(QLabel("字段:"))
        info_layout.addWidget(field_name_edit)
        info_layout.addWidget(QLabel("显示:"))
        info_layout.addWidget(display_name_edit)
        info_layout.addWidget(QLabel("默认:"))
        info_layout.addWidget(default_value_edit)
        info_layout.addWidget(QLabel("类型:"))
        info_layout.addWidget(type_combo)
        info_layout.addWidget(QLabel("必填:"))  # 增加"必填："标签
        info_layout.addWidget(required_checkbox)
        info_layout.addWidget(delete_btn)
        info_layout.addWidget(add_enum_btn)  # 紧贴删除按钮
        info_layout.addStretch()
        
        param_layout.addWidget(info_widget)
        
        # 枚举配置容器（初始隐藏，缩进显示）
        enum_container = QWidget()
        enum_container.setObjectName("enum_container")  # 设置对象名称以便识别
        enum_container_layout = QVBoxLayout(enum_container)
        enum_container_layout.setContentsMargins(30, 0, 0, 0)  # 增加缩进到30像素
        enum_container_layout.setSpacing(2)  # 减少枚举行间距
        enum_container.hide()
        
        param_layout.addWidget(enum_container)
        
        # 类型改变时显示/隐藏枚举配置
        type_combo.currentTextChanged.connect(lambda text: self.on_param_type_changed(text, enum_container, add_enum_btn))
        
        self.param_container_layout.addWidget(param_widget)

    def add_enum_row(self, enum_layout):
        """添加枚举配置行"""
        # 检查当前枚举数量限制
        param_widget = enum_layout.parentWidget()
        if param_widget:
            # 查找参数行的类型下拉框 - 直接在整个对话框中查找
            type_combo = None
            # 查找所有类型下拉框
            combos = self.findChildren(NoWheelComboBox)
            for combo in combos:
                # 检查是否是参数类型下拉框（通过检查下拉框中的选项是否包含字段类型）
                if combo.count() > 0 and any(text in FieldType.DISPLAY_TYPES for text in [combo.itemText(i) for i in range(combo.count())]):
                    # 检查这个下拉框是否在当前参数行的父控件层级中
                    parent = combo.parent()
                    while parent:
                        if parent == param_widget.parent():
                            type_combo = combo
                            break
                        parent = parent.parent()
                    if type_combo:
                        break
            
            # 如果是点选类型且已有4个枚举，则不允许再添加
            if type_combo and FieldType.is_radio_type(type_combo.currentText()):
                current_enum_count = enum_layout.count()
                if current_enum_count >= 4:
                    Toast.warning(self, "点选类型最多只能添加4个枚举")
                    return
            # 下拉框类型没有枚举数量限制
        
        enum_widget = QWidget()
        enum_row_layout = QHBoxLayout(enum_widget)
        enum_row_layout.setContentsMargins(0, 0, 0, 0)
        enum_row_layout.setSpacing(8)
        
        # 枚举值输入框
        enum_value_edit = QLineEdit()
        enum_value_edit.setPlaceholderText("枚举值")
        enum_value_edit.setStyleSheet("QLineEdit { height: 20px; font-size: 14px; min-width: 120px; max-width: 120px; }")
        enum_value_edit.setFixedWidth(120)
        
        # 枚举描述输入框
        enum_desc_edit = QLineEdit()
        enum_desc_edit.setPlaceholderText("枚举描述")
        enum_desc_edit.setStyleSheet("QLineEdit { height: 20px; font-size: 14px; min-width: 120px; max-width: 120px; }")
        enum_desc_edit.setFixedWidth(120)
        
        # 删除枚举按钮
        delete_enum_btn = QPushButton("×")
        delete_enum_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f56565;
                color: white;
                border: none;
                border-radius: 1px;
                font-size: 8px;
                font-weight: normal;
                width: 16px;
                height: 16px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #e53e3e;
            }
        """
        )
        delete_enum_btn.clicked.connect(lambda: self.delete_enum_row(enum_widget))
        
        enum_row_layout.addWidget(QLabel("值:"))
        enum_row_layout.addWidget(enum_value_edit)
        enum_row_layout.addWidget(QLabel("描述:"))
        enum_row_layout.addWidget(enum_desc_edit)
        enum_row_layout.addWidget(delete_enum_btn)
        enum_row_layout.addStretch()
        
        enum_layout.addWidget(enum_widget)


    def on_param_type_changed(self, param_type, enum_container, add_enum_btn):
        """参数类型改变时的处理"""
        if FieldType.is_any_enum_type(param_type):
            enum_container.show()
            add_enum_btn.show()
        else:
            enum_container.hide()
            add_enum_btn.hide()

    def delete_parameter_row(self, param_widget):
        """删除参数配置行"""
        param_widget.deleteLater()

    def delete_enum_row(self, enum_widget):
        """删除枚举配置行"""
        enum_widget.deleteLater()

    def collect_sql_config(self):
        """收集SQL配置数据"""
        config = {
            "database": {
                "host": self.db_host_edit.text().strip() or "localhost",
                "port": self.db_port_edit.text().strip() or "5432",
                "name": self.db_name_edit.text().strip(),
                "user": self.db_user_edit.text().strip(),
                "password": self.db_password_edit.text().strip()
            },
            "query": self.sql_query_edit.toPlainText().strip()
        }
        return config

    def collect_http_config(self):
        """收集HTTP配置数据"""
        # 清理URL，移除反引号等特殊字符
        raw_url = self.http_url_edit.text().strip()
        # 更彻底的URL清理：移除反引号、空格、逗号等
        cleaned_url = raw_url.replace('`', '').replace(',', '').strip()
        
        config = {
            "url": cleaned_url,
            "method": self.http_method_combo.currentText(),
            "headers": {},
            "body": {}
        }
        
        print(f"[DEBUG] HTTP配置收集 - 原始URL: '{raw_url}'")
        print(f"[DEBUG] HTTP配置收集 - 清理后URL: '{cleaned_url}', 方法: {config['method']}")
        
        # 解析请求头
        headers_text = self.http_headers_edit.toPlainText().strip()
        if headers_text:
            try:
                config["headers"] = json.loads(headers_text)
                print(f"[DEBUG] HTTP头解析成功: {config['headers']}")
            except Exception as e:
                print(f"[DEBUG] HTTP头解析失败: {e}")
                pass
        
        # 解析请求体
        body_text = self.http_body_edit.toPlainText().strip()
        if body_text:
            try:
                config["body"] = json.loads(body_text)
                print(f"[DEBUG] HTTP请求体解析成功: {config['body']}")
            except Exception as e:
                print(f"[DEBUG] HTTP请求体解析失败: {e}")
                pass
        
        print(f"[DEBUG] 最终HTTP配置: {config}")
        return config

    def collect_python_config(self):
        """收集Python配置数据"""
        config = {
            "module": self.python_module_edit.text().strip(),
            "class": self.python_class_edit.text().strip(),
            "method": self.python_method_edit.text().strip(),
            "args": []
        }
        
        # 解析参数
        args_text = self.python_args_edit.toPlainText().strip()
        if args_text:
            try:
                config["args"] = json.loads(args_text)
            except:
                pass
        
        return config

    def collect_parameter_mappings(self):
        """收集参数映射配置"""
        mappings = {}
        
        print(f"[DEBUG] 开始收集参数映射，参数容器数量: {self.param_container_layout.count()}")
        
        # 遍历参数容器中的所有参数行
        for i in range(self.param_container_layout.count()):
            param_widget = self.param_container_layout.itemAt(i).widget()
            if param_widget:
                print(f"[DEBUG] 处理第{i}个参数行")
                # 获取参数行的所有子控件
                children = param_widget.findChildren(QLineEdit)
                combos = param_widget.findChildren(QComboBox)
                
                print(f"[DEBUG] 找到{len(children)}个输入框，{len(combos)}个下拉框")
                
                if len(children) >= 3 and len(combos) >= 1:
                    field_name = children[0].text().strip()  # 英文字段名
                    display_name = children[1].text().strip()  # 中文字段名
                    default_value = children[2].text().strip()  # 默认值
                    param_type = combos[0].currentText()  # 参数类型
                    
                    # 查找必填复选框
                    checkboxes = param_widget.findChildren(QCheckBox)
                    required = False
                    if checkboxes:
                        required = checkboxes[0].isChecked()
                    
                    print(f"[DEBUG] 参数信息 - 字段名: '{field_name}', 显示名: '{display_name}', 类型: {param_type}, 必填: {required}")
                    
                    if field_name and display_name:
                        # 构建结构化的映射配置
                        mapping_config = {
                            "display_name": display_name,
                            "type": FieldType.get_type_from_display(param_type),
                            "required": required,
                            "order": i  # 添加顺序字段
                        }
                        
                        # 添加默认值（如果有）
                        if default_value:
                            mapping_config["default_value"] = default_value
                        
                        # 如果是枚举类型（下拉框或点选），收集枚举配置
                        if FieldType.is_any_enum_type(param_type):
                             # 收集枚举配置
                             enum_items = []
                             # 查找枚举容器 - 通过objectName查找
                             enum_containers = param_widget.findChildren(QWidget, "enum_container")
                             
                             print(f"[DEBUG] 找到{len(enum_containers)}个枚举容器")
                             
                             for enum_container in enum_containers:
                                 if enum_container and enum_container.layout():
                                     # 检查这个容器是否有枚举行
                                     enum_layout = enum_container.layout()
                                     print(f"[DEBUG] 枚举容器有{enum_layout.count()}个枚举行")
                                     for k in range(enum_layout.count()):
                                         enum_widget = enum_layout.itemAt(k).widget()
                                         if enum_widget:
                                             enum_edits = enum_widget.findChildren(QLineEdit)
                                             if len(enum_edits) >= 2:
                                                 enum_value = enum_edits[0].text().strip()
                                                 enum_desc = enum_edits[1].text().strip()
                                                 if enum_value and enum_desc:
                                                     enum_items.append({
                                                         "value": enum_value,
                                                         "description": enum_desc
                                                     })
                             
                             if enum_items:
                                 mapping_config["options"] = enum_items
                                 print(f"[DEBUG] 添加了{len(enum_items)}个枚举选项")
                        
                        mappings[field_name] = mapping_config
                        print(f"[DEBUG] 成功添加参数映射: {field_name} -> {mapping_config}")
                else:
                    print(f"[DEBUG] 参数行控件不完整，跳过")
        
        print(f"[DEBUG] 最终参数映射: {mappings}")
        return mappings

    def load_sql_config(self, config):
        """加载SQL配置数据"""
        # 确保config是字典类型
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except:
                config = {}
        
        db_config = config.get("database", {})
        
        # 确保db_config是字典类型
        if isinstance(db_config, str):
            try:
                db_config = json.loads(db_config)
            except:
                db_config = {}
        
        self.db_host_edit.setText(db_config.get("host", ""))
        self.db_port_edit.setText(db_config.get("port", ""))
        self.db_name_edit.setText(db_config.get("name", ""))
        self.db_user_edit.setText(db_config.get("user", ""))
        self.db_password_edit.setText(db_config.get("password", ""))
        self.sql_query_edit.setPlainText(config.get("query", ""))

    def load_http_config(self, config):
        """加载HTTP配置数据"""
        # 确保config是字典类型
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except:
                config = {}
        
        self.http_url_edit.setText(config.get("url", ""))
        method = config.get("method", "GET")
        index = self.http_method_combo.findText(method)
        if index >= 0:
            self.http_method_combo.setCurrentIndex(index)
        
        headers = config.get("headers", {})
        if isinstance(headers, str):
            try:
                headers = json.loads(headers)
            except:
                headers = {}
        if headers:
            self.http_headers_edit.setPlainText(json.dumps(headers, ensure_ascii=False, indent=2))
        
        body = config.get("body", {})
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except:
                body = {}
        if body:
            self.http_body_edit.setPlainText(json.dumps(body, ensure_ascii=False, indent=2))

    def load_python_config(self, config):
        """加载Python配置数据"""
        # 确保config是字典类型
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except:
                config = {}
        
        self.python_module_edit.setText(config.get("module", ""))
        self.python_class_edit.setText(config.get("class", ""))
        self.python_method_edit.setText(config.get("method", ""))
        
        args = config.get("args", [])
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = []
        if args:
            self.python_args_edit.setPlainText(json.dumps(args, ensure_ascii=False, indent=2))

    def filter_mappings_by_type(self, mappings, card_type):
        """根据卡片类型过滤参数映射"""
        filtered_mappings = {}
        
        for field_name, mapping_config in mappings.items():
            # 检查参数是否与当前卡片类型匹配
            if self.is_mapping_compatible_with_type(mapping_config, card_type):
                filtered_mappings[field_name] = mapping_config
        
        return filtered_mappings
    
    def is_mapping_compatible_with_type(self, mapping_config, card_type):
        """检查参数映射是否与卡片类型兼容"""
        # 如果参数映射包含特定类型的标识符，则进行过滤
        if isinstance(mapping_config, str):
            # 旧格式：检查是否包含特定类型的标识符
            if card_type == "HTTP接口":
                # HTTP接口应该只包含HTTP相关的参数
                return not ("数据库" in mapping_config or "SQL" in mapping_config or "查询" in mapping_config)
            elif card_type == "SQL工具":
                # SQL工具应该只包含SQL相关的参数
                return not ("HTTP" in mapping_config or "URL" in mapping_config or "请求" in mapping_config)
            elif card_type == "Python类":
                # Python类应该只包含Python相关的参数
                return True  # Python类型参数通常比较通用
        else:
            # 新格式：检查是否有类型字段
            if "card_type" in mapping_config:
                # 如果参数映射指定了卡片类型，则进行严格匹配
                mapping_card_type = mapping_config.get("card_type", "")
                type_map = {"sql": "SQL工具", "http": "HTTP接口", "python": "Python类"}
                expected_type = type_map.get(mapping_card_type, "")
                return expected_type == card_type
            else:
                # 如果没有指定类型，则根据内容进行推断
                if card_type == "HTTP接口":
                    return not ("database" in str(mapping_config).lower() or "sql" in str(mapping_config).lower())
                elif card_type == "SQL工具":
                    return not ("http" in str(mapping_config).lower() or "url" in str(mapping_config).lower())
                elif card_type == "Python类":
                    return True
        
        # 默认情况下，允许所有参数映射
        return True

    def load_parameter_mappings(self, mappings):
        """加载参数映射配置"""
        # 清空现有参数配置
        for i in reversed(range(self.param_container_layout.count())):
            widget = self.param_container_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 根据当前卡片类型过滤参数映射
        current_type = self.type_combo.currentText()
        filtered_mappings = self.filter_mappings_by_type(mappings, current_type)
        
        # 按顺序字段排序参数映射
        sorted_mappings = sorted(
            filtered_mappings.items(),
            key=lambda x: x[1].get("order", 0) if isinstance(x[1], dict) else 0
        )
        
        # 添加参数配置行
        for field_name, mapping_config in sorted_mappings:
            # 处理新旧格式兼容
            if isinstance(mapping_config, str):
                # 旧格式：字符串格式，如"哈哥-下拉框，枚举aaa-男,bbb-女"
                config_parts = str(mapping_config).split('-')
                display_name = config_parts[0] if len(config_parts) > 0 else field_name
                # 兼容旧格式：如果包含"下拉框"则认为是下拉框类型
                control_type = FieldType.SELECT_DISPLAY if "下拉框" in mapping_config else FieldType.INPUT_DISPLAY
            else:
                # 新格式：结构化JSON对象
                display_name = mapping_config.get("display_name", field_name)
                control_type = FieldType.get_display_from_type(mapping_config.get("type", FieldType.INPUT))
            
            # 添加参数行
            self.add_parameter_row("")
            
            # 获取最新添加的参数行
            last_index = self.param_container_layout.count() - 1
            param_widget = self.param_container_layout.itemAt(last_index).widget()
            
            if param_widget:
                # 设置字段名、显示名和默认值
                children = param_widget.findChildren(QLineEdit)
                if len(children) >= 3:
                    children[0].setText(field_name)
                    children[1].setText(display_name)
                    # 设置默认值（如果存在）
                    if isinstance(mapping_config, dict) and "default_value" in mapping_config:
                        children[2].setText(mapping_config["default_value"])
                
                # 设置必填复选框状态
                checkboxes = param_widget.findChildren(QCheckBox)
                if checkboxes:
                    required = mapping_config.get("required", False) if isinstance(mapping_config, dict) else False
                    checkboxes[0].setChecked(required)
                
                # 设置参数类型
                combos = param_widget.findChildren(QComboBox)
                if len(combos) >= 1:
                    index = combos[0].findText(control_type)
                    if index >= 0:
                        combos[0].setCurrentIndex(index)
                    
                    # 如果是枚举类型（下拉框或点选），显示枚举容器和添加按钮
                    if FieldType.is_any_enum_type(control_type):
                            # 查找枚举容器和添加枚举按钮
                            enum_container = None
                            add_enum_btn = None
                            
                            # 使用objectName可靠地查找枚举容器
                            containers = param_widget.findChildren(QWidget)
                            for container in containers:
                                if container.objectName() == "enum_container":
                                    enum_container = container
                                    break
                            
                            # 查找添加枚举按钮
                            buttons = param_widget.findChildren(QPushButton)
                            for btn in buttons:
                                if btn.text() == "+枚举":
                                    add_enum_btn = btn
                                    break
                            
                            if enum_container and add_enum_btn:
                                self.on_param_type_changed(control_type, enum_container, add_enum_btn)
                
                # 如果是枚举类型（下拉框或点选），加载枚举配置
                if FieldType.is_any_enum_type(control_type):
                    # 使用objectName可靠地查找枚举容器
                    enum_container = None
                    containers = param_widget.findChildren(QWidget)
                    for container in containers:
                        if container.objectName() == "enum_container":
                            enum_container = container
                            break
                    
                    if enum_container:
                        # 确保枚举容器正确显示
                        enum_container.show()
                        
                        # 先清空现有的枚举配置
                        enum_layout = enum_container.layout()
                        if enum_layout:
                            for i in reversed(range(enum_layout.count())):
                                widget = enum_layout.itemAt(i).widget()
                                if widget:
                                    widget.deleteLater()
                        
                        # 处理新旧格式枚举配置
                        if isinstance(mapping_config, str) and "枚举" in mapping_config:
                            # 旧格式：字符串格式
                            enum_part = mapping_config.split("枚举")[1].strip()
                            enum_items = [item.strip() for item in enum_part.split(',')]
                            
                            for enum_item in enum_items:
                                enum_parts = enum_item.split('-')
                                if len(enum_parts) >= 2:
                                    self.add_enum_row(enum_container.layout())
                                    
                                    # 获取最新添加的枚举行
                                    enum_layout = enum_container.layout()
                                    last_enum_index = enum_layout.count() - 1
                                    enum_widget = enum_layout.itemAt(last_enum_index).widget()
                                    
                                    if enum_widget:
                                        enum_edits = enum_widget.findChildren(QLineEdit)
                                        if len(enum_edits) >= 2:
                                            enum_edits[0].setText(enum_parts[0])
                                            enum_edits[1].setText(enum_parts[1])
                        elif isinstance(mapping_config, dict) and "options" in mapping_config:
                            # 新格式：结构化JSON对象
                            enum_items = mapping_config.get("options", [])
                            
                            for enum_item in enum_items:
                                self.add_enum_row(enum_container.layout())
                                
                                # 获取最新添加的枚举行
                                enum_layout = enum_container.layout()
                                last_enum_index = enum_layout.count() - 1
                                enum_widget = enum_layout.itemAt(last_enum_index).widget()
                                
                                if enum_widget:
                                    enum_edits = enum_widget.findChildren(QLineEdit)
                                    if len(enum_edits) >= 2:
                                        enum_edits[0].setText(enum_item.get("value", ""))
                                        enum_edits[1].setText(enum_item.get("description", ""))



    def get_folder_name(self):
        """获取当前文件夹名称"""
        if not self.current_folder_id:
            return "未知文件夹"
        
        # 使用数据库服务获取文件夹名称
        folder = self.tool_cards_service.get_folder_by_id(self.current_folder_id)
        if folder:
            return folder.get("name", "未知文件夹")
        
        return "未知文件夹"

    def load_card_data(self):
        """加载卡片数据"""
        if not self.card_data:
            return

        self.name_edit.setText(self.card_data.get("name", ""))
        self.description_edit.setText(self.card_data.get("description", ""))
        
        # 设置卡片类型
        card_type = self.card_data.get("type", "sql")
        type_map = {"sql": "SQL工具", "http": "HTTP接口", "python": "Python类"}
        type_display = type_map.get(card_type, "SQL工具")
        index = self.type_combo.findText(type_display)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        
        # 加载配置数据到动态界面
        config = self.card_data.get("config", {})
        mappings = self.card_data.get("mappings", {})
        
        # 只加载与当前卡片类型相关的配置和参数映射
        if card_type == "sql":
            self.load_sql_config(config)
            self.load_parameter_mappings(mappings)
        elif card_type == "http":
            self.load_http_config(config)
            self.load_parameter_mappings(mappings)
        elif card_type == "python":
            self.load_python_config(config)
            self.load_parameter_mappings(mappings)

    def save_config(self):
        """保存配置"""
        # 验证输入
        name = self.name_edit.text().strip()
        if not name:
            Toast.error(self, "输入错误", "请输入卡片名称")
            return

        # 根据类型收集配置数据
        current_type = self.type_combo.currentText()
        config_data = {}
        mapping_data = {}
        
        print(f"[DEBUG] 开始保存配置，类型: {current_type}, 名称: {name}")
        
        if current_type == "SQL工具":
            config_data = self.collect_sql_config()
            mapping_data = self.collect_parameter_mappings()
        elif current_type == "HTTP接口":
            config_data = self.collect_http_config()
            mapping_data = self.collect_parameter_mappings()
        elif current_type == "Python类":
            config_data = self.collect_python_config()
            mapping_data = self.collect_parameter_mappings()

        print(f"[DEBUG] 收集到的配置数据: {config_data}")
        print(f"[DEBUG] 收集到的映射数据: {mapping_data}")

        # 创建或更新卡片数据
        if self.is_edit:
            # 更新现有卡片
            self.update_card(name, config_data, mapping_data)
        else:
            # 创建新卡片
            self.create_card(name, config_data, mapping_data)

    def create_card(self, name, config_data, mapping_data):
        """创建新卡片"""
        if not self.current_folder_id:
            Toast.error(self, "操作错误", "请先选择文件夹")
            return

        # 获取卡片类型
        type_display = self.type_combo.currentText()
        type_map = {"SQL工具": "sql", "HTTP接口": "http", "Python类": "python"}
        card_type = type_map.get(type_display, "sql")
        
        # 创建卡片数据
        card_data = {
            "folder_id": self.current_folder_id,
            "name": name,
            "description": self.description_edit.toPlainText(),
            "card_type": card_type,
            "config": config_data,
            "mappings": mapping_data,
            "sort_order": 0,
            "enabled": True,
            "created_by": "admin"
        }
        
        print(f"[DEBUG] 创建卡片数据: {card_data}")
        
        # 使用数据库服务创建卡片
        card_id = self.tool_cards_service.create_card(card_data)
        
        print(f"[DEBUG] 数据库创建结果: {card_id}")
        
        if card_id:
            self.accept()
            Toast.success(self, "添加成功", f"卡片 '{name}' 已添加")
        else:
            Toast.error(self, "添加失败", "无法创建卡片，请检查数据库连接")

    def update_card(self, name, config_data, mapping_data):
        """更新现有卡片"""
        if not self.current_folder_id:
            Toast.error(self, "操作错误", "请先选择文件夹")
            return

        # 获取卡片ID
        card_id = self.card_data.get('id')
        if not card_id:
            print(f"[ERROR] 卡片ID不存在，无法更新")
            Toast.error(self, "保存失败", "卡片ID不存在")
            return

        # 获取卡片类型
        type_display = self.type_combo.currentText()
        type_map = {"SQL工具": "sql", "HTTP接口": "http", "Python类": "python"}
        card_type = type_map.get(type_display, "sql")
        
        # 创建卡片数据
        card_data = {
            "name": name,
            "description": self.description_edit.toPlainText(),
            "card_type": card_type,
            "config": config_data,
            "mappings": mapping_data,
            "sort_order": 0,
            "enabled": True
        }
        
        print(f"[DEBUG] 更新卡片数据 - 卡片ID: {card_id}")
        print(f"[DEBUG] 更新卡片数据: {card_data}")
        
        # 使用数据库服务更新卡片
        success = self.tool_cards_service.update_card(card_id, card_data)
        
        print(f"[DEBUG] 数据库更新结果: {success}")
        
        if success:
            self.accept()
            Toast.success(self, "保存成功", f"卡片 '{name}' 已更新")
        else:
            print(f"[ERROR] 卡片更新失败，卡片ID: {card_id}")
            Toast.error(self, "保存失败", "无法更新卡片，请检查数据库连接或卡片是否存在")

    def get_config_data(self):
        """获取配置数据"""
        return self.folder_data