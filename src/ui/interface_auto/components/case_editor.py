import os
import json
import time
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
                             QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QTabWidget, QGroupBox, QFormLayout, QComboBox,
                             QHeaderView, QInputDialog, QCheckBox, QSpinBox,
                             QListWidget, QListWidgetItem, QSplitter, QToolBar,
                             QAction, QToolButton, QMenu, QApplication, QDateTimeEdit,
                             QProgressBar, QFrame, QScrollArea, QGridLayout,
                             QTableWidget, QTableWidgetItem, QListWidget, QAbstractItemView,
                             QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
                             QSplitter, QStackedWidget)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QDateTime, QMimeData, QPoint, QThread, pyqtSignal as Signal
from PyQt5.QtGui import QIcon, QFont, QColor, QDrag, QPixmap, QCursor, QTextCursor
from src.core.services.environment_service import EnvironmentService
from src.core.services.api_template_service import ApiTemplateService
from src.core.services.test_case_service import TestCaseService
from src.core.models.interface_models import TestCase, TestCaseStep
from src.ui.interface_auto.components.api_card import ApiCard
from src.utils.interface_utils.variable_manager import get_global_variable_manager
from src.utils.interface_utils.request_engine import RequestEngine


class CaseExecutionThread(QThread):
    """用例执行线程"""
    step_started = Signal(int, str)  # 步骤序号, 步骤名称
    step_finished = Signal(int, dict)  # 步骤序号, 执行结果
    case_finished = Signal(dict)  # 用例执行结果
    log_message = Signal(str)  # 日志消息

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
            self.log_message.emit(f"开始执行测试用例: {self.case_data['name']}")

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

                self.step_started.emit(step_index, step.get('name', f"步骤 {step_index + 1}"))
                result = self.execute_step(step, step_index)
                self.step_finished.emit(step_index, result)

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
            self.log_message.emit(f"执行步骤 {step_index + 1}: {step.get('name', '未命名步骤')}")

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
            self.log_message.emit(f"步骤 {step_index + 1} 执行完成: {status}, 耗时: {duration:.2f}秒")

            return result

        except Exception as e:
            self.log_message.emit(f"步骤 {step_index + 1} 执行错误: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'status': 'error',
                'duration': 0
            }

    def execute_pre_processing(self, pre_processing):
        """执行前置处理"""
        # 这里可以执行变量设置、脚本执行等前置操作
        variables = pre_processing.get('variables', {})
        if variables:
            self.variable_manager.set_local_variables(variables)
            self.log_message.emit(f"设置局部变量: {variables}")

    def execute_post_processing(self, post_processing, step_result):
        """执行后置处理"""
        # 这里可以执行变量提取、数据转换等后置操作
        extractors = post_processing.get('extractors', {})
        for var_name, extractor in extractors.items():
            try:
                # 从响应中提取数据
                value = self.extract_value(step_result.get('response_data', {}), extractor)
                self.variable_manager.set_local_variables({var_name: value})
                self.log_message.emit(f"提取变量 {var_name} = {value}")
            except Exception as e:
                self.log_message.emit(f"提取变量 {var_name} 失败: {str(e)}")

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
            self.log_message.emit(f"发送请求: {request_data['method']} {request_data['url']}")

            # 执行请求
            response = self.request_engine.execute_request(request_data)

            # 记录响应日志
            if response.get('success'):
                self.log_message.emit(f"请求成功: 状态码 {response['status_code']}")
            else:
                self.log_message.emit(f"请求失败: {response.get('error', '未知错误')}")

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
                    self.log_message.emit(
                        f"断言 {assertion_name}: 状态码 {actual} {'==' if expected == actual else '!='} {expected}")

                elif assertion_config.get('type') == 'response_contains':
                    expected = assertion_config.get('value')
                    actual = json.dumps(response_data)
                    results[assertion_name] = expected in actual
                    self.log_message.emit(f"断言 {assertion_name}: 响应包含 '{expected}' -> {expected in actual}")

                elif assertion_config.get('type') == 'json_path':
                    path = assertion_config.get('path')
                    expected = assertion_config.get('value')
                    actual = self.simple_json_path_extract(response_data, path)
                    results[assertion_name] = expected == actual
                    self.log_message.emit(
                        f"断言 {assertion_name}: {path} = {actual} {'==' if expected == actual else '!='} {expected}")

            except Exception as e:
                results[assertion_name] = False
                self.log_message.emit(f"断言 {assertion_name} 执行错误: {str(e)}")

        # 检查所有断言是否通过
        all_passed = all(results.values())
        step_result['success'] = all_passed
        step_result['status'] = 'success' if all_passed else 'failure'

        return results

    def stop(self):
        """停止执行"""
        self.is_running = False


