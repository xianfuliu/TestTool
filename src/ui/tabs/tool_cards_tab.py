from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
                             QTabWidget, QPushButton, QLabel, QFrame, QMenu,
                             QAction, QMessageBox, QApplication, QSizePolicy)
from src.ui.widgets.toast_tips import Toast
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor
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
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e6ed;
                border-radius: 8px;
                padding: 0px;
            }
            QFrame:hover {
                border: 2px solid #4299e1;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 卡片头部
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                          stop:0 #4299e1, stop:1 #3182ce);
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 12px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(self.card_data.get('title', '未命名卡片'))
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
        """)

        # 菜单按钮（三个点）
        self.menu_btn = QPushButton("⋯")
        self.menu_btn.setStyleSheet("""
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
        """)
        self.menu_btn.setCursor(Qt.PointingHandCursor)
        self.menu_btn.clicked.connect(self.show_card_menu)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.menu_btn)

        # 卡片主体
        body = QWidget()
        body.setStyleSheet("""
            QWidget {
                background-color: white;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
                padding: 12px;
            }
        """)
        body_layout = QVBoxLayout(body)

        # 显示卡片类型和描述
        type_label = QLabel(f"类型: {self.get_type_display()}")
        type_label.setStyleSheet("QLabel { color: #666; font-size: 12px; }")

        desc_label = QLabel(self.card_data.get('description', '暂无描述'))
        desc_label.setStyleSheet("QLabel { color: #333; font-size: 12px; margin-top: 8px; }")
        desc_label.setWordWrap(True)

        # 锁定状态显示
        if self.card_data.get('locked', False):
            lock_label = QLabel("🔒 已锁定")
            lock_label.setStyleSheet("QLabel { color: #e53e3e; font-size: 11px; margin-top: 8px; }")
            body_layout.addWidget(lock_label)

        body_layout.addWidget(type_label)
        body_layout.addWidget(desc_label)
        body_layout.addStretch()

        # 执行按钮
        execute_btn = QPushButton("执行")
        execute_btn.setStyleSheet("""
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
        """)
        execute_btn.clicked.connect(self.execute_card)

        body_layout.addWidget(execute_btn)

        layout.addWidget(header)
        layout.addWidget(body)

    def get_type_display(self):
        card_type = self.card_data.get('type', 'sql')
        type_map = {
            'sql': 'SQL查询',
            'sql_update': 'SQL更新',
            'sql_delete': 'SQL删除',
            'http': 'HTTP接口',
            'python': 'Python类'
        }
        return type_map.get(card_type, card_type)

    def show_card_menu(self):
        menu = QMenu(self)

        view_action = QAction("👁 查看", self)
        view_action.triggered.connect(lambda: self.parent_tab.view_card(self.card_data))
        menu.addAction(view_action)

        # 如果卡片未锁定，显示编辑选项
        if not self.card_data.get('locked', False):
            edit_action = QAction("✏️ 编辑", self)
            edit_action.triggered.connect(lambda: self.parent_tab.edit_card(self.card_data))
            menu.addAction(edit_action)

        copy_action = QAction("📋 复制", self)
        copy_action.triggered.connect(lambda: self.parent_tab.copy_card(self.card_data))
        menu.addAction(copy_action)

        # 如果卡片未锁定，显示删除选项
        if not self.card_data.get('locked', False):
            delete_action = QAction("🗑️ 删除", self)
            delete_action.triggered.connect(lambda: self.parent_tab.delete_card(self.card_data))
            menu.addAction(delete_action)

        menu.exec_(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft()))

    def execute_card(self):
        self.parent_tab.execute_card(self.card_data)


class ToolCardsTab(QWidget):
    """卡片工具Tab页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = "config/tool_cards.json"
        self.config_data = {}
        self.current_business_line = ""
        self.current_sub_business = ""
        self.init_ui()
        self.load_config()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 顶部业务线区域
        self.create_business_line_bar(main_layout)

        # 子业务模块区域
        self.create_sub_business_bar(main_layout)

        # 卡片区域
        self.create_cards_area(main_layout)

    def create_business_line_bar(self, parent_layout):
        # 业务线容器
        business_container = QWidget()
        business_container.setStyleSheet("""
            QWidget {
                background-color: #f8fafc;
                border-bottom: 1px solid #e2e8f0;
                padding: 8px 12px;
            }
        """)
        business_container.setFixedHeight(50)

        business_layout = QHBoxLayout(business_container)
        business_layout.setContentsMargins(0, 0, 0, 0)
        business_layout.setSpacing(10)

        # 业务线标签
        business_label = QLabel("业务线:")
        business_label.setStyleSheet("QLabel { font-weight: bold; color: #2d3748; }")

        # 业务线Tab区域（可滚动）
        self.business_tab_widget = QTabWidget()
        self.business_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar::tab {
                background: #e2e8f0;
                border: 1px solid #cbd5e0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                margin-right: 2px;
                color: #4a5568;
            }
            QTabBar::tab:selected {
                background: #4299e1;
                color: white;
                border-color: #4299e1;
            }
            QTabBar::tab:hover:!selected {
                background: #cbd5e0;
            }
        """)
        self.business_tab_widget.tabBar().setExpanding(False)
        self.business_tab_widget.currentChanged.connect(self.on_business_line_changed)

        # 配置按钮
        config_btn = QPushButton("配置")
        config_btn.setStyleSheet("""
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
        """)
        config_btn.clicked.connect(self.open_config_dialog)

        business_layout.addWidget(business_label)
        business_layout.addWidget(self.business_tab_widget, 1)
        business_layout.addWidget(config_btn)

        parent_layout.addWidget(business_container)

    def create_sub_business_bar(self, parent_layout):
        # 子业务容器
        sub_business_container = QWidget()
        sub_business_container.setStyleSheet("""
            QWidget {
                background-color: #f1f5f9;
                border-bottom: 1px solid #e2e8f0;
                padding: 6px 12px;
            }
        """)
        sub_business_container.setFixedHeight(40)

        sub_business_layout = QHBoxLayout(sub_business_container)
        sub_business_layout.setContentsMargins(0, 0, 0, 0)
        sub_business_layout.setSpacing(10)

        # 子业务标签
        sub_business_label = QLabel("子模块:")
        sub_business_label.setStyleSheet("QLabel { font-weight: bold; color: #2d3748; }")

        # 子业务Tab区域
        self.sub_business_tab_widget = QTabWidget()
        self.sub_business_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar::tab {
                background: transparent;
                border: none;
                padding: 4px 12px;
                margin-right: 8px;
                color: #4a5568;
                border-radius: 12px;
            }
            QTabBar::tab:selected {
                background: #4299e1;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #e2e8f0;
            }
        """)
        self.sub_business_tab_widget.tabBar().setExpanding(False)
        self.sub_business_tab_widget.currentChanged.connect(self.on_sub_business_changed)

        sub_business_layout.addWidget(sub_business_label)
        sub_business_layout.addWidget(self.sub_business_tab_widget, 1)
        sub_business_layout.addStretch()

        parent_layout.addWidget(sub_business_container)

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

    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
            else:
                # 创建默认配置
                self.config_data = {
                    "business_lines": [],
                    "default_business_line": ""
                }
                self.save_config()
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            self.config_data = {
                "business_lines": [],
                "default_business_line": ""
            }

    def save_config(self):
        """保存配置文件"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def refresh_ui(self):
        """刷新UI显示"""
        # 清空现有Tab
        self.business_tab_widget.clear()
        self.sub_business_tab_widget.clear()

        # 清空卡片区域
        for i in reversed(range(self.cards_layout.count())):
            widget = self.cards_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        business_lines = self.config_data.get('business_lines', [])

        # 添加业务线Tab
        for business in business_lines:
            self.business_tab_widget.addTab(QWidget(), business.get('name', '未命名'))

        # 设置默认业务线
        default_business = self.config_data.get('default_business_line', '')
        if business_lines and default_business:
            for i in range(len(business_lines)):
                if business_lines[i].get('name') == default_business:
                    self.business_tab_widget.setCurrentIndex(i)
                    break
            else:
                # 如果默认业务线不存在，选择第一个
                if business_lines:
                    self.business_tab_widget.setCurrentIndex(0)
        elif business_lines:
            self.business_tab_widget.setCurrentIndex(0)

        # 触发业务线变更事件
        if business_lines:
            self.on_business_line_changed(self.business_tab_widget.currentIndex())

    def on_business_line_changed(self, index):
        """业务线变更事件"""
        if index < 0:
            return

        business_lines = self.config_data.get('business_lines', [])
        if index >= len(business_lines):
            return

        current_business = business_lines[index]
        self.current_business_line = current_business.get('name', '')

        # 清空子业务Tab
        self.sub_business_tab_widget.clear()

        # 添加子业务Tab
        sub_businesses = current_business.get('sub_business', [])
        for sub_business in sub_businesses:
            self.sub_business_tab_widget.addTab(QWidget(), sub_business.get('name', '未命名'))

        # 触发子业务变更事件
        if sub_businesses:
            self.on_sub_business_changed(0)

    def on_sub_business_changed(self, index):
        """子业务变更事件"""
        if index < 0:
            return

        business_lines = self.config_data.get('business_lines', [])
        current_business_index = self.business_tab_widget.currentIndex()

        if current_business_index < 0 or current_business_index >= len(business_lines):
            return

        current_business = business_lines[current_business_index]
        sub_businesses = current_business.get('sub_business', [])

        if index >= len(sub_businesses):
            return

        current_sub_business = sub_businesses[index]
        self.current_sub_business = current_sub_business.get('name', '')

        # 清空卡片区域
        for i in reversed(range(self.cards_layout.count())):
            item = self.cards_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        # 添加卡片 - 使用网格布局，每行最多3个卡片
        cards = current_sub_business.get('cards', [])
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
        dialog = ToolCardsConfigDialog(self.config_data, self)
        if dialog.exec_() == ToolCardsConfigDialog.Accepted:
            self.config_data = dialog.get_config_data()
            self.save_config()
            self.refresh_ui()

    def view_card(self, card_data):
        """查看卡片"""
        dialog = ToolCardsConfigDialog(self.config_data, self, card_data, view_mode=True)
        dialog.exec_()

    def edit_card(self, card_data):
        """编辑卡片"""
        dialog = ToolCardsConfigDialog(self.config_data, self, card_data)
        if dialog.exec_() == ToolCardsConfigDialog.Accepted:
            self.config_data = dialog.get_config_data()
            self.save_config()
            self.refresh_ui()

    def copy_card(self, card_data):
        """复制卡片"""
        # 找到卡片所在位置
        business_lines = self.config_data.get('business_lines', [])
        for business in business_lines:
            for sub_business in business.get('sub_business', []):
                cards = sub_business.get('cards', [])
                for i, card in enumerate(cards):
                    if card.get('id') == card_data.get('id'):
                        # 创建副本
                        new_card = card_data.copy()
                        new_card['id'] = self.generate_card_id()

                        # 生成副本名称
                        base_name = card_data.get('title', '卡片')
                        copy_count = 1
                        new_title = f"{base_name}_cp{copy_count}"

                        # 检查名称是否已存在
                        while any(c.get('title') == new_title for c in cards):
                            copy_count += 1
                            new_title = f"{base_name}_cp{copy_count}"

                        new_card['title'] = new_title
                        new_card['locked'] = False  # 副本默认不锁定

                        # 添加到同一子业务模块
                        cards.append(new_card)

                        self.save_config()
                        self.refresh_ui()
                        return

        Toast.warning(self, "未找到要复制的卡片")

    def delete_card(self, card_data):
        """删除卡片"""
        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除卡片 '{card_data.get('title')}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            business_lines = self.config_data.get('business_lines', [])
            for business in business_lines:
                for sub_business in business.get('sub_business', []):
                    cards = sub_business.get('cards', [])
                    for i, card in enumerate(cards):
                        if card.get('id') == card_data.get('id'):
                            cards.pop(i)
                            self.save_config()
                            self.refresh_ui()
                            return

            Toast.warning(self, "未找到要删除的卡片")

    def execute_card(self, card_data):
        """执行卡片"""
        # 这里实现卡片执行逻辑
        # 根据卡片类型调用相应的执行器
        card_type = card_data.get('type', 'sql')

        if card_type.startswith('sql'):
            self.execute_sql_card(card_data)
        elif card_type == 'http':
            self.execute_http_card(card_data)
        elif card_type == 'python':
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
