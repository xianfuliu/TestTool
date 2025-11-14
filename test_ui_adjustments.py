#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试UI调整效果：
1. HTTP工具条icon替换
2. 工具容器高度增加但保持工具条置顶
3. 步骤容器高度固定
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_icon_replacement():
    """测试HTTP工具条icon替换"""
    print("=== 测试HTTP工具条icon替换 ===")
    
    # 检查图标文件是否存在
    icon_path = os.path.join("src", "resources", "icons", "http.png")
    if os.path.exists(icon_path):
        print("✓ http.png图标文件存在")
    else:
        print("✗ http.png图标文件不存在")
        return False
    
    # 检查interface_step_card.py中的修改
    card_file = os.path.join("src", "ui", "interface_auto", "components", "interface_step_card.py")
    if os.path.exists(card_file):
        with open(card_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查是否添加了os和QPixmap导入
        if 'import os' in content and 'QPixmap' in content:
            print("✓ 已添加必要的导入语句")
        else:
            print("✗ 缺少必要的导入语句")
            return False
            
        # 检查HTTP工具图标替换代码
        if 'http_icon_path = os.path.join("src", "resources", "icons", "http.png")' in content:
            print("✓ HTTP工具图标替换代码已添加")
        else:
            print("✗ HTTP工具图标替换代码未找到")
            return False
    else:
        print("✗ interface_step_card.py文件不存在")
        return False
    
    return True

def test_container_height():
    """测试工具容器高度调整"""
    print("\n=== 测试工具容器高度调整 ===")
    
    card_file = os.path.join("src", "ui", "interface_auto", "components", "interface_step_card.py")
    if os.path.exists(card_file):
        with open(card_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查前置Tab滚动区域高度
        if 'scroll_area.setFixedHeight(120)  # 增加高度，让工具容器有更多空间，但工具条仍置顶' in content:
            print("✓ 前置Tab滚动区域高度已调整为120px")
        else:
            print("✗ 前置Tab滚动区域高度未正确调整")
            return False
            
        # 检查断言Tab滚动区域高度
        if content.count('scroll_area.setFixedHeight(120)') >= 3:
            print("✓ 所有Tab滚动区域高度已统一调整为120px")
        else:
            print("✗ 部分Tab滚动区域高度未正确调整")
            return False
            
    else:
        print("✗ interface_step_card.py文件不存在")
        return False
        
    return True

def test_step_container_height():
    """测试步骤容器高度固定"""
    print("\n=== 测试步骤容器高度固定 ===")
    
    card_file = os.path.join("src", "ui", "interface_auto", "components", "interface_step_card.py")
    if os.path.exists(card_file):
        with open(card_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查步骤容器高度设置
        if 'self.setMinimumHeight(300)  # 最小高度' in content and 'self.setMaximumHeight(400)  # 最大高度' in content:
            print("✓ 步骤容器已设置固定高度（最小300px，最大400px）")
        else:
            print("✗ 步骤容器高度未正确固定")
            return False
            
    else:
        print("✗ interface_step_card.py文件不存在")
        return False
        
    return True

def main():
    """主测试函数"""
    print("开始UI调整测试...\n")
    
    tests = [
        ("HTTP工具条icon替换", test_icon_replacement),
        ("工具容器高度调整", test_container_height),
        ("步骤容器高度固定", test_step_container_height)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name}测试通过\n")
            else:
                print(f"✗ {test_name}测试失败\n")
        except Exception as e:
            print(f"✗ {test_name}测试出错: {e}\n")
    
    print(f"测试完成: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有UI调整已成功实现！")
        return True
    else:
        print("⚠️ 部分UI调整存在问题，请检查代码")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)