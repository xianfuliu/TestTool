from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
import os
from src.utils.resource_utils import resource_path


class BackfillButton(QPushButton):
    """自定义回填按钮"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.backfill_icon_path = "src/resources/icons/backfill.png"

        # 设置按钮样式
        self.setFixedSize(24, 24)  # 与复制按钮保持一致
        self.setIconSize(QSize(16, 16))  # 减小图标大小

        # 设置样式 - 去掉边框
        self.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """
        )

        # 使用 resource_path 处理图标路径
        backfill_icon_path = resource_path(self.backfill_icon_path)

        if not os.path.exists(backfill_icon_path):
            # 尝试直接使用 resources 目录
            static_icon = os.path.normpath(self.backfill_icon_path)
            if os.path.exists(static_icon):
                backfill_icon_path = static_icon

        if os.path.exists(backfill_icon_path):
            self.setIcon(QIcon(backfill_icon_path))
        else:
            self.setText("↩️")

        self.setToolTip("回填到输入框")
