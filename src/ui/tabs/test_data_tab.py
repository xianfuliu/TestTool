from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QLineEdit, QPushButton, QGroupBox, QFileDialog, QRadioButton, QMenu, QApplication)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer
import random
import os
from datetime import datetime
from src.ui.widgets.copy_button import CopyButton
from src.ui.widgets.download_button import DownloadButton
from src.ui.widgets.no_wheel_combo_box import NoWheelComboBox
from src.ui.widgets.toast_tips import Toast
from src.utils.id_card_images_generator import IdCardImageGenerator
from src.utils.resource_utils import resource_path
from PIL import Image


class TestDataTab(QWidget):
    """测试数据Tab - 包含原有的身份证生成功能"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.init_ui()

        # 初始化图片生成器
        self.image_generator = IdCardImageGenerator(parent)

        # 使用单次定时器延迟执行自动生成，确保UI完全加载
        QTimer.singleShot(100, self.auto_generate_on_startup)

        # 使用单次定时器延迟执行自动生成，确保UI完全加载
        QTimer.singleShot(100, self.auto_generate_on_startup)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 第一栏：参数配置
        config_panel = self.create_config_panel()

        # 第二栏：数据信息
        data_panel = self.create_data_panel()

        # 第三栏：图片预览
        preview_panel = self.create_preview_panel()

        # 添加到主布局
        main_layout.addWidget(config_panel, 1)
        main_layout.addWidget(data_panel, 1)
        main_layout.addWidget(preview_panel, 2)

    def auto_generate_on_startup(self):
        """程序启动时自动生成数据"""
        print("程序启动，自动生成测试数据...")
        self.generate_id_card()

    def create_config_panel(self):
        """创建参数配置面板"""
        panel = QGroupBox("参数配置")
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
        self.mode_age_radio.setChecked(True)  # 默认选中年龄

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
        self.age_input = QLineEdit()
        self.age_input.setFixedWidth(180)
        self.age_input.setPlaceholderText("请输入年龄(16-60)")
        layout.addWidget(self.age_input, row, 1)
        row += 1

        # 身份证号输入（身份证号模式）
        layout.addWidget(QLabel("身份证号:"), row, 0)
        self.id_input = QLineEdit()
        self.id_input.setFixedWidth(180)
        self.id_input.setPlaceholderText("请输入身份证号码")
        layout.addWidget(self.id_input, row, 1)
        self.id_input.setVisible(False)  # 默认隐藏
        row += 1

        # 姓名
        layout.addWidget(QLabel("姓名:"), row, 0)
        self.name_input = QLineEdit()
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

        # 手机号开头数字
        layout.addWidget(QLabel("手机号开头:"), row, 0)
        self.phone_prefix_input = QLineEdit()
        self.phone_prefix_input.setFixedWidth(120)
        self.phone_prefix_input.setPlaceholderText("前3位")
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

        # 创建小按钮的布局
        small_buttons_layout = QHBoxLayout()
        small_buttons_layout.setSpacing(5)

        # 更新姓名按钮
        self.update_name_btn = QPushButton("更新姓名")
        self.update_name_btn.setFixedHeight(28)
        self.update_name_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                font-size: 12px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.update_name_btn.clicked.connect(self.update_name)
        small_buttons_layout.addWidget(self.update_name_btn)

        # 更新身份证按钮
        self.update_id_btn = QPushButton("更新身份证")
        self.update_id_btn.setFixedHeight(28)
        self.update_id_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                font-size: 12px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.update_id_btn.clicked.connect(self.update_id_number)
        small_buttons_layout.addWidget(self.update_id_btn)

        # 更新手机号按钮
        self.update_phone_btn = QPushButton("更新手机号")
        self.update_phone_btn.setFixedHeight(28)
        self.update_phone_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                font-size: 12px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.update_phone_btn.clicked.connect(self.update_phone)
        small_buttons_layout.addWidget(self.update_phone_btn)

        # 更新银行卡按钮
        self.update_bank_btn = QPushButton("更新银行卡")
        self.update_bank_btn.setFixedHeight(28)
        self.update_bank_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                font-size: 12px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.update_bank_btn.clicked.connect(self.update_bank_card)
        small_buttons_layout.addWidget(self.update_bank_btn)

        layout.addLayout(small_buttons_layout, row, 0, 1, 2)
        row += 1

        # 生成按钮
        generate_btn = QPushButton("一键生成")
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                font-size: 16px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        generate_btn.clicked.connect(self.generate_id_card)
        layout.addWidget(generate_btn, row, 0, 1, 2)
        row += 1

        # 添加弹性空间
        layout.setRowStretch(row, 1)

        panel.setLayout(layout)
        return panel

    def create_data_panel(self):
        """创建数据信息面板"""
        panel = QGroupBox("数据信息")
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
        name_layout.addWidget(self.name_label)
        self.name_copy_btn = CopyButton("", self)
        name_layout.addWidget(self.name_copy_btn)
        name_layout.addStretch()
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
        id_layout.addWidget(self.id_label)
        self.id_copy_btn = CopyButton("", self)
        id_layout.addWidget(self.id_copy_btn)
        id_layout.addStretch()
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
        phone_layout.addWidget(self.phone_label)
        self.phone_copy_btn = CopyButton("", self)
        phone_layout.addWidget(self.phone_copy_btn)
        phone_layout.addStretch()
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
        bank_card_layout.addWidget(self.bank_card_label)
        self.bank_card_copy_btn = CopyButton("", self)
        bank_card_layout.addWidget(self.bank_card_copy_btn)
        bank_card_layout.addStretch()
        bank_card_widget = QWidget()
        bank_card_widget.setLayout(bank_card_layout)
        layout.addWidget(bank_card_widget)

        # 一键复制按钮
        copy_all_btn = QPushButton("一键复制")
        copy_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                font-size: 16px;
                padding: 10px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        copy_all_btn.clicked.connect(self.copy_all_data)
        layout.addWidget(copy_all_btn)

        # 添加弹性空间
        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def create_preview_panel(self):
        """创建图片预览面板"""
        panel = QGroupBox("图片预览")
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(15, 20, 15, 15)

        # 正面图片
        front_layout = QHBoxLayout()
        front_label = QLabel("身份证正面")
        front_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        front_layout.addWidget(front_label)
        front_layout.addStretch()
        self.front_download_btn = DownloadButton(self)
        self.front_download_btn.clicked.connect(lambda: self.download_single_image("front"))
        front_layout.addWidget(self.front_download_btn)
        front_widget = QWidget()
        front_widget.setLayout(front_layout)
        layout.addWidget(front_widget)

        self.id_front_label = QLabel()
        self.id_front_label.setAlignment(Qt.AlignCenter)
        self.id_front_label.setMinimumSize(400, 375)
        self.id_front_label.setText("身份证正面将显示在这里")
        self.id_front_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px dashed #cccccc;
                border-radius: 8px;
                color: #666666;
                font-size: 16px;
            }
        """)
        self.id_front_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.id_front_label.customContextMenuRequested.connect(lambda pos: self.show_image_context_menu(pos, "front"))
        layout.addWidget(self.id_front_label)

        # 反面图片
        back_layout = QHBoxLayout()
        back_label = QLabel("身份证反面")
        back_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        back_layout.addWidget(back_label)
        back_layout.addStretch()
        self.back_download_btn = DownloadButton(self)
        self.back_download_btn.clicked.connect(lambda: self.download_single_image("back"))
        back_layout.addWidget(self.back_download_btn)
        back_widget = QWidget()
        back_widget.setLayout(back_layout)
        layout.addWidget(back_widget)

        self.id_back_label = QLabel()
        self.id_back_label.setAlignment(Qt.AlignCenter)
        self.id_back_label.setMinimumSize(400, 375)
        self.id_back_label.setText("身份证反面将显示在这里")
        self.id_back_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px dashed #cccccc;
                border-radius: 8px;
                color: #666666;
                font-size: 16px;
            }
        """)
        self.id_back_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.id_back_label.customContextMenuRequested.connect(lambda pos: self.show_image_context_menu(pos, "back"))
        layout.addWidget(self.id_back_label)

        # 一键下载按钮
        download_all_btn = QPushButton("一键下载")
        download_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                font-size: 16px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        download_all_btn.clicked.connect(self.download_id_card)
        layout.addWidget(download_all_btn)

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
        clipboard = QApplication.clipboard()
        clipboard.setText(data_text)
        Toast.information(self, '成功', '复制成功')

    def on_mode_changed(self):
        """模式改变时的处理"""
        if self.mode_age_radio.isChecked():
            self.age_input.setVisible(True)
            self.id_input.setVisible(False)
            # 清空身份证号输入框
            self.id_input.clear()
        else:  # 身份证号模式
            self.age_input.setVisible(False)
            self.id_input.setVisible(True)
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
        action = menu.exec_(self.sender().mapToGlobal(pos))

        if action == copy_action:
            self.copy_image_to_clipboard(image_type)

    def copy_image_to_clipboard(self, image_type):
        """复制图片到剪贴板"""
        if image_type == "front":
            image = self.parent_app.front_image
        else:
            image = self.parent_app.back_image

        if image:
            # 将PIL图像转换为QPixmap
            qimage = self.parent_app.pil_image_to_qimage(image)
            pixmap = QPixmap.fromImage(qimage)

            # 复制到剪贴板
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)

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
        file_path, _ = QFileDialog.getSaveFileName(self, "保存图片", default_name, "PNG Files (*.png)", options=options)

        if file_path:
            try:
                if image_type == "front":
                    self.parent_app.front_image.save(file_path)
                else:
                    self.parent_app.back_image.save(file_path)
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

            # 生成身份证数据
            self.parent_app.id_data = self.parent_app.generator.generate_id_card_data(
                name=name,
                gender=gender,
                ethnic=ethnic,
                id_start=id_prefix,
                bank_name=bank_name,
                card_type=card_type,
                phone_prefix=phone_prefix
            )

            # 根据模式处理年龄或身份证号
            if mode == "年龄" and age:
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
            elif mode == "身份证号" and id_number:
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

                self.id_front_label.setPixmap(QPixmap.fromImage(front_qimage).scaled(
                    600, 375, Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))

                self.id_back_label.setPixmap(QPixmap.fromImage(back_qimage).scaled(
                    600, 375, Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))

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

        # 更新复制按钮的文本
        self.name_copy_btn.text_to_copy = self.parent_app.id_data["name"]
        self.id_copy_btn.text_to_copy = self.parent_app.id_data["id_number"]
        self.phone_copy_btn.text_to_copy = self.parent_app.id_data["phone"]
        self.bank_card_copy_btn.text_to_copy = self.parent_app.id_data["bank_card_number"]

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
        """更新姓名"""
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

        # 重新生成身份证图片（仅更新姓名）
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

        # 获取用户配置的手机号前缀
        phone_prefix = self.phone_prefix_input.text().strip() or None

        # 生成新的手机号
        new_phone = self.parent_app.generator.generate_phone_number(phone_prefix)
        self.parent_app.id_data["phone"] = new_phone

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
