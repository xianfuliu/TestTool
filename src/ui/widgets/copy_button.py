from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QApplication
import os
from src.utils.resource_utils import resource_path


class CopyButton(QPushButton):
    """自定义复制按钮"""

    def __init__(self, text_to_copy, parent=None):
        super().__init__(parent)
        self.text_to_copy = text_to_copy
        self.copy_icon_path = "src/resources/icons/copy_icon.png"

        # 设置按钮样式
        self.setFixedSize(28, 28)
        self.setIconSize(self.size())

        # 设置样式
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #cccccc;
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
        copy_icon_path = resource_path(self.copy_icon_path)

        if not os.path.exists(copy_icon_path):
            # 尝试直接使用 resources 目录
            static_icon = os.path.normpath(self.copy_icon_path)
            if os.path.exists(static_icon):
                copy_icon_path = static_icon

        if os.path.exists(copy_icon_path):
            self.setIcon(QIcon(copy_icon_path))
            print(f"使用复制图标: {copy_icon_path}")
        else:
            self.setText("📋")
            self.setFont(QFont("Arial", 12))
            print("警告: 无法找到复制图标，使用文本替代")

        self.setToolTip("复制")
        self.clicked.connect(self.copy_text)

    def copy_text(self):
        """复制文本到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_to_copy)
