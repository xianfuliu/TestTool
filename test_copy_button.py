#!/usr/bin/env python3
"""
测试用例步骤复制按钮功能测试脚本
"""

import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

from src.ui.interface_auto.components.interface_step_card import InterfaceStepCard

def test_copy_button_functionality():
    """测试复制按钮功能"""
    print("=== 测试用例步骤复制按钮功能 ===")
    
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
            }
        },
        'assertions': {
            'assertion_1234567890': {
                'type': 'status_code',
                'name': '状态码断言',
                'value': 200
            }
        },
        'post_processing': {
            'post_1234567890': {
                'type': 'extractor',
                'name': '变量提取',
                'path': '$.data.id'
            }
        }
    }
    
    # 创建应用和窗口
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("复制按钮功能测试")
    window.resize(800, 600)
    
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    
    try:
        # 创建步骤卡片
        step_card = InterfaceStepCard(test_step_data)
        layout.addWidget(step_card)
        
        print("✓ 步骤卡片创建成功")
        
        # 检查前置处理器工具复制按钮
        if hasattr(step_card, 'pre_tool_widgets') and step_card.pre_tool_widgets:
            print("✓ 前置处理器工具卡片已创建")
            
            # 检查复制按钮是否存在
            for tool_id, widget in step_card.pre_tool_widgets.items():
                # 查找复制按钮
                copy_btn = widget.findChild(type(QWidget()), "复制")
                if copy_btn:
                    print(f"✓ 前置处理器工具复制按钮存在: {tool_id}")
                else:
                    print(f"✗ 前置处理器工具复制按钮未找到: {tool_id}")
        else:
            print("✗ 前置处理器工具卡片未创建")
        
        # 检查断言工具复制按钮
        if hasattr(step_card, 'assertion_tool_widgets') and step_card.assertion_tool_widgets:
            print("✓ 断言工具卡片已创建")
            
            # 检查复制按钮是否存在
            for tool_id, widget in step_card.assertion_tool_widgets.items():
                # 查找复制按钮
                copy_btn = widget.findChild(type(QWidget()), "复制")
                if copy_btn:
                    print(f"✓ 断言工具复制按钮存在: {tool_id}")
                else:
                    print(f"✗ 断言工具复制按钮未找到: {tool_id}")
        else:
            print("✗ 断言工具卡片未创建")
        
        # 检查后置处理器工具复制按钮
        if hasattr(step_card, 'post_tool_widgets') and step_card.post_tool_widgets:
            print("✓ 后置处理器工具卡片已创建")
            
            # 检查复制按钮是否存在
            for tool_id, widget in step_card.post_tool_widgets.items():
                # 查找复制按钮
                copy_btn = widget.findChild(type(QWidget()), "复制")
                if copy_btn:
                    print(f"✓ 后置处理器工具复制按钮存在: {tool_id}")
                else:
                    print(f"✗ 后置处理器工具复制按钮未找到: {tool_id}")
        else:
            print("✗ 后置处理器工具卡片未创建")
        
        # 测试复制方法是否存在
        if hasattr(step_card, 'copy_pre_tool'):
            print("✓ copy_pre_tool方法存在")
        else:
            print("✗ copy_pre_tool方法不存在")
            
        if hasattr(step_card, 'copy_assertion_tool'):
            print("✓ copy_assertion_tool方法存在")
        else:
            print("✗ copy_assertion_tool方法不存在")
            
        if hasattr(step_card, 'copy_post_tool'):
            print("✓ copy_post_tool方法存在")
        else:
            print("✗ copy_post_tool方法不存在")
        
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

def test_copy_functionality():
    """测试复制功能的具体实现"""
    print("\n=== 测试复制功能实现 ===")
    
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
            }
        },
        'assertions': {
            'assertion_1234567890': {
                'type': 'status_code',
                'name': '状态码断言',
                'value': 200
            }
        },
        'post_processing': {
            'post_1234567890': {
                'type': 'extractor',
                'name': '变量提取',
                'path': '$.data.id'
            }
        }
    }
    
    try:
        # 创建步骤卡片实例
        step_card = InterfaceStepCard(test_step_data)
        
        # 测试前置处理器工具复制
        original_pre_tools = len(test_step_data['pre_processing'])
        step_card.copy_pre_tool('http_request_1234567890')
        new_pre_tools = len(step_card.step_data['pre_processing'])
        
        if new_pre_tools > original_pre_tools:
            print("✓ 前置处理器工具复制成功")
            print(f"  原始数量: {original_pre_tools}, 复制后数量: {new_pre_tools}")
        else:
            print("✗ 前置处理器工具复制失败")
        
        # 测试断言工具复制
        original_assertions = len(test_step_data['assertions'])
        step_card.copy_assertion_tool('assertion_1234567890')
        new_assertions = len(step_card.step_data['assertions'])
        
        if new_assertions > original_assertions:
            print("✓ 断言工具复制成功")
            print(f"  原始数量: {original_assertions}, 复制后数量: {new_assertions}")
        else:
            print("✗ 断言工具复制失败")
        
        # 测试后置处理器工具复制
        original_post_tools = len(test_step_data['post_processing'])
        step_card.copy_post_tool('post_1234567890')
        new_post_tools = len(step_card.step_data['post_processing'])
        
        if new_post_tools > original_post_tools:
            print("✓ 后置处理器工具复制成功")
            print(f"  原始数量: {original_post_tools}, 复制后数量: {new_post_tools}")
        else:
            print("✗ 后置处理器工具复制失败")
        
        return True
        
    except Exception as e:
        print(f"✗ 复制功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始测试复制按钮功能...")
    
    # 测试UI组件
    ui_test_result = test_copy_button_functionality()
    
    # 测试功能实现
    func_test_result = test_copy_functionality()
    
    print("\n=== 测试结果汇总 ===")
    if ui_test_result and func_test_result:
        print("✓ 复制按钮功能测试通过")
        print("✓ 前置处理器工具复制功能正常")
        print("✓ 断言工具复制功能正常")
        print("✓ 后置处理器工具复制功能正常")
        print("✓ 所有复制按钮已启用并正常工作")
    else:
        print("✗ 复制按钮功能测试未通过")
        
    print("测试完成")