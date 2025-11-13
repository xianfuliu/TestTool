"""
可复用的展开/收缩箭头组件
支持展开和收起两种状态，点击切换状态
"""

from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
import os


class CollapseButton(QPushButton):
    """展开/收缩按钮组件"""
    
    # 状态变化信号
    state_changed = pyqtSignal(bool)  # True: 展开状态, False: 收起状态
    
    def __init__(self, parent=None, is_expanded=True):
        super().__init__(parent)
        self._is_expanded = is_expanded
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setFixedSize(24, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border: 1px solid #999;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        
        self.update_icon()
        self.clicked.connect(self.toggle_state)
        
    def update_icon(self):
        """更新图标显示"""
        if self._is_expanded:
            # 展开状态：显示收缩图标（指向左）
            icon_path = os.path.join("src", "resources", "icons", "close_left.png")
            if os.path.exists(icon_path):
                self.setIcon(QIcon(icon_path))
                self.setText("")
            else:
                self.setText("▶")
            self.setToolTip("收起左侧菜单栏")
        else:
            # 收起状态：显示展开图标（指向右）
            icon_path = os.path.join("src", "resources", "icons", "open_right.png")
            if os.path.exists(icon_path):
                self.setIcon(QIcon(icon_path))
                self.setText("")
            else:
                self.setText("◀")
            self.setToolTip("展开左侧菜单栏")
        
        self.setIconSize(self.size())
    
    def toggle_state(self):
        """切换展开/收起状态"""
        self._is_expanded = not self._is_expanded
        self.update_icon()
        self.state_changed.emit(self._is_expanded)
        
    def set_expanded(self, expanded):
        """设置展开状态"""
        if self._is_expanded != expanded:
            self._is_expanded = expanded
            self.update_icon()
            self.state_changed.emit(self._is_expanded)
            
    def is_expanded(self):
        """获取当前状态"""
        return self._is_expanded