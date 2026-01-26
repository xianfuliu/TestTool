import time
from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QListWidget,
    QStackedWidget,
    QListWidgetItem,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
)
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
        self.stacked_widget = None

    def connect_signals(self):
        """连接各个页面的信号"""
        # 检查子页面是否已创建
        if (
            self.business_management is None
            or self.api_template is None
            or self.test_case is None
        ):
            return

        # 当业务管理页面数据变化时，刷新接口模板页面的项目列表
        self.business_management.data_changed.connect(
            self.api_template.refresh_project_list
        )

        # 当业务管理页面数据变化时，刷新测试用例管理页面的项目列表
        self.business_management.data_changed.connect(
            self.test_case.refresh_project_list
        )

        # 当业务切换时，刷新接口模板页面的项目列表（根据业务分组ID过滤）
        self.business_management.business_changed.connect(
            lambda business_group_id: self.api_template.refresh_project_list(
                business_group_id, show_toast=False
            )
        )

        # 当业务切换时，刷新测试用例管理页面的项目列表（根据业务分组ID过滤）
        self.business_management.business_changed.connect(
            lambda business_group_id: self.test_case.refresh_project_list(
                business_group_id, show_toast=False
            )
        )

        # 当业务切换时，刷新定时调度页面的项目列表（根据业务分组ID过滤）
        self.business_management.business_changed.connect(
            self.scheduler.on_business_changed
        )

        # 当业务切换时，刷新测试报告页面的项目列表（根据业务分组ID过滤）
        self.business_management.business_changed.connect(
            self.test_report.on_business_changed
        )

        # 当业务切换时，刷新变量管理页面的项目列表（根据业务分组ID过滤）
        self.business_management.business_changed.connect(
            self.variable_management.on_business_changed
        )

        # 当测试用例管理页面请求编辑接口模板时，跳转到接口模板标签页并打开对应模板
        self.test_case.api_template_edit_requested.connect(
            self.on_api_template_edit_requested
        )

        # 当定时调度页面请求查看报告详情时，跳转到测试报告标签页并打开对应报告
        self.scheduler.report_detail_requested.connect(self.on_report_detail_requested)

        # 当定时调度页面请求跳转到测试报告tab并筛选时，处理跳转和筛选
        self.scheduler.report_tab_requested.connect(self.on_report_tab_requested)

    def delayed_init(self):
        """延迟初始化数据库连接和实际UI"""
        print("开始执行delayed_init方法")
        if not self.ui_initialized:
            print("UI未初始化，跳过delayed_init")
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
            error_label = QLabel(
                f"数据库连接失败: {str(e)}\\n请检查数据库配置或网络连接。"
            )
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: red; font-size: 14px; margin: 20px;")

            # 清除占位界面
            for i in reversed(range(self.main_layout.count())):
                self.main_layout.itemAt(i).widget().setParent(None)

            self.main_layout.addWidget(error_label)
            return

        # 数据库连接成功，创建实际界面
        print("开始创建实际界面")
        self.create_actual_ui()

        # 连接信号
        print("开始连接信号")
        self.connect_signals()

        # 在所有页面创建和信号连接完成后，延迟触发初始业务切换
        print("开始延迟触发初始业务切换")
        from PyQt5.QtCore import QTimer

        QTimer.singleShot(1000, self.delayed_trigger_initial_business_change)
        print("delayed_init方法执行完成")

    def delayed_trigger_initial_business_change(self):
        """延迟触发初始业务切换，确保数据已加载完成"""
        print("开始执行delayed_trigger_initial_business_change")

        # 检查business_management对象是否存在
        if not hasattr(self, "business_management") or not self.business_management:
            print("business_management对象不存在，跳过业务切换")
            return

        # 检查数据是否已加载完成
        if not hasattr(self.business_management, "initial_business_ready"):
            print("initial_business_ready属性不存在，跳过业务切换")
            return

        # 检查是否有业务数据，如果没有业务数据，停止循环检查
        if not hasattr(self.business_management, "business_groups"):
            print("business_groups属性不存在，跳过业务切换")
            return

        # 如果没有业务数据，停止循环检查
        if not self.business_management.business_groups:
            print("没有业务数据，停止循环检查")
            return

        # 如果数据尚未准备好，继续延迟检查
        if not self.business_management.initial_business_ready:
            print("数据尚未准备好，继续延迟检查")
            from PyQt5.QtCore import QTimer

            QTimer.singleShot(500, self.delayed_trigger_initial_business_change)
            return

        print("数据已准备好，开始触发初始业务切换")

        # 手动触发初始业务切换
        self.trigger_initial_business_change()

        print("delayed_trigger_initial_business_change执行完成")

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

        # 创建堆叠窗口
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

        # 添加到主布局
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.stacked_widget)

        # 将主容器添加到界面
        self.main_layout.addWidget(main_container)

        # 默认显示第一个页面
        self.stacked_widget.setCurrentIndex(0)
        
        # 初始化当前页面索引
        self.current_page_index = 0

    def on_collapse_state_changed(self, is_expanded):
        """处理展开/收缩状态变化（已弃用，保留方法签名）"""
        # 由于移除了左侧导航栏，此方法不再需要
        pass

    def on_api_template_edit_requested(self, api_template_id):
        """处理接口模板编辑请求，跳转到接口模板标签页并打开对应模板

        Args:
            api_template_id: 接口模板ID
        """
        try:
            # 跳转到接口模板标签页（索引为1）
            self.stacked_widget.setCurrentIndex(1)

            # 检查api_template对象是否有open_template_by_id方法
            if hasattr(self.api_template, "open_template_by_id"):
                # 调用open_template_by_id方法打开对应模板
                self.api_template.open_template_by_id(api_template_id)
                print(f"成功跳转到接口模板编辑页面，模板ID: {api_template_id}")
            else:
                print("ApiTemplateManager类中没有open_template_by_id方法")

        except Exception as e:
            print(f"跳转到接口模板编辑页面失败: {str(e)}")

    def on_report_detail_requested(self, report_data):
        """处理报告详情请求，跳转到测试报告标签页并打开对应报告

        Args:
            report_data: 报告数据字典，包含报告ID等信息
        """
        try:
            print(f"收到报告详情请求，报告数据: {report_data}")

            # 跳转到测试报告标签页（索引为4）
            self.stacked_widget.setCurrentIndex(4)

            # 检查test_report对象是否有view_report_detail_by_id方法
            if hasattr(self.test_report, "view_report_detail_by_id"):
                # 从报告数据中获取报告ID
                report_id = report_data.get("id")
                if report_id:
                    # 调用view_report_detail_by_id方法打开对应报告
                    self.test_report.view_report_detail_by_id(report_id)
                else:
                    print("报告数据中没有找到ID字段")
            else:
                print("TestReportManager类中没有view_report_detail_by_id方法")

        except Exception as e:
            print(f"跳转到测试报告详情页面失败: {str(e)}")
            Toast.critical(self, "错误", f"打开报告详情失败: {str(e)}")

    def on_report_tab_requested(self, jump_data):
        """处理测试报告tab跳转请求，自动筛选调度相关的报告

        Args:
            jump_data: 跳转数据字典，包含调度信息和报告列表
        """
        try:
            # 跳转到测试报告标签页（索引为4）
            self.stacked_widget.setCurrentIndex(4)

            # 检查test_report对象是否有filter_by_scheduler方法
            if hasattr(self.test_report, "filter_by_scheduler"):
                # 调用filter_by_scheduler方法进行自动筛选
                self.test_report.filter_by_scheduler(jump_data)
            else:
                # 备用方案：直接显示报告列表
                self._handle_report_tab_fallback(jump_data)

        except Exception as e:
            print(f"跳转到测试报告tab并筛选失败: {str(e)}")
            Toast.critical(self, "错误", f"跳转到测试报告tab失败: {str(e)}")

    def _handle_report_tab_fallback(self, jump_data):
        """处理测试报告tab跳转的备用方案"""
        try:
            # 如果test_report对象有refresh_report_list方法，刷新列表
            if hasattr(self.test_report, "refresh_report_list"):
                self.test_report.refresh_report_list()

            # 显示提示信息
            scheduler_name = jump_data.get("scheduler", {}).get("name", "未知")
            report_count = len(jump_data.get("reports", []))

            from src.ui.widgets.toast_tips import Toast

            Toast.info(
                self,
                f"已跳转到测试报告tab，调度 '{scheduler_name}' 共有 {report_count} 条执行记录",
            )

        except Exception as e:
            print(f"备用方案处理失败: {str(e)}")

    def trigger_initial_business_change(self):
        """在所有页面创建和信号连接完成后，手动触发初始业务切换"""
        print("检查business_management对象和trigger_initial_business_change方法")
        print(
            f"business_management对象是否存在: {self.business_management is not None}"
        )
        if self.business_management:
            print(f"business_management对象类型: {type(self.business_management)}")
            print(
                f"是否有trigger_initial_business_change方法: {hasattr(self.business_management, 'trigger_initial_business_change')}"
            )

        if self.business_management and hasattr(
            self.business_management, "trigger_initial_business_change"
        ):
            print("开始调用business_management.trigger_initial_business_change()")
            self.business_management.trigger_initial_business_change()
            print("business_management.trigger_initial_business_change()调用完成")
        else:
            print("无法调用trigger_initial_business_change方法，条件不满足")

    def on_nav_changed(self, index):
        """处理导航栏切换事件（已弃用，保留方法签名）"""
        # 由于移除了左侧导航栏，此方法不再需要
        # 现在使用switch_to_subpage方法来切换页面
        pass

    def switch_to_subpage(self, subpage_name):
        """切换到指定的子页面
        
        Args:
            subpage_name: 子页面名称，如"业务管理"、"接口模板"等
        """
        # 检查是否已经初始化了实际界面
        if not hasattr(self, 'stacked_widget') or self.stacked_widget is None:
            print("接口自动化tab尚未初始化，无法切换子页面")
            return
        
        # 映射子页面名称到索引
        subpage_mapping = {
            "业务管理": 0,
            "接口模板": 1,
            "用例管理": 2,
            "定时调度": 3,
            "测试报告": 4,
            "全局工具": 5,
            "变量管理": 6
        }
        
        if subpage_name in subpage_mapping:
            subpage_index = subpage_mapping[subpage_name]
            # 切换到对应的子页面
            self.stacked_widget.setCurrentIndex(subpage_index)
            self.current_page_index = subpage_index
            print(f"已切换到接口自动化tab的{subpage_name}页面")
            
            # 如果切换到业务管理页面，更新操作按钮状态
            if subpage_index == 0 and self.business_management:
                if hasattr(self.business_management, "update_operation_buttons_visibility"):
                    self.business_management.update_operation_buttons_visibility()
        else:
            print(f"未知的子页面名称: {subpage_name}")
            # 默认显示第一个页面
            self.stacked_widget.setCurrentIndex(0)
            self.current_page_index = 0
