#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试美化图标路径构建和功能
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, src_dir)

def test_icon_path():
    """测试图标路径构建"""
    print("=== 测试美化图标路径构建 ===")
    
    # 模拟tabbed_template_editor.py中的路径构建逻辑
    # tabbed_template_editor.py位于: src/ui/interface_auto/components/tabbed_template_editor.py
    # 项目根目录应该是: ../../../../
    
    # 计算从tabbed_template_editor.py到项目根目录的路径
    tabbed_editor_path = os.path.join(project_root, "src", "ui", "interface_auto", "components", "tabbed_template_editor.py")
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(tabbed_editor_path)))))
    
    # 正确的路径构建应该是从项目根目录开始
    correct_base_dir = project_root  # 项目根目录
    icon_path = os.path.join(correct_base_dir, "src", "resources", "icons", "beauty.png")
    
    print(f"项目根目录: {project_root}")
    print(f"tabbed_template_editor.py路径: {tabbed_editor_path}")
    print(f"计算的基础目录: {base_dir}")
    print(f"正确的图标路径: {icon_path}")
    print(f"图标文件是否存在: {os.path.exists(icon_path)}")
    
    # 检查各级目录
    resources_dir = os.path.join(correct_base_dir, "src", "resources")
    icons_dir = os.path.join(resources_dir, "icons")
    
    print(f"resources目录是否存在: {os.path.exists(resources_dir)}")
    print(f"icons目录是否存在: {os.path.exists(icons_dir)}")
    
    # 列出icons目录下的所有文件
    if os.path.exists(icons_dir):
        print(f"icons目录内容: {os.listdir(icons_dir)}")
    
    return os.path.exists(icon_path)

def test_icon_loading():
    """测试图标加载"""
    print("\n=== 测试图标加载 ===")
    
    try:
        from PyQt5.QtGui import QIcon
        from PyQt5.QtCore import QSize
        
        # 使用正确的路径构建
        project_root = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(project_root, "src", "resources", "icons", "beauty.png")
        
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            print(f"图标加载成功: {icon_path}")
            print(f"图标是否为空: {icon.isNull()}")
            
            # 测试图标大小
            icon_size = QSize(16, 16)
            print(f"图标大小设置: {icon_size.width()}x{icon_size.height()}")
            
            return True
        else:
            print("图标文件不存在")
            return False
            
    except Exception as e:
        print(f"图标加载失败: {e}")
        return False

if __name__ == "__main__":
    print("开始测试美化图标功能...")
    
    # 测试路径构建
    path_ok = test_icon_path()
    
    # 测试图标加载
    loading_ok = test_icon_loading()
    
    print(f"\n=== 测试结果 ===")
    print(f"路径构建: {'✓ 成功' if path_ok else '✗ 失败'}")
    print(f"图标加载: {'✓ 成功' if loading_ok else '✗ 失败'}")
    
    if path_ok and loading_ok:
        print("美化图标功能测试通过！")
    else:
        print("美化图标功能测试失败！")