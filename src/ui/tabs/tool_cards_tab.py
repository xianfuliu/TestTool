from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QScrollArea,
    QTabWidget,
    QPushButton,
    QLabel,
    QFrame,
    QMenu,
    QAction,
    QMessageBox,
    QComboBox,
)
from src.ui.widgets.toast_tips import Toast
from PyQt5.QtCore import Qt
import json
import os

from src.ui.dialogs.tool_cards_config_dialog import ToolCardsConfigDialog


class ToolCardWidget(QFrame):
    """单个卡片控件"""

    def __init__(self, card_data, parent=None):
        super().__init__(parent)
        self.card_data = card_data
        self.parent_tab = parent
        self.init_ui()

    def init_ui(self):
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)
        self.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border: 1px solid #e0e6ed;
                border-radius: 8px;
                padding: 0px;
            }
            QFrame:hover {
                border: 2px solid #4299e1;
            }
        """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 卡片头部
        header = QWidget()
        header.setStyleSheet(
            """
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                          stop:0 #4299e1, stop:1 #3182ce);
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 12px;
            }
        """
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(self.card_data.get("title", "未命名卡片"))
        title_label.setStyleSheet(
            """
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
        """
        )

        # 菜单按钮（三个点）
        self.menu_btn = QPushButton("⋯")
        self.menu_btn.setStyleSheet(
            """
            QPushButton {
                background: rgba(255, 255, 255, 0.2);
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 16px;
                font-weight: bold;
                width: 24px;
                height: 24px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.3);
            }
        """
        )
        self.menu_btn.setCursor(Qt.PointingHandCursor)
        self.menu_btn.clicked.connect(self.show_card_menu)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.menu_btn)

        # 卡片主体
        body = QWidget()
        body.setStyleSheet(
            """
            QWidget {
                background-color: white;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
                padding: 12px;
            }
        """
        )
        body_layout = QVBoxLayout(body)

        # 显示卡片类型和描述
        type_label = QLabel(f"类型: {self.get_type_display()}")
        type_label.setStyleSheet("QLabel { color: #666; font-size: 12px; }")

        desc_label = QLabel(self.card_data.get("description", "暂无描述"))
        desc_label.setStyleSheet(
            "QLabel { color: #333; font-size: 12px; margin-top: 8px; }"
        )
        desc_label.setWordWrap(True)

        # 锁定状态显示
        if self.card_data.get("locked", False):
            lock_label = QLabel("🔒 已锁定")
            lock_label.setStyleSheet(
                "QLabel { color: #e53e3e; font-size: 11px; margin-top: 8px; }"
            )
            body_layout.addWidget(lock_label)

        body_layout.addWidget(type_label)
        body_layout.addWidget(desc_label)
        body_layout.addStretch()

        # 执行按钮
        execute_btn = QPushButton("执行")
        execute_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #48bb78;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                margin-top: 8px;
            }
            QPushButton:hover {
                background-color: #38a169;
            }
        """
        )
        execute_btn.clicked.connect(self.execute_card)

        body_layout.addWidget(execute_btn)

        layout.addWidget(header)
        layout.addWidget(body)

    def get_type_display(self):
        card_type = self.card_data.get("type", "sql")
        type_map = {"sql": "SQL工具", "http": "HTTP接口", "python": "Python类"}
        return type_map.get(card_type, card_type)

    def show_card_menu(self):
        menu = QMenu(self)

        view_action = QAction("👁 查看", self)
        view_action.triggered.connect(lambda: self.parent_tab.view_card(self.card_data))
        menu.addAction(view_action)

        # 如果卡片未锁定，显示编辑选项
        if not self.card_data.get("locked", False):
            edit_action = QAction("✏️ 编辑", self)
            edit_action.triggered.connect(
                lambda: self.parent_tab.edit_card(self.card_data)
            )
            menu.addAction(edit_action)

        copy_action = QAction("📋 复制", self)
        copy_action.triggered.connect(lambda: self.parent_tab.copy_card(self.card_data))
        menu.addAction(copy_action)

        # 如果卡片未锁定，显示删除选项
        if not self.card_data.get("locked", False):
            delete_action = QAction("🗑️ 删除", self)
            delete_action.triggered.connect(
                lambda: self.parent_tab.delete_card(self.card_data)
            )
            menu.addAction(delete_action)

        menu.exec_(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft()))

    def execute_card(self):
        self.parent_tab.execute_card(self.card_data)


