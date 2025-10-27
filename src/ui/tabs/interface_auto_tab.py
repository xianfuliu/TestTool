from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
                             QListWidget, QStackedWidget, QListWidgetItem)
from PyQt5.QtCore import Qt
from src.ui.interface_auto.business_management import BusinessManagement
from src.ui.interface_auto.api_template import ApiTemplateManager
from src.ui.interface_auto.test_case import TestCaseManager
from src.ui.interface_auto.scheduler import SchedulerManager
from src.ui.interface_auto.test_report import TestReportManager
from src.ui.interface_auto.global_tools import GlobalToolsManager


class InterfaceAutoTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

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
            "定时调度", "测试报告", "全局工具"
        ]
        for item in nav_items:
            self.left_nav.addItem(item)

        # 右侧堆叠窗口
        self.stacked_widget = QStackedWidget()

        # 创建各个页面
        self.business_management = BusinessManagement(self)
        self.api_template = ApiTemplateManager(self)
        self.test_case = TestCaseManager(self)
        self.scheduler = SchedulerManager(self)
        self.test_report = TestReportManager(self)
        self.global_tools = GlobalToolsManager(self)

        # 添加到堆叠窗口
        self.stacked_widget.addWidget(self.business_management)
        self.stacked_widget.addWidget(self.api_template)
        self.stacked_widget.addWidget(self.test_case)
        self.stacked_widget.addWidget(self.scheduler)
        self.stacked_widget.addWidget(self.test_report)
        self.stacked_widget.addWidget(self.global_tools)

        # 添加到分割器
        splitter.addWidget(self.left_nav)
        splitter.addWidget(self.stacked_widget)
        splitter.setSizes([200, 1000])

        main_layout.addWidget(splitter)

        # 连接信号
        self.left_nav.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)

        # 默认选择第一个
        self.left_nav.setCurrentRow(0)

    def connect_signals(self):
        """连接各个页面的信号"""
        # 当业务管理页面数据变化时，刷新接口模板页面的项目列表
        self.business_management.data_changed.connect(self.api_template.refresh_project_list)

        # 如果需要，也可以连接其他页面的信号
        # self.business_management.data_changed.connect(self.test_case.refresh_project_list)
