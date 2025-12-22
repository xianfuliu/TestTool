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
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))


def load_config():
    """加载配置文件"""
    config_path = resource_path("config/settings.json")
    default_config = {
        "features": {
            "interface_automation": False
        },
        "app": {
            "name": "测试工具",
            "version": "1.0.0"
        }
    }

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 如果配置文件不存在，创建默认配置
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            return default_config
    except Exception as e:
        logging.error(f"加载配置文件失败: {e}")
        return default_config


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def initialize_application():
    """初始化应用程序"""
    # 在应用程序启动前设置
    sys.excepthook = excepthook

    # 加载配置
    config = load_config()
    enable_interface_auto = config.get("features", {}).get("interface_automation", False)
    enable_tool_cards = config.get("features", {}).get("tool_cards", False)

    app = QApplication(sys.argv)

    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # 检查必要的资源文件
    required_files = [
        "src/resources/images/id_card_template.png",
        "src/resources/images/ocr_face_1.png",
        "src/resources/images/ocr_face_2.png"
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
    """启动加载页面"""
    # 创建主窗口实例（但不显示）
    window = MainWindow(config=config)
    
    # 设置应用程序图标
    app.setWindowIcon(window.create_icon())
    
    # 创建加载页面
    loading_page = LoadingPage(window)
    loading_page.show()
    
    # 启动调度后台服务（使用分布式锁确保单实例运行）
    try:
        scheduler_service = UnifiedSchedulerService()
        
        # 直接调用start_service()，它内部会处理分布式锁检查
        if scheduler_service.start_service():
            # 成功启动服务，启动服务主循环（在新线程中）
            import threading
            service_thread = threading.Thread(target=scheduler_service.run_service_loop, daemon=True)
            service_thread.start()
            
            print("统一调度服务已启动（当前实例持有调度锁）")
            
            # 将调度服务实例传递给主窗口
            window.set_scheduler_service(scheduler_service)
        else:
            # 无法启动服务，说明已有其他实例在运行
            print("警告：检测到已有调度服务实例在运行，当前实例将作为只读客户端运行")
            print("调度任务将由已运行的实例统一执行，避免重复执行")
            
            # 创建只读的调度服务实例（不启动调度循环）
            scheduler_service.running = False
            window.set_scheduler_service(scheduler_service)
            
    except Exception as e:
        print(f"启动统一调度服务失败: {e}")
    
    # 连接加载完成信号
    def on_loading_completed():
        loading_page.close()
        # 显示主窗口（最大化模式）
        window.show_and_maximize()
    
    loading_page.loading_completed.connect(on_loading_completed)
    
    # 开始加载
    loading_page.start_loading()
    
    return window


if __name__ == "__main__":
    app, config = initialize_application()
    window = start_loading_page(app, config)
    sys.exit(app.exec_())