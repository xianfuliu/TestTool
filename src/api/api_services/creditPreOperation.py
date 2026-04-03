"""
征信前置操作接口
"""

import logging
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from ..service_impl.creditPreOperationImpl import CreditPreOperationImpl
from ..utils.validation_utils import is_empty_value, validate_enum_value

logger = logging.getLogger(__name__)


class CreditPreOperationRequest(BaseModel):
    """征信前置操作请求模型"""
    operation_type: int = Field(..., description="操作类型: 1-更新人脸, 2-还原手机号")
    business_num: Optional[str] = Field(None, description="业务号，类型=1时需要")
    mobile: Optional[str] = Field(None, description="手机号，类型=2时需要")


class CreditPreOperation:
    """征信前置操作API"""

    def __init__(self):
        self.credit_pre_operation_impl = CreditPreOperationImpl()

    async def credit_pre_operation(self, request: CreditPreOperationRequest) -> Dict[str, Any]:
        """征信前置操作"""
        try:
            # 验证操作类型
            is_valid, error_msg = validate_enum_value(
                str(request.operation_type), ["1", "2"], "操作类型"
            )
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)
            
            # 根据操作类型验证必填参数
            if request.operation_type == 1:
                if is_empty_value(request.business_num):
                    raise HTTPException(
                        status_code=400, 
                        detail=f"操作类型{request.operation_type}需要业务号(business_num)参数"
                    )
            
            if request.operation_type == 2:
                if is_empty_value(request.mobile):
                    raise HTTPException(
                        status_code=400, 
                        detail=f"操作类型{request.operation_type}需要手机号(mobile)参数"
                    )
            
            # 调用实现类执行操作
            result = await self.credit_pre_operation_impl.credit_pre_operation(
                operation_type=request.operation_type,
                business_num=request.business_num,
                mobile=request.mobile
            )
            
            return {
                "code": 200,
                "message": "征信前置操作执行成功",
                "data": result
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"征信前置操作失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"征信前置操作失败: {str(e)}")