import os
import sys
import math
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QGroupBox, QFormLayout,QHeaderView, QInputDialog,
                             QListWidget, QListWidgetItem, QSplitter, QToolBar,
                             QTreeWidget, QTreeWidgetItem, 
                             QSizePolicy, QScrollArea, QStackedLayout, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QRect, QThread
from PyQt5.QtGui import QIcon, QFont, QColor, QCursor, QBrush, QPainter, QPen
from src.core.services.scheduler_service import UnifiedSchedulerService
from src.core.services.test_report_service import TestReportService
from src.core.services.test_case_service import TestCaseService
from src.core.services.project_service import ProjectService
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelComboBox
from src.utils.css_utils import get_toolbar_combobox_style, get_combobox_style
from PyQt5.QtGui import QTextCursor
from src.ui.widgets.toast_tips import Toast


class ReportLoadingThread(QThread):
    """报告加载线程 - 异步加载报告数据"""
    
    loading_finished = pyqtSignal(list)  # 加载完成信号
    loading_progress = pyqtSignal(int, int)  # 加载进度信号
    
    def __init__(self, report_service, filters, parent=None):
        super().__init__(parent)
        self.report_service = report_service
        self.filters = filters
        
    def run(self):
        """线程执行函数"""
        try:
            # 获取报告数据
            reports = self.report_service.get_reports_with_filters(self.filters)
            
            # 发送加载完成信号
            self.loading_finished.emit(reports)
            
        except Exception as e:
            print(f"报告加载线程出错: {str(e)}")
            self.loading_finished.emit([])

class PaginationReportLoadingThread(QThread):
    """分页报告加载线程 - 异步加载分页报告数据"""
    
    loading_finished = pyqtSignal(dict)  # 加载完成信号，返回分页数据
    
    def __init__(self, report_service, filters, parent=None):
        super().__init__(parent)
        self.report_service = report_service
        self.filters = filters
        
    def run(self):
        """线程执行函数"""
        try:
            # 获取分页报告数据
            result = self.report_service.get_reports_with_pagination(self.filters)
            
            # 发送加载完成信号
            self.loading_finished.emit(result)
            
        except Exception as e:
            # 发送空数据
            self.loading_finished.emit({
                'data': [],
                'pagination': {
                    'total': 0,
                    'page': 1,
                    'page_size': 20,
                    'total_pages': 0,
                    'has_prev': False,
                    'has_next': False
                }
            })
            print(f"报告加载线程出错: {str(e)}")
            self.loading_finished.emit([])


