#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化测试前置处理器UI功能
"""

import sys
import os
import time

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer
from src.ui.interface_auto.components.interface_step_card import InterfaceStepCard

def test_pre_processing_auto():
    """自动化测试前置处理器UI功能"""
    app = QApplication(sys.argv)
    
    # 创建主窗口
    main_window = QMainWindow()
    main_window.setWindowTitle("前置处理器UI自动化测试")
    main_window.resize(800, 600)
    
    # 创建中央部件
    central_widget = QWidget()
    main_window.setCentralWidget(central_widget)
    
    layout = QVBoxLayout(central_widget)
    
    # 创建测试步骤数据
    step_data = {
        'id': 1,
        'order': 1,
        'enabled': True,
        'api_name': '测试接口',
        'api_template': {
            'id': 'test_api',
            'name': '测试接口',
            'method': 'GET',
            'url': '/api/test'
        },
        'pre_processing': {}
    }
    
    # 创建步骤卡片
    step_card = InterfaceStepCard(step_data)
    layout.addWidget(step_card)
    
    # 显示窗口
    main_window.show()
    
    print("前置处理器UI自动化测试启动成功！")
    print("测试步骤：")
    
    # 使用定时器模拟用户操作
    def simulate_user_actions():
        print("1. 检查前置处理器tab是否显示...")
        
        # 检查前置tab是否存在
        if hasattr(step_card, 'pre_tab') and step_card.pre_tab:
            print("✓ 前置处理器tab存在")
        else:
            print("✗ 前置处理器tab不存在")
            return
        
        # 检查工具容器是否存在
        if hasattr(step_card, 'pre_tools_container') and step_card.pre_tools_container:
            print("✓ 前置处理器工具容器存在")
        else:
            print("✗ 前置处理器工具容器不存在")
            return
        
        # 检查添加按钮是否存在
        if hasattr(step_card, 'add_pre_button') and step_card.add_pre_button:
            print("✓ 添加前置处理按钮存在")
        else:
            print("✗ 添加前置处理按钮不存在")
            return
        
        # 检查步骤数据中前置处理器配置
        if 'pre_processing' in step_card.step_data:
            print("✓ 步骤数据中包含pre_processing配置")
        else:
            print("✗ 步骤数据中不包含pre_processing配置")
            return
        
        print("2. 模拟添加HTTP请求工具...")
        
        # 模拟添加HTTP请求工具
        try:
            # 创建测试配置数据
            test_config = {
                'type': 'http_request',
                'method': 'GET',
                'url': 'https://api.example.com/test',
                'timeout': 30,
                'headers': {},
                'body': '',
                'variables': {}
            }
            
            # 模拟保存HTTP请求配置
            step_card.on_http_request_saved(test_config)
            
            print("✓ HTTP请求工具配置保存成功")
            
            # 检查工具是否添加到步骤数据
            # 工具ID由on_http_request_saved方法自动生成
            pre_processing = step_card.step_data['pre_processing']
            if pre_processing:
                # 获取第一个工具ID
                tool_id = list(pre_processing.keys())[0]
                print(f"✓ HTTP请求工具已添加到步骤数据，工具ID: {tool_id}")
            else:
                print("✗ HTTP请求工具未添加到步骤数据")
                return
            
            # 检查工具显示是否更新
            if hasattr(step_card, 'pre_tools_container') and step_card.pre_tools_container:
                # 检查容器中是否有子部件
                if step_card.pre_tools_container.layout() and step_card.pre_tools_container.layout().count() > 0:
                    print("✓ 前置处理器工具容器中有工具显示")
                else:
                    print("✗ 前置处理器工具容器中没有工具显示")
                    return
            
            print("3. 模拟编辑HTTP请求工具...")
            
            # 模拟编辑工具
            updated_config = test_config.copy()
            updated_config['url'] = 'https://api.example.com/updated'
            
            step_card.on_http_request_edited(tool_id, updated_config)
            
            # 检查配置是否更新
            if step_card.step_data['pre_processing'][tool_id]['config']['url'] == 'https://api.example.com/updated':
                print("✓ HTTP请求工具配置更新成功")
            else:
                print("✗ HTTP请求工具配置更新失败")
                return
            
            print("4. 模拟删除HTTP请求工具...")
            
            # 模拟删除工具
            step_card.delete_pre_tool(tool_id)
            
            # 检查工具是否从步骤数据中删除
            if tool_id not in step_card.step_data['pre_processing']:
                print("✓ HTTP请求工具删除成功")
            else:
                print("✗ HTTP请求工具删除失败")
                return
            
            print("\n🎉 所有测试通过！前置处理器中HTTP请求工具的显示和编辑功能正常工作！")
            
        except Exception as e:
            print(f"✗ 测试过程中出现错误: {str(e)}")
        
        # 关闭应用
        QTimer.singleShot(1000, app.quit)
    
    # 延迟执行测试
    QTimer.singleShot(1000, simulate_user_actions)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    test_pre_processing_auto()