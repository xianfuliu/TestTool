from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QFrame,
    QApplication,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QBrush, QPen, QLinearGradient
from src.utils.resource_utils import resource_path
import os
import time


class LoadingTask:
    """加载任务类"""

    def __init__(self, name, weight=1, delay=0):
        self.name = name
        self.weight = weight  # 任务权重，用于计算进度
        self.delay = delay  # 延迟执行时间（ms）
        self.completed = False
        self.progress = 0

    def set_progress(self, progress):
        """设置任务进度"""
        self.progress = max(0, min(100, progress))

    def complete(self):
        """标记任务完成"""
        self.completed = True
        self.progress = 100


class LoadingWorker(QThread):
    """加载工作线程"""

    task_progress = pyqtSignal(str, int)  # 任务名, 进度
    task_completed = pyqtSignal(str)  # 任务名
    all_completed = pyqtSignal()  # 所有任务完成

    def __init__(self, tasks, main_window):
        super().__init__()
        self.tasks = tasks
        self.main_window = main_window
        self.running = True

    def run(self):
        """执行所有加载任务"""
        total_weight = sum(task.weight for task in self.tasks)

        for task in self.tasks:
            if not self.running:
                break

            # 延迟执行
            if task.delay > 0:
                time.sleep(task.delay / 1000)

            # 根据任务名称执行实际的初始化操作
            self.execute_task(task)

        if self.running:
            self.all_completed.emit()

    def execute_task(self, task):
        """执行具体的初始化任务"""
        try:
            if task.name == "加载配置文件":
                self.load_config_task(task)
            elif task.name == "初始化UI框架":
                self.init_ui_framework_task(task)
            elif task.name == "启动调度服务":
                self.start_scheduler_task(task)
            elif task.name == "初始化测试数据模块":
                self.init_test_data_task(task)
            elif task.name == "初始化数据查询模块":
                self.init_data_query_task(task)
            elif task.name == "初始化接口工具模块":
                self.init_api_tool_task(task)
            elif task.name == "初始化接口自动化模块":
                self.init_interface_auto_task(task)
            elif task.name == "完成最终配置":
                self.finalize_config_task(task)
            else:
                # 默认模拟进度
                self.simulate_task_progress(task)
        except Exception as e:
            print(f"任务 {task.name} 执行失败: {e}")
            task.complete()
            self.task_completed.emit(task.name)

    def simulate_task_progress(self, task):
        """模拟任务进度（用于非关键任务）"""
        for progress in range(0, 101, 20):
            if not self.running:
                break
            task.set_progress(progress)
            self.task_progress.emit(task.name, progress)
            time.sleep(0.1)

        task.complete()
        self.task_completed.emit(task.name)

    def load_config_task(self, task):
        """加载配置文件任务"""
        # 配置文件已经在main.py中加载完成
        task.set_progress(100)
        self.task_progress.emit(task.name, 100)
        task.complete()
        self.task_completed.emit(task.name)

    def init_ui_framework_task(self, task):
        """初始化UI框架任务"""
        # UI框架已经在MainWindow构造函数中初始化
        task.set_progress(100)
        self.task_progress.emit(task.name, 100)
        task.complete()
        self.task_completed.emit(task.name)

    def start_scheduler_task(self, task):
        """启动调度服务任务"""
        # 调度服务已经在main.py中启动
        task.set_progress(100)
        self.task_progress.emit(task.name, 100)
        task.complete()
        self.task_completed.emit(task.name)

    def init_test_data_task(self, task):
        """初始化测试数据模块任务"""
        # 测试数据Tab的初始化
        if hasattr(self.main_window, "test_data_tab"):
            # 等待自动生成完成
            from PyQt5.QtCore import QTimer

            def check_auto_generate():
                task.set_progress(100)
                self.task_progress.emit(task.name, 100)
                task.complete()
                self.task_completed.emit(task.name)

            QTimer.singleShot(200, check_auto_generate)
        else:
            self.simulate_task_progress(task)

    def init_data_query_task(self, task):
        """初始化数据查询模块任务"""
        # 数据查询Tab的初始化
        if hasattr(self.main_window, "data_query_tab"):
            task.set_progress(100)
            self.task_progress.emit(task.name, 100)
            task.complete()
            self.task_completed.emit(task.name)
        else:
            self.simulate_task_progress(task)

    def init_api_tool_task(self, task):
        """初始化接口工具模块任务"""
        # 接口工具Tab的初始化
        if hasattr(self.main_window, "api_tool_tab"):
            task.set_progress(100)
            self.task_progress.emit(task.name, 100)
            task.complete()
            self.task_completed.emit(task.name)
        else:
            self.simulate_task_progress(task)

    def init_interface_auto_task(self, task):
        """初始化接口自动化模块任务"""
        # 接口自动化Tab的延迟初始化
        if hasattr(self.main_window, "interface_auto_tab"):
            # 监听接口自动化的延迟初始化
            def on_delayed_init_complete():
                task.set_progress(100)
                self.task_progress.emit(task.name, 100)
                task.complete()
                self.task_completed.emit(task.name)

            # 检查接口自动化Tab是否已经初始化
            if (
                hasattr(self.main_window.interface_auto_tab, "ui_initialized")
                and self.main_window.interface_auto_tab.ui_initialized
            ):
                # 如果已经初始化，等待delayed_init完成
                from PyQt5.QtCore import QTimer

                QTimer.singleShot(1500, on_delayed_init_complete)
            else:
                self.simulate_task_progress(task)
        else:
            self.simulate_task_progress(task)

    def finalize_config_task(self, task):
        """完成最终配置任务"""
        # 等待所有其他任务完成
        task.set_progress(100)
        self.task_progress.emit(task.name, 100)
        task.complete()
        self.task_completed.emit(task.name)

    def stop(self):
        """停止加载"""
        self.running = False