class PieChartWidget(QWidget):
    """现代饼图组件 - 支持鼠标悬浮提示"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.passed_cases = 0
        self.failed_cases = 0
        self.error_cases = 0
        self.total_cases = 0
        self.hovered_slice = None  # 当前悬停的扇区
        self.setMinimumSize(200, 200)
        self.setMouseTracking(True)  # 启用鼠标跟踪
        
        # 现代配色方案
        self.colors = {
            'passed': QColor(34, 197, 94),   # 现代绿色
            'failed': QColor(239, 68, 68),   # 现代红色
            'error': QColor(245, 158, 11)    # 现代橙色
        }
        
        # 悬停颜色（更亮的版本）
        self.hover_colors = {
            'passed': QColor(74, 222, 128),
            'failed': QColor(248, 113, 113),
            'error': QColor(251, 191, 36)
        }
        
    def set_data(self, passed_cases, failed_cases, error_cases):
        """设置饼图数据"""
        self.passed_cases = passed_cases
        self.failed_cases = failed_cases
        self.error_cases = error_cases
        self.total_cases = passed_cases + failed_cases + error_cases
        self.update()
        
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 检测悬停的扇区"""
        if self.total_cases == 0:
            return
            
        # 计算鼠标位置相对于饼图中心的位置
        size = min(self.width(), self.height()) - 40
        center_x = self.width() // 2
        center_y = self.height() // 2
        mouse_x = event.x()
        mouse_y = event.y()
        
        # 计算鼠标到中心的距离和角度
        dx = mouse_x - center_x
        dy = mouse_y - center_y
        distance = (dx**2 + dy**2)**0.5
        
        # 如果鼠标在饼图范围内
        if distance <= size // 2:
            # 计算角度（0-360度，从右侧开始顺时针）
            # 修正角度计算，确保与绘制顺序一致
            angle = (360 - math.degrees(math.atan2(dy, dx))) % 360
            
            # 计算每个扇区的角度范围（十六分度制，与绘制一致）
            passed_angle = 360 * self.passed_cases / self.total_cases
            failed_angle = 360 * self.failed_cases / self.total_cases
            error_angle = 360 * self.error_cases / self.total_cases
            
            # 确定悬停的扇区（从0度开始顺时针，与绘制顺序一致）
            current_angle = 0
            if self.passed_cases > 0 and angle < current_angle + passed_angle:
                self.hovered_slice = 'passed'
            elif self.failed_cases > 0 and angle < current_angle + passed_angle + failed_angle:
                self.hovered_slice = 'failed'
            elif self.error_cases > 0 and angle < current_angle + passed_angle + failed_angle + error_angle:
                self.hovered_slice = 'error'
            else:
                self.hovered_slice = None
        else:
            self.hovered_slice = None
            
        self.update()
        
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.hovered_slice = None
        self.update()
        
    def paintEvent(self, event):
        """绘制现代饼图"""
        if self.total_cases == 0:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置饼图区域（带内边距）
        size = min(self.width(), self.height()) - 40
        rect = QRect((self.width() - size) // 2, (self.height() - size) // 2, size, size)
        
        # 计算角度（十六分度制）
        passed_angle = int(5760 * self.passed_cases / self.total_cases)
        failed_angle = int(5760 * self.failed_cases / self.total_cases)
        error_angle = int(5760 * self.error_cases / self.total_cases)
        
        # 绘制饼图 - 使用现代样式
        start_angle = 0
        
        # 通过的部分
        if self.passed_cases > 0:
            color = self.hover_colors['passed'] if self.hovered_slice == 'passed' else self.colors['passed']
            painter.setPen(QPen(QColor(255, 255, 255, 180), 3))
            painter.setBrush(QBrush(color))
            painter.drawPie(rect, start_angle, passed_angle)
            start_angle += passed_angle
        
        # 失败的部分
        if self.failed_cases > 0:
            color = self.hover_colors['failed'] if self.hovered_slice == 'failed' else self.colors['failed']
            painter.setPen(QPen(QColor(255, 255, 255, 180), 3))
            painter.setBrush(QBrush(color))
            painter.drawPie(rect, start_angle, failed_angle)
            start_angle += failed_angle
        
        # 错误的部分
        if self.error_cases > 0:
            color = self.hover_colors['error'] if self.hovered_slice == 'error' else self.colors['error']
            painter.setPen(QPen(QColor(255, 255, 255, 180), 3))
            painter.setBrush(QBrush(color))
            painter.drawPie(rect, start_angle, error_angle)
        
        # 绘制中心圆形装饰
        center_size = size // 3
        center_rect = QRect(
            (self.width() - center_size) // 2,
            (self.height() - center_size) // 2,
            center_size, center_size
        )
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255, 30)))
        painter.drawEllipse(center_rect)
        
        # 绘制悬停提示
        if self.hovered_slice:
            self.draw_tooltip(painter, event)
    
    def draw_tooltip(self, painter, event):
        """绘制悬停提示"""
        if not self.hovered_slice:
            return
            
        # 获取当前扇区的数据
        if self.hovered_slice == 'passed':
            count = self.passed_cases
            percentage = (self.passed_cases / self.total_cases) * 100
            label = '通过'
        elif self.hovered_slice == 'failed':
            count = self.failed_cases
            percentage = (self.failed_cases / self.total_cases) * 100
            label = '失败'
        else:
            count = self.error_cases
            percentage = (self.error_cases / self.total_cases) * 100
            label = '错误'
        
        # 设置提示文本
        text = f"{label}: {count} ({percentage:.1f}%)"
        
        # 计算提示框位置
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        
        text_rect = painter.fontMetrics().boundingRect(text)
        tooltip_width = text_rect.width() + 20
        tooltip_height = text_rect.height() + 10
        
        # 鼠标位置
        mouse_pos = self.mapFromGlobal(QCursor.pos())
        tooltip_x = mouse_pos.x() - tooltip_width // 2
        tooltip_y = mouse_pos.y() - tooltip_height - 10
        
        # 确保提示框在窗口内
        if tooltip_x < 5:
            tooltip_x = 5
        if tooltip_x + tooltip_width > self.width() - 5:
            tooltip_x = self.width() - tooltip_width - 5
        if tooltip_y < 5:
            tooltip_y = mouse_pos.y() + 20
        
        # 绘制提示框背景
        painter.setPen(QPen(QColor(0, 0, 0, 200), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
        painter.drawRoundedRect(tooltip_x, tooltip_y, tooltip_width, tooltip_height, 5, 5)
        
        # 绘制提示文本
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(tooltip_x + 10, tooltip_y + tooltip_height - 5, text)



class ReportDetailPage(QWidget):
    """测试报告详情页 - 二级页面，覆盖整个测试报告tab"""
    
    back_requested = pyqtSignal()  # 返回信号
    
    def __init__(self, parent=None, report_data=None):
        super().__init__(parent)
        self.report_data = report_data or {}
        self.report_service = TestReportService()
        
        # 分页相关变量初始化
        self.current_page = 1
        self.current_page_size = 20
        self.total_pages = 0
        
        self.init_ui()
        self.load_report_details()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # 顶部导航栏
        nav_layout = QHBoxLayout()
        
        # 返回按钮
        back_btn = QPushButton("返回")
        back_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                background: #ffffff;
                font-size: 14px;
                color: #24292f;
            }
            QPushButton:hover {
                background: #f6f8fa;
                border-color: #0969da;
            }
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        
        # 页面标题
        title_label = QLabel("测试报告详情")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #24292f;")
        
        nav_layout.addWidget(back_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(title_label)
        nav_layout.addStretch()
        
        layout.addLayout(nav_layout)
        
        # 基础概要信息区域
        self.setup_summary_section(layout)
        
        # 用例列表树形结构
        self.setup_case_tree_section(layout)
    
    def setup_summary_section(self, parent_layout):
        """设置基础概要信息区域"""
        # 创建水平布局容器，报告信息左对齐，执行统计右对齐
        summary_container = QWidget()
        summary_layout = QHBoxLayout(summary_container)
        
        # 左侧：报告基本信息
        left_widget = QWidget()
        left_widget.setFixedWidth(450)  # 增加宽度以适应更大的字体和间隙
        left_layout = QVBoxLayout(left_widget)
        
        basic_info_group = QWidget()
        basic_layout = QFormLayout(basic_info_group)
        basic_layout.setSpacing(30)  # 增加行间距
        basic_layout.setContentsMargins(5, 0, 15, 0)  # 调整内边距，左内边距减小以与报告详情对齐
        
        self.report_name_label = QLabel()
        self.report_name_label.setStyleSheet("font-size: 18px; font-weight: normal;")
        self.report_status_label = QLabel()
        self.report_status_label.setStyleSheet("font-size: 18px; font-weight: normal;")
        self.report_start_time_label = QLabel()
        self.report_start_time_label.setStyleSheet("font-size: 18px; font-weight: normal;")
        self.report_end_time_label = QLabel()
        self.report_end_time_label.setStyleSheet("font-size: 18px; font-weight: normal;")
        self.report_duration_label = QLabel()
        self.report_duration_label.setStyleSheet("font-size: 18px; font-weight: normal;")

        # 创建标签并设置字体样式
        name_label = QLabel("报告名称:")
        name_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        status_label = QLabel("执行状态:")
        status_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        start_time_label = QLabel("开始时间:")
        start_time_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        end_time_label = QLabel("结束时间:")
        end_time_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        duration_label = QLabel("执行时长:")
        duration_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        basic_layout.addRow(name_label, self.report_name_label)
        basic_layout.addRow(status_label, self.report_status_label)
        basic_layout.addRow(start_time_label, self.report_start_time_label)
        basic_layout.addRow(end_time_label, self.report_end_time_label)
        basic_layout.addRow(duration_label, self.report_duration_label)

        left_layout.addWidget(basic_info_group)
        left_layout.addStretch()
        
        # 右侧：执行统计（饼图+数字统计）
        right_widget = QWidget()
        right_widget.setFixedWidth(500)  # 增加宽度以适应新的布局
        right_layout = QVBoxLayout(right_widget)
        
        stats_group = QWidget()
        stats_layout = QHBoxLayout(stats_group)  # 改为水平布局
        stats_layout.setSpacing(20)  # 增加间距
        
        # 左侧：饼图
        pie_chart_widget = QWidget()
        pie_chart_layout = QVBoxLayout(pie_chart_widget)
        
        # 创建饼图
        self.pie_chart = PieChartWidget()
        self.pie_chart.setMinimumSize(200, 200)
        pie_chart_layout.addWidget(self.pie_chart, 0, Qt.AlignCenter)
        
        stats_layout.addWidget(pie_chart_widget)
        
        # 右侧：统计信息（key:value样式）
        stats_info_widget = QWidget()
        stats_info_layout = QVBoxLayout(stats_info_widget)
        stats_info_layout.setSpacing(40)  # 增加行间距
        
        # 用例数
        total_layout = QHBoxLayout()
        total_label = QLabel("用例数：")
        total_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        self.total_cases_label = QLabel("0")
        self.total_cases_label.setStyleSheet("font-size: 16px; color: #333;")
        total_layout.addWidget(total_label)
        total_layout.addWidget(self.total_cases_label)
        total_layout.addStretch()
        stats_info_layout.addLayout(total_layout)
        
        # 成功数
        passed_layout = QHBoxLayout()
        passed_label = QLabel("成功数：")
        passed_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
        self.passed_cases_label = QLabel("0")
        self.passed_cases_label.setStyleSheet("font-size: 16px; color: #4CAF50;")
        passed_layout.addWidget(passed_label)
        passed_layout.addWidget(self.passed_cases_label)
        passed_layout.addStretch()
        stats_info_layout.addLayout(passed_layout)
        
        # 失败数
        failed_layout = QHBoxLayout()
        failed_label = QLabel("失败数：")
        failed_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #F44336;")
        self.failed_cases_label = QLabel("0")
        self.failed_cases_label.setStyleSheet("font-size: 16px; color: #F44336;")
        failed_layout.addWidget(failed_label)
        failed_layout.addWidget(self.failed_cases_label)
        failed_layout.addStretch()
        stats_info_layout.addLayout(failed_layout)
        
        # 通过率
        rate_layout = QHBoxLayout()
        rate_label = QLabel("通过率：")
        rate_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2196F3;")
        self.success_rate_label = QLabel("0%")
        self.success_rate_label.setStyleSheet("font-size: 16px; color: #2196F3;")
        rate_layout.addWidget(rate_label)
        rate_layout.addWidget(self.success_rate_label)
        rate_layout.addStretch()
        stats_info_layout.addLayout(rate_layout)
        
        stats_info_layout.addStretch()
        stats_layout.addWidget(stats_info_widget)
        
        right_layout.addWidget(stats_group)
        
        # 将两部分添加到水平布局，报告信息左对齐，执行统计右对齐
        summary_layout.addWidget(left_widget)
        summary_layout.addStretch()  # 添加弹性空间
        summary_layout.addWidget(right_widget)
        
        parent_layout.addWidget(summary_container)
    
    def setup_case_tree_section(self, parent_layout):
        """设置用例列表布局结构"""
        # 用例树容器
        case_tree_widget = QWidget()
        case_tree_layout = QVBoxLayout(case_tree_widget)
        
        # 创建滚动区域
        self.steps_scroll_area = QScrollArea()
        self.steps_scroll_area.setWidgetResizable(True)
        self.steps_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.steps_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.steps_scroll_area.setStyleSheet("""
            QScrollArea {
                background: #f8f9fa;
                border: 1px solid #e1e4e8;
                border-radius: 12px;
            }
            QScrollBar:vertical {
                background: #f5f5f5;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #c1c1c1;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a8a8a8;
            }
            QScrollBar::handle:vertical:pressed {
                background: #787878;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background: #f5f5f5;
                height: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #c1c1c1;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #a8a8a8;
            }
            QScrollBar::handle:horizontal:pressed {
                background: #787878;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)
        
        # 创建容器用于存放步骤组件
        self.steps_container = QWidget()
        self.steps_container.setStyleSheet("""
            QWidget {
                background: #f8f9fa;
                border: none;
                border-radius: 12px;
            }
        """)
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.setSpacing(4)
        self.steps_layout.setContentsMargins(8, 8, 8, 8)
        self.steps_layout.addStretch()  # 添加拉伸因子，使内容靠上显示
        
        self.steps_scroll_area.setWidget(self.steps_container)
        case_tree_layout.addWidget(self.steps_scroll_area)
        parent_layout.addWidget(case_tree_widget, 1)  # 设置拉伸因子为1
    
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

        # 时间信息
        start_time = self.report_data.get('start_time')
        if start_time:
            if isinstance(start_time, str):
                start_text = start_time
            else:
                start_text = start_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            start_text = 'N/A'
        self.report_start_time_label.setText(start_text)

        end_time = self.report_data.get('end_time')
        if end_time:
            if isinstance(end_time, str):
                end_text = end_time
            else:
                end_text = end_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            end_text = 'N/A'
        self.report_end_time_label.setText(end_text)

        duration = self.report_data.get('duration', 0)
        try:
            duration_value = float(duration)
            self.report_duration_label.setText(f"{duration_value:.2f} 秒")
        except (ValueError, TypeError):
            self.report_duration_label.setText(f"{duration} 秒")

        # 统计信息
        total_cases = self.report_data.get('total_cases', 0)
        passed_cases = self.report_data.get('passed_cases', 0)
        failed_cases = self.report_data.get('failed_cases', 0)
        error_cases = self.report_data.get('error_cases', 0)

        self.total_cases_label.setText(str(total_cases))
        self.passed_cases_label.setText(str(passed_cases))
        self.failed_cases_label.setText(str(failed_cases))

        # 计算通过率
        if total_cases > 0:
            success_rate = (passed_cases / total_cases) * 100
            self.success_rate_label.setText(f"{success_rate:.1f}%")
        else:
            self.success_rate_label.setText("0%")

        # 更新饼图
        self.pie_chart.set_data(passed_cases, failed_cases, error_cases)

        # 加载用例树形结构
        self.load_case_tree()
    
    def _get_case_status(self, steps):
        """根据步骤状态确定用例状态"""
        if not steps:
            return 'unknown'
        
        status_priority = {
            'error': 4,
            'failure': 3,
            'skipped': 2,
            'success': 1
        }
        
        # 获取最高优先级的状态
        highest_priority = 0
        case_status = 'success'
        
        for step in steps:
            status = step.get('status', 'skipped')
            priority = status_priority.get(status, 0)
            if priority > highest_priority:
                highest_priority = priority
                case_status = status
        
        return case_status
    
    def _calculate_case_duration(self, steps):
        """计算用例总执行时间"""
        total_duration = 0.0
        for step in steps:
            duration = step.get('duration', 0)
            try:
                total_duration += float(duration)
            except (ValueError, TypeError):
                # 如果转换失败，跳过该步骤
                continue
        return total_duration

    def _format_steps_data(self, steps):
        """格式化步骤数据"""
        formatted_steps = []
        
        for step in steps:
            # 优先使用step_name字段，如果为空则使用api_name字段，最后使用默认值
            step_name = step.get('step_name') or step.get('api_name', '未知接口')
            formatted_step = {
                'step_name': step_name,
                'status': step.get('status', 'skipped'),
                'duration': step.get('duration', 0),  # 使用duration字段
                'execution_logs': step.get('execution_logs', [])
            }
            formatted_steps.append(formatted_step)
        
        return formatted_steps
    
    def load_case_tree(self):
        """加载用例布局结构 - 使用新的布局架构"""
        try:
            # 清空现有内容
            self._clear_steps_layout()
            
            # 检查report_data中是否包含id字段
            if 'id' not in self.report_data:
                self._show_no_data_message("报告数据不完整")
                return
                
            report_id = self.report_data['id']
            
            # 从数据库加载步骤结果
            step_results = self.report_service.get_step_results_by_report(report_id)
            
            if not step_results:
                self._show_no_data_message("暂无步骤执行数据")
                return
            
            # 按用例分组
            case_groups = self._group_steps_by_case(step_results)
            
            # 创建用例组件
            self._create_case_items(case_groups)
            
        except Exception as e:
            self._show_error_message(f"加载用例布局失败: {e}")
    

    
    def on_case_item_double_clicked(self, item, column):
        """处理用例树形结构双击事件 - 在新的布局架构中不再需要"""
        # 在新的布局架构中，双击事件由CaseItem组件内部处理
        print("[DEBUG] 双击事件在新的布局架构中由组件内部处理")
    
    def show_step_logs_dialog(self, step_data):
        """显示步骤执行日志对话框"""
        try:
            # 优先使用step_name字段，如果为空则使用api_name字段，最后使用默认值
            step_name = step_data.get('step_name') or step_data.get('api_name', '未知接口')
            
            # 创建对话框
            dialog = QDialog(self)
            dialog.setWindowTitle(f"步骤执行日志 - {step_name}")
            dialog.setMinimumSize(800, 600)
            
            layout = QVBoxLayout(dialog)
            
            # 步骤基本信息
            info_group = QGroupBox("步骤信息")
            info_layout = QFormLayout(info_group)
            
            step_order = step_data.get('step_order', 0)
            status = step_data.get('status', 'skipped')
            execution_time = step_data.get('execution_time', 0)
            
            info_layout.addRow("步骤序号:", QLabel(str(step_order)))
            info_layout.addRow("接口名称:", QLabel(step_name))
            info_layout.addRow("执行状态:", QLabel({
                'success': '通过',
                'failure': '失败', 
                'error': '错误',
                'skipped': '跳过'
            }.get(status, status)))
            info_layout.addRow("执行时间:", QLabel(f"{execution_time:.2f}秒"))
            
            layout.addWidget(info_group)
            
            # 执行日志区域
            logs_group = QGroupBox("执行日志")
            logs_layout = QVBoxLayout(logs_group)
            
            # 日志文本框
            logs_text = QTextEdit()
            logs_text.setReadOnly(True)
            logs_text.setFont(QFont("Consolas", 10))
            logs_text.setStyleSheet("""
                QTextEdit {
                    border: 1px solid #e1e4e8;
                    border-radius: 4px;
                    background: #fafbfc;
                    padding: 12px;
                    font-size: 13px;
                    line-height: 1.5;
                }
            """)
            
            # 加载执行日志
            execution_logs = step_data.get('execution_logs', [])
            if execution_logs:
                for log in execution_logs:
                    timestamp = log.get('timestamp', '')
                    level = log.get('level', 'info')
                    message = log.get('message', '')
                    
                    # 根据日志级别设置颜色
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
                    logs_text.append(log_entry)
            else:
                logs_text.setText("暂无执行日志")
            
            logs_layout.addWidget(logs_text)
            layout.addWidget(logs_group)
            
            # 按钮区域
            button_box = QDialogButtonBox(QDialogButtonBox.Close)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            dialog.exec_()
            
        except Exception as e:
            print(f"显示步骤日志对话框失败: {e}")
            import traceback
            traceback.print_exc()

    def _clear_steps_layout(self):
        """清空步骤布局"""
        for i in reversed(range(self.steps_layout.count())):
            item = self.steps_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()

    def _show_no_data_message(self, message):
        """显示无数据消息"""
        no_data_label = QLabel(message)
        no_data_label.setAlignment(Qt.AlignCenter)
        no_data_label.setStyleSheet("color: gray; font-size: 14px; padding: 20px;")
        self.steps_layout.insertWidget(0, no_data_label)

    def _group_steps_by_case(self, step_results):
        """按用例分组步骤结果"""
        case_groups = {}
        for step in step_results:
            case_id = step.get('case_id')
            if case_id not in case_groups:
                case_groups[case_id] = []
            case_groups[case_id].append(step)
        return case_groups

    def _create_case_items(self, case_groups):
        """创建用例组件"""
        for case_id, steps in case_groups.items():
            # 获取用例名称（从第一个步骤中获取），直接使用用例名称而不是"用例 X"格式
            case_name = steps[0].get('case_name', f'用例 {case_id}') if steps else f'用例 {case_id}'
            # 如果用例名称是"用例 X"格式，提取实际用例名称
            if case_name.startswith('用例 '):
                # 尝试从步骤数据中获取实际用例名称
                actual_case_name = steps[0].get('case_name', case_name) if steps else case_name
                case_name = actual_case_name
            
            # 创建用例数据
            case_data = {
                'status': self._get_case_status(steps),
                'steps': self._format_steps_data(steps),
                'duration': self._calculate_case_duration(steps)  # 计算用例总执行时间
            }
            
            # 创建CaseItem组件
            case_item = CaseItem(case_name, case_data)
            
            # 添加到布局
            self.steps_layout.insertWidget(self.steps_layout.count() - 1, case_item)

    def _show_error_message(self, message):
        """显示错误消息"""
        print(message)
        import traceback
        traceback.print_exc()


class CaseItem(QWidget):
    """用例项组件 - 支持展开收起，管理步骤和日志容器"""
    
    def __init__(self, case_name, case_data, parent=None):
        super().__init__(parent)
        self.case_name = case_name
        self.case_data = case_data
        self.is_expanded = False
        self.step_items = []
        self.step_logs_containers = {}  # 存储每个步骤的日志容器
        self.init_ui()
        self.load_case_steps()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 用例标题栏 - 添加背景容器
        self.header_widget = QWidget()
        self.header_widget.setCursor(Qt.PointingHandCursor)
        # 启用鼠标跟踪以接收鼠标事件
        self.header_widget.setMouseTracking(True)
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(12, 8, 12, 8)
        
        # 为标题栏添加背景容器
        self.header_container = QWidget()
        self.header_container.setStyleSheet("""
            QWidget {
                background: #e6f3ff;  /* 统一的浅蓝色背景 */
                border: none;        /* 去除边框 */
                border-radius: 20px; /* 加大倒角，呈现半圆样式 */
                margin: 2px;
            }
        """)
        header_container_layout = QHBoxLayout(self.header_container)
        header_container_layout.setContentsMargins(12, 8, 12, 8)
        
        # 展开/收起按钮 - 使用图片图标
        self.expand_btn = QPushButton()
        self.expand_btn.setFixedSize(20, 20)
        self.expand_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                qproperty-iconSize: 14px;
            }
            QPushButton:hover {
                background: #f0f0f0;
                border-radius: 3px;
            }
        """)
        self.expand_btn.clicked.connect(self.toggle_expand)
        
        # 设置初始图标
        self.update_expand_icon()
        
        # 用例名称 - 加大字体
        self.case_label = QLabel(self.case_name)
        self.case_label.setStyleSheet("font-weight: 600; font-size: 16px; color: #24292f;")
        
        # 用例状态信息 - 左边三个字段
        left_info_widget = QWidget()
        left_layout = QHBoxLayout(left_info_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(20)
        
        # 步骤数量
        steps = self.case_data.get('steps', [])
        self.step_count_label = QLabel(f"{len(steps)} 个步骤")
        self.step_count_label.setStyleSheet("color: #666; font-size: 14px;")
        
        # 耗时
        duration = self.case_data.get('duration', 0)
        self.duration_label = QLabel(f"耗时: {duration:.2f}s")
        self.duration_label.setStyleSheet("color: #666; font-size: 14px;")
        
        left_layout.addWidget(self.case_label)
        left_layout.addWidget(self.step_count_label)
        left_layout.addWidget(self.duration_label)
        left_layout.addStretch()
        
        # 右边状态显示 - PASS/FAIL
        self.status_label = QWidget()
        status_layout = QHBoxLayout(self.status_label)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setAlignment(Qt.AlignRight)
        
        status = self.case_data.get('status', 'unknown')
        status_text = {
            'success': 'PASS',
            'failure': 'FAIL',
            'error': 'FAIL',
            'skipped': 'SKIP',
            'unknown': 'UNKNOWN'
        }.get(status, status)
        
        self.status_label_text = QLabel(status_text)
        status_color = {
            'success': '#4CAF50',
            'failure': '#F44336',
            'error': '#FF9800',
            'skipped': '#9E9E9E',
            'unknown': '#9E9E9E'
        }.get(status, '#9E9E9E')
        self.status_label_text.setStyleSheet(f"color: {status_color}; font-size: 18px; font-weight: bold;")
        
        status_layout.addWidget(self.status_label_text)
        
        # 将组件添加到背景容器中
        header_container_layout.addWidget(self.expand_btn)
        header_container_layout.addWidget(left_info_widget)
        header_container_layout.addStretch()
        header_container_layout.addWidget(self.status_label)
        
        # 将背景容器添加到标题栏
        header_layout.addWidget(self.header_container)
        
        # 步骤列表容器
        self.steps_container = QWidget()
        self.steps_container.setVisible(self.is_expanded)
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.setContentsMargins(32, 0, 0, 0)
        self.steps_layout.setSpacing(4)
        
        # 不再使用单独的日志布局，日志容器将直接插入到步骤布局中
        layout.addWidget(self.header_widget)
        layout.addWidget(self.steps_container)
        
        # 设置样式
        self.update_case_style()
    
    def update_case_style(self):
        """根据用例状态更新样式"""
        # 根据用例状态设置背景色
        status = self.case_data.get('status', 'unknown')
        
        if status == 'success':
            bg_color = '#e8f5e8'  # 浅绿色 - 执行通过
        elif status in ['failure', 'error']:
            bg_color = '#ffeaea'  # 浅红色 - 执行失败
        else:
            bg_color = '#e6f3ff'  # 浅蓝色 - 未知状态
        
        # 设置用例样式 - 应用到header_container，去除hover效果
        self.header_container.setStyleSheet(f"""
            QWidget {{
                background: {bg_color};
                border: none;        /* 去除边框 */
                border-radius: 12px;
                margin: 2px;
            }}
        """)
    
    def get_icon(self, icon_name):
        """获取图标 - 复制自ReportDetailPage类的实现"""
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

    def update_expand_icon(self):
        """更新展开/收起图标"""
        if self.is_expanded:
            # 展开状态：使用向下箭头图标
            icon = self.get_icon("exband_down.png")
        else:
            # 收起状态：使用向左箭头图标
            icon = self.get_icon("expand_left.png")
        
        # 设置图标
        self.expand_btn.setIcon(icon)
    
    def mouseDoubleClickEvent(self, event):
        """处理鼠标双击事件"""
        # 检查双击是否发生在标题栏区域
        if self.header_widget.rect().contains(event.pos()):
            self.toggle_expand()
        super().mouseDoubleClickEvent(event)
    
    def toggle_expand(self):
        """切换用例展开/收起状态"""
        self.is_expanded = not self.is_expanded
        
        print(f"[DEBUG] CaseItem toggle_expand: self.is_expanded={self.is_expanded}")
        
        # 更新按钮图标
        self.update_expand_icon()
        
        # 显示/隐藏步骤列表
        self.steps_container.setVisible(self.is_expanded)
        
        # 显示/隐藏所有步骤的日志容器
        for step_index, logs_data in self.step_logs_containers.items():
            logs_scroll_area = logs_data['scroll_area']
            # 只有当用例展开且步骤本身也展开时才显示日志容器
            step_expanded = self.step_items[step_index].is_expanded
            should_show = self.is_expanded and step_expanded
            print(f"[DEBUG] 步骤 {step_index}: step_expanded={step_expanded}, should_show={should_show}")
            logs_scroll_area.setVisible(should_show)
    
    def load_case_steps(self):
        """加载用例步骤"""
        steps = self.case_data.get('steps', [])
        print(f"[DEBUG] 加载用例步骤，步骤数量: {len(steps)}")
        for step_index, step_data in enumerate(steps):
            # 获取步骤名称，优先使用接口名称，如果没有则使用默认名称
            # 直接显示步骤名称，而不是"步骤 X：接口名称"格式
            api_name = step_data.get('step_name') or step_data.get('api_template', {}).get('name') or step_data.get('name', '未知接口')
            step_display_name = api_name  # 直接使用接口名称
            
            print(f"[DEBUG] 步骤 {step_index}: api_name={step_data.get('step_name')}, api_template.name={step_data.get('api_template', {}).get('name')}, name={step_data.get('name')}, 最终显示名称: {step_display_name}")
            
            step_item = StepItem(step_display_name, step_index, step_data, self, self)
            self.steps_layout.addWidget(step_item)
            self.step_items.append(step_item)
            
            # 为每个步骤创建日志容器
            self.create_step_logs_container(step_item, step_index)
    
    def create_step_logs_container(self, step_item, step_index):
        """为步骤创建日志容器"""
        # 创建滚动区域
        logs_scroll_area = QScrollArea()
        logs_scroll_area.setWidgetResizable(True)
        logs_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        logs_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        logs_scroll_area.setFixedHeight(250)  # 固定高度，超出滚动
        logs_scroll_area.setVisible(False)  # 默认隐藏
        logs_scroll_area.setStyleSheet("""
            QScrollArea {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
            QScrollBar:vertical {
                background: #f5f5f5;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #c1c1c1;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a8a8a8;
            }
            QScrollBar::handle:vertical:pressed {
                background: #787878;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background: #f5f5f5;
                height: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #c1c1c1;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #a8a8a8;
            }
            QScrollBar::handle:horizontal:pressed {
                background: #787878;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)
        
        # 创建日志容器
        logs_container = QWidget()
        logs_layout = QVBoxLayout(logs_container)
        logs_layout.setContentsMargins(30, 2, 0, 2)  # 减少边距，更紧凑
        logs_layout.setSpacing(1)  # 减少间距
        logs_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # 居上左对齐
        
        logs_container.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border: none;
            }
        """)
        
        logs_scroll_area.setWidget(logs_container)
        
        # 存储日志容器引用
        self.step_logs_containers[step_index] = {
            'scroll_area': logs_scroll_area,
            'container': logs_container,
            'layout': logs_layout
        }
        
        # 将日志容器直接插入到步骤布局中对应的步骤项后面
        # 计算插入位置：步骤项的位置 + 1
        step_position = self.steps_layout.indexOf(step_item) + 1
        self.steps_layout.insertWidget(step_position, logs_scroll_area)
        
        # 加载步骤日志到容器中
        self.load_step_logs_to_container(step_item, step_index)
    
    def load_step_logs_to_container(self, step_item, step_index):
        """加载步骤日志到对应的容器中（文本编辑框版本）"""
        if step_index not in self.step_logs_containers:
            return
            
        logs_container = self.step_logs_containers[step_index]['container']
        logs_layout = self.step_logs_containers[step_index]['layout']
        
        # 清空现有日志
        while logs_layout.count():
            child = logs_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 创建新的LogItem组件（文本编辑框版本）
        log_item = LogItem(step_item.step_name, step_index, step_item.step_data, self)
        logs_layout.addWidget(log_item)
    
    def on_step_expand_changed(self, step_item, is_expanded):
        """处理步骤展开/收起状态变化"""
        step_index = step_item.step_index
        
        print(f"[DEBUG] on_step_expand_changed: step_index={step_index}, is_expanded={is_expanded}, self.is_expanded={self.is_expanded}")
        
        if step_index not in self.step_logs_containers:
            print(f"[DEBUG] 步骤 {step_index} 的日志容器不存在")
            return
            
        logs_scroll_area = self.step_logs_containers[step_index]['scroll_area']
        
        # 显示/隐藏对应的日志容器
        # 只有当用例展开且步骤本身也展开时才显示日志容器
        should_show = self.is_expanded and is_expanded
        print(f"[DEBUG] 设置日志容器可见性: {should_show}")
        logs_scroll_area.setVisible(should_show)
        
        # 强制更新布局
        self.updateGeometry()
        if self.parent():
            self.parent().updateGeometry()


class StepItem(QWidget):
    """步骤项组件 - 只包含步骤条本身，日志容器由父组件管理"""
    
    def __init__(self, step_name, step_index, step_data, parent=None, case_item_ref=None):
        super().__init__(parent)
        self.step_name = step_name
        self.step_index = step_index
        self.step_data = step_data
        self.is_expanded = False
        self.log_items = []
        self.logs_scroll_area = None  # 日志容器由父组件管理
        self.case_item_ref = case_item_ref  # 保存CaseItem引用
        self.init_ui()
        self.load_step_logs()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 步骤标题栏 - 添加背景容器
        self.header_widget = QWidget()
        # 移除点击光标，设置不可点击
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(12, 6, 12, 6)
        
        # 为步骤标题栏添加背景容器
        self.header_container = QWidget()
        self.header_container.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border: none;        /* 去除边框 */
                border-radius: 20px; /* 加大倒角，呈现半圆样式 */
                margin: 1px;
            }
        """)
        header_container_layout = QHBoxLayout(self.header_container)
        header_container_layout.setContentsMargins(12, 6, 12, 6)
        
        # 展开/收起按钮 - 使用图片图标
        self.expand_btn = QPushButton()
        self.expand_btn.setFixedSize(18, 18)
        self.expand_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                qproperty-iconSize: 12px;
            }
            QPushButton:hover {
                background: #f0f0f0;
                border-radius: 3px;
            }
        """)
        self.expand_btn.clicked.connect(self.toggle_expand)
        
        # 设置初始图标
        self.update_expand_icon()
        
        # 步骤名称 - 加大字体
        self.step_label = QLabel(self.step_name)
        self.step_label.setStyleSheet("font-weight: 500; font-size: 15px; color: #24292f;")
        
        # 设置步骤条固定高度为50像素
        self.header_container.setFixedHeight(50)
        
        # 左边三个字段
        left_info_widget = QWidget()
        left_layout = QHBoxLayout(left_info_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        # 日志数量
        execution_logs = self.step_data.get('execution_logs', '')
        # 计算文本格式日志的行数（非空行）
        log_lines = [line.strip() for line in execution_logs.strip().split('\n') if line.strip()]
        log_count = len(log_lines)
        self.log_count_label = QLabel(f"{log_count} 条日志")
        self.log_count_label.setStyleSheet("color: #666; font-size: 13px;")
        
        # 执行时间 - 使用duration字段
        duration = self.step_data.get('duration', 0)
        self.time_label = QLabel(f"耗时: {duration:.2f}s")
        self.time_label.setStyleSheet("color: #666; font-size: 13px;")
        
        left_layout.addWidget(self.step_label)
        left_layout.addWidget(self.log_count_label)
        left_layout.addWidget(self.time_label)
        left_layout.addStretch()
        
        # 右边状态显示 - PASS/FAIL
        self.status_label = QWidget()
        status_layout = QHBoxLayout(self.status_label)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setAlignment(Qt.AlignRight)
        
        status = self.step_data.get('status', 'skipped')
        status_text = {
            'success': 'PASS',
            'failure': 'FAIL',
            'error': 'FAIL',
            'skipped': 'SKIP'
        }.get(status, status)
        
        self.status_label_text = QLabel(status_text)
        status_color = {
            'success': '#4CAF50',
            'failure': '#F44336',
            'error': '#FF9800',
            'skipped': '#9E9E9E'
        }.get(status, '#9E9E9E')
        self.status_label_text.setStyleSheet(f"color: {status_color}; font-size: 16px; font-weight: bold;")
        
        status_layout.addWidget(self.status_label_text)
        
        # 将组件添加到背景容器中
        header_container_layout.addWidget(self.expand_btn)
        header_container_layout.addWidget(left_info_widget)
        header_container_layout.addStretch()
        header_container_layout.addWidget(self.status_label)
        
        # 将背景容器添加到标题栏
        header_layout.addWidget(self.header_container)
        
        # 只添加步骤标题栏，日志容器由父组件管理
        layout.addWidget(self.header_widget)
        
        # 启用鼠标跟踪以接收鼠标事件
        self.header_widget.setMouseTracking(True)
        
        # 设置样式
        self.update_step_style()
    
    def update_step_style(self):
        """根据步骤状态更新样式"""
        status = self.step_data.get('status', 'unknown')
        
        # 根据状态设置背景色 - 参考执行日志弹窗的步骤条样式
        if status == 'success':
            bg_color = '#E8F5E8'  # 浅绿色
        elif status == 'failure':
            bg_color = '#FFE8E8'  # 浅红色
        elif status == 'error':
            bg_color = '#FFF3CD'  # 浅黄色
        else:
            bg_color = '#FFFFFF'  # 默认白色背景，参考执行日志弹窗的StepLogItem
        
        # 设置步骤样式 - 应用到header_container，去除边框和hover效果
        self.header_container.setStyleSheet(f"""
            QWidget {{
                border: none;        /* 去除边框 */
                border-radius: 12px;
                background: {bg_color};
                margin: 1px;
            }}
        """)
    
    def get_icon(self, icon_name):
        """获取图标 - 复制自ReportDetailPage类的实现"""
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

    def update_expand_icon(self):
         """更新展开/收起图标"""
         if self.is_expanded:
             # 展开状态：使用向下箭头图标
             icon = self.get_icon("exband_down.png")
         else:
             # 收起状态：使用向左箭头图标
             icon = self.get_icon("expand_left.png")
         
         # 设置图标
         self.expand_btn.setIcon(icon)
    
    def toggle_expand(self):
        """切换展开/收起状态"""
        self.is_expanded = not self.is_expanded
        
        print(f"[DEBUG] StepItem toggle_expand: step_index={self.step_index}, is_expanded={self.is_expanded}")
        
        # 更新按钮图标
        self.update_expand_icon()
        
        # 通知父组件展开/收起状态变化
        parent = self.parent()
        print(f"[DEBUG] 父组件类型: {type(parent)}")
        print(f"[DEBUG] 父组件对象: {parent}")
        
        # 优先使用case_item_ref来调用CaseItem的方法
        if hasattr(self, 'case_item_ref') and self.case_item_ref:
            print(f"[DEBUG] 使用case_item_ref调用CaseItem方法")
            try:
                self.case_item_ref.on_step_expand_changed(self, self.is_expanded)
                print(f"[DEBUG] 成功通过case_item_ref调用on_step_expand_changed方法")
            except Exception as e:
                print(f"[DEBUG] 通过case_item_ref调用方法失败: {e}")
        # 如果case_item_ref不存在，尝试使用父组件
        elif parent:
            try:
                # 直接调用父组件的on_step_expand_changed方法
                print(f"[DEBUG] 直接调用父组件的on_step_expand_changed方法")
                parent.on_step_expand_changed(self, self.is_expanded)
                print(f"[DEBUG] 成功调用父组件的on_step_expand_changed方法")
            except AttributeError as e:
                print(f"[DEBUG] 父组件没有on_step_expand_changed方法: {e}")
                # 检查父组件是否有其他相关方法
                print(f"[DEBUG] 父组件方法列表: {[method for method in dir(parent) if not method.startswith('_')]}")
                
                # 如果父组件没有该方法，尝试调用CaseItem的toggle_expand方法来更新日志显示
                try:
                    print(f"[DEBUG] 尝试调用父组件的toggle_expand方法")
                    parent.toggle_expand()
                    print(f"[DEBUG] 成功调用父组件的toggle_expand方法")
                except AttributeError as e2:
                    print(f"[DEBUG] 父组件也没有toggle_expand方法: {e2}")
            except Exception as e:
                print(f"[DEBUG] 调用父组件方法时发生其他错误: {e}")
        else:
            print(f"[DEBUG] 父组件为None")
        
        # 强制更新布局
        self.updateGeometry()
        if parent:
            parent.updateGeometry()
        
        # 强制更新布局，确保立即显示
        self.updateGeometry()
        if parent:
            parent.updateGeometry()
    
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件处理"""
        # 检查双击是否发生在标题栏区域
        if self.header_widget.rect().contains(event.pos()):
            # 双击标题栏区域时触发展开/收起
            self.toggle_expand()
            event.accept()
        else:
            event.ignore()
    
    def load_step_logs(self):
        """加载步骤日志 - 现在由父组件管理"""
        # 通知父组件加载步骤日志
        if hasattr(self.parent(), 'load_step_logs_to_container'):
            self.parent().load_step_logs_to_container(self, self.step_index)


class LogItem(QWidget):
    """日志项组件 - 展示日志内容（文本编辑框版本，与执行日志弹窗保持一致）"""
    
    def __init__(self, step_name, step_index, step_data, parent=None):
        super().__init__(parent)
        self.step_name = step_name
        self.step_index = step_index
        self.step_data = step_data
        self.logs = []
        # 步骤执行状态：None-未执行，True-执行成功，False-执行报错
        self.step_status = None
        self.init_ui()
        # 加载执行日志
        self.load_step_logs()
        # 确保初始化后组件可见（现在组件始终可见）
        self.setVisible(True)
    
    def load_step_logs(self):
        """加载步骤执行日志 - 支持文本格式的execution_logs字段"""
        execution_logs = self.step_data.get('execution_logs', '')
        
        # 清空现有日志
        self.logs = []
        self.logs_text.clear()
        
        # 处理文本格式的日志数据
        if execution_logs and isinstance(execution_logs, str):
            # 按行分割日志
            log_lines = execution_logs.strip().split('\n')
            
            for log_line in log_lines:
                if not log_line.strip():
                    continue
                    
                # 解析日志行格式：直接使用数据库中的标准格式
                # 标准格式: [时间戳] 级别: 消息
                import re
                
                # 尝试匹配标准格式: [时间戳] 级别: 消息
                pattern = r'^\[(.*?)\] (.*?): (.*)$'
                match = re.match(pattern, log_line)
                
                if match:
                    # 提取时间戳
                    timestamp = match.group(1).strip()
                    
                    # 提取级别
                    level_part = match.group(2).strip()
                    level = level_part.upper()
                    
                    # 提取消息
                    message = match.group(3).strip()
                else:
                    # 如果格式不标准，使用默认值
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    level = "INFO"
                    message = log_line
                
                # 格式化日志消息（支持大小写）
                level_lower = level.lower()
                if level_lower == "error":
                    color = "red"
                    prefix = "[ERROR]"
                elif level_lower == "warning" or level_lower == "warn":
                    color = "orange"
                    prefix = "[WARN]"
                elif level_lower == "success":
                    color = "green"
                    prefix = "[SUCCESS]"
                else:
                    color = "black"
                    prefix = "[INFO]"
                
                # 整条日志使用相同的颜色
                log_entry = f"<span style='color: {color};'>[{timestamp}] {prefix} {message}</span>"
                
                # 添加到日志文本框
                self.logs_text.append(log_entry)
                
                # 保存到日志列表
                self.logs.append({
                    'timestamp': timestamp,
                    'level': level.lower(),
                    'message': message
                })
        
        # 更新日志数量显示（现在不需要显示在UI上，但内部计数仍然有效）
        # self.log_count_label.setText(f"{len(self.logs)} 条日志")  # 已移除log_count_label
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)  # 去除内边距，让日志文本框充满整个容器
        
        # 直接显示日志文本框，不包含步骤标题栏
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFont(QFont("Consolas", 10))
        # 移除最小高度设置，让外层容器统一控制滚动
        # 移除日志文本框的样式，让外层容器统一处理样式
        layout.addWidget(self.logs_text)
        
        # 设置外层容器样式，统一处理边框和背景
        self.setStyleSheet("""
            LogItem {
                border: 1px solid #e1e4e8;
                border-radius: 12px;
                background: #ffffff;
                margin: 4px;
            }
            LogItem:hover {
                border-color: #d0d7de;
                background: #f6f8fa;
            }
            LogItem QTextEdit {
                border: none;
                background: transparent;
                padding: 12px;
                font-size: 13px;
                line-height: 1.5;
            }
        """)
    

    
    def add_log(self, message, level="info"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 根据级别设置颜色（支持大小写）
        level_lower = level.lower()
        if level_lower == "error":
            color = "red"
            prefix = "[ERROR]"
        elif level_lower == "warning" or level_lower == "warn":
            color = "orange"
            prefix = "[WARN]"
        elif level_lower == "success":
            color = "green"
            prefix = "[SUCCESS]"
        else:
            color = "black"
            prefix = "[INFO]"
        
        # 处理消息中的换行符，确保HTML格式正确
        # 将换行符转换为HTML的<br>标签
        processed_message = message.replace('\n', '<br>')
        
        # 格式化日志消息 - 整条日志使用相同的颜色
        log_entry = f"<span style='color: {color};'>[{timestamp}] {prefix} {processed_message}</span>"
        
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
        
        # 更新步骤状态：智能判断最终状态
        if self.step_status is None:
            # 第一次添加日志，根据日志级别设置初始状态
            if level == "error" or "失败" in message or "failure" in message.lower():
                self.step_status = False
            else:
                self.step_status = True
        else:
            # 后续日志：优先根据最终执行结果判断
            if level == "error" or "失败" in message or "failure" in message.lower():
                self.step_status = False
        


class StepLogItem(QWidget):
    """步骤日志项组件 - 合并整行单元格版本"""
    
    def __init__(self, step_name, step_index, step_data, parent=None):
        super().__init__(parent)
        self.step_name = step_name
        self.step_index = step_index
        self.step_data = step_data
        # 默认收起步骤日志项，使界面更简洁
        self.is_expanded = False
        self.logs = []
        # 步骤执行状态：None-未执行，True-执行成功，False-执行报错
        self.step_status = None
        self.init_ui()
        # 加载执行日志
        self.load_step_logs()
        # 确保初始化后组件可见
        self.ensure_visibility()
    
    def load_step_logs(self):
        """加载步骤执行日志"""
        execution_logs = self.step_data.get('execution_logs', '')
        
        # 清空现有日志
        self.logs = []
        self.logs_text.clear()
        
        # 处理执行日志（数据库存储的是格式化好的文本）
        if isinstance(execution_logs, str):
            # 按行分割日志
            log_lines = execution_logs.split('\n')
            for log_line in log_lines:
                if log_line.strip():  # 跳过空行
                    # 根据日志级别确定整行颜色
                    color = self._get_log_line_color(log_line)
                    
                    # 处理消息中的换行符，确保HTML格式正确
                    processed_message = log_line.replace('\n', '<br>')
                    
                    # 使用整行颜色显示日志
                    log_entry = f"<span style='color: {color};'>{processed_message}</span>"
                    
                    # 添加到日志文本框
                    self.logs_text.append(log_entry)
                    
                    # 保存到日志列表
                    self.logs.append({
                        'timestamp': '',
                        'level': 'info',
                        'message': log_line
                    })
        else:
            # 兼容旧格式（字典列表）
            for log in execution_logs:
                level = log.get('level', 'info')
                message = log.get('message', '')
                timestamp = log.get('timestamp', '')
                
                # 格式化日志消息（支持大小写）
                level_lower = level.lower()
                if level_lower == "error":
                    color = "red"
                    prefix = "[ERROR]"
                elif level_lower == "warning" or level_lower == "warn":
                    color = "orange"
                    prefix = "[WARN]"
                elif level_lower == "success":
                    color = "green"
                    prefix = "[SUCCESS]"
                else:
                    color = "black"
                    prefix = "[INFO]"
                
                # 如果没有时间戳，使用当前时间
                if not timestamp:
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 处理消息中的换行符，确保HTML格式正确
                # 将换行符转换为HTML的<br>标签
                processed_message = message.replace('\n', '<br>')
                
                # 使用整行颜色显示日志
                log_entry = f"<span style='color: {color};'>[{timestamp}] {prefix} {processed_message}</span>"
                
                # 添加到日志文本框
                self.logs_text.append(log_entry)
                
                # 保存到日志列表
                self.logs.append({
                    'timestamp': timestamp,
                    'level': level,
                    'message': message
                })
        
        # 更新日志数量显示
        self.log_count_label.setText(f"{len(self.logs)} 条日志")
    
    def _get_log_line_color(self, log_line):
        """根据日志行内容确定颜色"""
        log_line_lower = log_line.lower()
        
        # 根据日志级别关键词确定颜色
        if 'error' in log_line_lower:
            return 'red'
        elif 'warning' in log_line_lower or 'warn' in log_line_lower:
            return 'orange'
        elif 'success' in log_line_lower:
            return 'green'
        elif 'info' in log_line_lower:
            return 'black'
        else:
            # 默认颜色
            return 'black'
    
    def ensure_visibility(self):
        """确保组件可见性正确设置"""
        # 设置content_widget的可见性
        self.content_widget.setVisible(self.is_expanded)
        # 确保自身可见
        self.setVisible(True)
    
    def init_ui(self):
        """初始化界面 - 合并整行单元格版本"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 步骤标题栏 - 合并整行单元格
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
        
        # 步骤状态和基本信息
        status_info_widget = QWidget()
        status_layout = QHBoxLayout(status_info_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(20)
        
        # 执行状态
        status = self.step_data.get('status', 'skipped')
        status_text = {
            'success': '通过',
            'failure': '失败',
            'error': '错误',
            'skipped': '跳过'
        }.get(status, status)
        
        self.status_label = QLabel(status_text)
        status_color = {
            'success': '#4CAF50',
            'failure': '#F44336',
            'error': '#FF9800',
            'skipped': '#9E9E9E'
        }.get(status, '#9E9E9E')
        self.status_label.setStyleSheet(f"color: {status_color}; font-size: 12px; font-weight: 600;")
        
        # 执行时间
        execution_time = self.step_data.get('execution_time', 0)
        self.time_label = QLabel(f"{execution_time:.2f}秒")
        self.time_label.setStyleSheet("color: #666; font-size: 12px;")
        
        # 日志数量
        execution_logs = self.step_data.get('execution_logs', [])
        self.log_count_label = QLabel(f"{len(execution_logs)} 条日志")
        self.log_count_label.setStyleSheet("color: #666; font-size: 12px;")
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.time_label)
        status_layout.addWidget(self.log_count_label)
        status_layout.addStretch()
        
        header_layout.addWidget(self.expand_btn)
        header_layout.addWidget(self.step_label)
        header_layout.addStretch()
        header_layout.addWidget(status_info_widget)
        
        # 步骤日志内容区域 - 紧凑布局
        self.content_widget = QWidget()
        # 默认收起状态
        self.content_widget.setVisible(self.is_expanded)
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(30, 4, 0, 4)  # 减少边距，更紧凑
        content_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # 居上左对齐
        
        # 日志文本框 - 紧凑布局
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFont(QFont("Consolas", 9))  # 减小字体
        self.logs_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.logs_text.setFixedHeight(200)  # 固定高度，紧凑显示
        self.logs_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e1e4e8;
                border-radius: 8px;
                background: #ffffff;
                padding: 12px;
                font-size: 11px;
                line-height: 1.4;
            }
            QTextEdit:hover {
                border-color: #d0d7de;
            }
        """)
        content_layout.addWidget(self.logs_text)
        
        layout.addWidget(self.header_widget)
        layout.addWidget(self.content_widget)
        
        # 设置样式 - 合并整行单元格
        self.setStyleSheet("""
            StepLogItem {
                border: 1px solid #e1e4e8;
                border-radius: 12px;
                background: #ffffff;
                margin: 0px;
            }
            StepLogItem:hover {
                border-color: #d0d7de;
                background: #f6f8fa;
            }
        """)
    
    def toggle_expand(self):
        """切换展开/收起状态 - 紧凑布局版本"""
        self.is_expanded = not self.is_expanded
        
        # 更新按钮图标
        if self.is_expanded:
            self.expand_btn.setText("▼")
        else:
            self.expand_btn.setText("▶")
        
        # 显示/隐藏内容区域
        self.content_widget.setVisible(self.is_expanded)
        
        # 强制更新布局，确保立即显示
        self.updateGeometry()
        if self.parent():
            self.parent().updateGeometry()
    
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


class TestReportManager(QWidget):
    """测试报告管理页面"""
    data_changed = pyqtSignal()  # 数据变化信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.report_service = None
        self.case_service = None
        self.scheduler_service = None
        self.project_service = None
        self.current_scheduler_id = None  # 当前选中的调度ID，用于过滤
        self.current_business_id = None  # 当前选中的业务分组ID，用于项目过滤
        self.loading_thread = None  # 异步加载线程
        self.is_loading = False  # 是否正在加载
        self.current_request_id = 0  # 当前请求ID，用于防止竞态条件
        
        # 分页相关变量初始化
        self.current_page = 1
        self.current_page_size = 20
        self.total_pages = 0
        
        self.init_ui()
        # 延迟加载数据，避免启动时数据库连接失败导致弹窗
        QTimer.singleShot(100, self.delayed_load_data)

    def init_ui(self):
        # 使用堆栈布局管理列表页和详情页
        self.stack_layout = QStackedLayout(self)
        
        # 创建列表页容器
        self.list_page = QWidget()
        main_layout = QVBoxLayout(self.list_page)

        # 筛选工具栏
        filter_toolbar = QToolBar()
        filter_toolbar.setIconSize(QSize(16, 16))
        filter_toolbar.setStyleSheet(f"""
            QToolBar {{
                spacing: 15px;  /* 工具栏内控件间距 */
                padding: 8px 12px;  /* 工具栏内边距 */
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                margin-bottom: 8px;
            }}
            QToolBar QLabel {{
                font-weight: bold;
                color: #495057;
                margin-right: 5px;
                padding: 4px 0px;
            }}
            QToolBar QComboBox, QToolBar QLineEdit {{
                margin-right: 15px;  /* 控件右侧间距 */
                padding: 6px 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                min-height: 28px;
            }}
            QToolBar QComboBox:focus, QToolBar QLineEdit:focus {{
                border-color: #0078d4;
                outline: none;
            }}
            {get_toolbar_combobox_style()}
        """)

        # 项目筛选（移到最左边）
        filter_toolbar.addWidget(QLabel("项目:"))
        self.project_combo = NoWheelComboBox()
        self.project_combo.setMinimumWidth(150)
        # 延迟加载项目列表，避免服务未初始化
        self.project_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_toolbar.addWidget(self.project_combo)

        # 时间筛选
        filter_toolbar.addWidget(QLabel("时间范围:"))
        self.time_range_combo = NoWheelComboBox()
        self.time_range_combo.setMinimumWidth(120)
        self.time_range_combo.addItems([
            "全部", "今天", "最近7天", "最近30天", "最近90天", "自定义"
        ])
        self.time_range_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_toolbar.addWidget(self.time_range_combo)

        # 状态筛选
        filter_toolbar.addWidget(QLabel("状态:"))
        self.status_combo = NoWheelComboBox()
        self.status_combo.setMinimumWidth(100)
        self.status_combo.addItems(["全部", "成功", "失败", "错误", "执行中"])
        self.status_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_toolbar.addWidget(self.status_combo)

        filter_toolbar.addSeparator()

        # 搜索框
        filter_toolbar.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("报告名称...")
        self.search_edit.textChanged.connect(self.on_filter_changed)
        self.search_edit.setFixedWidth(300)  # 固定宽度180px
        filter_toolbar.addWidget(self.search_edit)

        filter_toolbar.addSeparator()

        main_layout.addWidget(filter_toolbar)

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
        
        # 禁用右键菜单
        self.scheduler_list_widget.setContextMenuPolicy(Qt.NoContextMenu)
        
        left_layout.addWidget(self.scheduler_list_widget)
        
        # 设置左侧宽度
        left_widget.setMaximumWidth(350)
        left_widget.setMinimumWidth(350)
        
        splitter.addWidget(left_widget)
        
        # 右侧：报告列表表格
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 操作工具栏 - 移动到报告列表容器上方
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setAlignment(Qt.AlignLeft)  # 左对齐
        
        # 刷新按钮
        refresh_btn = QPushButton()
        refresh_btn.setFixedSize(32, 32)
        refresh_btn.setIcon(self.get_icon("refresh.png"))
        refresh_btn.setIconSize(QSize(24, 24))
        refresh_btn.setToolTip("刷新报告列表")
        refresh_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #dee2e6;
                background-color: #ffffff;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #e9ecef;
            }
        """)
        refresh_btn.clicked.connect(self.on_refresh_clicked)
        
        # 清理报告按钮
        clear_btn = QPushButton()
        clear_btn.setFixedSize(32, 32)
        clear_btn.setIcon(self.get_icon("delete.png"))
        clear_btn.setIconSize(QSize(24, 24))
        clear_btn.setToolTip("清理旧报告")
        clear_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #dee2e6;
                background-color: #ffffff;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #e9ecef;
            }
        """)
        clear_btn.clicked.connect(self.clear_old_reports)
        
        toolbar_layout.addWidget(refresh_btn)
        toolbar_layout.addWidget(clear_btn)
        toolbar_layout.addStretch()  # 添加拉伸，确保按钮左对齐
        
        right_layout.addLayout(toolbar_layout)
        
        # 报告列表表格
        self.tree_widget = QTreeWidget()
        self.tree_widget.setColumnCount(9)
        self.tree_widget.setHeaderLabels([
            "序号", "报告名称", "用例数", "执行结果", "通过率", "开始时间", "结束时间", "执行耗时", "操作"
        ])
        
        # 设置固定列宽 - 参考定时调度UI设计
        self.tree_widget.setColumnWidth(0, 80)     # 序号
        self.tree_widget.setColumnWidth(1, 445)    # 报告名称
        self.tree_widget.setColumnWidth(2, 80)    # 用例数
        self.tree_widget.setColumnWidth(3, 150)    # 执行结果
        self.tree_widget.setColumnWidth(4, 150)    # 通过率
        self.tree_widget.setColumnWidth(5, 300)    # 开始时间
        self.tree_widget.setColumnWidth(6, 300)    # 结束时间
        self.tree_widget.setColumnWidth(7, 100)    # 执行耗时
        
        # 设置列宽调整模式 - 操作栏自适应拉伸
        header = self.tree_widget.header()
        header.setSectionResizeMode(QHeaderView.Fixed)  # 其他列固定宽度
        header.setSectionResizeMode(8, QHeaderView.Stretch)  # 操作栏自适应拉伸
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
        # 去除固定高度限制，让表格自适应高度

        right_layout.addWidget(self.tree_widget)
        
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
                border: 1px solid #e9ecef;
            }
        """)
        self.first_page_btn.clicked.connect(self.go_to_first_page)
        pagination_layout.addWidget(self.first_page_btn)
        
        # 上一页按钮
        self.prev_page_btn = QPushButton("‹ 上一页")
        self.prev_page_btn.setFixedSize(70, 32)
        self.prev_page_btn.setStyleSheet(self.first_page_btn.styleSheet())
        self.prev_page_btn.clicked.connect(self.go_to_prev_page)
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
        self.page_input.returnPressed.connect(self.go_to_specific_page)
        pagination_layout.addWidget(self.page_input)
        
        # 总页数标签
        self.total_pages_label = QLabel("/ 0")
        self.total_pages_label.setStyleSheet("color: #6c757d; font-size: 12px; font-weight: 500; margin: 0 4px;")
        pagination_layout.addWidget(self.total_pages_label)
        
        # 下一页按钮
        self.next_page_btn = QPushButton("下一页 ›")
        self.next_page_btn.setFixedSize(70, 32)
        self.next_page_btn.setStyleSheet(self.first_page_btn.styleSheet())
        self.next_page_btn.clicked.connect(self.go_to_next_page)
        pagination_layout.addWidget(self.next_page_btn)
        
        # 末页按钮
        self.last_page_btn = QPushButton("末页 »")
        self.last_page_btn.setFixedSize(70, 32)
        self.last_page_btn.setStyleSheet(self.first_page_btn.styleSheet())
        self.last_page_btn.clicked.connect(self.go_to_last_page)
        pagination_layout.addWidget(self.last_page_btn)
        
        # 每页显示数量选择
        self.page_size_combo = QComboBox()
        self.page_size_combo.setFixedSize(85, 32)
        self.page_size_combo.addItems(["10", "20", "50", "100"])
        self.page_size_combo.setCurrentText("20")
        self.page_size_combo.setStyleSheet(get_combobox_style())
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        pagination_layout.addWidget(self.page_size_combo)
        
        right_layout.addWidget(self.pagination_widget)
        
        splitter.addWidget(right_widget)
        
        # 设置分割比例和大小策略
        splitter.setStretchFactor(0, 0)  # 左侧不拉伸
        splitter.setStretchFactor(1, 1)  # 右侧拉伸
        
        # 设置分割器大小策略，让右侧可以充分拉伸
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        main_layout.addWidget(splitter, 1)  # 设置拉伸因子为1，让分割器占据主要空间

        # 状态栏（已移除状态标签）
        status_layout = QHBoxLayout()
        status_layout.addStretch()

        main_layout.addLayout(status_layout)

        # 将列表页添加到堆栈布局
        self.stack_layout.addWidget(self.list_page)
        
        # 创建详情页（初始为空，需要时创建）
        self.detail_page = None
        
        # 设置堆栈布局为当前布局
        self.setLayout(self.stack_layout)

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
            self.project_service = ProjectService()
            
            # 检查服务是否成功初始化
            if not all([self.report_service, self.case_service, self.scheduler_service, self.project_service]):
                raise Exception("服务初始化失败，部分服务对象为None")
            
            # 确保分页相关属性已初始化
            if not hasattr(self, 'current_page'):
                self.current_page = 1
            if not hasattr(self, 'current_page_size'):
                self.current_page_size = 20
            if not hasattr(self, 'total_pages'):
                self.total_pages = 0
            
            # 加载项目列表
            self.load_projects()
            
            # 加载调度任务列表
            self.load_schedulers()
            
            # 加载报告数据
            self.load_reports()
            
            # 不再启动定时刷新调度任务列表，改为手动刷新
            
        except Exception as e:
            # 提供用户友好的错误提示
            error_msg = f"测试报告页面初始化失败: {str(e)}"
            print(error_msg)
            
            # 在界面上显示错误信息
            self.tree_widget.clear()
            error_item = QTreeWidgetItem(self.tree_widget)
            error_item.setText(0, error_msg)
            self.tree_widget.setFirstItemColumnSpanned(error_item, True)
            error_item.setTextAlignment(0, Qt.AlignCenter | Qt.AlignVCenter)
            error_item.setBackground(0, QBrush(QColor("#ffebee")))
            error_item.setForeground(0, QBrush(QColor("#c62828")))
            
            # 同时清空调度任务列表并显示错误提示
            self.scheduler_list_widget.clear()
            error_list_item = QListWidgetItem("服务初始化失败，请检查数据库连接")
            error_list_item.setFlags(Qt.NoItemFlags)
            error_list_item.setForeground(QColor("#c62828"))
            error_list_item.setTextAlignment(Qt.AlignCenter)
            self.scheduler_list_widget.addItem(error_list_item)

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

    def load_projects(self, business_id=None):
        """加载项目列表到下拉框，支持按业务分组过滤
        
        Args:
            business_id: 业务分组ID，为None时加载所有项目
        """
        # 检查服务对象是否已初始化
        if not hasattr(self, 'project_service') or self.project_service is None:
            print("项目服务未初始化，跳过加载项目列表")
            return
            
        try:
            # 根据business_id参数决定加载方式
            if business_id:
                projects = self.project_service.get_projects_by_group(business_id)
            else:
                projects = self.project_service.get_all_projects()
                
            self.project_combo.clear()
            
            # 不再添加"全部"选项，直接添加实际项目列表
            for project in projects:
                self.project_combo.addItem(project['name'], project['id'])
                
            # 如果项目列表不为空，默认选中第一个项目
            if projects:
                self.project_combo.setCurrentIndex(0)
        except Exception as e:
            print(f"加载项目列表失败: {e}")

    def on_business_changed(self, business_id):
        """业务切换事件处理
        
        Args:
            business_id: 业务分组ID
        """
        try:
            # 更新当前业务分组ID
            self.current_business_id = business_id
            
            # 根据业务分组重新加载项目列表
            self.load_projects(business_id)
            
            # 重新加载调度任务列表
            self.load_schedulers()
            
            # 清空调度任务选择状态
            self.current_scheduler_id = None
            self.scheduler_list_widget.clearSelection()
            
            # 清空报告列表
            self.tree_widget.clear()
            
                
        except Exception as e:
            print(f"处理业务切换事件失败: {e}")

    def load_schedulers(self):
        """加载测试用例集列表"""
        # 检查服务对象是否已初始化
        if self.scheduler_service is None:
            # 显示服务未初始化提示
            self.scheduler_list_widget.clear()
            error_item = QListWidgetItem("调度服务未初始化，请检查数据库连接")
            error_item.setFlags(Qt.NoItemFlags)
            error_item.setForeground(QColor("#c62828"))
            error_item.setTextAlignment(Qt.AlignCenter)
            self.scheduler_list_widget.addItem(error_item)
            print("调度服务未初始化，跳过加载测试用例集")
            return
            
        try:
            # 清空调度任务列表
            self.scheduler_list_widget.clear()
            
            # 获取当前选中的项目ID
            project_id = None
            if self.project_combo.currentIndex() >= 0:
                project_id = self.project_combo.currentData()
                # 确保project_id是整数类型
                if project_id and isinstance(project_id, str) and project_id.isdigit():
                    project_id = int(project_id)
            
            # 根据项目筛选调度任务
            schedulers = self.scheduler_service.get_schedulers_for_test_report(project_id)
            
            if not schedulers:
                # 添加提示项
                if project_id:
                    project_name = self.project_combo.currentText()
                    empty_item = QListWidgetItem(f"项目 '{project_name}' 暂无测试用例集")
                else:
                    empty_item = QListWidgetItem("暂无测试用例集")
                empty_item.setFlags(Qt.NoItemFlags)  # 不可选择
                empty_item.setForeground(QColor("#6c757d"))
                empty_item.setTextAlignment(Qt.AlignCenter)
                self.scheduler_list_widget.addItem(empty_item)
                
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
                
            # 更新状态（已移除状态标签）
            
            # 如果有测试用例集，自动选择第一个测试用例集
            if schedulers and self.scheduler_list_widget.count() > 0:
                first_item = self.scheduler_list_widget.item(0)
                self.scheduler_list_widget.setCurrentItem(first_item)
                self.current_scheduler_id = first_item.data(Qt.UserRole)
                # 触发报告加载
                self.load_reports()
            
        except Exception as e:
            print(f"加载测试用例集失败: {e}")
            # 显示错误提示
            self.scheduler_list_widget.clear()
            error_item = QListWidgetItem(f"加载测试用例集失败: {str(e)}")
            error_item.setFlags(Qt.NoItemFlags)
            error_item.setForeground(QColor("#c62828"))
            error_item.setTextAlignment(Qt.AlignCenter)
            self.scheduler_list_widget.addItem(error_item)

    def on_scheduler_item_clicked(self, item):
        """点击测试用例集项事件"""
        try:
            # 检查是否为提示项（不可选择）
            if item.flags() == Qt.NoItemFlags:
                print("点击了不可选择的提示项，跳过处理")
                return
                
            # 获取选中的测试用例集ID
            scheduler_id = item.data(Qt.UserRole)
            
            # 设置当前选中的调度ID
            self.current_scheduler_id = scheduler_id
            
            # 调试信息：打印测试用例集信息
            scheduler_name = item.text()
            print(f"=== 点击测试用例集 ===")
            print(f"测试用例集名称: {scheduler_name}")
            print(f"测试用例集ID: {scheduler_id}")
            print(f"当前报告服务状态: {self.report_service is not None}")
            
            # 获取测试用例集名称（直接获取文本）
            
            # 加载该测试用例集的报告
            self.load_reports_by_scheduler(scheduler_id)
            
        except Exception as e:
            print(f"处理测试用例集点击事件失败: {e}")

    def load_reports_by_scheduler(self, scheduler_id):
        """根据测试用例集ID加载对应的测试报告 - 使用分页功能"""
        # 重置到第一页
        self.current_page = 1
        
        # 获取筛选条件
        filters = self.get_filters()
        
        # 添加测试用例集ID筛选条件
        filters['scheduler_id'] = scheduler_id
        
        # 添加分页参数
        filters['page'] = self.current_page
        filters['page_size'] = self.current_page_size
        
        # 使用分页加载
        self.load_reports_with_pagination(filters)

    def on_reports_loaded(self, reports, request_id=None):
        """异步加载完成后的回调函数"""
        try:
            # 检查请求ID是否匹配，防止处理过期的请求
            if request_id is not None and request_id != self.current_request_id:
                print(f"忽略过期请求: {request_id}，当前请求ID: {self.current_request_id}")
                return
                
            # 重置加载状态
            self.is_loading = False
            self.loading_thread = None
            
            print(f"异步加载完成，获取到的报告数量: {len(reports) if reports else 0}")
            
            # 清空树形控件
            self.tree_widget.clear()
            
            if not reports:
                # 创建提示节点 - 合并第一行所有单元格并居中显示
                empty_item = QTreeWidgetItem(self.tree_widget)
                empty_item.setText(0, "该测试用例集暂无测试报告")
                
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
                
                # 设置状态颜色
                status_color = {
                    'success': '#28a745',  # 绿色
                    'failure': '#dc3545',  # 红色
                    'error': '#ffc107',    # 黄色
                    'running': '#17a2b8'   # 蓝色
                }.get(status, '#6c757d')   # 默认灰色
                
                item.setText(3, status_text)
                item.setForeground(3, QColor(status_color))
                
                # 通过率
                passed_cases = report.get('passed_cases', 0)
                if total_cases > 0:
                    success_rate = (passed_cases / total_cases) * 100
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
                
                # 操作栏 - 使用按钮组件替换文字按钮
                operation_widget = QWidget()
                operation_layout = QHBoxLayout(operation_widget)
                operation_layout.setContentsMargins(5, 2, 5, 2)
                operation_layout.setSpacing(3)
                operation_layout.setAlignment(Qt.AlignCenter)  # 设置布局居中对齐
                
                # 查看详情按钮
                view_btn = QPushButton()
                view_btn.setFixedSize(25, 25)
                view_btn.setIcon(self.get_icon("detail.png"))
                view_btn.setToolTip("查看详情")
                view_btn.setStyleSheet("""
                    QPushButton {
                        border: 1px solid transparent;
                        background: transparent;
                        padding: 2px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background: #e0e0e0;
                        border: 1px solid #c0c0c0;
                    }
                    QPushButton:pressed {
                        background: #d0d0d0;
                        border: 1px solid #a0a0a0;
                    }
                """)
                view_btn.clicked.connect(lambda checked, report_id=report['id']: self.view_report_detail_by_id(report_id))
                
                # 删除按钮
                delete_btn = QPushButton()
                delete_btn.setFixedSize(25, 25)
                delete_btn.setIcon(self.get_icon("delete.png"))
                delete_btn.setToolTip("删除")
                delete_btn.setStyleSheet("""
                    QPushButton {
                        border: 1px solid transparent;
                        background: transparent;
                        padding: 2px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background: #e0e0e0;
                        border: 1px solid #c0c0c0;
                    }
                    QPushButton:pressed {
                        background: #d0d0d0;
                        border: 1px solid #a0a0a0;
                    }
                """)
                delete_btn.clicked.connect(lambda checked, report_id=report['id']: self.delete_report_by_id(report_id))
                
                operation_layout.addWidget(view_btn)
                operation_layout.addWidget(delete_btn)
                
                self.tree_widget.setItemWidget(item, 8, operation_widget)
                
                # 设置数据
                item.setData(0, Qt.UserRole, report['id'])
            
            print(f"异步加载完成，成功显示 {len(reports)} 个报告")
            
        except Exception as e:
            print(f"处理异步加载结果失败: {str(e)}")
            self.is_loading = False
            
            # 显示错误提示
            self.tree_widget.clear()
            error_item = QTreeWidgetItem(self.tree_widget)
            error_item.setText(0, f"处理加载结果失败: {str(e)}")
            self.tree_widget.setFirstItemColumnSpanned(error_item, True)
            error_item.setTextAlignment(0, Qt.AlignCenter | Qt.AlignVCenter)
            error_item.setBackground(0, QBrush(QColor("#ffebee")))
            error_item.setForeground(0, QBrush(QColor("#c62828")))

    def load_reports(self):
        """加载报告列表 - 使用分页功能"""
        # 重置到第一页
        self.current_page = 1
        
        # 获取筛选条件
        filters = self.get_filters()
        
        # 添加分页参数
        filters['page'] = self.current_page
        filters['page_size'] = self.current_page_size
        
        # 使用分页加载
        self.load_reports_with_pagination(filters)

    def display_reports(self, reports):
        """显示报告数据到树形控件"""
        try:
            # 清空树形控件
            self.tree_widget.clear()
            
            if not reports:
                # 创建提示节点 - 合并第一行所有单元格并居中显示
                empty_item = QTreeWidgetItem(self.tree_widget)
                empty_item.setText(0, "暂无测试报告")
                
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
                
                return
            
            # 按开始时间排序（最新的在前）
            reports.sort(key=lambda x: x.get('start_time', ''), reverse=True)
            
            # 计算起始序号：根据当前页码和每页大小
            start_index = (self.current_page - 1) * self.current_page_size + 1
            
            # 直接平铺显示所有报告
            for i, report in enumerate(reports, start=start_index):
                item = QTreeWidgetItem(self.tree_widget)
                
                # 设置所有列的文本居中对齐
                for col in range(8):  # 0-7列（第8列是操作列，使用widget）
                    item.setTextAlignment(col, Qt.AlignCenter)
                
                # 序号
                item.setText(0, str(i))
                
                # 报告名称
                report_name = report.get('report_name', 'N/A')
                item.setText(1, report_name)
                
                # 用例数
                total_cases = report.get('total_cases', 0)
                item.setText(2, str(total_cases))
                
                # 状态
                status = report.get('status', 'unknown')
                status_text = {
                    'success': '成功',
                    'failure': '失败',
                    'error': '错误',
                    'running': '执行中'
                }.get(status, status)
                
                # 设置状态颜色
                status_color = {
                    'success': '#28a745',  # 绿色
                    'failure': '#dc3545',  # 红色
                    'error': '#ffc107',    # 黄色
                    'running': '#17a2b8'   # 蓝色
                }.get(status, '#6c757d')   # 默认灰色
                
                item.setText(3, status_text)
                item.setForeground(3, QColor(status_color))
                
                # 通过率
                total_cases = report.get('total_cases', 0)
                passed_cases = report.get('passed_cases', 0)
                if total_cases > 0:
                    success_rate = (passed_cases / total_cases) * 100
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
                
                # 操作栏 - 使用按钮组件替换文字按钮
                operation_widget = QWidget()
                operation_layout = QHBoxLayout(operation_widget)
                operation_layout.setContentsMargins(5, 2, 5, 2)
                operation_layout.setSpacing(3)
                operation_layout.setAlignment(Qt.AlignCenter)  # 设置布局居中对齐
                
                # 查看详情按钮
                view_btn = QPushButton()
                view_btn.setFixedSize(25, 25)
                view_btn.setIcon(self.get_icon("detail.png"))
                view_btn.setToolTip("查看详情")
                view_btn.setStyleSheet("""
                    QPushButton {
                        border: 1px solid transparent;
                        background: transparent;
                        padding: 2px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background: #e0e0e0;
                        border: 1px solid #c0c0c0;
                    }
                    QPushButton:pressed {
                        background: #d0d0d0;
                        border: 1px solid #a0a0a0;
                    }
                """)
                view_btn.clicked.connect(lambda checked, report_id=report['id']: self.view_report_detail_by_id(report_id))
                
                # 删除按钮
                delete_btn = QPushButton()
                delete_btn.setFixedSize(25, 25)
                delete_btn.setIcon(self.get_icon("delete.png"))
                delete_btn.setToolTip("删除")
                delete_btn.setStyleSheet("""
                    QPushButton {
                        border: 1px solid transparent;
                        background: transparent;
                        padding: 2px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background: #e0e0e0;
                        border: 1px solid #c0c0c0;
                    }
                    QPushButton:pressed {
                        background: #d0d0d0;
                        border: 1px solid #a0a0a0;
                    }
                """)
                delete_btn.clicked.connect(lambda checked, report_id=report['id']: self.delete_report_by_id(report_id))
                
                operation_layout.addWidget(view_btn)
                operation_layout.addWidget(delete_btn)
                
                self.tree_widget.setItemWidget(item, 8, operation_widget)
                
                # 设置数据
                item.setData(0, Qt.UserRole, report['id'])
            
            # 调试信息：显示加载完成
            print(f"=== 报告显示完成 ===")
            print(f"成功显示 {len(reports)} 份报告")
            if reports:
                print("报告列表:")
                for i, report in enumerate(reports):
                    print(f"  {i+1}. ID: {report.get('id', 'N/A')}, 名称: {report.get('name', 'N/A')}, 状态: {report.get('status', 'N/A')}")
            else:
                print("没有找到符合条件的报告")

        except Exception as e:
            print(f"显示报告数据失败: {str(e)}")
            import traceback
            traceback.print_exc()

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

        # 项目
        project_id = self.project_combo.currentData()
        if project_id:
            filters['project_id'] = project_id

        # 调度（测试用例集）
        if self.current_scheduler_id:
            filters['scheduler_id'] = self.current_scheduler_id

        # 搜索关键词
        search_text = self.search_edit.text().strip()
        if search_text:
            filters['search'] = search_text

        return filters

    def on_filter_changed(self):
        """筛选条件变化"""
        # 获取发送信号的控件
        sender = self.sender()
        
        # 如果是项目选择变更，需要刷新测试用例集
        if sender == self.project_combo:
            # 保存当前选中的调度ID
            current_scheduler_id = self.current_scheduler_id
            
            # 刷新测试用例集列表
            self.load_schedulers()
            
            # 尝试恢复之前选中的调度项
            found_previous = False
            if current_scheduler_id:
                for i in range(self.scheduler_list_widget.count()):
                    item = self.scheduler_list_widget.item(i)
                    if item.flags() != Qt.NoItemFlags and item.data(Qt.UserRole) == current_scheduler_id:
                        self.scheduler_list_widget.setCurrentItem(item)
                        self.current_scheduler_id = current_scheduler_id
                        found_previous = True
                        break
            
            # 如果没有找到之前的调度项，自动选择第一个测试用例集
            if not found_previous and self.scheduler_list_widget.count() > 0:
                first_item = self.scheduler_list_widget.item(0)
                if first_item.flags() != Qt.NoItemFlags:  # 确保不是提示项
                    self.scheduler_list_widget.setCurrentItem(first_item)
                    self.current_scheduler_id = first_item.data(Qt.UserRole)
        
        # 刷新报告列表，根据是否有当前选中的调度ID决定调用哪个方法
        if self.current_scheduler_id:
            # 如果有选中的调度ID，使用调度过滤方法
            self.load_reports_by_scheduler(self.current_scheduler_id)
        else:
            # 如果没有选中的调度ID，使用普通加载方法
            self.load_reports()

    def on_refresh_clicked(self):
        """刷新按钮点击事件"""
        # 保存当前选中的调度ID
        current_scheduler_id = self.current_scheduler_id
        
        # 刷新测试用例集列表（新增调度后需要更新列表）
        self.load_schedulers()
        
        # 尝试恢复之前选中的调度项
        found_previous = False
        if current_scheduler_id:
            for i in range(self.scheduler_list_widget.count()):
                item = self.scheduler_list_widget.item(i)
                if item.flags() != Qt.NoItemFlags and item.data(Qt.UserRole) == current_scheduler_id:
                    self.scheduler_list_widget.setCurrentItem(item)
                    self.current_scheduler_id = current_scheduler_id
                    found_previous = True
                    break
        
        # 如果没有找到之前的调度项，自动选择第一个测试用例集
        if not found_previous and self.scheduler_list_widget.count() > 0:
            first_item = self.scheduler_list_widget.item(0)
            if first_item.flags() != Qt.NoItemFlags:  # 确保不是提示项
                self.scheduler_list_widget.setCurrentItem(first_item)
                self.current_scheduler_id = first_item.data(Qt.UserRole)
        
        # 根据当前选中的调度ID决定如何刷新报告列表
        if self.current_scheduler_id:
            # 如果有选中的调度ID，使用调度过滤方法
            self.load_reports_by_scheduler(self.current_scheduler_id)
        else:
            # 如果没有选中的调度ID，使用普通加载方法
            self.load_reports()

    def update_pagination_ui(self, pagination_info):
        """更新分页UI状态"""
        total = pagination_info.get('total', 0)
        page = pagination_info.get('page', 1)
        page_size = pagination_info.get('page_size', 20)
        total_pages = pagination_info.get('total_pages', 0)
        has_prev = pagination_info.get('has_prev', False)
        has_next = pagination_info.get('has_next', False)
        
        # 更新分页信息标签
        self.pagination_label.setText(f"共 {total} 条记录")
        self.page_input.setText(str(page))
        self.total_pages_label.setText(f"/ {total_pages}")
        
        # 更新按钮状态
        self.first_page_btn.setEnabled(has_prev)
        self.prev_page_btn.setEnabled(has_prev)
        self.next_page_btn.setEnabled(has_next)
        self.last_page_btn.setEnabled(has_next)
        
        # 更新每页显示数量
        self.page_size_combo.setCurrentText(str(page_size))

    def go_to_first_page(self):
        """跳转到首页"""
        self.current_page = 1
        self.load_reports_with_pagination()

    def go_to_prev_page(self):
        """跳转到上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_reports_with_pagination()

    def go_to_next_page(self):
        """跳转到下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_reports_with_pagination()

    def go_to_last_page(self):
        """跳转到末页"""
        self.current_page = self.total_pages
        self.load_reports_with_pagination()

    def go_to_specific_page(self):
        """跳转到指定页码"""
        try:
            page = int(self.page_input.text())
            if 1 <= page <= self.total_pages:
                self.current_page = page
                self.load_reports_with_pagination()
            else:
                self.page_input.setText(str(self.current_page))
        except ValueError:
            self.page_input.setText(str(self.current_page))

    def on_page_size_changed(self, page_size_text):
        """每页显示数量变化"""
        try:
            page_size = int(page_size_text)
            self.current_page_size = page_size
            self.current_page = 1  # 重置到第一页
            self.load_reports_with_pagination()
        except ValueError:
            pass

    def load_reports_with_pagination(self, filters=None):
        """使用分页加载测试报告"""
        try:
            # 获取筛选条件
            if filters is None:
                filters = self.get_filters()
            
            # 添加分页参数
            filters['page'] = self.current_page
            filters['page_size'] = self.current_page_size
            
            # 使用分页API获取数据
            result = self.report_service.get_reports_with_pagination(filters)
            
            if result:
                reports = result.get('data', [])
                pagination_info = result.get('pagination', {})
                
                # 更新分页信息
                self.total_pages = pagination_info.get('total_pages', 0)
                
                # 更新UI
                self.update_pagination_ui(pagination_info)
                
                # 显示报告数据
                self.display_reports(reports)
            else:
                # 显示空数据
                self.tree_widget.clear()
                self.update_pagination_ui({
                    'total': 0,
                    'page': 1,
                    'page_size': self.current_page_size,
                    'total_pages': 0,
                    'has_prev': False,
                    'has_next': False
                })
                
        except Exception as e:
            print(f"分页加载测试报告失败: {str(e)}")
            import traceback
            traceback.print_exc()

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
            Toast.warning(self, "提示", "请先选择一个测试报告")
            return

        # 创建详情页（如果不存在）
        if self.detail_page is None:
            self.detail_page = ReportDetailPage(report_data=report_data)
            self.detail_page.back_requested.connect(self.show_list_page)
            self.stack_layout.addWidget(self.detail_page)
        else:
            # 如果详情页已存在，更新报告数据
            self.detail_page.report_data = report_data
            self.detail_page.load_report_details()
        
        # 切换到详情页
        self.stack_layout.setCurrentWidget(self.detail_page)

    def view_report_detail_by_id(self, report_id):
        """根据报告ID查看详情"""
        if not report_id:
            Toast.warning(self, "提示", "无效的报告ID")
            return

        try:
            report_data = self.report_service.get_report_with_details(report_id)
            if report_data:
                # 创建详情页（如果不存在）
                if self.detail_page is None:
                    self.detail_page = ReportDetailPage(report_data=report_data)
                    self.detail_page.back_requested.connect(self.show_list_page)
                    self.stack_layout.addWidget(self.detail_page)
                else:
                    # 如果详情页已存在，更新报告数据
                    self.detail_page.report_data = report_data
                    self.detail_page.load_report_details()
                
                # 切换到详情页
                self.stack_layout.setCurrentWidget(self.detail_page)
            else:
                Toast.warning(self, "提示", "报告数据不存在")
        except Exception as e:
            Toast.critical(self, "错误", f"加载报告详情失败: {str(e)}")
    
    def show_list_page(self):
        """显示列表页"""
        self.stack_layout.setCurrentWidget(self.list_page)

    def filter_by_scheduler(self, jump_data):
        """根据调度信息自动筛选报告列表
        
        Args:
            jump_data: 跳转数据字典，包含调度信息和报告列表
        """
        try:
            # 确保显示列表页
            self.show_list_page()
            
            # 获取调度信息
            scheduler_data = jump_data.get('scheduler', {})
            reports = jump_data.get('reports', [])
            
            if not scheduler_data or not reports:
                print("调度数据或报告列表为空，使用普通加载")
                self.load_reports()
                return
            
            # 设置当前调度ID用于过滤
            scheduler_id = scheduler_data.get('id')
            if scheduler_id:
                self.current_scheduler_id = scheduler_id
                
                # 尝试在调度列表中选择对应的调度项
                for i in range(self.scheduler_list_widget.count()):
                    item = self.scheduler_list_widget.item(i)
                    if item.flags() != Qt.NoItemFlags and item.data(Qt.UserRole) == scheduler_id:
                        self.scheduler_list_widget.setCurrentItem(item)
                        break
            
            # 设置项目筛选
            project_id = scheduler_data.get('project_id')
            if project_id and self.project_combo:
                # 查找项目在组合框中的索引
                for i in range(self.project_combo.count()):
                    if self.project_combo.itemData(i) == project_id:
                        self.project_combo.setCurrentIndex(i)
                        break
            
            # 设置报告名称搜索
            scheduler_name = scheduler_data.get('name', '')
            if scheduler_name and self.search_edit:
                self.search_edit.setText(scheduler_name)
            
            # 加载调度相关的报告
            if scheduler_id:
                self.load_reports_by_scheduler(scheduler_id)
            else:
                self.load_reports()
                
            print(f"已应用调度筛选: {scheduler_name}")
                
        except Exception as e:
            print(f"应用调度筛选失败: {str(e)}")
            # 出错时使用普通加载
            self.load_reports()

    def delete_scheduler_reports(self, scheduler_data):
        """删除调度组的所有报告"""
        if not scheduler_data:
            return
            
        # 确认删除
        msg_box = QMessageBox(QMessageBox.Question, "确认删除", "确定要删除这个调度组的所有测试报告吗？")
        confirm_button = msg_box.addButton("确认", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_button)
        msg_box.exec_()
        reply = QMessageBox.Yes if msg_box.clickedButton() == confirm_button else QMessageBox.No
        
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
                        Toast.info(self, f"成功删除 {success_count} 个测试报告")
                        # 重新加载报告列表
                        self.load_reports()
                    else:
                        Toast.warn(self, "报告删除失败")
                else:
                    # 如果是单个报告ID，直接删除
                    self.delete_report_by_id(scheduler_data)
            except Exception as e:
                Toast.error(self, f"删除报告失败: {str(e)}")

    def delete_report_by_id(self, report_id):
        """根据报告ID删除报告"""
        if not report_id:
            return
            
        # 确认删除
        msg_box = QMessageBox(QMessageBox.Question, "确认删除", "确定要删除这个测试报告吗？")
        confirm_button = msg_box.addButton("确认", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_button)
        msg_box.exec_()
        reply = QMessageBox.Yes if msg_box.clickedButton() == confirm_button else QMessageBox.No
        
        if reply == QMessageBox.Yes:
            try:
                # 删除报告
                success = self.report_service.delete_report(report_id)
                if success:
                    Toast.info(self, "报告删除成功")
                    # 重新加载报告列表
                    self.load_reports()
                else:
                    Toast.warn(self, "报告删除失败")
            except Exception as e:
                Toast.error(self, f"删除报告失败: {str(e)}")



    def delete_selected_report(self):
        """删除选中的报告"""
        report_data = self.get_selected_report_data()
        if not report_data:
            Toast.warn(self, "请先选择一个测试报告")
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
                Toast.info(self, "报告删除成功")
            except Exception as e:
                Toast.error(self, f"删除报告失败: {str(e)}")

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
                    Toast.information(self, "成功", f"已清理 {deleted_count} 个旧报告")

        except Exception as e:
            Toast.critical(self, "错误", f"清理报告失败: {str(e)}")

    def toggle_scheduler_status(self, scheduler_id, enable):
        """切换调度任务状态"""
        try:
            # 更新调度状态
            success = self.scheduler_service.update_scheduler_status(scheduler_id, enable)
            
            if success:
                action_text = "启用" if enable else "禁用"
                Toast.information(self, "成功", f"调度任务{action_text}成功")
                # 刷新调度任务列表
                self.load_schedulers()
            else:
                Toast.warning(self, "警告", "操作失败，请重试")
                
        except Exception as e:
            print(f"切换调度状态失败: {e}")
            Toast.critical(self, "错误", f"操作失败: {str(e)}")


