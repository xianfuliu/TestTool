import threading
import subprocess
import time
import logging
from typing import Optional
import os
import sys

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QGroupBox,
    QMessageBox,
    QFrame,
    QProgressBar,
    QSplitter,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QApplication,
)
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QIcon, QColor

from src.ui.widgets.toast_tips import Toast

logger = logging.getLogger(__name__)


class FastAPIService:
    """FastAPI服务管理器"""

    def __init__(self, config=None):
        self.process: Optional[subprocess.Popen] = None
        self.thread: Optional[threading.Thread] = None
        self.is_running = False
        self.port = 8000
        self.config = config or {}
        self.auto_start = self.config.get("auto_start", False)
        self.default_port = self.config.get("default_port", 8000)
        self._stop_event = threading.Event()
        
        # 如果配置了自动启动，则立即启动服务
        if self.auto_start:
            logger.info("检测到自动启动配置，正在启动FastAPI服务...")
            self.start(self.default_port)

    def start(self, port: int = 8000) -> bool:
        """启动FastAPI服务"""
        try:
            if self.is_running:
                logger.warning("FastAPI服务已经在运行中")
                return False

            self.port = port
            self._stop_event.clear()

            # 使用线程启动FastAPI服务
            self.thread = threading.Thread(target=self._run_fastapi, daemon=True)
            self.thread.start()

            # 等待服务启动，最多等待5秒
            for i in range(5):
                if self.is_running:
                    break
                time.sleep(1)

            if self.is_running:
                logger.info(f"FastAPI服务启动成功，端口: {self.port}")
                return True
            else:
                logger.error("FastAPI服务启动超时")
                return False

        except Exception as e:
            logger.error(f"启动FastAPI服务失败: {e}")
            return False

    def _run_fastapi(self):
        """运行FastAPI应用"""
        try:
            # 导入并运行FastAPI应用
            from src.api.main import FastAPIApp

            fastapi_app = FastAPIApp()
            # 设置端口
            fastapi_app.instance_manager.port = self.port

            # 标记服务为运行中
            self.is_running = True
            
            # 运行应用
            fastapi_app.run()

        except Exception as e:
            logger.error(f"FastAPI服务运行异常: {e}")
            self.is_running = False

    def stop(self) -> bool:
        """停止FastAPI服务"""
        try:
            if not self.is_running:
                logger.warning("FastAPI服务未在运行")
                return False

            # 设置停止事件
            self._stop_event.set()
            self.is_running = False

            # 等待线程结束，最多等待3秒
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=3)

            logger.info("FastAPI服务已停止")
            return True

        except Exception as e:
            logger.error(f"停止FastAPI服务失败: {e}")
            return False

    def get_status(self) -> dict:
        """获取服务状态"""
        return {"is_running": self.is_running, "port": self.port, "service": "FastAPI"}

    def restart(self, port: int = 8000) -> bool:
        """重启FastAPI服务"""
        try:
            if self.is_running:
                self.stop()
                time.sleep(1)

            return self.start(port)

        except Exception as e:
            logger.error(f"重启FastAPI服务失败: {e}")
            return False


