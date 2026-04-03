from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QPushButton, QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from src.utils.update_manager import UpdateManager


class UpdateDialog(QDialog):
    """更新对话框"""
    
    def __init__(self, current_version, parent=None):
        super().__init__(parent)
        self.current_version = current_version
        self.update_manager = UpdateManager(current_version)
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """设置UI界面"""
        self.setWindowTitle("检查更新")
        self.setFixedSize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout()
        
        # 当前版本信息
        current_version_label = QLabel(f"当前版本: v{self.current_version}")
        current_version_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(current_version_label)
        
        # 状态标签
        self.status_label = QLabel("正在检查更新...")
        layout.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 更新说明区域
        self.release_notes_text = QTextEdit()
        self.release_notes_text.setVisible(False)
        self.release_notes_text.setReadOnly(True)
        layout.addWidget(self.release_notes_text)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.check_button = QPushButton("检查更新")
        self.download_button = QPushButton("下载更新")
        self.install_button = QPushButton("安装更新")
        self.close_button = QPushButton("关闭")
        
        self.download_button.setVisible(False)
        self.install_button.setVisible(False)
        
        button_layout.addWidget(self.check_button)
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.install_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # 连接信号
        self.check_button.clicked.connect(self.check_for_updates)
        self.download_button.clicked.connect(self.download_update)
        self.install_button.clicked.connect(self.install_update)
        self.close_button.clicked.connect(self.close)
        
        # 自动开始检查更新
        self.check_for_updates()
        
    def connect_signals(self):
        """连接更新管理器的信号"""
        self.update_manager.update_available.connect(self.on_update_available)
        self.update_manager.download_progress.connect(self.on_download_progress)
        self.update_manager.download_complete.connect(self.on_download_complete)
        self.update_manager.update_error.connect(self.on_update_error)
        
    def check_for_updates(self):
        """检查更新"""
        self.status_label.setText("正在检查更新...")
        self.check_button.setEnabled(False)
        self.update_manager.check_for_updates()
        
    def on_update_available(self, new_version, release_notes, download_url):
        """有新版本可用"""
        self.new_version = new_version
        self.download_url = download_url
        
        self.status_label.setText(f"发现新版本: v{new_version}")
        self.release_notes_text.setPlainText(release_notes)
        self.release_notes_text.setVisible(True)
        self.download_button.setVisible(True)
        self.check_button.setEnabled(True)
        
    def download_update(self):
        """下载更新"""
        self.status_label.setText("正在下载更新...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.download_button.setEnabled(False)
        self.update_manager.download_update(self.download_url)
        
    def on_download_progress(self, progress):
        """下载进度更新"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"正在下载更新... {progress}%")
        
    def on_download_complete(self, file_path):
        """下载完成"""
        self.downloaded_file = file_path
        self.status_label.setText("下载完成，准备安装")
        self.progress_bar.setVisible(False)
        self.install_button.setVisible(True)
        self.download_button.setVisible(False)
        
    def install_update(self):
        """安装更新"""
        reply = QMessageBox.question(self, "确认安装", 
                                   "安装更新将重启应用程序。是否继续？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.status_label.setText("正在安装更新...")
            self.update_manager.install_update(self.downloaded_file)
            
    def on_update_error(self, error_message):
        """更新错误"""
        self.status_label.setText("检查更新完成")
        self.check_button.setEnabled(True)
        
        # 如果是"当前已是最新版本"，显示信息而不是警告
        if error_message == "当前已是最新版本":
            QMessageBox.information(self, "检查更新", error_message)
        else:
            QMessageBox.warning(self, "更新错误", error_message)
        
    def closeEvent(self, event):
        """关闭事件"""
        event.accept()