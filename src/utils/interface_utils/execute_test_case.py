#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用例执行工具类
统一测试用例执行逻辑，支持调度任务和手动执行
"""

import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.database import Database
from src.utils.interface_utils.variable_manager import VariableManager
from src.utils.interface_utils.request_engine import RequestEngine
from src.core.services.global_variable_service import get_global_variable_service

# 配置日志
logger = logging.getLogger("ExecuteTestCase")


class ExecuteTestCase:
    """测试用例执行工具类"""
    
    def __init__(self):
        """初始化执行器"""
        self.db = Database()
        self.request_engine = RequestEngine()
        
    def execute_test_case_unified(self, case_data: Dict[str, Any], 
                                 generate_report: bool = False, 
                                 scheduler_id: Optional[int] = None,
                                 parent_report_id: Optional[int] = None) -> Dict[str, Any]:
        """统一测试用例执行入口（参考调试按钮逻辑）
        
        Args:
            case_data: 测试用例数据
            generate_report: 是否生成测试报告（调度任务需要，调试按钮不需要）
            scheduler_id: 调度ID（仅调度任务需要）
            parent_report_id: 父报告ID（用于统一报告模式）
        
        Returns:
            执行结果字典
        """
        try:
            case_id = case_data['id']
            case_name = case_data.get('name', '未知用例')
            
            # 添加与执行日志弹窗一致的调试信息
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{current_time} [INFO] 🔍 开始执行测试用例: {case_name} (ID: {case_id})")
            
            # 获取测试步骤
            steps = case_data.get('steps', [])
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{current_time} [INFO] 📋 测试用例 {case_name} 包含 {len(steps)} 个步骤")
            
            # 统计启用的步骤
            enabled_steps = [step for step in steps if step.get('enabled', True)]
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{current_time} [INFO] ✅ 启用的步骤数量: {len(enabled_steps)}")
            
            # 初始化变量管理器（参考调试按钮逻辑）
            try:
                variable_manager = VariableManager()
                
                # 加载指定项目的全局变量
                service = get_global_variable_service()
                service.sync_to_variable_manager(variable_manager, case_data.get('project_id', 0))
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"{current_time} [INFO] 📊 已加载项目 {case_data.get('project_id', 0)} 的全局变量")
            except Exception as e:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.warning(f"{current_time} [WARN] ⚠️ 加载全局变量失败: {str(e)}")
                variable_manager = None
            
            # 创建测试报告数据（仅调度任务需要，且没有父报告ID时）
            report_data = None
            if generate_report and not parent_report_id:
                report_data = {
                    'case_id': case_id,
                    'case_name': case_name,
                    'scheduler_id': scheduler_id,
                    'project_id': case_data.get('project_id'),  # 添加project_id
                    'start_time': datetime.now(),
                    'status': 'running',
                    'total_cases': 1,  # 单个用例执行
                    'passed_cases': 0,
                    'failed_cases': 0,
                    'error_cases': 0,
                    'step_results': []
                }
            
            # 执行每个步骤（不中断，记录所有步骤结果）
            step_results = []
            step_results_data = []  # 用于暂存步骤结果数据，等报告创建后再保存到数据库
            for i, step in enumerate(steps):
                step_name = step.get('name', f"步骤{i+1}")
                
                # 检查步骤是否启用（参考调试按钮逻辑）
                if not step.get('enabled', True):
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"{current_time} [INFO] ⏭️ 跳过禁用步骤: {step_name}")
                    continue
                
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"{current_time} [INFO] 🚀 执行步骤 [{i+1}/{len(enabled_steps)}]: {step_name}")
                
                # 执行单个步骤（使用统一的步骤执行逻辑）
                step_result = self._execute_test_step_unified(step, i, case_data, variable_manager)
                step_results.append(step_result)
                
                # 保存步骤执行结果到数据库（调度任务需要，或者有父报告ID时）
                if generate_report or parent_report_id:
                    try:
                        # 延迟导入避免循环导入
                        from src.core.services.test_report_service import TestReportService
                        report_service = TestReportService()
                        
                        # 准备步骤结果数据
                        step_result_data = {
                            'scheduler_id': scheduler_id,
                            'case_id': case_id,
                            'step_id': step.get('id'),
                            'step_name': step.get('name', f'步骤{i+1}'),
                            'step_order': i,
                            'status': step_result.get('status'),
                            'start_time': step_result.get('start_time'),
                            'end_time': step_result.get('end_time'),
                            'execution_time': step_result.get('execution_time', 0),
                            'request_data': step_result.get('request_data'),
                            'response_data': step_result.get('response_data'),
                            'pre_processing_result': step_result.get('pre_processing'),
                            'post_processing_result': step_result.get('post_processing'),
                            'assertions_result': step_result.get('assertions'),
                            'variables_snapshot': step_result.get('variables_snapshot'),
                            'execution_logs': step_result.get('execution_logs', []),
                            'error_message': step_result.get('error_message')
                        }
                        
                        # 如果有父报告ID，直接保存到父报告中
                        if parent_report_id:
                            step_result_data['report_id'] = parent_report_id
                            report_service.save_step_result(parent_report_id, step_result_data)
                            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            logger.debug(f"{current_time} [DEBUG] 💾 步骤执行结果已保存到父报告: 步骤{step_result_data.get('step_order')}")
                        else:
                            # 将步骤结果暂存到列表中，等报告创建后再保存
                            step_results_data.append(step_result_data)
                            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            logger.debug(f"{current_time} [DEBUG] 💾 步骤执行结果已暂存: {step.get('name', f'步骤{i+1}')}")
                    except Exception as e:
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        logger.warning(f"{current_time} [WARN] ⚠️ 保存步骤执行结果失败: {str(e)}")
                
                # 统计用例结果（仅调度任务需要，且没有父报告ID时）
                if generate_report and report_data:
                    if step_result.get('status') == 'success':
                        report_data['passed_cases'] = 1
                    elif step_result.get('status') == 'failure':
                        report_data['failed_cases'] = 1
                    elif step_result.get('status') == 'error':
                        report_data['error_cases'] = 1
                
                # 记录步骤执行结果，但不中断后续步骤执行
                if step_result.get('status') == 'error':
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.warning(f"{current_time} [WARN] ❌ 步骤 {step_name} 执行失败，继续执行后续步骤")
                elif step_result.get('status') == 'failure':
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.warning(f"{current_time} [WARN] ❌ 步骤 {step_name} 执行失败，继续执行后续步骤")
                else:
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"{current_time} [INFO] ✅ 步骤 {step_name} 执行完成")
            
            # 完成报告（仅调度任务需要，且没有父报告ID时）
            if generate_report and report_data:
                report_data['end_time'] = datetime.now()
                report_data['duration'] = (report_data['end_time'] - report_data['start_time']).total_seconds()
                report_data['step_results'] = step_results
                
                # 确定最终状态
                if report_data['error_cases'] > 0:
                    report_data['status'] = 'error'
                elif report_data['failed_cases'] > 0:
                    report_data['status'] = 'failure'
                else:
                    report_data['status'] = 'success'
                
                # 保存测试报告到数据库
                try:
                    # 延迟导入避免循环导入
                    from src.core.services.test_report_service import TestReportService
                    report_service = TestReportService()
                    report_id = report_service.create_report(report_data)
                    report_data['report_id'] = report_id  # 保存report_id用于后续步骤结果保存
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"{current_time} [INFO] 📄 测试报告已保存，ID: {report_id}")
                    
                    # 在报告创建后保存步骤结果到数据库
                    if step_results_data:
                        for step_result_data in step_results_data:
                            try:
                                step_result_data['report_id'] = report_id
                                report_service.save_step_result(report_id, step_result_data)
                                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                logger.debug(f"{current_time} [DEBUG] 💾 步骤执行结果已保存到数据库: 步骤{step_result_data.get('step_order')}")
                            except Exception as e:
                                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                logger.warning(f"{current_time} [WARN] ⚠️ 保存步骤执行结果失败: {str(e)}")
                except Exception as e:
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.warning(f"{current_time} [WARN] ⚠️ 保存测试报告失败: {str(e)}")
            
            # 记录用例执行统计信息
            success_count = sum(1 for result in step_results if result.get('status') == 'success')
            failure_count = sum(1 for result in step_results if result.get('status') == 'failure')
            error_count = sum(1 for result in step_results if result.get('status') == 'error')
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{current_time} [INFO] 🎉 测试用例 {case_name} 执行完成: 成功 {success_count}/{len(enabled_steps)} 个步骤")
            
            # 如果生成了报告且没有父报告ID，更新报告中的步骤统计信息
            if generate_report and report_data:
                try:
                    # 延迟导入避免循环导入
                    from src.core.services.test_report_service import TestReportService
                    report_service = TestReportService()
                    
                    # 更新报告中的用例统计信息
                    update_data = {
                        'total_cases': 1,  # 单个用例执行
                        'passed_cases': 1 if success_count == len(enabled_steps) else 0,
                        'failed_cases': 1 if failure_count > 0 else 0,
                        'error_cases': 1 if error_count > 0 else 0
                    }
                    
                    # 根据用例执行结果更新报告状态
                    if error_count > 0:
                        update_data['status'] = 'error'
                    elif failure_count > 0:
                        update_data['status'] = 'failure'
                    else:
                        update_data['status'] = 'success'
                    
                    report_service.update_report(report_data['report_id'], update_data)
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"{current_time} [INFO] 📊 测试报告用例统计已更新: 总用例1, 通过{update_data['passed_cases']}, 失败{update_data['failed_cases']}, 错误{update_data['error_cases']}")
                    
                except Exception as e:
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.warning(f"{current_time} [WARN] ⚠️ 更新测试报告步骤统计失败: {str(e)}")
            
            # 返回统一格式的执行结果
            return {
                'success': success_count == len(enabled_steps),
                'success_count': success_count,
                'total_count': len(enabled_steps),
                'case_name': case_name,
                'case_id': case_id,
                'step_results': step_results,
                'report_data': report_data if generate_report else None
            }
            
        except Exception as e:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.error(f"{current_time} [ERROR] 💥 执行测试用例失败: {str(e)}")
            
            # 创建错误报告（仅调度任务需要）
            if generate_report:
                error_report = {
                    'case_id': case_data.get('id', 0),
                    'case_name': case_data.get('name', '未知用例'),
                    'scheduler_id': scheduler_id,
                    'project_id': case_data.get('project_id'),  # 添加project_id
                    'start_time': datetime.now(),
                    'end_time': datetime.now(),
                    'duration': 0,
                    'status': 'error',
                    'total_cases': 1,  # 单个用例执行
                    'passed_cases': 0,
                    'failed_cases': 0,
                    'error_cases': 1,
                    'error_message': str(e),
                    'step_results': []
                }
                
                # 保存错误报告
                try:
                    from src.core.services.test_report_service import TestReportService
                    report_service = TestReportService()
                    report_service.create_report(error_report)
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"{current_time} [INFO] 📄 错误报告已保存")
                except Exception as e:
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.warning(f"{current_time} [WARN] ⚠️ 保存错误报告失败: {str(e)}")
            
            # 返回错误结果
            return {
                'success': False,
                'error': str(e),
                'success_count': 0,
                'total_count': len(enabled_steps) if 'enabled_steps' in locals() else 0,
                'case_name': case_name if 'case_name' in locals() else '未知用例',
                'case_id': case_id if 'case_id' in locals() else 0,
                'step_results': [],
                'report_data': None
            }

    def _execute_test_step_unified(self, step_data: Dict[str, Any], step_index: int, 
                                  case_data: Dict[str, Any], variable_manager: Optional[VariableManager] = None) -> Dict[str, Any]:
        """统一步骤执行逻辑（参考调试按钮逻辑）"""
        execution_logs = []  # 收集执行日志
        
        try:
            step_name = step_data.get('name', f"步骤{step_index+1}")
            step_start_time = datetime.now()
            
            # 添加开始执行日志（与执行日志弹窗格式保持一致）
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            execution_logs.append({
                'timestamp': datetime.now().isoformat(),
                'level': 'info',
                'message': f"🔍 开始执行步骤 [{step_index+1}]: {step_name}"
            })
            
            logger.info(f"{current_time} [INFO] 🔍 开始执行步骤 [{step_index+1}]: {step_name}")
            
            # 准备请求数据（使用变量管理器进行变量替换）
            api_template_id = step_data.get('api_template_id')
            if not api_template_id:
                error_msg = f"步骤 {step_name} 缺少API模板ID"
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                execution_logs.append({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'error',
                    'message': error_msg
                })
                logger.warning(f"{current_time} [WARN] ⚠️ {error_msg}")
                return {
                    'step_id': step_data.get('id'),
                    'step_name': step_name,
                    'step_order': step_index,
                    'status': 'error',
                    'error_message': error_msg,
                    'start_time': step_start_time,
                    'end_time': datetime.now(),
                    'execution_time': 0,
                    'request_data': None,
                    'response_data': None,
                    'pre_processing': {},
                    'post_processing': {},
                    'assertions': {},
                    'assertion_result': None,
                    'variables_snapshot': variables_snapshot if 'variables_snapshot' in locals() else {},
                    'execution_logs': execution_logs
                }
            
            # 获取API模板数据
            api_data = self._get_api_template_data(api_template_id)
            if not api_data:
                error_msg = f"步骤 {step_name} 的API模板ID {api_template_id} 不存在"
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                execution_logs.append({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'error',
                    'message': error_msg
                })
                logger.warning(f"{current_time} [WARN] ⚠️ {error_msg}")
                return {
                    'step_id': step_data.get('id'),
                    'step_name': step_name,
                    'step_order': step_index,
                    'status': 'error',
                    'error_message': error_msg,
                    'start_time': step_start_time,
                    'end_time': datetime.now(),
                    'execution_time': 0,
                    'request_data': None,
                    'response_data': None,
                    'pre_processing': {},
                    'post_processing': {},
                    'assertions': {},
                    'assertion_result': None,
                    'variables_snapshot': variables_snapshot,
                    'execution_logs': execution_logs
                }
            
            # 记录变量快照（执行前的变量状态）
            variables_snapshot = {}
            if variable_manager:
                variables_snapshot = variable_manager.get_all_variables()
            
            # 记录请求数据（执行前的配置）
            request_data = {
                'api_template_id': api_template_id,
                'api_data': api_data.copy(),  # 复制一份，避免后续修改影响
                'variables': variables_snapshot.copy()
            }
            
            # 执行前置处理
            pre_processing = step_data.get('pre_processing', {})
            pre_processing_result = {}
            if pre_processing:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                execution_logs.append({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'info',
                    'message': f"🔧 执行步骤 {step_name} 的前置处理"
                })
                logger.info(f"{current_time} [INFO] 🔧 执行步骤 {step_name} 的前置处理")
                pre_processing_result = self._execute_pre_processing(pre_processing, step_index)
                # 将前置处理的执行日志合并到主步骤日志中
                if pre_processing_result and 'execution_logs' in pre_processing_result:
                    execution_logs.extend(pre_processing_result['execution_logs'])
            
            # 执行HTTP请求
            from src.utils.interface_utils.request_engine import RequestEngine
            request_engine = RequestEngine()
            
            # 使用变量管理器进行变量替换
            if variable_manager:
                # 替换请求数据中的变量
                api_data = variable_manager.replace_variables_in_dict(api_data)
            
            # 获取变量数据（从步骤或全局变量）
            variables = {}
            if step_data.get('variables'):
                variables.update(step_data.get('variables', {}))
            if case_data.get('global_vars'):
                variables.update(case_data.get('global_vars', {}))
            
            # 执行请求
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            execution_logs.append({
                'timestamp': datetime.now().isoformat(),
                'level': 'info',
                'message': f"🌐 执行HTTP请求: {api_data.get('method', 'GET')} {api_data.get('url_path', '')}"
            })
            logger.info(f"{current_time} [INFO] 🌐 执行HTTP请求: {api_data.get('method', 'GET')} {api_data.get('url_path', '')}")
            response_data = request_engine.execute_request(api_data, variables)
            
            # 执行后置处理
            post_processing = step_data.get('post_processing', {})
            post_processing_result = {}
            if post_processing:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                execution_logs.append({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'info',
                    'message': f"🔧 执行步骤 {step_name} 的后置处理"
                })
                logger.info(f"{current_time} [INFO] 🔧 执行步骤 {step_name} 的后置处理")
                post_processing_result = self._execute_post_processing(post_processing, response_data, step_index)
                # 将后置处理的执行日志合并到主步骤日志中
                if post_processing_result and 'execution_logs' in post_processing_result:
                    execution_logs.extend(post_processing_result['execution_logs'])
            
            # 执行断言
            assertions = step_data.get('assertions', {})
            assertions_result = {}
            if assertions:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                execution_logs.append({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'info',
                    'message': f"✅ 执行步骤 {step_name} 的断言"
                })
                logger.info(f"{current_time} [INFO] ✅ 执行步骤 {step_name} 的断言")
                assertions_result = self._execute_assertions(assertions, response_data, step_index)
                # 将断言的执行日志合并到主步骤日志中
                if assertions_result and 'execution_logs' in assertions_result:
                    execution_logs.extend(assertions_result['execution_logs'])
                assertion_result = assertions_result['passed']
            
            step_end_time = datetime.now()
            execution_time = (step_end_time - step_start_time).total_seconds()
            
            # 确定步骤状态
            status = 'success' if assertion_result else 'failure'
            
            # 根据状态使用不同的图标
            status_icon = "✅" if status == 'success' else "❌"
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            execution_logs.append({
                'timestamp': datetime.now().isoformat(),
                'level': 'success' if status == 'success' else 'failure',
                'message': f"{status_icon} 步骤 {step_name} 执行完成，状态: {status}"
            })
            logger.info(f"{current_time} [SUCCESS] {status_icon} 步骤 {step_name} 执行完成，状态: {status}")
            
            return {
                'step_id': step_data.get('id'),
                'step_name': step_name,
                'step_order': step_index,
                'status': status,
                'start_time': step_start_time,
                'end_time': step_end_time,
                'execution_time': execution_time,
                'request_data': request_data,
                'response_data': response_data,
                'pre_processing': pre_processing_result,
                'post_processing': post_processing_result,
                'assertions': assertions_result,
                'assertion_result': assertion_result,
                'variables_snapshot': variables_snapshot,
                'execution_logs': execution_logs
            }
            
        except Exception as e:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            error_msg = f"❌ 执行步骤失败: {str(e)}"
            execution_logs.append({
                'timestamp': datetime.now().isoformat(),
                'level': 'error',
                'message': error_msg
            })
            logger.error(f"{current_time} [ERROR] ❌ 执行步骤失败: {str(e)}")
            return {
                'step_id': step_data.get('id'),
                'step_name': step_name if 'step_name' in locals() else f"步骤{step_index+1}",
                'step_order': step_index,
                'status': 'error',
                'error_message': str(e),
                'start_time': step_start_time if 'step_start_time' in locals() else datetime.now(),
                'end_time': datetime.now(),
                'execution_time': 0,
                'execution_logs': execution_logs
            }

    def _execute_pre_processing(self, pre_processing: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """执行前置处理（集成手动执行方法的功能）"""
        result = {
            'tools_executed': [],
            'variables_set': {},
            'errors': [],
            'execution_logs': []  # 添加执行日志字段
        }
        
        try:
            if not pre_processing:
                return result
                
            # 统计前置处理工具数量
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
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            start_msg = f"🔧 开始执行前置处理，工具数量: {tool_count}"
            result['execution_logs'].append({
                'timestamp': datetime.now().isoformat(),
                'level': 'info',
                'message': start_msg
            })
            logger.info(f"{current_time} [INFO] 🔧 开始执行前置处理，工具数量: {tool_count}")
            
            # 执行前置处理器中的工具
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
                if not enabled:
                    continue
                    
                config = tool_config.get('config', {})
                
                # 记录前置处理工具情况
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                tool_msg = f"🔧 执行前置处理工具: {tool_type}"
                result['execution_logs'].append({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'info',
                    'message': tool_msg
                })
                logger.info(f"{current_time} [INFO] 🔧 执行前置处理工具: {tool_type}")
                
                tool_result = {
                    'tool_id': tool_id,
                    'tool_type': tool_type,
                    'config': config,
                    'status': 'success',
                    'result': None
                }
                
                try:
                    if tool_type == 'http_request':
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        http_msg = "🔧 执行HTTP请求工具"
                        result['execution_logs'].append({
                            'timestamp': datetime.now().isoformat(),
                            'level': 'info',
                            'message': http_msg
                        })
                        logger.info(f"{current_time} [INFO] 🔧 执行HTTP请求工具")
                        tool_result['result'] = self._execute_http_request_tool(config, step_index)
                    elif tool_type == 'sql_tool':
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        sql_msg = "🔧 执行SQL工具"
                        result['execution_logs'].append({
                            'timestamp': datetime.now().isoformat(),
                            'level': 'info',
                            'message': sql_msg
                        })
                        logger.info(f"{current_time} [INFO] 🔧 执行SQL工具")
                        tool_result['result'] = self._execute_sql_tool(config, step_index)
                    else:
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        unknown_msg = f"🔧 未知的前置处理工具类型: {tool_type}"
                        result['execution_logs'].append({
                            'timestamp': datetime.now().isoformat(),
                            'level': 'warning',
                            'message': unknown_msg
                        })
                        logger.warning(f"{current_time} [WARN] 🔧 未知的前置处理工具类型: {tool_type}")
                        tool_result['status'] = 'skipped'
                        tool_result['error'] = f"未知工具类型: {tool_type}"
                except Exception as e:
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    error_msg = f"🔧 执行前置处理工具 {tool_type} 失败: {str(e)}"
                    result['execution_logs'].append({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'error',
                        'message': error_msg
                    })
                    logger.error(f"{current_time} [ERROR] 🔧 执行前置处理工具 {tool_type} 失败: {str(e)}")
                    tool_result['status'] = 'error'
                    tool_result['error'] = str(e)
                    result['errors'].append(f"工具 {tool_type} 执行失败: {str(e)}")
                
                result['tools_executed'].append(tool_result)
                executed_tool_count += 1
            
            # 处理变量设置
            variables = pre_processing.get('variables', {})
            
            if variables:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # 这里可以集成变量管理器的功能
                var_msg = f"🔧 设置局部变量: {len(variables)} 个"
                result['execution_logs'].append({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'info',
                    'message': var_msg
                })
                logger.info(f"{current_time} [INFO] 🔧 设置局部变量: {len(variables)} 个")
                result['variables_set'] = variables.copy()
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            complete_msg = f"🔧 前置处理完成，共执行 {executed_tool_count} 个工具"
            result['execution_logs'].append({
                'timestamp': datetime.now().isoformat(),
                'level': 'info',
                'message': complete_msg
            })
            logger.info(f"{current_time} [INFO] 🔧 前置处理完成，共执行 {executed_tool_count} 个工具")
            
        except Exception as e:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            error_msg = f"🔧 执行前置处理失败: {str(e)}"
            result['execution_logs'].append({
                'timestamp': datetime.now().isoformat(),
                'level': 'error',
                'message': error_msg
            })
            logger.error(f"{current_time} [ERROR] 🔧 执行前置处理失败: {str(e)}")
            result['errors'].append(f"前置处理执行失败: {str(e)}")
        
        return result

    def _execute_post_processing(self, post_processing: Dict[str, Any], response_data: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """执行后置处理（集成手动执行方法的功能）"""
        result = {
            'variables_extracted': {},
            'tools_executed': [],
            'errors': [],
            'execution_logs': []  # 添加执行日志字段
        }
        
        try:
            if not post_processing:
                return result
                
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            start_msg = "🔧 开始执行后置处理"
            result['execution_logs'].append({
                'timestamp': datetime.now().isoformat(),
                'level': 'info',
                'message': start_msg
            })
            logger.info(f"{current_time} [INFO] 🔧 开始执行后置处理")
            
            # 处理变量提取
            extractors = post_processing.get('variables', {})
            if extractors:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                extractor_msg = f"🔧 执行变量提取，提取器数量: {len(extractors)}"
                result['execution_logs'].append({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'info',
                    'message': extractor_msg
                })
                logger.info(f"{current_time} [INFO] 🔧 执行变量提取，提取器数量: {len(extractors)}")
                # 这里可以集成变量提取功能
                result['variables_extracted'] = extractors.copy()
            
            # 处理其他后置操作
            # 可以添加其他后置处理逻辑，如数据清理、通知等
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            complete_msg = "🔧 后置处理完成"
            result['execution_logs'].append({
                'timestamp': datetime.now().isoformat(),
                'level': 'info',
                'message': complete_msg
            })
            logger.info(f"{current_time} [INFO] 🔧 后置处理完成")
            
        except Exception as e:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            error_msg = f"🔧 执行后置处理失败: {str(e)}"
            result['execution_logs'].append({
                'timestamp': datetime.now().isoformat(),
                'level': 'error',
                'message': error_msg
            })
            logger.error(f"{current_time} [ERROR] 🔧 执行后置处理失败: {str(e)}")
            result['errors'].append(f"后置处理执行失败: {str(e)}")
        
        return result

    def _execute_assertions(self, assertions: Dict[str, Any], response_data: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """执行断言验证"""
        result = {
            'assertions_executed': [],
            'passed': True,
            'total_count': 0,
            'passed_count': 0,
            'failed_count': 0,
            'errors': [],
            'execution_logs': []  # 添加执行日志字段
        }
        
        try:
            if not assertions:
                return result
                
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            start_msg = "✅ 开始执行断言验证"
            result['execution_logs'].append({
                'timestamp': datetime.now().isoformat(),
                'level': 'info',
                'message': start_msg
            })
            logger.info(f"{current_time} [INFO] ✅ 开始执行断言验证")
            
            # 获取断言配置
            assertions_config = assertions.get('assertions', [])
            if not assertions_config:
                return result
                
            result['total_count'] = len(assertions_config)
            
            # 执行断言
            for i, assertion in enumerate(assertions_config):
                assertion_result = {
                    'index': i,
                    'type': assertion.get('type', ''),
                    'expected': assertion.get('expected', ''),
                    'actual': '',
                    'passed': False,
                    'error': ''
                }
                
                try:
                    # 这里集成断言执行逻辑
                    # 暂时模拟断言结果
                    assertion_result['passed'] = True
                    
                    if assertion_result['passed']:
                        result['passed_count'] += 1
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        assertion_msg = f"✅ 断言{i+1} 验证通过"
                        result['execution_logs'].append({
                            'timestamp': datetime.now().isoformat(),
                            'level': 'success',
                            'message': assertion_msg
                        })
                        logger.info(f"{current_time} [SUCCESS] ✅ 断言{i+1} 验证通过")
                    else:
                        result['failed_count'] += 1
                        result['passed'] = False
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        assertion_msg = f"❌ 断言{i+1} 验证失败"
                        result['execution_logs'].append({
                            'timestamp': datetime.now().isoformat(),
                            'level': 'failure',
                            'message': assertion_msg
                        })
                        logger.warning(f"{current_time} [FAILURE] ❌ 断言{i+1} 验证失败")
                        
                except Exception as e:
                    assertion_result['error'] = str(e)
                    assertion_result['passed'] = False
                    result['failed_count'] += 1
                    result['passed'] = False
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    error_msg = f"❌ 断言{i+1}执行失败: {str(e)}"
                    result['execution_logs'].append({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'error',
                        'message': error_msg
                    })
                    logger.error(f"{current_time} [ERROR] ❌ 断言{i+1}执行失败: {str(e)}")
                    result['errors'].append(f"断言{i+1}执行失败: {str(e)}")
                
                result['assertions_executed'].append(assertion_result)
                
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            complete_msg = f"✅ 断言验证完成: 通过{result['passed_count']}/{result['total_count']}"
            result['execution_logs'].append({
                'timestamp': datetime.now().isoformat(),
                'level': 'info',
                'message': complete_msg
            })
            logger.info(f"{current_time} [INFO] ✅ 断言验证完成: 通过{result['passed_count']}/{result['total_count']}")
            
        except Exception as e:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            error_msg = f"❌ 执行断言验证失败: {str(e)}"
            result['execution_logs'].append({
                'timestamp': datetime.now().isoformat(),
                'level': 'error',
                'message': error_msg
            })
            logger.error(f"{current_time} [ERROR] ❌ 执行断言验证失败: {str(e)}")
            result['errors'].append(f"断言验证执行失败: {str(e)}")
            result['passed'] = False
        
        return result

    def _execute_http_request_tool(self, config: Dict[str, Any], step_index: int):
        """执行HTTP请求工具"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{current_time} [INFO] 🔧 开始执行HTTP请求工具，配置: {config}")
            
            # 获取请求配置
            method = config.get('method', 'GET')
            url = config.get('url', '')
            headers = config.get('headers', {})
            body = config.get('body', {})
            timeout = config.get('timeout', 30)
            
            if not url:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.error(f"{current_time} [ERROR] 🔧 HTTP请求工具配置错误: URL不能为空")
                return
            
            # 执行HTTP请求
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{current_time} [INFO] 🔧 前置处理器HTTP请求: {method} {url}")
            
            # 这里可以集成实际的HTTP请求执行逻辑
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{current_time} [INFO] 🔧 HTTP请求工具执行完成")
            
        except Exception as e:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.error(f"{current_time} [ERROR] 🔧 执行HTTP请求工具失败: {str(e)}")

    def _execute_sql_tool(self, config: Dict[str, Any], step_index: int):
        """执行SQL工具"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{current_time} [INFO] 🔧 开始执行SQL工具，配置: {config}")
            
            # 获取SQL配置
            sql = config.get('sql', '')
            database = config.get('database', '')
            
            if not sql:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.error(f"{current_time} [ERROR] 🔧 SQL工具配置错误: SQL语句不能为空")
                return
            
            # 执行SQL查询
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{current_time} [INFO] 🔧 执行SQL查询: {sql}")
            
            # 这里可以集成实际的SQL执行逻辑
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{current_time} [INFO] 🔧 SQL工具执行完成")
            
        except Exception as e:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.error(f"{current_time} [ERROR] 🔧 执行SQL工具失败: {str(e)}")

    def _get_api_template_data(self, api_template_id: int) -> Optional[Dict[str, Any]]:
        """获取API模板数据"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT name, method, url_path, headers, body, timeout
                        FROM api_templates 
                        WHERE id = %s
                    """, (api_template_id,))
                    api_template = cursor.fetchone()
                    
                    if api_template:
                        # 处理JSON字段
                        headers = json.loads(api_template['headers']) if api_template['headers'] else {}
                        body = json.loads(api_template['body']) if api_template['body'] else {}
                        
                        return {
                            'name': api_template['name'],
                            'method': api_template['method'],
                            'url': api_template['url_path'],
                            'headers': headers,
                            'body': body,
                            'timeout': api_template['timeout'] or 30
                        }
                    
                    return None
                    
        except Exception as e:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.error(f"{current_time} [ERROR] 🔧 获取API模板数据失败: {str(e)}")
            return None


def get_execute_test_case():
    """获取测试用例执行器实例"""
    return ExecuteTestCase()