class ApiManagementTab(QWidget):
    """API管理标签页 - 集成优化版"""

    status_updated = pyqtSignal(dict)

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.config = config or {}
        self.api_service = FastAPIService(self.config)
        self.init_ui()
        self.setup_timer()
        # 初始化按钮状态
        self.update_button_states()
        
        # 加载并刷新接口列表
        self.refresh_interface_list()

    def get_icon(self, icon_name):
        """获取图标，支持exe打包后的资源路径"""
        import os
        import sys

        # 尝试多种路径方式加载图标
        icon_paths = [
            # 开发环境路径
            os.path.join("src", "resources", "icons", icon_name),
            # exe打包后路径
            os.path.join(
                os.path.dirname(sys.executable), "src", "resources", "icons", icon_name
            ),
            # 相对路径（如果exe在项目根目录）
            os.path.join("src", "resources", "icons", icon_name),
            # 临时解压路径（PyInstaller）
            (
                os.path.join(sys._MEIPASS, "src", "resources", "icons", icon_name)
                if hasattr(sys, "_MEIPASS")
                else None
            ),
        ]

        for path in icon_paths:
            if path and os.path.exists(path):
                return QIcon(path)

        # 如果所有路径都找不到，返回空图标
        return QIcon()

    def init_ui(self):
        """初始化界面 - 统一布局版"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 创建统一的服务状态容器
        unified_panel = self.create_unified_panel()
        main_layout.addWidget(unified_panel, stretch=0)  # 不拉伸，固定高度
        
        # 创建接口列表容器
        interface_panel = self.create_interface_panel()
        main_layout.addWidget(interface_panel, stretch=1)  # 拉伸，占据剩余空间

    def create_unified_panel(self):
        """创建统一的服务状态面板"""
        panel = QGroupBox("")  # 标题置为空
        panel.setStyleSheet(
            """
            QGroupBox {
                border: none;  /* 隐藏边框 */
                background-color: transparent;  /* 透明背景 */
                margin-top: 0px;
                padding-top: 0px;
            }
            QGroupBox::title {
                display: none;  /* 隐藏标题 */
            }
        """
        )

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 状态指示器
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)

        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(16, 16)
        self.status_indicator.setStyleSheet(
            """
            QLabel {
                border-radius: 8px;
                background-color: #dc3545;
            }
        """
        )

        self.status_label = QLabel("服务未启动")
        self.status_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.status_label.setStyleSheet("color: #495057;")

        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        layout.addWidget(status_frame)

        # 详细信息网格布局
        info_grid = QVBoxLayout()
        info_grid.setSpacing(8)
        info_grid.setAlignment(Qt.AlignTop)  # 居上对齐

        # 端口配置和图标按钮在同一行
        control_row = QHBoxLayout()
        control_row.setAlignment(Qt.AlignLeft)  # 左对齐
        
        # 端口配置
        port_layout = QHBoxLayout()
        port_layout.setAlignment(Qt.AlignLeft)  # 左对齐
        port_label = QLabel("端口:")
        port_label.setFont(QFont("Microsoft YaHei", 10))
        port_label.setStyleSheet("color: #6c757d; min-width: 40px;")
        port_layout.addWidget(port_label)
        
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(8000, 9000)
        self.port_spinbox.setValue(8000)
        self.port_spinbox.setFixedWidth(80)
        self.port_spinbox.setStyleSheet("""
            QSpinBox {
                border: 1px solid #ced4da;
                border-radius: 3px;
                padding: 4px;
                background-color: white;
            }
        """)
        port_layout.addWidget(self.port_spinbox)
        
        # 图标按钮贴着端口配置右侧
        button_layout = QHBoxLayout()
        button_layout.setSpacing(6)
        button_layout.setContentsMargins(10, 0, 0, 0)  # 左侧间距10px

        # 启动按钮 - 只显示图标，无背景色
        self.start_button = QPushButton()
        self.start_button.setIcon(self.get_icon("start.png"))
        self.start_button.setToolTip("启动服务")
        self.start_button.setFixedSize(24, 24)
        self.start_button.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """
        )
        self.start_button.clicked.connect(self.start_service)
        button_layout.addWidget(self.start_button)

        # 停止按钮
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.get_icon("stoping.png"))
        self.stop_button.setToolTip("停止服务")
        self.stop_button.setFixedSize(24, 24)
        self.stop_button.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """
        )
        self.stop_button.clicked.connect(self.stop_service)
        button_layout.addWidget(self.stop_button)

        # 重启按钮
        self.restart_button = QPushButton()
        self.restart_button.setIcon(self.get_icon("refresh.png"))
        self.restart_button.setToolTip("重启服务")
        self.restart_button.setFixedSize(24, 24)
        self.restart_button.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """
        )
        self.restart_button.clicked.connect(self.restart_service)
        button_layout.addWidget(self.restart_button)
        
        port_layout.addLayout(button_layout)
        control_row.addLayout(port_layout)
        control_row.addStretch()  # 在右侧添加弹性空间
        info_grid.addLayout(control_row)

        # 服务详细信息
        details_layout = QVBoxLayout()
        details_layout.setSpacing(6)
        details_layout.setAlignment(Qt.AlignTop)  # 居上对齐

        # 启动模式
        mode_layout = QHBoxLayout()
        mode_layout.setAlignment(Qt.AlignLeft)  # 左对齐
        mode_layout.addWidget(QLabel("启动模式:"))
        self.mode_label = QLabel("-")
        self.mode_label.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.mode_label.setStyleSheet("color: #495057;")
        mode_layout.addWidget(self.mode_label)
        mode_layout.addStretch()
        details_layout.addLayout(mode_layout)

        # 启动时间
        time_layout = QHBoxLayout()
        time_layout.setAlignment(Qt.AlignLeft)  # 左对齐
        time_layout.addWidget(QLabel("启动时间:"))
        self.time_label = QLabel("-")
        self.time_label.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.time_label.setStyleSheet("color: #495057;")
        time_layout.addWidget(self.time_label)
        time_layout.addStretch()
        details_layout.addLayout(time_layout)

        # 运行时长
        duration_layout = QHBoxLayout()
        duration_layout.setAlignment(Qt.AlignLeft)  # 左对齐
        duration_layout.addWidget(QLabel("运行时长:"))
        self.duration_label = QLabel("-")
        self.duration_label.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.duration_label.setStyleSheet("color: #495057;")
        duration_layout.addWidget(self.duration_label)
        duration_layout.addStretch()
        details_layout.addLayout(duration_layout)

        info_grid.addLayout(details_layout)
        layout.addLayout(info_grid)

        # 日志区域
        log_section = QVBoxLayout()
        log_section.setSpacing(8)
        
        log_label = QLabel("服务日志:")
        log_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        log_label.setStyleSheet("color: #495057;")
        log_section.addWidget(log_label)

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(100)  # 固定高度，避免拉伸
        self.log_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9px;
                color: #495057;
            }
        """
        )
        log_section.addWidget(self.log_text)

        # 日志控制按钮
        log_control_layout = QHBoxLayout()

        clear_button = QPushButton("清空日志")
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 9px;
                font-family: Microsoft YaHei;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        clear_button.clicked.connect(self.log_text.clear)
        log_control_layout.addWidget(clear_button)

        log_control_layout.addStretch()
        log_section.addLayout(log_control_layout)

        layout.addLayout(log_section)
        layout.addStretch()  # 在底部添加弹性空间，避免内容被拉伸

        panel.setLayout(layout)
        return panel

    def create_interface_panel(self):
        """创建接口列表面板"""
        panel = QGroupBox("")  # 标题置为空
        panel.setStyleSheet(
            """
            QGroupBox {
                border: none;  /* 隐藏边框 */
                background-color: transparent;  /* 透明背景 */
                margin-top: 0px;
                padding-top: 0px;
            }
            QGroupBox::title {
                display: none;  /* 隐藏标题 */
            }
        """
        )

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 刷新按钮
        refresh_layout = QHBoxLayout()
        
        refresh_button = QPushButton("刷新接口列表")
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 12px;
                font-size: 10px;
                font-family: Microsoft YaHei;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        refresh_button.clicked.connect(self.refresh_interface_list)
        refresh_layout.addWidget(refresh_button)
        refresh_layout.addStretch()
        
        layout.addLayout(refresh_layout)

        # 创建表格
        self.interface_table = QTableWidget()
        self.interface_table.setColumnCount(3)
        self.interface_table.setHorizontalHeaderLabels(["请求方式", "请求路径", "中文描述"])
        
        # 设置表格样式
        self.interface_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                gridline-color: #dee2e6;
                font-size: 12px;
                font-family: Microsoft YaHei;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #f0f0f0;
                color: black;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
                outline: none;
            }
            QTableWidget::item:focus {
                outline: none;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #dee2e6;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        
        # 设置表格属性
        self.interface_table.setAlternatingRowColors(True)
        self.interface_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.interface_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.interface_table.setFocusPolicy(Qt.NoFocus)  # 移除焦点虚线
        self.interface_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.interface_table.verticalHeader().setVisible(False)
        
        # 连接双击事件
        self.interface_table.doubleClicked.connect(self.on_table_double_click)
        
        layout.addWidget(self.interface_table)
        
        panel.setLayout(layout)
        return panel

    def refresh_interface_list(self):
        """刷新接口列表"""
        try:
            # 加载接口数据
            interface_list = self.load_interface_list()
            
            # 清空表格
            self.interface_table.setRowCount(0)
            
            if not interface_list:
                # 如果没有接口数据，显示提示信息
                self.interface_table.setRowCount(1)
                
                item1 = QTableWidgetItem("-")
                item1.setTextAlignment(Qt.AlignCenter)
                self.interface_table.setItem(0, 0, item1)
                
                item2 = QTableWidgetItem("未找到接口数据")
                item2.setTextAlignment(Qt.AlignCenter)
                self.interface_table.setItem(0, 1, item2)
                
                item3 = QTableWidgetItem("请检查src/api/urls.py文件")
                item3.setTextAlignment(Qt.AlignCenter)
                self.interface_table.setItem(0, 2, item3)
                
                # 合并单元格显示提示信息
                self.interface_table.setSpan(0, 1, 1, 2)
                return
            
            # 设置行数
            self.interface_table.setRowCount(len(interface_list))
            
            # 填充数据
            for row, interface in enumerate(interface_list):
                method = interface.get("method", "-")
                path = interface.get("path", "-")
                summary = interface.get("summary", "-")
                
                # 设置方法单元格，添加样式
                method_item = QTableWidgetItem(method.upper())
                method_item.setTextAlignment(Qt.AlignCenter)
                if method.upper() == "GET":
                    method_item.setBackground(QColor("#007bff"))
                elif method.upper() == "POST":
                    method_item.setBackground(QColor("#28a745"))
                elif method.upper() == "PUT":
                    method_item.setBackground(QColor("#ffc107"))
                elif method.upper() == "DELETE":
                    method_item.setBackground(QColor("#dc3545"))
                elif method.upper() == "PATCH":
                    method_item.setBackground(QColor("#17a2b8"))
                
                # 统一设置黑色字体
                method_item.setForeground(QColor("black"))
                
                self.interface_table.setItem(row, 0, method_item)
                
                # 设置路径单元格，居中对齐，并显示完整地址
                full_url = f"http://localhost:{self.api_service.port}/api/v1{path}"
                path_item = QTableWidgetItem(full_url)
                path_item.setTextAlignment(Qt.AlignCenter)
                path_item.setData(Qt.UserRole, full_url)  # 存储完整URL用于复制
                self.interface_table.setItem(row, 1, path_item)
                
                # 设置描述单元格，居中对齐
                summary_item = QTableWidgetItem(summary)
                summary_item.setTextAlignment(Qt.AlignCenter)
                self.interface_table.setItem(row, 2, summary_item)
            
            # 调整列宽
            self.interface_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.interface_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.interface_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            
            logger.info(f"接口列表已刷新，共 {len(interface_list)} 个接口")
            
        except Exception as e:
            logger.error(f"刷新接口列表失败: {e}")
            # 显示错误信息
            self.interface_table.setRowCount(1)
            
            item1 = QTableWidgetItem("错误")
            item1.setTextAlignment(Qt.AlignCenter)
            self.interface_table.setItem(0, 0, item1)
            
            item2 = QTableWidgetItem("加载接口列表失败")
            item2.setTextAlignment(Qt.AlignCenter)
            self.interface_table.setItem(0, 1, item2)
            
            item3 = QTableWidgetItem(str(e))
            item3.setTextAlignment(Qt.AlignCenter)
            self.interface_table.setItem(0, 2, item3)
            self.interface_table.setSpan(0, 1, 1, 2)

    def on_table_double_click(self, index):
        """表格双击事件 - 复制请求地址"""
        try:
            # 只处理第二列（请求地址）的双击
            if index.column() == 1:
                item = self.interface_table.item(index.row(), 1)
                if item:
                    # 获取存储的完整URL
                    full_url = item.data(Qt.UserRole)
                    if full_url:
                        # 复制到剪贴板
                        clipboard = QApplication.clipboard()
                        clipboard.setText(full_url)
                        
                        # 显示提示信息
                        Toast.information(
                            self, 
                            "复制成功", 
                            f"已复制请求地址到剪贴板\n{full_url}"
                        )
                        logger.info(f"已复制请求地址: {full_url}")
        except Exception as e:
            logger.error(f"复制请求地址失败: {e}")
            Toast.warning(self, "错误", "复制请求地址失败")

    def setup_timer(self):
        """设置定时器更新状态"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(2000)  # 每2秒更新一次状态

        self.start_time = None

    def update_button_states(self):
        """更新按钮状态 - 启动和停止按钮根据状态只显示一个"""
        status = self.api_service.get_status()
        
        if status["is_running"]:
            # 服务运行中：显示停止按钮，隐藏启动按钮
            self.start_button.setVisible(False)
            self.stop_button.setVisible(True)
        else:
            # 服务停止中：显示启动按钮，隐藏停止按钮
            self.start_button.setVisible(True)
            self.stop_button.setVisible(False)

    def update_status(self):
        """更新服务状态"""
        status = self.api_service.get_status()

        if status["is_running"]:
            # 服务运行中
            self.status_indicator.setStyleSheet(
                """
                QLabel {
                    border-radius: 8px;
                    background-color: #28a745;
                    border: 2px solid #c3e6cb;
                }
            """
            )
            self.status_label.setText("服务运行中")
            self.status_label.setStyleSheet("color: #155724; font-weight: bold;")

            # 更新端口SpinBox的值
            self.port_spinbox.setValue(status["port"])
            
            # 显示启动模式
            if self.api_service.auto_start:
                self.mode_label.setText("自动启动")
            else:
                self.mode_label.setText("手动启动")

            # 设置启动时间
            if self.start_time is None:
                self.start_time = time.time()
                self.time_label.setText(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.start_time)))

            # 计算运行时长
            if self.start_time:
                duration = int(time.time() - self.start_time)
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                seconds = duration % 60
                self.duration_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

            # 更新按钮状态
            self.update_button_states()

        else:
            # 服务未运行
            self.status_indicator.setStyleSheet(
                """
                QLabel {
                    border-radius: 8px;
                    background-color: #dc3545;
                    border: 2px solid #f5c6cb;
                }
            """
            )
            self.status_label.setText("服务未启动")
            self.status_label.setStyleSheet("color: #721c24; font-weight: bold;")

            # 重置端口为默认值
            self.port_spinbox.setValue(8000)
            self.mode_label.setText("-")
            self.time_label.setText("-")
            self.duration_label.setText("-")

            # 更新按钮状态
            self.update_button_states()

            self.start_time = None

        self.status_updated.emit(status)

    def load_interface_list(self):
        """加载接口列表"""
        try:
            # 获取项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            urls_file = os.path.join(project_root, "src", "api", "urls.py")
            
            if not os.path.exists(urls_file):
                logger.warning(f"URL路由文件不存在: {urls_file}")
                return []
            
            # 动态导入urls模块
            sys.path.insert(0, project_root)
            try:
                from src.api.urls import url_routes
                
                # 解析路由信息
                interface_list = []
                for route in url_routes:
                    method = route.get("method", "")
                    path = route.get("path", "")
                    summary = route.get("summary", "")
                    
                    interface_list.append({
                        "method": method,
                        "path": path,
                        "summary": summary
                    })
                
                return interface_list
                
            except ImportError as e:
                logger.error(f"导入URL路由模块失败: {e}")
                return []
            finally:
                # 恢复sys.path
                if project_root in sys.path:
                    sys.path.remove(project_root)
                    
        except Exception as e:
            logger.error(f"加载接口列表失败: {e}")
            return []

    def start_service(self):
        """启动服务"""
        port = self.port_spinbox.value()

        if self.api_service.start(port):
            self.log_text.append(f"[INFO] 🚀 FastAPI服务启动成功，端口: {port}")
            Toast.information(
                self, "成功", f"FastAPI服务启动成功！\n端口: {port}"
            )
            # 更新按钮状态
            self.update_button_states()
        else:
            self.log_text.append("[ERROR] ❌ FastAPI服务启动失败")
            Toast.warning(self, "错误", "FastAPI服务启动失败")

    def stop_service(self):
        """停止服务"""
        if self.api_service.stop():
            self.log_text.append("[INFO] ⏹️ FastAPI服务已停止")
            Toast.information(self, "成功", "FastAPI服务已停止")
            # 更新按钮状态
            self.update_button_states()
        else:
            self.log_text.append("[ERROR] ❌ FastAPI服务停止失败")
            Toast.warning(self, "错误", "FastAPI服务停止失败")

    def restart_service(self):
        """重启服务"""
        port = self.port_spinbox.value()

        if self.api_service.restart(port):
            self.log_text.append(f"[INFO] 🔄 FastAPI服务重启成功，端口: {port}")
            Toast.information(
                self, "成功", f"FastAPI服务重启成功！\n端口: {port}"
            )
            # 更新按钮状态
            self.update_button_states()
        else:
            self.log_text.append("[ERROR] ❌ FastAPI服务重启失败")
            Toast.warning(self, "错误", "FastAPI服务重启失败")

    def closeEvent(self, event):
        """关闭事件，确保服务停止"""
        if self.api_service.is_running:
            self.api_service.stop()
        self.timer.stop()
        event.accept()
