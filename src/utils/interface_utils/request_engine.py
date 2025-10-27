import requests
import json
from typing import Dict, Any
from src.utils.interface_utils.variable_manager import VariableManager


class RequestEngine:
    def __init__(self):
        self.session = requests.Session()
        self.variable_manager = VariableManager()

    def execute_request(self, api_data: Dict[str, Any], variables: Dict[str, Any] = None):
        """执行HTTP请求"""
        try:
            # 替换变量
            url = self.variable_manager.replace_variables(api_data['url'], variables)
            headers = self.variable_manager.replace_variables_in_dict(
                api_data.get('headers', {}), variables
            )
            params = self.variable_manager.replace_variables_in_dict(
                api_data.get('params', {}), variables
            )
            body = self.variable_manager.replace_variables_in_dict(
                api_data.get('body', {}), variables
            )

            method = api_data['method'].upper()

            # 执行请求
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=body if method in ['POST', 'PUT', 'PATCH'] else None,
                timeout=30
            )

            return {
                'success': True,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': response.json() if response.text else {},
                'text': response.text,
                'elapsed': response.elapsed.total_seconds()
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }