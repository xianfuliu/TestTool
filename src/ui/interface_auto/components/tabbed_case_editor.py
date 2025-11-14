import json
from datetime import datetime
from PyQt5.QtCore import pyqtSignal, Qt, QDataStream, QIODevice, QSize, QThread
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget, QLabel, 
    QLineEdit, QTextEdit, QComboBox, QPushButton, QMessageBox, QSplitter, QMenu,
    QToolBar, QScrollArea, QDialog, QSizePolicy
)
from PyQt5.QtGui import QFont, QTextCursor
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
    step_started = pyqtSignal(str)  # 步骤名称
    step_finished = pyqtSignal(dict)  # 执行结果
    case_finished = pyqtSignal(dict)  # 用例执行结果
    log_message = pyqtSignal(str, str)  # 日志消息, 级别

    def __init__(self, case_data, environment_config=None):
        super().__init__()
        self.case_data = case_data
        self.environment_config = environment_config or {}
        self.variable_manager = get_global_variable_manager()
        self.request_engine = RequestEngine()
        self.is_running = True

    def run(self):
        """执行测试用例"""
        try:
            self.log_message.emit(f"开始执行测试用例: {self.case_data['name']}", "info")

            # 初始化变量管理器
            self.variable_manager.clear_local_variables()
            global_vars = self.case_data.get('global_vars', {})
            self.variable_manager.set_global_variables(global_vars)

            # 执行每个步骤
            steps = self.case_data.get('steps', [])
            enabled_steps = [step for step in steps if step.get('enabled', True)]

            for step_index, step in enumerate(enabled_steps):
                if not self.is_running:
                    break

                self.step_started.emit(step.get('name', f"步骤 {step_index + 1}"))
                result = self.execute_step(step, step_index)
                self.step_finished.emit(result)

            self.case_finished.emit({
                'success': True,
                'message': '用例执行完成'
            })

        except Exception as e:
            self.case_finished.emit({
                'success': False,
                'error': str(e)
            })

    def execute_step(self, step, step_index):
        """执行单个步骤"""
        try:
            step_start_time = datetime.now()

            # 记录开始日志
            self.log_message.emit(f"执行步骤 {step_index + 1}: {step.get('name', '未命名步骤')}", "info")

            # 执行前置处理
            self.execute_pre_processing(step.get('pre_processing', {}))

            # 执行接口请求
            api_template_id = step.get('api_template_id')
            if api_template_id:
                result = self.execute_api_request(step, api_template_id)
            else:
                result = {
                    'success': True,
                    'message': '跳过接口执行（无接口模板）',
                    'status': 'skipped'
                }

            # 执行后置处理
            if result.get('success'):
                self.execute_post_processing(step.get('post_processing', {}), result)

            # 执行断言
            if result.get('success'):
                assertion_result = self.execute_assertions(step.get('assertions', {}), result)
                result['assertions_result'] = assertion_result

            # 计算执行时长
            step_end_time = datetime.now()
            duration = (step_end_time - step_start_time).total_seconds()
            result['duration'] = duration

            # 记录完成日志
            status = result.get('status', 'success' if result.get('success') else 'failure')
            log_level = "info" if status == "success" else "warning"
            self.log_message.emit(f"步骤 {step_index + 1} 执行完成: {status}, 耗时: {duration:.2f}秒", log_level)

            return result

        except Exception as e:
            self.log_message.emit(f"步骤 {step_index + 1} 执行错误: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e),
                'status': 'error',
                'duration': 0
            }

    def execute_pre_processing(self, pre_processing):
        """执行前置处理"""
        # 执行前置处理器中的工具
        for tool_id, tool_config in pre_processing.items():
            if not isinstance(tool_config, dict):
                continue
                
            if not tool_config.get('enabled', True):
                continue
                
            tool_type = tool_config.get('type')
            config = tool_config.get('config', {})
            
            if tool_type == 'http_request':
                self.execute_http_request_tool(config)
            else:
                self.log_message.emit(f"未知的前置处理工具类型: {tool_type}", "warning")
        
        # 这里可以执行变量设置、脚本执行等前置操作
        variables = pre_processing.get('variables', {})
        if variables:
            self.variable_manager.set_local_variables(variables)
            self.log_message.emit(f"设置局部变量: {variables}", "info")

    def execute_http_request_tool(self, config):
        """执行HTTP请求工具"""
        try:
            # 获取请求配置
            method = config.get('method', 'GET')
            url = config.get('url', '')
            headers = config.get('headers', {})
            body = config.get('body', {})
            timeout = config.get('timeout', 30)
            extractors = config.get('extractors', {})
            
            if not url:
                self.log_message.emit("HTTP请求工具配置错误: URL不能为空", "error")
                return
            
            # 替换变量
            all_variables = {}
            all_variables.update(self.variable_manager.global_variables)
            all_variables.update(self.variable_manager.local_variables)
            
            url = self.variable_manager.replace_variables(url, all_variables)
            headers = self.variable_manager.replace_variables_in_dict(headers, all_variables)
            body = self.variable_manager.replace_variables_in_dict(body, all_variables)
            
            # 记录请求日志
            self.log_message.emit(f"前置处理器HTTP请求: {method} {url}", "info")
            
            # 执行请求
            request_data = {
                'method': method,
                'url': url,
                'headers': headers,
                'body': body,
                'timeout': timeout
            }
            
            response = self.request_engine.execute_request(request_data)
            
            if response.get('success'):
                # 请求成功，处理响应
                response_data = response.get('response_data', {})
                status_code = response.get('status_code', 0)
                
                self.log_message.emit(f"前置处理器HTTP请求成功: 状态码 {status_code}", "info")
                
                # 提取变量
                if extractors:
                    for var_name, json_path in extractors.items():
                        try:
                            # 从响应中提取数据
                            value = self.extract_value(response_data, json_path)
                            if value is not None:
                                # 将提取的变量保存到变量管理器
                                self.variable_manager.set_local_variables({var_name: value})
                                self.log_message.emit(f"提取变量 {var_name} = {value}", "info")
                            else:
                                self.log_message.emit(f"提取变量 {var_name} 失败: JSON路径 {json_path} 未找到数据", "warning")
                        except Exception as e:
                            self.log_message.emit(f"提取变量 {var_name} 失败: {str(e)}", "error")
            else:
                # 请求失败
                error_msg = response.get('error', '未知错误')
                self.log_message.emit(f"前置处理器HTTP请求失败: {error_msg}", "error")
                
        except Exception as e:
            self.log_message.emit(f"执行HTTP请求工具失败: {str(e)}", "error")

    def execute_post_processing(self, post_processing, step_result):
        """执行后置处理"""
        # 这里可以执行变量提取、数据转换等后置操作
        extractors = post_processing.get('extractors', {})
        for var_name, extractor in extractors.items():
            try:
                # 从响应中提取数据
                value = self.extract_value(step_result.get('response_data', {}), extractor)
                self.variable_manager.set_local_variables({var_name: value})
                self.log_message.emit(f"提取变量 {var_name} = {value}", "info")
            except Exception as e:
                self.log_message.emit(f"提取变量 {var_name} 失败: {str(e)}", "error")

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

    def execute_api_request(self, step, api_template_id):
        """执行接口请求"""
        try:
            # 获取接口模板数据
            api_service = ApiTemplateService()
            api_template = api_service.get_template_by_id(api_template_id)
            if not api_template:
                return {
                    'success': False,
                    'error': f'接口模板不存在: {api_template_id}',
                    'status': 'error'
                }

            # 准备请求数据
            request_data = self.prepare_request_data(api_template, step.get('variables', {}))

            # 记录请求日志
            self.log_message.emit(f"发送请求: {request_data['method']} {request_data['url']}", "info")

            # 执行请求
            response = self.request_engine.execute_request(request_data)

            # 记录响应日志
            if response.get('success'):
                self.log_message.emit(f"请求成功: 状态码 {response['status_code']}", "info")
            else:
                self.log_message.emit(f"请求失败: {response.get('error', '未知错误')}", "error")

            return response

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status': 'error'
            }

    def prepare_request_data(self, api_template, step_variables):
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

        return {
            'method': api_template['method'],
            'url': full_url,
            'headers': headers,
            'params': params,
            'body': body,
            'timeout': api_template.get('timeout', 30)
        }

    def execute_assertions(self, assertions, step_result):
        """执行断言"""
        results = {}
        response_data = step_result.get('response_data', {})

        for assertion_name, assertion_config in assertions.items():
            try:
                if assertion_config.get('type') == 'status_code':
                    expected = assertion_config.get('value')
                    actual = step_result.get('status_code')
                    results[assertion_name] = expected == actual
                    log_level = "info" if results[assertion_name] else "warning"
                    self.log_message.emit(
                        f"断言 {assertion_name}: 状态码 {actual} {'==' if expected == actual else '!='} {expected}", log_level)

                elif assertion_config.get('type') == 'response_contains':
                    expected = assertion_config.get('value')
                    actual = json.dumps(response_data)
                    results[assertion_name] = expected in actual
                    log_level = "info" if results[assertion_name] else "warning"
                    self.log_message.emit(f"断言 {assertion_name}: 响应包含 '{expected}' -> {expected in actual}", log_level)

                elif assertion_config.get('type') == 'json_path':
                    path = assertion_config.get('path')
                    expected = assertion_config.get('value')
                    actual = self.simple_json_path_extract(response_data, path)
                    results[assertion_name] = expected == actual
                    log_level = "info" if results[assertion_name] else "warning"
                    self.log_message.emit(
                        f"断言 {assertion_name}: {path} = {actual} {'==' if expected == actual else '!='} {expected}", log_level)

            except Exception as e:
                results[assertion_name] = False
                self.log_message.emit(f"断言 {assertion_name} 执行错误: {str(e)}", "error")

        # 检查所有断言是否通过
        all_passed = all(results.values())
        step_result['success'] = all_passed
        step_result['status'] = 'success' if all_passed else 'failure'

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
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_case)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel)
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
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
        self.description_edit.setMaximumHeight(60)
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
        layout.addLayout(env_layout)
    
    def setup_steps_tab(self, parent):
        """设置测试步骤区域"""
        layout = QVBoxLayout(parent)
        layout.setSpacing(5)  # 增加布局间距，从3改为5
        layout.setContentsMargins(5, 5, 5, 5)  # 设置边距为5，增加外层边距
        
        # 步骤操作工具栏
        steps_toolbar = QToolBar()
        steps_toolbar.setIconSize(QSize(16, 16))
        steps_toolbar.setStyleSheet("QToolBar { spacing: 5px; }")  # 增加工具栏间距，从2px改为5px

        # 查询变量按钮（绿色）
        self.query_vars_btn = QPushButton("查询变量")
        self.query_vars_btn.clicked.connect(self.edit_global_variables)
        self.query_vars_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 15px; border-radius: 4px; font-weight: bold;")



        self.run_case_btn = QPushButton("调试")
        self.run_case_btn.clicked.connect(self.execute_case)
        self.run_case_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px 15px; border-radius: 4px;")

        self.stop_case_btn = QPushButton("停止")
        self.stop_case_btn.clicked.connect(self.stop_execution)
        self.stop_case_btn.setEnabled(False)
        self.stop_case_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px 15px; border-radius: 4px;")

        # 添加日志按钮到工具栏
        self.log_btn_toolbar = QPushButton("日志")
        self.log_btn_toolbar.clicked.connect(self.show_execution_logs)
        self.log_btn_toolbar.setStyleSheet("padding: 8px 15px; border-radius: 4px;")

        # 将查询变量按钮放在前面，增加间距
        steps_toolbar.addWidget(self.query_vars_btn)
        steps_toolbar.addSeparator()  # 添加分隔符
        steps_toolbar.addWidget(self.run_case_btn)
        steps_toolbar.addWidget(self.stop_case_btn)
        steps_toolbar.addSeparator()  # 添加分隔符
        steps_toolbar.addWidget(self.log_btn_toolbar)

        layout.addWidget(steps_toolbar)

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

        # 初始提示
        self.steps_placeholder = QLabel("暂无测试步骤，请添加步骤或从左侧拖拽接口")
        self.steps_placeholder.setAlignment(Qt.AlignCenter)
        self.steps_placeholder.setStyleSheet("color: #999; font-style: italic; padding: 30px;")  # 减少内边距，从50px改为30px
        self.steps_layout.addWidget(self.steps_placeholder)

        self.steps_scroll.setWidget(self.steps_widget)
        layout.addWidget(self.steps_scroll)

        # 启用拖拽功能 - 设置到步骤容器上，而不是滚动区域
        self.steps_widget.setAcceptDrops(True)
        self.steps_widget.dragEnterEvent = self.drag_enter_event
        self.steps_widget.dragMoveEvent = self.drag_move_event
        self.steps_widget.dropEvent = self.drop_event
    
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
        """保存用例"""
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
        """拖拽放置事件"""
        mime_data = event.mimeData()
        
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
                            # 添加接口模板到测试步骤
                            self.add_api_template_to_steps(template_data)
                            event.acceptProposedAction()
                            return
            except Exception as e:
                print(f"解析JSON格式拖拽数据失败: {e}")
        
        # 然后尝试解析QAbstractItemModel格式的数据
        elif mime_data.hasFormat("application/x-qabstractitemmodeldatalist"):
            item_data = self.parse_drag_data(mime_data)
            
            if item_data and item_data.get('type') == 'template':
                # 添加接口模板到测试步骤
                self.add_api_template_to_steps(item_data['data'])
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
                            # 添加接口模板到测试步骤
                            self.add_api_template_to_steps(template_data)
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
    
    def add_api_template_to_steps(self, template_data):
        """添加接口模板到测试步骤"""
        if not self.current_case:
            # 创建新的测试用例对象
            self.current_case = TestCase()
            self.current_case.name = self.name_edit.text().strip() or "未命名用例"
            self.current_case.description = self.description_edit.toPlainText().strip()
            self.current_case.environment_id = self.env_combo.currentData()

        # 计算新步骤的序号（基于当前最大序号+1）
        max_order = 0
        if self.current_case and self.current_case.steps:
            max_order = max(step.step_order for step in self.current_case.steps)
        
        # 创建步骤数据（只包含TestCaseStep支持的字段）
        step_data_for_model = {
            'id': None,  # 新步骤的id为None，将在保存时由数据库生成
            'case_id': self.current_case.id if self.current_case else 0,
            'step_order': max_order + 1,
            'name': template_data.get('name', f"步骤 {max_order + 1}"),
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

        step = TestCaseStep.from_dict(step_data_for_model)
        if self.current_case:
            self.current_case.add_step(step)
        self.add_step_card(step_data_for_card)

        # 更新所有步骤的序号显示
        self.update_step_orders()

        # 隐藏占位符
        self.steps_placeholder.hide()
        self.on_case_changed()
        
        # 标记为已修改
        if not self.modified:
            self.modified = True
            self.modified_signal.emit(True)
    
    def add_test_step(self):
        """添加测试步骤"""
        Toast.info(self, "添加测试步骤功能将在后续版本中实现")



    def add_step_card(self, step_data):
        """添加步骤卡片"""
        # 使用新的InterfaceStepCard组件
        step_card = InterfaceStepCard(step_data, self)
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
        """步骤删除事件"""
        # 从UI中移除步骤卡片
        for i in reversed(range(self.steps_layout.count())):
            item = self.steps_layout.itemAt(i)
            if item.widget() and hasattr(item.widget(), 'step_id') and item.widget().step_id == step_id:
                item.widget().deleteLater()
                break
        
        # 从内存中删除步骤数据
        if self.current_case:
            self.current_case.steps = [step for step in self.current_case.steps 
                                     if step.id != step_id]
        
        # 如果没有步骤了，显示占位符
        if not self.current_case or not self.current_case.steps:
            self.steps_placeholder.show()
        
        self.on_case_changed()

    def on_step_moved(self, from_index, to_index):
        """步骤移动事件"""
        if self.current_case and 0 <= from_index < len(self.current_case.steps) and 0 <= to_index < len(self.current_case.steps):
            step = self.current_case.steps.pop(from_index)
            self.current_case.steps.insert(to_index, step)
            
            # 重新加载步骤列表以更新流式布局
            self.load_steps()
            
            self.on_case_changed()
    
    def on_api_template_clicked(self, api_template_id):
        """接口模板点击事件 - 跳转到对应接口模板编辑tab"""
        # 发送信号通知主窗口跳转到接口模板编辑tab
        self.api_template_edit_requested.emit(api_template_id)
    
    def on_step_copied(self, step_id, copied_step_data):
        """步骤复制事件"""
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
                if step.id == step_id or step.name == copied_step_data.get('name', '').replace('(副本)', ''):
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
            
            # 更新所有步骤的序号
            self.update_step_orders()
            
            # 重新加载步骤列表
            self.load_steps()
            
            # 隐藏占位符
            self.steps_placeholder.hide()
            
            # 标记为已修改
            if not self.modified:
                self.modified = True
                self.modified_signal.emit(True)
            
            print(f"步骤复制成功: 从步骤 {step_id} 复制到新步骤 {new_step.id}")
            
        except Exception as e:
            print(f"步骤复制失败: {str(e)}")
            Toast.error(self, f"步骤复制失败: {str(e)}")
    
    def update_step_orders(self):
        """更新所有步骤的序号"""
        if not self.current_case or not self.current_case.steps:
            return
            
        # 更新步骤数据中的序号
        for i, step in enumerate(self.current_case.steps, 1):
            step.step_order = i
            
        # 更新UI中步骤卡片的序号显示
        # 需要找到每个步骤对应的卡片，并更新其序号
        for i, step in enumerate(self.current_case.steps, 1):
            # 在布局中找到对应的步骤卡片
            for j in range(self.steps_layout.count()):
                item = self.steps_layout.itemAt(j)
                if item and item.widget():
                    widget = item.widget()
                    # 检查这个卡片是否对应当前的步骤
                    if hasattr(widget, 'step_data') and widget.step_data.get('id') == step.id:
                        if hasattr(widget, 'update_step_order'):
                            widget.update_step_order(i)
                        break

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
        
        if self.is_executing:
            Toast.warning(self, "警告", "用例正在执行中")
            return
        
        # 准备执行数据
        case_data = self.current_case.to_dict()
        
        # 创建执行线程
        self.execution_thread = CaseExecutionThread(case_data)
        
        # 连接信号
        self.execution_thread.step_started.connect(self.on_step_started)
        self.execution_thread.step_finished.connect(self.on_step_finished)
        self.execution_thread.case_finished.connect(self.on_case_finished)
        self.execution_thread.log_message.connect(self.log_message)
        
        # 开始执行
        self.execution_thread.start()
        self.is_executing = True
        
        # 更新按钮状态
        self.update_buttons_state()
        
        # 清空日志
        self.clear_logs()
        
        # 记录开始执行日志
        self.log_message(f"开始执行用例: {self.current_case.name}", "info")

    def stop_execution(self):
        """停止执行"""
        if not self.is_executing or not self.execution_thread:
            return
        
        # 停止执行线程
        self.execution_thread.stop()
        self.is_executing = False
        
        # 更新按钮状态
        self.update_buttons_state()
        
        # 记录停止执行日志
        self.log_message("用例执行已停止", "warning")

    def on_step_started(self, step_name):
        """步骤开始执行"""
        self.log_message(f"开始执行步骤: {step_name}", "info")

    def on_step_finished(self, step_result):
        """步骤执行完成"""
        status = "成功" if step_result.get('success') else "失败"
        self.log_message(f"步骤执行完成: {step_result.get('step_name')} - {status}", "info")

    def on_case_finished(self, case_result):
        """用例执行完成"""
        self.is_executing = False
        self.execution_thread = None
        
        # 更新按钮状态
        self.update_buttons_state()
        
        # 记录执行结果
        success_count = case_result.get('success_count', 0)
        total_count = case_result.get('total_count', 0)
        status = "成功" if success_count == total_count else "失败"
        
        self.log_message(f"用例执行完成: {status} (成功: {success_count}/{total_count})", "info")

    def log_message(self, message, level="info"):
        """记录日志消息"""
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
            'message': message
        })

    def clear_logs(self):
        """清空日志"""
        # 只清空执行日志列表，不操作日志文本控件
        self.execution_logs = []

    def clear_steps(self):
        """清空步骤列表"""
        # 移除所有步骤卡片
        for i in reversed(range(self.steps_layout.count())):
            item = self.steps_layout.itemAt(i)
            if item.widget() and item.widget() != self.steps_placeholder:
                item.widget().deleteLater()

        # 显示占位符
        self.steps_placeholder.show()

    def load_steps(self):
        """加载步骤列表"""
        # 清空现有步骤
        self.clear_steps()

        if not self.current_case or not self.current_case.steps:
            return

        # 隐藏占位符
        self.steps_placeholder.hide()

        # 添加步骤卡片
        for step in self.current_case.steps:
            self.add_step_card(step.to_dict())

    def update_buttons_state(self):
        """更新按钮状态"""
        # 根据用例状态更新按钮可用性
        has_steps = self.current_case and len(self.current_case.steps) > 0
        
        # 执行按钮状态
        self.run_case_btn.setEnabled(has_steps and not self.is_executing)
        self.stop_case_btn.setEnabled(self.is_executing)
        self.save_btn.setEnabled(not self.is_executing)
        
        # 根据执行状态设置按钮样式
        if self.is_executing:
            self.run_case_btn.setStyleSheet("background-color: #9E9E9E; color: white;")
            self.stop_case_btn.setStyleSheet("background-color: #f44336; color: white;")
        else:
            self.run_case_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            self.stop_case_btn.setStyleSheet("background-color: #9E9E9E; color: white;")
        
        # 保存按钮始终可用（除非正在执行）
        self.save_btn.setStyleSheet("background-color: #2196F3; color: white;")

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
        # 创建执行日志弹窗
        self.execution_logs_dialog = ExecutionLogsDialog(self)
        
        # 添加一些示例日志
        self.execution_logs_dialog.add_log("执行日志弹窗已打开", "info")
        self.execution_logs_dialog.add_log("可以查看测试用例的执行日志", "success")
        
        # 显示弹窗
        self.execution_logs_dialog.show()

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


class ExecutionLogsDialog(QDialog):
    """执行日志弹窗"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logs = []
        self.setWindowTitle("执行日志")
        self.setMinimumSize(800, 600)
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 日志工具栏
        toolbar_layout = QHBoxLayout()
        
        self.clear_logs_btn = QPushButton("清空日志")
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        
        self.export_logs_btn = QPushButton("导出日志")
        self.export_logs_btn.clicked.connect(self.export_logs)
        
        toolbar_layout.addWidget(self.clear_logs_btn)
        toolbar_layout.addWidget(self.export_logs_btn)
        toolbar_layout.addStretch()
        
        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        toolbar_layout.addWidget(self.close_btn)
        
        layout.addLayout(toolbar_layout)
        
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
        
        # 日志工具栏
        toolbar_layout = QHBoxLayout()
        
        self.clear_logs_btn = QPushButton("清空日志")
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        
        self.export_logs_btn = QPushButton("导出日志")
        self.export_logs_btn.clicked.connect(self.export_logs)
        
        toolbar_layout.addWidget(self.clear_logs_btn)
        toolbar_layout.addWidget(self.export_logs_btn)
        toolbar_layout.addStretch()
        
        layout.addLayout(toolbar_layout)
        
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