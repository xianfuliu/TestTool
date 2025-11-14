"""
多标签页接口模板编辑器
支持同时编辑多个接口模板，每个模板在独立的标签页中编辑
"""

import json
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QTextEdit, QTableWidget,
                             QTableWidgetItem, QPushButton, QGroupBox,
                             QLabel, QCheckBox, QScrollArea,
                             QMessageBox, QDialog, QDialogButtonBox,
                             QShortcut, QMenu, QToolButton)
from PyQt5.QtCore import pyqtSignal, Qt, QEvent
from PyQt5.QtGui import QFont, QKeySequence, QIcon
from PyQt5.QtCore import QSize
from .no_wheel_widgets import NoWheelComboBox, NoWheelTabWidget
from src.ui.widgets.toast_tips import Toast


class TabbedTemplateEditor(QWidget):
    """多标签页接口模板编辑器主窗口"""
    
    saved = pyqtSignal(dict)  # 保存信号，传递模板数据
    tab_closed = pyqtSignal()  # 标签页关闭信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabs = {}  # 存储标签页数据：{tab_id: {'editor': editor, 'data': data, 'modified': bool}}
        self.current_tab_id = None
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 创建标签页控件
        self.tab_widget = NoWheelTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(lambda index: self.close_tab(index, from_close_button=True))
        self.tab_widget.currentChanged.connect(self.tab_changed)
        
        # 设置tab右键菜单
        self.tab_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self.show_tab_context_menu)
        
        layout.addWidget(self.tab_widget)
        
        
    def open_template(self, template_data=None, project_id=None, folder_id=None):
        """打开或创建模板编辑标签页"""
        # 生成标签页ID
        tab_id = self.generate_tab_id(template_data)
        
        # 如果标签页已存在，切换到该标签页
        if tab_id in self.tabs:
            index = self.tab_widget.indexOf(self.tabs[tab_id]['widget'])
            self.tab_widget.setCurrentIndex(index)
            return tab_id
        
        # 创建新的标签页
        editor_widget = TemplateTabWidget(template_data, project_id, folder_id)
        
        # 连接信号
        editor_widget.modified_signal.connect(lambda modified: self.set_tab_modified(tab_id, modified))
        editor_widget.saved.connect(lambda data: self.template_saved(tab_id, data))
        editor_widget.debugged.connect(lambda data: self.template_debugged(tab_id, data))
        
        # 添加到标签页
        tab_name = template_data.get('name', '新增接口') if template_data else '新增接口'
        index = self.tab_widget.addTab(editor_widget, tab_name)
        
        # 存储标签页数据
        self.tabs[tab_id] = {
            'widget': editor_widget,
            'data': template_data or {},
            'modified': False,
            'tab_name': tab_name
        }
        
        # 设置当前标签页
        self.tab_widget.setCurrentIndex(index)
        self.current_tab_id = tab_id
        
        return tab_id
    
    def generate_tab_id(self, template_data):
        """生成标签页唯一ID"""
        if template_data and 'id' in template_data:
            return f"template_{template_data['id']}"
        else:
            return f"new_template_{len(self.tabs)}"
    
    def close_tab(self, index, from_close_button=True):
        """关闭标签页
        
        Args:
            index: 标签页索引
            from_close_button: 是否来自关闭按钮的调用，True表示用户点击关闭按钮，False表示程序内部调用
        """
        widget = self.tab_widget.widget(index)
        
        # 查找对应的标签页ID
        tab_id = None
        for tid, tab_data in self.tabs.items():
            if tab_data['widget'] == widget:
                tab_id = tid
                break
        
        if tab_id is None:
            self.tab_widget.removeTab(index)
            # 检查是否还有标签页，如果没有则发出关闭信号
            if self.tab_widget.count() == 0:
                self.tab_closed.emit()
            return
        
        # 检查是否有未保存的修改
        if self.tabs[tab_id]['modified']:
            # 无论是用户点击关闭按钮还是程序内部调用，都显示保存确认弹窗
            # 这样可以避免意外丢失未保存的工作，也能防止潜在的Qt框架异常
            tab_name = self.tabs[tab_id]['tab_name']
            
            # 创建自定义消息框，使用中文按钮名称
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('保存确认')
            msg_box.setText(f'标签页 "{tab_name}" 有未保存的修改，请选择操作：')
            
            # 添加自定义按钮
            save_btn = msg_box.addButton('保存', QMessageBox.AcceptRole)
            ignore_btn = msg_box.addButton('忽略', QMessageBox.DestructiveRole)
            cancel_btn = msg_box.addButton('取消', QMessageBox.RejectRole)
            
            # 设置默认按钮
            msg_box.setDefaultButton(save_btn)
            
            msg_box.exec_()
            
            clicked_button = msg_box.clickedButton()
            
            if clicked_button == save_btn:
                # 保存模板
                self.tabs[tab_id]['widget'].save_template()
                # 保存完成后，标记标签页为已保存状态
                self.set_tab_modified(tab_id, False)
                
                # 保存后关闭标签页
                self.tab_widget.removeTab(index)
                del self.tabs[tab_id]
                # 检查是否还有标签页，如果没有则发出关闭信号
                if self.tab_widget.count() == 0:
                    self.tab_closed.emit()
            elif clicked_button == ignore_btn:
                # 忽略修改，直接关闭
                self.tab_widget.removeTab(index)
                del self.tabs[tab_id]
                # 检查是否还有标签页，如果没有则发出关闭信号
                if self.tab_widget.count() == 0:
                    self.tab_closed.emit()
            else:
                # 取消关闭
                return
        else:
            # 没有修改，直接关闭
            self.tab_widget.removeTab(index)
            del self.tabs[tab_id]
            # 检查是否还有标签页，如果没有则发出关闭信号
            if self.tab_widget.count() == 0:
                self.tab_closed.emit()
    
    def show_tab_context_menu(self, pos):
        """显示tab右键菜单"""
        # 获取点击位置的tab索引
        index = self.tab_widget.tabBar().tabAt(pos)
        if index == -1:
            return
            
        # 创建右键菜单
        menu = QMenu(self)
        
        # 添加菜单项
        close_current_action = menu.addAction("关闭当前")
        close_others_action = menu.addAction("关闭其他")
        close_all_action = menu.addAction("关闭全部")
        
        # 连接菜单项信号
        close_current_action.triggered.connect(lambda: self.close_current_tab(index))
        close_others_action.triggered.connect(lambda: self.close_other_tabs(index))
        close_all_action.triggered.connect(self.close_all_tabs)
        
        # 显示菜单
        menu.exec_(self.tab_widget.mapToGlobal(pos))
    
    def close_current_tab(self, index):
        """关闭当前标签页"""
        self.close_tab(index, from_close_button=False)
    
    def close_other_tabs(self, current_index):
        """关闭其他标签页"""
        # 获取所有标签页索引
        tab_count = self.tab_widget.count()
        if tab_count <= 1:
            return
            
        # 从后往前关闭标签页（避免索引变化问题）
        for i in range(tab_count - 1, -1, -1):
            if i != current_index:
                self.close_tab(i, from_close_button=False)
    
    def close_all_tabs(self):
        """关闭全部标签页"""
        # 直接关闭所有标签页，不依赖循环索引
        while self.tab_widget.count() > 0:
            self.close_tab(0, from_close_button=False)
        
        # 确保在所有标签页关闭后发出tab_closed信号
        # 这里不需要再次检查，因为close_tab方法内部已经检查并发射了信号
        # 但为了确保信号被正确发射，我们直接发射一次
        self.tab_closed.emit()
    
    def close_tab_by_template_id(self, template_id):
        """根据模板ID关闭对应的标签页"""
        tab_id = f"template_{template_id}"
        
        # 查找对应的标签页索引
        for index in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(index)
            
            # 查找对应的标签页ID
            for tid, tab_data in self.tabs.items():
                if tab_data['widget'] == widget and tid == tab_id:
                    # 关闭标签页
                    self.close_tab(index, from_close_button=False)
                    return True
        
        return False  # 没有找到对应的标签页
    
    def tab_changed(self, index):
        """标签页切换事件"""
        if index == -1:
            self.current_tab_id = None
            return
        
        widget = self.tab_widget.widget(index)
        
        # 查找对应的标签页ID
        for tab_id, tab_data in self.tabs.items():
            if tab_data['widget'] == widget:
                self.current_tab_id = tab_id
                break
    
    def set_tab_modified(self, tab_id, modified):
        """设置标签页修改状态"""
        if tab_id in self.tabs:
            self.tabs[tab_id]['modified'] = modified
            
            # 更新标签页标题（添加*号表示修改）
            tab_name = self.tabs[tab_id]['tab_name']
            if modified:
                tab_name = f"*{tab_name}"
            
            # 查找标签页索引
            for i in range(self.tab_widget.count()):
                if self.tab_widget.widget(i) == self.tabs[tab_id]['widget']:
                    self.tab_widget.setTabText(i, tab_name)
                    break
    
    def template_saved(self, tab_id, data):
        """模板保存事件"""
        if tab_id in self.tabs:
            self.tabs[tab_id]['data'] = data
            self.tabs[tab_id]['tab_name'] = data.get('name', '未命名')
            
            # 触发外部保存信号，传递模板数据到实际的保存逻辑
            # 注意：这里不立即设置修改状态，等待实际的保存结果
            self.saved.emit(data)
    
    def template_debugged(self, tab_id, data):
        """模板调试事件"""
        # 直接更新当前标签页的响应信息展示区域
        if tab_id in self.tabs:
            tab_widget = self.tabs[tab_id]['widget']
            response_data = data.get('response', {})
            
            # 获取响应体内容
            response_body = response_data.get('body', {})
            if not response_body:
                response_body = response_data.get('text', '')
            
            # 格式化JSON响应体
            try:
                if isinstance(response_body, str):
                    # 如果是字符串，尝试解析为JSON
                    parsed_body = json.loads(response_body)
                    formatted_body = json.dumps(parsed_body, indent=2, ensure_ascii=False)
                else:
                    # 如果是字典，直接格式化
                    formatted_body = json.dumps(response_body, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                # 如果不是JSON格式，直接显示原始内容
                formatted_body = str(response_body)
            
            # 更新响应信息展示区域
            tab_widget.response_body_edit.setPlainText(formatted_body)
            
            # 如果调试失败，显示错误信息
            if not response_data.get('success', True):
                error_message = response_data.get('error', '调试失败')
                tab_widget.response_body_edit.setPlainText(f"调试失败: {error_message}")
    
    def get_current_template_data(self):
        """获取当前标签页的模板数据"""
        if self.current_tab_id and self.current_tab_id in self.tabs:
            return self.tabs[self.current_tab_id]['data']
        return None
    
    def has_modified_tabs(self):
        """检查是否有未保存的标签页"""
        return any(tab['modified'] for tab in self.tabs.values())


class TemplateTabWidget(QWidget):
    """单个模板标签页的编辑组件"""
    
    modified_signal = pyqtSignal(bool)  # 修改状态信号
    saved = pyqtSignal(dict)     # 保存信号
    debugged = pyqtSignal(dict)  # 调试信号
    
    def __init__(self, template_data=None, project_id=None, folder_id=None, parent=None):
        super().__init__(parent)
        self.template_data = template_data or {}
        self.project_id = project_id
        self.folder_id = folder_id
        self.is_edit = bool(template_data)
        self.modified = False
        
        # 如果是新增模板，设置默认的Content-Type请求头
        if not self.is_edit:
            if 'headers' not in self.template_data:
                self.template_data['headers'] = {}
            self.template_data['headers']['Content-Type'] = 'application/json'
        
        self.init_ui()
        self.setup_shortcuts()
        
        if self.is_edit:
            self.load_template_data()
    
    def setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+S 保存模板
        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self.save_template)
        self.save_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
    
    # close_current_tab方法已被移除，Ctrl+W快捷键功能已取消
    
    def init_ui(self):
        """初始化界面 - 固定高度布局，外层无滚动条"""
        # 主布局 - 使用垂直布局，外层无滚动条
        main_layout = QVBoxLayout(self)
        
        # 接口信息区域（紧凑布局）
        self.setup_interface_info(main_layout)
        
        # 基本信息区域
        self.setup_basic_info(main_layout)
        
        # 功能子标签页 - 固定高度，内部可以有滚动条
        self.setup_function_tabs(main_layout)
        
        # 底部按钮区域
        self.setup_bottom_buttons(main_layout)
    
    def setup_interface_info(self, layout):
        """设置接口信息区域（接口名称和描述在两行）"""
        # 接口名称在第一行
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("接口名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入接口名称")
        self.name_edit.textChanged.connect(self.on_content_changed)
        self.name_edit.setMinimumHeight(30)  # 设置最小高度
        # 设置字体大小
        font = self.name_edit.font()
        font.setPointSize(10)
        self.name_edit.setFont(font)
        name_layout.addWidget(self.name_edit)
        name_layout.addStretch()
        layout.addLayout(name_layout)
        
        # 接口描述在第二行
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("接口描述:"))
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setMinimumHeight(30)  # 设置最小高度
        self.description_edit.setPlaceholderText("请输入接口描述")
        self.description_edit.textChanged.connect(self.on_content_changed)
        # 设置字体大小与接口名称保持一致
        desc_font = self.description_edit.font()
        desc_font.setPointSize(10)
        self.description_edit.setFont(desc_font)
        desc_layout.addWidget(self.description_edit)
        desc_layout.addStretch()
        layout.addLayout(desc_layout)
        
        layout.addSpacing(15)  # 增加区域之间的间距
    
    def setup_basic_info(self, layout):
        """设置基本信息区域（请求方法、URL）"""
        # 基本信息区域 - 请求方法和URL路径
        basic_layout = QHBoxLayout()
        
        # 请求方法 - 仅保留GET/POST/PUT/DELETE
        basic_layout.addWidget(QLabel("请求方法:"))
        self.method_combo = NoWheelComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE"])
        self.method_combo.currentTextChanged.connect(self.on_content_changed)
        self.method_combo.setMaximumWidth(100)
        basic_layout.addWidget(self.method_combo)
        
        # URL路径 - 进一步增加输入框宽度
        basic_layout.addWidget(QLabel("URL路径:"))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("例如: /api/v1/users")
        self.url_edit.textChanged.connect(self.on_content_changed)
        self.url_edit.setMinimumWidth(600)  # 设置更大的最小宽度
        basic_layout.addWidget(self.url_edit)
        
        # 添加弹性空间
        basic_layout.addStretch()
        
        layout.addLayout(basic_layout)
        layout.addSpacing(5)
    
    def setup_bottom_buttons(self, layout):
        """设置底部按钮区域（响应信息展示区域 + 保存、调试按钮在右侧）"""
        
        # 响应信息展示区域 - 紧凑布局，支持可扩展
        response_widget = QWidget()
        response_layout = QVBoxLayout(response_widget)
        response_layout.setSpacing(1)  # 进一步减少内部间距
        response_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 响应信息标签放在左上角 - 固定高度，无上下间隙
        response_label = QLabel("响应")
        response_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 0px; padding: 0px;")
        response_label.setFixedHeight(25)  # 固定高度
        response_layout.addWidget(response_label)
        
        # 响应体展示区域 - 可扩展高度
        self.response_body_edit = QTextEdit()
        self.response_body_edit.setReadOnly(True)
        self.response_body_edit.setFont(QFont("Consolas", 10))  # 调大字体
        self.response_body_edit.setMinimumHeight(80)  # 最小高度
        self.response_body_edit.setMaximumHeight(300)  # 最大高度，可扩展
        self.response_body_edit.setPlaceholderText("调试响应将显示在这里...")
        
        # 添加滚动条支持
        self.response_body_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        response_layout.addWidget(self.response_body_edit)
        
        layout.addWidget(response_widget)
        layout.addSpacing(2)  # 进一步减少外部间距
        
        # 底部按钮布局
        button_layout = QHBoxLayout()
        
        # 添加弹性空间使按钮靠右
        button_layout.addStretch()
        
        # 调试按钮
        self.debug_btn = QPushButton("调试")
        self.debug_btn.clicked.connect(self.debug_template)
        self.debug_btn.setMaximumWidth(80)
        self.debug_btn.setMinimumHeight(35)
        button_layout.addWidget(self.debug_btn)
        
        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_template)
        self.save_btn.setMaximumWidth(80)
        self.save_btn.setMinimumHeight(35)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        layout.addSpacing(5)  # 减少底部间距
    
    def setup_function_tabs(self, layout):
        """设置功能子标签页"""
        # 创建子标签页控件
        self.function_tabs = NoWheelTabWidget()
        self.function_tabs.setMinimumHeight(400)  # 增加标签页的最小高度
        
        # 设置标签页字体大小
        font = self.function_tabs.font()
        font.setPointSize(11)  # 增大字体大小，提高可读性
        self.function_tabs.setFont(font)
        
        # 调整tab的宽度和高度，使其更加协调
        self.function_tabs.setStyleSheet("""
            QTabBar::tab {
                min-width: 60px;
                max-width: 80px;
                height: 20px;
                font-size: 12px; 
                padding: 5px 10px;
            }
        """)
        
        # 请求头标签页
        headers_tab = QWidget()
        self.setup_headers_tab(headers_tab)
        self.function_tabs.addTab(headers_tab, "请求头")
        
        # 参数标签页
        params_tab = QWidget()
        self.setup_params_tab(params_tab)
        self.function_tabs.addTab(params_tab, "参数")
        
        # 请求体标签页
        body_tab = QWidget()
        self.setup_body_tab(body_tab)
        self.function_tabs.addTab(body_tab, "请求体")
        
        # 配置标签页
        config_tab = QWidget()
        self.setup_config_tab(config_tab)
        self.function_tabs.addTab(config_tab, "配置")
        
        layout.addWidget(self.function_tabs)
    
    def setup_headers_tab(self, parent):
        """设置请求头标签页 - 内部滚动条"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        
        # 主容器
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)  # 增加边距避免边框重叠
        layout.setSpacing(10)
        
        # 请求头表格
        self.headers_table = QTableWidget()
        self.headers_table.setColumnCount(2)
        self.headers_table.setHorizontalHeaderLabels(["Header名称", "Header值"])
        self.headers_table.horizontalHeader().setStretchLastSection(True)
        self.headers_table.verticalHeader().setVisible(False)  # 隐藏序号列
        self.headers_table.cellChanged.connect(self.on_content_changed)
        # 优化表格样式
        self.headers_table.setAlternatingRowColors(True)
        self.headers_table.setStyleSheet("""
            QTableWidget {
                background-color: #fafafa;
                alternate-background-color: #f0f0f0;
                gridline-color: #e0e0e0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #e8e8e8;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QTableWidget::item:hover {
                background-color: #f5f5f5;
            }
            QHeaderView::section {
                background-color: #d0d0d0;
                color: #333333;
                font-weight: bold;
                font-size: 11px;
                padding: 6px;
                border: none;
                border-right: 1px solid #b0b0b0;
                min-height: 25px;
            }
            QTableCornerButton::section {
                background-color: #4caf50;
                border: none;
            }
        """)
        self.headers_table.setMinimumHeight(300)  # 增加表格最小高度
        self.headers_table.verticalHeader().setDefaultSectionSize(50)  # 进一步增加行高确保内容完全可见
        layout.addWidget(self.headers_table)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        add_header_btn = QPushButton("新增")
        remove_header_btn = QPushButton("删除")
        add_header_btn.clicked.connect(self.add_header_row)
        remove_header_btn.clicked.connect(self.remove_header_row)
        
        # 优化按钮样式
        button_style = """
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
            QPushButton:pressed {
                background-color: #2e7d32;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        add_header_btn.setStyleSheet(button_style)
        remove_header_btn.setStyleSheet(button_style)
        
        button_layout.addWidget(add_header_btn)
        button_layout.addWidget(remove_header_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 设置滚动区域
        scroll_area.setWidget(container)
        
        # 主布局
        main_layout = QVBoxLayout(parent)
        main_layout.addWidget(scroll_area)
    
    def setup_params_tab(self, parent):
        """设置参数标签页 - 内部滚动条"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        
        # 主容器
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # 参数表格
        self.params_table = QTableWidget()
        self.params_table.setColumnCount(2)
        self.params_table.setHorizontalHeaderLabels(["参数名", "参数值"])
        self.params_table.horizontalHeader().setStretchLastSection(True)
        self.params_table.verticalHeader().setVisible(False)  # 隐藏序号列
        self.params_table.cellChanged.connect(self.on_content_changed)
        # 优化表格样式
        self.params_table.setAlternatingRowColors(True)
        self.params_table.setStyleSheet("""
            QTableWidget {
                background-color: #fafafa;
                alternate-background-color: #f0f0f0;
                gridline-color: #e0e0e0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #e8e8e8;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QTableWidget::item:hover {
                background-color: #f5f5f5;
            }
            QHeaderView::section {
                background-color: #d0d0d0;
                color: #333333;
                font-weight: bold;
                font-size: 11px;
                padding: 6px;
                border: none;
                border-right: 1px solid #b0b0b0;
                min-height: 25px;
            }
            QTableCornerButton::section {
                background-color: #4caf50;
                border: none;
            }
        """)
        self.params_table.setMinimumHeight(300)  # 增加表格最小高度
        self.params_table.verticalHeader().setDefaultSectionSize(50)  # 进一步增加行高确保内容完全可见
        layout.addWidget(self.params_table)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        add_param_btn = QPushButton("新增")
        remove_param_btn = QPushButton("删除")
        add_param_btn.clicked.connect(self.add_param_row)
        remove_param_btn.clicked.connect(self.remove_param_row)
        
        # 优化按钮样式
        button_style = """
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
            QPushButton:pressed {
                background-color: #2e7d32;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        add_param_btn.setStyleSheet(button_style)
        remove_param_btn.setStyleSheet(button_style)
        
        button_layout.addWidget(add_param_btn)
        button_layout.addWidget(remove_param_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 设置滚动区域
        scroll_area.setWidget(container)
        
        # 主布局
        main_layout = QVBoxLayout(parent)
        main_layout.addWidget(scroll_area)
    
    def setup_body_tab(self, parent):
        """设置请求体标签页 - 内部滚动条"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        
        # 主容器
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 5, 10, 10)
        layout.setSpacing(8)
        
        # 操作按钮布局
        button_layout = QHBoxLayout()
        
        button_layout.addStretch()  # 将按钮推到右边
        
        # JSON美化图标按钮
        beautify_btn = QToolButton()
        beautify_btn.setToolTip("美化JSON")
        beautify_btn.clicked.connect(self.beautify_json)
        
        # 设置图标 - 修正路径构建逻辑
        # 从当前文件路径计算项目根目录
        current_file_path = os.path.abspath(__file__)
        # 当前文件路径：d:\workspace\TestTool\src\ui\interface_auto\components\tabbed_template_editor.py
        # 项目根目录应该是：d:\workspace\TestTool
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))))
        icon_path = os.path.join(base_dir, "src", "resources", "icons", "beauty.png")
        if os.path.exists(icon_path):
            beautify_btn.setIcon(QIcon(icon_path))
        else:
            # 如果图标文件不存在，使用文本作为备选
            beautify_btn.setText("美化")
        
        # 设置图标大小
        beautify_btn.setIconSize(QSize(16, 16))
        
        # 使用工具按钮样式
        button_style = """
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px 4px;
                margin: 0px;
            }
            QToolButton:hover {
                background-color: #f0f0f0;
            }
            QToolButton:pressed {
                background-color: #e0e0e0;
            }
        """
        beautify_btn.setStyleSheet(button_style)
        
        button_layout.addWidget(beautify_btn)
        layout.addLayout(button_layout)
        
        # 请求体编辑器
        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText('请输入JSON格式的请求体，例如: {"key": "value"}')
        self.body_edit.textChanged.connect(self.on_content_changed)
        self.body_edit.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
                font-size: 14px;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border-color: #b0b0b0;
                background-color: #ffffff;
            }
        """)
        self.body_edit.setMinimumHeight(300)  # 增加编辑器最小高度
        layout.addWidget(self.body_edit)
        
        # 设置滚动区域
        scroll_area.setWidget(container)
        
        # 主布局
        main_layout = QVBoxLayout(parent)
        main_layout.addWidget(scroll_area)
    
    def setup_config_tab(self, parent):
        """设置配置标签页 - 内部滚动条"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white;
            }
            QScrollArea > QWidget > QWidget {
                background-color: white;
            }
        """)
        
        # 主容器
        container = QWidget()
        container.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 超时设置
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("超时时间(秒):"))
        self.timeout_edit = QLineEdit()
        self.timeout_edit.setText("30")
        self.timeout_edit.setMaximumWidth(100)
        self.timeout_edit.textChanged.connect(self.on_content_changed)
        timeout_layout.addWidget(self.timeout_edit)
        timeout_layout.addStretch()
        
        # 重试设置
        retry_layout = QHBoxLayout()
        self.retry_check = QCheckBox("启用重试机制")
        self.retry_count_edit = QLineEdit()
        self.retry_count_edit.setText("3")
        self.retry_count_edit.setMaximumWidth(50)
        self.retry_count_edit.setEnabled(False)
        self.retry_check.toggled.connect(self.retry_count_edit.setEnabled)
        self.retry_check.toggled.connect(self.on_content_changed)
        self.retry_count_edit.textChanged.connect(self.on_content_changed)
        retry_layout.addWidget(self.retry_check)
        retry_layout.addWidget(QLabel("重试次数:"))
        retry_layout.addWidget(self.retry_count_edit)
        retry_layout.addStretch()
        
        layout.addLayout(timeout_layout)
        layout.addLayout(retry_layout)
        layout.addStretch()
        
        # 设置滚动区域
        scroll_area.setWidget(container)
        
        # 主布局
        main_layout = QVBoxLayout(parent)
        main_layout.addWidget(scroll_area)
    
    def on_content_changed(self):
        """内容改变事件"""
        if not self.modified:
            self.modified = True
            self.modified_signal.emit(True)
    
    def add_header_row(self):
        """添加Header行"""
        row = self.headers_table.rowCount()
        self.headers_table.insertRow(row)
        self.headers_table.setItem(row, 0, QTableWidgetItem(""))
        self.headers_table.setItem(row, 1, QTableWidgetItem(""))
        self.on_content_changed()
    
    def remove_header_row(self):
        """删除选中的Header行"""
        selected_rows = set()
        for item in self.headers_table.selectedItems():
            selected_rows.add(item.row())
        
        for row in sorted(selected_rows, reverse=True):
            self.headers_table.removeRow(row)
        self.on_content_changed()
    
    def add_param_row(self):
        """添加参数行"""
        row = self.params_table.rowCount()
        self.params_table.insertRow(row)
        self.params_table.setItem(row, 0, QTableWidgetItem(""))
        self.params_table.setItem(row, 1, QTableWidgetItem(""))
        self.on_content_changed()
    
    def remove_param_row(self):
        """删除选中的参数行"""
        selected_rows = set()
        for item in self.params_table.selectedItems():
            selected_rows.add(item.row())
        
        for row in sorted(selected_rows, reverse=True):
            self.params_table.removeRow(row)
        self.on_content_changed()
    
    def load_template_data(self):
        """加载模板数据到表单"""
        if not self.template_data:
            return
        
        # 基本信息
        self.name_edit.setText(self.template_data.get('name', ''))
        self.description_edit.setText(self.template_data.get('description', ''))
        
        # 请求配置
        self.method_combo.setCurrentText(self.template_data.get('method', 'GET'))
        self.url_edit.setText(self.template_data.get('url_path', ''))
        
        # Headers
        headers = self.template_data.get('headers', {})
        self.headers_table.setRowCount(len(headers))
        for i, (key, value) in enumerate(headers.items()):
            self.headers_table.setItem(i, 0, QTableWidgetItem(key))
            self.headers_table.setItem(i, 1, QTableWidgetItem(str(value)))
        
        # 参数
        params = self.template_data.get('params', {})
        self.params_table.setRowCount(len(params))
        for i, (key, value) in enumerate(params.items()):
            self.params_table.setItem(i, 0, QTableWidgetItem(key))
            self.params_table.setItem(i, 1, QTableWidgetItem(str(value)))
        
        # 请求体
        body = self.template_data.get('body', {})
        if body:
            self.body_edit.setText(json.dumps(body, indent=2, ensure_ascii=False))
        
        # 高级配置
        self.timeout_edit.setText(str(self.template_data.get('timeout', 30)))
        self.retry_check.setChecked(self.template_data.get('retry_enabled', False))
        self.retry_count_edit.setText(str(self.template_data.get('retry_count', 3)))
        self.retry_count_edit.setEnabled(self.template_data.get('retry_enabled', False))
        
        self.modified = False
    
    def get_data(self):
        """获取表单数据"""
        # 基本信息
        data = {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'method': self.method_combo.currentText(),
            'url_path': self.url_edit.text().strip(),
            'project_id': self.project_id or self.template_data.get('project_id'),
            'folder_id': self.folder_id or self.template_data.get('folder_id'),
            'sort_order': self.template_data.get('sort_order', 0),  # 关键修复：包含排序顺序
            'timeout': int(self.timeout_edit.text()) if self.timeout_edit.text().isdigit() else 30,
            'retry_enabled': self.retry_check.isChecked(),
            'retry_count': int(self.retry_count_edit.text()) if self.retry_count_edit.text().isdigit() else 3
        }
        
        # Headers
        headers = {}
        for row in range(self.headers_table.rowCount()):
            key_item = self.headers_table.item(row, 0)
            value_item = self.headers_table.item(row, 1)
            if key_item and key_item.text().strip():
                headers[key_item.text().strip()] = value_item.text().strip() if value_item else ""
        data['headers'] = headers
        
        # 参数
        params = {}
        for row in range(self.params_table.rowCount()):
            key_item = self.params_table.item(row, 0)
            value_item = self.params_table.item(row, 1)
            if key_item and key_item.text().strip():
                params[key_item.text().strip()] = value_item.text().strip() if value_item else ""
        data['params'] = params
        
        # 请求体
        body_text = self.body_edit.toPlainText().strip()
        if body_text:
            try:
                data['body'] = json.loads(body_text)
            except json.JSONDecodeError:
                data['body'] = body_text
        else:
            data['body'] = {}
        
        return data
    
    def save_template(self):
        """保存模板"""
        # 验证必填字段
        if not self.name_edit.text().strip():
            Toast.warning(self, "请输入接口名称")
            return
        
        if not self.url_edit.text().strip():
            Toast.warning(self, "请输入URL路径")
            return
        
        data = self.get_data()
        
        # 如果是编辑模式，添加ID
        if self.is_edit and 'id' in self.template_data:
            data['id'] = self.template_data['id']
        
        # 发出保存信号，但不立即标记为已保存状态
        # 等待实际的保存结果来决定是否更新状态
        self.saved.emit(data)
    
    def debug_template(self):
        """调试模板"""
        # 验证必填字段
        if not self.name_edit.text().strip():
            Toast.warning(self, "请输入接口名称")
            return
        
        if not self.url_edit.text().strip():
            Toast.warning(self, "请输入URL路径")
            return
        
        # 获取表单数据
        data = self.get_data()
        
        # 如果是编辑模式，添加ID
        if self.is_edit and 'id' in self.template_data:
            data['id'] = self.template_data['id']
        
        # 禁用调试按钮，防止重复点击
        self.debug_btn.setEnabled(False)
        self.debug_btn.setText("调试中...")
        
        # 导入调试请求引擎
        from .debug_request_engine import DebugRequestEngine, create_debug_request_data
        
        # 创建调试请求引擎
        self.debug_engine = DebugRequestEngine()
        
        # 创建调试请求数据
        debug_request_data = create_debug_request_data(data)
        
        # 执行调试请求
        self.debug_engine.execute_debug_request(
            debug_request_data,
            finished_callback=self.on_debug_finished,
            error_callback=self.on_debug_error
        )
    
    def on_debug_finished(self, response_data):
        """调试完成回调"""
        # 重新启用调试按钮
        self.debug_btn.setEnabled(True)
        self.debug_btn.setText("调试")
        
        # 获取表单数据
        request_data = self.get_data()
        
        # 构建调试结果数据
        debug_result = {
            'request': request_data,
            'response': response_data
        }
        
        # 发出调试完成信号
        self.debugged.emit(debug_result)
    
    def on_debug_error(self, error_message):
        """调试错误回调"""
        # 重新启用调试按钮
        self.debug_btn.setEnabled(True)
        self.debug_btn.setText("调试")
        
        # 获取表单数据
        request_data = self.get_data()
        
        # 构建错误响应数据
        error_response = {
            'success': False,
            'error': error_message,
            'status_code': 0,
            'response_time': 0
        }
        
        # 构建调试结果数据
        debug_result = {
            'request': request_data,
            'response': error_response
        }
        
        # 发出调试完成信号
        self.debugged.emit(debug_result)
    
    def beautify_json(self):
        """JSON美化功能"""
        current_text = self.body_edit.toPlainText().strip()
        
        if not current_text:
            Toast.info(self, "请输入JSON内容")
            return
        
        try:
            # 解析JSON
            json_data = json.loads(current_text)
            
            # 格式化JSON
            formatted_json = json.dumps(json_data, indent=2, ensure_ascii=False)
            
            # 更新编辑器内容
            self.body_edit.setPlainText(formatted_json)
            
            # 标记为已修改
            if not self.modified:
                self.modified = True
                self.modified_signal.emit(True)
                
        except json.JSONDecodeError as e:
            Toast.error(self, f"JSON格式不正确：{str(e)}")