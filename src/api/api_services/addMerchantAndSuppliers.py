import logging
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from ..service_impl.addMerchantAndSuppliersImpl import AddMerchantAndSuppliersImpl

logger = logging.getLogger(__name__)


class AddMerchantAndSuppliersRequest(BaseModel):
    """新增商户和供应商请求模型"""
    type: int  # 1=新增商户, 2=新增供应商, 3=新增商户和供应商
    enterpriseName: str = None
    creditCode: str = None
    legalPersonName: str = None
    idNumber: str = None  # 身份证号，法人身份证号，必填
    bankCardNo: str = None
    bankName: str = None
    openBankName: str = None
    merchantId: str = None  # 商户ID，用户可传入，未传入时随机生成


class AddMerchantAndSuppliers:
    """新增商户和供应商API - 流程串联类"""

    def __init__(self):
        self.add_merchant_and_suppliers_impl = AddMerchantAndSuppliersImpl()

    async def add_merchant_and_suppliers(self, request: AddMerchantAndSuppliersRequest) -> Dict[str, Any]:
        """商户工作流程：根据type参数执行不同业务"""
        try:
            # 从请求模型中获取参数
            type_value = request.type
            enterpriseName = request.enterpriseName
            creditCode = request.creditCode
            legalPersonName = request.legalPersonName
            idNumber = request.idNumber  # 身份证号，法人身份证号
            bankCardNo = request.bankCardNo
            bankName = request.bankName
            openBankName = request.openBankName
            merchantId = request.merchantId
            
            # 根据type值进行参数验证
            if type_value == 1:  # 新增商户
                if not all([enterpriseName, creditCode, legalPersonName]):
                    raise HTTPException(status_code=400, detail="新增商户缺少必填参数: enterpriseName, creditCode, legalPersonName")
                # 如果未传入merchantId，则随机生成
                if not merchantId:
                    merchantId = f"SHID{self.add_merchant_and_suppliers_impl._get_timestamp()}"
                    
            elif type_value == 2:  # 新增供应商
                if not all([merchantId, legalPersonName, idNumber, bankCardNo, bankName, openBankName]):
                    raise HTTPException(status_code=400, detail="新增供应商缺少必填参数: merchantId, legalPersonName, idNumber, bankCardNo, bankName, openBankName")
                    
            elif type_value == 3:  # 新增商户和供应商
                if not all([enterpriseName, creditCode, legalPersonName, idNumber, bankCardNo, bankName, openBankName]):
                    raise HTTPException(status_code=400, detail="新增商户和供应商缺少必填参数: enterpriseName, creditCode, legalPersonName, idNumber, bankCardNo, bankName, openBankName")
                # 如果未传入merchantId，则随机生成
                if not merchantId:
                    merchantId = f"SHID{self.add_merchant_and_suppliers_impl._get_timestamp()}"
            else:
                raise HTTPException(status_code=400, detail="type参数错误，必须是1、2或3")
            
            # 1. 登录
            logger.info("开始登录流程...")
            token = self.add_merchant_and_suppliers_impl.login()
            
            result = {}
            
            # 2. 根据type执行不同业务
            if type_value in [1, 3]:  # 新增商户或商户+供应商
                logger.info("开始新增商户流程...")
                merchant_result = self.add_merchant_and_suppliers_impl.add_merchant(
                    enterpriseName=enterpriseName,
                    creditCode=creditCode,
                    legalPersonName=legalPersonName,
                    merchantId=merchantId,
                    token=token
                )
                
                if not merchant_result.get("success"):
                    return {
                        "success": False, 
                        "message": f"新增商户失败: {merchant_result.get('message')}", 
                        "step": "add_merchant"
                    }
                result["merchant"] = merchant_result
            
            if type_value in [2, 3]:  # 新增供应商或商户+供应商
                logger.info("开始新增供应商流程...")
                supplier_result = self.add_merchant_and_suppliers_impl.edit_suppliers(
                    merchantId=merchantId,
                    legalPersonName=legalPersonName,
                    idNumber=idNumber,
                    bankCardNo=bankCardNo,
                    bankName=bankName,
                    openBankName=openBankName,
                    token=token
                )
                
                if not supplier_result.get("success"):
                    return {
                        "success": False, 
                        "message": f"新增供应商失败: {supplier_result.get('message')}", 
                        "step": "edit_suppliers"
                    }
                result["supplier"] = supplier_result
            
            # 根据type返回不同的成功消息
            if type_value == 1:
                message = "商户创建成功"
            elif type_value == 2:
                message = "供应商创建成功"
            else:
                message = "商户和供应商创建成功"
            
            return {
                "success": True,
                "message": message,
                "data": result
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"工作流程异常: {e}")
            raise HTTPException(status_code=500, detail=f"工作流程异常: {str(e)}")