class LoadingPage(QWidget):
    """中间加载页面"""

    loading_completed = pyqtSignal()  # 加载完成信号

    def __init__(self, main_window, config=None):
        super().__init__()
        self.main_window = main_window
        self.config = config or {}
        self.tasks = []
        self.worker = None
        self.init_ui()
        self.setup_tasks()

    def init_ui(self):
        """初始化UI"""
        # 设置窗口标题
        self.setWindowTitle("测试工具 - 启动中")

        # 设置窗口大小和位置，优化宽高比
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()

        # 设置合适的窗口大小（16:9宽高比）
        width = min(800, screen_rect.width() * 0.4)
        height = int(width * 9 / 16)

        # 居中显示
        x = (screen_rect.width() - width) // 2
        y = (screen_rect.height() - height) // 2
        self.setGeometry(x, y, width, height)

        # 设置窗口样式
        self.setStyleSheet(
            """
            QLabel {
                color: white;
                background: transparent;
                border: none;
            }
            QProgressBar {
                border: none;
                border-radius: 12px;
                background-color: rgba(255, 255, 255, 0.05);
                text-align: center;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 2px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                stop:0 #00E5FF, stop:0.5 #00B0FF, stop:1 #0091EA);
                border-radius: 10px;
                margin: 2px;
            }
        """
        )

        # 设置窗口标志，使其看起来更像启动窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        # 设置透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 主布局
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(25)
        layout.setContentsMargins(40, 40, 40, 40)

        # 应用图标和标题
        self.create_header(layout)

        # 进度条区域
        self.create_progress_area(layout)

    def create_header(self, layout):
        """创建标题区域"""
        # 创建标题容器，用于更好的布局控制
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setSpacing(15)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # 应用图标
        try:
            icon_path = resource_path("src/resources/icons/app_icon.png")
            if os.path.exists(icon_path):
                pixmap = QPixmap(icon_path)
                # 优化图标大小，适应新的宽高比
                pixmap = pixmap.scaled(
                    90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                icon_label = QLabel()
                icon_label.setPixmap(pixmap)
                icon_label.setAlignment(Qt.AlignCenter)
                icon_label.setStyleSheet(
                    "padding: 8px; background: transparent; border-radius: 0px; border: none;"
                )
                header_layout.addWidget(icon_label)
        except Exception:
            # 如果没有图标，创建一个占位图标
            icon_label = QLabel("⚡")
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setFont(QFont("Microsoft YaHei", 42, QFont.Bold))
            icon_label.setStyleSheet(
                "color: rgba(255, 255, 255, 0.9); padding: 8px; background: transparent; border-radius: 0px; border: none;"
            )
            header_layout.addWidget(icon_label)

        # 应用标题
        title_label = QLabel("测试工具")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 26, QFont.Bold))
        title_label.setStyleSheet(
            "color: white; margin: 0; padding: 0; letter-spacing: 1px;"
        )
        header_layout.addWidget(title_label)

        # 将标题容器添加到主布局
        layout.addWidget(header_container)

    def create_progress_area(self, layout):
        """创建进度条区域"""
        # 创建进度条容器，用于更好的布局控制
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setAlignment(Qt.AlignCenter)
        progress_layout.setSpacing(12)
        progress_layout.setContentsMargins(0, 0, 0, 0)

        # 主进度条
        self.main_progress = QProgressBar()
        self.main_progress.setMinimum(0)
        self.main_progress.setMaximum(100)
        self.main_progress.setValue(0)
        self.main_progress.setFixedHeight(18)
        self.main_progress.setTextVisible(True)
        self.main_progress.setFormat("加载进度: %p%")
        progress_layout.addWidget(self.main_progress)

        # 将进度容器添加到主布局
        layout.addWidget(progress_container)

    def setup_tasks(self):
        """设置加载任务"""
        # 检查登录开关配置
        enable_login = self.config.get("auth", {}).get("enable_login", True)

        # 基础任务列表
        self.tasks = [
            LoadingTask("加载配置文件", weight=5, delay=0),
            LoadingTask("初始化UI框架", weight=15, delay=100),
            LoadingTask("启动调度服务", weight=10, delay=200),
        ]

        # 只有在启用登录功能时才添加数据库相关任务
        if enable_login:
            self.tasks.extend(
                [
                    LoadingTask("初始化测试数据模块", weight=15, delay=300),
                    LoadingTask("初始化数据查询模块", weight=15, delay=400),
                    LoadingTask("初始化接口工具模块", weight=15, delay=500),
                    LoadingTask("初始化接口自动化模块", weight=20, delay=600),
                ]
            )
        else:
            print("登录功能已关闭，跳过数据库相关模块初始化")

        # 添加最终配置任务
        self.tasks.append(LoadingTask("完成最终配置", weight=5, delay=800))

    def start_loading(self):
        """开始加载"""
        # 创建并启动工作线程
        self.worker = LoadingWorker(self.tasks, self.main_window)
        self.worker.task_progress.connect(self.on_task_progress)
        self.worker.task_completed.connect(self.on_task_completed)
        self.worker.all_completed.connect(self.on_all_completed)
        self.worker.start()

    @pyqtSlot(str, int)
    def on_task_progress(self, task_name, progress):
        """处理任务进度更新"""
        # 更新总进度
        self.update_main_progress()

    @pyqtSlot(str)
    def on_task_completed(self, task_name):
        """处理任务完成"""
        # 进度文本已移除，无需更新
        pass

    @pyqtSlot()
    def on_all_completed(self):
        """所有任务完成"""
        self.main_progress.setValue(100)

        # 延迟500ms后发出完成信号
        QTimer.singleShot(500, self.loading_completed.emit)

    def update_main_progress(self):
        """更新主进度条"""
        total_weight = sum(task.weight for task in self.tasks)
        completed_weight = 0

        for task in self.tasks:
            # 计算加权进度
            task_progress = task.progress / 100.0
            completed_weight += task_progress * task.weight

        # 计算总进度百分比
        total_progress = int((completed_weight / total_weight) * 100)
        self.main_progress.setValue(total_progress)

    def stop_loading(self):
        """停止加载"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

    def closeEvent(self, event):
        """关闭事件处理"""
        self.stop_loading()
        super().closeEvent(event)

    def paintEvent(self, event):
        """绘制窗口圆角效果"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 创建圆角矩形路径
        rect = self.rect()
        radius = 25  # 圆角半径

        # 先绘制透明背景
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect)

        # 设置渐变背景
        gradient = QLinearGradient(0, 0, 0, rect.height())
        gradient.setColorAt(0, QColor(26, 35, 126))  # #1A237E
        gradient.setColorAt(0.3, QColor(40, 53, 147))  # #283593
        gradient.setColorAt(0.7, QColor(48, 63, 159))  # #303F9F
        gradient.setColorAt(1, QColor(57, 73, 171))  # #3949AB

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)

        # 绘制圆角矩形
        painter.drawRoundedRect(rect, radius, radius)
