#!/usr/bin/env python3
"""
调试美化图标路径和加载问题
"""

import os
import sys

# 模拟tabbed_template_editor.py中的路径构建逻辑
def debug_icon_path():
    print("=== 调试美化图标路径 ===")
    
    # 模拟当前文件路径
    current_file_path = r"D:\workspace\TestTool\src\ui\interface_auto\components\tabbed_template_editor.py"
    print(f"当前文件路径: {current_file_path}")
    
    # 计算项目根目录 - 修正版本
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))))
    print(f"计算的项目根目录: {base_dir}")
    
    # 构建图标路径
    icon_path = os.path.join(base_dir, "src", "resources", "icons", "beauty.png")
    print(f"构建的图标路径: {icon_path}")
    
    # 检查路径是否存在
    print(f"图标文件是否存在: {os.path.exists(icon_path)}")
    
    # 检查路径的每一部分
    print("\n=== 路径分解检查 ===")
    parts = icon_path.split(os.sep)
    current_path = parts[0] + os.sep
    for part in parts[1:]:
        current_path = os.path.join(current_path, part)
        exists = os.path.exists(current_path)
        is_dir = os.path.isdir(current_path) if exists else False
        print(f"{current_path} - 存在: {exists}, 是目录: {is_dir}")
    
    # 检查图标文件详细信息
    if os.path.exists(icon_path):
        stat_info = os.stat(icon_path)
        print(f"\n图标文件大小: {stat_info.st_size} 字节")
        print(f"创建时间: {stat_info.st_ctime}")
        print(f"修改时间: {stat_info.st_mtime}")
    
    # 检查项目中的其他图标文件
    print("\n=== 检查icons目录内容 ===")
    icons_dir = os.path.join(base_dir, "src", "resources", "icons")
    if os.path.exists(icons_dir):
        files = os.listdir(icons_dir)
        png_files = [f for f in files if f.lower().endswith('.png')]
        print(f"icons目录中的PNG文件: {png_files}")
        if 'beauty.png' in files:
            print("✓ beauty.png 文件存在")
        else:
            print("✗ beauty.png 文件不存在")
    else:
        print("✗ icons目录不存在")

if __name__ == "__main__":
    debug_icon_path()