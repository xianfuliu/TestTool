import os
import json
import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QGroupBox,
                             QComboBox, QCheckBox, QTextEdit, QMessageBox,
                             QScrollArea, QSizePolicy, QDialog,
                             QListWidget, QListWidgetItem, QFormLayout, QTabWidget, QTableWidget,
                             QTableWidgetItem, QSpacerItem)
from PyQt5.QtCore import Qt, pyqtSignal
from src.ui.dialogs.api_tool_interface_config_dialog import InterfaceConfigDialog
from src.ui.dialogs.api_tool_sql_config_dialog import SQLConfigDialog
from src.ui.widgets.no_wheel_combo_box import NoWheelComboBox
from src.ui.widgets.toast_tips import Toast
from src.utils.resource_utils import resource_path


class ConfigManagementDialog(QDialog):
    """配置管理弹窗"""
    # 定义保存成功的信号
    config_saved = pyqtSignal(str)  # 参数为消息内容

    def __init__(self, parent=None, api_tool_tab=None):
        super().__init__(parent)
        self.api_tool_tab = api_tool_tab
        self.setWindowTitle("配置")
        self.setModal(True)
        self.setFixedSize(900, 800)  # 固定尺寸，更加紧凑

        self.init_ui()
        self.load_products_config()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # 创建Tab控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)  # 更现代的标签样式

        # 产品管理Tab
        self.product_management_tab = self.create_product_management_tab()
        self.tab_widget.addTab(self.product_management_tab, "产品管理")

        # 产品详情配置Tab
        self.product_detail_tab = self.create_product_detail_tab()
        self.tab_widget.addTab(self.product_detail_tab, "产品详情配置")

        layout.addWidget(self.tab_widget)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_all_config)
        self.save_btn.setFixedWidth(80)

        self.cancel_btn = QPushButton("关闭")
        self.cancel_btn.clicked.connect(self.close)
        self.cancel_btn.setFixedWidth(80)

        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def create_product_management_tab(self):
        """创建产品管理Tab - 优化版"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)

        # 产品编辑区域
        product_edit_group = QGroupBox()
        product_edit_group.setContentsMargins(8, 12, 8, 8)
        product_edit_layout = QVBoxLayout(product_edit_group)
        product_edit_layout.setSpacing(10)

        # 产品选择
        product_select_layout = QHBoxLayout()
        product_select_layout.setSpacing(8)
        product_select_layout.addWidget(QLabel("产品:"))
        self.product_combo = NoWheelComboBox()
        self.product_combo.currentTextChanged.connect(self.on_product_selected)
        self.product_combo.setFixedWidth(250)
        product_select_layout.addWidget(self.product_combo)
        product_select_layout.addStretch()
        product_edit_layout.addLayout(product_select_layout)

        # 产品编辑表单
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(10)

        self.product_name_edit = QLineEdit()
        self.product_name_edit.setReadOnly(True)
        self.product_name_edit.setFixedWidth(300)
        self.product_name_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")

        self.product_config_path_edit = QLineEdit()
        self.product_config_path_edit.setReadOnly(True)
        self.product_config_path_edit.setFixedWidth(400)
        self.product_config_path_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")

        # 锁定状态显示（只读）
        self.product_locked_label = QLabel("未锁定")
        self.product_locked_label.setStyleSheet("color: green; font-weight: bold; padding: 3px;")
        self.product_locked_label.setFixedWidth(80)
        self.product_locked_label.setAlignment(Qt.AlignCenter)

        form_layout.addRow("产品名称:", self.product_name_edit)
        form_layout.addRow("配置文件路径:", self.product_config_path_edit)
        form_layout.addRow("状态:", self.product_locked_label)
        product_edit_layout.addLayout(form_layout)

        # 产品操作按钮
        product_btn_layout = QHBoxLayout()
        product_btn_layout.setSpacing(8)

        self.add_product_btn = QPushButton("新增")
        self.add_product_btn.clicked.connect(self.add_product)
        self.add_product_btn.setFixedWidth(80)

        self.edit_product_btn = QPushButton("编辑")
        self.edit_product_btn.clicked.connect(self.edit_product)
        self.edit_product_btn.setFixedWidth(80)

        self.delete_product_btn = QPushButton("删除")
        self.delete_product_btn.clicked.connect(self.delete_product)
        self.delete_product_btn.setFixedWidth(80)

        product_btn_layout.addWidget(self.add_product_btn)
        product_btn_layout.addWidget(self.edit_product_btn)
        product_btn_layout.addWidget(self.delete_product_btn)
        product_btn_layout.addStretch()

        product_edit_layout.addLayout(product_btn_layout)
        layout.addWidget(product_edit_group)
        layout.addStretch()

        return widget

    def create_product_detail_tab(self):
        """创建产品详情配置Tab - 优化版"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)

        # 产品选择和锁定提示
        product_select_layout = QHBoxLayout()
        product_select_layout.setSpacing(8)
        product_select_layout.addWidget(QLabel("产品:"))
        self.detail_product_combo = NoWheelComboBox()
        self.detail_product_combo.currentTextChanged.connect(self.on_detail_product_changed)
        self.detail_product_combo.setFixedWidth(250)
        product_select_layout.addWidget(self.detail_product_combo)

        # 锁定状态提示
        self.detail_locked_label = QLabel("")
        self.detail_locked_label.setStyleSheet(
            "color: red; font-weight: bold; padding: 5px; border: 1px solid red; border-radius: 3px;")
        self.detail_locked_label.setVisible(False)
        self.detail_locked_label.setFixedWidth(180)
        self.detail_locked_label.setAlignment(Qt.AlignCenter)
        product_select_layout.addWidget(self.detail_locked_label)
        product_select_layout.addStretch()

        layout.addLayout(product_select_layout)

        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.detail_layout = QVBoxLayout(self.scroll_widget)
        self.detail_layout.setSpacing(8)
        self.detail_layout.setContentsMargins(5, 5, 5, 5)

        # 加解密配置
        encryption_group = QGroupBox("加解密")
        encryption_group.setContentsMargins(8, 12, 8, 8)
        self.encryption_layout = QFormLayout(encryption_group)
        self.encryption_layout.setSpacing(8)
        self.encryption_layout.setVerticalSpacing(8)

        self.detail_enable_encryption = QCheckBox("启用加解密")

        self.detail_encrypt_url_edit = QLineEdit()
        self.detail_encrypt_url_edit.setPlaceholderText("加密接口URL")
        self.detail_encrypt_url_edit.setFixedWidth(450)

        self.detail_decrypt_url_edit = QLineEdit()
        self.detail_decrypt_url_edit.setPlaceholderText("解密接口URL")
        self.detail_decrypt_url_edit.setFixedWidth(450)

        self.encryption_layout.addRow(self.detail_enable_encryption)
        self.encryption_layout.addRow("加密接口:", self.detail_encrypt_url_edit)
        self.encryption_layout.addRow("解密接口:", self.detail_decrypt_url_edit)

        self.detail_layout.addWidget(encryption_group)

        # 定时任务配置
        schedule_group = QGroupBox("定时任务")
        schedule_group.setContentsMargins(8, 12, 8, 8)
        self.schedule_layout = QVBoxLayout(schedule_group)
        self.schedule_layout.setSpacing(8)

        self.schedule_list = QListWidget()
        self.schedule_list.setFixedHeight(120)  # 固定高度

        schedule_btn_layout = QHBoxLayout()
        schedule_btn_layout.setSpacing(8)

        self.add_schedule_btn = QPushButton("新增")
        self.add_schedule_btn.clicked.connect(self.add_schedule_task)
        self.add_schedule_btn.setFixedWidth(80)

        self.edit_schedule_btn = QPushButton("编辑")
        self.edit_schedule_btn.clicked.connect(self.edit_schedule_task)
        self.edit_schedule_btn.setFixedWidth(80)

        self.view_schedule_btn = QPushButton("查看")  # 新增查看按钮
        self.view_schedule_btn.clicked.connect(self.view_schedule_task)
        self.view_schedule_btn.setFixedWidth(80)

        self.remove_schedule_btn = QPushButton("删除")
        self.remove_schedule_btn.clicked.connect(self.remove_schedule_task)
        self.remove_schedule_btn.setFixedWidth(80)

        schedule_btn_layout.addWidget(self.add_schedule_btn)
        schedule_btn_layout.addWidget(self.edit_schedule_btn)
        schedule_btn_layout.addWidget(self.view_schedule_btn)  # 添加查看按钮
        schedule_btn_layout.addWidget(self.remove_schedule_btn)
        schedule_btn_layout.addStretch()

        self.schedule_layout.addWidget(self.schedule_list)
        self.schedule_layout.addLayout(schedule_btn_layout)

        self.detail_layout.addWidget(schedule_group)

        # 布局配置
        layout_config_group = QGroupBox("布局")
        layout_config_group.setContentsMargins(8, 12, 8, 8)
        self.layout_config_layout = QVBoxLayout(layout_config_group)
        self.layout_config_layout.setSpacing(8)

        self.layout_list = QListWidget()
        self.layout_list.setSelectionMode(QListWidget.SingleSelection)
        self.layout_list.setDropIndicatorShown(True)
        self.layout_list.setFixedHeight(150)  # 固定高度

        layout_btn_layout = QHBoxLayout()
        layout_btn_layout.setSpacing(8)

        self.add_layout_item_btn = QPushButton("新增")
        self.add_layout_item_btn.clicked.connect(self.add_layout_item)
        self.add_layout_item_btn.setFixedWidth(70)

        self.edit_layout_item_btn = QPushButton("编辑")
        self.edit_layout_item_btn.clicked.connect(self.edit_layout_item)
        self.edit_layout_item_btn.setFixedWidth(70)

        self.view_layout_item_btn = QPushButton("查看")  # 新增查看按钮
        self.view_layout_item_btn.clicked.connect(self.view_layout_item)
        self.view_layout_item_btn.setFixedWidth(70)

        self.remove_layout_item_btn = QPushButton("删除")
        self.remove_layout_item_btn.clicked.connect(self.remove_layout_item)
        self.remove_layout_item_btn.setFixedWidth(70)

        layout_btn_layout.addWidget(self.add_layout_item_btn)
        layout_btn_layout.addWidget(self.edit_layout_item_btn)
        layout_btn_layout.addWidget(self.view_layout_item_btn)  # 添加查看按钮
        layout_btn_layout.addWidget(self.remove_layout_item_btn)
        layout_btn_layout.addStretch()

        self.layout_config_layout.addWidget(QLabel("提示：可以通过拖拽项来调整优先级顺序"))
        self.layout_config_layout.addWidget(self.layout_list)
        self.layout_config_layout.addLayout(layout_btn_layout)

        self.detail_layout.addWidget(layout_config_group)

        # 接口配置
        interface_group = QGroupBox("接口")
        interface_group.setContentsMargins(8, 12, 8, 8)
        self.interface_layout = QVBoxLayout(interface_group)
        self.interface_layout.setSpacing(8)

        self.interface_list = QListWidget()
        self.interface_list.setFixedHeight(120)  # 固定高度

        interface_btn_layout = QHBoxLayout()
        interface_btn_layout.setSpacing(8)

        self.edit_interface_btn = QPushButton("编辑")
        self.edit_interface_btn.clicked.connect(self.edit_interface)
        self.edit_interface_btn.setFixedWidth(80)

        self.view_interface_btn = QPushButton("查看")  # 新增查看按钮
        self.view_interface_btn.clicked.connect(self.view_interface)
        self.view_interface_btn.setFixedWidth(80)

        interface_btn_layout.addWidget(self.edit_interface_btn)
        interface_btn_layout.addWidget(self.view_interface_btn)  # 添加查看按钮
        interface_btn_layout.addStretch()

        self.interface_layout.addWidget(QLabel("提示：接口通过布局配置中的接口类型项自动生成和管理"))
        self.interface_layout.addWidget(self.interface_list)
        self.interface_layout.addLayout(interface_btn_layout)

        self.detail_layout.addWidget(interface_group)

        # SQL配置（新增）
        sql_group = QGroupBox("SQL配置")
        sql_group.setContentsMargins(8, 12, 8, 8)
        self.sql_layout = QVBoxLayout(sql_group)
        self.sql_layout.setSpacing(8)

        self.sql_list = QListWidget()
        self.sql_list.setFixedHeight(120)  # 固定高度

        sql_btn_layout = QHBoxLayout()
        sql_btn_layout.setSpacing(8)

        self.edit_sql_btn = QPushButton("编辑")
        self.edit_sql_btn.clicked.connect(self.edit_sql)
        self.edit_sql_btn.setFixedWidth(80)

        self.view_sql_btn = QPushButton("查看")
        self.view_sql_btn.clicked.connect(self.view_sql)
        self.view_sql_btn.setFixedWidth(80)

        sql_btn_layout.addWidget(self.edit_sql_btn)
        sql_btn_layout.addWidget(self.view_sql_btn)
        sql_btn_layout.addStretch()

        self.sql_layout.addWidget(QLabel("提示：SQL通过布局配置中的SQL类型项自动生成和管理"))
        self.sql_layout.addWidget(self.sql_list)
        self.sql_layout.addLayout(sql_btn_layout)

        self.detail_layout.addWidget(sql_group)

        self.detail_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area)

        return widget

    def load_products_config(self):
        """加载产品配置"""
        try:
            config_file = resource_path("config/products_config.json")
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.products_config = json.load(f)
            else:
                self.products_config = {
                    "products": {},
                    "default_product": "",
                    "locked_products": []
                }

            self.refresh_product_list()
            self.refresh_detail_product_combo()

            # 初始加载时检查默认产品的锁定状态
            default_product = self.products_config.get("default_product")
            if default_product:
                # 设置产品管理Tab的选择
                index = self.product_combo.findText(default_product)
                if index >= 0:
                    self.product_combo.setCurrentIndex(index)

                # 设置产品详情Tab的选择并检查锁定状态
                detail_index = self.detail_product_combo.findText(default_product)
                if detail_index >= 0:
                    self.detail_product_combo.setCurrentIndex(detail_index)
                    self.check_and_set_detail_tab_locked(default_product)

        except Exception as e:
            Toast.critical(self, "错误", f"加载产品配置失败: {str(e)}")
            self.products_config = {
                "products": {},
                "default_product": "",
                "locked_products": []
            }

    def refresh_product_list(self):
        """刷新产品列表"""
        self.product_combo.clear()
        if "products" in self.products_config and self.products_config["products"]:
            for product_name in self.products_config["products"].keys():
                # 检查产品是否被锁定
                is_locked = product_name in self.products_config.get("locked_products", [])
                display_name = product_name

                if product_name == self.products_config.get("default_product"):
                    self.product_combo.addItem(f"{display_name} (默认)", product_name)
                else:
                    self.product_combo.addItem(display_name, product_name)
        else:
            self.product_combo.addItem("无产品")

    def refresh_detail_product_combo(self):
        """刷新产品详情Tab中的产品下拉框"""
        self.detail_product_combo.clear()
        if "products" in self.products_config:
            for product_name in self.products_config["products"].keys():
                # 检查产品是否被锁定
                is_locked = product_name in self.products_config.get("locked_products", [])
                display_name = product_name
                self.detail_product_combo.addItem(display_name, product_name)

    def on_product_selected(self, product_name):
        """产品下拉框选中事件"""
        if not product_name or product_name == "无产品":
            self.product_name_edit.clear()
            self.product_config_path_edit.clear()
            self.product_locked_label.setText("未锁定")
            self.product_locked_label.setStyleSheet("color: green; font-weight: bold;")
            return

        # 从显示名称中提取真实产品名称（移除默认标志）
        real_product_name = product_name.replace(" (默认)", "") if " (默认)" in product_name else product_name

        config_path = self.products_config["products"].get(real_product_name, "")

        self.product_name_edit.setText(real_product_name)
        self.product_config_path_edit.setText(config_path)

        # 加载产品的锁定状态
        self.load_product_locked_status(real_product_name)

    def get_real_product_name(self, display_name):
        """从显示名称中提取真实产品名称"""
        # 移除锁标志
        name = display_name.replace('🔒', '').strip()
        # 移除默认标志
        if ' (默认)' in name:
            name = name.replace(' (默认)', '')
        return name

    def load_product_locked_status(self, product_name):
        """加载产品的锁定状态"""
        is_locked = product_name in self.products_config.get("locked_products", [])
        if is_locked:
            self.product_locked_label.setText("已锁定")
            self.product_locked_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.product_locked_label.setText("未锁定")
            self.product_locked_label.setStyleSheet("color: green; font-weight: bold;")

    def on_locked_changed(self, state):
        """锁定状态改变事件"""
        current_text = self.product_combo.currentText()
        if not current_text or current_text == "无产品":
            return

        product_name = self.get_real_product_name(current_text)
        locked = (state == Qt.Checked)

        # 更新锁定状态
        self.update_product_locked_status(product_name, locked)

        # 刷新显示
        self.refresh_product_list()
        self.refresh_detail_product_combo()

        # 如果当前在详情Tab中选中的是这个产品，更新详情Tab的状态
        current_detail_product = self.detail_product_combo.currentText()
        if current_detail_product and self.get_real_product_name(current_detail_product) == product_name:
            self.update_detail_tab_enabled(not locked)

    def update_product_locked_status(self, product_name, locked):
        """更新产品锁定状态"""
        if "locked_products" not in self.products_config:
            self.products_config["locked_products"] = []

        if locked:
            # 添加到锁定列表
            if product_name not in self.products_config["locked_products"]:
                self.products_config["locked_products"].append(product_name)
        else:
            # 从锁定列表移除
            if product_name in self.products_config["locked_products"]:
                self.products_config["locked_products"].remove(product_name)

        # 更新产品管理Tab的锁定状态显示
        self.load_product_locked_status(product_name)

        # 更新产品详情Tab的锁定状态
        if self.detail_product_combo.currentText() == product_name:
            self.check_and_set_detail_tab_locked(product_name)

    def save_product_locked_status(self, product_name, locked):
        """保存产品锁定状态"""
        try:
            config_path = self.products_config["products"].get(product_name)
            if not config_path:
                return False

            product_config_file = resource_path(f"{config_path}")

            # 加载现有配置
            if os.path.exists(product_config_file):
                with open(product_config_file, 'r', encoding='utf-8') as f:
                    product_config = json.load(f)
            else:
                product_config = {}

            # 更新锁定状态
            product_config["locked"] = locked

            # 保存配置
            with open(product_config_file, 'w', encoding='utf-8') as f:
                json.dump(product_config, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            Toast.critical(self, "错误", f"保存锁定状态失败: {str(e)}")
            return False

    def update_detail_tab_enabled(self, enabled):
        """更新产品详情Tab的启用状态"""
        # 启用或禁用各个配置组，但保持滚动区域始终可用
        self.detail_enable_encryption.setEnabled(enabled)
        self.detail_encrypt_url_edit.setEnabled(enabled)
        self.detail_decrypt_url_edit.setEnabled(enabled)

        # 定时任务相关控件
        self.add_schedule_btn.setEnabled(enabled)
        self.edit_schedule_btn.setEnabled(enabled)
        self.remove_schedule_btn.setEnabled(enabled)
        self.view_schedule_btn.setEnabled(True)  # 查看按钮始终可用

        # 布局配置相关控件
        self.add_layout_item_btn.setEnabled(enabled)
        self.edit_layout_item_btn.setEnabled(enabled)
        self.remove_layout_item_btn.setEnabled(enabled)
        self.view_layout_item_btn.setEnabled(True)  # 查看按钮始终可用

        # 设置布局列表的拖拽模式
        if enabled:
            self.layout_list.setDragDropMode(QListWidget.InternalMove)
        else:
            self.layout_list.setDragDropMode(QListWidget.NoDragDrop)

        # 接口配置相关控件
        self.edit_interface_btn.setEnabled(enabled)
        self.view_interface_btn.setEnabled(True)  # 查看按钮始终可用

        # SQL配置相关控件
        self.edit_sql_btn.setEnabled(enabled)
        self.view_sql_btn.setEnabled(True)  # 查看按钮始终可用

        # 特别注意：产品下拉框和滚动区域始终保持可用
        self.detail_product_combo.setEnabled(True)
        self.scroll_area.setEnabled(True)  # 确保滚动区域始终可用

        # 确保列表控件始终可以滚动查看内容
        self.schedule_list.setEnabled(True)  # 允许滚动查看
        self.layout_list.setEnabled(True)  # 允许滚动查看
        self.interface_list.setEnabled(True)  # 允许滚动查看

        # 当禁用时，设置列表的选择模式为只读，但允许滚动
        if not enabled:
            self.schedule_list.setSelectionMode(QListWidget.NoSelection)
            self.layout_list.setSelectionMode(QListWidget.NoSelection)
            self.interface_list.setSelectionMode(QListWidget.NoSelection)
        else:
            self.schedule_list.setSelectionMode(QListWidget.SingleSelection)
            self.layout_list.setSelectionMode(QListWidget.SingleSelection)
            self.interface_list.setSelectionMode(QListWidget.SingleSelection)

    def set_widgets_enabled(self, widget, enabled, exclude_widgets=None):
        """递归设置widget及其所有子控件的启用状态"""
        if exclude_widgets is None:
            exclude_widgets = []

        if widget in exclude_widgets:
            return

        if hasattr(widget, 'setEnabled'):
            widget.setEnabled(enabled)

        # 递归处理子控件
        for child in widget.children():
            self.set_widgets_enabled(child, enabled, exclude_widgets)

    def on_detail_product_changed(self, product_name):
        """产品详情Tab中的产品选择变化"""
        if not product_name:
            return

        real_product_name = product_name

        # 加载产品详情配置
        self.load_product_detail_config(real_product_name)

        # 检查并设置锁定状态
        self.check_and_set_detail_tab_locked(real_product_name)

    def check_and_set_detail_tab_locked(self, product_name):
        """检查并设置产品详情Tab的锁定状态"""
        is_locked = product_name in self.products_config.get("locked_products", [])

        # 更新锁定提示
        if is_locked:
            self.detail_locked_label.setText("🔒 产品已锁定，不可编辑")
            self.detail_locked_label.setVisible(True)
        else:
            self.detail_locked_label.setText("")
            self.detail_locked_label.setVisible(False)

        # 更新详情Tab的启用状态（但保持产品下拉框可用）
        self.update_detail_tab_enabled(not is_locked)

    def load_product_detail_config(self, product_name):
        """加载产品详情配置"""
        try:
            config_path = self.products_config["products"].get(product_name)
            if not config_path:
                return

            product_config_file = resource_path(f"{config_path}")
            if os.path.exists(product_config_file):
                with open(product_config_file, 'r', encoding='utf-8') as f:
                    product_config = json.load(f)

                # 更新加解密配置
                self.detail_enable_encryption.setChecked(
                    product_config.get("enable_encryption", False)
                )
                self.detail_encrypt_url_edit.setText(
                    product_config.get("encrypt_url", "")
                )
                self.detail_decrypt_url_edit.setText(
                    product_config.get("decrypt_url", "")
                )

                # 更新定时任务
                self.schedule_list.clear()
                for task in product_config.get("schedule_tasks", []):
                    item_text = f"{task['name']} (ID: {task['id']}, Group: {task.get('jobGroup', 'DEFAULT')})"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, task)  # 保存完整任务数据
                    self.schedule_list.addItem(item)

                # 更新布局配置
                self.layout_list.clear()
                for item in product_config.get("layout", []):
                    item_type = item.get("type", "")
                    item_key = item.get("key", "")
                    item_label = item.get("label", "")
                    item_name = item.get("name", "")

                    # 获取show_in_ui字段，默认为True（展示）
                    show_in_ui = item.get("show_in_ui", True)

                    if item_type == "field":
                        display_text = f"字段: {item_label} ({item_key})"
                        if not show_in_ui:
                            display_text += " [隐藏]"
                    elif item_type == "combo":
                        display_text = f"下拉框: {item_label} ({item_key})"
                        if not show_in_ui:
                            display_text += " [隐藏]"
                    elif item_type == "interface":
                        display_text = f"接口: {item_name}"
                    elif item_type == "sql":
                        display_text = f"SQL: {item_name}"
                    elif item_type == "condition":
                        display_text = f"条件: {item_label} ({item_key})"
                        if not show_in_ui:
                            display_text += " [隐藏]"  # 为条件字段添加隐藏标记
                    elif item_type == "formula":
                        display_text = f"公式: {item_label} ({item_key})"
                        if not show_in_ui:
                            display_text += " [隐藏]"  # 为条件字段添加隐藏标记
                    else:
                        display_text = f"未知: {item}"

                    list_item = QListWidgetItem(display_text)
                    list_item.setData(Qt.UserRole, item)  # 保存完整布局数据
                    self.layout_list.addItem(list_item)

                # 更新接口配置
                self.interface_list.clear()
                for interface_name, interface_config in product_config.get("interfaces", {}).items():
                    item = QListWidgetItem(interface_name)
                    item.setData(Qt.UserRole, interface_config)  # 保存完整接口数据
                    self.interface_list.addItem(item)

                # 更新SQL配置
                self.sql_list.clear()
                for sql_name, sql_config in product_config.get("sqls", {}).items():
                    item = QListWidgetItem(sql_name)
                    item.setData(Qt.UserRole, sql_config)
                    self.sql_list.addItem(item)

        except Exception as e:
            Toast.critical(self, "错误", f"加载产品详情配置失败: {str(e)}")

    def add_product(self):
        """新增产品 - 弹窗新增"""
        dialog = QDialog(self)
        dialog.setWindowTitle("新增产品")
        dialog.setModal(True)
        dialog.setFixedSize(350, 200)  # 保持原有大小
        layout = QVBoxLayout(dialog)  # 改为垂直布局
        layout.setSpacing(10)  # 添加间距
        layout.setContentsMargins(15, 15, 15, 15)  # 添加边距

        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(8)  # 设置紧凑间距
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(10)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("请输入产品名称")
        name_edit.setFixedWidth(200)  # 固定宽度

        is_default_checkbox = QCheckBox("设为默认产品")
        locked_checkbox = QCheckBox("锁定配置")

        form_layout.addRow("产品名称:", name_edit)
        form_layout.addRow("", is_default_checkbox)
        form_layout.addRow("", locked_checkbox)

        layout.addLayout(form_layout)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)

        def on_ok():
            name = name_edit.text().strip()

            if not name:
                Toast.warning(dialog, "警告", "请输入产品名称")
                return

            if name in self.products_config["products"]:
                Toast.warning(dialog, "警告", "产品名称已存在")
                return

            # 检查是否已存在默认产品
            if is_default_checkbox.isChecked() and self.products_config.get("default_product"):
                Toast.warning(
                    dialog, "无法设置默认产品",
                    f"已存在默认产品 '{self.products_config['default_product']}'，无法设置新的默认产品。\n请先取消现有产品的默认设置，再设置新的默认产品。"
                )
                return

            # 自动生成配置文件路径
            config_path = f"config/products/{name}.json"

            # 确保目录存在
            try:
                config_dir = resource_path("config/products")
                os.makedirs(config_dir, exist_ok=True)
            except Exception as e:
                Toast.critical(dialog, "错误", f"创建配置目录失败: {str(e)}")
                return

            # 添加到产品配置
            self.products_config["products"][name] = config_path

            # 设置锁定状态
            if locked_checkbox.isChecked():
                if "locked_products" not in self.products_config:
                    self.products_config["locked_products"] = []
                self.products_config["locked_products"].append(name)

            # 设置默认产品
            if is_default_checkbox.isChecked():
                self.products_config["default_product"] = name

            self.refresh_product_list()
            self.refresh_detail_product_combo()

            # 创建默认的产品配置文件
            if self.create_default_product_config(name, config_path):
                dialog.accept()
                Toast.information(self, "成功", f"产品 '{name}' 创建成功")

                # 设置新创建的产品为当前选择
                index = self.product_combo.findText(name)
                if index >= 0:
                    self.product_combo.setCurrentIndex(index)

                detail_index = self.detail_product_combo.findText(name)
                if detail_index >= 0:
                    self.detail_product_combo.setCurrentIndex(detail_index)
            else:
                # 如果创建配置文件失败，回滚产品配置
                del self.products_config["products"][name]
                if name in self.products_config.get("locked_products", []):
                    self.products_config["locked_products"].remove(name)
                if self.products_config.get("default_product") == name:
                    self.products_config["default_product"] = ""
                self.refresh_product_list()
                self.refresh_detail_product_combo()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addStretch()  # 添加拉伸，使按钮靠右
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        dialog.exec_()

    def edit_product(self):
        """编辑产品 - 弹窗编辑"""
        try:
            current_text = self.product_combo.currentText()
            if not current_text or current_text == "无产品":
                Toast.warning(self, "警告", "请先选择要编辑的产品")
                return

            # 获取真实产品名称
            old_name = current_text.replace(" (默认)", "") if " (默认)" in current_text else current_text

            # 获取当前锁定状态
            current_locked = old_name in self.products_config.get("locked_products", [])

            # 创建编辑对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑产品")
            dialog.setModal(True)
            dialog.setFixedSize(350, 200)
            layout = QVBoxLayout(dialog)  # 改为垂直布局
            layout.setSpacing(10)
            layout.setContentsMargins(15, 15, 15, 15)

            # 创建表单布局
            form_layout = QFormLayout()
            form_layout.setSpacing(8)
            form_layout.setVerticalSpacing(8)
            form_layout.setHorizontalSpacing(10)

            name_edit = QLineEdit()
            name_edit.setText(old_name)
            name_edit.setFixedWidth(200)

            is_default_checkbox = QCheckBox("设为默认产品")
            is_default_checkbox.setChecked(old_name == self.products_config.get("default_product"))

            locked_checkbox = QCheckBox("锁定配置")
            locked_checkbox.setChecked(current_locked)

            form_layout.addRow("产品名称:", name_edit)
            form_layout.addRow("", is_default_checkbox)
            form_layout.addRow("", locked_checkbox)

            layout.addLayout(form_layout)

            # 按钮布局
            button_layout = QHBoxLayout()
            button_layout.setSpacing(10)

            ok_btn = QPushButton("确定")
            ok_btn.setFixedWidth(80)

            cancel_btn = QPushButton("取消")
            cancel_btn.setFixedWidth(80)

            def on_ok():
                new_name = name_edit.text().strip()

                if not new_name:
                    Toast.warning(dialog, "警告", "请输入产品名称")
                    return

                # 如果产品名称发生变化
                if old_name != new_name:
                    if new_name in self.products_config["products"]:
                        Toast.warning(dialog, "警告", "产品名称已存在")
                        return

                # 检查是否尝试设置新的默认产品但已存在默认产品
                if (is_default_checkbox.isChecked() and
                        self.products_config.get("default_product") and
                        self.products_config["default_product"] != old_name):
                    Toast.warning(
                        dialog, "无法设置默认产品",
                        f"已存在默认产品 '{self.products_config['default_product']}'，无法设置新的默认产品。\n请先取消现有产品的默认设置，再设置新的默认产品。"
                    )
                    return

                # 更新锁定状态
                if current_locked != locked_checkbox.isChecked():
                    self.update_product_locked_status(old_name, locked_checkbox.isChecked())

                # 如果产品名称发生变化
                if old_name != new_name:
                    # 更新产品名称
                    self.products_config["products"][new_name] = self.products_config["products"][old_name]

                    # 重命名配置文件
                    try:
                        old_config_path = self.products_config["products"][old_name]
                        old_config_file = resource_path(f"{old_config_path}")
                        new_config_file = resource_path(f"config/products/{new_name}.json")

                        if os.path.exists(old_config_file):
                            # 确保新目录存在
                            os.makedirs(os.path.dirname(new_config_file), exist_ok=True)
                            os.rename(old_config_file, new_config_file)

                        # 更新配置文件路径
                        self.products_config["products"][new_name] = f"config/products/{new_name}.json"

                        # 更新锁定列表中的名称
                        if old_name in self.products_config.get("locked_products", []):
                            self.products_config["locked_products"].remove(old_name)
                            self.products_config["locked_products"].append(new_name)

                        del self.products_config["products"][old_name]

                        # 更新默认产品
                        if self.products_config.get("default_product") == old_name:
                            self.products_config["default_product"] = new_name

                    except Exception as e:
                        Toast.critical(dialog, "错误", f"重命名配置文件失败: {str(e)}")
                        return

                # 更新默认产品
                if is_default_checkbox.isChecked():
                    self.products_config["default_product"] = new_name if old_name != new_name else old_name
                elif self.products_config.get("default_product") == (new_name if old_name != new_name else old_name):
                    # 如果取消默认，清空默认产品
                    self.products_config["default_product"] = ""

                self.refresh_product_list()
                self.refresh_detail_product_combo()

                # 更新产品详情Tab中的下拉框选择
                final_name = new_name if old_name != new_name else old_name
                index = self.detail_product_combo.findText(final_name)
                if index >= 0:
                    self.detail_product_combo.setCurrentIndex(index)

                dialog.accept()
                Toast.information(self, "成功", "产品信息已更新")

            ok_btn.clicked.connect(on_ok)
            cancel_btn.clicked.connect(dialog.reject)

            button_layout.addStretch()  # 添加拉伸，使按钮靠右
            button_layout.addWidget(ok_btn)
            button_layout.addWidget(cancel_btn)

            layout.addLayout(button_layout)

            dialog.exec_()

        except Exception as e:
            Toast.critical(self, "错误", f"编辑产品失败: {str(e)}")

    def delete_product(self):
        """删除产品 - 弹窗二次确认"""
        try:
            current_text = self.product_combo.currentText()
            if not current_text or current_text == "无产品":
                Toast.warning(self, "警告", "请先选择要删除的产品")
                return

            product_name = current_text.replace(" (默认)", "")

            # 对于确认对话框，暂时保留QMessageBox.question，因为Toast没有确认对话框功能
            reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除产品 '{product_name}' 吗？\n此操作将删除产品配置文件，且不可恢复！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # 默认选择"No"更安全
        )

            if reply == QMessageBox.Yes:
                # 删除产品配置文件
                config_path = self.products_config["products"][product_name]
                product_config_file = resource_path(f"{config_path}")
                if os.path.exists(product_config_file):
                    try:
                        os.remove(product_config_file)
                    except Exception as e:
                        Toast.critical(self, "错误", f"删除配置文件失败: {str(e)}")
                        return

                # 从配置中删除
                del self.products_config["products"][product_name]

                # 如果删除的是默认产品，清空默认产品设置
                if self.products_config.get("default_product") == product_name:
                    self.products_config["default_product"] = ""

                self.refresh_product_list()
                self.refresh_detail_product_combo()

                # 检查是否还有产品
                if self.product_combo.count() > 0:
                    # 还有产品，自动选择第一个
                    self.product_combo.setCurrentIndex(0)
                else:
                    # 没有产品了，清空编辑框
                    self.product_name_edit.clear()
                    self.product_config_path_edit.clear()

                Toast.information(self, "成功", f"产品 '{product_name}' 已删除")

        except Exception as e:
            Toast.critical(self, "错误", f"删除产品失败: {str(e)}")

    def create_default_product_config(self, product_name, config_path, locked=False):
        """创建默认产品配置文件"""
        default_config = {
            "locked": locked,  # 新增锁定状态
            "enable_encryption": False,
            "encrypt_url": "",
            "decrypt_url": "",
            "schedule_tasks": [],
            "layout": [
                {
                    "type": "field",
                    "key": "name",
                    "label": "姓名",
                    "priority": 1,
                    "default": ""
                },
                {
                    "type": "field",
                    "key": "id_card",
                    "label": "身份证号",
                    "priority": 2,
                    "default": ""
                },
                {
                    "type": "interface",
                    "name": "默认接口",
                    "priority": 3
                }
            ],
            "interfaces": {
                "默认接口": {
                    "url": "http://api.example.com/default",
                    "method": "POST",
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body_template": {}
                }
            }
        }

        try:
            product_config_file = resource_path(f"{config_path}")

            # 确保目录存在
            os.makedirs(os.path.dirname(product_config_file), exist_ok=True)

            with open(product_config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            Toast.critical(self, "错误", f"创建产品配置文件失败: {str(e)}")
            return False

    def add_schedule_task(self):
        """添加定时任务 - 优化样式"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加定时任务")
        dialog.setModal(True)
        dialog.setFixedSize(350, 250)  # 稍微增加宽度以适应紧凑布局
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 创建表单布局 - 使用紧凑设置
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(10)

        # 任务ID
        task_id_edit = QLineEdit()
        task_id_edit.setPlaceholderText("请输入任务ID")
        task_id_edit.setFixedWidth(250)
        form_layout.addRow("任务ID:", task_id_edit)

        # 任务名称
        task_name_edit = QLineEdit()
        task_name_edit.setPlaceholderText("请输入任务名称")
        task_name_edit.setFixedWidth(250)
        form_layout.addRow("任务名称:", task_name_edit)

        # 任务组
        task_group_edit = QLineEdit()
        task_group_edit.setText("DEFAULT")
        task_group_edit.setEnabled(False)  # 任务组不可编辑
        task_group_edit.setFixedWidth(250)
        task_group_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")  # 灰色背景表示禁用
        form_layout.addRow("任务组:", task_group_edit)

        layout.addLayout(form_layout)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)

        def on_ok():
            task_id = task_id_edit.text().strip()
            task_name = task_name_edit.text().strip()
            task_group = task_group_edit.text().strip()

            if not task_id:
                Toast.warning(dialog, "警告", "请输入任务ID")
                return

            if not task_name:
                Toast.warning(dialog, "警告", "请输入任务名称")
                return

            if not task_group:
                task_group = "DEFAULT"

            # 检查任务ID是否已存在
            for i in range(self.schedule_list.count()):
                item = self.schedule_list.item(i)
                task_data = item.data(Qt.UserRole)
                if task_data and str(task_data["id"]) == task_id:
                    Toast.warning(dialog, "警告", "任务ID已存在")
                    return

            # 创建任务数据
            task_data = {
                "id": task_id,
                "name": task_name,
                "jobGroup": task_group
            }

            # 添加到列表
            item_text = f"{task_name} (ID: {task_id}, Group: {task_group})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, task_data)
            self.schedule_list.addItem(item)

            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.exec_()

    def edit_schedule_task(self):
        """编辑定时任务 - 优化样式"""
        current_row = self.schedule_list.currentRow()
        if current_row < 0:
            Toast.warning(self, "警告", "请先选择要编辑的定时任务")
            return

        current_item = self.schedule_list.item(current_row)
        task_data = current_item.data(Qt.UserRole)

        if not task_data:
            Toast.warning(self, "警告", "选中的定时任务数据格式错误")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("编辑定时任务")
        dialog.setModal(True)
        dialog.setFixedSize(350, 250)  # 与添加任务弹窗保持一致
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 创建表单布局 - 使用紧凑设置
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(10)

        # 任务ID
        task_id_edit = QLineEdit()
        task_id_edit.setText(str(task_data["id"]))
        task_id_edit.setFixedWidth(250)
        form_layout.addRow("任务ID:", task_id_edit)

        # 任务名称
        task_name_edit = QLineEdit()
        task_name_edit.setText(task_data["name"])
        task_name_edit.setFixedWidth(250)
        form_layout.addRow("任务名称:", task_name_edit)

        # 任务组
        task_group_edit = QLineEdit()
        task_group_edit.setText(task_data.get("jobGroup", "DEFAULT"))
        task_group_edit.setEnabled(False)  # 任务组不可编辑
        task_group_edit.setFixedWidth(250)
        task_group_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")  # 灰色背景表示禁用
        form_layout.addRow("任务组:", task_group_edit)

        layout.addLayout(form_layout)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)

        def on_ok():
            task_id = task_id_edit.text().strip()
            task_name = task_name_edit.text().strip()
            task_group = task_group_edit.text().strip()

            if not task_id:
                Toast.warning(dialog, "警告", "请输入任务ID")
                return

            if not task_name:
                Toast.warning(dialog, "警告", "请输入任务名称")
                return

            if not task_group:
                task_group = "DEFAULT"

            # 检查任务ID是否已存在（排除当前编辑的任务）
            for i in range(self.schedule_list.count()):
                if i == current_row:
                    continue
                item = self.schedule_list.item(i)
                existing_task_data = item.data(Qt.UserRole)
                if existing_task_data and str(existing_task_data["id"]) == task_id:
                    Toast.warning(dialog, "警告", "任务ID已存在")
                    return

            # 更新列表显示
            item_text = f"{task_name} (ID: {task_id}, Group: {task_group})"
            current_item.setText(item_text)

            # 更新任务数据
            current_item.setData(Qt.UserRole, {
                "id": task_id,
                "name": task_name,
                "jobGroup": task_group
            })

            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.exec_()

    def remove_schedule_task(self):
        """删除定时任务"""
        current_row = self.schedule_list.currentRow()
        if current_row < 0:
            Toast.warning(self, "警告", "请先选择要删除的定时任务")
            return

        current_item = self.schedule_list.item(current_row)
        task_data = current_item.data(Qt.UserRole)

        if not task_data:
            Toast.warning(self, "警告", "选中的定时任务数据格式错误")
            return

        task_name = task_data.get("name", "未知任务")
        task_id = task_data.get("id", "未知ID")

        # 对于确认对话框，暂时保留QMessageBox.question，因为Toast没有确认对话框功能
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除定时任务 '{task_name}' (ID: {task_id}) 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.schedule_list.takeItem(current_row)

    def view_schedule_task(self):
        """查看定时任务详情"""
        current_row = self.schedule_list.currentRow()
        if current_row < 0:
            Toast.warning(self, "警告", "请先选择要查看的定时任务")
            return

        current_item = self.schedule_list.item(current_row)
        task_data = current_item.data(Qt.UserRole)

        if not task_data:
            Toast.warning(self, "警告", "选中的定时任务数据格式错误")
            return

        # 使用编辑任务的对话框，但设置为只读模式
        dialog = QDialog(self)
        dialog.setWindowTitle("查看定时任务")
        dialog.setModal(True)
        dialog.setFixedSize(350, 250)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(10)

        # 任务ID（只读）
        task_id_edit = QLineEdit()
        task_id_edit.setText(str(task_data["id"]))
        task_id_edit.setReadOnly(True)
        task_id_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")
        task_id_edit.setFixedWidth(250)
        form_layout.addRow("任务ID:", task_id_edit)

        # 任务名称（只读）
        task_name_edit = QLineEdit()
        task_name_edit.setText(task_data["name"])
        task_name_edit.setReadOnly(True)
        task_name_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")
        task_name_edit.setFixedWidth(250)
        form_layout.addRow("任务名称:", task_name_edit)

        # 任务组（只读）
        task_group_edit = QLineEdit()
        task_group_edit.setText(task_data.get("jobGroup", "DEFAULT"))
        task_group_edit.setReadOnly(True)
        task_group_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")
        task_group_edit.setFixedWidth(250)
        form_layout.addRow("任务组:", task_group_edit)

        layout.addLayout(form_layout)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(dialog.accept)

        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        dialog.exec_()

    def add_layout_item(self):
        """添加布局项 - 优化版，样式与编辑项统一"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加布局项")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # 类型选择 - 紧凑布局
        type_layout = QHBoxLayout()
        type_layout.setSpacing(5)
        type_label = QLabel("类型:")
        type_label.setFixedWidth(30)
        type_layout.addWidget(type_label)

        self.add_type_combo = NoWheelComboBox()
        # 使用中文显示，但存储英文值
        self.add_type_combo.addItem("字段", "field")
        self.add_type_combo.addItem("下拉框", "combo")
        self.add_type_combo.addItem("接口", "interface")
        self.add_type_combo.addItem("SQL", "sql")
        self.add_type_combo.addItem("条件", "condition")
        self.add_type_combo.addItem("公式", "formula")  # 新增公式类型
        self.add_type_combo.setFixedWidth(120)
        type_layout.addWidget(self.add_type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        # 现在可以安全地获取初始类型并设置对话框大小
        initial_type = self.add_type_combo.currentData()
        self._set_dialog_size_by_type(dialog, initial_type)

        # 连接信号（必须在设置大小之后）
        self.add_type_combo.currentTextChanged.connect(self.on_add_type_changed)

        # 创建表单布局 - 使用紧凑的设置
        form_layout = QFormLayout()
        form_layout.setSpacing(6)  # 减少行间距
        form_layout.setVerticalSpacing(6)
        form_layout.setHorizontalSpacing(8)

        # 键 - 字段、下拉框、条件和公式显示
        self.add_key_label = QLabel("键:")
        self.add_key_edit = QLineEdit()
        self.add_key_edit.setPlaceholderText("字段键名")
        self.add_key_edit.setFixedWidth(250)
        form_layout.addRow(self.add_key_label, self.add_key_edit)

        # 标签 - 字段、下拉框、条件和公式显示
        self.add_label_label = QLabel("标签:")
        self.add_label_edit = QLineEdit()
        self.add_label_edit.setPlaceholderText("显示标签")
        self.add_label_edit.setFixedWidth(250)
        form_layout.addRow(self.add_label_label, self.add_label_edit)

        # 接口名称 - 仅接口显示
        self.add_interface_name_label = QLabel("接口名称:")
        self.add_interface_name_edit = QLineEdit()
        self.add_interface_name_edit.setPlaceholderText("接口名称")
        self.add_interface_name_edit.setFixedWidth(250)
        self.add_interface_name_label.setVisible(False)
        self.add_interface_name_edit.setVisible(False)
        form_layout.addRow(self.add_interface_name_label, self.add_interface_name_edit)

        # SQL名称 - 仅SQL显示
        self.add_sql_name_label = QLabel("SQL名称:")
        self.add_sql_name_edit = QLineEdit()
        self.add_sql_name_edit.setPlaceholderText("SQL名称")
        self.add_sql_name_edit.setFixedWidth(250)
        self.add_sql_name_label.setVisible(False)
        self.add_sql_name_edit.setVisible(False)
        form_layout.addRow(self.add_sql_name_label, self.add_sql_name_edit)

        # 条件字段选择 - 仅条件类型显示
        self.add_condition_field_label = QLabel("条件字段:")
        self.add_condition_field_combo = NoWheelComboBox()
        self.add_condition_field_combo.setFixedWidth(250)
        self.add_condition_field_combo.currentIndexChanged.connect(self.on_condition_field_changed)
        self.add_condition_field_label.setVisible(False)
        self.add_condition_field_combo.setVisible(False)
        form_layout.addRow(self.add_condition_field_label, self.add_condition_field_combo)

        # 数据类型 - 字段和下拉框显示
        self.add_data_type_label = QLabel("数据类型:")
        self.add_data_type_combo = NoWheelComboBox()
        self.add_data_type_combo.addItems(["string", "int", "float", "bool"])
        self.add_data_type_combo.setCurrentText("string")
        self.add_data_type_combo.setFixedWidth(120)
        form_layout.addRow(self.add_data_type_label, self.add_data_type_combo)

        # 默认值 - 字段和下拉框显示
        self.add_default_label = QLabel("默认值:")
        self.add_default_edit = QLineEdit()
        self.add_default_edit.setPlaceholderText("默认值")
        self.add_default_edit.setFixedWidth(250)
        form_layout.addRow(self.add_default_label, self.add_default_edit)

        # 是否展示到前端 - 字段、下拉框和公式显示
        self.add_show_in_ui_label = QLabel("展示到前端:")
        self.add_show_in_ui_checkbox = QCheckBox()
        self.add_show_in_ui_checkbox.setChecked(True)  # 默认勾选
        self.add_show_in_ui_checkbox.setToolTip("勾选时在前端显示该字段，不勾选时仅作为变量传递给请求参数")
        form_layout.addRow(self.add_show_in_ui_label, self.add_show_in_ui_checkbox)

        # 新增：公式类型选择 - 仅公式类型显示
        self.add_formula_type_label = QLabel("公式类型:")
        self.add_formula_type_combo = NoWheelComboBox()
        self.add_formula_type_combo.addItem("数值", "numeric")
        self.add_formula_type_combo.addItem("日期", "date")
        self.add_formula_type_combo.setFixedWidth(100)  # 减小宽度
        self.add_formula_type_combo.setVisible(False)
        form_layout.addRow(self.add_formula_type_label, self.add_formula_type_combo)

        # 新增：公式输入框 - 仅公式类型显示
        self.add_formula_label = QLabel("公式:")
        self.add_formula_edit = QTextEdit()
        self.add_formula_edit.setPlaceholderText("请输入公式表达式，例如: {field1} + {field2} * 0.06")
        self.add_formula_edit.setFixedHeight(80)
        self.add_formula_edit.setVisible(False)
        form_layout.addRow(self.add_formula_label, self.add_formula_edit)

        layout.addLayout(form_layout)

        # 下拉框枚举配置 - 仅下拉框显示
        self.add_options_group = QGroupBox("下拉框选项配置")
        self.add_options_group.setContentsMargins(8, 8, 8, 8)
        self.add_options_group.setVisible(False)
        options_layout = QVBoxLayout(self.add_options_group)
        options_layout.setSpacing(6)

        # 枚举表格
        self.add_options_table = QTableWidget()
        self.add_options_table.setColumnCount(2)
        self.add_options_table.setHorizontalHeaderLabels(["显示文本", "值"])
        self.add_options_table.horizontalHeader().setStretchLastSection(True)
        self.add_options_table.setMaximumHeight(180)  # 限制表格高度

        # 设置列宽
        self.add_options_table.setColumnWidth(0, 150)
        self.add_options_table.setColumnWidth(1, 150)
        options_layout.addWidget(self.add_options_table)

        # 枚举操作按钮
        options_btn_layout = QHBoxLayout()
        options_btn_layout.setSpacing(6)

        self.add_option_btn = QPushButton("添加")
        self.add_option_btn.clicked.connect(self.add_option_item)
        self.add_option_btn.setFixedWidth(70)

        self.edit_option_btn = QPushButton("编辑")
        self.edit_option_btn.clicked.connect(self.edit_option_item)
        self.edit_option_btn.setFixedWidth(70)

        self.remove_option_btn = QPushButton("删除")
        self.remove_option_btn.clicked.connect(self.remove_option_item)
        self.remove_option_btn.setFixedWidth(70)

        options_btn_layout.addWidget(self.add_option_btn)
        options_btn_layout.addWidget(self.edit_option_btn)
        options_btn_layout.addWidget(self.remove_option_btn)
        options_btn_layout.addStretch()

        options_layout.addLayout(options_btn_layout)
        layout.addWidget(self.add_options_group)

        # 条件映射配置 - 仅条件类型显示
        self.add_condition_mapping_group = QGroupBox("条件映射配置")
        self.add_condition_mapping_group.setContentsMargins(8, 8, 8, 8)
        self.add_condition_mapping_group.setVisible(False)
        condition_mapping_layout = QVBoxLayout(self.add_condition_mapping_group)
        condition_mapping_layout.setSpacing(6)

        self.add_condition_mapping_table = QTableWidget()
        self.add_condition_mapping_table.setColumnCount(2)
        self.add_condition_mapping_table.setHorizontalHeaderLabels(["条件值", "变量字段"])
        self.add_condition_mapping_table.horizontalHeader().setStretchLastSection(True)
        self.add_condition_mapping_table.setMaximumHeight(180)
        self.add_condition_mapping_table.setColumnWidth(0, 150)
        self.add_condition_mapping_table.setColumnWidth(1, 150)
        condition_mapping_layout.addWidget(self.add_condition_mapping_table)

        layout.addWidget(self.add_condition_mapping_group)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)

        def on_ok():
            # 获取类型值（使用itemData获取存储的英文值）
            item_type = self.add_type_combo.currentData()
            key = self.add_key_edit.text().strip()
            label = self.add_label_edit.text().strip()
            interface_name = self.add_interface_name_edit.text().strip()
            sql_name = self.add_sql_name_edit.text().strip()
            data_type = self.add_data_type_combo.currentText() if item_type in ["field", "combo"] else "string"
            default_value = self.add_default_edit.text().strip()
            show_in_ui = self.add_show_in_ui_checkbox.isChecked()
            formula_type = self.add_formula_type_combo.currentData() if item_type == "formula" else ""
            formula = self.add_formula_edit.toPlainText().strip() if item_type == "formula" else ""

            # 验证必填字段
            if item_type in ["field", "combo", "condition", "formula"]:  # 添加公式类型
                if not key:
                    Toast.warning(dialog, "警告", "请输入键")
                    return
                if not label:
                    Toast.warning(dialog, "警告", "请输入标签")
                    return
            elif item_type == "interface":
                if not interface_name:
                    Toast.warning(dialog, "警告", "请输入接口名称")
                    return

                # 检查接口名称是否已存在
                for i in range(self.interface_list.count()):
                    if self.interface_list.item(i).text() == interface_name:
                        Toast.warning(dialog, "警告", "接口名称已存在")
                        return
            elif item_type == "sql":  # 新增SQL类型验证
                if not sql_name:
                    Toast.warning(dialog, "警告", "请输入SQL名称")
                    return

                # 检查SQL名称是否已存在
                for i in range(self.sql_list.count()):
                    if self.sql_list.item(i).text() == sql_name:
                        Toast.warning(dialog, "警告", "SQL名称已存在")
                        return

            if item_type == "formula":  # 新增公式类型验证
                if not formula:
                    Toast.warning(dialog, "警告", "请输入公式")
                    return

                # 根据公式类型进行不同的验证
                if formula_type == "numeric":
                    # 数值公式验证：检查是否包含数字运算符号
                    if not any(op in formula for op in ['+', '-', '*', '/']):
                        Toast.warning(dialog, "警告", "数值公式应包含数学运算符（+、-、*、/）")
                        return
                elif formula_type == "date":
                    # 日期公式验证：检查是否包含日期运算
                    if not any(op in formula for op in ['-']):
                        Toast.warning(dialog, "警告", "日期公式应包含减法运算符（-）")
                        return

                # 验证公式语法（简单验证）
                try:
                    # 提取公式中的变量进行验证
                    dependencies = self.extract_formula_dependencies(formula)
                    if not dependencies:
                        Toast.warning(dialog, "警告", "公式中未包含任何变量")
                        return
                except Exception as e:
                    Toast.warning(dialog, "警告", f"公式格式错误: {str(e)}")
                    return

            # 构建布局项数据
            item_data = {
                "type": item_type,
                "priority": self.layout_list.count() + 1
            }

            if item_type == "field":
                item_data.update({
                    "key": key,
                    "label": label,
                    "data_type": data_type,
                    "default": default_value,
                    "show_in_ui": show_in_ui
                })
                display_text = f"字段: {label} ({key})"
                if not show_in_ui:
                    display_text += " [隐藏]"

            elif item_type == "combo":
                # 获取枚举选项
                options = []
                for row in range(self.add_options_table.rowCount()):
                    text_item = self.add_options_table.item(row, 0)
                    value_item = self.add_options_table.item(row, 1)
                    if text_item and value_item:
                        options.append({
                            "text": text_item.text(),
                            "value": value_item.text()
                        })

                if not options:
                    Toast.warning(dialog, "警告", "请至少添加一个下拉框选项")
                    return

                item_data.update({
                    "key": key,
                    "label": label,
                    "data_type": data_type,
                    "default": default_value,
                    "options": options,
                    "show_in_ui": show_in_ui
                })
                display_text = f"下拉框: {label} ({key})"
                if not show_in_ui:
                    display_text += " [隐藏]"

            elif item_type == "interface":
                item_data.update({
                    "name": interface_name
                })
                display_text = f"接口: {interface_name}"

                # 自动在接口配置中生成默认接口
                self.add_default_interface(interface_name)

            elif item_type == "sql":  # 新增SQL类型处理
                item_data.update({
                    "name": sql_name
                })
                display_text = f"SQL: {sql_name}"

                # 自动在SQL配置中生成默认SQL配置
                self.add_default_sql_config(sql_name)

            elif item_type == "condition":  # 新增条件类型处理
                # 获取条件字段
                condition_field_key = self.add_condition_field_combo.currentData()
                if not condition_field_key:
                    Toast.warning(dialog, "警告", "请选择条件字段")
                    return

                # 获取映射关系
                mappings = {}
                for row in range(self.add_condition_mapping_table.rowCount()):
                    value_item = self.add_condition_mapping_table.item(row, 0)
                    if not value_item:
                        continue
                    condition_value = value_item.data(Qt.UserRole)  # 获取原始值
                    combo = self.add_condition_mapping_table.cellWidget(row, 1)
                    variable_field_key = combo.currentData()
                    if condition_value and variable_field_key:
                        mappings[condition_value] = variable_field_key
                if not mappings:
                    Toast.warning(dialog, "警告", "请至少配置一个条件映射")
                    return
                item_data.update({
                    "key": key,
                    "label": label,
                    "condition_field": condition_field_key,
                    "mappings": mappings,
                    "show_in_ui": show_in_ui  # 新增展示到前端配置
                })
                display_text = f"条件: {label} ({key})"
                if not show_in_ui:
                    display_text += " [隐藏]"  # 添加隐藏标记

            elif item_type == "formula":  # 新增公式类型处理
                item_data.update({
                    "key": key,
                    "label": label,
                    "formula_type": formula_type,  # 新增公式类型
                    "formula": formula,
                    "show_in_ui": show_in_ui  # 确保这一行存在
                })
                display_text = f"公式: {label} ({key})"
                if not show_in_ui:
                    display_text += " [隐藏]"

            # 添加到列表
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, item_data)
            self.layout_list.addItem(item)

            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        # 保存对话框引用用于大小调整
        self._add_dialog = dialog

        # 初始化界面状态
        self.on_add_type_changed(self.add_type_combo.currentText())

        dialog.exec_()

        # 清理引用
        self._add_dialog = None

    def edit_layout_item(self):
        """编辑布局项 - 修复固定变量编辑问题"""
        current_row = self.layout_list.currentRow()
        if current_row < 0:
            Toast.warning(self, "警告", "请先选择要编辑的布局项")
            return

        current_item = self.layout_list.item(current_row)
        item_data = current_item.data(Qt.UserRole)

        if not item_data:
            Toast.warning(self, "警告", "选中的布局项数据格式错误")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("编辑布局项")
        dialog.setModal(True)

        # 根据类型设置弹窗大小--防止字段间距垂直拉伸
        item_type = item_data.get("type")
        if item_type == "combo" or item_type == "condition":
            dialog.setFixedSize(500, 650)  # 增加宽度和高度
        elif item_type == "formula":  # 不能与其他类型的公用，不然会被拉伸垂直间距
            dialog.setFixedSize(400, 400)
        elif item_type == "interface" or item_type == "sql":
            dialog.setFixedSize(400, 200)
        else:  # field
            dialog.setFixedSize(400, 350)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # 类型显示（不可编辑） - 紧凑布局
        type_layout = QHBoxLayout()
        type_layout.setSpacing(5)
        type_label = QLabel("类型:")
        type_label.setFixedWidth(30)
        type_layout.addWidget(type_label)

        # 将英文类型映射为中文显示
        type_mapping = {
            "field": "字段",
            "combo": "下拉框",
            "interface": "接口",
            "sql": "SQL",
            "condition": "条件",
            "formula": "公式"
        }

        type_value = QLabel(type_mapping.get(item_data.get("type", ""), item_data.get("type", "")))
        type_value.setStyleSheet("font-weight: bold; color: blue;")
        type_layout.addWidget(type_value)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(6)
        form_layout.setVerticalSpacing(6)
        form_layout.setHorizontalSpacing(8)

        # 根据类型显示不同的字段
        if item_type in ["field", "combo", "condition", "formula"]:  # 新增公式类型
            # 键
            key_edit = QLineEdit()
            key_edit.setText(item_data.get("key", ""))
            key_edit.setFixedWidth(250)
            form_layout.addRow("键:", key_edit)

            # 标签
            label_edit = QLineEdit()
            label_edit.setText(item_data.get("label", ""))
            label_edit.setFixedWidth(250)
            form_layout.addRow("标签:", label_edit)

        if item_type in ["field", "combo", "condition", "formula"]:  # 添加公式类型
            # 是否展示到前端
            show_in_ui_checkbox = QCheckBox()
            show_in_ui = item_data.get("show_in_ui", True)  # 默认True
            show_in_ui_checkbox.setChecked(show_in_ui)
            show_in_ui_checkbox.setToolTip("勾选时在前端显示该字段，不勾选时仅作为变量传递给请求参数")
            form_layout.addRow("展示到前端:", show_in_ui_checkbox)

        if item_type in ["field", "combo"]:
            # 数据类型
            data_type_combo = NoWheelComboBox()
            data_type_combo.addItems(["string", "int", "float", "bool"])
            data_type_combo.setCurrentText(item_data.get("data_type", "string"))
            data_type_combo.setFixedWidth(120)
            form_layout.addRow("数据类型:", data_type_combo)

            # 默认值
            default_edit = QLineEdit()
            default_edit.setText(item_data.get("default", ""))
            default_edit.setFixedWidth(250)
            form_layout.addRow("默认值:", default_edit)

        elif item_type == "interface":
            # 接口名称
            interface_name_edit = QLineEdit()
            interface_name_edit.setText(item_data.get("name", ""))
            interface_name_edit.setFixedWidth(250)
            form_layout.addRow("接口名称:", interface_name_edit)

        elif item_type == "sql":
            # SQL名称
            sql_name_edit = QLineEdit()
            sql_name_edit.setText(item_data.get("name", ""))
            sql_name_edit.setFixedWidth(250)
            form_layout.addRow("SQL名称:", sql_name_edit)

        elif item_type == "formula":  # 新增公式类型处理
            # 公式类型选择
            formula_type_combo = NoWheelComboBox()
            formula_type_combo.addItem("数值", "numeric")
            formula_type_combo.addItem("日期", "date")
            formula_type_combo.setFixedWidth(120)

            # 设置当前公式类型
            current_formula_type = item_data.get("formula_type", "numeric")
            index = formula_type_combo.findData(current_formula_type)
            if index >= 0:
                formula_type_combo.setCurrentIndex(index)

            form_layout.addRow("公式类型:", formula_type_combo)

            # 公式编辑框
            formula_label = QLabel("公式:")
            formula_edit = QTextEdit()
            formula_edit.setText(item_data.get("formula", ""))
            formula_edit.setPlaceholderText("请输入公式表达式，例如: {field1} + {field2} * 0.06")
            formula_edit.setFixedHeight(80)
            form_layout.addRow(formula_label, formula_edit)

        # 条件字段 - 仅条件类型显示
        condition_field_combo = None  # 提前声明变量
        if item_type == "condition":
            # 条件字段（可编辑）
            condition_field_combo = NoWheelComboBox()
            condition_field_combo.setFixedWidth(250)

            # 初始化条件字段下拉框
            combo_fields = []
            for i in range(self.layout_list.count()):
                item = self.layout_list.item(i)
                item_data_field = item.data(Qt.UserRole)
                if item_data_field and item_data_field.get("type") == "combo":
                    combo_fields.append({
                        "key": item_data_field.get("key"),
                        "label": item_data_field.get("label")
                    })

            # 添加到下拉框
            for field in combo_fields:
                display_text = f"{field['label']} ({field['key']})"
                condition_field_combo.addItem(display_text, field['key'])

            # 设置当前选中的条件字段
            current_condition_field = item_data.get("condition_field")
            if current_condition_field:
                index = condition_field_combo.findData(current_condition_field)
                if index >= 0:
                    condition_field_combo.setCurrentIndex(index)

            form_layout.addRow("条件字段:", condition_field_combo)

        layout.addLayout(form_layout)

        # 下拉框枚举配置 - 仅下拉框显示
        if item_type == "combo":
            options_group = QGroupBox("下拉框选项配置")
            options_group.setContentsMargins(8, 8, 8, 8)
            options_layout = QVBoxLayout(options_group)
            options_layout.setSpacing(6)

            # 枚举表格
            options_table = QTableWidget()
            options_table.setColumnCount(2)
            options_table.setHorizontalHeaderLabels(["显示文本", "值"])
            options_table.horizontalHeader().setStretchLastSection(True)
            options_table.setMaximumHeight(180)

            # 设置列宽
            options_table.setColumnWidth(0, 150)
            options_table.setColumnWidth(1, 150)

            # 填充现有选项
            options = item_data.get("options", [])
            for option in options:
                row = options_table.rowCount()
                options_table.insertRow(row)
                options_table.setItem(row, 0, QTableWidgetItem(option.get("text", "")))
                options_table.setItem(row, 1, QTableWidgetItem(option.get("value", "")))

            options_layout.addWidget(options_table)

            # 枚举操作按钮
            options_btn_layout = QHBoxLayout()
            options_btn_layout.setSpacing(6)

            add_option_btn = QPushButton("添加")
            add_option_btn.setFixedWidth(70)

            edit_option_btn = QPushButton("编辑")
            edit_option_btn.setFixedWidth(70)

            remove_option_btn = QPushButton("删除")
            remove_option_btn.setFixedWidth(70)

            def add_option():
                sub_dialog = QDialog(dialog)
                sub_dialog.setWindowTitle("添加选项")
                sub_dialog.setModal(True)
                sub_dialog.setFixedSize(300, 180)
                sub_layout = QFormLayout(sub_dialog)
                sub_layout.setSpacing(12)
                sub_layout.setContentsMargins(15, 15, 15, 15)

                text_edit = QLineEdit()
                text_edit.setPlaceholderText("显示文本")
                text_edit.setFixedWidth(200)
                sub_layout.addRow("显示文本:", text_edit)

                value_edit = QLineEdit()
                value_edit.setPlaceholderText("值")
                value_edit.setFixedWidth(200)
                sub_layout.addRow("值:", value_edit)

                # 添加一些弹性空间，使布局更舒适
                sub_layout.addItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))

                sub_button_layout = QHBoxLayout()
                sub_ok_btn = QPushButton("确定")
                sub_ok_btn.setFixedWidth(70)
                sub_cancel_btn = QPushButton("取消")
                sub_cancel_btn.setFixedWidth(70)

                def on_sub_ok():
                    text = text_edit.text().strip()
                    value = value_edit.text().strip()

                    if not text:
                        Toast.warning(sub_dialog, "警告", "请输入显示文本")
                        return
                    if not value:
                        Toast.warning(sub_dialog, "警告", "请输入值")
                        return

                    # 检查值是否重复
                    for row in range(options_table.rowCount()):
                        existing_value = options_table.item(row, 1).text()
                        if existing_value == value:
                            Toast.warning(sub_dialog, "警告", "值已存在")
                            return

                    # 添加到表格
                    row = options_table.rowCount()
                    options_table.insertRow(row)
                    options_table.setItem(row, 0, QTableWidgetItem(text))
                    options_table.setItem(row, 1, QTableWidgetItem(value))

                    sub_dialog.accept()

                sub_ok_btn.clicked.connect(on_sub_ok)
                sub_cancel_btn.clicked.connect(sub_dialog.reject)

                sub_button_layout.addStretch()
                sub_button_layout.addWidget(sub_ok_btn)
                sub_button_layout.addWidget(sub_cancel_btn)
                sub_layout.addRow(sub_button_layout)

                sub_dialog.exec_()

            def edit_option():
                current_row = options_table.currentRow()
                if current_row < 0:
                    Toast.warning(dialog, "警告", "请先选择要编辑的选项")
                    return

                current_text = options_table.item(current_row, 0).text()
                current_value = options_table.item(current_row, 1).text()

                sub_dialog = QDialog(dialog)
                sub_dialog.setWindowTitle("编辑选项")
                sub_dialog.setModal(True)
                sub_dialog.setFixedSize(300, 180)  # 同样增加高度
                sub_layout = QFormLayout(sub_dialog)
                sub_layout.setSpacing(12)
                sub_layout.setContentsMargins(15, 15, 15, 15)

                text_edit = QLineEdit()
                text_edit.setText(current_text)
                text_edit.setFixedWidth(200)
                sub_layout.addRow("显示文本:", text_edit)

                value_edit = QLineEdit()
                value_edit.setText(current_value)
                value_edit.setFixedWidth(200)
                sub_layout.addRow("值:", value_edit)

                # 添加弹性空间
                sub_layout.addItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))

                sub_button_layout = QHBoxLayout()
                sub_ok_btn = QPushButton("确定")
                sub_ok_btn.setFixedWidth(70)
                sub_cancel_btn = QPushButton("取消")
                sub_cancel_btn.setFixedWidth(70)

                def on_sub_ok():
                    text = text_edit.text().strip()
                    value = value_edit.text().strip()

                    if not text:
                        Toast.warning(sub_dialog, "警告", "请输入显示文本")
                        return
                    if not value:
                        Toast.warning(sub_dialog, "警告", "请输入值")
                        return

                    # 检查值是否重复（排除当前行）
                    for row in range(options_table.rowCount()):
                        if row == current_row:
                            continue
                        existing_value = options_table.item(row, 1).text()
                        if existing_value == value:
                            Toast.warning(sub_dialog, "警告", "值已存在")
                            return

                    # 更新表格
                    options_table.setItem(current_row, 0, QTableWidgetItem(text))
                    options_table.setItem(current_row, 1, QTableWidgetItem(value))

                    sub_dialog.accept()

                sub_ok_btn.clicked.connect(on_sub_ok)
                sub_cancel_btn.clicked.connect(sub_dialog.reject)

                sub_button_layout.addStretch()
                sub_button_layout.addWidget(sub_ok_btn)
                sub_button_layout.addWidget(sub_cancel_btn)
                sub_layout.addRow(sub_button_layout)

                sub_dialog.exec_()

            def remove_option():
                current_row = options_table.currentRow()
                if current_row >= 0:
                    options_table.removeRow(current_row)

            add_option_btn.clicked.connect(add_option)
            edit_option_btn.clicked.connect(edit_option)
            remove_option_btn.clicked.connect(remove_option)

            options_btn_layout.addWidget(add_option_btn)
            options_btn_layout.addWidget(edit_option_btn)
            options_btn_layout.addWidget(remove_option_btn)
            options_btn_layout.addStretch()

            options_layout.addLayout(options_btn_layout)
            layout.addWidget(options_group)

        # 条件映射配置 - 仅条件显示
        condition_mapping_table = None  # 提前声明变量
        if item_type == "condition":
            condition_mapping_group = QGroupBox("条件映射配置")
            condition_mapping_group.setContentsMargins(8, 8, 8, 8)
            condition_mapping_layout = QVBoxLayout(condition_mapping_group)
            condition_mapping_layout.setSpacing(6)

            condition_mapping_table = QTableWidget()
            condition_mapping_table.setColumnCount(2)
            condition_mapping_table.setHorizontalHeaderLabels(["条件值", "变量字段"])
            condition_mapping_table.horizontalHeader().setStretchLastSection(True)
            condition_mapping_table.setMaximumHeight(180)
            condition_mapping_table.setColumnWidth(0, 150)
            condition_mapping_table.setColumnWidth(1, 150)

            # 填充现有映射
            mappings = item_data.get("mappings", {})

            # 获取所有字段类型的布局项（用于第二列的下拉框）
            field_items = []
            for i in range(self.layout_list.count()):
                item = self.layout_list.item(i)
                item_data_field = item.data(Qt.UserRole)
                if item_data_field and item_data_field.get("type") == "field":
                    field_items.append({
                        "key": item_data_field.get("key"),
                        "label": item_data_field.get("label")
                    })

            # 获取当前条件字段的选项（如果条件字段已设置）
            current_condition_field_key = item_data.get("condition_field")
            condition_options = []
            if current_condition_field_key:
                for i in range(self.layout_list.count()):
                    item = self.layout_list.item(i)
                    item_data_field = item.data(Qt.UserRole)
                    if item_data_field and item_data_field.get(
                            "key") == current_condition_field_key and item_data_field.get("type") == "combo":
                        condition_options = item_data_field.get("options", [])
                        break

            for option in condition_options:
                condition_value = option.get("value")
                row = condition_mapping_table.rowCount()
                condition_mapping_table.insertRow(row)

                # 第一列：条件值（不可编辑）
                value_item = QTableWidgetItem(condition_value)
                value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
                condition_mapping_table.setItem(row, 0, value_item)

                # 第二列：变量字段选择（下拉框）
                combo = NoWheelComboBox()
                combo.addItem("", "")  # 空选项
                current_index = 0
                for idx, field in enumerate(field_items):
                    display_text = f"{field['label']} ({field['key']})"
                    combo.addItem(display_text, field['key'])
                    # 如果当前有映射，设置选中项
                    if condition_value in mappings and mappings[condition_value] == field['key']:
                        current_index = idx + 1  # +1 因为第一个是空选项
                combo.setCurrentIndex(current_index)
                condition_mapping_table.setCellWidget(row, 1, combo)

            condition_mapping_layout.addWidget(condition_mapping_table)

            # 当条件字段改变时，更新条件映射表格
            def on_condition_field_changed():
                current_field_key = condition_field_combo.currentData()
                condition_mapping_table.setRowCount(0)
                if not current_field_key:
                    return
                # 查找选中的下拉框配置
                combo_config = None
                for i in range(self.layout_list.count()):
                    item = self.layout_list.item(i)
                    item_data_field = item.data(Qt.UserRole)
                    if item_data_field and item_data_field.get("key") == current_field_key and item_data_field.get(
                            "type") == "combo":
                        combo_config = item_data_field
                        break
                if not combo_config:
                    return
                options = combo_config.get("options", [])
                for option in options:
                    row = condition_mapping_table.rowCount()
                    condition_mapping_table.insertRow(row)
                    condition_value = option.get("value")
                    value_item = QTableWidgetItem(condition_value)
                    value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
                    condition_mapping_table.setItem(row, 0, value_item)
                    combo = NoWheelComboBox()
                    combo.addItem("", "")
                    current_index = 0
                    for idx, field in enumerate(field_items):
                        display_text = f"{field['label']} ({field['key']})"
                        combo.addItem(display_text, field['key'])
                        if condition_value in mappings and mappings[condition_value] == field['key']:
                            current_index = idx + 1
                    combo.setCurrentIndex(current_index)
                    condition_mapping_table.setCellWidget(row, 1, combo)

            # 将信号连接移到条件类型判断内部
            if condition_field_combo:
                condition_field_combo.currentIndexChanged.connect(on_condition_field_changed)

            layout.addWidget(condition_mapping_group)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)

        def on_ok():
            # 根据类型校验必填字段
            if item_type in ["field", "combo", "condition", "formula"]:  # 新增公式类型
                key = key_edit.text().strip()
                label = label_edit.text().strip()

                # 必填校验
                if not key:
                    Toast.warning(dialog, "警告", "请输入键")
                    return
                if not label:
                    Toast.warning(dialog, "警告", "请输入标签")
                    return

            # 对于字段和下拉框类型，还需要获取其他字段的值
            if item_type in ["field", "combo"]:
                # 只有在字段和下拉框类型中才获取数据类型和默认值
                data_type = data_type_combo.currentText()
                default_value = default_edit.text().strip()
                show_in_ui = show_in_ui_checkbox.isChecked()

                # 数据类型校验
                if data_type in ["int", "float"] and default_value:
                    try:
                        if data_type == "int":
                            int(default_value)
                        elif data_type == "float":
                            float(default_value)
                    except ValueError:
                        Toast.warning(dialog, "警告", f"默认值 '{default_value}' 与数据类型 '{data_type}' 不匹配")
                        return
                elif data_type == "bool" and default_value:
                    if default_value.lower() not in ["true", "false", "1", "0"]:
                        Toast.warning(dialog, "警告", "布尔类型的默认值应为 true/false 或 1/0")
                        return

                # 下拉框特殊校验
                if item_type == "combo":
                    # 检查是否有选项
                    if options_table.rowCount() == 0:
                        Toast.warning(dialog, "警告", "请至少添加一个下拉框选项")
                        return

                    # 检查默认值是否在选项中
                    if default_value:
                        found = False
                        for row in range(options_table.rowCount()):
                            if options_table.item(row, 1).text() == default_value:
                                found = True
                                break
                        if not found:
                            Toast.warning(dialog, "警告", f"默认值 '{default_value}' 不在下拉框选项中")
                            return

            elif item_type == "interface":
                old_interface_name = item_data.get("name", "")
                new_interface_name = interface_name_edit.text().strip()

                # 必填校验
                if not new_interface_name:
                    Toast.warning(dialog, "警告", "请输入接口名称")
                    return

                # 如果接口名称发生变化，检查是否重复
                if old_interface_name != new_interface_name:
                    # 检查新名称是否已存在
                    for i in range(self.interface_list.count()):
                        if self.interface_list.item(i).text() == new_interface_name:
                            Toast.warning(dialog, "警告", "接口名称已存在")
                            return

            elif item_type == "sql":
                old_sql_name = item_data.get("name", "")
                new_sql_name = sql_name_edit.text().strip()

                # 必填校验
                if not new_sql_name:
                    Toast.warning(dialog, "警告", "请输入SQL名称")
                    return

                # 如果SQL名称发生变化，检查是否重复
                if old_sql_name != new_sql_name:
                    # 检查新名称是否已存在
                    for i in range(self.sql_list.count()):
                        if self.sql_list.item(i).text() == new_sql_name:
                            Toast.warning(dialog, "警告", "SQL名称已存在")
                            return

            elif item_type == "condition":
                # 对于条件类型，只需要获取是否展示到前端
                show_in_ui = show_in_ui_checkbox.isChecked()
                # 条件类型不需要数据类型和默认值验证

            elif item_type == "formula":  # 新增公式类型验证
                formula = formula_edit.toPlainText().strip()
                if not formula:
                    Toast.warning(dialog, "警告", "请输入公式")
                    return

                # 根据公式类型进行不同的验证
                formula_type = formula_type_combo.currentData()
                if formula_type == "numeric":
                    # 数值公式验证：检查是否包含数字运算符号
                    if not any(op in formula for op in ['+', '-', '*', '/']):
                        Toast.warning(dialog, "警告", "数值公式应包含数学运算符（+、-、*、/）")
                        return
                elif formula_type == "date":
                    # 日期公式验证：检查是否包含日期运算
                    if not any(op in formula for op in ['-']):
                        Toast.warning(dialog, "警告", "日期公式应包含减法运算符（-）")
                        return

            # 更新布局项数据
            if item_type in ["field", "combo"]:
                item_data.update({
                    "key": key_edit.text().strip(),
                    "label": label_edit.text().strip(),
                    "data_type": data_type_combo.currentText(),
                    "default": default_edit.text().strip(),
                    "show_in_ui": show_in_ui_checkbox.isChecked()
                })

                if item_type == "combo":
                    # 获取枚举选项
                    options = []
                    for row in range(options_table.rowCount()):
                        text_item = options_table.item(row, 0)
                        value_item = options_table.item(row, 1)
                        if text_item and value_item:
                            options.append({
                                "text": text_item.text(),
                                "value": value_item.text()
                            })
                    item_data["options"] = options

                display_text = f"{'字段' if item_type == 'field' else '下拉框'}: {label_edit.text().strip()} ({key_edit.text().strip()})"
                if not show_in_ui_checkbox.isChecked():
                    display_text += " [隐藏]"

            elif item_type == "interface":
                old_interface_name = item_data.get("name", "")
                new_interface_name = interface_name_edit.text().strip()

                # 如果接口名称发生变化，需要更新接口列表
                if old_interface_name != new_interface_name:
                    # 更新接口列表中的名称
                    for i in range(self.interface_list.count()):
                        if self.interface_list.item(i).text() == old_interface_name:
                            self.interface_list.item(i).setText(new_interface_name)
                            break

                item_data.update({
                    "name": new_interface_name
                })
                display_text = f"接口: {new_interface_name}"

            elif item_type == "sql":
                old_sql_name = item_data.get("name", "")
                new_sql_name = sql_name_edit.text().strip()

                # 如果SQL名称发生变化，需要更新SQL列表
                if old_sql_name != new_sql_name:
                    # 更新SQL列表中的名称
                    for i in range(self.sql_list.count()):
                        if self.sql_list.item(i).text() == old_sql_name:
                            self.sql_list.item(i).setText(new_sql_name)
                            break

                item_data.update({
                    "name": new_sql_name
                })
                display_text = f"SQL: {new_sql_name}"

            elif item_type == "condition":
                # 获取条件字段
                new_condition_field_key = condition_field_combo.currentData() if condition_field_combo else None
                if not new_condition_field_key:
                    Toast.warning(dialog, "警告", "请选择条件字段")
                    return

                # 获取映射关系
                mappings = {}
                if condition_mapping_table:
                    for row in range(condition_mapping_table.rowCount()):
                        value_item = condition_mapping_table.item(row, 0)
                        if not value_item:
                            continue

                        condition_value = value_item.text()  # 获取条件值
                        combo = condition_mapping_table.cellWidget(row, 1)
                        variable_field_key = combo.currentData() if combo else None

                        if condition_value and variable_field_key:
                            mappings[condition_value] = variable_field_key

                if not mappings:
                    Toast.warning(dialog, "警告", "请至少配置一个条件映射")
                    return

                item_data.update({
                    "key": key_edit.text().strip(),
                    "label": label_edit.text().strip(),
                    "condition_field": new_condition_field_key,
                    "mappings": mappings,
                    "show_in_ui": show_in_ui_checkbox.isChecked()  # 使用复选框的值
                })
                display_text = f"条件: {label_edit.text().strip()} ({key_edit.text().strip()})"
                if not show_in_ui_checkbox.isChecked():
                    display_text += " [隐藏]"  # 添加隐藏标记

            elif item_type == "formula":  # 新增公式类型更新
                item_data.update({
                    "key": key_edit.text().strip(),
                    "label": label_edit.text().strip(),
                    "formula_type": formula_type_combo.currentData(),
                    "formula": formula_edit.toPlainText().strip(),
                    "show_in_ui": show_in_ui_checkbox.isChecked()  # 确保这一行存在
                })
                display_text = f"公式: {label_edit.text().strip()} ({key_edit.text().strip()})"
                if not show_in_ui_checkbox.isChecked():
                    display_text += " [隐藏]"

            # 更新列表显示
            current_item.setText(display_text)
            current_item.setData(Qt.UserRole, item_data)

            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.exec_()

    def remove_layout_item(self):
        """删除布局项 - 添加二次确认"""
        current_row = self.layout_list.currentRow()
        if current_row < 0:
            Toast.warning(self, "警告", "请先选择要删除的布局项")
            return

        current_item = self.layout_list.item(current_row)
        item_data = current_item.data(Qt.UserRole)

        if not item_data:
            Toast.warning(self, "警告", "选中的布局项数据格式错误")
            return

        # 获取显示文本用于确认对话框
        display_text = current_item.text()

        # 二次确认弹窗
        # 对于确认对话框，暂时保留QMessageBox.question，因为Toast没有确认对话框功能
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除布局项 '{display_text}' 吗？\n此操作将同时删除相关的接口配置！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # 默认选择"No"更安全
        )

        if reply != QMessageBox.Yes:
            return

        # 如果是接口类型，同步删除接口配置
        if item_data and item_data.get("type") == "interface":
            interface_name = item_data.get("name")
            # 在接口列表中查找并删除对应的接口
            for i in range(self.interface_list.count()):
                if self.interface_list.item(i).text() == interface_name:
                    self.interface_list.takeItem(i)
                    break

        # 如果是SQL类型，同步删除SQL配置
        elif item_data and item_data.get("type") == "sql":
            sql_name = item_data.get("name")
            # 在SQL列表中查找并删除对应的SQL
            for i in range(self.sql_list.count()):
                if self.sql_list.item(i).text() == sql_name:
                    self.sql_list.takeItem(i)
                    break

        # 删除布局项
        self.layout_list.takeItem(current_row)

    def view_layout_item(self):
        """查看布局项详情"""
        current_row = self.layout_list.currentRow()
        if current_row < 0:
            Toast.warning(self, "警告", "请先选择要查看的布局项")
            return

        current_item = self.layout_list.item(current_row)
        item_data = current_item.data(Qt.UserRole)

        if not item_data:
            Toast.warning(self, "警告", "选中的布局项数据格式错误")
            return

        # 使用编辑布局项的对话框，但设置为只读模式
        dialog = QDialog(self)
        dialog.setWindowTitle("查看布局项")
        dialog.setModal(True)

        item_type = item_data.get("type")
        if item_type == "combo" or item_type == "condition":
            dialog.setFixedSize(500, 650)  # 与编辑对话框保持一致
        elif item_type == "formula":  # 不能与其他类型的公用，不然会被拉伸垂直间距
            dialog.setFixedSize(400, 400)
        elif item_type == "interface" or item_type == "sql":
            dialog.setFixedSize(400, 200)
        else:  # field
            dialog.setFixedSize(400, 350)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # 类型显示（只读）
        type_layout = QHBoxLayout()
        type_layout.setSpacing(5)
        type_label = QLabel("类型:")
        type_label.setFixedWidth(30)
        type_layout.addWidget(type_label)

        type_mapping = {
            "field": "字段",
            "combo": "下拉框",
            "interface": "接口",
            "sql": "SQL",
            "condition": "条件",
            "formula": "公式"  # 新增公式类型
        }
        type_value = QLabel(type_mapping.get(item_data.get("type", ""), item_data.get("type", "")))
        type_value.setStyleSheet("font-weight: bold; color: blue;")
        type_layout.addWidget(type_value)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(6)
        form_layout.setVerticalSpacing(6)
        form_layout.setHorizontalSpacing(8)

        # 根据类型显示不同的字段（全部只读）
        if item_type in ["field", "combo", "condition", "formula"]:  # 新增公式类型
            # 键（只读）
            key_edit = QLineEdit()
            key_edit.setText(item_data.get("key", ""))
            key_edit.setReadOnly(True)
            key_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")
            key_edit.setFixedWidth(250)
            form_layout.addRow("键:", key_edit)

            # 标签（只读）
            label_edit = QLineEdit()
            label_edit.setText(item_data.get("label", ""))
            label_edit.setReadOnly(True)
            label_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")
            label_edit.setFixedWidth(250)
            form_layout.addRow("标签:", label_edit)

        if item_type in ["field", "combo", "formula"]:
            # 是否展示到前端（只读）- 使用 QLineEdit 保持一致的间距
            show_in_ui_edit = QLineEdit()
            show_in_ui_edit.setText("是" if item_data.get("show_in_ui", True) else "否")
            show_in_ui_edit.setReadOnly(True)
            show_in_ui_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")
            show_in_ui_edit.setFixedWidth(250)
            form_layout.addRow("展示到前端:", show_in_ui_edit)

        if item_type in ["field", "combo"]:
            # 数据类型（只读）
            data_type_combo = NoWheelComboBox()
            data_type_combo.addItems(["string", "int", "float", "bool"])
            data_type_combo.setCurrentText(item_data.get("data_type", "string"))
            data_type_combo.setEnabled(False)
            data_type_combo.setFixedWidth(120)
            form_layout.addRow("数据类型:", data_type_combo)

            # 默认值（只读）
            default_edit = QLineEdit()
            default_edit.setText(item_data.get("default", ""))
            default_edit.setReadOnly(True)
            default_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")
            default_edit.setFixedWidth(250)
            form_layout.addRow("默认值:", default_edit)

        elif item_type == "interface":
            # 接口名称（只读）
            interface_name_edit = QLineEdit()
            interface_name_edit.setText(item_data.get("name", ""))
            interface_name_edit.setReadOnly(True)
            interface_name_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")
            interface_name_edit.setFixedWidth(250)
            form_layout.addRow("接口名称:", interface_name_edit)

        elif item_type == "sql":
            # SQL名称（只读）
            sql_name_edit = QLineEdit()
            sql_name_edit.setText(item_data.get("name", ""))
            sql_name_edit.setReadOnly(True)
            sql_name_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")
            sql_name_edit.setFixedWidth(250)
            form_layout.addRow("SQL名称:", sql_name_edit)

        elif item_type == "condition":
            # 条件字段（只读）
            condition_field_edit = QLineEdit()
            condition_field_edit.setText(item_data.get("condition_field", ""))
            condition_field_edit.setReadOnly(True)
            condition_field_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")
            condition_field_edit.setFixedWidth(250)
            form_layout.addRow("条件字段:", condition_field_edit)

        elif item_type == "formula":  # 新增公式类型处理
            # 公式类型显示（只读）
            formula_type_edit = NoWheelComboBox()
            formula_type_edit.addItems(["数值", "日期"])
            formula_type_edit.setEnabled(False)
            formula_type_edit.setFixedWidth(120)
            # 将英文类型映射为对应的索引
            current_formula_type = item_data.get("formula_type", "numeric")
            if current_formula_type == "numeric":
                formula_type_edit.setCurrentIndex(0)  # 数值
            elif current_formula_type == "date":
                formula_type_edit.setCurrentIndex(1)  # 日期
            form_layout.addRow("公式类型:", formula_type_edit)

            # 公式显示框（只读）
            formula_edit = QTextEdit()
            formula_edit.setText(item_data.get("formula", ""))
            formula_edit.setReadOnly(True)
            formula_edit.setStyleSheet("background-color: #f0f0f0; color: #666;")
            formula_edit.setFixedHeight(80)
            form_layout.addRow("公式:", formula_edit)

        layout.addLayout(form_layout)

        # 下拉框枚举配置 - 仅下拉框显示（只读）
        if item_type == "combo":
            options_group = QGroupBox("下拉框枚举配置")
            options_group.setContentsMargins(8, 8, 8, 8)
            options_layout = QVBoxLayout(options_group)
            options_layout.setSpacing(6)

            # 枚举表格（只读）
            options_table = QTableWidget()
            options_table.setColumnCount(2)
            options_table.setHorizontalHeaderLabels(["显示文本", "值"])
            options_table.horizontalHeader().setStretchLastSection(True)
            options_table.setMaximumHeight(180)
            options_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 禁止编辑

            # 设置列宽
            options_table.setColumnWidth(0, 150)
            options_table.setColumnWidth(1, 150)

            # 填充现有选项
            options = item_data.get("options", [])
            for option in options:
                row = options_table.rowCount()
                options_table.insertRow(row)
                options_table.setItem(row, 0, QTableWidgetItem(option.get("text", "")))
                options_table.setItem(row, 1, QTableWidgetItem(option.get("value", "")))

            options_layout.addWidget(options_table)
            layout.addWidget(options_group)

        # 条件映射配置 - 仅条件类型显示（只读）
        if item_type == "condition":
            condition_mapping_group = QGroupBox("条件映射配置")
            condition_mapping_group.setContentsMargins(8, 8, 8, 8)
            condition_mapping_layout = QVBoxLayout(condition_mapping_group)
            condition_mapping_layout.setSpacing(6)

            condition_mapping_table = QTableWidget()
            condition_mapping_table.setColumnCount(2)
            condition_mapping_table.setHorizontalHeaderLabels(["条件值", "变量字段"])
            condition_mapping_table.horizontalHeader().setStretchLastSection(True)
            condition_mapping_table.setMaximumHeight(180)
            condition_mapping_table.setColumnWidth(0, 150)
            condition_mapping_table.setColumnWidth(1, 150)
            condition_mapping_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 禁止编辑

            # 填充现有映射
            mappings = item_data.get("mappings", {})
            # 获取所有字段类型的布局项（用于显示变量字段的标签）
            field_mapping = {}
            for i in range(self.layout_list.count()):
                item = self.layout_list.item(i)
                item_data_field = item.data(Qt.UserRole)
                if item_data_field and item_data_field.get("type") == "field":
                    field_mapping[item_data_field.get("key")] = item_data_field.get("label")

            # 获取条件字段的选项（用于显示条件值的标签）
            condition_field_options = {}
            condition_field_key = item_data.get("condition_field")
            if condition_field_key:
                for i in range(self.layout_list.count()):
                    item = self.layout_list.item(i)
                    item_data_field = item.data(Qt.UserRole)
                    if (item_data_field and
                            item_data_field.get("type") == "combo" and
                            item_data_field.get("key") == condition_field_key):
                        options = item_data_field.get("options", [])
                        for option in options:
                            condition_field_options[option.get("value")] = option.get("text")
                        break

            for condition_value, variable_field in mappings.items():
                row = condition_mapping_table.rowCount()
                condition_mapping_table.insertRow(row)

                # 第一列：条件值（显示文本）
                condition_text = condition_field_options.get(condition_value, condition_value)
                condition_mapping_table.setItem(row, 0, QTableWidgetItem(f"{condition_text} ({condition_value})"))

                # 第二列：变量字段显示（显示标签）
                field_label = field_mapping.get(variable_field, variable_field)
                condition_mapping_table.setItem(row, 1, QTableWidgetItem(f"{field_label} ({variable_field})"))

            condition_mapping_layout.addWidget(condition_mapping_table)
            layout.addWidget(condition_mapping_group)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(dialog.accept)

        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        dialog.exec_()

    def _set_dialog_size_by_type(self, dialog, item_type):
        """根据布局类型设置对话框大小---只针对与add_layout_item方法"""
        size_mapping = {
            "field": (400, 350),  # 字段类型
            "combo": (500, 650),  # 下拉框类型（需要更多空间显示选项）
            "interface": (400, 250),  # 接口类型
            "sql": (400, 250),  # SQL类型
            "condition": (500, 650),  # 条件类型（需要显示映射表格）
            "formula": (400, 400)  # 公式类型
        }

        width, height = size_mapping.get(item_type, (450, 580))  # 默认大小
        dialog.setFixedSize(width, height)

    def on_add_type_changed(self, item_type):
        """添加布局项类型改变事件 - 修复版"""
        # 安全检查：确保 add_type_combo 存在
        if not hasattr(self, 'add_type_combo'):
            return

            # 获取实际的类型值（如果是中文显示，需要映射到英文）
        type_mapping = {
            "字段": "field",
            "下拉框": "combo",
            "接口": "interface",
            "SQL": "sql",
            "条件": "condition",
            "公式": "formula"
        }
        actual_type = type_mapping.get(item_type, item_type)

        # 动态调整对话框大小
        if hasattr(self, '_add_dialog') and self._add_dialog:
            self._set_dialog_size_by_type(self._add_dialog, actual_type)

        # 显示/隐藏相关字段 - 修复：确保所有变量都是布尔值
        is_field_or_combo_or_condition = actual_type in ["field", "combo", "condition"]  # 添加条件类型
        is_interface = actual_type == "interface"
        is_sql = actual_type == "sql"
        is_combo = actual_type == "combo"  # 修复：确保这是布尔值，不是元组
        is_condition = actual_type == "condition"  # 新增条件类型判断
        is_formula = actual_type == "formula"  # 新增公式类型处理

        # 键/名称和标签 - 仅字段、下拉框、条件和公式显示
        self.add_key_label.setVisible(is_field_or_combo_or_condition or is_formula)  # 修改
        self.add_key_edit.setVisible(is_field_or_combo_or_condition or is_formula)  # 修改
        self.add_label_label.setVisible(is_field_or_combo_or_condition or is_formula)  # 修改
        self.add_label_edit.setVisible(is_field_or_combo_or_condition or is_formula)  # 修改

        # 接口名称 - 仅接口显示
        self.add_interface_name_label.setVisible(is_interface)
        self.add_interface_name_edit.setVisible(is_interface)

        # SQL名称 - 仅SQL显示
        self.add_sql_name_label.setVisible(is_sql)
        self.add_sql_name_edit.setVisible(is_sql)

        # 条件字段和映射配置 - 仅条件类型显示
        self.add_condition_field_label.setVisible(is_condition)
        self.add_condition_field_combo.setVisible(is_condition)
        self.add_condition_mapping_group.setVisible(is_condition)

        # 数据类型 - 仅字段和下拉框显示
        self.add_data_type_label.setVisible(is_field_or_combo_or_condition)
        self.add_data_type_combo.setVisible(is_field_or_combo_or_condition)

        # 默认值 - 仅字段和下拉框显示
        self.add_default_label.setVisible(is_field_or_combo_or_condition)
        self.add_default_edit.setVisible(is_field_or_combo_or_condition)

        # 是否展示到前端 - 仅字段、下拉框和公式显示
        self.add_show_in_ui_label.setVisible(is_field_or_combo_or_condition or is_formula)  # 修改
        self.add_show_in_ui_checkbox.setVisible(is_field_or_combo_or_condition or is_formula)  # 修改

        # 下拉框枚举配置 - 仅下拉框显示
        self.add_options_group.setVisible(is_combo)  # 修复：这里应该是 is_combo 而不是 is_combo

        # 新增：公式类型选择 - 仅公式类型显示
        self.add_formula_type_label.setVisible(is_formula)
        self.add_formula_type_combo.setVisible(is_formula)

        # 新增：公式输入框 - 仅公式类型显示
        self.add_formula_label.setVisible(is_formula)
        self.add_formula_edit.setVisible(is_formula)

        # 清空字段
        if not is_field_or_combo_or_condition and not is_condition:
            self.add_key_edit.clear()
            self.add_label_edit.clear()
        if not is_interface:
            self.add_interface_name_edit.clear()
        if not is_sql:
            self.add_sql_name_edit.clear()
        if not is_formula:  # 新增：清空公式字段
            self.add_formula_type_combo.setCurrentIndex(0)  # 重置为默认值
            self.add_formula_edit.clear()

        # 如果是条件类型，初始化条件字段下拉框
        if is_condition:
            self.init_condition_field_combo()

    def init_condition_field_combo(self):
        """初始化条件字段下拉框 - 只显示下拉框类型的布局项"""
        self.add_condition_field_combo.clear()

        # 获取所有已配置的下拉框类型布局项
        combo_fields = []
        for i in range(self.layout_list.count()):
            item = self.layout_list.item(i)
            item_data = item.data(Qt.UserRole)
            if item_data and item_data.get("type") == "combo":
                combo_fields.append({
                    "key": item_data.get("key"),
                    "label": item_data.get("label")
                })

        # 添加到下拉框
        for field in combo_fields:
            display_text = f"{field['label']} ({field['key']})"
            self.add_condition_field_combo.addItem(display_text, field['key'])

        # 如果有条件字段，初始化映射表格
        if self.add_condition_field_combo.count() > 0:
            self.init_condition_mapping_table()
        else:
            self.add_condition_mapping_table.setRowCount(0)

    def on_condition_field_changed(self):
        """条件字段改变事件"""
        self.init_condition_mapping_table()

    def init_condition_mapping_table(self):
        """初始化条件映射表格"""
        self.add_condition_mapping_table.setRowCount(0)

        current_field_key = self.add_condition_field_combo.currentData()
        if not current_field_key:
            return

        # 查找选中的下拉框配置
        combo_config = None
        for i in range(self.layout_list.count()):
            item = self.layout_list.item(i)
            item_data = item.data(Qt.UserRole)
            if item_data and item_data.get("key") == current_field_key and item_data.get("type") == "combo":
                combo_config = item_data
                break

        if not combo_config:
            return

        # 获取下拉框的选项
        options = combo_config.get("options", [])

        # 获取所有字段类型的布局项（用于第二列的下拉框）
        field_items = []
        for i in range(self.layout_list.count()):
            item = self.layout_list.item(i)
            item_data = item.data(Qt.UserRole)
            if item_data and item_data.get("type") == "field":
                field_items.append({
                    "key": item_data.get("key"),
                    "label": item_data.get("label")
                })

        # 填充表格
        for option in options:
            row = self.add_condition_mapping_table.rowCount()
            self.add_condition_mapping_table.insertRow(row)

            # 第一列：条件值（不可编辑）
            condition_value = option.get("value", "")
            condition_text = option.get("text", "")
            display_text = f"{condition_text} ({condition_value})" if condition_text != condition_value else condition_value

            value_item = QTableWidgetItem(display_text)
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)  # 设置为不可编辑
            value_item.setData(Qt.UserRole, condition_value)  # 保存原始值到 UserRole
            self.add_condition_mapping_table.setItem(row, 0, value_item)

            # 第二列：变量字段选择（下拉框）
            combo = NoWheelComboBox()
            combo.addItem("", "")  # 空选项
            for field in field_items:
                display_text = f"{field['label']} ({field['key']})"
                combo.addItem(display_text, field['key'])
            self.add_condition_mapping_table.setCellWidget(row, 1, combo)

    def add_option_item(self):
        """添加下拉框选项"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加选项")
        dialog.setModal(True)
        dialog.setFixedSize(300, 150)
        layout = QFormLayout(dialog)

        text_edit = QLineEdit()
        text_edit.setPlaceholderText("显示文本")
        text_edit.setFixedWidth(200)  # 固定宽度
        layout.addRow("显示文本:", text_edit)

        value_edit = QLineEdit()
        value_edit.setPlaceholderText("值")
        value_edit.setFixedWidth(200)  # 固定宽度
        layout.addRow("值:", value_edit)

        button_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)  # 固定宽度

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)  # 固定宽度

        def on_ok():
            text = text_edit.text().strip()
            value = value_edit.text().strip()

            if not text:
                Toast.warning(dialog, "警告", "请输入显示文本")
                return
            if not value:
                Toast.warning(dialog, "警告", "请输入值")
                return

            # 检查值是否重复
            for row in range(self.add_options_table.rowCount()):
                existing_value = self.add_options_table.item(row, 1).text()
                if existing_value == value:
                    Toast.warning(dialog, "警告", "值已存在")
                    return

            # 添加到表格
            row = self.add_options_table.rowCount()
            self.add_options_table.insertRow(row)
            self.add_options_table.setItem(row, 0, QTableWidgetItem(text))
            self.add_options_table.setItem(row, 1, QTableWidgetItem(value))

            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)

        dialog.exec_()

    def edit_option_item(self):
        """编辑下拉框选项"""
        current_row = self.add_options_table.currentRow()
        if current_row < 0:
            Toast.warning(self, "警告", "请先选择要编辑的选项")
            return

        current_text = self.add_options_table.item(current_row, 0).text()
        current_value = self.add_options_table.item(current_row, 1).text()

        dialog = QDialog(self)
        dialog.setWindowTitle("编辑选项")
        dialog.setModal(True)
        dialog.setFixedSize(300, 150)
        layout = QFormLayout(dialog)

        text_edit = QLineEdit()
        text_edit.setText(current_text)
        text_edit.setFixedWidth(200)  # 固定宽度
        layout.addRow("显示文本:", text_edit)

        value_edit = QLineEdit()
        value_edit.setText(current_value)
        value_edit.setFixedWidth(200)  # 固定宽度
        layout.addRow("值:", value_edit)

        button_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)  # 固定宽度

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)  # 固定宽度

        def on_ok():
            text = text_edit.text().strip()
            value = value_edit.text().strip()

            if not text:
                Toast.warning(dialog, "警告", "请输入显示文本")
                return
            if not value:
                Toast.warning(dialog, "警告", "请输入值")
                return

            # 检查值是否重复（排除当前行）
            for row in range(self.add_options_table.rowCount()):
                if row == current_row:
                    continue
                existing_value = self.add_options_table.item(row, 1).text()
                if existing_value == value:
                    Toast.warning(dialog, "警告", "值已存在")
                    return

            # 更新表格
            self.add_options_table.setItem(current_row, 0, QTableWidgetItem(text))
            self.add_options_table.setItem(current_row, 1, QTableWidgetItem(value))

            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)

        dialog.exec_()

    def remove_option_item(self):
        """删除下拉框选项"""
        current_row = self.add_options_table.currentRow()
        if current_row >= 0:
            self.add_options_table.removeRow(current_row)

    def add_default_interface(self, interface_name):
        """为布局中的接口项生成默认接口配置"""
        # 创建默认接口配置 - 通用请求模板
        default_interface_config = {
            "url": "",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json"
            },
            "body_template": {},
            "response_mapping": {},
            "field_types": {}
        }

        # 检查接口是否已存在
        for i in range(self.interface_list.count()):
            if self.interface_list.item(i).text() == interface_name:
                # 接口已存在，不重复添加
                return

        # 添加到接口列表
        item = QListWidgetItem(interface_name)
        item.setData(Qt.UserRole, default_interface_config)
        self.interface_list.addItem(item)

    def edit_interface(self):
        """编辑接口"""
        current_row = self.interface_list.currentRow()
        if current_row < 0:
            Toast.warning(self, "警告", "请先选择要编辑的接口")
            return

        current_item = self.interface_list.item(current_row)
        interface_name = current_item.text()
        interface_config = current_item.data(Qt.UserRole)

        # 打开接口配置对话框
        dialog = InterfaceConfigDialog(interface_name, interface_config, self)
        if dialog.exec_() == QDialog.Accepted:
            # 更新接口配置
            current_item.setData(Qt.UserRole, dialog.interface_config)
            Toast.information(self, "成功", f"接口 '{interface_name}' 配置已更新")

    def view_interface(self):
        """查看接口详情"""
        current_row = self.interface_list.currentRow()
        if current_row < 0:
            Toast.warning(self, "警告", "请先选择要查看的接口")
            return

        current_item = self.interface_list.item(current_row)
        interface_name = current_item.text()
        interface_config = current_item.data(Qt.UserRole)

        # 打开接口配置对话框，但设置为只读模式
        dialog = InterfaceConfigDialog(interface_name, interface_config, self)

        # 设置对话框为只读模式
        dialog.setWindowTitle(f"查看接口 - {interface_name}")

        # 禁用所有可编辑控件
        for widget in dialog.findChildren((QLineEdit, QTextEdit, QComboBox, QCheckBox)):
            if isinstance(widget, QLineEdit):
                widget.setReadOnly(True)
                widget.setStyleSheet("background-color: #f0f0f0; color: #666;")
            elif isinstance(widget, QTextEdit):
                widget.setReadOnly(True)
                widget.setStyleSheet("background-color: #f0f0f0; color: #666;")
            elif isinstance(widget, QComboBox):
                widget.setEnabled(False)
            elif isinstance(widget, QCheckBox):
                widget.setEnabled(False)

        # 隐藏保存按钮，只显示关闭按钮
        dialog.save_btn.setVisible(False)
        dialog.cancel_btn.setText("关闭")

        dialog.exec_()

    def add_default_sql_config(self, sql_name):
        """为布局中的SQL项生成默认SQL配置"""
        default_sql_config = {
            "database": {
                "host": "47.106.192.83",
                "port": 3306,
                "user": "xvdba",
                "password": "xvdba@2022",
                "database": "cfloan_biz"
            },
            "sql": "",
            "output_fields": []
        }

        # 检查SQL是否已存在
        for i in range(self.sql_list.count()):
            if self.sql_list.item(i).text() == sql_name:
                # SQL已存在，不重复添加
                return

        # 添加到SQL列表
        item = QListWidgetItem(sql_name)
        item.setData(Qt.UserRole, default_sql_config)
        self.sql_list.addItem(item)

    def edit_sql(self):
        """编辑SQL配置"""
        current_row = self.sql_list.currentRow()
        if current_row < 0:
            Toast.warning(self, "警告", "请先选择要编辑的SQL")
            return

        current_item = self.sql_list.item(current_row)
        sql_name = current_item.text()
        sql_config = current_item.data(Qt.UserRole)

        # 打开SQL配置对话框
        dialog = SQLConfigDialog(sql_name, sql_config, self)
        if dialog.exec_() == QDialog.Accepted:
            # 更新SQL配置
            current_item.setData(Qt.UserRole, dialog.get_config())
            Toast.information(self, "成功", f"SQL '{sql_name}' 配置已更新")

    def view_sql(self):
        """查看SQL详情"""
        current_row = self.sql_list.currentRow()
        if current_row < 0:
            Toast.warning(self, "警告", "请先选择要查看的SQL")
            return

        current_item = self.sql_list.item(current_row)
        sql_name = current_item.text()
        sql_config = current_item.data(Qt.UserRole)

        # 打开SQL配置对话框，但设置为只读模式
        dialog = SQLConfigDialog(sql_name, sql_config, self)
        dialog.setWindowTitle(f"查看SQL - {sql_name}")

        # 禁用所有可编辑控件
        for widget in dialog.findChildren((QLineEdit, QTextEdit, QComboBox, QPushButton, QTableWidget)):
            if isinstance(widget, QLineEdit):
                widget.setReadOnly(True)
                widget.setStyleSheet("background-color: #f0f0f0; color: #666;")
            elif isinstance(widget, QTextEdit):
                widget.setReadOnly(True)
                widget.setStyleSheet("background-color: #f0f0f0; color: #666;")
            elif isinstance(widget, QComboBox):
                widget.setEnabled(False)
            elif isinstance(widget, QPushButton):
                # 不要禁用关闭按钮
                if widget != dialog.cancel_btn:
                    widget.setEnabled(False)
            elif isinstance(widget, QTableWidget):
                widget.setEditTriggers(QTableWidget.NoEditTriggers)

        # 隐藏保存按钮，只显示关闭按钮
        dialog.save_btn.setVisible(False)
        dialog.cancel_btn.setText("关闭")

        # 确保关闭按钮是启用的
        dialog.cancel_btn.setEnabled(True)

        dialog.exec_()

    def save_all_config(self):
        """保存所有配置"""
        try:
            # 保存产品管理配置
            config_file = resource_path("config/products_config.json")
            os.makedirs(os.path.dirname(config_file), exist_ok=True)

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.products_config, f, ensure_ascii=False, indent=2)

            # 保存当前选中的产品详情配置（仅当产品未锁定时）
            current_product = self.detail_product_combo.currentText()
            if current_product:
                real_product_name = self.get_real_product_name(current_product)
                # 只有产品未锁定时才允许保存
                if real_product_name not in self.products_config.get("locked_products", []):
                    self.save_product_detail_config(real_product_name)

            # 通知主界面重新加载配置
            if self.api_tool_tab:
                self.api_tool_tab.load_products_config()

            # 发射保存成功信号
            self.config_saved.emit("配置保存成功")
            self.close()

        except Exception as e:
            Toast.critical(self, "错误", f"配置保存失败: {str(e)}")

    def save_product_detail_config(self, product_name):
        """保存产品详情配置"""
        try:
            config_path = self.products_config["products"].get(product_name)
            if not config_path:
                return False

            product_config_file = resource_path(f"{config_path}")

            # 构建产品配置
            product_config = {
                "enable_encryption": self.detail_enable_encryption.isChecked(),
                "encrypt_url": self.detail_encrypt_url_edit.text().strip(),
                "decrypt_url": self.detail_decrypt_url_edit.text().strip(),
                "schedule_tasks": [],
                "layout": [],
                "interfaces": {},
                "sqls": {}  # 新增SQL配置
            }

            # 保存定时任务
            for i in range(self.schedule_list.count()):
                item = self.schedule_list.item(i)
                task_data = item.data(Qt.UserRole)
                if task_data:
                    product_config["schedule_tasks"].append(task_data)

            # 保存布局配置 - 按照拖拽后的顺序重新计算优先级
            for i in range(self.layout_list.count()):
                item = self.layout_list.item(i)
                layout_data = item.data(Qt.UserRole)
                if layout_data:
                    # 更新优先级为当前顺序
                    layout_data['priority'] = i + 1
                    product_config["layout"].append(layout_data)

            # 保存接口配置
            for i in range(self.interface_list.count()):
                interface_name = self.interface_list.item(i).text()
                interface_data = self.interface_list.item(i).data(Qt.UserRole)
                if interface_data:
                    product_config["interfaces"][interface_name] = interface_data
                else:
                    # 如果没有保存的数据，创建默认接口配置
                    product_config["interfaces"][interface_name] = {
                        "url": "",
                        "method": "POST",
                        "headers": {
                            "Content-Type": "application/json"
                        },
                        "body_template": {}
                    }

            # 保存SQL配置
            for i in range(self.sql_list.count()):
                sql_name = self.sql_list.item(i).text()
                sql_data = self.sql_list.item(i).data(Qt.UserRole)
                if sql_data:
                    product_config["sqls"][sql_name] = sql_data

            os.makedirs(os.path.dirname(product_config_file), exist_ok=True)

            with open(product_config_file, 'w', encoding='utf-8') as f:
                json.dump(product_config, f, ensure_ascii=False, indent=2)

            # 刷新主界面的定时任务下拉列表
            if self.api_tool_tab:
                self.api_tool_tab.load_products_config()
                # 如果当前产品是主界面正在使用的产品，更新定时任务下拉框
                if self.api_tool_tab.current_product == product_name:
                    product_config = self.api_tool_tab.api_config["products"].get(product_name, {})
                    self.api_tool_tab.update_schedule_tasks_combo(product_config)

            return True

        except Exception as e:
            Toast.critical(self, "错误", f"保存产品详情配置失败: {str(e)}")
            return False

    def extract_formula_dependencies(self, formula):
        """提取公式中依赖的变量"""
        pattern = r'\{(\w+)\}'
        variables = re.findall(pattern, formula)
        return list(set(variables))  # 去重
