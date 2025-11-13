from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QToolButton, QMenu)
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelTabWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon


class ApiCard(QWidget):
    status_changed = pyqtSignal(int, bool)  # case_step_id, enabled
    order_changed = pyqtSignal(int, int)  # from_index, to_index
    step_updated = pyqtSignal(dict)  # 步骤更新信号
    step_deleted = pyqtSignal(dict)  # 步骤删除信号
    step_moved = pyqtSignal(int, int)  # 步骤移动信号

    def __init__(self, step_data, parent=None):
        super().__init__(parent)
        self.step_data = step_data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 卡片头部
        header_layout = QHBoxLayout()
        self.api_name = QLabel(self.step_data['api_name'])
        self.status_btn = QPushButton("启用" if self.step_data['enabled'] else "停用")
        self.status_btn.setCheckable(True)
        self.status_btn.setChecked(self.step_data['enabled'])
        
        # 删除按钮
        self.delete_btn = QPushButton("删除")
        self.delete_btn.setStyleSheet("background-color: #f44336; color: white;")
        
        # 移动按钮
        self.move_up_btn = QPushButton("↑")
        self.move_down_btn = QPushButton("↓")

        header_layout.addWidget(self.api_name)
        header_layout.addStretch()
        header_layout.addWidget(self.status_btn)
        header_layout.addWidget(self.move_up_btn)
        header_layout.addWidget(self.move_down_btn)
        header_layout.addWidget(self.delete_btn)

        # Tab区域
        self.tab_widget = NoWheelTabWidget()

        # 前置处理Tab
        self.pre_process_tab = QWidget()
        self.setup_pre_process_tab()

        # 后置处理Tab
        self.post_process_tab = QWidget()
        self.setup_post_process_tab()

        # 断言Tab
        self.assertion_tab = QWidget()
        self.setup_assertion_tab()

        self.tab_widget.addTab(self.pre_process_tab, "前置处理")
        self.tab_widget.addTab(self.post_process_tab, "后置处理")
        self.tab_widget.addTab(self.assertion_tab, "断言")

        # 添加工具按钮
        self.add_tool_btn()

        layout.addLayout(header_layout)
        layout.addWidget(self.tab_widget)

        # 连接信号
        self.status_btn.toggled.connect(self.on_status_changed)
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        self.move_up_btn.clicked.connect(self.on_move_up_clicked)
        self.move_down_btn.clicked.connect(self.on_move_down_clicked)

    def on_status_changed(self, enabled):
        """状态改变事件"""
        self.step_data['enabled'] = enabled
        self.status_btn.setText("启用" if enabled else "停用")
        self.step_updated.emit(self.step_data)

    def setup_pre_process_tab(self):
        """设置前置处理Tab"""
        layout = QVBoxLayout(self.pre_process_tab)
        layout.addWidget(QLabel("前置处理功能将在后续版本中实现"))

    def setup_post_process_tab(self):
        """设置后置处理Tab"""
        layout = QVBoxLayout(self.post_process_tab)
        layout.addWidget(QLabel("后置处理功能将在后续版本中实现"))

    def setup_assertion_tab(self):
        """设置断言Tab"""
        layout = QVBoxLayout(self.assertion_tab)
        layout.addWidget(QLabel("断言功能将在后续版本中实现"))

    def on_delete_clicked(self):
        """删除按钮点击事件"""
        self.step_deleted.emit(self.step_data)

    def on_move_up_clicked(self):
        """上移按钮点击事件"""
        # 获取当前步骤在父容器中的索引
        parent_layout = self.parent().layout()
        if parent_layout:
            for i in range(parent_layout.count()):
                if parent_layout.itemAt(i).widget() == self:
                    if i > 0:
                        self.step_moved.emit(i, i - 1)
                    break

    def on_move_down_clicked(self):
        """下移按钮点击事件"""
        # 获取当前步骤在父容器中的索引
        parent_layout = self.parent().layout()
        if parent_layout:
            for i in range(parent_layout.count()):
                if parent_layout.itemAt(i).widget() == self:
                    if i < parent_layout.count() - 1:
                        self.step_moved.emit(i, i + 1)
                    break

    def add_tool_btn(self):
        # 在每个Tab中添加+号按钮
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            tab_layout = tab.layout()

            tool_btn = QToolButton()
            tool_btn.setText("+")
            tool_btn.setPopupMode(QToolButton.InstantPopup)

            # 创建工具菜单
            menu = QMenu(self)
            tools = ["SQL查询", "随机数生成", "Python脚本", "等待定时器", "HTTP请求"]
            for tool in tools:
                menu.addAction(tool)

            tool_btn.setMenu(menu)
            tab_layout.addWidget(tool_btn)