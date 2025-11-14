#!/usr/bin/env python3
"""
HTTP请求工具功能测试脚本
"""

import json
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.interface_utils.variable_manager import VariableManager
from src.utils.interface_utils.request_engine import RequestEngine


def extract_value(response_data, json_path):
    """从响应数据中提取值（简化实现）"""
    if not json_path:
        return response_data
    
    # 简化实现，只支持简单的点分隔路径
    keys = json_path.split('.')
    current = response_data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def extract_value_from_response(response, json_path):
    """从完整的响应对象中提取值"""
    if not json_path:
        return response
    
    # 支持从响应对象的不同层级提取数据
    if json_path == 'status_code':
        return response.get('status_code')
    elif json_path == 'url':
        return response.get('url')
    elif json_path == 'response_data':
        return response.get('response_data', {})
    
    # 对于其他路径，尝试从response_data中提取
    response_data = response.get('response_data', {})
    return extract_value(response_data, json_path)


def test_http_request_tool():
    """测试HTTP请求工具功能"""
    print("=== 测试HTTP请求工具功能 ===")
    
    # 创建VariableManager和RequestEngine实例
    variable_manager = VariableManager()
    request_engine = RequestEngine()
    
    # 设置全局变量
    variable_manager.set_global_variables({
        'base_url': 'https://httpbin.org'
    })
    
    # 创建HTTP请求工具配置
    http_tool_config = {
        'method': 'GET',
        'url': '${base_url}/get',
        'headers': {
            'Content-Type': 'application/json',
            'User-Agent': 'TestTool/1.0'
        },
        'body': {},
        'timeout': 30,
        'extractors': {
            'response_status': 'status_code',
            'response_url': 'url'
        }
    }
    
    # 模拟execute_http_request_tool方法的逻辑
    try:
        # 获取请求配置
        method = http_tool_config.get('method', 'GET')
        url = http_tool_config.get('url', '')
        headers = http_tool_config.get('headers', {})
        body = http_tool_config.get('body', {})
        timeout = http_tool_config.get('timeout', 30)
        extractors = http_tool_config.get('extractors', {})
        
        if not url:
            print("HTTP请求工具配置错误: URL不能为空")
            return
        
        # 替换变量
        all_variables = {}
        all_variables.update(variable_manager.global_variables)
        all_variables.update(variable_manager.local_variables)
        
        url = variable_manager.replace_variables(url, all_variables)
        headers = variable_manager.replace_variables_in_dict(headers, all_variables)
        body = variable_manager.replace_variables_in_dict(body, all_variables)
        
        print(f"前置处理器HTTP请求: {method} {url}")
        print(f"请求头: {headers}")
        
        # 执行请求
        request_data = {
            'method': method,
            'url': url,
            'headers': headers,
            'body': body,
            'timeout': timeout
        }
        
        print("正在执行HTTP请求...")
        response = request_engine.execute_request(request_data)
        
        if response.get('success'):
            # 请求成功，处理响应
            response_data = response.get('response_data', {})
            status_code = response.get('status_code', 0)
            
            print(f"前置处理器HTTP请求成功: 状态码 {status_code}")
            print(f"响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
            
            # 提取变量
            if extractors:
                extracted_vars = {}
                for var_name, json_path in extractors.items():
                    try:
                        # 从完整的响应对象中提取数据
                        value = extract_value_from_response(response, json_path)
                        if value is not None:
                            extracted_vars[var_name] = value
                            print(f"提取变量 {var_name}: {value}")
                        else:
                            print(f"无法提取变量 {var_name} (路径: {json_path})")
                    except Exception as e:
                        print(f"提取变量 {var_name} 时出错: {e}")
                
                # 将提取的变量保存到变量管理器
                if extracted_vars:
                    variable_manager.set_local_variables(extracted_vars)
                    print(f"已设置局部变量: {extracted_vars}")
            
            print("✅ HTTP请求工具执行成功")
        else:
            error_msg = response.get('error', '未知错误')
            print(f"HTTP请求失败: {error_msg}")
            
    except Exception as e:
        print(f"HTTP请求工具执行异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("=== HTTP请求工具测试完成 ===")


def test_variable_replacement():
    """测试变量替换功能"""
    print("\n=== 测试变量替换功能 ===")
    
    # 创建VariableManager实例
    variable_manager = VariableManager()
    
    # 设置全局变量
    variable_manager.set_global_variables({
        'base_url': 'https://httpbin.org',
        'api_key': 'test_api_key_123'
    })
    
    # 测试字符串变量替换
    test_url = '${base_url}/api/test'
    test_headers = {
        'Authorization': 'Bearer ${api_key}',
        'Content-Type': 'application/json'
    }
    
    print(f"原始URL: {test_url}")
    print(f"原始Headers: {test_headers}")
    
    # 替换变量
    replaced_url = variable_manager.replace_variables(test_url)
    replaced_headers = variable_manager.replace_variables_in_dict(test_headers)
    
    print(f"替换后URL: {replaced_url}")
    print(f"替换后Headers: {replaced_headers}")
    
    # 验证替换结果
    expected_url = 'https://httpbin.org/api/test'
    expected_headers = {
        'Authorization': 'Bearer test_api_key_123',
        'Content-Type': 'application/json'
    }
    
    assert replaced_url == expected_url, f"URL替换失败: 期望{expected_url}, 实际{replaced_url}"
    assert replaced_headers == expected_headers, f"Headers替换失败"
    
    print("✅ 变量替换测试通过")


if __name__ == '__main__':
    try:
        # 测试变量替换
        test_variable_replacement()
        
        # 测试HTTP请求工具
        test_http_request_tool()
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()