import aiohttp
import asyncio
import logging
from typing import Dict, Any, List
from fastapi import HTTPException

from ..utils.micro_login import MicroLogin

logger = logging.getLogger(__name__)


class CreditOrderApprovalImpl:
    """授信订单审批实现类"""

    def __init__(self):
        self.base_url = "http://47.106.192.83/stage-rims-api"
        self.micro_login = MicroLogin()

    def _build_headers(self, token: str = None) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        if token:
            headers["Cookie"] = f"XXL_JOB_LOGIN_IDENTITY=7b226964223a312c22757365726e616d65223a2261646d696e222c2270617373776f7264223a226531306164633339343962613539616262653536653035376632306638383365222c22726f6c65223a312c227065726d697373696f6e223a6e756c6b7d; sidebarStatus=1; Luna-Token={token}; Luna-UserCn=%E6%B5%8B%E8%AF%9520000; Luna-Org=10000; Luna-User=test20000"
            headers["x-authorization"] = token
        
        return headers

    async def _make_request(self, method: str, url: str, headers: Dict[str, str], data: Dict = None) -> Dict[str, Any]:
        """发送HTTP请求"""
        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == "GET":
                    async with session.get(url, headers=headers) as response:
                        response_text = await response.text()
                        logger.info(f"GET请求响应: {response_text}")
                        return await response.json()
                elif method.upper() == "POST":
                    async with session.post(url, headers=headers, json=data) as response:
                        response_text = await response.text()
                        logger.info(f"POST请求响应: {response_text}")
                        return await response.json()
                else:
                    raise HTTPException(status_code=400, detail=f"不支持的HTTP方法: {method}")
        except aiohttp.ClientError as e:
            logger.error(f"HTTP请求失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"请求处理失败: {str(e)}")

    async def fetch_unassigned_task_list(self, applyNo: str) -> Dict[str, Any]:
        """查询未分配审批任务"""
        try:
            token = self.micro_login.login()
            headers = self._build_headers(token)
            
            url = f"{self.base_url}/rims/workbench/fetchUnAssignedTaskList?criteriaMap[applyNo]={applyNo}"
            
            result = await self._make_request("POST", url, headers)
            
            # 处理响应数据，提取taskId和applyNo
            if result.get("code") == 200 and "data" in result and "rowList" in result["data"]:
                row_list = result["data"]["rowList"]
                if row_list and len(row_list) > 0:
                    task_info = row_list[0]
                    extracted_data = {
                        "taskId": task_info.get("taskId"),
                        "applyNo": task_info.get("applyNo")
                    }
                    logger.info(f"提取的任务信息: {extracted_data}")
                    return extracted_data
                else:
                    raise HTTPException(status_code=404, detail="未找到未分配的审批任务")
            else:
                raise HTTPException(status_code=500, detail=f"查询未分配任务失败: {result.get('message', '未知错误')}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"查询未分配审批任务异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"查询未分配审批任务异常: {str(e)}")

    async def claim_task(self, applyNo: str, taskId: str) -> Dict[str, Any]:
        """领取审批任务"""
        try:
            token = self.micro_login.login()
            headers = self._build_headers(token)
            
            url = f"{self.base_url}/rims/workbench/claimTask"
            data = {
                "applyNo": applyNo,
                "taskId": taskId
            }
            
            result = await self._make_request("POST", url, headers, data)
            
            if result.get("code") == 200:
                return {"message": "任务领取成功"}
            else:
                raise HTTPException(status_code=500, detail=f"任务领取失败: {result.get('message', '未知错误')}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"领取审批任务异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"领取审批任务异常: {str(e)}")

    async def fetch_assigned_task_list(self, applyNo: str) -> Dict[str, Any]:
        """查询待审批任务"""
        try:
            token = self.micro_login.login()
            headers = self._build_headers(token)
            
            url = f"{self.base_url}/rims/workbench/fetchAssignedTaskList?criteriaMap[applyNo]={applyNo}"
            
            result = await self._make_request("POST", url, headers)
            
            # 处理响应数据，提取taskId和applyNo
            if result.get("code") == 200 and "data" in result and "rowList" in result["data"]:
                row_list = result["data"]["rowList"]
                if row_list and len(row_list) > 0:
                    task_info = row_list[0]
                    extracted_data = {
                        "taskId": task_info.get("taskId"),
                        "applyNo": task_info.get("applyNo")
                    }
                    logger.info(f"提取的待审批任务信息: {extracted_data}")
                    return extracted_data
                else:
                    raise HTTPException(status_code=404, detail="未找到待审批任务")
            else:
                raise HTTPException(status_code=500, detail=f"查询待审批任务失败: {result.get('message', '未知错误')}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"查询待审批任务异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"查询待审批任务异常: {str(e)}")

    async def commit_approval(self, applyNo: str, taskId: str, remark: str = "1", rtfState: str = "Pass", rejectionReasonCode: List[str] = ["风控成功"]) -> Dict[str, Any]:
        """提交审批"""
        try:
            token = self.micro_login.login()
            headers = self._build_headers(token)
            
            url = f"{self.base_url}/rims/basicCheck/commit"
            data = {
                "applyNo": applyNo,
                "taskId": taskId,
                "remark": remark,
                "rtfState": rtfState,
                "rejectionReasonCode": rejectionReasonCode
            }
            
            result = await self._make_request("POST", url, headers, data)
            
            if result.get("code") == 200:
                return {"message": "审批提交成功"}
            else:
                raise HTTPException(status_code=500, detail=f"审批提交失败: {result.get('message', '未知错误')}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"提交审批异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"提交审批异常: {str(e)}")

    async def execute_complete_approval_flow(self, applyNo: str, remark: str = "1", rtfState: str = "Pass", rejectionReasonCode: List[str] = ["风控成功"]) -> Dict[str, Any]:
        """执行完整的授信订单审批流程"""
        try:
            flow_steps = []
            
            # 步骤1: 查询未分配任务 - 获取taskId和applyNo
            logger.info("开始查询未分配审批任务")
            unassigned_result = await self.fetch_unassigned_task_list(applyNo)
            taskId = unassigned_result.get("taskId")
            extracted_applyNo = unassigned_result.get("applyNo")
            
            if not taskId:
                raise HTTPException(status_code=404, detail="未找到可用的任务ID")
            
            flow_steps.append({
                "step": "查询未分配任务", 
                "status": "成功", 
                "taskId": taskId,
                "applyNo": extracted_applyNo
            })
            
            # 步骤2: 领取任务 - 使用获取到的taskId和applyNo
            logger.info("开始领取审批任务")
            claim_result = await self.claim_task(extracted_applyNo, taskId)
            flow_steps.append({"step": "领取审批任务", "status": "成功"})
            
            # 步骤3: 查询待审批任务 - 再次获取taskId和applyNo（确认）
            logger.info("开始查询待审批任务")
            assigned_result = await self.fetch_assigned_task_list(extracted_applyNo)
            confirmed_taskId = assigned_result.get("taskId")
            confirmed_applyNo = assigned_result.get("applyNo")
            
            flow_steps.append({
                "step": "查询待审批任务", 
                "status": "成功",
                "taskId": confirmed_taskId,
                "applyNo": confirmed_applyNo
            })
            
            # 步骤4: 提交审批 - 使用确认后的taskId和applyNo
            logger.info("开始提交审批")
            approval_result = await self.commit_approval(confirmed_applyNo, confirmed_taskId, remark, rtfState, rejectionReasonCode)
            flow_steps.append({"step": "提交审批", "status": "成功"})
            
            return {
                "flow_steps": flow_steps,
                "original_applyNo": applyNo,
                "final_taskId": confirmed_taskId,
                "final_applyNo": confirmed_applyNo,
                "final_result": approval_result
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"授信订单审批流程执行异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"授信订单审批流程执行异常: {str(e)}")