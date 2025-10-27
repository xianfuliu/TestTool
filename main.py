import logging
import sys
import os
import json
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from src.ui.main_window import MainWindow
from src.utils.resource_utils import resource_path
from src.utils.except_hook import excepthook

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


if __name__ == "__main__":
    # 在应用程序启动前设置
    sys.excepthook = excepthook

    # 加载配置
    config = load_config()
    enable_interface_auto = config.get("features", {}).get("interface_automation", False)

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

    # 创建主窗口实例
    window = MainWindow(config=config)

    # 设置应用程序图标（使用已经创建的主窗口实例）
    app.setWindowIcon(window.create_icon())

    # 显示窗口
    window.show()
    sys.exit(app.exec_())