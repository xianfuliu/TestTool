"""
征信前置操作实现类
"""

import logging
import time
from typing import Dict, Any, Optional

from ..utils.database_utils import DatabaseManager, DatabaseConfig

logger = logging.getLogger(__name__)


class CreditPreOperationImpl:
    """征信前置操作实现类"""

    def __init__(self):
        # 使用征信前置操作专用配置，不使用默认配置
        credit_pre_config = DatabaseConfig(DatabaseConfig.CREDIT_PRE_OPERATION_CONFIG)
        self.db_manager = DatabaseManager(credit_pre_config)

    async def credit_pre_operation(
        self, 
        operation_type: int, 
        business_num: Optional[str] = None,
        mobile: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        征信前置操作
        
        Args:
            operation_type: 操作类型 (1-更新人脸, 2-还原手机号)
            business_num: 业务号
            mobile: 手机号
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            if operation_type == 1:
                return await self._update_face_operation(business_num)
            elif operation_type == 2:
                return await self._restore_mobile_operation(mobile)
            else:
                raise ValueError(f"不支持的操作类型: {operation_type}")
                
        except Exception as e:
            logger.error(f"征信前置操作执行失败: {str(e)}")
            raise

    async def _update_face_operation(self, business_num: str) -> Dict[str, Any]:
        """更新人脸操作"""
        # 获取当前时间戳（毫秒）
        current_timestamp = int(time.time() * 1000)
        
        sql = """
        UPDATE indiv_auth.identity_auth_info 
        SET auth_url = %s,
            auth_short_url = %s,
            status = 1,
            similarity_score = '100.0',
            living_score = '99.0',
            authorized_scope = 'get_psn_identity_info',
            effective_time = %s,
            expire_time = '4100749995000'
        WHERE business_num = %s
        """
        
        params = (
            'https://smlh5.esign.cn/auth/h5/index?authFlowId=OF-260e0c2da508000d&clientType=ALL&appId=7438931189',
            'https://smlt.esign.cn/k8dKOYBHBFgS',
            str(current_timestamp),
            business_num
        )
        
        connection = self.db_manager.get_connection()
        try:
            with connection.cursor() as cursor:
                affected_rows = cursor.execute(sql, params)
                connection.commit()
                
                if affected_rows == 0:
                    return {
                        "operation_type": 1,
                        "business_num": business_num,
                        "affected_rows": 0,
                        "message": "未找到匹配的业务号，更新失败"
                    }
                
                return {
                    "operation_type": 1,
                    "business_num": business_num,
                    "affected_rows": affected_rows,
                    "message": "人脸信息更新成功"
                }
                
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()

    async def _restore_mobile_operation(self, mobile: str) -> Dict[str, Any]:
        """还原手机号操作"""
        connection = self.db_manager.get_connection()
        total_affected_rows = 0
        
        try:
            with connection.cursor() as cursor:
                # 第一个SQL：更新psn_account_info表
                sql1 = """
                UPDATE indiv_auth.psn_account_info AS A 
                INNER JOIN indiv_auth.identity_auth_info AS B ON A.id_num = B.id_card_no 
                SET A.mobile = B.mobile 
                WHERE A.mobile = %s
                """
                affected_rows1 = cursor.execute(sql1, (mobile,))
                total_affected_rows += affected_rows1
                
                # 第二个SQL：更新auth_flow_info表
                sql2 = """
                UPDATE indiv_auth.auth_flow_info AS A 
                INNER JOIN indiv_auth.identity_auth_info AS B ON A.card_no = B.id_card_no 
                SET A.mobile = B.mobile 
                WHERE A.mobile = %s
                """
                affected_rows2 = cursor.execute(sql2, (mobile,))
                total_affected_rows += affected_rows2
                
                connection.commit()
                
                return {
                    "operation_type": 2,
                    "mobile": mobile,
                    "affected_rows": total_affected_rows,
                    "psn_account_affected": affected_rows1,
                    "auth_flow_affected": affected_rows2,
                    "message": "手机号还原操作完成"
                }
                
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()