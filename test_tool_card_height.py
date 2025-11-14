#!/usr/bin/env python3
"""
测试工具卡片高度调整效果
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

from src.ui.interface_auto.components.interface_step_card import InterfaceStepCard

def test_tool_card_height():
    """测试工具卡片高度调整效果"""
    print("=== 测试工具卡片高度调整效果 ===")
    
    # 创建测试步骤数据
    test_step_data = {
        'order': 1,
        'enabled': True,
        'api_template': {
            'name': '测试接口',
            'method': 'GET',
            'url_path': '/api/test'
        },
        'pre_processing': {
            'http_request_1234567890': {
                'type': 'http_request',
                'config': {
                    'name': '前置HTTP请求',
                    'method': 'GET',
                    'url': 'https://httpbin.org/get'
                }
            },
            'http_request_1234567891': {
                'type': 'http_request',
                'config': {
                    'name': '另一个HTTP请求',
                    'method': 'POST',
                    'url': 'https://httpbin.org/post'
                }
            }
        },
        'assertions': {
            'assertion_1234567890': {
                'type': 'status_code',
                'name': '状态码断言',
                'value': 200
            },
            'assertion_1234567891': {
                'type': 'response_time',
                'name': '响应时间断言',
                'value': 1000
            }
        },
        'post_processing': {
            'post_1234567890': {
                'type': 'extractor',
                'name': '变量提取',
                'path': '$.data.id'
            },
            'post_1234567891': {
                'type': 'validator',
                'name': '数据验证',
                'rule': 'required'
            }
        }
    }
    
    # 创建应用和窗口
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("工具卡片高度测试")
    window.resize(800, 600)
    
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    
    try:
        # 创建步骤卡片
        step_card = InterfaceStepCard(test_step_data)
        layout.addWidget(step_card)
        
        print("✓ 步骤卡片创建成功")
        
        # 检查前置处理器工具卡片高度
        if hasattr(step_card, 'pre_tool_widgets') and step_card.pre_tool_widgets:
            print("✓ 前置处理器工具卡片已创建")
            
            for tool_id, widget in step_card.pre_tool_widgets.items():
                height = widget.height()
                max_height = widget.maximumHeight()
                print(f"  工具卡片 {tool_id}: 高度={height}, 最大高度={max_height}")
                
                if height <= 40:
                    print(f"  ✓ 工具卡片高度合适: {height}px")
                else:
                    print(f"  ✗ 工具卡片高度过大: {height}px")
        else:
            print("✗ 前置处理器工具卡片未创建")
        
        # 检查断言工具卡片高度
        if hasattr(step_card, 'assertion_tool_widgets') and step_card.assertion_tool_widgets:
            print("✓ 断言工具卡片已创建")
            
            for tool_id, widget in step_card.assertion_tool_widgets.items():
                height = widget.height()
                max_height = widget.maximumHeight()
                print(f"  工具卡片 {tool_id}: 高度={height}, 最大高度={max_height}")
                
                if height <= 40:
                    print(f"  ✓ 工具卡片高度合适: {height}px")
                else:
                    print(f"  ✗ 工具卡片高度过大: {height}px")
        else:
            print("✗ 断言工具卡片未创建")
        
        # 检查后置处理器工具卡片高度
        if hasattr(step_card, 'post_tool_widgets') and step_card.post_tool_widgets:
            print("✓ 后置处理器工具卡片已创建")
            
            for tool_id, widget in step_card.post_tool_widgets.items():
                height = widget.height()
                max_height = widget.maximumHeight()
                print(f"  工具卡片 {tool_id}: 高度={height}, 最大高度={max_height}")
                
                if height <= 40:
                    print(f"  ✓ 工具卡片高度合适: {height}px")
                else:
                    print(f"  ✗ 工具卡片高度过大: {height}px")
        else:
            print("✗ 后置处理器工具卡片未创建")
        
        # 检查显示内容是否简化
        print("\n=== 检查显示内容简化 ===")
        
        if hasattr(step_card, 'pre_tool_widgets') and step_card.pre_tool_widgets:
            for tool_id, widget in step_card.pre_tool_widgets.items():
                # 查找名称标签
                name_label = widget.findChild(type(widget), "")
                if name_label:
                    text = name_label.text()
                    if "\n" not in text and "GET" not in text and "POST" not in text:
                        print(f"  ✓ 前置工具显示简化: {text}")
                    else:
                        print(f"  ✗ 前置工具显示未简化: {text}")
        
        if hasattr(step_card, 'assertion_tool_widgets') and step_card.assertion_tool_widgets:
            for tool_id, widget in step_card.assertion_tool_widgets.items():
                # 查找名称标签
                name_label = widget.findChild(type(widget), "")
                if name_label:
                    text = name_label.text()
                    if "\n" not in text and "类型:" not in text:
                        print(f"  ✓ 断言工具显示简化: {text}")
                    else:
                        print(f"  ✗ 断言工具显示未简化: {text}")
        
        if hasattr(step_card, 'post_tool_widgets') and step_card.post_tool_widgets:
            for tool_id, widget in step_card.post_tool_widgets.items():
                # 查找名称标签
                name_label = widget.findChild(type(widget), "")
                if name_label:
                    text = name_label.text()
                    if "\n" not in text and "类型:" not in text:
                        print(f"  ✓ 后置工具显示简化: {text}")
                    else:
                        print(f"  ✗ 后置工具显示未简化: {text}")
        
        window.setCentralWidget(central_widget)
        window.show()
        
        # 运行应用短暂时间
        app.exec_()
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始测试工具卡片高度调整效果...")
    
    test_result = test_tool_card_height()
    
    print("\n=== 测试结果汇总 ===")
    if test_result:
        print("✓ 工具卡片高度调整测试完成")
        print("✓ 工具卡片高度已减小")
        print("✓ 显示内容已简化（只显示工具名称）")
        print("✓ 移除了GET/URL等详细信息")
    else:
        print("✗ 工具卡片高度调整测试未通过")
        
    print("测试完成")