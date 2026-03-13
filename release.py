#!/usr/bin/env python3
"""
发布脚本 - 用于自动构建和发布到GitHub Releases
"""

import os
import sys
import subprocess
import json
import argparse
import datetime


def run_command(cmd, cwd=None):
    """运行命令并返回输出"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"命令执行失败: {cmd}")
            print(f"错误输出: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"执行命令时出错: {e}")
        return False

def get_current_version():
    """获取当前版本号"""
    config_file = "config/settings.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("app", {}).get("version", "1.0.0")
        except:
            pass
    return "1.0.0"

def increment_version(version):
    """递增版本号"""
    parts = version.split('.')
    if len(parts) == 3:
        try:
            major, minor, patch = map(int, parts)
            patch += 1
            return f"{major}.{minor}.{patch}"
        except:
            pass
    return "1.0.1"

def create_release(version, release_notes=""):
    """创建GitHub Release"""
    # 构建应用程序
    print(f"正在构建版本 v{version}...")
    if not run_command(f"python build.py --version {version}"):
        print("构建失败")
        return False
    
    # 检查构建结果
    if not os.path.exists("dist/TestTool.exe"):
        print("构建失败：可执行文件未生成")
        return False
    
    # 创建Git标签
    tag_name = f"v{version}"
    print(f"创建Git标签: {tag_name}")
    
    if not run_command(f"git tag {tag_name}"):
        print("创建标签失败")
        return False
    
    # 推送标签到远程仓库
    print("推送标签到远程仓库...")
    if not run_command("git push origin --tags"):
        print("推送标签失败")
        return False
    
    print(f"\n✅ 发布完成!")
    print(f"版本: v{version}")
    print(f"标签: {tag_name}")
    print(f"可执行文件: dist/TestTool.exe")
    print(f"\nGitHub Actions将自动处理后续的构建和发布流程")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='发布脚本')
    parser.add_argument('--version', type=str, help='指定版本号')
    parser.add_argument('--increment', action='store_true', help='自动递增版本号')
    parser.add_argument('--notes', type=str, help='发布说明')
    
    args = parser.parse_args()
    
    # 获取当前版本
    current_version = get_current_version()
    
    # 确定新版本号
    if args.version:
        new_version = args.version
    elif args.increment:
        new_version = increment_version(current_version)
    else:
        # 如果没有指定版本号，询问用户
        print(f"当前版本: v{current_version}")
        choice = input("选择操作: [1]使用当前版本 [2]递增版本 [3]指定版本: ")
        
        if choice == "1":
            new_version = current_version
        elif choice == "2":
            new_version = increment_version(current_version)
        elif choice == "3":
            new_version = input("请输入新版本号 (格式: x.y.z): ")
        else:
            print("无效选择")
            return
    
    # 确认发布
    print(f"\n准备发布版本: v{new_version}")
    confirm = input("确认发布? (y/N): ")
    
    if confirm.lower() != 'y':
        print("发布取消")
        return
    
    # 获取发布说明
    release_notes = args.notes or input("请输入发布说明 (可选): ")
    
    # 执行发布
    if create_release(new_version, release_notes):
        print("\n📋 发布说明:")
        print("- 确保GitHub仓库已设置GitHub Actions")
        print("- 推送标签后，GitHub Actions会自动构建和发布")
        print("- 用户可以通过应用内的更新功能自动获取新版本")
    else:
        print("发布失败")


if __name__ == "__main__":
    main()