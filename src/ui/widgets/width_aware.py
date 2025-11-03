from PyQt5.QtWidgets import QWidget, QVBoxLayout


class WidthAwareWidget(QWidget):
    """自定义宽度感知部件，确保在渲染完成后调整宽度"""

    def __init__(self, content_widget, parent_tab):
        super().__init__()
        self.parent_tab = parent_tab
        layout = QVBoxLayout(self)
        layout.addWidget(content_widget)
        layout.setContentsMargins(0, 0, 0, 0)

    def paintEvent(self, event):
        """重写绘制事件 - 在第一次绘制时调整宽度"""
        super().paintEvent(event)
        # 只在第一次绘制时调整宽度
        if not hasattr(self, '_width_adjusted'):
            self.parent_tab.adjust_all_elements_width()
            self._width_adjusted = True
