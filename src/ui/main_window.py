import os
from PyQt5.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QMessageBox,
    QMenuBar,
    QMenu,
    QAction,
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QLabel,
    QFrame,
    QScrollArea,
    QSizePolicy,
)
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon, QPainter, QColor
from PyQt5.QtCore import Qt, QTimer, QEvent, QSize

from src.utils.id_card_generator import UserInfoGenerator
from src.utils.id_card_filler import IDCardFiller
from src.ui.tabs import TestDataTab, DataQueryTab, ApiToolTab

# 条件导入API管理标签页
try:
    from src.ui.tabs.api_management_tab import ApiManagementTab

    API_MANAGEMENT_AVAILABLE = True
except ImportError as e:
    print(f"API管理模块不可用: {e}")
    API_MANAGEMENT_AVAILABLE = False
from src.core.services.user_service import UserService
from src.core.services.session_service import SessionService
from src.utils.resource_utils import resource_path
from src.ui.widgets.toast_tips import Toast

# 条件导入调度服务
try:
    from src.core.services.scheduler_service import UnifiedSchedulerService

    SCHEDULER_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"调度服务模块不可用: {e}")
    SCHEDULER_SERVICE_AVAILABLE = False

# 条件导入接口自动化标签页
try:
    from src.ui.tabs.interface_auto_tab import InterfaceAutoTab
    INTERFACE_AUTO_AVAILABLE = True
except ImportError as e:
    print(f"接口自动化模块不可用: {e}")
    INTERFACE_AUTO_AVAILABLE = False

# 条件导入CollapseButton组件
try:
    from src.ui.interface_auto.components.collapse_button import CollapseButton
    COLLAPSE_BUTTON_AVAILABLE = True
except ImportError as e:
    print(f"CollapseButton模块不可用: {e}")
    COLLAPSE_BUTTON_AVAILABLE = False
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
        self.enable_interface_auto = self.config.get("features", {}).get(
            "interface_automation", False
        )
        self.enable_tool_cards = self.config.get("features", {}).get(
            "tool_cards", False
        )
        self.enable_api_management = self.config.get("features", {}).get(
            "api_management", True
        )

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
                Toast.critical(self, "文件缺失", "无法找到身份证模板文件")
                return

        print(f"最终使用的模板路径: {template_path}")
        self.filler = IDCardFiller(template_path)

        # 存储生成的身份证数据
        self.id_data = None
        self.front_image = None
        self.back_image = None

        # 存储生成的营业执照数据
        self.business_license_data = None
        self.business_license_image = None

        # 创建UI
        self.init_ui()

        # 标记为已初始化
        self._initialized = True

        # 存储调度服务实例
        self.scheduler_service = None

        # 用户管理相关
        self.current_user = None
        self.user_service = UserService()

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
            self.move(
                (screen_width - window_width) // 2, (screen_height - window_height) // 2
            )
            self.show()

    def init_ui(self):
        """初始化UI，确保只执行一次"""
        if hasattr(self, "_ui_initialized") and self._ui_initialized:
            return

        # 设置应用样式
        self.setStyleSheet(
            """
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
                border: 1px solid #DCDFE6;
                border-top: none;
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #f8fafc, stop: 1 #f1f5f9);
                border-radius: 0 4px 4px 4px;
                margin-top: -1px; /* 消除pane与tab之间的间隙 */
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar {
                border-bottom: 1px solid #E4E7ED;
            }
            QTabBar::tab {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #f8fafc, stop: 1 #f1f5f9);
                border: 1px solid #DCDFE6;
                border-bottom: none;
                padding: 10px 20px;
                height: 22px;
                margin-right: 0px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 100px;
                font-weight: 500;
                font-size: 15px;
                color: #606266;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ffffff, stop: 1 #f8fafc);
                color: #409EFF;
                border-color: #DCDFE6;
                border-bottom-color: #ffffff;
            }
            QTabBar::tab:!selected {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #f8fafc, stop: 1 #f1f5f9);
                color: #606266;
            }
            QTabBar::tab:!selected:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ECF5FF, stop: 1 #f8fafc);
                color: #409EFF;
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
        """
        )

        # 创建主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建左侧菜单栏
        self.left_menu = self.create_left_menu()
        main_layout.addWidget(self.left_menu)
        
        # 创建收起按钮（放在菜单容器的外部右侧）
        self.collapse_button = self.create_collapse_button()
        self.collapse_button.state_changed.connect(self.on_collapse_state_changed)
        main_layout.addWidget(self.collapse_button, 0, Qt.AlignLeft)

        # 创建右侧内容区域
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建内容堆栈窗口
        self.content_stack = QWidget()
        self.content_stack_layout = QVBoxLayout(self.content_stack)
        self.content_stack_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建各个Tab
        self.test_data_tab = TestDataTab(self)
        self.data_query_tab = DataQueryTab(self)
        self.api_tool_tab = ApiToolTab(self)

        # 添加Tab到内容堆栈
        self.content_stack_layout.addWidget(self.test_data_tab)
        self.test_data_tab.hide()

        # 条件加载卡片工具标签页
        if self.enable_tool_cards and TOOL_CARDS_AVAILABLE:
            try:
                self.tool_cards_tab = ToolCardsTab(self)
                self.content_stack_layout.addWidget(self.tool_cards_tab)
                self.tool_cards_tab.hide()
                print("卡片工具标签页已加载")
            except Exception as e:
                print(f"加载卡片工具标签页失败: {e}")
        else:
            print("卡片工具功能已禁用或模块不可用")

        self.content_stack_layout.addWidget(self.api_tool_tab)
        self.api_tool_tab.hide()

        # 条件加载接口自动化标签页
        if self.enable_interface_auto and INTERFACE_AUTO_AVAILABLE:
            try:
                self.interface_auto_tab = InterfaceAutoTab(self)
                self.content_stack_layout.addWidget(self.interface_auto_tab)
                self.interface_auto_tab.hide()
                print("接口自动化标签页已加载")

                # 延迟初始化接口自动化标签页，避免启动时出现短暂小窗口
                QTimer.singleShot(800, self.interface_auto_tab.delayed_init)
            except Exception as e:
                print(f"加载接口自动化标签页失败: {e}")
        else:
            print("接口自动化功能已禁用或模块不可用")

        # 条件加载API管理标签页
        if self.enable_api_management and API_MANAGEMENT_AVAILABLE:
            try:
                self.api_management_tab = ApiManagementTab(self)
                self.content_stack_layout.addWidget(self.api_management_tab)
                self.api_management_tab.hide()
                print("API管理标签页已加载")
            except Exception as e:
                print(f"加载API管理标签页失败: {e}")
        else:
            print("API管理功能已禁用或模块不可用")

        # 数据查询放到最后
        self.content_stack_layout.addWidget(self.data_query_tab)
        self.data_query_tab.hide()

        # 添加设置和退出页面
        self.settings_tab = self.create_fake_settings_tab()
        self.content_stack_layout.addWidget(self.settings_tab)
        self.settings_tab.hide()
        
        self.logout_tab = self.create_fake_logout_tab()
        self.content_stack_layout.addWidget(self.logout_tab)
        self.logout_tab.hide()

        # 将内容堆栈添加到内容区域
        self.content_layout.addWidget(self.content_stack)
        
        # 添加内容区域到主布局
        main_layout.addWidget(self.content_area)
        main_layout.setStretchFactor(self.content_area, 1)

        # 设置主部件为中心部件
        self.setCentralWidget(main_widget)

        # 默认显示第一个tab
        self.show_tab(0)

        # 标记UI已初始化
        self._ui_initialized = True

    def pil_image_to_qimage(self, pil_image):
        """将PIL图像转换为QImage"""
        try:
            if pil_image.mode == "RGB":
                # 直接使用RGB格式，不需要交换通道
                data = pil_image.tobytes()
                qimage = QImage(
                    data,
                    pil_image.width,
                    pil_image.height,
                    pil_image.width * 3,
                    QImage.Format_RGB888,
                )
            elif pil_image.mode == "RGBA":
                # 直接使用RGBA格式，不需要交换通道
                data = pil_image.tobytes()
                qimage = QImage(
                    data,
                    pil_image.width,
                    pil_image.height,
                    pil_image.width * 4,
                    QImage.Format_RGBA8888,
                )
            else:
                # 其他模式转换为RGB
                pil_image_rgb = pil_image.convert("RGB")
                data = pil_image_rgb.tobytes()
                qimage = QImage(
                    data,
                    pil_image_rgb.width,
                    pil_image_rgb.height,
                    pil_image_rgb.width * 3,
                    QImage.Format_RGB888,
                )

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
            Toast.warning(self, "功能不可用", "变量管理模块不可用，请检查模块依赖")
            return

        try:
            # 创建变量管理对话框
            dialog = VariableManagement(self)
            dialog.exec_()
        except Exception as e:
            Toast.critical(self, "错误", f"打开变量管理失败: {str(e)}")

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
        """Tab切换事件处理 - 已弃用，使用新的左侧菜单系统"""
        # 这个方法现在由show_tab方法处理
        pass

    def set_current_user(self, user):
        """设置当前登录用户"""
        self.current_user = user
        # 更新窗口标题
        self.setWindowTitle(f"测试工具-{user.username}")
        
        # 重新创建左侧菜单以更新权限相关的菜单项
        if hasattr(self, "left_menu"):
            # 保存当前显示的tab索引
            current_tab_index = 0
            if hasattr(self, "menu_items") and self.menu_items:
                for item in self.menu_items:
                    if hasattr(item, 'tab_index') and hasattr(item, 'styleSheet'):
                        if "background-color: #007bff" in item.styleSheet():
                            current_tab_index = item.tab_index
                            break
            
            # 重新创建左侧菜单
            self.left_menu.deleteLater()
            self.left_menu = self.create_left_menu()
            
            # 将新的左侧菜单添加到主布局
            main_widget = self.centralWidget()
            main_layout = main_widget.layout()
            main_layout.insertWidget(0, self.left_menu)
            
            # 恢复之前显示的tab
            self.show_tab(current_tab_index)

    def create_user_menu(self):
        """创建用户菜单 - 已弃用，退出功能已移至tab菜单栏"""
        # 不再创建用户菜单，退出功能已通过图标按钮实现
        pass

    def restart_scheduler_service(self):
        """重新启动调度服务"""
        if not SCHEDULER_SERVICE_AVAILABLE:
            print("调度服务模块不可用，跳过重启")
            return

        try:
            # 检查是否已经有调度服务实例
            if self.scheduler_service:
                # 如果服务正在运行，先停止
                if (
                    hasattr(self.scheduler_service, "running")
                    and self.scheduler_service.running
                ):
                    print("调度服务正在运行，先停止...")
                    self.scheduler_service.stop_service()

                # 重新创建调度服务实例
                self.scheduler_service = UnifiedSchedulerService()
            else:
                # 创建新的调度服务实例
                self.scheduler_service = UnifiedSchedulerService()

            # 启动调度服务
            print("正在启动调度服务...")
            if self.scheduler_service.start_service():
                print("调度服务启动成功")
                # 检查是否成功获取分布式锁
                if (
                    hasattr(self.scheduler_service, "running")
                    and self.scheduler_service.running
                ):
                    print("当前实例持有调度锁，调度服务已启动")
                else:
                    print("检测到已有调度服务实例在运行，当前实例作为只读客户端")
            else:
                print("调度服务启动失败")

        except Exception as e:
            print(f"重启调度服务时出错: {e}")

    def handle_settings(self):
        """处理设置按钮点击"""
        if self.current_user and self.current_user.is_admin:
            # 只有admin用户可以打开全局设置
            from src.ui.dialogs.global_email_config_dialog import (
                GlobalEmailConfigDialog,
            )

            dialog = GlobalEmailConfigDialog(self)
            dialog.exec_()
        else:
            Toast.warning(self, "权限不足", "只有管理员可以访问全局设置")

    def handle_logout(self):
        """处理用户登出"""
        if self.current_user:
            # 创建自定义确认对话框，使用"确认"和"取消"按钮
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("确认登出")
            msg_box.setText(f"确定要登出用户 {self.current_user.username} 吗？")
            msg_box.setIcon(QMessageBox.Question)

            # 添加自定义按钮
            confirm_button = msg_box.addButton("确认", QMessageBox.YesRole)
            cancel_button = msg_box.addButton("取消", QMessageBox.NoRole)

            # 设置默认按钮
            msg_box.setDefaultButton(cancel_button)

            # 显示对话框并获取结果
            msg_box.exec_()

            if msg_box.clickedButton() == confirm_button:
                # 执行登出逻辑
                self.perform_logout()

    def perform_logout(self):
        """执行登出操作"""
        try:
            # 检查登录开关配置
            import sys
            import os

            sys.path.append(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
            )
            from main import load_config

            config = load_config()
            enable_login = config.get("auth", {}).get("enable_login", True)

            # 只有在启用登录功能时才删除session文件
            if enable_login:
                session_service = SessionService()
                session_service.delete_session()

            # 关闭主窗口
            self.close()

            # 只有在启用登录功能时才重新启动认证页面
            if enable_login:
                from src.ui.auth_page import AuthPage

                auth_page = AuthPage(enable_login=enable_login)
                auth_page.showMaximized()

                # 连接认证成功信号
                def on_login_success(user):
                    auth_page.close()
                    # 重新设置当前用户并显示主窗口
                    self.set_current_user(user)
                    self.show_and_maximize()
                    # 重新启动调度服务（如果存在）
                    self.restart_scheduler_service()
                    # 显示登录成功Toast提示
                    Toast.success(self, f"欢迎回来，{user.username}!")

                auth_page.login_success.connect(on_login_success)
            else:
                # 登录功能已关闭，直接退出应用程序
                print("登录功能已关闭，应用程序将退出")
                QApplication.quit()

        except Exception as e:
            Toast.critical(self, "登出错误", f"登出过程中发生错误: {str(e)}")

    def get_current_user(self):
        """获取当前用户"""
        return self.current_user

    def create_fake_settings_tab(self):
        """创建假的设置tab"""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
        
        class FakeSettingsTab(QWidget):
            def __init__(self, parent):
                super().__init__(parent)
                self.parent = parent
                self.init_ui()
            
            def init_ui(self):
                layout = QVBoxLayout(self)
                layout.setAlignment(Qt.AlignCenter)
                
                label = QLabel("点击设置标签将打开全局设置对话框")
                label.setStyleSheet("font-size: 16px; color: #666;")
                layout.addWidget(label)
        
        return FakeSettingsTab(self)

    def create_fake_logout_tab(self):
        """创建假的退出tab"""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
        
        class FakeLogoutTab(QWidget):
            def __init__(self, parent):
                super().__init__(parent)
                self.parent = parent
                self.init_ui()
            
            def init_ui(self):
                layout = QVBoxLayout(self)
                layout.setAlignment(Qt.AlignCenter)
                
                label = QLabel("点击退出标签将退出当前登录")
                label.setStyleSheet("font-size: 16px; color: #666;")
                layout.addWidget(label)
        
        return FakeLogoutTab(self)

    def create_left_menu(self):
        """创建左侧菜单栏"""
        # 创建左侧菜单容器
        menu_container = QFrame()
        menu_container.setFixedWidth(250)
        menu_container.setStyleSheet("""
            QFrame {
                background-color: rgb(48, 65, 86);
                border-right: 1px solid rgb(48, 65, 86);
            }
        """)
        
        # 创建水平布局来放置菜单
        container_layout = QHBoxLayout(menu_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 创建菜单框架
        menu_frame = QFrame()
        menu_frame.setFixedWidth(250)
        menu_frame.setStyleSheet("""
            QFrame {
                background-color: rgb(48, 65, 86);
                border: none;
            }
        """)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: rgb(48, 65, 86);
            }
            QScrollBar:vertical {
                background-color: rgb(48, 65, 86);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #1890ff;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #40a9ff;
            }
        """)
        
        # 创建菜单内容容器
        menu_content = QWidget()
        menu_content.setStyleSheet("""
            QWidget {
                background-color: rgb(48, 65, 86);
            }
        """)
        menu_layout = QVBoxLayout(menu_content)
        menu_layout.setContentsMargins(0, 0, 0, 10)
        menu_layout.setSpacing(0)
        
        # 创建菜单项
        self.menu_items = []
        
        # 初始化子菜单项列表
        self.submenu_items = []
        
        # 当前选中的子菜单项索引
        self.current_submenu_index = None
        
        # 测试数据菜单项
        test_data_item = self.create_menu_item("测试数据", 0)
        menu_layout.addWidget(test_data_item)
        
        # 卡片工具菜单项（如果可用）
        if self.enable_tool_cards and TOOL_CARDS_AVAILABLE:
            tool_cards_item = self.create_menu_item("卡片工具", 1)
            menu_layout.addWidget(tool_cards_item)
        
        # 接口工具菜单项
        api_tool_item = self.create_menu_item("接口工具", 2)
        menu_layout.addWidget(api_tool_item)
        
        # 接口自动化菜单项（如果可用）
        if self.enable_interface_auto and INTERFACE_AUTO_AVAILABLE:
            interface_auto_item = self.create_expandable_menu_item("接口自动化", 3)
            menu_layout.addWidget(interface_auto_item)
        
        # API管理菜单项（如果可用）
        if self.enable_api_management and API_MANAGEMENT_AVAILABLE:
            api_management_item = self.create_menu_item("API管理", 4)
            menu_layout.addWidget(api_management_item)
        
        # 数据查询菜单项
        data_query_item = self.create_menu_item("数据查询", 5)
        menu_layout.addWidget(data_query_item)
        
        # 添加弹性空间
        menu_layout.addStretch(1)
        
        # 创建左下角图标区域
        self.create_bottom_icon_area(menu_layout)
        
        # 设置滚动区域的内容
        scroll_area.setWidget(menu_content)
        
        # 创建菜单框架布局
        menu_frame_layout = QVBoxLayout(menu_frame)
        menu_frame_layout.setContentsMargins(0, 0, 0, 0)
        menu_frame_layout.addWidget(scroll_area)
        
        # 添加菜单到容器
        container_layout.addWidget(menu_frame)
        
        return menu_container

    def create_menu_item(self, text, tab_index):
        """创建普通菜单项"""
        item_frame = QFrame()
        item_frame.setFixedHeight(45)
        item_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
            QFrame:hover {
                background-color: #1890ff;
            }
            QFrame[pressed="true"] {
                background-color: #096dd9;
            }
        """)
        
        layout = QHBoxLayout(item_frame)
        layout.setContentsMargins(20, 0, 10, 0)
        layout.setSpacing(10)
        
        # 菜单项文本
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #ffffff;
                font-weight: bold;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
        """)
        
        layout.addWidget(label)
        layout.addStretch(1)
        
        # 存储tab索引
        item_frame.tab_index = tab_index
        
        # 添加点击事件
        item_frame.mousePressEvent = lambda event: self.on_menu_item_clicked(item_frame)
        
        self.menu_items.append(item_frame)
        return item_frame

    def create_expandable_menu_item(self, text, tab_index):
        """创建可展开的菜单项"""
        item_frame = QFrame()
        item_frame.setMinimumHeight(45)
        item_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
            QFrame:hover {
                background-color: #1890ff;
            }
            QFrame[pressed="true"] {
                background-color: #096dd9;
            }
        """)
        
        layout = QVBoxLayout(item_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 主菜单项
        main_item = QFrame()
        main_item.setFixedHeight(45)
        main_item.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        
        main_layout = QHBoxLayout(main_item)
        main_layout.setContentsMargins(20, 0, 10, 0)
        
        # 菜单项文本
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #ffffff;
                font-weight: bold;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
        """)
        
        # 展开/折叠箭头 - 使用图片资源
        arrow_label = QLabel()
        arrow_label.setFixedSize(16, 16)
        arrow_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
            }
        """)
        
        # 设置初始图标（折叠状态）
        expand_icon = self.get_icon("exband_w_left.png")
        if not expand_icon.isNull():
            pixmap = expand_icon.pixmap(16, 16)
            arrow_label.setPixmap(pixmap)
        else:
            # 如果图标加载失败，使用文本作为备用
            arrow_label.setText("▶")
            arrow_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: #ffffff;
                    background-color: transparent;
                    border: none;
                }
            """)
        
        main_layout.addWidget(label)
        main_layout.addStretch(1)
        main_layout.addWidget(arrow_label)
        
        # 子菜单容器（初始隐藏）
        submenu_frame = QFrame()
        submenu_frame.setVisible(False)
        submenu_frame.setStyleSheet("""
            QFrame {
                background-color: rgb(48, 65, 86);
                border: none;
            }
        """)
        submenu_layout = QVBoxLayout(submenu_frame)
        submenu_layout.setContentsMargins(30, 0, 0, 0)
        submenu_layout.setSpacing(0)
        
        # 动态获取接口自动化tab的子页面名称
        submenu_items = self.get_interface_auto_submenu_items()
        
        for sub_text, sub_index in submenu_items:
            sub_item = self.create_submenu_item(sub_text, sub_index)
            submenu_layout.addWidget(sub_item)
        
        layout.addWidget(main_item)
        layout.addWidget(submenu_frame)
        
        # 存储展开状态和引用
        item_frame.is_expanded = False
        item_frame.arrow_label = arrow_label
        item_frame.submenu_frame = submenu_frame
        item_frame.tab_index = tab_index
        
        # 计算子菜单总高度（动态计算）
        item_frame.submenu_height = len(submenu_items) * 40
        
        # 添加点击事件
        main_item.mousePressEvent = lambda event: self.toggle_expandable_menu(item_frame)
        
        self.menu_items.append(item_frame)
        return item_frame

    def create_submenu_item(self, text, tab_index):
        """创建子菜单项"""
        item_frame = QFrame()
        item_frame.setFixedHeight(40)
        item_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
            QFrame:hover {
                background-color: #1890ff;
            }
            QFrame[pressed="true"] {
                background-color: #096dd9;
            }
        """)
        
        layout = QHBoxLayout(item_frame)
        layout.setContentsMargins(20, 0, 10, 0)
        
        # 子菜单项文本
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                font-size: 15px;
                color: #ffffff;
                font-weight: bold;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
        """)
        
        layout.addWidget(label)
        
        # 存储tab索引
        item_frame.tab_index = tab_index
        item_frame.submenu_text = text
        
        # 初始选中状态为False
        item_frame.is_selected = False
        
        # 添加点击事件
        item_frame.mousePressEvent = lambda event: self.on_submenu_item_clicked(item_frame)
        
        # 添加到子菜单项列表
        self.submenu_items.append(item_frame)
        
        return item_frame

    def toggle_expandable_menu(self, menu_frame):
        """切换可展开菜单的状态"""
        menu_frame.is_expanded = not menu_frame.is_expanded
        
        if menu_frame.is_expanded:
            # 展开状态：使用向下箭头图标
            expand_icon = self.get_icon("exband_w_down.png")
            if not expand_icon.isNull():
                pixmap = expand_icon.pixmap(16, 16)
                menu_frame.arrow_label.setPixmap(pixmap)
            else:
                # 如果图标加载失败，使用文本作为备用
                menu_frame.arrow_label.setText("▼")
            
            # 展开后自动展示所有子菜单
            menu_frame.submenu_frame.setVisible(True)
            
            # 动态调整菜单项高度
            menu_frame.setFixedHeight(45 + menu_frame.submenu_height)
        else:
            # 折叠状态：使用向右箭头图标
            expand_icon = self.get_icon("exband_w_left.png")
            if not expand_icon.isNull():
                pixmap = expand_icon.pixmap(16, 16)
                menu_frame.arrow_label.setPixmap(pixmap)
            else:
                # 如果图标加载失败，使用文本作为备用
                menu_frame.arrow_label.setText("▶")
            
            menu_frame.submenu_frame.setVisible(False)
            
            # 恢复菜单项高度
            menu_frame.setFixedHeight(45)
        
        # 强制刷新布局，确保下方tab自动下移
        menu_frame.parent().updateGeometry()
        menu_frame.parent().adjustSize()

    def on_menu_item_clicked(self, item_frame):
        """处理菜单项点击"""
        # 清除所有子菜单项的选中状态（当点击主菜单项时）
        if hasattr(self, 'submenu_items') and self.submenu_items:
            for sub_item in self.submenu_items:
                if hasattr(sub_item, 'is_selected'):
                    sub_item.is_selected = False
        
        # 更新选中状态
        self.update_menu_selection(item_frame.tab_index)
        
        # 显示对应的tab
        self.show_tab(item_frame.tab_index)

    def on_submenu_item_clicked(self, item_frame):
        """处理子菜单项点击"""
        # 首先清除所有子菜单项的选中状态
        if hasattr(self, 'submenu_items') and self.submenu_items:
            for sub_item in self.submenu_items:
                if hasattr(sub_item, 'is_selected'):
                    sub_item.is_selected = False
        
        # 设置当前子菜单项为选中状态
        item_frame.is_selected = True
        
        # 设置当前选中的子菜单项索引
        self.current_submenu_index = item_frame.tab_index
        
        # 更新选中状态
        self.update_menu_selection(item_frame.tab_index)
        
        # 显示对应的tab
        self.show_tab(item_frame.tab_index)
        
        # 这里可以添加子菜单项特定的逻辑
        print(f"点击了子菜单项: {item_frame.submenu_text}")
        
        # 如果是接口自动化tab的子菜单项，需要切换到对应的子页面
        if item_frame.tab_index == 3 and hasattr(self, 'interface_auto_tab'):
            self.switch_interface_auto_subpage(item_frame.submenu_text)

    def get_interface_auto_submenu_items(self):
        """获取接口自动化tab的子菜单项"""
        # 定义接口自动化tab的实际子页面名称
        submenu_items = [
            ("业务管理", 3),
            ("接口模板", 3),
            ("用例管理", 3),
            ("定时调度", 3),
            ("测试报告", 3),
            ("全局工具", 3),
            ("变量管理", 3)
        ]
        return submenu_items

    def switch_interface_auto_subpage(self, subpage_name):
        """切换接口自动化tab的子页面"""
        if not hasattr(self, 'interface_auto_tab') or not self.interface_auto_tab:
            print("接口自动化tab未加载，无法切换子页面")
            return
        
        # 切换到接口自动化tab
        self.show_tab(3)
        
        # 调用接口自动化tab的切换方法
        if hasattr(self.interface_auto_tab, 'switch_to_subpage'):
            self.interface_auto_tab.switch_to_subpage(subpage_name)
            
            # 更新对应的子菜单项选中状态
            if hasattr(self, 'submenu_items') and self.submenu_items:
                for sub_item in self.submenu_items:
                    if hasattr(sub_item, 'submenu_text') and sub_item.submenu_text == subpage_name:
                        # 清除所有子菜单项的选中状态
                        for item in self.submenu_items:
                            if hasattr(item, 'is_selected'):
                                item.is_selected = False
                        
                        # 设置当前子菜单项为选中状态
                        sub_item.is_selected = True
                        break
            
            # 更新菜单选中状态
            self.update_menu_selection(3)
        else:
            print("接口自动化tab没有switch_to_subpage方法")

    def update_menu_selection(self, selected_index):
        """更新菜单选中状态"""
        # 更新主菜单项选中状态
        for item in self.menu_items:
            if hasattr(item, 'tab_index'):
                if item.tab_index == selected_index:
                    item.setStyleSheet("""
                        QFrame {
                            background-color: #1890ff;
                            border: none;
                        }
                        QLabel {
                            font-size: 14px;
                            color: #ffffff;
                            font-weight: bold;
                            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                        }
                    """)
                else:
                    item.setStyleSheet("""
                        QFrame {
                            background-color: transparent;
                            border: none;
                        }
                        QFrame:hover {
                            background-color: #1890ff;
                        }
                        QLabel {
                            font-size: 14px;
                            color: #ffffff;
                            font-weight: bold;
                            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                        }
                    """)
        
        # 更新子菜单项选中状态
        if hasattr(self, 'submenu_items') and self.submenu_items:
            for sub_item in self.submenu_items:
                if hasattr(sub_item, 'tab_index'):
                    # 检查是否是当前选中的子菜单项
                    if hasattr(sub_item, 'is_selected') and sub_item.is_selected:
                        sub_item.setStyleSheet("""
                            QFrame {
                                background-color: #1890ff;
                                border: none;
                            }
                            QLabel {
                                font-size: 15px;
                                color: #ffffff;
                                font-weight: bold;
                                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                            }
                        """)
                    else:
                        sub_item.setStyleSheet("""
                            QFrame {
                                background-color: transparent;
                                border: none;
                            }
                            QFrame:hover {
                                background-color: #1890ff;
                            }
                            QLabel {
                                font-size: 15px;
                                color: #ffffff;
                                font-weight: bold;
                                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                            }
                        """)

    def create_bottom_icon_area(self, menu_layout):
        """创建左下角图标区域"""
        # 创建图标容器
        icon_container = QFrame()
        icon_container.setFixedHeight(60)
        icon_container.setStyleSheet("""
            QFrame {
                background-color: rgb(48, 65, 86);
                border-top: 1px solid #1890ff;
                border-radius: 0px;
            }
        """)
        
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setContentsMargins(10, 5, 10, 5)
        icon_layout.setSpacing(15)
        
        # 添加弹性空间，使图标靠左对齐
        icon_layout.addStretch(1)
        
        # 创建设置图标按钮（仅管理员可见）
        if hasattr(self, 'current_user') and self.current_user and self.current_user.is_admin:
            settings_icon = self.create_icon_button("settings.png", "设置", self.handle_settings)
            icon_layout.addWidget(settings_icon)
        
        # 创建退出图标按钮
        logout_icon = self.create_icon_button("logout.png", "退出", self.handle_logout)
        icon_layout.addWidget(logout_icon)
        
        # 添加弹性空间，使图标靠左对齐
        icon_layout.addStretch(1)
        
        menu_layout.addWidget(icon_container)

    def create_icon_button(self, icon_name, tooltip_text, click_handler):
        """创建图标按钮"""
        icon_frame = QFrame()
        icon_frame.setFixedSize(40, 40)
        icon_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                border-radius: 20px;
            }
            QFrame:hover {
                background-color: #1890ff;
                border: none;
            }
            QFrame:pressed {
                background-color: #096dd9;
                border: none;
            }
        """)
        
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignCenter)
        
        # 图标标签 - 使用图片资源
        icon_label = QLabel()
        icon_label.setFixedSize(24, 24)
        icon_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
            }
        """)
        
        # 获取图标并设置
        icon = self.get_icon(icon_name)
        if not icon.isNull():
            pixmap = icon.pixmap(24, 24)
            icon_label.setPixmap(pixmap)
        else:
            # 如果图标加载失败，使用文本作为备用
            icon_label.setText(icon_name.replace(".png", ""))
            icon_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: #ffffff;
                    background-color: transparent;
                    border: none;
                }
            """)
        
        icon_label.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(icon_label)
        
        # 设置工具提示
        icon_frame.setToolTip(tooltip_text)
        
        # 添加点击事件
        icon_frame.mousePressEvent = lambda event: click_handler()
        
        return icon_frame

    def get_icon(self, icon_name):
        """获取图标，支持exe打包后的资源路径"""
        import os
        import sys

        # 尝试多种路径方式加载图标
        icon_paths = [
            # 开发环境路径
            os.path.join("src", "resources", "icons", icon_name),
            # exe打包后路径
            os.path.join(
                os.path.dirname(sys.executable), "src", "resources", "icons", icon_name
            ),
            # 相对路径（如果exe在项目根目录）
            os.path.join("src", "resources", "icons", icon_name),
            # 临时解压路径（PyInstaller）
            (
                os.path.join(sys._MEIPASS, "src", "resources", "icons", icon_name)
                if hasattr(sys, "_MEIPASS")
                else None
            ),
        ]

        for path in icon_paths:
            if path and os.path.exists(path):
                return QIcon(path)

        # 如果所有路径都找不到，返回空图标
        return QIcon()

    def show_tab(self, tab_index):
        """显示指定的tab"""
        # 隐藏所有tab
        tabs = [
            self.test_data_tab,
            self.tool_cards_tab if self.enable_tool_cards and TOOL_CARDS_AVAILABLE else None,
            self.api_tool_tab,
            self.interface_auto_tab if self.enable_interface_auto and INTERFACE_AUTO_AVAILABLE else None,
            self.api_management_tab if self.enable_api_management and API_MANAGEMENT_AVAILABLE else None,
            self.data_query_tab
        ]
        
        for tab in tabs:
            if tab:
                tab.hide()
        
        # 显示选中的tab
        if tab_index < len(tabs) and tabs[tab_index]:
            tabs[tab_index].show()

        # 更新菜单选中状态
        self.update_menu_selection(tab_index)

    def create_collapse_button(self):
        """创建收起按钮"""
        if COLLAPSE_BUTTON_AVAILABLE:
            # 使用现有的CollapseButton组件
            button = CollapseButton(is_expanded=True)
        else:
            # 如果CollapseButton不可用，创建简单的按钮
            button = QPushButton()
            button.setFixedSize(24, 24)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: #ffffff;
                    font-size: 16px;
                    font-weight: bold;
                    margin: 0px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: transparent;
                    color: rgba(255, 255, 255, 0.8);
                }
                QPushButton:pressed {
                    background-color: transparent;
                    color: rgba(255, 255, 255, 0.6);
                }
            """)
            button.setText("◀")
            button.setToolTip("收起左侧菜单栏")
            
            # 手动实现状态切换
            button._is_expanded = True
            button.toggle_state = lambda: self._toggle_simple_collapse_button(button)
            button.state_changed = lambda expanded: self.on_collapse_state_changed(expanded)
            button.clicked.connect(button.toggle_state)
        
        return button

    def _toggle_simple_collapse_button(self, button):
        """切换简单收起按钮的状态"""
        button._is_expanded = not button._is_expanded
        if button._is_expanded:
            button.setText("◀")
            button.setToolTip("收起左侧菜单栏")
        else:
            button.setText("▶")
            button.setToolTip("展开左侧菜单栏")
        button.state_changed.emit(button._is_expanded)

    def on_collapse_state_changed(self, is_expanded):
        """处理展开/收缩状态变化"""
        # 获取主布局和左侧菜单容器
        main_widget = self.centralWidget()
        main_layout = main_widget.layout()
        
        # 找到左侧菜单容器（第一个widget）
        if main_layout.count() > 1:
            left_menu_container = main_layout.itemAt(0).widget()
            
            if is_expanded:
                # 展开状态：恢复菜单宽度并显示
                left_menu_container.setFixedWidth(250)
                left_menu_container.show()
                # 确保菜单内容可见
                for i in range(left_menu_container.layout().count()):
                    widget = left_menu_container.layout().itemAt(i).widget()
                    if widget:
                        widget.show()
            else:
                # 收起状态：隐藏菜单容器
                left_menu_container.setFixedWidth(0)
                left_menu_container.hide()
            
            # 强制刷新布局
            main_widget.updateGeometry()
            main_widget.adjustSize()
