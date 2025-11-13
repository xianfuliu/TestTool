from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QToolButton, QMenu)
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelTabWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon


class ApiCard(QWidget):
    status_changed = pyqtSignal(int, bool)  # case_step_id, enabled
    order_changed = pyqtSignal(int, int)  # from_index, to_index

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

        header_layout.addWidget(self.api_name)
        header_layout.addStretch()
        header_layout.addWidget(self.status_btn)

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