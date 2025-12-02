import os
import json
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
                             QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QGroupBox, QFormLayout,QCheckBox, 
                             QListWidget, QListWidgetItem, QSplitter,QFrame, 
                             QListWidget, QAbstractItemView,
                             QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
                             QStackedLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QMimeData, QSize
from PyQt5.QtGui import QIcon, QColor, QDrag, QPixmap, QKeySequence
from PyQt5.QtWidgets import QShortcut
from src.core.services.case_folder_service import CaseFolderService
from src.core.services.api_template_service import ApiTemplateService
from src.core.services.api_folder_service import ApiFolderService
from src.core.services.project_service import ProjectService
from src.core.services.test_case_service import TestCaseService
from src.ui.interface_auto.components.tabbed_case_editor import TabbedCaseEditor
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelComboBox, NoWheelTabWidget
from src.ui.widgets.toast_tips import Toast


class ApiTemplateTreeWidget(QTreeWidget):
    """自定义接口模板树控件，支持拖拽接口模板到步骤区域"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_manager = parent
    
    def startDrag(self, supported_actions):
        """重写拖拽开始事件"""
        # 获取当前选中的项
        selected_items = self.selectedItems()
        if not selected_items:
            return
            
        item = selected_items[0]
        data = item.data(0, Qt.UserRole)
        
        # 只允许拖拽接口模板，不允许拖拽文件夹
        if not data or data['type'] != 'template':
            return
            
        template_data = data['data']
        
        # 创建拖拽数据
        mime_data = QMimeData()
        
        # 设置拖拽数据为JSON格式
        import json
        drag_data = {
            'type': 'api_template',
            'template_id': template_data['id'],
            'template_name': template_data['name'],
            'method': template_data.get('method', 'GET'),
            'url': template_data.get('url', '')
        }
        
        mime_data.setData('application/json', json.dumps(drag_data).encode('utf-8'))
        mime_data.setText(f"API模板: {template_data['name']}")
        
        # 创建拖拽对象
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        
        # 设置拖拽图标
        if self.parent_manager:
            icon = self.parent_manager.get_api_icon_by_method(template_data.get('method', 'GET'))
            drag.setPixmap(icon.pixmap(32, 32))
        
        drag.exec_(supported_actions)





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
        
        # 修改按钮文本为中文
        button_box.button(QDialogButtonBox.Ok).setText("确认")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")

        layout.addLayout(form_layout)
        layout.addWidget(button_box)

    def get_data(self):
        return {
            'name': self.name_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip(),
            'project_id': self.project_id or self.folder_data.get('project_id'),
            'parent_id': self.parent_folder_id or self.folder_data.get('parent_id')
        }

    def accept(self):
        """重写accept方法，在保存前验证文件夹名称是否重复"""
        data = self.get_data()
        folder_name = data['name']
        project_id = data['project_id']
        parent_id = data['parent_id']
        
        # 检查文件夹名称是否为空
        if not folder_name:
            Toast.warning(self, "警告", "文件夹名称不能为空！")
            return
            
        # 检查文件夹名称是否重复
        try:
            from src.core.services.case_folder_service import CaseFolderService
            folder_service = CaseFolderService()
            
            # 如果是编辑模式，排除当前文件夹ID
            exclude_id = self.folder_data.get('id') if self.is_edit else None
            
            if folder_service.check_folder_name_exists(project_id, parent_id, folder_name, exclude_id):
                Toast.warning(self, "警告", f"同一级目录下已存在名为 '{folder_name}' 的文件夹！")
                return
                
        except Exception as e:
            print(f"检查文件夹名称重复时出错: {e}")
            Toast.warning(self, "错误", "检查文件夹名称时发生错误，请稍后重试")
            return
            
        # 名称验证通过，调用父类的accept方法
        super().accept()


class DraggableCaseTreeWidget(QTreeWidget):
    """可拖拽的测试用例树控件（完全复用api_template.py的拖拽功能）"""
    item_dragged = pyqtSignal(QTreeWidgetItem, QTreeWidgetItem)  # 拖拽信号
    item_dragged_with_position = pyqtSignal(QTreeWidgetItem, QTreeWidgetItem, QTreeWidgetItem, str)  # 带位置的拖拽信号
    blank_area_clicked = pyqtSignal()  # 空白区域点击信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeWidget.InternalMove)

    def mousePressEvent(self, event):
        """鼠标点击事件处理"""
        # 调用父类方法处理正常点击
        super().mousePressEvent(event)
        
        # 检查是否点击在空白区域
        item = self.itemAt(event.pos())
        if not item:
            # 点击空白区域，清除选中状态并发出信号
            self.clearSelection()
            self.blank_area_clicked.emit()

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
                # 根节点拖拽时，传递源项本身作为目标项的占位符
                self.item_dragged.emit(source_item, source_item)

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
                # 传递目标项和位置信息（根节点没有文件夹，所以传递目标项本身作为占位符）
                self.item_dragged_with_position.emit(source_item, target_item, target_item, drop_position)

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
    api_template_edit_requested = pyqtSignal(str)  # 接口模板编辑请求信号

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
        # 复制粘贴相关变量
        self.copied_case_data = None  # 存储复制的测试用例数据
        self.init_ui()
        # 延迟加载数据，避免启动时数据库连接失败导致弹窗
        QTimer.singleShot(100, self.delayed_load_data)
        # 设置快捷键
        self.setup_shortcuts()

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
        project_layout.setSpacing(10)  # 增加控件之间的间距
        project_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距
        
        project_layout.addWidget(QLabel("项目:"))
        self.project_combo = NoWheelComboBox()
        self.project_combo.setMinimumWidth(150)  # 完全复刻接口模板的最小宽度设置
        self.project_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 30px 6px 8px;
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                color: #495057;
                font-size: 13px;
                min-height: 28px;
            }
            QComboBox:hover {
                border-color: #adb5bd;
                background-color: #f8f9fa;
            }
            QComboBox:focus {
                border-color: #0078d4;
                background-color: #fff;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid #ced4da;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background-color: #f8f9fa;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(src/resources/icons/combobox.png);
            }
            QComboBox::down-arrow:hover {
                image: url(src/resources/icons/combobox.png);
            }
            QComboBox QAbstractItemView {
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                outline: none;
                margin-top: 2px;
                padding: 4px 0px;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px 12px;
                color: #495057;
                background-color: transparent;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e9ecef;
                color: #0078d4;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        project_layout.addWidget(self.project_combo)
        
        # 新建文件夹按钮 - 完全复刻接口模板样式
        self.new_folder_btn = QPushButton(self)
        self.new_folder_btn.setIcon(self.get_icon("add_folder.png"))
        self.new_folder_btn.setIconSize(QSize(24, 24))
        self.new_folder_btn.setFixedSize(32, 32)
        self.new_folder_btn.setToolTip("新建文件夹")
        self.new_folder_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; } QPushButton:hover { background-color: #f0f0f0; }")
        self.new_folder_btn.clicked.connect(self.create_new_folder)
        project_layout.addWidget(self.new_folder_btn)
        
        # 删除文件夹按钮 - 完全复刻接口模板样式
        self.delete_folder_btn = QPushButton(self)
        self.delete_folder_btn.setIcon(self.get_icon("del_folder.png"))
        self.delete_folder_btn.setIconSize(QSize(24, 24))
        self.delete_folder_btn.setFixedSize(32, 32)
        self.delete_folder_btn.setToolTip("删除文件夹")
        self.delete_folder_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; } QPushButton:hover { background-color: #f0f0f0; }")
        self.delete_folder_btn.clicked.connect(self.delete_selected_folder)
        self.delete_folder_btn.setEnabled(False)  # 初始禁用，需要选中文件夹后才能使用
        project_layout.addWidget(self.delete_folder_btn)
        
        project_layout.addStretch()

        # 刷新项目列表按钮
        self.refresh_btn = QPushButton()
        self.refresh_btn.setIcon(self.get_icon("refresh.png"))
        self.refresh_btn.setToolTip("刷新项目列表")
        self.refresh_btn.clicked.connect(self.refresh_project_list)
        self.refresh_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; margin-left: 10px; } QPushButton:hover { background-color: #f0f0f0; }")
        project_layout.addWidget(self.refresh_btn)

        left_layout.addLayout(project_layout)

        # 测试用例搜索框
        case_search_layout = QHBoxLayout()
        case_search_icon_label = QLabel()
        case_search_icon_label.setPixmap(self.get_icon("search.png").pixmap(16, 16))
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
        self.case_tree.item_dragged_with_position.connect(self.on_case_dragged_with_position)
        self.case_tree.blank_area_clicked.connect(self.on_blank_area_clicked)
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
        search_icon_label.setPixmap(self.get_icon("search.png").pixmap(16, 16))
        search_layout.addWidget(search_icon_label)
        self.api_search_edit = QLineEdit()
        self.api_search_edit.setPlaceholderText("输入接口名称或描述...")
        self.api_search_edit.textChanged.connect(self.filter_api_templates)
        search_layout.addWidget(self.api_search_edit)
        middle_layout.addLayout(search_layout)

        # 接口模板树形结构
        self.api_tree = ApiTemplateTreeWidget(self)
        self.api_tree.setHeaderLabels(["接口模板"])
        self.api_tree.setDragEnabled(True)  # 启用拖拽
        self.api_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.api_tree.itemClicked.connect(self.on_api_tree_item_clicked)
        
        # 设置拖拽模式 - 只允许拖拽，不允许放置
        self.api_tree.setDragDropMode(QAbstractItemView.DragOnly)
        
        # 设置拖拽数据格式
        self.api_tree.setDragDropOverwriteMode(False)
        
        middle_layout.addWidget(self.api_tree)

        # 右侧：用例编辑器
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 使用堆叠布局管理标签页编辑器和提示信息
        self.right_stack = QStackedLayout()
        
        # 多标签页用例编辑器
        self.tabbed_case_editor = TabbedCaseEditor(self)
        self.tabbed_case_editor.tab_closed.connect(self.on_tab_closed)
        # 连接保存信号
        self.tabbed_case_editor.saved.connect(self.on_case_saved)
        # 连接接口模板编辑请求信号
        self.tabbed_case_editor.api_template_edit_requested.connect(self.api_template_edit_requested.emit)
        
        # 提示信息组件（当没有打开的测试用例时显示）
        self.empty_prompt_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_prompt_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(20)
        
        # 添加图标
        empty_icon_label = QLabel()
        empty_icon_label.setPixmap(self.get_icon("test_case.png").pixmap(64, 64))
        empty_icon_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_icon_label)
        
        # 添加提示文字
        empty_label = QLabel("请先在左侧新增测试用例或选择对应测试用例")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("font-size: 16px; color: #666; margin: 0;")
        empty_layout.addWidget(empty_label)
        
        # 添加堆叠布局到右侧布局
        right_layout.addLayout(self.right_stack)
        
        # 添加组件到堆叠布局
        self.right_stack.addWidget(self.empty_prompt_widget)
        self.right_stack.addWidget(self.tabbed_case_editor)
        
        # 初始显示提示信息
        self.right_stack.setCurrentWidget(self.empty_prompt_widget)

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
        """获取图标，支持exe打包后的资源路径"""
        import os
        import sys
        
        # 尝试多种路径方式加载图标
        icon_paths = [
            # 开发环境路径
            os.path.join("src", "resources", "icons", icon_name),
            # exe打包后路径
            os.path.join(os.path.dirname(sys.executable), "src", "resources", "icons", icon_name),
            # 相对路径（如果exe在项目根目录）
            os.path.join("src", "resources", "icons", icon_name),
            # 临时解压路径（PyInstaller）
            os.path.join(sys._MEIPASS, "src", "resources", "icons", icon_name) if hasattr(sys, '_MEIPASS') else None
        ]
        
        for path in icon_paths:
            if path and os.path.exists(path):
                return QIcon(path)
        
        # 如果所有路径都找不到，返回空图标
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
                self.load_case_tree(preserve_expanded_state=True)
                self.load_api_templates(preserve_expanded_state=True)

        except Exception as e:
            # 静默处理，不显示弹窗
            print(f"加载项目列表失败: {str(e)}")

    def refresh_project_list(self, business_group_id=None, show_toast=True):
        """刷新项目下拉列表
        
        Args:
            business_group_id: 业务分组ID，如果提供则只显示该业务分组下的项目
            show_toast: 是否显示Toast提示，默认为True
        """
        # 检查服务对象是否已初始化
        if self.project_service is None:
            print("项目服务未初始化，跳过刷新项目列表")
            return
            
        try:
            # 保存当前选中的项目
            current_project_id = self.current_project

            # 暂时断开信号连接，避免在清空和重新填充项目列表时触发on_project_changed
            self.project_combo.currentIndexChanged.disconnect(self.on_project_changed)

            # 重新加载项目列表
            if business_group_id:
                # 根据业务分组ID过滤项目
                projects = self.project_service.get_projects_by_group(business_group_id)
            else:
                # 获取所有项目
                projects = self.project_service.get_all_projects()
                
            self.project_combo.clear()

            for project in projects:
                self.project_combo.addItem(project['name'], project['id'])

            # 尝试恢复之前选中的项目
            if current_project_id:
                index = self.project_combo.findData(current_project_id)
                if index >= 0:
                    self.project_combo.setCurrentIndex(index)
                    # 恢复选中项目后，重新加载用例树以保持展开状态
                    self.load_case_tree(preserve_expanded_state=True)
                    self.load_api_templates(preserve_expanded_state=True)
                elif self.project_combo.count() > 0:
                    # 如果之前的项目不存在了，选择第一个项目
                    self.project_combo.setCurrentIndex(0)
                    self.current_project = self.project_combo.currentData()
                    self.load_case_tree(preserve_expanded_state=True)
                    self.load_api_templates(preserve_expanded_state=True)
            elif self.project_combo.count() > 0:
                # 如果没有之前选中的项目，选择第一个
                self.project_combo.setCurrentIndex(0)
                self.current_project = self.project_combo.currentData()
                self.load_case_tree(preserve_expanded_state=True)
                self.load_api_templates(preserve_expanded_state=True)

            # 重新连接信号
            self.project_combo.currentIndexChanged.connect(self.on_project_changed)
            
            # 只在需要时显示刷新成功提示
            if show_toast:
                Toast.success(self, "刷新成功")

        except Exception as e:
            # 静默处理，不显示弹窗
            print(f"刷新项目列表失败: {str(e)}")
            # 确保在异常情况下也重新连接信号
            self.project_combo.currentIndexChanged.connect(self.on_project_changed)

    def on_project_changed(self, index):
        """项目选择变化"""
        if index >= 0:
            self.current_project = self.project_combo.currentData()
            self.current_folder = None
            self.current_case = None
            self.current_case_data = None
            # 多标签页编辑器不需要清空
            self.load_case_tree(preserve_expanded_state=True)
            self.load_api_templates(preserve_expanded_state=True)
            
            # 更新删除文件夹图标的启用状态
            self.update_delete_folder_icon_state()

    def create_new_folder(self):
        """新建文件夹"""
        if not self.current_project:
            Toast.warn(self, "请先选择项目")
            return

        # 根据当前选中的文件夹决定父文件夹ID
        # 如果选中了文件夹，则在选中目录下创建子文件夹
        # 如果没有选中文件夹，则在根目录创建文件夹
        parent_folder_id = self.current_folder['id'] if self.current_folder else None
        
        dialog = CaseFolderDialog(self, project_id=self.current_project, parent_folder_id=parent_folder_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warn(self, "文件夹名称不能为空")
                return

            try:
                self.folder_service.create_folder(data)
                self.load_case_tree(preserve_expanded_state=True)
                Toast.success(self, "文件夹创建成功")
            except Exception as e:
                Toast.error(self, f"创建文件夹失败: {str(e)}")

    def get_expanded_case_folder_ids(self):
        """获取当前展开的文件夹ID集合"""
        expanded_folder_ids = set()
        self._collect_expanded_case_folder_ids(self.case_tree.invisibleRootItem(), expanded_folder_ids)
        return expanded_folder_ids

    def _collect_expanded_case_folder_ids(self, parent_item, expanded_folder_ids):
        """递归收集展开的文件夹ID"""
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            data = item.data(0, Qt.UserRole)
            if data and data.get('type') == 'folder':
                folder_id = data['data']['id']
                if item.isExpanded():
                    expanded_folder_ids.add(folder_id)
                # 递归处理子项
                self._collect_expanded_case_folder_ids(item, expanded_folder_ids)

    def restore_case_expanded_state(self, folder_map, expanded_folder_ids):
        """恢复文件夹展开状态"""
        # 需要展开的文件夹ID集合
        folders_to_expand = set(expanded_folder_ids)
        
        # 递归展开所有父文件夹，确保展开的文件夹可见
        for folder_id in expanded_folder_ids:
            # 获取文件夹数据
            folder_item = folder_map.get(folder_id)
            if folder_item:
                # 递归展开所有父文件夹
                parent = folder_item.parent()
                while parent:
                    parent_data = parent.data(0, Qt.UserRole)
                    if parent_data and parent_data.get('type') == 'folder':
                        parent_folder_id = parent_data['data']['id']
                        folders_to_expand.add(parent_folder_id)
                        parent = parent.parent()
                    else:
                        break
        
        # 展开所有需要展开的文件夹
        for folder_id in folders_to_expand:
            folder_item = folder_map.get(folder_id)
            if folder_item:
                folder_item.setExpanded(True)

    def expand_case_root_folders(self):
        """展开根级文件夹"""
        root = self.case_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            data = item.data(0, Qt.UserRole)
            if data and data.get('type') == 'folder':
                item.setExpanded(True)

    def get_expanded_api_folder_ids(self):
        """获取当前展开的接口模板文件夹ID集合"""
        expanded_folder_ids = set()
        self._collect_expanded_api_folder_ids(self.api_tree.invisibleRootItem(), expanded_folder_ids)
        return expanded_folder_ids

    def _collect_expanded_api_folder_ids(self, parent_item, expanded_folder_ids):
        """递归收集展开的接口模板文件夹ID"""
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            data = item.data(0, Qt.UserRole)
            if data and data.get('type') == 'folder':
                folder_id = data['data']['id']
                if item.isExpanded():
                    expanded_folder_ids.add(folder_id)
                # 递归处理子项
                self._collect_expanded_api_folder_ids(item, expanded_folder_ids)

    def restore_api_expanded_state(self, folder_map, expanded_folder_ids):
        """恢复接口模板文件夹展开状态"""
        # 需要展开的文件夹ID集合
        folders_to_expand = set(expanded_folder_ids)
        
        # 递归展开所有父文件夹，确保展开的文件夹可见
        for folder_id in expanded_folder_ids:
            # 获取文件夹数据
            folder_item = folder_map.get(folder_id)
            if folder_item:
                # 递归展开所有父文件夹
                parent = folder_item.parent()
                while parent:
                    parent_data = parent.data(0, Qt.UserRole)
                    if parent_data and parent_data.get('type') == 'folder':
                        parent_folder_id = parent_data['data']['id']
                        folders_to_expand.add(parent_folder_id)
                        parent = parent.parent()
                    else:
                        break
        
        # 展开所有需要展开的文件夹
        for folder_id in folders_to_expand:
            folder_item = folder_map.get(folder_id)
            if folder_item:
                folder_item.setExpanded(True)

    def expand_api_root_folders(self):
        """展开接口模板根级文件夹"""
        root = self.api_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            data = item.data(0, Qt.UserRole)
            if data and data.get('type') == 'folder':
                item.setExpanded(True)

    def _expand_folder_by_id(self, folder_id):
        """根据文件夹ID展开对应的文件夹项"""
        def expand_folder_recursive(item):
            """递归查找并展开文件夹"""
            for i in range(item.childCount()):
                child_item = item.child(i)
                data = child_item.data(0, Qt.UserRole)
                if data and data.get('type') == 'folder' and data['data']['id'] == folder_id:
                    child_item.setExpanded(True)
                    return True
                # 递归查找子项
                if expand_folder_recursive(child_item):
                    return True
            return False
        
        # 从根节点开始查找
        root = self.case_tree.invisibleRootItem()
        expand_folder_recursive(root)

    def load_case_tree(self, preserve_expanded_state=True):
        """加载用例树
        
        Args:
            preserve_expanded_state: 是否保持之前的展开状态，默认为True
        """
        # 保存当前展开的文件夹ID
        expanded_folder_ids = set()
        if preserve_expanded_state:
            expanded_folder_ids = self.get_expanded_case_folder_ids()
        
        self.case_tree.clear()

        if not self.current_project:
            return

        try:
            # 加载文件夹（返回的是嵌套的树形结构）
            folders = self.folder_service.get_folders_by_project(self.current_project)
            folder_map = {}

            # 递归添加文件夹及其子文件夹到树中
            def add_folder_to_tree(folder_data, parent_item=None):
                """递归添加文件夹到树形结构"""
                folder_item = QTreeWidgetItem()
                folder_item.setText(0, folder_data['name'])
                folder_item.setData(0, Qt.UserRole, {'type': 'folder', 'data': folder_data})
                folder_item.setIcon(0, self.get_icon("folder.png"))

                folder_map[folder_data['id']] = folder_item

                # 添加到树中
                if parent_item:
                    parent_item.addChild(folder_item)
                else:
                    self.case_tree.addTopLevelItem(folder_item)

                # 递归添加子文件夹
                for child_folder in folder_data.get('children', []):
                    add_folder_to_tree(child_folder, folder_item)

            # 添加所有根文件夹及其子文件夹
            for folder in folders:
                add_folder_to_tree(folder)

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

            # 恢复之前展开的文件夹状态
            if preserve_expanded_state:
                if expanded_folder_ids:
                    self.restore_case_expanded_state(folder_map, expanded_folder_ids)
                # 如果 expanded_folder_ids 为空，说明之前所有文件夹都是收起的，不展开任何文件夹
            else:
                # 默认情况下，只展开根级文件夹
                self.expand_case_root_folders()

        except Exception as e:
                Toast.error(self, f"加载用例树失败: {str(e)}")

    def load_api_templates(self, preserve_expanded_state=True):
        """加载接口模板树形结构
        
        Args:
            preserve_expanded_state: 是否保持之前的展开状态，默认为True
        """
        # 保存当前展开的文件夹ID
        expanded_folder_ids = set()
        if preserve_expanded_state:
            expanded_folder_ids = self.get_expanded_api_folder_ids()
        
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
            
            # 恢复之前展开的文件夹状态
            if preserve_expanded_state:
                if expanded_folder_ids:
                    self.restore_api_expanded_state(folder_map, expanded_folder_ids)
                # 如果 expanded_folder_ids 为空，说明之前所有文件夹都是收起的，不展开任何文件夹
            else:
                # 默认情况下，保持所有文件夹收起状态
                # 不自动展开任何文件夹
                pass
                

        except Exception as e:
            Toast.error(self, f"加载接口模板树形结构失败: {str(e)}")        

    def filter_api_templates(self):
        """过滤接口模板树形结构
        
        搜索时如果有命中的结果，则自动展开匹配的层级，无命中则恢复原来的展开状态
        """
        search_text = self.api_search_edit.text().lower()
        
        # 保存搜索前的展开状态
        original_expanded_ids = self.get_expanded_api_folder_ids() if not search_text else set()
        
        # 如果没有搜索文本，显示所有内容并恢复原来的展开状态
        if not search_text:
            self.load_api_templates(preserve_expanded_state=True)
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
            matched_folder_ids = set()
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
                        matched_folder_ids.add(folder_id)
                    else:
                        # 添加到根节点
                        self.api_tree.addTopLevelItem(template_item)
            
            # 如果有匹配结果，自动展开所有包含匹配项的文件夹及其父文件夹
            if matched_folder_ids:
                for folder_id in matched_folder_ids:
                    if folder_id in folder_map:
                        folder_map[folder_id].setExpanded(True)
                        # 递归展开父文件夹
                        folder = next((f for f in folders if f['id'] == folder_id), None)
                        if folder and folder['parent_id']:
                            parent_id = folder['parent_id']
                            while parent_id:
                                parent_folder = next((f for f in folders if f['id'] == parent_id), None)
                                if parent_folder and parent_folder['id'] in folder_map:
                                    folder_map[parent_folder['id']].setExpanded(True)
                                    parent_id = parent_folder['parent_id']
                                else:
                                    break
            else:
                # 无匹配结果，恢复原来的展开状态
                if original_expanded_ids:
                    self.restore_api_expanded_state(folder_map, original_expanded_ids)

        except Exception as e:
            Toast.warn(self, f"搜索接口模板失败: {str(e)}")

    def filter_test_cases(self):
        """过滤测试用例树形结构（仅对测试用例名称做搜索）"""
        search_text = self.case_search_edit.text().lower()
        
        # 如果没有搜索文本，显示所有内容
        if not search_text:
            self.load_case_tree(preserve_expanded_state=True)
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
            Toast.warn(self, f"搜索测试用例失败: {str(e)}")

    def on_blank_area_clicked(self):
        """空白区域点击事件处理"""
        # 清除选中状态
        self.current_folder = None
        self.current_case = None
        self.current_case_data = None
        
        # 更新删除文件夹图标的启用状态
        self.update_delete_folder_icon_state()
        
        # 如果没有标签页打开，显示提示信息
        if not self.tabbed_case_editor.has_open_tabs():
            self.right_stack.setCurrentWidget(self.empty_prompt_widget)

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
            
            # 调试信息：检查用例数据
            print(f"[DEBUG open_case_for_editing] 传入的case_data: id={case_data.get('id')}, name={case_data.get('name')}")
            print(f"[DEBUG open_case_for_editing] 获取的完整数据: id={full_case_data.get('id')}, name={full_case_data.get('name')}")
            
            # 打开标签页进行编辑
            self.tabbed_case_editor.open_case(
                case_data=full_case_data,
                project_id=full_case_data.get('project_id'),
                folder_id=full_case_data.get('folder_id')
            )
            
            # 打开用例后更新界面显示
            self.update_editor_display()

        except Exception as e:
            Toast.warning(self, "错误", f"加载用例详情失败: {str(e)}")

    def load_case_details(self, case_data):
        """加载用例详情"""
        try:
            # 参数验证：如果case_data是字符串（用例ID），则转换为字典格式
            if isinstance(case_data, str):
                # 如果是字符串，假设它是用例ID，获取完整的用例数据
                full_case_data = self.case_service.get_case_with_steps(case_data)
                if not full_case_data:
                    Toast.warning(self, "错误", f"无法找到用例ID为 {case_data} 的测试用例")
                    return
                self.current_case_data = full_case_data
                # 使用tabbed_case_editor打开用例进行编辑
                self.tabbed_case_editor.open_case(full_case_data, self.current_project, full_case_data.get('folder_id'))
            elif isinstance(case_data, dict) and 'id' in case_data:
                # 如果是字典格式，正常处理
                full_case_data = self.case_service.get_case_with_steps(case_data['id'])
                self.current_case_data = full_case_data
                # 使用tabbed_case_editor打开用例进行编辑
                self.tabbed_case_editor.open_case(full_case_data, self.current_project, case_data.get('folder_id'))
            else:
                Toast.warning(self, "错误", f"无效的用例数据格式: {type(case_data)}")
            
            # 打开用例后更新界面显示
            self.update_editor_display()

        except Exception as e:
            Toast.warning(self, "错误", f"加载用例详情失败: {str(e)}")

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
        else:
            # 当target_item为None时（拖拽到根节点），使用None表示根文件夹
            target_folder_id = None
        
        try:
            # 检查目标文件夹下是否已存在同名用例
            if self.case_service.check_case_name_exists(
                source_case['project_id'], 
                source_case['name'], 
                target_folder_id, 
                source_case['id']
            ):
                Toast.warning(
                    self, 
                    "名称冲突", 
                    f"目标文件夹下已存在名为 '{source_case['name']}' 的测试用例，请先修改用例名称再进行拖拽操作。"
                )
                return
            
            # 更新用例的文件夹ID - 修复：获取完整的用例数据，包括步骤信息
            if source_case['folder_id'] != target_folder_id:
                # 获取完整的用例数据，包括步骤信息
                full_case_data = self.case_service.get_case_with_steps(source_case['id'])
                if not full_case_data:
                    Toast.error(self, "获取测试用例数据失败")
                    return
                
                # 更新文件夹ID，保持其他数据不变
                full_case_data['folder_id'] = target_folder_id
                
                # 使用完整的用例数据进行更新，确保步骤不会丢失
                self.case_service.update_case(source_case['id'], full_case_data)
            
            # 重新计算并更新排序顺序
            self.update_case_order(source_case['id'], target_folder_id)
            
            # 刷新用例树，保持展开状态
            self.load_case_tree(preserve_expanded_state=True)
            self.data_changed.emit()
            
        except Exception as e:
            # 检查是否是拖拽到根节点相关的错误
            if "NoneType" in str(e) or "folder_id" in str(e).lower():
                Toast.error(self, "拖拽到根节点操作失败，请确保目标用例有有效的文件夹信息")
            else:
                Toast.error(self, f"拖拽操作失败: {str(e)}")

    def on_case_dragged_with_position(self, source_item, folder_item, target_item, drop_position):
        """处理带位置的测试用例拖拽事件（优化版，参考接口模板实现）"""
        print(f"[DEBUG] 拖拽事件触发: drop_position={drop_position}")
        
        if not source_item or not target_item:
            print("[DEBUG] 源项或目标项为空，返回")
            return
            
        source_data = source_item.data(0, Qt.UserRole)
        if not source_data or source_data['type'] != 'case':
            print(f"[DEBUG] 源数据类型不正确: {source_data.get('type') if source_data else 'None'}")
            return
            
        target_data = target_item.data(0, Qt.UserRole)
        if not target_data or target_data['type'] != 'case':
            print(f"[DEBUG] 目标数据类型不正确: {target_data.get('type') if target_data else 'None'}")
            return
            
        # 检查拖拽位置：只有当拖拽到目标前面或后面时才执行位置变更
        if drop_position == 'on':
            print("[DEBUG] 拖拽到目标位置（on），不执行位置变更")
            return
            
        source_case = source_data['data']
        target_case = target_data['data']
        
        # 检查是否拖拽到自身
        if source_case['id'] == target_case['id']:
            return
        
        # 确定目标文件夹ID
        target_folder_id = None
        if folder_item:
            folder_data = folder_item.data(0, Qt.UserRole)
            if folder_data and folder_data['type'] == 'folder':
                target_folder_id = folder_data['data']['id']
        else:
            target_folder_id = target_case.get('folder_id')
        
        # 检查拖拽到根节点的情况
        if not target_folder_id:
            # 拖拽到根节点，使用None表示根文件夹
            target_folder_id = None
        
        # 显示拖动操作提示
        position_text = "前面" if drop_position == 'above' else "后面"
        print(f"正在将 '{source_case['name']}' 移动到 '{target_case['name']}' 的{position_text}...")
        
        try:
            # 检查目标文件夹下是否已存在同名用例
            if self.case_service.check_case_name_exists(
                source_case['project_id'], 
                source_case['name'], 
                target_folder_id, 
                source_case['id']
            ):
                Toast.warning(
                    self, 
                    "名称冲突", 
                    f"目标文件夹下已存在名为 '{source_case['name']}' 的测试用例，请先修改用例名称再进行拖拽操作。"
                )
                print("拖动操作取消：名称冲突")
                return
            
            # 保存原始位置信息（用于恢复机制）
            original_folder_id = source_case['folder_id']
            original_sort_order = source_case.get('sort_order', 0)
            
            # 更新用例的文件夹ID - 修复：获取完整的用例数据，包括步骤信息
            if source_case['folder_id'] != target_folder_id:
                # 获取完整的用例数据，包括步骤信息
                full_case_data = self.case_service.get_case_with_steps(source_case['id'])
                if not full_case_data:
                    Toast.error(self, "获取测试用例数据失败")
                    return
                
                # 更新文件夹ID，保持其他数据不变
                full_case_data['folder_id'] = target_folder_id
                
                # 使用完整的用例数据进行更新，确保步骤不会丢失
                self.case_service.update_case(source_case['id'], full_case_data)
            
            # 根据位置重新计算并更新排序顺序
            self.update_case_order_with_position(source_case['id'], target_folder_id, target_case['id'], drop_position)
            
            # 刷新用例树，保持展开状态
            print("[DEBUG] 开始刷新用例树...")
            self.load_case_tree(preserve_expanded_state=True)
            print("[DEBUG] 用例树刷新完成")
            self.data_changed.emit()
            print("[DEBUG] 数据变更信号已发射")
            
            # 关键修复：同步更新编辑页面中的用例数据
            self.sync_case_data_in_editor(source_case['id'])
            
            # 显示成功消息
            print(f"成功将 '{source_case['name']}' 移动到 '{target_case['name']}' 的{position_text}")
            
        except Exception as e:
            error_msg = f"带位置拖拽操作失败: {str(e)}"
            Toast.error(self, error_msg)
            print(f"拖动失败：{error_msg}")
            
            # 尝试恢复原始状态（参考接口模板的恢复机制）
            try:
                self._restore_case_original_state(source_case['id'], original_folder_id, original_sort_order)
                print("已尝试恢复原始状态")
            except Exception as restore_error:
                print(f"恢复原始状态失败: {restore_error}")

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

    def update_case_order_with_position(self, case_id, folder_id, target_case_id, drop_position):
        """根据位置更新测试用例的排序顺序（优化版，参考接口模板实现）"""
        print(f"[DEBUG] 开始更新用例顺序: case_id={case_id}, folder_id={folder_id}, target_case_id={target_case_id}, drop_position={drop_position}")
        
        try:
            # 获取目标文件夹中的所有用例（包含源用例，用于计算完整列表）
            if folder_id:
                all_cases_in_folder = self.case_service.get_cases_by_folder(self.current_project, folder_id)
            else:
                # 对于根节点，只获取folder_id为None的用例
                all_cases = self.case_service.get_cases_by_project(self.current_project)
                all_cases_in_folder = [c for c in all_cases if c.get('folder_id') is None]
            
            # 过滤掉源用例（如果已经在文件夹中）
            cases = [c for c in all_cases_in_folder if c['id'] != case_id]
            
            print(f"[DEBUG] 获取到用例数量: {len(cases)}")
            
            if not cases:
                print("[DEBUG] 没有用例，使用默认排序")
                self.update_case_order(case_id, folder_id)
                return
            
            # 找到目标用例的位置
            target_index = -1
            for i, case in enumerate(cases):
                if case['id'] == target_case_id:
                    target_index = i
                    break
            
            if target_index == -1:
                # 如果找不到目标用例，使用默认排序
                self.update_case_order(case_id, folder_id)
                return
            
            # 主流拖动算法：使用更健壮的排序策略（参考接口模板）
            if drop_position == 'above':
                # 拖拽到目标用例上方：放在目标用例前面
                if target_index == 0:
                    # 如果是第一个用例，放在最前面（使用更安全的差值）
                    new_sort_order = cases[0].get('sort_order', 0) - 100
                else:
                    # 放在目标用例和它前面的用例之间
                    prev_sort = cases[target_index - 1].get('sort_order', 0)
                    target_sort = cases[target_index].get('sort_order', 0)
                    
                    # 使用更健壮的算法：如果间距足够，直接使用中间值；否则重新分配排序值
                    if target_sort - prev_sort > 1:
                        new_sort_order = (prev_sort + target_sort) // 2
                    else:
                        # 间距不足，需要重新分配排序值
                        new_sort_order = self._recalculate_case_sort_order(cases, target_index, 'above')
            
            elif drop_position == 'below':
                # 拖拽到目标用例下方：放在目标用例后面
                if target_index == len(cases) - 1:
                    # 如果是最后一个用例，放在最后面
                    new_sort_order = cases[-1].get('sort_order', 0) + 100
                else:
                    # 放在目标用例和它后面的用例之间
                    target_sort = cases[target_index].get('sort_order', 0)
                    next_sort = cases[target_index + 1].get('sort_order', 0)
                    
                    # 使用更健壮的算法
                    if next_sort - target_sort > 1:
                        new_sort_order = (target_sort + next_sort) // 2
                    else:
                        # 间距不足，需要重新分配排序值
                        new_sort_order = self._recalculate_case_sort_order(cases, target_index, 'below')
            
            else:
                # 默认放在最后
                max_sort_order = max([c.get('sort_order', 0) for c in cases] + [0])
                new_sort_order = max_sort_order + 100
            
            # 确保排序顺序是整数
            new_sort_order = int(new_sort_order)
            
            # 更新用例的排序顺序
            self.case_service.update_case_order(case_id, folder_id, new_sort_order)
            
            # 如果排序值冲突，重新分配所有用例的排序值
            if self._check_case_sort_order_conflict(folder_id):
                self._normalize_case_sort_orders(folder_id)
            
            print(f"[DEBUG] 用例排序更新成功: case_id={case_id}, new_sort_order={new_sort_order}")
                
        except Exception as e:
            # 检查是否是拖拽到根节点相关的错误
            if "NoneType" in str(e) or "folder_id" in str(e).lower():
                print(f"拖拽到根节点排序失败: {str(e)}")
                # 尝试使用默认排序方法作为备选方案
                try:
                    self.update_case_order(case_id, folder_id)
                except Exception as fallback_error:
                    print(f"备选排序方法也失败: {str(fallback_error)}")
            else:
                print(f"根据位置更新排序顺序失败: {str(e)}")
                # 提供用户友好的错误提示
                Toast.error(self, f"拖拽操作失败，请重试。错误信息: {str(e)}")

    def _normalize_sort_orders(self, cases):
        """标准化排序值，确保间距均匀"""
        if not cases:
            return []
        
        # 保持原有的顺序，只重新分配排序值
        # 重新分配排序值，间距为100
        for i, case in enumerate(cases):
            case['sort_order'] = (i + 1) * 100
        
        return cases

    def _recalculate_case_sort_order(self, cases, target_index, position):
        """重新计算排序顺序（当间距不足时使用）"""
        if position == 'above':
            # 从目标位置开始向前重新分配排序值
            base_sort = cases[target_index].get('sort_order', 0)
            return base_sort - 1
        else:  # 'below'
            # 从目标位置开始向后重新分配排序值
            base_sort = cases[target_index].get('sort_order', 0)
            return base_sort + 1

    def _check_case_sort_order_conflict(self, folder_id):
        """检查排序值是否存在冲突"""
        try:
            if folder_id:
                cases = self.case_service.get_cases_by_folder(self.current_project, folder_id)
            else:
                all_cases = self.case_service.get_cases_by_project(self.current_project)
                cases = [c for c in all_cases if c.get('folder_id') is None]
            
            # 检查是否有重复的排序值
            sort_orders = [c.get('sort_order', 0) for c in cases]
            return len(sort_orders) != len(set(sort_orders))
            
        except Exception as e:
            print(f"检查排序值冲突失败: {e}")
            return False

    def _normalize_case_sort_orders(self, folder_id):
        """标准化用例排序值，解决冲突"""
        try:
            if folder_id:
                cases = self.case_service.get_cases_by_folder(self.current_project, folder_id)
            else:
                all_cases = self.case_service.get_cases_by_project(self.current_project)
                cases = [c for c in all_cases if c.get('folder_id') is None]
            
            # 按当前排序值排序
            sorted_cases = sorted(cases, key=lambda x: x.get('sort_order', 0))
            
            # 重新分配排序值，间距为100
            for i, case in enumerate(sorted_cases):
                self.case_service.update_case_order(case['id'], folder_id, (i + 1) * 100)
                
        except Exception as e:
            print(f"标准化用例排序值失败: {e}")

    def _restore_case_original_state(self, case_id, original_folder_id, original_sort_order):
        """恢复用例的原始状态（用于错误恢复）"""
        try:
            # 恢复文件夹ID
            self.case_service.update_case_order(case_id, original_folder_id, original_sort_order)
            
            # 刷新用例树，保持展开状态
            self.load_case_tree(preserve_expanded_state=True)
            self.data_changed.emit()
            
            print(f"已恢复用例 {case_id} 的原始状态")
            
        except Exception as e:
            print(f"恢复用例原始状态失败: {e}")

    def sync_case_data_in_editor(self, case_id):
        """同步更新编辑页面中的用例数据（关键修复：确保拖拽后编辑页面数据同步）"""
        try:
            # 获取更新后的用例数据
            updated_case = self.case_service.get_case_by_id(case_id)
            
            if updated_case:
                # 同步到多标签页编辑器
                self.tabbed_case_editor.sync_case_data(case_id, updated_case)
                print(f"[DEBUG] 已同步用例数据到编辑器: case_id={case_id}")
            else:
                print(f"[DEBUG] 无法获取更新后的用例数据: case_id={case_id}")
                
        except Exception as e:
            print(f"[DEBUG] 同步用例数据到编辑器失败: {e}")

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
            
            # 关键修复：通知标签页编辑器更新内部状态
            # 查找当前活动的标签页ID
            if hasattr(self, 'tabbed_case_editor') and hasattr(self.tabbed_case_editor, 'current_tab_id'):
                current_tab_id = self.tabbed_case_editor.current_tab_id
                if current_tab_id:
                    # 直接更新标签页widget的状态，避免循环调用
                    if current_tab_id in self.tabbed_case_editor.tabs:
                        tab_data = self.tabbed_case_editor.tabs[current_tab_id]
                        widget = tab_data['widget']
                        
                        # 直接更新widget的case_data和is_edit状态
                        if hasattr(widget, 'case_data'):
                            widget.case_data = case_data
                        if hasattr(widget, 'is_edit'):
                            widget.is_edit = True
                        
                        # 更新标签页数据
                        tab_data['data'] = case_data
                        
                        print(f"=== DEBUG: 已直接更新标签页状态 - tab_id: {current_tab_id}, case_id: {case_data.get('id')} ===")
            
            # 刷新用例树和数据，保持展开状态
            self.load_case_tree(preserve_expanded_state=True)
            
            # 自动展开测试用例所在的目录
            folder_id = case_data.get('folder_id')
            if folder_id:
                # 展开测试用例所在的文件夹
                self._expand_folder_by_id(folder_id)
            
            self.data_changed.emit()
            
        except Exception as e:
            Toast.error(self, f"保存测试用例失败: {str(e)}")

    def on_case_executed(self, case_id, result):
        """用例执行事件"""
        # 这里可以处理执行结果，比如更新状态、显示通知等
        print(f"用例 {case_id} 执行完成: {result}")

    def on_tab_closed(self):
        """标签页关闭事件"""
        # 检查是否还有打开的标签页，更新界面显示
        self.update_editor_display()
    
    def update_editor_display(self):
        """根据标签页数量更新编辑器显示状态"""
        if hasattr(self, 'tabbed_case_editor') and hasattr(self.tabbed_case_editor, 'tab_widget'):
            tab_count = self.tabbed_case_editor.tab_widget.count()
            if tab_count > 0:
                # 有打开的标签页，显示标签页编辑器
                self.right_stack.setCurrentWidget(self.tabbed_case_editor)
            else:
                # 没有打开的标签页，显示提示信息
                self.right_stack.setCurrentWidget(self.empty_prompt_widget)

    def create_test_case(self):
        """创建测试用例（打开新的标签页）"""
        if not self.current_project:
            Toast.warn(self, "请先选择项目")
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
        
        # 创建用例后更新界面显示
        self.update_editor_display()

    def create_test_case_in_folder(self, folder_data):
        """在指定文件夹中创建测试用例"""
        if not self.current_project:
            Toast.warn(self, "请先选择项目")
            return

        # 设置当前文件夹
        self.current_folder = folder_data
        
        # 打开新的标签页用于创建测试用例
        self.tabbed_case_editor.open_case(
            case_data=None, 
            project_id=self.current_project, 
            folder_id=folder_data['id']
        )
        
        # 创建用例后更新界面显示
        self.update_editor_display()

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
            Toast.warn(self, "请先选择项目")
            return

        parent_folder_id = None
        if self.current_folder:
            parent_folder_id = self.current_folder['id']
            
            # 检查文件夹层级，最多允许3级
            if parent_folder_id:
                # 获取当前文件夹的层级
                current_level = self.get_folder_level(parent_folder_id)
                if current_level >= 3:
                    Toast.warn(self, "文件夹层级最多为3级，无法在当前文件夹下创建子文件夹")
                    return

        dialog = CaseFolderDialog(self, project_id=self.current_project, parent_folder_id=parent_folder_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warn(self, "文件夹名称不能为空")
                return

            try:
                self.folder_service.create_folder(data)
                
                # 保存当前展开状态，并确保父文件夹展开
                expanded_folder_ids = self.get_expanded_case_folder_ids()
                if parent_folder_id:
                    expanded_folder_ids.add(parent_folder_id)
                
                # 重新加载树形结构，保持展开状态
                self.load_case_tree(preserve_expanded_state=True)
                
                # 确保父文件夹展开
                if parent_folder_id:
                    self._expand_folder_by_id(parent_folder_id)
                
                self.data_changed.emit()
                Toast.success(self, "文件夹创建成功")
            except Exception as e:
                Toast.error(self, f"创建文件夹失败: {str(e)}")

    def add_case_folder_with_parent(self, parent_folder_id):
        """在指定父文件夹下新增用例文件夹"""
        if not self.current_project:
            Toast.warn(self, "请先选择项目")
            return
            
        # 检查文件夹层级，最多允许3级
        if parent_folder_id:
            # 获取当前文件夹的层级
            current_level = self.get_folder_level(parent_folder_id)
            if current_level >= 3:
                Toast.warn(self, "文件夹层级最多为3级，无法在当前文件夹下创建子文件夹")
                return

        dialog = CaseFolderDialog(self, project_id=self.current_project, parent_folder_id=parent_folder_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warn(self, "文件夹名称不能为空")
                return

            try:
                self.folder_service.create_folder(data)
                
                # 保存当前展开状态，并确保父文件夹展开
                expanded_folder_ids = self.get_expanded_case_folder_ids()
                if parent_folder_id:
                    expanded_folder_ids.add(parent_folder_id)
                
                # 重新加载树形结构，保持展开状态
                self.load_case_tree(preserve_expanded_state=True)
                
                # 确保父文件夹展开
                if parent_folder_id:
                    self._expand_folder_by_id(parent_folder_id)
                
                self.data_changed.emit()
                Toast.success(self, "文件夹创建成功")
            except Exception as e:
                Toast.error(self, f"创建文件夹失败: {str(e)}")



    def delete_test_case(self, case_data):
        """删除测试用例"""
        # 创建确认对话框，手动设置按钮文本
        msg_box = QMessageBox(QMessageBox.Question, "确认删除",
                             f"确定要删除测试用例 '{case_data['name']}' 吗？\n此操作将同时删除用例的所有步骤！")
        
        # 添加确认和取消按钮
        confirm_btn = msg_box.addButton("确认", QMessageBox.YesRole)
        cancel_btn = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_btn)
        
        msg_box.exec_()
        
        if msg_box.clickedButton() == confirm_btn:
            try:
                case_id = case_data['id']
                self.case_service.delete_case(case_id)
                self.load_case_tree(preserve_expanded_state=True)
                self.data_changed.emit()
                
                # 关闭对应的编辑标签页（如果存在）
                self.tabbed_case_editor.close_tab_by_case_id(case_id)
                
                Toast.success(self, "测试用例删除成功")
            except Exception as e:
                Toast.error(self, f"删除测试用例失败: {str(e)}")

    def import_cases(self):
        """导入测试用例"""
        if not self.current_project:
            Toast.warn(self, "请先选择项目")
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

                self.load_case_tree(preserve_expanded_state=True)
                self.data_changed.emit()
                Toast.success(self, f"成功导入 {success_count} 个测试用例")

            except Exception as e:
                Toast.error(self, f"导入测试用例失败: {str(e)}")

    def export_cases(self):
        """导出测试用例"""
        if not self.current_project:
            Toast.warn(self, "请先选择项目")
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
            folder_id = data['data']['id']
            current_level = self.get_folder_level(folder_id)
            
            # 只有当文件夹层级 < 2时才显示"新建子文件夹"按钮（根目录0级，最多到2级）
            if current_level < 2:
                add_folder_action = QAction("新建子文件夹", self)
                add_folder_action.triggered.connect(lambda: self.add_case_folder_with_parent(folder_id))
                menu.addAction(add_folder_action)

            add_case_action = QAction("新建用例", self)
            add_case_action.triggered.connect(lambda: self.create_test_case_in_folder(data['data']))
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
            # edit_test_case方法已删除，使用TabbedCaseEditor进行编辑
            pass

            run_action = QAction("执行", self)
            run_action.triggered.connect(lambda: self.run_test_case(data['data']))
            menu.addAction(run_action)

            menu.addSeparator()

            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda: self.delete_test_case(data['data']))
            menu.addAction(delete_action)

        menu.exec_(self.case_tree.mapToGlobal(position))

    def add_api_folder(self):
        """新增接口文件夹"""
        if not self.current_project:
            Toast.warn(self, "请先选择项目")
            return

        # 导入ApiFolderDialog
        from src.ui.interface_auto.components.api_folder_dialog import ApiFolderDialog
        
        dialog = ApiFolderDialog(self, project_id=self.current_project, parent_folder_id=None)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                Toast.warn(self, "文件夹名称不能为空")
                return

            try:
                self.api_folder_service.create_folder(data)
                self.load_api_templates(preserve_expanded_state=True)
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
                Toast.warn(self, "文件夹名称不能为空")
                return

            try:
                self.api_folder_service.update_folder(folder_data['id'], data)
                self.load_api_templates(preserve_expanded_state=True)
                Toast.success(self, "文件夹更新成功")
            except Exception as e:
                Toast.error(self, f"更新文件夹失败: {str(e)}")

    def delete_api_folder(self, folder_data):
        """删除接口文件夹"""
        # 创建确认对话框，手动设置按钮文本
        msg_box = QMessageBox(QMessageBox.Question, "确认删除",
                             f"确定要删除文件夹 '{folder_data['name']}' 吗？\n此操作将同时删除文件夹下的所有接口模板！")
        
        # 添加确认和取消按钮
        confirm_btn = msg_box.addButton("确认", QMessageBox.YesRole)
        cancel_btn = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_btn)
        
        msg_box.exec_()
        
        if msg_box.clickedButton() == confirm_btn:
            try:
                self.api_folder_service.delete_folder(folder_data['id'])
                self.load_api_templates(preserve_expanded_state=True)
                Toast.success(self, "文件夹删除成功")
            except Exception as e:
                Toast.error(self, f"删除文件夹失败: {str(e)}")

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
                Toast.warn(self, "文件夹名称不能为空")
                return

            try:
                self.folder_service.update_folder(folder_data['id'], data)
                self.load_case_tree(preserve_expanded_state=True)
                self.data_changed.emit()
                Toast.success(self, "文件夹更新成功")
            except Exception as e:
                Toast.error(self, f"更新文件夹失败: {str(e)}")

    def delete_case_folder(self, folder_data):
        """删除用例文件夹"""
        # 对于确认对话框，暂时保留QMessageBox.question，因为Toast不支持确认对话框
        msg_box = QMessageBox(QMessageBox.Question, "确认删除",
                             f"确定要删除文件夹 '{folder_data['name']}' 吗？\n此操作将同时删除文件夹下的所有测试用例！")
        confirm_button = msg_box.addButton("确认", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_button)
        msg_box.exec_()
        reply = QMessageBox.Yes if msg_box.clickedButton() == confirm_button else QMessageBox.No

        if reply == QMessageBox.Yes:
            try:
                self.folder_service.delete_folder(folder_data['id'])
                self.load_case_tree(preserve_expanded_state=True)
                self.data_changed.emit()
                # 多标签页编辑器不需要清空
                Toast.success(self, "文件夹删除成功")
            except Exception as e:
                Toast.error(self, f"删除文件夹失败: {str(e)}")

    def delete_selected_folder(self):
        """删除选中的文件夹"""
        if not self.current_folder:
            Toast.warn(self, "请先选择一个文件夹")
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

    def start_api_template_drag(self, supported_actions):
        """开始接口模板拖拽"""
        # 获取当前选中的项
        selected_items = self.api_tree.selectedItems()
        if not selected_items:
            return None
            
        item = selected_items[0]
        data = item.data(0, Qt.UserRole)
        
        # 只允许拖拽接口模板，不允许拖拽文件夹
        if not data or data['type'] != 'template':
            return None
            
        template_data = data['data']
        
        # 创建拖拽数据
        mime_data = QMimeData()
        
        # 设置拖拽数据为JSON格式
        import json
        drag_data = {
            'type': 'api_template',
            'template_id': template_data['id'],
            'template_name': template_data['name'],
            'method': template_data.get('method', 'GET'),
            'url': template_data.get('url', '')
        }
        
        mime_data.setData('application/json', json.dumps(drag_data).encode('utf-8'))
        mime_data.setText(f"API模板: {template_data['name']}")
        
        # 创建拖拽对象
        drag = QDrag(self.api_tree)
        drag.setMimeData(mime_data)
        
        # 设置拖拽图标
        icon = self.get_api_icon_by_method(template_data.get('method', 'GET'))
        drag.setPixmap(icon.pixmap(32, 32))
        
        return drag.exec_(supported_actions)

    def setup_shortcuts(self):
        """设置复制粘贴快捷键"""
        # Ctrl+C 复制快捷键 - 只在用例列表区域有效
        copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self.case_tree)
        copy_shortcut.setContext(Qt.WidgetWithChildrenShortcut)  # 限制在用例列表及其子组件内有效
        copy_shortcut.activated.connect(self.on_copy_shortcut)
        
        # Ctrl+V 粘贴快捷键 - 只在用例列表区域有效
        paste_shortcut = QShortcut(QKeySequence("Ctrl+V"), self.case_tree)
        paste_shortcut.setContext(Qt.WidgetWithChildrenShortcut)  # 限制在用例列表及其子组件内有效
        paste_shortcut.activated.connect(self.on_paste_shortcut)

    def on_copy_shortcut(self):
        """处理Ctrl+C复制快捷键"""
        # 获取当前选中的项
        selected_items = self.case_tree.selectedItems()
        if not selected_items:
            return
            
        item = selected_items[0]
        data = item.data(0, Qt.UserRole)
        
        # 只允许复制测试用例，不允许复制文件夹
        if not data or data['type'] != 'case':
            return
            
        case_data = data['data']
        
        # 获取完整的测试用例数据（包括步骤）
        case_id = case_data.get('id')
        if case_id:
            full_case_data = self.case_service.get_case_with_steps(case_id)
        else:
            full_case_data = case_data
        
        # 保存复制的测试用例数据（深拷贝，避免引用问题）
        import copy
        self.copied_case_data = copy.deepcopy(full_case_data)
        
        # 保存当前用例的文件夹ID，用于默认粘贴位置
        self.copied_case_folder_id = case_data.get('folder_id')
        


    def on_paste_shortcut(self):
        """处理Ctrl+V粘贴快捷键"""
        if not self.copied_case_data:
            return
            
        if not self.current_project:
            return
            
        # 获取当前选中的项
        selected_items = self.case_tree.selectedItems()
        
        if selected_items:
            # 如果选中了项，粘贴到对应位置
            item = selected_items[0]
            data = item.data(0, Qt.UserRole)
            
            if data and data['type'] == 'folder':
                # 粘贴到文件夹
                self.paste_to_folder(data['data']['id'])
            else:
                # 如果选中了项但不是文件夹，使用复制时的文件夹作为默认位置
                if hasattr(self, 'copied_case_folder_id') and self.copied_case_folder_id is not None:
                    self.paste_to_folder(self.copied_case_folder_id)
                else:
                    # 如果没有复制时的文件夹ID，粘贴到根目录（需要修复）
                    self.paste_to_root()
        else:
            # 没有选中项，使用复制时的文件夹作为默认位置
            if hasattr(self, 'copied_case_folder_id') and self.copied_case_folder_id is not None:
                self.paste_to_folder(self.copied_case_folder_id)
            else:
                # 粘贴到根目录
                self.paste_to_root()

    def paste_to_folder(self, folder_id):
        """粘贴到指定文件夹"""
        try:
            # 生成唯一的副本名称
            copy_name = self.generate_copy_name(self.copied_case_data['name'], folder_id)
            
            # 创建副本数据，包含所有必要的字段
            copy_data = {
                'project_id': self.current_project,
                'folder_id': folder_id,
                'name': copy_name,
                'description': self.copied_case_data.get('description', ''),
                'environment_id': self.copied_case_data.get('environment_id'),
                'global_vars': self.copied_case_data.get('global_vars', {}),
                'enable_encryption': self.copied_case_data.get('enable_encryption', False),
                'encrypt_url': self.copied_case_data.get('encrypt_url', ''),
                'decrypt_url': self.copied_case_data.get('decrypt_url', ''),
                'steps': self.copied_case_data.get('steps', [])  # 修复：使用正确的字段名 'steps' 而不是 'test_steps'
            }
            
            # 创建新的测试用例
            new_case_id = self.case_service.create_case(copy_data)
            if new_case_id:
                # 刷新用例树
                self.load_case_tree(preserve_expanded_state=True)
                self.data_changed.emit()
            
        except Exception as e:
            pass

    def paste_to_root(self):
        """粘贴到根目录（如果没有选中文件夹，使用复制用例原本的文件夹ID）"""
        try:
            # 获取复制用例原本的文件夹ID
            original_folder_id = self.copied_case_data.get('folder_id')
            
            # 生成唯一的副本名称
            copy_name = self.generate_copy_name(self.copied_case_data['name'], original_folder_id)
            
            # 创建副本数据，包含所有必要的字段
            copy_data = {
                'project_id': self.current_project,
                'folder_id': original_folder_id,  # 使用复制用例原本的文件夹ID
                'name': copy_name,
                'description': self.copied_case_data.get('description', ''),
                'environment_id': self.copied_case_data.get('environment_id'),
                'global_vars': self.copied_case_data.get('global_vars', {}),
                'enable_encryption': self.copied_case_data.get('enable_encryption', False),
                'encrypt_url': self.copied_case_data.get('encrypt_url', ''),
                'decrypt_url': self.copied_case_data.get('decrypt_url', ''),
                'steps': self.copied_case_data.get('steps', [])  # 修复：使用正确的字段名 'steps' 而不是 'test_steps'
            }
            
            # 创建新的测试用例
            new_case_id = self.case_service.create_case(copy_data)
            if new_case_id:
                # 刷新用例树
                self.load_case_tree(preserve_expanded_state=True)
                self.data_changed.emit()
            
        except Exception as e:
            pass

    def generate_copy_name(self, original_name: str, folder_id: int = None) -> str:
        """生成唯一的副本名称"""
        # 获取当前项目下的所有测试用例
        cases = self.case_service.get_cases_by_project(self.current_project)
        
        # 如果指定了文件夹，只考虑该文件夹下的测试用例
        if folder_id:
            cases = [c for c in cases if c.get('folder_id') == folder_id]
        
        # 查找所有以原始名称开头的副本
        copy_pattern = f"{original_name}_copy"
        existing_copies = []
        
        for case in cases:
            name = case['name']
            if name.startswith(copy_pattern):
                # 提取副本编号
                suffix = name[len(copy_pattern):]
                if suffix.isdigit():
                    existing_copies.append(int(suffix))
        
        # 如果没有副本，从copy1开始
        if not existing_copies:
            return f"{original_name}_copy1"
        
        # 找到最大的副本编号并加1
        max_copy = max(existing_copies)
        return f"{original_name}_copy{max_copy + 1}"