"""
修改用户手机号接口
"""

import logging
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any

from ..service_impl.modifyPhoneImpl import ModifyPhoneImpl
from ..utils.validation_utils import is_empty_value

logger = logging.getLogger(__name__)


class ModifyPhoneRequest(BaseModel):
    """修改用户手机号请求模型"""
    newPhone: str = Field(..., description="新手机号")
    oldPhone: str = Field(..., description="旧手机号")


class ModifyPhone:
    """修改用户手机号API"""

    def __init__(self):
        self.modify_phone_impl = ModifyPhoneImpl()

    def modify_phone(self, request: ModifyPhoneRequest) -> Dict[str, Any]:
        """修改用户手机号"""
        try:
            # 验证必填参数
            if is_empty_value(request.newPhone):
                raise HTTPException(status_code=400, detail="新手机号(newPhone)为必填参数")
            
            if is_empty_value(request.oldPhone):
                raise HTTPException(status_code=400, detail="旧手机号(oldPhone)为必填参数")
            
            # 调用实现类执行操作
            result = self.modify_phone_impl.modify_phone(
                new_phone=request.newPhone,
                old_phone=request.oldPhone
            )
            
            return {
                "code": 200,
                "message": "手机号修改操作执行成功",
                "data": result
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"手机号修改操作失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"手机号修改操作失败: {str(e)}")