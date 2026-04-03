"""
小微系统登录工具类
"""

import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MicroLogin:
    """小微系统登录工具类"""    
    def __init__(self):
        self.base_url = "http://47.106.192.83/stage-sysmng-api"
        self.login_params = {
            "orgCode": "10000",
            "userName": "test20000",
            "password": "pmJAuxqJXB0g2J8N3NSeCQ==",
            "smsCode": "123123"
        }

    def _build_headers(self, token: str = None) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        if token:
            headers["Cookie"] = f"XXL_JOB_LOGIN_IDENTITY=7b226964223a312c22757365726e616d65223a2261646d696e222c2270617373776f7264223a226531306164633339343962613539616262653536653035376632306638383365222c22726f6c65223a312c227065726d697373696f6e223a6e756c6b7d; sidebarStatus=1; Luna-Token={token}; Luna-UserCn=%E6%B5%8B%E8%AF%9520000; Luna-Org=10000; Luna-User=test20000"
            headers["x-authorization"] = token
        
        return headers

    def login(self) -> str:
        """登录小微系统并获取token"""
        try:
            url = f"{self.base_url}/auth/login"
            
            logger.info(f"小微系统登录请求: {url} with params: {self.login_params}")
            
            response = requests.post(url, params=self.login_params, headers=self._build_headers())
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"小微系统登录响应: {result}")
                
                if result.get("success"):
                    token = result.get("data", {}).get("token")
                    if token:
                        logger.info(f"小微系统登录成功，获取到token: {token}")
                        return token
                    else:
                        raise Exception("登录成功但未获取到token")
                else:
                    raise Exception(f"登录失败: {result.get('message')}")
            else:
                raise Exception(f"HTTP错误: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"小微系统登录请求异常: {e}")
            raise Exception(f"网络请求异常: {str(e)}")
        except Exception as e:
            logger.error(f"小微系统登录处理异常: {e}")
            raise

    def get_auth_headers(self, token: str) -> Dict[str, str]:
        """获取认证头信息"""
        return self._build_headers(token)