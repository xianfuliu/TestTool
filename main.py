import logging
import sys
import os
import json
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt

from src.ui.main_window import MainWindow
from src.ui.loading_page import LoadingPage
from src.utils.resource_utils import resource_path
from src.utils.except_hook import excepthook
from src.core.services.scheduler_service import UnifiedSchedulerService

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))


def load_config():
    """加载配置文件"""
    config_path = resource_path("config/settings.json")
    default_config = {
        "features": {"interface_automation": False},
        "app": {"name": "测试工具管理", "version": "1.0.0"},
    }

    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # 如果配置文件不存在，创建默认配置
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            return default_config
    except Exception as e:
        logging.error(f"加载配置文件失败: {e}")
        return default_config


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("app.log"), logging.StreamHandler(sys.stdout)],
    )


def initialize_application():
    """初始化应用程序"""
    # 在应用程序启动前设置
    sys.excepthook = excepthook

    # 加载配置
    config = load_config()
    enable_interface_auto = config.get("features", {}).get(
        "interface_automation", False
    )
    enable_tool_cards = config.get("features", {}).get("tool_cards", False)

    app = QApplication(sys.argv)

    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # 检查必要的资源文件
    required_files = [
        "src/resources/images/id_card_template.png",
        "src/resources/images/ocr_face_1.png",
        "src/resources/images/ocr_face_2.png",
    ]

    missing_files = []
    for file_path in required_files:
        full_path = resource_path(file_path)
        if not os.path.exists(full_path):
            missing_files.append(file_path)

    if missing_files:
        print("警告: 以下文件缺失:")
        for file in missing_files:
            print(f"  - {file}")
        print("程序可能无法正常工作。")

    return app, config


def start_loading_page(app, config):
    """启动加载页面，初始化完成后跳转到认证页面"""
    from src.ui.auth_page import AuthPage

    # 检查登录开关配置
    enable_login = config.get("auth", {}).get("enable_login", True)

    # 创建主窗口实例（但不显示）
    window = MainWindow(config=config)

    # 创建加载页面，传入main_window实例和配置
    loading_page = LoadingPage(window, config)
    loading_page.show()

    # 设置应用程序图标
    app.setWindowIcon(window.create_icon())

    # 初始化服务变量
    token_service = None
    scheduler_service = None

    # 调度服务将在用户登录成功后启动
    # 这里只创建服务实例，但不启动（无论是否启用登录功能）
    try:
        scheduler_service = UnifiedSchedulerService()
        # 将调度服务实例传递给主窗口，但不启动
        window.set_scheduler_service(scheduler_service)
        print("调度服务实例已创建，将在用户登录后启动")
    except Exception as e:
        print(f"创建调度服务实例失败: {e}")

    # 只有在启用登录功能时才初始化数据库相关服务
    if enable_login:
        from src.core.services.token_service import TokenService
        from src.core.services.session_service import SessionService
        from src.core.services.user_service import UserService

        # 启动Token服务（每周清理任务）
        try:
            token_service = TokenService()
            token_service.start_weekly_cleanup()
            print("Token服务已启动，每周清理任务运行中")
        except Exception as e:
            print(f"启动Token服务失败: {e}")
    else:
        print("登录功能已关闭，跳过数据库相关服务初始化")

    # 创建认证页面（但不显示）
    auth_page = AuthPage(enable_login=enable_login)

    # 连接加载完成信号
    def on_loading_completed():
        """加载完成后显示认证页面或直接登录"""
        loading_page.close()

        # 检查登录开关配置
        enable_login = config.get("auth", {}).get("enable_login", True)

        if not enable_login:
            # 登录开关关闭，直接进入主页面
            print("登录功能已关闭，直接进入主页面")
            # 创建匿名用户或默认用户
            from src.core.models.user_model import User

            anonymous_user = User(
                id=0,
                username="匿名用户",
                email="anonymous@example.com",
                business_line="",
                is_admin=False,
            )
            window.set_current_user(anonymous_user)
            window.show_and_maximize()
            # 启动调度服务（无论是否启用登录功能）
            window.restart_scheduler_service()
            return

        # 只有在启用登录功能时才检查session
        if enable_login:
            from src.core.services.session_service import SessionService
            from src.core.services.user_service import UserService

            session_service = SessionService()
            user_service = UserService()

            session_data = session_service.validate_session(token_service)
            if session_data:
                # 有有效的session，直接登录
                print(
                    f"检测到有效session，自动登录用户: {session_data.get('username')}"
                )

                # 获取完整的用户信息
                user = user_service.get_user_by_id(session_data.get("user_id"))
                if user:
                    # 直接显示主窗口
                    window.set_current_user(user)
                    window.show_and_maximize()
                    # 自动登录成功后启动调度服务
                    window.restart_scheduler_service()
                    return
                else:
                    print("用户信息获取失败，显示登录页面")

            # 没有有效session，显示认证页面
            print("未检测到有效session，显示登录页面")
            auth_page.showMaximized()
        else:
            # 登录功能关闭，但代码不应该执行到这里
            print("错误：登录功能已关闭，但代码执行到了登录检查流程")
            auth_page.showMaximized()

    loading_page.loading_completed.connect(on_loading_completed)

    # 只有在启用登录功能时才连接认证成功信号
    if enable_login:

        def on_login_success(user):
            auth_page.close()
            # 显示主窗口（最大化模式）
            window.set_current_user(user)
            window.show_and_maximize()
            # 登录成功后启动调度服务
            window.restart_scheduler_service()

        auth_page.login_success.connect(on_login_success)

    # 开始加载过程
    loading_page.start_loading()

    return window, auth_page, loading_page


def start_auth_page(app, config):
    """启动认证页面（兼容旧版本）"""
    from src.ui.auth_page import AuthPage
    from src.core.services.token_service import TokenService

    # 创建认证页面
    auth_page = AuthPage()
    auth_page.showMaximized()

    # 创建主窗口实例（但不显示）
    window = MainWindow(config=config)

    # 设置应用程序图标
    app.setWindowIcon(window.create_icon())

    # 启动Token服务（每周清理任务）
    try:
        token_service = TokenService()
        token_service.start_weekly_cleanup()
        print("Token服务已启动，每周清理任务运行中")
    except Exception as e:
        print(f"启动Token服务失败: {e}")

    # 调度服务将在用户登录成功后启动
    # 这里只创建服务实例，但不启动
    try:
        scheduler_service = UnifiedSchedulerService()
        # 将调度服务实例传递给主窗口，但不启动
        window.set_scheduler_service(scheduler_service)
        print("调度服务实例已创建，将在用户登录后启动")
    except Exception as e:
        print(f"创建调度服务实例失败: {e}")

    # 连接认证成功信号
    def on_login_success(user):
        auth_page.close()
        # 显示主窗口（最大化模式）
        window.set_current_user(user)
        window.show_and_maximize()

    auth_page.login_success.connect(on_login_success)

    return window, auth_page


if __name__ == "__main__":
    app, config = initialize_application()
    # 使用新的启动流程：先显示loading_page，再显示认证页面
    window, auth_page, loading_page = start_loading_page(app, config)
    sys.exit(app.exec_())
