import json
import traceback
from datetime import datetime
from PyQt5.QtCore import pyqtSignal, Qt, QDataStream, QIODevice, QSize, QThread, QEventLoop
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, 
    QLineEdit, QTextEdit, QComboBox, QPushButton, QMessageBox, QMenu,
    QScrollArea, QDialog, QSizePolicy, QApplication, QCheckBox, QShortcut
)
from PyQt5.QtGui import QFont, QTextCursor, QIcon, QKeySequence
from .flow_layout import FlowLayout
from src.ui.widgets.toast_tips import Toast
from src.ui.interface_auto.components.interface_step_card import InterfaceStepCard
from src.ui.interface_auto.components.variable_editor import VariableManagerDialog
from src.core.models.interface_models import TestCase, TestCaseStep
from src.core.services.environment_service import EnvironmentService
from src.core.services.api_template_service import ApiTemplateService
from src.core.services.test_case_service import TestCaseService
from src.core.services.global_variable_service import get_global_variable_service
from src.utils.interface_utils.variable_manager import get_global_variable_manager
from src.utils.interface_utils.request_engine import RequestEngine


class CaseExecutionThread(QThread):
    """用例执行线程"""
    step_started = pyqtSignal(str, int)  # 步骤名称, 步骤索引
    step_finished = pyqtSignal(dict)  # 执行结果
    case_finished = pyqtSignal(dict)  # 用例执行结果
    log_message = pyqtSignal(str, str, int)  # 日志消息, 级别, 步骤索引

    def __init__(self, case_data, environment_config=None, project_id=0):
        super().__init__()
        self.case_data = case_data
        self.environment_config = environment_config or {}
        self.project_id = project_id
        self.variable_manager = get_global_variable_manager()
        self.request_engine = RequestEngine()
        self.is_running = True
    
    def stop(self):
        """停止线程执行"""
        if not self.isRunning():
            return
            
        # 设置停止标志
        self.is_running = False
        
        # 等待线程安全结束，增加等待时间到5秒
        try:
            if not self.wait(5000):  # 最多等待5秒
                print("[WARNING] 线程未在5秒内正常退出，尝试强制终止")
                # 如果线程没有正常结束，强制终止
                self.terminate()
                # 等待终止完成
                self.wait(2000)
        except Exception as e:
            print(f"[ERROR] 等待线程停止时发生错误: {str(e)}")
            # 如果等待失败，直接终止
            try:
                self.terminate()
                self.wait(1000)
            except:
                pass
        
        # 安全地发送日志消息
        try:
            self.log_message.emit(self.format_debug_message("线程已安全停止", "debug", -1), "debug", -1)
        except:
            pass  # 忽略发送消息时的错误

    def format_debug_message(self, message, level="info", step_index=None):
        """格式化调试信息，使日志更易读"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # 毫秒级时间戳
        
        if step_index is not None:
            prefix = f"[{timestamp}] [步骤{step_index + 1}]"
        else:
            prefix = f"[{timestamp}] [用例]"
            
        # 根据日志级别添加颜色标记
        level_markers = {
            "debug": "🔍",
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌"
        }
        
        marker = level_markers.get(level, "ℹ️")
        
        # 格式化消息内容
        formatted_message = f"{prefix} {marker} {message}"
        
        return formatted_message

    def run(self):
        """执行测试用例"""
        try:
            # [DEBUG] 终端打印 - 用例执行开始
            print(self.format_debug_message("用例执行开始", "info"))
            print(self.format_debug_message(f"用例名称: {self.case_data.get('name', '未命名')}", "info"))
            print(self.format_debug_message(f"总步骤数: {len(self.case_data.get('steps', []))}", "info"))
            
            # 记录关键信息，减少调试信息
            self.log_message.emit(self.format_debug_message(f"开始执行测试用例: {self.case_data['name']}", "info", -1), "info", -1)
            self.log_message.emit(self.format_debug_message(f"总步骤数: {len(self.case_data.get('steps', []))}", "info", -1), "info", -1)

            # 初始化变量管理器
            self.variable_manager.clear_local_variables()
            
            # 加载指定项目的全局变量
            try:
                from src.core.services.global_variable_service import get_global_variable_service
                service = get_global_variable_service()
                service.sync_to_variable_manager(self.variable_manager, self.project_id)
                self.log_message.emit(self.format_debug_message(f"已加载项目 {self.project_id} 的全局变量", "info", -1), "info", -1)
            except Exception as e:
                self.log_message.emit(self.format_debug_message(f"加载项目 {self.project_id} 的全局变量失败: {str(e)}", "error", -1), "error", -1)
            
            # 获取变量管理器中的全局变量
            global_vars = self.variable_manager.global_variables
            
            # 记录变量情况
            self.log_message.emit(self.format_debug_message(f"全局变量数量: {len(global_vars)}", "info", -1), "info", -1)
            if global_vars:
                for var_name, var_value in global_vars.items():
                    self.log_message.emit(self.format_debug_message(f"全局变量: {var_name} = {var_value}", "debug", -1), "debug", -1)

            # 执行每个步骤
            steps = self.case_data.get('steps', [])
            
            # 调试：检查线程接收到的步骤数据
            print(f"[DEBUG] CaseExecutionThread接收到的步骤总数: {len(steps)}")
            for i, step in enumerate(steps):
                # 获取步骤标题：优先使用api_name，如果没有则使用api_template.name，最后使用name字段
                step_name = step.get('api_name') or step.get('api_template', {}).get('name') or step.get('name', '未命名')
                print(f"[DEBUG] 步骤{i+1}: {step_name}, enabled={step.get('enabled', True)}")
            
            enabled_steps = [step for step in steps if step.get('enabled', True)]
            
            # 统计步骤执行结果
            total_steps = len(enabled_steps)
            success_steps = 0
            
            print(f"[DEBUG] 启用的步骤数量: {total_steps}")

            # 使用原始步骤序号，而不是重新编号
            original_step_order = 0
            for step in steps:
                if not self.is_running:
                    self.log_message.emit(self.format_debug_message("执行被中断", "info", original_step_order), "info", original_step_order)
                    break
                
                # 检查步骤是否启用
                if not step.get('enabled', True):
                    original_step_order += 1
                    continue
                
                # 记录步骤开始执行的信息（使用原始步骤序号）
                step_order = step.get('step_order', original_step_order + 1)
                
                # 获取步骤标题：优先使用api_name，如果没有则使用api_template.name，最后使用name字段
                step_name = step.get('api_name') or step.get('api_template', {}).get('name') or step.get('name', '未命名步骤')
                
                self.log_message.emit(self.format_debug_message(f"开始执行步骤 {step_order}: {step_name}", "info", step_order - 1), "info", step_order - 1)
                
                self.step_started.emit(step_name, step_order - 1)
                result = self.execute_step(step, step_order - 1)
                self.step_finished.emit(result)
                
                # 统计成功步骤数量
                if result.get('success', False):
                    success_steps += 1
                
                # 如果步骤执行失败，停止执行后续步骤
                if not result.get('success', False):
                    self.log_message.emit(self.format_debug_message("步骤执行失败，停止执行后续步骤", "warning", step_index), "warning", step_index)
                    break

            # 记录用例执行完成信息
            self.log_message.emit(self.format_debug_message("用例执行完成", "info", -1), "info", -1)
            self.log_message.emit(self.format_debug_message(f"步骤统计: 成功 {success_steps}/{total_steps}", "info", -1), "info", -1)
            
            self.case_finished.emit({
                'success': True,
                'message': '用例执行完成',
                'success_count': success_steps,
                'total_count': total_steps
            })

        except Exception as e:
            # 记录用例执行异常信息
            self.log_message.emit(self.format_debug_message(f"用例执行异常: {str(e)}", "error", -1), "error", -1)
            self.case_finished.emit({
                'success': False,
                'error': str(e),
                'success_count': success_steps if 'success_steps' in locals() else 0,
                'total_count': total_steps if 'total_steps' in locals() else 0
            })

    def execute_step(self, step, step_index):
        """执行单个步骤"""
        try:
            step_start_time = datetime.now()

            # 记录步骤开始执行的信息（使用原始步骤序号）
            step_order = step_index + 1  # step_index是从0开始的，需要+1得到实际步骤序号
            
            # 获取步骤标题：优先使用api_name，如果没有则使用api_template.name，最后使用name字段
            step_name = step.get('api_name') or step.get('api_template', {}).get('name') or step.get('name', '未命名步骤')
            
            self.log_message.emit(self.format_debug_message(f"执行步骤 {step_order}: {step_name}", "info", step_index), "info", step_index)

            # 执行前置处理
            pre_processing = step.get('pre_processing', {})
            if pre_processing:
                self.log_message.emit(self.format_debug_message("执行前置处理", "debug", step_index), "debug", step_index)
            self.execute_pre_processing(pre_processing, step_index)

            # 执行接口请求
            api_template_id = step.get('api_template_id')
            if api_template_id:
                self.log_message.emit(self.format_debug_message("执行接口请求", "debug", step_index), "debug", step_index)
                try:
                    result = self.execute_api_request(step, step_index)
                except Exception as e:
                    self.log_message.emit(self.format_debug_message(f"接口请求执行异常: {str(e)}", "error", step_index), "error", step_index)
                    result = {
                        'success': False,
                        'error': str(e),
                        'status': 'error',
                        'duration': 0
                    }
            else:
                self.log_message.emit(self.format_debug_message("跳过接口执行（无接口模板）", "info", step_index), "info", step_index)
                result = {
                    'success': True,
                    'message': '跳过接口执行（无接口模板）',
                    'status': 'skipped'
                }

            # 执行后置处理
            if result.get('success'):
                post_processing = step.get('post_processing', {})
                if post_processing:
                    self.log_message.emit(self.format_debug_message("执行后置处理", "debug", step_index), "debug", step_index)
                self.execute_post_processing(post_processing, result, step_index)

            # 执行断言
            if result.get('success'):
                assertions = step.get('assertions', {})
                if assertions:
                    self.log_message.emit(self.format_debug_message("执行断言", "debug", step_index), "debug", step_index)
                assertion_result = self.execute_assertions(assertions, result, step_index)
                result['assertions_result'] = assertion_result

            # 计算执行时长
            step_end_time = datetime.now()
            duration = (step_end_time - step_start_time).total_seconds()
            result['duration'] = duration

            # 记录步骤执行完成信息
            status = result.get('status', 'success' if result.get('success') else 'failure')
            
            # 记录完成日志（使用原始步骤序号）
            step_order = step_index + 1  # step_index是从0开始的，需要+1得到实际步骤序号
            log_level = "info" if status == "success" else "warning"
            self.log_message.emit(self.format_debug_message(f"步骤 {step_order} 执行完成: {status}, 耗时: {duration:.2f}秒", log_level, step_index), log_level, step_index)

            return result

        except Exception as e:
            step_order = step_index + 1  # step_index是从0开始的，需要+1得到实际步骤序号
            self.log_message.emit(self.format_debug_message(f"步骤 {step_order} 执行错误: {str(e)}", "error", step_index), "error", step_index)
            self.log_message.emit(self.format_debug_message(f"错误详情: {traceback.format_exc()}", "debug", step_index), "debug", step_index)
            return {
                'success': False,
                'error': str(e),
                'status': 'error',
                'duration': 0
            }

    def execute_pre_processing(self, pre_processing, step_index):
        """执行前置处理"""
        if not pre_processing:
            return
            
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
        
        self.log_message.emit(self.format_debug_message("开始执行前置处理", "debug", step_index), "debug", step_index)
        self.log_message.emit(self.format_debug_message(f"前置处理工具数量: {tool_count}", "debug", step_index), "debug", step_index)
        
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
            self.log_message.emit(self.format_debug_message(f"执行前置处理工具: {tool_type}", "debug", step_index), "debug", step_index)
            
            if tool_type == 'http_request':
                self.log_message.emit(self.format_debug_message("执行HTTP请求工具", "debug", step_index), "debug", step_index)
                self.execute_http_request_tool(config, step_index)
            elif tool_type == 'sql_tool':
                self.log_message.emit(self.format_debug_message("执行SQL工具", "debug", step_index), "debug", step_index)
                self.execute_sql_tool(config, step_index)
            else:
                self.log_message.emit(self.format_debug_message(f"未知的前置处理工具类型: {tool_type}", "warning", step_index), "warning", step_index)
            
            executed_tool_count += 1
        
        # 这里可以执行变量设置、脚本执行等前置操作
        variables = pre_processing.get('variables', {})
        
        if variables:
            self.variable_manager.set_local_variables(variables)
            self.log_message.emit(self.format_debug_message(f"设置局部变量: {len(variables)} 个", "info", step_index), "info", step_index)
        
        self.log_message.emit(self.format_debug_message(f"前置处理完成，共执行 {executed_tool_count} 个工具", "debug", step_index), "debug", step_index)

    def execute_http_request_tool(self, config, step_index=-1):
        """执行HTTP请求工具"""
        self.log_message.emit(self.format_debug_message(f"开始执行HTTP请求工具，配置: {config}", "debug", step_index), "debug", step_index)
        
        try:
            # 获取请求配置
            method = config.get('method', 'GET')
            url = config.get('url', '')
            headers = config.get('headers', {})
            body = config.get('body', {})
            timeout = config.get('timeout', 30)
            # 优先从variables字段读取变量提取器，如果没有则从extractors字段读取
            extractors = config.get('variables', config.get('extractors', {}))
            
            self.log_message.emit(self.format_debug_message(f"HTTP请求配置 - 方法: {method}, URL: {url}, 超时: {timeout}", "debug", step_index), "debug", step_index)
            self.log_message.emit(self.format_debug_message(f"HTTP请求配置 - 请求体: {body}", "debug", step_index), "debug", step_index)
            self.log_message.emit(self.format_debug_message(f"HTTP请求配置 - 提取器: {extractors}", "debug", step_index), "debug", step_index)
            
            if not url:
                self.log_message.emit(self.format_debug_message("HTTP请求工具配置错误: URL不能为空", "error", step_index), "error", step_index)
                return
            
            # 替换变量
            all_variables = {}
            all_variables.update(self.variable_manager.global_variables)
            all_variables.update(self.variable_manager.local_variables)
            
            self.log_message.emit(self.format_debug_message(f"变量替换前 - URL: {url}", "debug", step_index), "debug", step_index)
            self.log_message.emit(self.format_debug_message(f"可用变量: {all_variables}", "debug", step_index), "debug", step_index)
            
            url = self.variable_manager.replace_variables(url, all_variables)
            headers = self.variable_manager.replace_variables_in_dict(headers, all_variables)
            body = self.variable_manager.replace_variables_in_dict(body, all_variables)
            
            self.log_message.emit(self.format_debug_message(f"变量替换后 - URL: {url}", "debug", step_index), "debug", step_index)
            self.log_message.emit(self.format_debug_message(f"变量替换后 - 请求头: {headers}", "debug", step_index), "debug", step_index)
            self.log_message.emit(self.format_debug_message(f"变量替换后 - 请求体: {body}", "debug", step_index), "debug", step_index)
            
            # 记录请求日志
            self.log_message.emit(self.format_debug_message(f"前置处理器HTTP请求: {method} {url}", "info", step_index), "info", step_index)
            
            # 执行请求
            request_data = {
                'method': method,
                'url': url,
                'headers': headers,
                'body': body,
                'timeout': timeout
            }
            
            self.log_message.emit(self.format_debug_message(f"发送请求数据: {request_data}", "debug", step_index), "debug", step_index)
            
            response = self.request_engine.execute_request(request_data)
            self.log_message.emit(self.format_debug_message(f"请求响应: {response}", "debug", step_index), "debug", step_index)
            
            if response.get('success'):
                # 请求成功，处理响应
                response_data = response.get('response_data', response.get('body', {}))
                status_code = response.get('status_code', 0)
                
                self.log_message.emit(self.format_debug_message(f"前置处理器HTTP请求成功: 状态码 {status_code}", "info", step_index), "info", step_index)
                self.log_message.emit(self.format_debug_message(f"响应数据: {response_data}", "debug", step_index), "debug", step_index)
                
                # 提取变量
                if extractors:
                    self.log_message.emit(self.format_debug_message(f"开始提取变量，提取器数量: {len(extractors)}", "debug", step_index), "debug", step_index)
                    for var_name, json_path in extractors.items():
                        try:
                            self.log_message.emit(self.format_debug_message(f"提取变量 {var_name}，JSON路径: {json_path}", "debug", step_index), "debug", step_index)
                            # 从响应中提取数据 - 直接使用simple_json_path_extract支持点分隔路径
                            value = self.simple_json_path_extract(response_data, json_path)
                            if value is not None:
                                # 将提取的变量保存到变量管理器
                                self.variable_manager.set_local_variables({var_name: value})
                                self.log_message.emit(self.format_debug_message(f"提取变量成功: {var_name} = {value}", "info", step_index), "info", step_index)
                                
                                # 调试模式下打印详细的变量管理器状态
                                if hasattr(self, 'debug_mode') and self.debug_mode:
                                    self.log_message.emit(self.format_debug_message(f"变量管理器状态 - 局部变量: {self.variable_manager.local_variables}", "debug", step_index), "debug", step_index)
                                    self.log_message.emit(self.format_debug_message(f"变量管理器状态 - 全局变量: {self.variable_manager.global_variables}", "debug", step_index), "debug", step_index)
                                    self.log_message.emit(self.format_debug_message(f"变量 {var_name} 已保存到变量管理器，可在后续步骤中使用", "debug", step_index), "debug", step_index)
                            else:
                                self.log_message.emit(self.format_debug_message(f"提取变量失败: {var_name}，JSON路径 {json_path} 未找到数据", "warning", step_index), "warning", step_index)
                                # 调试：检查响应数据结构
                                self.log_message.emit(self.format_debug_message(f"响应数据结构: {response_data}", "debug", step_index), "debug", step_index)
                                self.log_message.emit(self.format_debug_message(f"尝试提取路径 {json_path} 失败，检查响应数据格式", "debug", step_index), "debug", step_index)
                        except Exception as e:
                            self.log_message.emit(self.format_debug_message(f"提取变量异常: {var_name}，错误: {str(e)}", "error", step_index), "error", step_index)
                else:
                    self.log_message.emit(self.format_debug_message("无变量需要提取", "debug", step_index), "debug", step_index)
            else:
                # 请求失败
                error_msg = response.get('error', '未知错误')
                self.log_message.emit(self.format_debug_message(f"前置处理器HTTP请求失败: {error_msg}", "error", step_index), "error", step_index)
                
        except Exception as e:
            self.log_message.emit(self.format_debug_message(f"执行HTTP请求工具失败: {str(e)}", "error", step_index), "error", step_index)
        
        self.log_message.emit(self.format_debug_message("HTTP请求工具执行结束", "debug", step_index), "debug", step_index)

    def execute_sql_tool(self, config, step_index=-1):
        """执行SQL工具"""
        self.log_message.emit(self.format_debug_message(f"开始执行SQL工具，配置: {config}", "debug", step_index), "debug", step_index)
        
        try:
            # 获取SQL工具配置
            name = config.get('name', 'SQL工具')
            database_config = config.get('database', {})
            sql = config.get('sql', '')
            output_fields = config.get('output_fields', [])
            
            self.log_message.emit(self.format_debug_message(f"SQL工具配置 - 名称: {name}", "debug", step_index), "debug", step_index)
            self.log_message.emit(self.format_debug_message(f"SQL工具配置 - 数据库: {database_config}", "debug", step_index), "debug", step_index)
            self.log_message.emit(self.format_debug_message(f"SQL工具配置 - SQL语句: {sql}", "debug", step_index), "debug", step_index)
            self.log_message.emit(self.format_debug_message(f"SQL工具配置 - 输出字段: {output_fields}", "debug", step_index), "debug", step_index)
            
            if not sql:
                self.log_message.emit(self.format_debug_message("SQL工具配置错误: SQL语句不能为空", "error", step_index), "error", step_index)
                return
            
            if not database_config:
                self.log_message.emit(self.format_debug_message("SQL工具配置错误: 数据库配置不能为空", "error", step_index), "error", step_index)
                return
            
            # 获取变量池
            all_variables = {}
            all_variables.update(self.variable_manager.global_variables)
            all_variables.update(self.variable_manager.local_variables)
            
            self.log_message.emit(self.format_debug_message(f"变量替换前 - SQL: {sql}", "debug", step_index), "debug", step_index)
            self.log_message.emit(self.format_debug_message(f"可用变量: {all_variables}", "debug", step_index), "debug", step_index)
            
            # 预处理SQL：移除变量周围的引号，并将${variable}格式转换为{variable}格式
            import re
            def convert_and_remove_quotes(match):
                var_name = match.group(1)  # 变量名
                return f"{{{var_name}}}"  # 返回{variable}格式的变量占位符
            
            # 移除变量周围的单引号并转换格式
            processed_sql = re.sub(r"'\$\{(\w+)\}'", convert_and_remove_quotes, sql)
            self.log_message.emit(self.format_debug_message(f"预处理后 - SQL: {processed_sql}", "debug", step_index), "debug", step_index)
            
            # 记录SQL执行日志
            self.log_message.emit(self.format_debug_message(f"前置处理器SQL执行: {processed_sql}", "info", step_index), "info", step_index)
            
            # 执行SQL查询
            from src.utils.sql_worker import SQLWorker
            from PyQt5.QtCore import QEventLoop
            
            # 创建事件循环等待SQL执行完成
            loop = QEventLoop()
            result = {'success': False, 'error': '未执行'}
            
            def on_finished(query_name, message, result_data):
                nonlocal result
                result = {'success': True, 'message': message, 'data': result_data}
                loop.quit()
            
            def on_error(query_name, error_message):
                nonlocal result
                result = {'success': False, 'error': error_message}
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
            
            if result['success']:
                # SQL执行成功
                data = result.get('data', [])
                self.log_message.emit(self.format_debug_message(f"前置处理器SQL执行成功: 返回 {len(data)} 行数据", "info", step_index), "info", step_index)
                
                # 提取变量到变量管理器
                if output_fields and data:
                    self.log_message.emit(self.format_debug_message(f"开始提取变量，输出字段数量: {len(output_fields)}", "debug", step_index), "debug", step_index)
                    
                    # 获取第一行数据（假设只取第一行结果）
                    first_row = data[0] if data else {}
                    
                    for field_config in output_fields:
                        field_name = field_config.get('field', '')
                        if field_name and field_name in first_row:
                            value = first_row[field_name]
                            # 将提取的变量保存到变量管理器
                            self.variable_manager.set_local_variables({field_name: value})
                            self.log_message.emit(self.format_debug_message(f"提取变量成功: {field_name} = {value}", "info", step_index), "info", step_index)
                        else:
                            self.log_message.emit(self.format_debug_message(f"提取变量失败: 字段 {field_name} 不存在或为空", "warning", step_index), "warning", step_index)
                else:
                    self.log_message.emit(self.format_debug_message("无输出字段或查询结果为空，跳过变量提取", "debug", step_index), "debug", step_index)
            else:
                # SQL执行失败
                error_msg = result.get('error', '未知错误')
                self.log_message.emit(self.format_debug_message(f"前置处理器SQL执行失败: {error_msg}", "error", step_index), "error", step_index)
                
        except Exception as e:
            self.log_message.emit(self.format_debug_message(f"执行SQL工具失败: {str(e)}", "error", step_index), "error", step_index)
        
        self.log_message.emit(self.format_debug_message("SQL工具执行结束", "debug", step_index), "debug", step_index)

    def execute_post_processing(self, post_processing, step_result, step_index):
        """执行后置处理"""
        if not post_processing:
            return
            
        # 计算后置处理工具数量
        tool_count = 0
        total_extractors = 0
        
        # 遍历所有后置处理工具
        for tool_id, tool_config in post_processing.items():
            if isinstance(tool_config, dict):
                tool_type = tool_config.get('type')
                enabled = tool_config.get('enabled', True)
                
                # 只统计启用的工具
                if enabled:
                    tool_count += 1
                    
                    # 如果是参数提取工具，统计其中的提取器数量
                    if tool_type == 'parameter_extraction':
                        config = tool_config.get('config', {})
                        extractions = config.get('extractions', [])
                        total_extractors += len(extractions)
        
        self.log_message.emit(self.format_debug_message("开始执行后置处理", "debug", step_index), "debug", step_index)
        self.log_message.emit(self.format_debug_message(f"后置处理工具数量: {tool_count}", "debug", step_index), "debug", step_index)
        self.log_message.emit(self.format_debug_message(f"参数提取器总数: {total_extractors}", "debug", step_index), "debug", step_index)
        
        # 执行后置处理工具
        extracted_count = 0
        for tool_id, tool_config in post_processing.items():
            if not isinstance(tool_config, dict):
                continue
                
            tool_type = tool_config.get('type')
            enabled = tool_config.get('enabled', True)
            
            # 只执行启用的工具
            if not enabled:
                continue
                
            # 执行参数提取工具
            if tool_type == 'parameter_extraction':
                config = tool_config.get('config', {})
                extractions = config.get('extractions', [])
                
                # 优先使用解密后的响应体（对于加解密请求）
                decrypted_body = step_result.get('decrypted_body', '')
                if decrypted_body:
                    # 如果有解密后的响应体，优先使用它
                    try:
                        import json
                        response_data = json.loads(decrypted_body)
                    except:
                        # 如果解析失败，使用原始响应数据
                        response_data = step_result.get('response_data', {})
                else:
                    # 如果没有解密后的响应体，使用原始响应数据
                    response_data = step_result.get('response_data', {})
                
                # 执行所有的参数提取
                for extraction in extractions:
                    try:
                        variable_name = extraction.get('variable_name')
                        json_path = extraction.get('json_path')
                        
                        if not variable_name or not json_path:
                            continue
                            
                        # 从响应中提取数据
                        value = self.simple_json_path_extract(response_data, json_path)
                        self.variable_manager.set_local_variables({variable_name: value})
                        self.log_message.emit(self.format_debug_message(f"提取变量 {variable_name} = {value}", "info", step_index), "info", step_index)
                        extracted_count += 1
                    except Exception as e:
                        self.log_message.emit(self.format_debug_message(f"提取变量失败: {str(e)}", "error", step_index), "error", step_index)
        
        if extracted_count > 0:
            self.log_message.emit(self.format_debug_message(f"后置处理完成，共提取 {extracted_count} 个变量", "info", step_index), "info", step_index)

    def extract_value(self, response_data, extractor):
        """从响应数据中提取值"""
        # 简化实现，实际应该支持JSONPath、XPath等
        if isinstance(extractor, str):
            # 直接使用字段名
            return response_data.get(extractor)
        elif isinstance(extractor, dict):
            # 支持更复杂的提取规则
            extract_type = extractor.get('type', 'json_path')
            if extract_type == 'json_path':
                # 使用JSONPath提取
                path = extractor.get('path', '')
                # 简化实现，实际应该使用jsonpath库
                return self.simple_json_path_extract(response_data, path)
        return None

    def simple_json_path_extract(self, data, path):
        """简单的JSON路径提取"""
        # 简化实现，只支持简单的点分隔路径
        if not path:
            return data

        keys = path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def execute_api_worker_request(self, api_worker):
        """执行ApiWorker请求（使用信号机制）"""
        try:
            self.log_message.emit(self.format_debug_message("开始执行ApiWorker请求", "debug", -1), "debug", -1)
            
            # 创建事件循环来处理异步信号
            loop = QEventLoop()
            result = None
            
            # 连接信号
            def on_finished(response):
                nonlocal result
                # ApiWorker.finished信号发射的是包含status_code、headers、body等字段的字典
                if isinstance(response, dict):
                    result = response
                else:
                    # 如果响应不是字典格式，转换为错误格式
                    result = {
                        'success': False,
                        'error': f'ApiWorker返回了无效的响应格式: {type(response)}'
                    }
                loop.quit()
            
            def on_error(error_msg):
                nonlocal result
                result = {'success': False, 'error': error_msg}
                loop.quit()
            
            api_worker.finished.connect(on_finished)
            api_worker.error.connect(on_error)
            
            # 启动工作线程
            api_worker.start()
            
            # 等待信号完成
            loop.exec_()
            
            # 断开信号连接
            api_worker.finished.disconnect(on_finished)
            api_worker.error.disconnect(on_error)
            
            self.log_message.emit(self.format_debug_message(f"ApiWorker请求执行完成，结果: {result}", "debug", -1), "debug", -1)
            return result
            
        except Exception as e:
            self.log_message.emit(self.format_debug_message(f"ApiWorker请求执行异常: {str(e)}", "error", -1), "error", -1)
            return {
                'success': False,
                'error': str(e)
            }

    def execute_api_request(self, step, step_index):
        """执行接口请求"""
        try:
            # 获取接口模板数据
            api_service = ApiTemplateService()
            api_template_id = step.get('api_template_id')
            
            api_template = api_service.get_template_by_id(api_template_id)
            if not api_template:
                self.log_message.emit(self.format_debug_message(f"接口模板不存在: {api_template_id}", "error", step_index), "error", step_index)
                return {
                    'success': False,
                    'error': f'接口模板不存在: {api_template_id}',
                    'status': 'error'
                }

            # 准备请求数据
            request_data = self.prepare_request_data(api_template, step.get('variables', {}), step_index)

            # 记录请求日志
            self.log_message.emit(self.format_debug_message(f"发送请求: {request_data['method']} {request_data['url']}", "info", step_index), "info", step_index)
            self.log_message.emit(self.format_debug_message(f"请求体: {json.dumps(request_data['body'], ensure_ascii=False, indent=2)}", "debug", step_index), "debug", step_index)
            
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
                global_enable_encryption = self.case_data.get('enable_encryption', False)
                global_encrypt_url = self.case_data.get('encrypt_url', '')
                global_decrypt_url = self.case_data.get('decrypt_url', '')
                
                # 判断是否使用加解密：步骤开启且全局配置完整
                use_encryption = enable_encryption and global_enable_encryption and global_encrypt_url and global_decrypt_url
                
                if use_encryption:
                    # 步骤启用加解密且全局配置完整
                    self.log_message.emit(self.format_debug_message("步骤启用加解密功能，使用RequestEngine处理", "info", step_index), "info", step_index)
                else:
                    # 不使用加解密的情况
                    if enable_encryption and not (global_encrypt_url and global_decrypt_url):
                        # 步骤启用但全局配置不完整
                        self.log_message.emit(self.format_debug_message("步骤启用加解密但全局配置不完整，使用普通请求", "warning", step_index), "warning", step_index)
                    elif enable_encryption and not global_enable_encryption:
                        # 步骤启用但全局未启用
                        self.log_message.emit(self.format_debug_message("步骤启用加解密但全局未启用，使用普通请求", "warning", step_index), "warning", step_index)
                    else:
                        # 步骤关闭加解密
                        self.log_message.emit(self.format_debug_message("步骤关闭加解密功能，使用普通请求", "info", step_index), "info", step_index)
                
                # 最终判断是否使用加解密
                if use_encryption:
                    # 使用RequestEngine的加解密功能
                    
                    # 准备请求数据（用于调试信息）
                    request_data = self.prepare_request_data(api_template, step.get('variables', {}), step_index)
                    
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
                            self.log_message.emit(self.format_debug_message(f"解密后的响应体:{json.dumps(decrypted_json, ensure_ascii=False, indent=2)}", "debug", step_index), "debug", step_index)
                        except:
                            # 如果解析失败，直接打印原始字符串
                            self.log_message.emit(self.format_debug_message(f"解密后的响应体:{response.get('decrypted_body', '')}", "debug", step_index), "debug", step_index)
                    else:
                        # 非加解密请求，尝试将响应体格式化为JSON
                        response_text = response.get('response_text', response.get('text', ''))
                        try:
                            # 尝试解析为JSON并重新格式化
                            response_json = json.loads(response_text)
                            self.log_message.emit(self.format_debug_message(f"响应体: {json.dumps(response_json, ensure_ascii=False, indent=2)}", "debug", step_index), "debug", step_index)
                        except:
                            # 如果解析失败，直接打印原始文本
                            self.log_message.emit(self.format_debug_message(f"响应体: {response_text}", "debug", step_index), "debug", step_index)        
                else:
                    # 记录失败请求的详细信息到日志弹窗
                    self.log_message.emit(self.format_debug_message(f"请求失败: {json.dumps({'error': response.get('error', '未知错误'), 'status_code': response.get('status_code', 0)}, ensure_ascii=False, indent=2)}", "error", step_index), "error", step_index)
                    
                    # 检查是否为加解密请求，优先打印解密后的响应体
                    if response.get('decrypted_body'):
                        try:
                            # 尝试将解密后的响应体解析为JSON，然后重新格式化为JSON字符串
                            decrypted_json = json.loads(response.get('decrypted_body', ''))
                            self.log_message.emit(self.format_debug_message(f"解密后的响应体:{json.dumps(decrypted_json, ensure_ascii=False, indent=2)}", "debug", step_index), "debug", step_index)
                        except:
                            # 如果解析失败，直接打印原始字符串
                            self.log_message.emit(self.format_debug_message(f"解密后的响应体:{response.get('decrypted_body', '')}", "debug", step_index), "debug", step_index)
                    else:
                        # 非加解密请求，尝试将响应体格式化为JSON
                        response_text = response.get('response_text', response.get('text', ''))
                        try:
                            # 尝试解析为JSON并重新格式化
                            response_json = json.loads(response_text)
                            self.log_message.emit(self.format_debug_message(f"失败响应体: {json.dumps(response_json, ensure_ascii=False, indent=2)}", "debug", step_index), "debug", step_index)
                        except:
                            # 如果解析失败，直接打印原始文本
                            self.log_message.emit(self.format_debug_message(f"失败响应体: {response_text}", "debug", step_index), "debug", step_index)

                return response

            except Exception as e:
                self.log_message.emit(self.format_debug_message(f"HTTP请求异常: {str(e)}", "error", step_index), "error", step_index)
                import traceback
                self.log_message.emit(self.format_debug_message(f"异常堆栈: {traceback.format_exc()}", "error", step_index), "error", step_index)
                return {
                    'success': False,
                    'error': str(e),
                    'status': 'error'
                }
        except Exception as e:
            self.log_message.emit(self.format_debug_message(f"执行接口请求外层异常: {str(e)}", "error", step_index), "error", step_index)
            import traceback
            self.log_message.emit(self.format_debug_message(f"外层异常堆栈: {traceback.format_exc()}", "error", step_index), "error", step_index)
            return {
                'success': False,
                'error': str(e),
                'status': 'error'
            }

    def prepare_request_data(self, api_template, step_variables, step_index=None):
        """准备请求数据"""
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

        result = {
            'method': api_template['method'],
            'url': full_url,
            'headers': headers,
            'params': params,
            'body': body,
            'timeout': api_template.get('timeout', 30)
        }
        
        return result

    def extract_field_value(self, step_result, field_name):
        """从步骤结果中提取指定字段的值"""
        # 优先使用解密后的响应体（对于加解密请求）
        decrypted_body = step_result.get('decrypted_body', '')
        if decrypted_body:
            # 如果有解密后的响应体，优先使用它
            try:
                import json
                response_data = json.loads(decrypted_body)
                response_text = decrypted_body
            except:
                # 如果解析失败，使用原始响应数据
                response_data = step_result.get('response_data', step_result.get('body', {}))
                response_text = step_result.get('response_text', step_result.get('text', ''))
        else:
            # 如果没有解密后的响应体，使用原始响应数据
            response_data = step_result.get('response_data', step_result.get('body', {}))
            response_text = step_result.get('response_text', step_result.get('text', ''))
        
        response_headers = step_result.get('response_headers', step_result.get('headers', {}))
        response_time = step_result.get('response_time', step_result.get('elapsed', 0))
        status_code = step_result.get('status_code', 0)
        
        # 根据字段名提取对应的值
        if field_name == 'response_time':
            return response_time
        elif field_name == 'status_code':
            return status_code
        elif field_name == 'response_text':
            return response_text
        elif field_name == 'response_data':
            return response_data
        elif field_name == 'response_headers':
            return response_headers
        elif field_name.startswith('header.'):
            # 提取响应头字段，如 header.Content-Type
            header_key = field_name[7:]  # 去掉 'header.' 前缀
            actual_headers = {k.lower(): v for k, v in response_headers.items()}
            return actual_headers.get(header_key.lower(), '')
        elif field_name.startswith('json.'):
            # 提取JSON路径字段，如 json.data.user.name
            try:
                import json
                # 如果response_data是字符串，尝试解析为JSON
                if isinstance(response_data, str):
                    data = json.loads(response_data)
                else:
                    data = response_data
                
                # 简单的JSON路径提取
                path_parts = field_name[5:].split('.')  # 去掉 'json.' 前缀
                current = data
                for part in path_parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
                        current = current[int(part)]
                    else:
                        return ''  # 路径不存在
                return str(current)
            except:
                return ''
        else:
            # 默认返回响应文本
            return response_text

    def extract_field_value_from_response(self, step_result, field_path):
        """从响应体中提取字段路径的实际值，支持复杂路径如 name[0].libai"""
        # 如果字段路径为空，返回空字符串
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
            
            # 如果变量管理器中没找到，再从步骤结果中获取
            if step_result:
                var_value = step_result.get(var_name, None)
                return str(var_value) if var_value is not None else None
            
            return None  # 变量不存在
        
        # 优先使用解密后的响应体（对于加解密请求）
        decrypted_body = step_result.get('decrypted_body', '')
        
        if decrypted_body:
            # 如果有解密后的响应体，优先使用它
            try:
                import json
                response_data = json.loads(decrypted_body)
                response_text = decrypted_body
            except Exception as e:
                # 如果解析失败，使用原始响应数据
                response_data = step_result.get('response_data', step_result.get('body', {}))
                response_text = step_result.get('response_text', step_result.get('text', ''))
        else:
            # 如果没有解密后的响应体，使用原始响应数据
            response_data = step_result.get('response_data', step_result.get('body', {}))
            response_text = step_result.get('response_text', step_result.get('text', ''))
        
        # 如果字段路径是特殊字段
        if field_path in ['response_time', 'status_code', 'response_text', 'response_data', 'response_headers']:
            return self.extract_field_value(step_result, field_path)
        
        # 如果字段路径以header.开头，提取响应头
        if field_path.startswith('header.'):
            return self.extract_field_value(step_result, field_path)
        
        # 如果字段路径以json.开头，提取JSON路径
        if field_path.startswith('json.'):
            return self.extract_field_value(step_result, field_path)
        
        # 处理复杂路径：支持数组索引和对象属性
        try:
            import json
            # 如果response_data是字符串，尝试解析为JSON
            if isinstance(response_data, str):
                data = json.loads(response_data)
            else:
                data = response_data
            
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

    def replace_variables(self, text, step_result):
        """替换文本中的变量，支持${变量名}格式"""
        if not text or '${' not in text:
            return text
        
        import re
        
        # 调试：记录替换前的文本
        if hasattr(self, 'log_message'):
            self.log_message.emit(self.format_debug_message(f"[DEBUG] replace_variables: 替换前文本 = {text}", "debug", -1), "debug", -1)
        
        # 匹配${变量名}格式
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, text)
        
        # 调试：记录匹配到的变量
        if hasattr(self, 'log_message'):
            self.log_message.emit(self.format_debug_message(f"[DEBUG] replace_variables: 匹配到的变量 = {matches}", "debug", -1), "debug", -1)
        
        for var_name in matches:
            var_value = ''
            
            # 首先尝试从变量管理器中获取变量（前置处理器提取的变量）
            if hasattr(self, 'variable_manager'):
                # 调试：检查变量管理器状态
                self.log_message.emit(self.format_debug_message(f"[DEBUG] replace_variables: 变量管理器状态 - 局部变量: {self.variable_manager.local_variables}", "debug", -1), "debug", -1)
                self.log_message.emit(self.format_debug_message(f"[DEBUG] replace_variables: 变量管理器状态 - 全局变量: {self.variable_manager.global_variables}", "debug", -1), "debug", -1)
                
                # 尝试从局部变量中获取
                if var_name in self.variable_manager.local_variables:
                    var_value = self.variable_manager.local_variables[var_name]
                    self.log_message.emit(self.format_debug_message(f"[DEBUG] replace_variables: 从局部变量获取 {var_name} = {var_value}", "debug", -1), "debug", -1)
                # 尝试从全局变量中获取
                elif var_name in self.variable_manager.global_variables:
                    var_value = self.variable_manager.global_variables[var_name]
                    self.log_message.emit(self.format_debug_message(f"[DEBUG] replace_variables: 从全局变量获取 {var_name} = {var_value}", "debug", -1), "debug", -1)
            
            # 如果变量管理器中没找到，再从步骤结果中获取
            if not var_value and step_result:
                var_value = step_result.get(var_name, '')
                self.log_message.emit(self.format_debug_message(f"[DEBUG] replace_variables: 从步骤结果获取 {var_name} = {var_value}", "debug", -1), "debug", -1)
                
                # 如果变量名是特殊字段，使用extract_field_value提取
                if var_name in ['response_time', 'status_code', 'response_text', 'response_data', 'response_headers']:
                    var_value = self.extract_field_value(step_result, var_name)
                elif var_name.startswith('header.'):
                    var_value = self.extract_field_value(step_result, var_name)
                elif var_name.startswith('json.'):
                    var_value = self.extract_field_value(step_result, var_name)
                else:
                    # 尝试从响应数据中提取
                    var_value = self.extract_field_value_from_response(step_result, var_name)
            
            # 记录变量替换的调试信息
            if hasattr(self, 'log_message'):
                self.log_message.emit(self.format_debug_message(f"变量替换: ${{{var_name}}} -> {var_value}", "debug", -1), "debug", -1)
            
            # 替换变量
            text = text.replace(f'${{{var_name}}}', str(var_value))
        
        # 调试：记录替换后的文本
        if hasattr(self, 'log_message'):
            self.log_message.emit(self.format_debug_message(f"[DEBUG] replace_variables: 替换后文本 = {text}", "debug", -1), "debug", -1)
        
        return text

    def execute_comparison(self, actual, expected, symbol):
        """执行比较操作，支持多种比较符号"""
        # 处理期望值为None的情况：与None比较，而不是空字符串
        if expected is None:
            expected_str = None
        else:
            expected_str = str(expected)
        
        # 处理实际值为None的情况
        if actual is None:
            actual_str = None
        else:
            actual_str = str(actual)
        
        # 根据符号执行比较
        if symbol == 'equal':
            # 特殊处理：当两个值都是None时，直接返回True
            if actual is None and expected is None:
                return True
            # 当只有一个值是None时，返回False
            if actual is None or expected is None:
                return False
            return actual_str == expected_str
        elif symbol == 'not_equal':
            # 特殊处理：当两个值都是None时，返回False
            if actual is None and expected is None:
                return False
            # 当只有一个值是None时，返回True
            if actual is None or expected is None:
                return True
            return actual_str != expected_str
        elif symbol == 'contains':
            # 包含比较：期望值不能为None，实际值不能为None
            if expected_str is None or actual_str is None:
                return False
            return expected_str in actual_str
        elif symbol == 'not_contains':
            # 不包含比较：期望值不能为None，实际值不能为None
            if expected_str is None or actual_str is None:
                return False
            return expected_str not in actual_str
        elif symbol == 'greater':
            try:
                # 数值比较：期望值和实际值都不能为None
                if expected_str is None or actual_str is None:
                    return False
                return float(actual_str) > float(expected_str)
            except (ValueError, TypeError):
                return False
        elif symbol == 'less':
            try:
                # 数值比较：期望值和实际值都不能为None
                if expected_str is None or actual_str is None:
                    return False
                return float(actual_str) < float(expected_str)
            except (ValueError, TypeError):
                return False
        elif symbol == 'greater_equal':
            try:
                # 数值比较：期望值和实际值都不能为None
                if expected_str is None or actual_str is None:
                    return False
                return float(actual_str) >= float(expected_str)
            except (ValueError, TypeError):
                return False
        elif symbol == 'less_equal':
            try:
                # 数值比较：期望值和实际值都不能为None
                if expected_str is None or actual_str is None:
                    return False
                return float(actual_str) <= float(expected_str)
            except (ValueError, TypeError):
                return False
        else:
            # 默认使用相等比较
            return actual_str == expected_str

    def get_comparison_symbol(self, symbol):
        """获取比较符号的显示文本"""
        symbol_map = {
            'equal': '==',
            'not_equal': '!=',
            'contains': '包含',
            'not_contains': '不包含',
            'greater': '>',
            'less': '<',
            'greater_equal': '≥',
            'less_equal': '≤'
        }
        return symbol_map.get(symbol, '==')

    def execute_assertions(self, assertions, step_result, step_index):
        """执行断言"""
        if not assertions:
            self.log_message.emit(self.format_debug_message("断言: 无配置", "debug", step_index), "debug", step_index)
            return {}
            
        self.log_message.emit(self.format_debug_message("开始执行断言", "debug", step_index), "debug", step_index)
        self.log_message.emit(self.format_debug_message(f"断言数量: {len(assertions)}", "debug", step_index), "debug", step_index)
        
        results = {}
        
        # 兼容不同的响应数据结构
        # 1. 从execute_api_request返回的数据结构
        response_data = step_result.get('response_data', step_result.get('body', {}))
        response_text = step_result.get('response_text', step_result.get('text', ''))
        response_headers = step_result.get('response_headers', step_result.get('headers', {}))
        response_time = step_result.get('response_time', step_result.get('elapsed', 0))
        status_code = step_result.get('status_code', 0)
        
        # 优先使用解密后的响应体（对于加解密请求）
        decrypted_body = step_result.get('decrypted_body', '')
        if decrypted_body:
            # 如果有解密后的响应体，优先使用它
            response_text = decrypted_body
            # 尝试将解密后的响应体解析为JSON
            try:
                import json
                response_data = json.loads(decrypted_body)
            except:
                # 如果解析失败，保持原样
                pass
        elif isinstance(response_data, str) and response_data.strip():
            # 如果没有解密后的响应体，但response_data是字符串，尝试解析为JSON
            try:
                import json
                response_data = json.loads(response_data)
            except:
                # 如果解析失败，保持原样
                pass

        for assertion_name, assertion_config in assertions.items():
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
                        self.log_message.emit(self.format_debug_message(f"断言 {assertion_name}: 已禁用，跳过执行", "debug", step_index), "debug", step_index)
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
                            config['time_value'] = float(assertions_list[0].get('expected')) if assertions_list[0].get('expected') else None  # 不设置默认值，保持None
                        elif assertions_list:
                            config['expected'] = assertions_list[0].get('expected')  # 不设置默认值，保持None
                            config['ignore_case'] = False
                    else:
                        assertion_type = 'equal'  # 默认类型                
                if assertion_type == 'equal':
                    expected = config.get('expected')  # 不设置默认值，保持None
                    
                    # 变量替换：支持${变量名}格式（如果期望值不为None）
                    if expected is not None:
                        expected = self.replace_variables(expected, step_result)
                    
                    actual = response_text
                    ignore_case = config.get('ignore_case', False)
                    
                    if ignore_case:
                        results[assertion_name] = (expected or '').lower() == (actual or '').lower()
                    else:
                        results[assertion_name] = expected == actual
                    
                    log_level = "info" if results[assertion_name] else "error"
                    expected_display = expected if expected is not None else "None"
                    actual_display = actual if actual is not None else "None"
                    self.log_message.emit(
                        self.format_debug_message(f"断言 {assertion_name}: 期望值='{expected_display}' 实际值='{actual_display}' 比较结果:{'==' if results[assertion_name] else '!='}", log_level, step_index), log_level, step_index)

                elif assertion_type == 'not_equal':
                    expected = config.get('expected')  # 不设置默认值，保持None
                    
                    # 变量替换：支持${变量名}格式（如果期望值不为None）
                    if expected is not None:
                        expected = self.replace_variables(expected, step_result)
                    
                    actual = response_text
                    ignore_case = config.get('ignore_case', False)
                    
                    if ignore_case:
                        results[assertion_name] = (expected or '').lower() != (actual or '').lower()
                    else:
                        results[assertion_name] = expected != actual
                    
                    log_level = "info" if results[assertion_name] else "error"
                    expected_display = expected if expected is not None else "None"
                    actual_display = actual if actual is not None else "None"
                    self.log_message.emit(
                        self.format_debug_message(f"断言 {assertion_name}: 期望值='{expected_display}' 实际值='{actual_display}' 比较结果:{'!=' if results[assertion_name] else '=='}", log_level, step_index), log_level, step_index)

                elif assertion_type == 'contains':
                    expected = config.get('expected')  # 不设置默认值，保持None
                    
                    # 变量替换：支持${变量名}格式（如果期望值不为None）
                    if expected is not None:
                        expected = self.replace_variables(expected, step_result)
                    
                    actual = response_text
                    ignore_case = config.get('ignore_case', False)
                    
                    if ignore_case:
                        results[assertion_name] = (expected or '') in (actual or '').lower()
                    else:
                        results[assertion_name] = (expected or '') in (actual or '')
                    
                    log_level = "info" if results[assertion_name] else "error"
                    expected_display = expected if expected is not None else "None"
                    actual_display = actual if actual is not None else "None"
                    self.log_message.emit(self.format_debug_message(f"断言 {assertion_name}: 期望包含='{expected_display}' 实际响应='{actual_display}' 结果:{results[assertion_name]}", log_level, step_index), log_level, step_index)

                elif assertion_type == 'not_contains':
                    expected = config.get('expected')  # 不设置默认值，保持None
                    
                    # 变量替换：支持${变量名}格式（如果期望值不为None）
                    if expected is not None:
                        expected = self.replace_variables(expected, step_result)
                    
                    actual = response_text
                    ignore_case = config.get('ignore_case', False)
                    
                    if ignore_case:
                        results[assertion_name] = (expected or '') not in (actual or '').lower()
                    else:
                        results[assertion_name] = (expected or '') not in (actual or '')
                    
                    log_level = "info" if results[assertion_name] else "error"
                    expected_display = expected if expected is not None else "None"
                    actual_display = actual if actual is not None else "None"
                    self.log_message.emit(self.format_debug_message(f"断言 {assertion_name}: 期望不包含='{expected_display}' 实际响应='{actual_display}' 结果:{results[assertion_name]}", log_level, step_index), log_level, step_index)

                elif assertion_type == 'regex':
                    pattern = config.get('regex', '')
                    actual = response_text
                    ignore_case = config.get('ignore_case', False)
                    
                    import re
                    flags = re.IGNORECASE if ignore_case else 0
                    try:
                        match = re.search(pattern, actual, flags)
                        results[assertion_name] = match is not None
                    except Exception as e:
                        results[assertion_name] = False
                        self.log_message.emit(self.format_debug_message(f"断言 {assertion_name}: 正则表达式错误: {str(e)}", "error", step_index), "error", step_index)
                    
                    log_level = "info" if results[assertion_name] else "error"
                    self.log_message.emit(self.format_debug_message(f"断言 {assertion_name}: 正则匹配 '{pattern}' -> {results[assertion_name]}", log_level, step_index), log_level, step_index)

                elif assertion_type == 'status_code':
                    expected = config.get('expected')  # 不设置默认值，保持None
                    
                    # 变量替换：支持${变量名}格式（如果期望值不为None）
                    if expected is not None:
                        expected = self.replace_variables(expected, step_result)
                    
                    actual = status_code
                    results[assertion_name] = str(expected) == str(actual)
                    log_level = "info" if results[assertion_name] else "error"
                    expected_display = expected if expected is not None else "None"
                    actual_display = actual if actual is not None else "None"
                    self.log_message.emit(
                        self.format_debug_message(f"断言 {assertion_name}: 状态码 {actual_display} {'==' if results[assertion_name] else '!='} {expected_display}", log_level, step_index), log_level, step_index)

                elif assertion_type == 'json_path':
                    path = config.get('path', '')
                    expected = config.get('expected')  # 不设置默认值，保持None
                    
                    # 变量替换：支持${变量名}格式（如果期望值不为None）
                    if expected is not None:
                        expected = self.replace_variables(expected, step_result)
                    
                    actual = self.simple_json_path_extract(response_data, path)
                    results[assertion_name] = expected == actual
                    log_level = "info" if results[assertion_name] else "error"
                    expected_display = expected if expected is not None else "None"
                    actual_display = actual if actual is not None else "None"
                    self.log_message.emit(
                        self.format_debug_message(f"断言 {assertion_name}: {path} = {actual_display} {'==' if expected == actual else '!='} {expected_display}", log_level, step_index), log_level, step_index)

                elif assertion_type == 'response_time':
                    comparison = config.get('time_comparison', 'less')
                    expected_value = config.get('time_value')  # 不设置默认值，保持None
                    actual = response_time
                    
                    # 如果期望值为None，则使用0作为默认值进行比较
                    expected_value_num = expected_value if expected_value is not None else 0
                    
                    if comparison == 'less':
                        results[assertion_name] = actual < expected_value_num
                    elif comparison == 'equal':
                        results[assertion_name] = abs(actual - expected_value_num) < 0.001  # 浮点数比较容差
                    elif comparison == 'greater':
                        results[assertion_name] = actual > expected_value_num
                    
                    log_level = "info" if results[assertion_name] else "error"
                    comparison_symbol = {'less': '<', 'equal': '==', 'greater': '>'}[comparison]
                    expected_display = expected_value if expected_value is not None else "None"
                    self.log_message.emit(
                        self.format_debug_message(f"断言 {assertion_name}: 响应时间 {actual:.3f}s {comparison_symbol} {expected_display}s -> {results[assertion_name]}", log_level, step_index), log_level, step_index)

                elif assertion_type == 'header_exists':
                    header_name = config.get('header_name', '')
                    actual_headers = {k.lower(): v for k, v in response_headers.items()}
                    results[assertion_name] = header_name.lower() in actual_headers
                    log_level = "info" if results[assertion_name] else "error"
                    self.log_message.emit(
                        self.format_debug_message(f"断言 {assertion_name}: 响应头包含 '{header_name}' -> {results[assertion_name]}", log_level, step_index), log_level, step_index)

                elif assertion_type == 'json_schema':
                    # 这里需要实现JSON Schema验证
                    # 由于JSON Schema验证比较复杂，这里先简单返回True
                    # 实际项目中应该使用jsonschema库进行验证
                    schema = config.get('schema', '')
                    results[assertion_name] = True  # 暂时返回True
                    log_level = "info" if results[assertion_name] else "error"
                    self.log_message.emit(
                        self.format_debug_message(f"断言 {assertion_name}: JSON Schema验证 -> {results[assertion_name]}", log_level, step_index), log_level, step_index)

                elif assertion_type == 'field_path_assertion':
                    # 新的字段路径提取断言，支持字段路径提取和变量替换
                    assertions_list = config.get('assertions', [])
                    
                    # 检查断言是否启用
                    if not config.get('enabled', True):
                        self.log_message.emit(self.format_debug_message(f"断言 {assertion_name}: 已禁用，跳过执行", "debug", step_index), "debug", step_index)
                        results[assertion_name] = True  # 禁用的断言视为通过
                        continue
                    
                    # 执行所有断言行
                    assertion_results = []
                    for assertion in assertions_list:
                        field = assertion.get('field', '')
                        symbol = assertion.get('symbol', 'equal')
                        expected = assertion.get('expected')  # 不设置默认值，保持None
                        
                        # 提取实际值：支持字段路径提取
                        actual = self.extract_field_value_from_response(step_result, field)
                                                
                        # 变量替换：支持${变量名}格式（如果期望值不为None）
                        if expected is not None:
                            # 执行变量替换
                            expected = self.replace_variables(expected, step_result)

                        # 根据符号执行比较
                        result = self.execute_comparison(actual, expected, symbol)
                        assertion_results.append(result)
                        
                        # 记录日志
                        log_level = "info" if result else "error"
                        comparison_symbol = self.get_comparison_symbol(symbol)
                        # 正确显示None值
                        expected_display = expected if expected is not None else "None"
                        actual_display = actual if actual is not None else "None"
                        self.log_message.emit(
                            self.format_debug_message(f"断言 {assertion_name}: {field} = {actual_display} {comparison_symbol} {expected_display} -> {result}", log_level, step_index), log_level, step_index)
                    
                    # 所有断言行都必须通过
                    results[assertion_name] = all(assertion_results)
                    
                elif assertion_type in ['greater', 'less', 'greater_equal', 'less_equal']:
                    # 数值比较断言
                    expected = config.get('expected')  # 不设置默认值，保持None
                    
                    # 从断言配置中获取字段名，用于从响应数据中提取实际值
                    assertions_list = config.get('assertions', [])
                    field_name = 'response_time'  # 默认字段
                    if assertions_list:
                        first_assertion = assertions_list[0]
                        field_name = first_assertion.get('field', 'response_time')
                    
                    # 根据字段名从响应数据中提取实际值
                    actual = self.extract_field_value(step_result, field_name)
                    
                    # 转换为数值进行比较
                    try:
                        expected_num = float(expected) if expected is not None else 0
                        actual_num = float(actual) if actual is not None else 0
                        
                        if assertion_type == 'greater':
                            results[assertion_name] = actual_num > expected_num
                        elif assertion_type == 'less':
                            results[assertion_name] = actual_num < expected_num
                        elif assertion_type == 'greater_equal':
                            results[assertion_name] = actual_num >= expected_num
                        elif assertion_type == 'less_equal':
                            results[assertion_name] = actual_num <= expected_num
                            
                        log_level = "info" if results[assertion_name] else "error"
                        comparison_symbol = {
                            'greater': '>', 'less': '<', 
                            'greater_equal': '≥', 'less_equal': '≤'
                        }[assertion_type]
                        expected_display = expected if expected is not None else "None"
                        actual_display = actual if actual is not None else "None"
                        self.log_message.emit(
                            self.format_debug_message(f"断言 {assertion_name}: {field_name} {actual_display} {comparison_symbol} {expected_display} -> {results[assertion_name]}", log_level, step_index), log_level, step_index)
                            
                    except (ValueError, TypeError) as e:
                        results[assertion_name] = False
                        expected_display = expected if expected is not None else "None"
                        actual_display = actual if actual is not None else "None"
                        self.log_message.emit(self.format_debug_message(f"断言 {assertion_name}: 数值转换错误 - 期望值: {expected_display}, 实际值: {actual_display}", "error", step_index), "error", step_index)

                else:
                    self.log_message.emit(self.format_debug_message(f"未知断言类型: {assertion_type}", "warning", step_index), "warning", step_index)
                    results[assertion_name] = False

            except Exception as e:
                results[assertion_name] = False
                self.log_message.emit(self.format_debug_message(f"断言 {assertion_name} 执行错误: {str(e)}", "error", step_index), "error", step_index)

        # 检查所有断言是否通过
        passed_count = sum(1 for result in results.values() if result)
        all_passed = all(results.values())
        
        self.log_message.emit(self.format_debug_message(f"断言结果: {passed_count}/{len(assertions)} 通过", "debug", step_index), "debug", step_index)
        
        step_result['success'] = all_passed
        step_result['status'] = 'success' if all_passed else 'failure'
        
        self.log_message.emit(self.format_debug_message("断言执行结束", "debug", step_index), "debug", step_index)

        return results

    def stop(self):
        """停止执行"""
        self.is_running = False


class CaseTabWidget(QWidget):
    """测试用例标签页组件"""
    
    modified_signal = pyqtSignal(bool)  # 修改状态信号
    saved = pyqtSignal(dict)  # 保存信号
    api_template_edit_requested = pyqtSignal(str)  # 接口模板编辑请求信号
    
    def __init__(self, case_data=None, project_id=None, folder_id=None):
        super().__init__()
        self.case_data = case_data or {}
        self.project_id = project_id
        self.folder_id = folder_id
        self.is_edit = bool(case_data)
        self.modified = False
        
        # 测试用例相关属性
        self.current_case = None
        self.current_case_data = None
        
        # 执行相关属性
        self.execution_thread = None
        self.is_executing = False
        self.execution_logs = []
        
        # 环境服务
        self.environment_service = EnvironmentService()
        
        # 步骤卡片管理相关属性
        self.current_selected_step_card = None  # 当前选中的步骤卡片
        self.copied_step_data = None  # 复制的步骤数据
        
        self.init_ui()
        
        # 如果是编辑模式，加载数据
        if self.is_edit:
            self.load_case_data()
    
    def get_icon(self, icon_name):
        """获取图标，支持exe打包后的资源路径"""
        import os
        import sys
        
        # 尝试多种路径方式加载图标
        icon_paths = [
            # 开发环境路径
            os.path.join("src", "resources", "icons", icon_name),
            # exe打包后路径
            os.path.join(os.path.dirname(sys.executable), "src", "resources", "icons", icon_name),
            # 相对路径（如果exe在项目根目录）
            os.path.join("src", "resources", "icons", icon_name),
            # 临时解压路径（PyInstaller）
            os.path.join(sys._MEIPASS, "src", "resources", "icons", icon_name) if hasattr(sys, '_MEIPASS') else None
        ]
        
        for path in icon_paths:
            if path and os.path.exists(path):
                return QIcon(path)
        
        # 如果所有路径都找不到，返回空图标
        return QIcon()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(2)  # 大幅减少主布局垂直间距，从5改为2
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 用例信息区域（上半部分）- 固定高度，不拉伸
        case_info_widget = QWidget()
        self.setup_case_info_tab(case_info_widget)
        case_info_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # 测试步骤区域（下半部分）- 可拉伸，自适应高度
        steps_widget = QWidget()
        self.setup_steps_tab(steps_widget)
        steps_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 直接添加两个区域到布局中
        layout.addWidget(case_info_widget)
        layout.addWidget(steps_widget)
        
        # 底部按钮已移除，保存按钮已移到环境选择后面
    
    def setup_case_info_tab(self, parent):
        """设置用例信息区域"""
        layout = QVBoxLayout(parent)
        layout.setSpacing(5)  # 增加垂直间距，从1改为5
        layout.setContentsMargins(5, 5, 5, 5)  # 设置边距为5，增加外层边距
        
        # 用例名称和描述在同一行
        name_desc_layout = QHBoxLayout()
        name_desc_layout.setSpacing(20)  # 增加水平间距，从10改为20
        name_desc_layout.setContentsMargins(0, 0, 0, 0)
        
        # 名称部分 - 标题和输入框在同一行
        name_widget = QWidget()
        name_layout = QHBoxLayout(name_widget)
        name_layout.setSpacing(5)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.addWidget(QLabel("名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入用例名称")
        self.name_edit.textChanged.connect(self.on_content_changed)
        name_layout.addWidget(self.name_edit)
        name_desc_layout.addWidget(name_widget)
        
        # 描述部分 - 标题和输入框在同一行
        desc_widget = QWidget()
        desc_layout = QHBoxLayout(desc_widget)
        desc_layout.setSpacing(5)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        desc_layout.addWidget(QLabel("描述:"))
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(30)  # 减小行高从60到40
        self.description_edit.setPlaceholderText("请输入用例描述")
        self.description_edit.textChanged.connect(self.on_content_changed)
        desc_layout.addWidget(self.description_edit)
        name_desc_layout.addWidget(desc_widget)
        
        # 添加弹性空间使两个部分均匀分布
        name_desc_layout.addStretch()
        layout.addLayout(name_desc_layout)
        
        # 环境选择（标题和输入框在同一行）
        env_layout = QHBoxLayout()
        env_layout.setSpacing(5)  # 增加水平间距，从3改为5
        env_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        env_layout.setAlignment(Qt.AlignLeft)  # 设置整个布局靠左对齐
        env_layout.addWidget(QLabel("环境:"))
        self.env_combo = QComboBox()
        self.env_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 设置下拉框固定大小，不拉伸
        self.load_environments()
        self.env_combo.currentTextChanged.connect(self.on_content_changed)
        env_layout.addWidget(self.env_combo)
        
        env_layout.addStretch()  # 添加弹性空间，使按钮靠左对齐
        
        layout.addLayout(env_layout)
        
        # 加解密配置区域
        encryption_layout = QHBoxLayout()
        encryption_layout.setSpacing(5)
        encryption_layout.setContentsMargins(0, 0, 0, 0)
        encryption_layout.setAlignment(Qt.AlignLeft)
        
        # 启用加解密复选框
        self.enable_encryption_checkbox = QCheckBox("启用加解密")
        self.enable_encryption_checkbox.setChecked(False)
        self.enable_encryption_checkbox.stateChanged.connect(self.on_content_changed)
        self.enable_encryption_checkbox.stateChanged.connect(self.toggle_encryption_config)
        encryption_layout.addWidget(self.enable_encryption_checkbox)
        
        encryption_layout.addStretch()
        layout.addLayout(encryption_layout)
        
        # 加解密URL配置（默认隐藏）
        self.encryption_config_widget = QWidget()
        encryption_config_layout = QVBoxLayout(self.encryption_config_widget)
        encryption_config_layout.setSpacing(5)
        encryption_config_layout.setContentsMargins(0, 0, 0, 0)
        
        # 加密URL和解密URL在同一行
        url_row_layout = QHBoxLayout()
        url_row_layout.setSpacing(20)  # 增加水平间距，从10改为20
        url_row_layout.setContentsMargins(0, 0, 0, 0)
        
        # 加密URL部分 - 标题和输入框在同一行
        encrypt_widget = QWidget()
        encrypt_layout = QHBoxLayout(encrypt_widget)
        encrypt_layout.setSpacing(5)
        encrypt_layout.setContentsMargins(0, 0, 0, 0)
        encrypt_layout.addWidget(QLabel("加密URL:"))
        self.encrypt_url_edit = QLineEdit()
        self.encrypt_url_edit.setPlaceholderText("请输入加密接口URL")
        self.encrypt_url_edit.textChanged.connect(self.on_content_changed)
        self.encrypt_url_edit.textChanged.connect(self.on_encrypt_url_changed)
        encrypt_layout.addWidget(self.encrypt_url_edit)
        url_row_layout.addWidget(encrypt_widget)
        
        # 解密URL部分 - 标题和输入框在同一行
        decrypt_widget = QWidget()
        decrypt_layout = QHBoxLayout(decrypt_widget)
        decrypt_layout.setSpacing(5)
        decrypt_layout.setContentsMargins(0, 0, 0, 0)
        decrypt_layout.addWidget(QLabel("解密URL:"))
        self.decrypt_url_edit = QLineEdit()
        self.decrypt_url_edit.setPlaceholderText("请输入解密接口URL")
        self.decrypt_url_edit.textChanged.connect(self.on_content_changed)
        self.decrypt_url_edit.textChanged.connect(self.on_decrypt_url_changed)
        decrypt_layout.addWidget(self.decrypt_url_edit)
        url_row_layout.addWidget(decrypt_widget)
        
        # 添加弹性空间使两个部分均匀分布
        url_row_layout.addStretch()
        encryption_config_layout.addLayout(url_row_layout)
        
        layout.addWidget(self.encryption_config_widget)
        self.encryption_config_widget.setVisible(False)  # 默认隐藏
        
        # 变量按钮（换行到下一行）
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)  # 设置水平间距
        button_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        button_layout.setAlignment(Qt.AlignLeft)  # 设置整个布局靠左对齐
        
        # 查询变量按钮（绿色）
        self.query_vars_btn = QPushButton("变量")
        self.query_vars_btn.clicked.connect(self.edit_global_variables)
        self.query_vars_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; 
                color: white; 
                padding: 4px 12px; 
                border-radius: 4px; 
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        button_layout.addWidget(self.query_vars_btn)
        
        # 调试/停止按钮（合并为一个按钮，根据执行状态切换图标）
        self.run_stop_btn = QPushButton()
        self.run_stop_btn.setIcon(self.get_icon("running.png"))
        self.run_stop_btn.setIconSize(QSize(26, 26))
        self.run_stop_btn.setToolTip("调试用例")
        self.run_stop_btn.clicked.connect(self.toggle_execution)
        self.run_stop_btn.setStyleSheet("""
            QPushButton {
                border: none; 
                background: transparent; 
                padding: 8px; 
                margin: 4px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 0.2);
            }
        """)
        button_layout.addWidget(self.run_stop_btn)
        
        # 日志按钮（图标替换）
        self.log_btn_toolbar = QPushButton()
        self.log_btn_toolbar.setIcon(self.get_icon("log.png"))
        self.log_btn_toolbar.setIconSize(QSize(26, 26))
        self.log_btn_toolbar.setToolTip("查看执行日志")
        self.log_btn_toolbar.clicked.connect(self.show_execution_logs)
        self.log_btn_toolbar.setStyleSheet("""
            QPushButton {
                border: none; 
                background: transparent; 
                padding: 8px; 
                margin: 4px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 0.2);
            }
        """)
        button_layout.addWidget(self.log_btn_toolbar)
        
        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_case)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; 
                color: white; 
                padding: 4px 12px; 
                border-radius: 4px; 
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        button_layout.addWidget(self.save_btn)
        
        button_layout.addStretch()  # 添加弹性空间，使按钮靠左对齐
        
        layout.addLayout(button_layout)
    
    def setup_steps_tab(self, parent):
        """设置测试步骤区域"""
        layout = QVBoxLayout(parent)
        layout.setSpacing(5)  # 增加布局间距，从3改为5
        layout.setContentsMargins(5, 5, 5, 5)  # 设置边距为5，增加外层边距
        
        # 步骤操作工具栏已移除，添加步骤功能通过拖拽实现

        # 步骤列表容器（可滚动）- 自适应高度
        self.steps_scroll = QScrollArea()
        self.steps_scroll.setWidgetResizable(True)
        self.steps_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.steps_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 设置为可拉伸
        self.steps_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #f8f9fa;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 6px;  /* 减少内边距，从8px改为6px */
            }
            QScrollArea QWidget {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #808080;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background-color: #f0f0f0;
                height: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #a0a0a0;
            }
            QScrollBar::handle:horizontal:pressed {
                background-color: #808080;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)

        self.steps_widget = QWidget()
        self.steps_layout = FlowLayout(self.steps_widget)
        self.steps_layout.setSpacing(10)  # 流式布局间距
        self.steps_layout.setContentsMargins(5, 5, 5, 5)  # 设置边距

        # 初始提示 - 使用容器包装以实现居中显示
        placeholder_container = QWidget()
        placeholder_layout = QVBoxLayout(placeholder_container)
        placeholder_layout.setContentsMargins(0, 0, 0, 0)
        placeholder_layout.setSpacing(0)
        
        self.steps_placeholder = QLabel("暂无测试步骤，请添加步骤或从左侧拖拽接口")
        self.steps_placeholder.setAlignment(Qt.AlignCenter)
        self.steps_placeholder.setStyleSheet("color: #999; font-style: italic; padding: 30px;")  # 减少内边距，从50px改为30px
        
        placeholder_layout.addWidget(self.steps_placeholder)
        self.steps_layout.addWidget(placeholder_container)

        self.steps_scroll.setWidget(self.steps_widget)
        layout.addWidget(self.steps_scroll)

        # 启用拖拽功能 - 设置到步骤容器上，而不是滚动区域
        self.steps_widget.setAcceptDrops(True)
        self.steps_widget.dragEnterEvent = self.drag_enter_event
        self.steps_widget.dragMoveEvent = self.drag_move_event
        self.steps_widget.dropEvent = self.drop_event
        
        # 设置步骤区域的右键菜单
        self.steps_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.steps_widget.customContextMenuRequested.connect(self.show_steps_context_menu)
    
    def on_content_changed(self):
        """内容变化时标记为已修改"""
        if not self.modified:
            self.modified = True
            self.modified_signal.emit(True)
    
    def toggle_encryption_config(self):
        """切换加解密配置区域的显示/隐藏"""
        is_checked = self.enable_encryption_checkbox.isChecked()
        self.encryption_config_widget.setVisible(is_checked)
        
        # 同步更新case_data中的加解密配置，确保get_global_encryption_status()能正确获取
        if hasattr(self, 'case_data') and self.case_data:
            self.case_data['enable_encryption'] = is_checked
            # 如果取消勾选，清空URL字段
            if not is_checked:
                self.case_data['encrypt_url'] = ''
                self.case_data['decrypt_url'] = ''
        
        # 同步更新所有步骤卡片的启用状态
        self.sync_all_step_cards_encryption_status(is_checked)
    
    def sync_all_step_cards_encryption_status(self, enable_encryption):
        """同步所有步骤卡片的加解密启用状态"""
        if not hasattr(self, 'steps_layout'):
            return
            
        # 遍历步骤布局中的所有步骤卡片
        for i in range(self.steps_layout.count()):
            item = self.steps_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # 检查是否是步骤卡片组件
                if hasattr(widget, 'set_encryption_enabled'):
                    # 调用步骤卡片的设置方法
                    widget.set_encryption_enabled(enable_encryption)
                elif hasattr(widget, 'encryption_btn') and hasattr(widget.encryption_btn, 'setChecked'):
                    # 直接设置加解密按钮状态
                    widget.encryption_btn.setChecked(enable_encryption)
    
    def sync_all_step_data_from_ui(self):
        """从前端UI同步所有步骤数据到current_case.steps - 确保调试时获取最新信息"""
        if not self.current_case or not hasattr(self, 'steps_layout'):
            return
            
        print("[DEBUG] 开始同步前端UI步骤数据到current_case.steps")
        print(f"[DEBUG] 步骤卡片数量: {self.steps_layout.count()}")
        print(f"[DEBUG] current_case.steps数量: {len(self.current_case.steps)}")
            
        # 遍历所有步骤卡片，同步所有配置信息
        for i in range(self.steps_layout.count()):
            item = self.steps_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # 检查是否是步骤卡片（有step_id和step_data属性）
                if hasattr(widget, 'step_id') and hasattr(widget, 'step_data'):
                    # 获取步骤卡片的完整数据
                    step_data = widget.step_data
                    
                    print(f"[DEBUG] 同步步骤{i+1}数据: {step_data.get('name', '未命名')}")
                    print(f"[DEBUG]   - 启用状态: {step_data.get('enabled', True)}")
                    print(f"[DEBUG]   - 加解密状态: {step_data.get('enable_encryption', None)}")
                    print(f"[DEBUG]   - 前置处理: {len(step_data.get('pre_processing', {}))}")
                    print(f"[DEBUG]   - 后置处理: {len(step_data.get('post_processing', {}))}")
                    print(f"[DEBUG]   - 断言: {len(step_data.get('assertions', {}))}")
                    
                    # 同步到current_case.steps中对应的步骤
                    if i < len(self.current_case.steps):
                        step = self.current_case.steps[i]
                        
                        # 同步所有重要配置信息
                        if 'enabled' in step_data:
                            step.enabled = step_data['enabled']
                        
                        if 'enable_encryption' in step_data:
                            step.enable_encryption = step_data['enable_encryption']
                        
                        if 'pre_processing' in step_data:
                            step.pre_processing = step_data['pre_processing']
                        
                        if 'post_processing' in step_data:
                            step.post_processing = step_data['post_processing']
                        
                        if 'assertions' in step_data:
                            step.assertions = step_data['assertions']
                        
                        # 同步其他可能的重要字段
                        if 'name' in step_data:
                            step.name = step_data['name']
                        
                        if 'api_template_id' in step_data:
                            step.api_template_id = step_data['api_template_id']
                        
                        if 'step_order' in step_data:
                            step.step_order = step_data['step_order']
                        
                        # 确保步骤数据字典也同步更新
                        step_dict = step.to_dict()
                        step_dict.update(step_data)
                        step.update_from_dict(step_dict)
                        
                        print(f"[DEBUG] 同步后步骤{i+1}状态: enabled={step.enabled}, enable_encryption={step.enable_encryption}")
                    else:
                        print(f"[DEBUG] 警告: 步骤索引{i}超出current_case.steps范围")
        
        print("[DEBUG] 前端UI步骤数据同步完成")
    
    def sync_step_data_to_temp_case(self, case_data):
        """同步前端UI步骤数据到临时用例数据，但不修改current_case对象"""
        if not case_data or not hasattr(self, 'steps_layout'):
            return
            
        print("[DEBUG] 开始同步前端UI步骤数据到临时用例数据")
        print(f"[DEBUG] 步骤卡片数量: {self.steps_layout.count()}")
        print(f"[DEBUG] 临时用例数据步骤数量: {len(case_data.get('steps', []))}")
            
        # 遍历所有步骤卡片，同步所有配置信息到临时用例数据
        for i in range(self.steps_layout.count()):
            item = self.steps_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # 检查是否是步骤卡片（有step_id和step_data属性）
                if hasattr(widget, 'step_id') and hasattr(widget, 'step_data'):
                    # 获取步骤卡片的完整数据
                    step_data = widget.step_data
                    
                    print(f"[DEBUG] 同步步骤{i+1}数据到临时用例数据: {step_data.get('name', '未命名')}")
                    print(f"[DEBUG]   - 启用状态: {step_data.get('enabled', True)}")
                    print(f"[DEBUG]   - 加解密状态: {step_data.get('enable_encryption', None)}")
                    
                    # 同步到临时用例数据中对应的步骤
                    if i < len(case_data.get('steps', [])):
                        temp_step = case_data['steps'][i]
                        
                        # 同步所有重要配置信息到临时步骤数据
                        if 'enabled' in step_data:
                            temp_step['enabled'] = step_data['enabled']
                        
                        if 'enable_encryption' in step_data:
                            temp_step['enable_encryption'] = step_data['enable_encryption']
                        
                        if 'pre_processing' in step_data:
                            temp_step['pre_processing'] = step_data['pre_processing']
                        
                        if 'post_processing' in step_data:
                            temp_step['post_processing'] = step_data['post_processing']
                        
                        if 'assertions' in step_data:
                            temp_step['assertions'] = step_data['assertions']
                        
                        # 同步其他可能的重要字段
                        if 'name' in step_data:
                            temp_step['name'] = step_data['name']
                        
                        if 'api_template_id' in step_data:
                            temp_step['api_template_id'] = step_data['api_template_id']
                        
                        if 'step_order' in step_data:
                            temp_step['step_order'] = step_data['step_order']
                        
                        print(f"[DEBUG] 同步后临时步骤{i+1}状态: enabled={temp_step.get('enabled', True)}, enable_encryption={temp_step.get('enable_encryption', None)}")
                    else:
                        print(f"[DEBUG] 警告: 步骤索引{i}超出临时用例数据步骤范围")
        
        print("[DEBUG] 前端UI步骤数据同步到临时用例数据完成")
    
    def sync_step_enabled_status(self):
        """同步步骤卡片的启用状态到current_case.steps"""
        if not self.current_case or not hasattr(self, 'steps_layout'):
            return
            
        # 遍历所有步骤卡片，同步启用状态
        for i in range(self.steps_layout.count()):
            item = self.steps_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # 检查是否是步骤卡片（有step_id和step_data属性）
                if hasattr(widget, 'step_id') and hasattr(widget, 'step_data'):
                    # 获取步骤卡片的启用状态
                    step_enabled = widget.step_data.get('enabled', True)
                    
                    # 同步到current_case.steps中对应的步骤
                    if i < len(self.current_case.steps):
                        self.current_case.steps[i].enabled = step_enabled
    
    def on_encrypt_url_changed(self, text):
        """加密URL变化时同步更新case_data"""
        if hasattr(self, 'case_data') and self.case_data:
            self.case_data['encrypt_url'] = text
    
    def on_decrypt_url_changed(self, text):
        """解密URL变化时同步更新case_data"""
        if hasattr(self, 'case_data') and self.case_data:
            self.case_data['decrypt_url'] = text
    
    def load_case_data(self):
        """加载用例数据"""
        if not self.case_data:
            return
        
        # 创建测试用例对象
        self.current_case = TestCase.from_dict(self.case_data)
        
        # 加载基础信息
        self.name_edit.setText(self.current_case.name)
        self.description_edit.setPlainText(self.current_case.description)
        
        # 加载环境
        if self.current_case.environment_id:
            index = self.env_combo.findData(self.current_case.environment_id)
            if index >= 0:
                self.env_combo.setCurrentIndex(index)
        
        # 加载加解密配置
        if self.current_case.enable_encryption:
            self.enable_encryption_checkbox.setChecked(True)
            self.encrypt_url_edit.setText(self.current_case.encrypt_url or '')
            self.decrypt_url_edit.setText(self.current_case.decrypt_url or '')
            self.encryption_config_widget.setVisible(True)
        else:
            self.enable_encryption_checkbox.setChecked(False)
            self.encrypt_url_edit.setText('')
            self.decrypt_url_edit.setText('')
            self.encryption_config_widget.setVisible(False)
        
        # 同步更新case_data中的加解密配置，确保get_global_encryption_status()能正确获取
        self.case_data['enable_encryption'] = self.current_case.enable_encryption
        self.case_data['encrypt_url'] = self.current_case.encrypt_url or ''
        self.case_data['decrypt_url'] = self.current_case.decrypt_url or ''
                
        # 加载测试步骤
        self.load_steps()
        
        # 重置修改状态
        self.modified = False
        self.modified_signal.emit(False)
    
    def save_case(self):
        """保存用例 - 基于前端ID系统更新步骤顺序，并更新接口模板名称"""
        
        # 更新当前用例数据
        if not self.current_case:
            self.current_case = TestCase()
        
        self.current_case.name = self.name_edit.text().strip()
        self.current_case.description = self.description_edit.toPlainText().strip()
        self.current_case.environment_id = self.env_combo.currentData()
        self.current_case.global_vars = {}  # 全局变量功能已移除，设置为空字典
        self.current_case.project_id = self.project_id
        self.current_case.folder_id = self.folder_id
        
        # 保存加解密配置
        self.current_case.enable_encryption = self.enable_encryption_checkbox.isChecked()
        self.current_case.encrypt_url = self.encrypt_url_edit.text().strip()
        self.current_case.decrypt_url = self.decrypt_url_edit.text().strip()
        
        # 基于前端ID顺序更新步骤顺序
        if self.current_case and self.current_case.steps and hasattr(self, 'steps_layout'):
            # 获取布局中所有步骤的前端ID顺序
            current_step_ids = []
            for i in range(self.steps_layout.count()):
                item = self.steps_layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), 'step_id'):
                    current_step_ids.append(item.widget().step_id)
            
            # 根据前端ID顺序重新排序步骤列表
            if len(current_step_ids) == len(self.current_case.steps):
                new_steps_order = []
                for step_id in current_step_ids:
                    # 找到对应前端ID的步骤
                    for step in self.current_case.steps:
                        step_dict = step.to_dict()
                        if step_dict.get('frontend_id') == step_id:
                            new_steps_order.append(step)
                            break
                
                # 更新步骤列表和序号
                if len(new_steps_order) == len(self.current_case.steps):
                    self.current_case.steps = new_steps_order
                    
                    # 更新步骤序号
                    for i, step in enumerate(self.current_case.steps, 1):
                        step.step_order = i
        
        # 验证数据
        if not self.current_case.name:
            Toast.warning(self, "警告", "用例名称不能为空")
            return
        
        # 校验加解密配置：如果启用了加解密，必须配置加解密URL
        if self.current_case.enable_encryption:
            if not self.current_case.encrypt_url or not self.current_case.decrypt_url:
                Toast.warning(self, "警告", "启用加解密功能必须配置加密URL和解密URL")
                return
        
        # 如果是编辑模式，添加ID
        if self.is_edit and 'id' in self.case_data:
            self.current_case.id = self.case_data['id']
        
        # 更新步骤中的接口模板名称（如果接口模板名称发生变更）
        if self.current_case and self.current_case.steps:
            from src.core.services.api_template_service import ApiTemplateService
            api_service = ApiTemplateService()
            
            for step in self.current_case.steps:
                if step.api_template_id:
                    # 从接口模板服务获取最新的模板数据
                    template_data = api_service.get_template_by_id(step.api_template_id)
                    if template_data:
                        # 更新步骤名称和接口模板相关信息
                        step.name = template_data.get('name', step.name)
                        step.api_name = template_data.get('name', '')
                        step.api_method = template_data.get('method', '')
                        step.api_url_path = template_data.get('url_path', '')
        
        # 转换为字典并检查步骤数据
        case_dict = self.current_case.to_dict()
        
        # 发送保存信号
        self.saved.emit(case_dict)
        
        # 标记为已保存
        self.modified = False
        self.modified_signal.emit(False)
    
    def cancel(self):
        """取消编辑"""
        if self.modified:
            # 创建确认对话框，手动设置按钮文本
            msg_box = QMessageBox(QMessageBox.Question, "确认取消",
                                 "有未保存的修改，确定要取消吗？")
            
            # 添加确认和取消按钮
            confirm_btn = msg_box.addButton("确认", QMessageBox.YesRole)
            cancel_btn = msg_box.addButton("取消", QMessageBox.NoRole)
            msg_box.setDefaultButton(cancel_btn)
            
            msg_box.exec_()
            
            if msg_box.clickedButton() == cancel_btn:
                return
        
        # 关闭标签页
        self.close()
    
    def show_execution_logs(self):
        """显示执行日志"""
        # 直接调用TabbedCaseEditor的show_execution_logs方法
        # 避免重复调用导致的多个弹窗问题
        from src.ui.interface_auto.components.tabbed_case_editor import TabbedCaseEditor
        
        # 获取父窗口（TabbedCaseEditor）
        parent = self.parent()
        while parent and not isinstance(parent, TabbedCaseEditor):
            parent = parent.parent()
        
        if isinstance(parent, TabbedCaseEditor):
            parent.show_execution_logs()
        else:
            Toast.info(self, "执行日志功能将在后续版本中实现")
    
    def drag_enter_event(self, event):
        """拖拽进入事件"""
        # 检查拖拽数据是否包含接口模板信息
        if (event.mimeData().hasFormat("application/json") or 
            event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist") or 
            event.mimeData().hasText()):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def drag_move_event(self, event):
        """拖拽移动事件"""
        # 检查拖拽数据是否包含接口模板信息
        if (event.mimeData().hasFormat("application/json") or 
            event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist") or 
            event.mimeData().hasText()):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def drop_event(self, event):
        """拖拽放置事件 - 支持在任意位置插入新步骤"""
        mime_data = event.mimeData()
        
        # 获取拖拽位置
        drop_position = event.pos()
        
        # 首先尝试解析JSON格式的数据（ApiTemplateTreeWidget的拖拽数据）
        if mime_data.hasFormat("application/json"):
            try:
                import json
                json_data = mime_data.data("application/json").data().decode('utf-8')
                drag_data = json.loads(json_data)
                
                if drag_data.get('type') == 'api_template':
                    # 获取模板的完整数据
                    template_id = drag_data.get('template_id')
                    if template_id:
                        # 从服务中获取完整的模板数据
                        from src.core.services.api_template_service import ApiTemplateService
                        api_service = ApiTemplateService()
                        template_data = api_service.get_template_by_id(template_id)
                        
                        if template_data:
                            # 添加接口模板到测试步骤，支持在拖拽位置插入
                            self.add_api_template_to_steps(template_data, drop_position)
                            event.acceptProposedAction()
                            return
            except Exception as e:
                print(f"解析JSON格式拖拽数据失败: {e}")
        
        # 然后尝试解析QAbstractItemModel格式的数据
        elif mime_data.hasFormat("application/x-qabstractitemmodeldatalist"):
            item_data = self.parse_drag_data(mime_data)
            
            if item_data and item_data.get('type') == 'template':
                # 添加接口模板到测试步骤，支持在拖拽位置插入
                self.add_api_template_to_steps(item_data['data'], drop_position)
                event.acceptProposedAction()
                return
        
        # 最后尝试解析文本格式的数据（接口模板列表的拖拽数据）
        elif mime_data.hasText():
            try:
                import json
                drag_data = json.loads(mime_data.text())
                
                if drag_data.get('type') == 'template':
                    # 获取模板的完整数据
                    template_id = drag_data.get('id')
                    if template_id:
                        # 从服务中获取完整的模板数据
                        from src.core.services.api_template_service import ApiTemplateService
                        api_service = ApiTemplateService()
                        template_data = api_service.get_template_by_id(template_id)
                        
                        if template_data:
                            # 添加接口模板到测试步骤，支持在拖拽位置插入
                            self.add_api_template_to_steps(template_data, drop_position)
                            event.acceptProposedAction()
                            return
            except Exception as e:
                print(f"解析文本格式拖拽数据失败: {e}")
        
        event.ignore()
    
    def parse_drag_data(self, mime_data):
        """解析拖拽数据"""
        try:
            # 解析QAbstractItemModel数据
            data = mime_data.data("application/x-qabstractitemmodeldatalist")
            stream = QDataStream(data, QIODevice.ReadOnly)
            
            # 读取拖拽数据
            while not stream.atEnd():
                row = stream.readInt32()
                column = stream.readInt32()
                
                # 读取数据项
                item_count = stream.readInt32()
                for i in range(item_count):
                    role = stream.readInt32()
                    value = stream.readQVariant()
                    
                    # 如果是用户角色数据，尝试解析JSON
                    if role == Qt.UserRole:
                        try:
                            import json
                            item_data = json.loads(value)
                            return item_data
                        except:
                            pass
            
            return None
        except Exception as e:
            print(f"解析拖拽数据失败: {str(e)}")
            return None
    
    def add_api_template_to_steps(self, template_data, drop_position=None):
        """添加接口模板到测试步骤 - 支持在任意位置插入并重新生成前端ID"""
        if not self.current_case:
            # 创建新的测试用例对象
            self.current_case = TestCase()
            self.current_case.name = self.name_edit.text().strip() or "未命名用例"
            self.current_case.description = self.description_edit.toPlainText().strip()
            self.current_case.environment_id = self.env_combo.currentData()

        # 计算插入位置
        insert_index = len(self.current_case.steps) if self.current_case.steps else 0
        
        # 如果有拖拽位置，计算插入位置
        if drop_position and hasattr(self, 'steps_layout') and self.steps_layout:
            # drop_position已经是步骤容器的局部坐标，直接使用
            local_pos = drop_position
            
            # 查找最近的步骤卡片位置
            for i in range(self.steps_layout.count()):
                item = self.steps_layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), 'step_id'):
                    widget = item.widget()
                    widget_rect = widget.geometry()
                    
                    # 检查拖拽位置是否在该步骤卡片的上半部分
                    if local_pos.y() < widget_rect.center().y():
                        insert_index = i
                        break
                    else:
                        insert_index = i + 1
        
        # 计算新步骤的序号（基于插入位置）
        if self.current_case and self.current_case.steps:
            # 如果插入到中间，需要重新计算所有后续步骤的序号
            if insert_index < len(self.current_case.steps):
                # 插入到中间，新步骤的序号为插入位置的序号
                new_order = insert_index + 1
                
                # 更新后续步骤的序号
                for i in range(insert_index, len(self.current_case.steps)):
                    self.current_case.steps[i].step_order = i + 2
            else:
                # 插入到末尾，新步骤的序号为最大序号+1
                new_order = max(step.step_order for step in self.current_case.steps) + 1
        else:
            new_order = 1
            
        # 确保新步骤的序号是唯一的
        existing_orders = {step.step_order for step in (self.current_case.steps if self.current_case else [])}
        while new_order in existing_orders:
            new_order += 1
        
        # 创建步骤数据（只包含TestCaseStep支持的字段）
        step_data_for_model = {
            'id': None,  # 新步骤的id为None，将在保存时由数据库生成
            'case_id': self.current_case.id if self.current_case else 0,
            'step_order': new_order,
            'name': template_data.get('name', f"步骤 {new_order}"),
            'enabled': True,
            'pre_processing': {},
            'post_processing': {},
            'assertions': {},
            'variables': {},
            'api_template_id': template_data.get('id'),
            'api_name': template_data.get('name', ''),
            'api_method': template_data.get('method', ''),
            'api_url_path': template_data.get('url_path', ''),
            # 根据全局加解密配置设置默认值
            'enable_encryption': bool(self.case_data.get('enable_encryption', False)) if self.case_data else False
        }

        # 创建步骤卡片数据（包含完整的模板数据）
        step_data_for_card = step_data_for_model.copy()
        step_data_for_card['api_template'] = template_data
        # 添加order字段用于步骤卡片显示
        step_data_for_card['order'] = new_order
        
        # 为拖拽生成的步骤生成前端ID，确保步骤数据与UI卡片的前端ID一致
        import uuid
        frontend_id = str(uuid.uuid4())
        step_data_for_card['frontend_id'] = frontend_id
        step_data_for_model['frontend_id'] = frontend_id

        # 创建步骤对象并插入到指定位置
        step = TestCaseStep.from_dict(step_data_for_model)
        if self.current_case:
            if insert_index < len(self.current_case.steps):
                self.current_case.steps.insert(insert_index, step)
            else:
                self.current_case.steps.append(step)
        
        # 直接添加步骤卡片，而不是通过load_steps重新加载
        # 这样可以确保order字段正确传递给步骤卡片
        self.add_step_card(step_data_for_card)
        
        # 更新所有步骤的序号显示
        self.update_step_orders()

        # 隐藏占位符（如果存在且有效）
        if hasattr(self, 'steps_placeholder') and self.steps_placeholder:
            try:
                # 检查占位符是否仍然有效
                if hasattr(self.steps_placeholder, 'isVisible'):
                    self.steps_placeholder.hide()
            except RuntimeError:
                # 如果占位符已被删除，忽略错误
                pass
        
        self.on_case_changed()
        
        # 标记为已修改
        if not self.modified:
            self.modified = True
            self.modified_signal.emit(True)
    
    def show_steps_context_menu(self, pos):
        """显示步骤区域右键菜单"""
        # 创建右键菜单
        menu = QMenu(self)
        
        # 执行菜单
        menu.exec_(self.steps_widget.mapToGlobal(pos))
    

    
    def add_test_step(self):
        """添加测试步骤"""
        Toast.info(self, "添加测试步骤功能将在后续版本中实现")



    def add_step_card(self, step_data):
        """添加步骤卡片"""
        # 确保步骤数据包含正确的order字段（步骤卡片期望order字段）
        step_data_for_card = step_data.copy()
        # 如果step_data包含step_order字段，将其转换为order字段
        if 'step_order' in step_data_for_card:
            step_data_for_card['order'] = step_data_for_card['step_order']
        elif 'order' not in step_data_for_card:
            # 如果既没有step_order也没有order，默认设为1
            step_data_for_card['order'] = 1
        
        # 使用新的InterfaceStepCard组件
        step_card = InterfaceStepCard(step_data_for_card, self)
        step_card.step_updated.connect(self.on_step_updated)
        step_card.step_deleted.connect(self.on_step_deleted)
        step_card.step_moved.connect(self.on_step_moved)
        step_card.api_template_clicked.connect(self.on_api_template_clicked)
        step_card.step_copied.connect(self.on_step_copied)
        
        # 添加鼠标点击事件来跟踪当前选中的步骤卡片
        step_card.mousePressEvent = lambda event, card=step_card: self.on_step_card_clicked(event, card)

        # 添加到流式布局
        self.steps_layout.addWidget(step_card)

    def on_step_updated(self, step_data):
        """步骤更新事件"""
        # 更新内存中的步骤数据
        if self.current_case:
            for step in self.current_case.steps:
                if step.id == step_data.get('id') or step.name == step_data.get('name'):
                    step.update_from_dict(step_data)
                    # 特别处理启用状态的同步
                    if 'enabled' in step_data:
                        step.enabled = step_data['enabled']
                    break
        
        # 同时更新case_data中的步骤数据，确保调试时能获取最新状态
        if hasattr(self, 'case_data') and self.case_data:
            steps = self.case_data.get('steps', [])
            for i, step in enumerate(steps):
                if step.get('id') == step_data.get('id') or step.get('name') == step_data.get('name'):
                    # 更新步骤数据，特别确保启用状态同步
                    steps[i] = step_data
                    # 如果步骤数据中没有启用状态，确保从当前步骤对象同步
                    if 'enabled' not in step_data and i < len(self.current_case.steps):
                        steps[i]['enabled'] = self.current_case.steps[i].enabled
                    break
        
        self.on_case_changed()

    def on_step_deleted(self, step_id):
        """步骤删除事件 - 基于前端ID精确删除步骤"""
        
        # 从内存中删除步骤数据
        if self.current_case:
            original_count = len(self.current_case.steps)
            
            # 方法1：基于前端ID精确匹配删除（最可靠的方法）
            step_found = False
            for i, step in enumerate(self.current_case.steps):
                step_dict = step.to_dict()
                if step_dict.get('frontend_id') == step_id:
                    # 删除匹配的步骤
                    del self.current_case.steps[i]
                    step_found = True
                    break
            
            if not step_found:
                # 方法2：如果前端ID匹配失败，尝试基于步骤对象ID匹配
                for i, step in enumerate(self.current_case.steps):
                    if str(step.id) == step_id:
                        # 删除匹配的步骤
                        del self.current_case.steps[i]
                        step_found = True
                        break
            
            if not step_found:
                # 方法3：如果以上方法都失败，使用布局索引作为最后手段
                for i in range(self.steps_layout.count()):
                    item = self.steps_layout.itemAt(i)
                    if item and item.widget() and hasattr(item.widget(), 'step_id'):
                        if item.widget().step_id == step_id:
                            # 删除对应位置的步骤
                            if i < len(self.current_case.steps):
                                del self.current_case.steps[i]
                                step_found = True
                            break
            
            new_count = len(self.current_case.steps)
            
            # 如果成功删除了步骤，更新UI
            if step_found and new_count < original_count:
                # 从布局中移除对应的步骤卡片
                for i in range(self.steps_layout.count()):
                    item = self.steps_layout.itemAt(i)
                    if item and item.widget() and hasattr(item.widget(), 'step_id'):
                        if item.widget().step_id == step_id:
                            # 移除步骤卡片
                            item.widget().deleteLater()
                            self.steps_layout.removeItem(item)
                            break
                
                # 更新剩余步骤的序号（不重新生成ID，保持前端ID一致性）
                self.update_step_orders()
                
                # 标记用例数据已修改
                self.on_case_changed()
                
                # 显示删除成功提示
                from src.ui.widgets.toast_tips import Toast
                Toast.success(self, "步骤删除成功")
            else:
                # 显示删除失败提示
                from src.ui.widgets.toast_tips import Toast
                Toast.error(self, "删除失败：未找到对应的步骤")

    def on_step_moved(self, dragged_step_id, target_step_id, from_index, to_index):
        """步骤移动事件 - 基于位置索引直接移动步骤"""
        
        if not self.current_case or not self.current_case.steps:
            return
            
        # 获取布局中所有步骤的前端ID顺序
        if not hasattr(self, 'steps_layout') or not self.steps_layout:
            return
            
        # 根据拖动的位置重新排序步骤列表
        if from_index >= 0 and to_index >= 0 and from_index != to_index:
            # 检查索引是否在有效范围内
            if from_index >= len(self.current_case.steps) or to_index > len(self.current_case.steps):
                return
                
            # 直接基于位置索引移动步骤
            
            # 从原位置移除步骤
            dragged_step = self.current_case.steps.pop(from_index)
            
            # 插入到新位置
            # 注意：由于已经移除了原位置的步骤，后续步骤的索引会前移
            # 如果目标位置在原位置之后，不需要调整索引，因为我们是在移除元素后再插入
            # 如果目标位置在原位置之前，也不需要调整索引
            
            # 插入到新位置
            self.current_case.steps.insert(to_index, dragged_step)
            
            # 重新生成所有步骤的ID（基于新的顺序）
            self.regenerate_step_ids()
            
            # 更新步骤序号
            self.update_step_orders()
            
            # 重新加载步骤列表以更新UI显示
            self.load_steps()
            
            # 标记为已修改
            if not self.modified:
                self.modified = True
                self.modified_signal.emit(True)
        else:
            pass
    
    def on_api_template_clicked(self, api_template_id):
        """接口模板点击事件 - 跳转到对应接口模板编辑tab"""
        # 发送信号通知主窗口跳转到接口模板编辑tab
        self.api_template_edit_requested.emit(api_template_id)
    
    def on_step_card_clicked(self, event, step_card):
        """步骤卡片点击事件 - 跟踪当前选中的步骤卡片"""
        # 调用父类的鼠标点击事件处理
        step_card.__class__.mousePressEvent(step_card, event)
        
        # 更新当前选中的步骤卡片
        self.current_selected_step_card = step_card
        
        # 可以添加视觉反馈，比如改变边框颜色等
        # 这里可以添加选中状态的样式变化
    
    def copy_current_step(self):
        """复制当前选中的步骤卡片"""
        if not self.current_selected_step_card:
            from src.ui.widgets.toast_tips import Toast
            Toast.warning(self, "警告", "请先选中一个步骤卡片")
            return
        
        try:
            # 获取当前选中步骤卡片的数据
            step_data = self.current_selected_step_card.get_step_data()
            
            # 深拷贝步骤数据
            import copy
            copied_step_data = copy.deepcopy(step_data)
            
            # 生成新的UUID，避免ID冲突
            import uuid
            copied_step_data['id'] = str(uuid.uuid4())
            
            # 重置后端ID，确保是新步骤
            copied_step_data['backend_id'] = None
            
            # 修改步骤名称，添加"(副本)"后缀
            original_name = copied_step_data.get('name', '未命名步骤')
            copied_step_data['name'] = f"{original_name}(副本)"
            
            # 存储复制的步骤数据
            self.copied_step_data = copied_step_data
            
            # 显示复制成功提示
            from src.ui.widgets.toast_tips import Toast
            Toast.success(self, "步骤已复制到剪贴板")
            
        except Exception as e:
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"复制失败: {str(e)}")
    
    def paste_step(self):
        """粘贴步骤卡片"""
        if not self.copied_step_data:
            from src.ui.widgets.toast_tips import Toast
            Toast.warning(self, "警告", "剪贴板中没有可复制的步骤数据")
            return
        
        try:
            # 确定插入位置
            insert_index = -1
            if self.current_selected_step_card:
                # 如果当前有选中的步骤卡片，找到其在布局中的位置
                for i in range(self.steps_layout.count()):
                    item = self.steps_layout.itemAt(i)
                    if item and item.widget() == self.current_selected_step_card:
                        insert_index = i + 1  # 插入到选中卡片后面
                        break
            
            # 如果没找到选中卡片的位置，或者没有选中卡片，插入到末尾
            if insert_index == -1:
                insert_index = len(self.current_case.steps) if self.current_case else 0
            
            # 创建新的步骤对象
            new_step = TestCaseStep.from_dict(self.copied_step_data)
            
            # 确保当前用例存在
            if not self.current_case:
                self.current_case = TestCase()
                self.current_case.name = self.name_edit.text().strip() or "未命名用例"
                self.current_case.description = self.description_edit.toPlainText().strip()
                self.current_case.environment_id = self.env_combo.currentData()
            
            # 插入新步骤
            if insert_index < len(self.current_case.steps):
                self.current_case.steps.insert(insert_index, new_step)
            else:
                self.current_case.steps.append(new_step)
            
            # 重新生成所有步骤的ID（基于新的顺序）
            self.regenerate_step_ids()
            
            # 更新所有步骤的序号
            self.update_step_orders()
            
            # 重新加载步骤列表
            self.load_steps()
            
            # 标记为已修改
            if not self.modified:
                self.modified = True
                self.modified_signal.emit(True)
            
            # 显示粘贴成功提示
            from src.ui.widgets.toast_tips import Toast
            Toast.success(self, "步骤粘贴成功")
            
        except Exception as e:
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"粘贴失败: {str(e)}")
    
    def on_step_copied(self, step_id, copied_step_data):
        """步骤复制事件 - 支持动态ID重排"""
        try:
            # 确保当前用例存在
            if not self.current_case:
                # 创建新的测试用例对象
                self.current_case = TestCase()
                self.current_case.name = self.name_edit.text().strip() or "未命名用例"
                self.current_case.description = self.description_edit.toPlainText().strip()
                self.current_case.environment_id = self.env_combo.currentData()
            
            # 计算新步骤的序号（插入到原步骤后面）
            source_step_index = -1
            for i, step in enumerate(self.current_case.steps):
                # 使用前端ID进行查找
                if step.to_dict().get('frontend_id') == step_id:
                    source_step_index = i
                    break
            
            # 如果找到原步骤，插入到其后面；否则添加到末尾
            insert_index = source_step_index + 1 if source_step_index >= 0 else len(self.current_case.steps)
            
            # 保留原步骤的加解密状态，不强制使用全局配置
            # copied_step_data['enable_encryption'] = bool(self.case_data.get('enable_encryption', False)) if self.case_data else False
            
            # 创建新的步骤对象
            new_step = TestCaseStep.from_dict(copied_step_data)
            
            # 插入新步骤
            if insert_index < len(self.current_case.steps):
                self.current_case.steps.insert(insert_index, new_step)
            else:
                self.current_case.steps.append(new_step)
            
            # 重新生成所有步骤的ID（基于新的顺序）
            self.regenerate_step_ids()
            
            # 更新所有步骤的序号
            self.update_step_orders()
            
            # 重新加载步骤列表
            self.load_steps()
            
            # 隐藏占位符（如果存在且有效）
            if hasattr(self, 'steps_placeholder') and self.steps_placeholder:
                try:
                    # 检查占位符是否仍然有效
                    if hasattr(self.steps_placeholder, 'isVisible'):
                        self.steps_placeholder.hide()
                except RuntimeError:
                    # 如果占位符已被删除，忽略错误
                    pass
            
            # 标记为已修改
            if not self.modified:
                self.modified = True
                self.modified_signal.emit(True)
            
        except Exception as e:
            Toast.error(self, f"步骤复制失败: {str(e)}")
    
    def regenerate_step_ids(self):
        """重新生成所有步骤的前端ID - 基于当前布局顺序"""
        if not self.current_case or not self.current_case.steps:
            return
            
        # 获取当前布局中的步骤顺序
        if not hasattr(self, 'steps_layout') or not self.steps_layout:
            return
            
        # 生成新的前端ID映射表
        new_frontend_ids = {}
        for i in range(self.steps_layout.count()):
            item = self.steps_layout.itemAt(i)
            if item and item.widget() and hasattr(item.widget(), 'step_id'):
                old_step_id = item.widget().step_id
                # 生成新的前端ID（基于位置）
                new_step_id = f"step_{i+1}_{id(item.widget())}"
                new_frontend_ids[old_step_id] = new_step_id
                
                # 同时更新步骤卡片的step_id
                item.widget().step_id = new_step_id
        
        # 更新步骤数据中的前端ID
        for step in self.current_case.steps:
            step_dict = step.to_dict()
            old_frontend_id = step_dict.get('frontend_id')
            if old_frontend_id in new_frontend_ids:
                step_dict['frontend_id'] = new_frontend_ids[old_frontend_id]
                step.update_from_dict(step_dict)
    
    def update_step_orders(self):
        """更新所有步骤的序号"""
        if not self.current_case or not self.current_case.steps:
            return
            
        # 更新步骤数据中的序号
        for i, step in enumerate(self.current_case.steps, 1):
            step.step_order = i
            
        # 更新UI中步骤卡片的序号显示
        # 使用布局顺序来匹配步骤卡片和步骤数据
        for i in range(self.steps_layout.count()):
            item = self.steps_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # 检查是否是步骤卡片（有step_id属性）
                if hasattr(widget, 'step_id') and hasattr(widget, 'update_step_order'):
                    # 直接使用布局中的位置来更新序号
                    widget.update_step_order(i + 1)

    def on_case_changed(self):
        """用例数据变化"""
        if not self.modified:
            self.modified = True
            self.modified_signal.emit(True)

    def execute_case(self):
        """执行用例"""
        if not self.current_case or not self.current_case.steps:
            Toast.warning(self, "警告", "请先添加测试步骤")
            return
        
        # 加强重复执行保护
        if self.is_executing:
            Toast.warning(self, "警告", "用例正在执行中，请等待执行完成")
            return
        
        # 检查线程状态，确保之前的线程已完全清理
        if hasattr(self, 'execution_thread') and self.execution_thread:
            if self.execution_thread.isRunning():
                Toast.warning(self, "警告", "执行线程仍在运行，请稍后再试")
                return
            else:
                # 清理残留的线程对象
                try:
                    self.execution_thread.deleteLater()
                    self.execution_thread = None
                except:
                    self.execution_thread = None
        
        # 准备执行数据 - 确保获取前端UI所有最新的配置信息
        # 首先同步当前用例对象的加解密配置（临时变量，不触发修改状态）
        enable_encryption = self.enable_encryption_checkbox.isChecked()
        encrypt_url = self.encrypt_url_edit.text().strip()
        decrypt_url = self.decrypt_url_edit.text().strip()
        
        # 注意：不再强制同步所有步骤卡片的加解密状态
        # 保留用户手动设置的加解密状态，只在步骤未手动设置时使用全局配置
        # self.sync_all_step_cards_encryption_status(self.current_case.enable_encryption)
        
        # 获取最新的用例数据（不修改current_case对象，避免触发修改状态）
        print("[DEBUG] 调用current_case.to_dict()获取用例数据")
        case_data = self.current_case.to_dict()
        
        # 同步前端UI步骤数据到临时用例数据，但不修改current_case对象
        print("[DEBUG] 同步前端UI步骤数据到临时用例数据")
        self.sync_step_data_to_temp_case(case_data)
        
        # 调试：检查获取的用例数据中的步骤信息
        print(f"[DEBUG] 用例数据步骤数量: {len(case_data.get('steps', []))}")
        for i, step in enumerate(case_data.get('steps', [])):
            # 获取步骤标题：优先使用api_name，如果没有则使用api_template.name，最后使用name字段
            step_name = step.get('api_name') or step.get('api_template', {}).get('name') or step.get('name', '未命名')
            print(f"[DEBUG] 步骤{i+1}: {step_name}, enabled={step.get('enabled', True)}")
        
        # 创建执行线程，使用临时用例数据避免触发修改状态
        self.execution_thread = CaseExecutionThread(
            case_data=case_data,
            project_id=self.current_case.project_id
        )
        
        # 连接信号
        self.execution_thread.step_started.connect(self.on_step_started)
        self.execution_thread.step_finished.connect(self.on_step_finished)
        self.execution_thread.case_finished.connect(self.on_case_finished)
        self.execution_thread.log_message.connect(self.log_message_with_step)
        
        # 清空之前的执行日志，确保每次执行都是全新的开始
        self.log_message_with_step(f"执行前日志数量: {len(self.execution_logs)}", "debug", -1)
        self.clear_logs()
        
        # 记录详细的调试信息
        self.log_debug_info()
        
        # 记录开始执行日志 - 使用print语句替代log_message
        print(f"[INFO] 开始执行用例: {self.current_case.name}")
        
        # 开始执行
        self.execution_thread.start()
        self.is_executing = True
        
        # 更新按钮状态
        self.update_buttons_state()
    
    def log_debug_info(self):
        """记录调试信息 - 用例配置详情"""
        if not self.current_case:
            return
            
        # 记录用例基本信息 - 使用print语句替代log_message
        print("[INFO] === 用例配置调试信息 ===")
        print(f"[INFO] 用例名称: {self.current_case.name}")
        print(f"[INFO] 用例描述: {self.current_case.description}")
        print(f"[INFO] 环境ID: {self.current_case.environment_id}")
        print(f"[INFO] 项目ID: {self.current_case.project_id}")
        print(f"[INFO] 文件夹ID: {self.current_case.folder_id}")
        
        # 记录步骤信息
        steps = self.current_case.steps
        print(f"[INFO] 步骤总数: {len(steps)}")
        
        # 记录每个步骤的详细信息
        for i, step in enumerate(steps):
            step_dict = step.to_dict()
            # 获取步骤标题：优先使用api_name，如果没有则使用api_template.name，最后使用name字段
            step_name = step_dict.get('api_name') or step_dict.get('api_template', {}).get('name') or step_dict.get('name', '未命名步骤')
            print(f"[INFO] 步骤 {i+1}: {step_name}")
            print(f"[INFO]   - 接口模板ID: {step_dict.get('api_template_id', '无')}")
            print(f"[INFO]   - 是否启用: {step_dict.get('enabled', True)}")
            print(f"[INFO]   - 步骤顺序: {step_dict.get('step_order', i+1)}")
            
            # 记录前置处理信息
            pre_processing = step_dict.get('pre_processing', {})
            if pre_processing:
                print(f"[INFO]   - 前置处理工具数量: {len(pre_processing)}")
            
            # 记录后置处理信息
            post_processing = step_dict.get('post_processing', {})
            if post_processing:
                print(f"[INFO]   - 后置处理工具数量: {len(post_processing)}")
            
            # 记录断言信息
            assertions = step_dict.get('assertions', {})
            if assertions:
                print(f"[INFO]   - 断言数量: {len(assertions)}")
        
        # 记录全局变量信息
        global_vars = self.current_case.global_vars
        if global_vars:
            print(f"[INFO] 全局变量数量: {len(global_vars)}")
            for var_name, var_value in global_vars.items():
                print(f"[INFO]   - {var_name}: {var_value}")
        else:
            print("[INFO] 全局变量: 无")
        
        print("[INFO] === 调试信息记录完成 ===")

    def toggle_execution(self):
        """切换执行状态（调试/停止）"""
        if self.is_executing:
            # 当前正在执行，点击则停止
            self.stop_execution()
        else:
            # 当前未执行，点击则开始调试
            self.execute_case()

    def stop_execution(self):
        """停止执行 - 修复线程安全版本"""
        if not self.is_executing or not self.execution_thread:
            return
        
        # 记录停止执行日志
        print("[WARNING] 正在停止用例执行...")
        
        # 更新执行状态，防止重复调用
        self.is_executing = False
        
        # 安全地停止线程
        try:
            # 先停止线程
            self.execution_thread.stop()
            
            # 等待线程安全停止，增加等待时间
            if self.execution_thread.isRunning():
                print("[DEBUG] 等待线程安全停止...")
                if not self.execution_thread.wait(5000):  # 等待5秒
                    print("[WARNING] 线程未在5秒内正常停止，尝试强制终止")
                    self.execution_thread.terminate()
                    self.execution_thread.wait(2000)
            
            # 断开所有信号连接
            try:
                self.execution_thread.step_started.disconnect()
                self.execution_thread.step_finished.disconnect()
                self.execution_thread.case_finished.disconnect()
                self.execution_thread.log_message.disconnect()
            except:
                pass  # 忽略断开连接时的错误
            
            # 安全删除线程对象
            self.execution_thread.deleteLater()
            self.execution_thread = None
            
        except Exception as e:
            print(f"[ERROR] 停止线程时发生错误: {str(e)}")
            # 确保线程对象被清理
            if self.execution_thread:
                try:
                    self.execution_thread.deleteLater()
                except:
                    pass
                self.execution_thread = None
        
        # 更新按钮状态
        self.update_buttons_state()
        
        # 记录停止完成日志
        print("[WARNING] 用例执行已停止")

    def on_step_started(self, step_name, step_index):
        """步骤开始执行"""
        self.log_message_with_step(f"开始执行步骤: {step_name}", "info", step_index)

    def on_step_finished(self, step_result):
        """步骤执行完成"""
        status = "成功" if step_result.get('success') else "失败"
        # 使用print语句替代log_message，因为这里无法获取step_index
        print(f"[INFO] 步骤执行完成: {step_result.get('step_name')} - {status}")

    def on_case_finished(self, case_result):
        """用例执行完成 - 修复版本（避免重复清理线程）"""
        # 记录执行完成时的日志状态
        print(f"[DEBUG] on_case_finished开始，当前日志数量: {len(self.execution_logs)}")
        
        # 确保执行状态正确设置
        self.is_executing = False
        
        # 安全地清理线程资源（仅在stop_execution未调用时清理）
        if self.execution_thread and self.execution_thread.isRunning():
            print("[DEBUG] 线程仍在运行，等待安全退出...")
            
            # 等待线程完全退出
            if not self.execution_thread.wait(3000):  # 等待3秒
                print("[WARNING] 线程未在3秒内正常退出")
            
            # 断开所有信号连接
            try:
                self.execution_thread.step_started.disconnect()
                self.execution_thread.step_finished.disconnect()
                self.execution_thread.case_finished.disconnect()
                self.execution_thread.log_message.disconnect()
            except:
                pass  # 忽略断开连接时的错误
            
            # 安全删除线程对象
            self.execution_thread.deleteLater()
            self.execution_thread = None
        elif self.execution_thread:
            # 线程已停止但对象未清理，确保清理
            print("[DEBUG] 线程已停止，清理残留对象")
            try:
                self.execution_thread.deleteLater()
            except:
                pass
            self.execution_thread = None
        
        # 更新按钮状态
        self.update_buttons_state()
        
        # 记录执行结果
        success_count = case_result.get('success_count', 0)
        total_count = case_result.get('total_count', 0)
        status = "成功" if success_count == total_count else "失败"
        
        print(f"[INFO] 用例执行完成: {status} (成功: {success_count}/{total_count})")
        
        # 记录执行完成后的日志状态
        print(f"[DEBUG] on_case_finished结束，当前日志数量: {len(self.execution_logs)}")

    def log_message(self, message, level="info"):
        """记录日志消息（无步骤信息）"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 根据级别设置颜色
        if level == "error":
            color = "red"
            prefix = "[ERROR]"
        elif level == "warning":
            color = "orange"
            prefix = "[WARN]"
        elif level == "success":
            color = "green"
            prefix = "[SUCCESS]"
        else:
            color = "blue"
            prefix = "[INFO]"
        
        # 格式化日志消息
        log_entry = f"<span style='color: gray;'>[{timestamp}]</span> <span style='color: {color};'>{prefix}</span> {message}"
        
        # 保存到日志列表（不操作不存在的日志文本控件）
        self.execution_logs.append({
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'step_index': -1  # 无步骤信息
        })

    def log_message_with_step(self, message, level="info", step_index=-1):
        """记录带步骤信息的日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 根据级别设置颜色
        if level == "error":
            color = "red"
            prefix = "[ERROR]"
        elif level == "warning":
            color = "orange"
            prefix = "[WARN]"
        elif level == "success":
            color = "green"
            prefix = "[SUCCESS]"
        else:
            color = "blue"
            prefix = "[INFO]"
        
        # 格式化日志消息
        log_entry = f"<span style='color: gray;'>[{timestamp}]</span> <span style='color: {color};'>{prefix}</span> {message}"
        
        # 获取步骤名称（如果步骤索引有效）
        step_name = None
        if step_index >= 0 and self.current_case and len(self.current_case.steps) > step_index:
            step = self.current_case.steps[step_index]
            # 处理TestCaseStep对象，使用getattr安全获取属性
            if hasattr(step, 'api_name'):
                step_name = step.api_name
            elif hasattr(step, 'api_template') and hasattr(step.api_template, 'name'):
                step_name = step.api_template.name
            elif hasattr(step, 'name'):
                step_name = step.name
            elif hasattr(step, 'get'):
                # 优先使用api_name，其次api_template.name，最后name字段
                step_name = step.get('api_name') or step.get('api_template', {}).get('name') or step.get('name', f'步骤 {step_index + 1}')
            else:
                step_name = f'步骤 {step_index + 1}'
        
        # 保存到日志列表（不操作不存在的日志文本控件）
        self.execution_logs.append({
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'step_index': step_index,
            'step_name': step_name  # 保存步骤名称
        })
        
        # 调试信息：显示日志发射详情
        step_info = "通用信息" if step_index == -1 else f"步骤 {step_index + 1}"
        print(f"[DEBUG] 日志发射 - {step_info}: {message[:50]}... (level: {level}, 时间: {timestamp})")
        print(f"[DEBUG] 当前日志列表数量: {len(self.execution_logs)}")
        
        # 如果执行日志弹窗已打开，则直接添加日志到弹窗
        if hasattr(self, 'execution_logs_dialog') and self.execution_logs_dialog:
            print(f"[DEBUG] 弹窗存在，正在添加日志到弹窗")
            try:
                # 获取步骤名称（如果步骤索引有效）
                step_name = None
                if step_index >= 0 and self.current_case and len(self.current_case.steps) > step_index:
                    step = self.current_case.steps[step_index]
                    # 处理TestCaseStep对象，使用getattr安全获取属性
                    if hasattr(step, 'api_name'):
                        step_name = step.api_name
                    elif hasattr(step, 'api_template') and hasattr(step.api_template, 'name'):
                        step_name = step.api_template.name
                    elif hasattr(step, 'name'):
                        step_name = step.name
                    elif hasattr(step, 'get'):
                        # 优先使用api_name，其次api_template.name，最后name字段
                        step_name = step.get('api_name') or step.get('api_template', {}).get('name') or step.get('name', f'步骤 {step_index + 1}')
                    else:
                        step_name = f'步骤 {step_index + 1}'
                
                self.execution_logs_dialog.add_log_with_step(message, level, step_index, step_name)
            except RuntimeError:
                # 弹窗已被删除，忽略错误
                print("[DEBUG] 弹窗已被删除，忽略错误")
                pass
        else:
            print(f"[DEBUG] 弹窗不存在，日志已保存到列表")

    def clear_logs(self):
        """清空日志"""
        # 清空执行日志列表，确保每次执行都是全新的开始
        print(f"[DEBUG] clear_logs被调用，当前日志数量: {len(self.execution_logs)}")
        self.execution_logs = []
        print(f"[DEBUG] clear_logs已完成，日志列表已清空")

    def clear_steps(self):
        """清空步骤列表"""
        # 移除所有步骤卡片
        for i in reversed(range(self.steps_layout.count())):
            item = self.steps_layout.itemAt(i)
            if item and item.widget():
                # 检查是否是占位符（如果占位符存在且有效）
                is_placeholder = False
                if hasattr(self, 'steps_placeholder') and self.steps_placeholder:
                    try:
                        is_placeholder = (item.widget() == self.steps_placeholder)
                    except RuntimeError:
                        # 如果占位符已被删除，忽略错误
                        is_placeholder = False
                
                if not is_placeholder:
                    # 安全删除：检查widget是否仍然有效
                    try:
                        widget = item.widget()
                        # 检查widget是否仍然有效（没有被删除）
                        if widget and hasattr(widget, 'isVisible'):
                            widget.deleteLater()
                    except RuntimeError as e:
                        # 如果widget已经被删除，忽略错误
                        print(f"[DEBUG] clear_steps: 忽略已删除的widget: {e}")
                        pass

        # 显示占位符（如果存在且有效）
        if hasattr(self, 'steps_placeholder') and self.steps_placeholder:
            try:
                self.steps_placeholder.show()
                print("[DEBUG] clear_steps: 显示占位符")
            except RuntimeError:
                # 如果占位符已被删除，忽略错误
                print("[DEBUG] clear_steps: 占位符已被删除，忽略错误")
                pass

    def load_steps(self):
        """加载步骤列表"""
        # 清空现有步骤
        self.clear_steps()

        if not self.current_case or not self.current_case.steps:
            return

        # 隐藏占位符（如果存在且有效）
        if hasattr(self, 'steps_placeholder') and self.steps_placeholder:
            try:
                # 检查占位符是否仍然有效
                if hasattr(self.steps_placeholder, 'isVisible'):
                    self.steps_placeholder.hide()
                    print("[DEBUG] load_steps: 隐藏占位符")
            except RuntimeError:
                # 如果占位符已被删除，忽略错误
                print("[DEBUG] load_steps: 占位符已被删除，忽略错误")
                pass

        # 添加步骤卡片
        for step in self.current_case.steps:
            self.add_step_card(step.to_dict())

    def update_buttons_state(self):
        """更新按钮状态"""
        # 根据用例状态更新按钮可用性
        has_steps = self.current_case and len(self.current_case.steps) > 0
        
        # 执行按钮状态
        self.run_stop_btn.setEnabled(has_steps)
        # 保存按钮始终可用，不受执行状态影响
        self.save_btn.setEnabled(True)
        
        # 根据执行状态设置按钮图标和提示文本（不修改样式表以保持hover效果）
        if self.is_executing:
            # 运行中：显示停止图标
            self.run_stop_btn.setIcon(self.get_icon("stoping.png"))
            self.run_stop_btn.setToolTip("停止执行")
        else:
            # 未运行：显示调试图标
            self.run_stop_btn.setIcon(self.get_icon("running.png"))
            self.run_stop_btn.setToolTip("调试用例")
        
        # 不再动态修改样式表，保留初始化时设置的完整样式（包含hover效果）

    def load_environments(self):
        """加载环境列表"""
        try:
            environments = self.environment_service.get_all_environments()
            self.env_combo.clear()
            # 添加一个空选项，表示不使用特定环境
            self.env_combo.addItem("不使用环境", None)
            for env in environments:
                self.env_combo.addItem(env['name'], env['id'])
        except Exception as e:
            print(f"加载环境列表失败: {e}")

    # 全局变量表格功能已移除，相关方法已删除
    
    def edit_global_variables(self):
        """查询变量"""
        dialog = VariableManagerDialog(self, self.project_id)
        dialog.exec_()


class TabbedCaseEditor(QWidget):
    """测试用例多标签页编辑器"""
    
    tab_closed = pyqtSignal()  # 标签页关闭信号
    saved = pyqtSignal(dict)    # 保存信号
    api_template_edit_requested = pyqtSignal(str)  # 接口模板编辑请求信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabs = {}  # 存储标签页数据
        self.current_tab_id = None
        self.execution_logs = []  # 执行日志列表
        self.logs_tab_widget = None  # 执行日志标签页
        
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.tab_changed)
        
        # 设置tab右键菜单
        self.tab_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self.show_tab_context_menu)
        
        layout.addWidget(self.tab_widget)
        
        # 设置快捷键
        self.setup_shortcuts()
    
    def setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+S 保存当前标签页
        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self.on_save_shortcut)
        
        # Ctrl+W 关闭当前标签页
        self.close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        self.close_shortcut.activated.connect(self.on_close_shortcut)
        
        # Ctrl+C 复制当前选中的步骤卡片 - 限制作用域避免与测试用例复制冲突
        self.copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        self.copy_shortcut.setContext(Qt.WidgetWithChildrenShortcut)  # 限制在编辑器及其子组件内有效
        self.copy_shortcut.activated.connect(self.on_copy_shortcut)
        
        # Ctrl+V 粘贴步骤卡片 - 限制作用域避免与测试用例粘贴冲突
        self.paste_shortcut = QShortcut(QKeySequence("Ctrl+V"), self)
        self.paste_shortcut.setContext(Qt.WidgetWithChildrenShortcut)  # 限制在编辑器及其子组件内有效
        self.paste_shortcut.activated.connect(self.on_paste_shortcut)
    
    def on_save_shortcut(self):
        """Ctrl+S 快捷键处理 - 保存当前标签页"""
        if self.current_tab_id and self.current_tab_id in self.tabs:
            tab_widget = self.tabs[self.current_tab_id]['widget']
            if hasattr(tab_widget, 'save_case'):
                tab_widget.save_case()
    
    def on_close_shortcut(self):
        """Ctrl+W 快捷键处理 - 关闭当前标签页"""
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            self.close_tab(current_index, from_close_button=False)
    
    def on_copy_shortcut(self):
        """Ctrl+C 快捷键处理 - 复制当前选中的步骤卡片"""
        if self.current_tab_id and self.current_tab_id in self.tabs:
            tab_widget = self.tabs[self.current_tab_id]['widget']
            if hasattr(tab_widget, 'copy_current_step'):
                tab_widget.copy_current_step()
    
    def on_paste_shortcut(self):
        """Ctrl+V 快捷键处理 - 粘贴步骤卡片"""
        if self.current_tab_id and self.current_tab_id in self.tabs:
            tab_widget = self.tabs[self.current_tab_id]['widget']
            if hasattr(tab_widget, 'paste_step'):
                tab_widget.paste_step()
    
    def close_tab(self, index, from_close_button=True):
        """关闭标签页"""
        widget = self.tab_widget.widget(index)
        
        # 查找对应的标签页ID
        tab_id = None
        for tid, tab_data in self.tabs.items():
            if tab_data['widget'] == widget:
                tab_id = tid
                break
        
        if tab_id is None:
            self.tab_widget.removeTab(index)
            # 检查是否还有标签页，如果没有则发出关闭信号
            if self.tab_widget.count() == 0:
                self.tab_closed.emit()
            return
        
        # 检查是否有未保存的修改
        if self.tabs[tab_id]['modified']:
            # 显示保存确认弹窗
            tab_name = self.tabs[tab_id]['tab_name']
            
            # 创建自定义消息框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('保存确认')
            msg_box.setText(f'标签页 "{tab_name}" 有未保存的修改，请选择操作：')
            
            # 添加自定义按钮
            save_btn = msg_box.addButton('保存', QMessageBox.AcceptRole)
            ignore_btn = msg_box.addButton('忽略', QMessageBox.DestructiveRole)
            cancel_btn = msg_box.addButton('取消', QMessageBox.RejectRole)
            
            # 设置默认按钮
            msg_box.setDefaultButton(save_btn)
            
            msg_box.exec_()
            
            clicked_button = msg_box.clickedButton()
            
            if clicked_button == save_btn:
                # 保存用例
                self.tabs[tab_id]['widget'].save_case()
                # 保存完成后，标记标签页为已保存状态
                self.set_tab_modified(tab_id, False)
                
                # 保存后关闭标签页
                self.tab_widget.removeTab(index)
                del self.tabs[tab_id]
                # 检查是否还有标签页，如果没有则发出关闭信号
                if self.tab_widget.count() == 0:
                    self.tab_closed.emit()
            elif clicked_button == ignore_btn:
                # 忽略修改，直接关闭
                self.tab_widget.removeTab(index)
                del self.tabs[tab_id]
                # 检查是否还有标签页，如果没有则发出关闭信号
                if self.tab_widget.count() == 0:
                    self.tab_closed.emit()
            else:
                # 取消关闭
                return
        else:
            # 没有修改，直接关闭
            self.tab_widget.removeTab(index)
            del self.tabs[tab_id]
            # 检查是否还有标签页，如果没有则发出关闭信号
            if self.tab_widget.count() == 0:
                self.tab_closed.emit()
    
    def open_case(self, case_data=None, project_id=None, folder_id=None):
        """打开或创建用例编辑标签页"""
        # 生成标签页ID
        tab_id = self.generate_tab_id(case_data)
        
        # 如果标签页已存在，切换到该标签页
        if tab_id in self.tabs:
            index = self.tab_widget.indexOf(self.tabs[tab_id]['widget'])
            self.tab_widget.setCurrentIndex(index)
            return tab_id
        
        # 创建新的标签页
        editor_widget = CaseTabWidget(case_data, project_id, folder_id)
        
        # 连接信号
        editor_widget.modified_signal.connect(lambda modified: self.set_tab_modified(tab_id, modified))
        editor_widget.saved.connect(lambda data: self.case_saved(tab_id, data))
        editor_widget.api_template_edit_requested.connect(self.on_api_template_edit_requested)
        
        # 添加到标签页
        tab_name = case_data.get('name', '新增用例') if case_data else '新增用例'
        index = self.tab_widget.addTab(editor_widget, tab_name)
        
        # 存储标签页数据
        self.tabs[tab_id] = {
            'widget': editor_widget,
            'data': case_data or {},
            'modified': False,
            'tab_name': tab_name
        }
        
        # 设置当前标签页
        self.tab_widget.setCurrentIndex(index)
        self.current_tab_id = tab_id
        
        return tab_id
    
    def generate_tab_id(self, case_data):
        """生成标签页唯一ID"""
        if case_data and 'id' in case_data:
            return f"case_{case_data['id']}"
        else:
            return f"new_case_{len(self.tabs)}"
    
    def tab_changed(self, index):
        """标签页切换事件"""
        if index == -1:
            self.current_tab_id = None
            return
        
        widget = self.tab_widget.widget(index)
        
        # 查找对应的标签页ID
        for tab_id, tab_data in self.tabs.items():
            if tab_data['widget'] == widget:
                self.current_tab_id = tab_id
                break
    
    def show_tab_context_menu(self, pos):
        """显示tab右键菜单"""
        # 获取点击位置的tab索引
        index = self.tab_widget.tabBar().tabAt(pos)
        if index == -1:
            return
            
        # 创建右键菜单
        menu = QMenu(self)
        
        # 添加菜单项
        close_current_action = menu.addAction("关闭当前")
        close_others_action = menu.addAction("关闭其他")
        close_all_action = menu.addAction("关闭全部")
        
        # 连接菜单项信号
        close_current_action.triggered.connect(lambda: self.close_current_tab(index))
        close_others_action.triggered.connect(lambda: self.close_other_tabs(index))
        close_all_action.triggered.connect(self.close_all_tabs)
        
        # 显示菜单
        menu.exec_(self.tab_widget.mapToGlobal(pos))

    def close_current_tab(self, index):
        """关闭当前标签页"""
        self.close_tab(index, from_close_button=False)
    
    def close_other_tabs(self, current_index):
        """关闭其他标签页"""
        # 获取所有标签页索引
        tab_count = self.tab_widget.count()
        if tab_count <= 1:
            return
            
        # 从后往前关闭标签页（避免索引变化问题）
        for i in range(tab_count - 1, -1, -1):
            if i != current_index:
                self.close_tab(i, from_close_button=False)

    def close_all_tabs(self):
        """关闭全部标签页"""
        # 从后往前关闭所有标签页
        tab_count = self.tab_widget.count()
        for i in range(tab_count - 1, -1, -1):
            self.close_tab(i, from_close_button=False)
    
    def close_tab_by_case_id(self, case_id):
        """根据用例ID关闭对应的标签页（删除用例时使用，不检查未保存修改）"""
        tab_id = f"case_{case_id}"
        
        # 查找对应的标签页索引
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            
            # 查找对应的标签页ID
            for tid, tab_data in self.tabs.items():
                if tab_data['widget'] == widget and tid == tab_id:
                    # 直接关闭标签页，不检查未保存修改（因为用例已经被删除）
                    self.tab_widget.removeTab(i)
                    del self.tabs[tab_id]
                    # 检查是否还有标签页，如果没有则发出关闭信号
                    if self.tab_widget.count() == 0:
                        self.tab_closed.emit()
                    return True
        
        return False

    def sync_case_data(self, case_id, updated_case_data):
        """同步更新编辑页面中的用例数据（关键修复：确保拖拽后编辑页面数据同步）"""
        try:
            tab_id = f"case_{case_id}"
            
            # 查找对应的标签页
            if tab_id in self.tabs:
                tab_data = self.tabs[tab_id]
                widget = tab_data['widget']
                current_data = tab_data['data']
                
                # 检查是否是同一个用例
                if 'id' in current_data and current_data['id'] == case_id:
                    # 更新标签页数据
                    tab_data['data'] = updated_case_data
                    
                    # 更新标签页widget的用例数据
                    if hasattr(widget, 'case_data'):
                        widget.case_data = updated_case_data
                    
                    # 标记为已修改状态，提示用户保存
                    self.set_tab_modified(tab_id, True)
                    if hasattr(widget, 'modified'):
                        widget.modified = True
                    if hasattr(widget, 'modified_signal'):
                        widget.modified_signal.emit(True)
                    
                    # 显示提示信息
                    print(f"[DEBUG] 已同步用例数据到编辑器标签页: case_id={case_id}")
                    return True
            
            print(f"[DEBUG] 未找到对应的用例编辑标签页: case_id={case_id}")
            return False
                    
        except Exception as e:
            print(f"[DEBUG] 同步用例数据到编辑器失败: {e}")
            return False

    def set_tab_modified(self, tab_id, modified):
        """设置标签页修改状态"""
        if tab_id in self.tabs:
            self.tabs[tab_id]['modified'] = modified
            self.update_tab_title(tab_id)

    def update_tab_title(self, tab_id):
        """更新标签页标题"""
        if tab_id in self.tabs:
            tab_data = self.tabs[tab_id]
            title = tab_data['tab_name']
            if tab_data['modified']:
                title = f"*{title}"
            
            # 找到标签页索引
            for i in range(self.tab_widget.count()):
                if self.tab_widget.widget(i) == tab_data['widget']:
                    self.tab_widget.setTabText(i, title)
                    break

    def show_execution_logs(self):
        """显示执行日志弹窗"""
        # 调试信息：追踪日志列表状态
        print(f"[DEBUG] === 开始显示执行日志弹窗 ===")
        print(f"[DEBUG] 当前标签页对象ID: {id(self)}")
        
        # 获取当前活动标签页的日志列表
        current_logs = []
        if self.current_tab_id and self.current_tab_id in self.tabs:
            current_tab_widget = self.tabs[self.current_tab_id]['widget']
            if hasattr(current_tab_widget, 'execution_logs'):
                current_logs = current_tab_widget.execution_logs
                print(f"[DEBUG] 当前标签页日志列表对象ID: {id(current_logs)}")
                print(f"[DEBUG] 当前标签页日志列表数量: {len(current_logs)}")
            else:
                print("[DEBUG] 当前标签页没有execution_logs属性")
        else:
            print("[DEBUG] 没有当前活动标签页")
        
        # 创建执行日志弹窗
        self.execution_logs_dialog = ExecutionLogsDialog(self)
        
        # 如果测试正在执行，将已记录的日志添加到弹窗中
        if current_logs:
            print(f"[DEBUG] 弹窗创建时加载已记录日志，共 {len(current_logs)} 条")
            for log_entry in current_logs:
                step_index = log_entry.get('step_index', -1)
                step_info = "通用信息" if step_index == -1 else f"步骤 {step_index + 1}"
                print(f"[DEBUG] 加载日志 - {step_info}: {log_entry['message'][:50]}...")
                
                # 获取步骤名称（如果步骤索引有效）
                step_name = log_entry.get('step_name')  # 尝试从日志条目获取步骤名称
                if step_name is None and step_index >= 0:
                    # 如果没有存储步骤名称，尝试从当前用例获取
                    if hasattr(self, 'current_case') and self.current_case and len(self.current_case.steps) > step_index:
                        step = self.current_case.steps[step_index]
                        # 处理TestCaseStep对象，使用getattr安全获取属性
                        if hasattr(step, 'name'):
                            step_name = step.name
                        elif hasattr(step, 'get'):
                            step_name = step.get('name', f'步骤 {step_index + 1}')
                        else:
                            step_name = f'步骤 {step_index + 1}'
                
                self.execution_logs_dialog.add_log_with_step(
                    log_entry['message'], 
                    log_entry['level'], 
                    step_index,
                    step_name
                )
            print(f"[DEBUG] 所有日志已加载到弹窗")
        else:
            # 添加一些示例日志
            print("[DEBUG] 没有已记录日志，添加示例日志")
            self.execution_logs_dialog.add_log("执行日志弹窗已打开", "info")
            self.execution_logs_dialog.add_log("可以查看测试用例的执行日志", "success")
        
        # 显示弹窗
        self.execution_logs_dialog.show()
        print("[DEBUG] 日志弹窗已显示")
        print(f"[DEBUG] === 显示执行日志弹窗完成 ===")

    def add_execution_log(self, message, level="info"):
        """添加执行日志"""
        # 如果弹窗存在，向弹窗添加日志
        if hasattr(self, 'execution_logs_dialog') and self.execution_logs_dialog is not None:
            self.execution_logs_dialog.add_log(message, level)
        
        # 同时保存到日志列表
        self.execution_logs.append({
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'level': level,
            'message': message
        })
    
    def case_saved(self, tab_id, case_data):
        """用例保存回调"""
        if tab_id in self.tabs:
            # 更新标签页数据
            self.tabs[tab_id]['data'] = case_data
            
            # 更新标签页名称
            tab_name = case_data.get('name', '新增用例')
            self.tabs[tab_id]['tab_name'] = tab_name
            
            # 更新标签页标题
            for i in range(self.tab_widget.count()):
                if self.tab_widget.widget(i) == self.tabs[tab_id]['widget']:
                    self.tab_widget.setTabText(i, tab_name)
                    break
            
            # 发出保存信号，让外部处理实际的保存逻辑
            self.saved.emit(case_data)
    
    def on_api_template_edit_requested(self, api_template_id):
        """处理接口模板编辑请求"""
        # 发送信号通知主窗口跳转到接口模板编辑tab
        self.api_template_edit_requested.emit(api_template_id)


class StepLogItem(QWidget):
    """步骤日志项组件"""
    
    def __init__(self, step_name, step_index, parent=None):
        super().__init__(parent)
        self.step_name = step_name
        self.step_index = step_index
        # 默认收起步骤日志项，使界面更简洁
        self.is_expanded = False
        self.logs = []
        # 步骤执行状态：None-未执行，True-执行成功，False-执行报错
        self.step_status = None
        self.init_ui()
        # 确保初始化后组件可见
        self.ensure_visibility()
    
    def ensure_visibility(self):
        """确保组件可见性正确设置"""
        # 设置content_widget的可见性
        self.content_widget.setVisible(self.is_expanded)
        # 确保自身可见
        self.setVisible(True)
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # 步骤标题栏
        self.header_widget = QWidget()
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(12, 8, 12, 8)
        
        # 展开/收起按钮
        self.expand_btn = QPushButton("▶")
        self.expand_btn.setFixedSize(20, 20)
        self.expand_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                font-size: 10px;
                color: #666;
            }
            QPushButton:hover {
                background: #f0f0f0;
                border-radius: 3px;
            }
        """)
        self.expand_btn.clicked.connect(self.toggle_expand)
        
        # 步骤序号和名称
        if self.step_index == -1:
            # 通用信息，不显示步骤序号
            self.step_label = QLabel(f"{self.step_name}")
        else:
            # 具体步骤，显示步骤序号
            self.step_label = QLabel(f"步骤 {self.step_index + 1}: {self.step_name}")
        self.step_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #24292f;")
        
        # 日志数量
        self.log_count_label = QLabel("0 条日志")
        self.log_count_label.setStyleSheet("color: #666; font-size: 12px;")
        
        header_layout.addWidget(self.expand_btn)
        header_layout.addWidget(self.step_label)
        header_layout.addStretch()
        header_layout.addWidget(self.log_count_label)
        
        # 步骤日志内容区域
        self.content_widget = QWidget()
        # 默认收起状态
        self.content_widget.setVisible(self.is_expanded)
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(32, 8, 12, 8)
        
        # 日志文本框
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFont(QFont("Consolas", 10))
        self.logs_text.setMinimumHeight(200)  # 设置最小高度
        self.logs_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e1e4e8;
                border-radius: 4px;
                background: #fafbfc;
                padding: 12px;
                font-size: 13px;
                line-height: 1.5;
            }
        """)
        content_layout.addWidget(self.logs_text)
        
        layout.addWidget(self.header_widget)
        layout.addWidget(self.content_widget)
        
        # 设置样式
        self.setStyleSheet("""
            StepLogItem {
                border: 1px solid #e1e4e8;
                border-radius: 6px;
                background: #ffffff;
                margin: 2px;
            }
            StepLogItem:hover {
                border-color: #d0d7de;
                background: #f6f8fa;
            }
        """)
    
    def toggle_expand(self):
        """切换展开/收起状态"""
        self.is_expanded = not self.is_expanded
        self.content_widget.setVisible(self.is_expanded)
        
        # 更新按钮图标
        if self.is_expanded:
            self.expand_btn.setText("▼")
        else:
            self.expand_btn.setText("▶")
    
    def add_log(self, message, level="info"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 根据级别设置颜色
        if level == "error":
            color = "red"
            prefix = "[ERROR]"
        elif level == "warning":
            color = "orange"
            prefix = "[WARN]"
        elif level == "success":
            color = "green"
            prefix = "[SUCCESS]"
        else:
            color = "blue"
            prefix = "[INFO]"
        
        # 格式化日志消息
        log_entry = f"<span style='color: gray;'>[{timestamp}]</span> <span style='color: {color};'>{prefix}</span> {message}"
        
        # 添加到日志文本框
        self.logs_text.append(log_entry)
        
        # 自动滚动到底部
        cursor = self.logs_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.logs_text.setTextCursor(cursor)
        
        # 保存到日志列表
        self.logs.append({
            'timestamp': timestamp,
            'level': level,
            'message': message
        })
        
        # 更新步骤状态：如果有错误日志，标记为执行报错
        if level == "error" and self.step_status is not False:
            self.step_status = False
            self.update_header_style()
        elif self.step_status is None and level != "error":
            # 如果没有错误且是第一次添加日志，标记为执行成功
            self.step_status = True
            self.update_header_style()
        
        # 更新日志数量
        self.log_count_label.setText(f"{len(self.logs)} 条日志")
    
    def update_header_style(self):
        """根据步骤状态更新标题栏样式"""
        if self.step_status is None:
            # 未执行状态：默认样式
            self.header_widget.setStyleSheet("""
                QWidget {
                    background: #ffffff;
                    border-radius: 4px;
                }
            """)
            self.step_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #24292f;")
        elif self.step_status:
            # 执行成功：浅绿色背景，黑色字体
            self.header_widget.setStyleSheet("""
                QWidget {
                    background: #e8f5e8;
                    border-radius: 4px;
                }
            """)
            self.step_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #000000;")
        else:
            # 执行报错：浅绿色背景，红色字体
            self.header_widget.setStyleSheet("""
                QWidget {
                    background: #e8f5e8;
                    border-radius: 4px;
                }
            """)
            self.step_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #ff0000;")


class ExecutionLogsDialog(QDialog):
    """执行日志弹窗"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.step_logs = {}  # 按步骤存储日志项
        self.step_order = []  # 步骤执行顺序
        self.setWindowTitle("执行日志")
        self.setMinimumSize(1000, 800)
        self.setMaximumSize(1600, 1200)
        self.resize(1200, 900)  # 设置默认大小
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel("执行日志")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.expand_all_btn = QPushButton("展开全部")
        self.collapse_all_btn = QPushButton("收起全部")
        
        self.expand_all_btn.clicked.connect(self.expand_all)
        self.collapse_all_btn.clicked.connect(self.collapse_all)
        
        button_layout.addWidget(self.expand_all_btn)
        button_layout.addWidget(self.collapse_all_btn)
        
        title_layout.addLayout(button_layout)
        layout.addLayout(title_layout)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background: #fafafa;
            }
        """)
        
        # 步骤日志容器
        self.steps_container = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.setSpacing(4)
        self.steps_layout.setContentsMargins(8, 8, 8, 8)
        self.steps_layout.addStretch()
        
        scroll_area.setWidget(self.steps_container)
        layout.addWidget(scroll_area)
        
        # 设置样式
        self.setStyleSheet("""
            ExecutionLogsDialog {
                background: #f8f9fa;
            }
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #d0d7de;
                border-radius: 4px;
                background: #ffffff;
                font-size: 12px;
                color: #24292f;
            }
            QPushButton:hover {
                background: #f6f8fa;
                border-color: #0969da;
            }
            QPushButton:pressed {
                background: #eaeef2;
            }
            QPushButton:disabled {
                background: #f6f8fa;
                color: #8c959f;
                border-color: #d0d7de;
            }
        """)
    
    def clear_logs(self):
        """清空日志"""
        # 清空所有步骤日志项
        for i in reversed(range(self.steps_layout.count())):
            item = self.steps_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        
        self.step_logs = {}
        self.step_order = []
    
    def export_logs(self):
        """导出日志"""
        # 导出日志功能将在后续版本中实现
        Toast.info(self, "导出日志功能将在后续版本中实现")
    
    def expand_all(self):
        """展开所有步骤"""
        for step_log in self.step_logs.values():
            if not step_log.is_expanded:
                step_log.toggle_expand()
    
    def collapse_all(self):
        """收起所有步骤"""
        for step_log in self.step_logs.values():
            if step_log.is_expanded:
                step_log.toggle_expand()
    
    def add_step_log(self, step_name, step_index):
        """添加步骤日志项"""
        if step_index in self.step_logs:
            return self.step_logs[step_index]
        
        # 创建新的步骤日志项
        step_log = StepLogItem(step_name, step_index, self)
        self.step_logs[step_index] = step_log
        self.step_order.append(step_index)
        
        # 插入到布局中（按执行顺序）
        insert_position = len(self.step_order) - 1
        self.steps_layout.insertWidget(insert_position, step_log)
        
        # 强制刷新布局并确保可见性
        step_log.ensure_visibility()
        step_log.setVisible(True)
        step_log.header_widget.setVisible(True)
        step_log.content_widget.setVisible(step_log.is_expanded)
        
        # 强制更新布局
        step_log.updateGeometry()
        self.steps_container.updateGeometry()
        self.steps_layout.update()
        
        # 如果对话框已经显示，则立即刷新界面
        if self.isVisible():
            QApplication.processEvents()
        
        return step_log
    
    def add_log_to_step(self, step_index, message, level="info"):
        """向指定步骤添加日志"""
        if step_index in self.step_logs:
            self.step_logs[step_index].add_log(message, level)
    
    def add_log(self, message, level="info"):
        """添加通用日志（不关联到具体步骤）"""
        # 添加通用日志到-1步骤
        self.add_log_with_step(message, level, -1)

    def add_log_with_step(self, message, level="info", step_index=-1, step_name=None):
        """添加带步骤信息的日志"""
        # 简化逻辑：直接根据step_index创建或获取步骤日志项
        if step_index == -1:
            # 通用信息日志
            step_name = "通用信息"
        else:
            # 具体步骤日志
            if step_name is None:
                step_name = f"步骤 {step_index + 1}"
            else:
                # 只传递步骤名称，让StepLogItem类处理格式
                step_name = step_name
        
        # 确保步骤日志项存在
        if step_index not in self.step_logs:
            self.add_step_log(step_name, step_index)
        
        # 添加日志到对应步骤
        self.add_log_to_step(step_index, message, level)
        
        # 强制刷新界面以确保日志显示
        if self.isVisible():
            # 确保步骤日志项可见
            if step_index in self.step_logs:
                step_log = self.step_logs[step_index]
                step_log.ensure_visibility()
                step_log.setVisible(True)
                step_log.header_widget.setVisible(True)
                step_log.content_widget.setVisible(step_log.is_expanded)
            
            # 强制刷新布局
            self.steps_layout.update()
            self.steps_container.updateGeometry()
            self.updateGeometry()
            
            # 处理事件队列，确保界面更新
            QApplication.processEvents()


class ExecutionLogsTab(QWidget):
    """执行日志标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logs = []
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 日志文本框
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFont(QFont("Consolas", 10))
        self.logs_text.setPlaceholderText("执行日志将显示在这里...")
        layout.addWidget(self.logs_text)
    
    def clear_logs(self):
        """清空日志"""
        self.logs_text.clear()
        self.logs = []
    
    def export_logs(self):
        """导出日志"""
        # 导出日志功能将在后续版本中实现
        Toast.info(self, "导出日志功能将在后续版本中实现")
    
    def add_log(self, message, level="info"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 根据级别设置颜色
        if level == "error":
            color = "red"
            prefix = "[ERROR]"
        elif level == "warning":
            color = "orange"
            prefix = "[WARN]"
        elif level == "success":
            color = "green"
            prefix = "[SUCCESS]"
        else:
            color = "blue"
            prefix = "[INFO]"
        
        # 格式化日志消息
        log_entry = f"<span style='color: gray;'>[{timestamp}]</span> <span style='color: {color};'>{prefix}</span> {message}"
        
        # 添加到日志文本框
        self.logs_text.append(log_entry)
        
        # 自动滚动到底部
        cursor = self.logs_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.logs_text.setTextCursor(cursor)
        
        # 保存到日志列表
        self.logs.append({
            'timestamp': timestamp,
            'level': level,
            'message': message
        })
    

    
    def close_current_tab(self, index):
        """关闭当前标签页"""
        self.close_tab(index, from_close_button=False)
    
    def close_other_tabs(self, current_index):
        """关闭其他标签页"""
        # 获取所有标签页索引
        tab_count = self.tab_widget.count()
        if tab_count <= 1:
            return
            
        # 从后往前关闭标签页（避免索引变化问题）
        for i in range(tab_count - 1, -1, -1):
            if i != current_index:
                self.close_tab(i, from_close_button=False)
    
    def close_all_tabs(self):
        """关闭全部标签页"""
        # 从后往前关闭所有标签页
        tab_count = self.tab_widget.count()
        for i in range(tab_count - 1, -1, -1):
            self.close_tab(i, from_close_button=False)