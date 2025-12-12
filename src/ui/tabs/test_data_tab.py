from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QLineEdit, QPushButton, QGroupBox, QFileDialog, QRadioButton, QMenu, QApplication, QFrame, QScrollArea, QDialog, QAction)
from PyQt5.QtGui import QPixmap, QIcon, QFont
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QKeySequence
import random
import os
from datetime import datetime
from src.ui.widgets.copy_button import CopyButton
from src.ui.widgets.refresh_button import RefreshButton
from src.ui.widgets.backfill_button import BackfillButton
from src.ui.widgets.download_button import DownloadButton
from src.ui.widgets.no_wheel_combo_box import NoWheelComboBox
from src.ui.widgets.toast_tips import Toast
from src.ui.widgets.clear_button import ClearLineEdit
from src.utils.id_card_images_generator import IdCardImageGenerator
from src.utils.business_license_images_generator import BusinessLicenseImageGenerator
from src.utils.resource_utils import resource_path
from PIL import Image


class TestDataTab(QWidget):
    """测试数据Tab - 包含原有的身份证生成功能"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        
        # 初始化保存路径
        self.last_save_dir = os.getcwd()  # 默认使用当前工作目录
        
        self.init_ui()

        # 初始化图片生成器
        self.image_generator = IdCardImageGenerator(parent)
        self.business_license_generator = BusinessLicenseImageGenerator(parent)

        # 使用单次定时器延迟执行自动生成，确保UI完全加载
        QTimer.singleShot(100, self.auto_generate_on_startup)

    def init_ui(self):
        # 创建主滚动区域
        main_scroll_area = QScrollArea()
        main_scroll_area.setWidgetResizable(True)
        main_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        main_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        main_scroll_area.setStyleSheet("QScrollArea { border: none; background: white; }")
        
        # 创建主容器
        main_container = QWidget()
        main_layout = QHBoxLayout(main_container)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setAlignment(Qt.AlignLeft)  # 设置主布局左对齐
        
        # 设置滚动区域的内容
        main_scroll_area.setWidget(main_container)
        
        # 设置主布局
        container_layout = QVBoxLayout(self)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(main_scroll_area)

        # 第一栏：参数配置
        config_panel = self.create_config_panel()
        config_panel.setFixedWidth(400)  # 固定配置栏宽度

        # 第二栏：数据信息
        data_panel = self.create_data_panel()
        data_panel.setFixedWidth(480)  # 固定信息栏宽度

        # 第三栏：图片预览容器（添加滚动条）
        preview_scroll_area = QScrollArea()
        preview_scroll_area.setWidgetResizable(True)
        preview_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        preview_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        preview_scroll_area.setMinimumWidth(1060)  # 设置最小宽度，允许自适应
        preview_scroll_area.setMaximumWidth(1400)  # 设置最大宽度，允许自适应
        preview_scroll_area.setStyleSheet("QScrollArea { border: none; background: white; }")
        
        preview_container = QWidget()
        preview_layout = QHBoxLayout(preview_container)
        preview_layout.setSpacing(8)  # 设置第三栏和第四栏之间的间隙为8px
        preview_layout.setContentsMargins(0, 0, 0, 0)

        # 身份证预览
        id_preview_panel = self.create_id_preview_panel()
        # 移除固定宽度，让布局自适应

        # 营业执照预览
        business_preview_panel = self.create_business_preview_panel()
        # 移除固定宽度，让布局自适应

        preview_layout.addWidget(id_preview_panel)
        preview_layout.addWidget(business_preview_panel)
        
        preview_scroll_area.setWidget(preview_container)

        # 添加到主布局
        main_layout.addWidget(config_panel, alignment=Qt.AlignLeft)
        main_layout.addWidget(data_panel, alignment=Qt.AlignLeft)
        main_layout.addWidget(preview_scroll_area, alignment=Qt.AlignLeft)

    def auto_generate_on_startup(self):
        """程序启动时自动生成数据"""
        print("程序启动，自动生成测试数据...")
        # 设置自动生成标记
        self._is_auto_generate = True
        
        # 调用模式切换逻辑，确保界面正确显示
        self.on_mode_changed()
        
        # 生成身份证数据
        self.generate_id_card()
        
        # 生成营业执照数据
        self.generate_business_license()
        
        # 清除自动生成标记
        if hasattr(self, '_is_auto_generate'):
            delattr(self, '_is_auto_generate')

    def create_config_panel(self):
        """创建参数配置面板"""
        panel = QGroupBox()
        layout = QGridLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)

        row = 0

        # 模式选择
        layout.addWidget(QLabel("模式:"), row, 0)
        mode_widget = QWidget()
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(15)

        self.mode_age_radio = QRadioButton("年龄")
        self.mode_id_radio = QRadioButton("身份证号")
        self.mode_id_radio.setChecked(True)  # 默认选中身份证号

        mode_layout.addWidget(self.mode_age_radio)
        mode_layout.addWidget(self.mode_id_radio)
        mode_layout.addStretch()

        # 连接信号
        self.mode_age_radio.toggled.connect(self.on_mode_changed)
        self.mode_id_radio.toggled.connect(self.on_mode_changed)

        layout.addWidget(mode_widget, row, 1)
        row += 1

        # 年龄范围
        layout.addWidget(QLabel("年龄范围:"), row, 0)
        age_layout = QHBoxLayout()
        self.min_age_input = QLineEdit("22")
        self.min_age_input.setFixedWidth(60)
        self.max_age_input = QLineEdit("55")
        self.max_age_input.setFixedWidth(60)
        age_layout.addWidget(self.min_age_input)
        age_layout.addWidget(QLabel("-"))
        age_layout.addWidget(self.max_age_input)
        age_layout.addStretch()
        age_widget = QWidget()
        age_widget.setLayout(age_layout)
        layout.addWidget(age_widget, row, 1)
        row += 1

        # 年龄输入（年龄模式）
        layout.addWidget(QLabel("年龄:"), row, 0)
        self.age_input = ClearLineEdit()
        self.age_input.setFixedWidth(180)
        self.age_input.setPlaceholderText("请输入年龄(16-60)")
        layout.addWidget(self.age_input, row, 1)
        row += 1

        # 身份证号输入（身份证号模式）
        layout.addWidget(QLabel("身份证号:"), row, 0)
        self.id_input = ClearLineEdit()
        self.id_input.setFixedWidth(180)
        self.id_input.setPlaceholderText("请输入身份证号码")
        layout.addWidget(self.id_input, row, 1)
        self.id_input.setVisible(False)  # 默认隐藏
        row += 1

        # 姓名
        layout.addWidget(QLabel("姓名:"), row, 0)
        self.name_input = ClearLineEdit()
        self.name_input.setFixedWidth(180)
        self.name_input.setPlaceholderText("请输入姓名")
        layout.addWidget(self.name_input, row, 1)
        row += 1

        # 性别选择
        layout.addWidget(QLabel("性别:"), row, 0)
        gender_widget = QWidget()
        gender_layout = QHBoxLayout(gender_widget)
        gender_layout.setContentsMargins(0, 0, 0, 0)
        gender_layout.setSpacing(15)

        self.gender_random_radio = QRadioButton("随机")
        self.gender_male_radio = QRadioButton("男")
        self.gender_female_radio = QRadioButton("女")
        self.gender_male_radio.setChecked(True)  # 默认选中男

        gender_layout.addWidget(self.gender_random_radio)
        gender_layout.addWidget(self.gender_male_radio)
        gender_layout.addWidget(self.gender_female_radio)
        gender_layout.addStretch()

        layout.addWidget(gender_widget, row, 1)
        row += 1

        # 民族选择
        layout.addWidget(QLabel("民族:"), row, 0)
        self.ethnic_combo = NoWheelComboBox()
        self.ethnic_combo.setFixedWidth(120)
        self.ethnic_combo.addItems(
            ["随机", "汉", "蒙古", "回", "藏", "维吾尔", "苗", "彝", "壮", "布依", "朝鲜", "满", "侗", "瑶", "白",
             "土家", "哈尼", "哈萨克", "傣", "黎", "傈僳", "佤", "畲", "高山", "拉祜", "水", "东乡", "纳西", "景颇",
             "柯尔克孜", "土", "达斡尔", "仫佬", "羌", "布朗", "撒拉", "毛南", "仡佬", "锡伯", "阿昌", "普米", "塔吉克",
             "怒", "乌孜别克", "俄罗斯", "鄂温克", "德昂", "保安", "裕固", "京", "塔塔尔", "独龙", "鄂伦春", "赫哲",
             "门巴", "珞巴", "基诺"])
        layout.addWidget(self.ethnic_combo, row, 1)
        row += 1

        # 身份证号开头数字（下拉框）
        layout.addWidget(QLabel("身份证开头:"), row, 0)
        self.id_prefix_combo = NoWheelComboBox()
        self.id_prefix_combo.setFixedWidth(120)
        self.id_prefix_combo.addItems(["随机"] + list(self.parent_app.generator.area_codes.keys()))
        layout.addWidget(self.id_prefix_combo, row, 1)
        row += 1

        # 手机号
        layout.addWidget(QLabel("手机号:"), row, 0)
        self.phone_prefix_input = ClearLineEdit()
        self.phone_prefix_input.setFixedWidth(200)
        self.phone_prefix_input.setPlaceholderText("请输入前3位或完整手机号")
        layout.addWidget(self.phone_prefix_input, row, 1)
        row += 1

        # 银行选择
        layout.addWidget(QLabel("银行:"), row, 0)
        self.bank_combo = NoWheelComboBox()
        self.bank_combo.setFixedWidth(120)
        self.bank_combo.addItems(list(self.parent_app.generator.banks.keys()))
        layout.addWidget(self.bank_combo, row, 1)
        row += 1

        # 银行卡类型
        layout.addWidget(QLabel("银行卡类型:"), row, 0)
        card_type_widget = QWidget()
        card_type_layout = QHBoxLayout(card_type_widget)
        card_type_layout.setContentsMargins(0, 0, 0, 0)
        card_type_layout.setSpacing(15)

        self.card_type_debit_radio = QRadioButton("储蓄卡")
        self.card_type_credit_radio = QRadioButton("信用卡")
        self.card_type_debit_radio.setChecked(True)  # 默认选中储蓄卡

        card_type_layout.addWidget(self.card_type_debit_radio)
        card_type_layout.addWidget(self.card_type_credit_radio)
        card_type_layout.addStretch()

        layout.addWidget(card_type_widget, row, 1)
        row += 1

        # 营业执照配置分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #cccccc; margin: 10px 0;")
        layout.addWidget(separator, row, 0, 1, 2)
        row += 1

        # 公司类型选择
        layout.addWidget(QLabel("公司类型:"), row, 0)
        self.company_type_combo = NoWheelComboBox()
        self.company_type_combo.setFixedWidth(120)
        self.company_type_combo.addItems(["随机", "有限责任公司", "股份有限公司", "个人独资企业", "合伙企业", "个体工商户"])
        layout.addWidget(self.company_type_combo, row, 1)
        row += 1

        # 公司名称
        layout.addWidget(QLabel("公司名称:"), row, 0)
        self.company_name_input = ClearLineEdit()
        self.company_name_input.setFixedWidth(250)
        self.company_name_input.setPlaceholderText("默认随机")
        layout.addWidget(self.company_name_input, row, 1)
        row += 1

        # 统一社会信用代码
        layout.addWidget(QLabel("信用代码:"), row, 0)
        self.credit_code_input = ClearLineEdit()
        self.credit_code_input.setFixedWidth(250)
        self.credit_code_input.setPlaceholderText("默认随机")
        layout.addWidget(self.credit_code_input, row, 1)
        row += 1

        # 法定代表人
        layout.addWidget(QLabel("法定代表人:"), row, 0)
        self.legal_representative_input = ClearLineEdit()
        self.legal_representative_input.setFixedWidth(200)
        self.legal_representative_input.setPlaceholderText("默认随机")
        layout.addWidget(self.legal_representative_input, row, 1)
        row += 1

        # 住所
        layout.addWidget(QLabel("住所:"), row, 0)
        self.address_input = ClearLineEdit()
        self.address_input.setFixedWidth(250)
        self.address_input.setPlaceholderText("默认随机")
        layout.addWidget(self.address_input, row, 1)
        row += 1

        # 注册资本（改为输入框）
        layout.addWidget(QLabel("注册资本:"), row, 0)
        self.capital_input = ClearLineEdit()
        self.capital_input.setFixedWidth(150)
        self.capital_input.setPlaceholderText("默认随机")
        layout.addWidget(self.capital_input, row, 1)
        row += 1

        # 成立日期
        layout.addWidget(QLabel("成立日期:"), row, 0)
        self.establishment_date_input = ClearLineEdit()
        self.establishment_date_input.setFixedWidth(150)
        self.establishment_date_input.setPlaceholderText("格式: YYYYMMDD")
        layout.addWidget(self.establishment_date_input, row, 1)
        row += 1

        # 营业期限（开始日期）
        layout.addWidget(QLabel("营业期限开始:"), row, 0)
        self.business_start_date_input = ClearLineEdit()
        self.business_start_date_input.setFixedWidth(150)
        self.business_start_date_input.setPlaceholderText("格式: YYYYMMDD")
        layout.addWidget(self.business_start_date_input, row, 1)
        row += 1

        # 营业期限（结束日期）
        layout.addWidget(QLabel("营业期限结束:"), row, 0)
        self.business_end_date_input = ClearLineEdit()
        self.business_end_date_input.setFixedWidth(150)
        self.business_end_date_input.setPlaceholderText("格式: YYYYMMDD")
        layout.addWidget(self.business_end_date_input, row, 1)
        row += 1

        # 经营范围
        layout.addWidget(QLabel("经营范围:"), row, 0)
        self.business_scope_input = ClearLineEdit()
        self.business_scope_input.setFixedWidth(250)
        self.business_scope_input.setPlaceholderText("默认随机生成")
        layout.addWidget(self.business_scope_input, row, 1)
        row += 1

        # 行业类型
        layout.addWidget(QLabel("行业类型:"), row, 0)
        self.industry_combo = NoWheelComboBox()
        self.industry_combo.setFixedWidth(120)
        self.industry_combo.addItems(["随机", "科技", "贸易", "制造", "服务", "金融", "教育", "医疗", "建筑", "餐饮"])
        layout.addWidget(self.industry_combo, row, 1)
        row += 1

        # 按钮区域 - 生成和清空
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        layout.addLayout(button_layout, row, 0, 1, 2)
        row += 1

        # 添加弹性空间
        layout.setRowStretch(row, 1)

        panel.setLayout(layout)
        return panel

    def create_data_panel(self):
        """创建数据信息面板"""
        panel = QGroupBox()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(15, 20, 15, 15)

        # 姓名
        name_layout = QHBoxLayout()
        name_label = QLabel("用户姓名:")
        name_label.setFixedWidth(70)
        name_label.setStyleSheet("font-weight: bold;")
        name_layout.addWidget(name_label)
        self.name_label = QLabel("")
        self.name_label.setStyleSheet("font-size: 16px; color: #2196F3; font-family: 'Courier New'; font-weight: bold;")
        self.name_label.setMinimumWidth(200)  # 设置最小宽度确保按钮位置固定
        self.name_label.mouseDoubleClickEvent = lambda event: self.copy_value_on_double_click("name")
        name_layout.addWidget(self.name_label)
        name_layout.addStretch()  # 添加弹性空间，让按钮右对齐
        self.name_refresh_btn = RefreshButton(self)
        self.name_refresh_btn.clicked.connect(self.update_name)
        name_layout.addWidget(self.name_refresh_btn)
        self.name_copy_btn = CopyButton("", self)
        name_layout.addWidget(self.name_copy_btn)
        self.name_backfill_btn = BackfillButton(self)
        self.name_backfill_btn.clicked.connect(lambda: self.backfill_single_data("name"))
        name_layout.addWidget(self.name_backfill_btn)
        name_widget = QWidget()
        name_widget.setLayout(name_layout)
        layout.addWidget(name_widget)

        # 身份证号
        id_layout = QHBoxLayout()
        id_label = QLabel("身份证号:")
        id_label.setFixedWidth(70)
        id_label.setStyleSheet("font-weight: bold;")
        id_layout.addWidget(id_label)
        self.id_label = QLabel("")
        self.id_label.setStyleSheet("font-size: 16px; color: #2196F3; font-family: 'Courier New'; font-weight: bold;")
        self.id_label.setMinimumWidth(200)  # 设置最小宽度确保按钮位置固定
        self.id_label.mouseDoubleClickEvent = lambda event: self.copy_value_on_double_click("id")
        id_layout.addWidget(self.id_label)
        id_layout.addStretch()  # 添加弹性空间，让按钮右对齐
        self.id_refresh_btn = RefreshButton(self)
        self.id_refresh_btn.clicked.connect(self.update_id_number)
        id_layout.addWidget(self.id_refresh_btn)
        self.id_copy_btn = CopyButton("", self)
        id_layout.addWidget(self.id_copy_btn)
        self.id_backfill_btn = BackfillButton(self)
        self.id_backfill_btn.clicked.connect(lambda: self.backfill_single_data("id"))
        id_layout.addWidget(self.id_backfill_btn)
        id_widget = QWidget()
        id_widget.setLayout(id_layout)
        layout.addWidget(id_widget)

        # 手机号
        phone_layout = QHBoxLayout()
        phone_label = QLabel("手机号码:")
        phone_label.setFixedWidth(70)
        phone_label.setStyleSheet("font-weight: bold;")
        phone_layout.addWidget(phone_label)
        self.phone_label = QLabel("")
        self.phone_label.setStyleSheet(
            "font-size: 16px; color: #2196F3; font-family: 'Courier New'; font-weight: bold;")
        self.phone_label.setMinimumWidth(200)  # 设置最小宽度确保按钮位置固定
        self.phone_label.mouseDoubleClickEvent = lambda event: self.copy_value_on_double_click("phone")
        phone_layout.addWidget(self.phone_label)
        phone_layout.addStretch()  # 添加弹性空间，让按钮右对齐
        self.phone_refresh_btn = RefreshButton(self)
        self.phone_refresh_btn.clicked.connect(self.update_phone)
        phone_layout.addWidget(self.phone_refresh_btn)
        self.phone_copy_btn = CopyButton("", self)
        phone_layout.addWidget(self.phone_copy_btn)
        self.phone_backfill_btn = BackfillButton(self)
        self.phone_backfill_btn.clicked.connect(lambda: self.backfill_single_data("phone"))
        phone_layout.addWidget(self.phone_backfill_btn)
        phone_widget = QWidget()
        phone_widget.setLayout(phone_layout)
        layout.addWidget(phone_widget)

        # 银行卡号
        bank_card_layout = QHBoxLayout()
        bank_card_label = QLabel("银行卡号:")
        bank_card_label.setFixedWidth(70)
        bank_card_label.setStyleSheet("font-weight: bold;")
        bank_card_layout.addWidget(bank_card_label)
        self.bank_card_label = QLabel("")
        self.bank_card_label.setStyleSheet(
            "font-size: 16px; color: #2196F3; font-family: 'Courier New'; font-weight: bold;")
        self.bank_card_label.setMinimumWidth(200)  # 设置最小宽度确保按钮位置固定
        self.bank_card_label.mouseDoubleClickEvent = lambda event: self.copy_value_on_double_click("bank_card")
        bank_card_layout.addWidget(self.bank_card_label)
        bank_card_layout.addStretch()  # 添加弹性空间，让按钮右对齐
        self.bank_card_refresh_btn = RefreshButton(self)
        self.bank_card_refresh_btn.clicked.connect(self.update_bank_card)
        bank_card_layout.addWidget(self.bank_card_refresh_btn)
        self.bank_card_copy_btn = CopyButton("", self)
        bank_card_layout.addWidget(self.bank_card_copy_btn)
        self.bank_card_backfill_btn = BackfillButton(self)
        self.bank_card_backfill_btn.clicked.connect(lambda: self.backfill_single_data("bank_card"))
        bank_card_layout.addWidget(self.bank_card_backfill_btn)
        bank_card_widget = QWidget()
        bank_card_widget.setLayout(bank_card_layout)
        layout.addWidget(bank_card_widget)

        # 分割线 - 个人信息与公司信息分隔
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #E0E0E0; margin: 10px 0; height: 1px;")
        layout.addWidget(separator)

        # 法人姓名（从身份证配置区域获取）
        legal_person_layout = QHBoxLayout()
        legal_person_label = QLabel("法人姓名:")
        legal_person_label.setFixedWidth(70)
        legal_person_label.setStyleSheet("font-weight: bold;")
        legal_person_layout.addWidget(legal_person_label)
        self.legal_person_label = QLabel("")
        self.legal_person_label.setStyleSheet(
            "font-size: 16px; color: #2196F3; font-family: 'Courier New'; font-weight: bold;")
        self.legal_person_label.setMinimumWidth(200)  # 设置最小宽度确保按钮位置固定
        self.legal_person_label.mouseDoubleClickEvent = lambda event: self.copy_value_on_double_click("legal_person")
        legal_person_layout.addWidget(self.legal_person_label)
        legal_person_layout.addStretch()  # 添加弹性空间，让按钮右对齐
        self.legal_person_refresh_btn = RefreshButton(self)
        self.legal_person_refresh_btn.clicked.connect(self.regenerate_legal_person)
        legal_person_layout.addWidget(self.legal_person_refresh_btn)
        self.legal_person_copy_btn = CopyButton("", self)
        legal_person_layout.addWidget(self.legal_person_copy_btn)
        self.legal_person_backfill_btn = BackfillButton(self)
        self.legal_person_backfill_btn.clicked.connect(lambda: self.backfill_single_data("legal_person"))
        legal_person_layout.addWidget(self.legal_person_backfill_btn)
        legal_person_widget = QWidget()
        legal_person_widget.setLayout(legal_person_layout)
        layout.addWidget(legal_person_widget)

        # 公司名称（从身份证配置区域获取）
        company_name_layout = QHBoxLayout()
        company_name_label = QLabel("公司名称:")
        company_name_label.setFixedWidth(70)
        company_name_label.setStyleSheet("font-weight: bold;")
        company_name_layout.addWidget(company_name_label)
        self.company_name_label = QLabel("")
        self.company_name_label.setStyleSheet(
            "font-size: 16px; color: #2196F3; font-family: 'Courier New'; font-weight: bold;")
        self.company_name_label.setMinimumWidth(200)  # 设置最小宽度确保按钮位置固定
        self.company_name_label.mouseDoubleClickEvent = lambda event: self.copy_value_on_double_click("company_name")
        company_name_layout.addWidget(self.company_name_label)
        company_name_layout.addStretch()  # 添加弹性空间，让按钮右对齐
        self.company_name_refresh_btn = RefreshButton(self)
        self.company_name_refresh_btn.clicked.connect(self.regenerate_company_name)
        company_name_layout.addWidget(self.company_name_refresh_btn)
        self.company_name_copy_btn = CopyButton("", self)
        company_name_layout.addWidget(self.company_name_copy_btn)
        self.company_name_backfill_btn = BackfillButton(self)
        self.company_name_backfill_btn.clicked.connect(lambda: self.backfill_single_data("company_name"))
        company_name_layout.addWidget(self.company_name_backfill_btn)
        company_name_widget = QWidget()
        company_name_widget.setLayout(company_name_layout)
        layout.addWidget(company_name_widget)

        # 统一社会信用代码（从身份证配置区域获取）
        credit_code_layout = QHBoxLayout()
        credit_code_label = QLabel("信用代码:")
        credit_code_label.setFixedWidth(70)
        credit_code_label.setStyleSheet("font-weight: bold;")
        credit_code_layout.addWidget(credit_code_label)
        self.credit_code_label = QLabel("")
        self.credit_code_label.setStyleSheet(
            "font-size: 16px; color: #2196F3; font-family: 'Courier New'; font-weight: bold;")
        self.credit_code_label.setMinimumWidth(200)  # 设置最小宽度确保按钮位置固定
        self.credit_code_label.mouseDoubleClickEvent = lambda event: self.copy_value_on_double_click("credit_code")
        credit_code_layout.addWidget(self.credit_code_label)
        credit_code_layout.addStretch()  # 添加弹性空间，让按钮右对齐
        self.credit_code_refresh_btn = RefreshButton(self)
        self.credit_code_refresh_btn.clicked.connect(self.regenerate_credit_code)
        credit_code_layout.addWidget(self.credit_code_refresh_btn)
        self.credit_code_copy_btn = CopyButton("", self)
        credit_code_layout.addWidget(self.credit_code_copy_btn)
        self.credit_code_backfill_btn = BackfillButton(self)
        self.credit_code_backfill_btn.clicked.connect(lambda: self.backfill_single_data("credit_code"))
        credit_code_layout.addWidget(self.credit_code_backfill_btn)
        credit_code_widget = QWidget()
        credit_code_widget.setLayout(credit_code_layout)
        layout.addWidget(credit_code_widget)

        # 按钮区域 - 生成、清空、复制和回显
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 生成按钮
        generate_btn = QPushButton("生成")
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        generate_btn.clicked.connect(self.generate_all_data)
        button_layout.addWidget(generate_btn)
        
        # 复制按钮
        copy_all_btn = QPushButton("复制")
        copy_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 14px;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 8px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #EF6C00;
            }
        """)
        copy_all_btn.clicked.connect(self.copy_all_data)
        button_layout.addWidget(copy_all_btn)
        
        # 回显按钮
        echo_all_btn = QPushButton("回显")
        echo_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 14px;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 8px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        echo_all_btn.clicked.connect(self.echo_all_data)
        button_layout.addWidget(echo_all_btn)
        
        # 清空按钮
        clear_input_btn = QPushButton("清空")
        clear_input_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 14px;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 8px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        clear_input_btn.clicked.connect(self.clear_all_inputs)
        button_layout.addWidget(clear_input_btn)
        
        layout.addLayout(button_layout)

        # 添加弹性空间
        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def create_id_preview_panel(self):
        """创建身份证图片预览面板"""
        panel = QGroupBox()
        layout = QVBoxLayout()
        layout.setSpacing(5)  # 进一步减少间距
        layout.setContentsMargins(5, 6, 5, 5)  # 进一步减少边距
        layout.setAlignment(Qt.AlignTop)

        # 正面图片
        front_layout = QHBoxLayout()
        front_layout.setSpacing(8)  # 减少水平间距
        front_layout.setContentsMargins(0, 0, 0, 0)
        
        front_label = QLabel("身份证正面")
        front_label.setStyleSheet("""
            QLabel {
                font-weight: bold; 
                font-size: 14px;
                color: #333;
                padding: 4px 0;
            }
        """)
        front_layout.addWidget(front_label)
        front_layout.addStretch()
        
        # 放大按钮
        self.front_enlarge_btn = QPushButton()
        self.front_enlarge_btn.setFixedSize(26, 18)  # 高度调小为20像素
        # 使用 resource_path 处理图标路径，确保打包后能正确显示
        enlarge_icon_path = resource_path("src/resources/icons/enlarge.png")
        if os.path.exists(enlarge_icon_path):
            self.front_enlarge_btn.setIcon(QIcon(enlarge_icon_path))
        else:
            # 如果资源文件不存在，使用文本替代
            self.front_enlarge_btn.setText("🔍")
        self.front_enlarge_btn.setIconSize(QSize(16, 16))  # 设置图标尺寸为16x16像素
        self.front_enlarge_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        self.front_enlarge_btn.clicked.connect(lambda: self.enlarge_image("front"))
        front_layout.addWidget(self.front_enlarge_btn)
        
        self.front_download_btn = DownloadButton(self)
        # 设置下载按钮样式，使其更紧凑
        self.front_download_btn.setFixedSize(24, 24)
        self.front_download_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        self.front_download_btn.clicked.connect(lambda: self.download_single_image("front"))
        front_layout.addWidget(self.front_download_btn)
        
        front_widget = QWidget()
        front_widget.setLayout(front_layout)
        layout.addWidget(front_widget)

        self.id_front_label = QLabel()
        self.id_front_label.setAlignment(Qt.AlignCenter)
        self.id_front_label.setMinimumSize(400, 190)  # 减小最小尺寸，允许自适应
        self.id_front_label.setMaximumSize(500, 290)  # 增大最大尺寸，允许自适应
        self.id_front_label.setScaledContents(True)  # 启用缩放内容，保持图片比例
        self.id_front_label.setText("身份证正面将显示在这里")
        self.id_front_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: none;
                border-radius: 0px;
                color: #666;
                font-size: 14px;
                padding: 0px;
            }
        """)
        self.id_front_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.id_front_label.customContextMenuRequested.connect(lambda pos: self.show_image_context_menu(pos, "front"))
        # 启用双击事件，双击图片放大
        self.id_front_label.mouseDoubleClickEvent = lambda event: self.enlarge_image("front") if hasattr(self.parent_app, 'front_image') and self.parent_app.front_image else None
        layout.addWidget(self.id_front_label)

        # 反面图片
        back_layout = QHBoxLayout()
        back_layout.setSpacing(8)  # 减少水平间距
        back_layout.setContentsMargins(0, 0, 0, 0)
        
        back_label = QLabel("身份证反面")
        back_label.setStyleSheet("""
            QLabel {
                font-weight: bold; 
                font-size: 14px;
                color: #333;
                padding: 4px 0;
            }
        """)
        back_layout.addWidget(back_label)
        back_layout.addStretch()
        
        # 放大按钮
        self.back_enlarge_btn = QPushButton()
        self.back_enlarge_btn.setFixedSize(26, 18)  # 高度调小为20像素
        # 使用 resource_path 处理图标路径，确保打包后能正确显示
        enlarge_icon_path = resource_path("src/resources/icons/enlarge.png")
        if os.path.exists(enlarge_icon_path):
            self.back_enlarge_btn.setIcon(QIcon(enlarge_icon_path))
        else:
            # 如果资源文件不存在，使用文本替代
            self.back_enlarge_btn.setText("🔍")
        self.back_enlarge_btn.setIconSize(QSize(16, 16))  # 设置图标尺寸为16x16像素
        self.back_enlarge_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        self.back_enlarge_btn.clicked.connect(lambda: self.enlarge_image("back"))
        back_layout.addWidget(self.back_enlarge_btn)
        
        self.back_download_btn = DownloadButton(self)
        # 设置下载按钮样式，使其更紧凑
        self.back_download_btn.setFixedSize(24, 24)
        self.back_download_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        self.back_download_btn.clicked.connect(lambda: self.download_single_image("back"))
        back_layout.addWidget(self.back_download_btn)
        
        back_widget = QWidget()
        back_widget.setLayout(back_layout)
        layout.addWidget(back_widget)

        self.id_back_label = QLabel()
        self.id_back_label.setAlignment(Qt.AlignCenter)
        self.id_back_label.setMinimumSize(400, 190)  # 减小最小尺寸，允许自适应
        self.id_back_label.setMaximumSize(500, 290)  # 增大最大尺寸，允许自适应
        self.id_back_label.setScaledContents(True)  # 启用缩放内容，保持图片比例
        self.id_back_label.setText("身份证背面将显示在这里")
        self.id_back_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: none;
                border-radius: 0px;
                color: #666;
                font-size: 14px;
                padding: 0px;
            }
        """)
        self.id_back_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.id_back_label.customContextMenuRequested.connect(lambda pos: self.show_image_context_menu(pos, "back"))
        # 启用双击事件，双击图片放大
        self.id_back_label.mouseDoubleClickEvent = lambda event: self.enlarge_image("back") if hasattr(self.parent_app, 'back_image') and self.parent_app.back_image else None
        layout.addWidget(self.id_back_label)

        # 下载按钮
        download_all_btn = QPushButton("下载")
        download_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        download_all_btn.clicked.connect(self.download_id_card)
        layout.addWidget(download_all_btn)

        panel.setLayout(layout)
        return panel

    def create_business_preview_panel(self):
        """创建营业执照预览面板"""
        panel = QGroupBox()
        layout = QVBoxLayout()
        layout.setSpacing(5)  # 进一步减少间距
        layout.setContentsMargins(5, 6, 5, 5)  # 进一步减少边距
        layout.setAlignment(Qt.AlignTop)

        # 营业执照图片
        business_layout = QHBoxLayout()
        business_layout.setSpacing(8)
        business_layout.setContentsMargins(0, 0, 0, 0)
        
        business_label = QLabel("营业执照")
        business_label.setStyleSheet("""
            QLabel {
                font-weight: bold; 
                font-size: 14px;
                color: #333;
                padding: 4px 0;
            }
        """)
        business_layout.addWidget(business_label)
        business_layout.addStretch()
        
        # 放大按钮
        self.business_enlarge_btn = QPushButton()
        self.business_enlarge_btn.setFixedSize(26, 18)  # 高度调小为20像素
        # 使用 resource_path 处理图标路径，确保打包后能正确显示
        enlarge_icon_path = resource_path("src/resources/icons/enlarge.png")
        if os.path.exists(enlarge_icon_path):
            self.business_enlarge_btn.setIcon(QIcon(enlarge_icon_path))
        else:
            # 如果资源文件不存在，使用文本替代
            self.business_enlarge_btn.setText("🔍")
        self.business_enlarge_btn.setIconSize(QSize(16, 16))  # 设置图标尺寸为16x16像素
        self.business_enlarge_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        self.business_enlarge_btn.clicked.connect(lambda: self.enlarge_image("business"))
        business_layout.addWidget(self.business_enlarge_btn)
        
        self.business_download_btn = DownloadButton(self)
        self.business_download_btn.setFixedSize(24, 24)
        self.business_download_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        self.business_download_btn.clicked.connect(lambda: self.download_single_business_image())
        business_layout.addWidget(self.business_download_btn)
        
        business_widget = QWidget()
        business_widget.setLayout(business_layout)
        layout.addWidget(business_widget)

        self.business_label = QLabel()
        self.business_label.setAlignment(Qt.AlignCenter)
        self.business_label.setMinimumSize(400, 550)  # 缩小最小高度
        self.business_label.setMaximumSize(600, 800)  # 缩小最大高度
        self.business_label.setScaledContents(True)
        self.business_label.setText("营业执照将显示在这里")
        self.business_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: none;
                border-radius: 0px;
                color: #666;
                font-size: 14px;
                padding: 0px;
            }
        """)
        self.business_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.business_label.customContextMenuRequested.connect(lambda pos: self.show_business_image_context_menu(pos))
        # 启用双击事件，双击图片放大
        self.business_label.mouseDoubleClickEvent = lambda event: self.enlarge_image("business") if hasattr(self.parent_app, 'business_license_image') and self.parent_app.business_license_image else None
        layout.addWidget(self.business_label)

        # 下载按钮 - 放在图片底部
        download_business_btn = QPushButton("下载")
        download_business_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        download_business_btn.clicked.connect(self.download_business_license)
        layout.addWidget(download_business_btn)

        # 添加弹性空间，让按钮固定在图片底部而不是容器底部
        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def copy_all_data(self):
        """复制所有数据到剪贴板"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成身份证数据")
            return

        data_text = f"""用户姓名: {self.parent_app.id_data['name']}
身份证号: {self.parent_app.id_data['id_number']}
手机号码: {self.parent_app.id_data['phone']}
银行卡号: {self.parent_app.id_data['bank_card_number']}
"""
        
        # 添加公司名称和统一社会信用代码（如果存在）
        if "company_name" in self.parent_app.id_data:
            data_text += f"公司名称: {self.parent_app.id_data['company_name']}\n"
        if "unified_social_credit_code" in self.parent_app.id_data:
            data_text += f"统一社会信用代码: {self.parent_app.id_data['unified_social_credit_code']}\n"
        
        # 添加法人姓名（如果存在）
        if "legal_representative" in self.parent_app.id_data:
            data_text += f"法人姓名: {self.parent_app.id_data['legal_representative']}\n"
        
        clipboard = QApplication.clipboard()
        clipboard.setText(data_text)
        Toast.information(self, '成功', '复制成功')

    def on_mode_changed(self):
        """模式改变时的处理"""
        # 获取配置面板的布局
        config_panel = self.findChild(QGroupBox)
        if config_panel:
            layout = config_panel.layout()
            
            if self.mode_age_radio.isChecked():
                # 年龄模式：显示年龄相关控件，隐藏身份证号相关控件
                self.age_input.setVisible(True)
                self.id_input.setVisible(False)
                # 显示年龄标签
                if layout.itemAtPosition(2, 0):
                    layout.itemAtPosition(2, 0).widget().setVisible(True)
                # 隐藏身份证号标签
                if layout.itemAtPosition(3, 0):
                    layout.itemAtPosition(3, 0).widget().setVisible(False)
                # 清空身份证号输入框
                self.id_input.clear()
                # 清空年龄输入框
                self.age_input.clear()
            else:  # 身份证号模式
                # 身份证号模式：显示身份证号相关控件，隐藏年龄相关控件
                self.age_input.setVisible(False)
                self.id_input.setVisible(True)
                # 隐藏年龄标签
                if layout.itemAtPosition(2, 0):
                    layout.itemAtPosition(2, 0).widget().setVisible(False)
                # 显示身份证号标签
                if layout.itemAtPosition(3, 0):
                    layout.itemAtPosition(3, 0).widget().setVisible(True)
                # 清空年龄输入框
                self.age_input.clear()

    def show_image_context_menu(self, pos, image_type):
        """显示图片右键菜单"""
        if image_type == "front" and not self.parent_app.front_image:
            return
        if image_type == "back" and not self.parent_app.back_image:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
            }
            QMenu::item {
                padding: 8px 20px 8px 10px;
            }
            QMenu::item:selected {
                background-color: #2196F3;
                color: white;
            }
        """)

        copy_action = menu.addAction("复制图片")
        download_action = menu.addAction("下载图片")
        action = menu.exec_(self.sender().mapToGlobal(pos))

        if action == copy_action:
            self.copy_image_to_clipboard(image_type)
        elif action == download_action:
            self.download_single_image(image_type)

    def copy_image_to_clipboard(self, image_type):
        """复制图片到剪贴板"""
        if image_type == "front":
            image = self.parent_app.front_image
        elif image_type == "back":
            image = self.parent_app.back_image
        elif image_type == "business":
            image = self.parent_app.business_license_image
        else:
            return

        if image:
            # 将PIL图像转换为QPixmap
            qimage = self.parent_app.pil_image_to_qimage(image)
            pixmap = QPixmap.fromImage(qimage)

            # 复制到剪贴板
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)

    def show_business_image_context_menu(self, pos):
        """显示营业执照图片右键菜单"""
        if not self.parent_app.business_license_image:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
            }
            QMenu::item {
                padding: 8px 20px 8px 10px;
            }
            QMenu::item:selected {
                background-color: #2196F3;
                color: white;
            }
        """)

        copy_action = menu.addAction("复制图片")
        download_action = menu.addAction("下载图片")
        action = menu.exec_(self.sender().mapToGlobal(pos))

        if action == copy_action:
            self.copy_image_to_clipboard("business")
        elif action == download_action:
            self.download_single_business_image()

    def download_single_business_image(self):
        """下载单张营业执照图片"""
        if not self.parent_app.business_license_image:
            Toast.warning(self, "警告", "请先生成营业执照")
            return

        # 选择保存文件
        options = QFileDialog.Options()
        default_name = "营业执照.png"
        # 使用上一次的保存目录
        default_path = os.path.join(self.last_save_dir, default_name)
        file_path, _ = QFileDialog.getSaveFileName(self, "保存图片", default_path, "PNG Files (*.png)", options=options)

        if file_path:
            try:
                self.parent_app.business_license_image.save(file_path)
                
                # 更新保存目录
                self.last_save_dir = os.path.dirname(file_path)
                Toast.information(self, '成功', '保存成功')

            except Exception as e:
                Toast.critical(self, "保存失败", f"保存图片时出错: {str(e)}")

    def download_single_image(self, image_type):
        """下载单张图片"""
        if image_type == "front" and not self.parent_app.front_image:
            Toast.warning(self, "警告", "请先生成身份证")
            return
        if image_type == "back" and not self.parent_app.back_image:
            Toast.warning(self, "警告", "请先生成身份证")
            return

        # 选择保存文件
        options = QFileDialog.Options()
        default_name = f"身份证{image_type}.png"
        # 使用上一次的保存目录
        default_path = os.path.join(self.last_save_dir, default_name)
        file_path, _ = QFileDialog.getSaveFileName(self, "保存图片", default_path, "PNG Files (*.png)", options=options)

        if file_path:
            try:
                if image_type == "front":
                    self.parent_app.front_image.save(file_path)
                else:
                    self.parent_app.back_image.save(file_path)
                
                # 更新保存目录
                self.last_save_dir = os.path.dirname(file_path)
                Toast.information(self, '成功', '保存成功')

            except Exception as e:
                Toast.critical(self, "保存失败", f"保存图片时出错: {str(e)}")

    def generate_id_card(self):
        """生成身份证图片 - 使用独立的图片生成器"""
        try:
            # 获取用户输入
            name = self.name_input.text().strip() or None
            age = self.age_input.text().strip() or None
            id_number = self.id_input.text().strip() or None
            id_prefix = self.id_prefix_combo.currentText()
            if id_prefix == "随机":
                id_prefix = None
            phone_prefix = self.phone_prefix_input.text().strip() or None
            bank_name = self.bank_combo.currentText()
            # 处理银行卡类型
            if self.card_type_debit_radio.isChecked():
                card_type = "储蓄卡"
            else:
                card_type = "信用卡"
            min_age = int(self.min_age_input.text())
            max_age = int(self.max_age_input.text())

            # 处理性别
            gender = None
            if self.gender_male_radio.isChecked():
                gender = "男"
            elif self.gender_female_radio.isChecked():
                gender = "女"

            # 处理民族
            ethnic = None
            if self.ethnic_combo.currentText() != "随机":
                ethnic = self.ethnic_combo.currentText()

            # 获取模式
            if self.mode_age_radio.isChecked():
                mode = "年龄"
            else:
                mode = "身份证号"

            # 校验手机号输入
            if phone_prefix:
                # 合法的手机号前缀列表
                valid_phone_prefixes = [
                    '134', '135', '136', '137', '138', '139', '147', '150', '151', '152', '157', '158', '159', '178',
                    '182', '183', '184', '187', '188', '198',
                    '130', '131', '132', '145', '155', '156', '166', '175', '176', '185', '186',
                    '133', '149', '153', '173', '177', '180', '181', '189', '199', '192'
                ]
                
                # 校验手机号输入长度
                if len(phone_prefix) == 3:
                    # 校验3位数是否在合法的手机号列表内
                    if phone_prefix not in valid_phone_prefixes:
                        # 自动生成时忽略错误，使用随机前缀
                        if hasattr(self, '_is_auto_generate') and self._is_auto_generate:
                            phone_prefix = None
                        else:
                            Toast.warning(self, "手机号错误", "手机号前三位有误，请重新输入")
                            return
                elif len(phone_prefix) == 11:
                    # 直接使用用户输入的11位手机号
                    # 简单校验是否为纯数字
                    if not phone_prefix.isdigit():
                        # 自动生成时忽略错误，使用随机前缀
                        if hasattr(self, '_is_auto_generate') and self._is_auto_generate:
                            phone_prefix = None
                        else:
                            Toast.warning(self, "手机号错误", "手机号必须为纯数字")
                            return
                else:
                    # 手机号位数不等于3或不等于11位
                    # 自动生成时忽略错误，使用随机前缀
                    if hasattr(self, '_is_auto_generate') and self._is_auto_generate:
                        phone_prefix = None
                    else:
                        Toast.warning(self, "手机号错误", "手机号位数有误，请输入3位前缀或11位完整手机号")
                        return

            # 验证输入
            if mode == "年龄" and age and id_number:
                # 仅在手动操作时显示警告，自动生成时不显示
                if hasattr(self, '_is_auto_generate') and self._is_auto_generate:
                    # 自动生成时清空冲突的输入
                    if age and id_number:
                        self.id_input.clear()
                else:
                    Toast.warning(self, "输入错误", "年龄和身份证号码只能输入一个")
                    return
            if mode == "身份证号" and age and id_number:
                if hasattr(self, '_is_auto_generate') and self._is_auto_generate:
                    # 自动生成时清空冲突的输入
                    if age and id_number:
                        self.age_input.clear()
                else:
                    Toast.warning(self, "输入错误", "年龄和身份证号码只能输入一个")
                    return

            # 根据模式处理年龄或身份证号
            # 优先处理用户输入的身份证号，无论当前模式是什么
            if id_number:
                # 如果用户选择了身份证号模式，必须严格校验身份证号
                if mode == "身份证号":
                    # 校验身份证号长度
                    if len(id_number) != 18:
                        Toast.warning(self, "身份证号有误", "身份证号码必须是18位，请重新输入")
                        return
                    
                    # 校验身份证号格式（前17位必须是数字）
                    if not id_number[:17].isdigit():
                        Toast.warning(self, "身份证号有误", "身份证号码前17位必须是数字，请重新输入")
                        return
                    
                    # 校验出生日期是否合法
                    birth_year = id_number[6:10]  # 第7-10位是年份
                    birth_month = id_number[10:12]  # 第11-12位是月份
                    birth_day = id_number[12:14]  # 第13-14位是日期
                    
                    try:
                        birth_date = datetime(int(birth_year), int(birth_month), int(birth_day))
                        current_date = datetime.now()
                        if birth_date > current_date:
                            Toast.warning(self, "身份证号有误", "出生日期不能晚于当前日期，请重新输入")
                            return
                    except ValueError:
                        Toast.warning(self, "身份证号有误", "出生日期格式不正确，请重新输入")
                        return
                    
                    # 验证身份证校验码
                    first_17 = id_number[:17]
                    check_code = self.parent_app.generator._calculate_check_code(first_17)
                    if check_code != id_number[17]:
                        Toast.warning(self, "身份证号有误", "身份证号码校验码不正确，请重新输入")
                        return
                
                # 如果是年龄模式但有身份证号输入，也进行基本校验
                elif mode == "年龄" and id_number:
                    if len(id_number) != 18:
                        # 自动生成时忽略身份证号格式错误
                        if not (hasattr(self, '_is_auto_generate') and self._is_auto_generate):
                            Toast.warning(self, "输入错误", "身份证号码必须是18位")
                        return
                    
                    # 验证身份证校验码
                    first_17 = id_number[:17]
                    check_code = self.parent_app.generator._calculate_check_code(first_17)
                    if check_code != id_number[17]:
                        # 自动生成时忽略校验码错误
                        if not (hasattr(self, '_is_auto_generate') and self._is_auto_generate):
                            Toast.warning(self, "输入错误", "身份证号码校验码不正确")
                        return

            # 生成身份证数据（公司名称和信用代码由营业执照生成方法统一生成）
            self.parent_app.id_data = self.parent_app.generator.generate_id_card_data(
                name=name,
                gender=gender,
                ethnic=ethnic,
                id_start=id_prefix,
                bank_name=bank_name,
                card_type=card_type,
                phone_prefix=phone_prefix if phone_prefix and len(phone_prefix) != 11 else None  # 11位完整手机号不传递前缀
            )
            
            # 如果用户输入了11位完整手机号，直接使用用户输入
            if phone_prefix and len(phone_prefix) == 11:
                self.parent_app.id_data["phone"] = phone_prefix

            # 根据模式处理年龄或身份证号
            if id_number:
                # 身份证号校验通过，使用用户输入的身份证号
                self.parent_app.id_data["id_number"] = id_number

                # 修复bug：从身份证号中提取出生年月日
                birth_year = id_number[6:10]  # 第7-10位是年份
                birth_month = id_number[10:12]  # 第11-12位是月份
                birth_day = id_number[12:14]  # 第13-14位是日期

                # 更新出生日期信息
                self.parent_app.id_data["birth_full"] = f"{birth_year}年{birth_month}月{birth_day}日"
                self.parent_app.id_data["birth_year"] = birth_year
                self.parent_app.id_data["birth_month"] = birth_month
                self.parent_app.id_data["birth_day"] = birth_day
            elif mode == "年龄" and age:
                try:
                    age = int(age)
                    if age < 16 or age > 60:
                        # 自动生成时使用默认范围
                        if hasattr(self, '_is_auto_generate') and self._is_auto_generate:
                            age = None
                        else:
                            Toast.warning(self, "输入错误", "年龄必须在16-60岁之间")
                            return

                    current_year = datetime.now().year
                    birth_year = current_year - age
                    birth_date = f"{birth_year}-01-01"  # 简单处理，假设1月1日出生
                    self.parent_app.id_data["birth_full"] = f"{birth_year}年01月01日"
                    self.parent_app.id_data["birth_year"] = f"{birth_year}"
                    self.parent_app.id_data["birth_month"] = "01"
                    self.parent_app.id_data["birth_day"] = "01"

                    # 重新生成身份证号码
                    self.parent_app.id_data["id_number"] = self.parent_app.generator.generate_id_number(
                        birth_date=self.parent_app.id_data["birth_full"],
                        area_code=id_prefix[:2] if id_prefix else None,
                        gender=gender,
                        id_start=id_prefix
                    )
                except ValueError:
                    # 自动生成时忽略年龄格式错误
                    if not (hasattr(self, '_is_auto_generate') and self._is_auto_generate):
                        Toast.warning(self, "输入错误", "年龄必须是数字")
                    return

            # 更新数据面板
            self.update_data_panel()

            # 使用图片生成器生成身份证图片
            try:
                front_image, back_image = self.image_generator.generate_id_card_images(
                    id_data=self.parent_app.id_data
                )

                # 显示图片
                self.parent_app.front_image = front_image
                self.parent_app.back_image = back_image

                # 转换为QPixmap并显示
                front_qimage = self.parent_app.pil_image_to_qimage(self.parent_app.front_image)
                back_qimage = self.parent_app.pil_image_to_qimage(self.parent_app.back_image)

                # 直接设置原始图片，让QLabel自动缩放保持宽高比
                self.id_front_label.setPixmap(QPixmap.fromImage(front_qimage))
                self.id_back_label.setPixmap(QPixmap.fromImage(back_qimage))

                print("身份证图片生成成功")

            except Exception as e:
                # 自动生成时忽略一般错误
                if not (hasattr(self, '_is_auto_generate') and self._is_auto_generate):
                    Toast.critical(self, "生成失败", f"身份证图片生成失败: {str(e)}")
                else:
                    print(f"自动生成身份证图片时出错: {str(e)}")

            # 清除自动生成标记
            if hasattr(self, '_is_auto_generate'):
                delattr(self, '_is_auto_generate')

        except Exception as e:
            # 自动生成时忽略一般错误
            if not (hasattr(self, '_is_auto_generate') and self._is_auto_generate):
                Toast.critical(self, "错误", f"生成身份证时出错: {str(e)}")
            else:
                print(f"自动生成身份证时出错: {str(e)}")

            # 清除自动生成标记
            if hasattr(self, '_is_auto_generate'):
                delattr(self, '_is_auto_generate')

    def update_data_panel(self):
        """更新数据面板"""
        if not self.parent_app.id_data:
            return

        self.name_label.setText(self.parent_app.id_data["name"])
        self.id_label.setText(self.parent_app.id_data["id_number"])
        self.phone_label.setText(self.parent_app.id_data["phone"])
        self.bank_card_label.setText(self.parent_app.id_data["bank_card_number"])
        
        # 更新公司名称和统一社会信用代码
        if "company_name" in self.parent_app.id_data:
            self.company_name_label.setText(self.parent_app.id_data["company_name"])
        if "unified_social_credit_code" in self.parent_app.id_data:
            self.credit_code_label.setText(self.parent_app.id_data["unified_social_credit_code"])
        
        # 更新法人姓名
        if "legal_representative" in self.parent_app.id_data:
            self.legal_person_label.setText(self.parent_app.id_data["legal_representative"])
        else:
            # 如果身份证数据中没有法人姓名，但营业执照数据中有，则显示营业执照中的法人姓名
            if hasattr(self.parent_app, 'business_license_data') and self.parent_app.business_license_data:
                if "legal_representative" in self.parent_app.business_license_data:
                    self.legal_person_label.setText(self.parent_app.business_license_data["legal_representative"])
                else:
                    self.legal_person_label.setText("")
            else:
                self.legal_person_label.setText("")

        # 更新复制按钮的文本
        self.name_copy_btn.text_to_copy = self.parent_app.id_data["name"]
        self.id_copy_btn.text_to_copy = self.parent_app.id_data["id_number"]
        self.phone_copy_btn.text_to_copy = self.parent_app.id_data["phone"]
        self.bank_card_copy_btn.text_to_copy = self.parent_app.id_data["bank_card_number"]
        
        # 更新公司名称和统一社会信用代码的复制按钮文本
        if "company_name" in self.parent_app.id_data:
            self.company_name_copy_btn.text_to_copy = self.parent_app.id_data["company_name"]
        if "unified_social_credit_code" in self.parent_app.id_data:
            self.credit_code_copy_btn.text_to_copy = self.parent_app.id_data["unified_social_credit_code"]
        
        # 更新法人姓名的复制按钮文本
        legal_person_value = ""
        if "legal_representative" in self.parent_app.id_data:
            legal_person_value = self.parent_app.id_data["legal_representative"]
        elif hasattr(self.parent_app, 'business_license_data') and self.parent_app.business_license_data:
            if "legal_representative" in self.parent_app.business_license_data:
                legal_person_value = self.parent_app.business_license_data["legal_representative"]
        self.legal_person_copy_btn.text_to_copy = legal_person_value

    def download_id_card(self):
        """下载身份证图片"""
        if not self.parent_app.front_image or not self.parent_app.back_image:
            Toast.warning(self, "警告", "请先生成身份证")
            return

        # 选择保存目录
        options = QFileDialog.Options()
        save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录", "", options=options)

        if not save_dir:
            return

        try:
            # 保存正面
            front_path = os.path.join(save_dir, "身份证正面.png")
            self.parent_app.front_image.save(front_path)

            # 保存反面
            back_path = os.path.join(save_dir, "身份证反面.png")
            self.parent_app.back_image.save(back_path)
            Toast.information(self, '成功', '保存成功')

        except Exception as e:
            Toast.critical(self, "保存失败", f"保存图片时出错: {str(e)}")

    def update_name(self):
        """更新姓名（只更新身份证数据，不更新营业执照）"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成身份证数据")
            return

        # 如果用户已经输入了姓名，则不更新
        user_name = self.name_input.text().strip()
        if user_name:
            return

        # 生成新的随机姓名
        new_name = self.parent_app.generator.generate_name()
        self.parent_app.id_data["name"] = new_name

        # 更新数据面板
        self.update_data_panel()

        # 只更新身份证图片（仅更新姓名）
        self.regenerate_id_card(update_fields=["name"])

    def update_id_number(self):
        """更新身份证号"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成身份证数据")
            return

        # 如果用户已经输入了身份证号，则不更新
        user_id = self.id_input.text().strip()
        if user_id:
            return

        # 获取当前配置
        gender = None
        if self.gender_male_radio.isChecked():
            gender = "男"
        elif self.gender_female_radio.isChecked():
            gender = "女"

        id_prefix = self.id_prefix_combo.currentText()
        if id_prefix == "随机":
            id_prefix = None

        # 根据年龄范围重新生成出生日期
        min_age = int(self.min_age_input.text())
        max_age = int(self.max_age_input.text())

        # 重新生成身份证号
        new_id_number = self.parent_app.generator.generate_id_number(
            birth_date=None,  # 让生成器根据年龄范围随机生成
            area_code=id_prefix,
            gender=gender,
            id_start=id_prefix
        )

        self.parent_app.id_data["id_number"] = new_id_number

        # 从新身份证号中提取出生日期并更新数据
        birth_year = new_id_number[6:10]
        birth_month = new_id_number[10:12]
        birth_day = new_id_number[12:14]
        self.parent_app.id_data["birth_full"] = f"{birth_year}年{birth_month}月{birth_day}日"
        self.parent_app.id_data["birth_year"] = birth_year
        self.parent_app.id_data["birth_month"] = birth_month
        self.parent_app.id_data["birth_day"] = birth_day

        # 更新数据面板
        self.update_data_panel()

        # 重新生成身份证图片
        self.regenerate_id_card(update_fields=["id_number", "birth"])

    def update_phone(self):
        """更新手机号"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成身份证数据")
            return

        # 获取用户输入的手机号
        phone_input = self.phone_prefix_input.text().strip()
        
        # 合法的手机号前缀列表
        valid_phone_prefixes = [
            '134', '135', '136', '137', '138', '139', '147', '150', '151', '152', '157', '158', '159', '178',
            '182', '183', '184', '187', '188', '198',
            '130', '131', '132', '145', '155', '156', '166', '175', '176', '185', '186',
            '133', '149', '153', '173', '177', '180', '181', '189', '199', '192'
        ]
        
        # 如果用户未输入，则随机生成手机号
        if not phone_input:
            new_phone = self.parent_app.generator.generate_phone_number(None)
            self.parent_app.id_data["phone"] = new_phone
            self.update_data_panel()
            return
        
        # 校验手机号输入长度
        if len(phone_input) == 3:
            # 校验3位数是否在合法的手机号列表内
            if phone_input not in valid_phone_prefixes:
                Toast.warning(self, "手机号错误", "手机号前三位有误，请重新输入")
                return
            # 使用前缀生成完整手机号
            new_phone = self.parent_app.generator.generate_phone_number(phone_input)
            self.parent_app.id_data["phone"] = new_phone
        elif len(phone_input) == 11:
            # 直接使用用户输入的11位手机号
            # 简单校验是否为纯数字
            if not phone_input.isdigit():
                Toast.warning(self, "手机号错误", "手机号必须为纯数字")
                return
            self.parent_app.id_data["phone"] = phone_input
        else:
            # 手机号位数不等于3或不等于11位
            Toast.warning(self, "手机号错误", "手机号位数有误，请输入3位前缀或11位完整手机号")
            return

        # 更新数据面板
        self.update_data_panel()

    def update_bank_card(self):
        """更新银行卡号"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成身份证数据")
            return

        # 获取用户配置的银行和卡类型
        bank_name = self.bank_combo.currentText()
        # 处理银行卡类型
        if self.card_type_debit_radio.isChecked():
            card_type = "储蓄卡"
        else:
            card_type = "信用卡"

        # 生成新的银行卡号
        new_bank_card = self.parent_app.generator.generate_bank_card_number(bank_name, card_type)
        self.parent_app.id_data["bank_card_number"] = new_bank_card

        # 更新数据面板
        self.update_data_panel()

    def update_company_name(self):
        """更新公司名称"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成身份证数据")
            return

        # 生成新的公司名称
        new_company_name = self.parent_app.generator.generate_company_name()
        self.parent_app.id_data["company_name"] = new_company_name

        # 更新数据面板
        self.update_data_panel()

    def update_unified_social_credit_code(self):
        """更新统一社会信用代码"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成身份证数据")
            return

        # 生成新的统一社会信用代码
        new_credit_code = self.parent_app.generator.generate_unified_social_credit_code()
        self.parent_app.id_data["unified_social_credit_code"] = new_credit_code

        # 更新数据面板
        self.update_data_panel()

    def copy_value_on_double_click(self, field):
        """双击标签复制值"""
        if not self.parent_app.id_data:
            return

        if field == "name":
            value = self.parent_app.id_data.get("name", "")
        elif field == "id":
            value = self.parent_app.id_data.get("id_number", "")
        elif field == "phone":
            value = self.parent_app.id_data.get("phone", "")
        elif field == "bank_card":
            value = self.parent_app.id_data.get("bank_card_number", "")
        elif field == "company_name":
            value = self.parent_app.id_data.get("company_name", "")
        elif field == "credit_code":
            value = self.parent_app.id_data.get("unified_social_credit_code", "")
        else:
            return

        if value:
            QApplication.clipboard().setText(value)
            Toast.information(self, "复制成功", f"已复制到剪贴板")

    def regenerate_id_card(self, update_fields=None):
        """重新生成身份证图片"""
        if not self.parent_app.id_data:
            return

        try:
            # 重新生成身份证图片
            front_image, back_image = self.image_generator.generate_id_card_images(
                self.parent_app.id_data
            )
            
            self.parent_app.front_image = front_image
            self.parent_app.back_image = back_image

            # 更新显示
            self.update_id_preview()

        except Exception as e:
            Toast.critical(self, "生成失败", f"重新生成身份证图片时出错: {str(e)}")

    def update_id_preview(self):
        """更新身份证预览"""
        if self.parent_app.front_image:
            # 调整图片大小以适应预览区域
            front_pixmap = self.image_to_pixmap(self.parent_app.front_image, 380, 240)
            self.front_label.setPixmap(front_pixmap)

        if self.parent_app.back_image:
            # 调整图片大小以适应预览区域
            back_pixmap = self.image_to_pixmap(self.parent_app.back_image, 380, 240)
            self.back_label.setPixmap(back_pixmap)

    def generate_all_data(self):
        """生成所有数据（身份证和营业执照）"""
        try:
            # 检查当前模式，如果是身份证号模式且有用户输入的身份证号，确保切换到身份证号模式
            if self.id_input.text().strip() and self.mode_age_radio.isChecked():
                # 用户输入了身份证号但当前是年龄模式，需要切换到身份证号模式
                self.mode_id_radio.setChecked(True)
                self.on_mode_changed()
            
            # 生成身份证数据，如果校验失败则直接返回，不继续生成营业执照
            self.generate_id_card()
            
            # 检查是否生成了有效的身份证数据
            if not self.parent_app.id_data or not self.parent_app.id_data.get("id_number"):
                # 身份证数据生成失败，不继续生成营业执照
                return
            
            # 生成营业执照数据
            self.generate_business_license()
                        
        except Exception as e:
            print(f"生成数据失败: {e}")
            Toast.error(self, '错误', f'生成数据失败: {str(e)}')

    def regenerate_business_license(self):
        """重新生成营业执照图片（更新法定代表人和公司名称）"""
        if not hasattr(self.parent_app, 'business_license_data') or not self.parent_app.business_license_data:
            return
            
        try:
            # 使用现有的营业执照数据，更新法定代表人和公司名称
            business_data = self.parent_app.business_license_data.copy()
            
            # 获取最新的法定代表人信息
            legal_representative = self.legal_representative_input.text().strip()
            if not legal_representative and self.parent_app.id_data:
                legal_representative = self.parent_app.id_data.get("name", "")
            
            # 获取最新的公司名称（如果用户配置了）
            company_name = self.company_name_input.text().strip()
            
            # 更新法定代表人字段
            if legal_representative:
                business_data["legal_representative"] = legal_representative
            
            # 更新公司名称字段（如果用户配置了）
            if company_name:
                business_data["company_name"] = company_name
            
            # 重新生成营业执照图片
            business_image = self.business_license_generator.generate_business_license_images(business_data)
            
            # 保存到应用实例
            self.parent_app.business_license_data = business_data
            self.parent_app.business_license_image = business_image
            
            # 更新预览
            self.update_business_preview()
                        
        except Exception as e:
            Toast.critical(self, "更新失败", f"重新生成营业执照图片时出错: {str(e)}")

    def generate_business_license(self):
        """生成营业执照"""
        try:
            # 获取用户配置
            company_type = self.company_type_combo.currentText()
            if company_type == "随机":
                company_type = None
                
            # 公司名称（如果用户配置了，则使用配置的值，否则随机生成）
            company_name = self.company_name_input.text().strip()
            
            # 法定代表人（优先使用第一栏配置的值，如果未配置则使用身份证姓名）
            legal_representative = self.legal_representative_input.text().strip()
            if not legal_representative and self.parent_app.id_data:
                legal_representative = self.parent_app.id_data.get("name", "")
                
            # 住所
            address = self.address_input.text().strip()
            
            # 注册资本（输入框）
            capital = self.capital_input.text().strip()
            
            # 成立日期
            establishment_date = self.establishment_date_input.text().strip()
            
            # 营业期限
            business_start_date = self.business_start_date_input.text().strip()
            business_end_date = self.business_end_date_input.text().strip()
            
            # 经营范围
            business_scope = self.business_scope_input.text().strip()
            
            industry = self.industry_combo.currentText()
            if industry == "随机":
                industry = None

            # 获取用户配置的信用代码
            unified_social_credit_code = self.credit_code_input.text().strip()
            if unified_social_credit_code == "默认随机":
                unified_social_credit_code = None

            # 构建配置参数
            config = {}
            if company_type:
                config['company_type'] = company_type
            if company_name:
                config['company_name'] = company_name
            if legal_representative:
                config['legal_representative'] = legal_representative
            if address:
                config['address'] = address
            if capital:
                config['registered_capital'] = capital
            if establishment_date:
                config['establishment_date'] = establishment_date
            if business_start_date:
                config['business_start_date'] = business_start_date
            if business_end_date:
                config['business_end_date'] = business_end_date
            if business_scope:
                config['business_scope'] = business_scope
            if industry:
                config['industry_type'] = industry
            if unified_social_credit_code:
                config['unified_social_credit_code'] = unified_social_credit_code

            # 生成营业执照数据
            business_data = self.parent_app.generator.generate_business_license_data(config)
            
            # 将公司名称和信用代码同步到身份证数据中，确保数据一致性
            if self.parent_app.id_data:
                # 优先使用营业执照生成的公司名称和信用代码
                if "company_name" in business_data:
                    self.parent_app.id_data["company_name"] = business_data["company_name"]
                if "unified_social_credit_code" in business_data:
                    self.parent_app.id_data["unified_social_credit_code"] = business_data["unified_social_credit_code"]
                # 将法定代表人信息同步到身份证数据中（仅用于显示）
                if "legal_representative" in business_data:
                    self.parent_app.id_data["legal_representative"] = business_data["legal_representative"]
            
            # 生成营业执照图片
            business_image = self.business_license_generator.generate_business_license_images(business_data)
            
            # 保存到应用实例
            self.parent_app.business_license_data = business_data
            self.parent_app.business_license_image = business_image
            
            # 更新数据面板（确保第二栏显示正确的公司名称、信用代码和法人姓名）
            self.update_data_panel()
            
            # 更新预览
            self.update_business_preview()
                        
        except Exception as e:
            Toast.critical(self, "生成失败", f"营业执照生成失败: {str(e)}")

    def download_business_license(self):
        """下载营业执照"""
        if not self.parent_app.business_license_image:
            Toast.warning(self, "警告", "请先生成营业执照")
            return

        # 选择保存目录
        options = QFileDialog.Options()
        save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录", "", options=options)

        if not save_dir:
            return

        try:
            # 保存营业执照
            save_path = os.path.join(save_dir, "营业执照.png")
            self.parent_app.business_license_image.save(save_path)
            Toast.information(self, '成功', '营业执照保存成功')

        except Exception as e:
            Toast.critical(self, "保存失败", f"保存营业执照时出错: {str(e)}")

    def update_business_preview(self):
        """更新营业执照预览"""
        if self.parent_app.business_license_image:
            # 根据营业执照模板的实际尺寸(1191x1684)进行缩放，保持图片比例
            business_qimage = self.parent_app.pil_image_to_qimage(self.parent_app.business_license_image)
            # 使用适合营业执照的缩放比例，避免拉伸模糊
            self.business_label.setPixmap(QPixmap.fromImage(business_qimage).scaled(
                700, 990, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))

    def image_to_pixmap(self, pil_image, max_width, max_height):
        """将PIL图像转换为QPixmap，并调整大小"""
        from PyQt5.QtGui import QImage
        
        # 调整图片大小
        pil_image = pil_image.copy()
        pil_image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # 转换为QPixmap
        if pil_image.mode == 'RGBA':
            # 处理透明背景
            data = pil_image.tobytes('raw', 'RGBA')
            qim = QImage(data, pil_image.size[0], pil_image.size[1], QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qim)
        else:
            # 普通图片
            data = pil_image.tobytes('raw', pil_image.mode)
            qim = QImage(data, pil_image.size[0], pil_image.size[1], QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qim)
        
        return pixmap

    def update_credit_code(self):
        """更新统一社会信用代码"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成身份证数据")
            return

        # 生成新的统一社会信用代码
        new_credit_code = self.parent_app.generator.generate_unified_social_credit_code()
        self.parent_app.id_data["unified_social_credit_code"] = new_credit_code

    def update_company_name_from_id_card(self):
        """从身份证配置区域获取公司名称"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成身份证数据")
            return

        # 优先使用用户配置的公司名称
        company_name = self.company_name_input.text().strip()
        if not company_name:
            # 如果用户没有配置，则从身份证数据中获取或生成
            if "company_name" in self.parent_app.id_data:
                company_name = self.parent_app.id_data["company_name"]
            else:
                # 如果身份证数据中没有公司名称，则生成一个
                company_name = self.parent_app.generator.generate_company_name()
                self.parent_app.id_data["company_name"] = company_name
        
        # 更新公司名称输入框
        self.company_name_input.setText(company_name)
        
        # 更新数据面板
        self.update_data_panel()

    def update_credit_code_from_id_card(self):
        """从身份证配置区域获取信用代码"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成身份证数据")
            return

        # 优先使用用户配置的信用代码
        credit_code = self.credit_code_input.text().strip()
        if not credit_code or credit_code == "默认随机":
            # 如果用户没有配置，则从身份证数据中获取或生成
            if "unified_social_credit_code" in self.parent_app.id_data:
                credit_code = self.parent_app.id_data["unified_social_credit_code"]
            else:
                # 如果身份证数据中没有信用代码，则生成一个
                credit_code = self.parent_app.generator.generate_unified_social_credit_code()
                self.parent_app.id_data["unified_social_credit_code"] = credit_code
        
        # 更新信用代码输入框
        self.credit_code_input.setText(credit_code)

        # 更新数据面板
        self.update_data_panel()

    def copy_value_on_double_click(self, field_type):
        """双击复制value值"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成身份证数据")
            return

        # 根据字段类型获取对应的值
        value_mapping = {
            "name": "name",
            "id": "id_number", 
            "phone": "phone",
            "bank_card": "bank_card_number",
            "company_name": "company_name",
            "credit_code": "unified_social_credit_code",
            "legal_person": "legal_representative"
        }

        if field_type not in value_mapping:
            return

        field_key = value_mapping[field_type]
        if field_key not in self.parent_app.id_data:
            return

        value = self.parent_app.id_data[field_key]
        if not value:
            return

        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setText(value)

        # 显示Toast提示
        Toast.show_message(self, f"已复制: {value}", "success", 1500)

    def regenerate_id_card(self, update_fields=None):
        """更新身份证按钮：身份证图片，只更新指定字段"""
        if not self.parent_app.id_data:
            return

        try:
            # 使用图片生成器重新生成身份证图片
            front_image, back_image = self.image_generator.generate_id_card_images(
                id_data=self.parent_app.id_data
            )

            # 加载并显示图片
            self.parent_app.front_image = front_image
            self.parent_app.back_image = back_image

            # 转换为QPixmap并显示
            front_qimage = self.parent_app.pil_image_to_qimage(self.parent_app.front_image)
            back_qimage = self.parent_app.pil_image_to_qimage(self.parent_app.back_image)

            self.id_front_label.setPixmap(QPixmap.fromImage(front_qimage).scaled(
                600, 375, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))

            self.id_back_label.setPixmap(QPixmap.fromImage(back_qimage).scaled(
                600, 375, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))

        except Exception as e:
            print(f"重新生成身份证图片时出错: {e}")

    def regenerate_company_name(self):
        """重新生成公司名称并更新营业执照预览"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成身份证数据")
            return

        # 检查第一栏是否已配置公司名称
        company_name = self.company_name_input.text().strip()
        if company_name and company_name != "默认随机":
            # 如果已配置，则不更新，直接提示用户
            Toast.information(self, "提示", "公司名称已配置，如需更新请在第一栏修改")
            return

        try:
            # 生成新的公司名称
            new_company_name = self.parent_app.generator.generate_company_name()
            
            # 更新身份证数据中的公司名称
            self.parent_app.id_data["company_name"] = new_company_name
            
            # 如果存在营业执照数据，也更新其中的公司名称
            if self.parent_app.business_license_data:
                self.parent_app.business_license_data["company_name"] = new_company_name
            
            # 重新生成营业执照图片
            if self.parent_app.business_license_data:
                business_image = self.business_license_generator.generate_business_license_images(
                    self.parent_app.business_license_data
                )
                self.parent_app.business_license_image = business_image
                
                # 更新营业执照预览
                self.update_business_preview()
                
                # 更新数据面板显示
                self.update_data_panel()
                
                Toast.information(self, "成功", f"公司名称已更新为: {new_company_name}")
            else:
                Toast.warning(self, "提示", "请先生成营业执照以更新预览")
                
        except Exception as e:
            Toast.critical(self, "更新失败", f"更新公司名称时出错: {str(e)}")

    def regenerate_credit_code(self):
        """重新生成信用代码并更新营业执照预览"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成身份证数据")
            return

        # 检查第一栏是否已配置信用代码
        credit_code = self.credit_code_input.text().strip()
        if credit_code and credit_code != "默认随机":
            # 如果已配置，则不更新，直接提示用户
            Toast.information(self, "提示", "信用代码已配置，如需更新请在第一栏修改")
            return

        try:
            # 生成新的信用代码
            new_credit_code = self.parent_app.generator.generate_unified_social_credit_code()
            
            # 更新身份证数据中的信用代码
            self.parent_app.id_data["unified_social_credit_code"] = new_credit_code
            
            # 如果存在营业执照数据，也更新其中的信用代码
            if self.parent_app.business_license_data:
                self.parent_app.business_license_data["unified_social_credit_code"] = new_credit_code
            
            # 重新生成营业执照图片
            if self.parent_app.business_license_data:
                business_image = self.business_license_generator.generate_business_license_images(
                    self.parent_app.business_license_data
                )
                self.parent_app.business_license_image = business_image
                
                # 更新营业执照预览
                self.update_business_preview()
                
                # 更新数据面板显示
                self.update_data_panel()
                
                Toast.information(self, "成功", f"信用代码已更新为: {new_credit_code}")
            else:
                Toast.warning(self, "提示", "请先生成营业执照以更新预览")
                
        except Exception as e:
            Toast.critical(self, "更新失败", f"更新信用代码时出错: {str(e)}")

    def regenerate_legal_person(self):
        """重新生成法人姓名并更新营业执照预览"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成身份证数据")
            return

        # 检查第一栏是否已配置法定代表人姓名
        legal_representative = self.legal_representative_input.text().strip()
        if legal_representative:
            # 如果已配置，则不更新，直接提示用户
            Toast.information(self, "提示", "法定代表人已配置，如需更新请在第一栏修改")
            return

        try:
            # 生成新的法人姓名
            new_legal_person = self.parent_app.generator.generate_name()
            
            # 更新身份证数据中的法定代表人（仅用于数据面板显示）
            self.parent_app.id_data["legal_representative"] = new_legal_person
            
            # 如果存在营业执照数据，更新其中的法定代表人
            if self.parent_app.business_license_data:
                self.parent_app.business_license_data["legal_representative"] = new_legal_person
                
                # 重新生成营业执照图片
                business_image = self.business_license_generator.generate_business_license_images(
                    self.parent_app.business_license_data
                )
                self.parent_app.business_license_image = business_image
                
                # 更新营业执照预览
                self.update_business_preview()
                
                # 更新数据面板显示
                self.update_data_panel()
                
                Toast.information(self, "成功", f"法人姓名已更新为: {new_legal_person}")
            else:
                Toast.warning(self, "提示", "请先生成营业执照以更新预览")
                
        except Exception as e:
            Toast.critical(self, "更新失败", f"更新法人姓名时出错: {str(e)}")

    def clear_all_inputs(self):
        """清空所有输入框的内容"""
        # 清空身份证配置区域输入框
        self.name_input.setText("")
        self.gender_random_radio.setChecked(True)  # 设置为"随机"
        self.id_prefix_combo.setCurrentIndex(0)  # 设置为"随机"
        self.phone_prefix_input.setText("")
        self.bank_combo.setCurrentIndex(0)  # 设置为第一个银行
        self.card_type_debit_radio.setChecked(True)  # 默认选中储蓄卡
        
        # 清空身份证号输入框
        self.id_input.setText("")
        
        # 清空年龄输入框
        self.age_input.setText("")
        
        # 清空营业执照配置区域输入框
        self.company_type_combo.setCurrentIndex(0)  # 设置为"随机"
        self.company_name_input.setText("")
        self.credit_code_input.setText("")
        self.legal_representative_input.setText("")
        self.address_input.setText("")
        self.capital_input.setText("")
        self.establishment_date_input.setText("")
        self.business_start_date_input.setText("")
        self.business_end_date_input.setText("")
        self.business_scope_input.setText("")
        self.industry_combo.setCurrentIndex(0)  # 设置为"随机"
        
        Toast.information(self, "成功", "所有输入框已清空")

    def echo_all_data(self):
        """将第二栏随机生成的信息回显到第一栏对应的输入框"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成数据")
            return
        
        try:
            # 回显姓名
            if "name" in self.parent_app.id_data:
                self.name_input.setText(self.parent_app.id_data["name"])
            
            # 根据模式判断是否回显身份证号
            # 只有在身份证号模式下才回填身份证号相关字段
            if self.mode_id_radio.isChecked():
                # 身份证号模式下，回显完整的身份证号
                if "id_number" in self.parent_app.id_data:
                    id_number = self.parent_app.id_data["id_number"]
                    # 设置身份证号输入框
                    self.id_input.setText(id_number)
                    
                    # 同时设置地区前缀（只回显前6位作为地区前缀）
                    if len(id_number) >= 6:
                        # 查找对应的地区名称
                        area_code = id_number[:6]
                        area_name = None
                        for name, code in self.parent_app.generator.area_codes.items():
                            if code == area_code:
                                area_name = name
                                break
                        if area_name:
                            index = self.id_prefix_combo.findText(area_name)
                            if index >= 0:
                                self.id_prefix_combo.setCurrentIndex(index)
            else:
                # 年龄模式下，不清除身份证号相关字段，保持用户原有设置
                pass
            
            # 回显手机号
            if "phone" in self.parent_app.id_data:
                phone = self.parent_app.id_data["phone"]
                if len(phone) == 11:
                    self.phone_prefix_input.setText(phone)
            
            # 回显公司名称
            if "company_name" in self.parent_app.id_data:
                self.company_name_input.setText(self.parent_app.id_data["company_name"])
            
            # 回显信用代码
            if "unified_social_credit_code" in self.parent_app.id_data:
                self.credit_code_input.setText(self.parent_app.id_data["unified_social_credit_code"])
            
            # 回显法定代表人
            if "legal_representative" in self.parent_app.id_data:
                self.legal_representative_input.setText(self.parent_app.id_data["legal_representative"])
            
            Toast.information(self, "成功", "数据已回显到第一栏")
            
        except Exception as e:
            Toast.critical(self, "回显失败", f"回显数据时出错: {str(e)}")

    def backfill_single_data(self, field_type):
        """将单个数据项回填到对应的输入框"""
        if not self.parent_app.id_data:
            Toast.warning(self, "警告", "请先生成数据")
            return
        
        try:
            # 根据字段类型回填到对应的输入框
            if field_type == "name" and "name" in self.parent_app.id_data:
                self.name_input.setText(self.parent_app.id_data["name"])
                Toast.information(self, "成功", "姓名已回填到输入框")
            
            elif field_type == "id" and "id_number" in self.parent_app.id_data:
                # 只有在身份证号模式下才回填身份证号
                if self.mode_id_radio.isChecked():
                    id_number = self.parent_app.id_data["id_number"]
                    self.id_input.setText(id_number)
                    
                    # 同时设置地区前缀
                    if len(id_number) >= 6:
                        area_code = id_number[:6]
                        area_name = None
                        for name, code in self.parent_app.generator.area_codes.items():
                            if code == area_code:
                                area_name = name
                                break
                        if area_name:
                            index = self.id_prefix_combo.findText(area_name)
                            if index >= 0:
                                self.id_prefix_combo.setCurrentIndex(index)
                    Toast.information(self, "成功", "身份证号已回填到输入框")
                else:
                    Toast.warning(self, "提示", "当前为年龄模式，无法回填身份证号")
            
            elif field_type == "phone" and "phone" in self.parent_app.id_data:
                phone = self.parent_app.id_data["phone"]
                if len(phone) == 11:
                    self.phone_prefix_input.setText(phone)
                    Toast.information(self, "成功", "手机号已回填到输入框")
                else:
                    Toast.warning(self, "提示", "手机号格式不正确，无法回填")
            
            elif field_type == "bank_card" and "bank_card_number" in self.parent_app.id_data:
                # 银行卡号没有对应的输入框，直接提示用户
                Toast.information(self, "提示", "银行卡号已复制到剪贴板，请手动粘贴到需要的位置")
                
            elif field_type == "company_name" and "company_name" in self.parent_app.id_data:
                self.company_name_input.setText(self.parent_app.id_data["company_name"])
                Toast.information(self, "成功", "公司名称已回填到输入框")
            
            elif field_type == "credit_code" and "unified_social_credit_code" in self.parent_app.id_data:
                self.credit_code_input.setText(self.parent_app.id_data["unified_social_credit_code"])
                Toast.information(self, "成功", "信用代码已回填到输入框")
            
            elif field_type == "legal_person" and "legal_representative" in self.parent_app.id_data:
                self.legal_representative_input.setText(self.parent_app.id_data["legal_representative"])
                Toast.information(self, "成功", "法人姓名已回填到输入框")
            
            else:
                Toast.warning(self, "警告", "该数据项不存在或无法回填")
                
        except Exception as e:
            Toast.critical(self, "回填失败", f"回填数据时出错: {str(e)}")

    def enlarge_image(self, image_type):
        """放大显示原尺寸图片"""
        try:
            # 根据图片类型获取对应的图片数据
            if image_type == "front":
                if not hasattr(self.parent_app, 'front_image') or not self.parent_app.front_image:
                    Toast.warning(self, "提示", "请先生成身份证正面图片")
                    return
                image_data = self.parent_app.front_image
                title = "身份证正面 - 原尺寸"
            elif image_type == "back":
                if not hasattr(self.parent_app, 'back_image') or not self.parent_app.back_image:
                    Toast.warning(self, "提示", "请先生成身份证反面图片")
                    return
                image_data = self.parent_app.back_image
                title = "身份证反面 - 原尺寸"
            elif image_type == "business":
                if not hasattr(self.parent_app, 'business_license_image') or not self.parent_app.business_license_image:
                    Toast.warning(self, "提示", "请先生成营业执照图片")
                    return
                image_data = self.parent_app.business_license_image
                title = "营业执照 - 原尺寸"
            else:
                Toast.warning(self, "错误", "不支持的图片类型")
                return

            # 创建放大对话框
            dialog = QDialog(self)
            dialog.setWindowTitle(title)
            dialog.setModal(True)
            dialog.setWindowFlags(Qt.FramelessWindowHint)  # 设置无边框
            dialog.setStyleSheet("QDialog { border: none; background-color: rgba(0, 0, 0, 0.8); }")  # 半透明黑色背景
            
            # 设置ESC键关闭功能
            close_action = QAction(dialog)
            close_action.setShortcut(QKeySequence("Esc"))
            close_action.triggered.connect(dialog.close)
            dialog.addAction(close_action)
            
            # 处理PIL Image对象
            if hasattr(image_data, 'save'):  # 检查是否为PIL Image对象
                # 直接使用临时文件方法转换PIL Image为QPixmap
                if isinstance(image_data, QPixmap):
                    pixmap = image_data
                else:
                    # 将PIL Image保存为临时文件再加载
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                        image_data.save(temp_file.name)
                        pixmap = QPixmap(temp_file.name)
            elif isinstance(image_data, str):
                # 如果是文件路径，直接加载
                pixmap = QPixmap(image_data)
            elif isinstance(image_data, QPixmap):
                # 如果已经是QPixmap对象，直接使用
                pixmap = image_data
            else:
                # 其他类型，尝试直接使用
                pixmap = image_data
            
            # 获取图片原始尺寸
            image_width = pixmap.width()
            image_height = pixmap.height()
            
            # 设置对话框大小，考虑图片尺寸和关闭按钮高度，但不超过屏幕尺寸
            screen = QApplication.desktop().screenGeometry()
            max_width = screen.width() - 100
            max_height = screen.height() - 100
            
            # 设置全屏显示
            dialog_width = screen.width()
            dialog_height = screen.height()
            
            dialog.resize(dialog_width, dialog_height)
            dialog.showFullScreen()  # 强制全屏显示
            
            # 创建滚动区域以支持大图片
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setFrameShape(QFrame.NoFrame)  # 移除滚动区域边框
            scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            
            # 创建图片标签
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)  # 靠顶部显示，水平居中
            image_label.setPixmap(pixmap)  # 直接使用原尺寸图片
            image_label.setScaledContents(False)  # 不缩放图片
            image_label.setStyleSheet("QLabel { border: none; background: transparent; }")
            
            # 设置滚动区域的内容
            scroll_area.setWidget(image_label)
            
            # 设置滚动区域的对齐方式，让图片靠顶部显示
            scroll_area.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
            
            # 创建主布局
            main_layout = QVBoxLayout(dialog)
            
            # 创建顶部布局用于放置关闭按钮
            top_layout = QHBoxLayout()
            top_layout.addStretch()  # 左侧弹性空间
            
            # 创建关闭按钮（图标按钮）
            close_button = QPushButton()
            close_button.clicked.connect(dialog.close)
            close_button.setFixedSize(80, 80)  # 增大按钮尺寸
            # 使用 resource_path 处理图标路径，确保打包后能正确显示
            clear_icon_path = resource_path("src/resources/icons/clear.png")
            if os.path.exists(clear_icon_path):
                close_button.setIcon(QIcon(clear_icon_path))
            else:
                # 如果资源文件不存在，使用文本替代
                close_button.setText("✕")
                close_button.setFont(QFont("Arial", 24, QFont.Bold))
            close_button.setIconSize(QSize(60, 60))  # 特别大的图标
            close_button.setStyleSheet("QPushButton { border: none; background: transparent; }")
            
            top_layout.addWidget(close_button)
            top_layout.addStretch()  # 右侧弹性空间
            
            # 添加到主布局
            main_layout.addLayout(top_layout)
            main_layout.setSpacing(0)  # 设置布局间距为0
            main_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
            main_layout.addWidget(scroll_area, 1)  # 滚动区域占据剩余空间
            
            # 显示对话框
            dialog.exec_()
            
        except Exception as e:
            Toast.critical(self, "放大失败", f"放大图片时出错: {str(e)}")
