import requests
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
        self._cached_token = None  # 缓存登录token，避免重复登录

    def _get_token(self, force_refresh: bool = False) -> str:
        """获取登录token，每次调用接口都刷新token缓存"""
        if self._cached_token is None or force_refresh:
            logger.info("登录小微系统获取token")
            self._cached_token = self.micro_login.login()
        else:
            logger.info("使用缓存的token进行请求")
        return self._cached_token

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

    def _make_request(self, method: str, url: str, headers: Dict[str, str], data: Dict = None, content_type: str = "application/json", retry_count: int = 1) -> Dict[str, Any]:
        """发送HTTP请求，支持认证失败重试"""
        try:
            # 根据内容类型设置请求头
            request_headers = headers.copy()
            request_headers["Content-Type"] = content_type
            
            if method.upper() == "GET":
                response = requests.get(url, headers=request_headers)
            elif method.upper() == "POST":
                if content_type == "application/x-www-form-urlencoded":
                    response = requests.post(url, headers=request_headers, data=data)
                else:
                    response = requests.post(url, headers=request_headers, json=data)
            else:
                raise HTTPException(status_code=400, detail=f"不支持的HTTP方法: {method}")
            
            logger.info(f"{method}请求响应: {response.text}")
            result = response.json()
            
            # 检查是否认证失败，如果是则重试
            if result.get("success") == False and result.get("code") in ["9997", "9999"] and retry_count > 0:
                logger.warning(f"认证失败，尝试重新登录并重试，剩余重试次数: {retry_count}")
                # 强制刷新token
                self._get_token(force_refresh=True)
                # 更新headers
                new_headers = self._build_headers(self._cached_token)
                # 递归调用，减少重试次数
                return self._make_request(method, url, new_headers, data, content_type, retry_count - 1)
            
            return result
            
        except requests.RequestException as e:
            logger.error(f"HTTP请求失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"请求处理失败: {str(e)}")

    def fetch_unassigned_task_list(self, applyNo: str) -> Dict[str, Any]:
        """查询未分配审批任务"""
        try:
            token = self._get_token()
            headers = self._build_headers(token)
            
            url = f"{self.base_url}/rims/workbench/fetchUnAssignedTaskList"
            data = {"criteriaMap[applyNo]": applyNo}
            
            result = self._make_request("POST", url, headers, data, "application/x-www-form-urlencoded")
            
            # 处理响应数据，提取taskId和applyNo
            if result.get("success") and result.get("code") == "0000" and "data" in result and "rowList" in result["data"]:
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
                    # 没有未分配任务，返回空结果而不是抛出异常
                    logger.info(f"未找到未分配的审批任务，applyNo: {applyNo}")
                    return {
                        "taskId": None,
                        "applyNo": applyNo,
                        "message": "未找到未分配的审批任务"
                    }
            else:
                raise HTTPException(status_code=500, detail=f"查询未分配任务失败: {result.get('message', '未知错误')}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"查询未分配审批任务异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"查询未分配审批任务异常: {str(e)}")

    def claim_task(self, applyNo: str, taskId: str) -> Dict[str, Any]:
        """领取审批任务"""
        try:
            token = self._get_token()
            headers = self._build_headers(token)
            
            url = f"{self.base_url}/rims/workbench/claimTask"
            data = {
                "applyNo": applyNo,
                "taskId": taskId
            }
            
            result = self._make_request("POST", url, headers, data, "application/json")
            
            if result.get("success") and result.get("code") == "0000":
                return {"message": "任务领取成功"}
            else:
                raise HTTPException(status_code=500, detail=f"任务领取失败: {result.get('message', '未知错误')})")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"领取审批任务异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"领取审批任务异常: {str(e)}")

    def fetch_assigned_task_list(self, applyNo: str) -> Dict[str, Any]:
        """查询待审批任务"""
        try:
            token = self._get_token()
            headers = self._build_headers(token)
            
            url = f"{self.base_url}/rims/workbench/fetchAssignedTaskList"
            data = {"criteriaMap[applyNo]": applyNo}
            
            result = self._make_request("POST", url, headers, data, "application/x-www-form-urlencoded")
            
            # 处理响应数据，提取taskId和applyNo
            if result.get("success") and result.get("code") == "0000" and "data" in result and "rowList" in result["data"]:
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

    def commit_approval(self, applyNo: str, taskId: str, remark: str = "1", rtfState: str = "Pass", rejectionReasonCode: List[str] = ["风控成功"]) -> Dict[str, Any]:
        """提交审批"""
        try:
            token = self._get_token()
            headers = self._build_headers(token)
            
            url = f"{self.base_url}/rims/basicCheck/commit"
            data = {
                "applyNo": applyNo,
                "taskId": taskId,
                "remark": remark,
                "rtfState": rtfState,
                "rejectionReasonCode": rejectionReasonCode
            }
            
            result = self._make_request("POST", url, headers, data, "application/json")
            
            if result.get("success") and result.get("code") == "0000":
                return {"message": "审批提交成功"}
            else:
                raise HTTPException(status_code=500, detail=f"审批提交失败: {result.get('message', '未知错误')})")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"提交审批异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"提交审批异常: {str(e)}")

    def execute_complete_approval_flow(self, applyNo: str, remark: str = "1", rtfState: str = "Pass", rejectionReasonCode: List[str] = ["风控成功"]) -> Dict[str, Any]:
        """执行完整的授信订单审批流程"""
        try:
            flow_steps = []
            
            # 步骤1: 查询未分配任务 - 获取taskId和applyNo
            logger.info("开始查询未分配审批任务")
            unassigned_result = self.fetch_unassigned_task_list(applyNo)
            taskId = unassigned_result.get("taskId")
            extracted_applyNo = unassigned_result.get("applyNo")
            
            if taskId:
                # 有未分配任务，需要先领取
                flow_steps.append({
                    "step": "查询未分配任务", 
                    "status": "成功", 
                    "taskId": taskId,
                    "applyNo": extracted_applyNo
                })
                
                # 步骤2: 领取任务 - 使用获取到的taskId和applyNo
                logger.info("开始领取审批任务")
                claim_result = self.claim_task(extracted_applyNo, taskId)
                flow_steps.append({"step": "领取审批任务", "status": "成功"})
                
                # 步骤3: 查询待审批任务 - 再次获取taskId和applyNo（确认）
                logger.info("开始查询待审批任务")
                assigned_result = self.fetch_assigned_task_list(extracted_applyNo)
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
                approval_result = self.commit_approval(confirmed_applyNo, confirmed_taskId, remark, rtfState, rejectionReasonCode)
                flow_steps.append({"step": "提交审批", "status": "成功"})
                
                return {
                    "flow_steps": flow_steps,
                    "original_applyNo": applyNo,
                    "final_taskId": confirmed_taskId,
                    "final_applyNo": confirmed_applyNo,
                    "final_result": approval_result
                }
            else:
                # 没有未分配任务，直接查询待审批任务
                flow_steps.append({
                    "step": "查询未分配任务", 
                    "status": "无任务", 
                    "taskId": None,
                    "applyNo": applyNo
                })
                
                # 直接查询待审批任务
                logger.info("未找到未分配任务，直接查询待审批任务")
                assigned_result = self.fetch_assigned_task_list(applyNo)
                confirmed_taskId = assigned_result.get("taskId")
                confirmed_applyNo = assigned_result.get("applyNo")
                
                if confirmed_taskId:
                    flow_steps.append({
                        "step": "查询待审批任务", 
                        "status": "成功",
                        "taskId": confirmed_taskId,
                        "applyNo": confirmed_applyNo
                    })
                    
                    # 提交审批
                    logger.info("开始提交审批")
                    approval_result = self.commit_approval(confirmed_applyNo, confirmed_taskId, remark, rtfState, rejectionReasonCode)
                    flow_steps.append({"step": "提交审批", "status": "成功"})
                    
                    return {
                        "flow_steps": flow_steps,
                        "original_applyNo": applyNo,
                        "final_taskId": confirmed_taskId,
                        "final_applyNo": confirmed_applyNo,
                        "final_result": approval_result
                    }
                else:
                    # 既没有未分配任务，也没有待审批任务
                    flow_steps.append({
                        "step": "查询待审批任务", 
                        "status": "无任务",
                        "taskId": None,
                        "applyNo": applyNo
                    })
                    
                    return {
                        "flow_steps": flow_steps,
                        "original_applyNo": applyNo,
                        "final_taskId": None,
                        "final_applyNo": applyNo,
                        "final_result": {"message": "未找到可审批的任务"}
                    }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"授信订单审批流程执行异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"授信订单审批流程执行异常: {str(e)}")