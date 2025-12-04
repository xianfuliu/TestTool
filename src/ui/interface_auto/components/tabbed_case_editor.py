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
from src.utils.interface_utils.test_case_executor import TestCaseExecutor


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
            
        # 将大写的日志等级转换为小写（TestCaseExecutor传递的是大写）
        original_level = level  # 保存原始级别
        level = level.lower()
            
        # 根据日志级别添加颜色标记和HTML颜色标签
        level_markers = {
            "debug": "🔍",
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }
        
        # 根据日志级别设置颜色
        level_colors = {
            "debug": "<font color='gray'>",
            "info": "<font color='black'>",
            "warning": "<font color='orange'>",
            "error": "<font color='red'>",
            "success": "<font color='green'>"
        }
        
        marker = level_markers.get(level, "ℹ️")
        color = level_colors.get(level, "<font color='blue'>")
        
        # 格式化消息内容，添加颜色标签和原始级别信息
        # 在消息末尾添加原始级别信息，供后续解析使用
        formatted_message = f"{color}{prefix} {marker} {message}</font>"
        
        return formatted_message

    def run(self):
        """执行测试用例"""
        try:
            # 创建测试用例执行器
            executor = TestCaseExecutor(
                project_id=self.project_id,
                environment_config=self.environment_config
            )
            
            # 设置执行来源为调试模式
            executor.set_execution_source('debug')
            
            # 设置日志回调函数，确保日志格式与原有系统一致
            def log_callback(message, level, step_index):
                # 使用原有的日志格式化方法
                formatted_message = self.format_debug_message(message, level, step_index)
                # 确保step_index为有效值，None转换为-1（通用信息）
                if step_index is None:
                    step_index = -1
                # 同时传递格式化后的消息和原始级别信息
                self.log_message.emit(formatted_message, level, step_index)
            
            executor.set_log_callback(log_callback)
            
            # 设置步骤开始回调函数，确保信号传递与原有系统一致
            def step_started_callback(step_name, step_index):
                # 发射步骤开始信号
                self.step_started.emit(step_name, step_index)
            
            executor.set_step_started_callback(step_started_callback)
            
            # 设置步骤完成回调函数，确保信号传递与原有系统一致
            def step_finished_callback(step_result):
                # 发射步骤完成信号
                self.step_finished.emit(step_result)
            
            executor.set_step_finished_callback(step_finished_callback)
            
            # 执行测试用例
            result = executor.execute_case(self.case_data, stop_on_failure=True)
            
            # 根据执行结果发送相应的信号
            if result.get('success'):
                self.case_finished.emit({
                    'success': True,
                    'message': result.get('message', '用例执行完成'),
                    'success_count': result.get('success_count', 0),
                    'total_count': result.get('total_count', 0)
                })
            else:
                self.case_finished.emit({
                    'success': False,
                    'error': result.get('error', '用例执行失败'),
                    'success_count': result.get('success_count', 0),
                    'total_count': result.get('total_count', 0)
                })

        except Exception as e:
            # 记录用例执行异常信息
            self.log_message.emit(self.format_debug_message(f"用例执行异常: {str(e)}", "error", -1), "error", -1)
            self.case_finished.emit({
                'success': False,
                'error': str(e),
                'success_count': 0,
                'total_count': 0
            })

    
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
        # 修复：is_edit不仅基于case_data是否为空，还要基于case_data中是否有id字段
        self.is_edit = bool(case_data) and ('id' in case_data and case_data['id'])
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
            
        # 遍历所有步骤卡片，同步所有配置信息
        for i in range(self.steps_layout.count()):
            item = self.steps_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # 检查是否是步骤卡片（有step_id和step_data属性）
                if hasattr(widget, 'step_id') and hasattr(widget, 'step_data'):
                    # 获取步骤卡片的完整数据
                    step_data = widget.step_data
                    
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
    
    def sync_step_data_to_temp_case(self, case_data):
        """同步前端UI步骤数据到临时用例数据，但不修改current_case对象"""
        if not case_data or not hasattr(self, 'steps_layout'):
            return
            
        # 遍历所有步骤卡片，同步所有配置信息到临时用例数据
        for i in range(self.steps_layout.count()):
            item = self.steps_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # 检查是否是步骤卡片（有step_id和step_data属性）
                if hasattr(widget, 'step_id') and hasattr(widget, 'step_data'):
                    # 获取步骤卡片的完整数据
                    step_data = widget.step_data
                    
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
        
        # 验证测试用例名称是否重复
        from src.core.services.test_case_service import TestCaseService
        case_service = TestCaseService()
        
        # 检查名称是否重复
        exclude_id = None
        
        if self.is_edit:
            # 优先从self.case_data获取ID
            if 'id' in self.case_data and self.case_data['id']:
                exclude_id = self.case_data['id']
            # 如果self.case_data中没有ID，尝试从current_case获取
            elif hasattr(self, 'current_case') and self.current_case and hasattr(self.current_case, 'id') and self.current_case.id:
                exclude_id = self.current_case.id
        
        name_exists = case_service.check_case_name_exists(
            self.project_id,
            self.current_case.name, 
            self.folder_id, 
            exclude_id
        )
        
        if name_exists:
            Toast.warning(self, "警告", f"测试用例名称 '{self.current_case.name}' 已存在，请使用其他名称")
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
            self.start_execution()

    def start_execution(self):
        """开始执行测试用例"""
        if self.is_executing:
            return
        
        # 清空上一次的日志，确保当前日志是空的
        self.clear_logs()
        
        # 构建测试用例数据
        case_data = self.build_case_data_for_execution()
        if not case_data:
            return
        
        # 获取环境配置
        environment_config = self.get_environment_config()
        
        # 创建执行线程
        self.execution_thread = CaseExecutionThread(
            case_data=case_data,
            environment_config=environment_config,
            project_id=self.project_id
        )
        
        # 连接信号
        self.execution_thread.step_started.connect(self.on_step_started)
        self.execution_thread.step_finished.connect(self.on_step_finished)
        self.execution_thread.case_finished.connect(self.on_case_finished)
        self.execution_thread.log_message.connect(self.log_message_with_step)
        
        # 开始执行
        self.is_executing = True
        self.execution_thread.start()
        
        # 更新按钮状态
        self.update_buttons_state()
        
        # 记录开始执行日志
        self.log_message(f"开始执行测试用例: {case_data.get('name', '未知用例')}", "info")

    def build_case_data_for_execution(self):
        """构建用于执行的测试用例数据"""
        # 创建TestCase对象
        case = TestCase()
        case.name = self.name_edit.text().strip()
        case.description = self.description_edit.toPlainText().strip()
        case.environment_id = self.env_combo.currentData()
        case.project_id = self.project_id
        case.folder_id = self.folder_id
        case.enable_encryption = self.enable_encryption_checkbox.isChecked()
        case.encrypt_url = self.encrypt_url_edit.text().strip()
        case.decrypt_url = self.decrypt_url_edit.text().strip()
        
        # 获取步骤数据
        steps_data = self.get_steps_data()
        if not steps_data:
            Toast.warning(self, "警告", "没有可执行的测试步骤")
            return None
        
        # 将步骤字典转换为TestCaseStep对象
        from src.core.models.interface_models import TestCaseStep
        case.steps = [TestCaseStep.from_dict(step_dict) for step_dict in steps_data]
        
        # 转换为字典格式
        return case.to_dict()

    def get_steps_data(self):
        """获取步骤数据"""
        steps = []
        
        # 从步骤布局中获取所有步骤卡片
        if hasattr(self, 'steps_layout'):
            for i in range(self.steps_layout.count()):
                item = self.steps_layout.itemAt(i)
                if item and item.widget():
                    step_card = item.widget()
                    if hasattr(step_card, 'get_step_data'):
                        step_data = step_card.get_step_data()
                        if step_data:
                            steps.append(step_data)
        
        return steps

    def get_environment_config(self):
        """获取环境配置"""
        environment_id = self.env_combo.currentData()
        if environment_id:
            try:
                environment = self.environment_service.get_environment_by_id(environment_id)
                if environment:
                    return {
                        'base_url': environment.get('base_url', ''),
                        'headers': environment.get('headers', {}),
                        'variables': environment.get('variables', {})
                    }
            except Exception as e:
                print(f"获取环境配置失败: {e}")
        
        # 返回默认配置
        return {
            'base_url': '',
            'headers': {},
            'variables': {}
        }

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
        # 确保执行状态正确设置
        self.is_executing = False
        
        # 安全地清理线程资源（仅在stop_execution未调用时清理）
        if self.execution_thread and self.execution_thread.isRunning():
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
        
        # 如果执行日志弹窗已打开，则直接添加日志到弹窗
        if hasattr(self, 'execution_logs_dialog') and self.execution_logs_dialog:
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
                pass

    def clear_logs(self):
        """清空日志"""
        # 清空执行日志列表，确保每次执行都是全新的开始
        self.execution_logs = []

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
                    except RuntimeError:
                        # 如果widget已经被删除，忽略错误
                        pass

        # 显示占位符（如果存在且有效）
        if hasattr(self, 'steps_placeholder') and self.steps_placeholder:
            try:
                self.steps_placeholder.show()
            except RuntimeError:
                # 如果占位符已被删除，忽略错误
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
            except RuntimeError:
                # 如果占位符已被删除，忽略错误
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
        
        # 额外检查：如果用例有ID，尝试通过widget查找已存在的标签页
        if case_data and 'id' in case_data and case_data['id']:
            case_id = case_data['id']
            
            for existing_tab_id, tab_data in self.tabs.items():
                widget = tab_data['widget']
                if hasattr(widget, 'case_data') and widget.case_data and 'id' in widget.case_data and widget.case_data['id'] == case_id:
                    index = self.tab_widget.indexOf(widget)
                    self.tab_widget.setCurrentIndex(index)
                    return existing_tab_id
        
        # 创建新的标签页
        editor_widget = CaseTabWidget(case_data, project_id, folder_id)
        
        # 连接信号（使用弱引用避免循环引用）
        from weakref import ref
        
        def create_modified_handler(widget_ref):
            def handler(modified):
                widget = widget_ref()
                if widget is not None:
                    # 动态查找对应的tab_id
                    for tid, tab_data in self.tabs.items():
                        if tab_data['widget'] == widget:
                            self.set_tab_modified(tid, modified)
                            break
            return handler
        
        def create_saved_handler(widget_ref):
            def handler(data):
                widget = widget_ref()
                if widget is not None:
                    # 动态查找对应的tab_id
                    for tid, tab_data in self.tabs.items():
                        if tab_data['widget'] == widget:
                            self.case_saved(tid, data)
                            break
            return handler
        
        widget_ref = ref(editor_widget)
        editor_widget.modified_signal.connect(create_modified_handler(widget_ref))
        editor_widget.saved.connect(create_saved_handler(widget_ref))
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
        if case_data and 'id' in case_data and case_data['id']:
            tab_id = f"case_{case_data['id']}"
            return tab_id
        else:
            # 使用计数器来确保新标签页ID的唯一性
            new_case_count = sum(1 for tab_id in self.tabs.keys() if tab_id.startswith("new_case_"))
            tab_id = f"new_case_{new_case_count}"
            return tab_id
    
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
    
    def has_open_tabs(self):
        """检查是否有打开的标签页"""
        return self.tab_widget.count() > 0
    
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
                    
                    return True
            
            return False
                    
        except Exception:
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
                widget = self.tab_widget.widget(i)
                if widget == tab_data['widget']:
                    self.tab_widget.setTabText(i, title)
                    break

    def show_execution_logs(self):
        """显示执行日志弹窗"""
        # 获取当前活动标签页的日志列表
        current_logs = []
        if self.current_tab_id and self.current_tab_id in self.tabs:
            current_tab_widget = self.tabs[self.current_tab_id]['widget']
            if hasattr(current_tab_widget, 'execution_logs'):
                current_logs = current_tab_widget.execution_logs
        
        # 创建执行日志弹窗
        self.execution_logs_dialog = ExecutionLogsDialog(self)
        
        # 如果测试正在执行，将已记录的日志添加到弹窗中
        if current_logs:
            for log_entry in current_logs:
                step_index = log_entry.get('step_index', -1)
                
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
        else:
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
        # 首先检查是否需要更新标签页ID（当用例从新增变为编辑时）
        new_tab_id = self.generate_tab_id(case_data)
        
        # 如果标签页ID需要更新
        if new_tab_id != tab_id:
            # 检查旧的标签页是否存在
            if tab_id in self.tabs:
                # 保存当前标签页数据
                tab_data = self.tabs[tab_id]
                widget_index = self.tab_widget.indexOf(tab_data['widget'])
                
                # 删除旧的标签页记录
                del self.tabs[tab_id]
                
                # 添加新的标签页记录
                self.tabs[new_tab_id] = tab_data
                
                # 更新当前标签页ID
                if self.current_tab_id == tab_id:
                    self.current_tab_id = new_tab_id
                
                tab_id = new_tab_id  # 更新后续使用的tab_id
            else:
                tab_id = new_tab_id
        
        # 确保标签页存在于tabs中
        if tab_id not in self.tabs:
            # 尝试通过widget查找标签页
            for existing_tab_id, existing_tab_data in self.tabs.items():
                if hasattr(existing_tab_data['widget'], 'case_data') and existing_tab_data['widget'].case_data == case_data:
                    # 如果找到的标签页ID与需要的新ID不同，需要更新标签页记录
                    if existing_tab_id != tab_id:
                        # 保存当前标签页数据
                        tab_data = self.tabs[existing_tab_id]
                        
                        # 删除旧的标签页记录
                        del self.tabs[existing_tab_id]
                        
                        # 添加新的标签页记录
                        self.tabs[tab_id] = tab_data
                        
                        # 更新当前标签页ID
                        if self.current_tab_id == existing_tab_id:
                            self.current_tab_id = tab_id
                    
                    break
            else:
                # 创建新的标签页记录（这种情况应该很少发生）
                self.tabs[tab_id] = {
                    'widget': None,  # 这里需要从其他地方获取widget
                    'data': case_data,
                    'modified': False,
                    'tab_name': case_data.get('name', '新增用例')
                }
        
        # 更新标签页数据
        if tab_id in self.tabs:
            self.tabs[tab_id]['data'] = case_data
            
            # 更新CaseTabWidget实例的case_data属性（关键修复）
            tab_widget = self.tabs[tab_id]['widget']
            
            if hasattr(tab_widget, 'case_data'):
                tab_widget.case_data = case_data
                # 如果是编辑模式，确保is_edit标志正确设置
                if 'id' in case_data and case_data['id']:
                    tab_widget.is_edit = True
            
            # 更新标签页名称
            tab_name = case_data.get('name', '新增用例')
            self.tabs[tab_id]['tab_name'] = tab_name
            
            # 更新标签页标题
            for i in range(self.tab_widget.count()):
                if self.tab_widget.widget(i) == self.tabs[tab_id]['widget']:
                    self.tab_widget.setTabText(i, tab_name)
                    break
            
            # 重置标签页修改状态为False（关键修复）
            self.tabs[tab_id]['modified'] = False
            
            # 更新标签页标题，移除未保存标识
            self.update_tab_title(tab_id)
            
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
        self.header_widget.setCursor(Qt.PointingHandCursor)  # 设置鼠标悬停为手型
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(12, 8, 12, 8)
        
        # 展开/收起按钮 - 使用树形结构样式
        self.expand_btn = QPushButton()
        self.expand_btn.setFixedSize(16, 16)
        self.expand_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
            }
            QPushButton:hover {
                background: #e1e4e8;
                border-radius: 3px;
            }
        """)
        self.expand_btn.clicked.connect(self.toggle_expand)
        # 初始设置收起状态图标
        self.expand_btn.setIcon(QIcon(self.get_icon_path("expand_left.png")))
        self.expand_btn.setIconSize(QSize(12, 12))
        
        # 步骤序号和名称
        if self.step_index == -1:
            # 通用信息，不显示步骤序号
            self.step_label = QLabel(f"{self.step_name}")
        else:
            # 具体步骤，显示步骤序号
            self.step_label = QLabel(f"步骤 {self.step_index + 1}: {self.step_name}")
        self.step_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #24292f;")
        
        # 日志数量（放在步骤名称后面）
        self.log_count_label = QLabel("0 条日志")
        self.log_count_label.setStyleSheet("color: #666; font-size: 12px; margin-left: 4px;")
        
        # 状态图标（放在最右边）
        self.status_icon_label = QLabel()
        self.status_icon_label.setFixedSize(32, 32)  # 增加图标容器大小以适应200x200图标
        self.status_icon_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        self.status_icon_label.setStyleSheet("margin-left: 0px; margin-right: 8px; padding: 0px; background: transparent;")
        
        header_layout.addWidget(self.expand_btn)
        header_layout.addWidget(self.step_label)
        header_layout.addWidget(self.log_count_label)
        header_layout.addStretch(1)  # 增加弹性空间
        header_layout.addWidget(self.status_icon_label)
        
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
                border-radius: 12px;
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
        
        # 更新按钮图标 - 使用实际的图标文件
        if self.is_expanded:
            self.expand_btn.setIcon(QIcon(self.get_icon_path("exband_down.png")))
        else:
            self.expand_btn.setIcon(QIcon(self.get_icon_path("expand_left.png")))
    
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件处理"""
        # 检查双击是否发生在标题栏区域
        if self.header_widget.geometry().contains(event.pos()):
            self.toggle_expand()
        super().mouseDoubleClickEvent(event)
    
    def add_log(self, message, level="info"):
        """添加日志消息"""
        # 从HTML格式的消息中提取原始日志级别（如果消息包含HTML格式）
        actual_level = level
        
        # 如果消息是HTML格式且包含颜色标记，尝试从消息中提取实际级别
        if isinstance(message, str) and "<font color=" in message:
            # 根据HTML颜色标记推断日志级别
            if "color='red'" in message or "color=\"red\"" in message:
                actual_level = "error"
            elif "color='orange'" in message or "color=\"orange\"" in message:
                actual_level = "warning"
            elif "color='green'" in message or "color=\"green\"" in message:
                actual_level = "success"
            elif "color='gray'" in message or "color=\"gray\"" in message:
                actual_level = "debug"
            else:
                actual_level = "info"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 根据实际级别设置颜色
        if actual_level == "error":
            color = "red"
            prefix = "[ERROR]"
        elif actual_level == "warning":
            color = "orange"
            prefix = "[WARN]"
        elif actual_level == "success":
            color = "green"
            prefix = "[SUCCESS]"
        else:
            color = "black"
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
            'level': actual_level,
            'message': message
        })
        
        # 更新步骤状态：智能判断最终状态
        if self.step_status is None:
            # 第一次添加日志，根据日志级别设置初始状态
            if actual_level == "error" or "失败" in message or "failure" in message.lower():
                self.step_status = False
            else:
                self.step_status = True
            self.update_header_style()
        else:
            # 后续日志：优先根据最终执行结果判断
            # 如果出现失败相关的日志，更新为失败状态
            if (actual_level == "error" or "失败" in message or "failure" in message.lower() or
                "断言结果" in message and "失败" in message or "执行完成: failure" in message):
                self.step_status = False
                self.update_header_style()
            # 如果有成功或断言通过的信息，标记为成功
            elif ("成功" in message or "success" in message.lower() or 
                  "断言通过" in message or "assertion passed" in message.lower() or
                  "执行完成: success" in message):
                self.step_status = True
                self.update_header_style()
        
        # 更新日志数量
        self.log_count_label.setText(f"{len(self.logs)} 条日志")
    
    def get_icon_path(self, icon_name):
        """获取图标路径，支持exe打包后的资源路径"""
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
                return path
        
        # 如果所有路径都找不到，返回空字符串
        return ""
    
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

    def update_status_icon(self):
        """根据步骤状态更新状态图标"""
        if self.step_status is None:
            # 未执行状态：不显示图标
            self.status_icon_label.clear()
        elif self.step_status:
            # 执行成功：显示成功图标
            success_icon = self.get_icon("success.png")
            self.status_icon_label.setPixmap(success_icon.pixmap(16, 16))  # 增加图标大小以适应200x200源文件
        else:
            # 执行报错：显示失败图标
            fail_icon = self.get_icon("fail.png")
            self.status_icon_label.setPixmap(fail_icon.pixmap(16, 16))  # 增加图标大小以适应200x200源文件

    def update_header_style(self):
        """根据步骤状态更新标题栏样式"""
        if self.step_status is None:
            # 未执行状态：默认样式
            self.header_widget.setStyleSheet("""
                QWidget {
                    background: #ffffff;
                    border-radius: 8px;
                }
            """)
            self.step_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #24292f;")
        elif self.step_status:
            # 执行成功：浅绿色背景，黑色字体
            self.header_widget.setStyleSheet("""
                QWidget {
                    background: #e8f5e8;
                    border-radius: 8px;
                }
            """)
            self.step_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #000000;")
        else:
            # 执行报错：浅红色背景，黑色字体
            self.header_widget.setStyleSheet("""
                QWidget {
                    background: #ffeaea;
                    border-radius: 8px;
                }
            """)
            self.step_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #000000;")
        
        # 更新状态图标
        self.update_status_icon()


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
        
        # 如果是通用信息步骤，则隐藏该步骤
        if step_name == "通用信息":
            step_log.setVisible(False)
            step_log.header_widget.setVisible(False)
            step_log.content_widget.setVisible(False)
        else:
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
        # 从HTML格式的消息中提取原始日志级别（如果消息包含HTML格式）
        actual_level = level
        
        # 如果消息是HTML格式且包含颜色标记，尝试从消息中提取实际级别
        if isinstance(message, str) and "<font color=" in message:
            # 根据HTML颜色标记推断日志级别
            if "color='red'" in message or "color=\"red\"" in message:
                actual_level = "error"
            elif "color='orange'" in message or "color=\"orange\"" in message:
                actual_level = "warning"
            elif "color='green'" in message or "color=\"green\"" in message:
                actual_level = "success"
            elif "color='gray'" in message or "color=\"gray\"" in message:
                actual_level = "debug"
            else:
                actual_level = "info"
        
        if step_index in self.step_logs:
            self.step_logs[step_index].add_log(message, actual_level)
    
    def add_log(self, message, level="info"):
        """添加通用日志（不关联到具体步骤）"""
        # 添加通用日志到-1步骤
        self.add_log_with_step(message, level, -1)

    def add_log_with_step(self, message, level="info", step_index=-1, step_name=None):
        """添加带步骤信息的日志"""
        # 从HTML格式的消息中提取原始日志级别（如果消息包含HTML格式）
        actual_level = level
        
        # 如果消息是HTML格式且包含颜色标记，尝试从消息中提取实际级别
        if isinstance(message, str) and "<font color=" in message:
            # 根据HTML颜色标记推断日志级别
            if "color='red'" in message or "color=\"red\"" in message:
                actual_level = "error"
            elif "color='orange'" in message or "color=\"orange\"" in message:
                actual_level = "warning"
            elif "color='green'" in message or "color=\"green\"" in message:
                actual_level = "success"
            elif "color='gray'" in message or "color=\"gray\"" in message:
                actual_level = "debug"
            else:
                actual_level = "info"
        
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
        
        # 添加日志到对应步骤，使用实际的日志级别
        self.add_log_to_step(step_index, message, actual_level)
        
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
            color = "black"
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