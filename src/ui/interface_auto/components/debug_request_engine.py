"""
接口模板调试请求引擎
专门用于接口模板的调试功能
"""

import json
import requests
import time
from typing import Dict, Any
from PyQt5.QtCore import QThread, pyqtSignal


class DebugRequestWorker(QThread):
    """调试请求工作线程"""
    
    finished = pyqtSignal(dict)  # 调试完成信号
    error = pyqtSignal(str)      # 错误信号
    
    def __init__(self, request_data: Dict[str, Any]):
        super().__init__()
        self.request_data = request_data
    
    def run(self):
        """执行调试请求"""
        try:
            start_time = time.time()
            
            # 准备请求参数
            method = self.request_data.get('method', 'GET').upper()
            url = self.request_data.get('url_path', '')
            headers = self.request_data.get('headers', {})
            params = self.request_data.get('params', {})
            body = self.request_data.get('body', {})
            timeout = self.request_data.get('timeout', 30)
            
            # 验证必填参数
            if not url:
                self.error.emit("URL不能为空")
                return
            
            # 设置默认请求头
            if not headers.get('Content-Type') and method in ['POST', 'PUT', 'PATCH']:
                headers['Content-Type'] = 'application/json'
            
            # 执行请求
            session = requests.Session()
            
            if method == 'GET':
                response = session.get(
                    url=url,
                    params=params,
                    headers=headers,
                    timeout=timeout
                )
            elif method == 'POST':
                response = session.post(
                    url=url,
                    params=params,
                    json=body,
                    headers=headers,
                    timeout=timeout
                )
            elif method == 'PUT':
                response = session.put(
                    url=url,
                    params=params,
                    json=body,
                    headers=headers,
                    timeout=timeout
                )
            elif method == 'DELETE':
                response = session.delete(
                    url=url,
                    params=params,
                    headers=headers,
                    timeout=timeout
                )
            else:
                self.error.emit(f"不支持的HTTP方法: {method}")
                return
            
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 解析响应
            response_body = ""
            try:
                if response.text:
                    # 尝试解析JSON
                    response_body = response.json()
                else:
                    response_body = {}
            except:
                # 如果不是JSON，使用文本
                response_body = response.text
            
            # 构建调试结果
            debug_result = {
                'success': True,
                'status_code': response.status_code,
                'response_time': response_time,
                'headers': dict(response.headers),
                'body': response_body,
                'text': response.text,
                'elapsed': response.elapsed.total_seconds()
            }
            
            self.finished.emit(debug_result)
            
        except requests.exceptions.Timeout:
            self.error.emit(f"请求超时 (timeout={self.request_data.get('timeout', 30)}秒)")
        except requests.exceptions.ConnectionError:
            self.error.emit("网络连接错误，请检查URL是否正确")
        except requests.exceptions.RequestException as e:
            self.error.emit(f"请求异常: {str(e)}")
        except Exception as e:
            self.error.emit(f"调试请求失败: {str(e)}")


class DebugRequestEngine:
    """调试请求引擎"""
    
    def __init__(self):
        self.worker = None
    
    def execute_debug_request(self, request_data: Dict[str, Any], 
                             finished_callback=None, error_callback=None):
        """执行调试请求"""
        # 停止之前的worker
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        
        # 创建新的worker
        self.worker = DebugRequestWorker(request_data)
        
        if finished_callback:
            self.worker.finished.connect(finished_callback)
        
        if error_callback:
            self.worker.error.connect(error_callback)
        
        # 启动worker
        self.worker.start()
    
    def stop_debug_request(self):
        """停止调试请求"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
    
    def is_running(self):
        """检查是否正在运行"""
        return self.worker and self.worker.isRunning()


def create_debug_request_data(template_data: Dict[str, Any]) -> Dict[str, Any]:
    """从模板数据创建调试请求数据"""
    return {
        'method': template_data.get('method', 'GET'),
        'url_path': template_data.get('url_path', ''),
        'headers': template_data.get('headers', {}),
        'params': template_data.get('params', {}),
        'body': template_data.get('body', {}),
        'timeout': template_data.get('timeout', 30),
        'retry_enabled': template_data.get('retry_enabled', False),
        'retry_count': template_data.get('retry_count', 3)
    }