class CaseEditor(QWidget):
    """用例编辑器组件"""

    # 信号定义
    case_saved = Signal(dict)  # 用例保存信号
    case_executed = Signal(int, dict)  # 用例执行信号（用例ID, 执行结果）
    step_added = Signal(dict)  # 步骤添加信号
    step_removed = Signal(int)  # 步骤删除信号（步骤ID）
    step_updated = Signal(dict)  # 步骤更新信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.case_service = TestCaseService()
        self.environment_service = EnvironmentService()
        self.current_case = None
        self.current_case_data = None
        self.execution_thread = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 创建分割器（基本信息 + 步骤列表 + 日志）
        splitter = QSplitter(Qt.Vertical)

        # 第一区域：用例基本信息和步骤列表
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)

        # 用例基本信息
        self.setup_case_info(top_layout)

        # 步骤列表区域
        self.setup_steps_area(top_layout)

        # 第二区域：日志输出
        self.setup_logs_area()

        splitter.addWidget(top_widget)
        splitter.addWidget(self.logs_widget)
        splitter.setSizes([600, 200])

        main_layout.addWidget(splitter)

    def setup_case_info(self, parent_layout):
        """设置用例基本信息区域"""
        info_group = QGroupBox("用例信息")
        info_layout = QVBoxLayout(info_group)

        # 基本信息表单
        form_layout = QFormLayout()

        self.case_name_edit = QLineEdit()
        self.case_name_edit.setPlaceholderText("请输入用例名称")
        self.case_name_edit.textChanged.connect(self.on_case_changed)

        self.case_desc_edit = QTextEdit()
        self.case_desc_edit.setMaximumHeight(60)
        self.case_desc_edit.setPlaceholderText("请输入用例描述")
        self.case_desc_edit.textChanged.connect(self.on_case_changed)

        self.env_combo = QComboBox()
        self.env_combo.currentIndexChanged.connect(self.on_case_changed)

        # 加载环境列表
        self.load_environments()

        form_layout.addRow("用例名称:", self.case_name_edit)
        form_layout.addRow("用例描述:", self.case_desc_edit)
        form_layout.addRow("测试环境:", self.env_combo)

        info_layout.addLayout(form_layout)

        # 全局变量编辑
        vars_layout = QHBoxLayout()
        vars_layout.addWidget(QLabel("全局变量:"))

        self.vars_edit_btn = QPushButton("编辑全局变量")
        self.vars_edit_btn.clicked.connect(self.edit_global_variables)

        vars_layout.addWidget(self.vars_edit_btn)
        vars_layout.addStretch()

        info_layout.addLayout(vars_layout)

        parent_layout.addWidget(info_group)

    def setup_steps_area(self, parent_layout):
        """设置步骤列表区域"""
        steps_group = QGroupBox("测试步骤")
        steps_layout = QVBoxLayout(steps_group)

        # 步骤操作工具栏
        steps_toolbar = QToolBar()
        steps_toolbar.setIconSize(QSize(16, 16))

        self.add_step_btn = QPushButton("添加步骤")
        self.add_step_btn.clicked.connect(self.add_empty_step)

        self.run_case_btn = QPushButton("执行用例")
        self.run_case_btn.clicked.connect(self.execute_case)
        self.run_case_btn.setStyleSheet("background-color: #4CAF50; color: white;")

        self.stop_case_btn = QPushButton("停止执行")
        self.stop_case_btn.clicked.connect(self.stop_execution)
        self.stop_case_btn.setEnabled(False)
        self.stop_case_btn.setStyleSheet("background-color: #f44336; color: white;")

        self.save_case_btn = QPushButton("保存用例")
        self.save_case_btn.clicked.connect(self.save_case)
        self.save_case_btn.setStyleSheet("background-color: #2196F3; color: white;")

        steps_toolbar.addWidget(self.add_step_btn)
        steps_toolbar.addWidget(self.run_case_btn)
        steps_toolbar.addWidget(self.stop_case_btn)
        steps_toolbar.addWidget(self.save_case_btn)

        steps_layout.addWidget(steps_toolbar)

        # 步骤列表容器（可滚动）
        self.steps_scroll = QScrollArea()
        self.steps_scroll.setWidgetResizable(True)
        self.steps_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.steps_widget = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_widget)
        self.steps_layout.setAlignment(Qt.AlignTop)

        # 初始提示
        self.steps_placeholder = QLabel("暂无测试步骤，请添加步骤或从左侧拖拽接口")
        self.steps_placeholder.setAlignment(Qt.AlignCenter)
        self.steps_placeholder.setStyleSheet("color: #999; font-style: italic; padding: 50px;")
        self.steps_layout.addWidget(self.steps_placeholder)

        self.steps_scroll.setWidget(self.steps_widget)
        steps_layout.addWidget(self.steps_scroll)

        parent_layout.addWidget(steps_group)

    def setup_logs_area(self):
        """设置日志输出区域"""
        self.logs_widget = QWidget()
        logs_layout = QVBoxLayout(self.logs_widget)

        logs_header = QHBoxLayout()
        logs_header.addWidget(QLabel("执行日志"))

        self.clear_logs_btn = QPushButton("清空日志")
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        logs_header.addWidget(self.clear_logs_btn)
        logs_header.addStretch()

        logs_layout.addLayout(logs_header)

        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFont(QFont("Consolas", 9))
        self.logs_text.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ddd;")

        logs_layout.addWidget(self.logs_text)

    def load_environments(self):
        """加载环境列表"""
        try:
            environments = self.environment_service.get_all_environments()
            self.env_combo.clear()
            self.env_combo.addItem("默认环境", 0)
            for env in environments:
                self.env_combo.addItem(env['name'], env['id'])
        except Exception as e:
            print(f"加载环境列表失败: {e}")

    def load_case(self, case_data):
        """加载用例数据"""
        self.current_case_data = case_data
        self.current_case = TestCase.from_dict(case_data)

        # 更新基本信息
        self.case_name_edit.setText(self.current_case.name)
        self.case_desc_edit.setText(self.current_case.description)

        # 设置环境
        if self.current_case.environment_id:
            index = self.env_combo.findData(self.current_case.environment_id)
            if index >= 0:
                self.env_combo.setCurrentIndex(index)

        # 加载步骤
        self.load_steps()

        # 更新按钮状态
        self.update_buttons_state()

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
            self.add_step_card(step)

    def clear_steps(self):
        """清空步骤列表"""
        # 移除所有步骤卡片
        for i in reversed(range(self.steps_layout.count())):
            item = self.steps_layout.itemAt(i)
            if item.widget() and item.widget() != self.steps_placeholder:
                item.widget().deleteLater()

        # 显示占位符
        self.steps_placeholder.show()

    def add_step_card(self, step_data):
        """添加步骤卡片"""
        step_card = ApiCard(step_data, self)
        step_card.step_updated.connect(self.on_step_updated)
        step_card.step_deleted.connect(self.on_step_deleted)
        step_card.step_moved.connect(self.on_step_moved)

        self.steps_layout.addWidget(step_card)

    def add_empty_step(self):
        """添加空步骤"""
        if not self.current_case:
            QMessageBox.warning(self, "提示", "请先创建或选择测试用例")
            return

        step_data = {
            'case_id': self.current_case.id,
            'step_order': len(self.current_case.steps),
            'name': f"步骤 {len(self.current_case.steps) + 1}",
            'enabled': True,
            'pre_processing': {},
            'post_processing': {},
            'assertions': {},
            'variables': {}
        }

        step = TestCaseStep.from_dict(step_data)
        self.current_case.add_step(step)
        self.add_step_card(step_data)

        # 隐藏占位符
        self.steps_placeholder.hide()

        self.on_case_changed()

    def add_step_from_api(self, api_data):
        """从接口模板添加步骤"""
        if not self.current_case:
            QMessageBox.warning(self, "提示", "请先创建或选择测试用例")
            return

        step_data = {
            'case_id': self.current_case.id,
            'api_template_id': api_data['id'],
            'step_order': len(self.current_case.steps),
            'name': api_data['name'],
            'enabled': True,
            'pre_processing': {},
            'post_processing': {},
            'assertions': {},
            'variables': {},
            'api_name': api_data['name'],
            'api_method': api_data['method'],
            'api_url_path': api_data['url_path']
        }

        step = TestCaseStep.from_dict(step_data)
        self.current_case.add_step(step)
        self.add_step_card(step_data)

        # 隐藏占位符
        self.steps_placeholder.hide()

        self.on_case_changed()
        self.step_added.emit(step_data)

    def on_step_updated(self, step_data):
        """步骤更新事件"""
        # 更新内存中的步骤数据
        if self.current_case:
            for i, step in enumerate(self.current_case.steps):
                if step.id == step_data.get('id') or step.step_order == step_data.get('step_order'):
                    updated_step = TestCaseStep.from_dict(step_data)
                    self.current_case.steps[i] = updated_step
                    break

        self.on_case_changed()
        self.step_updated.emit(step_data)

    def on_step_deleted(self, step_id):
        """步骤删除事件"""
        if self.current_case:
            self.current_case.remove_step(step_id)
            self.load_steps()  # 重新加载步骤

        self.on_case_changed()
        self.step_removed.emit(step_id)

        # 如果没有步骤了，显示占位符
        if not self.current_case.steps:
            self.steps_placeholder.show()

    def on_step_moved(self, from_index, to_index):
        """步骤移动事件"""
        if self.current_case:
            self.current_case.move_step(from_index, to_index)
            self.load_steps()  # 重新加载步骤

        self.on_case_changed()

    def on_case_changed(self):
        """用例数据变化事件"""
        # 这里可以设置脏标记，提示用户保存
        pass

    def save_case(self):
        """保存用例"""
        if not self.current_case:
            QMessageBox.warning(self, "提示", "没有可保存的用例")
            return

        try:
            # 更新用例基本信息
            self.current_case.name = self.case_name_edit.text().strip()
            self.current_case.description = self.case_desc_edit.toPlainText().strip()
            self.current_case.environment_id = self.env_combo.currentData()

            # 验证数据
            is_valid, error_msg = self.current_case.validate()
            if not is_valid:
                QMessageBox.warning(self, "输入错误", error_msg)
                return

            # 保存到数据库
            if self.current_case.id:
                # 更新现有用例
                case_dict = self.current_case.to_dict(for_db=True)
                self.case_service.update_case(self.current_case.id, case_dict)

                # 保存步骤
                self.save_steps()

                QMessageBox.information(self, "成功", "用例更新成功")
            else:
                # 创建新用例
                case_dict = self.current_case.to_dict(for_db=True)
                case_id = self.case_service.create_case(case_dict)
                self.current_case.id = case_id

                # 保存步骤
                self.save_steps()

                QMessageBox.information(self, "成功", "用例创建成功")

            # 发射保存信号
            self.case_saved.emit(self.current_case.to_dict())

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存用例失败: {str(e)}")

    def save_steps(self):
        """保存步骤数据"""
        if not self.current_case or not self.current_case.id:
            return

        # 先删除所有现有步骤
        existing_steps = self.case_service.get_case_steps(self.current_case.id)
        for step in existing_steps:
            self.case_service.delete_case_step(step['id'])

        # 保存新步骤
        for step in self.current_case.steps:
            step.case_id = self.current_case.id
            step_dict = step.to_dict(for_db=True)
            self.case_service.create_case_step(step_dict)

    def execute_case(self):
        """执行用例"""
        if not self.current_case:
            QMessageBox.warning(self, "提示", "请先加载测试用例")
            return

        # 清空日志
        self.clear_logs()

        # 获取环境配置
        environment_id = self.env_combo.currentData()
        environment_config = {}
        if environment_id:
            try:
                environment = self.environment_service.get_environment_by_id(environment_id)
                environment_config = environment
            except Exception as e:
                self.log_message(f"加载环境配置失败: {str(e)}")

        # 准备执行数据
        case_data = self.current_case.to_dict()

        # 创建执行线程
        self.execution_thread = CaseExecutionThread(case_data, environment_config)
        self.execution_thread.step_started.connect(self.on_step_started)
        self.execution_thread.step_finished.connect(self.on_step_finished)
        self.execution_thread.case_finished.connect(self.on_case_finished)
        self.execution_thread.log_message.connect(self.log_message)

        # 更新按钮状态
        self.run_case_btn.setEnabled(False)
        self.stop_case_btn.setEnabled(True)
        self.save_case_btn.setEnabled(False)

        # 开始执行
        self.execution_thread.start()
        self.log_message("开始执行测试用例...")

    def stop_execution(self):
        """停止执行"""
        if self.execution_thread and self.execution_thread.isRunning():
            self.execution_thread.stop()
            self.execution_thread.wait(5000)  # 等待5秒
            self.log_message("用例执行已停止")

        self.run_case_btn.setEnabled(True)
        self.stop_case_btn.setEnabled(False)
        self.save_case_btn.setEnabled(True)

    def on_step_started(self, step_index, step_name):
        """步骤开始执行事件"""
        self.log_message(f"开始执行步骤 {step_index + 1}: {step_name}")

    def on_step_finished(self, step_index, result):
        """步骤执行完成事件"""
        status = result.get('status', 'unknown')
        duration = result.get('duration', 0)

        if result.get('success'):
            self.log_message(f"步骤 {step_index + 1} 执行成功, 耗时: {duration:.2f}秒")
        else:
            error_msg = result.get('error', '未知错误')
            self.log_message(f"步骤 {step_index + 1} 执行失败: {error_msg}")

    def on_case_finished(self, result):
        """用例执行完成事件"""
        if result.get('success'):
            self.log_message("用例执行完成")
        else:
            self.log_message(f"用例执行失败: {result.get('error', '未知错误')}")

        # 更新按钮状态
        self.run_case_btn.setEnabled(True)
        self.stop_case_btn.setEnabled(False)
        self.save_case_btn.setEnabled(True)

        # 发射执行完成信号
        if self.current_case:
            self.case_executed.emit(self.current_case.id, result)

    def log_message(self, message):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"

        self.logs_text.append(log_entry)

        # 自动滚动到底部
        cursor = self.logs_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.logs_text.setTextCursor(cursor)

    def clear_logs(self):
        """清空日志"""
        self.logs_text.clear()

    def clear_editor(self):
        """清空编辑器"""
        self.current_case = None
        self.current_case_data = None

        # 清空表单
        self.case_name_edit.clear()
        self.case_desc_edit.clear()
        self.env_combo.setCurrentIndex(0)

        # 清空步骤
        self.clear_steps()

        # 清空日志
        self.clear_logs()

        # 更新按钮状态
        self.update_buttons_state()

    def update_buttons_state(self):
        """更新按钮状态"""
        has_case = self.current_case is not None
        self.add_step_btn.setEnabled(has_case)
        self.run_case_btn.setEnabled(has_case)
        self.save_case_btn.setEnabled(has_case)

    def edit_global_variables(self):
        """编辑全局变量"""
        from src.ui.interface_auto.components.variable_editor import VariableManagerDialog
        dialog = VariableManagerDialog(self)
        dialog.exec_()

    def get_case_data(self):
        """获取用例数据"""
        if self.current_case:
            return self.current_case.to_dict()
        return None

    def set_case_data(self, case_data):
        """设置用例数据"""
        self.load_case(case_data)


# 使用示例
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 创建测试用例数据
    test_case_data = {
        'id': 1,
        'name': '示例测试用例',
        'description': '这是一个示例测试用例',
        'project_id': 1,
        'environment_id': 1,
        'global_vars': {
            'base_url': 'https://api.example.com',
            'username': 'testuser'
        },
        'steps': [
            {
                'id': 1,
                'step_order': 0,
                'name': '用户登录',
                'api_template_id': 1,
                'enabled': True,
                'pre_processing': {
                    'variables': {
                        'password': 'testpass123'
                    }
                },
                'assertions': {
                    'status_code': {
                        'type': 'status_code',
                        'value': 200
                    }
                }
            }
        ]
    }

    editor = CaseEditor()
    editor.set_case_data(test_case_data)
    editor.show()

    sys.exit(app.exec_())