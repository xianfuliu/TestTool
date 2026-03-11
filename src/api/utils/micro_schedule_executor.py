"""
小微定时任务执行工具类
"""

import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MicroScheduleExecutor:
    """小微定时任务执行工具类"""
    
    def __init__(self):
        self.base_url = "http://47.106.192.83/job-admin"
        self.login_identity = None
        
    def _build_headers(self, content_type: str = "application/x-www-form-urlencoded; charset=UTF-8") -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": content_type
        }
        
        if self.login_identity:
            # 构建完整的cookie，包含所有必要的字段
            cookie_parts = [
                f"XXL_JOB_LOGIN_IDENTITY={self.login_identity}",
                "Luna-UserCn=%E6%B5%8B%E8%AF%9520000",
                "Luna-Org=10000", 
                "Luna-User=test20000",
                "username=test20000",
                "password=DBYYTRabcBiCT31xxWjd8DEXB/LIjwr2eKgl0WMndVv4bKh6B4X6LQbi+QFthcVucDz412aF3Wwku9vlO0ur3g==",
                "sidebarStatus=1",
                "Luna-Token=eyJhbGciOiJIUzI1NiJ9.eyJvcmciOiIxMDAwMCIsIm1vZHVsZSI6Imx1bmEiLCJ1c2VyIjoidGVzdDIwMDAwIiwidGltZXN0YW1wIjoxNzczMDQ2NzE0NTM3fQ.R8j3F8POX7zjE7piaSZtBU2sIfDZuZKFnHRwqpCbv4k",
                "acw_tc=2f6ac05317731057706997199e860c78400c71974d16110e8fd41536245987"
            ]
            headers["Cookie"] = "; ".join(cookie_parts)
        
        return headers
    
    def login(self) -> bool:
        """登录XXL-JOB管理后台并获取登录凭证"""
        try:
            url = f"{self.base_url}/login"
            
            login_data = {
                "userName": "test20000",
                "password": "test20000", 
                "ifRemember": "on"
            }
            
            logger.info(f"XXL-JOB登录请求: {url}")
            
            response = requests.post(url, data=login_data, headers=self._build_headers())
            
            if response.status_code == 200:
                # 从响应头中提取set-cookie字段
                set_cookie = response.headers.get('set-cookie', '')
                logger.info(f"XXL-JOB登录响应头set-cookie: {set_cookie}")
                
                # 提取XXL_JOB_LOGIN_IDENTITY字段
                if "XXL_JOB_LOGIN_IDENTITY=" in set_cookie:
                    cookie_parts = set_cookie.split(";")
                    for part in cookie_parts:
                        if "XXL_JOB_LOGIN_IDENTITY=" in part:
                            self.login_identity = part.split("XXL_JOB_LOGIN_IDENTITY=")[1].strip()
                            logger.info(f"成功获取XXL_JOB_LOGIN_IDENTITY: {self.login_identity}")
                            return True
                
                logger.warning("未找到XXL_JOB_LOGIN_IDENTITY字段")
                return False
            else:
                logger.error(f"XXL-JOB登录失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"XXL-JOB登录异常: {str(e)}")
            return False
    
    def execute_task(self, task_id: int, executor_param: Dict[str, Any]) -> Dict[str, Any]:
        """执行定时任务"""
        try:
            # 先登录获取凭证
            if not self.login():
                return {
                    "success": False,
                    "message": "登录失败，无法执行任务"
                }
            
            url = f"{self.base_url}/jobinfo/trigger"
            
            # 构建任务执行参数
            task_data = {
                "id": str(task_id),
                "executorParam": str(executor_param) if isinstance(executor_param, dict) else executor_param
            }
            
            logger.info(f"执行XXL-JOB任务: {url}, 任务ID: {task_id}, 参数: {executor_param}")
            
            response = requests.post(url, data=task_data, headers=self._build_headers())
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"XXL-JOB任务执行响应: {result}")
                
                # 执行完成后退出登录
                self.logout()
                
                return {
                    "success": True,
                    "data": result,
                    "message": "任务执行成功"
                }
            else:
                logger.error(f"XXL-JOB任务执行失败，状态码: {response.status_code}")
                
                # 执行失败也退出登录
                self.logout()
                
                return {
                    "success": False,
                    "message": f"任务执行失败，状态码: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"XXL-JOB任务执行异常: {str(e)}")
            
            # 异常情况下也尝试退出登录
            try:
                self.logout()
            except:
                pass
            
            return {
                "success": False,
                "message": f"任务执行异常: {str(e)}"
            }
    
    def logout(self) -> bool:
        """退出登录"""
        try:
            if not self.login_identity:
                logger.info("无登录凭证，无需退出")
                return True
            
            url = f"{self.base_url}/logout"
            
            logger.info(f"XXL-JOB退出登录请求: {url}")
            
            response = requests.post(url, headers=self._build_headers())
            
            if response.status_code == 200:
                logger.info("XXL-JOB退出登录成功")
                self.login_identity = None
                return True
            else:
                logger.warning(f"XXL-JOB退出登录失败，状态码: {response.status_code}")
                self.login_identity = None
                return False
                
        except Exception as e:
            logger.error(f"XXL-JOB退出登录异常: {str(e)}")
            self.login_identity = None
            return False
    
    def execute_specific_task(self) -> Dict[str, Any]:
        """执行特定的定时任务（任务ID: 45）"""
        task_id = 45
        executor_param = {
            "group": "cdms",
            "channel": "cdms-yy-simple", 
            "messageId": "yyLoanAuthorizationCallback",
            "body": {}
        }
        
        return self.execute_task(task_id, executor_param)