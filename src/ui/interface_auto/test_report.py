import os
import json
import webbrowser
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QTabWidget, QGroupBox, QFormLayout, QComboBox,
                             QHeaderView, QInputDialog, QCheckBox, QSpinBox,
                             QListWidget, QListWidgetItem, QSplitter, QToolBar,
                             QAction, QToolButton, QMenu, QApplication, QDateTimeEdit,
                             QProgressBar, QTreeWidget, QTreeWidgetItem, QFrame, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QDateTime, QUrl
from PyQt5.QtGui import QIcon, QFont, QColor, QDesktopServices
from src.core.services.scheduler_service import SchedulerService
from src.core.services.test_report_service import TestReportService
from src.core.services.test_case_service import TestCaseService
from src.core.models.interface_models import TestReport, TestStepResult
from src.utils.interface_utils.report_generator import HTMLReportGenerator


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
        tab_widget = QTabWidget()

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

        # 添加导出按钮
        export_btn = QPushButton("导出报告")
        export_btn.clicked.connect(self.export_report)
        button_box.addButton(export_btn, QDialogButtonBox.ActionRole)

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
        start_text = start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'N/A'
        self.report_start_time_label.setText(start_text)

        end_time = self.report_data.get('end_time')
        end_text = end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else 'N/A'
        self.report_end_time_label.setText(end_text)

        duration = self.report_data.get('duration', 0)
        self.report_duration_label.setText(f"{duration:.2f} 秒")

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
                start_text = start_time.strftime('%H:%M:%S') if start_time else 'N/A'
                self.steps_table.setItem(row, 3, QTableWidgetItem(start_text))

                # 结束时间
                end_time = step.get('end_time')
                end_text = end_time.strftime('%H:%M:%S') if end_time else 'N/A'
                self.steps_table.setItem(row, 4, QTableWidgetItem(end_text))

                # 执行时长
                duration = step.get('duration', 0)
                self.steps_table.setItem(row, 5, QTableWidgetItem(f"{duration:.3f}"))

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
                reply = QMessageBox.question(
                    self, "导出成功",
                    "测试报告导出成功，是否立即打开？",
                    QMessageBox.Yes | QMessageBox.No
                )

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
        self.report_service = TestReportService()
        self.case_service = TestCaseService()
        self.scheduler_service = SchedulerService()
        self.init_ui()
        self.load_reports()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 筛选工具栏
        filter_toolbar = QToolBar()
        filter_toolbar.setIconSize(QSize(16, 16))

        # 时间筛选
        filter_toolbar.addWidget(QLabel("时间范围:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems([
            "全部", "今天", "最近7天", "最近30天", "最近90天", "自定义"
        ])
        self.time_range_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_toolbar.addWidget(self.time_range_combo)

        # 状态筛选
        filter_toolbar.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["全部", "成功", "失败", "错误", "执行中"])
        self.status_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_toolbar.addWidget(self.status_combo)

        # 用例筛选
        filter_toolbar.addWidget(QLabel("测试用例:"))
        self.case_combo = QComboBox()
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

        self.view_action = QAction("查看详情", self)
        self.view_action.triggered.connect(self.view_report_detail)
        self.view_action.setIcon(self.get_icon("view.png"))

        self.export_action = QAction("导出报告", self)
        self.export_action.triggered.connect(self.export_selected_report)
        self.export_action.setIcon(self.get_icon("export.png"))

        self.delete_action = QAction("删除报告", self)
        self.delete_action.triggered.connect(self.delete_selected_report)
        self.delete_action.setIcon(self.get_icon("delete.png"))

        self.refresh_action = QAction("刷新", self)
        self.refresh_action.triggered.connect(self.load_reports)
        self.refresh_action.setIcon(self.get_icon("refresh.png"))

        self.clear_action = QAction("清理报告", self)
        self.clear_action.triggered.connect(self.clear_old_reports)
        self.clear_action.setIcon(self.get_icon("clear.png"))

        toolbar.addAction(self.view_action)
        toolbar.addAction(self.export_action)
        toolbar.addAction(self.delete_action)
        toolbar.addSeparator()
        toolbar.addAction(self.refresh_action)
        toolbar.addAction(self.clear_action)

        main_layout.addWidget(toolbar)

        # 报告列表表格
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(8)
        self.table_widget.setHorizontalHeaderLabels([
            "报告名称", "测试用例", "关联调度", "状态", "通过率", "开始时间", "结束时间", "执行时长"
        ])
        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_table_context_menu)
        self.table_widget.doubleClicked.connect(self.view_report_detail)

        main_layout.addWidget(self.table_widget)

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

    def get_icon(self, icon_name):
        """获取图标"""
        try:
            icon_path = os.path.join("src", "ui", "interface_auto", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
        except:
            pass
        return QIcon()

    def load_test_cases(self):
        """加载测试用例列表"""
        try:
            cases = self.case_service.get_all_cases()
            for case in cases:
                self.case_combo.addItem(case['name'], case['id'])
        except Exception as e:
            print(f"加载测试用例失败: {e}")

    def load_reports(self):
        """加载报告列表"""
        try:
            # 获取筛选条件
            filters = self.get_filters()
            reports = self.report_service.get_reports_with_filters(filters)

            self.table_widget.setRowCount(len(reports))

            for row, report in enumerate(reports):
                # 报告名称
                name_item = QTableWidgetItem(report['report_name'])
                name_item.setData(Qt.UserRole, report['id'])
                self.table_widget.setItem(row, 0, name_item)

                # 测试用例
                case_name = report.get('case_name', '未知用例')
                self.table_widget.setItem(row, 1, QTableWidgetItem(case_name))

                # 关联调度
                scheduler_name = report.get('scheduler_name', '手动执行')
                self.table_widget.setItem(row, 2, QTableWidgetItem(scheduler_name))

                # 状态
                status = report.get('status', '')
                status_text = {
                    'success': '成功',
                    'failure': '失败',
                    'error': '错误',
                    'running': '执行中'
                }.get(status, status)

                status_item = QTableWidgetItem(status_text)
                status_color = {
                    'success': QColor('green'),
                    'failure': QColor('red'),
                    'error': QColor('orange'),
                    'running': QColor('blue')
                }.get(status, QColor('black'))
                status_item.setForeground(status_color)
                self.table_widget.setItem(row, 3, status_item)

                # 通过率
                total_steps = report.get('total_steps', 0)
                passed_steps = report.get('passed_steps', 0)
                if total_steps > 0:
                    success_rate = (passed_steps / total_steps) * 100
                    rate_text = f"{success_rate:.1f}%"
                else:
                    rate_text = "0%"
                self.table_widget.setItem(row, 4, QTableWidgetItem(rate_text))

                # 开始时间
                start_time = report.get('start_time')
                start_text = start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else "N/A"
                self.table_widget.setItem(row, 5, QTableWidgetItem(start_text))

                # 结束时间
                end_time = report.get('end_time')
                end_text = end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else "N/A"
                self.table_widget.setItem(row, 6, QTableWidgetItem(end_text))

                # 执行时长
                duration = report.get('duration', 0)
                duration_text = f"{duration:.2f}s" if duration > 0 else "N/A"
                self.table_widget.setItem(row, 7, QTableWidgetItem(duration_text))

            # 调整列宽
            self.table_widget.resizeColumnsToContents()
            self.status_label.setText(f"共 {len(reports)} 个测试报告")

        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"加载测试报告失败: {str(e)}")
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

    def get_selected_report_id(self):
        """获取选中的报告ID"""
        selected_items = self.table_widget.selectedItems()
        if selected_items:
            return selected_items[0].data(Qt.UserRole)
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

    def export_selected_report(self):
        """导出选中的报告"""
        report_data = self.get_selected_report_data()
        if not report_data:
            QMessageBox.warning(self, "提示", "请先选择一个测试报告")
            return

        try:
            # 选择导出路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出测试报告",
                f"{report_data['report_name']}.html",
                "HTML Files (*.html);;All Files (*)"
            )

            if file_path:
                # 生成HTML报告
                generator = HTMLReportGenerator()
                generator.generate_report(report_data, file_path)

                # 询问是否打开
                reply = QMessageBox.question(
                    self, "导出成功",
                    "测试报告导出成功，是否立即打开？",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    webbrowser.open(f"file://{os.path.abspath(file_path)}")

                QMessageBox.information(self, "成功", "测试报告导出成功")

        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出测试报告失败: {str(e)}")

    def delete_selected_report(self):
        """删除选中的报告"""
        report_data = self.get_selected_report_data()
        if not report_data:
            QMessageBox.warning(self, "提示", "请先选择一个测试报告")
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除报告 '{report_data['report_name']}' 吗？\n此操作将同时删除相关的步骤执行记录！",
            QMessageBox.Yes | QMessageBox.No
        )

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
                reply = QMessageBox.question(
                    self, "确认清理",
                    f"确定要清理 {days} 天前的测试报告吗？此操作不可恢复！",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    deleted_count = self.report_service.delete_old_reports(days)
                    self.load_reports()
                    self.data_changed.emit()
                    QMessageBox.information(self, "成功", f"已清理 {deleted_count} 个旧报告")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"清理报告失败: {str(e)}")

    def show_table_context_menu(self, position):
        """显示表格右键菜单"""
        item = self.table_widget.itemAt(position)
        if not item:
            return

        from PyQt5.QtWidgets import QMenu, QAction

        menu = QMenu(self)

        view_action = QAction("查看详情", self)
        view_action.triggered.connect(self.view_report_detail)
        menu.addAction(view_action)

        export_action = QAction("导出报告", self)
        export_action.triggered.connect(self.export_selected_report)
        menu.addAction(export_action)

        menu.addSeparator()

        delete_action = QAction("删除报告", self)
        delete_action.triggered.connect(self.delete_selected_report)
        menu.addAction(delete_action)

        menu.exec_(self.table_widget.mapToGlobal(position))