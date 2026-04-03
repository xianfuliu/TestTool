import logging
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from ..service_impl.riskControlReRunImpl import RiskControlReRunImpl
from ..utils.validation_utils import is_empty_value

logger = logging.getLogger(__name__)


class RiskControlReRunRequest(BaseModel):
    """风控重跑请求模型"""
    apply_no: str  # 业务流水号


class RiskControlReRun:
    """风控重跑API - 流程串联类"""

    def __init__(self):
        self.risk_control_rerun_impl = RiskControlReRunImpl()

    def risk_control_rerun(self, request: RiskControlReRunRequest) -> Dict[str, Any]:
        """风控重跑工作流程：执行风控重跑操作"""
        try:
            # 验证必填参数
            if is_empty_value(request.apply_no):
                raise HTTPException(status_code=400, detail="业务流水号(apply_no)为必填参数")
            
            # 验证apply_no格式（CR开头，数字结尾）
            if not request.apply_no.startswith('CR') or not request.apply_no[2:].isdigit():
                raise HTTPException(status_code=400, detail="业务流水号格式不正确，应以CR开头，后接数字")
            
            # 调用实现类执行风控重跑
            result = self.risk_control_rerun_impl.risk_control_rerun(request.apply_no)
            
            # 如果执行失败，抛出异常
            if not result.get("success"):
                raise HTTPException(status_code=500, detail=result.get("message", "风控重跑执行失败"))
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"风控重跑API执行异常: {e}")
            raise HTTPException(status_code=500, detail=f"风控重跑API执行异常: {str(e)}")