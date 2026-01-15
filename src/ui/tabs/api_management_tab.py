import threading
import subprocess
import time
import logging
from typing import Optional

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
)
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class FastAPIService:
    """FastAPI服务管理器"""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.thread: Optional[threading.Thread] = None
        self.is_running = False
        self.port = 8000

    def start(self, port: int = 8000) -> bool:
        """启动FastAPI服务"""
        try:
            if self.is_running:
                logger.warning("FastAPI服务已经在运行中")
                return False

            self.port = port

            # 使用线程启动FastAPI服务
            self.thread = threading.Thread(target=self._run_fastapi, daemon=True)
            self.thread.start()

            # 等待服务启动
            time.sleep(2)

            self.is_running = True
            logger.info(f"FastAPI服务启动成功，端口: {self.port}")
            return True

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

            # 这里可以实现优雅关闭逻辑
            # 目前通过设置标志位让线程自然结束
            self.is_running = False

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_service = FastAPIService()
        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        """初始化界面"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 创建分割器，支持调整大小
        splitter = QSplitter(Qt.Vertical)

        # 上半部分：状态和控制面板
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(15)

        # 左侧：状态面板
        status_panel = self.create_status_panel()
        top_layout.addWidget(status_panel, 1)

        # 右侧：控制面板
        control_panel = self.create_control_panel()
        top_layout.addWidget(control_panel, 1)

        # 下半部分：日志和链接面板
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(15)

        # 左侧：日志面板
        log_panel = self.create_log_panel()
        bottom_layout.addWidget(log_panel, 2)

        # 右侧：链接面板
        link_panel = self.create_link_panel()
        bottom_layout.addWidget(link_panel, 1)

        # 添加到分割器
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        splitter.setSizes([300, 200])

        main_layout.addWidget(splitter)

    def create_status_panel(self):
        """创建状态面板"""
        panel = QGroupBox("服务状态")
        panel.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        )

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 状态指示器
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)
        status_layout = QHBoxLayout(status_frame)

        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(20, 20)
        self.status_indicator.setStyleSheet(
            """
            QLabel {
                border-radius: 10px;
                background-color: #f44336;
            }
        """
        )

        self.status_label = QLabel("服务未启动")
        self.status_label.setFont(QFont("Arial", 12, QFont.Bold))

        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        layout.addWidget(status_frame)

        # 详细信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        # 端口信息
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("端口:"))
        self.port_label = QLabel("-")
        self.port_label.setFont(QFont("Arial", 10, QFont.Bold))
        port_layout.addWidget(self.port_label)
        port_layout.addStretch()
        info_layout.addLayout(port_layout)

        # 启动时间
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("启动时间:"))
        self.time_label = QLabel("-")
        time_layout.addWidget(self.time_label)
        time_layout.addStretch()
        info_layout.addLayout(time_layout)

        # 运行时长
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("运行时长:"))
        self.duration_label = QLabel("-")
        duration_layout.addWidget(self.duration_label)
        duration_layout.addStretch()
        info_layout.addLayout(duration_layout)

        layout.addLayout(info_layout)

        panel.setLayout(layout)
        return panel

    def create_control_panel(self):
        """创建控制面板"""
        panel = QGroupBox("服务控制")
        panel.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        )

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 端口设置
        port_group = QGroupBox("端口配置")
        port_layout = QVBoxLayout()

        port_input_layout = QHBoxLayout()
        port_input_layout.addWidget(QLabel("服务端口:"))
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(8000, 9000)
        self.port_spinbox.setValue(8000)
        self.port_spinbox.setFixedWidth(100)
        port_input_layout.addWidget(self.port_spinbox)
        port_input_layout.addStretch()

        port_layout.addLayout(port_input_layout)
        port_group.setLayout(port_layout)
        layout.addWidget(port_group)

        # 控制按钮
        button_layout = QVBoxLayout()
        button_layout.setSpacing(8)

        # 启动按钮
        self.start_button = QPushButton("🚀 启动服务")
        self.start_button.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        )
        self.start_button.clicked.connect(self.start_service)
        button_layout.addWidget(self.start_button)

        # 停止按钮
        self.stop_button = QPushButton("⏹️ 停止服务")
        self.stop_button.setStyleSheet(
            """
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        )
        self.stop_button.clicked.connect(self.stop_service)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        # 重启按钮
        self.restart_button = QPushButton("🔄 重启服务")
        self.restart_button.setStyleSheet(
            """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """
        )
        self.restart_button.clicked.connect(self.restart_service)
        button_layout.addWidget(self.restart_button)

        layout.addLayout(button_layout)
        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def create_log_panel(self):
        """创建日志面板"""
        panel = QGroupBox("服务日志")
        panel.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        )

        layout = QVBoxLayout()

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
            }
        """
        )
        layout.addWidget(self.log_text)

        # 日志控制按钮
        log_control_layout = QHBoxLayout()

        clear_button = QPushButton("清空日志")
        clear_button.clicked.connect(self.log_text.clear)
        log_control_layout.addWidget(clear_button)

        log_control_layout.addStretch()
        layout.addLayout(log_control_layout)

        panel.setLayout(layout)
        return panel

    def create_link_panel(self):
        """创建链接面板"""
        panel = QGroupBox("快速访问")
        panel.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        )

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # API文档链接
        api_doc_frame = self.create_link_frame("📚 API文档", "http://localhost:-")
        layout.addWidget(api_doc_frame)

        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def create_link_frame(self, title, url_template):
        """创建链接框架"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame_layout = QVBoxLayout(frame)

        # 标题
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        frame_layout.addWidget(title_label)

        # URL标签
        url_label = QLabel(url_template)
        url_label.setStyleSheet(
            """
            QLabel {
                color: #2196F3;
                font-size: 9px;
                font-family: 'Courier New', monospace;
                background-color: #f0f0f0;
                padding: 4px;
                border-radius: 3px;
            }
        """
        )
        url_label.setWordWrap(True)
        frame_layout.addWidget(url_label)

        # 存储URL模板用于后续更新
        if title == "📚 API文档":
            self.api_doc_label = url_label
            self.api_doc_template = url_template
        elif title == "❤️ 健康检查":
            self.health_label = url_label
            self.health_template = url_template
        elif title == "📊 系统状态":
            self.status_label_link = url_label
            self.status_template = url_template
        elif title == "👥 用户管理":
            self.user_label = url_label
            self.user_template = url_template

        return frame

    def setup_timer(self):
        """设置定时器更新状态"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(2000)  # 每2秒更新一次状态

        self.start_time = None

    def update_status(self):
        """更新服务状态"""
        status = self.api_service.get_status()

        if status["is_running"]:
            # 服务运行中
            self.status_indicator.setStyleSheet(
                """
                QLabel {
                    border-radius: 10px;
                    background-color: #4CAF50;
                }
            """
            )
            self.status_label.setText("服务运行中")
            self.status_label.setStyleSheet("color: #4CAF50;")

            self.port_label.setText(str(status["port"]))

            # 更新启动时间
            if not self.start_time:
                self.start_time = status.get("start_time")
                self.time_label.setText(self.start_time or "-")

            # 更新运行时长
            if self.start_time:
                # 这里可以计算运行时长
                self.duration_label.setText("运行中...")

            # 更新按钮状态
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)

            # 更新链接
            port = status["port"]
            self.api_doc_label.setText(self.api_doc_template.replace(":-", f":{port}"))

        else:
            # 服务未运行
            self.status_indicator.setStyleSheet(
                """
                QLabel {
                    border-radius: 10px;
                    background-color: #f44336;
                }
            """
            )
            self.status_label.setText("服务未启动")
            self.status_label.setStyleSheet("color: #f44336;")

            self.port_label.setText("-")
            self.time_label.setText("-")
            self.duration_label.setText("-")

            # 更新按钮状态
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

            self.start_time = None

        self.status_updated.emit(status)

    def start_service(self):
        """启动服务"""
        port = self.port_spinbox.value()

        if self.api_service.start(port):
            self.log_text.append(f"[INFO] 🚀 FastAPI服务启动成功，端口: {port}")
            QMessageBox.information(
                self, "成功", f"FastAPI服务启动成功！\n端口: {port}"
            )
        else:
            self.log_text.append("[ERROR] ❌ FastAPI服务启动失败")
            QMessageBox.warning(self, "错误", "FastAPI服务启动失败")

    def stop_service(self):
        """停止服务"""
        if self.api_service.stop():
            self.log_text.append("[INFO] ⏹️ FastAPI服务已停止")
            QMessageBox.information(self, "成功", "FastAPI服务已停止")
        else:
            self.log_text.append("[ERROR] ❌ FastAPI服务停止失败")
            QMessageBox.warning(self, "错误", "FastAPI服务停止失败")

    def restart_service(self):
        """重启服务"""
        port = self.port_spinbox.value()

        if self.api_service.restart(port):
            self.log_text.append(f"[INFO] 🔄 FastAPI服务重启成功，端口: {port}")
            QMessageBox.information(
                self, "成功", f"FastAPI服务重启成功！\n端口: {port}"
            )
        else:
            self.log_text.append("[ERROR] ❌ FastAPI服务重启失败")
            QMessageBox.warning(self, "错误", "FastAPI服务重启失败")

    def closeEvent(self, event):
        """关闭事件，确保服务停止"""
        if self.api_service.is_running:
            self.api_service.stop()
        self.timer.stop()
        event.accept()
