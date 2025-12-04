#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用测试用例执行工具类
完整实现tabbed_case_editor.py中的测试用例执行逻辑
支持局部变量、全局变量、前置工具、后置工具、断言、参数提取、HTTP请求、接口模板等
"""

import sys
import os
import json
import logging
import traceback
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.database import Database
from src.utils.interface_utils.variable_manager import VariableManager
from src.utils.interface_utils.request_engine import RequestEngine
from src.core.services.global_variable_service import get_global_variable_service
from src.core.services.api_template_service import ApiTemplateService
from src.utils.sql_worker import SQLWorker
from PyQt5.QtCore import QEventLoop



class TestCaseExecutor:
    """通用测试用例执行器"""
    
    def __init__(self, project_id: int = 0, environment_config: Dict[str, Any] = None):
        """初始化执行器
        
        Args:
            project_id: 项目ID，用于加载全局变量
            environment_config: 环境配置，包含base_url等信息
        """
        self.db = Database()
        self.request_engine = RequestEngine()
        self.project_id = project_id
        self.environment_config = environment_config or {}
        self.variable_manager = VariableManager()
        
        # 日志回调机制
        self.log_callback = None
        self.execution_logs = []
        
        # 步骤级别回调机制
        self.step_started_callback = None
        self.step_finished_callback = None
        
        # 调用来源标识
        self.execution_source = 'debug'  # 默认调试模式
        
        # 调试模式标识
        self.debug_mode = self.execution_source == 'debug'
        
        # 初始化变量管理器
        self._init_variable_manager()
    
    def set_log_callback(self, callback: Callable[[str, str, int], None]):
        """设置日志回调函数
        
        Args:
            callback: 回调函数，参数为(日志级别, 日志内容, 步骤索引)
        """
        self.log_callback = callback
    
    def set_step_started_callback(self, callback: Callable[[str, int], None]):
        """设置步骤开始回调函数
        
        Args:
            callback: 回调函数，参数为(步骤名称, 步骤索引)
        """
        self.step_started_callback = callback
    
    def set_step_finished_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """设置步骤完成回调函数
        
        Args:
            callback: 回调函数，参数为(步骤结果字典)
        """
        self.step_finished_callback = callback
    
    def set_execution_source(self, source: str):
        """设置调用来源
        
        Args:
            source: 调用来源，'debug' 或 'scheduler'
        """
        if source in ['debug', 'scheduler']:
            self.execution_source = source
            # 更新调试模式标识
            self.debug_mode = self.execution_source == 'debug'
    
    def _log_message(self, level: str, message: str, step_index: int = None):
        """统一日志处理方法
        
        Args:
            level: 日志级别
            message: 日志内容
            step_index: 步骤索引（可选），用于按步骤归档日志
        """
        # 检查消息是否为空或无效
        if not message or message.strip() == "":
            # 如果消息为空，生成有意义的默认消息
            if step_index is not None and step_index >= 0:
                message = f"步骤 {step_index + 1} 执行信息"
            else:
                message = "通用执行信息"
            
            # 记录警告日志
            logging.warning(f"检测到空的日志消息，已使用默认消息: {message}")
        
        # 记录到执行日志列表，包含步骤索引信息
        log_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': level,
            'message': message,
            'step_index': step_index  # 添加步骤索引信息
        }
        self.execution_logs.append(log_entry)
        
        # 调用日志回调函数（如果设置），传递步骤索引
        if self.log_callback:
            self.log_callback(message, level, step_index)
        
        # 根据调用来源处理日志
        if self.execution_source == 'debug':
            # 调试模式：不调用标准logging，避免与已经格式化的消息冲突
            # 消息已经通过format_debug_message格式化，直接传递给UI线程显示
            pass
        else:
            # 定时调度模式：仅记录到日志列表，不输出到控制台
            pass
    
    def _store_step_logs_to_database(self, step_id: int, step_name: str, status: str, 
                                   start_time: datetime, end_time: datetime, 
                                   scheduler_id: int = None, report_id: int = None, 
                                   case_id: int = None, step_index: int = None):
        """存储步骤执行日志到test_step_results表
        
        Args:
            step_id: 步骤ID
            step_name: 步骤名称
            status: 执行状态
            start_time: 开始时间
            end_time: 结束时间
            scheduler_id: 调度器ID（定时调度时使用）
            report_id: 报告ID（定时调度时使用）
            case_id: 用例ID（定时调度时使用）
            step_index: 步骤索引（可选），用于日志记录
        """
        try:
            # 准备执行日志数据
            execution_logs = json.dumps(self.execution_logs, ensure_ascii=False, indent=2)
            
            # 插入步骤执行结果记录
            self.db.insert("test_step_results", {
                'scheduler_id': scheduler_id,
                'report_id': report_id,
                'case_id': case_id,
                'step_id': step_id,
                'step_name': step_name,
                'status': status,
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'execution_logs': execution_logs,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            self._log_message('INFO', f"步骤 '{step_name}' 执行日志已存储到数据库", step_index)
        except Exception as e:
            self._log_message('ERROR', f"存储步骤执行日志失败: {str(e)}", step_index)
    
    def _init_variable_manager(self):
        """初始化变量管理器，加载全局变量"""
        try:
            service = get_global_variable_service()
            service.sync_to_variable_manager(self.variable_manager, self.project_id)
            self._log_message('INFO', f"已加载项目 {self.project_id} 的全局变量")
        except Exception as e:
            self._log_message('WARNING', f"加载项目 {self.project_id} 的全局变量失败: {str(e)}")
    
    def execute_case(self, case_data: Dict[str, Any], 
                    stop_on_failure: bool = True,
                    generate_report: bool = False,
                    scheduler_id: Optional[int] = None,
                    parent_report_id: Optional[int] = None) -> Dict[str, Any]:
        """执行测试用例
        
        Args:
            case_data: 测试用例数据
            stop_on_failure: 是否在步骤失败时停止执行（tabbed_case_editor.py模式）
            generate_report: 是否生成测试报告（execute_test_case.py模式）
            scheduler_id: 调度ID（仅调度任务需要）
            parent_report_id: 父报告ID（用于统一报告模式）
        
        Returns:
            执行结果字典
        """
        # 清空执行日志
        self.execution_logs = []
        
        try:
            case_id = case_data.get('id', 0)
            case_name = case_data.get('name', '未知用例')
            
            # 记录用例开始执行信息（与tabbed_case_editor.py保持一致）
            self._log_message('INFO', f"开始执行测试用例: {case_name} (ID: {case_id})")
            
            # 获取测试步骤
            steps = case_data.get('steps', [])
            self._log_message('INFO', f"测试用例 {case_name} 包含 {len(steps)} 个步骤")
            
            # 统计启用的步骤（与tabbed_case_editor.py保持一致）
            enabled_steps = [step for step in steps if step.get('enabled', True)]
            self._log_message('INFO', f"启用的步骤数量: {len(enabled_steps)}")
            
            # 清空局部变量（每个用例执行时重新初始化，与tabbed_case_editor.py保持一致）
            self.variable_manager.clear_local_variables()
            
            # 记录变量管理器状态（与tabbed_case_editor.py保持一致）
            global_vars = self.variable_manager.global_variables
            self._log_message('INFO', f"全局变量数量: {len(global_vars)}")
            if global_vars:
                for var_name, var_value in global_vars.items():
                    self._log_message('DEBUG', f"全局变量: {var_name} = {var_value}")
            
            # 执行每个步骤（使用原始步骤序号，与tabbed_case_editor.py保持一致）
            step_results = []
            success_steps = 0
            original_step_order = 0
            
            for step in steps:
                # 检查步骤是否启用
                if not step.get('enabled', True):
                    original_step_order += 1
                    continue
                
                # 获取步骤序号（与tabbed_case_editor.py保持一致）
                step_order = step.get('step_order', original_step_order + 1)
                
                # 确保步骤序号是有效的正整数
                # 修复负数步骤序号问题：当step_order为负数时，使用original_step_order + 1
                if not isinstance(step_order, int) or step_order <= 0:
                    step_order = original_step_order + 1
                    logging.warning(f"检测到无效步骤序号{step.get('step_order')}，已修正为: {step_order}")
                
                # 再次确保step_order是有效的正整数（防止修正后仍然无效）
                if step_order <= 0:
                    step_order = 1
                    logging.warning(f"步骤序号修正后仍然无效，强制设置为: {step_order}")
                
                step_index = step_order - 1  # 转换为0开始的索引
                
                # 获取步骤标题（与tabbed_case_editor.py保持一致）
                step_name = step.get('api_name') or step.get('api_template', {}).get('name') or step.get('name', f'步骤{step_order}')
                
                # 调用步骤开始回调（如果设置）
                if self.step_started_callback:
                    try:
                        self.step_started_callback(step_name, step_index)
                    except Exception as e:
                        self._log_message('ERROR', f"步骤开始回调执行异常: {str(e)}", step_index)
                
                self._log_message('INFO', f"开始执行步骤 {step_order}: {step_name}", step_index)
                
                # 执行单个步骤
                step_start_time = datetime.now()
                step_result = self._execute_step(step, step_index, case_data)
                step_end_time = datetime.now()
                
                # 调用步骤完成回调（如果设置）
                if self.step_finished_callback:
                    try:
                        # 构建完整的步骤结果字典
                        step_result_with_metadata = {
                            'step_id': step.get('id'),
                            'step_name': step_name,
                            'step_order': step_order,
                            'step_index': step_index,
                            'status': step_result.get('status', 'unknown'),
                            'success': step_result.get('success', False),
                            'start_time': step_start_time,
                            'end_time': step_end_time,
                            'execution_time': (step_end_time - step_start_time).total_seconds(),
                            'response': step_result.get('response', {}),
                            'pre_processing': step_result.get('pre_processing', {}),
                            'post_processing': step_result.get('post_processing', {}),
                            'assertions': step_result.get('assertions', {})
                        }
                        self.step_finished_callback(step_result_with_metadata)
                    except Exception as e:
                        self._log_message('ERROR', f"步骤完成回调执行异常: {str(e)}", step_index)
                
                # 如果是定时调度执行，存储步骤日志到数据库
                if self.execution_source == 'scheduler' and scheduler_id and parent_report_id:
                    self._store_step_logs_to_database(
                        step_id=step.get('id'),
                        step_name=step_name,
                        status='PASS' if step_result.get('success', False) else 'FAIL',
                        start_time=step_start_time,
                        end_time=step_end_time,
                        scheduler_id=scheduler_id,
                        report_id=parent_report_id,
                        case_id=case_id,
                        step_index=step_index
                    )
                
                step_results.append(step_result)
                
                # 统计成功步骤数量
                if step_result.get('success', False):
                    success_steps += 1
                
                # 如果步骤执行失败且需要停止，则中断执行（与tabbed_case_editor.py保持一致）
                if not step_result.get('success', False) and stop_on_failure:
                    self._log_message('WARNING', "步骤执行失败，停止执行后续步骤", step_index)
                    break
                
                original_step_order += 1
            
            # 记录用例执行完成信息（与tabbed_case_editor.py保持一致）
            self._log_message('INFO', "用例执行完成")
            self._log_message('INFO', f"步骤统计: 成功 {success_steps}/{len(enabled_steps)}")
            
            return {
                'success': success_steps == len(enabled_steps),
                'message': '用例执行完成',
                'success_count': success_steps,
                'total_count': len(enabled_steps),
                'case_name': case_name,
                'case_id': case_id,
                'step_results': step_results,
                'execution_logs': self.execution_logs  # 添加执行日志到返回结果
            }
            
        except Exception as e:
            self._log_message('ERROR', f"用例执行异常: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'success_count': success_steps if 'success_steps' in locals() else 0,
                'total_count': len(enabled_steps) if 'enabled_steps' in locals() else 0,
                'case_name': case_name if 'case_name' in locals() else '未知用例',
                'case_id': case_id if 'case_id' in locals() else 0,
                'step_results': [],
                'execution_logs': self.execution_logs  # 添加执行日志到返回结果
            }
    
    def _execute_step(self, step_data: Dict[str, Any], step_index: int, 
                     case_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个步骤（与tabbed_case_editor.py保持一致）"""
        step_start_time = datetime.now()
        
        try:
            # 获取步骤序号和名称（与tabbed_case_editor.py保持一致）
            step_order = step_index + 1  # step_index是从0开始的，需要+1得到实际步骤序号
            step_name = step_data.get('api_name') or step_data.get('api_template', {}).get('name') or step_data.get('name', f'步骤{step_order}')
            
            self._log_message('INFO', f"执行步骤 {step_order}: {step_name}", step_index)
            
            # 1. 执行前置处理（与tabbed_case_editor.py保持一致）
            pre_processing = step_data.get('pre_processing', {})
            if pre_processing:
                self._log_message('DEBUG', "执行前置处理", step_index)
            pre_processing_result = self._execute_pre_processing(pre_processing, step_index)
            
            # 如果前置处理失败，直接返回错误
            if pre_processing_result.get('errors'):
                error_msg = f"步骤{step_order}前置处理失败: {pre_processing_result['errors'][0]}"
                self._log_message('ERROR', error_msg, step_index)
                return self._create_step_error_result(step_data, step_index, step_start_time, error_msg)
            
            # 2. 执行接口请求（使用execute_api_request方法，与tabbed_case_editor.py保持一致）
            api_template_id = step_data.get('api_template_id')
            if api_template_id:
                self._log_message('DEBUG', "执行接口请求", step_index)
                try:
                    response = self.execute_api_request(step_data, step_index, case_data)
                except Exception as e:
                    self._log_message('ERROR', f"接口请求执行异常: {str(e)}", step_index)
                    response = {
                        'success': False,
                        'error': str(e),
                        'status': 'error',
                        'duration': 0
                    }
            else:
                self._log_message('INFO', "跳过接口执行（无接口模板）", step_index)
                response = {
                    'success': True,
                    'message': '跳过接口执行（无接口模板）',
                    'status': 'skipped'
                }
            
            # 3. 执行后置处理（只在接口请求成功后执行，与tabbed_case_editor.py保持一致）
            post_processing_result = {}
            if response.get('success'):
                post_processing = step_data.get('post_processing', {})
                if post_processing:
                    self._log_message('DEBUG', "执行后置处理", step_index)
                    post_processing_result = self._execute_post_processing(post_processing, response, step_index)
            
            # 4. 执行断言（只在接口请求成功后执行，与tabbed_case_editor.py保持一致）
            assertions_result = {}
            if response.get('success'):
                assertions = step_data.get('assertions', {})
                if assertions:
                    self._log_message('DEBUG', "执行断言", step_index)
                    assertions_result = self._execute_assertions(assertions, response, step_index)
                response['assertions_result'] = assertions_result
            
            # 5. 判断步骤状态（与tabbed_case_editor.py保持一致）
            step_success = response.get('success', False) and assertions_result.get('passed', True)
            
            step_end_time = datetime.now()
            execution_time = (step_end_time - step_start_time).total_seconds()
            
            # 6. 更新变量管理器（合并前置、后置处理设置的变量）
            # 合并前置处理设置的变量
            pre_variables = pre_processing_result.get('variables_set', {})
            for var_name, var_value in pre_variables.items():
                self.variable_manager.set_local_variable(var_name, var_value)
            
            # 合并后置处理设置的变量
            post_variables = post_processing_result.get('variables_set', {})
            for var_name, var_value in post_variables.items():
                self.variable_manager.set_local_variable(var_name, var_value)
            
            # 7. 记录步骤执行完成信息（与tabbed_case_editor.py保持一致）
            status = response.get('status', 'success' if step_success else 'failure')
            log_level = "INFO" if status == "success" else "WARNING"
            self._log_message(log_level, f"步骤 {step_order} 执行完成: {status}, 耗时: {execution_time:.2f}秒", step_index)
            
            return {
                'step_id': step_data.get('id'),
                'step_name': step_name,
                'step_order': step_order,
                'status': status,
                'success': step_success,
                'start_time': step_start_time,
                'end_time': step_end_time,
                'execution_time': execution_time,
                'response': response,
                'pre_processing': pre_processing_result,
                'post_processing': post_processing_result,
                'assertions': assertions_result,
                'variables_snapshot': self.variable_manager.get_all_variables()
            }
            
        except Exception as e:
            step_order = step_index + 1  # step_index是从0开始的，需要+1得到实际步骤序号
            error_msg = f"步骤 {step_order} 执行错误: {str(e)}"
            self._log_message('ERROR', error_msg, step_index)
            self._log_message('DEBUG', f"错误详情: {traceback.format_exc()}", step_index)
            return self._create_step_error_result(step_data, step_index, step_start_time, error_msg)
    
    def _get_api_template(self, step_data: Dict[str, Any], step_index: int = None) -> Optional[Dict[str, Any]]:
        """获取API模板数据"""
        api_template_id = step_data.get('api_template_id')
        if not api_template_id:
            return None
            
        try:
            # 使用ApiTemplateService获取API模板数据
            api_template_service = ApiTemplateService()
            result = api_template_service.get_template_by_id(api_template_id)
            return result if result else None
        except Exception as e:
            self._log_message('ERROR', f"获取API模板失败: {str(e)}", step_index)
            return None
    
    def _prepare_request_data(self, api_template: Dict[str, Any], 
                             step_variables: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """准备请求数据，使用变量管理器进行变量替换"""
        # 合并变量
        all_variables = {}
        all_variables.update(self.variable_manager.global_variables)
        all_variables.update(self.variable_manager.local_variables)
        all_variables.update(step_variables)
        
        # 替换变量
        url = self.variable_manager.replace_variables(api_template['url_path'], all_variables)
        headers = self.variable_manager.replace_variables_in_dict(api_template.get('headers', {}), all_variables)
        params = self.variable_manager.replace_variables_in_dict(api_template.get('params', {}), all_variables)
        body = self.variable_manager.replace_variables_in_dict(api_template.get('body', {}), all_variables)
        
        # 构建完整URL
        base_url = self.environment_config.get('base_url', '')
        if base_url:
            full_url = base_url.rstrip('/') + '/' + url.lstrip('/')
        else:
            full_url = url
        
        return {
            'method': api_template['method'],
            'url': full_url,
            'headers': headers,
            'params': params,
            'body': body,
            'timeout': api_template.get('timeout', 30)
        }
    
    def _execute_pre_processing(self, pre_processing: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """执行前置处理"""
        result = {
            'tools_executed': [],
            'variables_set': {},
            'errors': []
        }
        
        if not pre_processing:
            return result
            
        # 计算前置处理工具数量 - 基于实际工具配置统计
        tool_count = 0
        executed_tool_count = 0
        
        # 遍历所有配置项，但只处理有效的工具配置
        for tool_id, tool_config in pre_processing.items():
            # 跳过空配置或无效配置
            if tool_config is None:
                continue
                
            if not isinstance(tool_config, dict):
                continue
                
            # 检查是否为工具配置：必须有type字段
            tool_type = tool_config.get('type')
            if not tool_type:
                continue
                
            enabled = tool_config.get('enabled', True)
            
            # 统计工具数量
            if enabled:
                tool_count += 1
        
        self._log_message('INFO', f"执行步骤 {step_index+1} 的前置处理", step_index)
        self._log_message('INFO', f"前置处理工具数量: {tool_count}", step_index)
        
        # 执行前置处理器中的工具 - 按照优先级字段排序
        sorted_tools = sorted(pre_processing.items(), 
                             key=lambda x: x[1].get('priority', 0))
        
        for tool_id, tool_config in sorted_tools:
            # 跳过空配置或无效配置
            if tool_config is None:
                continue
                
            if not isinstance(tool_config, dict):
                continue
                
            # 检查是否为工具配置：必须有type字段
            tool_type = tool_config.get('type')
            if not tool_type:
                continue
                
            enabled = tool_config.get('enabled', True)
            if not enabled:
                continue
                
            try:
                # 记录前置处理工具情况
                self._log_message('INFO', f"执行前置处理工具: {tool_type}", step_index)
                
                # 执行前置处理工具
                tool_result = self._execute_pre_processing_tool(tool_type, tool_config, step_index)
                if tool_result:
                    result['tools_executed'].append(tool_id)
                    # 合并变量设置
                    if 'variables_set' in tool_result:
                        result['variables_set'].update(tool_result['variables_set'])
                        # 更新变量管理器
                        for var_name, var_value in tool_result['variables_set'].items():
                            self.variable_manager.set_local_variable(var_name, var_value)
                    
                    executed_tool_count += 1
            except Exception as e:
                error_msg = f"执行前置处理工具 {tool_id} 失败: {str(e)}"
                result['errors'].append(error_msg)
                self._log_message('ERROR', error_msg, step_index)
        
        # 处理前置处理器中的变量设置
        variables = pre_processing.get('variables', {})
        if variables:
            self.variable_manager.set_local_variables(variables)
            result['variables_set'].update(variables)
            self._log_message('INFO', f"设置局部变量: {len(variables)} 个", step_index)
        
        self._log_message('INFO', f"前置处理完成，共执行 {executed_tool_count} 个工具", step_index)
        
        return result
    
    def _execute_pre_processing_tool(self, tool_type: str, tool_config: Dict[str, Any], 
                                   step_index: int) -> Dict[str, Any]:
        """执行具体的前置处理工具"""
        result = {
            'variables_set': {},
            'success': True
        }
        
        config = tool_config.get('config', {})
        
        if tool_type == 'http_request':
            # HTTP请求工具
            self._log_message('INFO', f"执行HTTP请求工具", step_index)
            return self._execute_http_request_tool(config, step_index)
        elif tool_type == 'sql_tool':
            # SQL工具
            self._log_message('INFO', f"执行SQL工具", step_index)
            return self._execute_sql_tool(config, step_index)
        else:
            self._log_message('WARNING', f"未知的前置处理工具类型: {tool_type}", step_index)
            result['success'] = False
            result['error'] = f"未知的前置处理工具类型: {tool_type}"
        
        return result
    
    def execute_api_request(self, step: Dict[str, Any], step_index: int, case_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行接口请求（用于定时调度执行）
        
        Args:
            step: 步骤数据，包含api_template_id、variables等
            step_index: 步骤索引
            case_data: 用例数据，包含加解密配置等
            
        Returns:
            HTTP响应结果
        """
        try:
            # 获取接口模板数据
            api_template_id = step.get('api_template_id')
            
            api_template = self._get_api_template(step, step_index)
            if not api_template:
                self._log_message('ERROR', f"接口模板不存在: {api_template_id}", step_index)
                return {
                    'success': False,
                    'error': f'接口模板不存在: {api_template_id}',
                    'status': 'error'
                }

            # 准备请求数据
            step_variables = step.get('variables', {})
            request_data = self._prepare_request_data(api_template, step_variables, step_index)

            # 获取步骤名称
            step_name = step.get('api_name') or step.get('api_template', {}).get('name') or step.get('name', f'步骤{step_index+1}')
            
            # 获取接口模板名称
            api_template_name = api_template.get('name', '未知接口')
            
            # 记录请求日志
            self._log_message('INFO', f"执行步骤 {step_name} 的HTTP请求 [{api_template_name}]: {request_data['method']} {request_data['url']}", step_index)
            self._log_message('DEBUG', f"请求体: {json.dumps(request_data['body'], ensure_ascii=False, indent=2)}", step_index)
            
            try:
                # 构建符合 execute_request 方法要求的 API 数据格式
                api_data = {
                    'method': request_data['method'],
                    'url': request_data['url'],
                    'headers': request_data['headers'],
                    'params': request_data['params'],
                    'body': request_data['body']
                }
                
                # 检查是否启用加解密功能
                enable_encryption = step.get('enable_encryption', False)
                
                # 简化逻辑：步骤卡片开启加解密时，直接使用全局的加解密配置
                # 步骤卡片只控制是否启用加解密，具体的加解密URL使用测试用例的全局配置
                # 优先从case_data获取加解密配置（与CaseExecutionThread保持一致）
                if case_data is None:
                    case_data = {}
                global_enable_encryption = case_data.get('enable_encryption', self.environment_config.get('enable_encryption', False))
                global_encrypt_url = case_data.get('encrypt_url', self.environment_config.get('encrypt_url', ''))
                global_decrypt_url = case_data.get('decrypt_url', self.environment_config.get('decrypt_url', ''))
                
                # 判断是否使用加解密：步骤开启且全局配置完整
                use_encryption = enable_encryption and global_enable_encryption and global_encrypt_url and global_decrypt_url
                
                if use_encryption:
                    # 步骤启用加解密且全局配置完整
                    self._log_message('INFO', "步骤启用加解密功能，使用RequestEngine处理", step_index)
                else:
                    # 不使用加解密的情况
                    if enable_encryption and not (global_encrypt_url and global_decrypt_url):
                        # 步骤启用但全局配置不完整
                        self._log_message('WARNING', "步骤启用加解密但全局配置不完整，使用普通请求", step_index)
                    elif enable_encryption and not global_enable_encryption:
                        # 步骤启用但全局未启用
                        self._log_message('WARNING', "步骤启用加解密但全局未启用，使用普通请求", step_index)
                    else:
                        # 步骤关闭加解密
                        self._log_message('INFO', "步骤关闭加解密功能，使用普通请求", step_index)
                
                # 最终判断是否使用加解密
                if use_encryption:
                    # 使用RequestEngine的加解密功能
                    
                    # 准备请求数据（用于调试信息）
                    request_data = self._prepare_request_data(api_template, step.get('variables', {}), step_index)
                    
                    # 使用RequestEngine的加解密方法，使用全局的加解密URL配置
                    response = self.request_engine.execute_request_with_encryption(
                        api_data=api_data,
                        encrypt_url=global_encrypt_url,
                        decrypt_url=global_decrypt_url,
                        variables=step.get('variables', {})
                    )
                else:
                    # 使用普通的RequestEngine
                    response = self.request_engine.execute_request(api_data, step.get('variables', {}))
                
                if response['success']:                    
                    # 检查是否为加解密请求，优先打印解密后的响应体
                    if response.get('decrypted_body'):
                        try:
                            # 尝试将解密后的响应体解析为JSON，然后重新格式化为JSON字符串
                            decrypted_json = json.loads(response.get('decrypted_body', ''))
                            self._log_message('DEBUG', f"解密后的响应体:{json.dumps(decrypted_json, ensure_ascii=False, indent=2)}", step_index)
                        except:
                            # 如果解析失败，直接打印原始字符串
                            self._log_message('DEBUG', f"解密后的响应体:{response.get('decrypted_body', '')}", step_index)
                    else:
                        # 非加解密请求，尝试将响应体格式化为JSON
                        response_text = response.get('response_text', response.get('text', ''))
                        try:
                            # 尝试解析为JSON并重新格式化
                            response_json = json.loads(response_text)
                            self._log_message('DEBUG', f"响应体: {json.dumps(response_json, ensure_ascii=False, indent=2)}", step_index)
                        except:
                            # 如果解析失败，直接打印原始文本
                            self._log_message('DEBUG', f"响应体: {response_text}", step_index)
                else:
                    # 记录失败请求的详细信息到日志
                    self._log_message('ERROR', f"请求失败: {json.dumps({'error': response.get('error', '未知错误'), 'status_code': response.get('status_code', 0)}, ensure_ascii=False, indent=2)}", step_index)
                    
                    # 检查是否为加解密请求，优先打印解密后的响应体
                    if response.get('decrypted_body'):
                        try:
                            # 尝试将解密后的响应体解析为JSON，然后重新格式化为JSON字符串
                            decrypted_json = json.loads(response.get('decrypted_body', ''))
                            self._log_message('DEBUG', f"解密后的响应体:{json.dumps(decrypted_json, ensure_ascii=False, indent=2)}", step_index)
                        except:
                            # 如果解析失败，直接打印原始字符串
                            self._log_message('DEBUG', f"解密后的响应体:{response.get('decrypted_body', '')}", step_index)
                    else:
                        # 非加解密请求，尝试将响应体格式化为JSON
                        response_text = response.get('response_text', response.get('text', ''))
                        try:
                            # 尝试解析为JSON并重新格式化
                            response_json = json.loads(response_text)
                            self._log_message('DEBUG', f"失败响应体: {json.dumps(response_json, ensure_ascii=False, indent=2)}", step_index)
                        except:
                            # 如果解析失败，直接打印原始文本
                            self._log_message('DEBUG', f"失败响应体: {response_text}", step_index)

                return response

            except Exception as e:
                self._log_message('ERROR', f"HTTP请求异常: {str(e)}", step_index)
                self._log_message('ERROR', f"异常堆栈: {traceback.format_exc()}", step_index)
                return {
                    'success': False,
                    'error': str(e),
                    'status': 'error'
                }
        except Exception as e:
            self._log_message('ERROR', f"执行接口请求外层异常: {str(e)}", step_index)
            self._log_message('ERROR', f"外层异常堆栈: {traceback.format_exc()}", step_index)
            return {
                'success': False,
                'error': str(e),
                'status': 'error'
            }

    def _execute_http_request_tool(self, config: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """执行HTTP请求工具"""
        result = {
            'variables_set': {},
            'success': True
        }
        
        try:
            # 获取请求配置
            name = config.get('name', 'HTTP请求工具')
            method = config.get('method', 'GET')
            url = config.get('url', '')
            headers = config.get('headers', {})
            body = config.get('body', {})
            timeout = config.get('timeout', 30)
            # 优先从variables字段读取变量提取器，如果没有则从extractors字段读取
            extractors = config.get('variables', config.get('extractors', {}))
            
            self._log_message('INFO', f"HTTP请求工具配置 - 名称: {name}, 方法: {method}, URL: {url}, 超时: {timeout}", step_index)
            self._log_message('DEBUG', f"HTTP请求工具配置 - 请求体: {body}", step_index)
            self._log_message('DEBUG', f"HTTP请求工具配置 - 提取器: {extractors}", step_index)
            
            if not url:
                error_msg = "HTTP请求工具配置错误: URL不能为空"
                self._log_message('ERROR', error_msg, step_index)
                result['success'] = False
                result['error'] = error_msg
                return result
            
            # 替换变量
            all_variables = self.variable_manager.get_all_variables()
            
            self._log_message('DEBUG', f"变量替换前 - URL: {url}", step_index)
            self._log_message('DEBUG', f"可用变量: {all_variables}", step_index)
            
            url = self.variable_manager.replace_variables(url, all_variables)
            headers = self.variable_manager.replace_variables_in_dict(headers, all_variables)
            body = self.variable_manager.replace_variables_in_dict(body, all_variables)
            
            self._log_message('INFO', f"变量替换后 - URL: {url}", step_index)
            self._log_message('DEBUG', f"变量替换后 - 请求头: {headers}", step_index)
            self._log_message('DEBUG', f"变量替换后 - 请求体: {body}", step_index)
            
            # 记录请求日志
            self._log_message('INFO', f"前置处理器HTTP请求工具[{name}]: {method} {url}", step_index)
            
            # 执行请求
            request_data = {
                'method': method,
                'url': url,
                'headers': headers,
                'body': body,
                'timeout': timeout
            }
            
            self._log_message('DEBUG', f"发送请求数据: {request_data}", step_index)
            
            response = self.request_engine.execute_request(request_data)
                        
            if response.get('success'):
                # 请求成功，处理响应
                response_data = response.get('response_data', response.get('body', {}))
                status_code = response.get('status_code', 0)
                
                self._log_message('INFO', f"前置处理器HTTP请求工具[{name}]成功: 状态码 {status_code}", step_index)
                self._log_message('DEBUG', f"响应数据: {response_data}", step_index)
                
                # 提取变量
                if extractors:
                    self._log_message('INFO', f"开始提取变量，提取器数量: {len(extractors)}", step_index)
                    for var_name, json_path in extractors.items():
                        try:
                            self._log_message('INFO', f"提取变量 {var_name}，JSON路径: {json_path}", step_index)
                            # 从响应中提取数据
                            value = self._simple_json_path_extract(response_data, json_path)
                            if value is not None:
                                # 将提取的变量保存到变量管理器
                                result['variables_set'][var_name] = value
                                self._log_message('INFO', f"提取变量成功: {var_name} = {value}", step_index)
                                
                                # 立即更新变量管理器（与后置处理器保持一致）
                                self.variable_manager.set_local_variable(var_name, value)
                                
                                # 打印局部变量状态
                                self._log_message('DEBUG', f"变量管理器状态 - 局部变量: {self.variable_manager.local_variables}", step_index)
                                
                                # 调试模式下打印详细的变量管理器状态
                                if self.debug_mode:
                                    self._log_message('DEBUG', f"变量管理器状态 - 全局变量: {self.variable_manager.global_variables}", step_index)
                            else:
                                self._log_message('WARNING', f"提取变量失败: {var_name}，JSON路径 {json_path} 未找到数据", step_index)
                                # 调试：检查响应数据结构
                                self._log_message('DEBUG', f"响应数据结构: {response_data}", step_index)
                                self._log_message('DEBUG', f"尝试提取路径 {json_path} 失败，检查响应数据格式", step_index)
                        except Exception as e:
                            self._log_message('ERROR', f"提取变量异常: {var_name}，错误: {str(e)}", step_index)
                else:
                    self._log_message('DEBUG', "无变量需要提取", step_index)
            else:
                # 请求失败
                error_msg = response.get('error', '未知错误')
                self._log_message('ERROR', f"前置处理器HTTP请求失败: {error_msg}", step_index)
                result['success'] = False
                result['error'] = error_msg
                
        except Exception as e:
            self._log_message('ERROR', f"执行HTTP请求工具失败: {str(e)}", step_index)
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _execute_sql_tool(self, config: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """执行SQL工具"""
        result = {
            'variables_set': {},
            'success': True
        }
        
        try:
            # 获取SQL工具配置
            name = config.get('name', 'SQL工具')
            database_config = config.get('database', {})
            sql = config.get('sql', '')
            output_fields = config.get('output_fields', [])
            
            self._log_message('INFO', f"SQL工具配置 - 名称: {name}", step_index)
            self._log_message('DEBUG', f"SQL工具配置 - SQL语句: {sql}", step_index)
            self._log_message('DEBUG', f"SQL工具配置 - 输出字段: {output_fields}", step_index)
            
            if not sql:
                error_msg = "SQL工具配置错误: SQL语句不能为空"
                self._log_message('ERROR', error_msg, step_index)
                result['success'] = False
                result['error'] = error_msg
                return result
            
            if not database_config:
                error_msg = "SQL工具配置错误: 数据库配置不能为空"
                self._log_message('ERROR', error_msg, step_index)
                result['success'] = False
                result['error'] = error_msg
                return result
            
            # 获取变量池
            all_variables = self.variable_manager.get_all_variables()
            
            self._log_message('DEBUG', f"变量替换前 - SQL: {sql}", step_index)
            self._log_message('DEBUG', f"可用变量: {all_variables}", step_index)
            
            # 预处理SQL：直接替换变量为实际值
            def replace_variable_value(match):
                var_name = match.group(1)  # 变量名
                # 从变量池中获取变量值
                var_value = all_variables.get(f"${{{var_name}}}", '')  # 使用完整的${variable}格式查找
                if var_value is None:
                    var_value = ''
                # 对字符串值添加单引号，其他类型直接使用
                if isinstance(var_value, str):
                    # 转义单引号以防止SQL注入
                    var_value = var_value.replace("'", "''")
                    return f"'{var_value}'"
                else:
                    return str(var_value)
            
            # 替换变量为实际值
            processed_sql = re.sub(r"'\$\{(\w+)\}'", replace_variable_value, sql)
            
            self._log_message('DEBUG', f"预处理后 - SQL: {processed_sql}", step_index)
            
            # 记录SQL执行日志
            self._log_message('INFO', f"前置处理器SQL执行: {processed_sql}", step_index)
            
            # 执行SQL查询
            loop = QEventLoop()
            sql_result = {'success': False, 'error': '未执行'}
            
            def on_finished(query_name, message, result_data):
                nonlocal sql_result
                sql_result = {'success': True, 'message': message, 'data': result_data}
                loop.quit()
            
            def on_error(query_name, error_message):
                nonlocal sql_result
                sql_result = {'success': False, 'error': error_message}
                loop.quit()
            
            # 创建SQLWorker并执行
            sql_worker = SQLWorker("pre_processing_sql", database_config, processed_sql, all_variables)
            sql_worker.finished.connect(on_finished)
            sql_worker.error.connect(on_error)
            sql_worker.start()
            
            # 等待信号完成
            loop.exec_()
            
            # 断开信号连接
            sql_worker.finished.disconnect(on_finished)
            sql_worker.error.disconnect(on_error)
            
            if sql_result['success']:
                # SQL执行成功
                data = sql_result.get('data', [])
                self._log_message('INFO', f"前置处理器SQL工具[{name}]执行成功: 返回 {len(data)} 行数据", step_index)
                
                # 提取变量到变量管理器
                if output_fields and data:
                    self._log_message('INFO', f"开始提取变量，输出字段数量: {len(output_fields)}", step_index)
                    
                    # 获取第一行数据（假设只取第一行结果）
                    first_row = data[0] if data else {}
                    
                    for field_config in output_fields:
                        field_name = field_config.get('field', '')
                        if field_name and field_name in first_row:
                            value = first_row[field_name]
                            # 将提取的变量保存到变量管理器
                            result['variables_set'][field_name] = value
                            self._log_message('INFO', f"提取变量成功: {field_name} = {value}", step_index)
                            
                            # 立即更新变量管理器（与后置处理器保持一致）
                            self.variable_manager.set_local_variable(field_name, value)
                            
                            # 打印局部变量状态
                            self._log_message('DEBUG', f"SQL工具[{name}]提取变量后局部变量状态: {self.variable_manager.local_variables}", step_index)
                        else:
                            self._log_message('WARNING', f"提取变量失败: 字段 {field_name} 不存在或为空", step_index)
                else:
                    self._log_message('DEBUG', "无输出字段或查询结果为空，跳过变量提取", step_index)
            else:
                # SQL执行失败
                error_msg = sql_result.get('error', '未知错误')
                self._log_message('ERROR', f"前置处理器SQL执行失败: {error_msg}", step_index)
                result['success'] = False
                result['error'] = error_msg
                
        except Exception as e:
            self._log_message('ERROR', f"执行SQL工具失败: {str(e)}", step_index)
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _execute_post_processing(self, post_processing: Dict[str, Any], 
                                response_data: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """执行后置处理"""
        result = {
            'tools_executed': [],
            'variables_set': {},
            'errors': []
        }
        
        if not post_processing:
            return result
            
        self._log_message('INFO', f"执行步骤 {step_index+1} 的后置处理", step_index)
        
        # 按照优先级字段对后置处理工具进行排序（与前端保持一致）
        sorted_tools = sorted(post_processing.items(), 
                             key=lambda x: x[1].get('priority', 0))
        
        # 执行后置处理器中的工具
        for tool_id, tool_config in sorted_tools:
            if not isinstance(tool_config, dict):
                continue
                
            tool_type = tool_config.get('type')
            enabled = tool_config.get('enabled', True)
            
            if not tool_type or not enabled:
                continue
                
            try:
                # 执行后置处理工具
                tool_result = self._execute_post_processing_tool(tool_type, tool_config, response_data, step_index)
                if tool_result:
                    result['tools_executed'].append(tool_id)
                    # 合并变量设置
                    if 'variables_set' in tool_result:
                        result['variables_set'].update(tool_result['variables_set'])
                        # 更新变量管理器
                        for var_name, var_value in tool_result['variables_set'].items():
                            self.variable_manager.set_local_variable(var_name, var_value)
            except Exception as e:
                error_msg = f"执行后置处理工具 {tool_id} 失败: {str(e)}"
                result['errors'].append(error_msg)
                self._log_message('ERROR', error_msg, step_index)
        
        return result
    
    def _execute_post_processing_tool(self, tool_type: str, tool_config: Dict[str, Any], 
                                     response_data: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """执行具体的后置处理工具（与tabbed_case_editor.py保持一致）"""
        result = {
            'variables_set': {},
            'success': True
        }
        
        config = tool_config.get('config', {})
        
        if tool_type == 'parameter_extraction':
            # 参数提取器（与tabbed_case_editor.py保持一致）
            self._log_message('INFO', f"执行参数提取器", step_index)
            return self._execute_parameter_extraction(config, response_data, step_index)
        elif tool_type == 'parameter_extractor':
            # 兼容性支持（旧版本工具类型）
            self._log_message('INFO', f"执行参数提取器（兼容模式）", step_index)
            return self._execute_parameter_extractor(config, response_data, step_index)
        else:
            self._log_message('WARNING', f"未知的后置处理工具类型: {tool_type}", step_index)
            result['success'] = False
            result['error'] = f"未知的后置处理工具类型: {tool_type}"
        
        return result
    
    def _execute_parameter_extraction(self, config: Dict[str, Any], response_data: Dict[str, Any], 
                                    step_index: int) -> Dict[str, Any]:
        """执行参数提取器（与tabbed_case_editor.py保持一致）"""
        result = {
            'variables_set': {},
            'success': True
        }
        
        try:
            # 获取参数提取器配置（使用extractions字段）
            extractions = config.get('extractions', [])
            
            if not extractions:
                self._log_message('WARNING', "参数提取器配置为空", step_index)
                return result
            
            self._log_message('INFO', f"开始提取参数，提取器数量: {len(extractions)}", step_index)
            
            # 优先使用解密后的响应体（对于加解密请求）
            decrypted_body = response_data.get('decrypted_body', '')
            if decrypted_body:
                # 如果有解密后的响应体，优先使用它
                try:
                    import json
                    response_data_for_extraction = json.loads(decrypted_body)
                    self._log_message('DEBUG', "使用解密后的响应体进行参数提取", step_index)
                except:
                    # 如果解析失败，使用原始响应数据
                    response_data_for_extraction = response_data.get('response_data', {})
                    self._log_message('WARNING', "解密后的响应体解析失败，使用原始响应数据", step_index)
            else:
                # 如果没有解密后的响应体，使用原始响应数据
                response_data_for_extraction = response_data.get('response_data', {})
            
            # 处理每个提取器
            for extraction in extractions:
                try:
                    variable_name = extraction.get('variable_name')
                    json_path = extraction.get('json_path')
                    
                    if not variable_name or not json_path:
                        self._log_message('WARNING', "参数提取器配置不完整，跳过", step_index)
                        continue
                    
                    self._log_message('INFO', f"提取参数 {variable_name}，JSON路径: {json_path}", step_index)
                    
                    # 从响应体中提取数据
                    value = self._simple_json_path_extract(response_data_for_extraction, json_path)
                    
                    if value is not None:
                        # 将提取的变量保存到变量管理器
                        result['variables_set'][variable_name] = value
                        # 立即更新变量管理器，确保后续日志能正确显示变量状态
                        self.variable_manager.set_local_variable(variable_name, value)
                        self._log_message('SUCCESS', f"提取参数成功: {variable_name} = {value}", step_index)
                        
                        # 打印局部变量状态
                        self._log_message('DEBUG', f"参数提取后局部变量状态: {self.variable_manager.local_variables}", step_index)
                    else:
                        self._log_message('WARNING', f"提取参数失败: {variable_name}，JSON路径 {json_path} 未找到数据", step_index)
                        
                except Exception as e:
                    self._log_message('ERROR', f"提取参数异常: {variable_name}，错误: {str(e)}", step_index)
                    
        except Exception as e:
            self._log_message('ERROR', f"执行参数提取器失败: {str(e)}", step_index)
            result['success'] = False
            result['error'] = str(e)
        
        return result

    def _execute_parameter_extractor(self, config: Dict[str, Any], response_data: Dict[str, Any], 
                                   step_index: int) -> Dict[str, Any]:
        """执行参数提取器（兼容性支持）"""
        result = {
            'variables_set': {},
            'success': True
        }
        
        try:
            # 获取参数提取器配置
            extractors = config.get('extractors', {})
            
            if not extractors:
                self._log_message('WARNING', "参数提取器配置为空", step_index)
                return result
            
            self._log_message('INFO', f"开始提取参数，提取器数量: {len(extractors)}", step_index)
            
            # 优先使用解密后的响应体（对于加解密请求）
            decrypted_body = response_data.get('decrypted_body', '')
            if decrypted_body:
                # 如果有解密后的响应体，优先使用它
                try:
                    import json
                    response_data_for_extraction = json.loads(decrypted_body)
                    self._log_message('DEBUG', "使用解密后的响应体进行参数提取", step_index)
                except:
                    # 如果解析失败，使用原始响应数据
                    response_data_for_extraction = response_data.get('response_data', {})
                    self._log_message('WARNING', "解密后的响应体解析失败，使用原始响应数据", step_index)
            else:
                # 如果没有解密后的响应体，使用原始响应数据
                response_data_for_extraction = response_data.get('response_data', {})
            
            # 处理每个提取器
            for var_name, extractor_config in extractors.items():
                try:
                    source = extractor_config.get('source', 'body')
                    json_path = extractor_config.get('json_path', '')
                    
                    self._log_message('INFO', f"提取参数 {var_name}，来源: {source}，JSON路径: {json_path}", step_index)
                    
                    if source == 'body':
                        # 从响应体提取
                        if json_path:
                            value = self._simple_json_path_extract(response_data_for_extraction, json_path)
                        else:
                            # 如果没有指定json_path，则使用变量名作为key
                            value = response_data_for_extraction.get(var_name)
                    elif source == 'headers':
                        # 从响应头提取
                        headers = response_data.get('response_headers', response_data.get('headers', {}))
                        value = headers.get(var_name)
                    elif source == 'status_code':
                        # 提取状态码
                        value = response_data.get('status_code')
                    else:
                        self._log_message('WARNING', f"未知的提取来源: {source}", step_index)
                        continue
                    
                    if value is not None:
                        # 将提取的变量保存到变量管理器
                        result['variables_set'][var_name] = value
                        # 立即更新变量管理器，确保后续日志能正确显示变量状态
                        self.variable_manager.set_local_variable(var_name, value)
                        self._log_message('SUCCESS', f"提取参数成功: {var_name} = {value}", step_index)
                        
                        # 打印局部变量状态
                        self._log_message('DEBUG', f"参数提取后局部变量状态: {self.variable_manager.local_variables}", step_index)
                    else:
                        self._log_message('WARNING', f"提取参数失败: {var_name}，未找到数据", step_index)
                        
                except Exception as e:
                    self._log_message('ERROR', f"提取参数异常: {var_name}，错误: {str(e)}", step_index)
                    
        except Exception as e:
            self._log_message('ERROR', f"执行参数提取器失败: {str(e)}", step_index)
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _execute_response_extractor(self, config: Dict[str, Any], response_data: Dict[str, Any], 
                                  step_index: int) -> Dict[str, Any]:
        """执行响应数据提取器"""
        result = {
            'variables_set': {},
            'success': True
        }
        
        try:
            # 获取响应数据提取器配置
            variables = config.get('variables', {})
            
            if not variables:
                self._log_message('WARNING', "响应数据提取器配置为空", step_index)
                return result
            
            self._log_message('INFO', f"开始提取响应数据，变量数量: {len(variables)}", step_index)
            
            # 优先使用解密后的响应体（对于加解密请求）
            decrypted_body = response_data.get('decrypted_body', '')
            if decrypted_body:
                # 如果有解密后的响应体，优先使用它
                try:
                    import json
                    response_data_for_extraction = json.loads(decrypted_body)
                    self._log_message('DEBUG', "使用解密后的响应体进行参数提取", step_index)
                except:
                    # 如果解析失败，使用原始响应数据
                    response_data_for_extraction = response_data.get('response_data', {})
                    self._log_message('WARNING', "解密后的响应体解析失败，使用原始响应数据", step_index)
            else:
                # 如果没有解密后的响应体，使用原始响应数据
                response_data_for_extraction = response_data.get('response_data', {})
            
            # 处理每个变量提取
            for var_name, json_path in variables.items():
                try:
                    self._log_message('INFO', f"提取变量 {var_name}，JSON路径: {json_path}", step_index)
                    
                    # 从响应数据中提取值
                    value = self._simple_json_path_extract(response_data_for_extraction, json_path)
                    
                    if value is not None:
                        # 将提取的变量保存到变量管理器
                        result['variables_set'][var_name] = value
                        # 立即更新变量管理器，确保后续日志能正确显示变量状态
                        self.variable_manager.set_local_variable(var_name, value)
                        self._log_message('SUCCESS', f"提取变量成功: {var_name} = {value}", step_index)
                        
                        # 打印局部变量状态
                        self._log_message('DEBUG', f"响应数据提取后局部变量状态: {self.variable_manager.local_variables}", step_index)
                    else:
                        self._log_message('WARNING', f"提取变量失败: {var_name}，JSON路径 {json_path} 未找到数据", step_index)
                        
                except Exception as e:
                    self._log_message('ERROR', f"提取变量异常: {var_name}，错误: {str(e)}", step_index)
                    
        except Exception as e:
            self._log_message('ERROR', f"执行响应数据提取器失败: {str(e)}", step_index)
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _execute_assertions(self, assertions: Dict[str, Any], 
                           response_data: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """执行断言（与tabbed_case_editor.py保持一致）"""
        if not assertions:
            self._log_message('DEBUG', f"步骤 {step_index+1}: 断言: 无配置", step_index)
            return {}
            
        self._log_message('INFO', f"执行步骤 {step_index+1} 的断言", step_index)
        self._log_message('INFO', f"断言数量: {len(assertions)}", step_index)
        
        results = {}
        
        # 兼容不同的响应数据结构
        # 1. 从execute_api_request返回的数据结构
        response_text = response_data.get('response_text', response_data.get('text', ''))
        response_headers = response_data.get('response_headers', response_data.get('headers', {}))
        response_time = response_data.get('response_time', response_data.get('elapsed', 0))
        status_code = response_data.get('status_code', 0)
        
        # 优先使用解密后的响应体（对于加解密请求）
        decrypted_body = response_data.get('decrypted_body', '')
        if decrypted_body:
            # 如果有解密后的响应体，优先使用它
            response_text = decrypted_body
            # 尝试将解密后的响应体解析为JSON
            try:
                response_data['response_data'] = json.loads(decrypted_body)
            except:
                # 如果解析失败，保持原样
                pass
        elif isinstance(response_data.get('response_data', ''), str) and response_data.get('response_data', '').strip():
            # 如果没有解密后的响应体，但response_data是字符串，尝试解析为JSON
            try:
                response_data['response_data'] = json.loads(response_data['response_data'])
            except:
                # 如果解析失败，保持原样
                pass

        # 按照优先级字段对断言工具进行排序（与前端保持一致）
        sorted_assertions = sorted(assertions.items(), 
                                  key=lambda x: x[1].get('priority', 0))
        
        for assertion_name, assertion_config in sorted_assertions:
            try:
                # 兼容新旧两种断言配置格式
                # 新格式: {'type': 'assertion_type', 'config': {...}}
                # 旧格式: {'name': '断言名称', 'assertions': [...]}
                
                # 判断配置格式
                if 'type' in assertion_config:
                    # 新格式
                    assertion_type = assertion_config.get('type')
                    config = assertion_config.get('config', {})
                    
                    # 检查断言是否启用
                    if not config.get('enabled', True):
                        self._log_message('DEBUG', f"断言 {assertion_name}: 已禁用，跳过执行", step_index)
                        results[assertion_name] = True  # 禁用的断言视为通过
                        continue
                else:
                    # 旧格式 - 转换为新格式
                    config = assertion_config
                    
                    # 从断言配置中推断类型
                    assertions_list = config.get('assertions', [])
                    if assertions_list:
                        first_assertion = assertions_list[0]
                        symbol = first_assertion.get('symbol', 'equal')
                        
                        # 符号到类型的映射
                        symbol_to_type_map = {
                            'equal': 'equal',
                            'not_equal': 'not_equal',
                            'contains': 'contains', 
                            'not_contains': 'not_contains',
                            'greater': 'greater',
                            'less': 'less',
                            'greater_equal': 'greater_equal',
                            'less_equal': 'less_equal'
                        }
                        
                        assertion_type = symbol_to_type_map.get(symbol, 'equal')
                        
                        # 为旧格式设置默认配置
                        if assertion_type == 'response_time' and assertions_list:
                            config['time_comparison'] = symbol
                            config['time_value'] = float(assertions_list[0].get('expected')) if assertions_list[0].get('expected') else None
                        elif assertions_list:
                            config['expected'] = assertions_list[0].get('expected')
                            config['ignore_case'] = False
                    else:
                        assertion_type = 'equal'  # 默认类型
                
                # 执行断言
                assertion_result = self._execute_single_assertion_new(assertion_type, config, response_data, response_text, response_headers, response_time, status_code, assertion_name, step_index)
                results[assertion_name] = assertion_result
                
                # 记录详细的断言结果日志
                log_level = "info" if assertion_result else "error"
                self._log_message(log_level.upper(), 
                          f"断言 {assertion_name}: 执行结果 {'通过' if assertion_result else '失败'}", step_index)
                
            except Exception as e:
                results[assertion_name] = False
                self._log_message('ERROR', f"断言 {assertion_name} 执行错误: {str(e)}", step_index)

        # 检查所有断言是否通过
        passed_count = sum(1 for result in results.values() if result)
        all_passed = all(results.values())
        
        self._log_message('INFO', f"断言结果: {passed_count}/{len(assertions)} 通过", step_index)
        self._log_message('INFO', "断言执行结束", step_index)
        
        return {
            'passed': all_passed,
            'passed_count': passed_count,
            'total_count': len(assertions),
            'results': results
        }
    
    def _execute_single_assertion_new(self, assertion_type: str, config: Dict[str, Any], 
                                     response_data: Dict[str, Any], response_text: str,
                                     response_headers: Dict[str, Any], response_time: float,
                                     status_code: int, assertion_name: str, step_index: int) -> bool:
        """执行单个断言（新格式，与tabbed_case_editor.py保持一致）"""
        
        # 创建步骤结果字典，用于变量替换
        step_result = {
            'response_data': response_data,
            'response_text': response_text,
            'response_headers': response_headers,
            'response_time': response_time,
            'status_code': status_code
        }
        
        if assertion_type == 'equal':
            expected = config.get('expected')
            # 变量替换：支持${变量名}格式（如果期望值不为None）
            if expected is not None:
                expected = self.replace_variables(str(expected), step_result, step_index)
            actual = response_text
            ignore_case = config.get('ignore_case', False)
            
            if ignore_case:
                result = (expected or '').lower() == (actual or '').lower()
            else:
                result = expected == actual
            
            # 记录详细的断言结果日志
            expected_display = expected if expected is not None else "None"
            actual_display = actual if actual is not None else "None"
            self._log_message('INFO', f"断言 {assertion_name}: 期望值='{expected_display}' 实际值='{actual_display}' 比较结果:{'==' if result else '!='}", step_index)
            
            return result
                
        elif assertion_type == 'not_equal':
            expected = config.get('expected')
            # 变量替换：支持${变量名}格式（如果期望值不为None）
            if expected is not None:
                expected = self.replace_variables(str(expected), step_result, step_index)
            actual = response_text
            ignore_case = config.get('ignore_case', False)
            
            if ignore_case:
                result = (expected or '').lower() != (actual or '').lower()
            else:
                result = expected != actual
            
            # 记录详细的断言结果日志
            expected_display = expected if expected is not None else "None"
            actual_display = actual if actual is not None else "None"
            self._log_message('INFO', f"断言 {assertion_name}: 期望值='{expected_display}' 实际值='{actual_display}' 比较结果:{'!=' if result else '=='}", step_index)
            
            return result
                
        elif assertion_type == 'contains':
            expected = config.get('expected')
            # 变量替换：支持${变量名}格式（如果期望值不为None）
            if expected is not None:
                expected = self.replace_variables(str(expected), step_result, step_index)
            actual = response_text
            ignore_case = config.get('ignore_case', False)
            
            if ignore_case:
                result = (expected or '') in (actual or '').lower()
            else:
                result = (expected or '') in (actual or '')
            
            # 记录详细的断言结果日志
            expected_display = expected if expected is not None else "None"
            actual_display = actual if actual is not None else "None"
            self._log_message('INFO', f"断言 {assertion_name}: 期望包含='{expected_display}' 实际响应='{actual_display}' 结果:{result}", step_index)
            
            return result
                
        elif assertion_type == 'not_contains':
            expected = config.get('expected')
            # 变量替换：支持${变量名}格式（如果期望值不为None）
            if expected is not None:
                expected = self.replace_variables(str(expected), step_result, step_index)
            actual = response_text
            ignore_case = config.get('ignore_case', False)
            
            if ignore_case:
                result = (expected or '') not in (actual or '').lower()
            else:
                result = (expected or '') not in (actual or '')
            
            # 记录详细的断言结果日志
            expected_display = expected if expected is not None else "None"
            actual_display = actual if actual is not None else "None"
            self._log_message('INFO', f"断言 {assertion_name}: 期望不包含='{expected_display}' 实际响应='{actual_display}' 结果:{result}", step_index)
            
            return result
                
        elif assertion_type == 'regex':
            pattern = config.get('regex', '')
            # 变量替换：支持${变量名}格式（如果期望值不为None）
            if pattern is not None:
                pattern = self.replace_variables(str(pattern), step_result, step_index)
            actual = response_text
            ignore_case = config.get('ignore_case', False)
            
            import re
            flags = re.IGNORECASE if ignore_case else 0
            try:
                match = re.search(pattern, actual, flags)
                result = match is not None
                
                # 记录详细的断言结果日志
                self._log_message('INFO', f"断言 {assertion_name}: 正则匹配 '{pattern}' -> {result}", step_index)
                
                return result
            except Exception as e:
                self._log_message('ERROR', f"断言 {assertion_name}: 正则表达式错误: {str(e)}", step_index)
                return False
                
        elif assertion_type == 'status_code':
            expected = config.get('expected')
            # 变量替换：支持${变量名}格式（如果期望值不为None）
            if expected is not None:
                expected = self.replace_variables(str(expected), step_result, step_index)
            actual = status_code
            result = str(expected) == str(actual)
            
            # 记录详细的断言结果日志
            expected_display = expected if expected is not None else "None"
            actual_display = actual if actual is not None else "None"
            self._log_message('INFO', f"断言 {assertion_name}: 状态码 {actual_display} {'==' if result else '!='} {expected_display}", step_index)
            
            return result
            
        elif assertion_type == 'json_path':
            path = config.get('path', '')
            expected = config.get('expected')
            # 变量替换：支持${变量名}格式（如果期望值不为None）
            if expected is not None:
                expected = self.replace_variables(str(expected), step_result, step_index)
            actual = self._simple_json_path_extract(response_data.get('response_data', {}), path)
            result = expected == actual
            
            # 记录详细的断言结果日志
            expected_display = expected if expected is not None else "None"
            actual_display = actual if actual is not None else "None"
            self._log_message('INFO', f"断言 {assertion_name}: {path} = {actual_display} {'==' if result else '!='} {expected_display}", step_index)
            
            return result
            
        elif assertion_type == 'response_time':
            comparison = config.get('time_comparison', 'less')
            expected_value = config.get('time_value')
            # 变量替换：支持${变量名}格式（如果期望值不为None）
            if expected_value is not None:
                expected_value = self.replace_variables(str(expected_value), step_result, step_index)
            actual = response_time
            
            # 如果期望值为None，则使用0作为默认值进行比较
            expected_value_num = float(expected_value) if expected_value is not None else 0
            
            if comparison == 'less':
                result = actual < expected_value_num
            elif comparison == 'equal':
                result = abs(actual - expected_value_num) < 0.001  # 浮点数比较容差
            elif comparison == 'greater':
                result = actual > expected_value_num
            else:
                result = False
            
            # 记录详细的断言结果日志
            comparison_symbol = {'less': '<', 'equal': '==', 'greater': '>'}[comparison]
            expected_display = expected_value if expected_value is not None else "None"
            self._log_message('INFO', f"断言 {assertion_name}: 响应时间 {actual:.3f}s {comparison_symbol} {expected_display}s -> {result}", step_index)
            
            return result
                
        elif assertion_type == 'header_exists':
            header_name = config.get('header_name', '')
            # 变量替换：支持${变量名}格式（如果期望值不为None）
            if header_name is not None:
                header_name = self.replace_variables(str(header_name), step_result, step_index)
            actual_headers = {k.lower(): v for k, v in response_headers.items()}
            result = header_name.lower() in actual_headers
            
            # 记录详细的断言结果日志
            self._log_message('INFO', f"断言 {assertion_name}: 响应头包含 '{header_name}' -> {result}", step_index)
            
            return result
            
        elif assertion_type == 'json_schema':
            # 这里需要实现JSON Schema验证
            # 由于JSON Schema验证比较复杂，这里先简单返回True
            # 实际项目中应该使用jsonschema库进行验证
            result = True  # 暂时返回True
            
            # 记录详细的断言结果日志
            self._log_message('INFO', f"断言 {assertion_name}: JSON Schema验证 -> {result}", step_index)
            
            return result
            
        elif assertion_type == 'field_path_assertion':
            # 新的字段路径提取断言，支持字段路径提取和变量替换
            assertions_list = config.get('assertions', [])
            
            # 检查断言是否启用
            if not config.get('enabled', True):
                self._log_message('INFO', f"断言 {assertion_name}: 断言已禁用，视为通过", step_index)
                return True  # 禁用的断言视为通过
            
            # 执行所有断言行
            assertion_results = []
            for i, assertion in enumerate(assertions_list):
                field = assertion.get('field', '')
                symbol = assertion.get('symbol', 'equal')
                expected = assertion.get('expected')
                
                # 变量替换：支持${变量名}格式（如果期望值不为None）
                if expected is not None:
                    expected = self.replace_variables(str(expected), step_result, step_index)
                
                # 提取实际值：支持字段路径提取
                actual = self._extract_field_value(response_data, field)
                
                # 根据符号执行比较
                result = self._execute_comparison_new(actual, expected, symbol)
                assertion_results.append(result)
                
                # 记录详细的断言结果日志
                expected_display = expected if expected is not None else "None"
                actual_display = actual if actual is not None else "None"
                self._log_message('INFO', f"断言 {assertion_name} 第{i+1}行: {field} {symbol} {expected_display} -> {result} (实际值: {actual_display})", step_index)
            
            # 所有断言行都必须通过
            final_result = all(assertion_results)
            self._log_message('INFO', f"断言 {assertion_name}: 所有断言行执行完成，最终结果: {final_result}", step_index)
            
            return final_result
            
        elif assertion_type in ['greater', 'less', 'greater_equal', 'less_equal']:
            # 数值比较断言
            expected = config.get('expected')
            # 变量替换：支持${变量名}格式（如果期望值不为None）
            if expected is not None:
                expected = self.replace_variables(str(expected), step_result, step_index)
            
            # 从断言配置中获取字段名，用于从响应数据中提取实际值
            assertions_list = config.get('assertions', [])
            field_name = 'response_time'  # 默认字段
            if assertions_list:
                first_assertion = assertions_list[0]
                field_name = first_assertion.get('field', 'response_time')
            
            # 根据字段名从响应数据中提取实际值
            actual = self._extract_field_value(response_data, field_name)
            
            # 转换为数值进行比较
            try:
                expected_num = float(expected) if expected is not None else 0
                actual_num = float(actual) if actual is not None else 0
                
                if assertion_type == 'greater':
                    result = actual_num > expected_num
                elif assertion_type == 'less':
                    result = actual_num < expected_num
                elif assertion_type == 'greater_equal':
                    result = actual_num >= expected_num
                elif assertion_type == 'less_equal':
                    result = actual_num <= expected_num
                else:
                    result = False
                
                # 记录详细的断言结果日志
                expected_display = expected if expected is not None else "None"
                actual_display = actual if actual is not None else "None"
                self._log_message('INFO', f"断言 {assertion_name}: {field_name} {assertion_type} {expected_display} -> {result} (实际值: {actual_display})", step_index)
                
                return result
                    
            except (ValueError, TypeError) as e:
                self._log_message('ERROR', f"断言 {assertion_name}: 数值转换错误 - 期望值: {expected}, 实际值: {actual}", step_index)
                return False

        else:
            self._log_message('WARNING', f"未知断言类型: {assertion_type}", step_index)
            return False
    
    def _execute_single_assertion(self, assertion_config: Dict[str, Any], 
                                 response_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个断言（兼容旧格式）"""
        # 获取断言配置
        field_path = assertion_config.get('field', '')
        expected_value = assertion_config.get('expected', '')
        comparison_symbol = assertion_config.get('symbol', 'equal')
        
        # 提取实际值
        actual_value = self._extract_field_value(response_data, field_path)
        
        # 执行比较
        passed = self._execute_comparison(actual_value, expected_value, comparison_symbol)
        
        return {
            'passed': passed,
            'actual': actual_value,
            'expected': expected_value,
            'symbol': comparison_symbol,
            'field': field_path
        }
    
    def _extract_field_value(self, response_data: Dict[str, Any], field_path: str) -> Any:
        """从响应数据中提取字段值（与tabbed_case_editor.py保持一致）"""
        if not field_path:
            return ''
        
        # 检查字段路径是否为变量格式（如${msg}），如果是则从变量管理器中获取
        if field_path.startswith('${') and field_path.endswith('}'):
            var_name = field_path[2:-1]  # 提取变量名
            
            # 首先尝试从变量管理器中获取变量
            if hasattr(self, 'variable_manager'):
                # 尝试从局部变量中获取
                if var_name in self.variable_manager.local_variables:
                    var_value = self.variable_manager.local_variables[var_name]
                    return str(var_value) if var_value is not None else None
                # 尝试从全局变量中获取
                elif var_name in self.variable_manager.global_variables:
                    var_value = self.variable_manager.global_variables[var_name]
                    return str(var_value) if var_value is not None else None
            
            # 如果变量管理器中没找到，再从响应数据中获取
            if response_data:
                var_value = response_data.get(var_name, None)
                return str(var_value) if var_value is not None else None
            
            return None  # 变量不存在
        
        # 优先使用解密后的响应体（对于加解密请求）
        decrypted_body = response_data.get('decrypted_body', '')
        
        if decrypted_body:
            # 如果有解密后的响应体，优先使用它
            try:
                response_data_json = json.loads(decrypted_body)
                response_text = decrypted_body
            except Exception as e:
                # 如果解析失败，使用原始响应数据
                response_data_json = response_data.get('response_data', response_data.get('body', {}))
                response_text = response_data.get('response_text', response_data.get('text', ''))
        else:
            # 如果没有解密后的响应体，使用原始响应数据
            response_data_json = response_data.get('response_data', response_data.get('body', {}))
            response_text = response_data.get('response_text', response_data.get('text', ''))
        
        # 特殊字段处理
        if field_path == 'response_time':
            return response_data.get('response_time', response_data.get('elapsed', 0))
        elif field_path == 'status_code':
            return response_data.get('status_code', 0)
        elif field_path == 'response_text':
            return response_text
        elif field_path == 'response_data':
            return response_data_json
        elif field_path == 'response_headers':
            return response_data.get('response_headers', response_data.get('headers', {}))
        elif field_path.startswith('header.'):
            # 提取响应头字段
            header_key = field_path[7:]  # 去掉 'header.' 前缀
            headers = response_data.get('response_headers', response_data.get('headers', {}))
            actual_headers = {k.lower(): v for k, v in headers.items()}
            return actual_headers.get(header_key.lower(), '')
        elif field_path.startswith('json.'):
            # 提取JSON路径字段
            try:
                data = response_data_json
                if isinstance(data, str):
                    data = json.loads(data)
                
                path_parts = field_path[5:].split('.')  # 去掉 'json.' 前缀
                current = data
                for part in path_parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
                        current = current[int(part)]
                    else:
                        return ''
                return str(current)
            except:
                return ''
        else:
            # 处理复杂路径：支持数组索引和对象属性
            return self._extract_field_value_from_response(response_data, field_path)
    
    def _extract_field_value_from_response(self, response_data: Dict[str, Any], field_path: str) -> Any:
        """从响应体中提取字段路径的实际值，支持复杂路径如 name[0].libai（与tabbed_case_editor.py保持一致）"""
        if not field_path:
            return ''
        
        # 优先使用解密后的响应体（对于加解密请求）
        decrypted_body = response_data.get('decrypted_body', '')
        
        if decrypted_body:
            # 如果有解密后的响应体，优先使用它
            try:
                response_data_json = json.loads(decrypted_body)
            except Exception as e:
                # 如果解析失败，使用原始响应数据
                response_data_json = response_data.get('response_data', response_data.get('body', {}))
        else:
            # 如果没有解密后的响应体，使用原始响应数据
            response_data_json = response_data.get('response_data', response_data.get('body', {}))
        
        # 处理复杂路径：支持数组索引和对象属性
        try:
            # 如果response_data_json是字符串，尝试解析为JSON
            if isinstance(response_data_json, str):
                data = json.loads(response_data_json)
            else:
                data = response_data_json
            
            # 解析字段路径，支持数组索引 [0] 和对象属性 .name
            path_parts = []
            current_part = ''
            
            i = 0
            while i < len(field_path):
                char = field_path[i]
                
                if char == '[':
                    # 数组索引开始
                    if current_part:
                        path_parts.append(current_part)
                        current_part = ''
                    
                    # 找到数组索引结束位置
                    j = i + 1
                    while j < len(field_path) and field_path[j] != ']':
                        j += 1
                    
                    if j < len(field_path):
                        index_str = field_path[i+1:j]
                        if index_str.isdigit():
                            path_parts.append(int(index_str))
                        i = j  # 跳过']'
                elif char == '.':
                    # 对象属性分隔符
                    if current_part:
                        path_parts.append(current_part)
                        current_part = ''
                else:
                    current_part += char
                
                i += 1
            
            # 添加最后一个部分
            if current_part:
                path_parts.append(current_part)
            
            # 根据路径提取值
            current = data
            for i, part in enumerate(path_parts):
                
                if isinstance(current, dict) and part in current:
                    current = current[part]
                elif isinstance(current, list) and isinstance(part, int) and 0 <= part < len(current):
                    current = current[part]
                else:
                    return None  # 路径不存在时返回None而不是空字符串
            
            # 如果最终值是None，直接返回None而不是'None'
            if current is None:
                return None
            
            return str(current)
            
        except Exception as e:
            # 如果提取失败，返回空字符串
            return ''
    
    def _simple_json_path_extract(self, data: Any, json_path: str) -> Any:
        """简单的JSON路径提取方法（与tabbed_case_editor.py保持一致）"""
        if not json_path:
            return data

        # 简化实现，只支持简单的点分隔路径
        keys = json_path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
    
    def replace_variables(self, text: str, step_result: Dict[str, Any], step_index: int = None) -> str:
        """替换文本中的变量，支持${变量名}格式（与tabbed_case_editor.py保持一致）"""
        if not text or '${' not in text:
            return text
        
        import re
        
        # 调试：记录替换前的文本
        self._log_message('DEBUG', f"[DEBUG] replace_variables: 替换前文本 = {text}", step_index)
        
        # 匹配${变量名}格式
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, text)
        
        # 调试：记录匹配到的变量
        self._log_message('DEBUG', f"[DEBUG] replace_variables: 匹配到的变量 = {matches}", step_index)
        
        for var_name in matches:
            var_value = ''
            
            # 首先尝试从变量管理器中获取变量（前置处理器提取的变量）
            if hasattr(self, 'variable_manager'):
                # 调试：检查变量管理器状态
                self._log_message('DEBUG', f"[DEBUG] replace_variables: 变量管理器状态 - 局部变量: {self.variable_manager.local_variables}", step_index)
                self._log_message('DEBUG', f"[DEBUG] replace_variables: 变量管理器状态 - 全局变量: {self.variable_manager.global_variables}", step_index)
                
                # 尝试从局部变量中获取
                if var_name in self.variable_manager.local_variables:
                    var_value = self.variable_manager.local_variables[var_name]
                    self._log_message('DEBUG', f"[DEBUG] replace_variables: 从局部变量获取 {var_name} = {var_value}", step_index)
                # 尝试从全局变量中获取
                elif var_name in self.variable_manager.global_variables:
                    var_value = self.variable_manager.global_variables[var_name]
                    self._log_message('DEBUG', f"[DEBUG] replace_variables: 从全局变量获取 {var_name} = {var_value}", step_index)
            
            # 如果变量管理器中没找到，再从步骤结果中获取
            if not var_value and step_result:
                var_value = step_result.get(var_name, '')
                self._log_message('DEBUG', f"[DEBUG] replace_variables: 从步骤结果获取 {var_name} = {var_value}", step_index)
                
                # 如果变量名是特殊字段，使用_extract_field_value提取
                if var_name in ['response_time', 'status_code', 'response_text', 'response_data', 'response_headers']:
                    var_value = self._extract_field_value(step_result, var_name)
                elif var_name.startswith('header.'):
                    var_value = self._extract_field_value(step_result, var_name)
                elif var_name.startswith('json.'):
                    var_value = self._extract_field_value(step_result, var_name)
                else:
                    # 尝试从响应数据中提取
                    var_value = self._extract_field_value(step_result, var_name)
            
            # 记录变量替换的调试信息
            self._log_message('DEBUG', f"[DEBUG] replace_variables: 变量替换: ${{{var_name}}} -> {var_value}", step_index)
            
            # 替换变量
            text = text.replace(f'${{{var_name}}}', str(var_value))
        
        # 调试：记录替换后的文本
        self._log_message('DEBUG', f"[DEBUG] replace_variables: 替换后文本 = {text}", step_index)
        
        return text

    def _execute_comparison_new(self, actual: Any, expected: Any, symbol: str) -> bool:
        """执行比较操作（新格式，与tabbed_case_editor.py保持一致）"""
        # 处理None值
        if actual is None:
            actual_str = None
        else:
            actual_str = str(actual)
            
        if expected is None:
            expected_str = None
        else:
            expected_str = str(expected)
        
        # 根据符号执行比较
        if symbol == 'equal':
            if actual is None and expected is None:
                return True
            if actual is None or expected is None:
                return False
            return actual_str == expected_str
        elif symbol == 'not_equal':
            if actual is None and expected is None:
                return False
            if actual is None or expected is None:
                return True
            return actual_str != expected_str
        elif symbol == 'contains':
            if expected_str is None or actual_str is None:
                return False
            return expected_str in actual_str
        elif symbol == 'not_contains':
            if expected_str is None or actual_str is None:
                return False
            return expected_str not in actual_str
        elif symbol == 'greater':
            try:
                if expected_str is None or actual_str is None:
                    return False
                return float(actual_str) > float(expected_str)
            except (ValueError, TypeError):
                return False
        elif symbol == 'less':
            try:
                if expected_str is None or actual_str is None:
                    return False
                return float(actual_str) < float(expected_str)
            except (ValueError, TypeError):
                return False
        elif symbol == 'greater_equal':
            try:
                if expected_str is None or actual_str is None:
                    return False
                return float(actual_str) >= float(expected_str)
            except (ValueError, TypeError):
                return False
        elif symbol == 'less_equal':
            try:
                if expected_str is None or actual_str is None:
                    return False
                return float(actual_str) <= float(expected_str)
            except (ValueError, TypeError):
                return False
        else:
            # 默认使用相等比较
            return actual_str == expected_str
    
    def _execute_comparison(self, actual: Any, expected: Any, symbol: str) -> bool:
        """执行比较操作（兼容旧格式）"""
        # 处理None值
        if actual is None:
            actual_str = None
        else:
            actual_str = str(actual)
            
        if expected is None:
            expected_str = None
        else:
            expected_str = str(expected)
        
        # 根据符号执行比较
        if symbol == 'equal':
            if actual is None and expected is None:
                return True
            if actual is None or expected is None:
                return False
            return actual_str == expected_str
        elif symbol == 'not_equal':
            if actual is None and expected is None:
                return False
            if actual is None or expected is None:
                return True
            return actual_str != expected_str
        elif symbol == 'contains':
            if expected_str is None or actual_str is None:
                return False
            return expected_str in actual_str
        elif symbol == 'not_contains':
            if expected_str is None or actual_str is None:
                return False
            return expected_str not in actual_str
        elif symbol == 'greater':
            try:
                if expected_str is None or actual_str is None:
                    return False
                return float(actual_str) > float(expected_str)
            except (ValueError, TypeError):
                return False
        elif symbol == 'less':
            try:
                if expected_str is None or actual_str is None:
                    return False
                return float(actual_str) < float(expected_str)
            except (ValueError, TypeError):
                return False
        else:
            # 默认使用相等比较
            return actual_str == expected_str
    
    def _create_step_error_result(self, step_data: Dict[str, Any], step_index: int, 
                                 start_time: datetime, error_msg: str) -> Dict[str, Any]:
        """创建步骤错误结果"""
        return {
            'step_id': step_data.get('id'),
            'step_name': step_data.get('name', f"步骤{step_index+1}"),
            'step_order': step_index,
            'status': 'error',
            'success': False,
            'error_message': error_msg,
            'start_time': start_time,
            'end_time': datetime.now(),
            'execution_time': 0,
            'variables_snapshot': self.variable_manager.get_all_variables()
        }


# 兼容性包装器，用于替换execute_test_case.py的功能
class ExecuteTestCase:
    """兼容性包装器，用于替换原有的ExecuteTestCase类"""
    
    def __init__(self):
        self.executor = TestCaseExecutor()
    
    def execute_test_case_unified(self, case_data: Dict[str, Any], 
                                 generate_report: bool = False, 
                                 scheduler_id: Optional[int] = None,
                                 parent_report_id: Optional[int] = None) -> Dict[str, Any]:
        """统一测试用例执行入口（兼容原有接口）"""
        # 使用新的执行器执行用例，不停止执行（保持原有行为）
        result = self.executor.execute_case(case_data, stop_on_failure=False)
        
        # 如果需要生成报告，添加报告相关逻辑
        if generate_report:
            # 这里可以添加报告生成逻辑
            pass
            
        return result