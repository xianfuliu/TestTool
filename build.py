import os
import subprocess
import sys
import json
import argparse
import datetime


def get_version():
    """获取版本号"""
    # 尝试从环境变量获取版本号（用于CI/CD）
    version = os.environ.get('APP_VERSION')
    if version:
        return version
    
    # 尝试从配置文件获取版本号
    config_file = "config/settings.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("app", {}).get("version", "1.0.0")
        except:
            pass
    
    # 默认版本号
    return "1.0.0"


def update_version_in_config(version):
    """在配置文件中更新版本号"""
    config_file = "config/settings.json"
    config_dir = "config"
    
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    
    default_config = {
        "features": {"interface_automation": False},
        "app": {"name": "测试工具管理", "version": version},
    }
    
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            # 更新版本号
            if "app" not in config:
                config["app"] = {}
            config["app"]["version"] = version
        except:
            config = default_config
    else:
        config = default_config
    
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def build_app():
    """构建应用程序"""
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='构建测试工具管理应用程序')
    parser.add_argument('--version', type=str, help='设置版本号')
    parser.add_argument('--increment', action='store_true', help='自动递增版本号')
    args = parser.parse_args()
    
    # 处理版本号
    version = get_version()
    
    if args.version:
        version = args.version
    elif args.increment:
        # 自动递增版本号
        parts = version.split('.')
        if len(parts) == 3:
            try:
                major, minor, patch = map(int, parts)
                patch += 1
                version = f"{major}.{minor}.{patch}"
            except:
                version = "1.0.1"
    
    # 更新配置文件中的版本号
    update_version_in_config(version)
    
    print(f"构建版本: v{version}")
    print(f"构建时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # PyInstaller 命令参数
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--icon=src/resources/icons/app_icon.ico",
        "--add-data=config;config",
        "--add-data=config/settings.json;config",  # 添加配置文件
        "--add-data=config/products_config.json;config",
        "--add-data=src/resources/icons;src/resources/icons",  # 添加所有图标文件
        "--add-data=src/resources/images;src/resources/images",  # 添加所有图片文件
        "--add-data=src/api;src/api",  # 添加API相关文件
        "--name",
        "TestTool",
        "main.py",
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
