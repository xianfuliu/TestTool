import logging
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from ..service_impl.creditOrderApprovalImpl import CreditOrderApprovalImpl

logger = logging.getLogger(__name__)


class CreditOrderApprovalRequest(BaseModel):
    """授信订单审批请求模型"""
    applyNo: str  # 申请编号
    remark: str = "1"  # 备注，默认"1"
    rtfState: str = "Pass"  # 审批状态，默认"Pass"
    rejectionReasonCode: List[str] = ["风控成功"]  # 拒绝原因代码，默认["风控成功"]


class CreditOrderApproval:
    """授信订单审批API - 流程串联类"""

    def __init__(self):
        self.credit_order_approval_impl = CreditOrderApprovalImpl()

    async def credit_order_approval(self, request: CreditOrderApprovalRequest) -> Dict[str, Any]:
        """授信订单审批完整流程：查询未分配任务 -> 领取任务 -> 查询待审批任务 -> 审批任务"""
        try:
            # 从请求模型中获取参数
            applyNo = request.applyNo
            remark = request.remark
            rtfState = request.rtfState
            rejectionReasonCode = request.rejectionReasonCode
            
            # 参数验证
            if not applyNo:
                raise HTTPException(status_code=400, detail="申请编号(applyNo)不能为空")
            
            # 执行完整的授信订单审批流程
            result = await self.credit_order_approval_impl.execute_complete_approval_flow(
                applyNo=applyNo,
                remark=remark,
                rtfState=rtfState,
                rejectionReasonCode=rejectionReasonCode
            )
            
            return {
                "code": 200,
                "message": "授信订单审批流程执行成功",
                "data": result
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"授信订单审批流程执行失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"授信订单审批流程执行失败: {str(e)}")