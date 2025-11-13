import os
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QMessageBox)
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon, QPainter, QColor
from PyQt5.QtCore import Qt, QTimer

from src.utils.id_card_generator import UserInfoGenerator
from src.utils.id_card_filler import IDCardFiller
from src.ui.tabs import TestDataTab, DataQueryTab, ApiToolTab  # 修改导入方式
from src.utils.resource_utils import resource_path

# 条件导入接口自动化标签页
try:
    from src.ui.tabs.interface_auto_tab import InterfaceAutoTab
    INTERFACE_AUTO_AVAILABLE = True
except ImportError as e:
    print(f"接口自动化模块不可用: {e}")
    INTERFACE_AUTO_AVAILABLE = False

# 条件导入卡片工具标签页
try:
    from src.ui.tabs.tool_cards_tab import ToolCardsTab
    TOOL_CARDS_AVAILABLE = True
except ImportError as e:
    print(f"卡片工具模块不可用: {e}")
    TOOL_CARDS_AVAILABLE = False


class MainWindow(QMainWindow):
    def __init__(self, config=None):
        super().__init__()

        # 标记是否已经初始化
        self._initialized = False

        # 存储配置
        self.config = config or {}

        # 获取功能开关状态
        self.enable_interface_auto = self.config.get("features", {}).get("interface_automation", False)
        self.enable_tool_cards = self.config.get("features", {}).get("tool_cards", False)


        self.setWindowTitle("测试工具")
        self.setGeometry(100, 100, 1720, 700)

        # 设置窗口图标
        self.setWindowIcon(self.create_icon())

        # 初始化生成器
        self.generator = UserInfoGenerator()

        self.id_card_template_path = "src/resources/images/id_card_template.png"

        # 使用 resource_path 处理模板路径
        template_path = resource_path(self.id_card_template_path)
        print(f"加载模板: {template_path}")

        # 确保路径正确
        if not os.path.exists(template_path):
            # 尝试直接使用 resources 目录
            static_template = os.path.normpath(self.id_card_template_path)
            if os.path.exists(static_template):
                template_path = static_template
            else:
                QMessageBox.critical(self, "文件缺失", "无法找到身份证模板文件")
                return

        print(f"最终使用的模板路径: {template_path}")
        self.filler = IDCardFiller(template_path)

        # 存储生成的身份证数据
        self.id_data = None
        self.front_image = None
        self.back_image = None

        # 创建UI
        self.init_ui()

        # 标记为已初始化
        self._initialized = True

    def init_ui(self):
        """初始化UI，确保只执行一次"""
        if hasattr(self, '_ui_initialized') and self._ui_initialized:
            return

        # 设置应用样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
            QLabel {
                font-size: 14px;
                color: #333333;
            }
            QLineEdit, QComboBox {
                font-size: 14px;
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #4CAF50;
                outline: none;
            }
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 10px 18px;
                border: none;
                border-radius: 6px;
                background-color: #4CAF50;
                color: white;
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
            QTabWidget::pane {
                border: 1px solid #C2C7CB;
                background-color: white;
            }
            QTabWidget::tab-bar {
                alignment: left;  /* 左对齐 */
            }
            QTabBar::tab {
                background-color: #E1E1E1;
                border: 1px solid #C4C4C3;
                padding: 8px 16px;
                height: 18px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
                color: white;
                border-color: #4CAF50;
            }
            QTabBar::tab:!selected {
                background-color: #E1E1E1;
                color: #333333;
            }
            QTabBar::tab:!selected:hover {
                background-color: #D1D1D1;
            }
            QRadioButton {
                font-size: 14px;
                spacing: 6px;
            }
        """)

        # 创建Tab Widget
        tab_widget = QTabWidget()
        tab_widget.setContentsMargins(0, 0, 0, 0)

        # 设置Tab位置为上方（默认），并设置对齐方式为左对齐
        tab_widget.setTabPosition(QTabWidget.North)
        tab_widget.setUsesScrollButtons(False)

        # 创建各个Tab
        self.test_data_tab = TestDataTab(self)
        self.data_query_tab = DataQueryTab(self)
        self.api_tool_tab = ApiToolTab(self)

        # 添加Tab到Tab Widget
        tab_widget.addTab(self.test_data_tab, "测试数据")
        tab_widget.addTab(self.data_query_tab, "数据查询")
        tab_widget.addTab(self.api_tool_tab, "接口工具")

        # 条件加载接口自动化标签页
        if self.enable_interface_auto and INTERFACE_AUTO_AVAILABLE:
            try:
                self.interface_auto_tab = InterfaceAutoTab(self)
                tab_widget.addTab(self.interface_auto_tab, "接口自动化")
                print("接口自动化标签页已加载")
                
                # 延迟初始化接口自动化标签页，避免启动时出现短暂小窗口
                QTimer.singleShot(800, self.interface_auto_tab.delayed_init)
            except Exception as e:
                print(f"加载接口自动化标签页失败: {e}")
        else:
            print("接口自动化功能已禁用或模块不可用")

        # 条件加载卡片工具标签页
        if self.enable_tool_cards and TOOL_CARDS_AVAILABLE:
            try:
                self.tool_cards_tab = ToolCardsTab(self)
                tab_widget.addTab(self.tool_cards_tab, '卡片工具')
                print("卡片工具标签页已加载")
            except Exception as e:
                print(f"加载卡片工具标签页失败: {e}")
        else:
            print("卡片工具功能已禁用或模块不可用")

        # 设置Tab Widget为中心部件
        self.setCentralWidget(tab_widget)

        # 标记UI已初始化
        self._ui_initialized = True

    def pil_image_to_qimage(self, pil_image):
        """将PIL图像转换为QImage"""
        try:
            if pil_image.mode == "RGB":
                # 直接使用RGB格式，不需要交换通道
                data = pil_image.tobytes()
                qimage = QImage(data, pil_image.width, pil_image.height,
                                pil_image.width * 3, QImage.Format_RGB888)
            elif pil_image.mode == "RGBA":
                # 直接使用RGBA格式，不需要交换通道
                data = pil_image.tobytes()
                qimage = QImage(data, pil_image.width, pil_image.height,
                                pil_image.width * 4, QImage.Format_RGBA8888)
            else:
                # 其他模式转换为RGB
                pil_image_rgb = pil_image.convert("RGB")
                data = pil_image_rgb.tobytes()
                qimage = QImage(data, pil_image_rgb.width, pil_image_rgb.height,
                                pil_image_rgb.width * 3, QImage.Format_RGB888)

            return qimage
        except Exception as e:
            print(f"图像转换错误: {e}")
            # 返回一个空的QImage作为备用
            return QImage(600, 375, QImage.Format_RGB888)

    def create_icon(self):
        """创建应用图标"""
        try:
            # 尝试加载图标文件
            icon_path = resource_path("src/resources/icons/app_icon.ico")

            if not os.path.exists(icon_path):
                # 如果找不到ico文件，尝试png文件
                icon_path = resource_path("src/resources/icons/app_icon.png")

            if os.path.exists(icon_path):
                return QIcon(icon_path)
            else:
                print("警告: 无法找到图标文件，使用默认图标")
                # 创建一个简单的默认图标
                return self.create_default_icon()
        except Exception as e:
            print(f"加载图标时出错: {e}")
            return self.create_default_icon()

    def create_default_icon(self):
        """创建默认图标"""
        # 创建一个简单的彩色图标
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(76, 175, 80))  # 绿色背景

        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "ID")
        painter.end()

        return QIcon(pixmap)
