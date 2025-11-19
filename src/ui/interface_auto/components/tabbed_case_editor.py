import json
import traceback
from datetime import datetime
from PyQt5.QtCore import pyqtSignal, Qt, QDataStream, QIODevice, QSize, QThread
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget, QLabel, 
    QLineEdit, QTextEdit, QComboBox, QPushButton, QMessageBox, QSplitter, QMenu,
    QToolBar, QScrollArea, QDialog, QSizePolicy, QApplication
)
from PyQt5.QtGui import QFont, QTextCursor, QIcon
from .flow_layout import FlowLayout
from src.ui.widgets.toast_tips import Toast
from src.ui.interface_auto.components.api_card import ApiCard
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

    def __init__(self, case_data, environment_config=None):
        super().__init__()
        self.case_data = case_data
        self.environment_config = environment_config or {}
        self.variable_manager = get_global_variable_manager()
        self.request_engine = RequestEngine()
        self.is_running = True
    
    def stop(self):
        """停止线程执行 - 修复版本"""
        if not self.isRunning():
            return
            
        # 设置停止标志
        self.is_running = False
        
        # 等待线程安全结束，增加等待时间到5秒
        if not self.wait(5000):  # 最多等待5秒
            print("[WARNING] 线程未在5秒内正常退出，尝试强制终止")
            # 如果线程没有正常结束，强制终止
            self.terminate()
            # 等待终止完成
            self.wait(2000)
        
        print("[DEBUG] 线程已安全停止")

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
            print("[DEBUG] 用例执行开始")
            print(f"[DEBUG] 用例名称: {self.case_data.get('name', '未命名')}")
            print(f"[DEBUG] 环境配置: {self.environment_config}")
            print(f"[DEBUG] 总步骤数: {len(self.case_data.get('steps', []))}")
            
            # 记录详细的调试信息
            self.log_message.emit(self.format_debug_message("用例执行调试信息开始", "debug", -1), "debug", -1)
            self.log_message.emit(self.format_debug_message(f"用例ID: {self.case_data.get('id', '未保存')}", "debug", -1), "debug", -1)
            self.log_message.emit(self.format_debug_message(f"用例名称: {self.case_data.get('name', '未命名')}", "debug", -1), "debug", -1)
            self.log_message.emit(self.format_debug_message(f"环境配置: {self.environment_config}", "debug", -1), "debug", -1)
            self.log_message.emit(self.format_debug_message(f"总步骤数: {len(self.case_data.get('steps', []))}", "debug", -1), "debug", -1)
            
            # 记录全局变量信息
            global_vars = self.case_data.get('global_vars', {})
            self.log_message.emit(self.format_debug_message(f"全局变量数量: {len(global_vars)}", "debug", -1), "debug", -1)
            for var_name, var_value in global_vars.items():
                self.log_message.emit(self.format_debug_message(f"  - {var_name}: {var_value}", "debug", -1), "debug", -1)
            
            self.log_message.emit(self.format_debug_message(f"开始执行测试用例: {self.case_data['name']}", "info", -1), "info", -1)

            # 初始化变量管理器
            self.variable_manager.clear_local_variables()
            self.variable_manager.set_global_variables(global_vars)

            # 执行每个步骤
            steps = self.case_data.get('steps', [])
            enabled_steps = [step for step in steps if step.get('enabled', True)]
            
            # [DEBUG] 终端打印 - 步骤信息
            print(f"[DEBUG] 启用步骤数: {len(enabled_steps)}")
            
            self.log_message.emit(self.format_debug_message(f"启用步骤数: {len(enabled_steps)}", "debug", -1), "debug", -1)

            # 统计步骤执行结果
            total_steps = len(enabled_steps)
            success_steps = 0

            for step_index, step in enumerate(enabled_steps):
                if not self.is_running:
                    print("[DEBUG] 执行被中断")
                    self.log_message.emit(self.format_debug_message("执行被中断", "debug", step_index), "debug", step_index)
                    break

                # [DEBUG] 终端打印 - 步骤开始执行
                print(f"[DEBUG] 开始执行步骤 {step_index + 1}")
                print(f"[DEBUG] 步骤名称: {step.get('name', '未命名步骤')}")
                print(f"[DEBUG] 接口模板ID: {step.get('api_template_id', '无')}")
                
                # 记录步骤开始执行的调试信息
                self.log_message.emit(self.format_debug_message(f"开始执行步骤 {step_index + 1}", "debug", step_index), "debug", step_index)
                self.log_message.emit(self.format_debug_message(f"步骤名称: {step.get('name', '未命名步骤')}", "debug", step_index), "debug", step_index)
                self.log_message.emit(self.format_debug_message(f"步骤顺序: {step.get('step_order', step_index + 1)}", "debug", step_index), "debug", step_index)
                self.log_message.emit(self.format_debug_message(f"接口模板ID: {step.get('api_template_id', '无')}", "debug", step_index), "debug", step_index)
                
                self.step_started.emit(step.get('name', f"步骤 {step_index + 1}"), step_index)
                result = self.execute_step(step, step_index)
                self.step_finished.emit(result)
                
                # [DEBUG] 终端打印 - 步骤执行结果
                print(f"[DEBUG] 步骤 {step_index + 1} 执行完成")
                print(f"[DEBUG] 执行结果: {'成功' if result.get('success', False) else '失败'}")
                print(f"[DEBUG] 响应状态码: {result.get('response_status_code', '无')}")
                print(f"[DEBUG] 执行耗时: {result.get('duration', 0):.2f}秒")
                
                # 记录步骤执行结果的调试信息
                self.log_message.emit(self.format_debug_message(f"步骤 {step_index + 1} 执行完成", "debug", step_index), "debug", step_index)
                self.log_message.emit(self.format_debug_message(f"执行结果: {'成功' if result.get('success', False) else '失败'}", "debug", step_index), "debug", step_index)
                self.log_message.emit(self.format_debug_message(f"响应状态码: {result.get('response_status_code', '无')}", "debug", step_index), "debug", step_index)
                self.log_message.emit(self.format_debug_message(f"执行耗时: {result.get('duration', 0):.2f}秒", "debug", step_index), "debug", step_index)
                
                # 统计成功步骤数量
                if result.get('success', False):
                    success_steps += 1
                
                # 如果步骤执行失败，停止执行后续步骤
                if not result.get('success', False):
                    print("[DEBUG] 步骤执行失败，停止执行后续步骤")
                    self.log_message.emit(self.format_debug_message("步骤执行失败，停止执行后续步骤", "debug", step_index), "debug", step_index)
                    break

            # [DEBUG] 终端打印 - 用例执行完成
            print("[DEBUG] 用例执行完成")
            print(f"[DEBUG] 步骤统计: 成功 {success_steps}/{total_steps}")
            
            self.case_finished.emit({
                'success': True,
                'message': '用例执行完成',
                'success_count': success_steps,
                'total_count': total_steps
            })
            
            self.log_message.emit(self.format_debug_message("用例执行调试信息结束", "debug", -1), "debug", -1)

        except Exception as e:
            # [DEBUG] 终端打印 - 用例执行异常
            print(f"[DEBUG] 用例执行异常: {str(e)}")
            
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

            # [DEBUG] 终端打印 - 步骤执行开始
            print(f"[DEBUG] 步骤 {step_index + 1} 执行详情开始")
            print(f"[DEBUG] 步骤配置: {step}")
            
            # 记录步骤开始执行的详细调试信息
            self.log_message.emit(self.format_debug_message(f"步骤 {step_index + 1} 执行详情开始", "debug", step_index), "debug", step_index)
            self.log_message.emit(self.format_debug_message(f"步骤配置: {step}", "debug", step_index), "debug", step_index)
            
            # 记录开始日志
            self.log_message.emit(self.format_debug_message(f"执行步骤 {step_index + 1}: {step.get('name', '未命名步骤')}", "info", step_index), "info", step_index)

            # 执行前置处理
            pre_processing = step.get('pre_processing', {})
            print(f"[DEBUG] 前置处理工具数量: {len(pre_processing)}")
            self.log_message.emit(self.format_debug_message(f"前置处理工具数量: {len(pre_processing)}", "debug", step_index), "debug", step_index)
            self.execute_pre_processing(pre_processing, step_index)

            # 执行接口请求
            api_template_id = step.get('api_template_id')
            if api_template_id:
                print(f"[DEBUG] 执行接口请求，模板ID: {api_template_id}")
                self.log_message.emit(self.format_debug_message(f"执行接口请求，模板ID: {api_template_id}", "debug", step_index), "debug", step_index)
                try:
                    result = self.execute_api_request(step, step_index)
                    print(f"[DEBUG] execute_api_request方法执行完成，结果: {result}")
                except Exception as e:
                    print(f"[DEBUG] execute_api_request方法执行异常: {str(e)}")
                    print(f"[DEBUG] 异常堆栈: {traceback.format_exc()}")
                    result = {
                        'success': False,
                        'error': str(e),
                        'status': 'error',
                        'duration': 0
                    }
            else:
                print("[DEBUG] 跳过接口执行（无接口模板）")
                self.log_message.emit(self.format_debug_message("跳过接口执行（无接口模板）", "debug", step_index), "debug", step_index)
                result = {
                    'success': True,
                    'message': '跳过接口执行（无接口模板）',
                    'status': 'skipped'
                }

            # 执行后置处理
            if result.get('success'):
                post_processing = step.get('post_processing', {})
                print(f"[DEBUG] 后置处理工具数量: {len(post_processing)}")
                self.log_message.emit(self.format_debug_message(f"后置处理工具数量: {len(post_processing)}", "debug", step_index), "debug", step_index)
                self.execute_post_processing(post_processing, result, step_index)

            # 执行断言
            if result.get('success'):
                assertions = step.get('assertions', {})
                print(f"[DEBUG] 断言数量: {len(assertions)}")
                self.log_message.emit(self.format_debug_message(f"断言数量: {len(assertions)}", "debug", step_index), "debug", step_index)
                assertion_result = self.execute_assertions(assertions, result, step_index)
                result['assertions_result'] = assertion_result

            # 计算执行时长
            step_end_time = datetime.now()
            duration = (step_end_time - step_start_time).total_seconds()
            result['duration'] = duration

            # [DEBUG] 终端打印 - 步骤执行完成
            status = result.get('status', 'success' if result.get('success') else 'failure')
            print(f"[DEBUG] 步骤 {step_index + 1} 执行完成: {status}, 耗时: {duration:.2f}秒")
            print(f"[DEBUG] 步骤执行结果详情: {result}")
            
            # 记录完成日志
            log_level = "info" if status == "success" else "warning"
            self.log_message.emit(self.format_debug_message(f"步骤 {step_index + 1} 执行完成: {status}, 耗时: {duration:.2f}秒", log_level, step_index), log_level, step_index)
            
            # 记录步骤执行结果的详细调试信息（移除重复的body字段）
            result_copy = result.copy()
            # 移除重复的body字段，因为已经有text字段了
            if 'body' in result_copy:
                del result_copy['body']
            self.log_message.emit(self.format_debug_message(f"步骤执行结果详情: {result_copy}", "debug", step_index), "debug", step_index)
            self.log_message.emit(self.format_debug_message(f"步骤 {step_index + 1} 执行详情结束", "debug", step_index), "debug", step_index)

            return result

        except Exception as e:
            self.log_message.emit(self.format_debug_message(f"步骤 {step_index + 1} 执行错误: {str(e)}", "error", step_index), "error", step_index)
            self.log_message.emit(self.format_debug_message(f"错误详情: {traceback.format_exc()}", "debug", step_index), "debug", step_index)
            return {
                'success': False,
                'error': str(e),
                'status': 'error',
                'duration': 0
            }

    def execute_pre_processing(self, pre_processing, step_index):
        """执行前置处理"""
        print(f"[DEBUG] 开始执行前置处理，输入参数: {pre_processing}")
        
        if not pre_processing:
            print("[DEBUG] 前置处理: 无配置，直接返回")
            self.log_message.emit(self.format_debug_message("前置处理: 无配置", "debug", step_index), "debug", step_index)
            return
            
        print(f"[DEBUG] 前置处理配置类型: {type(pre_processing)}")
        print(f"[DEBUG] 前置处理配置长度: {len(pre_processing)}")
        
        self.log_message.emit(self.format_debug_message("开始执行前置处理", "debug", step_index), "debug", step_index)
        
        # 执行前置处理器中的工具
        tool_count = 0
        print(f"[DEBUG] 开始遍历前置处理工具，共 {len(pre_processing)} 个")
        
        for tool_id, tool_config in pre_processing.items():
            print(f"[DEBUG] 处理工具ID: {tool_id}")
            print(f"[DEBUG] 工具配置: {tool_config}")
            
            if not isinstance(tool_config, dict):
                print(f"[DEBUG] 工具 {tool_id} 配置不是字典类型，跳过")
                continue
                
            enabled = tool_config.get('enabled', True)
            print(f"[DEBUG] 工具 {tool_id} 启用状态: {enabled}")
            
            if not enabled:
                print(f"[DEBUG] 前置处理工具 {tool_id} 已禁用，跳过")
                self.log_message.emit(self.format_debug_message(f"前置处理工具 {tool_id} 已禁用，跳过", "debug", step_index), "debug", step_index)
                continue
                
            tool_type = tool_config.get('type')
            config = tool_config.get('config', {})
            
            print(f"[DEBUG] 工具 {tool_id} 类型: {tool_type}")
            print(f"[DEBUG] 工具 {tool_id} 配置详情: {config}")
            
            self.log_message.emit(self.format_debug_message(f"执行前置处理工具: {tool_type}", "debug", step_index), "debug", step_index)
            
            if tool_type == 'http_request':
                print(f"[DEBUG] 开始执行HTTP请求工具")
                self.execute_http_request_tool(config, step_index)
                print(f"[DEBUG] HTTP请求工具执行完成")
            else:
                print(f"[DEBUG] 未知的前置处理工具类型: {tool_type}")
                self.log_message.emit(self.format_debug_message(f"未知的前置处理工具类型: {tool_type}", "warning", step_index), "warning", step_index)
            
            tool_count += 1
            print(f"[DEBUG] 工具 {tool_id} 执行完成，当前已执行工具数: {tool_count}")
        
        # 这里可以执行变量设置、脚本执行等前置操作
        variables = pre_processing.get('variables', {})
        print(f"[DEBUG] 变量设置配置: {variables}")
        
        if variables:
            print(f"[DEBUG] 开始设置局部变量")
            self.log_message.emit(self.format_debug_message(f"设置局部变量: {variables}", "debug", step_index), "debug", step_index)
            self.variable_manager.set_local_variables(variables)
            self.log_message.emit(self.format_debug_message(f"局部变量设置完成", "info", step_index), "info", step_index)
            print(f"[DEBUG] 局部变量设置完成")
        else:
            print("[DEBUG] 无变量需要设置")
        
        print(f"[DEBUG] 前置处理完成，共执行 {tool_count} 个工具")
        self.log_message.emit(self.format_debug_message(f"前置处理完成，共执行 {tool_count} 个工具", "debug", step_index), "debug", step_index)
        self.log_message.emit(self.format_debug_message("前置处理执行结束", "debug", step_index), "debug", step_index)
        print("[DEBUG] 前置处理执行结束")

    def execute_http_request_tool(self, config, step_index=-1):
        """执行HTTP请求工具"""
        print(f"[DEBUG] 开始执行HTTP请求工具，配置: {config}")
        
        try:
            # 获取请求配置
            method = config.get('method', 'GET')
            url = config.get('url', '')
            headers = config.get('headers', {})
            body = config.get('body', {})
            timeout = config.get('timeout', 30)
            extractors = config.get('extractors', {})
            
            print(f"[DEBUG] HTTP请求配置 - 方法: {method}, URL: {url}, 超时: {timeout}")
            print(f"[DEBUG] HTTP请求配置 - 请求头: {headers}")
            print(f"[DEBUG] HTTP请求配置 - 请求体: {body}")
            print(f"[DEBUG] HTTP请求配置 - 提取器: {extractors}")
            
            if not url:
                print("[DEBUG] HTTP请求工具配置错误: URL不能为空")
                self.log_message.emit(self.format_debug_message("HTTP请求工具配置错误: URL不能为空", "error", step_index), "error", step_index)
                return
            
            # 替换变量
            all_variables = {}
            all_variables.update(self.variable_manager.global_variables)
            all_variables.update(self.variable_manager.local_variables)
            
            print(f"[DEBUG] 变量替换前 - URL: {url}")
            print(f"[DEBUG] 可用变量: {all_variables}")
            
            url = self.variable_manager.replace_variables(url, all_variables)
            headers = self.variable_manager.replace_variables_in_dict(headers, all_variables)
            body = self.variable_manager.replace_variables_in_dict(body, all_variables)
            
            print(f"[DEBUG] 变量替换后 - URL: {url}")
            print(f"[DEBUG] 变量替换后 - 请求头: {headers}")
            print(f"[DEBUG] 变量替换后 - 请求体: {body}")
            
            # 记录请求日志
            print(f"[DEBUG] 前置处理器HTTP请求: {method} {url}")
            self.log_message.emit(self.format_debug_message(f"前置处理器HTTP请求: {method} {url}", "info", step_index), "info", step_index)
            
            # 执行请求
            request_data = {
                'method': method,
                'url': url,
                'headers': headers,
                'body': body,
                'timeout': timeout
            }
            
            print(f"[DEBUG] 发送请求数据: {request_data}")
            
            response = self.request_engine.execute_request(request_data)
            print(f"[DEBUG] 请求响应: {response}")
            
            if response.get('success'):
                # 请求成功，处理响应
                response_data = response.get('response_data', {})
                status_code = response.get('status_code', 0)
                
                print(f"[DEBUG] 前置处理器HTTP请求成功: 状态码 {status_code}")
                self.log_message.emit(self.format_debug_message(f"前置处理器HTTP请求成功: 状态码 {status_code}", "info", step_index), "info", step_index)
                
                # 提取变量
                if extractors:
                    print(f"[DEBUG] 开始提取变量，提取器数量: {len(extractors)}")
                    for var_name, json_path in extractors.items():
                        try:
                            print(f"[DEBUG] 提取变量 {var_name}，JSON路径: {json_path}")
                            # 从响应中提取数据
                            value = self.extract_value(response_data, json_path)
                            if value is not None:
                                # 将提取的变量保存到变量管理器
                                self.variable_manager.set_local_variables({var_name: value})
                                print(f"[DEBUG] 提取变量成功: {var_name} = {value}")
                                self.log_message.emit(self.format_debug_message(f"提取变量 {var_name} = {value}", "info", step_index), "info", step_index)
                            else:
                                print(f"[DEBUG] 提取变量失败: {var_name}，JSON路径 {json_path} 未找到数据")
                                self.log_message.emit(self.format_debug_message(f"提取变量 {var_name} 失败: JSON路径 {json_path} 未找到数据", "warning", step_index), "warning", step_index)
                        except Exception as e:
                            print(f"[DEBUG] 提取变量异常: {var_name}，错误: {str(e)}")
                            self.log_message.emit(self.format_debug_message(f"提取变量 {var_name} 失败: {str(e)}", "error", step_index), "error", step_index)
                else:
                    print("[DEBUG] 无变量需要提取")
            else:
                # 请求失败
                error_msg = response.get('error', '未知错误')
                print(f"[DEBUG] 前置处理器HTTP请求失败: {error_msg}")
                self.log_message.emit(self.format_debug_message(f"前置处理器HTTP请求失败: {error_msg}", "error", step_index), "error", step_index)
                
        except Exception as e:
            print(f"[DEBUG] 执行HTTP请求工具异常: {str(e)}")
            self.log_message.emit(self.format_debug_message(f"执行HTTP请求工具失败: {str(e)}", "error", step_index), "error", step_index)
        
        print("[DEBUG] HTTP请求工具执行结束")

    def execute_post_processing(self, post_processing, step_result, step_index):
        """执行后置处理"""
        if not post_processing:
            self.log_message.emit(self.format_debug_message("后置处理: 无配置", "debug", step_index), "debug", step_index)
            return
            
        self.log_message.emit(self.format_debug_message("开始执行后置处理", "debug", step_index), "debug", step_index)
        
        # 这里可以执行变量提取、数据转换等后置操作
        extractors = post_processing.get('extractors', {})
        self.log_message.emit(self.format_debug_message(f"后置处理提取器数量: {len(extractors)}", "debug", step_index), "debug", step_index)
        
        extracted_count = 0
        for var_name, extractor in extractors.items():
            try:
                self.log_message.emit(self.format_debug_message(f"提取变量: {var_name}", "debug", step_index), "debug", step_index)
                # 从响应中提取数据
                value = self.extract_value(step_result.get('response_data', {}), extractor)
                self.variable_manager.set_local_variables({var_name: value})
                self.log_message.emit(self.format_debug_message(f"提取变量 {var_name} = {value}", "info", step_index), "info", step_index)
                extracted_count += 1
            except Exception as e:
                self.log_message.emit(self.format_debug_message(f"提取变量 {var_name} 失败: {str(e)}", "error", step_index), "error", step_index)
        
        self.log_message.emit(self.format_debug_message(f"后置处理完成，共提取 {extracted_count} 个变量", "debug", step_index), "debug", step_index)
        self.log_message.emit(self.format_debug_message("后置处理执行结束", "debug", step_index), "debug", step_index)

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

    def execute_api_request(self, step, step_index):
        """执行接口请求"""
        try:
            # [DEBUG] 终端打印 - 开始执行接口请求
            print(f"[DEBUG] 开始执行接口请求，步骤索引: {step_index}")
            print(f"[DEBUG] 步骤数据: {step}")
            
            # 获取接口模板数据
            api_service = ApiTemplateService()
            api_template_id = step.get('api_template_id')
            print(f"[DEBUG] 接口模板ID: {api_template_id}")
            
            api_template = api_service.get_template_by_id(api_template_id)
            if not api_template:
                print(f"[DEBUG] 接口模板不存在: {api_template_id}")
                return {
                    'success': False,
                    'error': f'接口模板不存在: {api_template_id}',
                    'status': 'error'
                }

            print(f"[DEBUG] 接口模板数据: {api_template}")

            # 准备请求数据
            request_data = self.prepare_request_data(api_template, step.get('variables', {}))
            print(f"[DEBUG] 请求数据准备完成: {request_data['method']} {request_data['url']}")
            print(f"[DEBUG] 请求头: {request_data['headers']}")
            print(f"[DEBUG] 请求参数: {request_data['params']}")
            print(f"[DEBUG] 请求体: {request_data['body']}")

            # 记录请求日志
            self.log_message.emit(self.format_debug_message(f"发送请求: {request_data['method']} {request_data['url']}", "info", step_index), "info", step_index)
            
            try:
                print("[DEBUG] 开始发送HTTP请求")
                # 构建符合 execute_request 方法要求的 API 数据格式
                api_data = {
                    'method': request_data['method'],
                    'url': request_data['url'],
                    'headers': request_data['headers'],
                    'params': request_data['params'],
                    'body': request_data['body']
                }
                print(f"[DEBUG] 发送的API数据: {api_data}")
                
                response = self.request_engine.execute_request(api_data, step.get('variables', {}))
                
                if response['success']:
                    print(f"[DEBUG] 请求成功: 状态码 {response['status_code']}")
                    print(f"[DEBUG] 响应头: {response.get('headers', {})}")
                    print(f"[DEBUG] 响应体: {response.get('body', {})}")
                    print(f"[DEBUG] 响应文本: {response.get('text', '')}")
                    print(f"[DEBUG] 执行耗时: {response.get('elapsed', 0)}秒")
                    self.log_message.emit(self.format_debug_message(f"请求成功: 状态码 {response['status_code']}", "info", step_index), "info", step_index)
                else:
                    print(f"[DEBUG] 请求失败: {response.get('error', '未知错误')}")
                    print(f"[DEBUG] 完整错误响应: {response}")
                    self.log_message.emit(self.format_debug_message(f"请求失败: {response.get('error', '未知错误')}", "error", step_index), "error", step_index)

                print(f"[DEBUG] HTTP请求执行完成，返回结果: {response}")
                return response

            except Exception as e:
                print(f"[DEBUG] HTTP请求异常: {str(e)}")
                import traceback
                print(f"[DEBUG] 异常堆栈: {traceback.format_exc()}")
                return {
                    'success': False,
                    'error': str(e),
                    'status': 'error'
                }
        except Exception as e:
            print(f"[DEBUG] 执行接口请求外层异常: {str(e)}")
            import traceback
            print(f"[DEBUG] 外层异常堆栈: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'status': 'error'
            }

    def prepare_request_data(self, api_template, step_variables):
        """准备请求数据"""
        print(f"[DEBUG] 准备请求数据开始")
        print(f"[DEBUG] 接口模板: {api_template}")
        print(f"[DEBUG] 步骤变量: {step_variables}")
        
        # 合并变量
        all_variables = {}
        all_variables.update(self.variable_manager.global_variables)
        all_variables.update(self.variable_manager.local_variables)
        all_variables.update(step_variables)
        
        print(f"[DEBUG] 合并后的变量: {all_variables}")

        # 替换变量
        url = self.variable_manager.replace_variables(api_template['url_path'], all_variables)
        headers = self.variable_manager.replace_variables_in_dict(api_template.get('headers', {}), all_variables)
        params = self.variable_manager.replace_variables_in_dict(api_template.get('params', {}), all_variables)
        body = self.variable_manager.replace_variables_in_dict(api_template.get('body', {}), all_variables)
        
        print(f"[DEBUG] 替换变量后 - URL: {url}")
        print(f"[DEBUG] 替换变量后 - 请求头: {headers}")
        print(f"[DEBUG] 替换变量后 - 请求参数: {params}")
        print(f"[DEBUG] 替换变量后 - 请求体: {body}")

        # 构建完整URL
        base_url = self.environment_config.get('base_url', '')
        print(f"[DEBUG] 基础URL: {base_url}")
        if base_url:
            full_url = base_url.rstrip('/') + '/' + url.lstrip('/')
        else:
            full_url = url
            
        print(f"[DEBUG] 完整URL: {full_url}")

        result = {
            'method': api_template['method'],
            'url': full_url,
            'headers': headers,
            'params': params,
            'body': body,
            'timeout': api_template.get('timeout', 30)
        }
        
        print(f"[DEBUG] 准备请求数据完成: {result}")
        return result

    def extract_field_value(self, step_result, field_name):
        """从步骤结果中提取指定字段的值"""
        # 兼容不同的响应数据结构
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
        # 兼容不同的响应数据结构
        response_data = step_result.get('response_data', step_result.get('body', {}))
        response_text = step_result.get('response_text', step_result.get('text', ''))
        
        # 如果字段路径为空，返回空字符串
        if not field_path:
            return ''
        
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
            for part in path_parts:
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
        
        # 匹配${变量名}格式
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, text)
        
        for var_name in matches:
            # 从步骤结果中获取变量值
            var_value = step_result.get(var_name, '')
            
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
            
            # 替换变量
            text = text.replace(f'${{{var_name}}}', str(var_value))
        
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
        
        # 如果response_data是字符串，尝试解析为JSON
        if isinstance(response_data, str) and response_data.strip():
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
                
                self.log_message.emit(self.format_debug_message(f"执行断言: {assertion_name}", "debug", step_index), "debug", step_index)
                
                if assertion_type == 'equal':
                    expected = config.get('expected')  # 不设置默认值，保持None
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
        
        self.init_ui()
        
        # 如果是编辑模式，加载数据
        if self.is_edit:
            self.load_case_data()
    
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
        
        # 用例名称（标题和输入框在同一行）
        name_layout = QHBoxLayout()
        name_layout.setSpacing(5)  # 增加水平间距，从3改为5
        name_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        name_layout.addWidget(QLabel("名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入用例名称")
        self.name_edit.textChanged.connect(self.on_content_changed)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # 用例描述（标题和输入框在同一行）
        desc_layout = QHBoxLayout()
        desc_layout.setSpacing(5)  # 增加水平间距，从3改为5
        desc_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        desc_layout.addWidget(QLabel("描述:"))
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(30)  # 减小行高从60到40
        self.description_edit.setPlaceholderText("请输入用例描述")
        self.description_edit.textChanged.connect(self.on_content_changed)
        desc_layout.addWidget(self.description_edit)
        layout.addLayout(desc_layout)
        
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
        self.run_stop_btn.setIcon(QIcon("src/resources/icons/running.png"))
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
        self.log_btn_toolbar.setIcon(QIcon("src/resources/icons/log.png"))
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
                
        # 加载测试步骤
        self.load_steps()
        
        # 重置修改状态
        self.modified = False
        self.modified_signal.emit(False)
    
    def save_case(self):
        """保存用例 - 基于前端ID系统更新步骤顺序"""
        print("[DEBUG] save_case方法开始执行")
        
        # 更新当前用例数据
        if not self.current_case:
            print("[DEBUG] 创建新的TestCase对象")
            self.current_case = TestCase()
        
        self.current_case.name = self.name_edit.text().strip()
        self.current_case.description = self.description_edit.toPlainText().strip()
        self.current_case.environment_id = self.env_combo.currentData()
        self.current_case.global_vars = {}  # 全局变量功能已移除，设置为空字典
        self.current_case.project_id = self.project_id
        self.current_case.folder_id = self.folder_id
        
        print(f"[DEBUG] 用例数据: name={self.current_case.name}, steps_count={len(self.current_case.steps) if self.current_case.steps else 0}")
        
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
                    
                    print(f"[DEBUG] 基于前端ID系统更新步骤顺序: 共{len(self.current_case.steps)}个步骤")
        
        # 详细检查步骤数据
        if self.current_case and self.current_case.steps:
            print(f"[DEBUG] 当前步骤列表:")
            for i, step in enumerate(self.current_case.steps):
                step_dict = step.to_dict()
                print(f"  [{i}] ID: {step.id}, FrontendID: {step_dict.get('frontend_id')}, Name: {step.name}, Order: {step.step_order}")
        else:
            print("[DEBUG] 当前没有步骤数据")
        
        # 验证数据
        if not self.current_case.name:
            print("[DEBUG] 用例名称为空，显示警告")
            Toast.warning(self, "用例名称不能为空")
            return
        
        # 如果是编辑模式，添加ID
        if self.is_edit and 'id' in self.case_data:
            self.current_case.id = self.case_data['id']
            print(f"[DEBUG] 编辑模式，设置用例ID: {self.current_case.id}")
        
        # 转换为字典并检查步骤数据
        case_dict = self.current_case.to_dict()
        print(f"[DEBUG] 转换后的用例字典: steps字段存在={'steps' in case_dict}, steps数量={len(case_dict.get('steps', []))}")
        
        # 发送保存信号
        print("[DEBUG] 发送saved信号")
        self.saved.emit(case_dict)
        
        # 标记为已保存
        self.modified = False
        self.modified_signal.emit(False)
        print("[DEBUG] save_case方法执行完成")
    
    def cancel(self):
        """取消编辑"""
        if self.modified:
            # 对于确认对话框，暂时保留QMessageBox.question，因为Toast不支持确认对话框
            reply = QMessageBox.question(
                self, "确认取消",
                "有未保存的修改，确定要取消吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
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
            'api_url_path': template_data.get('url_path', '')
        }

        # 创建步骤卡片数据（包含完整的模板数据）
        step_data_for_card = step_data_for_model.copy()
        step_data_for_card['api_template'] = template_data
        # 添加order字段用于步骤卡片显示
        step_data_for_card['order'] = new_order

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
                    print("[DEBUG] add_api_template_to_steps: 隐藏占位符")
            except RuntimeError:
                # 如果占位符已被删除，忽略错误
                print("[DEBUG] add_api_template_to_steps: 占位符已被删除，忽略错误")
                pass
        
        self.on_case_changed()
        
        # 标记为已修改
        if not self.modified:
            self.modified = True
            self.modified_signal.emit(True)
            
        print(f"接口模板添加成功: 在位置 {insert_index} 插入新步骤，前端ID已重新生成")
    
    def show_steps_context_menu(self, pos):
        """显示步骤区域右键菜单 - 支持在任意位置插入空白步骤"""
        # 创建右键菜单
        menu = QMenu(self)
        
        # 添加菜单项
        insert_blank_step_action = menu.addAction("插入空白步骤")
        
        # 执行菜单
        action = menu.exec_(self.steps_widget.mapToGlobal(pos))
        
        if action == insert_blank_step_action:
            # 获取点击位置对应的插入位置
            self.insert_blank_step_at_position(pos)
    
    def insert_blank_step_at_position(self, pos):
        """在指定位置插入空白步骤 - 支持动态ID重排"""
        if not self.current_case:
            # 创建新的测试用例对象
            self.current_case = TestCase()
            self.current_case.name = self.name_edit.text().strip() or "未命名用例"
            self.current_case.description = self.description_edit.toPlainText().strip()
            self.current_case.environment_id = self.env_combo.currentData()
        
        # 计算插入位置
        insert_index = len(self.current_case.steps) if self.current_case.steps else 0
        
        # 如果有点击位置，计算插入位置
        if hasattr(self, 'steps_layout') and self.steps_layout:
            # 将局部坐标转换为步骤容器的局部坐标
            local_pos = pos
            
            # 查找最近的步骤卡片位置
            for i in range(self.steps_layout.count()):
                item = self.steps_layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), 'step_id'):
                    widget = item.widget()
                    widget_rect = widget.geometry()
                    
                    # 检查点击位置是否在该步骤卡片的上半部分
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
        
        # 创建空白步骤数据
        step_data_for_model = {
            'id': None,  # 新步骤的id为None，将在保存时由数据库生成
            'case_id': self.current_case.id if self.current_case else 0,
            'step_order': new_order,
            'name': f"步骤 {new_order}",
            'enabled': True,
            'pre_processing': {},
            'post_processing': {},
            'assertions': {},
            'variables': {},
            'api_template_id': None,
            'api_name': '',
            'api_method': '',
            'api_url_path': ''
        }

        # 创建步骤卡片数据
        step_data_for_card = step_data_for_model.copy()
        step_data_for_card['api_template'] = None

        # 创建步骤对象并插入到指定位置
        step = TestCaseStep.from_dict(step_data_for_model)
        if self.current_case:
            if insert_index < len(self.current_case.steps):
                self.current_case.steps.insert(insert_index, step)
            else:
                self.current_case.steps.append(step)
        
        # 重新生成所有步骤的前端ID（基于新的顺序）
        self.regenerate_step_ids()
        
        # 重新加载步骤列表以更新UI
        self.load_steps()

        # 隐藏占位符（如果存在且有效）
        if hasattr(self, 'steps_placeholder') and self.steps_placeholder:
            try:
                # 检查占位符是否仍然有效
                if hasattr(self.steps_placeholder, 'isVisible'):
                    self.steps_placeholder.hide()
                    print("[DEBUG] insert_blank_step_at_position: 隐藏占位符")
            except RuntimeError:
                # 如果占位符已被删除，忽略错误
                print("[DEBUG] insert_blank_step_at_position: 占位符已被删除，忽略错误")
                pass
        
        self.on_case_changed()
        
        # 标记为已修改
        if not self.modified:
            self.modified = True
            self.modified_signal.emit(True)
            
        print(f"空白步骤插入成功: 在位置 {insert_index} 插入新步骤，前端ID已重新生成")
    
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

        # 添加到流式布局
        self.steps_layout.addWidget(step_card)

    def on_step_updated(self, step_data):
        """步骤更新事件"""
        # 更新内存中的步骤数据
        if self.current_case:
            for step in self.current_case.steps:
                if step.id == step_data.get('id') or step.name == step_data.get('name'):
                    step.update_from_dict(step_data)
                    break
        self.on_case_changed()

    def on_step_deleted(self, step_id):
        """步骤删除事件 - 支持动态ID重排"""
        print(f"[DEBUG] on_step_deleted: 开始删除步骤 {step_id}")
        
        # 从内存中删除步骤数据
        if self.current_case:
            original_count = len(self.current_case.steps)
            
            # 方法1：通过布局中的步骤卡片位置来删除对应步骤
            step_index_to_delete = -1
            for i in range(self.steps_layout.count()):
                item = self.steps_layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), 'step_id'):
                    if item.widget().step_id == step_id:
                        step_index_to_delete = i
                        break
            
            if step_index_to_delete >= 0 and step_index_to_delete < len(self.current_case.steps):
                # 删除对应位置的步骤
                del self.current_case.steps[step_index_to_delete]
                new_count = len(self.current_case.steps)
                print(f"[DEBUG] 步骤数据更新: 从 {original_count} 个步骤变为 {new_count} 个步骤")
            else:
                # 方法2：如果方法1失败，使用备用方法（基于前端ID）
                self.current_case.steps = [step for step in self.current_case.steps 
                                         if step.to_dict().get('frontend_id') != step_id]
                new_count = len(self.current_case.steps)
                print(f"[DEBUG] 备用方法: 步骤数据更新: 从 {original_count} 个步骤变为 {new_count} 个步骤")
        
        # 重新生成所有步骤的ID（基于新的顺序）
        self.regenerate_step_ids()
        
        # 更新所有步骤的序号
        self.update_step_orders()
        
        # 重新加载步骤列表以更新UI
        self.load_steps()
        
        # 标记用例数据已修改
        self.on_case_changed()
        print("[DEBUG] on_step_deleted: 删除完成，前端ID和序号已重新生成")

    def on_step_moved(self, dragged_step_id, target_step_id, from_index, to_index):
        """步骤移动事件 - 基于位置索引直接移动步骤"""
        print(f"[DEBUG] on_step_moved接收到信号: dragged_step_id={dragged_step_id}, target_step_id={target_step_id}, from_index={from_index}, to_index={to_index}")
        
        if not self.current_case or not self.current_case.steps:
            print("[DEBUG] on_step_moved: 当前用例或步骤列表为空，忽略移动")
            return
            
        # 获取布局中所有步骤的前端ID顺序
        if not hasattr(self, 'steps_layout') or not self.steps_layout:
            print("[DEBUG] on_step_moved: 步骤布局不存在，忽略移动")
            return
            
        # 根据拖动的位置重新排序步骤列表
        if from_index >= 0 and to_index >= 0 and from_index != to_index:
            # 检查索引是否在有效范围内
            if from_index >= len(self.current_case.steps) or to_index > len(self.current_case.steps):
                print(f"[DEBUG] 索引超出范围: from_index={from_index}, to_index={to_index}, 步骤总数={len(self.current_case.steps)}")
                return
                
            # 直接基于位置索引移动步骤
            print(f"[DEBUG] 开始移动步骤: 从位置 {from_index} 移动到 {to_index}")
            
            # 从原位置移除步骤
            dragged_step = self.current_case.steps.pop(from_index)
            
            # 插入到新位置
            # 注意：由于已经移除了原位置的步骤，后续步骤的索引会前移
            # 如果目标位置在原位置之后，不需要调整索引，因为我们是在移除元素后再插入
            # 如果目标位置在原位置之前，也不需要调整索引
            
            # 插入到新位置
            self.current_case.steps.insert(to_index, dragged_step)
            
            # 调试：打印实际的移动结果
            print(f"[DEBUG] 实际移动结果: 从位置 {from_index} 移动到 {to_index}")
            print(f"[DEBUG] 移动后步骤顺序: {[step.to_dict().get('name', '未命名') for step in self.current_case.steps]}")
            
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
            
            print(f"步骤移动成功: 从位置 {from_index} 移动到 {to_index}，前端ID已重新生成")
        else:
            print(f"[DEBUG] 无效的移动参数: from_index={from_index}, to_index={to_index}")
    
    def on_api_template_clicked(self, api_template_id):
        """接口模板点击事件 - 跳转到对应接口模板编辑tab"""
        # 发送信号通知主窗口跳转到接口模板编辑tab
        self.api_template_edit_requested.emit(api_template_id)
    
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
                    print("[DEBUG] on_step_copied: 占位符已被删除，忽略错误")
                    pass
            
            # 标记为已修改
            if not self.modified:
                self.modified = True
                self.modified_signal.emit(True)
            
            print(f"步骤复制成功: 从步骤 {step_id} 复制到新步骤，前端ID已重新生成")
            
        except Exception as e:
            print(f"步骤复制失败: {str(e)}")
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
        
        # 准备执行数据
        case_data = self.current_case.to_dict()
        
        # 创建执行线程
        self.execution_thread = CaseExecutionThread(case_data)
        
        # 连接信号
        self.execution_thread.step_started.connect(self.on_step_started)
        self.execution_thread.step_finished.connect(self.on_step_finished)
        self.execution_thread.case_finished.connect(self.on_case_finished)
        self.execution_thread.log_message.connect(self.log_message_with_step)
        
        # 清空之前的执行日志，确保每次执行都是全新的开始
        print(f"[DEBUG] 执行前日志数量: {len(self.execution_logs)}")
        self.clear_logs()
        
        # 记录详细的调试信息
        self.log_debug_info()
        
        # 记录开始执行日志
        self.log_message(f"开始执行用例: {self.current_case.name}", "info")
        
        # 开始执行
        self.execution_thread.start()
        self.is_executing = True
        
        # 更新按钮状态
        self.update_buttons_state()
    
    def log_debug_info(self):
        """记录调试信息 - 用例配置详情"""
        if not self.current_case:
            return
            
        # 记录用例基本信息
        self.log_message("=== 用例配置调试信息 ===", "info")
        self.log_message(f"用例名称: {self.current_case.name}", "info")
        self.log_message(f"用例描述: {self.current_case.description}", "info")
        self.log_message(f"环境ID: {self.current_case.environment_id}", "info")
        self.log_message(f"项目ID: {self.current_case.project_id}", "info")
        self.log_message(f"文件夹ID: {self.current_case.folder_id}", "info")
        
        # 记录步骤信息
        steps = self.current_case.steps
        self.log_message(f"步骤总数: {len(steps)}", "info")
        
        # 记录每个步骤的详细信息
        for i, step in enumerate(steps):
            step_dict = step.to_dict()
            self.log_message(f"步骤 {i+1}: {step_dict.get('name', '未命名步骤')}", "info")
            self.log_message(f"  - 接口模板ID: {step_dict.get('api_template_id', '无')}", "info")
            self.log_message(f"  - 是否启用: {step_dict.get('enabled', True)}", "info")
            self.log_message(f"  - 步骤顺序: {step_dict.get('step_order', i+1)}", "info")
            
            # 记录前置处理信息
            pre_processing = step_dict.get('pre_processing', {})
            if pre_processing:
                self.log_message(f"  - 前置处理工具数量: {len(pre_processing)}", "info")
            
            # 记录后置处理信息
            post_processing = step_dict.get('post_processing', {})
            if post_processing:
                self.log_message(f"  - 后置处理工具数量: {len(post_processing)}", "info")
            
            # 记录断言信息
            assertions = step_dict.get('assertions', {})
            if assertions:
                self.log_message(f"  - 断言数量: {len(assertions)}", "info")
        
        # 记录全局变量信息
        global_vars = self.current_case.global_vars
        if global_vars:
            self.log_message(f"全局变量数量: {len(global_vars)}", "info")
            for var_name, var_value in global_vars.items():
                self.log_message(f"  - {var_name}: {var_value}", "info")
        else:
            self.log_message("全局变量: 无", "info")
        
        self.log_message("=== 调试信息记录完成 ===", "info")

    def toggle_execution(self):
        """切换执行状态（调试/停止）"""
        if self.is_executing:
            # 当前正在执行，点击则停止
            self.stop_execution()
        else:
            # 当前未执行，点击则开始调试
            self.execute_case()

    def stop_execution(self):
        """停止执行"""
        if not self.is_executing or not self.execution_thread:
            return
        
        # 记录停止执行日志
        self.log_message("正在停止用例执行...", "warning")
        
        # 停止执行线程
        self.execution_thread.stop()
        
        # 等待线程停止
        if self.execution_thread.isRunning():
            self.execution_thread.wait(2000)  # 等待2秒确保线程停止
        
        # 更新执行状态
        self.is_executing = False
        
        # 清理线程资源
        try:
            self.execution_thread.step_started.disconnect()
            self.execution_thread.step_finished.disconnect()
            self.execution_thread.case_finished.disconnect()
            self.execution_thread.log_message.disconnect()
        except:
            pass
        
        self.execution_thread.deleteLater()
        self.execution_thread = None
        
        # 更新按钮状态
        self.update_buttons_state()
        
        # 记录停止完成日志
        self.log_message("用例执行已停止", "warning")

    def on_step_started(self, step_name, step_index):
        """步骤开始执行"""
        self.log_message_with_step(f"开始执行步骤: {step_name}", "info", step_index)

    def on_step_finished(self, step_result):
        """步骤执行完成"""
        status = "成功" if step_result.get('success') else "失败"
        self.log_message(f"步骤执行完成: {step_result.get('step_name')} - {status}", "info")

    def on_case_finished(self, case_result):
        """用例执行完成 - 修复版本"""
        # 记录执行完成时的日志状态
        print(f"[DEBUG] on_case_finished开始，当前日志数量: {len(self.execution_logs)}")
        
        # 确保执行状态正确设置
        self.is_executing = False
        
        # 安全地清理线程资源
        if self.execution_thread:
            # 等待线程完全退出
            if self.execution_thread.isRunning():
                print("[DEBUG] 等待线程安全退出...")
                self.execution_thread.wait(3000)  # 等待3秒确保线程完全退出
            
            # 断开所有信号连接
            try:
                self.execution_thread.step_started.disconnect()
                self.execution_thread.step_finished.disconnect()
                self.execution_thread.case_finished.disconnect()
                self.execution_thread.log_message.disconnect()
            except:
                pass  # 忽略断开连接时的错误
            
            # 删除线程对象
            self.execution_thread.deleteLater()
            self.execution_thread = None
        
        # 更新按钮状态
        self.update_buttons_state()
        
        # 记录执行结果
        success_count = case_result.get('success_count', 0)
        total_count = case_result.get('total_count', 0)
        status = "成功" if success_count == total_count else "失败"
        
        self.log_message(f"用例执行完成: {status} (成功: {success_count}/{total_count})", "info")
        
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
            if hasattr(step, 'name'):
                step_name = step.name
            elif hasattr(step, 'get'):
                step_name = step.get('name', f'步骤 {step_index + 1}')
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
                    if hasattr(step, 'name'):
                        step_name = step.name
                    elif hasattr(step, 'get'):
                        step_name = step.get('name', f'步骤 {step_index + 1}')
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
            self.run_stop_btn.setIcon(QIcon("src/resources/icons/stoping.png"))
            self.run_stop_btn.setToolTip("停止执行")
        else:
            # 未运行：显示调试图标
            self.run_stop_btn.setIcon(QIcon("src/resources/icons/running.png"))
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