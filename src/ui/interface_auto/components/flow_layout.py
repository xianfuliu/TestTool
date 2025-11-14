"""
流式布局实现 - 用于测试步骤卡片的自动换行排列
"""

from PyQt5.QtWidgets import QLayout, QWidget, QLayoutItem
from PyQt5.QtCore import Qt, QSize, QRect, QPoint


class FlowLayout(QLayout):
    """流式布局 - 自动换行的布局管理器"""
    
    def __init__(self, parent=None, margin=5, hspacing=10, vspacing=10):
        super().__init__(parent)
        self._hspacing = hspacing
        self._vspacing = vspacing
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)
    
    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)
    
    def addItem(self, item):
        """添加布局项"""
        self._items.append(item)
    
    def horizontalSpacing(self):
        """获取水平间距"""
        return self._hspacing
    
    def verticalSpacing(self):
        """获取垂直间距"""
        return self._vspacing
    
    def count(self):
        """获取项目数量"""
        return len(self._items)
    
    def itemAt(self, index):
        """获取指定索引的项目"""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None
    
    def takeAt(self, index):
        """移除并返回指定索引的项目"""
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None
    
    def expandingDirections(self):
        """布局扩展方向"""
        return Qt.Orientations(Qt.Orientation(0))
    
    def hasHeightForWidth(self):
        """是否支持高度随宽度变化"""
        return True
    
    def heightForWidth(self, width):
        """根据宽度计算高度"""
        height = self._doLayout(QRect(0, 0, width, 0), True)
        return height
    
    def setGeometry(self, rect):
        """设置布局几何"""
        super().setGeometry(rect)
        self._doLayout(rect, False)
    
    def sizeHint(self):
        """大小提示"""
        return self.minimumSize()
    
    def minimumSize(self):
        """最小大小"""
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        
        margin, _, _, _ = self.getContentsMargins()
        size += QSize(2 * margin, 2 * margin)
        return size
    
    def _doLayout(self, rect, testonly):
        """执行布局计算"""
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(+left, +top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        
        for item in self._items:
            widget = item.widget()
            space_x = self.horizontalSpacing()
            if space_x == -1:
                space_x = widget.style().layoutSpacing(
                    QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            space_y = self.verticalSpacing()
            if space_y == -1:
                space_y = widget.style().layoutSpacing(
                    QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
            
            # 检查当前行是否能放下这个项目
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > effective_rect.right() and line_height > 0:
                # 换行
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = item.sizeHint().height()  # 重置为当前项目的高度
            else:
                # 当前行可以放下，更新行高
                line_height = max(line_height, item.sizeHint().height())
            
            if not testonly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            
            x = next_x
        
        return y + line_height - rect.y() + bottom