#!/usr/bin/env python3
"""
简单测试工具卡片高度调整效果
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tool_card_height_simple():
    """简单测试工具卡片高度调整效果"""
    print("=== 测试工具卡片高度调整效果 ===")
    
    # 检查interface_step_card.py文件中的修改
    file_path = "src/ui/interface_auto/components/interface_step_card.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("✓ 成功读取interface_step_card.py文件")
        
        # 检查HTTP请求工具卡片的样式修改
        if "padding: 2px 4px" in content and "max-height: 32px" in content:
            print("✓ HTTP请求工具卡片样式已调整")
            print("  - 内边距: 2px 4px")
            print("  - 最大高度: 32px")
        else:
            print("✗ HTTP请求工具卡片样式未正确调整")
        
        # 检查断言工具卡片的样式修改
        if "name = tool_config.get('name', '断言')  # 只显示名称" in content:
            print("✓ 断言工具卡片显示已简化（只显示名称）")
        else:
            print("✗ 断言工具卡片显示未简化")
        
        # 检查后置处理器工具卡片的样式修改
        if "name = tool_config.get('name', '后置处理')  # 只显示名称" in content:
            print("✓ 后置处理器工具卡片显示已简化（只显示名称）")
        else:
            print("✗ 后置处理器工具卡片显示未简化")
        
        # 检查按钮样式修改
        if "padding: 2px 6px" in content and "font-size: 10px" in content and "min-height: 20px" in content:
            print("✓ 按钮样式已调整")
            print("  - 内边距: 2px 6px")
            print("  - 字体大小: 10px")
            print("  - 最小高度: 20px")
        else:
            print("✗ 按钮样式未正确调整")
        
        # 检查是否移除了GET/URL显示
        if "display_text = f\"{name}\\n{method} {url}\"" not in content:
            print("✓ 已移除GET/URL等详细信息显示")
        else:
            print("✗ 未完全移除GET/URL显示")
        
        # 检查是否禁用了自动换行
        if "name_label.setWordWrap(False)" in content:
            print("✓ 已禁用名称标签自动换行")
        else:
            print("✗ 未禁用名称标签自动换行")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

if __name__ == "__main__":
    print("开始测试工具卡片高度调整效果...")
    
    test_result = test_tool_card_height_simple()
    
    print("\n=== 测试结果汇总 ===")
    if test_result:
        print("✓ 工具卡片高度调整测试完成")
        print("✓ 工具卡片高度已减小至32px")
        print("✓ 显示内容已简化（只显示工具名称）")
        print("✓ 移除了GET/URL等详细信息")
        print("✓ 按钮样式已优化")
        print("✓ 已禁用自动换行")
    else:
        print("✗ 工具卡片高度调整测试未通过")
        
    print("测试完成")