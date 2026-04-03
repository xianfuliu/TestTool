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
    
    print(f"Build version: v{version}")
    print(f"Build time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # PyInstaller 命令参数 - 修复云端DLL加载问题
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
        # 修复云端DLL加载的关键参数
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui", 
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=PyQt5",
        "--hidden-import=src",
        "--hidden-import=src.api",
        "--hidden-import=src.core",
        "--hidden-import=src.ui",
        "--hidden-import=src.utils",
        "--collect-all=PyQt5",
        "--collect-all=src",
        # 云端构建专用参数
        "--paths=.",
        "--paths=src",
        "--clean",  # 清理之前的构建缓存
        "--name",
        "TestTool",
        "main.py",
    ]

    try:
        print("Starting application build...")
        print("This may take several minutes depending on your system...")
        # 使用Popen来实时显示输出，避免进程挂起
        process = subprocess.Popen(pyinstaller_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # 实时输出PyInstaller的进度
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        # 检查返回码
        return_code = process.poll()
        if return_code != 0:
            print(f"Build failed with return code: {return_code}")
            sys.exit(1)
            
        print("Build completed!")
        print("Executable file location: dist/TestTool.exe")
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Build error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build_app()
