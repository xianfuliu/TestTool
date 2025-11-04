from PyQt5.QtWidgets import QComboBox


class NoWheelComboBox(QComboBox):
    """禁用鼠标滚轮的 QComboBox"""

    def wheelEvent(self, event):
        # 忽略滚轮事件，防止意外改变选项
        event.ignore()