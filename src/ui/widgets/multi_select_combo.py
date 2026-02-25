"""
多选下拉框组件
"""

from PyQt5.QtWidgets import QComboBox, QListWidget, QCheckBox, QVBoxLayout, QWidget, QLineEdit
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QMouseEvent, QWheelEvent


class MultiSelectComboBox(QComboBox):
    """多选下拉框组件"""
    
    selectionChanged = pyqtSignal(list)  # 选择项改变信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setAlignment(Qt.AlignLeft)
        
        # 创建列表控件用于显示多选项
        self.list_widget = QListWidget()
        self.setModel(self.list_widget.model())
        self.setView(self.list_widget)
        
        # 存储选中项
        self.selected_items = []
        
        # 连接信号
        self.lineEdit().installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理点击事件"""
        if obj == self.lineEdit() and event.type() == QMouseEvent.MouseButtonPress:
            # 点击lineEdit时展开下拉列表
            self.showPopup()
            return True
        return super().eventFilter(obj, event)
    
    def wheelEvent(self, event):
        """禁用鼠标滚轮事件，防止滚动切换选项"""
        # 忽略鼠标滚轮事件，防止滚动切换选项
        event.ignore()
    
    def addItem(self, text, userData=None):
        """添加选项"""
        super().addItem(text, userData)
        
        # 创建复选框项
        item = self.list_widget.item(self.count() - 1)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        
        checkbox = QCheckBox(text)
        checkbox.setChecked(False)
        checkbox.stateChanged.connect(lambda state, idx=self.count()-1: self.on_item_toggled(idx, state))
        
        layout.addWidget(checkbox)
        self.list_widget.setItemWidget(item, widget)
        
    def on_item_toggled(self, index, state):
        """选项切换状态"""
        item_text = self.itemText(index)
        item_data = self.itemData(index)
        
        if state == Qt.Checked:
            if item_text not in self.selected_items:
                self.selected_items.append(item_text)
        else:
            if item_text in self.selected_items:
                self.selected_items.remove(item_text)
        
        # 更新显示文本
        self.update_display_text()
        
        # 发射信号
        self.selectionChanged.emit(self.get_selected_data())
        
    def update_display_text(self):
        """更新显示文本"""
        if self.selected_items:
            display_text = ", ".join(self.selected_items)
            self.lineEdit().setText(display_text)
        else:
            self.lineEdit().setText("请选择")
            
    def get_selected_data(self):
        """获取选中的数据"""
        selected_data = []
        for i in range(self.count()):
            item_text = self.itemText(i)
            if item_text in self.selected_items:
                item_data = self.itemData(i)
                selected_data.append(item_data if item_data else item_text)
        return selected_data
        
    def set_selected_items(self, items):
        """设置选中项"""
        self.selected_items = items.copy()
        
        # 更新复选框状态
        for i in range(self.count()):
            item_text = self.itemText(i)
            checkbox = self.list_widget.itemWidget(self.list_widget.item(i)).findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(item_text in items)
        
        self.update_display_text()
        
    def clear_selection(self):
        """清空选择"""
        self.selected_items.clear()
        for i in range(self.count()):
            checkbox = self.list_widget.itemWidget(self.list_widget.item(i)).findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(False)
        self.update_display_text()