class ToolCardsTab(QWidget):
    """卡片工具Tab页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_business_group_id = None
        self.current_project_id = None
        self.business_groups = []
        self.projects = []
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 顶部筛选栏区域
        self.create_filter_bar(main_layout)

        # 项目Tab区域
        self.create_projects_tab(main_layout)

        # 卡片展示区域
        self.create_cards_area(main_layout)

    def create_filter_bar(self, parent_layout):
        # 筛选栏容器
        filter_container = QWidget()
        filter_container.setStyleSheet(
            """
            QWidget {
                background-color: #f8fafc;
                border-bottom: 1px solid #e2e8f0;
                padding: 8px 12px;
            }
        """
        )
        filter_container.setFixedHeight(50)

        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(10)

        # 业务线筛选
        business_label = QLabel("业务线:")
        business_label.setStyleSheet("QLabel { font-weight: bold; color: #2d3748; }")

        self.business_combo = QComboBox()
        self.business_combo.setStyleSheet(
            """
            QComboBox {
                background-color: white;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 150px;
            }
            QComboBox:hover {
                border-color: #4299e1;
            }
        """
        )
        self.business_combo.currentIndexChanged.connect(self.on_business_group_changed)

        # 配置按钮
        config_btn = QPushButton("配置")
        config_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4299e1;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #3182ce;
            }
        """
        )
        config_btn.clicked.connect(self.open_config_dialog)

        filter_layout.addWidget(business_label)
        filter_layout.addWidget(self.business_combo)
        filter_layout.addStretch()
        filter_layout.addWidget(config_btn)

        parent_layout.addWidget(filter_container)

    def create_projects_tab(self, parent_layout):
        # 项目Tab容器
        projects_container = QWidget()
        projects_container.setStyleSheet(
            """
            QWidget {
                background-color: #f7fafc;
                border-bottom: 1px solid #e2e8f0;
                padding: 0px;
            }
        """
        )

        projects_layout = QVBoxLayout(projects_container)
        projects_layout.setContentsMargins(0, 0, 0, 0)
        projects_layout.setSpacing(0)

        # 项目Tab区域
        self.projects_tab_widget = QTabWidget()
        self.projects_tab_widget.setStyleSheet(
            """
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar::tab {
                background: transparent;
                border: none;
                padding: 8px 16px;
                margin-right: 2px;
                color: #4a5568;
                border-radius: 0px;
            }
            QTabBar::tab:selected {
                background: #4299e1;
                color: white;
                border-bottom: 2px solid #3182ce;
            }
            QTabBar::tab:hover:!selected {
                background: #e2e8f0;
            }
        """
        )
        self.projects_tab_widget.tabBar().setExpanding(False)
        self.projects_tab_widget.currentChanged.connect(self.on_project_changed)

        projects_layout.addWidget(self.projects_tab_widget)
        parent_layout.addWidget(projects_container)

    def create_cards_area(self, parent_layout):
        # 卡片区域滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: #f8fafc; }")

        # 卡片容器 - 使用网格布局实现自动换行
        self.cards_container = QWidget()
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(15)
        self.cards_layout.setContentsMargins(15, 15, 15, 15)
        self.cards_layout.setAlignment(Qt.AlignTop)

        scroll_area.setWidget(self.cards_container)
        parent_layout.addWidget(scroll_area, 1)

    def load_data(self):
        """从数据库加载数据"""
        try:
            # 加载业务线数据
            self.business_groups = self.load_business_groups()

            # 加载业务线下拉框
            self.business_combo.clear()
            self.business_combo.addItem("全部业务线", None)
            for business in self.business_groups:
                self.business_combo.addItem(business["name"], business["id"])

            # 默认选择第一个业务线
            if self.business_groups:
                self.business_combo.setCurrentIndex(1)  # 跳过"全部业务线"
                self.on_business_group_changed(1)
        except Exception as e:
            print(f"加载数据失败: {e}")

    def load_business_groups(self):
        """从数据库加载业务线数据"""
        # 这里需要实现数据库查询逻辑
        # 暂时返回模拟数据
        return [
            {"id": 1, "name": "消费金融"},
            {"id": 2, "name": "小微测试"},
            {"id": 3, "name": "其他业务"},
        ]

    def load_projects(self, business_group_id=None):
        """根据业务线加载项目数据"""
        # 这里需要实现数据库查询逻辑
        # 暂时返回模拟数据
        if business_group_id == 1:
            return [
                {"id": 1, "name": "消费金融项目A", "business_group_id": 1},
                {"id": 2, "name": "消费金融项目B", "business_group_id": 1},
            ]
        elif business_group_id == 2:
            return [
                {"id": 3, "name": "小微测试项目A", "business_group_id": 2},
                {"id": 4, "name": "小微测试项目B", "business_group_id": 2},
            ]
        elif business_group_id == 3:
            return [
                {"id": 5, "name": "其他项目A", "business_group_id": 3},
                {"id": 6, "name": "其他项目B", "business_group_id": 3},
            ]
        else:
            # 返回所有项目
            return [
                {"id": 1, "name": "消费金融项目A", "business_group_id": 1},
                {"id": 2, "name": "消费金融项目B", "business_group_id": 1},
                {"id": 3, "name": "小微测试项目A", "business_group_id": 2},
                {"id": 4, "name": "小微测试项目B", "business_group_id": 2},
                {"id": 5, "name": "其他项目A", "business_group_id": 3},
                {"id": 6, "name": "其他项目B", "business_group_id": 3},
            ]

    def load_tool_cards(self, project_id):
        """根据项目ID加载卡片工具数据"""
        # 这里需要实现数据库查询逻辑
        # 暂时返回模拟数据
        if project_id == 1:
            return [
                {
                    "id": 1,
                    "title": "用户查询",
                    "description": "查询用户信息",
                    "card_type": "sql",
                },
                {
                    "id": 2,
                    "title": "订单统计",
                    "description": "统计订单数据",
                    "card_type": "sql",
                },
            ]
        elif project_id == 2:
            return [
                {
                    "id": 3,
                    "title": "API测试",
                    "description": "测试HTTP接口",
                    "card_type": "http",
                },
                {
                    "id": 4,
                    "title": "数据处理",
                    "description": "Python脚本处理",
                    "card_type": "python",
                },
            ]
        else:
            return []

    def on_business_group_changed(self, index):
        """业务线变更事件"""
        if index < 0:
            return

        # 获取选中的业务线ID
        business_group_id = self.business_combo.itemData(index)
        self.current_business_group_id = business_group_id

        # 清空项目Tab
        self.projects_tab_widget.clear()

        # 加载项目数据
        self.projects = self.load_projects(business_group_id)

        # 添加项目Tab
        for project in self.projects:
            self.projects_tab_widget.addTab(QWidget(), project["name"])

        # 触发项目变更事件
        if self.projects:
            self.on_project_changed(0)

    def on_project_changed(self, index):
        """项目变更事件"""
        if index < 0:
            return

        if index >= len(self.projects):
            return

        current_project = self.projects[index]
        self.current_project_id = current_project["id"]

        # 清空卡片区域
        for i in reversed(range(self.cards_layout.count())):
            item = self.cards_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        # 加载卡片数据
        cards = self.load_tool_cards(self.current_project_id)

        # 添加卡片 - 使用网格布局，每行最多3个卡片
        max_columns = 3  # 每行最多显示3个卡片

        for i, card_data in enumerate(cards):
            card_widget = ToolCardWidget(card_data, self)
            # 设置卡片固定大小
            card_widget.setFixedSize(280, 180)  # 固定卡片大小

            # 计算网格位置
            row = i // max_columns
            column = i % max_columns

            self.cards_layout.addWidget(card_widget, row, column)

    def open_config_dialog(self):
        """打开配置对话框"""
        # 确保当前有选中的项目
        if not self.current_project_id:
            Toast.warning(self, "配置失败", "请先选择项目")
            return

        # 创建空的配置数据，因为我们不再使用JSON配置
        empty_config = {"business_lines": []}
        dialog = ToolCardsConfigDialog(empty_config, self)
        if dialog.exec_() == ToolCardsConfigDialog.Accepted:
            # 配置保存逻辑需要更新为数据库操作
            # 暂时只刷新UI
            self.refresh_ui()

    def view_card(self, card_data):
        """查看卡片"""
        # 创建空的配置数据，因为我们不再使用JSON配置
        empty_config = {"business_lines": []}
        dialog = ToolCardsConfigDialog(empty_config, self, card_data, view_mode=True)
        dialog.exec_()

    def edit_card(self, card_data):
        """编辑卡片"""
        # 创建空的配置数据，因为我们不再使用JSON配置
        empty_config = {"business_lines": []}
        dialog = ToolCardsConfigDialog(empty_config, self, card_data)
        if dialog.exec_() == ToolCardsConfigDialog.Accepted:
            # 配置保存逻辑需要更新为数据库操作
            # 暂时只刷新UI
            self.refresh_ui()

    def copy_card(self, card_data):
        """复制卡片"""
        # 找到卡片所在位置
        business_lines = self.config_data.get("business_lines", [])
        for business in business_lines:
            for sub_business in business.get("sub_business", []):
                cards = sub_business.get("cards", [])
                for i, card in enumerate(cards):
                    if card.get("id") == card_data.get("id"):
                        # 创建副本
                        new_card = card_data.copy()
                        new_card["id"] = self.generate_card_id()

                        # 生成副本名称
                        base_name = card_data.get("title", "卡片")
                        copy_count = 1
                        new_title = f"{base_name}_cp{copy_count}"

                        # 检查名称是否已存在
                        while any(c.get("title") == new_title for c in cards):
                            copy_count += 1
                            new_title = f"{base_name}_cp{copy_count}"

                        new_card["title"] = new_title
                        new_card["locked"] = False  # 副本默认不锁定

                        # 添加到同一子业务模块
                        cards.append(new_card)

                        self.save_config()
                        self.refresh_ui()
                        return

        Toast.warn(self, "未找到要复制的卡片")

    def delete_card(self, card_data):
        """删除卡片"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除卡片 '{card_data.get('title')}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            business_lines = self.config_data.get("business_lines", [])
            for business in business_lines:
                for sub_business in business.get("sub_business", []):
                    cards = sub_business.get("cards", [])
                    for i, card in enumerate(cards):
                        if card.get("id") == card_data.get("id"):
                            cards.pop(i)
                            self.save_config()
                            self.refresh_ui()
                            return

            Toast.warn(self, "未找到要删除的卡片")

    def execute_card(self, card_data):
        """执行卡片"""
        # 这里实现卡片执行逻辑
        # 根据卡片类型调用相应的执行器
        card_type = card_data.get("type", "sql")

        if card_type == "sql":
            self.execute_sql_card(card_data)
        elif card_type == "http":
            self.execute_http_card(card_data)
        elif card_type == "python":
            self.execute_python_card(card_data)

    def execute_sql_card(self, card_data):
        """执行SQL卡片"""
        # TODO: 实现SQL执行逻辑
        print(f"执行SQL卡片: {card_data.get('title')}")

    def execute_http_card(self, card_data):
        """执行HTTP卡片"""
        # TODO: 实现HTTP执行逻辑
        print(f"执行HTTP卡片: {card_data.get('title')}")

    def execute_python_card(self, card_data):
        """执行Python卡片"""
        # TODO: 实现Python执行逻辑
        print(f"执行Python卡片: {card_data.get('title')}")

    def generate_card_id(self):
        """生成卡片ID"""
        import time

        return f"card_{int(time.time() * 1000)}"
