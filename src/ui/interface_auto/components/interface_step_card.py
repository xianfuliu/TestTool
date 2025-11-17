import json
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QToolButton, QMenu, QFrame, QTabWidget,
                             QScrollArea, QGridLayout, QLineEdit, QTextEdit,
                             QComboBox, QCheckBox, QMessageBox, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QByteArray, QDataStream, QIODevice, QSize, QPoint
from PyQt5.QtGui import QIcon, QFont, QDrag, QPixmap
from src.utils.resource_utils import resource_path


class InterfaceStepCard(QFrame):
    """接口步骤卡片组件"""
    
    status_changed = pyqtSignal(int, bool)  # step_id, enabled
    step_deleted = pyqtSignal(str)  # step_id
    step_updated = pyqtSignal(dict)  # 步骤数据更新
    step_moved = pyqtSignal(str, str, int, int)  # dragged_step_id, target_step_id, from_index, to_index
    step_copied = pyqtSignal(int, dict)  # step_id, copied_step_data - 步骤复制信号
    api_template_clicked = pyqtSignal(str)  # api_template_id - 接口模板点击信号

    def __init__(self, step_data, parent=None):
        super().__init__(parent)
        self.step_data = step_data
        # 使用前端独立UUID系统：如果step_data中没有frontend_id，则生成新的UUID
        if 'frontend_id' not in step_data:
            import uuid
            step_data['frontend_id'] = str(uuid.uuid4())
        self.step_id = step_data['frontend_id']  # 使用前端ID作为唯一标识
        self.drag_start_position = None
        self.init_ui()
        self.setup_styles()
        self.set_draggable(True)

    def get_icon(self, icon_name):
        """获取图标"""
        try:
            # 使用相对路径访问图标资源
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            icon_path = os.path.join(base_dir, "resources", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
        except:
            pass
        return QIcon()

    def init_ui(self):
        """初始化界面"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # 设置卡片样式
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: white;
            }
        """)
        
        # 设置步骤容器高度适应流式布局
        self.setMinimumHeight(485)  # 最小高度
        self.setMaximumHeight(600)  # 最大高度
        
        # 设置自适应宽度，适应流式布局
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMinimumWidth(400)  # 最小宽度
        self.setMaximumWidth(500)  # 最大宽度

        # 1. 顶部：启用/停用、删除
        self.create_header()
        
        # 2. 接口展示框：请求方式+接口名称
        self.create_interface_display()
        
        # 3. Tab区域：前置、断言、后置
        self.create_tab_area()
        
        # 添加到主布局
        main_layout.addLayout(self.header_layout)
        main_layout.addWidget(self.interface_frame)
        main_layout.addWidget(self.tab_widget)
        
        # 默认显示Tab区域
        self.tab_widget.show()

    def create_header(self):
        """创建顶部头部区域"""
        self.header_layout = QHBoxLayout()
        
        # 步骤序号
        self.step_label = QLabel(f"step{self.step_data.get('order', 1)}")
        self.step_label.setFont(QFont("Arial", 9, QFont.Bold))
        
        # 复制按钮 - 使用图标
        self.copy_btn = QPushButton()
        self.copy_btn.setFixedSize(28, 28)  # 固定按钮大小，正方形
        self.copy_btn.setIcon(self.get_icon("copy.png"))
        self.copy_btn.setIconSize(QSize(16, 16))
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(33, 150, 243, 0.15);
                border: 1px solid rgba(33, 150, 243, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(33, 150, 243, 0.25);
                border: 1px solid rgba(33, 150, 243, 0.4);
            }
        """)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setToolTip("复制步骤")
        
        # 启用/停用按钮
        self.status_btn = QPushButton()
        self.status_btn.setCheckable(True)
        self.status_btn.setChecked(self.step_data.get('enabled', True))
        self.status_btn.setFixedSize(28, 28)  # 固定按钮大小，正方形
        
        # 设置初始图标
        if self.step_data.get('enabled', True):
            self.status_btn.setIcon(self.get_icon("stop.png"))
            self.status_btn.setToolTip("停用步骤")
        else:
            self.status_btn.setIcon(self.get_icon("start.png"))
            self.status_btn.setToolTip("启用步骤")
            
        self.status_btn.setIconSize(QSize(16, 16))
        self.status_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(33, 150, 243, 0.15);
                border: 1px solid rgba(33, 150, 243, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(33, 150, 243, 0.25);
                border: 1px solid rgba(33, 150, 243, 0.4);
            }
            QPushButton:checked {
                background-color: transparent;
            }
        """)
        self.status_btn.setCursor(Qt.PointingHandCursor)
        
        # 删除按钮 - 使用图标
        self.delete_btn = QPushButton()
        self.delete_btn.setFixedSize(28, 28)  # 固定按钮大小，正方形
        self.delete_btn.setIcon(self.get_icon("delete.png"))
        self.delete_btn.setIconSize(QSize(16, 16))
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(244, 67, 54, 0.15);
                border: 1px solid rgba(244, 67, 54, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(244, 67, 54, 0.25);
                border: 1px solid rgba(244, 67, 54, 0.4);
            }
        """)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setToolTip("删除步骤")
        
        # 添加处理按钮 - 使用图标，动态根据当前Tab切换功能
        self.add_tool_btn = QPushButton()
        self.add_tool_btn.setFixedSize(28, 28)  # 固定按钮大小，正方形
        self.add_tool_btn.setIcon(self.get_icon("add.png"))
        self.add_tool_btn.setIconSize(QSize(16, 16))
        self.add_tool_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(76, 175, 80, 0.15);
                border: 1px solid rgba(76, 175, 80, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(76, 175, 80, 0.25);
                border: 1px solid rgba(76, 175, 80, 0.4);
            }
        """)
        self.add_tool_btn.setCursor(Qt.PointingHandCursor)
        self.add_tool_btn.setToolTip("添加处理工具")
        self.add_tool_btn.clicked.connect(self.on_add_tool_clicked)
        
        # 连接信号
        self.copy_btn.clicked.connect(self.on_copy_clicked)
        self.status_btn.toggled.connect(self.on_status_changed)
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        
        # 步骤标题容器内部布局：标题 + 操作按钮
        self.header_layout.addWidget(self.step_label)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.copy_btn)
        self.header_layout.addWidget(self.status_btn)
        self.header_layout.addWidget(self.delete_btn)

    def create_interface_display(self):
        """创建接口展示框"""
        self.interface_frame = QFrame()
        self.interface_frame.setFrameStyle(QFrame.NoFrame)  # 隐藏边框
        self.interface_frame.setStyleSheet("""
            QFrame {
                border: none;  /* 隐藏边框 */
                border-radius: 20px;
                background-color: #fff3e0;  /* 浅橙色背景 */
                padding: 4px;
            }
        """)
        
        # 移除整个框架的手型指针，只在接口名称上设置
        
        layout = QHBoxLayout(self.interface_frame)
        
        # 请求方式
        method = self.step_data.get('api_template', {}).get('method', 'GET')
        self.method_label = QLabel(method)
        self.method_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.method_label.setStyleSheet("""
            QLabel {
                color: #1976d2;
                background-color: #e3f2fd;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #bbdefb;
            }
        """)
        
        # 接口名称（可点击跳转）
        # 优先使用api_name字段，如果不存在则从api_template对象获取
        api_name = self.step_data.get('api_name') or self.step_data.get('api_template', {}).get('name', '未命名接口')
        self.api_name_label = QLabel(f"<a href=\"#\" style=\"text-decoration: none; color: #2c3e50; font-weight: 600; font-size: 13px; font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;\">{api_name}</a>")
        self.api_name_label.setFont(QFont("Microsoft YaHei", 12, QFont.DemiBold))
        self.api_name_label.setOpenExternalLinks(False)
        self.api_name_label.setCursor(Qt.PointingHandCursor)  # 只在接口名称上设置手型指针
        self.api_name_label.linkActivated.connect(self.on_api_name_clicked)
        
        layout.addWidget(self.method_label)
        layout.addWidget(self.api_name_label)
        layout.addStretch()
        layout.addWidget(self.add_tool_btn)
        
        # 默认隐藏Tab区域和处理区
        self.is_expanded = False

    def create_tab_area(self):
        """创建Tab区域"""
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: transparent;
                padding: 6px 12px;
                border: none;
                border-bottom: none;
                margin: 0px;
                margin-right: 1px;
                min-width: 60px;
                font-size: 13px;
                color: #666;
                outline: none;
            }
            QTabBar::tab:selected {
                background-color: transparent;
                color: #1976d2;
                border: none;
                border-bottom: 2px solid #1976d2;
                font-weight: bold;
                outline: none;
            }
            QTabBar::tab:selected:hover {
                background-color: transparent;
                color: #1565c0;
                border-bottom: 2px solid #1565c0;
                outline: none;
            }
            QTabBar::tab:hover {
                background-color: transparent;
                color: #333;
                outline: none;
            }
            QTabBar {
                background-color: transparent;
                border: none;
                outline: none;
            }
        """)
        
        # 前置Tab
        self.pre_tab = self.create_pre_tab()
        self.tab_widget.addTab(self.pre_tab, "前置")
        
        # 断言Tab
        self.assertion_tab = self.create_assertion_tab()
        self.tab_widget.addTab(self.assertion_tab, "断言")
        
        # 后置Tab
        self.post_tab = self.create_post_tab()
        self.tab_widget.addTab(self.post_tab, "后置")
        
        # 设置Tab区域固定高度，确保滚动条正常工作
        self.tab_widget.setMinimumHeight(300)
        self.tab_widget.setMaximumHeight(400)

    def create_pre_tab(self):
        """创建前置Tab"""
        from PyQt5.QtWidgets import QScrollArea
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # 创建内容容器
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)  # 减少间距，更紧凑
        layout.setAlignment(Qt.AlignTop)  # 确保工具从顶部开始排列
        
        # 为内容容器添加鼠标移动事件处理
        content_widget.setMouseTracking(True)
        content_widget.installEventFilter(self)
        
        # 设置内容到滚动区域
        scroll_area.setWidget(content_widget)
        
        # 初始化时显示已添加的工具
        self.refresh_pre_tools_display_with_layout(layout)
        
        return scroll_area

    def create_assertion_tab(self):
        """创建断言Tab"""
        from PyQt5.QtWidgets import QScrollArea
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # 创建内容容器
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)  # 减少间距，更紧凑
        layout.setAlignment(Qt.AlignTop)  # 确保工具从顶部开始排列
        
        # 为内容容器添加鼠标移动事件处理
        content_widget.setMouseTracking(True)
        content_widget.installEventFilter(self)
        
        # 设置内容到滚动区域
        scroll_area.setWidget(content_widget)
        
        return scroll_area

    def create_post_tab(self):
        """创建后置Tab"""
        from PyQt5.QtWidgets import QScrollArea
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # 创建内容容器
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)  # 减少间距，更紧凑
        layout.setAlignment(Qt.AlignTop)  # 确保工具从顶部开始排列
        
        # 为内容容器添加鼠标移动事件处理
        content_widget.setMouseTracking(True)
        content_widget.installEventFilter(self)
        
        # 设置内容到滚动区域
        scroll_area.setWidget(content_widget)
        
        return scroll_area

    def create_processing_area(self):
        """创建处理区域"""
        self.processing_frame = QFrame()
        self.processing_frame.setFrameStyle(QFrame.NoFrame)
        
        layout = QVBoxLayout(self.processing_frame)
        
        # 处理区域标题
        title_label = QLabel("处理区域")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        title_label.setStyleSheet("color: #666;")
        
        # 添加工具按钮
        tool_btn = QToolButton()
        tool_btn.setText("+ 添加处理工具")
        tool_btn.setStyleSheet("""
            QToolButton {
                background-color: #fff3e0;
                border: 1px dashed #f57c00;
                color: #f57c00;
                padding: 8px;
                border-radius: 4px;
                font-size: 12px;
            }
            QToolButton:hover {
                background-color: #ffe0b2;
            }
        """)
        
        # 创建菜单
        menu = QMenu(self)
        global_tools = ["全局工具", "断言管理", "后置参数提取", "数据验证", "性能监控"]
        for tool in global_tools:
            menu.addAction(tool)
        
        tool_btn.setMenu(menu)
        tool_btn.setPopupMode(QToolButton.InstantPopup)
        
        layout.addWidget(title_label)
        layout.addWidget(tool_btn)
        layout.addStretch()

    def setup_styles(self):
        """设置样式"""
        self.setStyleSheet("""
            InterfaceStepCard {
                background-color: #fafafa;
                border: 2px solid #d0d0d0;
                border-radius: 10px;
                margin: 6px 0;
                padding: 10px;
            }
            InterfaceStepCard:hover {
                border-color: #1976d2;
                background-color: #f5f5f5;
            }
        """)

    def on_status_changed(self, enabled):
        """状态改变事件"""
        self.step_data['enabled'] = enabled
        
        # 更新按钮图标和提示文本
        if enabled:
            self.status_btn.setIcon(self.get_icon("stop.png"))
            self.status_btn.setToolTip("停用步骤")
        else:
            self.status_btn.setIcon(self.get_icon("start.png"))
            self.status_btn.setToolTip("启用步骤")
            
        self.step_updated.emit(self.step_data)

    def on_delete_clicked(self):
        """删除按钮点击事件"""
        self.step_deleted.emit(self.step_id)

    def on_copy_clicked(self):
        """复制按钮点击事件 - 复制当前步骤"""
        try:
            # 深拷贝步骤数据
            import copy
            copied_step_data = copy.deepcopy(self.step_data)
            
            # 生成新的前端步骤ID（使用UUID）
            import uuid
            copied_step_data['frontend_id'] = str(uuid.uuid4())
            
            # 重置后端ID为None，表示这是新创建的步骤
            copied_step_data['id'] = None
            
            # 修改步骤名称，添加"(副本)"后缀
            if 'name' in copied_step_data:
                copied_step_data['name'] = f"{copied_step_data['name']}(副本)"
            elif 'api_name' in copied_step_data:
                copied_step_data['api_name'] = f"{copied_step_data['api_name']}(副本)"
            
            # 发送复制信号（需要父组件处理实际的复制逻辑）
            # 这里我们发出一个信号，让父组件知道需要复制这个步骤
            self.step_copied.emit(self.step_id, copied_step_data)
            
            # 显示成功提示
            from src.ui.widgets.toast_tips import Toast
            Toast.success(self, "步骤复制成功")
            
        except Exception as e:
            print(f"复制步骤失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"复制步骤失败: {str(e)}")
    
    def on_api_name_clicked(self):
        """接口名称点击事件 - 跳转到对应接口模板编辑tab"""
        # 获取接口模板ID
        # 优先从api_template对象获取ID，如果不存在则从api_template_id字段获取
        api_template_id = self.step_data.get('api_template', {}).get('id') or self.step_data.get('api_template_id')
        if api_template_id:
            # 发送信号通知父组件跳转到接口模板编辑tab
            # 确保api_template_id是字符串类型
            self.api_template_clicked.emit(str(api_template_id))
    
    def on_add_tool_clicked(self):
        """添加处理工具按钮点击事件 - 根据当前Tab决定添加类型"""
        current_tab_index = self.tab_widget.currentIndex()
        
        if current_tab_index == 0:  # 前置处理Tab
            self.show_pre_tool_menu()
        elif current_tab_index == 1:  # 断言Tab
            self.show_assertion_menu()
        elif current_tab_index == 2:  # 后置处理Tab
            self.show_post_tool_menu()
        else:
            print("未知的Tab索引")

    def show_pre_tool_menu(self):
        """显示前置处理工具菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 12px;
                border-radius: 2px;
                color: #333;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QMenu::item:hover {
                background-color: #f5f5f5;
            }
        """)
        
        tools = ["全局工具", "参数提取", "数据准备", "SQL查询", "Python脚本", "HTTP请求"]
        for tool in tools:
            action = menu.addAction(tool)
            action.triggered.connect(lambda checked, tool_name=tool: self.on_pre_tool_selected(tool_name))
        
        # 在添加按钮位置显示菜单
        menu.exec_(self.add_tool_btn.mapToGlobal(QPoint(0, self.add_tool_btn.height())))

    def show_assertion_menu(self):
        """显示断言菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 12px;
                border-radius: 2px;
                color: #333;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #f3e5f5;
                color: #7b1fa2;
            }
            QMenu::item:hover {
                background-color: #f5f5f5;
            }
        """)
        
        assertions = ["状态码断言", "响应时间断言", "JSON路径断言", "正则表达式断言", "XPath断言"]
        for assertion in assertions:
            action = menu.addAction(assertion)
            action.triggered.connect(lambda checked, assertion_name=assertion: self.on_assertion_selected(assertion_name))
        
        menu.exec_(self.add_tool_btn.mapToGlobal(QPoint(0, self.add_tool_btn.height())))

    def show_post_tool_menu(self):
        """显示后置处理工具菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 12px;
                border-radius: 2px;
                color: #333;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #e8f5e8;
                color: #388e3c;
            }
            QMenu::item:hover {
                background-color: #f5f5f5;
            }
        """)
        
        post_tools = ["参数提取", "数据存储", "变量设置", "数据库操作", "文件操作"]
        for tool in post_tools:
            action = menu.addAction(tool)
            action.triggered.connect(lambda checked, tool_name=tool: self.on_post_tool_selected(tool_name))
        
        menu.exec_(self.add_tool_btn.mapToGlobal(QPoint(0, self.add_tool_btn.height())))

    def on_assertion_selected(self, assertion_name):
        """断言工具选择"""
        print(f"选择断言工具: {assertion_name}")
        # 这里可以添加具体的断言添加逻辑

    def on_post_tool_selected(self, tool_name):
        """后置处理工具选择"""
        print(f"选择后置处理工具: {tool_name}")
        # 这里可以添加具体的工具添加逻辑
    
    def on_pre_tool_selected(self, tool_name):
        """前置处理器工具选择事件"""
        if tool_name == "HTTP请求":
            self.add_http_request_tool()
        else:
            # 其他工具的处理逻辑
            print(f"选择了工具: {tool_name}")
    
    def add_http_request_tool(self):
        """添加HTTP请求工具到前置处理器"""
        try:
            # 先创建默认配置，不打开对话框
            if 'pre_processing' not in self.step_data:
                self.step_data['pre_processing'] = {}
            
            # 生成唯一的工具ID
            tool_id = f"http_request_{len(self.step_data.get('pre_processing', {})) + 1}"
            
            # 创建默认配置
            default_config = {
                'type': 'http_request',
                'config': {
                    'name': 'HTTP请求',  # 默认名称
                    'method': 'GET',
                    'url': '',
                    'timeout': 30,
                    'headers': {},
                    'body': '',
                    'variables': {}
                },
                'enabled': True,
                'priority': len(self.step_data.get('pre_processing', {}))  # 添加优先级字段，按添加顺序排序
            }
            
            # 保存默认配置
            self.step_data['pre_processing'][tool_id] = default_config
            
            # 发送更新信号
            self.step_updated.emit(self.step_data)
            
            # 刷新显示
            self.refresh_pre_tools_display()
            
            print(f"HTTP请求工具添加成功: {tool_id}")
        except Exception as e:
            print(f"添加HTTP请求工具失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"添加HTTP请求工具失败: {str(e)}")
    
    def on_http_request_saved(self, config_data):
        """HTTP请求配置保存回调"""
        try:
            # 添加到前置处理器配置中
            if 'pre_processing' not in self.step_data:
                self.step_data['pre_processing'] = {}
            
            # 生成唯一的工具ID
            tool_id = f"http_request_{len(self.step_data.get('pre_processing', {})) + 1}"
            
            # 保存配置
            self.step_data['pre_processing'][tool_id] = {
                'type': 'http_request',
                'config': config_data,
                'enabled': True,
                'priority': len(self.step_data.get('pre_processing', {}))  # 添加优先级字段，按添加顺序排序
            }
            
            # 发送更新信号
            self.step_updated.emit(self.step_data)
            
            # 刷新显示
            self.refresh_pre_tools_display()
            
            print(f"HTTP请求工具添加成功: {tool_id}")
        except Exception as e:
            print(f"保存HTTP请求工具配置失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"保存HTTP请求工具配置失败: {str(e)}")
    
    def refresh_pre_tools_display(self):
        """刷新前置处理器工具显示"""
        # 获取滚动区域内的内容容器的布局
        if hasattr(self.pre_tab, 'widget') and self.pre_tab.widget():
            layout = self.pre_tab.widget().layout()
            self.refresh_pre_tools_display_with_layout(layout)
    
    def refresh_pre_tools_display_with_layout(self, layout):
        """使用指定布局刷新前置处理器工具显示"""
        # 清空现有显示（包括拉伸项）
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            else:
                # 移除拉伸项等非widget项
                layout.removeItem(item)
        
        # 获取前置处理器配置
        pre_processing = self.step_data.get('pre_processing', {})
        
        if not pre_processing:
            # 如果没有工具，显示提示信息
            no_tools_label = QLabel("暂无前置处理工具")
            no_tools_label.setStyleSheet("color: #999; font-style: italic; padding: 10px; font-size: 12px;")
            no_tools_label.setAlignment(Qt.AlignCenter)
            # 添加拉伸项确保居中显示
            layout.addStretch()
            layout.addWidget(no_tools_label)
            layout.addStretch()
            return
        
        # 按照优先级字段对工具进行排序
        sorted_tools = sorted(pre_processing.items(), 
                             key=lambda x: x[1].get('priority', 0))
        
        # 显示已添加的工具（按优先级排序）
        for tool_id, tool_config in sorted_tools:
            if tool_config.get('type') == 'http_request':
                self.add_http_request_tool_widget(tool_id, tool_config, layout)
    
    def refresh_assertion_tools_display(self):
        """刷新断言工具显示"""
        # 获取滚动区域内的内容容器的布局
        if hasattr(self.assertion_tab, 'widget') and self.assertion_tab.widget():
            layout = self.assertion_tab.widget().layout()
            
            # 清空现有显示（包括拉伸项）
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                if item.widget():
                    item.widget().deleteLater()
                else:
                    # 移除拉伸项等非widget项
                    layout.removeItem(item)
            
            # 获取断言配置
            assertions = self.step_data.get('assertions', {})
            
            if not assertions:
                # 如果没有工具，显示提示信息
                no_tools_label = QLabel("暂无断言工具")
                no_tools_label.setStyleSheet("color: #999; font-style: italic; padding: 10px; font-size: 12px;")
                no_tools_label.setAlignment(Qt.AlignCenter)
                # 添加拉伸项确保居中显示
                layout.addStretch()
                layout.addWidget(no_tools_label)
                layout.addStretch()
                return
            
            # 按照优先级字段对工具进行排序
            sorted_tools = sorted(assertions.items(), 
                                 key=lambda x: x[1].get('priority', 0))
            
            # 显示已添加的工具（按优先级排序）
            for tool_id, tool_config in sorted_tools:
                self.add_assertion_tool_widget(tool_id, tool_config, layout)
    
    def refresh_post_tools_display(self):
        """刷新后置处理工具显示"""
        # 获取滚动区域内的内容容器的布局
        if hasattr(self.post_tab, 'widget') and self.post_tab.widget():
            layout = self.post_tab.widget().layout()
            
            # 清空现有显示（包括拉伸项）
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                if item.widget():
                    item.widget().deleteLater()
                else:
                    # 移除拉伸项等非widget项
                    layout.removeItem(item)
            
            # 获取后置处理配置
            post_processing = self.step_data.get('post_processing', {})
            
            if not post_processing:
                # 如果没有工具，显示提示信息
                no_tools_label = QLabel("暂无后置处理工具")
                no_tools_label.setStyleSheet("color: #999; font-style: italic; padding: 10px; font-size: 12px;")
                no_tools_label.setAlignment(Qt.AlignCenter)
                # 添加拉伸项确保居中显示
                layout.addStretch()
                layout.addWidget(no_tools_label)
                layout.addStretch()
                return
            
            # 按照优先级字段对工具进行排序
            sorted_tools = sorted(post_processing.items(), 
                                 key=lambda x: x[1].get('priority', 0))
            
            # 显示已添加的工具（按优先级排序）
            for tool_id, tool_config in sorted_tools:
                self.add_post_tool_widget(tool_id, tool_config, layout)
    
    def add_http_request_tool_widget(self, tool_id, tool_config, parent_layout):
        """添加HTTP请求工具显示组件"""
        # 创建工具卡片
        tool_card = QFrame()
        tool_card.setFrameStyle(QFrame.StyledPanel)
        tool_card.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 2px 4px;
                max-height: 32px;
            }
            QFrame:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
        """)
        
        # 设置工具卡片为可拖动
        tool_card.setProperty("tool_id", tool_id)
        tool_card.setProperty("tool_type", "pre")  # 标记工具类型
        tool_card.setProperty("is_tool_card", True)  # 标记为工具卡片
        tool_card.setAcceptDrops(True)
        tool_card.installEventFilter(self)
        tool_card.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(tool_card)
        layout.setContentsMargins(4, 2, 4, 2)  # 减小边距
        layout.setSpacing(6)  # 减小间距
        
        # 拖拽手柄 - 使用图标
        drag_handle = QLabel()
        drag_handle.setFixedSize(16, 16)
        drag_handle.setText("⋮⋮")
        drag_handle.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 12px;
                font-weight: bold;
                qproperty-alignment: 'AlignCenter';
            }
            QLabel:hover {
                color: #495057;
                background-color: rgba(108, 117, 125, 0.1);
                border-radius: 2px;
            }
        """)
        drag_handle.setCursor(Qt.SizeAllCursor)
        drag_handle.setProperty("is_drag_handle", True)
        drag_handle.setProperty("tool_id", tool_id)
        drag_handle.setProperty("tool_type", "pre")
        drag_handle.installEventFilter(self)
        
        # 工具图标和名称
        icon_label = QLabel()
        # 使用HTTP图标文件
        http_icon_path = os.path.join("src", "resources", "icons", "http.png")
        if os.path.exists(http_icon_path):
            icon_pixmap = QPixmap(http_icon_path).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(icon_pixmap)
        else:
            # 如果图标文件不存在，使用默认emoji
            icon_label.setText("🌐")
            icon_label.setStyleSheet("font-size: 14px;")
        
        config = tool_config.get('config', {})
        name = config.get('name', 'HTTP请求')  # 只显示名称
        
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            font-weight: bold; 
            color: #1976d2;
            font-size: 11px;
        """)
        name_label.setWordWrap(False)
        
        # 复制按钮 - 使用图标
        copy_btn = QPushButton()
        copy_btn.setFixedSize(20, 20)  # 固定按钮大小，正方形
        copy_btn.setIcon(self.get_icon("copy.png"))
        copy_btn.setIconSize(QSize(12, 12))
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(76, 175, 80, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(76, 175, 80, 0.2);
            }
        """)
        copy_btn.setToolTip("复制")
        copy_btn.clicked.connect(lambda checked, tid=tool_id: self.copy_pre_tool(tid))
        
        # 编辑按钮 - 使用图标
        edit_btn = QPushButton()
        edit_btn.setFixedSize(20, 20)  # 固定按钮大小，正方形
        edit_btn.setIcon(self.get_icon("edit.png"))
        edit_btn.setIconSize(QSize(12, 12))
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(25, 118, 210, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(25, 118, 210, 0.2);
            }
        """)
        edit_btn.setToolTip("编辑")
        edit_btn.clicked.connect(lambda checked, tid=tool_id: self.edit_http_request_tool(tid))
        
        # 删除按钮 - 使用图标
        delete_btn = QPushButton()
        delete_btn.setFixedSize(20, 20)  # 固定按钮大小，正方形
        delete_btn.setIcon(self.get_icon("delete.png"))
        delete_btn.setIconSize(QSize(12, 12))
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(244, 67, 54, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(244, 67, 54, 0.2);
            }
        """)
        delete_btn.setToolTip("删除")
        delete_btn.clicked.connect(lambda checked, tid=tool_id: self.delete_pre_tool(tid))
        
        layout.addWidget(drag_handle)
        layout.addWidget(icon_label)
        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(copy_btn)
        layout.addWidget(edit_btn)
        layout.addWidget(delete_btn)
        
        # 将工具卡片直接添加到Tab布局中
        parent_layout.addWidget(tool_card)
        
        # 保存工具卡片引用
        if not hasattr(self, 'pre_tool_widgets'):
            self.pre_tool_widgets = {}
        self.pre_tool_widgets[tool_id] = tool_card
    
    def add_assertion_tool_widget(self, tool_id, tool_config, parent_layout):
        """添加断言工具显示组件"""
        # 创建工具卡片
        tool_card = QFrame()
        tool_card.setFrameStyle(QFrame.StyledPanel)
        tool_card.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 2px 4px;
                max-height: 32px;
            }
            QFrame:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
        """)
        
        # 设置工具卡片为可拖动
        tool_card.setProperty("tool_id", tool_id)
        tool_card.setProperty("tool_type", "assertion")  # 标记工具类型
        tool_card.setProperty("is_tool_card", True)  # 标记为工具卡片
        tool_card.setAcceptDrops(True)
        tool_card.installEventFilter(self)
        tool_card.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(tool_card)
        layout.setContentsMargins(4, 2, 4, 2)  # 减小边距
        layout.setSpacing(6)  # 减小间距
        
        # 拖拽手柄 - 使用图标
        drag_handle = QLabel()
        drag_handle.setFixedSize(16, 16)
        drag_handle.setText("⋮⋮")
        drag_handle.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 12px;
                font-weight: bold;
                qproperty-alignment: 'AlignCenter';
            }
            QLabel:hover {
                color: #495057;
                background-color: rgba(108, 117, 125, 0.1);
                border-radius: 2px;
            }
        """)
        drag_handle.setCursor(Qt.SizeAllCursor)
        drag_handle.setProperty("is_drag_handle", True)
        drag_handle.setProperty("tool_id", tool_id)
        drag_handle.setProperty("tool_type", "assertion")
        drag_handle.installEventFilter(self)
        
        # 工具图标和名称
        icon_label = QLabel("✅")
        icon_label.setStyleSheet("font-size: 14px;")
        
        name = tool_config.get('name', '断言')  # 只显示名称
        
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            font-weight: bold; 
            color: #f57c00;
            font-size: 11px;
        """)
        name_label.setWordWrap(False)
        
        # 复制按钮 - 使用图标
        copy_btn = QPushButton()
        copy_btn.setFixedSize(20, 20)  # 固定按钮大小，正方形
        copy_btn.setIcon(self.get_icon("copy.png"))
        copy_btn.setIconSize(QSize(12, 12))
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(76, 175, 80, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(76, 175, 80, 0.2);
            }
        """)
        copy_btn.setToolTip("复制")
        copy_btn.clicked.connect(lambda checked, tid=tool_id: self.copy_assertion_tool(tid))
        
        # 编辑按钮 - 使用图标
        edit_btn = QPushButton()
        edit_btn.setFixedSize(20, 20)  # 固定按钮大小，正方形
        edit_btn.setIcon(self.get_icon("edit.png"))
        edit_btn.setIconSize(QSize(12, 12))
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(245, 124, 0, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(245, 124, 0, 0.2);
            }
        """)
        edit_btn.setToolTip("编辑")
        edit_btn.clicked.connect(lambda checked, tid=tool_id: self.edit_assertion_tool(tid))
        
        # 删除按钮 - 使用图标
        delete_btn = QPushButton()
        delete_btn.setFixedSize(20, 20)  # 固定按钮大小，正方形
        delete_btn.setIcon(self.get_icon("delete.png"))
        delete_btn.setIconSize(QSize(12, 12))
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(244, 67, 54, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(244, 67, 54, 0.2);
            }
        """)
        delete_btn.setToolTip("删除")
        delete_btn.clicked.connect(lambda checked, tid=tool_id: self.delete_assertion_tool(tid))
        
        layout.addWidget(icon_label)
        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(copy_btn)
        layout.addWidget(edit_btn)
        layout.addWidget(delete_btn)
        
        # 将工具卡片直接添加到Tab布局中
        parent_layout.addWidget(tool_card)
        
        # 保存工具卡片引用
        if not hasattr(self, 'assertion_tool_widgets'):
            self.assertion_tool_widgets = {}
        self.assertion_tool_widgets[tool_id] = tool_card
    
    def add_post_tool_widget(self, tool_id, tool_config, parent_layout):
        """添加后置处理工具显示组件"""
        # 创建工具卡片
        tool_card = QFrame()
        tool_card.setFrameStyle(QFrame.StyledPanel)
        tool_card.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 2px 4px;
                max-height: 32px;
            }
            QFrame:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
        """)
        
        # 设置工具卡片为可拖动
        tool_card.setProperty("tool_id", tool_id)
        tool_card.setProperty("tool_type", "post")  # 标记工具类型
        tool_card.setProperty("is_tool_card", True)  # 标记为工具卡片
        tool_card.setAcceptDrops(True)
        tool_card.installEventFilter(self)
        tool_card.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(tool_card)
        layout.setContentsMargins(4, 2, 4, 2)  # 减小边距
        layout.setSpacing(6)  # 减小间距
        
        # 拖拽手柄 - 使用图标
        drag_handle = QLabel()
        drag_handle.setFixedSize(16, 16)
        drag_handle.setText("⋮⋮")
        drag_handle.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 12px;
                font-weight: bold;
                qproperty-alignment: 'AlignCenter';
            }
            QLabel:hover {
                color: #495057;
                background-color: rgba(108, 117, 125, 0.1);
                border-radius: 2px;
            }
        """)
        drag_handle.setCursor(Qt.SizeAllCursor)
        drag_handle.setProperty("is_drag_handle", True)
        drag_handle.setProperty("tool_id", tool_id)
        drag_handle.setProperty("tool_type", "post")
        drag_handle.installEventFilter(self)
        
        # 工具图标和名称
        icon_label = QLabel("🔧")
        icon_label.setStyleSheet("font-size: 14px;")
        
        name = tool_config.get('name', '后置处理')  # 只显示名称
        
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            font-weight: bold; 
            color: #7b1fa2;
            font-size: 11px;
        """)
        name_label.setWordWrap(False)
        
        # 复制按钮 - 使用图标
        copy_btn = QPushButton()
        copy_btn.setFixedSize(20, 20)  # 固定按钮大小，正方形
        copy_btn.setIcon(self.get_icon("copy.png"))
        copy_btn.setIconSize(QSize(12, 12))
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(76, 175, 80, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(76, 175, 80, 0.2);
            }
        """)
        copy_btn.setToolTip("复制")
        copy_btn.clicked.connect(lambda checked, tid=tool_id: self.copy_post_tool(tid))
        
        # 编辑按钮 - 使用图标
        edit_btn = QPushButton()
        edit_btn.setFixedSize(20, 20)  # 固定按钮大小，正方形
        edit_btn.setIcon(self.get_icon("edit.png"))
        edit_btn.setIconSize(QSize(12, 12))
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(123, 31, 162, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(123, 31, 162, 0.2);
            }
        """)
        edit_btn.setToolTip("编辑")
        edit_btn.clicked.connect(lambda checked, tid=tool_id: self.edit_post_tool(tid))
        
        # 删除按钮 - 使用图标
        delete_btn = QPushButton()
        delete_btn.setFixedSize(20, 20)  # 固定按钮大小，正方形
        delete_btn.setIcon(self.get_icon("delete.png"))
        delete_btn.setIconSize(QSize(12, 12))
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(244, 67, 54, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(244, 67, 54, 0.2);
            }
        """)
        delete_btn.setToolTip("删除")
        delete_btn.clicked.connect(lambda checked, tid=tool_id: self.delete_post_tool(tid))
        
        layout.addWidget(icon_label)
        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(copy_btn)
        layout.addWidget(edit_btn)
        layout.addWidget(delete_btn)
        
        # 将工具卡片直接添加到Tab布局中
        parent_layout.addWidget(tool_card)
        
        # 保存工具卡片引用
        if not hasattr(self, 'post_tool_widgets'):
            self.post_tool_widgets = {}
        self.post_tool_widgets[tool_id] = tool_card
    
    def edit_http_request_tool(self, tool_id):
        """编辑HTTP请求工具"""
        try:
            # 导入HTTP请求对话框
            from src.ui.interface_auto.components.http_request_dialog import HttpRequestDialog
            
            # 获取当前配置
            tool_config = self.step_data['pre_processing'][tool_id]
            request_data = tool_config.get('config', {})
            
            # 创建HTTP请求配置对话框
            dialog = HttpRequestDialog(self, request_data)
            
            # 连接保存信号
            dialog.request_saved.connect(lambda config_data: self.on_http_request_edited(tool_id, config_data))
            
            if dialog.exec_() == HttpRequestDialog.Accepted:
                # 配置数据通过信号传递，这里不需要额外处理
                pass
        except Exception as e:
            print(f"编辑HTTP请求工具失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"编辑HTTP请求工具失败: {str(e)}")
    
    def on_http_request_edited(self, tool_id, config_data):
        """HTTP请求工具编辑回调"""
        try:
            # 更新配置
            self.step_data['pre_processing'][tool_id]['config'] = config_data
            
            # 发送更新信号
            self.step_updated.emit(self.step_data)
            
            # 刷新显示
            self.refresh_pre_tools_display()
            
            print(f"HTTP请求工具编辑成功: {tool_id}")
        except Exception as e:
            print(f"更新HTTP请求工具配置失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"更新HTTP请求工具配置失败: {str(e)}")
    
    def edit_assertion_tool(self, tool_id):
        """编辑断言工具"""
        try:
            # 获取当前配置
            tool_config = self.step_data['assertions'][tool_id]
            
            # 打开编辑对话框
            from src.ui.interface_auto.dialogs.assertion_dialog import AssertionDialog
            dialog = AssertionDialog(self, tool_config)
            
            # 连接保存信号
            dialog.assertion_saved.connect(lambda config_data: self.on_assertion_edited(tool_id, config_data))
            
            if dialog.exec_() == AssertionDialog.Accepted:
                # 配置数据通过信号传递，这里不需要额外处理
                pass
        except Exception as e:
            print(f"编辑断言工具失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"编辑断言工具失败: {str(e)}")
    
    def on_assertion_edited(self, tool_id, new_config):
        """断言工具编辑完成回调"""
        try:
            # 更新工具配置
            self.step_data['assertions'][tool_id] = new_config
            
            # 发送更新信号
            self.step_updated.emit(self.step_data)
            
            # 刷新显示
            self.refresh_assertion_tools_display()
            
            print(f"断言工具编辑成功: {tool_id}")
        except Exception as e:
            print(f"编辑断言工具失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"编辑断言工具失败: {str(e)}")
    
    def edit_post_tool(self, tool_id):
        """编辑后置处理工具"""
        try:
            # 获取当前配置
            tool_config = self.step_data['post_processing'][tool_id]
            
            # 打开编辑对话框
            from src.ui.interface_auto.dialogs.post_processing_dialog import PostProcessingDialog
            dialog = PostProcessingDialog(self, tool_config)
            
            # 连接保存信号
            dialog.processing_saved.connect(lambda config_data: self.on_post_processing_edited(tool_id, config_data))
            
            if dialog.exec_() == PostProcessingDialog.Accepted:
                # 配置数据通过信号传递，这里不需要额外处理
                pass
        except Exception as e:
            print(f"编辑后置处理工具失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"编辑后置处理工具失败: {str(e)}")
    
    def on_post_processing_edited(self, tool_id, new_config):
        """后置处理工具编辑完成回调"""
        try:
            # 更新工具配置
            self.step_data['post_processing'][tool_id] = new_config
            
            # 发送更新信号
            self.step_updated.emit(self.step_data)
            
            # 刷新显示
            self.refresh_post_tools_display()
            
            print(f"后置处理工具编辑成功: {tool_id}")
        except Exception as e:
            print(f"编辑后置处理工具失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"编辑后置处理工具失败: {str(e)}")
    
    def copy_pre_tool(self, tool_id):
        """复制前置处理器工具"""
        try:
            # 获取原始工具配置
            original_config = self.step_data['pre_processing'][tool_id]
            
            # 深拷贝配置
            import copy
            new_config = copy.deepcopy(original_config)
            
            # 生成新的工具ID
            import time
            new_tool_id = f"http_request_{int(time.time() * 1000)}"
            
            # 修改工具名称，添加"(副本)"后缀
            if 'config' in new_config and 'name' in new_config['config']:
                new_config['config']['name'] = f"{new_config['config']['name']}(副本)"
            
            # 更新优先级字段，放在最后
            new_config['priority'] = len(self.step_data.get('pre_processing', {}))
            
            # 添加到前置处理器配置中
            self.step_data['pre_processing'][new_tool_id] = new_config
            
            # 发送更新信号
            self.step_updated.emit(self.step_data)
            
            # 刷新显示
            self.refresh_pre_tools_display()
            
            # 显示成功提示
            from src.ui.widgets.toast_tips import Toast
            Toast.success(self, "工具复制成功")
            
            print(f"工具复制成功: {tool_id} -> {new_tool_id}")
        except Exception as e:
            print(f"复制工具失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"复制工具失败: {str(e)}")
    
    def copy_assertion_tool(self, tool_id):
        """复制断言工具"""
        try:
            # 获取原始工具配置
            original_config = self.step_data['assertions'][tool_id]
            
            # 深拷贝配置
            import copy
            new_config = copy.deepcopy(original_config)
            
            # 生成新的工具ID
            import time
            new_tool_id = f"assertion_{int(time.time() * 1000)}"
            
            # 修改工具名称，添加"(副本)"后缀
            if 'name' in new_config:
                new_config['name'] = f"{new_config['name']}(副本)"
            
            # 更新优先级字段，放在最后
            new_config['priority'] = len(self.step_data.get('assertions', {}))
            
            # 添加到断言配置中
            self.step_data['assertions'][new_tool_id] = new_config
            
            # 发送更新信号
            self.step_updated.emit(self.step_data)
            
            # 刷新显示
            self.refresh_assertion_tools_display()
            
            # 显示成功提示
            from src.ui.widgets.toast_tips import Toast
            Toast.success(self, "断言工具复制成功")
            
            print(f"断言工具复制成功: {tool_id} -> {new_tool_id}")
        except Exception as e:
            print(f"复制断言工具失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"复制断言工具失败: {str(e)}")
    
    def copy_post_tool(self, tool_id):
        """复制后置处理工具"""
        try:
            # 获取原始工具配置
            original_config = self.step_data['post_processing'][tool_id]
            
            # 深拷贝配置
            import copy
            new_config = copy.deepcopy(original_config)
            
            # 生成新的工具ID
            import time
            new_tool_id = f"post_{int(time.time() * 1000)}"
            
            # 修改工具名称，添加"(副本)"后缀
            if 'name' in new_config:
                new_config['name'] = f"{new_config['name']}(副本)"
            
            # 更新优先级字段，放在最后
            new_config['priority'] = len(self.step_data.get('post_processing', {}))
            
            # 添加到后置处理配置中
            self.step_data['post_processing'][new_tool_id] = new_config
            
            # 发送更新信号
            self.step_updated.emit(self.step_data)
            
            # 刷新显示
            self.refresh_post_tools_display()
            
            # 显示成功提示
            from src.ui.widgets.toast_tips import Toast
            Toast.success(self, "后置处理工具复制成功")
            
            print(f"后置处理工具复制成功: {tool_id} -> {new_tool_id}")
        except Exception as e:
            print(f"复制后置处理工具失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"复制后置处理工具失败: {str(e)}")
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理工具卡片的拖动事件"""
        from PyQt5.QtCore import QEvent
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QCursor
        
        if event.type() == QEvent.MouseButtonPress:
            # 只在拖拽手柄上触发工具拖动
            if obj.property("is_drag_handle"):
                self.drag_start_position = event.pos()
                self.dragged_tool_id = obj.property("tool_id")
                self.dragged_tool_type = obj.property("tool_type")
                self.dragged_widget = obj
                return True
            
            # 阻止Tab容器内部的鼠标按下事件传递到步骤卡片
            elif (obj == self.pre_tab or 
                  obj == self.assertion_tab or 
                  obj == self.post_tab):
                # Tab容器内部按下，阻止事件传递
                return True
        
        elif event.type() == QEvent.MouseMove:
            # 处理工具卡片上的拖动
            if (event.buttons() & Qt.LeftButton and 
                hasattr(self, 'dragged_widget') and 
                self.dragged_widget and 
                hasattr(self, 'dragged_tool_id') and 
                self.dragged_tool_id and 
                hasattr(self, 'drag_start_position') and 
                self.drag_start_position is not None and 
                (event.pos() - self.drag_start_position).manhattanLength() > QApplication.startDragDistance()):
                
                # 检查dragged_widget是否仍然有效（防止已被删除的对象）
                try:
                    if not hasattr(self.dragged_widget, 'property'):
                        # 如果widget已被删除，清理拖动状态并返回
                        self.cleanup_drag_state()
                        return False
                except RuntimeError:
                    # 如果widget已被删除，清理拖动状态并返回
                    self.cleanup_drag_state()
                    return False
                
                # 开始拖动
                if not hasattr(self, 'dragging_widget'):
                    self.start_drag(self.dragged_widget, self.dragged_tool_id)
                
                # 更新拖动指示器位置
                self.update_drag_indicator(event.pos())
                return True
            
            # 处理Tab上的鼠标移动（用于更新指示器）
            elif ((obj == self.pre_tab or 
                   obj == self.assertion_tab or 
                   obj == self.post_tab) and 
                  hasattr(self, 'dragging_widget') and 
                  self.dragging_widget):
                self.update_drag_indicator(event.pos())
                return True
        
        elif event.type() == QEvent.MouseButtonRelease:
            if hasattr(self, 'dragged_widget') and self.dragged_widget:
                # 检查dragged_widget是否仍然有效（防止已被删除的对象）
                try:
                    if not hasattr(self.dragged_widget, 'property'):
                        # 如果widget已被删除，清理拖动状态并返回
                        self.cleanup_drag_state()
                        return False
                except RuntimeError:
                    # 如果widget已被删除，清理拖动状态并返回
                    self.cleanup_drag_state()
                    return False
                
                self.end_drag()
                return True
        
        return super().eventFilter(obj, event)
    
    def cleanup_drag_state(self):
        """清理拖动状态，用于处理对象被删除的情况"""
        from PyQt5.QtWidgets import QApplication
        
        # 安全地处理拖动指示器
        if hasattr(self, 'drag_indicator') and self.drag_indicator:
            try:
                # 检查拖动指示器是否仍然有效
                if hasattr(self.drag_indicator, 'deleteLater'):
                    self.drag_indicator.deleteLater()
            except RuntimeError:
                # 如果对象已经被删除，忽略错误
                pass
            self.drag_indicator = None
        
        # 恢复光标
        try:
            QApplication.restoreOverrideCursor()
        except RuntimeError:
            pass
        
        # 清理拖动变量
        if hasattr(self, 'dragged_tool_id'):
            del self.dragged_tool_id
        if hasattr(self, 'dragged_tool_type'):
            del self.dragged_tool_type
        if hasattr(self, 'dragged_widget'):
            del self.dragged_widget
        if hasattr(self, 'dragging_tool_id'):
            del self.dragging_tool_id
        if hasattr(self, 'dragging_widget'):
            del self.dragging_widget
        if hasattr(self, 'dragging_tool_type'):
            del self.dragging_tool_type
        if hasattr(self, 'drag_insert_index'):
            del self.drag_insert_index
        if hasattr(self, 'drag_start_position'):
            del self.drag_start_position
    
    def start_drag(self, widget, tool_id):
        """开始拖动工具"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QCursor
        
        # 检查widget是否仍然有效（防止已被删除的对象）
        if not widget:
            return
        
        # 安全地检查widget是否有效且未被删除
        try:
            if not hasattr(widget, 'property'):
                return
            # 尝试访问widget的属性来检查是否已被删除
            _ = widget.objectName()
        except RuntimeError:
            # 如果widget已被删除，直接返回
            return
        
        # 安全地获取工具类型
        try:
            tool_type = widget.property("tool_type")
        except RuntimeError:
            # 如果widget已被删除，直接返回
            return
        
        # 安全地查找对应的工具卡片（拖拽手柄的父控件）
        try:
            tool_card = widget.parent()
            if not tool_card or not hasattr(tool_card, 'property'):
                return
            # 检查tool_card是否有效
            _ = tool_card.objectName()
        except RuntimeError:
            # 如果tool_card已被删除，直接返回
            return
        
        # 安全地创建拖动指示器
        try:
            parent_widget = tool_card.parentWidget()
            if not parent_widget:
                return
            self.drag_indicator = QFrame(parent_widget)
            self.drag_indicator.setStyleSheet("""
                QFrame {
                    background-color: #2196F3;
                    border: 2px solid #1976D2;
                    border-radius: 4px;
                    height: 4px;
                    margin: 2px 0px;
                }
            """)
            self.drag_indicator.hide()
        except RuntimeError:
            # 如果parent_widget已被删除，直接返回
            return
        
        # 保存拖动信息
        self.dragging_tool_id = tool_id
        self.dragging_widget = tool_card  # 使用工具卡片而不是拖拽手柄
        self.dragging_tool_type = tool_type
        
        # 设置拖动光标
        try:
            QApplication.setOverrideCursor(Qt.ClosedHandCursor)
        except RuntimeError:
            # 如果应用程序状态异常，忽略错误
            pass
        
        # 安全地隐藏原始控件
        try:
            tool_card.setVisible(False)
        except RuntimeError:
            # 如果tool_card已被删除，忽略错误
            pass
    
    def update_drag_indicator(self, pos):
        """更新拖动指示器位置"""
        from PyQt5.QtGui import QCursor
        
        # 安全地检查拖动指示器是否存在且有效
        if not hasattr(self, 'drag_indicator') or not self.drag_indicator:
            return
        
        try:
            # 检查拖动指示器是否仍然有效
            if not hasattr(self.drag_indicator, 'setGeometry'):
                return
        except RuntimeError:
            # 如果对象已经被删除，直接返回
            return
        
        # 根据工具类型选择正确的Tab和布局
        if hasattr(self, 'dragging_tool_type'):
            if self.dragging_tool_type == 'pre':
                tab = self.pre_tab
                # 获取滚动区域内的内容容器的布局
                if hasattr(tab, 'widget') and tab.widget():
                    layout = tab.widget().layout()
                else:
                    return
            elif self.dragging_tool_type == 'assertion':
                tab = self.assertion_tab
                # 获取滚动区域内的内容容器的布局
                if hasattr(tab, 'widget') and tab.widget():
                    layout = tab.widget().layout()
                else:
                    return
            elif self.dragging_tool_type == 'post':
                tab = self.post_tab
                # 获取滚动区域内的内容容器的布局
                if hasattr(tab, 'widget') and tab.widget():
                    layout = tab.widget().layout()
                else:
                    return
            else:
                return
        else:
            return
        
        # 检查布局是否有效
        if layout is None:
            return
        
        # 转换坐标
        container_pos = tab.mapFromGlobal(QCursor.pos())
        
        # 查找插入位置
        insert_index = -1
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                widget_rect = widget.geometry()
                
                # 检查鼠标是否在控件上方
                if container_pos.y() < widget_rect.center().y():
                    insert_index = i
                    break
        
        # 如果没找到插入位置，放在最后
        if insert_index == -1:
            insert_index = layout.count()
        
        # 显示指示器
        if insert_index < layout.count():
            target_widget = layout.itemAt(insert_index).widget()
            if target_widget:
                target_rect = target_widget.geometry()
                try:
                    self.drag_indicator.setGeometry(
                        target_rect.x(), 
                        target_rect.y() - 2, 
                        target_rect.width(), 
                        4
                    )
                except RuntimeError:
                    # 如果拖动指示器已被删除，直接返回
                    return
        else:
            # 放在最后
            if layout.count() > 0:
                last_widget = layout.itemAt(layout.count() - 1).widget()
                if last_widget:
                    last_rect = last_widget.geometry()
                    try:
                        self.drag_indicator.setGeometry(
                            last_rect.x(), 
                            last_rect.bottom() + 2, 
                            last_rect.width(), 
                            4
                        )
                    except RuntimeError:
                        # 如果拖动指示器已被删除，直接返回
                        return
        
        try:
            self.drag_indicator.show()
        except RuntimeError:
            # 如果拖动指示器已被删除，直接返回
            return
        
        self.drag_insert_index = insert_index
    
    def end_drag(self):
        """结束拖动"""
        from PyQt5.QtWidgets import QApplication
        
        if (hasattr(self, 'dragging_widget') and self.dragging_widget and 
            hasattr(self, 'dragging_tool_id') and self.dragging_tool_id):
            # 检查widget是否仍然有效
            if hasattr(self.dragging_widget, 'setVisible'):
                # 恢复控件显示
                self.dragging_widget.setVisible(True)
            
            # 如果指定了插入位置，重新排序
            if hasattr(self, 'drag_insert_index') and self.drag_insert_index >= 0:
                self.reorder_tools(self.dragging_tool_id, self.drag_insert_index)
        
        # 清理拖动状态 - 安全地处理拖动指示器
        if hasattr(self, 'drag_indicator') and self.drag_indicator:
            try:
                # 检查拖动指示器是否仍然有效
                if hasattr(self.drag_indicator, 'deleteLater'):
                    self.drag_indicator.deleteLater()
            except RuntimeError:
                # 如果对象已经被删除，忽略错误
                pass
            self.drag_indicator = None
        
        # 恢复光标
        QApplication.restoreOverrideCursor()
        
        # 清理拖动变量
        if hasattr(self, 'dragging_tool_id'):
            del self.dragging_tool_id
        if hasattr(self, 'dragging_widget'):
            del self.dragging_widget
        if hasattr(self, 'drag_insert_index'):
            del self.drag_insert_index
    
    def reorder_tools(self, tool_id, new_index):
        """重新排序工具"""
        try:
            # 根据工具类型选择正确的配置字段
            if hasattr(self, 'dragging_tool_type'):
                if self.dragging_tool_type == 'pre':
                    tool_config = self.step_data.get('pre_processing', {})
                    config_key = 'pre_processing'
                elif self.dragging_tool_type == 'assertion':
                    tool_config = self.step_data.get('assertions', {})
                    config_key = 'assertions'
                elif self.dragging_tool_type == 'post':
                    tool_config = self.step_data.get('post_processing', {})
                    config_key = 'post_processing'
                else:
                    return
            else:
                return
            
            if tool_id not in tool_config:
                return
            
            # 创建新的有序字典
            new_order = {}
            tool_keys = list(tool_config.keys())
            
            # 移除当前工具
            tool_keys.remove(tool_id)
            
            # 插入到新位置
            if new_index >= len(tool_keys):
                tool_keys.append(tool_id)
            else:
                tool_keys.insert(new_index, tool_id)
            
            # 重新构建配置并更新优先级字段
            for index, key in enumerate(tool_keys):
                tool_config[key]['priority'] = index  # 更新优先级字段
                new_order[key] = tool_config[key]
            
            # 更新配置
            self.step_data[config_key] = new_order
            
            # 发送更新信号
            self.step_updated.emit(self.step_data)
            
            # 刷新显示
            if config_key == 'pre_processing':
                self.refresh_pre_tools_display()
            elif config_key == 'assertions':
                self.refresh_assertion_tools_display()
            elif config_key == 'post_processing':
                self.refresh_post_tools_display()
            
            print(f"工具重新排序成功: {tool_id} -> 位置 {new_index}")
        except Exception as e:
            print(f"工具重新排序失败: {str(e)}")
    
    def delete_pre_tool(self, tool_id):
        """删除前置处理器工具"""
        try:
            # 直接删除工具，不显示确认弹窗
            del self.step_data['pre_processing'][tool_id]
            
            # 发送更新信号
            self.step_updated.emit(self.step_data)
            
            # 刷新显示
            self.refresh_pre_tools_display()
            
            print(f"前置处理工具删除成功: {tool_id}")
        except Exception as e:
            print(f"删除前置处理工具失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"删除前置处理工具失败: {str(e)}")
    
    def delete_assertion_tool(self, tool_id):
        """删除断言工具"""
        try:
            # 直接删除工具，不显示确认弹窗
            del self.step_data['assertions'][tool_id]
            
            # 发送更新信号
            self.step_updated.emit(self.step_data)
            
            # 刷新显示
            self.refresh_assertion_tools_display()
            
            print(f"断言工具删除成功: {tool_id}")
        except Exception as e:
            print(f"删除断言工具失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"删除断言工具失败: {str(e)}")
    
    def delete_post_tool(self, tool_id):
        """删除后置处理工具"""
        try:
            # 直接删除工具，不显示确认弹窗
            del self.step_data['post_processing'][tool_id]
            
            # 发送更新信号
            self.step_updated.emit(self.step_data)
            
            # 刷新显示
            self.refresh_post_tools_display()
            
            print(f"后置处理工具删除成功: {tool_id}")
        except Exception as e:
            print(f"删除后置处理工具失败: {str(e)}")
            from src.ui.widgets.toast_tips import Toast
            Toast.error(self, f"删除后置处理工具失败: {str(e)}")
    


    def get_step_data(self):
        """获取步骤数据"""
        return self.step_data
    
    def update_step_order(self, order):
        """更新步骤序号显示"""
        self.step_data['order'] = order
        self.step_label.setText(f"step{order}")

    def set_draggable(self, draggable=True):
        """设置是否可拖拽"""
        self.setAcceptDrops(draggable)
        if draggable:
            # 设置拖动光标为手掌形状
            self.setCursor(Qt.OpenHandCursor)
        else:
            # 保持普通箭头光标
            self.setCursor(Qt.ArrowCursor)

    def _serialize_step_data(self, step_data):
        """序列化步骤数据，处理datetime对象"""
        from datetime import datetime
        
        def json_serializer(obj):
            """自定义JSON序列化器"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
        
        # 将数据转换为JSON字符串再解析回来，以处理datetime对象
        try:
            json_str = json.dumps(step_data, default=json_serializer)
            return json.loads(json_str)
        except Exception:
            # 如果序列化失败，返回原始数据（可能包含无法序列化的对象）
            return step_data

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            # 检查点击位置是否在允许拖动的区域
            is_allowed = self._is_drag_allowed_position(event.pos())
            print(f"[DEBUG] mousePressEvent: 左键按下，位置: {event.pos()}, 允许拖动: {is_allowed}")
            if is_allowed:
                self.drag_start_position = event.pos()
                print(f"[DEBUG] mousePressEvent: 设置拖动起始位置: {self.drag_start_position}")
            else:
                # 在tab容器内部等禁止拖动区域，不设置拖动起始位置
                self.drag_start_position = None
                print(f"[DEBUG] mousePressEvent: 禁止拖动区域，重置拖动起始位置")
        else:
            print(f"[DEBUG] mousePressEvent: 非左键按下，按钮: {event.button()}")
        super().mousePressEvent(event)
    
    def _is_drag_allowed_position(self, pos):
        """检查点击位置是否允许拖动"""
        # 获取步骤卡片的布局结构
        
        # 1. 检查是否点击在tab容器内部（禁止拖动区域）
        if self.tab_widget and self.tab_widget.isVisible():
            tab_rect = self.tab_widget.geometry()
            if tab_rect.contains(pos):
                # 在tab容器内部，禁止拖动
                print(f"[DEBUG] _is_drag_allowed_position: 点击在tab容器内部，禁止拖动")
                return False
        
        # 2. 检查是否点击在工具条区域（禁止拖动区域）
        # 工具条通常在tab容器内部，但为了安全起见单独检查
        
        # 3. 允许拖动的区域：步骤标题区域、接口展示区域等
        # 检查是否在头部区域（步骤标题、操作按钮等）
        if hasattr(self, 'header_layout') and self.header_layout:
            # 头部区域允许拖动
            header_rect = self.header_layout.geometry()
            if header_rect.contains(pos):
                print(f"[DEBUG] _is_drag_allowed_position: 点击在头部区域，允许拖动")
                return True
        
        # 检查是否在接口展示区域
        if hasattr(self, 'interface_frame') and self.interface_frame:
            interface_rect = self.interface_frame.geometry()
            if interface_rect.contains(pos):
                print(f"[DEBUG] _is_drag_allowed_position: 点击在接口展示区域，允许拖动")
                return True
        
        # 放宽限制：只要不在明确的禁止区域，就允许拖动
        # 这样可以提高拖拽的可用性
        print(f"[DEBUG] _is_drag_allowed_position: 默认区域，允许拖动")
        return True

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if not (event.buttons() & Qt.LeftButton):
            print(f"[DEBUG] mouseMoveEvent: 不是左键拖动，忽略")
            return
            
        if self.drag_start_position is None:
            print(f"[DEBUG] mouseMoveEvent: 没有拖动起始位置，忽略")
            return
            
        # 检查是否移动了足够的距离才开始拖拽
        drag_distance = (event.pos() - self.drag_start_position).manhattanLength()
        print(f"[DEBUG] mouseMoveEvent: 拖动距离: {drag_distance}")
        if drag_distance < 10:
            print(f"[DEBUG] mouseMoveEvent: 拖动距离不足，忽略")
            return
            
        # 检查当前鼠标位置是否在允许拖动的区域
        if not self._is_drag_allowed_position(event.pos()):
            # 如果在禁止拖动区域，重置拖动状态并返回
            print(f"[DEBUG] mouseMoveEvent: 当前位置不允许拖动，重置拖动状态")
            self.drag_start_position = None
            return
            
        print(f"[DEBUG] mouseMoveEvent: 开始拖拽，步骤ID: {self.step_id}")
        
        # 创建拖拽对象
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # 创建拖拽数据，处理datetime对象
        drag_data = {
            'type': 'step_card',
            'step_id': self.step_id,
            'step_data': self._serialize_step_data(self.step_data)
        }
        
        # 将数据转换为JSON格式
        json_data = json.dumps(drag_data)
        print(f"[DEBUG] mouseMoveEvent: 拖拽数据: {json_data}")
        
        # 设置MIME数据
        mime_data.setData('application/x-dnd-step-card', json_data.encode('utf-8'))
        drag.setMimeData(mime_data)
        
        # 设置拖拽时的预览图像
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        # 开始拖拽
        print(f"[DEBUG] mouseMoveEvent: 执行拖拽操作")
        drag.exec_(Qt.MoveAction)
        print(f"[DEBUG] mouseMoveEvent: 拖拽操作完成")
        
        # 清理拖拽状态
        self.drag_start_position = None
        
        # 恢复光标
        try:
            from PyQt5.QtWidgets import QApplication
            QApplication.restoreOverrideCursor()
        except RuntimeError:
            pass

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        print(f"[DEBUG] dragEnterEvent: 接收到拖拽事件，MIME类型: {event.mimeData().formats()}")
        if event.mimeData().hasFormat('application/x-dnd-step-card'):
            print(f"[DEBUG] dragEnterEvent: 检测到步骤卡片拖拽，接受动作")
            event.acceptProposedAction()
            # 添加拖拽进入时的视觉反馈
            self._add_drag_visual_feedback()
        else:
            print(f"[DEBUG] dragEnterEvent: 未检测到步骤卡片拖拽，忽略事件")
            event.ignore()

    def dragMoveEvent(self, event):
        """拖拽移动事件 - 计算目标位置"""
        print(f"[DEBUG] dragMoveEvent: 拖拽移动，位置: {event.pos()}")
        if event.mimeData().hasFormat('application/x-dnd-step-card'):
            print(f"[DEBUG] dragMoveEvent: 检测到步骤卡片拖拽，计算目标位置")
            event.acceptProposedAction()
            # 计算目标位置（不显示光标指示器）
            self._calculate_drop_position(event.pos())
        else:
            print(f"[DEBUG] dragMoveEvent: 未检测到步骤卡片拖拽，忽略事件")
            event.ignore()

    def dragLeaveEvent(self, event):
        """拖拽离开事件 - 清理状态"""
        print(f"[DEBUG] dragLeaveEvent: 拖拽离开卡片")
        # 清理拖拽状态
        self._remove_drag_visual_feedback()
        print(f"[DEBUG] dragLeaveEvent: 清理状态完成")
        event.accept()

    def dropEvent(self, event):
        """放置事件 - 使用前端ID系统进行动态排序和ID重排"""
        print(f"[DEBUG] dropEvent: 开始处理放置事件")
        if event.mimeData().hasFormat('application/x-dnd-step-card'):
            print(f"[DEBUG] dropEvent: 检测到步骤卡片拖拽数据")
            # 解析拖拽数据
            data = event.mimeData().data('application/x-dnd-step-card')
            json_data = data.data().decode('utf-8')
            print(f"[DEBUG] dropEvent: 原始拖拽数据: {json_data}")
            
            try:
                drag_data = json.loads(json_data)
                print(f"[DEBUG] dropEvent: 解析后的拖拽数据: {drag_data}")
                if drag_data.get('type') == 'step_card':
                    # 获取拖拽的步骤ID
                    dragged_step_id = drag_data.get('step_id')
                    print(f"[DEBUG] dropEvent: 拖拽的步骤ID: {dragged_step_id}, 当前卡片步骤ID: {self.step_id}")
                    
                    # 获取当前卡片在布局中的位置
                    parent_layout = self.parent().layout()
                    if parent_layout:
                        print(f"[DEBUG] dropEvent: 父布局存在，布局项数量: {parent_layout.count()}")
                        # 找到拖拽步骤在布局中的位置
                        dragged_index = -1
                        for i in range(parent_layout.count()):
                            widget = parent_layout.itemAt(i).widget()
                            if widget and hasattr(widget, 'step_id'):
                                if widget.step_id == dragged_step_id:
                                    dragged_index = i
                                    print(f"[DEBUG] dropEvent: 找到拖拽步骤在布局中的位置: {dragged_index}")
                                    break
                        
                        # 如果拖拽的步骤ID与当前步骤ID相同，说明是拖拽到自身位置，不处理
                        if dragged_step_id == self.step_id:
                            print(f"[DEBUG] dropEvent: 拖拽到自身位置，忽略")
                            event.ignore()
                            return
                        
                        # 使用新的位置计算逻辑
                        if hasattr(self, 'step_drag_insert_index'):
                            target_index = self.step_drag_insert_index
                            print(f"[DEBUG] dropEvent: 使用新的位置计算逻辑，插入位置: {target_index}")
                        else:
                            # 如果没有计算位置，使用当前卡片位置作为默认
                            target_index = -1
                            for i in range(parent_layout.count()):
                                widget = parent_layout.itemAt(i).widget()
                                if widget == self:
                                    target_index = i
                                    break
                            print(f"[DEBUG] dropEvent: 使用当前卡片位置作为默认: {target_index}")
                        
                        # 如果找到了有效的位置，发送移动信号
                        if dragged_index >= 0 and target_index >= 0:
                            # 如果拖拽到相同位置，不执行移动但也不显示错误
                            if dragged_index == target_index:
                                print(f"[DEBUG] dropEvent: 拖拽到相同位置，无需移动: dragged_index={dragged_index}, target_index={target_index}")
                                # 清理拖拽状态
                                self._remove_drag_visual_feedback()
                                print(f"[DEBUG] dropEvent: 放置完成，清理状态")
                                # 接受事件但忽略动作
                                event.ignore()
                                return
                            else:
                                # 修正插入位置：如果拖拽的卡片在目标位置之前，需要调整索引
                                if dragged_index < target_index:
                                    # 如果拖拽的卡片在目标位置之前，放在目标位置后面时，索引需要减1
                                    if hasattr(self, 'step_drag_insert_before') and not self.step_drag_insert_before:
                                        target_index = target_index - 1
                                        print(f"[DEBUG] dropEvent: 修正插入位置，从 {target_index + 1} 调整为 {target_index}")
                                
                                # 发送新的移动信号，包含前端ID信息
                                print(f"[DEBUG] dropEvent: 发送step_moved信号: dragged_step_id={dragged_step_id}, target_step_id={self.step_id}, from_index={dragged_index}, to_index={target_index}")
                                self.step_moved.emit(dragged_step_id, self.step_id, dragged_index, target_index)
                                event.acceptProposedAction()
                                # 清理拖拽状态
                                self._remove_drag_visual_feedback()
                                print(f"[DEBUG] dropEvent: 放置成功，清理状态")
                                return
                        else:
                            print(f"[DEBUG] dropEvent: 无效的拖拽位置: dragged_index={dragged_index}, target_index={target_index}, dragged_step_id={dragged_step_id}, current_step_id={self.step_id}")
                            # 清理拖拽状态
                            self._remove_drag_visual_feedback()
                            event.ignore()
                            print(f"[DEBUG] dropEvent: 放置失败，清理状态并忽略事件")
                            return
            except Exception as e:
                print(f"[DEBUG] dropEvent: 解析拖拽数据失败: {e}")
        else:
            print(f"[DEBUG] dropEvent: 未检测到步骤卡片拖拽数据")
        
        # 清理拖拽状态
        self._remove_drag_visual_feedback()
        event.ignore()
        print(f"[DEBUG] dropEvent: 放置失败，清理状态并忽略事件")

    def _cleanup_drag_state(self):
        """清理拖拽状态"""
        # 清理插入位置变量
        if hasattr(self, 'step_drag_insert_index'):
            del self.step_drag_insert_index
        if hasattr(self, 'step_drag_target_index'):
            del self.step_drag_target_index
        if hasattr(self, 'step_drag_insert_before'):
            del self.step_drag_insert_before

    def _calculate_drop_position(self, pos):
        """计算放置位置 - 基于卡片中间线左右50%判断"""
        from PyQt5.QtGui import QCursor
        
        # 获取父布局
        parent_layout = self.parent().layout()
        if not parent_layout:
            return
        
        # 转换坐标到父控件
        parent_pos = self.parent().mapFromGlobal(QCursor.pos())
        
        # 查找目标卡片和插入位置
        target_index = -1
        insert_before = True  # 默认插入在卡片前面
        
        for i in range(parent_layout.count()):
            item = parent_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                widget_rect = widget.geometry()
                
                # 检查鼠标是否在当前卡片区域内
                if widget_rect.contains(parent_pos):
                    target_index = i
                    
                    # 计算卡片中间线
                    middle_x = widget_rect.center().x()
                    
                    # 判断鼠标在卡片中间线左侧50%还是右侧50%
                    if parent_pos.x() < middle_x:
                        # 左侧50% - 放在当前卡片前面
                        insert_before = True
                        print(f"[DEBUG] _calculate_drop_position: 鼠标在卡片{i}左侧50%，放在前面")
                    else:
                        # 右侧50% - 放在当前卡片后面
                        insert_before = False
                        print(f"[DEBUG] _calculate_drop_position: 鼠标在卡片{i}右侧50%，放在后面")
                    break
        
        # 如果没找到目标卡片，放在最后
        if target_index == -1:
            target_index = parent_layout.count()
            insert_before = False  # 放在最后面
            print(f"[DEBUG] _calculate_drop_position: 未找到目标卡片，放在最后")
        
        # 计算最终插入位置
        if insert_before:
            # 放在目标卡片前面
            final_insert_index = target_index
        else:
            # 放在目标卡片后面
            final_insert_index = target_index + 1
        
        # 保存插入位置用于drop事件
        self.step_drag_insert_index = final_insert_index
        self.step_drag_target_index = target_index
        self.step_drag_insert_before = insert_before
        
        print(f"[DEBUG] _calculate_drop_position: 目标卡片索引={target_index}, 插入位置={final_insert_index}, 插入方式={'前面' if insert_before else '后面'}")

    def _add_drag_visual_feedback(self):
        """添加拖拽视觉反馈 - 让卡片有挪开的效果"""
        parent_layout = self.parent().layout()
        if not parent_layout:
            return
        
        # 为所有卡片添加拖拽反馈样式
        for i in range(parent_layout.count()):
            item = parent_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'setStyleSheet'):
                    # 保存原始样式
                    if not hasattr(widget, '_original_style'):
                        widget._original_style = widget.styleSheet()
                    
                    # 添加拖拽反馈样式 - 让卡片有轻微的缩放效果
                    widget.setStyleSheet(widget._original_style + """
                        QFrame {
                            border: 2px solid #E0E0E0;
                            margin: 4px 0px;
                        }
                    """)
    
    def _remove_drag_visual_feedback(self):
        """移除拖拽视觉反馈"""
        parent_layout = self.parent().layout()
        if not parent_layout:
            return
        
        # 恢复所有卡片的原始样式
        for i in range(parent_layout.count()):
            item = parent_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, '_original_style') and hasattr(widget, 'setStyleSheet'):
                    widget.setStyleSheet(widget._original_style)