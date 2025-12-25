import os
import json
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# 配置日志
logger = logging.getLogger('SchedulerManager')
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QFormLayout, QHeaderView, QCheckBox, QSpinBox,
                             QListWidget, QListWidgetItem, QToolBar, QAction,
                             QSizePolicy, QTabWidget, QRadioButton, QTreeWidget, 
                             QTreeWidgetItem, QGroupBox, QComboBox)
from src.ui.widgets.toast_tips import Toast
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelComboBox, NoWheelTabWidget
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QDateTime
from PyQt5.QtGui import QIcon, QFont, QColor, QBrush
from src.utils.css_utils import get_combobox_style
from src.core.services.scheduler_service import UnifiedSchedulerService
from src.core.services.test_case_service import TestCaseService
from src.core.services.project_service import ProjectService
from src.core.services.case_folder_service import CaseFolderService
from src.core.models.interface_models import TestScheduler
from src.utils.interface_utils.cron_parser import CronParser
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelTabWidget
from src.ui.interface_auto.components.tabbed_case_editor import CaseExecutionThread


class SchedulerDialog(QDialog):
    """调度编辑对话框"""

    def __init__(self, parent=None, scheduler_data=None):
        super().__init__(parent)
        self.scheduler_data = scheduler_data or {}
        self.is_edit = bool(scheduler_data)
        self.test_case_service = None  # 延迟初始化
        self.project_service = ProjectService()
        self.folder_service = CaseFolderService()
        self.current_project_id = None  # 存储当前项目ID
        self.init_ui()
        # 延迟加载数据，避免启动时数据库连接失败导致弹窗
        QTimer.singleShot(100, self.delayed_load_data)

    def set_current_project_id(self, project_id):
        """设置当前项目ID"""
        self.current_project_id = project_id

    def init_ui(self):
        self.setWindowTitle("编辑调度" if self.is_edit else "新增调度")
        self.setMinimumSize(1250, 1000)
        self.resize(1250, 1000)

        layout = QVBoxLayout(self)

        # 创建Tab页
        tab_widget = NoWheelTabWidget()

        # 基本信息Tab
        basic_tab = QWidget()
        self.setup_basic_tab(basic_tab)

        # 调度配置Tab
        schedule_tab = QWidget()
        self.setup_schedule_tab(schedule_tab)

        # 通知配置Tab
        notify_tab = QWidget()
        self.setup_notify_tab(notify_tab)

        tab_widget.addTab(basic_tab, "基本信息")
        tab_widget.addTab(schedule_tab, "调度配置")
        tab_widget.addTab(notify_tab, "通知配置")

        # 按钮布局
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        
        # 修改按钮文本为中文
        button_box.button(QDialogButtonBox.Ok).setText("确定")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")

        layout.addWidget(tab_widget)
        layout.addWidget(button_box)

    def setup_basic_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setSpacing(15)  # 增加间距
        layout.setContentsMargins(20, 20, 20, 20)  # 设置边距

        # 基本信息表单 - 去除标题和边框
        basic_info_widget = QWidget()
        basic_layout = QVBoxLayout(basic_info_widget)
        basic_layout.setSpacing(12)
        
        # 调度名称
        name_layout = QHBoxLayout()
        name_layout.setAlignment(Qt.AlignLeft)  # 设置整体靠左对齐
        name_label = QLabel("调度名称")
        name_label.setFixedWidth(80)
        name_label.setStyleSheet("font-weight: bold; color: #333;")
        name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 设置标签靠左对齐
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入调度名称")
        self.name_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
                outline: none;
            }
        """)
        name_layout.addWidget(name_label)
        self.name_edit.setFixedWidth(400)  # 设置固定宽度
        name_layout.addWidget(self.name_edit)
        
        # 调度描述 - 与标题放在同一行
        desc_layout = QHBoxLayout()
        desc_layout.setAlignment(Qt.AlignLeft)  # 设置整体靠左对齐
        desc_label = QLabel("调度描述")
        desc_label.setFixedWidth(80)
        desc_label.setStyleSheet("font-weight: bold; color: #333;")
        desc_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 设置标签靠左对齐
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(60)
        self.desc_edit.setPlaceholderText("请输入调度描述（可选）")
        self.desc_edit.setStyleSheet("""
            QTextEdit {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #0078d4;
                outline: none;
            }
        """)
        desc_layout.addWidget(desc_label)
        self.desc_edit.setFixedWidth(400)  # 设置固定宽度
        desc_layout.addWidget(self.desc_edit)
        
        basic_layout.addLayout(name_layout)
        basic_layout.addLayout(desc_layout)
        
        # 测试用例选择区域 - 去除标题和边框
        case_selection_widget = QWidget()
        case_selection_layout = QHBoxLayout(case_selection_widget)
        case_selection_layout.setSpacing(0)  # 移除间距，使三个竖栏紧挨在一起
        
        # 第一栏：文件夹树形列表
        folder_panel = QWidget()
        folder_layout = QVBoxLayout(folder_panel)
        folder_layout.setSpacing(0)  # 移除内部间距
        folder_layout.setContentsMargins(0, 0, 0, 0)  # 移除内容边距
        
        folder_label = QLabel("文件夹")
        folder_label.setStyleSheet("font-weight: bold; color: #333; margin-bottom: 5px;")
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: white;
                outline: none;
                min-height: 350px;
                margin: 0px;
                padding: 0px;
            }
            QTreeWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #f0f0f0;
                height: 30px;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #0078d4;
            }
            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        self.folder_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_tree)
        
        # 第二栏：测试用例列表
        case_panel = QWidget()
        case_layout = QVBoxLayout(case_panel)
        case_layout.setSpacing(0)  # 移除内部间距
        case_layout.setContentsMargins(0, 0, 0, 0)  # 移除内容边距
        
        case_label = QLabel("选择用例")
        case_label.setStyleSheet("font-weight: bold; color: #333; margin-bottom: 5px;")
        self.case_list = QListWidget()
        self.case_list.setSelectionMode(QListWidget.MultiSelection)
        self.case_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: white;
                outline: none;
                min-height: 350px;
                margin: 0px;
                padding: 0px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #0078d4;
            }
        """)
        self.case_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        case_layout.addWidget(case_label)
        case_layout.addWidget(self.case_list)
        
        # 按钮区域（放在选择用例和已选用例之间）
        button_panel = QWidget()
        button_layout = QVBoxLayout(button_panel)
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # 导入按钮（使用图标）
        self.import_btn = QPushButton()
        self.import_btn.setIcon(self.get_icon("input.png"))
        self.import_btn.setFixedSize(32, 32)
        self.import_btn.setToolTip("导入")
        self.import_btn.clicked.connect(self.import_selected_cases)
        self.import_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                padding: 0px;
                margin: 0px;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 0.2);
            }
        """)
        
        # 移除按钮（使用图标）
        self.remove_btn = QPushButton()
        self.remove_btn.setIcon(self.get_icon("out.png"))
        self.remove_btn.setFixedSize(32, 32)
        self.remove_btn.setToolTip("移除")
        self.remove_btn.clicked.connect(self.remove_selected_cases)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                padding: 0px;
                margin: 0px;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 0.2);
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.remove_btn)
        button_layout.addStretch()
        
        # 第三栏：已选用例区域
        selected_panel = QWidget()
        selected_layout = QVBoxLayout(selected_panel)
        selected_layout.setSpacing(0)
        selected_layout.setContentsMargins(0, 0, 0, 0)
        
        selected_label = QLabel("已选用例")
        selected_label.setStyleSheet("font-weight: bold; color: #333; margin-bottom: 5px;")
        self.selected_case_list = QListWidget()
        self.selected_case_list.setSelectionMode(QListWidget.MultiSelection)  # 支持多选
        self.selected_case_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: #f8f9fa;
                outline: none;
                min-height: 350px;
                margin: 0px;
                padding: 0px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #e9ecef;
                background-color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #d4edda;
                color: #155724;
            }
        """)
        self.selected_case_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        selected_layout.addWidget(selected_label)
        selected_layout.addWidget(self.selected_case_list)
        
        # 创建右侧固定区域：按钮 + 已选用例
        right_panel = QWidget()
        right_layout = QHBoxLayout(right_panel)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 将按钮区域和已选用例区域添加到右侧固定区域
        right_layout.addWidget(button_panel)
        right_layout.addWidget(selected_panel)
        
        # 设置面板大小策略，两个竖栏可以拉伸
        folder_panel.setMinimumWidth(250)  # 增加文件夹栏最小宽度
        folder_panel.setMaximumWidth(400)  # 增加文件夹栏最大宽度
        case_panel.setMinimumWidth(200)    # 减小选择用例栏最小宽度
        case_panel.setMaximumWidth(350)    # 减小选择用例栏最大宽度
        right_panel.setMinimumWidth(250)   # 右侧固定区域最小宽度
        right_panel.setMaximumWidth(400)   # 右侧固定区域最大宽度
        
        # 设置拉伸因子，让两个竖栏可以按比例拉伸
        case_selection_layout.addWidget(folder_panel, 3)  # 增加文件夹栏拉伸因子
        case_selection_layout.addWidget(case_panel, 2)    # 保持选择用例栏拉伸因子
        case_selection_layout.addWidget(right_panel, 0)   # 右侧固定区域不拉伸
        
        # 添加到主布局，设置拉伸因子让测试用例选择区域可以拉伸
        layout.addWidget(basic_info_widget, 0)  # 基本信息区域不拉伸
        layout.addWidget(case_selection_widget, 1)  # 测试用例选择区域可以拉伸
        
        # 连接信号
        self.folder_tree.itemSelectionChanged.connect(self.on_folder_selected)
        
        # 加载文件夹列表（基于当前选中的项目）
        self.load_folders()

    def get_icon(self, icon_name):
        """获取图标"""
        try:
            # 首先尝试从 resources/icons 目录加载（开发环境）
            icon_path = os.path.join("src", "resources", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
            
            # 如果不存在，尝试从 ui/interface_auto/icons 目录加载
            icon_path = os.path.join("src", "ui", "interface_auto", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
            
            # 打包后路径处理：尝试从 PyInstaller 临时解压目录加载
            if getattr(sys, 'frozen', False):
                # 打包后的可执行文件路径
                base_path = sys._MEIPASS
                # 尝试从打包后的 resources/icons 目录加载
                icon_path = os.path.join(base_path, "src", "resources", "icons", icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
                
                # 尝试直接加载图标文件
                icon_path = os.path.join(base_path, icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
                
                # 尝试从当前目录加载
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "resources", "icons", icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
        except:
            pass
        return QIcon()

    def setup_next_runs_display(self, parent_layout):
        """设置最近5次运行时间展示区域"""
        # 创建最近5次运行时间展示区域
        next_runs_widget = QWidget()
        next_runs_layout = QVBoxLayout(next_runs_widget)
        next_runs_layout.setSpacing(8)
        
        # 标题
        next_runs_title = QLabel("最近5次运行时间:")
        next_runs_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333;
                margin-bottom: 5px;
            }
        """)
        next_runs_layout.addWidget(next_runs_title)
        
        # 运行时间展示区域
        self.next_runs_text = QTextEdit()
        self.next_runs_text.setReadOnly(True)
        self.next_runs_text.setFixedHeight(120)
        self.next_runs_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-size: 12px;
                font-family: Consolas, 'Courier New', monospace;
                padding: 8px;
                color: #555;
            }
        """)
        self.next_runs_text.setPlaceholderText("点击'解析'按钮计算最近5次运行时间...")
        next_runs_layout.addWidget(self.next_runs_text)
        
        parent_layout.addWidget(next_runs_widget)


    def parse_cron_expression(self):
        """解析Cron表达式并计算最近5次运行时间"""
        try:
            cron_expression = self.cron_edit.text().strip()
            
            if not cron_expression:
                Toast.warning(self, "警告", "请输入Cron表达式")
                return
            
            # 校验Cron表达式格式
            is_valid, error_msg = self.validate_cron_expression(cron_expression)
            if not is_valid:
                Toast.warning(self, "Cron表达式错误", error_msg)
                return
            
            # 导入Cron解析器
            from src.utils.interface_utils.cron_parser import CronParser
            
            # 创建解析器实例
            parser = CronParser()
            
            # 获取当前时间作为基准时间
            base_time = datetime.now()
            
            # 计算最近5次运行时间
            next_runs = []
            current_time = base_time
            
            for i in range(5):
                next_run = parser.get_next_run(cron_expression, current_time)
                if next_run:
                    next_runs.append(next_run)
                    # 将下次执行时间作为新的基准时间，继续计算下一次
                    current_time = next_run + timedelta(seconds=1)
                else:
                    break
            
            # 更新下一次执行时间
            self.update_next_runs_display(next_runs)
            
            # 只在解析失败时显示警告
            if not next_runs:
                Toast.warning(self, "解析失败", "无法计算运行时间，请检查Cron表达式")
                
        except Exception as e:
            Toast.critical(self, "解析错误", f"解析Cron表达式时发生错误：{str(e)}")

    def setup_schedule_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setSpacing(20)  # 区域间距
        layout.setContentsMargins(20, 20, 20, 20)  # 设置边距

        # Cron表达式配置区域
        cron_widget = QWidget()
        cron_layout = QVBoxLayout(cron_widget)
        cron_layout.setSpacing(12)
        
        # Cron表达式标题
        cron_title = QLabel("Cron表达式配置")
        cron_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                margin-bottom: 10px;
            }
        """)
        cron_layout.addWidget(cron_title)

        # Cron表达式输入行
        cron_input_layout = QHBoxLayout()
        cron_input_layout.setSpacing(10)
        cron_input_layout.setAlignment(Qt.AlignLeft)  # 设置整体靠左对齐
        
        cron_label = QLabel("Cron表达式")
        cron_label.setStyleSheet("font-weight: bold; color: #555; min-width: 80px;")
        cron_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 设置标签靠左对齐
        
        self.cron_edit = QLineEdit()
        self.cron_edit.setPlaceholderText("例如: 0 0 12 * * ? (每天12点执行)")
        self.cron_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
                outline: none;
            }
        """)
        
        cron_input_layout.addWidget(cron_label)
        self.cron_edit.setFixedWidth(400)  # 设置固定宽度
        cron_input_layout.addWidget(self.cron_edit)

        # 解析按钮
        self.parse_button = QPushButton("解析")
        self.parse_button.setFixedSize(60, 32)
        self.parse_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        cron_input_layout.addWidget(self.parse_button)

        # 校验状态标签（放在解析按钮右侧）
        self.cron_validation_label = QLabel()
        self.cron_validation_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                padding: 4px 8px;
                border-radius: 4px;
                margin-left: 10px;
            }
        """)
        cron_input_layout.addWidget(self.cron_validation_label)
        
        # 添加拉伸因子，确保内容靠左对齐
        cron_input_layout.addStretch(1)

        # Cron表达式详细配置Tab栏
        self.setup_cron_tabs(cron_layout)

        cron_layout.addLayout(cron_input_layout)
        
        # 最近5次运行时间展示区域
        self.setup_next_runs_display(cron_layout)
        
        # 连接所有Tab选项的变化信号
        self.connect_tab_signals()
        
        # 连接cron表达式输入框的实时校验信号
        self.cron_edit.textChanged.connect(self.validate_cron_input)
        
        # 连接解析按钮的点击信号
        self.parse_button.clicked.connect(self.parse_cron_expression)

        layout.addWidget(cron_widget)
        layout.addStretch()  # 添加弹性空间

    def setup_cron_tabs(self, parent_layout):
        """设置Cron表达式详细配置Tab栏"""
        # Tab容器
        tab_widget = QTabWidget()
        tab_widget.setFixedHeight(300)  # 设置固定高度，避免自适应
        tab_widget.setFixedWidth(1000)  # 设置固定宽度，避免自适应
        tab_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 设置固定大小策略
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: white;
                margin-top: 5px;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 16px;
                margin-right: 2px;
                font-weight: bold;
                color: #555;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #0078d4;
                color: #0078d4;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
        """)

        # 秒Tab
        second_tab = self.create_second_tab()
        tab_widget.addTab(second_tab, "秒")

        # 分钟Tab
        minute_tab = self.create_minute_tab()
        tab_widget.addTab(minute_tab, "分钟")

        # 小时Tab
        hour_tab = self.create_hour_tab()
        tab_widget.addTab(hour_tab, "小时")

        # 日Tab
        day_tab = self.create_day_tab()
        tab_widget.addTab(day_tab, "日")

        # 月Tab
        month_tab = self.create_month_tab()
        tab_widget.addTab(month_tab, "月")

        # 周Tab
        week_tab = self.create_week_tab()
        tab_widget.addTab(week_tab, "周")

        # 年Tab
        year_tab = self.create_year_tab()
        tab_widget.addTab(year_tab, "年")

        parent_layout.addWidget(tab_widget)

    def create_second_tab(self):
        """创建秒Tab配置"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 选项组
        group_layout = QVBoxLayout()
        group_layout.setSpacing(8)

        # 选项1: 每秒
        option1_layout = QHBoxLayout()
        self.second_option1 = QRadioButton("每秒")
        self.second_option1.setChecked(True)
        option1_layout.addWidget(self.second_option1)
        option1_layout.addWidget(QLabel("允许的通配符[, - * /]"))
        option1_layout.addStretch()
        group_layout.addLayout(option1_layout)

        # 选项2: 周期
        option2_layout = QHBoxLayout()
        self.second_option2 = QRadioButton("周期从")
        option2_layout.addWidget(self.second_option2)
        
        self.second_start = QSpinBox()
        self.second_start.setRange(0, 59)
        self.second_start.setValue(0)
        option2_layout.addWidget(self.second_start)
        option2_layout.addWidget(QLabel("-"))
        
        self.second_end = QSpinBox()
        self.second_end.setRange(0, 59)
        self.second_end.setValue(59)
        option2_layout.addWidget(self.second_end)
        option2_layout.addWidget(QLabel("秒"))
        option2_layout.addStretch()
        group_layout.addLayout(option2_layout)

        # 选项3: 间隔
        option3_layout = QHBoxLayout()
        self.second_option3 = QRadioButton("从")
        option3_layout.addWidget(self.second_option3)
        
        self.second_from = QSpinBox()
        self.second_from.setRange(0, 59)
        self.second_from.setValue(0)
        option3_layout.addWidget(self.second_from)
        option3_layout.addWidget(QLabel("秒开始，每"))
        
        self.second_interval = QSpinBox()
        self.second_interval.setRange(1, 59)
        self.second_interval.setValue(1)
        option3_layout.addWidget(self.second_interval)
        option3_layout.addWidget(QLabel("秒执行一次"))
        option3_layout.addStretch()
        group_layout.addLayout(option3_layout)

        # 选项4: 指定秒数
        option4_layout = QHBoxLayout()
        self.second_option4 = QRadioButton("指定")
        option4_layout.addWidget(self.second_option4)
        
        self.second_specific = NoWheelComboBox()
        self.second_specific.setEditable(True)
        self.second_specific.addItems([str(i).zfill(2) for i in range(60)])
        self.second_specific.setStyleSheet(get_combobox_style())
        self.second_specific.setCurrentText("00")
        option4_layout.addWidget(self.second_specific)
        option4_layout.addWidget(QLabel("秒"))
        option4_layout.addStretch()
        group_layout.addLayout(option4_layout)

        layout.addLayout(group_layout)
        layout.addStretch()
        
        return widget

    def create_minute_tab(self):
        """创建分钟Tab配置"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 选项组
        group_layout = QVBoxLayout()
        group_layout.setSpacing(8)

        # 选项1: 每分钟
        option1_layout = QHBoxLayout()
        self.minute_option1 = QRadioButton("每分钟")
        self.minute_option1.setChecked(True)
        option1_layout.addWidget(self.minute_option1)
        option1_layout.addWidget(QLabel("允许的通配符[, - * /]"))
        option1_layout.addStretch()
        group_layout.addLayout(option1_layout)

        # 选项2: 周期
        option2_layout = QHBoxLayout()
        self.minute_option2 = QRadioButton("周期从")
        option2_layout.addWidget(self.minute_option2)
        
        self.minute_start = QSpinBox()
        self.minute_start.setRange(0, 59)
        self.minute_start.setValue(0)
        option2_layout.addWidget(self.minute_start)
        option2_layout.addWidget(QLabel("-"))
        
        self.minute_end = QSpinBox()
        self.minute_end.setRange(0, 59)
        self.minute_end.setValue(59)
        option2_layout.addWidget(self.minute_end)
        option2_layout.addWidget(QLabel("分钟"))
        option2_layout.addStretch()
        group_layout.addLayout(option2_layout)

        # 选项3: 间隔
        option3_layout = QHBoxLayout()
        self.minute_option3 = QRadioButton("从")
        option3_layout.addWidget(self.minute_option3)
        
        self.minute_from = QSpinBox()
        self.minute_from.setRange(0, 59)
        self.minute_from.setValue(0)
        option3_layout.addWidget(self.minute_from)
        option3_layout.addWidget(QLabel("分钟开始，每"))
        
        self.minute_interval = QSpinBox()
        self.minute_interval.setRange(1, 59)
        self.minute_interval.setValue(1)
        option3_layout.addWidget(self.minute_interval)
        option3_layout.addWidget(QLabel("分钟执行一次"))
        option3_layout.addStretch()
        group_layout.addLayout(option3_layout)

        # 选项4: 指定分钟数
        option4_layout = QHBoxLayout()
        self.minute_option4 = QRadioButton("指定")
        option4_layout.addWidget(self.minute_option4)
        
        self.minute_specific = NoWheelComboBox()
        self.minute_specific.setEditable(True)
        self.minute_specific.addItems([str(i).zfill(2) for i in range(60)])
        self.minute_specific.setStyleSheet(get_combobox_style())
        self.minute_specific.setCurrentText("00")
        option4_layout.addWidget(self.minute_specific)
        option4_layout.addWidget(QLabel("分钟"))
        option4_layout.addStretch()
        group_layout.addLayout(option4_layout)

        layout.addLayout(group_layout)
        layout.addStretch()
        
        return widget

    def create_hour_tab(self):
        """创建小时Tab配置"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 选项组
        group_layout = QVBoxLayout()
        group_layout.setSpacing(8)

        # 选项1: 每小时
        option1_layout = QHBoxLayout()
        self.hour_option1 = QRadioButton("每小时")
        self.hour_option1.setChecked(True)
        option1_layout.addWidget(self.hour_option1)
        option1_layout.addWidget(QLabel("允许的通配符[, - * /]"))
        option1_layout.addStretch()
        group_layout.addLayout(option1_layout)

        # 选项2: 周期
        option2_layout = QHBoxLayout()
        self.hour_option2 = QRadioButton("周期从")
        option2_layout.addWidget(self.hour_option2)
        
        self.hour_start = QSpinBox()
        self.hour_start.setRange(0, 23)
        self.hour_start.setValue(0)
        option2_layout.addWidget(self.hour_start)
        option2_layout.addWidget(QLabel("-"))
        
        self.hour_end = QSpinBox()
        self.hour_end.setRange(0, 23)
        self.hour_end.setValue(23)
        option2_layout.addWidget(self.hour_end)
        option2_layout.addWidget(QLabel("小时"))
        option2_layout.addStretch()
        group_layout.addLayout(option2_layout)

        # 选项3: 间隔
        option3_layout = QHBoxLayout()
        self.hour_option3 = QRadioButton("从")
        option3_layout.addWidget(self.hour_option3)
        
        self.hour_from = QSpinBox()
        self.hour_from.setRange(0, 23)
        self.hour_from.setValue(0)
        option3_layout.addWidget(self.hour_from)
        option3_layout.addWidget(QLabel("小时开始，每"))
        
        self.hour_interval = QSpinBox()
        self.hour_interval.setRange(1, 23)
        self.hour_interval.setValue(1)
        option3_layout.addWidget(self.hour_interval)
        option3_layout.addWidget(QLabel("小时执行一次"))
        option3_layout.addStretch()
        group_layout.addLayout(option3_layout)

        # 选项4: 指定小时数
        option4_layout = QHBoxLayout()
        self.hour_option4 = QRadioButton("指定")
        option4_layout.addWidget(self.hour_option4)
        
        self.hour_specific = NoWheelComboBox()
        self.hour_specific.setEditable(True)
        self.hour_specific.addItems([str(i).zfill(2) for i in range(24)])
        self.hour_specific.setStyleSheet(get_combobox_style())
        self.hour_specific.setCurrentText("00")
        option4_layout.addWidget(self.hour_specific)
        option4_layout.addWidget(QLabel("小时"))
        option4_layout.addStretch()
        group_layout.addLayout(option4_layout)

        layout.addLayout(group_layout)
        layout.addStretch()
        
        return widget

    def create_day_tab(self):
        """创建日Tab配置"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 选项组
        group_layout = QVBoxLayout()
        group_layout.setSpacing(8)

        # 选项1: 每日
        option1_layout = QHBoxLayout()
        self.day_option1 = QRadioButton("每日")
        self.day_option1.setChecked(True)
        option1_layout.addWidget(self.day_option1)
        option1_layout.addWidget(QLabel("允许的通配符[, - * / L W]"))
        option1_layout.addStretch()
        group_layout.addLayout(option1_layout)

        # 选项2: 不指定
        option2_layout = QHBoxLayout()
        self.day_option2 = QRadioButton("不指定")
        option2_layout.addWidget(self.day_option2)
        option2_layout.addWidget(QLabel("忽略日字段"))
        option2_layout.addStretch()
        group_layout.addLayout(option2_layout)

        # 选项3: 周期
        option3_layout = QHBoxLayout()
        self.day_option3 = QRadioButton("周期从")
        option3_layout.addWidget(self.day_option3)
        
        self.day_start = QSpinBox()
        self.day_start.setRange(1, 31)
        self.day_start.setValue(1)
        option3_layout.addWidget(self.day_start)
        option3_layout.addWidget(QLabel("-"))
        
        self.day_end = QSpinBox()
        self.day_end.setRange(1, 31)
        self.day_end.setValue(31)
        option3_layout.addWidget(self.day_end)
        option3_layout.addWidget(QLabel("日"))
        option3_layout.addStretch()
        group_layout.addLayout(option3_layout)

        # 选项4: 从...日开始,每...天执行一次
        option4_layout = QHBoxLayout()
        self.day_option4 = QRadioButton("从")
        option4_layout.addWidget(self.day_option4)
        
        self.day_from = QSpinBox()
        self.day_from.setRange(1, 31)
        self.day_from.setValue(1)
        option4_layout.addWidget(self.day_from)
        option4_layout.addWidget(QLabel("日开始,每"))
        
        self.day_interval = QSpinBox()
        self.day_interval.setRange(1, 31)
        self.day_interval.setValue(1)
        option4_layout.addWidget(self.day_interval)
        option4_layout.addWidget(QLabel("天执行一次"))
        option4_layout.addStretch()
        group_layout.addLayout(option4_layout)

        # 选项5: 每月最后一天
        option5_layout = QHBoxLayout()
        self.day_option5 = QRadioButton("每月最后一天")
        option5_layout.addWidget(self.day_option5)
        option5_layout.addWidget(QLabel("使用W通配符"))
        option5_layout.addStretch()
        group_layout.addLayout(option5_layout)

        # 选项6: 指定日期
        option6_layout = QHBoxLayout()
        self.day_option6 = QRadioButton("指定")
        option6_layout.addWidget(self.day_option6)
        
        self.day_specific = NoWheelComboBox()
        self.day_specific.setEditable(True)
        self.day_specific.addItems([str(i) for i in range(1, 32)])
        self.day_specific.setStyleSheet(get_combobox_style())
        self.day_specific.setCurrentText("1")
        option6_layout.addWidget(self.day_specific)
        option6_layout.addWidget(QLabel("日"))
        option6_layout.addStretch()
        group_layout.addLayout(option6_layout)

        layout.addLayout(group_layout)
        layout.addStretch()
        
        return widget

    def create_month_tab(self):
        """创建月Tab配置"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 选项组
        group_layout = QVBoxLayout()
        group_layout.setSpacing(8)

        # 选项1: 每月
        option1_layout = QHBoxLayout()
        self.month_option1 = QRadioButton("每月")
        self.month_option1.setChecked(True)
        option1_layout.addWidget(self.month_option1)
        option1_layout.addWidget(QLabel("允许的通配符[, - * /]"))
        option1_layout.addStretch()
        group_layout.addLayout(option1_layout)

        # 选项2: 不指定
        option2_layout = QHBoxLayout()
        self.month_option2 = QRadioButton("不指定")
        option2_layout.addWidget(self.month_option2)
        option2_layout.addWidget(QLabel("忽略月字段"))
        option2_layout.addStretch()
        group_layout.addLayout(option2_layout)

        # 选项3: 周期
        option3_layout = QHBoxLayout()
        self.month_option3 = QRadioButton("周期从")
        option3_layout.addWidget(self.month_option3)
        
        self.month_start = QSpinBox()
        self.month_start.setRange(1, 12)
        self.month_start.setValue(1)
        option3_layout.addWidget(self.month_start)
        option3_layout.addWidget(QLabel("-"))
        
        self.month_end = QSpinBox()
        self.month_end.setRange(1, 12)
        self.month_end.setValue(12)
        option3_layout.addWidget(self.month_end)
        option3_layout.addWidget(QLabel("月"))
        option3_layout.addStretch()
        group_layout.addLayout(option3_layout)

        # 选项4: 从...日开始,每...月执行一次
        option4_layout = QHBoxLayout()
        self.month_option4 = QRadioButton("从")
        option4_layout.addWidget(self.month_option4)
        
        self.month_from = QSpinBox()
        self.month_from.setRange(1, 12)
        self.month_from.setValue(1)
        option4_layout.addWidget(self.month_from)
        option4_layout.addWidget(QLabel("月开始,每"))
        
        self.month_interval = QSpinBox()
        self.month_interval.setRange(1, 12)
        self.month_interval.setValue(1)
        option4_layout.addWidget(self.month_interval)
        option4_layout.addWidget(QLabel("月执行一次"))
        option4_layout.addStretch()
        group_layout.addLayout(option4_layout)

        # 选项5: 指定月份
        option5_layout = QHBoxLayout()
        self.month_option5 = QRadioButton("指定")
        option5_layout.addWidget(self.month_option5)
        
        self.month_specific = NoWheelComboBox()
        self.month_specific.setEditable(True)
        self.month_specific.addItems([str(i) for i in range(1, 13)])
        self.month_specific.setStyleSheet(get_combobox_style())
        self.month_specific.setCurrentText("1")
        option5_layout.addWidget(self.month_specific)
        option5_layout.addWidget(QLabel("月"))
        option5_layout.addStretch()
        group_layout.addLayout(option5_layout)

        layout.addLayout(group_layout)
        layout.addStretch()
        
        return widget

    def create_week_tab(self):
        """创建周Tab配置"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 选项组
        group_layout = QVBoxLayout()
        group_layout.setSpacing(8)

        # 选项1: 每周
        option1_layout = QHBoxLayout()
        self.week_option1 = QRadioButton("每周")
        option1_layout.addWidget(self.week_option1)
        option1_layout.addWidget(QLabel("允许的通配符[, - * / L #]"))
        option1_layout.addStretch()
        group_layout.addLayout(option1_layout)

        # 选项2: 不指定
        option2_layout = QHBoxLayout()
        self.week_option2 = QRadioButton("不指定")
        self.week_option2.setChecked(True)
        option2_layout.addWidget(self.week_option2)
        option2_layout.addWidget(QLabel("忽略周字段"))
        option2_layout.addStretch()
        group_layout.addLayout(option2_layout)

        # 选项3: 周期
        option3_layout = QHBoxLayout()
        self.week_option3 = QRadioButton("周期从")
        option3_layout.addWidget(self.week_option3)
        
        self.week_start = NoWheelComboBox()
        week_days = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
        self.week_start.addItems(week_days)
        self.week_start.setStyleSheet(get_combobox_style())
        option3_layout.addWidget(self.week_start)
        option3_layout.addWidget(QLabel("-"))
        
        self.week_end = NoWheelComboBox()
        self.week_end.addItems(week_days)
        self.week_end.setStyleSheet(get_combobox_style())
        self.week_end.setCurrentText("周一")
        option3_layout.addWidget(self.week_end)
        option3_layout.addStretch()
        group_layout.addLayout(option3_layout)

        # 选项4: 第X周的周X
        option4_layout = QHBoxLayout()
        self.week_option4 = QRadioButton("第")
        option4_layout.addWidget(self.week_option4)
        
        self.week_which = QSpinBox()
        self.week_which.setRange(1, 5)
        self.week_which.setValue(1)
        option4_layout.addWidget(self.week_which)
        option4_layout.addWidget(QLabel("周的"))
        
        self.week_day = NoWheelComboBox()
        self.week_day.addItems(week_days)
        self.week_day.setStyleSheet(get_combobox_style())
        self.week_day.setCurrentText("周一")
        option4_layout.addWidget(self.week_day)
        option4_layout.addStretch()
        group_layout.addLayout(option4_layout)

        # 选项5: 本月最后一个周X
        option5_layout = QHBoxLayout()
        self.week_option5 = QRadioButton("本月最后一个")
        option5_layout.addWidget(self.week_option5)
        
        self.week_last_day = NoWheelComboBox()
        self.week_last_day.addItems(week_days)
        self.week_last_day.setStyleSheet(get_combobox_style())
        self.week_last_day.setCurrentText("周一")
        option5_layout.addWidget(self.week_last_day)
        option5_layout.addStretch()
        group_layout.addLayout(option5_layout)

        # 选项6: 指定星期
        option6_layout = QHBoxLayout()
        self.week_option6 = QRadioButton("指定")
        option6_layout.addWidget(self.week_option6)
        
        self.week_specific = NoWheelComboBox()
        self.week_specific.setEditable(True)
        self.week_specific.addItems(week_days)
        self.week_specific.setStyleSheet(get_combobox_style())
        self.week_specific.setCurrentText("周一")
        option6_layout.addWidget(self.week_specific)
        option6_layout.addStretch()
        group_layout.addLayout(option6_layout)

        layout.addLayout(group_layout)
        layout.addStretch()
        
        return widget

    def create_year_tab(self):
        """创建年Tab配置"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 选项组
        group_layout = QVBoxLayout()
        group_layout.setSpacing(8)

        # 选项1: 每年
        option1_layout = QHBoxLayout()
        self.year_option1 = QRadioButton("每年")
        self.year_option1.setChecked(True)
        option1_layout.addWidget(self.year_option1)
        option1_layout.addWidget(QLabel("允许的通配符[, - * /]"))
        option1_layout.addStretch()
        group_layout.addLayout(option1_layout)

        # 选项2: 不指定
        option2_layout = QHBoxLayout()
        self.year_option2 = QRadioButton("不指定")
        option2_layout.addWidget(self.year_option2)
        option2_layout.addWidget(QLabel("忽略年字段"))
        option2_layout.addStretch()
        group_layout.addLayout(option2_layout)

        # 选项3: 周期
        option3_layout = QHBoxLayout()
        self.year_option3 = QRadioButton("周期从")
        option3_layout.addWidget(self.year_option3)
        
        self.year_start = QSpinBox()
        self.year_start.setRange(2023, 2030)
        self.year_start.setValue(2024)
        option3_layout.addWidget(self.year_start)
        option3_layout.addWidget(QLabel("-"))
        
        self.year_end = QSpinBox()
        self.year_end.setRange(2023, 2030)
        self.year_end.setValue(2030)
        option3_layout.addWidget(self.year_end)
        option3_layout.addWidget(QLabel("年"))
        option3_layout.addStretch()
        group_layout.addLayout(option3_layout)

        layout.addLayout(group_layout)
        layout.addStretch()
        
        return widget

    def setup_notify_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)  # 设置边距
        layout.setAlignment(Qt.AlignLeft)  # 设置整体靠左对齐

        # 邮件通知配置
        email_group = QGroupBox("邮件通知")
        email_layout = QVBoxLayout(email_group)
        
        # 启用邮件通知
        self.email_enabled_check = QCheckBox("启用")
        email_layout.addWidget(self.email_enabled_check)
        
        # 收件人配置
        recipient_layout = QFormLayout()
        recipient_layout.setLabelAlignment(Qt.AlignLeft)
        recipient_layout.setFormAlignment(Qt.AlignLeft)
        
        self.email_recipient_edit = QLineEdit()
        self.email_recipient_edit.setPlaceholderText("多个邮箱用逗号分隔")
        self.email_recipient_edit.setFixedWidth(400)
        recipient_layout.addRow("收件人:", self.email_recipient_edit)
        
        email_layout.addLayout(recipient_layout)
        
        # 说明文本
        info_label = QLabel("注意：邮件发送将使用全局邮箱配置，请先在系统设置中配置SMTP服务器。")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 12px; margin-top: 10px;")
        email_layout.addWidget(info_label)

        # 企业微信通知配置
        wechat_group = QGroupBox("企业微信通知")
        wechat_layout = QVBoxLayout(wechat_group)
        
        self.wechat_enabled_check = QCheckBox("启用")
        wechat_layout.addWidget(self.wechat_enabled_check)
        
        wechat_form_layout = QFormLayout()
        wechat_form_layout.setLabelAlignment(Qt.AlignLeft)
        wechat_form_layout.setFormAlignment(Qt.AlignLeft)
        
        self.wechat_webhook_edit = QLineEdit()
        self.wechat_webhook_edit.setPlaceholderText("输入企业微信机器人Webhook URL")
        self.wechat_webhook_edit.setFixedWidth(400)
        wechat_form_layout.addRow("Webhook URL:", self.wechat_webhook_edit)
        
        wechat_layout.addLayout(wechat_form_layout)

        # 添加布局到主布局
        layout.addWidget(email_group)
        layout.addWidget(wechat_group)
        layout.addStretch()

    def delayed_load_data(self):
        """延迟加载数据，避免启动时数据库连接失败导致弹窗"""
        try:
            # 初始化服务对象
            self.test_case_service = TestCaseService()
            
            # 如果是编辑模式，先从scheduler_data中获取项目ID并设置
            if self.is_edit and self.scheduler_data:
                project_id = self.scheduler_data.get('project_id')
                if project_id:
                    self.current_project_id = project_id
            
            # 直接加载文件夹列表（根据当前选中的项目）
            self.load_folders()
            
            # 如果是编辑模式，在文件夹列表加载完成后重新加载调度数据
            if self.is_edit:
                self.load_scheduler_data()
        except Exception as e:
            # 静默处理，不显示弹窗
            print(f"延迟加载数据失败: {str(e)}")



    def load_folders(self):
        """加载当前选中项目的文件夹树形结构"""
        try:
            # 检查是否有有效的项目ID
            if not self.current_project_id:
                # 如果没有项目ID，显示提示信息
                self.folder_tree.clear()
                self.show_no_data_message("请先在调度管理页面选择项目")
                return
                
            # 从数据库动态获取指定项目的文件夹（带层级结构）
            root_folders = self.folder_service.get_folders_by_project(self.current_project_id)
            
            self.folder_tree.clear()
            if not root_folders:
                # 如果没有文件夹，显示提示信息
                self.show_no_data_message("该项目下暂无文件夹")
                return
                
            # 递归构建树形结构
            self._build_folder_tree(root_folders, None)
            self.folder_tree.expandAll()  # 展开所有节点
        except Exception as e:
            print(f"加载文件夹树失败: {e}")
            self.show_no_data_message("加载文件夹失败，请检查数据库连接")

    def _build_folder_tree(self, folders: List[Dict[str, Any]], parent_item: Optional[QTreeWidgetItem]):
        """递归构建文件夹树形结构"""
        for folder in folders:
            # 创建树节点
            item = QTreeWidgetItem()
            item.setText(0, folder['name'])
            item.setData(0, Qt.UserRole, folder['id'])
            item.setIcon(0, self.get_icon("folder.png"))
            
            # 添加到父节点或根节点
            if parent_item:
                parent_item.addChild(item)
            else:
                self.folder_tree.addTopLevelItem(item)
            
            # 递归处理子文件夹
            if 'children' in folder and folder['children']:
                self._build_folder_tree(folder['children'], item)

    def show_no_data_message(self, message):
        """在文件夹树中显示无数据提示"""
        item = QTreeWidgetItem()
        item.setText(0, message)
        item.setFlags(Qt.NoItemFlags)  # 设置为不可选择
        item.setTextAlignment(0, Qt.AlignCenter)
        item.setForeground(0, QColor("#999"))
        self.folder_tree.addTopLevelItem(item)

    def on_folder_selected(self):
        """文件夹选择变化时加载测试用例"""
        selected_items = self.folder_tree.selectedItems()
        if not selected_items:
            return
            
        # 检查是否是提示信息项（不可选择的项）
        if selected_items[0].flags() == Qt.NoItemFlags:
            self.case_list.clear()
            return
            
        folder_id = selected_items[0].data(0, Qt.UserRole)
        self.load_test_cases_by_folder(folder_id)

    def load_test_cases_by_folder(self, folder_id):
        """根据文件夹ID加载测试用例列表"""
        try:
            # 延迟初始化测试用例服务
            if self.test_case_service is None:
                self.test_case_service = TestCaseService()
            
            # 检查是否有有效的项目ID
            if not self.current_project_id:
                self.case_list.clear()
                return
                
            # 从数据库动态获取指定文件夹的测试用例
            cases = self.test_case_service.get_cases_by_folder(self.current_project_id, folder_id)
            
            self.case_list.clear()
            if not cases:
                # 如果没有测试用例，显示提示信息
                self.show_no_cases_message("该文件夹下暂无测试用例")
                return
                
            for case in cases:
                item = QListWidgetItem(case['name'])
                item.setData(Qt.UserRole, case['id'])
                # 设置测试用例图标
                item.setIcon(self.get_icon("test_case.png"))
                self.case_list.addItem(item)
        except Exception as e:
            print(f"加载测试用例失败: {e}")
            self.show_no_cases_message("加载测试用例失败")

    def show_no_cases_message(self, message):
        """在测试用例列表中显示无数据提示"""
        item = QListWidgetItem(message)
        item.setFlags(Qt.NoItemFlags)  # 设置为不可选择
        item.setTextAlignment(Qt.AlignCenter)
        item.setForeground(QColor("#999"))
        self.case_list.addItem(item)

    def import_selected_cases(self):
        """导入选中的测试用例到已选用例区域"""
        selected_items = self.case_list.selectedItems()
        if not selected_items:
            Toast.warning(self, "提示", "请先选择要导入的测试用例")
            return
            
        for item in selected_items:
            # 检查是否已存在
            exists = False
            for i in range(self.selected_case_list.count()):
                existing_item = self.selected_case_list.item(i)
                if existing_item.data(Qt.UserRole) == item.data(Qt.UserRole):
                    exists = True
                    break
                    
            if not exists:
                new_item = QListWidgetItem(item.text())
                new_item.setData(Qt.UserRole, item.data(Qt.UserRole))
                # 设置测试用例图标
                new_item.setIcon(self.get_icon("test_case.png"))
                self.selected_case_list.addItem(new_item)

    def remove_selected_cases(self):
        """从已选用例区域移除选中的用例（支持多选）"""
        selected_items = self.selected_case_list.selectedItems()
        if not selected_items:
            Toast.warning(self, "提示", "请先选择要移除的测试用例")
            return
            
        # 批量移除选中的用例（按行号从大到小排序，避免索引变化问题）
        rows = sorted([self.selected_case_list.row(item) for item in selected_items], reverse=True)
        for row in rows:
            self.selected_case_list.takeItem(row)

    def load_test_cases(self):
        """加载测试用例列表（兼容旧方法）"""
        # 检查服务对象是否已初始化
        if self.test_case_service is None:
            print("测试用例服务未初始化，跳过加载测试用例")
            return
            
        try:
            cases = self.test_case_service.get_all_cases()
            for case in cases:
                item = QListWidgetItem(case['name'])
                item.setData(Qt.UserRole, case['id'])
                self.case_list.addItem(item)
        except Exception as e:
            print(f"加载测试用例失败: {e}")

    def load_scheduler_data(self):
        """加载调度数据到表单"""
        if not self.scheduler_data:
            return

        # 基本信息
        self.name_edit.setText(self.scheduler_data.get('name', ''))
        self.desc_edit.setText(self.scheduler_data.get('description', ''))

        # 项目选择 - 已移除项目列表，直接使用当前选中的项目
        # 不再需要手动选择项目，系统会自动使用当前业务管理页面选中的项目

        # 测试用例选择
        case_ids = self.scheduler_data.get('case_ids', [])
        # 清空已选用例列表
        self.selected_case_list.clear()
        
        # 延迟初始化测试用例服务
        if self.test_case_service is None:
            self.test_case_service = TestCaseService()
        
        # 加载所有测试用例到已选用例区域
        try:
            all_cases = self.test_case_service.get_all_cases()
            for case in all_cases:
                if case['id'] in case_ids:
                    item = QListWidgetItem(case['name'])
                    item.setData(Qt.UserRole, case['id'])
                    # 设置测试用例图标
                    item.setIcon(self.get_icon("test_case.png"))
                    self.selected_case_list.addItem(item)
        except Exception as e:
            print(f"加载已选用例失败: {e}")

        # Cron表达式
        cron_expression = self.scheduler_data.get('cron_expression', '')
        self.cron_edit.setText(cron_expression)
        
        # 解析Cron表达式并更新Tab页选项
        if cron_expression:
            self.parse_cron_to_tabs(cron_expression)

        # 通知配置
        notify_emails = self.scheduler_data.get('notify_emails', [])
        self.email_recipient_edit.setText(','.join(notify_emails))

        # 邮件服务器配置
        email_config = self.scheduler_data.get('email_config', {})
        
        # 设置邮件通知启用状态
        # 直接使用数据库中保存的启用状态
        email_enabled = email_config.get('enabled', True)  # 默认为启用状态
        self.email_enabled_check.setChecked(email_enabled)

        notify_wechat = self.scheduler_data.get('notify_wechat', {})
        # 处理notify_wechat可能是列表的情况
        if isinstance(notify_wechat, list):
            # 如果是列表，取第一个元素（如果有）
            if notify_wechat:
                notify_wechat = notify_wechat[0] if isinstance(notify_wechat[0], dict) else {}
            else:
                notify_wechat = {}
        
        self.wechat_webhook_edit.setText(notify_wechat.get('webhook', ''))
        
        # 设置企业微信通知启用状态
        # 直接使用数据库中保存的启用状态
        wechat_enabled = notify_wechat.get('enabled', True)  # 默认为启用状态
        self.wechat_enabled_check.setChecked(wechat_enabled)

    def validate_and_accept(self):
        """校验表单数据，通过后关闭对话框"""
        # 校验调度名称
        name = self.name_edit.text().strip()
        if not name:
            Toast.warning(self, "校验错误", "请填写调度名称")
            self.name_edit.setFocus()
            return
            
        # 校验调度名称是否重复
        scheduler_service = UnifiedSchedulerService()
        if self.is_edit:
            # 编辑模式：检查除当前调度外的其他调度是否有相同名称
            if scheduler_service.check_scheduler_name_exists(name, self.scheduler_data.get('id')):
                Toast.warning(self, "校验错误", f"调度名称 '{name}' 已存在，请使用其他名称")
                self.name_edit.setFocus()
                return
        else:
            # 新增模式：检查是否有相同名称的调度
            if scheduler_service.check_scheduler_name_exists(name):
                Toast.warning(self, "校验错误", f"调度名称 '{name}' 已存在，请使用其他名称")
                self.name_edit.setFocus()
                return
            
        # 校验Cron表达式
        cron_expression = self.cron_edit.text().strip()
        if not cron_expression:
            Toast.warning(self, "校验错误", "请填写Cron表达式")
            self.cron_edit.setFocus()
            return
            
        # 校验Cron表达式格式
        is_valid, error_msg = self.validate_cron_expression(cron_expression)
        if not is_valid:
            Toast.warning(self, "校验错误", f"Cron表达式格式错误：{error_msg}")
            self.cron_edit.setFocus()
            return
            
        # 校验测试用例选择
        if self.selected_case_list.count() == 0:
            Toast.warning(self, "校验错误", "请至少关联一个测试用例")
            return
            
        # 所有校验通过，关闭对话框
        self.accept()

    def get_data(self):
        """获取表单数据"""
        # 基本信息
        data = {
            'name': self.name_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip(),
            'cron_expression': self.cron_edit.text().strip(),
            'enabled': False,  # 新增调度默认为不启用状态
            'project_id': self.current_project_id  # 使用传递的项目ID
        }

        # 测试用例ID列表（从已选用例区域获取）
        case_ids = []
        for i in range(self.selected_case_list.count()):
            item = self.selected_case_list.item(i)
            case_ids.append(item.data(Qt.UserRole))
        data['case_ids'] = case_ids

        # 通知配置
        email_recipients = self.email_recipient_edit.text().strip()
        if email_recipients:
            data['notify_emails'] = [email.strip() for email in email_recipients.split(',')]
        else:
            data['notify_emails'] = []

        # 邮件服务器配置
        # 记录邮件通知启用状态
        email_enabled = self.email_enabled_check.isChecked()
        
        if email_enabled:
            data['email_config'] = {
                'enabled': email_enabled  # 记录邮件通知启用状态
            }
        else:
            data['email_config'] = {}

        wechat_webhook = self.wechat_webhook_edit.text().strip()
        wechat_enabled = self.wechat_enabled_check.isChecked()
        
        # 只要用户填写了Webhook URL或启用了企业微信通知，就保存配置
        if wechat_webhook or wechat_enabled:
            data['notify_wechat'] = {
                'webhook': wechat_webhook,
                'enabled': wechat_enabled  # 记录企业微信通知启用状态
            }
        else:
            data['notify_wechat'] = {}

        return data





    def connect_tab_signals(self):
        """连接所有Tab选项的变化信号"""
        # 秒Tab
        self.second_option1.toggled.connect(self.update_cron_expression)
        self.second_option2.toggled.connect(self.update_cron_expression)
        self.second_option3.toggled.connect(self.update_cron_expression)
        self.second_option4.toggled.connect(self.update_cron_expression)
        self.second_start.valueChanged.connect(self.update_cron_expression)
        self.second_end.valueChanged.connect(self.update_cron_expression)
        self.second_from.valueChanged.connect(self.update_cron_expression)
        self.second_interval.valueChanged.connect(self.update_cron_expression)
        self.second_specific.currentTextChanged.connect(self.update_cron_expression)
        
        # 分钟Tab
        self.minute_option1.toggled.connect(self.update_cron_expression)
        self.minute_option2.toggled.connect(self.update_cron_expression)
        self.minute_option3.toggled.connect(self.update_cron_expression)
        self.minute_option4.toggled.connect(self.update_cron_expression)
        self.minute_start.valueChanged.connect(self.update_cron_expression)
        self.minute_end.valueChanged.connect(self.update_cron_expression)
        self.minute_from.valueChanged.connect(self.update_cron_expression)
        self.minute_interval.valueChanged.connect(self.update_cron_expression)
        self.minute_specific.currentTextChanged.connect(self.update_cron_expression)
        
        # 小时Tab
        self.hour_option1.toggled.connect(self.update_cron_expression)
        self.hour_option2.toggled.connect(self.update_cron_expression)
        self.hour_option3.toggled.connect(self.update_cron_expression)
        self.hour_option4.toggled.connect(self.update_cron_expression)
        self.hour_start.valueChanged.connect(self.update_cron_expression)
        self.hour_end.valueChanged.connect(self.update_cron_expression)
        self.hour_from.valueChanged.connect(self.update_cron_expression)
        self.hour_interval.valueChanged.connect(self.update_cron_expression)
        self.hour_specific.currentTextChanged.connect(self.update_cron_expression)
        
        # 日Tab
        self.day_option1.toggled.connect(self.update_cron_expression)
        self.day_option2.toggled.connect(self.update_cron_expression)
        self.day_option3.toggled.connect(self.update_cron_expression)
        self.day_option4.toggled.connect(self.update_cron_expression)
        self.day_option5.toggled.connect(self.update_cron_expression)
        self.day_option6.toggled.connect(self.update_cron_expression)
        self.day_start.valueChanged.connect(self.update_cron_expression)
        self.day_end.valueChanged.connect(self.update_cron_expression)
        self.day_from.valueChanged.connect(self.update_cron_expression)
        self.day_interval.valueChanged.connect(self.update_cron_expression)
        self.day_specific.currentTextChanged.connect(self.update_cron_expression)
        
        # 月Tab
        self.month_option1.toggled.connect(self.update_cron_expression)
        self.month_option2.toggled.connect(self.update_cron_expression)
        self.month_option3.toggled.connect(self.update_cron_expression)
        self.month_option4.toggled.connect(self.update_cron_expression)
        self.month_option5.toggled.connect(self.update_cron_expression)
        self.month_start.valueChanged.connect(self.update_cron_expression)
        self.month_end.valueChanged.connect(self.update_cron_expression)
        self.month_from.valueChanged.connect(self.update_cron_expression)
        self.month_interval.valueChanged.connect(self.update_cron_expression)
        self.month_specific.currentTextChanged.connect(self.update_cron_expression)
        
        # 周Tab
        self.week_option1.toggled.connect(self.update_cron_expression)
        self.week_option2.toggled.connect(self.update_cron_expression)
        self.week_option3.toggled.connect(self.update_cron_expression)
        self.week_option4.toggled.connect(self.update_cron_expression)
        self.week_option5.toggled.connect(self.update_cron_expression)
        self.week_option6.toggled.connect(self.update_cron_expression)
        self.week_start.currentTextChanged.connect(self.update_cron_expression)
        self.week_end.currentTextChanged.connect(self.update_cron_expression)
        self.week_which.valueChanged.connect(self.update_cron_expression)
        self.week_day.currentTextChanged.connect(self.update_cron_expression)
        self.week_last_day.currentTextChanged.connect(self.update_cron_expression)
        self.week_specific.currentTextChanged.connect(self.update_cron_expression)
        
        # 年Tab
        self.year_option1.toggled.connect(self.update_cron_expression)
        self.year_option2.toggled.connect(self.update_cron_expression)
        self.year_option3.toggled.connect(self.update_cron_expression)
        self.year_start.valueChanged.connect(self.update_cron_expression)
        self.year_end.valueChanged.connect(self.update_cron_expression)

    def update_cron_expression(self):
        """根据Tab选项实时生成Cron表达式并进行校验"""
        try:
            print("[DEBUG] ===== 开始生成Cron表达式 =====")
            
            # 获取各字段的Cron表达式部分
            second_part = self.get_second_cron()
            minute_part = self.get_minute_cron()
            hour_part = self.get_hour_cron()
            day_part = self.get_day_cron()
            month_part = self.get_month_cron()
            week_part = self.get_week_cron()
            year_part = self.get_year_cron()
            
            print(f"[DEBUG] 各字段值：")
            print(f"[DEBUG]   秒字段: {second_part}")
            print(f"[DEBUG]   分钟字段: {minute_part}")
            print(f"[DEBUG]   小时字段: {hour_part}")
            print(f"[DEBUG]   日字段: {day_part}")
            print(f"[DEBUG]   月字段: {month_part}")
            print(f"[DEBUG]   周字段: {week_part}")
            print(f"[DEBUG]   年字段: {year_part}")
            
            # 构建完整的Cron表达式
            cron_expr = f"{second_part} {minute_part} {hour_part} {day_part} {month_part} {week_part}"
            if year_part:
                cron_expr += f" {year_part}"
            
            print(f"[DEBUG] 生成的完整Cron表达式: {cron_expr}")
            
            # 校验Cron表达式
            is_valid, error_msg = self.validate_cron_expression(cron_expr)
            print(f"[DEBUG] Cron表达式校验结果: 有效={is_valid}, 错误信息={error_msg}")
            
            # 更新到输入框，如果无效则显示错误样式
            self.cron_edit.setText(cron_expr)
            if not is_valid:
                self.cron_edit.setStyleSheet("QLineEdit { border: 2px solid red; background-color: #fff0f0; }")
                # 可以添加错误提示，但避免频繁弹窗
                # QMessageBox.warning(self, "Cron表达式错误", error_msg)
            else:
                self.cron_edit.setStyleSheet("QLineEdit { border: 2px solid green; background-color: #f0fff0; }")
            
            print("[DEBUG] ===== Cron表达式生成完成 =====")
            
        except Exception as e:
            print(f"[ERROR] 生成Cron表达式错误: {str(e)}")
            self.cron_edit.setStyleSheet("QLineEdit { border: 2px solid red; background-color: #fff0f0; }")
    
    def parse_cron_to_tabs(self, cron_expr):
        """将cron表达式解析并回显到各个tab选项
        
        Args:
            cron_expr: cron表达式字符串
        """
        try:
            print(f"[DEBUG] ===== 开始解析Cron表达式: {cron_expr} =====")
            
            # 分割cron表达式为各个字段
            parts = cron_expr.strip().split()
            print(f"[DEBUG] 分割后的字段: {parts}, 字段数量: {len(parts)}")
            
            # 标准cron表达式有5-7个字段
            if len(parts) < 5 or len(parts) > 7:
                print(f"[DEBUG] 字段数量异常，跳过解析")
                return
            
            # 解析各个字段（秒、分钟、小时、日、月、周、年）
            if len(parts) == 6:
                # 6字段格式：秒 分钟 小时 日 月 周
                second_field = parts[0]
                minute_field = parts[1]
                hour_field = parts[2]
                day_field = parts[3]
                month_field = parts[4]
                week_field = parts[5]
                year_field = "*"
                print(f"[DEBUG] 识别为6字段格式:")
                print(f"[DEBUG]   秒字段: {second_field}")
                print(f"[DEBUG]   分钟字段: {minute_field}")
                print(f"[DEBUG]   小时字段: {hour_field}")
                print(f"[DEBUG]   日字段: {day_field}")
                print(f"[DEBUG]   月字段: {month_field}")
                print(f"[DEBUG]   周字段: {week_field}")
            elif len(parts) == 7:
                # 7字段格式：秒 分钟 小时 日 月 周 年
                second_field = parts[0]
                minute_field = parts[1]
                hour_field = parts[2]
                day_field = parts[3]
                month_field = parts[4]
                week_field = parts[5]
                year_field = parts[6]
                print(f"[DEBUG] 识别为7字段格式:")
                print(f"[DEBUG]   秒字段: {second_field}")
                print(f"[DEBUG]   分钟字段: {minute_field}")
                print(f"[DEBUG]   小时字段: {hour_field}")
                print(f"[DEBUG]   日字段: {day_field}")
                print(f"[DEBUG]   月字段: {month_field}")
                print(f"[DEBUG]   周字段: {week_field}")
                print(f"[DEBUG]   年字段: {year_field}")
            else:
                # 5字段格式：分钟 小时 日 月 周
                second_field = "*"
                minute_field = parts[0]
                hour_field = parts[1]
                day_field = parts[2]
                month_field = parts[3]
                week_field = parts[4]
                year_field = "*"
                print(f"[DEBUG] 识别为5字段格式:")
                print(f"[DEBUG]   秒字段: {second_field}")
                print(f"[DEBUG]   分钟字段: {minute_field}")
                print(f"[DEBUG]   小时字段: {hour_field}")
                print(f"[DEBUG]   日字段: {day_field}")
                print(f"[DEBUG]   月字段: {month_field}")
                print(f"[DEBUG]   周字段: {week_field}")
            
            print(f"[DEBUG] 开始回显到各个Tab...")
            
            # 回显到秒tab
            self._update_second_tab(second_field)
            
            # 回显到分钟tab
            self._update_minute_tab(minute_field)
            
            # 回显到小时tab
            self._update_hour_tab(hour_field)
            
            # 回显到日tab
            self._update_day_tab(day_field)
            
            # 回显到月tab
            self._update_month_tab(month_field)
            
            # 回显到周tab
            self._update_week_tab(week_field)
            
            # 回显到年tab
            self._update_year_tab(year_field)
            
            print(f"[DEBUG] ===== Cron表达式解析完成 =====")
            
            # 解析完成后立即更新Cron表达式显示
            self.update_cron_expression()
            
        except Exception as e:
            print(f"[ERROR] 解析cron表达式失败: {e}")

    def _update_second_tab(self, second_field):
        """更新秒tab选项"""
        # 临时断开信号连接，避免递归调用
        try:
            self.second_start.valueChanged.disconnect(self.update_cron_expression)
            self.second_end.valueChanged.disconnect(self.update_cron_expression)
            self.second_from.valueChanged.disconnect(self.update_cron_expression)
            self.second_interval.valueChanged.disconnect(self.update_cron_expression)
            self.second_specific.currentTextChanged.disconnect(self.update_cron_expression)
        except:
            pass
        
        try:
            if second_field == "*":
                # 每秒执行
                self.second_option1.setChecked(True)
            elif "/" in second_field:
                # 间隔执行（从X秒开始，每Y秒执行一次）
                self.second_option3.setChecked(True)
                try:
                    start, step = second_field.split("/")
                    self.second_from.setValue(int(start))
                    self.second_interval.setValue(int(step))
                except:
                    pass
            elif "-" in second_field:
                # 周期执行（从X秒到Y秒）
                self.second_option2.setChecked(True)
                try:
                    start, end = second_field.split("-")
                    self.second_start.setValue(int(start))
                    self.second_end.setValue(int(end))
                except:
                    pass
            elif second_field.isdigit():
                # 指定秒数
                self.second_option4.setChecked(True)
                self.second_specific.setCurrentText(second_field)
            else:
                # 其他情况，保持当前选择
                pass
        finally:
            # 重新连接信号
            try:
                self.second_start.valueChanged.connect(self.update_cron_expression)
                self.second_end.valueChanged.connect(self.update_cron_expression)
                self.second_from.valueChanged.connect(self.update_cron_expression)
                self.second_interval.valueChanged.connect(self.update_cron_expression)
                self.second_specific.currentTextChanged.connect(self.update_cron_expression)
            except:
                pass

    def _update_minute_tab(self, minute_field):
        """更新分钟tab选项"""
        # 临时断开信号连接，避免递归调用
        try:
            self.minute_start.valueChanged.disconnect(self.update_cron_expression)
            self.minute_end.valueChanged.disconnect(self.update_cron_expression)
            self.minute_from.valueChanged.disconnect(self.update_cron_expression)
            self.minute_interval.valueChanged.disconnect(self.update_cron_expression)
            self.minute_specific.currentTextChanged.disconnect(self.update_cron_expression)
        except:
            pass
        
        try:
            if minute_field == "*":
                # 每分钟执行
                self.minute_option1.setChecked(True)
            elif "/" in minute_field:
                # 间隔执行（从X分钟开始，每Y分钟执行一次）
                self.minute_option3.setChecked(True)
                try:
                    start, step = minute_field.split("/")
                    self.minute_from.setValue(int(start))
                    self.minute_interval.setValue(int(step))
                except:
                    pass
            elif "-" in minute_field:
                # 周期执行（从X分钟到Y分钟）
                self.minute_option2.setChecked(True)
                try:
                    start, end = minute_field.split("-")
                    self.minute_start.setValue(int(start))
                    self.minute_end.setValue(int(end))
                except:
                    pass
            elif minute_field.isdigit():
                # 指定分钟数
                self.minute_option4.setChecked(True)
                self.minute_specific.setCurrentText(minute_field)
            else:
                # 其他情况，保持当前选择
                pass
        finally:
            # 重新连接信号
            try:
                self.minute_start.valueChanged.connect(self.update_cron_expression)
                self.minute_end.valueChanged.connect(self.update_cron_expression)
                self.minute_from.valueChanged.connect(self.update_cron_expression)
                self.minute_interval.valueChanged.connect(self.update_cron_expression)
                self.minute_specific.currentTextChanged.connect(self.update_cron_expression)
            except:
                pass

    def _update_hour_tab(self, hour_field):
        """更新小时tab选项"""
        # 临时断开信号连接，避免递归调用
        try:
            self.hour_start.valueChanged.disconnect(self.update_cron_expression)
            self.hour_end.valueChanged.disconnect(self.update_cron_expression)
            self.hour_from.valueChanged.disconnect(self.update_cron_expression)
            self.hour_interval.valueChanged.disconnect(self.update_cron_expression)
            self.hour_specific.currentTextChanged.disconnect(self.update_cron_expression)
        except:
            pass
        
        try:
            if hour_field == "*":
                # 每小时执行
                self.hour_option1.setChecked(True)
            elif "/" in hour_field:
                # 间隔执行（从X小时开始，每Y小时执行一次）
                self.hour_option3.setChecked(True)
                try:
                    start, step = hour_field.split("/")
                    self.hour_from.setValue(int(start))
                    self.hour_interval.setValue(int(step))
                except:
                    pass
            elif "-" in hour_field:
                # 周期执行（从X小时到Y小时）
                self.hour_option2.setChecked(True)
                try:
                    start, end = hour_field.split("-")
                    self.hour_start.setValue(int(start))
                    self.hour_end.setValue(int(end))
                except:
                    pass
            elif hour_field.isdigit():
                # 指定小时数
                self.hour_option4.setChecked(True)
                self.hour_specific.setCurrentText(hour_field)
            else:
                # 其他情况，保持当前选择
                pass
        finally:
            # 重新连接信号
            try:
                self.hour_start.valueChanged.connect(self.update_cron_expression)
                self.hour_end.valueChanged.connect(self.update_cron_expression)
                self.hour_from.valueChanged.connect(self.update_cron_expression)
                self.hour_interval.valueChanged.connect(self.update_cron_expression)
                self.hour_specific.currentTextChanged.connect(self.update_cron_expression)
            except:
                pass

    def _update_day_tab(self, day_field):
        """更新日tab选项"""
        # 临时断开信号连接，避免递归调用
        try:
            self.day_start.valueChanged.disconnect(self.update_cron_expression)
            self.day_end.valueChanged.disconnect(self.update_cron_expression)
            self.day_from.valueChanged.disconnect(self.update_cron_expression)
            self.day_interval.valueChanged.disconnect(self.update_cron_expression)
            self.day_specific.currentTextChanged.disconnect(self.update_cron_expression)
        except:
            pass
        
        try:
            if day_field == "*":
                # 每日执行
                self.day_option1.setChecked(True)
            elif "/" in day_field:
                # 间隔执行（从X日开始，每Y日执行一次）
                self.day_option4.setChecked(True)
                try:
                    start, step = day_field.split("/")
                    self.day_from.setValue(int(start))
                    self.day_interval.setValue(int(step))
                except:
                    pass
            elif "-" in day_field:
                # 周期执行（从X日到Y日）
                self.day_option3.setChecked(True)
                try:
                    start, end = day_field.split("-")
                    self.day_start.setValue(int(start))
                    self.day_end.setValue(int(end))
                except:
                    pass
            elif day_field.isdigit():
                # 指定日期
                self.day_option6.setChecked(True)
                self.day_specific.setCurrentText(day_field)
            else:
                # 其他情况，保持当前选择
                pass
        finally:
            # 重新连接信号
            try:
                self.day_start.valueChanged.connect(self.update_cron_expression)
                self.day_end.valueChanged.connect(self.update_cron_expression)
                self.day_from.valueChanged.connect(self.update_cron_expression)
                self.day_interval.valueChanged.connect(self.update_cron_expression)
                self.day_specific.currentTextChanged.connect(self.update_cron_expression)
            except:
                pass

    def _update_month_tab(self, month_field):
        """更新月tab选项"""
        # 临时断开信号连接，避免递归调用
        try:
            self.month_start.valueChanged.disconnect(self.update_cron_expression)
            self.month_end.valueChanged.disconnect(self.update_cron_expression)
            self.month_from.valueChanged.disconnect(self.update_cron_expression)
            self.month_interval.valueChanged.disconnect(self.update_cron_expression)
            self.month_specific.currentTextChanged.disconnect(self.update_cron_expression)
        except:
            pass
        
        try:
            if month_field == "*":
                # 每月执行
                self.month_option1.setChecked(True)
            elif "/" in month_field:
                # 间隔执行（从X月开始，每Y月执行一次）
                self.month_option4.setChecked(True)
                try:
                    start, step = month_field.split("/")
                    self.month_from.setValue(int(start))
                    self.month_interval.setValue(int(step))
                except:
                    pass
            elif "-" in month_field:
                # 周期执行（从X月到Y月）
                self.month_option3.setChecked(True)
                try:
                    start, end = month_field.split("-")
                    self.month_start.setValue(int(start))
                    self.month_end.setValue(int(end))
                except:
                    pass
            elif month_field.isdigit():
                # 指定月份
                self.month_option5.setChecked(True)
                self.month_specific.setCurrentText(month_field)
            else:
                # 其他情况，保持当前选择
                pass
        finally:
            # 重新连接信号
            try:
                self.month_start.valueChanged.connect(self.update_cron_expression)
                self.month_end.valueChanged.connect(self.update_cron_expression)
                self.month_from.valueChanged.connect(self.update_cron_expression)
                self.month_interval.valueChanged.connect(self.update_cron_expression)
                self.month_specific.currentTextChanged.connect(self.update_cron_expression)
            except:
                pass

    def _update_week_tab(self, week_field):
        """更新周tab选项"""
        # 临时断开信号连接，避免递归调用
        try:
            self.week_start.currentTextChanged.disconnect(self.update_cron_expression)
            self.week_end.currentTextChanged.disconnect(self.update_cron_expression)
            self.week_from.valueChanged.disconnect(self.update_cron_expression)
            self.week_specific.currentTextChanged.disconnect(self.update_cron_expression)
        except:
            pass
        
        try:
            print(f"[DEBUG] 更新周字段Tab，传入的周字段值: {week_field}")
            
            if week_field == "*":
                # 每周执行
                print(f"[DEBUG] 周字段为'*'，设置选项1")
                self.week_option1.setChecked(True)
            elif week_field == "?":
                # 不指定周（当日字段被指定时）
                print(f"[DEBUG] 周字段为'?'，设置选项2")
                self.week_option2.setChecked(True)
            elif "/" in week_field:
                # 周期执行
                print(f"[DEBUG] 周字段包含'/'，设置选项3")
                self.week_option3.setChecked(True)
                try:
                    _, step = week_field.split("/")
                    self.week_start.setCurrentText("周一")
                    self.week_end.setCurrentText("周日")
                    self.week_step.setValue(int(step))
                except:
                    pass
            elif "-" in week_field:
                # 间隔执行
                print(f"[DEBUG] 周字段包含'-'，设置选项4")
                self.week_option4.setChecked(True)
                try:
                    start, end = week_field.split("-")
                    self.week_from.setValue(int(start))
                    self.week_to.setValue(int(end))
                except:
                    pass
            elif week_field.isdigit():
                # 指定星期
                print(f"[DEBUG] 周字段为数字，设置选项6")
                self.week_option6.setChecked(True)
                # 将数字转换为星期名称
                day_mapping = {"0": "周一", "1": "周二", "2": "周三", "3": "周四", 
                              "4": "周五", "5": "周六", "6": "周日"}
                if week_field in day_mapping:
                    self.week_specific.setCurrentText(day_mapping[week_field])
            else:
                # 其他情况，保持当前选择
                print(f"[DEBUG] 周字段为其他值: {week_field}，保持当前选择")
                pass
        finally:
            # 重新连接信号
            try:
                self.week_start.currentTextChanged.connect(self.update_cron_expression)
                self.week_end.currentTextChanged.connect(self.update_cron_expression)
                self.week_from.valueChanged.connect(self.update_cron_expression)
                self.week_specific.currentTextChanged.connect(self.update_cron_expression)
            except:
                pass

    def _update_year_tab(self, year_field):
        """更新年tab选项"""
        # 临时断开信号连接，避免递归调用
        try:
            self.year_start.valueChanged.disconnect(self.update_cron_expression)
            self.year_end.valueChanged.disconnect(self.update_cron_expression)
            self.year_from.valueChanged.disconnect(self.update_cron_expression)
            self.year_specific.currentTextChanged.disconnect(self.update_cron_expression)
        except:
            pass
        
        try:
            if year_field == "*":
                # 每年执行
                self.year_option1.setChecked(True)
            elif "/" in year_field:
                # 周期执行
                self.year_option3.setChecked(True)
                try:
                    _, step = year_field.split("/")
                    self.year_start.setText("2024")
                    self.year_end.setText("2030")
                    self.year_step.setText(step)
                except:
                    pass
            elif "-" in year_field:
                # 间隔执行
                self.year_option4.setChecked(True)
                try:
                    start, end = year_field.split("-")
                    self.year_from.setText(start)
                    self.year_to.setText(end)
                except:
                    pass
            elif year_field.isdigit():
                # 指定年份
                self.year_option5.setChecked(True)
                self.year_specific.setCurrentText(year_field)
            else:
                # 其他情况，保持当前选择
                pass
        finally:
            # 重新连接信号
            try:
                self.year_start.valueChanged.connect(self.update_cron_expression)
                self.year_end.valueChanged.connect(self.update_cron_expression)
                self.year_from.valueChanged.connect(self.update_cron_expression)
                self.year_specific.currentTextChanged.connect(self.update_cron_expression)
            except:
                pass

    def validate_cron_expression(self, cron_expression):
        """校验Cron表达式是否符合标准格式"""
        try:
            # 分割表达式
            parts = cron_expression.strip().split()
            
            # 检查字段数量（6或7个字段）
            if len(parts) not in [6, 7]:
                return False, f"Cron表达式应包含6或7个字段，当前有{len(parts)}个"
            
            # 校验每个字段
            field_names = ["秒", "分钟", "小时", "日", "月", "周"]
            if len(parts) == 7:
                field_names.append("年")
            
            for i, (field_name, part) in enumerate(zip(field_names, parts)):
                if not self.validate_cron_field(part, i):
                    return False, f"{field_name}字段格式错误: {part}"
            
            # 检查日和周的冲突（不能同时指定日和周）
            if len(parts) >= 6:
                day_field = parts[3]  # 第4个字段是日
                week_field = parts[5]  # 第6个字段是周
                
                # 正确的日周互斥逻辑：如果日字段不是?，周字段必须是?；如果周字段不是?，日字段必须是?
                if day_field != "?" and week_field != "?":
                    return False, "日和周字段不能同时指定，其中一个必须为?"
                # 注意：日和周字段可以同时为?，这是允许的
            
            return True, "表达式格式正确"
            
        except Exception as e:
            return False, f"校验过程中出错: {str(e)}"
    
    def validate_cron_input(self, text):
        """实时校验cron表达式输入"""
        # 检查是否正在解析cron表达式，避免递归调用
        if hasattr(self, '_parsing_cron') and self._parsing_cron:
            return
            
        if not text.strip():
            # 空输入时重置样式和提示
            self.cron_edit.setStyleSheet("""
                QLineEdit {
                    padding: 8px 12px;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    background-color: white;
                    font-size: 14px;
                }
                QLineEdit:focus {
                    border-color: #0078d4;
                    outline: none;
                }
            """)
            self.cron_validation_label.setText("")
            self.cron_validation_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    padding: 4px 8px;
                    border-radius: 4px;
                    margin-top: 5px;
                }
            """)
            return
        
        # 校验cron表达式
        is_valid, error_msg = self.validate_cron_expression(text)
        
        if is_valid:
            # 校验通过，显示绿色提示
            self.cron_edit.setStyleSheet("""
                QLineEdit {
                    padding: 8px 12px;
                    border: 2px solid #28a745;
                    border-radius: 6px;
                    background-color: #f8fff9;
                    font-size: 14px;
                }
                QLineEdit:focus {
                    border-color: #28a745;
                    outline: none;
                }
            """)
            self.cron_validation_label.setText("✓ 表达式格式正确")
            self.cron_validation_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    padding: 4px 8px;
                    border-radius: 4px;
                    margin-top: 5px;
                    color: #155724;
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                }
            """)
            # 校验通过后，将表达式回显到各个tab选项
            self._parsing_cron = True
            try:
                self.parse_cron_to_tabs(text)
            finally:
                self._parsing_cron = False
        else:
            # 校验失败，显示红色错误提示
            self.cron_edit.setStyleSheet("""
                QLineEdit {
                    padding: 8px 12px;
                    border: 2px solid #dc3545;
                    border-radius: 6px;
                    background-color: #fff0f0;
                    font-size: 14px;
                }
                QLineEdit:focus {
                    border-color: #dc3545;
                    outline: none;
                }
            """)
            self.cron_validation_label.setText(f"✗ {error_msg}")
            self.cron_validation_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    padding: 4px 8px;
                    border-radius: 4px;
                    margin-top: 5px;
                    color: #721c24;
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                }
            """)
    
    def validate_cron_field(self, field, field_index):
        """校验单个Cron字段"""
        # 空字段
        if not field:
            return False
        
        # 通配符
        if field == "*" or field == "?":
            return True
        
        # 检查数字范围
        if field.isdigit():
            value = int(field)
            return self.check_field_range(value, field_index)
        
        # 检查范围表达式 (如 1-5)
        if "-" in field:
            parts = field.split("-")
            if len(parts) != 2:
                return False
            if not parts[0].isdigit() or not parts[1].isdigit():
                return False
            start, end = int(parts[0]), int(parts[1])
            if not (self.check_field_range(start, field_index) and self.check_field_range(end, field_index)):
                return False
            if start > end:
                return False
            return True
        
        # 检查步长表达式 (如 */5 或 1/2)
        if "/" in field:
            if field.startswith("*/"):
                step_part = field[2:]
                if not step_part.isdigit():
                    return False
                step = int(step_part)
                return step > 0 and self.check_field_range(step, field_index)
            else:
                parts = field.split("/")
                if len(parts) != 2:
                    return False
                if not parts[0].isdigit() or not parts[1].isdigit():
                    return False
                base, step = int(parts[0]), int(parts[1])
                if not (self.check_field_range(base, field_index) and self.check_field_range(step, field_index)):
                    return False
                return step > 0
        
        # 检查列表表达式 (如 1,3,5)
        if "," in field:
            parts = field.split(",")
            for part in parts:
                if not part.isdigit():
                    return False
                value = int(part)
                if not self.check_field_range(value, field_index):
                    return False
            return True
        
        # 检查特殊字符（周字段的特殊格式）
        if field_index == 5:  # 周字段
            if "#" in field:
                parts = field.split("#")
                if len(parts) != 2:
                    return False
                if not parts[0].isdigit() or not parts[1].isdigit():
                    return False
                day, week_num = int(parts[0]), int(parts[1])
                if not (0 <= day <= 6 and 1 <= week_num <= 5):
                    return False
                return True
            if field.endswith("L"):
                day_part = field[:-1]
                if not day_part.isdigit():
                    return False
                day = int(day_part)
                return 0 <= day <= 6
        
        # 检查日字段的特殊字符
        if field_index == 3:  # 日字段
            if field == "L":
                return True
            if field.endswith("W"):
                day_part = field[:-1]
                if not day_part.isdigit():
                    return False
                day = int(day_part)
                return 1 <= day <= 31
        
        return False
    
    def check_field_range(self, value, field_index):
        """检查字段值是否在有效范围内"""
        ranges = [
            (0, 59),   # 秒
            (0, 59),   # 分钟
            (0, 23),   # 小时
            (1, 31),   # 日
            (1, 12),   # 月
            (0, 6),    # 周（0=周日，6=周六）
            (1970, 2099)  # 年
        ]
        
        if field_index < len(ranges):
            min_val, max_val = ranges[field_index]
            return min_val <= value <= max_val
        
        return False

    def get_second_cron(self):
        """获取秒字段的Cron表达式"""
        if self.second_option1.isChecked():
            return "*"
        elif self.second_option2.isChecked():
            return f"{self.second_start.value()}-{self.second_end.value()}"
        elif self.second_option3.isChecked():
            return f"{self.second_from.value()}/{self.second_interval.value()}"
        elif self.second_option4.isChecked():
            return self.second_specific.currentText()
        return "*"

    def get_minute_cron(self):
        """获取分钟字段的Cron表达式"""
        if self.minute_option1.isChecked():
            return "*"
        elif self.minute_option2.isChecked():
            return f"{self.minute_start.value()}-{self.minute_end.value()}"
        elif self.minute_option3.isChecked():
            from_val = self.minute_from.value()
            interval_val = self.minute_interval.value()
            print(f"[DEBUG] 分钟字段：选项3被选中，开始值={from_val}, 间隔值={interval_val}")
            return f"{from_val}/{interval_val}"
        elif self.minute_option4.isChecked():
            return self.minute_specific.currentText()
        return "*"

    def get_hour_cron(self):
        """获取小时字段的Cron表达式"""
        if self.hour_option1.isChecked():
            return "*"
        elif self.hour_option2.isChecked():
            return f"{self.hour_start.value()}-{self.hour_end.value()}"
        elif self.hour_option3.isChecked():
            return f"{self.hour_from.value()}/{self.hour_interval.value()}"
        elif self.hour_option4.isChecked():
            return self.hour_specific.currentText()
        return "*"

    def get_day_cron(self):
        """获取日字段的Cron表达式"""
        # 正确的日周互斥逻辑：如果周字段被指定了具体值（不是"*"或"?"），日字段应该为"?"
        # 避免递归调用，直接检查周字段的选项状态
        if self.week_option3.isChecked() or self.week_option4.isChecked() or self.week_option5.isChecked() or self.week_option6.isChecked():
            print(f"[DEBUG] 日字段：周字段被指定了具体值，日字段返回'?'")
            return "?"
        
        if self.day_option1.isChecked():
            print(f"[DEBUG] 日字段：选项1被选中，返回'*'")
            return "*"
        elif self.day_option2.isChecked():
            print(f"[DEBUG] 日字段：选项2被选中，返回'?'")
            return "?"
        elif self.day_option3.isChecked():
            result = f"{self.day_start.value()}-{self.day_end.value()}"
            print(f"[DEBUG] 日字段：选项3被选中，返回'{result}'")
            return result
        elif self.day_option4.isChecked():
            result = f"{self.day_from.value()}/{self.day_interval.value()}"
            print(f"[DEBUG] 日字段：选项4被选中，返回'{result}'")
            return result
        elif self.day_option5.isChecked():
            print(f"[DEBUG] 日字段：选项5被选中，返回'L'")
            return "L"
        elif self.day_option6.isChecked():
            result = self.day_specific.currentText()
            print(f"[DEBUG] 日字段：选项6被选中，返回'{result}'")
            return result
        print(f"[DEBUG] 日字段：没有选项被选中，默认返回'?'")
        return "?"

    def get_month_cron(self):
        """获取月字段的Cron表达式"""
        if self.month_option1.isChecked():
            return "*"
        elif self.month_option2.isChecked():
            return "?"
        elif self.month_option3.isChecked():
            return f"{self.month_start.value()}-{self.month_end.value()}"
        elif self.month_option4.isChecked():
            return f"{self.month_from.value()}/{self.month_interval.value()}"
        elif self.month_option5.isChecked():
            return self.month_specific.currentText()
        return "*"

    def get_week_cron(self):
        """获取周字段的Cron表达式"""
        # 正确的日周互斥逻辑：如果日字段被指定了具体值（不是"*"或"?"），周字段应该为"?"
        # 避免递归调用，直接检查日字段的选项状态
        if self.day_option3.isChecked() or self.day_option4.isChecked() or self.day_option5.isChecked() or self.day_option6.isChecked():
            print(f"[DEBUG] 周字段：日字段被指定了具体值，周字段返回'?'")
            return "?"
        
        if self.week_option1.isChecked():
            print(f"[DEBUG] 周字段：选项1被选中，返回'*'")
            return "*"
        elif self.week_option2.isChecked():
            print(f"[DEBUG] 周字段：选项2被选中，返回'?'")
            return "?"
        elif self.week_option3.isChecked():
            # 周期从周X到周Y，转换为数字格式（0=周日，6=周六）
            week_days = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
            # 正确的Cron映射：周日=0, 周一=1, 周二=2, 周三=3, 周四=4, 周五=5, 周六=6
            day_mapping = {"周日": 0, "周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5, "周六": 6}
            start_idx = day_mapping[self.week_start.currentText()]
            end_idx = day_mapping[self.week_end.currentText()]
            result = f"{start_idx}-{end_idx}"
            print(f"[DEBUG] 周字段：选项3被选中，返回'{result}'")
            return result
        elif self.week_option4.isChecked():
            # 第X周的周X，转换为数字格式
            week_days = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
            day_mapping = {"周日": 0, "周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5, "周六": 6}
            day_idx = day_mapping[self.week_day.currentText()]
            result = f"{day_idx}#{self.week_which.value()}"
            print(f"[DEBUG] 周字段：选项4被选中，返回'{result}'")
            return result
        elif self.week_option5.isChecked():
            # 本月最后一个周X，转换为数字格式
            week_days = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
            day_mapping = {"周日": 0, "周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5, "周六": 6}
            day_idx = day_mapping[self.week_last_day.currentText()]
            result = f"{day_idx}L"
            print(f"[DEBUG] 周字段：选项5被选中，返回'{result}'")
            return result
        elif self.week_option6.isChecked():
            # 指定星期，转换为数字格式
            week_days = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
            day_mapping = {"周日": 0, "周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5, "周六": 6}
            day_idx = day_mapping[self.week_specific.currentText()]
            result = str(day_idx)
            print(f"[DEBUG] 周字段：选项6被选中，返回'{result}'")
            return result
        print(f"[DEBUG] 周字段：没有选项被选中，默认返回'?'")
        return "?"

    def get_year_cron(self):
        """获取年字段的Cron表达式"""
        if self.year_option1.isChecked():
            return ""
        elif self.year_option2.isChecked():
            return "?"
        elif self.year_option3.isChecked():
            return f"{self.year_start.value()}-{self.year_end.value()}"
        return ""

    
    def update_next_runs_display(self, next_runs):
        """更新最近5次运行时间显示"""
        if not next_runs:
            self.next_runs_text.setPlainText("无法计算运行时间")
            return
        
        # 格式化时间显示
        time_text = ""
        for i, run_time in enumerate(next_runs, 1):
            time_text += f"{run_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        self.next_runs_text.setPlainText(time_text.strip())


class SchedulerManager(QWidget):
    """调度管理页面"""
    data_changed = pyqtSignal()  # 数据变化信号
    report_detail_requested = pyqtSignal(dict)  # 报告详情请求信号，传递报告数据
    report_tab_requested = pyqtSignal(dict)  # 测试报告tab跳转请求信号，传递调度和报告数据

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.scheduler_service = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_next_run_times)
        self.timer.start(60000)  # 每分钟更新一次
        self.execution_status = {}  # 执行状态监控
        self.current_business_id = None  # 当前选中的业务分组ID
        
        # 分页相关变量初始化
        self.current_page = 1
        self.current_page_size = 20
        self.total_pages = 0
        self.total_records = 0
        
        self.init_ui()
        # 延迟加载数据，避免启动时数据库连接失败导致弹窗
        QTimer.singleShot(100, self.delayed_load_data)
        # 启动调度服务
        self.start_service()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 工具栏
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))

        # 项目选择下拉框
        project_label = QLabel("项目:")
        project_label.setStyleSheet("color: #333; font-weight: bold; margin-left: 5px; margin-right: 5px;")
        toolbar.addWidget(project_label)
        
        self.project_combo = NoWheelComboBox()
        self.project_combo.setMinimumWidth(150)
        self.project_combo.setStyleSheet(get_combobox_style())
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        toolbar.addWidget(self.project_combo)
        
        toolbar.addSeparator()

        self.add_action = QAction("新增调度", self)
        self.add_action.triggered.connect(self.add_scheduler)
        self.add_action.setIcon(self.get_icon("add.png"))

        self.refresh_action = QAction("刷新", self)
        self.refresh_action.triggered.connect(lambda: self.load_schedulers(self.project_combo.currentData()))
        self.refresh_action.setIcon(self.get_icon("refresh.png"))

        toolbar.addAction(self.add_action)
        toolbar.addSeparator()
        toolbar.addAction(self.refresh_action)

        main_layout.addWidget(toolbar)

        # 调度列表树形控件
        self.tree_widget = QTreeWidget()
        self.tree_widget.setColumnCount(10)
        self.tree_widget.setHeaderLabels([
            "序号", "调度名称", "状态", "Cron表达式", "用例数量", "上次执行", "下次执行", "创建时间", "更新时间", "操作"
        ])
        
        # 设置固定列宽 - 参考测试报告列表设计
        self.tree_widget.setColumnWidth(0, 80)     # 序号
        self.tree_widget.setColumnWidth(1, 450)    # 调度名称
        self.tree_widget.setColumnWidth(2, 80)    # 状态
        self.tree_widget.setColumnWidth(3, 200)    # Cron表达式
        self.tree_widget.setColumnWidth(4, 100)    # 用例数量
        self.tree_widget.setColumnWidth(5, 250)    # 上次执行
        self.tree_widget.setColumnWidth(6, 250)    # 下次执行
        self.tree_widget.setColumnWidth(7, 250)    # 创建时间
        self.tree_widget.setColumnWidth(8, 250)    # 更新时间
        
        # 设置列宽调整模式 - 操作栏自适应拉伸
        header = self.tree_widget.header()
        header.setSectionResizeMode(QHeaderView.Fixed)  # 其他列固定宽度
        header.setSectionResizeMode(9, QHeaderView.Stretch)  # 操作栏自适应拉伸
        header.setStretchLastSection(True)  # 最后一列自动拉伸
        header.setSectionsMovable(False)  # 禁止表头拖拽
        header.setDefaultAlignment(Qt.AlignCenter)  # 表头文本居中
        
        # 设置树形控件属性
        self.tree_widget.setSelectionBehavior(QTreeWidget.SelectRows)
        self.tree_widget.setContextMenuPolicy(Qt.NoContextMenu)  # 禁用右键菜单
        self.tree_widget.setRootIsDecorated(False)  # 不显示展开/折叠图标列
        self.tree_widget.setAlternatingRowColors(True)
        
        # 设置所有列文本居中
        for i in range(self.tree_widget.columnCount()):
            self.tree_widget.headerItem().setTextAlignment(i, Qt.AlignCenter)
        
        # 参考测试报告列表的树形控件样式美化
        self.tree_widget.setStyleSheet("""
            QTreeWidget {
                background-color: #f8f9fa;
                alternate-background-color: #ffffff;
                gridline-color: #e9ecef;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                outline: 0;
            }
            QTreeWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #e9ecef;
                text-align: center;
                height: 32px;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
                font-weight: bold;
            }
            QTreeWidget::item:selected:!active {
                background-color: #e3f2fd;
                color: #1976d2;
                font-weight: bold;
            }
            QTreeWidget::item:hover {
                background-color: #f8f9fa;
            }
            QTreeWidget::item:has-children {
                background-color: #f1f3f4;
                font-weight: bold;
            }
            QTreeWidget::item:has-children:hover {
                background-color: #e8eaed;
            }
            QTreeWidget::branch:has-siblings:!adjoins-item {
                border-image: url(vline.png) 0;
            }
            QTreeWidget::branch:has-siblings:adjoins-item {
                border-image: url(branch-more.png) 0;
            }
            QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {
                border-image: url(branch-end.png) 0;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                border-image: none;
                image: url(branch-closed.png);
            }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                border-image: none;
                image: url(branch-open.png);
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #495057;
                font-weight: 600;
                font-size: 13px;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid #1976d2;
                min-height: 25px;
                text-align: center;
            }
            QHeaderView::section:hover {
                background-color: #e9ecef;
            }
        """)
        self.tree_widget.setMinimumHeight(400)  # 增加控件高度

        main_layout.addWidget(self.tree_widget)

        # 分页控件
        self.pagination_widget = QWidget()
        pagination_layout = QHBoxLayout(self.pagination_widget)
        pagination_layout.setContentsMargins(10, 5, 10, 5)
        pagination_layout.setSpacing(10)
        
        # 分页信息标签
        self.pagination_label = QLabel("共 0 条记录")
        self.pagination_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        pagination_layout.addWidget(self.pagination_label)
        
        pagination_layout.addStretch()
        
        # 首页按钮
        self.first_page_btn = QPushButton("« 首页")
        self.first_page_btn.setFixedSize(70, 32)
        self.first_page_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border-radius: 6px;
                padding: 6px 8px;
                font-size: 12px;
                font-weight: 500;
                color: #495057;
                margin: 1px;
            }
            QPushButton:hover:enabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007bff, stop:1 #0056b3);
                color: white;
                border: 1px solid #007bff;
            }
            QPushButton:pressed:enabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0056b3, stop:1 #004085);
                border: 1px solid #004085;
            }
            QPushButton:disabled {
                background: #f8f9fa;
                color: #adb5bd;
            }
        """)
        pagination_layout.addWidget(self.first_page_btn)
        
        # 上一页按钮
        self.prev_page_btn = QPushButton("‹ 上一页")
        self.prev_page_btn.setFixedSize(70, 32)
        self.prev_page_btn.setStyleSheet(self.first_page_btn.styleSheet())
        pagination_layout.addWidget(self.prev_page_btn)
        
        # 页码输入框
        self.page_input = QLineEdit()
        self.page_input.setFixedSize(50, 32)
        self.page_input.setAlignment(Qt.AlignCenter)
        self.page_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
                background-color: #ffffff;
                font-weight: 500;
                margin: 1px;
            }
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
                border-width: 2px;
            }
            QLineEdit:hover:enabled {
                border-color: #adb5bd;
            }
        """)
        pagination_layout.addWidget(self.page_input)
        
        # 总页数标签
        self.total_pages_label = QLabel("/ 0")
        self.total_pages_label.setStyleSheet("color: #6c757d; font-size: 12px; font-weight: 500; margin: 0 4px;")
        pagination_layout.addWidget(self.total_pages_label)
        
        # 下一页按钮
        self.next_page_btn = QPushButton("下一页 ›")
        self.next_page_btn.setFixedSize(70, 32)
        self.next_page_btn.setStyleSheet(self.first_page_btn.styleSheet())
        pagination_layout.addWidget(self.next_page_btn)
        
        # 末页按钮
        self.last_page_btn = QPushButton("末页 »")
        self.last_page_btn.setFixedSize(70, 32)
        self.last_page_btn.setStyleSheet(self.first_page_btn.styleSheet())
        pagination_layout.addWidget(self.last_page_btn)
        
        # 每页显示数量选择
        self.page_size_combo = QComboBox()
        self.page_size_combo.setFixedSize(85, 32)
        self.page_size_combo.addItems(["10", "20", "50", "100"])
        self.page_size_combo.setStyleSheet(get_combobox_style())
        self.page_size_combo.setCurrentText("20")
        pagination_layout.addWidget(self.page_size_combo)
        
        main_layout.addWidget(self.pagination_widget)

        # 连接分页控件信号
        self.first_page_btn.clicked.connect(self.go_to_first_page)
        self.prev_page_btn.clicked.connect(self.go_to_prev_page)
        self.next_page_btn.clicked.connect(self.go_to_next_page)
        self.last_page_btn.clicked.connect(self.go_to_last_page)
        self.page_input.returnPressed.connect(self.go_to_specific_page)
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)

    def delayed_load_data(self):
        """延迟加载数据，避免启动时数据库连接失败导致弹窗"""
        try:
            # 初始化服务对象
            self.scheduler_service = UnifiedSchedulerService()
            # 加载项目列表（初始不按业务过滤）
            self.load_projects()
            # 加载数据 - 根据当前选中的项目进行过滤
            project_id = self.project_combo.currentData() if self.project_combo.count() > 0 else None
            self.load_schedulers(project_id)
        except Exception as e:
            # 静默处理，不显示弹窗
            print(f"延迟加载数据失败: {str(e)}")

    def load_projects(self, business_id=None):
        """加载项目列表到下拉框，支持按业务分组过滤"""
        try:
            # 清空下拉框
            self.project_combo.clear()
            
            # 获取项目列表
            project_service = ProjectService()
            
            # 根据业务分组ID过滤项目
            if business_id is not None:
                projects = project_service.get_projects_by_group(business_id)
            else:
                projects = project_service.get_all_projects()
            
            # 添加项目到下拉框
            for project in projects:
                self.project_combo.addItem(project['name'], project['id'])
                
            # 设置默认选中第一个项目
            if projects:
                self.project_combo.setCurrentIndex(0)
            
        except Exception as e:
            print(f"加载项目列表失败: {str(e)}")
            # 添加一个错误提示选项
            self.project_combo.addItem("加载失败", None)

    def on_business_changed(self, business_id):
        """业务切换事件处理"""
        self.current_business_id = business_id
        # 重新加载项目列表，按业务分组过滤
        self.load_projects(business_id)
        # 重新加载调度列表
        project_id = self.project_combo.currentData() if self.project_combo.count() > 0 else None
        self.load_schedulers(project_id)

    def on_project_changed(self):
        """项目选择变更事件"""
        # 获取当前选中的项目ID
        project_id = self.project_combo.currentData()
        
        # 根据项目ID筛选调度列表
        self.load_schedulers(project_id)

    def load_schedulers(self, project_id=None):
        """加载调度列表，支持按项目筛选和分页"""
        # 检查服务对象是否已初始化
        if self.scheduler_service is None:
            print("调度服务未初始化，跳过加载调度列表")
            return
            
        try:
            # 使用分页查询获取调度数据
            schedulers, total_records = self.scheduler_service.get_schedulers_with_pagination(
                page=self.current_page,
                page_size=self.current_page_size,
                project_id=project_id
            )
            
            # 更新分页信息
            self.total_records = total_records
            self.total_pages = (total_records + self.current_page_size - 1) // self.current_page_size
            
            # 清空树形控件
            self.tree_widget.clear()
            
            if not schedulers:
                # 创建提示节点 - 合并第一行所有单元格并居中显示
                empty_item = QTreeWidgetItem(self.tree_widget)
                empty_item.setText(0, "暂无调度任务")
                
                # 合并所有列（从第0列到第8列）
                self.tree_widget.setFirstItemColumnSpanned(empty_item, True)
                
                # 设置文本居中对齐（水平和垂直都居中）
                empty_item.setTextAlignment(0, Qt.AlignCenter | Qt.AlignVCenter)
                
                # 设置特殊样式
                empty_item.setBackground(0, QBrush(QColor("#f8f9fa")))
                empty_item.setForeground(0, QBrush(QColor("#6c757d")))
                
                # 设置更大的字体和行高
                font = QFont()
                font.setPointSize(12)
                font.setBold(True)
                empty_item.setFont(0, font)
                
                # 设置更大的行高
                empty_item.setSizeHint(0, QSize(0, 60))
                
                # 更新分页信息显示
                self.update_pagination_info()
                return

            # 创建树形结构
            for i, scheduler in enumerate(schedulers, start=1):
                item = QTreeWidgetItem(self.tree_widget)
                
                # 设置所有列文本居中对齐
                for j in range(10):
                    item.setTextAlignment(j, Qt.AlignCenter)
                
                # 序号（计算当前页的序号）
                item_index = (self.current_page - 1) * self.current_page_size + i
                item.setText(0, str(item_index))
                
                # 调度名称
                item.setText(1, scheduler['name'])
                item.setData(1, Qt.UserRole, scheduler['id'])  # 存储ID到第一列
                
                # 状态
                status_text = "启用" if scheduler['enabled'] else "禁用"
                item.setText(2, status_text)
                # 设置状态颜色
                if scheduler['enabled']:
                    item.setForeground(2, QBrush(QColor("green")))
                else:
                    item.setForeground(2, QBrush(QColor("red")))
                
                # Cron表达式
                item.setText(3, scheduler['cron_expression'])
                
                # 用例数量
                case_ids = scheduler.get('case_ids', [])
                case_count = len(case_ids) if isinstance(case_ids, list) else 0
                item.setText(4, str(case_count))
                
                # 上次执行时间
                last_run = scheduler.get('last_run_at')
                last_run_text = last_run.strftime('%Y-%m-%d %H:%M:%S') if last_run else "从未执行"
                item.setText(5, last_run_text)
                
                # 下次执行时间
                next_run = scheduler.get('next_run_at')
                next_run_text = next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else "未计算"
                item.setText(6, next_run_text)
                if next_run and next_run < datetime.now():
                    item.setForeground(6, QBrush(QColor("orange")))
                
                # 创建时间
                created_at = scheduler.get('created_at')
                created_text = created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else ""
                item.setText(7, created_text)
                
                # 更新时间
                updated_at = scheduler.get('updated_at')
                updated_text = updated_at.strftime('%Y-%m-%d %H:%M:%S') if updated_at else ""
                item.setText(8, updated_text)
                
                # 操作栏 - 设置为空，实际按钮通过setItemWidget添加
                item.setText(9, "")
                
                # 创建操作按钮容器
                operation_widget = QWidget()
                operation_layout = QHBoxLayout(operation_widget)
                operation_layout.setContentsMargins(5, 2, 5, 2)
                operation_layout.setSpacing(3)
                operation_layout.setAlignment(Qt.AlignCenter)
                
                # 执行按钮
                run_btn = QPushButton()
                run_btn.setFixedSize(25, 25)
                run_btn.setIcon(self.get_icon("running.png"))
                run_btn.setToolTip("执行")
                run_btn.setStyleSheet("QPushButton { border: none; background: transparent; padding: 0px; } QPushButton:hover { background: #e0e0e0; }")
                run_btn.clicked.connect(lambda checked, sched_id=scheduler['id']: self.run_scheduler_by_id(sched_id))
                
                # 编辑按钮
                edit_btn = QPushButton()
                edit_btn.setFixedSize(25, 25)
                edit_btn.setIcon(self.get_icon("edit.png"))
                edit_btn.setToolTip("编辑")
                edit_btn.setStyleSheet("QPushButton { border: none; background: transparent; padding: 0px; } QPushButton:hover { background: #e0e0e0; }")
                edit_btn.clicked.connect(lambda checked, sched_id=scheduler['id']: self.edit_scheduler_by_id(sched_id))
                
                # 启用/禁用按钮
                toggle_btn = QPushButton()
                toggle_btn.setFixedSize(25, 25)
                if scheduler['enabled']:
                    toggle_btn.setIcon(self.get_icon("stop.png"))
                    toggle_btn.setToolTip("禁用")
                else:
                    toggle_btn.setIcon(self.get_icon("start.png"))
                    toggle_btn.setToolTip("启用")
                toggle_btn.setStyleSheet("QPushButton { border: none; background: transparent; padding: 0px; } QPushButton:hover { background: #e0e0e0; }")
                toggle_btn.clicked.connect(lambda checked, sched_id=scheduler['id']: self.toggle_scheduler_by_id(sched_id))
                
                # 复制按钮
                copy_btn = QPushButton()
                copy_btn.setFixedSize(25, 25)
                copy_btn.setIcon(self.get_icon("copy.png"))
                copy_btn.setToolTip("复制")
                copy_btn.setStyleSheet("QPushButton { border: none; background: transparent; padding: 0px; } QPushButton:hover { background: #e0e0e0; }")
                copy_btn.clicked.connect(lambda checked, sched_id=scheduler['id']: self.copy_scheduler_by_id(sched_id))
                
                # 删除按钮
                delete_btn = QPushButton()
                delete_btn.setFixedSize(25, 25)
                delete_btn.setIcon(self.get_icon("delete.png"))
                delete_btn.setToolTip("删除")
                delete_btn.setStyleSheet("QPushButton { border: none; background: transparent; padding: 0px; } QPushButton:hover { background: #e0e0e0; }")
                delete_btn.clicked.connect(lambda checked, sched_id=scheduler['id']: self.delete_scheduler_by_id(sched_id))
                
                # 详情按钮
                detail_btn = QPushButton()
                detail_btn.setFixedSize(25, 25)
                detail_btn.setIcon(self.get_icon("detail.png"))
                detail_btn.setToolTip("查看执行记录")
                detail_btn.setStyleSheet("QPushButton { border: none; background: transparent; padding: 0px; } QPushButton:hover { background: #e0e0e0; }")
                detail_btn.clicked.connect(lambda checked, sched_id=scheduler['id']: self.show_execution_logs(sched_id))
                
                operation_layout.addWidget(run_btn)
                operation_layout.addWidget(edit_btn)
                operation_layout.addWidget(toggle_btn)
                operation_layout.addWidget(copy_btn)
                operation_layout.addWidget(delete_btn)
                operation_layout.addWidget(detail_btn)
                
                # 设置操作按钮到第9列
                self.tree_widget.setItemWidget(item, 9, operation_widget)

            # 更新分页信息
            self.update_pagination_info()
            
            # 加载完成后重新计算下次执行时间
            self.update_next_run_times()

        except Exception as e:
            # 静默处理，不显示弹窗
            print(f"加载调度列表失败: {str(e)}")
            # 重置分页信息
            self.total_records = 0
            self.total_pages = 0
            self.update_pagination_info()

    def start_service(self):
        """启动调度服务"""
        try:
            if self.scheduler_service:
                self.scheduler_service.start_service()
                logger.info("调度服务已启动")
        except Exception as e:
            logger.error(f"启动调度服务失败: {str(e)}")

    def stop_service(self):
        """停止调度服务"""
        try:
            if self.scheduler_service:
                self.scheduler_service.stop_service()
                logger.info("调度服务已停止")
        except Exception as e:
            logger.error(f"停止调度服务失败: {str(e)}")
    
    def on_scheduler_executed(self, scheduler_data, success, message):
        """调度执行完成回调"""
        scheduler_id = scheduler_data['id']
        scheduler_name = scheduler_data['name']
        
        # 更新执行状态
        self.execution_status[scheduler_id] = {
            'status': 'completed',
            'success': success,
            'message': message,
            'timestamp': datetime.now()
        }
        
        # 刷新表格显示
        self.update_scheduler_status(scheduler_id)
        
        # 显示Toast提示
        status_text = f"调度 '{scheduler_name}' 执行{'成功' if success else '失败'}: {message}"
        if success:
            Toast.success(self, status_text)
        else:
            Toast.warn(self, status_text)
    
    def on_scheduler_error(self, scheduler_data, error_msg):
        """调度执行错误回调"""
        scheduler_id = scheduler_data['id']
        scheduler_name = scheduler_data['name']
        
        # 更新执行状态
        self.execution_status[scheduler_id] = {
            'status': 'error',
            'success': False,
            'message': error_msg,
            'timestamp': datetime.now()
        }
        
        # 刷新表格显示
        self.update_scheduler_status(scheduler_id)
        
        # 显示Toast提示
        status_text = f"调度 '{scheduler_name}' 执行错误: {error_msg}"
        Toast.error(self, status_text)
    
    def update_scheduler_status(self, scheduler_id):
        """更新调度状态显示"""
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item and item.data(1, Qt.UserRole) == scheduler_id:  # 调度名称列存储ID
                # 更新状态列
                if scheduler_id in self.execution_status:
                    status_info = self.execution_status[scheduler_id]
                    if status_info['status'] == 'executing':
                        item.setText(2, '执行中')
                        item.setBackground(2, QBrush(QColor('#fff3cd')))  # 黄色背景
                    elif status_info['status'] == 'completed':
                        if status_info['success']:
                            item.setText(2, '执行成功')
                            item.setBackground(2, QBrush(QColor('#d4edda')))  # 绿色背景
                        else:
                            item.setText(2, '执行失败')
                            item.setBackground(2, QBrush(QColor('#f8d7da')))  # 红色背景
                    elif status_info['status'] == 'error':
                        item.setText(2, '执行错误')
                        item.setBackground(2, QBrush(QColor('#f8d7da')))  # 红色背景
                else:
                    # 检查调度是否启用
                    scheduler_data = self.get_scheduler_data_by_id(scheduler_id)
                    if scheduler_data and scheduler_data.get('enabled', False):
                        item.setText(2, '已启用')
                        item.setBackground(2, QBrush(QColor('#d4edda')))  # 绿色背景
                    else:
                        item.setText(2, '已禁用')
                        item.setBackground(2, QBrush(QColor('#f8d7da')))  # 红色背景
                break

    def closeEvent(self, event):
        """窗口关闭事件，停止后台服务"""
        self.stop_background_service()
        event.accept()

    def get_icon(self, icon_name):
        """获取图标"""
        try:
            # 打包后路径处理：尝试从 PyInstaller 临时解压目录加载
            if getattr(sys, 'frozen', False):
                # 打包后的可执行文件路径
                base_path = sys._MEIPASS
                # 尝试从打包后的 resources/icons 目录加载
                icon_path = os.path.join(base_path, "src", "resources", "icons", icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
                
                # 尝试直接加载图标文件
                icon_path = os.path.join(base_path, icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
                
                # 尝试从当前目录加载
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "icons", icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
            
            # 开发环境：尝试从 ui/interface_auto/icons 目录加载
            icon_path = os.path.join("src", "ui", "interface_auto", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
            
            # 尝试从 resources/icons 目录加载
            icon_path = os.path.join("src", "resources", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
        except:
            pass
        return QIcon()



    def update_next_run_times(self):
        """更新下次执行时间显示"""
        from src.utils.interface_utils.cron_parser import CronParser
        parser = CronParser()
        
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item:
                # 获取Cron表达式
                cron_expr = item.text(3)  # 第3列是Cron表达式
                
                # 重新计算下次执行时间
                next_run = parser.get_next_run(cron_expr)
                if next_run:
                    next_run_text = next_run.strftime('%Y-%m-%d %H:%M:%S')
                    item.setText(6, next_run_text)  # 第6列是下次执行时间
                    
                    # 更新颜色：如果下次执行时间已过，显示橙色
                    if next_run < datetime.now():
                        item.setForeground(6, QBrush(QColor("orange")))
                    else:
                        item.setForeground(6, QBrush(QColor("black")))
                else:
                    item.setText(6, "未计算")
                    item.setForeground(6, QBrush(QColor("black")))

    def get_selected_scheduler_id(self):
        """获取选中的调度ID"""
        selected_items = self.tree_widget.selectedItems()
        if selected_items:
            return selected_items[0].data(1, Qt.UserRole)  # 第1列存储ID
        return None

    def get_selected_scheduler_data(self):
        """获取选中的调度数据"""
        scheduler_id = self.get_selected_scheduler_id()
        if scheduler_id:
            return self.scheduler_service.get_scheduler_by_id(scheduler_id)
        return None

    def get_scheduler_data_by_id(self, scheduler_id):
        """根据ID获取调度数据"""
        try:
            if self.scheduler_service:
                return self.scheduler_service.get_scheduler_by_id(scheduler_id)
            else:
                logger.error("调度服务未初始化")
                return None
        except Exception as e:
            logger.error(f"获取调度数据失败: {str(e)}")
            return None

    def add_scheduler(self):
        """新增调度"""
        # 获取当前选中的项目ID
        current_project_id = self.project_combo.currentData()
        
        # 创建调度对话框，并传递当前选中的项目ID
        dialog = SchedulerDialog(self)
        
        # 如果当前选中了具体项目，则在对话框中自动选中该项目
        if current_project_id is not None:
            # 延迟执行，确保对话框已初始化完成
            QTimer.singleShot(100, lambda: self._preselect_project_in_dialog(dialog, current_project_id))
        
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warn(self, "调度名称不能为空")
                return
            if not data['cron_expression']:
                Toast.warn(self, "Cron表达式不能为空")
                return
            if not data['case_ids']:
                Toast.warn(self, "请选择至少一个测试用例")
                return

            try:
                # 验证Cron表达式
                parser = CronParser()
                if not parser.validate_cron(data['cron_expression']):
                    Toast.warn(self, "Cron表达式格式不正确")
                    return

                self.scheduler_service.create_scheduler(data)
                self.load_schedulers(self.project_combo.currentData())
                self.data_changed.emit()
                Toast.info(self, "调度创建成功")
                
                # 保存成功后立即更新下次执行时间显示
                self.update_next_run_times()
            except Exception as e:
                Toast.error(self, f"创建调度失败: {str(e)}")

    def _preselect_project_in_dialog(self, dialog, project_id):
        """在对话框中选择指定的项目（已移除项目列表，直接加载文件夹）"""
        try:
            # 设置当前项目ID
            dialog.set_current_project_id(project_id)
            # 项目列表功能已移除，系统会自动使用当前业务管理页面选中的项目
            # 直接加载文件夹列表，无需手动选择项目
            dialog.load_folders()
        except Exception as e:
            print(f"预选项目失败: {str(e)}")





    def edit_scheduler_by_id(self, scheduler_id):
        """根据ID编辑调度"""
        scheduler_data = self.scheduler_service.get_scheduler_by_id(scheduler_id)
        if scheduler_data:
            self.edit_scheduler(scheduler_data)

    def delete_scheduler_by_id(self, scheduler_id):
        """根据ID删除调度"""
        scheduler_data = self.scheduler_service.get_scheduler_by_id(scheduler_id)
        if scheduler_data:
            self.delete_scheduler(scheduler_data)

    def delete_scheduler(self, scheduler_data):
        """删除调度"""
        # 检查调度是否已启用
        if scheduler_data.get('enabled', False):
            Toast.warn(self, f"调度 '{scheduler_data['name']}' 当前处于启用状态，请先禁用后再删除")
            return
        
        # 创建确认对话框，手动设置按钮文本
        msg_box = QMessageBox(QMessageBox.Question, "确认删除",
                             f"确定要删除调度 '{scheduler_data['name']}' 吗？")
        
        # 添加确认和取消按钮
        confirm_btn = msg_box.addButton("确认", QMessageBox.YesRole)
        cancel_btn = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_btn)
        
        msg_box.exec_()
        
        if msg_box.clickedButton() == confirm_btn:
            try:
                self.scheduler_service.delete_scheduler(scheduler_data['id'])
                self.load_schedulers(self.project_combo.currentData())
                self.data_changed.emit()
                Toast.info(self, "调度删除成功")
            except Exception as e:
                Toast.error(self, f"删除调度失败: {str(e)}")







    def run_scheduler_by_id(self, scheduler_id):
        """根据ID执行调度"""
        scheduler_data = self.scheduler_service.get_scheduler_by_id(scheduler_id)
        if scheduler_data:
            # 检查调度是否被禁用
            if not scheduler_data['enabled']:
                Toast.warn(self, "该调度已被禁用，无法执行")
                return
            self.run_scheduler(scheduler_data)

    def edit_scheduler(self, scheduler_data):
        """编辑调度"""
        dialog = SchedulerDialog(self, scheduler_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warn(self, "调度名称不能为空")
                return
            if not data['cron_expression']:
                Toast.warn(self, "Cron表达式不能为空")
                return
            if not data['case_ids']:
                Toast.warn(self, "请选择至少一个测试用例")
                return

            try:
                # 验证Cron表达式
                parser = CronParser()
                if not parser.validate_cron(data['cron_expression']):
                    Toast.warn(self, "Cron表达式格式不正确")
                    return

                self.scheduler_service.update_scheduler(scheduler_data['id'], data)
                self.load_schedulers(self.project_combo.currentData())
                self.data_changed.emit()
                Toast.info(self, "调度更新成功")
                
                # 更新成功后立即更新下次执行时间显示
                self.update_next_run_times()
            except Exception as e:
                Toast.error(self, f"更新调度失败: {str(e)}")

    def run_scheduler(self, scheduler_data):
        """执行调度"""
        try:
            # 获取调度中配置的测试用例ID列表
            case_ids = scheduler_data.get('case_ids', [])
            if not case_ids:
                Toast.warn(self, f"调度 '{scheduler_data['name']}' 中没有配置测试用例")
                return

            # 显示开始执行提示
            Toast.info(self, f"开始执行调度: {scheduler_data['name']} (包含 {len(case_ids)} 个测试用例)")

            # 使用统一调度服务执行调度
            if self.scheduler_service:
                # 通过统一调度服务执行调度
                success = self.scheduler_service.execute_scheduler(scheduler_data['id'])
                
                if success:                    
                    # 刷新调度列表以更新状态
                    self.load_schedulers(self.project_combo.currentData())
                else:
                    # 如果异步执行失败，使用同步执行方式
                    self._run_scheduler_sync(scheduler_data)
            else:
                # 如果没有调度服务，使用原来的同步执行方式
                self._run_scheduler_sync(scheduler_data)

        except Exception as e:
            Toast.error(self, f"执行调度失败: {str(e)}")

    def _run_scheduler_sync(self, scheduler_data):
        """同步执行调度（备用方案）"""
        try:
            # 获取调度中配置的测试用例ID列表
            case_ids = scheduler_data.get('case_ids', [])
            if not case_ids:
                return

            # 获取测试用例服务
            test_case_service = TestCaseService()
            
            # 执行每个测试用例
            success_count = 0
            total_count = len(case_ids)
            
            # 记录执行开始时间
            execution_start_time = datetime.now()
            
            # 存储每个用例的执行结果
            case_results = []
            
            for i, case_id in enumerate(case_ids):
                try:
                    # 获取测试用例数据
                    case_data = test_case_service.get_case_with_steps(case_id)
                    if not case_data:
                        Toast.warn(self, f"测试用例ID {case_id} 不存在，跳过执行")
                        continue

                    case_name = case_data.get('name', '未知用例')
                    
                    # 创建执行线程
                    execution_thread = CaseExecutionThread(
                        case_data=case_data,
                        environment_config={},  # 使用默认环境配置
                        project_id=case_data.get('project_id', 0)
                    )

                    # 连接信号
                    execution_thread.case_finished.connect(self._on_case_execution_finished)
                    execution_thread.log_message.connect(self._on_execution_log_message)

                    # 启动执行线程
                    execution_thread.start()
                    
                    # 等待执行完成
                    execution_thread.wait()
                    
                    # 检查执行结果 - 线程正常结束表示执行成功
                    if not execution_thread.isRunning():
                        success_count += 1
                        case_results.append({
                            'case_id': case_id,
                            'case_name': case_name,
                            'success': True,
                            'execution_time': datetime.now()
                        })
                    else:
                        case_results.append({
                            'case_id': case_id,
                            'case_name': case_name,
                            'success': False,
                            'execution_time': datetime.now()
                        })
                    
                except Exception as e:
                    Toast.error(self, f"执行测试用例ID {case_id} 失败: {str(e)}")
                    case_results.append({
                        'case_id': case_id,
                        'case_name': '未知用例',
                        'success': False,
                        'error': str(e),
                        'execution_time': datetime.now()
                    })

            # 记录执行结束时间
            execution_end_time = datetime.now()
            execution_duration = (execution_end_time - execution_start_time).total_seconds()
            
            # 更新上次执行时间
            self.scheduler_service.update_last_run(scheduler_data['id'])
            
            # 显示执行结果
            if success_count == total_count:
                Toast.success(self, f"调度执行完成: 成功 {success_count}/{total_count} 个测试用例")
            else:
                Toast.warn(self, f"调度执行完成: 成功 {success_count}/{total_count} 个测试用例")
            
            # 发送邮件通知（如果配置了收件人）
            notify_emails = scheduler_data.get('notify_emails', [])
            if notify_emails:
                try:
                    # 导入邮件服务
                    from src.core.services.email_service import EmailService
                    email_service = EmailService()
                    
                    # 生成邮件报告数据
                    scheduler_name = scheduler_data['name']
                    
                    # 发送邮件
                    email_service.send_test_report_email(
                        notify_emails,
                        case_results,
                        scheduler_name,
                        execution_duration
                    )
                    
                    Toast.info(self, f"测试报告邮件已发送至: {', '.join(notify_emails)}")
                    
                except Exception as e:
                    Toast.error(self, f"发送测试报告邮件失败: {str(e)}")
            
            # 刷新调度列表
            self.load_schedulers(self.project_combo.currentData())

        except Exception as e:
            Toast.error(self, f"同步执行调度失败: {str(e)}")

    def _on_case_execution_finished(self, result):
        """测试用例执行完成回调"""
        try:
            success = result.get('success', False)
            success_count = result.get('success_count', 0)
            total_count = result.get('total_count', 0)
            
            if success:
                print(f"测试用例执行成功: {success_count}/{total_count} 步骤")
            else:
                error_msg = result.get('error', '未知错误')
                print(f"测试用例执行失败: {error_msg}")
                
        except Exception as e:
            print(f"处理测试用例执行完成回调时出错: {str(e)}")

    def _on_execution_log_message(self, message, level, step_index):
        """执行日志消息回调"""
        try:
            # 这里可以记录执行日志到文件或数据库
            print(f"[{level}] {message}")
            
        except Exception as e:
            print(f"处理执行日志消息时出错: {str(e)}")

    def toggle_scheduler_by_id(self, scheduler_id):
        """根据ID启用/禁用调度"""
        scheduler_data = self.scheduler_service.get_scheduler_by_id(scheduler_id)
        if scheduler_data:
            self.toggle_scheduler(scheduler_data)

    def toggle_scheduler(self, scheduler_data):
        """启用/禁用调度"""
        new_status = not scheduler_data['enabled']
        status_text = "启用" if new_status else "禁用"

        try:
            self.scheduler_service.update_scheduler_status(scheduler_data['id'], new_status)
            self.load_schedulers(self.project_combo.currentData())
            self.data_changed.emit()
            Toast.info(self, f"调度已{status_text}")
        except Exception as e:
            Toast.error(self, f"{status_text}调度失败: {str(e)}")

    def copy_scheduler_by_id(self, scheduler_id):
        """根据ID复制调度"""
        scheduler_data = self.scheduler_service.get_scheduler_by_id(scheduler_id)
        if scheduler_data:
            self.copy_scheduler(scheduler_data)

    def copy_scheduler(self, scheduler_data):
        """复制调度"""
        try:
            # 创建副本数据
            copy_data = {
                'name': f"{scheduler_data['name']}_副本",
                'cron_expression': scheduler_data['cron_expression'],
                'case_ids': scheduler_data.get('case_ids', []),
                'enabled': False,  # 默认禁用副本
                'description': scheduler_data.get('description', ''),
                'project_id': scheduler_data.get('project_id')  # 复制项目ID
            }

            # 验证名称是否重复
            existing_names = [s['name'] for s in self.scheduler_service.get_all_schedulers()]
            base_name = copy_data['name']
            counter = 1
            while copy_data['name'] in existing_names:
                copy_data['name'] = f"{base_name}_{counter}"
                counter += 1

            # 创建副本
            self.scheduler_service.create_scheduler(copy_data)
            self.load_schedulers(self.project_combo.currentData())
            self.data_changed.emit()
            Toast.info(self, f"调度复制成功: {copy_data['name']}")

        except Exception as e:
            Toast.error(self, f"复制调度失败: {str(e)}")

    def show_execution_logs(self, scheduler_id):
        """显示调度执行记录 - 直接跳转到测试报告tab并自动筛选"""
        try:
            # 保存当前调度ID，用于报告详情跳转
            self.current_scheduler_id = scheduler_id
            
            # 获取调度数据
            scheduler_data = self.get_scheduler_data_by_id(scheduler_id)
            if not scheduler_data:
                Toast.warn(self, "调度数据不存在")
                return

            # 获取执行记录
            from src.core.services.test_report_service import TestReportService
            report_service = TestReportService()
            reports = report_service.get_reports_by_scheduler_id(scheduler_id)

            if not reports:
                Toast.info(self, f"调度 '{scheduler_data['name']}' 暂无执行记录")
                return

            # 直接跳转到测试报告tab，并自动筛选
            self._jump_to_test_report_tab(scheduler_data, reports)

        except Exception as e:
            Toast.error(self, f"显示执行记录失败: {str(e)}")
    
    def _jump_to_test_report_tab(self, scheduler_data, reports):
        """跳转到测试报告tab并自动筛选"""
        try:
            # 发送信号，通知主窗口跳转到测试报告tab
            if hasattr(self, 'report_tab_requested'):
                # 创建一个包含调度信息和报告列表的数据对象
                jump_data = {
                    'scheduler': scheduler_data,
                    'reports': reports,
                    'action': 'filter_by_scheduler'
                }
                self.report_tab_requested.emit(jump_data)
            else:
                # 如果信号不存在，使用备用方式
                self._jump_to_test_report_fallback(scheduler_data, reports)
                
        except Exception as e:
            Toast.error(self, f"跳转到测试报告tab失败: {str(e)}")
    
    def _jump_to_test_report_fallback(self, scheduler_data, reports):
        """备用方式跳转到测试报告tab"""
        try:
            # 尝试直接调用主窗口的方法
            parent = self.parent()
            if parent and hasattr(parent, 'switch_to_test_report_tab'):
                parent.switch_to_test_report_tab(scheduler_data, reports)
            else:
                # 如果无法找到主窗口，显示提示信息
                Toast.info(self, f"已跳转到测试报告tab，调度 '{scheduler_data['name']}' 共有 {len(reports)} 条执行记录")
                
        except Exception as e:
            Toast.error(self, f"跳转到测试报告tab失败: {str(e)}")
    
    def _view_report_detail(self, table_widget, parent_dialog):
        """查看报告详情 - 跳转到测试报告tab并自动进入详情页"""
        try:
            selected_items = table_widget.selectedItems()
            if not selected_items:
                Toast.warn(parent_dialog, "请先选择一条执行记录")
                return

            # 获取选中的报告数据
            row = selected_items[0].row()
            report_name = table_widget.item(row, 0).text()
            
            # 获取报告ID（从数据中获取）
            from src.core.services.test_report_service import TestReportService
            report_service = TestReportService()
            
            # 根据报告名称和调度ID获取完整的报告数据
            scheduler_id = self.current_scheduler_id if hasattr(self, 'current_scheduler_id') else None
            reports = report_service.get_reports_by_scheduler_id(scheduler_id) if scheduler_id else []
            
            selected_report = None
            for report in reports:
                if report.get('report_name') == report_name:
                    selected_report = report
                    break
            
            if not selected_report:
                Toast.warn(parent_dialog, "未找到对应的报告数据")
                return
            
            # 关闭当前对话框
            parent_dialog.accept()
            
            # 发送信号，通知主窗口跳转到测试报告tab并显示详情
            if hasattr(self, 'report_detail_requested'):
                self.report_detail_requested.emit(selected_report)
            else:
                # 如果信号不存在，使用备用方式
                self._open_report_detail_fallback(selected_report)

        except Exception as e:
            Toast.error(parent_dialog, f"查看报告详情失败: {str(e)}")
    
    def _open_report_detail_fallback(self, report_data):
        """备用方式打开报告详情"""
        try:
            from src.ui.interface_auto.test_report import ReportDetailPage
            
            # 创建一个对话框来包装ReportDetailPage
            detail_dialog = QDialog(self)
            detail_dialog.setWindowTitle(f"测试报告 - {report_data.get('report_name', '')}")
            detail_dialog.setMinimumSize(1000, 700)
            
            layout = QVBoxLayout(detail_dialog)
            
            # 创建ReportDetailPage
            detail_page = ReportDetailPage(report_data=report_data)
            
            # 添加关闭按钮
            button_box = QDialogButtonBox(QDialogButtonBox.Close)
            button_box.rejected.connect(detail_dialog.reject)
            close_button = button_box.button(QDialogButtonBox.Close)
            if close_button:
                close_button.setText("关闭")
            
            layout.addWidget(detail_page)
            layout.addWidget(button_box)
            
            detail_dialog.exec_()
        except Exception as e:
            Toast.error(self, f"打开报告详情失败: {str(e)}")



    def update_pagination_info(self):
        """更新分页信息显示"""
        if self.total_records == 0:
            self.pagination_label.setText("共 0 条记录")
            self.page_input.setText("1")
            self.total_pages_label.setText("共 0 页")
        else:
            self.pagination_label.setText(f"共 {self.total_records} 条记录")
            self.page_input.setText(str(self.current_page))
            self.total_pages_label.setText(f"共 {self.total_pages} 页")
        
        # 更新按钮状态
        self.first_page_btn.setEnabled(self.current_page > 1)
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages)
        self.last_page_btn.setEnabled(self.current_page < self.total_pages)

    def go_to_first_page(self):
        """跳转到第一页"""
        if self.current_page != 1:
            self.current_page = 1
            self.load_schedulers()

    def go_to_prev_page(self):
        """跳转到上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_schedulers()

    def go_to_next_page(self):
        """跳转到下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_schedulers()

    def go_to_last_page(self):
        """跳转到最后一页"""
        if self.current_page != self.total_pages:
            self.current_page = self.total_pages
            self.load_schedulers()

    def go_to_specific_page(self):
        """跳转到指定页码"""
        try:
            page = int(self.page_input.text().strip())
            if 1 <= page <= self.total_pages:
                if page != self.current_page:
                    self.current_page = page
                    self.load_schedulers()
            else:
                Toast.warning(self, "警告", f"页码必须在 1 到 {self.total_pages} 之间")
        except ValueError:
            Toast.warning(self, "警告", "请输入有效的页码")

    def on_page_size_changed(self, page_size_text):
        """页面大小改变事件"""
        try:
            new_page_size = int(page_size_text)
            if new_page_size != self.current_page_size:
                self.current_page_size = new_page_size
                self.current_page = 1  # 重置到第一页
                self.load_schedulers()
        except ValueError:
            # 忽略无效输入
            pass
