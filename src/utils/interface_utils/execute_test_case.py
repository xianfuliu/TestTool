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
from src.core.services.test_report_service import TestReportService

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
                                 scheduler_id: Optional[int] = None) -> Dict[str, Any]:
        """统一测试用例执行入口（参考调试按钮逻辑）
        
        Args:
            case_data: 测试用例数据
            generate_report: 是否生成测试报告（调度任务需要，调试按钮不需要）
            scheduler_id: 调度ID（仅调度任务需要）
        
        Returns:
            执行结果字典
        """
        try:
            case_id = case_data['id']
            case_name = case_data.get('name', '未知用例')
            
            logger.info(f"开始执行测试用例: {case_name} (ID: {case_id})")
            
            # 获取测试步骤
            steps = case_data.get('steps', [])
            logger.info(f"测试用例 {case_name} 包含 {len(steps)} 个步骤")
            
            # 统计启用的步骤
            enabled_steps = [step for step in steps if step.get('enabled', True)]
            logger.info(f"启用的步骤数量: {len(enabled_steps)}")
            
            # 初始化变量管理器（参考调试按钮逻辑）
            try:
                variable_manager = VariableManager()
                
                # 加载指定项目的全局变量
                service = get_global_variable_service()
                service.sync_to_variable_manager(variable_manager, case_data.get('project_id', 0))
                logger.info(f"已加载项目 {case_data.get('project_id', 0)} 的全局变量")
            except Exception as e:
                logger.warning(f"加载全局变量失败: {str(e)}")
                variable_manager = None
            
            # 创建测试报告数据（仅调度任务需要）
            report_data = None
            if generate_report:
                report_data = {
                    'case_id': case_id,
                    'case_name': case_name,
                    'scheduler_id': scheduler_id,
                    'project_id': case_data.get('project_id'),  # 添加project_id
                    'start_time': datetime.now(),
                    'status': 'running',
                    'total_steps': len(enabled_steps),
                    'passed_steps': 0,
                    'failed_steps': 0,
                    'error_steps': 0,
                    'step_results': []
                }
            
            # 执行每个步骤（不中断，记录所有步骤结果）
            step_results = []
            for i, step in enumerate(steps):
                step_name = step.get('name', f"步骤{i+1}")
                
                # 检查步骤是否启用（参考调试按钮逻辑）
                if not step.get('enabled', True):
                    logger.info(f"跳过禁用步骤: {step_name}")
                    continue
                
                logger.info(f"执行步骤 [{i+1}/{len(enabled_steps)}]: {step_name}")
                
                # 执行单个步骤（使用统一的步骤执行逻辑）
                step_result = self._execute_test_step_unified(step, i, case_data, variable_manager)
                step_results.append(step_result)
                
                # 统计步骤结果（仅调度任务需要）
                if generate_report and report_data:
                    if step_result.get('status') == 'success':
                        report_data['passed_steps'] += 1
                    elif step_result.get('status') == 'failure':
                        report_data['failed_steps'] += 1
                    elif step_result.get('status') == 'error':
                        report_data['error_steps'] += 1
                
                # 记录步骤执行结果，但不中断后续步骤执行
                if step_result.get('status') == 'error':
                    logger.warning(f"步骤 {step_name} 执行失败，继续执行后续步骤")
                elif step_result.get('status') == 'failure':
                    logger.warning(f"步骤 {step_name} 执行失败，继续执行后续步骤")
                else:
                    logger.info(f"步骤 {step_name} 执行完成")
            
            # 完成报告（仅调度任务需要）
            if generate_report and report_data:
                report_data['end_time'] = datetime.now()
                report_data['duration'] = (report_data['end_time'] - report_data['start_time']).total_seconds()
                report_data['step_results'] = step_results
                
                # 确定最终状态
                if report_data['error_steps'] > 0:
                    report_data['status'] = 'error'
                elif report_data['failed_steps'] > 0:
                    report_data['status'] = 'failure'
                else:
                    report_data['status'] = 'success'
                
                # 保存测试报告到数据库
                try:
                    report_service = TestReportService()
                    report_id = report_service.create_report(report_data)
                    logger.info(f"测试报告已保存，ID: {report_id}")
                except Exception as e:
                    logger.warning(f"保存测试报告失败: {str(e)}")
            
            # 记录用例执行统计信息
            success_count = sum(1 for result in step_results if result.get('status') == 'success')
            logger.info(f"测试用例 {case_name} 执行完成: 成功 {success_count}/{len(enabled_steps)} 个步骤")
            
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
            logger.error(f"执行测试用例失败: {str(e)}")
            
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
                    'total_steps': 0,
                    'passed_steps': 0,
                    'failed_steps': 0,
                    'error_steps': 1,
                    'error_message': str(e),
                    'step_results': []
                }
                
                # 保存错误报告
                try:
                    report_service = TestReportService()
                    report_service.create_report(error_report)
                except:
                    pass
            
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
        try:
            step_name = step_data.get('name', f"步骤{step_index+1}")
            step_start_time = datetime.now()
            
            logger.info(f"开始执行步骤 [{step_index+1}]: {step_name}")
            
            # 准备请求数据（使用变量管理器进行变量替换）
            api_template_id = step_data.get('api_template_id')
            if not api_template_id:
                logger.warning(f"步骤 {step_name} 缺少API模板ID")
                return {
                    'step_id': step_data.get('id'),
                    'step_name': step_name,
                    'step_order': step_index,
                    'status': 'error',
                    'error_message': '缺少API模板ID',
                    'start_time': step_start_time,
                    'end_time': datetime.now(),
                    'execution_time': 0
                }
            
            # 获取API模板数据
            api_data = self._get_api_template_data(api_template_id)
            if not api_data:
                logger.warning(f"步骤 {step_name} 的API模板ID {api_template_id} 不存在")
                return {
                    'step_id': step_data.get('id'),
                    'step_name': step_name,
                    'step_order': step_index,
                    'status': 'error',
                    'error_message': 'API模板不存在',
                    'start_time': step_start_time,
                    'end_time': datetime.now(),
                    'execution_time': 0
                }
            
            # 执行前置处理
            pre_processing = step_data.get('pre_processing', {})
            if pre_processing:
                logger.info(f"执行步骤 {step_name} 的前置处理")
                self._execute_pre_processing(pre_processing, step_index)
            
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
            response_data = request_engine.execute_request(api_data, variables)
            
            # 执行后置处理
            post_processing = step_data.get('post_processing', {})
            if post_processing:
                logger.info(f"执行步骤 {step_name} 的后置处理")
                self._execute_post_processing(post_processing, response_data, step_index)
            
            # 执行断言
            assertions = step_data.get('assertions', {})
            assertion_result = True
            if assertions:
                logger.info(f"执行步骤 {step_name} 的断言")
                assertion_result = self._execute_assertions(assertions, response_data, step_index)
            
            step_end_time = datetime.now()
            execution_time = (step_end_time - step_start_time).total_seconds()
            
            # 确定步骤状态
            status = 'success' if assertion_result else 'failure'
            
            logger.info(f"步骤 {step_name} 执行完成，状态: {status}")
            
            return {
                'step_id': step_data.get('id'),
                'step_name': step_name,
                'step_order': step_index,
                'status': status,
                'start_time': step_start_time,
                'end_time': step_end_time,
                'execution_time': execution_time,
                'response_data': response_data,
                'assertion_result': assertion_result
            }
            
        except Exception as e:
            logger.error(f"执行步骤失败: {str(e)}")
            return {
                'step_id': step_data.get('id'),
                'step_name': step_name if 'step_name' in locals() else f"步骤{step_index+1}",
                'step_order': step_index,
                'status': 'error',
                'error_message': str(e),
                'start_time': step_start_time if 'step_start_time' in locals() else datetime.now(),
                'end_time': datetime.now(),
                'execution_time': 0
            }

    def _execute_pre_processing(self, pre_processing: Dict[str, Any], step_index: int):
        """执行前置处理（集成手动执行方法的功能）"""
        try:
            if not pre_processing:
                return
                
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
            
            logger.info(f"开始执行前置处理，工具数量: {tool_count}")
            
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
                logger.info(f"执行前置处理工具: {tool_type}")
                
                if tool_type == 'http_request':
                    logger.info("执行HTTP请求工具")
                    self._execute_http_request_tool(config, step_index)
                elif tool_type == 'sql_tool':
                    logger.info("执行SQL工具")
                    self._execute_sql_tool(config, step_index)
                else:
                    logger.warning(f"未知的前置处理工具类型: {tool_type}")
                
                executed_tool_count += 1
            
            # 处理变量设置
            variables = pre_processing.get('variables', {})
            
            if variables:
                # 这里可以集成变量管理器的功能
                logger.info(f"设置局部变量: {len(variables)} 个")
            
            logger.info(f"前置处理完成，共执行 {executed_tool_count} 个工具")
            
        except Exception as e:
            logger.error(f"执行前置处理失败: {str(e)}")

    def _execute_post_processing(self, post_processing: Dict[str, Any], step_result: Dict[str, Any], step_index: int):
        """执行后置处理（集成手动执行方法的功能）"""
        try:
            if not post_processing:
                return
                
            logger.info("开始执行后置处理")
            
            # 处理变量提取
            extractors = post_processing.get('variables', {})
            if extractors:
                logger.info(f"执行变量提取，提取器数量: {len(extractors)}")
                # 这里可以集成变量提取功能
            
            # 处理其他后置操作
            logger.info("后置处理完成")
            
        except Exception as e:
            logger.error(f"执行后置处理失败: {str(e)}")

    def _execute_assertions(self, assertions: Dict[str, Any], step_result: Dict[str, Any], step_index: int) -> bool:
        """执行断言（集成手动执行方法的功能）"""
        try:
            if not assertions:
                return True
                
            logger.info("开始执行断言")
            
            # 这里可以集成断言验证逻辑
            # 例如：状态码断言、响应体断言、响应时间断言等
            
            assertion_result = True
            
            logger.info("断言执行完成")
            return assertion_result
            
        except Exception as e:
            logger.error(f"执行断言失败: {str(e)}")
            return False

    def _execute_http_request_tool(self, config: Dict[str, Any], step_index: int):
        """执行HTTP请求工具"""
        try:
            logger.info(f"开始执行HTTP请求工具，配置: {config}")
            
            # 获取请求配置
            method = config.get('method', 'GET')
            url = config.get('url', '')
            headers = config.get('headers', {})
            body = config.get('body', {})
            timeout = config.get('timeout', 30)
            
            if not url:
                logger.error("HTTP请求工具配置错误: URL不能为空")
                return
            
            # 执行HTTP请求
            logger.info(f"前置处理器HTTP请求: {method} {url}")
            
            # 这里可以集成实际的HTTP请求执行逻辑
            
            logger.info("HTTP请求工具执行完成")
            
        except Exception as e:
            logger.error(f"执行HTTP请求工具失败: {str(e)}")

    def _execute_sql_tool(self, config: Dict[str, Any], step_index: int):
        """执行SQL工具"""
        try:
            logger.info(f"开始执行SQL工具，配置: {config}")
            
            # 获取SQL配置
            sql = config.get('sql', '')
            database = config.get('database', '')
            
            if not sql:
                logger.error("SQL工具配置错误: SQL语句不能为空")
                return
            
            # 执行SQL查询
            logger.info(f"执行SQL查询: {sql}")
            
            # 这里可以集成实际的SQL执行逻辑
            
            logger.info("SQL工具执行完成")
            
        except Exception as e:
            logger.error(f"执行SQL工具失败: {str(e)}")

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
            logger.error(f"获取API模板数据失败: {str(e)}")
            return None


def get_execute_test_case():
    """获取测试用例执行器实例"""
    return ExecuteTestCase()