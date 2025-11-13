import os
import json
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
                             QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QGroupBox, QFormLayout,
                             QHeaderView, QInputDialog, QCheckBox, QSpinBox,
                             QListWidget, QListWidgetItem, QSplitter, QToolBar,
                             QAction, QToolButton, QMenu, QApplication, QDateTimeEdit,
                             QProgressBar, QFrame, QScrollArea, QGridLayout,
                             QTableWidget, QTableWidgetItem, QListWidget, QAbstractItemView,
                             QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QDateTime, QMimeData, QPoint
from PyQt5.QtGui import QIcon, QFont, QColor, QDrag, QPixmap, QCursor
from src.core.services.case_folder_service import CaseFolderService
from src.core.services.api_template_service import ApiTemplateService
from src.core.services.api_folder_service import ApiFolderService
from src.core.services.project_service import ProjectService
from src.core.services.test_case_service import TestCaseService
from src.core.models.interface_models import TestCase, TestCaseStep
from src.ui.interface_auto.components.api_card import ApiCard
from src.ui.interface_auto.components.case_editor import CaseEditor
from src.ui.interface_auto.components.tabbed_case_editor import TabbedCaseEditor
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelComboBox, NoWheelTabWidget
from src.utils.interface_utils.variable_manager import get_global_variable_manager
from src.ui.widgets.toast_tips import Toast


class TestCaseDialog(QDialog):
    """测试用例编辑对话框"""

    def __init__(self, parent=None, case_data=None, project_id=None, folder_id=None):
        super().__init__(parent)
        self.case_data = case_data or {}
        self.project_id = project_id
        self.folder_id = folder_id
        self.is_edit = bool(case_data)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑测试用例" if self.is_edit else "新增测试用例")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        # 创建Tab页
        tab_widget = NoWheelTabWidget()

        # 基本信息Tab
        basic_tab = QWidget()
        self.setup_basic_tab(basic_tab)

        # 环境配置Tab
        env_tab = QWidget()
        self.setup_env_tab(env_tab)

        # 变量配置Tab
        vars_tab = QWidget()
        self.setup_vars_tab(vars_tab)

        tab_widget.addTab(basic_tab, "基本信息")
        tab_widget.addTab(env_tab, "环境配置")
        tab_widget.addTab(vars_tab, "变量配置")

        # 按钮布局
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(tab_widget)
        layout.addWidget(button_box)

        # 加载数据
        if self.is_edit:
            self.load_case_data()

    def setup_basic_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 基本信息表单
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入测试用例名称")

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        self.desc_edit.setPlaceholderText("请输入测试用例描述")

        form_layout.addRow("用例名称:", self.name_edit)
        form_layout.addRow("用例描述:", self.desc_edit)

        layout.addLayout(form_layout)
        layout.addStretch()

    def setup_env_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 环境选择
        env_layout = QFormLayout()

        self.env_combo = NoWheelComboBox()
        self.env_combo.addItem("默认环境", 0)
        # 这里可以从数据库加载环境列表
        self.env_combo.addItem("开发环境", 1)
        self.env_combo.addItem("测试环境", 2)
        self.env_combo.addItem("生产环境", 3)

        env_layout.addRow("测试环境:", self.env_combo)

        layout.addLayout(env_layout)
        layout.addStretch()

    def setup_vars_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 全局变量配置
        vars_group = QGroupBox("全局变量配置")
        vars_layout = QVBoxLayout(vars_group)

        self.vars_text = QTextEdit()
        self.vars_text.setPlaceholderText(
            '请输入JSON格式的全局变量，例如: {"base_url": "https://api.example.com", "token": "your_token"}')
        self.vars_text.setMaximumHeight(200)

        vars_layout.addWidget(QLabel("全局变量 (JSON格式):"))
        vars_layout.addWidget(self.vars_text)

        # 变量管理器按钮
        vars_btn_layout = QHBoxLayout()
        self.vars_manager_btn = QPushButton("打开变量管理器")
        self.vars_manager_btn.clicked.connect(self.open_variable_manager)
        vars_btn_layout.addWidget(self.vars_manager_btn)
        vars_btn_layout.addStretch()

        vars_layout.addLayout(vars_btn_layout)

        layout.addWidget(vars_group)
        layout.addStretch()

    def load_case_data(self):
        """加载用例数据到表单"""
        if not self.case_data:
            return

        # 基本信息
        self.name_edit.setText(self.case_data.get('name', ''))
        self.desc_edit.setText(self.case_data.get('description', ''))

        # 环境
        env_id = self.case_data.get('environment_id')
        if env_id:
            index = self.env_combo.findData(env_id)
            if index >= 0:
                self.env_combo.setCurrentIndex(index)

        # 全局变量
        global_vars = self.case_data.get('global_vars', {})
        if global_vars:
            self.vars_text.setText(json.dumps(global_vars, indent=2, ensure_ascii=False))

    def get_data(self):
        """获取表单数据"""
        # 基本信息
        data = {
            'name': self.name_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip(),
            'project_id': self.project_id or self.case_data.get('project_id'),
            'folder_id': self.folder_id or self.case_data.get('folder_id'),
            'environment_id': self.env_combo.currentData()
        }

        # 全局变量
        vars_text = self.vars_text.toPlainText().strip()
        if vars_text:
            try:
                data['global_vars'] = json.loads(vars_text)
            except json.JSONDecodeError:
                # 如果不是有效的JSON，作为字符串处理
                data['global_vars'] = vars_text
        else:
            data['global_vars'] = {}

        return data

    def open_variable_manager(self):
        """打开变量管理器"""
        from src.ui.interface_auto.components.variable_editor import VariableManagerDialog
        dialog = VariableManagerDialog(self)
        dialog.exec_()


