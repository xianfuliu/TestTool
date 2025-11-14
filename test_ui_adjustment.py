#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试前置处理区域UI调整效果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ui_adjustments():
    """测试UI调整效果"""
    print("=== 前置处理区域UI调整测试 ===")
    
    # 检查interface_step_card.py文件中的修改
    file_path = "src/ui/interface_auto/components/interface_step_card.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("\n1. 检查滚动区域高度调整:")
        if "scroll_area.setFixedHeight(80)" in content:
            print("   ✓ 滚动区域高度已调整为80px")
        else:
            print("   ✗ 滚动区域高度未正确调整")
        
        print("\n2. 检查Tab标题样式:")
        if "QTabBar::tab {" in content and "border: none;" in content:
            print("   ✓ Tab标题已设置为无边框")
        else:
            print("   ✗ Tab标题边框设置有问题")
        
        if "background-color: transparent;" in content:
            print("   ✓ Tab标题背景已设置为透明")
        else:
            print("   ✗ Tab标题背景未透明")
        
        if "QTabBar::tab:selected {" in content and "border-bottom: 2px solid #1976d2;" in content:
            print("   ✓ 选中状态仅显示底部蓝色下划线")
        else:
            print("   ✗ 选中状态样式有问题")
        
        print("\n3. 检查所有Tab的一致性:")
        tabs = ["前置", "断言", "后置"]
        for tab in tabs:
            if f"scroll_area.setFixedHeight(80)" in content and f"{tab}Tab" in content:
                print(f"   ✓ {tab}Tab滚动区域高度一致")
            else:
                print(f"   ✗ {tab}Tab滚动区域高度不一致")
        
        print("\n4. 检查TabBar整体样式:")
        if "QTabBar {" in content and "border: none;" in content:
            print("   ✓ TabBar整体无边框")
        else:
            print("   ✗ TabBar边框设置有问题")
        
        print("\n=== UI调整测试完成 ===")
        
    except FileNotFoundError:
        print(f"错误: 文件 {file_path} 未找到")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    test_ui_adjustments()