import logging
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ..service_impl.generateUserDataImpl import GenerateUserDataImpl
from ..utils.validation_utils import is_empty_value, validate_enum_value

logger = logging.getLogger(__name__)


class GenerateUserDataRequest(BaseModel):
    """用户造数请求模型"""
    guarantor_loan_no: Optional[str] = None  # 担保贷款号，未填写则随机生成
    phone: Optional[str] = None  # 手机号，未填写则随机生成
    relationship_A: Optional[str] = None  # 联系人A关系，未填写则写死
    relationship_B: Optional[str] = None  # 联系人B关系，未填写则写死
    phone_A: Optional[str] = None  # 联系人A手机号，未填写则随机生成
    phone_B: Optional[str] = None  # 联系人B手机号，未填写则随机生成
    name_A: Optional[str] = None  # 联系人A姓名，未填写则随机生成
    name_B: Optional[str] = None  # 联系人B姓名，未填写则随机生成
    loan_apply_no: Optional[str] = None  # 贷款申请号，未填写则随机生成
    name_OCR: Optional[str] = None  # OCR姓名，未填写则随机生成
    id_card_no_OCR: Optional[str] = None  # OCR身份证号，未填写则随机生成
    bank_card_no: Optional[str] = None  # 银行卡号，未填写则随机生成
    term: Optional[str] = None  # 贷款期限，必填
    module_type: Optional[str] = None  # 模块类型，必填（70019或70016）


class GenerateUserData:
    """用户造数API - 流程串联类"""

    def __init__(self):
        self.generate_user_data_impl = GenerateUserDataImpl()

    async def generate_user_data(self, request: GenerateUserDataRequest) -> Dict[str, Any]:
        """用户造数工作流程：生成完整的用户数据"""
        try:
            # 验证必填参数（使用公共验证工具）
            if is_empty_value(request.term):
                raise HTTPException(status_code=400, detail="贷款期限(term)为必填参数")
            if is_empty_value(request.module_type):
                raise HTTPException(status_code=400, detail="模块类型(module_type)为必填参数")
            
            # 验证枚举值（使用公共验证工具）
            is_valid, error_msg = validate_enum_value(request.module_type, ["70019", "70016"], "模块类型")
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)
            
            # 调用实现类生成用户数据
            result = await self.generate_user_data_impl.generate_user_data(
                guarantor_loan_no=request.guarantor_loan_no,
                phone=request.phone,
                relationship_A=request.relationship_A,
                relationship_B=request.relationship_B,
                phone_A=request.phone_A,
                phone_B=request.phone_B,
                name_A=request.name_A,
                name_B=request.name_B,
                loan_apply_no=request.loan_apply_no,
                name_OCR=request.name_OCR,
                id_card_no_OCR=request.id_card_no_OCR,
                bank_card_no=request.bank_card_no,
                term=request.term,
                module_type=request.module_type
            )
            
            # 检查是否存在错误（数据已存在等情况）
            if "error" in result:
                return {
                    "code": 400,
                    "message": result["error"],
                    "data": result
                }
            
            return {
                "code": 200,
                "message": "用户数据生成成功",
                "data": {
                    "basic_info": result["basic_info"],
                    "contact_info": result["contact_info"],
                    "file_info": result["file_info"],
                    "summary": result["summary"],
                    "message": result["message"]
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"用户数据生成失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"用户数据生成失败: {str(e)}")