class CaseFolderDialog(QDialog):
    """用例文件夹编辑对话框"""

    def __init__(self, parent=None, folder_data=None, project_id=None, parent_folder_id=None):
        super().__init__(parent)
        self.folder_data = folder_data or {}
        self.project_id = project_id
        self.parent_folder_id = parent_folder_id
        self.is_edit = bool(folder_data)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑文件夹" if self.is_edit else "新增文件夹")
        self.setFixedSize(400, 200)

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入文件夹名称")
        if self.folder_data:
            self.name_edit.setText(self.folder_data.get('name', ''))

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(60)
        self.desc_edit.setPlaceholderText("请输入文件夹描述")
        if self.folder_data:
            self.desc_edit.setText(self.folder_data.get('description', ''))

        form_layout.addRow("文件夹名称:", self.name_edit)
        form_layout.addRow("文件夹描述:", self.desc_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(button_box)

    def get_data(self):
        return {
            'name': self.name_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip(),
            'project_id': self.project_id or self.folder_data.get('project_id'),
            'parent_id': self.parent_folder_id or self.folder_data.get('parent_id')
        }


class DraggableCaseTreeWidget(QTreeWidget):
    """可拖拽的测试用例树控件（完全复用api_template.py的拖拽功能）"""
    item_dragged = pyqtSignal(QTreeWidgetItem, QTreeWidgetItem)  # 拖拽信号
    item_dragged_with_position = pyqtSignal(QTreeWidgetItem, QTreeWidgetItem, QTreeWidgetItem, str)  # 带位置的拖拽信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeWidget.InternalMove)

    def startDrag(self, supportedActions):
        """开始拖拽"""
        items = self.selectedItems()
        if not items:
            return

        drag = QDrag(self)
        mime_data = QMimeData()

        # 设置拖拽数据
        item_data = {
            'type': items[0].data(0, Qt.UserRole)['type'],
            'id': items[0].data(0, Qt.UserRole)['data']['id']
        }
        mime_data.setText(json.dumps(item_data))

        # 创建拖拽预览
        pixmap = QPixmap(100, 30)
        pixmap.fill(QColor(200, 200, 200, 180))
        drag.setPixmap(pixmap)
        drag.setMimeData(mime_data)
        drag.exec_(Qt.MoveAction)

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.setDropIndicatorShown(True)
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            
            # 更新拖拽指示器
            target_item = self.itemAt(event.pos())
            if target_item:
                # 设置正确的拖拽指示器位置
                rect = self.visualItemRect(target_item)
                if event.pos().y() < rect.top() + rect.height() / 3:
                    # 拖拽到项的上方
                    self.setDropIndicatorShown(True)
                    self.setDragDropMode(QTreeWidget.DragDrop)
                elif event.pos().y() > rect.bottom() - rect.height() / 3:
                    # 拖拽到项的下方
                    self.setDropIndicatorShown(True)
                    self.setDragDropMode(QTreeWidget.DragDrop)
                else:
                    # 拖拽到项中间（作为子项）
                    self.setDropIndicatorShown(True)
                    self.setDragDropMode(QTreeWidget.DragDrop)
            else:
                self.setDropIndicatorShown(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """拖拽离开事件"""
        self.setDropIndicatorShown(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        """拖拽释放事件"""
        if not event.mimeData().hasText():
            event.ignore()
            return

        try:
            # 解析拖拽数据
            drag_data = json.loads(event.mimeData().text())
            drag_type = drag_data['type']
            drag_id = drag_data['id']

            # 获取目标位置
            target_item = self.itemAt(event.pos())
            
            if not target_item:
                # 如果拖拽到空白区域，则放到根节点
                self.handle_drop_to_root(drag_type, drag_id)
            else:
                # 获取目标项的类型
                target_data = target_item.data(0, Qt.UserRole)
                target_type = target_data['type']
                
                # 确定拖拽位置（上方、中间、下方）- 使用更精确的检测逻辑
                rect = self.visualItemRect(target_item)
                drop_position = None
                item_height = rect.height()
                relative_y = event.pos().y() - rect.top()
                
                # 使用更精确的比例划分：上方25%，中间50%，下方25%
                if relative_y < item_height * 0.25:
                    drop_position = 'above'
                elif relative_y > item_height * 0.75:
                    drop_position = 'below'
                else:
                    drop_position = 'on'
                
                if target_type == 'folder':
                    if drop_position == 'on':
                        # 拖拽到文件夹内部
                        self.handle_drop_to_folder(drag_type, drag_id, target_data['data']['id'])
                    else:
                        # 拖拽到文件夹的上方或下方，则放到同一层级
                        parent_item = target_item.parent()
                        if parent_item:
                            parent_data = parent_item.data(0, Qt.UserRole)
                            self.handle_drop_to_folder_with_position(drag_type, drag_id, parent_data['data']['id'], target_data['data']['id'], drop_position)
                        else:
                            self.handle_drop_to_root_with_position(drag_type, drag_id, target_data['data']['id'], drop_position)
                else:
                    # 拖拽到测试用例
                    parent_item = target_item.parent()
                    if parent_item:
                        parent_data = parent_item.data(0, Qt.UserRole)
                        self.handle_drop_to_folder_with_position(drag_type, drag_id, parent_data['data']['id'], target_data['data']['id'], drop_position)
                    else:
                        self.handle_drop_to_root_with_position(drag_type, drag_id, target_data['data']['id'], drop_position)

            # 拖拽完成后隐藏指示器
            self.setDropIndicatorShown(False)
            event.acceptProposedAction()
            
        except Exception as e:
            print(f"拖拽处理失败: {e}")
            self.setDropIndicatorShown(False)
            event.ignore()

    def handle_drop_to_root(self, drag_type, drag_id):
        """处理拖拽到根节点"""
        if drag_type == 'case':
            # 发出拖拽信号，让父组件处理
            source_item = self.find_item_by_id(drag_id, drag_type)
            if source_item:
                self.item_dragged.emit(source_item, None)

    def handle_drop_to_folder(self, drag_type, drag_id, folder_id):
        """处理拖拽到文件夹"""
        if drag_type == 'case':
            # 发出拖拽信号，让父组件处理
            source_item = self.find_item_by_id(drag_id, drag_type)
            target_item = self.find_item_by_id(folder_id, 'folder')
            if source_item and target_item:
                self.item_dragged.emit(source_item, target_item)

    def handle_drop_to_root_with_position(self, drag_type, drag_id, target_id, drop_position):
        """处理带位置的拖拽到根节点"""
        if drag_type == 'case':
            # 发出带位置的拖拽信号
            source_item = self.find_item_by_id(drag_id, drag_type)
            target_item = self.find_item_by_id(target_id, 'case')
            if source_item and target_item:
                # 传递目标项和位置信息（根节点没有文件夹，所以传递None）
                self.item_dragged_with_position.emit(source_item, None, target_item, drop_position)

    def handle_drop_to_folder_with_position(self, drag_type, drag_id, folder_id, target_id, drop_position):
        """处理带位置的拖拽到文件夹"""
        if drag_type == 'case':
            # 发出带位置的拖拽信号
            source_item = self.find_item_by_id(drag_id, drag_type)
            folder_item = self.find_item_by_id(folder_id, 'folder')
            target_item = self.find_item_by_id(target_id, 'case')
            if source_item and folder_item and target_item:
                # 传递文件夹、目标项和位置信息
                self.item_dragged_with_position.emit(source_item, folder_item, target_item, drop_position)

    def find_item_by_id(self, item_id, item_type):
        """根据ID和类型查找树项"""
        def search_item(parent_item):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                data = child.data(0, Qt.UserRole)
                if data and data['type'] == item_type and data['data']['id'] == item_id:
                    return child
                
                # 递归搜索子项
                result = search_item(child)
                if result:
                    return result
            return None

        # 从根节点开始搜索
        for i in range(self.topLevelItemCount()):
            top_item = self.topLevelItem(i)
            data = top_item.data(0, Qt.UserRole)
            if data and data['type'] == item_type and data['data']['id'] == item_id:
                return top_item
            
            result = search_item(top_item)
            if result:
                return result
        
        return None


class DraggableListWidget(QListWidget):
    """可拖拽的列表控件"""
    item_dragged = pyqtSignal(QListWidgetItem)  # 拖拽信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def startDrag(self, supportedActions):
        """开始拖拽"""
        items = self.selectedItems()
        if not items:
            return

        drag = QDrag(self)
        mime_data = QMimeData()

        # 设置拖拽数据
        item_data = {
            'type': 'api_template',
            'id': items[0].data(Qt.UserRole)['id'],
            'name': items[0].text()
        }
        mime_data.setText(json.dumps(item_data))

        # 创建拖拽预览
        pixmap = QPixmap(150, 30)
        pixmap.fill(QColor(200, 200, 200, 180))
        drag.setPixmap(pixmap)
        drag.setMimeData(mime_data)
        drag.exec_(Qt.CopyAction)


class DropArea(QFrame):
    """拖拽放置区域"""
    item_dropped = pyqtSignal(dict)  # 放置信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            DropArea {
                border: 2px dashed #ccc;
                border-radius: 5px;
                background-color: #f9f9f9;
                min-height: 100px;
            }
            DropArea:hover {
                border-color: #4CAF50;
                background-color: #f0f9f0;
            }
        """)

        layout = QVBoxLayout(self)
        self.placeholder_label = QLabel("拖拽接口到这里添加测试步骤")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #999; font-style: italic;")
        layout.addWidget(self.placeholder_label)

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """放置事件"""
        if event.mimeData().hasText():
            try:
                data = json.loads(event.mimeData().text())
                self.item_dropped.emit(data)
                event.acceptProposedAction()
            except json.JSONDecodeError:
                event.ignore()


class TestCaseManager(QWidget):
    """测试用例管理页面"""
    data_changed = pyqtSignal()  # 数据变化信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.case_service = None
        self.api_service = None
        self.project_service = None
        self.folder_service = None
        self.current_project = None
        self.current_folder = None
        self.current_case = None
        self.current_case_data = None
        self.init_ui()
        # 延迟加载数据，避免启动时数据库连接失败导致弹窗
        QTimer.singleShot(100, self.delayed_load_data)

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：项目选择和用例树
        left_widget = QWidget()
        left_widget.setMaximumWidth(400)
        left_layout = QVBoxLayout(left_widget)

        # 项目选择
        project_layout = QHBoxLayout()
        project_layout.addWidget(QLabel("选择项目:"))
        self.project_combo = NoWheelComboBox()
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        project_layout.addWidget(self.project_combo)
        
        # 新建文件夹图标 - 放在下拉框后面
        self.new_folder_icon = QLabel()
        self.new_folder_icon.setPixmap(QIcon(os.path.join("src", "resources", "icons", "add_folder.png")).pixmap(24, 24))
        self.new_folder_icon.setToolTip("新建文件夹")
        self.new_folder_icon.mousePressEvent = lambda event: self.create_new_folder()
        self.new_folder_icon.setCursor(Qt.PointingHandCursor)
        project_layout.addWidget(self.new_folder_icon)
        
        # 删除文件夹图标
        self.del_folder_icon = QLabel()
        self.del_folder_icon.setPixmap(QIcon(os.path.join("src", "resources", "icons", "del_folder.png")).pixmap(24, 24))
        self.del_folder_icon.setToolTip("删除文件夹")
        self.del_folder_icon.mousePressEvent = lambda event: self.delete_selected_folder()
        self.del_folder_icon.setCursor(Qt.PointingHandCursor)
        project_layout.addWidget(self.del_folder_icon)
        
        project_layout.addStretch()

        # 刷新项目列表按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setIcon(self.get_icon("refresh.png"))
        self.refresh_btn.clicked.connect(self.refresh_project_list)
        project_layout.addWidget(self.refresh_btn)

        left_layout.addLayout(project_layout)

        # 测试用例搜索框
        case_search_layout = QHBoxLayout()
        case_search_icon_label = QLabel()
        case_search_icon_label.setPixmap(QIcon(os.path.join("src", "resources", "icons", "search.png")).pixmap(16, 16))
        case_search_layout.addWidget(case_search_icon_label)
        self.case_search_edit = QLineEdit()
        self.case_search_edit.setPlaceholderText("搜索测试用例名称...")
        self.case_search_edit.textChanged.connect(self.filter_test_cases)
        case_search_layout.addWidget(self.case_search_edit)
        left_layout.addLayout(case_search_layout)

        # 测试用例树
        self.case_tree = DraggableCaseTreeWidget()
        self.case_tree.setHeaderLabels(["测试用例"])
        self.case_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.case_tree.item_dragged.connect(self.on_case_dragged)
        self.case_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        self.case_tree.itemClicked.connect(self.on_tree_item_clicked)
        left_layout.addWidget(self.case_tree)

        # 中间：接口模板树形结构
        middle_widget = QWidget()
        middle_widget.setMaximumWidth(350)
        middle_layout = QVBoxLayout(middle_widget)

        # 接口模板搜索
        search_layout = QHBoxLayout()
        search_icon_label = QLabel()
        search_icon_label.setPixmap(QIcon(os.path.join("src", "resources", "icons", "search.png")).pixmap(16, 16))
        search_layout.addWidget(search_icon_label)
        self.api_search_edit = QLineEdit()
        self.api_search_edit.setPlaceholderText("输入接口名称或描述...")
        self.api_search_edit.textChanged.connect(self.filter_api_templates)
        search_layout.addWidget(self.api_search_edit)
        middle_layout.addLayout(search_layout)

        # 接口模板树形结构
        self.api_tree = QTreeWidget()
        self.api_tree.setHeaderLabels(["接口模板"])
        self.api_tree.setDragEnabled(True)  # 启用拖拽
        self.api_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.api_tree.itemClicked.connect(self.on_api_tree_item_clicked)
        
        # 设置拖拽模式 - 只允许拖拽，不允许放置
        self.api_tree.setDragDropMode(QAbstractItemView.DragOnly)
        
        middle_layout.addWidget(self.api_tree)

        # 右侧：用例编辑器
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 多标签页用例编辑器
        self.tabbed_case_editor = TabbedCaseEditor(self)
        self.tabbed_case_editor.tab_closed.connect(self.on_tab_closed)
        # 连接保存信号
        self.tabbed_case_editor.saved.connect(self.on_case_saved)
        right_layout.addWidget(self.tabbed_case_editor)

        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(middle_widget)
        splitter.addWidget(right_widget)

        # 设置分割比例
        splitter.setSizes([300, 300, 600])

        main_layout.addWidget(splitter)

        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
            }
        """)

    def delayed_load_data(self):
        """延迟加载数据，避免启动时数据库连接失败导致弹窗"""
        try:
            # 初始化服务对象
            self.case_service = TestCaseService()
            self.api_service = ApiTemplateService()
            self.project_service = ProjectService()
            self.folder_service = CaseFolderService()
            self.api_folder_service = ApiFolderService()
            # 加载数据
            self.load_projects()
        except Exception as e:
            # 静默处理，不显示弹窗
            print(f"延迟加载数据失败: {str(e)}")

    def get_icon(self, icon_name):
        """获取图标"""
        try:
            # 使用相对路径访问图标资源
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            icon_path = os.path.join(base_dir, "src", "resources", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
        except:
            pass
        return QIcon()

    def get_api_icon_by_method(self, method):
        """根据HTTP方法获取对应的API图标"""
        method = method.upper() if method else "GET"
        icon_map = {
            "GET": "http_get.png",
            "POST": "http_post.png", 
            "PUT": "http_put.png",
            "DELETE": "http_del.png"
        }
        icon_name = icon_map.get(method, "api.png")
        return self.get_icon(icon_name)

    def load_projects(self):
        """加载项目列表"""
        # 检查服务对象是否已初始化
        if self.project_service is None:
            print("项目服务未初始化，跳过加载项目列表")
            return
            
        try:
            projects = self.project_service.get_all_projects()
            self.project_combo.clear()
            for project in projects:
                self.project_combo.addItem(project['name'], project['id'])

            if projects:
                self.current_project = projects[0]['id']
                self.load_case_tree()
                self.load_api_templates()

        except Exception as e:
            # 静默处理，不显示弹窗
            print(f"加载项目列表失败: {str(e)}")

    def refresh_project_list(self):
        """刷新项目下拉列表"""
        # 检查服务对象是否已初始化
        if self.project_service is None:
            print("项目服务未初始化，跳过刷新项目列表")
            return
            
        try:
            # 保存当前选中的项目
            current_project_id = self.current_project

            # 重新加载项目列表
            projects = self.project_service.get_all_projects()
            self.project_combo.clear()

            for project in projects:
                self.project_combo.addItem(project['name'], project['id'])

            # 尝试恢复之前选中的项目
            if current_project_id:
                index = self.project_combo.findData(current_project_id)
                if index >= 0:
                    self.project_combo.setCurrentIndex(index)
                elif self.project_combo.count() > 0:
                    # 如果之前的项目不存在了，选择第一个项目
                    self.project_combo.setCurrentIndex(0)
                    self.current_project = self.project_combo.currentData()
                    self.load_case_tree()
                    self.load_api_templates()
            elif self.project_combo.count() > 0:
                # 如果没有之前选中的项目，选择第一个
                self.project_combo.setCurrentIndex(0)
                self.current_project = self.project_combo.currentData()
                self.load_case_tree()
                self.load_api_templates()

        except Exception as e:
            # 静默处理，不显示弹窗
            print(f"刷新项目列表失败: {str(e)}")

    def on_project_changed(self, index):
        """项目选择变化"""
        if index >= 0:
            self.current_project = self.project_combo.currentData()
            self.current_folder = None
            self.current_case = None
            self.current_case_data = None
            # 多标签页编辑器不需要清空
            self.load_case_tree()
            self.load_api_templates()
            
            # 更新删除文件夹图标的启用状态
            self.update_delete_folder_icon_state()

    def create_new_folder(self):
        """新建文件夹"""
        if not self.current_project:
            Toast.warning(self, "请先选择项目")
            return

        dialog = CaseFolderDialog(self, project_id=self.current_project, parent_folder_id=None)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warning(self, "文件夹名称不能为空")
                return

            try:
                self.folder_service.create_folder(data)
                self.load_case_tree()
                Toast.success(self, "文件夹创建成功")
            except Exception as e:
                Toast.error(self, f"创建文件夹失败: {str(e)}")

    def load_case_tree(self):
        """加载用例树"""
        self.case_tree.clear()

        if not self.current_project:
            return

        try:
            # 加载文件夹
            folders = self.folder_service.get_folders_by_project(self.current_project)
            folder_map = {}

            # 先创建所有文件夹项
            for folder in folders:
                folder_item = QTreeWidgetItem()
                folder_item.setText(0, folder['name'])
                folder_item.setData(0, Qt.UserRole, {'type': 'folder', 'data': folder})
                folder_item.setIcon(0, self.get_icon("folder.png"))

                folder_map[folder['id']] = folder_item

                # 如果是根文件夹，添加到树中
                if not folder['parent_id']:
                    self.case_tree.addTopLevelItem(folder_item)
                else:
                    # 添加到父文件夹
                    parent_item = folder_map.get(folder['parent_id'])
                    if parent_item:
                        parent_item.addChild(folder_item)

            # 加载测试用例
            cases = self.case_service.get_cases_by_project(self.current_project)
            for case in cases:
                case_item = QTreeWidgetItem()
                case_item.setText(0, case['name'])
                case_item.setData(0, Qt.UserRole, {'type': 'case', 'data': case})
                case_item.setIcon(0, self.get_icon("test_case.png"))

                # 添加到对应文件夹
                folder_id = case.get('folder_id')
                if folder_id and folder_id in folder_map:
                    folder_map[folder_id].addChild(case_item)
                else:
                    # 添加到根节点
                    self.case_tree.addTopLevelItem(case_item)

            # 展开所有文件夹
            self.case_tree.expandAll()

        except Exception as e:
                Toast.error(self, f"加载用例树失败: {str(e)}")

    def load_api_templates(self):
        """加载接口模板树形结构"""
        try:
            if not self.current_project:
                return

            # 清空树形结构
            self.api_tree.clear()

            # 加载接口模板文件夹
            folders = self.api_folder_service.get_folders_by_project(self.current_project)
            
            # 加载接口模板
            templates = self.api_service.get_templates_by_project(self.current_project)
            
            # 创建文件夹映射
            folder_map = {}
            
            # 先创建所有文件夹项
            for folder in folders:
                folder_item = QTreeWidgetItem()
                folder_item.setText(0, folder['name'])
                folder_item.setData(0, Qt.UserRole, {'type': 'folder', 'data': folder})
                
                # 设置文件夹图标
                folder_item.setIcon(0, self.get_icon("folder.png"))
                
                folder_map[folder['id']] = folder_item
                
                # 如果是根文件夹，添加到树中
                if not folder['parent_id']:
                    self.api_tree.addTopLevelItem(folder_item)
                else:
                    # 添加到父文件夹
                    parent_item = folder_map.get(folder['parent_id'])
                    if parent_item:
                        parent_item.addChild(folder_item)
            
            # 添加接口模板到对应文件夹
            for template in templates:
                template_item = QTreeWidgetItem()
                template_item.setText(0, template['name'])
                template_item.setData(0, Qt.UserRole, {'type': 'template', 'data': template})
                template_item.setToolTip(0, f"{template['method']} {template['url_path']}\n{template.get('description', '')}")
                
                # 设置接口模板图标（根据HTTP方法动态设置）
                template_item.setIcon(0, self.get_api_icon_by_method(template.get('method')))
                
                # 添加到对应文件夹
                folder_id = template.get('folder_id')
                if folder_id and folder_id in folder_map:
                    folder_map[folder_id].addChild(template_item)
                else:
                    # 添加到根节点
                    self.api_tree.addTopLevelItem(template_item)
            
            # 展开所有文件夹
            self.api_tree.expandAll()

        except Exception as e:
                Toast.error(self, f"加载接口模板树形结构失败: {str(e)}")

    def filter_api_templates(self):
        """过滤接口模板树形结构（仅对接口模板名称做搜索，保持文件夹层级关系）"""
        search_text = self.api_search_edit.text().lower()
        
        # 如果没有搜索文本，显示所有内容
        if not search_text:
            self.load_api_templates()
            return
        
        # 重新加载数据并手动过滤
        try:
            if not self.current_project:
                return

            # 清空树形结构
            self.api_tree.clear()

            # 加载接口模板文件夹
            folders = self.api_folder_service.get_folders_by_project(self.current_project)
            
            # 加载接口模板
            templates = self.api_service.get_templates_by_project(self.current_project)
            
            # 创建文件夹映射
            folder_map = {}
            
            # 先创建所有文件夹项（搜索时显示所有文件夹以保持层级关系）
            for folder in folders:
                folder_item = QTreeWidgetItem()
                folder_item.setText(0, folder['name'])
                folder_item.setData(0, Qt.UserRole, {'type': 'folder', 'data': folder})
                
                # 设置文件夹图标
                folder_item.setIcon(0, self.get_icon("folder.png"))
                
                folder_map[folder['id']] = folder_item
                
                # 如果是根文件夹，添加到树中
                if not folder['parent_id']:
                    self.api_tree.addTopLevelItem(folder_item)
                else:
                    # 添加到父文件夹
                    parent_item = folder_map.get(folder['parent_id'])
                    if parent_item:
                        parent_item.addChild(folder_item)
            
            # 添加匹配的接口模板到对应文件夹（仅对接口模板名称做模糊搜索）
            for template in templates:
                # 仅对接口模板名称做模糊搜索
                if search_text in template['name'].lower():
                    template_item = QTreeWidgetItem()
                    template_item.setText(0, template['name'])
                    template_item.setData(0, Qt.UserRole, {'type': 'template', 'data': template})
                    template_item.setToolTip(0, f"{template['method']} {template['url_path']}\n{template.get('description', '')}")
                    
                    # 设置接口模板图标（根据HTTP方法动态设置）
                    template_item.setIcon(0, self.get_api_icon_by_method(template.get('method')))
                    
                    # 添加到对应文件夹
                    folder_id = template.get('folder_id')
                    if folder_id and folder_id in folder_map:
                        folder_map[folder_id].addChild(template_item)
                    else:
                        # 添加到根节点
                        self.api_tree.addTopLevelItem(template_item)
            
            # 展开所有文件夹
            self.api_tree.expandAll()

        except Exception as e:
            Toast.warning(self, f"搜索接口模板失败: {str(e)}")

    def filter_test_cases(self):
        """过滤测试用例树形结构（仅对测试用例名称做搜索）"""
        search_text = self.case_search_edit.text().lower()
        
        # 如果没有搜索文本，显示所有内容
        if not search_text:
            self.load_case_tree()
            return
        
        # 重新加载数据并手动过滤
        try:
            if not self.current_project:
                return

            # 清空树形结构
            self.case_tree.clear()

            # 加载文件夹
            folders = self.folder_service.get_folders_by_project(self.current_project)
            folder_map = {}

            # 先创建所有文件夹项（搜索时显示所有文件夹以保持层级关系）
            for folder in folders:
                folder_item = QTreeWidgetItem()
                folder_item.setText(0, folder['name'])
                folder_item.setData(0, Qt.UserRole, {'type': 'folder', 'data': folder})
                folder_item.setIcon(0, self.get_icon("folder.png"))

                folder_map[folder['id']] = folder_item

                # 如果是根文件夹，添加到树中
                if not folder['parent_id']:
                    self.case_tree.addTopLevelItem(folder_item)
                else:
                    # 添加到父文件夹
                    parent_item = folder_map.get(folder['parent_id'])
                    if parent_item:
                        parent_item.addChild(folder_item)

            # 加载测试用例
            cases = self.case_service.get_cases_by_project(self.current_project)
            
            # 添加匹配的测试用例到对应文件夹
            for case in cases:
                # 仅对测试用例名称做模糊搜索
                if search_text in case['name'].lower():
                    case_item = QTreeWidgetItem()
                    case_item.setText(0, case['name'])
                    case_item.setData(0, Qt.UserRole, {'type': 'case', 'data': case})
                    case_item.setIcon(0, self.get_icon("test_case.png"))

                    # 添加到对应文件夹
                    folder_id = case.get('folder_id')
                    if folder_id and folder_id in folder_map:
                        folder_map[folder_id].addChild(case_item)
                    else:
                        # 添加到根节点
                        self.case_tree.addTopLevelItem(case_item)

            # 展开所有文件夹
            self.case_tree.expandAll()

        except Exception as e:
            Toast.warning(self, f"搜索测试用例失败: {str(e)}")

    def on_tree_item_clicked(self, item):
        """树形项目点击事件"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type = data['type']
        item_data = data['data']

        if item_type == 'folder':
            self.current_folder = item_data
            self.current_case = None
            self.current_case_data = None
        else:
            self.current_case = item_data
            self.current_folder = None
            # 打开测试用例进行编辑
            self.open_case_for_editing(item_data)
        
        # 更新删除文件夹图标的启用状态
        self.update_delete_folder_icon_state()

    def open_case_for_editing(self, case_data):
        """打开测试用例进行编辑"""
        try:
            # 获取用例完整数据（包括步骤）
            full_case_data = self.case_service.get_case_with_steps(case_data['id'])
            self.current_case_data = full_case_data
            
            # 打开标签页进行编辑
            self.tabbed_case_editor.open_case(
                case_data=full_case_data,
                project_id=full_case_data.get('project_id'),
                folder_id=full_case_data.get('folder_id')
            )

        except Exception as e:
            Toast.warning(self, f"加载用例详情失败: {str(e)}")

    def load_case_details(self, case_data):
        """加载用例详情"""
        try:
            # 获取用例完整数据（包括步骤）
            full_case_data = self.case_service.get_case_with_steps(case_data['id'])
            self.current_case_data = full_case_data
            self.case_editor.load_case(full_case_data)

        except Exception as e:
            Toast.warning(self, f"加载用例详情失败: {str(e)}")

    def on_case_dragged(self, source_item, target_item):
        """处理测试用例拖拽事件"""
        if not source_item:
            return
            
        source_data = source_item.data(0, Qt.UserRole)
        if not source_data or source_data['type'] != 'case':
            return
            
        source_case = source_data['data']
        
        # 确定目标文件夹ID
        target_folder_id = None
        if target_item:
            target_data = target_item.data(0, Qt.UserRole)
            if target_data and target_data['type'] == 'folder':
                target_folder_id = target_data['data']['id']
        
        try:
            # 检查目标文件夹下是否已存在同名用例
            if self.case_service.check_case_name_exists(
                source_case['project_id'], 
                source_case['name'], 
                target_folder_id, 
                source_case['id']
            ):
                QMessageBox.warning(
                    self, 
                    "名称冲突", 
                    f"目标文件夹下已存在名为 '{source_case['name']}' 的测试用例，请先修改用例名称再进行拖拽操作。"
                )
                return
            
            # 更新用例的文件夹ID
            if source_case['folder_id'] != target_folder_id:
                # 修复：传入完整的数据字典，包含name字段
                self.case_service.update_case(source_case['id'], {
                    'name': source_case['name'],
                    'folder_id': target_folder_id
                })
            
            # 重新计算并更新排序顺序
            self.update_case_order(source_case['id'], target_folder_id)
            
            # 刷新用例树
            self.load_case_tree()
            self.data_changed.emit()
            
        except Exception as e:
            Toast.error(self, f"拖拽操作失败: {str(e)}")

    def update_case_order(self, case_id, folder_id):
        """更新测试用例的排序顺序"""
        try:
            # 获取目标文件夹中的所有用例
            cases = self.case_service.get_cases_by_folder(self.current_project, folder_id) if folder_id else self.case_service.get_cases_by_project(self.current_project)
            
            # 计算新的排序顺序（使用最大sort_order + 1）
            max_sort_order = max([case.get('sort_order', 0) for case in cases] + [0])
            new_sort_order = max_sort_order + 1
            
            # 更新用例的文件夹ID和排序顺序
            self.case_service.update_case_order(case_id, folder_id, new_sort_order)
            
        except Exception as e:
            print(f"更新用例顺序失败: {e}")

    def on_case_saved(self, case_data):
        """用例保存事件"""
        try:
            if 'id' in case_data and case_data['id']:
                # 更新现有用例
                self.case_service.update_case(case_data['id'], case_data)
                Toast.success(self, "测试用例已成功更新")
            else:
                # 创建新用例
                case_id = self.case_service.create_case(case_data)
                case_data['id'] = case_id
                Toast.success(self, "测试用例已成功创建")
            
            # 刷新用例树和数据
            self.load_case_tree()
            self.data_changed.emit()
            
        except Exception as e:
            Toast.error(self, f"保存测试用例失败: {str(e)}")

    def on_case_executed(self, case_id, result):
        """用例执行事件"""
        # 这里可以处理执行结果，比如更新状态、显示通知等
        print(f"用例 {case_id} 执行完成: {result}")

    def on_tab_closed(self):
        """标签页关闭事件"""
        # 当所有标签页都关闭时，可以执行一些清理操作
        pass

    def create_test_case(self):
        """创建测试用例（打开新的标签页）"""
        if not self.current_project:
            Toast.warning(self, "请先选择项目")
            return

        folder_id = None
        if self.current_folder:
            folder_id = self.current_folder['id']

        # 打开新的标签页用于创建测试用例
        self.tabbed_case_editor.open_case(
            case_data=None, 
            project_id=self.current_project, 
            folder_id=folder_id
        )

    def get_folder_level(self, folder_id):
        """获取文件夹的层级，根文件夹为0级"""
        try:
            with self.folder_service.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    level = 0
                    current_id = folder_id
                    
                    # 递归向上查找父文件夹，直到根文件夹
                    while current_id:
                        cursor.execute("SELECT parent_id FROM case_folders WHERE id = %s", (current_id,))
                        result = cursor.fetchone()
                        if result and result['parent_id']:
                            current_id = result['parent_id']
                            level += 1
                        else:
                            break
                    
                    return level
        except Exception as e:
            print(f"获取文件夹层级失败: {e}")
            return 0

    def add_case_folder(self):
        """新增用例文件夹"""
        if not self.current_project:
            Toast.warning(self, "请先选择项目")
            return

        parent_folder_id = None
        if self.current_folder:
            parent_folder_id = self.current_folder['id']
            
            # 检查文件夹层级，最多允许3级
            if parent_folder_id:
                # 获取当前文件夹的层级
                current_level = self.get_folder_level(parent_folder_id)
                if current_level >= 3:
                    Toast.warning(self, "文件夹层级最多为3级，无法在当前文件夹下创建子文件夹")
                    return

        dialog = CaseFolderDialog(self, project_id=self.current_project, parent_folder_id=parent_folder_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warning(self, "文件夹名称不能为空")
                return

            try:
                self.folder_service.create_folder(data)
                self.load_case_tree()
                self.data_changed.emit()
                Toast.success(self, "文件夹创建成功")
            except Exception as e:
                Toast.error(self, f"创建文件夹失败: {str(e)}")

    def add_test_case(self):
        """新增测试用例"""
        if not self.current_project:
            Toast.warning(self, "请先选择项目")
            return

        folder_id = None
        if self.current_folder:
            folder_id = self.current_folder['id']

        dialog = TestCaseDialog(self, project_id=self.current_project, folder_id=folder_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warning(self, "用例名称不能为空")
                return

            try:
                case_id = self.case_service.create_case(data)
                self.load_case_tree()
                self.data_changed.emit()

                # 加载新创建的用例
                new_case = self.case_service.get_case_by_id(case_id)
                self.load_case_details(new_case)

                Toast.success(self, "测试用例创建成功")
            except Exception as e:
                Toast.error(self, f"创建测试用例失败: {str(e)}")

    def edit_test_case(self, case_data):
        """编辑测试用例"""
        dialog = TestCaseDialog(self, case_data=case_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warning(self, "用例名称不能为空")
                return

            try:
                self.case_service.update_case(case_data['id'], data)
                self.load_case_tree()
                self.data_changed.emit()

                # 如果当前正在编辑这个用例，刷新详情
                if self.current_case and self.current_case['id'] == case_data['id']:
                    updated_case = self.case_service.get_case_by_id(case_data['id'])
                    self.load_case_details(updated_case)

                Toast.success(self, "测试用例更新成功")
            except Exception as e:
                Toast.error(self, f"更新测试用例失败: {str(e)}")

    def delete_test_case(self, case_data):
        """删除测试用例"""
        # 对于确认对话框，暂时保留QMessageBox.question，因为Toast不支持确认对话框
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除测试用例 '{case_data['name']}' 吗？\n此操作将同时删除用例的所有步骤！",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.case_service.delete_case(case_data['id'])
                self.load_case_tree()
                self.data_changed.emit()
                # 多标签页编辑器不需要清空
                Toast.success(self, "测试用例删除成功")
            except Exception as e:
                Toast.error(self, f"删除测试用例失败: {str(e)}")

    def import_cases(self):
        """导入测试用例"""
        if not self.current_project:
            Toast.warning(self, "请先选择项目")
            return

        from PyQt5.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择导入文件", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    cases_data = json.load(f)

                # 批量导入测试用例
                success_count = 0
                for case_data in cases_data:
                    try:
                        case_data['project_id'] = self.current_project
                        self.case_service.create_case(case_data)
                        success_count += 1
                    except Exception as e:
                        print(f"导入用例失败: {e}")

                self.load_case_tree()
                self.data_changed.emit()
                Toast.success(self, f"成功导入 {success_count} 个测试用例")

            except Exception as e:
                Toast.error(self, f"导入测试用例失败: {str(e)}")

    def export_cases(self):
        """导出测试用例"""
        if not self.current_project:
            Toast.warning(self, "请先选择项目")
            return

        from PyQt5.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择导出位置", "test_cases.json", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                cases = self.case_service.get_cases_by_project(self.current_project)

                # 准备导出数据
                export_data = []
                for case in cases:
                    # 获取用例完整数据
                    full_case = self.case_service.get_case_with_steps(case['id'])
                    # 移除数据库相关字段
                    case_copy = full_case.copy()
                    for field in ['id', 'project_id', 'folder_id', 'created_at', 'updated_at']:
                        case_copy.pop(field, None)
                    # 处理步骤数据
                    if 'steps' in case_copy:
                        for step in case_copy['steps']:
                            for field in ['id', 'case_id', 'created_at', 'updated_at']:
                                step.pop(field, None)
                    export_data.append(case_copy)

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                Toast.success(self, f"成功导出 {len(export_data)} 个测试用例")

            except Exception as e:
                Toast.error(self, f"导出测试用例失败: {str(e)}")

    def show_tree_context_menu(self, position):
        """显示树形结构的右键菜单"""
        item = self.case_tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.UserRole)
        if not data:
            return

        from PyQt5.QtWidgets import QMenu, QAction

        menu = QMenu(self)

        if data['type'] == 'folder':
            # 文件夹的右键菜单
            add_folder_action = QAction("新建子文件夹", self)
            add_folder_action.triggered.connect(self.add_case_folder)
            menu.addAction(add_folder_action)

            add_case_action = QAction("新建用例", self)
            add_case_action.triggered.connect(self.create_test_case)
            menu.addAction(add_case_action)

            menu.addSeparator()

            edit_action = QAction("重命名", self)
            edit_action.triggered.connect(lambda: self.edit_case_folder(data['data']))
            menu.addAction(edit_action)

            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda: self.delete_case_folder(data['data']))
            menu.addAction(delete_action)

        else:
            # 测试用例的右键菜单
            edit_action = QAction("编辑", self)
            edit_action.triggered.connect(lambda: self.edit_test_case(data['data']))
            menu.addAction(edit_action)

            run_action = QAction("执行", self)
            run_action.triggered.connect(lambda: self.run_test_case(data['data']))
            menu.addAction(run_action)

            menu.addSeparator()

            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda: self.delete_test_case(data['data']))
            menu.addAction(delete_action)

        menu.exec_(self.case_tree.mapToGlobal(position))

    def show_api_context_menu(self, position):
        """显示接口模板树形结构的右键菜单"""
        item = self.api_tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.UserRole)
        if not data:
            return

        from PyQt5.QtWidgets import QMenu, QAction

        menu = QMenu(self)

        if data['type'] == 'folder':
            # 文件夹的右键菜单
            add_folder_action = QAction("新建子文件夹", self)
            add_folder_action.triggered.connect(self.add_api_folder)
            menu.addAction(add_folder_action)

            add_template_action = QAction("新建接口模板", self)
            add_template_action.triggered.connect(self.add_api_template)
            menu.addAction(add_template_action)

            menu.addSeparator()

            edit_action = QAction("重命名", self)
            edit_action.triggered.connect(lambda: self.edit_api_folder(data['data']))
            menu.addAction(edit_action)

            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda: self.delete_api_folder(data['data']))
            menu.addAction(delete_action)

        else:
            # 接口模板的右键菜单
            edit_action = QAction("编辑", self)
            edit_action.triggered.connect(lambda: self.edit_api_template(data['data']))
            menu.addAction(edit_action)

            run_action = QAction("测试", self)
            run_action.triggered.connect(lambda: self.test_api_template(data['data']))
            menu.addAction(run_action)

            menu.addSeparator()

            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda: self.delete_api_template(data['data']))
            menu.addAction(delete_action)

        menu.exec_(self.api_tree.mapToGlobal(position))

    def add_api_folder(self):
        """新增接口文件夹"""
        if not self.current_project:
            Toast.warning(self, "请先选择项目")
            return

        # 导入ApiFolderDialog
        from src.ui.interface_auto.components.api_folder_dialog import ApiFolderDialog
        
        dialog = ApiFolderDialog(self, project_id=self.current_project, parent_folder_id=None)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warning(self, "文件夹名称不能为空")
                return

            try:
                self.api_folder_service.create_folder(data)
                self.load_api_templates()
                Toast.success(self, "文件夹创建成功")
            except Exception as e:
                Toast.error(self, f"创建文件夹失败: {str(e)}")

    def edit_api_folder(self, folder_data):
        """编辑接口文件夹"""
        # 导入ApiFolderDialog
        from src.ui.interface_auto.components.api_folder_dialog import ApiFolderDialog
        
        dialog = ApiFolderDialog(self, folder_data=folder_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warning(self, "文件夹名称不能为空")
                return

            try:
                self.api_folder_service.update_folder(folder_data['id'], data)
                self.load_api_templates()
                Toast.success(self, "文件夹更新成功")
            except Exception as e:
                Toast.error(self, f"更新文件夹失败: {str(e)}")

    def delete_api_folder(self, folder_data):
        """删除接口文件夹"""
        # 对于确认对话框，暂时保留QMessageBox.question，因为Toast不支持确认对话框
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除文件夹 '{folder_data['name']}' 吗？\n此操作将同时删除文件夹下的所有接口模板！",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.api_folder_service.delete_folder(folder_data['id'])
                self.load_api_templates()
                Toast.success(self, "文件夹删除成功")
            except Exception as e:
                Toast.error(self, f"删除文件夹失败: {str(e)}")

    def add_api_template(self):
        """新增接口模板"""
        if not self.current_project:
            Toast.warning(self, "请先选择项目")
            return

        # 导入ApiTemplateDialog
        from src.ui.interface_auto.components.api_template_dialog import ApiTemplateDialog
        
        dialog = ApiTemplateDialog(self, project_id=self.current_project)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warning(self, "接口模板名称不能为空")
                return

            try:
                self.api_service.create_template(data)
                self.load_api_templates()
                Toast.success(self, "接口模板创建成功")
            except Exception as e:
                Toast.error(self, f"创建接口模板失败: {str(e)}")

    def edit_api_template(self, template_data):
        """编辑接口模板"""
        # 导入ApiTemplateDialog
        from src.ui.interface_auto.components.api_template_dialog import ApiTemplateDialog
        
        dialog = ApiTemplateDialog(self, template_data=template_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warning(self, "接口模板名称不能为空")
                return

            try:
                self.api_service.update_template(template_data['id'], data)
                self.load_api_templates()
                Toast.success(self, "接口模板更新成功")
            except Exception as e:
                Toast.error(self, f"更新接口模板失败: {str(e)}")

    def delete_api_template(self, template_data):
        """删除接口模板"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除接口模板 '{template_data['name']}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.api_service.delete_template(template_data['id'])
                self.load_api_templates()
                Toast.success(self, "接口模板删除成功")
            except Exception as e:
                Toast.error(self, f"删除接口模板失败: {str(e)}")

    def test_api_template(self, template_data):
        """测试接口模板"""
        Toast.info(self, f"测试接口模板: {template_data['name']}")
        # 这里可以添加实际的接口测试逻辑

    def on_api_tree_item_clicked(self, item, column):
        """处理接口模板树形结构项点击事件"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        if data['type'] == 'template':
            # 点击的是接口模板，显示模板详情
            template_data = data['data']
            # 这里可以添加显示接口模板详情的逻辑
            print(f"点击了接口模板: {template_data['name']}")
        elif data['type'] == 'folder':
            # 点击的是文件夹，可以展开/折叠或显示文件夹信息
            folder_data = data['data']
            print(f"点击了文件夹: {folder_data['name']}")

    def edit_case_folder(self, folder_data):
        """编辑用例文件夹"""
        dialog = CaseFolderDialog(self, folder_data=folder_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warning(self, "文件夹名称不能为空")
                return

            try:
                self.folder_service.update_folder(folder_data['id'], data)
                self.load_case_tree()
                self.data_changed.emit()
                Toast.success(self, "文件夹更新成功")
            except Exception as e:
                Toast.error(self, f"更新文件夹失败: {str(e)}")

    def delete_case_folder(self, folder_data):
        """删除用例文件夹"""
        # 对于确认对话框，暂时保留QMessageBox.question，因为Toast不支持确认对话框
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除文件夹 '{folder_data['name']}' 吗？\n此操作将同时删除文件夹下的所有测试用例！",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.folder_service.delete_folder(folder_data['id'])
                self.load_case_tree()
                self.data_changed.emit()
                # 多标签页编辑器不需要清空
                Toast.success(self, "文件夹删除成功")
            except Exception as e:
                Toast.error(self, f"删除文件夹失败: {str(e)}")

    def delete_selected_folder(self):
        """删除选中的文件夹"""
        if not self.current_folder:
            Toast.warning(self, "请先选择一个文件夹")
            return
            
        self.delete_case_folder(self.current_folder)

    def run_test_case(self, case_data):
        """执行测试用例"""
        if not self.current_case_data or self.current_case_data['id'] != case_data['id']:
            # 如果当前没有加载这个用例，先加载
            self.load_case_details(case_data)

        # 触发用例执行（多标签页编辑器暂不支持直接执行）
        Toast.info(self, "测试用例执行功能将在多标签页编辑器中实现")

    def update_delete_folder_icon_state(self):
        """更新删除文件夹图标的启用状态"""
        if hasattr(self, 'del_folder_icon'):
            # 只有当选中文件夹时才启用删除图标
            if self.current_folder:
                self.del_folder_icon.setEnabled(True)
                self.del_folder_icon.setStyleSheet("")
            else:
                self.del_folder_icon.setEnabled(False)
                self.del_folder_icon.setStyleSheet("opacity: 0.5;")