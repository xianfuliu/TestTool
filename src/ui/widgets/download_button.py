from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QIcon, QFont
import os
from src.utils.resource_utils import resource_path


class DownloadButton(QPushButton):
    """自定义下载按钮"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.download_icon_path = "src/resources/icons/download_icon.png"

        # 设置按钮样式
        self.setFixedSize(32, 32)
        self.setIconSize(self.size())

        # 设置样式 - 透明背景
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)

        # 使用 resource_path 处理图标路径
        download_icon_path = resource_path(self.download_icon_path)

        if not os.path.exists(download_icon_path):
            # 尝试直接使用 resources 目录
            static_icon = os.path.normpath(self.download_icon_path)
            if os.path.exists(static_icon):
                download_icon_path = static_icon

        if os.path.exists(download_icon_path):
            self.setIcon(QIcon(download_icon_path))
            print(f"使用下载图标: {download_icon_path}")
        else:
            self.setText("↓")
            self.setFont(QFont("Arial", 14, QFont.Bold))
            print("警告: 无法找到下载图标，使用文本替代")

        self.setToolTip("下载图片")
