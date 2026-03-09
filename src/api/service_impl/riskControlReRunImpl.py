import logging
import requests
from typing import Dict, Any, Optional
from ..utils.database_utils import DatabaseConfig, DatabaseManager
from ..utils.micro_login import MicroLogin

logger = logging.getLogger(__name__)


class RiskControlReRunImpl:
    """风控重跑实现类"""
    
    def __init__(self):
        self.risk_db_manager = DatabaseManager(DatabaseConfig(DatabaseConfig.RISK_CONTROL_CONFIG))
        self.app_db_manager = DatabaseManager(DatabaseConfig(DatabaseConfig.APPLICATION_CONFIG))
        self.base_url = "http://47.106.192.83"
        self.micro_login = MicroLogin()
        # 初始化时获取登录态，避免重复登录
        self.token = self.micro_login.login()
        self.headers = self._build_headers(self.token)
    
    def _build_headers(self, token: str = None) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Origin": "http://47.106.192.83",
            "Referer": "http://47.106.192.83/"
        }
        
        if token:
            headers["Cookie"] = f"XXL_JOB_LOGIN_IDENTITY=7b226964223a312c22757365726e616d65223a2261646d696e222c2270617373776f7264223a226531306164633339343962613539616262653536653035376632306638383365222c22726f6c65223a312c227065726d697373696f6e223a6e756c6c7d; username=test20000; Luna-UserCn=%E6%B5%8B%E8%AF%9520000; Luna-Org=10000; Luna-User=test20000; Luna-Token={token}; password=OWZPiYL57w76I27rs4QIv0fjgMMpdfkn20BoHAOMYIXB+/WuLP3LfT17/poCR1VTtMmvT1apyf/EihxnYSP0SQ==; Admin-Token=eyJhbGciOiJIUzUxMiJ9.eyJsb2dpbl91c2VyX2tleSI6IjE3N2IxZjk3LWYwNDgtNGQxZC1hOTI0LWIzMzY5NDY1NzQyNiJ9.WwEAir9L1-4EhEkMLIn9IaeAECYYCTniZjPfSvDGOTtUvEJtk6Y8f07ZX1k5zltZgNt31CO_6U3JlFgfXy0M9Q; sidebarStatus=1"
            headers["X-Authorization"] = token
        
        return headers
    
    def _make_request(self, method: str, url: str, headers: Dict[str, str], data: Dict = None) -> Dict[str, Any]:
        """发送HTTP请求"""
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
                logger.info(f"GET请求响应: {response.text}")
                return response.json()
            elif method.upper() == "POST":
                # 根据Content-Type决定使用data还是json参数
                content_type = headers.get("Content-Type", "")
                if "application/json" in content_type:
                    # 使用JSON格式
                    response = requests.post(url, headers=headers, json=data)
                else:
                    # 使用URL编码的表单数据
                    response = requests.post(url, headers=headers, data=data)
                logger.info(f"POST请求响应: {response.text}")
                return response.json()
            else:
                raise Exception(f"不支持的HTTP方法: {method}")
        except requests.RequestException as e:
            logger.error(f"HTTP请求失败: {str(e)}")
            raise Exception(f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}")
            raise Exception(f"请求处理失败: {str(e)}")
    
    def execute_sql_operations(self, apply_no: str) -> Dict[str, Any]:
        """执行SQL删除和更新操作"""
        try:
            # 从applyNo提取order_no（假设格式为CR开头，最后8位为order_no）
            order_no = apply_no
            
            # 执行风控库删除操作
            delete_operations = [
                ("DELETE FROM micro_rimsdb.rims_apply_main WHERE APPLY_NO = %s", (apply_no,)),
                ("DELETE FROM micro_rimsdb.rims_loan_risk WHERE APPLY_NO = %s", (apply_no,)),
                ("DELETE FROM micro_rimsdb.rims_apply_history WHERE APPLY_NO = %s", (apply_no,))
            ]
            
            for sql, params in delete_operations:
                affected_rows = self.risk_db_manager.execute_update(sql, params)
                logger.info(f"执行SQL: {sql}, 影响行数: {affected_rows}")
            
            # 执行进件库更新操作
            update_sql = "UPDATE micro_cdmsdb.cdms_order SET `STATUS` = 'D' WHERE ORDER_NO = %s"
            update_affected = self.app_db_manager.execute_update(update_sql, (order_no,))
            logger.info(f"执行SQL: {update_sql}, 影响行数: {update_affected}")
            
            return {
                "success": True,
                "message": "SQL操作执行成功",
                "deleted_rows": len(delete_operations),
                "updated_rows": update_affected
            }
            
        except Exception as e:
            logger.error(f"SQL操作执行失败: {e}")
            return {
                "success": False,
                "message": f"SQL操作执行失败: {str(e)}"
            }
    
    def query_running_instance(self, business_key: str) -> Optional[str]:
        """查询运行中的实例ID"""
        try:
            url = f"{self.base_url}/stage-flow-api/flow/instance/fetchInstanceList"
            data = {
                "draw": 5,
                "pageNo": 1,
                "pageSize": 10,
                "criteriaMap[processDefId]": "ytloan_verify_process:1:2892515",
                "criteriaMap[businessKey]": business_key
            }
            
            result = self._make_request("POST", url, self.headers, data)
            
            # 检查接口返回是否成功
            if not result.get("success"):
                error_msg = result.get("code", "未知错误")
                raise Exception(f"查询运行中实例接口返回失败: {error_msg}")
            
            if result.get("data") and result["data"].get("rowList"):
                row_list = result["data"]["rowList"]
                if row_list and len(row_list) > 0:
                    return row_list[0].get("id")
            
            return None
                
        except Exception as e:
            logger.error(f"查询运行中实例失败: {e}")
            raise Exception(f"查询运行中实例失败: {str(e)}")
    
    def delete_running_instance(self, instance_id: str) -> bool:
        """删除运行中的实例"""
        try:
            url = f"{self.base_url}/stage-flow-api/flow/instance/deleteProcessInstance"
            # 删除实例接口需要使用JSON格式的数组
            data = [instance_id]
            
            # 临时修改Content-Type为JSON
            headers = self.headers.copy()
            headers["Content-Type"] = "application/json; charset=utf-8"
            
            result = self._make_request("POST", url, headers, data)
            
            # 检查接口返回是否成功
            if not result.get("success"):
                error_msg = result.get("message", result.get("code", "未知错误"))
                raise Exception(f"删除运行中实例接口返回失败: {error_msg}")
            
            logger.info(f"删除运行中实例成功: {instance_id}")
            return True
                
        except Exception as e:
            logger.error(f"删除运行中实例失败: {e}")
            raise Exception(f"删除运行中实例失败: {str(e)}")
    
    def query_history_instance(self, business_key: str) -> Optional[str]:
        """查询已完成的实例ID"""
        try:
            url = f"{self.base_url}/stage-flow-api/flow/historyInstance/fetchHisInstanceList"
            data = {
                "draw": 16,
                "pageNo": 1,
                "pageSize": 10,
                "criteriaMap[processDefId]": "ytloan_verify_process:1:2892515",
                "criteriaMap[businessKey]": business_key
            }
            
            result = self._make_request("POST", url, self.headers, data)
            
            # 检查接口返回是否成功
            if not result.get("success"):
                error_msg = result.get("code", "未知错误")
                raise Exception(f"查询历史实例接口返回失败: {error_msg}")
            
            if result.get("data") and result["data"].get("rowList"):
                row_list = result["data"]["rowList"]
                if row_list and len(row_list) > 0:
                    return row_list[0].get("id")
            
            return None
                
        except Exception as e:
            logger.error(f"查询历史实例失败: {e}")
            raise Exception(f"查询历史实例失败: {str(e)}")
    
    def delete_history_instance(self, instance_id: str) -> bool:
        """删除已完成的实例"""
        try:
            url = f"{self.base_url}/stage-flow-api/flow/historyInstance/deleteHistoryInstance"
            # 删除实例接口需要使用JSON格式的数组
            data = [instance_id]
            
            # 临时修改Content-Type为JSON
            headers = self.headers.copy()
            headers["Content-Type"] = "application/json; charset=utf-8"
            
            result = self._make_request("POST", url, headers, data)
            
            # 检查接口返回是否成功
            if not result.get("success"):
                error_msg = result.get("message", result.get("code", "未知错误"))
                raise Exception(f"删除历史实例接口返回失败: {error_msg}")
            
            logger.info(f"删除历史实例成功: {instance_id}")
            return True
                
        except Exception as e:
            logger.error(f"删除历史实例失败: {e}")
            raise Exception(f"删除历史实例失败: {str(e)}")
    
    def execute_rerun(self, apply_no: str) -> bool:
        """执行重跑操作"""
        try:
            # 重跑接口不需要登录态，直接调用
            url = f"{self.base_url}/fres-file/tcl/reRiskFlow"
            params = {"applyNo": apply_no}
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            result = response.text
            logger.info(f"重跑接口调用成功: {result}")
            return result.strip().lower() == "ok"
                
        except Exception as e:
            logger.error(f"重跑接口调用失败: {e}")
            return False
    
    def risk_control_rerun(self, apply_no: str) -> Dict[str, Any]:
        """风控重跑主流程"""
        try:
            # 第一步：执行SQL操作
            sql_result = self.execute_sql_operations(apply_no)
            if not sql_result["success"]:
                return sql_result
            
            # 第二步：删除实例
            instance_operations = []
            
            # 先查询运行中的实例
            running_instance_id = self.query_running_instance(apply_no)
            if running_instance_id:
                # 如果存在运行中实例，删除运行中实例
                delete_success = self.delete_running_instance(running_instance_id)
                instance_operations.append({
                    "type": "running",
                    "instance_id": running_instance_id,
                    "success": delete_success
                })
                
                # 检查删除操作是否成功
                if not delete_success:
                    return {
                        "success": False,
                        "message": f"运行中实例删除失败，实例ID: {running_instance_id}",
                        "apply_no": apply_no,
                        "sql_operations": sql_result,
                        "instance_operations": instance_operations
                    }
            else:
                # 如果没有运行中实例，查询已完成的实例
                history_instance_id = self.query_history_instance(apply_no)
                if history_instance_id:
                    # 如果存在已完成实例，删除已完成实例
                    delete_success = self.delete_history_instance(history_instance_id)
                    instance_operations.append({
                        "type": "history", 
                        "instance_id": history_instance_id,
                        "success": delete_success
                    })
                    
                    # 检查删除操作是否成功
                    if not delete_success:
                        return {
                            "success": False,
                            "message": f"已完成实例删除失败，实例ID: {history_instance_id}",
                            "apply_no": apply_no,
                            "sql_operations": sql_result,
                            "instance_operations": instance_operations
                        }
                else:
                    # 如果两个实例都不存在，记录无实例状态
                    instance_operations.append({
                        "type": "none",
                        "instance_id": None,
                        "success": True,
                        "message": "未找到运行中或已完成的实例"
                    })
            
            # 第三步：执行重跑
            rerun_success = self.execute_rerun(apply_no)
            if not rerun_success:
                return {
                    "success": False,
                    "message": "重跑接口调用失败",
                    "apply_no": apply_no,
                    "sql_operations": sql_result,
                    "instance_operations": instance_operations,
                    "rerun_success": rerun_success
                }
            
            return {
                "success": True,
                "message": "风控重跑流程执行完成",
                "apply_no": apply_no,
                "sql_operations": sql_result,
                "instance_operations": instance_operations,
                "rerun_success": rerun_success
            }
            
        except Exception as e:
            logger.error(f"风控重跑流程执行失败: {e}")
            return {
                "success": False,
                "message": f"风控重跑流程执行失败: {str(e)}",
                "apply_no": apply_no
            }