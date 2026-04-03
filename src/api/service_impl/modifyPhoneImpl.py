"""
修改用户手机号实现类
"""

import logging
import requests
import json
from typing import Dict, Any

from ..utils.database_utils import DatabaseManager, DatabaseConfig

logger = logging.getLogger(__name__)


class ModifyPhoneImpl:
    """修改用户手机号实现类"""

    def __init__(self):
        # 使用征信前置操作专用配置
        credit_pre_config = DatabaseConfig(DatabaseConfig.CREDIT_PRE_OPERATION_CONFIG)
        self.db_manager = DatabaseManager(credit_pre_config)

    def modify_phone(
        self, 
        new_phone: str, 
        old_phone: str
    ) -> Dict[str, Any]:
        """
        修改用户手机号 - 五步操作
        
        Args:
            new_phone: 新手机号
            old_phone: 旧手机号
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 第一步：还原手机号（参考operation_type=3）
            step1_result = self._step1_restore_mobile(new_phone)
            
            # 第二步：通过oldPhone查询card_no和business_num
            step2_result = self._step2_query_card_no(old_phone)
            if not step2_result["success"]:
                return step2_result
                
            id_num = step2_result["data"]["card_no"]
            business_num = step2_result["data"]["business_num"]
            
            # 第三步：调用接口创建签章账号
            step3_result = self._step3_create_sign_account(business_num, new_phone)
            if step3_result["code"] != 200:
                return step3_result
            
            # 第四步：调用HTTP接口修改手机号
            step4_result = self._step4_call_modify_phone_api(id_num, new_phone, old_phone)
            if step4_result["code"] != 200:
                return step4_result
            
            # 第五步：更新签章手机号（参考operation_type=2）
            step5_result = self._step5_update_mobile(id_num, new_phone)
            
            return {
                "operation_type": "modify_phone",
                "old_phone": old_phone,
                "new_phone": new_phone,
                "id_num": id_num,
                "business_num": business_num,
                "step1": step1_result,
                "step2": step2_result,
                "step3": step3_result,
                "step4": step4_result,
                "step5": step5_result,
                "message": "手机号修改操作执行成功"
            }
                
        except Exception as e:
            logger.error(f"手机号修改操作执行失败: {str(e)}")
            raise

    def _step1_restore_mobile(self, mobile: str) -> Dict[str, Any]:
        """
        第一步：还原手机号
        参考CreditPreOperationRequest类operation_type=3时，SQL的mobile=newPhone
        """
        connection = self.db_manager.get_connection()
        total_affected_rows = 0
        
        try:
            with connection.cursor() as cursor:
                # 更新auth_flow_info表
                sql1 = """
                UPDATE indiv_auth.auth_flow_info 
                SET mobile = %s 
                WHERE mobile = %s
                """
                affected_rows1 = cursor.execute(sql1, (mobile, mobile))
                total_affected_rows += affected_rows1
                
                # 更新identity_auth_info表
                sql2 = """
                UPDATE indiv_auth.identity_auth_info 
                SET mobile = %s 
                WHERE mobile = %s
                """
                affected_rows2 = cursor.execute(sql2, (mobile, mobile))
                total_affected_rows += affected_rows2
                
                connection.commit()
                
                return {
                    "step": 1,
                    "operation": "restore_mobile",
                    "mobile": mobile,
                    "affected_rows": total_affected_rows,
                    "message": "手机号还原操作执行成功"
                }
                
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()

    def _step2_query_card_no(self, mobile: str) -> Dict[str, Any]:
        """
        第二步：通过oldPhone查询表获取card_no和business_num
        SQL: SELECT card_no, business_num FROM indiv_auth.auth_flow_info WHERE mobile = 'oldPhone'
        """
        connection = self.db_manager.get_connection()
        
        try:
            with connection.cursor() as cursor:
                sql = """
                SELECT card_no, business_num 
                FROM indiv_auth.auth_flow_info 
                WHERE mobile = %s
                """
                cursor.execute(sql, (mobile,))
                result = cursor.fetchone()
                
                if not result:
                    return {
                        "step": 2,
                        "operation": "query_card_no",
                        "mobile": mobile,
                        "success": False,
                        "message": f"未找到手机号{mobile}对应的用户信息"
                    }
                
                card_no = result["card_no"]
                business_num = result["business_num"]
                
                return {
                    "step": 2,
                    "operation": "query_card_no",
                    "mobile": mobile,
                    "success": True,
                    "data": {
                        "card_no": card_no,
                        "business_num": business_num
                    },
                    "message": "用户信息查询成功"
                }
                
        except Exception as e:
            raise e
        finally:
            connection.close()

    def _step3_create_sign_account(self, business_num: str, new_phone: str) -> Dict[str, Any]:
        """
        第三步：调用接口创建签章账号
        POST: http://47.106.192.83:8091/api/v2/sign/createSignAccount
        参数提交方式：content-type：application/x-www-form-urlencoded
        """
        url = "http://47.106.192.83:8091/api/v2/sign/createSignAccount"
        payload = {
            "businessNum": business_num
        }
        
        try:
            response = requests.post(
                url, 
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30
            )
            
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("code") == "200":
                return {
                    "step": 3,
                    "operation": "create_sign_account",
                    "url": url,
                    "payload": payload,
                    "response": response_data,
                    "code": 200,
                    "message": "签章账号创建成功"
                }
            else:
                return {
                    "step": 3,
                    "operation": "create_sign_account",
                    "url": url,
                    "payload": payload,
                    "response": response_data,
                    "code": response_data.get("code", response.status_code),
                    "message": f"签章账号创建失败: {response_data.get('msg', '未知错误')}"
                }
                        
        except Exception as e:
            return {
                "step": 3,
                "operation": "create_sign_account",
                "url": url,
                "payload": payload,
                "error": str(e),
                "code": 500,
                "message": f"签章账号创建异常: {str(e)}"
            }

    def _step4_call_modify_phone_api(
        self, 
        id_num: str, 
        new_phone: str, 
        old_phone: str
    ) -> Dict[str, Any]:
        """
        第四步：调用HTTP接口修改手机号
        POST: http://47.106.192.83:8091/api/v2/psn/modifyPhone
        入参: {"idNum": "${idNum}", "newPhone": "${newPhone}", "oldPhone": "${oldPhone}"}
        """
        url = "http://47.106.192.83:8091/api/v2/psn/modifyPhone"
        payload = {
            "idNum": id_num,
            "newPhone": new_phone,
            "oldPhone": old_phone
        }
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("code") == 200:
                return {
                    "step": 4,
                    "operation": "call_modify_phone_api",
                    "url": url,
                    "payload": payload,
                    "response": response_data,
                    "code": 200,
                    "message": "HTTP接口调用成功"
                }
            else:
                return {
                    "step": 4,
                    "operation": "call_modify_phone_api",
                    "url": url,
                    "payload": payload,
                    "response": response_data,
                    "code": response_data.get("code", response.status_code),
                    "message": f"HTTP接口调用失败: {response_data.get('msg', '未知错误')}"
                }
                        
        except Exception as e:
            return {
                "step": 4,
                "operation": "call_modify_phone_api",
                "url": url,
                "payload": payload,
                "error": str(e),
                "code": 500,
                "message": f"HTTP接口调用异常: {str(e)}"
            }

    def _step5_update_mobile(self, card_no: str, mobile: str) -> Dict[str, Any]:
        """
        第五步：更新签章手机号
        参考CreditPreOperationRequest类operation_type=2时，SQL需要修改为：
        UPDATE indiv_auth.auth_flow_info SET mobile = 'newPhone' WHERE card_no = 'idNum'
        """
        connection = self.db_manager.get_connection()
        
        try:
            with connection.cursor() as cursor:
                sql = """
                UPDATE indiv_auth.auth_flow_info 
                SET mobile = %s 
                WHERE card_no = %s
                """
                
                affected_rows = cursor.execute(sql, (mobile, card_no))
                connection.commit()
                
                if affected_rows == 0:
                    return {
                        "step": 5,
                        "operation": "update_mobile",
                        "card_no": card_no,
                        "mobile": mobile,
                        "affected_rows": 0,
                        "message": "未找到匹配的card_no，更新失败"
                    }
                
                return {
                    "step": 5,
                    "operation": "update_mobile",
                    "card_no": card_no,
                    "mobile": mobile,
                    "affected_rows": affected_rows,
                    "message": "签章手机号更新成功"
                }
                
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()