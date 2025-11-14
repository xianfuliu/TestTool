#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试前置处理器UI功能
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from src.ui.interface_auto.components.interface_step_card import InterfaceStepCard

def test_pre_processing_ui():
    """测试前置处理器UI功能"""
    app = QApplication(sys.argv)
    
    # 创建主窗口
    main_window = QMainWindow()
    main_window.setWindowTitle("前置处理器UI测试")
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
    
    print("前置处理器UI测试启动成功！")
    print("请检查以下功能：")
    print("1. 前置处理器tab是否显示")
    print("2. 点击'+ 添加前置处理'按钮")
    print("3. 选择'HTTP请求'工具")
    print("4. 配置HTTP请求并保存")
    print("5. 检查已添加的工具是否显示在前置处理器tab中")
    print("6. 测试编辑和删除功能")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    test_pre_processing_ui()