from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import sys
import os
import logging

# 添加项目根目录到Python路径，以便导入settings
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from config.settings import BIZ_DATABASES
from ..services.data_sync_service import DataSyncService

# 配置日志
logger = logging.getLogger(__name__)


class DataSyncRequest(BaseModel):
    """数据同步请求模型"""
    guarantor_loan_no: str


class DataSyncResponse(BaseModel):
    """数据同步响应模型"""
    success: bool
    message: str
    details: Dict[str, Any]


class DataSyncController:
    """数据同步控制器"""
    
    def __init__(self):
        self.data_sync_service = None
        
    def _get_service(self) -> DataSyncService:
        """获取数据同步服务实例"""
        if not BIZ_DATABASES:
            raise HTTPException(
                status_code=500, 
                detail="未找到可用的数据库配置"
            )
        
        # 使用第一个数据库配置
        db_config = BIZ_DATABASES[0]
        
        if not self.data_sync_service:
            self.data_sync_service = DataSyncService(db_config)
            
        return self.data_sync_service
    
    async def sync_data(self, request: DataSyncRequest) -> DataSyncResponse:
        """
        数据同步接口
        
        根据guarantor_loan_no生成相关数据到各个业务表
        
        Args:
            request: 包含guarantor_loan_no的请求对象
            
        Returns:
            DataSyncResponse: 数据同步结果
        """
        try:
            # 记录请求参数
            logger.info(f"数据同步接口调用开始，请求参数: guarantor_loan_no={request.guarantor_loan_no}")
            
            # 获取数据同步服务
            service = self._get_service()
            logger.info("数据同步服务初始化完成")
            
            # 执行数据同步
            result = service.sync_data(request.guarantor_loan_no)
            logger.info(f"数据同步执行完成，结果: {result}")
            
            # 记录响应信息
            response = DataSyncResponse(
                success=result['success'],
                message=result['message'],
                details=result['details']
            )
            logger.info(f"接口响应: {response}")
            
            return response
            
        except HTTPException as e:
            # 记录HTTP异常
            logger.error(f"HTTP异常: 状态码={e.status_code}, 详情={e.detail}")
            logger.error(f"请求参数: guarantor_loan_no={request.guarantor_loan_no}")
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 记录其他异常
            logger.error(f"数据同步过程中出现异常: {str(e)}")
            logger.error(f"异常类型: {type(e).__name__}")
            logger.error(f"请求参数: guarantor_loan_no={request.guarantor_loan_no}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            # 处理其他异常
            raise HTTPException(
                status_code=500, 
                detail=f"数据同步过程中出现异常: {str(e)}"
            )