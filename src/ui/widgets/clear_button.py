from PyQt5.QtWidgets import QLineEdit, QPushButton
from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QIcon
import os
from src.utils.resource_utils import resource_path


class ClearLineEdit(QLineEdit):
    """带清空按钮的输入框组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.clear_button = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 创建清空按钮
        self.clear_button = QPushButton(self)
        self.clear_button.setFixedSize(24, 24)  # 调整为与RefreshButton相同的大小
        
        # 设置按钮样式 - 默认隐藏，根据条件显示
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                color: #999999;
                font-size: 12px;
                font-weight: bold;
                margin: 0px;
                padding: 0px;
                opacity: 0;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                color: #666666;
            }
            QPushButton:pressed {
                background-color: #cccccc;
                color: #333333;
            }
        """)
        
        # 设置按钮图标
        try:
            # 使用 resource_path 处理图标路径（参考 RefreshButton 的实现）
            clear_icon_path = "src/resources/icons/clear.png"
            
            # 使用 resource_path 获取绝对路径
            icon_path = resource_path(clear_icon_path)
            
            # 如果找不到文件，尝试直接使用路径
            if not os.path.exists(icon_path):
                static_icon = os.path.normpath(clear_icon_path)
                if os.path.exists(static_icon):
                    icon_path = static_icon
            
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                if not icon.isNull():
                    self.clear_button.setIcon(icon)
                    self.clear_button.setIconSize(QSize(16, 16))  # 图标大小
                    self.clear_button.setText("")  # 清空文本，只显示图标
                else:
                    self.clear_button.setText("×")
            else:
                # 如果图标文件不存在，使用文本作为备选
                self.clear_button.setText("×")
        except Exception as e:
            # 如果出现异常，使用文本作为备选
            self.clear_button.setText("×")
            print(f"清空按钮图标加载异常: {e}")
        
        # 设置提示文本
        self.clear_button.setToolTip("清空输入框")
        
        # 连接点击事件
        self.clear_button.clicked.connect(self.clear)
        
        # 按钮默认隐藏，通过CSS的opacity属性控制显示/隐藏
        self.clear_button.setVisible(False)  # 确保按钮默认隐藏
        
        # 监听文本变化，控制按钮的可用性
        self.textChanged.connect(self.on_text_changed)
        
        # 初始化时设置正确的按钮显示状态
        self.update_button_visibility()
    
    def on_text_changed(self, text):
        """文本变化时更新清空按钮的显示状态"""
        if self.clear_button:
            # 根据文本内容和鼠标悬浮状态更新按钮透明度
            self.update_button_visibility()

    def enterEvent(self, event):
        """鼠标进入输入框事件"""
        super().enterEvent(event)
        self.update_button_visibility()

    def leaveEvent(self, event):
        """鼠标离开输入框事件"""
        super().leaveEvent(event)
        self.update_button_visibility()

    def update_button_visibility(self):
        """根据条件更新按钮的显示状态"""
        if self.clear_button:
            # 条件：鼠标悬浮在输入框上且输入框有实际内容（排除placeholder）
            is_hovered = self.underMouse()
            current_text = self.text()
            placeholder_text = self.placeholderText()
            
            # 只有当用户实际输入了内容（不是placeholder）时才显示按钮
            has_real_text = bool(current_text) and current_text != placeholder_text
            
            if is_hovered and has_real_text:
                # 显示按钮
                self.clear_button.setVisible(True)
                self.clear_button.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        border-radius: 8px;
                        color: #999999;
                        font-size: 12px;
                        font-weight: bold;
                        margin: 0px;
                        padding: 0px;
                        opacity: 1;
                    }
                """)
            else:
                # 隐藏按钮
                self.clear_button.setVisible(False)
                self.clear_button.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        border-radius: 8px;
                        color: #999999;
                        font-size: 12px;
                        font-weight: bold;
                        margin: 0px;
                        padding: 0px;
                        opacity: 0;
                    }
                """)
    
    def resizeEvent(self, event):
        """调整大小事件，重新定位清空按钮"""
        super().resizeEvent(event)
        
        # 将清空按钮放在输入框右侧内部，垂直居中
        button_size = self.clear_button.size()
        frame_width = self.style().pixelMetric(self.style().PM_DefaultFrameWidth)
        
        # 计算按钮位置 - 右上角，垂直居中
        button_x = self.width() - button_size.width() - frame_width - 2
        button_y = (self.height() - button_size.height()) // 2
        
        self.clear_button.move(button_x, button_y)
    
    def clear(self):
        """清空输入框"""
        super().clear()
        self.setFocus()  # 保持焦点在输入框