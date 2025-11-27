import os
import json
import sys
import webbrowser
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QGroupBox, QFormLayout,
                             QHeaderView, QInputDialog, QCheckBox, QSpinBox,
                             QListWidget, QListWidgetItem, QSplitter, QToolBar,
                             QAction, QToolButton, QMenu, QApplication, QDateTimeEdit,
                             QProgressBar, QTreeWidget, QTreeWidgetItem, QFrame, QFileDialog,
                             QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QDateTime, QUrl
from PyQt5.QtGui import QIcon, QFont, QColor, QDesktopServices, QCursor
from src.core.services.scheduler_service import UnifiedSchedulerService
from src.core.services.test_report_service import TestReportService
from src.core.services.test_case_service import TestCaseService
from src.core.models.interface_models import TestReport, TestStepResult
from src.utils.interface_utils.report_generator import HTMLReportGenerator
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelComboBox, NoWheelTabWidget


class ReportDetailDialog(QDialog):
    """报告详情对话框"""

    def __init__(self, parent=None, report_data=None):
        super().__init__(parent)
        self.report_data = report_data or {}
        self.report_service = TestReportService()
        self.init_ui()
        self.load_report_details()

    def init_ui(self):
        self.setWindowTitle(f"测试报告 - {self.report_data.get('report_name', '')}")
        self.setMinimumSize(1000, 700)

        layout = QVBoxLayout(self)

        # 创建Tab页
        tab_widget = NoWheelTabWidget()

        # 概览Tab
        overview_tab = QWidget()
        self.setup_overview_tab(overview_tab)

        # 步骤详情Tab
        steps_tab = QWidget()
        self.setup_steps_tab(steps_tab)

        # 日志Tab
        logs_tab = QWidget()
        self.setup_logs_tab(logs_tab)

        tab_widget.addTab(overview_tab, "概览")
        tab_widget.addTab(steps_tab, "步骤详情")
        tab_widget.addTab(logs_tab, "日志")

        # 按钮布局
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)

        layout.addWidget(tab_widget)
        layout.addWidget(button_box)

    def setup_overview_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 报告基本信息
        basic_info_group = QGroupBox("报告信息")
        basic_layout = QFormLayout(basic_info_group)

        self.report_name_label = QLabel()
        self.report_status_label = QLabel()
        self.report_case_label = QLabel()
        self.report_scheduler_label = QLabel()
        self.report_start_time_label = QLabel()
        self.report_end_time_label = QLabel()
        self.report_duration_label = QLabel()

        basic_layout.addRow("报告名称:", self.report_name_label)
        basic_layout.addRow("执行状态:", self.report_status_label)
        basic_layout.addRow("测试用例:", self.report_case_label)
        basic_layout.addRow("关联调度:", self.report_scheduler_label)
        basic_layout.addRow("开始时间:", self.report_start_time_label)
        basic_layout.addRow("结束时间:", self.report_end_time_label)
        basic_layout.addRow("执行时长:", self.report_duration_label)

        # 统计信息
        stats_group = QGroupBox("执行统计")
        stats_layout = QVBoxLayout(stats_group)

        # 进度条显示
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        stats_layout.addWidget(self.progress_bar)

        # 数字统计
        stats_grid = QHBoxLayout()

        # 总步骤数
        total_frame = QFrame()
        total_frame.setFrameStyle(QFrame.Box)
        total_layout = QVBoxLayout(total_frame)
        self.total_steps_label = QLabel("0")
        self.total_steps_label.setAlignment(Qt.AlignCenter)
        self.total_steps_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        total_layout.addWidget(self.total_steps_label)
        total_layout.addWidget(QLabel("总步骤"))
        stats_grid.addWidget(total_frame)

        # 通过数
        passed_frame = QFrame()
        passed_frame.setFrameStyle(QFrame.Box)
        passed_layout = QVBoxLayout(passed_frame)
        self.passed_steps_label = QLabel("0")
        self.passed_steps_label.setAlignment(Qt.AlignCenter)
        self.passed_steps_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #4CAF50;")
        passed_layout.addWidget(self.passed_steps_label)
        passed_layout.addWidget(QLabel("通过"))
        stats_grid.addWidget(passed_frame)

        # 失败数
        failed_frame = QFrame()
        failed_frame.setFrameStyle(QFrame.Box)
        failed_layout = QVBoxLayout(failed_frame)
        self.failed_steps_label = QLabel("0")
        self.failed_steps_label.setAlignment(Qt.AlignCenter)
        self.failed_steps_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #F44336;")
        failed_layout.addWidget(self.failed_steps_label)
        failed_layout.addWidget(QLabel("失败"))
        stats_grid.addWidget(failed_frame)

        # 错误数
        error_frame = QFrame()
        error_frame.setFrameStyle(QFrame.Box)
        error_layout = QVBoxLayout(error_frame)
        self.error_steps_label = QLabel("0")
        self.error_steps_label.setAlignment(Qt.AlignCenter)
        self.error_steps_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #FF9800;")
        error_layout.addWidget(self.error_steps_label)
        error_layout.addWidget(QLabel("错误"))
        stats_grid.addWidget(error_frame)

        # 通过率
        rate_frame = QFrame()
        rate_frame.setFrameStyle(QFrame.Box)
        rate_layout = QVBoxLayout(rate_frame)
        self.success_rate_label = QLabel("0%")
        self.success_rate_label.setAlignment(Qt.AlignCenter)
        self.success_rate_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3;")
        rate_layout.addWidget(self.success_rate_label)
        rate_layout.addWidget(QLabel("通过率"))
        stats_grid.addWidget(rate_frame)

        stats_layout.addLayout(stats_grid)

        layout.addWidget(basic_info_group)
        layout.addWidget(stats_group)
        layout.addStretch()

    def setup_steps_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 步骤列表
        self.steps_table = QTableWidget()
        self.steps_table.setColumnCount(7)
        self.steps_table.setHorizontalHeaderLabels([
            "步骤", "接口名称", "状态", "开始时间", "结束时间", "时长(秒)", "错误信息"
        ])
        self.steps_table.horizontalHeader().setStretchLastSection(True)
        self.steps_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.steps_table.doubleClicked.connect(self.show_step_detail)

        layout.addWidget(self.steps_table)

    def setup_logs_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 日志内容
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFont(QFont("Consolas", 10))

        layout.addWidget(QLabel("执行日志:"))
        layout.addWidget(self.logs_text)

    def load_report_details(self):
        """加载报告详情"""
        if not self.report_data:
            return

        # 基本信息
        self.report_name_label.setText(self.report_data.get('report_name', ''))

        status = self.report_data.get('status', '')
        status_text = {
            'success': '成功',
            'failure': '失败',
            'error': '错误',
            'running': '执行中'
        }.get(status, status)
        status_color = {
            'success': 'green',
            'failure': 'red',
            'error': 'orange',
            'running': 'blue'
        }.get(status, 'black')
        self.report_status_label.setText(f"<font color='{status_color}'>{status_text}</font>")

        # 测试用例信息
        case_name = self.report_data.get('case_name', '未知用例')
        self.report_case_label.setText(case_name)

        # 调度信息
        scheduler_name = self.report_data.get('scheduler_name', '手动执行')
        self.report_scheduler_label.setText(scheduler_name)

        # 时间信息
        start_time = self.report_data.get('start_time')
        if start_time:
            if isinstance(start_time, str):
                # 如果是字符串，直接显示或尝试解析
                start_text = start_time
            else:
                # 如果是datetime对象，格式化显示
                start_text = start_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            start_text = 'N/A'
        self.report_start_time_label.setText(start_text)

        end_time = self.report_data.get('end_time')
        if end_time:
            if isinstance(end_time, str):
                # 如果是字符串，直接显示或尝试解析
                end_text = end_time
            else:
                # 如果是datetime对象，格式化显示
                end_text = end_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            end_text = 'N/A'
        self.report_end_time_label.setText(end_text)

        duration = self.report_data.get('duration', 0)
        # 确保duration是数字类型
        try:
            duration_value = float(duration)
            self.report_duration_label.setText(f"{duration_value:.2f} 秒")
        except (ValueError, TypeError):
            # 如果转换失败，直接显示原始值
            self.report_duration_label.setText(f"{duration} 秒")

        # 统计信息
        total_steps = self.report_data.get('total_steps', 0)
        passed_steps = self.report_data.get('passed_steps', 0)
        failed_steps = self.report_data.get('failed_steps', 0)
        error_steps = self.report_data.get('error_steps', 0)

        self.total_steps_label.setText(str(total_steps))
        self.passed_steps_label.setText(str(passed_steps))
        self.failed_steps_label.setText(str(failed_steps))
        self.error_steps_label.setText(str(error_steps))

        # 计算通过率
        if total_steps > 0:
            success_rate = (passed_steps / total_steps) * 100
            self.success_rate_label.setText(f"{success_rate:.1f}%")
            self.progress_bar.setValue(int(success_rate))
        else:
            self.success_rate_label.setText("0%")
            self.progress_bar.setValue(0)

        # 加载步骤详情
        self.load_step_results()

        # 加载日志
        self.load_logs()

    def load_step_results(self):
        """加载步骤执行结果"""
        try:
            step_results = self.report_service.get_step_results_by_report(self.report_data['id'])
            self.steps_table.setRowCount(len(step_results))

            for row, step in enumerate(step_results):
                # 步骤序号
                self.steps_table.setItem(row, 0, QTableWidgetItem(str(step.get('step_order', 0))))

                # 接口名称
                api_name = step.get('api_name', '未知接口')
                self.steps_table.setItem(row, 1, QTableWidgetItem(api_name))

                # 状态
                status = step.get('status', 'skipped')
                status_text = {
                    'success': '成功',
                    'failure': '失败',
                    'error': '错误',
                    'skipped': '跳过'
                }.get(status, status)

                status_item = QTableWidgetItem(status_text)
                status_color = {
                    'success': QColor('green'),
                    'failure': QColor('red'),
                    'error': QColor('orange'),
                    'skipped': QColor('gray')
                }.get(status, QColor('black'))
                status_item.setForeground(status_color)
                self.steps_table.setItem(row, 2, status_item)

                # 开始时间
                start_time = step.get('start_time')
                if start_time:
                    if isinstance(start_time, str):
                        # 如果是字符串，直接显示或尝试解析
                        start_text = start_time
                    else:
                        # 如果是datetime对象，格式化显示
                        start_text = start_time.strftime('%H:%M:%S')
                else:
                    start_text = 'N/A'
                self.steps_table.setItem(row, 3, QTableWidgetItem(start_text))

                # 结束时间
                end_time = step.get('end_time')
                if end_time:
                    if isinstance(end_time, str):
                        # 如果是字符串，直接显示或尝试解析
                        end_text = end_time
                    else:
                        # 如果是datetime对象，格式化显示
                        end_text = end_time.strftime('%H:%M:%S')
                else:
                    end_text = 'N/A'
                self.steps_table.setItem(row, 4, QTableWidgetItem(end_text))

                # 执行时长
                duration = step.get('duration', 0)
                # 确保duration是数字类型
                try:
                    duration_value = float(duration)
                    self.steps_table.setItem(row, 5, QTableWidgetItem(f"{duration_value:.3f}"))
                except (ValueError, TypeError):
                    # 如果转换失败，直接显示原始值
                    self.steps_table.setItem(row, 5, QTableWidgetItem(f"{duration}"))

                # 错误信息
                error_msg = step.get('error_message', '')
                self.steps_table.setItem(row, 6, QTableWidgetItem(error_msg))

            # 调整列宽
            self.steps_table.resizeColumnsToContents()

        except Exception as e:
            print(f"加载步骤结果失败: {e}")

    def load_logs(self):
        """加载日志内容"""
        try:
            log_path = self.report_data.get('log_path')
            if log_path and os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8') as f:
                    logs = f.read()
                self.logs_text.setText(logs)
            else:
                # 从数据库加载日志或显示无日志
                self.logs_text.setText("暂无日志内容")
        except Exception as e:
            self.logs_text.setText(f"加载日志失败: {str(e)}")

    def show_step_detail(self):
        """显示步骤详情"""
        selected_items = self.steps_table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        step_order = self.steps_table.item(row, 0).text()

        # 这里可以打开步骤详情对话框，显示请求、响应、断言等详细信息
        QMessageBox.information(self, "步骤详情", f"查看步骤 {step_order} 的详细信息")

    def export_report(self):
        """导出报告"""
        try:
            # 选择导出路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出测试报告",
                f"{self.report_data['report_name']}.html",
                "HTML Files (*.html);;All Files (*)"
            )

            if file_path:
                # 生成HTML报告
                generator = HTMLReportGenerator()
                generator.generate_report(self.report_data, file_path)

                # 询问是否打开
                msg_box = QMessageBox(QMessageBox.Question, "导出成功", 
                                    "测试报告导出成功，是否立即打开？")
                confirm_button = msg_box.addButton("确认", QMessageBox.YesRole)
                cancel_button = msg_box.addButton("取消", QMessageBox.NoRole)
                msg_box.setDefaultButton(cancel_button)
                msg_box.exec_()
                reply = QMessageBox.Yes if msg_box.clickedButton() == confirm_button else QMessageBox.No

                if reply == QMessageBox.Yes:
                    webbrowser.open(f"file://{os.path.abspath(file_path)}")

                QMessageBox.information(self, "成功", "测试报告导出成功")

        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出测试报告失败: {str(e)}")


