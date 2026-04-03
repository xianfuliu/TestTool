"""
小微定时任务接口
"""

import json
import logging
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Union

from ..utils.micro_schedule_executor import MicroScheduleExecutor

logger = logging.getLogger(__name__)


class MicroScheduleRequest(BaseModel):
    """小微定时任务请求模型"""
    id: int  # 任务ID
    executorParam: Union[Dict[str, Any], str]  # 执行参数（支持字典或JSON字符串）


class MicroSchedule:
    """小微定时任务API"""

    def __init__(self):
        self.micro_schedule_executor = MicroScheduleExecutor()

    def _parse_executor_param(self, executor_param: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """解析执行参数，支持字典和JSON字符串格式"""
        if isinstance(executor_param, dict):
            return executor_param
        elif isinstance(executor_param, str):
            try:
                # 尝试解析JSON字符串
                return json.loads(executor_param)
            except json.JSONDecodeError as e:
                logger.error(f"executorParam JSON解析失败: {str(e)}, 原始数据: {executor_param}")
                raise HTTPException(status_code=400, detail=f"executorParam格式错误: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="executorParam必须是字典或JSON字符串")

    def micro_schedule(self, request: MicroScheduleRequest) -> Dict[str, Any]:
        """小微定时任务 - 调用小微定时任务执行器"""
        try:
            # 从请求模型中获取参数
            task_id = request.id
            executor_param_raw = request.executorParam
            
            # 参数验证
            if not task_id:
                raise HTTPException(status_code=400, detail="任务ID(id)不能为空")
            
            if not executor_param_raw:
                raise HTTPException(status_code=400, detail="执行参数(executorParam)不能为空")
            
            # 解析执行参数
            executor_param = self._parse_executor_param(executor_param_raw)
            
            # 调用小微定时任务执行器
            result = self.micro_schedule_executor.execute_task(task_id, executor_param)
            
            # 根据执行结果返回响应
            if result.get("success"):
                return {
                    "code": 200,
                    "message": "小微定时任务执行成功",
                    "data": result.get("data", {})
                }
            else:
                raise HTTPException(status_code=500, detail=result.get("message", "小微定时任务执行失败"))
                
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            logger.error(f"小微定时任务执行异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"小微定时任务执行异常: {str(e)}")