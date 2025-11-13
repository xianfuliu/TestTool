"""
禁用鼠标滚轮切换的自定义组件
用于接口自动化项目中所有下拉框和tab组件
"""

from PyQt5.QtWidgets import QComboBox, QTabWidget
from PyQt5.QtCore import Qt


class NoWheelComboBox(QComboBox):
    """禁用鼠标滚轮切换的下拉框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def wheelEvent(self, event):
        """忽略滚轮事件"""
        event.ignore()


class NoWheelTabWidget(QTabWidget):
    """禁用鼠标滚轮切换的标签页控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def wheelEvent(self, event):
        """忽略滚轮事件"""
        event.ignore()