class TestReportManager(QWidget):
    """测试报告管理页面"""
    data_changed = pyqtSignal()  # 数据变化信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.report_service = None
        self.case_service = None
        self.scheduler_service = None
        self.init_ui()
        # 延迟加载数据，避免启动时数据库连接失败导致弹窗
        QTimer.singleShot(100, self.delayed_load_data)

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 筛选工具栏
        filter_toolbar = QToolBar()
        filter_toolbar.setIconSize(QSize(16, 16))

        # 时间筛选
        filter_toolbar.addWidget(QLabel("时间范围:"))
        self.time_range_combo = NoWheelComboBox()
        self.time_range_combo.addItems([
            "全部", "今天", "最近7天", "最近30天", "最近90天", "自定义"
        ])
        self.time_range_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_toolbar.addWidget(self.time_range_combo)

        # 状态筛选
        filter_toolbar.addWidget(QLabel("状态:"))
        self.status_combo = NoWheelComboBox()
        self.status_combo.addItems(["全部", "成功", "失败", "错误", "执行中"])
        self.status_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_toolbar.addWidget(self.status_combo)

        # 用例筛选
        filter_toolbar.addWidget(QLabel("测试用例:"))
        self.case_combo = NoWheelComboBox()
        self.case_combo.addItem("全部", 0)
        self.load_test_cases()
        self.case_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_toolbar.addWidget(self.case_combo)

        filter_toolbar.addSeparator()

        # 搜索框
        filter_toolbar.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("报告名称...")
        self.search_edit.textChanged.connect(self.on_filter_changed)
        self.search_edit.setMaximumWidth(200)
        filter_toolbar.addWidget(self.search_edit)

        main_layout.addWidget(filter_toolbar)

        # 操作工具栏
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))

        self.delete_action = QAction("删除报告", self)
        self.delete_action.triggered.connect(self.delete_selected_report)
        self.delete_action.setIcon(self.get_icon("delete.png"))

        self.refresh_action = QAction("刷新", self)
        self.refresh_action.triggered.connect(self.load_reports)
        self.refresh_action.setIcon(self.get_icon("refresh.png"))

        self.clear_action = QAction("清理报告", self)
        self.clear_action.triggered.connect(self.clear_old_reports)
        self.clear_action.setIcon(self.get_icon("clear.png"))

        toolbar.addAction(self.delete_action)
        toolbar.addSeparator()
        toolbar.addAction(self.refresh_action)
        toolbar.addAction(self.clear_action)

        main_layout.addWidget(toolbar)

        # 创建水平分割布局：左侧调度任务列表，右侧报告列表
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：调度任务列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 调度任务标题栏
        scheduler_title_layout = QHBoxLayout()
        
        # 标题标签
        title_label = QLabel("测试用例集")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #1976d2;
                padding: 8px 0px;
            }
        """)
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        scheduler_title_layout.addWidget(title_label)
        scheduler_title_layout.addStretch()
        
        left_layout.addLayout(scheduler_title_layout)
        
        # 调度任务列表
        self.scheduler_list_widget = QListWidget()
        self.scheduler_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                outline: 0;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #e9ecef;
                background-color: #ffffff;
                text-align: left;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
                font-weight: bold;
                border-left: 4px solid #1976d2;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
            QListWidget::item:selected:hover {
                background-color: #e3f2fd;
            }
        """)
        self.scheduler_list_widget.itemClicked.connect(self.on_scheduler_item_clicked)
        
        # 连接双击事件（快速查看调度详情）
        self.scheduler_list_widget.itemDoubleClicked.connect(self.on_scheduler_item_double_clicked)
        
        # 禁用右键菜单
        self.scheduler_list_widget.setContextMenuPolicy(Qt.NoContextMenu)
        
        left_layout.addWidget(self.scheduler_list_widget)
        
        # 添加提示信息
        tip_label = QLabel("点击调度任务查看对应的测试报告")
        tip_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #6c757d;
                padding: 8px 4px;
                background-color: #f8f9fa;
                border-radius: 4px;
                margin-top: 8px;
            }
        """)
        tip_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(tip_label)
        
        # 设置左侧宽度
        left_widget.setMaximumWidth(300)
        left_widget.setMinimumWidth(250)
        
        splitter.addWidget(left_widget)
        
        # 右侧：报告列表表格
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 报告列表表格 - 重构为树形分类表格，参考定时调度UI设计
        self.tree_widget = QTreeWidget()
        self.tree_widget.setColumnCount(9)
        self.tree_widget.setHeaderLabels([
            "序号", "报告名称", "用例数", "执行结果", "通过率", "开始时间", "结束时间", "执行耗时", "操作"
        ])
        
        # 设置固定列宽 - 参考定时调度UI设计
        self.tree_widget.setColumnWidth(0, 80)     # 序号
        self.tree_widget.setColumnWidth(1, 400)    # 报告名称
        self.tree_widget.setColumnWidth(2, 80)    # 用例数
        self.tree_widget.setColumnWidth(3, 150)    # 执行结果
        self.tree_widget.setColumnWidth(4, 150)    # 通过率
        self.tree_widget.setColumnWidth(5, 250)    # 开始时间
        self.tree_widget.setColumnWidth(6, 250)    # 结束时间
        self.tree_widget.setColumnWidth(7, 100)    # 执行耗时
        self.tree_widget.setColumnWidth(8, 300)    # 操作栏
        
        # 设置列宽调整模式为固定
        header = self.tree_widget.header()
        header.setSectionResizeMode(QHeaderView.Fixed)  # 所有列固定宽度
        header.setStretchLastSection(False)  # 最后一列不自动拉伸
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
        
        # 连接点击事件
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        
        # 参考定时调度UI的表格样式美化
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
                height: 48px;
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
        # 去除固定高度限制，让表格自适应高度

        right_layout.addWidget(self.tree_widget)
        
        splitter.addWidget(right_widget)
        
        # 设置分割比例和大小策略
        splitter.setStretchFactor(0, 0)  # 左侧不拉伸
        splitter.setStretchFactor(1, 1)  # 右侧拉伸
        
        # 设置分割器大小策略，让右侧可以充分拉伸
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        main_layout.addWidget(splitter, 1)  # 设置拉伸因子为1，让分割器占据主要空间

        # 状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        main_layout.addLayout(status_layout)

        self.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
            }
        """)

    def delayed_load_data(self):
        """延迟加载数据"""
        try:
            # 初始化服务
            self.report_service = TestReportService()
            self.case_service = TestCaseService()
            self.scheduler_service = UnifiedSchedulerService()
            
            # 加载调度任务列表
            self.load_schedulers()
            
            # 加载报告数据
            self.load_reports()
            
            # 启动定时刷新调度任务列表（每30秒刷新一次）
            self.scheduler_refresh_timer = QTimer(self)
            self.scheduler_refresh_timer.timeout.connect(self.load_schedulers)
            self.scheduler_refresh_timer.start(30000)  # 30秒
            
        except Exception as e:
            # 静默处理，不显示弹窗
            print(f"延迟加载数据失败: {str(e)}")

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

    def load_test_cases(self):
        """加载测试用例列表"""
        # 检查服务对象是否已初始化
        if self.case_service is None:
            print("测试用例服务未初始化，跳过加载测试用例")
            return
            
        try:
            cases = self.case_service.get_all_cases()
            for case in cases:
                self.case_combo.addItem(case['name'], case['id'])
        except Exception as e:
            print(f"加载测试用例失败: {e}")

    def load_schedulers(self):
        """加载测试用例集列表"""
        # 检查服务对象是否已初始化
        if self.scheduler_service is None:
            print("调度服务未初始化，跳过加载测试用例集")
            self.status_label.setText("调度服务未就绪")
            return
            
        try:
            # 清空调度任务列表
            self.scheduler_list_widget.clear()
            
            # 获取所有调度任务
            schedulers = self.scheduler_service.get_all_schedulers()
            
            if not schedulers:
                # 添加提示项
                empty_item = QListWidgetItem("暂无测试用例集")
                empty_item.setFlags(Qt.NoItemFlags)  # 不可选择
                empty_item.setForeground(QColor("#6c757d"))
                empty_item.setTextAlignment(Qt.AlignCenter)
                self.scheduler_list_widget.addItem(empty_item)
                self.status_label.setText("暂无测试用例集")
                return
                
            # 添加测试用例集到列表
            for scheduler in schedulers:
                scheduler_name = scheduler.get('name', '未知测试用例集')
                scheduler_id = scheduler.get('id', 0)
                
                # 创建列表项
                item = QListWidgetItem(scheduler_name)
                item.setData(Qt.UserRole, scheduler_id)
                
                # 设置简单的文本显示
                item.setFont(QFont("Microsoft YaHei", 11))
                item.setSizeHint(QSize(200, 40))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                
                # 设置统一的图标
                item.setIcon(self.get_icon("folder.png"))
                item.setToolTip(f"测试用例集: {scheduler_name}")
                
                self.scheduler_list_widget.addItem(item)
                
            self.status_label.setText(f"已加载 {len(schedulers)} 个测试用例集")
            
            # 如果有测试用例集，自动选择第一个并加载其报告
            if schedulers and self.scheduler_list_widget.count() > 0:
                first_item = self.scheduler_list_widget.item(0)
                if first_item.flags() != Qt.NoItemFlags:  # 确保不是提示项
                    self.scheduler_list_widget.setCurrentItem(first_item)
                    # 注释掉自动点击，避免自动触发日志
                    # self.on_scheduler_item_clicked(first_item)
            
        except Exception as e:
            print(f"加载测试用例集失败: {e}")
            self.status_label.setText("加载测试用例集失败")

    def on_scheduler_item_clicked(self, item):
        """点击测试用例集项事件"""
        try:
            # 检查是否为提示项（不可选择）
            if item.flags() == Qt.NoItemFlags:
                return
                
            # 获取选中的测试用例集ID
            scheduler_id = item.data(Qt.UserRole)
            
            # 调试信息：打印测试用例集ID
            # print(f"点击测试用例集，ID: {scheduler_id}")
            
            # 获取测试用例集名称（直接获取文本）
            scheduler_name = item.text()
            
            # 更新状态栏
            self.status_label.setText(f"正在加载测试用例集 '{scheduler_name}' 的报告...")
            
            # 加载该测试用例集的报告
            self.load_reports_by_scheduler(scheduler_id)
            
        except Exception as e:
            print(f"处理测试用例集点击事件失败: {e}")
            self.status_label.setText("处理测试用例集点击事件失败")

    def load_reports_by_scheduler(self, scheduler_id):
        """根据测试用例集ID加载对应的测试报告"""
        # 检查服务对象是否已初始化
        if self.report_service is None:
            print("报告服务未初始化，跳过加载报告")
            self.status_label.setText("报告服务未就绪")
            return
            
        try:
            # 获取筛选条件
            filters = self.get_filters()
            
            # 添加测试用例集ID筛选条件
            filters['scheduler_id'] = scheduler_id
            
            # 获取报告数据
            reports = self.report_service.get_reports_with_filters(filters)
            
            # 清空树形控件
            self.tree_widget.clear()
            
            if not reports:
                # 创建提示节点
                empty_item = QTreeWidgetItem(self.tree_widget)
                empty_item.setText(0, "1")
                empty_item.setText(1, "该测试用例集暂无测试报告")
                empty_item.setText(2, "0")
                empty_item.setText(3, "N/A")
                empty_item.setText(4, "0%")
                empty_item.setText(5, "N/A")
                empty_item.setText(6, "N/A")
                empty_item.setText(7, "N/A")
                empty_item.setText(8, "N/A")
                
                # 设置所有列文本居中对齐
                for i in range(9):
                    empty_item.setTextAlignment(i, Qt.AlignCenter)
                
                self.status_label.setText("该测试用例集暂无测试报告")
                return
            
            # 按开始时间排序（最新的在前）
            reports.sort(key=lambda x: x.get('start_time', ''), reverse=True)
            
            # 创建树形结构
            for i, report in enumerate(reports, start=1):
                item = QTreeWidgetItem(self.tree_widget)
                
                # 设置所有列文本居中对齐
                for j in range(9):
                    item.setTextAlignment(j, Qt.AlignCenter)
                
                # 序号
                item.setText(0, str(i))
                
                # 报告名称
                item.setText(1, report['report_name'])
                
                # 用例数（单个报告）
                item.setText(2, "1")
                
                # 状态
                status = report.get('status', '')
                status_text = {
                    'success': '成功',
                    'failure': '失败',
                    'error': '错误',
                    'running': '执行中'
                }.get(status, status)
                item.setText(3, status_text)
                
                # 通过率
                total_steps = report.get('total_steps', 0)
                passed_steps = report.get('passed_steps', 0)
                if total_steps > 0:
                    success_rate = (passed_steps / total_steps) * 100
                    rate_text = f"{success_rate:.1f}%"
                else:
                    rate_text = "0%"
                item.setText(4, rate_text)
                
                # 开始时间
                start_time = report.get('start_time')
                if start_time:
                    if isinstance(start_time, str):
                        start_text = start_time
                    else:
                        start_text = start_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    start_text = "N/A"
                item.setText(5, start_text)
                
                # 结束时间
                end_time = report.get('end_time')
                if end_time:
                    if isinstance(end_time, str):
                        end_text = end_time
                    else:
                        end_text = end_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    end_text = "N/A"
                item.setText(6, end_text)
                
                # 执行时长
                duration = report.get('duration', 0)
                duration_text = f"{duration:.2f}s" if duration > 0 else "N/A"
                item.setText(7, duration_text)
                
                # 操作栏
                item.setText(8, "查看详情 | 删除")
                
                # 设置数据
                item.setData(0, Qt.UserRole, report['id'])
            
            self.status_label.setText(f"已加载 {len(reports)} 个测试报告")
            
        except Exception as e:
            print(f"加载测试用例集报告失败: {e}")
            self.status_label.setText("加载测试用例集报告失败")

    def load_reports(self):
        """加载报告列表 - 修改为直接平铺显示所有报告"""
        # 检查服务对象是否已初始化
        if self.report_service is None:
            print("报告服务未初始化，跳过加载报告列表")
            self.status_label.setText("报告服务未就绪")
            return
            
        try:
            # 获取筛选条件
            filters = self.get_filters()
            reports = self.report_service.get_reports_with_filters(filters)

            # 清空树形控件
            self.tree_widget.clear()
            
            if not reports:
                # 创建提示节点
                empty_item = QTreeWidgetItem(self.tree_widget)
                empty_item.setText(0, "1")
                empty_item.setText(1, "暂无测试报告")
                empty_item.setText(2, "0")
                empty_item.setText(3, "N/A")
                empty_item.setText(4, "0%")
                empty_item.setText(5, "N/A")
                empty_item.setText(6, "N/A")
                empty_item.setText(7, "N/A")
                empty_item.setText(8, "N/A")
                
                # 设置所有列文本居中对齐
                for i in range(9):
                    empty_item.setTextAlignment(i, Qt.AlignCenter)
                
                self.status_label.setText("暂无测试报告")
                return
            
            # 按开始时间排序（最新的在前）
            reports.sort(key=lambda x: x.get('start_time', ''), reverse=True)
            
            # 直接平铺显示所有报告
            for i, report in enumerate(reports, start=1):
                item = QTreeWidgetItem(self.tree_widget)
                
                # 设置所有列文本居中对齐
                for j in range(9):
                    item.setTextAlignment(j, Qt.AlignCenter)
                
                # 序号
                item.setText(0, str(i))
                
                # 报告名称
                item.setText(1, report['report_name'])
                
                # 用例数（单个报告）
                item.setText(2, "1")
                
                # 状态
                status = report.get('status', '')
                status_text = {
                    'success': '成功',
                    'failure': '失败',
                    'error': '错误',
                    'running': '执行中'
                }.get(status, status)
                item.setText(3, status_text)
                
                # 通过率
                total_steps = report.get('total_steps', 0)
                passed_steps = report.get('passed_steps', 0)
                if total_steps > 0:
                    success_rate = (passed_steps / total_steps) * 100
                    rate_text = f"{success_rate:.1f}%"
                else:
                    rate_text = "0%"
                item.setText(4, rate_text)
                
                # 开始时间
                start_time = report.get('start_time')
                if start_time:
                    if isinstance(start_time, str):
                        start_text = start_time
                    else:
                        start_text = start_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    start_text = "N/A"
                item.setText(5, start_text)
                
                # 结束时间
                end_time = report.get('end_time')
                if end_time:
                    if isinstance(end_time, str):
                        end_text = end_time
                    else:
                        end_text = end_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    end_text = "N/A"
                item.setText(6, end_text)
                
                # 执行时长
                duration = report.get('duration', 0)
                duration_text = f"{duration:.2f}s" if duration > 0 else "N/A"
                item.setText(7, duration_text)
                
                # 操作栏
                item.setText(8, "查看详情 | 删除")
                
                # 设置数据
                item.setData(0, Qt.UserRole, report['id'])
            
            self.status_label.setText(f"已加载 {len(reports)} 个测试报告")

        except Exception as e:
            # 静默处理，不显示弹窗
            print(f"加载测试报告失败: {str(e)}")
            self.status_label.setText("加载失败")

    def get_filters(self):
        """获取筛选条件"""
        filters = {}

        # 时间范围
        time_range = self.time_range_combo.currentText()
        if time_range != "全部":
            end_date = datetime.now()
            if time_range == "今天":
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_range == "最近7天":
                start_date = end_date - timedelta(days=7)
            elif time_range == "最近30天":
                start_date = end_date - timedelta(days=30)
            elif time_range == "最近90天":
                start_date = end_date - timedelta(days=90)
            else:  # 自定义
                # 这里可以添加自定义时间选择器
                start_date = end_date - timedelta(days=30)

            filters['start_date'] = start_date
            filters['end_date'] = end_date

        # 状态
        status_map = {
            "成功": "success",
            "失败": "failure",
            "错误": "error",
            "执行中": "running"
        }
        status_text = self.status_combo.currentText()
        if status_text != "全部":
            filters['status'] = status_map.get(status_text, status_text)

        # 测试用例
        case_id = self.case_combo.currentData()
        if case_id:
            filters['case_id'] = case_id

        # 搜索关键词
        search_text = self.search_edit.text().strip()
        if search_text:
            filters['search'] = search_text

        return filters

    def on_filter_changed(self):
        """筛选条件变化"""
        self.load_reports()

    def on_tree_item_clicked(self, item, column):
        """处理树形表格点击事件"""
        # 获取节点数据
        node_data = item.data(0, Qt.UserRole)
        
        # 判断是父节点（调度组）还是子节点（报告记录）
        if isinstance(node_data, str) and node_data.startswith("scheduler_"):
            # 父节点：只有点击序号列（第0列）时才展开/折叠
            if column == 0:
                item.setExpanded(not item.isExpanded())
            # 父节点：点击操作栏时处理详情和删除
            elif column == 8:
                # 获取操作栏文本
                action_text = item.text(8)
                # 获取点击位置，判断是点击"查看详情"还是"删除"
                cursor_pos = self.tree_widget.viewport().mapFromGlobal(QCursor.pos())
                item_rect = self.tree_widget.visualItemRect(item)
                column_rect = self.tree_widget.visualRect(self.tree_widget.indexFromItem(item, 8))
                
                # 计算操作栏内点击位置
                click_x_in_column = cursor_pos.x() - column_rect.x()
                column_width = column_rect.width()
                
                # 判断点击的是"查看详情"还是"删除"
                if click_x_in_column < column_width / 2:
                    # 点击"查看详情"
                    if item.parent() is None:  # 父节点
                        # 父节点查看第一条报告的详情
                        if not isinstance(node_data, str) or not node_data.startswith("scheduler_"):
                            self.view_report_detail_by_id(node_data)
                else:
                    # 点击"删除"
                    if item.parent() is None:  # 父节点
                        # 父节点删除整个调度组的所有报告
                        self.delete_scheduler_reports(node_data)
        else:
            # 子节点：点击操作栏时处理详情和删除
            if column == 8:
                # 获取操作栏文本
                action_text = item.text(8)
                # 获取点击位置，判断是点击"查看详情"还是"删除"
                cursor_pos = self.tree_widget.viewport().mapFromGlobal(QCursor.pos())
                item_rect = self.tree_widget.visualItemRect(item)
                column_rect = self.tree_widget.visualRect(self.tree_widget.indexFromItem(item, 8))
                
                # 计算操作栏内点击位置
                click_x_in_column = cursor_pos.x() - column_rect.x()
                column_width = column_rect.width()
                
                # 判断点击的是"查看详情"还是"删除"
                if click_x_in_column < column_width / 2:
                    # 点击"查看详情"
                    report_id = node_data
                    if report_id:
                        self.view_report_detail_by_id(report_id)
                else:
                    # 点击"删除"
                    report_id = node_data
                    if report_id:
                        self.delete_report_by_id(report_id)
            # 子节点：点击其他列时选中该行
            else:
                self.tree_widget.setCurrentItem(item)

    def get_selected_report_id(self):
        """获取选中的报告ID - 适配树形表格"""
        selected_items = self.tree_widget.selectedItems()
        if selected_items:
            item = selected_items[0]
            # 检查是否是子节点（报告记录）
            if item.parent() is not None:
                report_id = item.data(0, Qt.UserRole)
                # 确保不是调度组ID
                if report_id and not str(report_id).startswith("scheduler_"):
                    return report_id
        return None

    def get_selected_report_data(self):
        """获取选中的报告数据"""
        report_id = self.get_selected_report_id()
        if report_id:
            return self.report_service.get_report_with_details(report_id)
        return None

    def view_report_detail(self):
        """查看报告详情"""
        report_data = self.get_selected_report_data()
        if not report_data:
            QMessageBox.warning(self, "提示", "请先选择一个测试报告")
            return

        dialog = ReportDetailDialog(self, report_data)
        dialog.exec_()

    def view_report_detail_by_id(self, report_id):
        """根据报告ID查看详情"""
        if not report_id:
            QMessageBox.warning(self, "提示", "无效的报告ID")
            return

        try:
            report_data = self.report_service.get_report_with_details(report_id)
            if report_data:
                dialog = ReportDetailDialog(self, report_data)
                dialog.exec_()
            else:
                QMessageBox.warning(self, "提示", "报告数据不存在")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载报告详情失败: {str(e)}")

    def delete_scheduler_reports(self, scheduler_data):
        """删除调度组的所有报告"""
        if not scheduler_data:
            return
            
        # 确认删除
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个调度组的所有测试报告吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # 如果是调度组标识，需要先获取调度组名称
                if isinstance(scheduler_data, str) and scheduler_data.startswith("scheduler_"):
                    scheduler_name = scheduler_data.replace("scheduler_", "")
                    # 获取该调度组的所有报告
                    filters = {'scheduler_name': scheduler_name}
                    reports = self.report_service.get_reports_with_filters(filters)
                    
                    # 删除所有报告
                    success_count = 0
                    for report in reports:
                        if self.report_service.delete_report(report['id']):
                            success_count += 1
                    
                    if success_count > 0:
                        QMessageBox.information(self, "成功", f"成功删除 {success_count} 个测试报告")
                        # 重新加载报告列表
                        self.load_reports()
                    else:
                        QMessageBox.warning(self, "警告", "报告删除失败")
                else:
                    # 如果是单个报告ID，直接删除
                    self.delete_report_by_id(scheduler_data)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除报告失败: {str(e)}")

    def delete_report_by_id(self, report_id):
        """根据报告ID删除报告"""
        if not report_id:
            return
            
        # 确认删除
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个测试报告吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # 删除报告
                success = self.report_service.delete_report(report_id)
                if success:
                    QMessageBox.information(self, "成功", "报告删除成功")
                    # 重新加载报告列表
                    self.load_reports()
                else:
                    QMessageBox.warning(self, "警告", "报告删除失败")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除报告失败: {str(e)}")



    def delete_selected_report(self):
        """删除选中的报告"""
        report_data = self.get_selected_report_data()
        if not report_data:
            QMessageBox.warning(self, "提示", "请先选择一个测试报告")
            return

        msg_box = QMessageBox(QMessageBox.Question, "确认删除", 
                            f"确定要删除报告 '{report_data['report_name']}' 吗？\n此操作将同时删除相关的步骤执行记录！")
        confirm_button = msg_box.addButton("确认", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_button)
        msg_box.exec_()
        reply = QMessageBox.Yes if msg_box.clickedButton() == confirm_button else QMessageBox.No

        if reply == QMessageBox.Yes:
            try:
                self.report_service.delete_report(report_data['id'])
                self.load_reports()
                self.data_changed.emit()
                QMessageBox.information(self, "成功", "报告删除成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除报告失败: {str(e)}")

    def clear_old_reports(self):
        """清理旧报告"""
        try:
            # 询问保留天数
            days, ok = QInputDialog.getInt(
                self, "清理报告",
                "保留最近多少天的报告:",
                30, 1, 365, 1
            )

            if ok:
                # 确认清理
                msg_box = QMessageBox(QMessageBox.Question, "确认清理", 
                                    f"确定要清理 {days} 天前的测试报告吗？此操作不可恢复！")
                confirm_button = msg_box.addButton("确认", QMessageBox.YesRole)
                cancel_button = msg_box.addButton("取消", QMessageBox.NoRole)
                msg_box.setDefaultButton(cancel_button)
                msg_box.exec_()
                reply = QMessageBox.Yes if msg_box.clickedButton() == confirm_button else QMessageBox.No

                if reply == QMessageBox.Yes:
                    deleted_count = self.report_service.delete_old_reports(days)
                    self.load_reports()
                    self.data_changed.emit()
                    QMessageBox.information(self, "成功", f"已清理 {deleted_count} 个旧报告")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"清理报告失败: {str(e)}")

    def on_scheduler_item_double_clicked(self, item):
        """双击调度任务项事件 - 快速查看调度详情"""
        try:
            # 检查是否为提示项（不可选择）
            if item.flags() == Qt.NoItemFlags:
                return
                
            # 获取选中的调度任务ID
            scheduler_id = item.data(Qt.UserRole)
            
            # 获取调度详细信息
            scheduler = self.scheduler_service.get_scheduler_by_id(scheduler_id)
            if not scheduler:
                QMessageBox.warning(self, "提示", "调度任务不存在")
                return
            
            # 显示调度详情对话框
            self.show_scheduler_detail_dialog(scheduler)
            
        except Exception as e:
            print(f"处理调度任务双击事件失败: {e}")
            QMessageBox.critical(self, "错误", f"查看调度详情失败: {str(e)}")



    def show_scheduler_detail_dialog(self, scheduler):
        """显示调度详情对话框"""
        try:
            # 创建详情对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("调度任务详情")
            dialog.setModal(True)
            dialog.resize(500, 400)
            
            layout = QVBoxLayout(dialog)
            
            # 创建表单布局
            form_layout = QFormLayout()
            form_layout.setLabelAlignment(Qt.AlignRight)
            
            # 调度名称
            name_label = QLabel(scheduler.get('name', '未知调度'))
            name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            form_layout.addRow("调度名称:", name_label)
            
            # 状态
            status_text = "已启用" if scheduler.get('enabled', False) else "已禁用"
            status_color = "#28a745" if scheduler.get('enabled', False) else "#dc3545"
            status_label = QLabel(status_text)
            status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
            form_layout.addRow("状态:", status_label)
            
            # Cron表达式
            cron_label = QLabel(scheduler.get('cron_expression', 'N/A'))
            form_layout.addRow("Cron表达式:", cron_label)
            
            # 上次执行时间
            last_run = scheduler.get('last_run_at')
            last_run_text = last_run.strftime('%Y-%m-%d %H:%M:%S') if last_run else "N/A"
            last_run_label = QLabel(last_run_text)
            form_layout.addRow("上次执行时间:", last_run_label)
            
            # 下次执行时间
            next_run = scheduler.get('next_run_at')
            next_run_text = next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else "N/A"
            next_run_label = QLabel(next_run_text)
            form_layout.addRow("下次执行时间:", next_run_label)
            
            # 创建时间
            created_at = scheduler.get('created_at')
            created_text = created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else "N/A"
            created_label = QLabel(created_text)
            form_layout.addRow("创建时间:", created_label)
            
            layout.addLayout(form_layout)
            
            # 添加关闭按钮
            button_box = QDialogButtonBox(QDialogButtonBox.Close)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            dialog.exec_()
            
        except Exception as e:
            print(f"显示调度详情对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"显示调度详情失败: {str(e)}")

    def toggle_scheduler_status(self, scheduler_id, enable):
        """切换调度任务状态"""
        try:
            # 更新调度状态
            success = self.scheduler_service.update_scheduler_status(scheduler_id, enable)
            
            if success:
                action_text = "启用" if enable else "禁用"
                QMessageBox.information(self, "成功", f"调度任务{action_text}成功")
                # 刷新调度任务列表
                self.load_schedulers()
            else:
                QMessageBox.warning(self, "警告", "操作失败，请重试")
                
        except Exception as e:
            print(f"切换调度状态失败: {e}")
            QMessageBox.critical(self, "错误", f"操作失败: {str(e)}")


