import time
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
                             QListWidget, QStackedWidget, QListWidgetItem, QLabel,
                             QHBoxLayout, QVBoxLayout)
from PyQt5.QtCore import Qt
from src.ui.interface_auto.business_management import BusinessManagement
from src.ui.interface_auto.api_template import ApiTemplateManager
from src.ui.interface_auto.test_case import TestCaseManager
from src.ui.interface_auto.scheduler import SchedulerManager
from src.ui.interface_auto.test_report import TestReportManager
from src.ui.interface_auto.global_tools import GlobalToolsManager
from src.ui.interface_auto.variable_management import VariableManagement
from src.ui.interface_auto.components.collapse_button import CollapseButton


class InterfaceAutoTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.database_available = False  # 初始化为False，延迟检查
        self.ui_initialized = False
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建占位界面，不立即创建任何子页面
        placeholder_label = QLabel("接口自动化功能加载中...")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_label.setStyleSheet("color: #666; font-size: 14px; margin: 20px;")
        main_layout.addWidget(placeholder_label)
        
        self.main_layout = main_layout
        self.ui_initialized = True
        
        # 初始化子页面为None，延迟创建
        self.business_management = None
        self.api_template = None
        self.test_case = None
        self.scheduler = None
        self.test_report = None
        self.global_tools = None
        self.variable_management = None
        self.left_nav = None
        self.stacked_widget = None

    def connect_signals(self):
        """连接各个页面的信号"""
        # 检查子页面是否已创建
        if self.business_management is None or self.api_template is None or self.test_case is None:
            return
            
        # 当业务管理页面数据变化时，刷新接口模板页面的项目列表
        self.business_management.data_changed.connect(self.api_template.refresh_project_list)
        
        # 当业务管理页面数据变化时，刷新测试用例管理页面的项目列表
        self.business_management.data_changed.connect(self.test_case.refresh_project_list)
        
        # 当测试用例管理页面请求编辑接口模板时，跳转到接口模板标签页并打开对应模板
        self.test_case.api_template_edit_requested.connect(self.on_api_template_edit_requested)

        # 如果需要，也可以连接其他页面的信号
        # self.business_management.data_changed.connect(self.test_case.refresh_project_list)

    def delayed_init(self):
        """延迟初始化数据库连接和实际UI"""
        if not self.ui_initialized:
            return
            
        # 检查数据库连接是否可用
        try:
            from config.database import Database
            db = Database()
            # 测试数据库连接
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            self.database_available = True
            print("数据库连接成功，初始化接口自动化界面")
        except Exception as e:
            print(f"数据库连接失败: {e}")
            self.database_available = False
            # 显示错误信息
            error_label = QLabel(f"数据库连接失败: {str(e)}\\n请检查数据库配置或网络连接。")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: red; font-size: 14px; margin: 20px;")
            
            # 清除占位界面
            for i in reversed(range(self.main_layout.count())):
                self.main_layout.itemAt(i).widget().setParent(None)
            
            self.main_layout.addWidget(error_label)
            return
        
        # 数据库连接成功，创建实际界面
        self.create_actual_ui()
        
        # 连接信号
        self.connect_signals()

    def create_actual_ui(self):
        """创建实际的界面组件"""
        # 清除占位界面
        for i in reversed(range(self.main_layout.count())):
            self.main_layout.itemAt(i).widget().setParent(None)
        
        # 创建主容器
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_container.setContentsMargins(0, 0, 0, 0)
        
        # 顶部工具栏（移除展开/收缩按钮，因为每个子页面有自己的按钮）
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        toolbar_layout.addStretch()
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Horizontal)

        # 左侧导航栏容器（包含导航栏和展开/收缩图标）
        self.left_container = QWidget()
        self.left_container.setFixedWidth(224)  # 200px导航栏 + 24px按钮
        left_container_layout = QHBoxLayout(self.left_container)
        left_container_layout.setContentsMargins(0, 0, 0, 0)
        left_container_layout.setSpacing(0)
        left_container_layout.setAlignment(Qt.AlignLeft)

        # 左侧导航栏
        self.left_nav = QListWidget()
        self.left_nav.setFixedWidth(200)
        self.left_nav.setStyleSheet("""
            QListWidget {
                background-color: #f5f5f5;
                border: none;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
        """)

        # 添加导航项
        nav_items = [
            "业务管理", "接口模板", "用例管理",
            "定时调度", "测试报告", "全局工具", "变量管理"
        ]
        for item in nav_items:
            self.left_nav.addItem(item)

        # 添加展开/收缩图标（在左侧导航栏的右侧边线上）
        self.collapse_button = CollapseButton()
        self.collapse_button.state_changed.connect(self.on_collapse_state_changed)
        
        # 设置图标样式（无背景、无边框）
        self.collapse_button.setFixedSize(24, 24)
        self.collapse_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-radius: 12px;
            }
        """)

        # 将导航栏和按钮添加到容器
        left_container_layout.addWidget(self.left_nav)
        left_container_layout.addWidget(self.collapse_button)
        
        # 设置按钮紧贴导航栏右侧，无间隙
        left_container_layout.setStretchFactor(self.left_nav, 0)
        left_container_layout.setStretchFactor(self.collapse_button, 0)

        # 右侧堆叠窗口
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setContentsMargins(0, 0, 0, 0)  # 移除边距

        # 创建各个页面
        self.business_management = BusinessManagement(self)
        self.api_template = ApiTemplateManager(self)
        self.test_case = TestCaseManager(self)
        self.scheduler = SchedulerManager(self)
        self.test_report = TestReportManager(self)
        self.global_tools = GlobalToolsManager(self)
        self.variable_management = VariableManagement(self)

        # 添加到堆叠窗口
        self.stacked_widget.addWidget(self.business_management)
        self.stacked_widget.addWidget(self.api_template)
        self.stacked_widget.addWidget(self.test_case)
        self.stacked_widget.addWidget(self.scheduler)
        self.stacked_widget.addWidget(self.test_report)
        self.stacked_widget.addWidget(self.global_tools)
        self.stacked_widget.addWidget(self.variable_management)

        # 添加到分割器
        self.splitter.addWidget(self.left_container)
        self.splitter.addWidget(self.stacked_widget)
        self.splitter.setSizes([224, 1000])  # 200px导航栏 + 24px按钮

        # 添加到主布局
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.splitter)
        
        # 将主容器添加到界面
        self.main_layout.addWidget(main_container)

        # 连接信号
        self.left_nav.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)

        # 默认选择第一个
        self.left_nav.setCurrentRow(0)

    def on_collapse_state_changed(self, is_expanded):
        """处理展开/收缩状态变化"""
        if is_expanded:
            # 展开状态：显示左侧导航栏，容器宽度为224px
            self.left_nav.show()
            self.left_container.setFixedWidth(224)  # 200px导航栏 + 24px按钮
            self.splitter.setSizes([224, 1000])
        else:
            # 收起状态：隐藏左侧导航栏内容，容器宽度收缩到24px
            self.left_nav.hide()
            self.left_container.setFixedWidth(24)  # 只保留按钮宽度
            self.splitter.setSizes([24, 1000])
    
    def on_api_template_edit_requested(self, api_template_id):
        """处理接口模板编辑请求，跳转到接口模板标签页并打开对应模板
        
        Args:
            api_template_id: 接口模板ID
        """
        try:
            # 跳转到接口模板标签页（索引为1）
            self.left_nav.setCurrentRow(1)
            
            # 检查api_template对象是否有open_template_by_id方法
            if hasattr(self.api_template, 'open_template_by_id'):
                # 调用open_template_by_id方法打开对应模板
                self.api_template.open_template_by_id(api_template_id)
                print(f"成功跳转到接口模板编辑页面，模板ID: {api_template_id}")
            else:
                print("ApiTemplateManager类中没有open_template_by_id方法")
                
        except Exception as e:
            print(f"跳转到接口模板编辑页面失败: {str(e)}")
