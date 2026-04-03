import logging
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ..service_impl.deleteUserDataImpl import DeleteUserDataImpl
from ..utils.validation_utils import is_empty_value

logger = logging.getLogger(__name__)


class DeleteUserDataRequest(BaseModel):
    """用户删除请求模型"""
    guarantor_loan_no: str  # 担保贷款号，必填


class DeleteUserData:
    """用户删除API - 流程串联类"""

    def __init__(self):
        self.delete_user_data_impl = DeleteUserDataImpl()

    async def delete_user_data(self, request: DeleteUserDataRequest) -> Dict[str, Any]:
        """用户删除工作流程：删除用户相关数据"""
        try:
            # 验证必填参数
            if is_empty_value(request.guarantor_loan_no):
                raise HTTPException(status_code=400, detail="担保贷款号(guarantor_loan_no)为必填参数")
            
            # 调用实现类删除用户数据
            result = await self.delete_user_data_impl.delete_user_data(
                guarantor_loan_no=request.guarantor_loan_no
            )
            
            return {
                "code": 200,
                "message": "用户数据删除成功",
                "data": result
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"用户数据删除失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"用户数据删除失败: {str(e)}")