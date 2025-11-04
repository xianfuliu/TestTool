import os
import json
import re
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QGroupBox,
                             QCheckBox, QTextEdit, QMessageBox, QSplitter, QScrollArea, QSizePolicy)
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from src.ui.widgets.no_wheel_combo_box import NoWheelComboBox
from src.ui.widgets.toast_tips import Toast
from src.ui.widgets.width_aware import WidthAwareWidget
from src.utils.id_card_generator import UserInfoGenerator
from src.utils.id_card_images_generator import IdCardImageGenerator
from src.ui.dialogs.api_tool_config_management_dialog import ConfigManagementDialog
from src.utils.resource_utils import resource_path
from src.utils.api_worker import ApiWorker
from src.utils.schedule_executor import ScheduleExecutor
from src.utils.sql_worker import SQLWorker
from src.utils.template_processor import TemplateProcessor
import jsonpath_ng


class ApiToolTab(QWidget):
    """接口工具Tab - 支持多产品接口测试"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.user_info_generator = UserInfoGenerator()
        self.id_card_image_generator = IdCardImageGenerator(parent)
        self.api_config = {"products": {}}  # 存储所有产品配置
        self.products_config = {}  # 存储产品文件映射
        self.sql_buttons = {}  # 新增SQL按钮字典
        self.condition_displays = {}  # 新增：存储条件显示控件
        self.sql_worker = None  # 新增SQL工作线程
        self.formula_displays = {}  # 存储公式显示控件
        self.formula_configs = {}  # 存储公式配置
        # 新增：记录最后一次SQL查询的时间戳
        self.last_sql_execution_time = None
        # 新增：记录各字段的最后更新时间
        self.field_last_update_time = {}
        self.current_product = None
        self.current_interface = None
        self.field_inputs = {}
        self.combo_boxes = {}
        self.schedule_executor = None
        self.worker = None
        self.loading_svg_path = "src/resources/icons/loading.svg"
        self.products_config_path = "/config/products_config.json"
        self.default_products_config_path = "config/products/default.json"
        self.products_config_dir_path = "config/products/"
        # Base64 变量键常量
        self.BASE64_VARIABLE_KEYS = [
            'id_card_front_base64',
            'id_card_back_base64',
            'face_base64'
        ]
        # 变量池 - 存储所有变量（包括响应映射变量等）
        self.variable_pool = {}
        # 初始化变量池
        self.init_variable_pool()

        # 动画相关属性
        self.schedule_original_text = ""

        # 初始化UI
        self.init_ui()
        # 加载配置，配置加载完成后会自动更新流水
        self.load_products_config()

    def init_variable_pool(self):
        """初始化变量池"""
        self.variable_pool = {
            'request_id': self.generate_request_id()
        }

    def load_configs(self):
        """统一加载所有配置"""
        self.load_products_config()

    def load_products_config(self):
        """加载全局产品配置文件"""
        config_file = resource_path(self.products_config_path)

        # 如果全局配置文件不存在，创建默认配置
        if not os.path.exists(config_file):
            self.create_default_products_config(self.default_products_config_path)

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.products_config = json.load(f)

            # 加载所有产品配置
            self.load_all_products()

            # 更新产品下拉框
            self.update_product_combo()  # 修改这里：调用正确的方法

            # 设置默认产品
            default_product = self.products_config.get("default_product")
            if default_product and self.product_combo.findText(default_product) >= 0:
                self.product_combo.setCurrentText(default_product)
            elif self.product_combo.count() > 0:
                self.product_combo.setCurrentIndex(0)

            # 如果有产品，自动更新流水
            if self.product_combo.count() > 0:
                # 这里会触发 on_product_changed，其中会调用 update_request_id()
                self.on_product_changed(self.product_combo.currentText(), initial_load=True)
            else:
                self.product_combo.addItem("无可用产品")

        except Exception as e:
            print(f"加载产品配置失败: {str(e)}")
            self.create_default_products_config(self.default_products_config_path)

    def update_product_combo(self):
        """更新产品下拉框"""
        self.product_combo.clear()
        if "products" in self.products_config:
            for product_name in self.products_config["products"].keys():
                self.product_combo.addItem(product_name)

    def load_all_products(self):
        """加载所有产品的配置文件"""
        if "products" not in self.products_config:
            return

        for product_name, config_path in self.products_config["products"].items():
            try:
                product_config_file = resource_path(f"{config_path}")
                if os.path.exists(product_config_file):
                    with open(product_config_file, 'r', encoding='utf-8') as f:
                        product_config = json.load(f)
                    self.api_config["products"][product_name] = product_config
                else:
                    print(f"产品配置文件不存在: {product_config_file}")
                    # 创建默认产品配置
                    self.create_default_product_config(product_name, config_path)
            except Exception as e:
                print(f"加载产品 {product_name} 配置失败: {str(e)}")

    def load_product_config(self, product_name):
        """动态加载单个产品配置（用于热重载）"""
        if product_name not in self.products_config.get("products", {}):
            return False

        config_path = self.products_config["products"][product_name]
        try:
            product_config_file = resource_path(f"{config_path}")
            if os.path.exists(product_config_file):
                with open(product_config_file, 'r', encoding='utf-8') as f:
                    product_config = json.load(f)
                self.api_config["products"][product_name] = product_config
                return True
        except Exception as e:
            print(f"重新加载产品 {product_name} 配置失败: {str(e)}")

        return False

    def save_product_config(self, product_name):
        """保存单个产品配置到文件"""
        if product_name not in self.api_config["products"]:
            return False

        if product_name not in self.products_config.get("products", {}):
            return False

        config_path = self.products_config["products"][product_name]
        product_config_file = resource_path(f"{config_path}")

        # 确保目录存在
        os.makedirs(os.path.dirname(product_config_file), exist_ok=True)

        try:
            with open(product_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.api_config["products"][product_name], f,
                          ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            Toast.critical(self, "失败", f"保存产品配置失败: {str(e)}")
            return False

    def create_default_products_config(self, default_products_config_path):
        """创建默认的产品配置文件结构"""
        try:
            self.products_config = {
                "products": {
                    "中银消金": f"{default_products_config_path}"
                },
                "default_product": "中银消金",
                "locked_products": []  # 添加锁定产品列表
            }

            # 确保配置目录存在
            config_dir = resource_path(self.products_config_dir_path)
            os.makedirs(config_dir, exist_ok=True)

            # 保存全局配置
            self.save_products_config()

            # 创建默认产品配置
            self.create_default_product_config("default")

            # 更新UI
            self.update_product_combo()  # 修改这里：调用正确的方法

            # 设置当前产品并更新流水
            if self.product_combo.count() > 0:
                self.product_combo.setCurrentIndex(0)
                self.on_product_changed(self.product_combo.currentText(), initial_load=True)

            return True
        except Exception as e:
            print(f"创建默认产品配置失败: {str(e)}")
            return False

    def save_products_config(self):
        """保存全局产品配置文件"""
        config_file = resource_path(self.products_config_path)
        os.makedirs(os.path.dirname(config_file), exist_ok=True)

        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.products_config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存产品配置失败: {str(e)}")
            return False

    def create_default_product_config(self, product_name):
        """创建默认产品配置"""
        default_config = {
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
                    "type": "field",
                    "key": "phone",
                    "label": "手机号",
                    "priority": 3,
                    "default": ""
                },
                {
                    "type": "interface",
                    "name": "默认接口",
                    "priority": 4
                }
            ],
            "interfaces": {
                "默认接口": {
                    "url": "http://api.example.com/default",
                    "method": "POST",
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body_template": {
                        "requestId": "{request_id}",
                        "userInfo": {
                            "name": "{name}",
                            "idCard": "{id_card}",
                            "phone": "{phone}"
                        }
                    }
                }
            }
        }

        self.api_config["products"][product_name] = default_config
        return self.save_product_config(product_name)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # 顶部全局配置
        global_config_panel = self.create_global_config_panel()
        main_layout.addWidget(global_config_panel)

        # 创建水平分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧栏 - 产品要素
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # 右侧栏 - 请求信息
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # 设置分割比例
        splitter.setSizes([500, 400])  # 左侧500，右侧400
        main_layout.addWidget(splitter, 1)

    def create_global_config_panel(self):
        """创建全局配置面板"""
        panel = QGroupBox("全局配置")
        main_vertical_layout = QVBoxLayout(panel)

        # 第一行：水平布局，包含所有主要控件
        first_row_layout = QHBoxLayout()
        first_row_layout.setSpacing(15)

        # 产品选择
        first_row_layout.addWidget(QLabel("产品:"))
        self.product_combo = NoWheelComboBox()
        self.product_combo.currentTextChanged.connect(self.on_product_changed)
        self.product_combo.setFixedWidth(150)
        first_row_layout.addWidget(self.product_combo)

        # 增加间距（添加固定宽度的空白）
        first_row_layout.addSpacing(35)

        # 请求流水
        first_row_layout.addWidget(QLabel("请求流水:"))
        self.request_id_input = QLineEdit()
        self.request_id_input.setText(self.generate_request_id())
        self.request_id_input.setFixedWidth(150)
        first_row_layout.addWidget(self.request_id_input)

        self.update_request_id_btn = QPushButton("更新")
        self.update_request_id_btn.clicked.connect(self.update_request_id)
        self.update_request_id_btn.setFixedWidth(80)
        first_row_layout.addWidget(self.update_request_id_btn)

        # 增加间距（添加固定宽度的空白）
        first_row_layout.addSpacing(35)

        # 定时任务控件
        first_row_layout.addWidget(QLabel("定时任务:"))
        self.schedule_combo = NoWheelComboBox()
        self.schedule_combo.setFixedWidth(250)
        first_row_layout.addWidget(self.schedule_combo)

        # 执行按钮 - 修改为支持SVG动画
        self.execute_schedule_btn = QPushButton("执行")
        self.execute_schedule_btn.clicked.connect(self.execute_schedule_task)
        self.execute_schedule_btn.setFixedWidth(80)
        self.execute_schedule_btn.setEnabled(False)

        # 创建SVG部件并嵌入到按钮中
        self.loading_svg = QSvgWidget(self.execute_schedule_btn)
        svg_path = resource_path(self.loading_svg_path)
        if os.path.exists(svg_path):
            self.loading_svg.load(svg_path)
        self.loading_svg.setFixedSize(16, 16)  # 设置合适的大小
        self.loading_svg.setVisible(False)  # 初始隐藏

        first_row_layout.addWidget(self.execute_schedule_btn)

        # 增加间距（添加固定宽度的空白）
        first_row_layout.addSpacing(35)

        # 发送请求复选框
        self.auto_request_checkbox = QCheckBox("发送请求")
        self.auto_request_checkbox.setChecked(True)
        first_row_layout.addWidget(self.auto_request_checkbox)

        # 添加弹性空间，将右侧控件推到最右边
        first_row_layout.addStretch(1)

        # 配置管理按钮
        self.config_manage_btn = QPushButton("配置管理")
        self.config_manage_btn.clicked.connect(self.open_config_management)
        self.config_manage_btn.setFixedWidth(100)
        first_row_layout.addWidget(self.config_manage_btn)

        # 添加弹性空间使控件左对齐
        first_row_layout.addStretch()

        # 将第一行布局添加到主垂直布局
        main_vertical_layout.addLayout(first_row_layout)

        return panel

    def create_left_panel(self):
        """创建左侧面板 - 接口按钮和参数字段混合在一起，左对齐"""
        panel = QGroupBox("产品要素")
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # 修改：面板布局左对齐

        # 创建滚动区域，包含混合的接口和字段
        self.combined_scroll = QScrollArea()
        self.combined_widget = QWidget()
        self.combined_layout = QVBoxLayout(self.combined_widget)  # 修改：使用垂直布局
        self.combined_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # 修改：滚动区域内容左对齐
        self.combined_scroll.setWidget(self.combined_widget)
        self.combined_scroll.setWidgetResizable(True)
        self.combined_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 需要时显示水平滚动条
        layout.addWidget(self.combined_scroll)

        panel.setLayout(layout)
        return panel

    def create_right_panel(self):
        panel = QGroupBox("请求信息")
        layout = QVBoxLayout()

        # URL 输入框（原来显示为标签）
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.url_input = QLineEdit()  # 改为输入框
        self.url_input.setPlaceholderText("请输入请求URL或从左侧选择接口自动填充")
        self.url_input.setStyleSheet("color: blue; font-weight: bold;")
        url_layout.addWidget(self.url_input, 1)
        layout.addLayout(url_layout)

        # 请求体编辑
        layout.addWidget(QLabel("请求体:"))
        self.request_body_edit = QTextEdit()
        self.request_body_edit.setPlaceholderText("请求体将在这里生成...")
        self.request_body_edit.setFont(QFont("Consolas", 10))
        layout.addWidget(self.request_body_edit, 2)

        # 手动请求按钮
        self.manual_request_btn = QPushButton("发送请求")
        self.manual_request_btn.clicked.connect(self.send_manual_request)
        self.manual_request_btn.setEnabled(True)  # 始终启用
        layout.addWidget(self.manual_request_btn)

        # 响应体显示
        layout.addWidget(QLabel("响应体:"))
        self.response_body_edit = QTextEdit()
        self.response_body_edit.setPlaceholderText("响应内容将显示在这里...")
        self.response_body_edit.setFont(QFont("Consolas", 10))
        self.response_body_edit.setReadOnly(True)
        layout.addWidget(self.response_body_edit, 3)

        panel.setLayout(layout)
        return panel

    def generate_request_id(self):
        """生成请求流水号"""
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def update_request_id(self):
        """更新请求流水号 - 修复：调用新的强制刷新方法"""
        self.update_request_id_and_reset_fields()

    def on_product_changed(self, product_name, initial_load=False):
        """首页产品切换事件 - 修复：切换产品时自动生成测试数据"""
        if not product_name or product_name == "无可用产品":
            return

        # 确保产品存在于配置中
        if product_name not in self.api_config.get("products", {}):
            QMessageBox.warning(self, "错误", f"产品 '{product_name}' 不存在于配置中")
            return

        self.current_product = product_name
        # 重置当前接口
        self.current_interface = None
        product_config = self.api_config["products"][product_name]

        # 更新定时任务下拉框
        self.update_schedule_tasks_combo(product_config)

        # 更新混合展示
        self.update_mixed_display(product_config)

        # 清空右侧栏
        self.clear_right_panel()

        # 无论是初始加载还是切换产品，都更新流水并生成测试数据
        self.update_request_id_and_reset_fields()

    def clear_right_panel(self):
        """清空右侧面板内容"""
        self.url_input.clear()
        self.request_body_edit.clear()
        self.response_body_edit.clear()
        # 发送请求按钮保持可用状态
        self.manual_request_btn.setEnabled(True)

    def update_schedule_tasks_combo(self, product_config):
        """更新定时任务下拉框"""
        self.schedule_combo.clear()

        schedule_tasks = product_config.get("schedule_tasks", [])
        if schedule_tasks:
            for task in schedule_tasks:
                self.schedule_combo.addItem(
                    f"{task['name']} (ID: {task['id']})",
                    (task["id"], task.get("jobGroup", "DEFAULT"))
                )
            self.execute_schedule_btn.setEnabled(True)
        else:
            self.schedule_combo.addItem("无定时任务")
            self.execute_schedule_btn.setEnabled(False)

    def update_mixed_display(self, product_config):
        """更新混合的接口和字段展示 - 每个元素独立自适应宽度，向左对齐"""
        # 清空现有内容
        while self.combined_layout.count():
            item = self.combined_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        self.field_inputs.clear()
        self.combo_boxes.clear()  # 清空下拉框字典
        self.sql_buttons.clear()  # 清空SQL按钮字典
        self.condition_displays.clear()  # 新增：清空条件显示控件字典
        self.formula_displays.clear()  # 新增：清空公式显示控件字典
        self.formula_configs.clear()  # 新增：清空公式配置字典

        # 获取布局配置
        layout_config = product_config.get("layout", [])
        interfaces_config = product_config.get("interfaces", {})
        sqls_config = product_config.get("sqls", {})  # 新增SQL配置

        # 按优先级排序
        sorted_layout = sorted(layout_config, key=lambda x: x.get("priority", 999))

        # 使用灵活的布局策略
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(35)  # 行间距,行高,高度
        main_layout.setContentsMargins(5, 10, 5, 10)  # 添加边距
        main_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # 修改：主布局左对齐

        current_row_layout = QHBoxLayout()
        current_row_layout.setSpacing(20)  # 更大的水平间距
        current_row_layout.setAlignment(Qt.AlignLeft)  # 修改：行布局左对齐

        # 每行最多显示的元素数量
        max_items_per_row = 4
        current_item_count = 0

        for item in sorted_layout:
            # 检查是否需要在UI中显示（仅对字段和下拉框类型）
            if item["type"] in ["field", "combo", "condition", "formula"]:  # 添加公式类型
                # 默认值为True，保持向后兼容
                show_in_ui = item.get("show_in_ui", True)
                if not show_in_ui:
                    # 不显示在前端，但仍然需要在对应的字典中记录
                    if item["type"] == "field" and item["key"] not in self.field_inputs:
                        # 创建隐藏的字段输入框，但不添加到UI
                        field_input = QLineEdit()
                        # 设置默认值
                        default_value = item.get("default", "")
                        if default_value:
                            field_input.setText(default_value)
                        self.field_inputs[item["key"]] = field_input

                    elif item["type"] == "combo" and item["key"] not in self.combo_boxes:
                        # 创建隐藏的下拉框，但不添加到UI
                        combo_box = NoWheelComboBox()
                        # 添加选项
                        options = item.get("options", [])
                        for option in options:
                            combo_box.addItem(option["text"], option["value"])

                        # 设置默认值
                        default_value = item.get("default", "")
                        if default_value:
                            # 在选项中查找默认值对应的索引
                            found_index = -1
                            for i in range(combo_box.count()):
                                if combo_box.itemData(i) == default_value:
                                    found_index = i
                                    break
                            if found_index >= 0:
                                combo_box.setCurrentIndex(found_index)
                            elif combo_box.count() > 0:
                                combo_box.setCurrentIndex(0)
                        self.combo_boxes[item["key"]] = combo_box

                    elif item["type"] == "condition" and item["key"] not in self.condition_displays:
                        # 创建隐藏的条件显示控件，但不添加到UI
                        condition_display = QLineEdit()
                        condition_display.setReadOnly(True)
                        # 初始显示值
                        condition_key = item["key"]
                        condition_value = self.get_condition_variable_value(condition_key)
                        if condition_value is not None:
                            condition_display.setText(str(condition_value))
                        self.condition_displays[condition_key] = condition_display

                    elif item["type"] == "formula" and item["key"] not in self.formula_displays:
                        # 新增：创建隐藏的公式显示控件，但不添加到UI
                        formula_display = QLineEdit()
                        formula_display.setReadOnly(True)
                        formula_display.setStyleSheet("background-color: #f0f0f0; color: #666;")
                        self.formula_displays[item["key"]] = formula_display

                        # 保存公式配置
                        formula_key = item["key"]
                        self.formula_configs[formula_key] = {
                            "formula": item.get("formula", ""),
                            "formula_type": item.get("formula_type", "numeric"),  # 新增公式类型
                            "dependencies": self.extract_formula_dependencies(item.get("formula", ""))
                        }
                        # 初始计算公式值
                        self.calculate_formula(formula_key)

                    # 跳过UI显示，继续下一个元素
                    continue

            if current_item_count >= max_items_per_row:
                # 当前行已满，创建新行
                main_layout.addLayout(current_row_layout)
                current_row_layout = QHBoxLayout()
                current_row_layout.setSpacing(12)
                current_row_layout.setAlignment(Qt.AlignLeft)  # 修改：新行也左对齐
                current_item_count = 0

            if item["type"] == "field":
                # 创建字段控件 - 根据内容自适应宽度
                field_label = QLabel(item["label"])
                field_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                field_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 标签固定宽度

                field_input = QLineEdit()
                # 智能设置默认值：优先使用变量池中的值，其次使用配置的默认值
                field_key = item["key"]
                # 始终使用变量池中的最新值（如果存在），否则使用默认值
                if field_key in self.variable_pool:
                    # 使用变量池中的最新值
                    field_value = self.variable_pool[field_key]
                    field_input.setText(str(field_value))
                    print(f"字段 '{field_key}' 初始化为变量池值: {field_value}")
                else:
                    # 使用配置的默认值（支持变量替换）
                    default_value = item.get("default", "")
                    if default_value:
                        processed_default = self.replace_variables_in_string(default_value)

                        # 处理字段数据类型
                        data_type = item.get("data_type", "string")
                        if data_type == "int":
                            try:
                                int(processed_default)
                            except ValueError:
                                pass
                        elif data_type == "float":
                            try:
                                float(processed_default)
                            except ValueError:
                                pass

                        field_input.setText(processed_default)

                # 设置固定的大小策略，不拉伸
                field_input.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                field_input.setMinimumWidth(120)
                field_input.setMaximumWidth(250)  # 所有字段统一最大宽度

                # 根据内容调整宽度
                self.adjust_field_width(field_input, field_input.text())
                field_input.textChanged.connect(lambda text, field=field_input: self.adjust_field_width(field, text))

                self.field_inputs[item["key"]] = field_input

                # 监听字段变化，实时更新变量池
                field_input.textChanged.connect(lambda text, key=field_key:
                                                self.on_field_changed(key, text))

                self.field_inputs[field_key] = field_input

                # 添加到当前行
                current_row_layout.addWidget(field_label)
                current_row_layout.addWidget(field_input)

            elif item["type"] == "combo":  # 处理下拉框类型
                # 创建下拉框控件 - 根据内容自适应宽度
                combo_label = QLabel(item["label"])
                combo_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                combo_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 标签固定宽度

                combo_box = NoWheelComboBox()
                # 添加选项
                options = item.get("options", [])
                for option in options:
                    combo_box.addItem(option["text"], option["value"])

                # 设置固定的大小策略，不拉伸
                combo_box.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                combo_box.setMinimumWidth(120)  # 设置最小宽度
                combo_box.setMaximumWidth(250)  # 设置最大宽度

                # 设置默认值 - 修复：使用配置的默认值而不是第一个选项
                combo_key = item["key"]
                # 始终使用变量池中的最新值（如果存在），否则使用默认值
                if combo_key in self.variable_pool:
                    # 使用变量池中的最新值
                    combo_value = self.variable_pool[combo_key]
                    # 在下拉框中查找匹配的选项
                    found_index = -1
                    for i in range(combo_box.count()):
                        if combo_box.itemData(i) == str(combo_value):
                            found_index = i
                            break
                    if found_index >= 0:
                        combo_box.setCurrentIndex(found_index)
                        print(f"下拉框 '{combo_key}' 初始化为变量池值: {combo_value}")
                else:
                    # 使用配置的默认值（支持变量替换）
                    default_value = item.get("default", "")
                    if default_value:
                        processed_default = self.replace_variables_in_string(default_value)

                        # 在选项中查找默认值对应的索引
                        found_index = -1
                        for i in range(combo_box.count()):
                            if combo_box.itemData(i) == processed_default:
                                found_index = i
                                break

                        # 如果找到了对应的值，设置当前索引
                        if found_index >= 0:
                            combo_box.setCurrentIndex(found_index)
                        else:
                            # 如果没有找到，尝试使用显示文本匹配
                            for i in range(combo_box.count()):
                                if combo_box.itemText(i) == processed_default:
                                    combo_box.setCurrentIndex(i)
                                    break
                            # 如果还是没有找到，保持第一个选项
                            if combo_box.count() > 0 and combo_box.currentIndex() < 0:
                                combo_box.setCurrentIndex(0)

                # 根据内容调整宽度
                self.adjust_combo_width(combo_box)
                combo_box.currentTextChanged.connect(lambda text, combo=combo_box: self.adjust_combo_width(combo))

                self.combo_boxes[item["key"]] = combo_box

                # 监听下拉框变化，实时更新变量池
                combo_box.currentIndexChanged.connect(lambda index, key=combo_key, combo=combo_box:
                                                      self.on_combo_changed(key, combo))

                self.combo_boxes[combo_key] = combo_box

                # 添加到当前行
                current_row_layout.addWidget(combo_label)
                current_row_layout.addWidget(combo_box)

            elif item["type"] == "interface":
                # 创建接口按钮 - 根据文本内容自适应宽度
                interface_name = item["name"]
                if interface_name in interfaces_config:
                    interface_btn = QPushButton(interface_name)
                    # 设置固定的大小策略，不拉伸
                    interface_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                    interface_btn.setMinimumWidth(80)  # 设置最小宽度
                    interface_btn.setMaximumWidth(200)  # 设置最大宽度

                    # 根据按钮文本调整宽度
                    self.adjust_button_width(interface_btn)

                    interface_btn.clicked.connect(lambda checked, name=interface_name: self.on_interface_clicked(name))

                    # 添加到当前行
                    current_row_layout.addWidget(interface_btn)

            elif item["type"] == "sql":  # 新增SQL类型处理
                # 创建SQL按钮 - 根据文本内容自适应宽度
                sql_name = item["name"]
                if sql_name in sqls_config:
                    sql_btn = QPushButton(sql_name)
                    # 设置固定的大小策略，不拉伸
                    sql_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                    sql_btn.setMinimumWidth(80)  # 设置最小宽度
                    sql_btn.setMaximumWidth(200)  # 设置最大宽度

                    # 根据按钮文本调整宽度
                    self.adjust_button_width(sql_btn)

                    sql_btn.clicked.connect(lambda checked, name=sql_name: self.on_sql_clicked(name))

                    # 保存SQL按钮引用
                    self.sql_buttons[sql_name] = sql_btn

                    # 添加到当前行
                    current_row_layout.addWidget(sql_btn)

            elif item["type"] == "condition":

                # 创建条件控件 - 根据文本内容自适应宽度
                condition_label = QLabel(item["label"])
                condition_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                condition_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

                # 条件字段显示当前映射的值
                condition_display = QLineEdit()
                condition_display.setReadOnly(True)  # 只读显示
                condition_display.setStyleSheet("background-color: #f0f0f0; color: #666;")

                # 设置固定的大小策略，不拉伸
                condition_display.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                condition_display.setMinimumWidth(120)
                condition_display.setMaximumWidth(250)

                # 初始显示值
                condition_key = item["key"]
                condition_value = self.get_condition_variable_value(condition_key)
                if condition_value is not None:
                    condition_display.setText(str(condition_value))

                # 保存条件显示控件引用，以便后续更新
                self.condition_displays[condition_key] = condition_display

                # 添加到当前行
                current_row_layout.addWidget(condition_label)
                current_row_layout.addWidget(condition_display)


            elif item["type"] == "formula":
                # 创建公式控件 - 只读显示计算结果
                formula_label = QLabel(item["label"])
                formula_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                formula_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                formula_display = QLineEdit()
                formula_display.setReadOnly(True)
                formula_display.setStyleSheet("background-color: #f0f0f0; color: #666;")

                # 设置固定的大小策略，不拉伸
                formula_display.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                formula_display.setMinimumWidth(120)
                formula_display.setMaximumWidth(250)

                # 保存公式显示控件引用和配置
                formula_key = item["key"]
                self.formula_displays[formula_key] = formula_display
                self.formula_configs[formula_key] = {
                    "formula": item.get("formula", ""),
                    "formula_type": item.get("formula_type", "numeric"),  # 新增公式类型
                    "dependencies": self.extract_formula_dependencies(item.get("formula", ""))
                }

                # 初始计算公式值
                self.calculate_formula(formula_key)

                # # 根据内容调整宽度
                # self.adjust_field_width(formula_display, formula_display.text())

                # 添加到当前行
                current_row_layout.addWidget(formula_label)
                current_row_layout.addWidget(formula_display)

            current_item_count += 1

        # 添加最后一行
        if current_row_layout.count() > 0:
            main_layout.addLayout(current_row_layout)

        # 将主部件添加到滚动区域
        self.combined_layout.addWidget(main_widget)

        # 初始调整所有元素的宽度
        self.adjust_all_elements_width()

        # 使用自定义的布局部件
        self.combined_layout.addWidget(WidthAwareWidget(main_widget, self))

    def adjust_all_elements_width_delayed(self):
        """延迟调整所有元素的宽度 - 修复：添加条件字段显示框的宽度调整"""
        # 调整所有字段输入框的宽度
        for field_key, field_input in self.field_inputs.items():
            text = field_input.text()
            self.adjust_field_width(field_input, text)

        # 调整所有下拉框的宽度
        for combo_box in self.combo_boxes.values():
            self.adjust_combo_width(combo_box)

        # 调整所有按钮的宽度（包括接口按钮和SQL按钮）
        for i in range(self.combined_layout.count()):
            item = self.combined_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, QPushButton):
                    self.adjust_button_width(widget)

        # 新增：调整所有条件字段显示控件的宽度
        for condition_key, condition_display in self.condition_displays.items():
            text = condition_display.text()
            self.adjust_field_width(condition_display, text)

        # 新增：调整所有公式显示控件的宽度
        for formula_key, formula_display in self.formula_displays.items():
            text = formula_display.text()
            self.adjust_field_width(formula_display, text)

    def adjust_field_width(self, field_input, text):
        """根据输入框内容调整宽度 - 统一处理所有字段"""
        # 计算文本宽度
        font_metrics = field_input.fontMetrics()
        text_width = font_metrics.horizontalAdvance(text) if text else 0

        # 设置宽度：有内容时根据内容调整，无内容时使用固定宽度
        if text:
            # 有内容时根据内容宽度调整，加上一些边距
            content_width = text_width + 30  # 增加边距
            # 限制在最小和最大宽度之间
            new_width = max(80, min(content_width, 250))
        else:
            # 无内容时使用固定宽度
            new_width = 120

        field_input.setFixedWidth(new_width)

    def adjust_combo_width(self, combo_box):
        """根据下拉框内容调整宽度 - 统一算法"""
        current_text = combo_box.currentText()
        font_metrics = combo_box.fontMetrics()
        text_width = font_metrics.horizontalAdvance(current_text) if current_text else 0

        if current_text:
            # 有内容时根据内容宽度调整，加上下拉箭头和边距
            content_width = text_width + 35  # 增加边距和下拉箭头空间
            new_width = max(120, min(content_width, 250))
        else:
            # 无内容时使用固定宽度
            new_width = 120

        combo_box.setFixedWidth(new_width)

    def adjust_button_width(self, button):
        """根据按钮文本调整宽度 - 统一算法"""
        text = button.text()
        font_metrics = button.fontMetrics()
        text_width = font_metrics.horizontalAdvance(text) if text else 0

        # 根据文本宽度调整，加上边距
        content_width = text_width + 42  # 增加边距（控制按钮宽度）
        new_width = max(80, min(content_width, 200))

        button.setFixedWidth(new_width)

    def adjust_all_elements_width(self):
        """初始调整所有元素的宽度 - 修复：添加条件字段显示框的宽度调整"""
        # 调整所有字段输入框的宽度
        for field_input in self.field_inputs.values():
            text = field_input.text()
            self.adjust_field_width(field_input, text)

        # 调整所有下拉框的宽度
        for combo_box in self.combo_boxes.values():
            self.adjust_combo_width(combo_box)

        # 调整所有按钮的宽度（包括接口按钮和SQL按钮）
        for i in range(self.combined_layout.count()):
            item = self.combined_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, QPushButton):
                    self.adjust_button_width(widget)

        # 新增：调整所有条件字段显示控件的宽度
        for condition_display in self.condition_displays.values():
            text = condition_display.text()
            self.adjust_field_width(condition_display, text)

        # 新增：调整所有公式显示控件的宽度
        for formula_display in self.formula_displays.values():
            text = formula_display.text()
            self.adjust_field_width(formula_display, text)

    def on_interface_clicked(self, interface_name):
        """接口按钮点击事件 - 优化：点击时清空响应体"""
        if not self.current_product:
            QMessageBox.warning(self, "警告", "请先选择产品")
            return

        # 清空响应体内容
        self.response_body_edit.clear()

        self.current_interface = interface_name
        product_config = self.api_config["products"][self.current_product]
        interface_config = product_config["interfaces"][interface_name]

        # 更新 URL 输入框（并进行变量替换）
        original_url = interface_config["url"]
        replaced_url = self.replace_variables_in_string(original_url)
        self.url_input.setText(replaced_url)

        # 生成请求体
        request_body = self.generate_request_body(interface_config)
        self.request_body_edit.setPlainText(json.dumps(request_body, ensure_ascii=False, indent=2))

        # 启用手动请求按钮
        self.manual_request_btn.setEnabled(True)

        # 如果启用了发送请求，直接发送请求
        if self.auto_request_checkbox.isChecked():
            self.send_request(interface_config, request_body)
        else:
            # 如果不发送请求，确保响应体是空的
            self.response_body_edit.setPlainText("")
            # 添加提示信息
            self.response_body_edit.setPlaceholderText("点击'发送请求'按钮发送请求...")

    def on_sql_clicked(self, sql_name):
        """SQL按钮点击事件 - 优化：点击时清空响应体"""
        if not self.current_product:
            QMessageBox.warning(self, "警告", "请先选择产品")
            return

        try:
            # 清空响应体内容
            self.response_body_edit.clear()
            # 添加提示信息
            self.response_body_edit.setPlaceholderText(f"正在执行SQL: {sql_name}...")

            product_config = self.api_config["products"][self.current_product]
            sql_config = product_config["sqls"][sql_name]

            # 执行SQL查询
            self.execute_sql_query(sql_name, sql_config)

        except KeyError as e:
            QMessageBox.warning(self, "错误", f"SQL配置不存在: {sql_name}")
            # 错误时也清空响应体
            self.response_body_edit.setPlainText("")
            self.response_body_edit.setPlaceholderText("响应内容将显示在这里...")
            return

    def execute_sql_query(self, sql_name, sql_config):
        """执行SQL查询"""
        try:
            # 获取数据库连接参数
            db_config = sql_config["database"]
            sql_statement = sql_config["sql"]

            # 替换SQL中的变量
            processed_sql = self.replace_variables_in_string(sql_statement)

            # 验证SQL是否为SELECT语句
            if not re.match(r'^\s*SELECT\s', processed_sql, re.IGNORECASE):
                Toast.warning(self, "警告", "仅支持SELECT查询语句")
                return

            # 在工作线程中执行SQL
            self.sql_worker = SQLWorker(sql_name, db_config, processed_sql)
            self.sql_worker.finished.connect(lambda query_name, message, result_data:
                                             self.on_sql_finished(sql_name, sql_config, result_data))
            self.sql_worker.error.connect(lambda query_name, error_message:
                                          self.on_sql_error(sql_name, error_message))
            self.sql_worker.start()

            # 显示加载状态
            self.response_body_edit.setPlainText(f"执行SQL查询中: {sql_name}...")

        except Exception as e:
            Toast.critical(self, "错误", f"执行SQL失败: {str(e)}")
            # 确保错误时也清空响应体
            self.response_body_edit.setPlainText("")

    def on_sql_finished(self, sql_name, sql_config, result_data):
        """SQL查询完成"""
        try:
            if not result_data:
                self.response_body_edit.setPlainText("SQL查询成功，但未返回数据")
                return

            # 显示查询结果
            formatted_result = json.dumps(result_data, ensure_ascii=False, indent=2)
            self.response_body_edit.setPlainText(f"SQL查询成功:\n{formatted_result}")

            # 将查询结果存储到变量池中，供请求体使用（会强制覆盖字段值）
            self.process_sql_output(sql_name, sql_config, result_data)

        except Exception as e:
            self.response_body_edit.setPlainText(f"处理SQL结果时出错: {str(e)}")

    def on_sql_error(self, sql_name, error_message):
        """SQL查询错误"""
        self.response_body_edit.setPlainText(f"SQL查询失败:\n{error_message}")

    def process_sql_output(self, sql_name, sql_config, result_data):
        """处理SQL输出结果，填充到变量池并更新相关字段 - 始终覆盖为最新值"""
        if not result_data:
            return

        # 获取第一条记录（假设只需要第一条记录）
        first_record = result_data[0] if result_data else {}

        # 获取输出字段配置
        output_fields = sql_config.get("output_fields", [])

        print(f"处理SQL '{sql_name}' 的输出结果，共 {len(output_fields)} 个输出字段")

        # 存储SQL输出变量到变量池（直接使用字段名作为变量名）
        for field_config in output_fields:
            field_name = field_config["field"]
            if field_name in first_record:
                # 直接使用字段名作为变量名
                variable_name = field_name
                old_value = self.variable_pool.get(variable_name, "未设置")
                new_value = first_record[field_name]
                self.variable_pool[variable_name] = new_value

                print(f"更新变量池: '{variable_name}' 从 '{old_value}' 到 '{new_value}'")

        # 自动填充到使用这些变量的字段输入框（始终覆盖）
        self.auto_fill_sql_variables_to_fields(sql_name, first_record)

        # 修复：无论是否勾选发送请求，都强制刷新请求体
        self.force_refresh_request_body()

    def auto_fill_sql_variables_to_fields(self, sql_name, sql_result):
        """将SQL输出结果自动填充到使用这些变量的字段输入框 - 始终覆盖为最新值"""
        if not self.current_product:
            return

        try:
            product_config = self.api_config["products"][self.current_product]
            layout_config = product_config.get("layout", [])

            print(f"开始自动填充SQL '{sql_name}' 的结果到相关字段")

            # 首先填充与SQL输出字段名完全匹配的字段
            for item in layout_config:
                if item["type"] in ["field", "combo"]:
                    field_key = item["key"]

                    # 检查这个字段是否在SQL结果中
                    if field_key in sql_result:
                        field_value = sql_result[field_key]
                        self.fill_field_with_sql_result(field_key, item, field_value)

            # 然后检查是否有字段的默认值引用了SQL变量
            self.fill_fields_with_sql_variables(sql_name, sql_result)

        except Exception as e:
            print(f"自动填充SQL变量到字段时出错: {str(e)}")

    def fill_fields_with_sql_variables(self, sql_name, sql_result):
        """填充使用SQL变量的字段"""
        try:
            product_config = self.api_config["products"][self.current_product]
            layout_config = product_config.get("layout", [])

            for item in layout_config:
                if item["type"] in ["field", "combo"]:
                    field_key = item["key"]
                    default_value = item.get("default", "")

                    # 检查默认值中是否包含SQL变量
                    if default_value and f"{{{sql_name}" in default_value:
                        # 构建替换后的值
                        filled_value = self.replace_sql_variables_in_default(default_value, sql_name, sql_result)

                        if filled_value != default_value:  # 如果有替换发生
                            if field_key in self.field_inputs:
                                self.field_inputs[field_key].setText(filled_value)
                                print(f"通过变量替换更新字段 '{field_key}' 值为: {filled_value}")
                            elif field_key in self.combo_boxes:
                                combo_box = self.combo_boxes[field_key]
                                # 在下拉框中查找匹配的选项
                                found_index = -1
                                for i in range(combo_box.count()):
                                    if combo_box.itemData(i) == filled_value:
                                        found_index = i
                                        break
                                if found_index >= 0:
                                    combo_box.setCurrentIndex(found_index)
                                    print(f"通过变量替换更新下拉框 '{field_key}' 为: {filled_value}")

        except Exception as e:
            print(f"填充使用SQL变量的字段时出错: {str(e)}")

    def replace_sql_variables_in_default(self, default_value, sql_name, sql_result):
        """替换默认值中的SQL变量"""
        processed_value = default_value

        # 匹配 {sql_name_field} 格式的变量
        sql_var_pattern = r'\{(' + re.escape(sql_name) + r'_\w+)\}'
        matches = re.findall(sql_var_pattern, processed_value)

        for sql_var in matches:
            # 提取字段名（去掉sql_name_前缀）
            field_name = sql_var.replace(f"{sql_name}_", "")

            # 从SQL结果中获取值
            if field_name in sql_result:
                field_value = sql_result[field_name]
                processed_value = processed_value.replace(f"{{{sql_var}}}", str(field_value))

        return processed_value

    def fill_field_with_sql_result(self, field_key, field_config, field_value):
        """使用SQL结果填充特定字段 - 始终覆盖为最新值"""
        try:
            # 如果字段在输入框中，直接更新输入框的值（始终覆盖）
            if field_key in self.field_inputs:
                field_input = self.field_inputs[field_key]
                field_input.setText(str(field_value))
                print(f"更新字段 '{field_key}' 值为: {field_value}")

            # 如果字段在下拉框中，尝试匹配下拉框选项（始终覆盖）
            elif field_key in self.combo_boxes:
                combo_box = self.combo_boxes[field_key]

                # 在下拉框中查找匹配的选项
                found_index = -1
                for i in range(combo_box.count()):
                    if combo_box.itemData(i) == str(field_value):
                        found_index = i
                        break

                # 如果找到匹配项，设置当前选项
                if found_index >= 0:
                    combo_box.setCurrentIndex(found_index)
                    print(f"更新下拉框 '{field_key}' 为: {field_value}")
                else:
                    # 如果没有找到匹配项，尝试在显示文本中查找
                    for i in range(combo_box.count()):
                        if combo_box.itemText(i) == str(field_value):
                            combo_box.setCurrentIndex(i)
                            print(f"更新下拉框 '{field_key}' 为: {field_value} (通过显示文本匹配)")
                            break

        except Exception as e:
            print(f"更新字段 {field_key} 时出错: {str(e)}")

    def generate_request_body(self, interface_config):
        """生成请求体 - 支持类型转换、条件模板和变量池"""
        # 检查是否存在条件模板
        if "conditional_body" in interface_config:
            body_template = self.process_conditional_body(interface_config["conditional_body"])
        else:
            body_template = interface_config["body_template"]

        # 获取字段类型映射配置
        field_types = interface_config.get("field_types", {})

        # 递归处理模板，使用新的变量替换方法
        def process_template(template):
            if isinstance(template, dict):
                result = {}
                for key, value in template.items():
                    result[key] = process_template(value)
                return result
            elif isinstance(template, list):
                return [process_template(item) for item in template]
            elif isinstance(template, str):
                # 使用增强的变量替换方法
                return self.replace_variables_in_string(template)
            else:
                return template

        # 先进行模板替换
        request_body = process_template(body_template)

        # 然后进行类型转换
        return self.convert_field_types(request_body, field_types)

    def process_conditional_body(self, conditional_config):
        """处理条件模板，根据字段值选择对应的请求体模板"""
        field_key = conditional_config["field"]
        cases = conditional_config["cases"]

        # 获取字段的当前值
        field_value = None
        if field_key in self.field_inputs:
            field_value = self.field_inputs[field_key].text()
        elif field_key in self.combo_boxes:
            field_value = self.combo_boxes[field_key].currentData()

        # 根据字段值选择对应的模板
        if field_value in cases:
            return cases[field_value]
        else:
            # 如果没有匹配的case，返回第一个case的模板
            first_case = next(iter(cases.values()))
            return first_case

    def convert_field_types(self, data, field_types):
        """递归转换字段类型"""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                # 如果该字段在类型映射中，进行类型转换
                if key in field_types:
                    field_type = field_types[key]
                    result[key] = self.convert_value_type(value, field_type)
                else:
                    # 递归处理嵌套结构
                    result[key] = self.convert_field_types(value, field_types)
            return result
        elif isinstance(data, list):
            return [self.convert_field_types(item, field_types) for item in data]
        else:
            return data

    def convert_value_type(self, value, field_type):
        """转换单个值的类型"""
        if field_type == "int":
            try:
                # 尝试转换为整数
                return int(value)
            except (ValueError, TypeError):
                # 如果转换失败，返回原始值
                return value
        elif field_type == "float":
            try:
                # 尝试转换为浮点数
                return float(value)
            except (ValueError, TypeError):
                return value
        elif field_type == "bool":
            # 转换为布尔值
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "y")
            else:
                return bool(value)
        else:
            # 未知类型，返回原始值
            return value

    def send_manual_request(self):
        """手动发送请求 - 支持独立请求和产品接口请求"""
        # 获取用户输入的 URL
        user_url = self.url_input.text().strip()
        if not user_url:
            Toast.info(self, '请输入URL')
            return

        # 获取请求体
        request_body_text = self.request_body_edit.toPlainText().strip()
        if not request_body_text:
            Toast.info(self, '请求体不能为空')
            return

        # 清空响应体内容
        self.response_body_edit.clear()

        try:
            request_body = json.loads(request_body_text)
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "格式错误", f"请求体格式错误: {str(e)}")
            return

        # 判断是产品接口请求还是独立手动请求
        if self.current_interface and self.current_product:
            # 产品接口请求：使用产品配置
            self.send_product_interface_request(user_url, request_body)
        else:
            # 独立手动请求：使用基本配置
            self.send_standalone_request(user_url, request_body)

    def send_product_interface_request(self, user_url, request_body):
        """发送产品接口请求（使用产品配置）"""
        try:
            product_config = self.api_config["products"][self.current_product]
            interface_config = product_config["interfaces"][self.current_interface].copy()

            # 使用用户修改的 URL
            interface_config["url"] = user_url

            # 发送请求（使用产品级别的加解密配置）
            self.send_request(interface_config, request_body)
        except KeyError as e:
            # 如果接口配置不存在，降级为独立请求
            print(f"接口配置不存在，降级为独立请求: {str(e)}")
            self.send_standalone_request(user_url, request_body)

    def send_standalone_request(self, user_url, request_body):
        """发送独立手动请求（不使用产品配置）"""
        # 构建基本的请求配置
        interface_config = {
            "url": user_url,
            "method": "POST",
            "headers": {
                "Content-Type": "application/json"
            },
            "enable_encryption": False  # 手动请求默认不启用加解密
        }

        # 发送请求（不启用加解密）
        self.send_request(interface_config, request_body)

    def send_request(self, interface_config, request_body):
        """发送 API 请求"""
        # 先对 URL 和 headers 进行变量替换
        url = self.replace_variables_in_string(interface_config["url"])
        method = interface_config.get("method", "POST")

        # 对 headers 进行变量替换
        headers = {}
        for key, value in interface_config.get("headers", {}).items():
            if isinstance(value, str):
                headers[key] = self.replace_variables_in_string(value)
            else:
                headers[key] = value

        # 检查是否启用加解密（默认启用，但可以针对特定接口禁用）
        enable_encryption = interface_config.get("enable_encryption", True)
        if not enable_encryption:
            # 对于不需要加解密的接口（如文件上传），强制禁用加解密
            encrypt_url = None
            decrypt_url = None
        else:
            # 直接从产品配置中获取加解密配置，不再依赖UI控件
            encrypt_url = None
            decrypt_url = None
            if self.current_product and self.current_product in self.api_config["products"]:
                product_config = self.api_config["products"][self.current_product]
                # 检查产品是否启用了加解密
                if product_config.get("enable_encryption", False):
                    encrypt_url = product_config.get("encrypt_url")
                    decrypt_url = product_config.get("decrypt_url")

        # 在工作线程中执行请求
        self.worker = ApiWorker(url, method, headers, request_body, encrypt_url, decrypt_url)
        self.worker.finished.connect(self.on_request_finished)
        self.worker.error.connect(self.on_request_error)
        self.worker.start()

        # 显示加载状态
        self.response_body_edit.setPlainText("请求中...")

    def replace_variables_in_string(self, text):
        """替换字符串中的变量占位符 - 增强版：支持JSONPath中的数组索引转换（用户输入1代表索引0）"""
        if not isinstance(text, str):
            return text

        processed = text

        # 特殊处理：如果是JSONPath并且包含数组索引，先处理数组索引
        if '[' in processed and ']' in processed:
            # 匹配数组索引中的变量，如 data[{rpyTerm}]
            array_index_pattern = r'\[(\{(\w+)\})\]'

            def replace_array_index(match):
                var_name = match.group(2)  # 提取变量名
                if var_name in self.variable_pool:
                    var_value = self.variable_pool[var_name]
                    try:
                        # 用户输入1代表索引0，所以需要减1
                        index = int(var_value) - 1
                        if index < 0:
                            print(f"警告: 变量 '{var_name}' 的值 {var_value} 小于1，使用索引0")
                            index = 0
                        return f"[{index}]"
                    except (ValueError, TypeError):
                        # 如果不是数字，保持原样
                        print(f"警告: 变量 '{var_name}' 的值 '{var_value}' 不是有效数字")
                        return match.group(0)
                else:
                    # 变量不存在，尝试获取默认值
                    default_value = self.get_variable_default_value(var_name)
                    if default_value is not None:
                        try:
                            # 用户输入1代表索引0，所以需要减1
                            index = int(default_value) - 1
                            if index < 0:
                                print(f"警告: 变量 '{var_name}' 的默认值 {default_value} 小于1，使用索引0")
                                index = 0
                            return f"[{index}]"
                        except (ValueError, TypeError):
                            # 如果不是数字，保持原样
                            print(f"警告: 变量 '{var_name}' 的默认值 '{default_value}' 不是有效数字")
                            return match.group(0)
                    else:
                        # 默认值也没有，使用索引0
                        print(f"警告: 变量 '{var_name}' 不存在且无默认值，使用索引0")
                        return "[0]"

            # 替换数组索引中的变量
            processed = re.sub(array_index_pattern, replace_array_index, processed)

        # 1. 处理复杂模板（日期时间、随机数等）
        if any(pattern in processed for pattern in
               ["{dateTime", "{date", "{time", "{random:"]):
            processed = TemplateProcessor.process_template(processed)

        # 然后处理其他类型的变量（与之前相同）
        # 2. 处理Base64变量
        for var_key in self.BASE64_VARIABLE_KEYS:
            if var_key in self.variable_pool:
                placeholder = "{" + var_key + "}"
                if placeholder in processed:
                    var_value = self.variable_pool[var_key]
                    str_value = str(var_value) if var_value is not None else ""
                    processed = processed.replace(placeholder, str_value)
                    print(f"替换Base64变量 {var_key}: 长度={len(str_value)}")

        # 3. 处理请求ID
        if "{request_id}" in processed:
            request_id_value = self.request_id_input.text()
            processed = processed.replace("{request_id}", request_id_value)
            print(f"替换request_id: {request_id_value}")

        # 4. 处理普通字段（从输入框获取当前值）
        for field_key, field_input in self.field_inputs.items():
            placeholder = "{" + field_key + "}"
            if placeholder in processed:
                field_value = field_input.text()
                processed = processed.replace(placeholder, field_value)
                print(f"替换字段 {field_key}: {field_value}")

        # 5. 处理下拉框字段
        for combo_key, combo_box in self.combo_boxes.items():
            placeholder = "{" + combo_key + "}"
            if placeholder in processed:
                combo_value = combo_box.currentData()
                processed = processed.replace(placeholder, combo_value)
                print(f"替换下拉框 {combo_key}: {combo_value}")

        # 6. 处理SQL输出变量（从变量池获取，使用字段名作为变量名）
        # 匹配所有变量占位符
        all_var_pattern = r'\{(\w+)\}'
        all_matches = re.findall(all_var_pattern, processed)

        for var_name in all_matches:
            # 如果变量在变量池中且不在其他已处理的类别中，则替换
            if (var_name in self.variable_pool and
                    var_name not in self.BASE64_VARIABLE_KEYS and
                    var_name != "request_id" and
                    var_name not in self.field_inputs and
                    var_name not in self.combo_boxes):
                var_value = self.variable_pool[var_name]
                str_value = str(var_value) if var_value is not None else ""
                processed = processed.replace(f"{{{var_name}}}", str_value)
                print(f"替换SQL变量 {var_name}: {str_value}")
            elif (var_name not in self.variable_pool and
                  var_name not in self.BASE64_VARIABLE_KEYS and
                  var_name != "request_id" and
                  var_name not in self.field_inputs and
                  var_name not in self.combo_boxes):
                # 变量不在变量池中，尝试获取默认值
                default_value = self.get_variable_default_value(var_name)
                if default_value is not None:
                    processed = processed.replace(f"{{{var_name}}}", str(default_value))
                    print(f"替换默认值变量 {var_name}: {default_value}")
                else:
                    # 默认值也没有，使用索引0或空字符串
                    # 如果是数组索引相关的变量，使用"0"
                    if var_name.endswith(('_index', '_idx', 'index', 'idx')):
                        processed = processed.replace(f"{{{var_name}}}", "0")
                        print(f"替换缺失变量 {var_name} 为索引: 0")
                    else:
                        processed = processed.replace(f"{{{var_name}}}", "")
                        print(f"替换缺失变量 {var_name} 为空字符串")

        # 7. 处理条件变量（在普通变量之后处理）
        condition_var_pattern = r'\{(\w+)\}'
        condition_matches = re.findall(condition_var_pattern, processed)

        for var_name in condition_matches:
            # 如果变量已经被其他类型处理过，跳过
            if (var_name in self.BASE64_VARIABLE_KEYS or
                    var_name == "request_id" or
                    var_name in self.field_inputs or
                    var_name in self.combo_boxes or
                    var_name in self.variable_pool):
                continue

            # 检查是否是条件变量
            condition_value = self.get_condition_variable_value(var_name)
            if condition_value is not None:
                processed = processed.replace(f"{{{var_name}}}", str(condition_value))
                print(f"替换条件变量 {var_name}: {condition_value}")

        print(f"替换后的文本: {processed}")
        return processed

    def get_condition_variable_value(self, condition_key):
        """获取条件变量的值 - 修正：正确处理未映射的情况"""
        if not self.current_product:
            return None

        try:
            product_config = self.api_config["products"][self.current_product]
            layout_config = product_config.get("layout", [])

            # 查找条件配置
            condition_config = None
            for item in layout_config:
                if item.get("type") == "condition" and item.get("key") == condition_key:
                    condition_config = item
                    break

            if not condition_config:
                return None

            # 获取条件字段的当前值
            condition_field_key = condition_config.get("condition_field")
            if not condition_field_key:
                return None

            # 从下拉框获取条件字段的当前值
            condition_field_value = None
            if condition_field_key in self.combo_boxes:
                combo_box = self.combo_boxes[condition_field_key]
                condition_field_value = combo_box.currentData()

            if not condition_field_value:
                return None

            # 根据条件字段值查找对应的变量字段
            mappings = condition_config.get("mappings", {})
            variable_field_key = mappings.get(condition_field_value)

            # 如果没有映射，返回空字符串
            if not variable_field_key:
                return ""

            # 获取变量字段的值
            variable_value = None
            if variable_field_key in self.field_inputs:
                variable_value = self.field_inputs[variable_field_key].text()
            elif variable_field_key in self.combo_boxes:
                combo_box = self.combo_boxes[variable_field_key]
                variable_value = combo_box.currentData()
            elif variable_field_key in self.variable_pool:
                variable_value = self.variable_pool[variable_field_key]

            return variable_value

        except Exception as e:
            print(f"获取条件变量 {condition_key} 值时出错: {str(e)}")
            return None

    def get_variable_default_value(self, var_name):
        """获取变量的默认值"""
        if not self.current_product:
            return None

        try:
            product_config = self.api_config["products"][self.current_product]
            layout_config = product_config.get("layout", [])

            # 在布局配置中查找该变量的默认值
            for item in layout_config:
                if item["type"] in ["field", "combo"] and item["key"] == var_name:
                    default_value = item.get("default", "")
                    if default_value:
                        # 对默认值进行变量替换（避免循环依赖）
                        return self.replace_variables_in_string_simple(default_value)
                    break

            return None
        except Exception as e:
            print(f"获取变量 {var_name} 默认值时出错: {str(e)}")
            return None

    def replace_variables_in_string_simple(self, text):
        """简化版的变量替换，避免循环依赖"""
        if not isinstance(text, str):
            return text

        processed = text

        # 只处理最基本的变量（避免递归调用）
        # 1. 处理Base64变量
        for var_key in self.BASE64_VARIABLE_KEYS:
            if var_key in self.variable_pool:
                placeholder = "{" + var_key + "}"
                if placeholder in processed:
                    var_value = self.variable_pool[var_key]
                    str_value = str(var_value) if var_value is not None else ""
                    processed = processed.replace(placeholder, str_value)

        # 2. 处理请求ID
        if "{request_id}" in processed:
            request_id_value = self.request_id_input.text()
            processed = processed.replace("{request_id}", request_id_value)

        # 3. 处理普通字段
        for field_key, field_input in self.field_inputs.items():
            placeholder = "{" + field_key + "}"
            if placeholder in processed:
                field_value = field_input.text()
                processed = processed.replace(placeholder, field_value)

        # 4. 处理下拉框字段
        for combo_key, combo_box in self.combo_boxes.items():
            placeholder = "{" + combo_key + "}"
            if placeholder in processed:
                combo_value = combo_box.currentData()
                processed = processed.replace(placeholder, combo_value)

        return processed

    def recursive_replace_variables(self, text, current_depth=0, max_depth=3):
        """递归替换嵌套变量"""
        if current_depth >= max_depth:
            return text

        # 检查是否还有变量占位符
        var_pattern = r'\{(\w+)\}'
        matches = re.findall(var_pattern, text)

        if not matches:
            return text

        processed = text
        for var_name in matches:
            # 尝试从各个来源获取变量值
            var_value = None

            # 从变量池获取
            if var_name in self.variable_pool:
                var_value = self.variable_pool[var_name]
            # 从字段输入框获取
            elif var_name in self.field_inputs:
                var_value = self.field_inputs[var_name].text()
            # 从下拉框获取
            elif var_name in self.combo_boxes:
                var_value = self.combo_boxes[var_name].currentData()

            if var_value is not None:
                processed = processed.replace(f"{{{var_name}}}", str(var_value))

        # 如果还有变化，继续递归
        if processed != text:
            return self.recursive_replace_variables(processed, current_depth + 1, max_depth)
        else:
            return processed

    def on_request_finished(self, response_data):
        """请求完成"""
        try:
            status_code = response_data.get("status_code", 0)
            response_body = response_data.get("decrypted_body") or response_data.get("body", "")

            parsed_response = None  # 初始化为 None

            # 格式化响应内容
            try:
                # 尝试解析为 JSON 并格式化
                if isinstance(response_body, str):
                    parsed_response = json.loads(response_body)
                else:
                    parsed_response = response_body
                formatted_response = json.dumps(parsed_response, ensure_ascii=False, indent=2)
            except:
                # 如果不是 JSON，直接显示原文
                if isinstance(response_body, (dict, list)):
                    parsed_response = response_body
                    formatted_response = json.dumps(response_body, ensure_ascii=False, indent=2)
                else:
                    parsed_response = {"raw_response": response_body}  # 将原始响应包装为字典
                    formatted_response = str(response_body)

            result_text = formatted_response
            self.response_body_edit.setPlainText(result_text)

            # 新增：处理响应参数映射
            if parsed_response is not None:
                self.process_response_mapping(parsed_response)

        except Exception as e:
            self.response_body_edit.setPlainText(f"处理响应时出错: {str(e)}")

    def process_response_mapping(self, response_data):
        """处理响应参数映射 - 支持嵌套路径和JSONPath，先替换变量再提取"""
        if not self.current_interface or not self.current_product:
            return

        try:
            # 获取当前接口的响应映射配置
            product_config = self.api_config["products"][self.current_product]
            interface_config = product_config["interfaces"][self.current_interface]
            response_mapping = interface_config.get("response_mapping", {})

            if not response_mapping:
                return

            print(f"开始处理响应映射，共有 {len(response_mapping)} 个映射项")
            print(f"响应数据: {json.dumps(response_data, ensure_ascii=False, indent=2)}")

            # 遍历映射关系，更新对应的字段输入框和变量池
            for field_key, response_path in response_mapping.items():
                print(f"处理字段: {field_key}, 原始路径: {response_path}")

                # 第一步：先替换JSONPath中的变量
                processed_response_path = self.replace_variables_in_string(response_path)

                print(f"处理后路径: {processed_response_path}")

                # 第二步：使用处理后的JSONPath提取值
                value = self.extract_value_by_jsonpath(response_data, processed_response_path)

                if value is not None:
                    # 更新变量池
                    old_value = self.variable_pool.get(field_key, "未设置")
                    self.variable_pool[field_key] = value

                    # 如果该字段在字段输入框中，也更新输入框
                    if field_key in self.field_inputs:
                        self.field_inputs[field_key].setText(str(value))

                    print(
                        f"从响应中提取字段 '{field_key}': '{old_value}' -> '{value}' (路径: {processed_response_path})")

            # 修复：无论是否勾选发送请求，都强制刷新请求体
            self.force_refresh_request_body()

        except Exception as e:
            print(f"处理响应映射失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def extract_value_by_jsonpath(self, data, jsonpath_expr):
        """使用JSONPath从数据中提取值 - 支持任意深度嵌套"""
        try:
            print(f"开始提取: {jsonpath_expr}")

            # 支持多种分隔符：| 或 -> 或 .
            separators = ['|', '->', '.']
            used_separator = None

            for sep in separators:
                if sep in jsonpath_expr:
                    used_separator = sep
                    break

            # 如果使用分隔符，按多级路径处理
            if used_separator:
                parts = [part.strip() for part in jsonpath_expr.split(used_separator) if part.strip()]
                current_data = data

                for i, part in enumerate(parts):
                    print(f"处理第 {i + 1} 级: {part}")

                    # 处理每个路径部分
                    if not part.startswith('$'):
                        part = '$.' + part

                    try:
                        expr = jsonpath_ng.parse(part)
                        matches = [match.value for match in expr.find(current_data)]

                        if not matches:
                            print(f"路径部分 '{part}' 未找到匹配的值")
                            return None

                        current_data = matches[0]
                        print(f"提取到值: {current_data}")

                        # 如果当前数据是字符串，尝试解析为JSON
                        if isinstance(current_data, str) and current_data.strip().startswith(('{', '[')):
                            try:
                                current_data = json.loads(current_data)
                                print(f"解析字符串为JSON: {current_data}")
                            except json.JSONDecodeError as e:
                                print(f"字符串不是有效的JSON: {e}")
                                # 如果不是JSON，继续使用原始字符串

                    except Exception as e:
                        print(f"处理路径部分 '{part}' 时出错: {str(e)}")
                        return None

                print(f"多级路径提取成功: {jsonpath_expr} = {current_data}")
                return current_data

            # 单级路径处理
            if not jsonpath_expr.startswith('$'):
                jsonpath_expr = '$.' + jsonpath_expr

            expr = jsonpath_ng.parse(jsonpath_expr)
            matches = [match.value for match in expr.find(data)]

            if matches:
                result = matches[0]
                print(f"JSONPath提取成功: {jsonpath_expr} = {result}")
                return result
            else:
                print(f"JSONPath '{jsonpath_expr}' 未找到匹配的值")
                return None

        except Exception as e:
            print(f"JSONPath提取失败: {jsonpath_expr}, 错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def extract_from_nested_json(self, data, jsonpath_expr):
        """处理嵌套JSON字符串的特殊情况

        对于您提供的响应结构，output字段是一个JSON字符串，需要特殊处理
        {
          "data": {
            "businessResponse": {
              "output": "{\"repayApplyNo\":\"78211212121212\"}"
            }
          }
        }
        """
        try:
            print(f"尝试处理嵌套JSON: {jsonpath_expr}")

            # 解析JSONPath表达式，找到output字段
            if 'output' in jsonpath_expr and 'repayApplyNo' in jsonpath_expr:
                # 提取output字段的路径部分
                output_path = jsonpath_expr.split('|')[0].strip() if '|' in jsonpath_expr else \
                    jsonpath_expr.split('.output')[0] + '.output'

                # 提取output字段的值
                output_expr = jsonpath_ng.parse(output_path if output_path.startswith('$') else '$.' + output_path)
                output_matches = [match.value for match in output_expr.find(data)]

                if output_matches:
                    output_value = output_matches[0]
                    print(f"找到output字段: {output_value}")

                    # 如果output是字符串，尝试解析为JSON
                    if isinstance(output_value, str):
                        try:
                            parsed_output = json.loads(output_value)
                            print(f"解析output为JSON: {parsed_output}")

                            # 从解析后的JSON中提取目标字段
                            target_field = jsonpath_expr.split('.')[-1] if '.' in jsonpath_expr else \
                                jsonpath_expr.split('|')[-1].strip() if '|' in jsonpath_expr else jsonpath_expr

                            if target_field in parsed_output:
                                result = parsed_output[target_field]
                                print(f"从嵌套JSON中提取成功: {target_field} = {result}")
                                return result
                        except json.JSONDecodeError as e:
                            print(f"解析output JSON失败: {e}")

            print("嵌套JSON提取失败")
            return None

        except Exception as e:
            print(f"嵌套JSON提取失败: {str(e)}")
            return None

    def get_nested_value(self, data, path):
        """获取嵌套路径的值

        Args:
            data: 响应数据字典
            path: 嵌套路径，如 "data.userInfo.param_b"

        Returns:
            路径对应的值，如果路径不存在返回None
        """
        try:
            keys = path.split('.')
            current = data

            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None

            return current
        except Exception:
            return None

    def on_request_error(self, error_message):
        """请求错误"""
        self.response_body_edit.setPlainText(f"请求失败:\n{error_message}")

    def execute_schedule_task(self):
        """执行定时任务"""
        if self.schedule_combo.currentData() is None:
            Toast.info(self, "请先选择定时任务")
            return

        # 获取选中的定时任务信息
        job_id, job_group = self.schedule_combo.currentData()

        # 禁用按钮并开始动画
        self.start_schedule_animation()

        # 显示开始执行的 Toast
        Toast.info(self, f"开始执行定时任务: {self.schedule_combo.currentText()}")

        # 在工作线程中执行定时任务
        self.schedule_executor = ScheduleExecutor(job_id, job_group)
        self.schedule_executor.finished.connect(self.on_schedule_task_finished)
        self.schedule_executor.error.connect(self.on_schedule_task_error)
        self.schedule_executor.start()

    def on_schedule_task_finished(self, message):
        """定时任务执行完成"""
        # 停止动画并恢复按钮
        self.stop_schedule_animation()
        # 显示成功 Toast
        Toast.success(self, f"定时任务执行成功: {message}")

    def on_schedule_task_error(self, error_message):
        """定时任务执行错误"""
        # 停止动画并恢复按钮
        self.stop_schedule_animation()
        # 显示错误 Toast
        Toast.critical(self, "失败", f"定时任务执行失败: {error_message}")

    def start_schedule_animation(self):
        """开始执行动画"""
        # 保存原始文本并隐藏
        self.schedule_original_text = self.execute_schedule_btn.text()
        self.execute_schedule_btn.setText("")
        self.execute_schedule_btn.setEnabled(False)

        # 显示SVG
        self.loading_svg.setVisible(True)
        self.center_svg_in_button()

    def stop_schedule_animation(self):
        """停止执行动画"""
        # 隐藏SVG，恢复按钮文本
        self.loading_svg.setVisible(False)
        self.execute_schedule_btn.setText(self.schedule_original_text)
        self.execute_schedule_btn.setEnabled(True)

    def center_svg_in_button(self):
        """将SVG居中放置在按钮中心"""
        btn_rect = self.execute_schedule_btn.rect()
        svg_size = self.loading_svg.size()

        # 计算居中位置
        x = (btn_rect.width() - svg_size.width()) // 2
        y = (btn_rect.height() - svg_size.height()) // 2

        self.loading_svg.move(x, y)

    def resizeEvent(self, event):
        """重写resizeEvent以确保SVG在按钮中居中"""
        super().resizeEvent(event)
        if hasattr(self, 'loading_svg') and self.loading_svg.isVisible():
            self.center_svg_in_button()

    def refresh_ui(self):
        """刷新界面"""
        try:
            # 重新加载产品配置
            self.load_products_config()

            # 如果有当前产品，更新界面状态
            if hasattr(self, 'current_product') and self.current_product:
                # 更新产品下拉框
                index = self.product_combo.findText(self.current_product)
                if index >= 0:
                    self.product_combo.setCurrentIndex(index)

            # 可以添加其他需要刷新的逻辑
            print("界面已刷新")

        except Exception as e:
            print(f"刷新界面时出错: {e}")

    # 在主窗口中连接信号
    def open_config_management(self):
        """打开配置管理弹窗"""
        dialog = ConfigManagementDialog(self, self)
        dialog.config_saved.connect(self.on_config_saved)
        dialog.exec_()

    def on_config_saved(self, message):
        """配置保存成功的回调 - 修复：保存后刷新界面并生成测试数据"""
        Toast.success(self, message)
        # 刷新界面
        self.refresh_ui()

        # 如果当前有产品，重新生成测试数据
        if self.current_product:
            self.update_request_id_and_reset_fields()

    def refresh_all_fields_from_variable_pool(self):
        """从变量池强制刷新所有字段的值"""
        print("强制刷新所有字段的值")

        # 刷新字段输入框
        for field_key, field_input in self.field_inputs.items():
            if field_key in self.variable_pool:
                new_value = self.variable_pool[field_key]
                current_value = field_input.text()
                if str(new_value) != current_value:
                    field_input.setText(str(new_value))
                    print(f"强制刷新字段 '{field_key}': '{current_value}' -> '{new_value}'")

        # 刷新下拉框
        for combo_key, combo_box in self.combo_boxes.items():
            if combo_key in self.variable_pool:
                new_value = self.variable_pool[combo_key]
                current_data = combo_box.currentData()
                if str(new_value) != str(current_data):
                    # 在下拉框中查找匹配的选项
                    found_index = -1
                    for i in range(combo_box.count()):
                        if combo_box.itemData(i) == str(new_value):
                            found_index = i
                            break
                    if found_index >= 0:
                        combo_box.setCurrentIndex(found_index)
                        print(f"强制刷新下拉框 '{combo_key}': '{current_data}' -> '{new_value}'")

    def on_field_changed(self, field_key, new_value):
        """字段值变化时的处理"""
        # 更新变量池
        self.variable_pool[field_key] = new_value
        print(f"字段 {field_key} 更新为: {new_value}")

        # 调整该字段的宽度
        if field_key in self.field_inputs:
            self.adjust_field_width(self.field_inputs[field_key], new_value)

        # 检查这个字段是否被用作条件字段，如果是，需要更新相关的条件变量
        self.update_condition_variables_for_field(field_key)

        # 检查这个字段是否被公式依赖，如果是，重新计算相关公式
        self.refresh_dependent_formulas(field_key)

        # 修复：无论是否勾选发送请求，都更新请求体
        self.force_refresh_request_body()

    def on_combo_changed(self, combo_key, combo_box):
        """下拉框值变化时的处理"""
        current_data = combo_box.currentData()
        # 更新变量池
        self.variable_pool[combo_key] = current_data
        print(f"下拉框 {combo_key} 更新为: {current_data}")

        # 检查这个下拉框是否被用作条件字段，如果是，需要更新相关的条件变量
        self.update_condition_variables_for_field(combo_key)

        # 检查这个下拉框是否被公式依赖，如果是，重新计算相关公式
        self.refresh_dependent_formulas(combo_key)

        # 修复：无论是否勾选发送请求，都更新请求体
        self.force_refresh_request_body()

    def update_condition_variables_for_field(self, field_key):
        """更新依赖于指定字段的条件变量 - 修正：只清空条件字段本身，并调整宽度"""
        if not self.current_product:
            return

        try:
            product_config = self.api_config["products"][self.current_product]
            layout_config = product_config.get("layout", [])

            # 查找所有使用这个字段作为条件字段的条件配置
            for item in layout_config:
                if item.get("type") == "condition" and item.get("condition_field") == field_key:
                    condition_key = item.get("key")
                    # 获取条件字段的当前值
                    condition_field_value = None
                    if field_key in self.combo_boxes:
                        combo_box = self.combo_boxes[field_key]
                        condition_field_value = combo_box.currentData()

                    if condition_field_value is None:
                        # 如果没有值，清空条件变量
                        self.clear_condition_variable(condition_key)
                        continue

                    # 根据条件字段值查找对应的变量字段
                    mappings = item.get("mappings", {})
                    variable_field_key = mappings.get(condition_field_value)

                    if not variable_field_key:
                        # 如果没有映射，只清空条件变量本身
                        print(
                            f"条件字段 '{field_key}' 的值 '{condition_field_value}' 没有配置映射，清空条件变量 '{condition_key}'")
                        self.clear_condition_variable(condition_key)
                        continue

                    # 获取变量字段的值
                    variable_value = None
                    if variable_field_key in self.field_inputs:
                        variable_value = self.field_inputs[variable_field_key].text()
                    elif variable_field_key in self.combo_boxes:
                        combo_box = self.combo_boxes[variable_field_key]
                        variable_value = combo_box.currentData()
                    elif variable_field_key in self.variable_pool:
                        variable_value = self.variable_pool[variable_field_key]

                    # 更新条件变量
                    old_value = self.variable_pool.get(condition_key, "未设置")
                    self.variable_pool[condition_key] = variable_value

                    # 更新UI显示
                    if condition_key in self.condition_displays:
                        display_value = str(variable_value) if variable_value is not None else ""
                        self.condition_displays[condition_key].setText(display_value)
                        # 新增：调整条件字段显示框的宽度
                        self.adjust_field_width(self.condition_displays[condition_key], display_value)
                        print(f"更新条件显示 {condition_key}: {old_value} -> {variable_value}")

                    # 强制刷新请求体
                    self.force_refresh_request_body()

        except Exception as e:
            print(f"更新条件变量时出错: {str(e)}")

    def clear_condition_variable(self, condition_key):
        """清空条件变量 - 只清空条件字段本身，并调整宽度"""
        old_value = self.variable_pool.get(condition_key, "未设置")
        self.variable_pool[condition_key] = ""

        # 更新UI显示
        if condition_key in self.condition_displays:
            self.condition_displays[condition_key].setText("")
            # 新增：调整条件字段显示框的宽度
            self.adjust_field_width(self.condition_displays[condition_key], "")
            print(f"清空条件变量 {condition_key}: {old_value} -> ''")

        # 强制刷新请求体
        self.force_refresh_request_body()

    def update_request_id_and_reset_fields(self):
        """更新请求流水号并重置字段 - 修复：确保刷新当前接口"""
        # 生成新的请求流水并更新变量池
        new_request_id = self.generate_request_id()
        self.request_id_input.setText(new_request_id)
        self.variable_pool['request_id'] = new_request_id

        # 生成测试数据
        if self.current_product and self.current_product in self.api_config["products"]:
            test_data = self.user_info_generator.generate_id_card_data()

            # 集中生成身份证图片的Base64编码
            try:
                base64_images = self.id_card_image_generator.generate_id_card_images_base64(
                    id_data=test_data
                )
                # 将Base64编码添加到变量池
                self.variable_pool['id_card_front_base64'] = base64_images['front']
                self.variable_pool['id_card_back_base64'] = base64_images['back']
                self.variable_pool['face_base64'] = base64_images['face']
                print(f"Base64生成成功 - 正面: {len(base64_images['front'])} 字符")
                print(f"Base64生成成功 - 背面: {len(base64_images['back'])} 字符")
                print(f"Base64生成成功 - 人脸: {len(base64_images['face'])} 字符")
            except Exception as e:
                print(f"生成身份证图片Base64失败: {str(e)}")
                # 如果生成失败，设置空值到变量池
                for key in self.BASE64_VARIABLE_KEYS:
                    self.variable_pool[key] = ""
                    print(f"设置空值到变量: {key}")

            # 重置所有字段：清空无默认值的字段，有默认值的设置为默认值
            self.reset_all_fields(test_data)

        # 修复：无论是否有当前接口，都强制刷新请求体
        self.force_refresh_request_body()

    def force_refresh_request_body(self):
        """强制刷新请求体 - 新增方法：确保使用最新的变量值"""
        # 如果有当前接口，重新生成请求体
        if self.current_interface and self.current_product:
            try:
                product_config = self.api_config["products"][self.current_product]
                interface_config = product_config["interfaces"][self.current_interface]

                # 重新生成请求体
                request_body = self.generate_request_body(interface_config)
                self.request_body_edit.setPlainText(json.dumps(request_body, ensure_ascii=False, indent=2))

                print(f"强制刷新请求体完成，使用最新的变量值")

            except Exception as e:
                print(f"强制刷新请求体时出错: {str(e)}")
        else:
            # 如果没有当前接口，但URL和请求体有内容，也尝试刷新
            if self.url_input.text().strip() and self.request_body_edit.toPlainText().strip():
                try:
                    # 尝试解析现有的请求体并重新生成
                    request_body_text = self.request_body_edit.toPlainText().strip()
                    if request_body_text:
                        # 先对现有请求体进行变量替换
                        processed_body = self.replace_variables_in_string(request_body_text)
                        # 如果处理后的内容不同，则更新
                        if processed_body != request_body_text:
                            self.request_body_edit.setPlainText(processed_body)
                            print("已更新独立请求体中的变量")
                except Exception as e:
                    print(f"刷新独立请求体时出错: {str(e)}")

    def reset_all_fields(self, test_data):
        """重置所有字段 - 修复：确保公式在依赖字段初始化后计算"""
        product_config = self.api_config["products"][self.current_product]
        layout_config = product_config.get("layout", [])

        print("开始重置所有字段...")

        # 首先，确保所有字段（包括隐藏字段）都在对应的字典中有记录
        for item in layout_config:
            if item["type"] == "field" and item["key"] not in self.field_inputs:
                # 如果字段不在field_inputs中（可能是隐藏字段），创建它
                field_input = QLineEdit()
                default_value = item.get("default", "")
                if default_value:
                    # 处理默认值中的变量
                    processed_default = self.replace_variables_in_string(default_value)
                    field_input.setText(processed_default)
                self.field_inputs[item["key"]] = field_input

            elif item["type"] == "combo" and item["key"] not in self.combo_boxes:
                # 如果下拉框不在combo_boxes中（可能是隐藏字段），创建它
                combo_box = NoWheelComboBox()
                options = item.get("options", [])
                for option in options:
                    combo_box.addItem(option["text"], option["value"])
                self.combo_boxes[item["key"]] = combo_box

            elif item["type"] == "condition" and item["key"] not in self.condition_displays:
                # 如果条件字段不在condition_displays中（可能是隐藏字段），创建它
                condition_display = QLineEdit()
                condition_display.setReadOnly(True)
                self.condition_displays[item["key"]] = condition_display

            # 新增：确保公式字段在对应的字典中有记录
            elif item["type"] == "formula" and item["key"] not in self.formula_displays:
                # 如果公式字段不在formula_displays中（可能是隐藏字段），创建它
                formula_display = QLineEdit()
                formula_display.setReadOnly(True)
                formula_display.setStyleSheet("background-color: #f0f0f0; color: #666;")
                self.formula_displays[item["key"]] = formula_display

                # 保存公式配置
                formula_key = item["key"]
                self.formula_configs[formula_key] = {
                    "formula": item.get("formula", ""),
                    "formula_type": item.get("formula_type", "numeric"),
                    "dependencies": self.extract_formula_dependencies(item.get("formula", ""))
                }

        # 然后，重置所有字段的值（先处理非公式字段）
        for item in layout_config:
            if item["type"] in ["field", "combo"]:
                field_key = item["key"]
                default_value = item.get("default", "")
                show_in_ui = item.get("show_in_ui", True)

                # 跳过Base64字段，因为它们已经通过变量池处理
                if field_key in self.BASE64_VARIABLE_KEYS:
                    continue

                if item["type"] == "field" and field_key in self.field_inputs:
                    field_input = self.field_inputs[field_key]

                    if default_value:
                        # 有默认值：使用默认值（支持变量替换）
                        processed_default = self.replace_variables_in_string(default_value)
                        field_input.setText(processed_default)
                        print(f"字段 '{field_key}' 设置为默认值: {processed_default}")
                    else:
                        # 无默认值：使用测试数据或清空
                        if field_key in self.get_test_data_mapping(test_data):
                            test_value = self.get_test_data_mapping(test_data)[field_key]
                            field_input.setText(str(test_value))
                            print(f"字段 '{field_key}' 设置为测试数据: {test_value}")
                        else:
                            field_input.clear()
                            print(f"字段 '{field_key}' 已清空")

                    # 更新变量池
                    self.variable_pool[field_key] = field_input.text()

                elif item["type"] == "combo" and field_key in self.combo_boxes:
                    combo_box = self.combo_boxes[field_key]

                    if default_value:
                        # 有默认值：使用默认值
                        processed_default = self.replace_variables_in_string(default_value)
                        # 在下拉框中查找匹配的选项
                        found_index = -1
                        for i in range(combo_box.count()):
                            if combo_box.itemData(i) == processed_default:
                                found_index = i
                                break
                        if found_index >= 0:
                            combo_box.setCurrentIndex(found_index)
                            print(f"下拉框 '{field_key}' 设置为默认值: {processed_default}")
                        else:
                            # 如果没有找到，尝试使用显示文本匹配
                            for i in range(combo_box.count()):
                                if combo_box.itemText(i) == processed_default:
                                    combo_box.setCurrentIndex(i)
                                    print(f"下拉框 '{field_key}' 设置为默认值(文本匹配): {processed_default}")
                                    break
                            else:
                                # 如果还是没有找到，使用第一个选项
                                if combo_box.count() > 0:
                                    combo_box.setCurrentIndex(0)
                                    first_value = combo_box.itemData(0)
                                    print(f"下拉框 '{field_key}' 未找到默认值，使用第一个选项: {first_value}")
                    else:
                        # 无默认值：使用测试数据或第一个选项
                        test_value = None
                        if field_key in self.get_test_data_mapping(test_data):
                            test_value = self.get_test_data_mapping(test_data)[field_key]

                        if test_value:
                            # 在下拉框中查找匹配的选项
                            found_index = -1
                            for i in range(combo_box.count()):
                                if combo_box.itemData(i) == str(test_value):
                                    found_index = i
                                    break
                            if found_index >= 0:
                                combo_box.setCurrentIndex(found_index)
                                print(f"下拉框 '{field_key}' 设置为测试数据: {test_value}")
                            else:
                                # 如果没有找到，尝试使用显示文本匹配
                                for i in range(combo_box.count()):
                                    if combo_box.itemText(i) == str(test_value):
                                        combo_box.setCurrentIndex(i)
                                        print(f"下拉框 '{field_key}' 设置为测试数据(文本匹配): {test_value}")
                                        break
                                else:
                                    # 如果还是没有找到，使用第一个选项
                                    if combo_box.count() > 0:
                                        combo_box.setCurrentIndex(0)
                                        first_value = combo_box.itemData(0)
                                        print(f"下拉框 '{field_key}' 未找到测试数据，使用第一个选项: {first_value}")
                        else:
                            # 无测试数据，使用第一个选项
                            if combo_box.count() > 0:
                                combo_box.setCurrentIndex(0)
                                first_value = combo_box.itemData(0)
                                print(f"下拉框 '{field_key}' 使用第一个选项: {first_value}")

                    # 更新变量池
                    current_data = combo_box.currentData()
                    self.variable_pool[field_key] = current_data if current_data is not None else ""

                elif item["type"] == "condition":
                    # 条件类型不需要重置，因为它的值依赖于其他字段
                    condition_key = item["key"]
                    # 更新变量池中的条件变量值
                    condition_value = self.get_condition_variable_value(condition_key)
                    if condition_value is not None:
                        self.variable_pool[condition_key] = condition_value
                        # 更新显示控件
                        if condition_key in self.condition_displays:
                            self.condition_displays[condition_key].setText(str(condition_value))
                        print(f"重置条件字段 '{condition_key}' 值为: {condition_value}")

        # 在所有非公式字段都初始化完成后，再处理公式字段
        for item in layout_config:
            if item["type"] == "formula":
                # 公式类型不需要手动设置值，因为它的值依赖于其他字段
                formula_key = item["key"]
                # 计算公式值
                self.calculate_formula(formula_key)
                print(f"重置公式字段 '{formula_key}' 并重新计算")

        # 在所有字段重置完成后，检查条件字段的映射状态
        self.check_all_condition_mappings()

        print("所有字段重置完成")

        # 使用与【更新】按钮相同的宽度调整逻辑
        self.adjust_all_elements_width()

    def check_all_condition_mappings(self):
        """检查所有条件字段的映射状态 - 修正：只清空条件字段本身"""
        if not self.current_product:
            return

        try:
            product_config = self.api_config["products"][self.current_product]
            layout_config = product_config.get("layout", [])

            # 查找所有条件配置
            condition_configs = [item for item in layout_config if item.get("type") == "condition"]

            for condition_config in condition_configs:
                condition_key = condition_config.get("key")
                condition_field_key = condition_config.get("condition_field")

                if condition_field_key and condition_field_key in self.combo_boxes:
                    # 获取条件字段的当前值
                    combo_box = self.combo_boxes[condition_field_key]
                    condition_field_value = combo_box.currentData()

                    if condition_field_value:
                        # 检查是否有映射
                        mappings = condition_config.get("mappings", {})
                        variable_field_key = mappings.get(condition_field_value)

                        if not variable_field_key:
                            # 没有映射，只清空条件变量本身
                            print(
                                f"初始化时发现条件字段 '{condition_field_key}' 的值 '{condition_field_value}' 没有配置映射，清空条件变量 '{condition_key}'")
                            self.clear_condition_variable(condition_key)

        except Exception as e:
            print(f"检查条件字段映射状态时出错: {str(e)}")

    def get_test_data_mapping(self, test_data):
        """获取测试数据映射 - 新增方法：将测试数据映射到字段名"""
        return {
            "name": test_data["name"],
            "id_card": test_data["id_number"],
            "phone": test_data["phone"],
            "bank_card_no": test_data["bank_card_number"],
            "id_card_start_time": test_data["id_card_start_time"],
            "id_card_end_time": test_data["id_card_end_time"]
        }

    def extract_formula_dependencies(self, formula):
        """提取公式中依赖的变量"""
        pattern = r'\{(\w+)\}'
        variables = re.findall(pattern, formula)
        return list(set(variables))  # 去重

    def calculate_formula(self, formula_key):
        """计算公式的值 - 修复：处理依赖变量为空的情况"""
        if formula_key not in self.formula_configs:
            return

        formula_config = self.formula_configs[formula_key]
        formula_str = formula_config["formula"]
        formula_type = formula_config.get("formula_type", "numeric")
        dependencies = formula_config["dependencies"]

        # 检查所有依赖变量是否都有值
        values = {}
        missing_dependencies = []

        for var in dependencies:
            if var in self.variable_pool:
                value = self.variable_pool[var]
                if value is None or value == "":
                    missing_dependencies.append(var)
                else:
                    values[var] = value
            else:
                missing_dependencies.append(var)

        # 如果有缺失的依赖变量，设置公式值为空
        if missing_dependencies:
            print(f"公式 '{formula_key}' 依赖的变量为空或不存在: {missing_dependencies}")
            self.set_formula_value(formula_key, "")
            return

        try:
            # 替换公式中的变量为实际值
            expression = formula_str
            for var, val in values.items():
                expression = expression.replace("{" + var + "}", str(val))

            print(f"计算公式 '{formula_key}': {expression} (类型: {formula_type})")

            # 根据公式类型计算公式结果
            if formula_type == "date":
                # 日期类型公式
                result = self.evaluate_date_expression(expression)
            else:
                # 数值类型公式
                result = self.evaluate_numeric_expression(expression)

            self.set_formula_value(formula_key, str(result))
            print(f"公式 '{formula_key}' 计算结果: {result}")

        except Exception as e:
            print(f"计算公式 {formula_key} 时出错: {str(e)}")
            self.set_formula_value(formula_key, "")

    def evaluate_numeric_expression(self, expression):
        """计算数值表达式 - 仅处理数值运算"""
        try:
            # 移除空格
            expression = expression.replace(" ", "")

            # 安全地计算数学表达式
            allowed_chars = set('0123456789+-*/().% ')
            if not all(c in allowed_chars for c in expression):
                raise ValueError("数值表达式包含非法字符")

            # 验证表达式包含必要的数学运算符
            if not any(op in expression for op in ['+', '-', '*', '/']):
                raise ValueError("数值公式应包含数学运算符（+、-、*、/）")

            # 替换百分比符号
            expression = expression.replace('%', '/100')

            # 使用 eval 计算（在生产环境中应考虑更安全的替代方案）
            result = eval(expression)
            return round(result, 2)  # 保留2位小数

        except Exception as e:
            raise ValueError(f"数值公式计算错误: {str(e)}")

    def evaluate_date_expression(self, expression):
        """计算日期表达式 - 增强调试信息"""
        from datetime import datetime, timedelta
        import re

        try:
            print(f"开始计算日期表达式: {expression}")

            # 移除空格
            expression = expression.replace(" ", "")

            # 验证日期表达式格式
            if not any(op in expression for op in ['-']):
                raise ValueError("日期公式应包含减法运算符（-）")

            # 提取日期和操作符
            date_pattern = r'(\d{4}[-/]?\d{2}[-/]?\d{2})(?:\s+\d{2}:\d{2}:\d{2})?'
            dates = re.findall(date_pattern, expression)
            operators = re.findall(r'[+-]', expression)

            print(f"找到日期: {dates}, 操作符: {operators}")

            if len(dates) != 2 or len(operators) != 1:
                raise ValueError("日期表达式格式错误，应为 '日期1 - 日期2' 格式")

            date1_str, date2_str = dates
            operator = operators[0]

            if operator != '-':
                raise ValueError("日期公式目前只支持减法运算")

            # 统一日期格式
            def parse_date(date_str):
                # 移除分隔符
                clean_str = re.sub(r'[-/]', '', date_str)
                if len(clean_str) == 8:
                    return datetime.strptime(clean_str, '%Y%m%d')
                else:
                    # 尝试解析带时间的日期
                    return datetime.strptime(date_str, '%Y%m%d %H:%M:%S')

            date1 = parse_date(date1_str)
            date2 = parse_date(date2_str)

            print(f"解析后的日期: date1={date1}, date2={date2}")

            # 计算日期差（天数）
            delta = date1 - date2
            result = delta.days
            print(f"日期差计算结果: {result} 天")

            return result

        except Exception as e:
            print(f"日期公式计算详细错误: {str(e)}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"日期公式计算错误: {str(e)}")

    def evaluate_numeric_expression(self, expression):
        """计算数字表达式"""
        # 安全地计算数学表达式
        allowed_chars = set('0123456789+-*/().% ')
        if not all(c in allowed_chars for c in expression):
            raise ValueError("表达式包含非法字符")

        # 替换百分比符号
        expression = expression.replace('%', '/100')

        # 使用 eval 计算（在生产环境中应考虑更安全的替代方案）
        result = eval(expression)
        return round(result, 2)  # 保留2位小数

    def set_formula_value(self, formula_key, value):
        """设置公式变量的值并更新显示"""
        self.variable_pool[formula_key] = value
        if formula_key in self.formula_displays:
            self.formula_displays[formula_key].setText(value)

    def refresh_dependent_formulas(self, variable_key):
        """刷新依赖指定变量的所有公式"""
        for formula_key, formula_config in self.formula_configs.items():
            if variable_key in formula_config["dependencies"]:
                self.calculate_formula(formula_key)
