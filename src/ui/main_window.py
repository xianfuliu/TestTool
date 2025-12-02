import os
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QMessageBox, QMenuBar, QMenu, QAction, QApplication)
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon, QPainter, QColor
from PyQt5.QtCore import Qt, QTimer, QEvent

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

# 条件导入变量管理对话框
try:
    from src.ui.interface_auto.variable_management import VariableManagement
    VARIABLE_MANAGEMENT_AVAILABLE = True
except ImportError as e:
    print(f"变量管理模块不可用: {e}")
    VARIABLE_MANAGEMENT_AVAILABLE = False


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
        # 设置更合适的初始窗口大小，避免全屏时界面元素显示不全
        # 延迟到show之后再获取屏幕尺寸
        self.initial_width = 1720
        self.initial_height = 700
        self.setMinimumSize(1200, 1000)  # 设置最小窗口尺寸
        self.setGeometry(100, 100, self.initial_width, self.initial_height)

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
        
        # 存储调度服务实例
        self.scheduler_service = None

    def show_and_maximize(self):
        """显示窗口并根据屏幕尺寸调整，确保在屏幕尺寸可用后调用"""
        # 获取当前屏幕尺寸
        screen_geometry = QApplication.desktop().screenGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        
        # 根据屏幕尺寸设置窗口大小
        if screen_width >= 1920 and screen_height >= 1080:
            # 大屏幕可以直接最大化
            self.showMaximized()
        else:
            # 对于小屏幕，先设置合适尺寸再显示
            window_width = min(self.initial_width, screen_width - 50)
            window_height = min(self.initial_height, screen_height - 50)
            
            # 确保不低于最小尺寸
            window_width = max(window_width, 1200)
            window_height = max(window_height, 600)
            
            self.resize(window_width, window_height)
            self.move((screen_width - window_width) // 2, (screen_height - window_height) // 2)
            self.show()

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
            QMessageBox {
                background-color: white;
                color: #333333;
                font-size: 14px;
            }
            QMessageBox QLabel {
                color: #333333;
                font-size: 14px;
            }
            QMessageBox QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #45a049;
            }
            QMessageBox QPushButton:pressed {
                background-color: #3d8b40;
            }
            /* 添加QDialogButtonBox样式，修复按钮背景消失问题 */
            QDialogButtonBox QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                min-width: 80px;
            }
            QDialogButtonBox QPushButton:hover {
                background-color: #45a049;
            }
            QDialogButtonBox QPushButton:pressed {
                background-color: #3d8b40;
            }
            QDialogButtonBox QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            /* 添加QToolTip样式，修复黑色背景问题 */
            QToolTip {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
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
        
        # 存储tab widget引用
        self.tab_widget = tab_widget
        
        # 连接tab切换信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

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


    def open_variable_management(self):
        """打开变量管理对话框"""
        if not VARIABLE_MANAGEMENT_AVAILABLE:
            QMessageBox.warning(self, "功能不可用", "变量管理模块不可用，请检查模块依赖")
            return

        try:
            # 创建变量管理对话框
            dialog = VariableManagement(self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开变量管理失败: {str(e)}")
    
    def set_scheduler_service(self, scheduler_service):
        """设置调度服务实例"""
        self.scheduler_service = scheduler_service
    
    def closeEvent(self, event):
        """重写关闭事件，确保调度服务正确停止"""
        try:
            if self.scheduler_service:
                print("正在停止调度后台服务...")
                self.scheduler_service.stop_service()
                print("调度后台服务已停止")
        except Exception as e:
            print(f"停止调度服务时出错: {e}")
        
        # 接受关闭事件
        event.accept()
    
    def on_tab_changed(self, index):
        """Tab切换事件处理
        
        Args:
            index: 新选中的tab索引
        """
        try:
            # 获取当前tab的widget
            current_widget = self.tab_widget.widget(index)
            
            # 如果切换到接口自动化tab，隐藏业务管理页面的操作按钮
            if (self.enable_interface_auto and INTERFACE_AUTO_AVAILABLE and 
                hasattr(self, 'interface_auto_tab') and current_widget == self.interface_auto_tab):
                
                # 检查接口自动化tab是否已经初始化
                if hasattr(self.interface_auto_tab, 'business_management'):
                    business_management = self.interface_auto_tab.business_management
                    
                    # 如果业务管理页面存在，隐藏操作按钮
                    if business_management:
                        # 调用业务管理页面的按钮隐藏方法
                        if hasattr(business_management, 'hide_all_operation_buttons_except_current'):
                            business_management.hide_all_operation_buttons_except_current()
                        
                        print("Tab切换：已隐藏业务管理页面的操作按钮")
                            
        except Exception as e:
            print(f"处理tab切换事件时出错: {e}")
