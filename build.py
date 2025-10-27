import os
import subprocess
import sys
import json


def build_app():
    """构建应用程序"""

    # 确保配置文件存在
    config_dir = "config"
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # 创建默认配置文件
    default_config = {
        "features": {
            "interface_automation": False
        },
        "app": {
            "name": "测试工具",
            "version": "1.0.0"
        }
    }

    config_file = os.path.join(config_dir, "settings.json")
    if not os.path.exists(config_file):
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)

    # PyInstaller 命令参数
    pyinstaller_cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--icon=src/resources/icons/app_icon.ico',
        '--add-data=config;config',
        '--add-data=config/settings.json;config',  # 添加配置文件
        '--add-data=config/products_config.json;config',
        '--add-data=src/resources/icons/loading.svg;src/resources/icons',
        '--add-data=src/resources/images/id_card_template.png;src/resources/images',
        '--add-data=src/resources/images/ocr_face_1.png;src/resources/images',
        '--add-data=src/resources/images/ocr_face_2.png;src/resources/images',
        '--add-data=src/resources/icons/copy_icon.png;src/resources/icons',
        '--add-data=src/resources/icons/download_icon.png;src/resources/icons',
        '--add-data=src/resources/icons/app_icon.ico;src/resources/icons',
        '--name', 'TestTool',
        'main.py'
    ]

    try:
        print("开始构建应用程序...")
        subprocess.run(pyinstaller_cmd, check=True)
        print("构建完成！")
        print("可执行文件位置: dist/TestTool.exe")
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build_app()