import os
import json
import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
                             QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QGroupBox, QFormLayout,
                             QHeaderView, QInputDialog, QTableWidget, QTableWidgetItem,
                             QSplitter, QToolBar, QAction, QToolButton, QMenu,
                             QFileDialog, QApplication, QScrollArea, QCheckBox,
                             QStyledItemDelegate, QStyle, QShortcut)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QMimeData, QTimer
from PyQt5.QtGui import QIcon, QFont, QDrag, QPixmap, QColor, QPainter, QPen
from src.core.services.api_folder_service import ApiFolderService
from src.core.services.api_template_service import ApiTemplateService
from src.core.services.project_service import ProjectService
from src.core.models.interface_models import ApiTemplate, ApiFolder
from src.ui.interface_auto.components.tabbed_template_editor import TabbedTemplateEditor
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelComboBox, NoWheelTabWidget
from src.ui.interface_auto.components.collapse_button import CollapseButton
from src.ui.widgets.toast_tips import Toast

# 导入请求引擎和变量管理器
from src.utils.interface_utils.request_engine import RequestEngine
from src.utils.interface_utils.variable_manager import VariableManager


class TreeWidgetDelegate(QStyledItemDelegate):
    """自定义树形视图委托，确保展开收缩符号正确显示"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def paint(self, painter, option, index):
        """重写绘制方法"""
        # 调用父类的绘制方法
        super().paint(painter, option, index)
        
        # 确保展开收缩符号能够正确显示
        if option.state & QStyle.State_Children:
            # 如果有子项，确保展开收缩符号可见
            option.state |= QStyle.State_Children


class ApiTemplateDialog(QDialog):
    """接口模板编辑对话框"""

    def __init__(self, parent=None, template_data=None, project_id=None, folder_id=None):
        super().__init__(parent)
        self.template_data = template_data or {}
        self.project_id = project_id
        self.folder_id = folder_id
        self.is_edit = bool(template_data)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑接口模板" if self.is_edit else "新增接口模板")
        self.setMinimumSize(600, 700)

        layout = QVBoxLayout(self)

        # 创建Tab页
        tab_widget = NoWheelTabWidget()

        # 基本信息Tab
        basic_tab = QWidget()
        self.setup_basic_tab(basic_tab)

        # 请求配置Tab
        request_tab = QWidget()
        self.setup_request_tab(request_tab)

        # 高级配置Tab
        advanced_tab = QWidget()
        self.setup_advanced_tab(advanced_tab)

        tab_widget.addTab(basic_tab, "基本信息")
        tab_widget.addTab(request_tab, "请求配置")
        tab_widget.addTab(advanced_tab, "高级配置")

        # 按钮布局
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(tab_widget)
        layout.addWidget(button_box)

        # 加载数据
        if self.is_edit:
            self.load_template_data()

    def setup_basic_tab(self, parent):
        layout = QFormLayout(parent)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入接口名称")

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("请输入接口描述")

        layout.addRow("接口名称:", self.name_edit)
        layout.addRow("接口描述:", self.description_edit)

    def setup_request_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 请求方法选择 - 仅保留GET/POST/PUT/DELETE
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("请求方法:"))
        self.method_combo = NoWheelComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE"])
        method_layout.addWidget(self.method_combo)
        method_layout.addStretch()

        # URL路径 - 进一步增加输入框宽度
        url_layout = QFormLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("例如: /api/v1/users")
        self.url_edit.setMinimumWidth(700)  # 设置更大的最小宽度
        url_layout.addRow("URL路径:", self.url_edit)

        # Headers配置
        headers_group = QGroupBox("请求头(Headers)")
        headers_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #2196f3;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #f8fdff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #1976d2;
            }
        """)
        headers_layout = QVBoxLayout(headers_group)
        self.headers_table = QTableWidget()
        self.headers_table.setColumnCount(2)
        self.headers_table.setHorizontalHeaderLabels(["Header名称", "Header值"])
        self.headers_table.horizontalHeader().setStretchLastSection(True)
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
            QHeaderView::section {
                background-color: #2196f3;
                color: white;
                font-weight: bold;
                padding: 8px;
                border: none;
                border-right: 1px solid #1976d2;
            }
        """)
        self.headers_table.setMinimumHeight(200)
        headers_layout.addWidget(self.headers_table)

        # 参数配置
        params_group = QGroupBox("查询参数(Query Parameters)")
        params_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #4caf50;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #f8fff8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #388e3c;
            }
        """)
        params_layout = QVBoxLayout(params_group)
        self.params_table = QTableWidget()
        self.params_table.setColumnCount(2)
        self.params_table.setHorizontalHeaderLabels(["参数名", "参数值"])
        self.params_table.horizontalHeader().setStretchLastSection(True)
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
            QHeaderView::section {
                background-color: #4caf50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border: none;
                border-right: 1px solid #388e3c;
            }
        """)
        self.params_table.setMinimumHeight(200)
        params_layout.addWidget(self.params_table)

        # 请求体配置
        body_group = QGroupBox("请求体(Body)")
        body_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #ff9800;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #fff8f0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #f57c00;
            }
        """)
        body_layout = QVBoxLayout(body_group)
        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText('请输入JSON格式的请求体，例如: {"key": "value"}')
        self.body_edit.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
            }
            QTextEdit:focus {
                border-color: #2196f3;
                background-color: #ffffff;
            }
        """)
        self.body_edit.setMinimumHeight(150)
        body_layout.addWidget(self.body_edit)

        layout.addLayout(method_layout)
        layout.addLayout(url_layout)
        layout.addWidget(headers_group)
        layout.addWidget(params_group)
        layout.addWidget(body_group)

    def setup_advanced_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 超时设置
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("超时时间(秒):"))
        self.timeout_edit = QLineEdit()
        self.timeout_edit.setText("30")
        self.timeout_edit.setMaximumWidth(100)
        timeout_layout.addWidget(self.timeout_edit)
        timeout_layout.addStretch()

        # 重试设置
        retry_layout = QHBoxLayout()
        self.retry_check = QCheckBox("启用重试机制")
        self.retry_count_edit = QLineEdit()
        self.retry_count_edit.setText("3")
        self.retry_count_edit.setMaximumWidth(50)
        self.retry_count_edit.setEnabled(False)
        retry_layout.addWidget(self.retry_check)
        retry_layout.addWidget(QLabel("重试次数:"))
        retry_layout.addWidget(self.retry_count_edit)
        retry_layout.addStretch()

        # 连接重试复选框和重试次数输入框
        self.retry_check.toggled.connect(self.retry_count_edit.setEnabled)

        layout.addLayout(timeout_layout)
        layout.addLayout(retry_layout)
        layout.addStretch()

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

    def get_data(self):
        """获取表单数据"""
        # 基本信息
        data = {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'method': self.method_combo.currentText(),
            'url_path': self.url_edit.text().strip(),
            'project_id': self.project_id or self.template_data.get('project_id'),
            'folder_id': self.folder_id or self.template_data.get('folder_id')
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
                # 如果不是有效的JSON，作为字符串处理
                data['body'] = body_text
        else:
            data['body'] = {}

        return data


class ApiFolderDialog(QDialog):
    """接口文件夹编辑对话框"""

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


class DraggableTreeWidget(QTreeWidget):
    """可拖拽的树形控件"""
    item_dragged = pyqtSignal(QTreeWidgetItem, QTreeWidgetItem)  # 拖拽信号
    item_dragged_with_position = pyqtSignal(QTreeWidgetItem, QTreeWidgetItem, QTreeWidgetItem, str)  # 带位置的拖拽信号
    item_copy_requested = pyqtSignal(QTreeWidgetItem)  # 复制请求信号
    item_rename_requested = pyqtSignal(QTreeWidgetItem)  # 重命名请求信号
    item_delete_requested = pyqtSignal(QTreeWidgetItem)  # 删除请求信号

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
                    # 拖拽到接口模板
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
        if drag_type == 'template':
            # 发出拖拽信号，让父组件处理
            source_item = self.find_item_by_id(drag_id, drag_type)
            if source_item:
                self.item_dragged.emit(source_item, None)

    def handle_drop_to_folder(self, drag_type, drag_id, folder_id):
        """处理拖拽到文件夹"""
        if drag_type == 'template':
            # 发出拖拽信号，让父组件处理
            source_item = self.find_item_by_id(drag_id, drag_type)
            target_item = self.find_item_by_id(folder_id, 'folder')
            if source_item and target_item:
                self.item_dragged.emit(source_item, target_item)

    def handle_drop_to_root_with_position(self, drag_type, drag_id, target_id, drop_position):
        """处理带位置的拖拽到根节点"""
        if drag_type == 'template':
            # 发出带位置的拖拽信号
            source_item = self.find_item_by_id(drag_id, drag_type)
            target_item = self.find_item_by_id(target_id, 'template')
            if source_item and target_item:
                # 传递目标项和位置信息
                self.item_dragged_with_position.emit(source_item, None, target_item, drop_position)

    def handle_drop_to_folder_with_position(self, drag_type, drag_id, folder_id, target_id, drop_position):
        """处理带位置的拖拽到文件夹"""
        if drag_type == 'template':
            # 发出带位置的拖拽信号
            source_item = self.find_item_by_id(drag_id, drag_type)
            folder_item = self.find_item_by_id(folder_id, 'folder')
            target_item = self.find_item_by_id(target_id, 'template')
            if source_item and folder_item and target_item:
                # 传递文件夹、目标项和位置信息
                self.item_dragged_with_position.emit(source_item, folder_item, target_item, drop_position)

    def find_item_by_id(self, item_id, item_type):
        """根据ID和类型查找树项"""
        def search_item(item):
            if item:
                data = item.data(0, Qt.UserRole)
                if data and data['type'] == item_type and data['data']['id'] == item_id:
                    return item
                
                for i in range(item.childCount()):
                    child = item.child(i)
                    result = search_item(child)
                    if result:
                        return result
            return None

        # 从根节点开始搜索
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            result = search_item(item)
            if result:
                return result
        return None


class ApiTemplateManager(QWidget):
    """接口模板管理页面"""
    data_changed = pyqtSignal()  # 数据变化信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.api_service = None
        self.project_service = None
        self.folder_service = None
        self.current_project = None
        self.current_folder = None
        self.current_template = None
        self.init_ui()
        # 延迟加载数据，避免启动时数据库连接失败导致弹窗
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.delayed_load_data)

    def delayed_load_data(self):
        """延迟加载数据，初始化服务对象"""
        try:
            self.api_service = ApiTemplateService()
            self.project_service = ProjectService()
            self.folder_service = ApiFolderService()
            self.load_projects()
        except Exception as e:
            print(f"初始化服务失败: {e}")
            # 静默处理，不显示弹窗

    def refresh_project_list(self):
        """刷新项目下拉列表"""
        # 检查服务对象是否已初始化
        if self.project_service is None:
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
                    self.load_api_tree()
            elif self.project_combo.count() > 0:
                # 如果没有之前选中的项目，选择第一个
                self.project_combo.setCurrentIndex(0)
                self.current_project = self.project_combo.currentData()
                self.load_api_tree()

        except Exception as e:
            print(f"刷新项目列表失败: {str(e)}")
            # 静默处理，不显示弹窗

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # 创建主容器
        main_container = QWidget()
        main_container_layout = QVBoxLayout(main_container)
        main_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建顶部工具栏（移除展开/收缩按钮，因为已经在左侧区域右侧边线上添加了按钮）
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        toolbar_layout.addStretch()
        main_container_layout.addLayout(toolbar_layout)

        # 创建分割器并设为实例变量
        self.splitter = QSplitter(Qt.Horizontal)
        
        # 左侧区域：包含菜单栏和展开/收缩按钮
        left_container = QWidget()
        left_container_layout = QHBoxLayout(left_container)
        left_container_layout.setContentsMargins(0, 0, 0, 0)
        left_container_layout.setSpacing(0)
        
        # 左侧菜单栏内容
        self.left_widget = QWidget()
        self.left_widget.setMaximumWidth(400)
        left_layout = QVBoxLayout(self.left_widget)
        left_layout.setContentsMargins(5, 0, 5, 5)

        # 项目选择和文件夹操作按钮
        project_layout = QHBoxLayout()
        project_layout.addWidget(QLabel("选择项目:"))
        self.project_combo = NoWheelComboBox()
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        project_layout.addWidget(self.project_combo)
        
        # 新建文件夹按钮
        self.new_folder_btn = QPushButton(self)
        self.new_folder_btn.setIcon(self.get_icon("add_folder.png"))
        self.new_folder_btn.setIconSize(QSize(24, 24))
        self.new_folder_btn.setFixedSize(32, 32)
        self.new_folder_btn.setToolTip("新建文件夹")
        self.new_folder_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; } QPushButton:hover { background-color: #f0f0f0; }")
        self.new_folder_btn.clicked.connect(self.add_api_folder)
        project_layout.addWidget(self.new_folder_btn)
        
        # 删除文件夹按钮
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
        left_layout.addLayout(project_layout)

        # 接口模板搜索栏
        search_layout = QHBoxLayout()
        search_icon_label = QLabel()
        search_icon_label.setPixmap(QIcon(os.path.join("src", "resources", "icons", "search.png")).pixmap(16, 16))
        search_layout.addWidget(search_icon_label)
        self.api_search_edit = QLineEdit()
        self.api_search_edit.setPlaceholderText("输入接口名称或描述...")
        self.api_search_edit.textChanged.connect(self.filter_api_templates)
        search_layout.addWidget(self.api_search_edit)
        left_layout.addLayout(search_layout)

        # 接口树
        self.tree_widget = DraggableTreeWidget()
        self.tree_widget.setHeaderHidden(True)  # 隐藏列头
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_tree_context_menu)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        self.tree_widget.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        
        # 设置展开/收缩符号在左侧
        self.tree_widget.setRootIsDecorated(True)
        self.tree_widget.setIndentation(20)
        
        # 设置自定义委托来确保展开收缩符号显示
        self.tree_widget.setItemDelegate(TreeWidgetDelegate(self.tree_widget))
        
        # 连接悬停按钮信号
        self.tree_widget.item_copy_requested.connect(self.on_item_copy_requested)
        self.tree_widget.item_delete_requested.connect(self.on_item_delete_requested)
        
        # 连接拖拽信号
        self.tree_widget.item_dragged.connect(self.on_item_dragged)
        self.tree_widget.item_dragged_with_position.connect(self.on_item_dragged_with_position)

        left_layout.addWidget(self.tree_widget)
        
        # 添加展开/收缩图标（在左侧区域的右侧边线上）
        self.collapse_button = CollapseButton()
        self.collapse_button.state_changed.connect(self.on_collapse_state_changed)
        
        # 设置图标样式（无背景、无边框）
        self.collapse_button.setFixedSize(24, 24)
        self.collapse_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-radius: 12px;
            }
        """)
        
        # 将左侧内容和按钮添加到容器
        left_container_layout.addWidget(self.left_widget)
        left_container_layout.addWidget(self.collapse_button)

        # 右侧：详情显示区域
        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)

        # 直接创建提示信息标签，参考business_management.py的实现
        self.info_label = QLabel("请先在左侧新增接口或选择对应接口")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #666; font-size: 14px; margin: 20px;")
        
        # 多标签页编辑器容器
        self.tabbed_editor_container = QWidget()
        self.tabbed_editor_layout = QVBoxLayout(self.tabbed_editor_container)
        
        # 创建多标签页编辑器
        self.tabbed_editor = TabbedTemplateEditor()
        self.tabbed_editor_layout.addWidget(self.tabbed_editor)
        
        # 连接保存信号到实际的保存逻辑
        self.tabbed_editor.saved.connect(self.on_template_saved)
        # 连接标签页关闭信号
        self.tabbed_editor.tab_closed.connect(self.on_tab_closed)
        
        # 默认显示提示信息，隐藏编辑器
        self.tabbed_editor_container.hide()

        detail_layout.addWidget(self.info_label)
        detail_layout.addWidget(self.tabbed_editor_container)

        self.splitter.addWidget(left_container)
        self.splitter.addWidget(self.detail_widget)
        self.splitter.setSizes([300, 700])

        main_container_layout.addWidget(self.splitter)
        main_layout.addWidget(main_container)

        self.setStyleSheet("""
            ApiTemplateManager {
                background-color: white;
            }
            QTreeWidget {
                border: none;
                border-radius: 0px;
                padding: 0px;
                background-color: white;
                color: black;
                alternate-background-color: white;
            }
            QTreeWidget::item {
                padding: 5px;
                border: none;
                border-radius: 0px;
                background-color: white;
                color: black;
            }
            QTreeWidget::item:hover {
                background-color: #f0f0f0;
                border: none;
                color: black;
            }
            QTreeWidget::item:selected {
                background-color: #e0e0e0;
                border: none;
                color: black;
            }
            QTreeWidget::item[dragEnabled=\"true\"] {
                background-color: #f8f9fa;
                border: none;
                color: black;
            }
            QTreeWidget::item[dropIndicator=\"true\"] {
                background-color: #f8f9fa;
                border: none;
                color: black;
            }
            QTreeWidget::branch {
                subcontrol-position: center left;
                width: 16px;
                height: 16px;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
            }
            QGroupBox {
                font-weight: bold;
                margin-top: 10px;
            }
        """)

        # 设置快捷键
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+C 复制快捷键
        self.copy_shortcut = QShortcut(Qt.CTRL + Qt.Key_C, self.tree_widget)
        self.copy_shortcut.activated.connect(self.on_copy_shortcut)
        
        # Ctrl+V 粘贴快捷键
        self.paste_shortcut = QShortcut(Qt.CTRL + Qt.Key_V, self.tree_widget)
        self.paste_shortcut.activated.connect(self.on_paste_shortcut)

    def on_collapse_state_changed(self, is_expanded):
        """处理展开/收缩状态变化"""
        if is_expanded:
            # 展开状态：显示左侧菜单栏
            self.left_widget.show()
            self.splitter.setSizes([300, 700])
        else:
            # 收起状态：隐藏左侧菜单栏内容，但保留按钮可见
            self.left_widget.hide()
            self.splitter.setSizes([24, 1000])  # 只保留按钮宽度（24px）

    def on_copy_shortcut(self):
        """处理Ctrl+C快捷键"""
        current_item = self.tree_widget.currentItem()
        if current_item:
            data = current_item.data(0, Qt.UserRole)
            if data and data['type'] == 'template':
                # 复制接口模板到剪贴板
                self.copied_template_data = data['data'].copy()
            # 其他情况不进行任何操作，也不显示提示

    def on_paste_shortcut(self):
        """处理Ctrl+V快捷键"""
        # 检查是否已复制模板数据
        if not hasattr(self, 'copied_template_data') or not self.copied_template_data:
            return
            
        current_item = self.tree_widget.currentItem()
        if current_item:
            data = current_item.data(0, Qt.UserRole)
            if data:
                if data['type'] == 'folder':
                    # 粘贴到文件夹
                    self.paste_to_folder(data['data'])
                else:
                    # 粘贴到根目录
                    self.paste_to_root()
        else:
            # 如果没有选中任何项目，粘贴到根目录
            self.paste_to_root()

    def paste_to_folder(self, folder_data):
        """粘贴到指定文件夹"""
        # 检查是否已复制模板数据
        if not hasattr(self, 'copied_template_data') or not self.copied_template_data:
            return
            
        # 检查文件夹数据是否有效
        if not folder_data or 'id' not in folder_data or 'name' not in folder_data:
            return
            
        original_name = self.copied_template_data['name']
        
        # 执行粘贴操作：直接创建模板副本
        try:
            # 创建模板副本数据
            template_copy = self.copied_template_data.copy()
            template_copy.pop('id', None)  # 移除原始ID
            
            # 生成新的副本名称
            template_copy['name'] = self.generate_copy_name(original_name, folder_data['id'])
            template_copy['project_id'] = self.current_project  # 确保项目ID正确
            template_copy['folder_id'] = folder_data['id']  # 设置目标文件夹ID
            
            # 创建新的模板
            self.api_service.create_template(template_copy)
            self.load_api_tree()
            self.data_changed.emit()
        except Exception as e:
            pass

    def paste_to_root(self):
        """粘贴到根目录（如果没有选中文件夹，使用复制接口原本的文件夹ID）"""
        # 检查是否已复制模板数据
        if not hasattr(self, 'copied_template_data') or not self.copied_template_data:
            return
            
        # 获取复制接口原本的文件夹ID
        original_folder_id = self.copied_template_data.get('folder_id')
        original_name = self.copied_template_data['name']
        
        # 执行粘贴操作：直接创建模板副本
        try:
            # 创建模板副本数据
            template_copy = self.copied_template_data.copy()
            template_copy.pop('id', None)  # 移除原始ID
            
            # 生成新的副本名称
            template_copy['name'] = self.generate_copy_name(original_name, original_folder_id)
            template_copy['project_id'] = self.current_project  # 确保项目ID正确
            template_copy['folder_id'] = original_folder_id  # 使用复制接口原本的文件夹ID
            
            # 创建新的模板
            self.api_service.create_template(template_copy)
            self.load_api_tree()
            self.data_changed.emit()
        except Exception as e:
            pass

    def get_icon(self, icon_name):
        """获取图标"""
        try:
            # 首先尝试从 resources/icons 目录加载
            icon_path = os.path.join("src", "resources", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
            
            # 如果不存在，尝试从 ui/interface_auto/icons 目录加载
            icon_path = os.path.join("src", "ui", "interface_auto", "icons", icon_name)
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
            return
            
        try:
            projects = self.project_service.get_all_projects()
            self.project_combo.clear()
            for project in projects:
                self.project_combo.addItem(project['name'], project['id'])

            if projects:
                self.current_project = projects[0]['id']
                self.load_api_tree()

        except Exception as e:
            print(f"加载项目列表失败: {str(e)}")
            # 静默处理，不显示弹窗

    def on_project_changed(self, index):
        """项目选择变化"""
        if index >= 0:
            # 保存当前项目选择，用于可能的恢复
            self.previous_project = getattr(self, 'current_project', None)
            
            # 检查是否有未保存的标签页
            if hasattr(self, 'tabbed_editor') and self.tabbed_editor:
                if self.tabbed_editor.has_modified_tabs():
                    # 显示保存确认弹窗
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle('保存确认')
                    msg_box.setText('有未保存的接口模板，切换项目将关闭所有标签页。请选择操作：')
                    
                    # 添加自定义按钮
                    save_all_btn = msg_box.addButton('保存全部', QMessageBox.AcceptRole)
                    ignore_btn = msg_box.addButton('忽略', QMessageBox.DestructiveRole)
                    cancel_btn = msg_box.addButton('取消', QMessageBox.RejectRole)
                    
                    # 设置默认按钮
                    msg_box.setDefaultButton(save_all_btn)
                    
                    msg_box.exec_()
                    
                    clicked_button = msg_box.clickedButton()
                    
                    if clicked_button == save_all_btn:
                        # 保存所有未保存的标签页
                        self.save_all_modified_tabs()
                        # 关闭所有标签页
                        self.tabbed_editor.close_all_tabs()
                    elif clicked_button == ignore_btn:
                        # 忽略修改，直接关闭所有标签页
                        self.tabbed_editor.close_all_tabs()
                    else:
                        # 取消切换项目，恢复之前的选择
                        self.restore_previous_project_selection()
                        return
                else:
                    # 没有未保存的标签页，直接关闭所有标签页
                    self.tabbed_editor.close_all_tabs()
            
            # 更新当前项目
            self.current_project = self.project_combo.currentData()
            self.current_folder = None
            self.delete_folder_btn.setEnabled(False)
            self.load_api_tree()
    
    def save_all_modified_tabs(self):
        """保存所有未保存的标签页"""
        if not hasattr(self, 'tabbed_editor') or not self.tabbed_editor:
            return
            
        # 遍历所有标签页，保存未保存的
        for tab_id, tab_data in self.tabbed_editor.tabs.items():
            if tab_data['modified']:
                # 保存标签页
                tab_data['widget'].save_template()
                # 标记为已保存
                self.tabbed_editor.set_tab_modified(tab_id, False)
    
    def restore_previous_project_selection(self):
        """恢复之前的项目选择"""
        if hasattr(self, 'previous_project') and self.previous_project:
            # 在项目下拉列表中查找之前的项目
            for i in range(self.project_combo.count()):
                if self.project_combo.itemData(i) == self.previous_project:
                    self.project_combo.setCurrentIndex(i)
                    break
        else:
            # 如果没有之前的项目，选择第一个项目
            if self.project_combo.count() > 0:
                self.project_combo.setCurrentIndex(0)

    def load_api_tree(self):
        """加载接口树"""
        self.tree_widget.clear()

        if not self.current_project:
            return

        # 检查服务对象是否已初始化
        if self.folder_service is None or self.api_service is None:
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
                    self.tree_widget.addTopLevelItem(folder_item)
                else:
                    # 添加到父文件夹
                    parent_item = folder_map.get(folder['parent_id'])
                    if parent_item:
                        parent_item.addChild(folder_item)

            # 加载接口模板
            templates = self.api_service.get_templates_by_project(self.current_project)
            for template in templates:
                template_item = QTreeWidgetItem()
                template_item.setText(0, template['name'])
                template_item.setData(0, Qt.UserRole, {'type': 'template', 'data': template})
                template_item.setIcon(0, self.get_api_icon_by_method(template.get('method')))

                # 添加到对应文件夹
                folder_id = template.get('folder_id')
                if folder_id and folder_id in folder_map:
                    folder_map[folder_id].addChild(template_item)
                else:
                    # 添加到根节点
                    self.tree_widget.addTopLevelItem(template_item)

            # 展开所有文件夹
            self.tree_widget.expandAll()

        except Exception as e:
            print(f"加载接口树失败: {str(e)}")
            # 静默处理，不显示弹窗

    def on_tree_item_clicked(self, item):
        """树形项目点击事件"""
        data = item.data(0, Qt.UserRole)
        if not data:
            # 如果没有选中项目，禁用删除按钮
            self.delete_folder_btn.setEnabled(False)
            return

        item_type = data['type']
        item_data = data['data']

        if item_type == 'folder':
            self.current_folder = item_data
            self.current_template = None
            
            # 只有当没有打开的标签页时才显示文件夹信息
            if hasattr(self, 'tabbed_editor') and self.tabbed_editor and self.tabbed_editor.tab_widget.count() == 0:
                self.show_folder_info()
            # 选中文件夹时启用删除按钮
            self.delete_folder_btn.setEnabled(True)
        else:
            self.current_template = item_data
            self.current_folder = None
            # 点击接口使用多标签页编辑器打开
            self.tabbed_editor.open_template(item_data)
            
            # 隐藏提示信息，显示多标签页编辑器
            self.info_label.hide()
            self.tabbed_editor_container.show()
            # 选中接口模板时禁用删除按钮
            self.delete_folder_btn.setEnabled(False)

    def on_tree_item_double_clicked(self, item):
        """树形项目双击事件"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        if data['type'] == 'template':
            # 双击接口使用多标签页编辑器打开
            self.tabbed_editor.open_template(data['data'])
            
            # 隐藏提示信息，显示多标签页编辑器
            self.info_label.hide()
            self.tabbed_editor_container.show()
            
    def on_item_copy_requested(self, item):
        """处理复制请求"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
            
        item_type = data['type']
        item_data = data['data']
        
        if item_type == 'folder':
            # 文件夹不允许复制
            return
        else:
            self.copy_api_template_to_edit(item_data)
            
    def on_item_edit_requested(self, item):
        """处理编辑请求"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
            
        item_type = data['type']
        item_data = data['data']
        
        if item_type == 'folder':
            self.edit_api_folder(item_data)
        # 接口模板不再支持编辑功能，直接打开多标签页编辑器
            
    def on_item_delete_requested(self, item):
        """处理删除请求"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
            
        item_type = data['type']
        item_data = data['data']
        
        if item_type == 'folder':
            self.delete_api_folder(item_data)
        else:
            self.delete_api_template(item_data)

    def on_item_dragged(self, source_item, target_item):
        """处理拖拽事件"""
        if not source_item:
            return
            
        source_data = source_item.data(0, Qt.UserRole)
        if not source_data or source_data['type'] != 'template':
            return
            
        source_template = source_data['data']
        
        # 确定目标文件夹ID
        target_folder_id = None
        if target_item:
            target_data = target_item.data(0, Qt.UserRole)
            if target_data and target_data['type'] == 'folder':
                target_folder_id = target_data['data']['id']
        
        try:
            # 检查目标文件夹下是否已存在同名接口
            if self.api_service.check_template_name_exists(
                source_template['project_id'], 
                target_folder_id, 
                source_template['name'], 
                source_template['id']
            ):
                QMessageBox.warning(
                    self, 
                    "名称冲突", 
                    f"目标文件夹下已存在名为 '{source_template['name']}' 的接口，请先修改接口名称再进行拖拽操作。"
                )
                return
            
            # 更新模板的文件夹ID
            if source_template['folder_id'] != target_folder_id:
                self.api_service.update_template_folder(source_template['id'], target_folder_id)
            
            # 重新计算并更新排序顺序
            self.update_template_order(source_template['id'], target_folder_id)
            
            # 刷新接口树
            self.load_api_tree()
            self.data_changed.emit()
            
            # 显示拖拽成功提示
            Toast.success(self, f"接口 '{source_template['name']}' 已成功移动")
            
            # 关键修复：同步更新编辑页面中的模板数据
            self.sync_template_data_in_editor(source_template['id'])
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"拖拽操作失败: {str(e)}")

    def on_item_dragged_with_position(self, source_item, folder_item, target_item, drop_position):
        """处理带位置的拖拽事件（优化版）"""
        if not source_item or not target_item:
            return
            
        source_data = source_item.data(0, Qt.UserRole)
        if not source_data or source_data['type'] != 'template':
            return
            
        target_data = target_item.data(0, Qt.UserRole)
        if not target_data or target_data['type'] != 'template':
            return
            
        # 检查拖拽位置：只有当拖拽到目标前面或后面时才执行位置变更
        if drop_position == 'on':
            # 拖拽到目标位置（替换目标），不执行位置变更
            # 提供视觉反馈：短暂高亮目标项
            self._highlight_item(target_item)
            return
            
        source_template = source_data['data']
        target_template = target_data['data']
        
        # 检查是否拖拽到自身
        if source_template['id'] == target_template['id']:
            # 拖拽到自身，不执行操作
            self._highlight_item(source_item)
            return
        
        # 确定目标文件夹ID
        target_folder_id = None
        if folder_item:
            folder_data = folder_item.data(0, Qt.UserRole)
            if folder_data and folder_data['type'] == 'folder':
                target_folder_id = folder_data['data']['id']
        else:
            target_folder_id = target_template.get('folder_id')
        
        # 显示拖动操作提示
        position_text = "前面" if drop_position == 'above' else "后面"
        print(f"正在将 '{source_template['name']}' 移动到 '{target_template['name']}' 的{position_text}...")
        
        try:
            # 检查目标文件夹下是否已存在同名接口
            if self.api_service.check_template_name_exists(
                source_template['project_id'], 
                target_folder_id, 
                source_template['name'], 
                source_template['id']
            ):
                QMessageBox.warning(
                    self, 
                    "名称冲突", 
                    f"目标文件夹下已存在名为 '{source_template['name']}' 的接口，请先修改接口名称再进行拖拽操作。"
                )
                print("拖动操作取消：名称冲突")
                return
            
            # 保存原始位置信息（用于撤销功能）
            original_folder_id = source_template['folder_id']
            original_sort_order = source_template.get('sort_order', 0)
            
            # 更新模板的文件夹ID
            if source_template['folder_id'] != target_folder_id:
                self.api_service.update_template_folder(source_template['id'], target_folder_id)
            
            # 根据位置重新计算并更新排序顺序
            self.update_template_order_with_position(source_template['id'], target_folder_id, target_template['id'], drop_position)
            
            # 刷新接口树
            self.load_api_tree()
            self.data_changed.emit()
            
            # 同步编辑页面数据
            self.sync_template_data_in_editor(source_template['id'])
            
            # 显示成功消息
            print(f"成功将 '{source_template['name']}' 移动到 '{target_template['name']}' 的{position_text}")
            
            # 记录操作历史（用于撤销）
            self._record_drag_operation(source_template['id'], original_folder_id, original_sort_order, target_folder_id)
            
        except Exception as e:
            error_msg = f"带位置拖拽操作失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            print(f"拖动失败：{error_msg}")
            
            # 尝试恢复原始状态
            self._restore_original_state(source_template['id'], source_template['folder_id'], source_template.get('sort_order', 0))

    def update_template_order_with_position(self, source_template_id, folder_id, target_template_id, drop_position):
        """根据位置更新模板的排序顺序（优化版）"""
        try:
            # 获取目标文件夹中的所有模板（包含源模板，用于计算完整列表）
            if folder_id:
                all_templates_in_folder = self.api_service.get_templates_by_folder(folder_id)
            else:
                # 对于根节点，只获取folder_id为None的模板
                all_templates = self.api_service.get_templates_by_project(self.current_project)
                all_templates_in_folder = [t for t in all_templates if t.get('folder_id') is None]
            
            # 过滤掉源模板（如果已经在文件夹中）
            templates = [t for t in all_templates_in_folder if t['id'] != source_template_id]
            
            # 找到目标模板的位置
            target_index = -1
            for i, template in enumerate(templates):
                if template['id'] == target_template_id:
                    target_index = i
                    break
            
            if target_index == -1:
                # 如果找不到目标模板，使用默认排序
                self.update_template_order(source_template_id, folder_id)
                return
            
            # 主流拖动算法：使用更健壮的排序策略
            if drop_position == 'above':
                # 拖拽到目标模板上方：放在目标模板前面
                if target_index == 0:
                    # 如果是第一个模板，放在最前面（使用更安全的差值）
                    new_sort_order = templates[0].get('sort_order', 0) - 100
                else:
                    # 放在目标模板和它前面的模板之间
                    prev_sort = templates[target_index - 1].get('sort_order', 0)
                    target_sort = templates[target_index].get('sort_order', 0)
                    
                    # 使用更健壮的算法：如果间距足够，直接使用中间值；否则重新分配排序值
                    if target_sort - prev_sort > 1:
                        new_sort_order = (prev_sort + target_sort) // 2
                    else:
                        # 间距不足，需要重新分配排序值
                        new_sort_order = self._recalculate_sort_order(templates, target_index, 'above')
            
            elif drop_position == 'below':
                # 拖拽到目标模板下方：放在目标模板后面
                if target_index == len(templates) - 1:
                    # 如果是最后一个模板，放在最后面
                    new_sort_order = templates[-1].get('sort_order', 0) + 100
                else:
                    # 放在目标模板和它后面的模板之间
                    target_sort = templates[target_index].get('sort_order', 0)
                    next_sort = templates[target_index + 1].get('sort_order', 0)
                    
                    # 使用更健壮的算法
                    if next_sort - target_sort > 1:
                        new_sort_order = (target_sort + next_sort) // 2
                    else:
                        # 间距不足，需要重新分配排序值
                        new_sort_order = self._recalculate_sort_order(templates, target_index, 'below')
            
            else:
                # 默认放在最后
                max_sort_order = max([t.get('sort_order', 0) for t in templates] + [0])
                new_sort_order = max_sort_order + 100
            
            # 确保排序顺序是整数
            new_sort_order = int(new_sort_order)
            
            # 更新模板的排序顺序
            self.api_service.update_template_order(source_template_id, new_sort_order)
            
            # 如果排序值冲突，重新分配所有模板的排序值
            if self._check_sort_order_conflict(folder_id):
                self._normalize_sort_orders(folder_id)
            
        except Exception as e:
            print(f"根据位置更新模板顺序失败: {e}")
            # 提供用户友好的错误提示
            QMessageBox.warning(self, "拖动失败", f"拖动操作失败，请重试。错误信息: {str(e)}")
    
    def _recalculate_sort_order(self, templates, target_index, position):
        """重新计算排序顺序（当间距不足时使用）"""
        if position == 'above':
            # 从目标位置开始向前重新分配排序值
            base_sort = templates[target_index].get('sort_order', 0)
            return base_sort - 1
        else:  # 'below'
            # 从目标位置开始向后重新分配排序值
            base_sort = templates[target_index].get('sort_order', 0)
            return base_sort + 1
    
    def _check_sort_order_conflict(self, folder_id):
        """检查排序值是否存在冲突"""
        try:
            if folder_id:
                templates = self.api_service.get_templates_by_folder(folder_id)
            else:
                all_templates = self.api_service.get_templates_by_project(self.current_project)
                templates = [t for t in all_templates if t.get('folder_id') is None]
            
            # 检查是否有重复的排序值
            sort_orders = [t.get('sort_order', 0) for t in templates]
            return len(sort_orders) != len(set(sort_orders))
            
        except Exception as e:
            print(f"检查排序值冲突失败: {e}")
            return False
    
    def _normalize_sort_orders(self, folder_id):
        """重新规范化排序值（解决冲突）"""
        try:
            if folder_id:
                templates = self.api_service.get_templates_by_folder(folder_id)
            else:
                all_templates = self.api_service.get_templates_by_project(self.current_project)
                templates = [t for t in all_templates if t.get('folder_id') is None]
            
            # 按当前排序值排序
            templates.sort(key=lambda x: x.get('sort_order', 0))
            
            # 重新分配排序值（间隔为100）
            for i, template in enumerate(templates):
                new_sort_order = (i + 1) * 100
                self.api_service.update_template_order(template['id'], new_sort_order)
                
        except Exception as e:
            print(f"规范化排序值失败: {e}")
    
    def _highlight_item(self, item):
        """高亮显示树形项（提供视觉反馈）"""
        try:
            # 保存原始背景色
            original_color = item.background(0)
            
            # 设置高亮颜色
            item.setBackground(0, QColor(255, 255, 200))  # 浅黄色背景
            
            # 使用定时器恢复原始颜色
            QTimer.singleShot(500, lambda: item.setBackground(0, original_color))
            
        except Exception as e:
            print(f"高亮项失败: {e}")
    
    def _record_drag_operation(self, template_id, original_folder_id, original_sort_order, new_folder_id):
        """记录拖动操作历史（用于撤销功能）"""
        try:
            # 初始化操作历史列表
            if not hasattr(self, '_drag_operation_history'):
                self._drag_operation_history = []
            
            # 记录操作信息
            operation = {
                'template_id': template_id,
                'original_folder_id': original_folder_id,
                'original_sort_order': original_sort_order,
                'new_folder_id': new_folder_id,
                'timestamp': time.time()
            }
            
            # 添加到历史记录（限制历史记录长度）
            self._drag_operation_history.append(operation)
            if len(self._drag_operation_history) > 10:  # 保留最近10次操作
                self._drag_operation_history.pop(0)
                
        except Exception as e:
            print(f"记录拖动操作失败: {e}")
    
    def _restore_original_state(self, template_id, original_folder_id, original_sort_order):
        """尝试恢复原始状态（错误恢复）"""
        try:
            # 恢复文件夹ID
            if original_folder_id is not None:
                self.api_service.update_template_folder(template_id, original_folder_id)
            
            # 恢复排序顺序
            self.api_service.update_template_order(template_id, original_sort_order)
            
            # 刷新界面
            self.load_api_tree()
            self.data_changed.emit()
            
            print(f"已恢复模板 {template_id} 的原始状态")
            
        except Exception as e:
            print(f"恢复原始状态失败: {e}")

    def filter_api_templates(self):
        """过滤接口模板树形结构（仅对接口模板名称做搜索，保持文件夹层级关系）"""
        search_text = self.api_search_edit.text().lower()
        
        # 如果没有搜索文本，显示所有内容
        if not search_text:
            self.load_api_tree()
            return
        
        # 重新加载数据并手动过滤
        try:
            if not self.current_project:
                return

            # 清空树形结构
            self.tree_widget.clear()

            # 加载接口模板文件夹
            folders = self.folder_service.get_folders_by_project(self.current_project)
            
            # 加载接口模板
            templates = self.api_service.get_templates_by_project(self.current_project)
            
            # 创建文件夹映射
            folder_map = {}
            
            # 第一步：创建所有文件夹项（搜索时显示所有文件夹以保持层级关系）
            for folder in folders:
                folder_item = QTreeWidgetItem()
                folder_item.setText(0, folder['name'])
                folder_item.setData(0, Qt.UserRole, {'type': 'folder', 'data': folder})
                
                # 设置文件夹图标
                folder_item.setIcon(0, self.get_icon("folder.png"))
                
                folder_map[folder['id']] = folder_item
            
            # 第二步：构建文件夹层级关系
            for folder in folders:
                folder_id = folder['id']
                if folder_id in folder_map:
                    folder_item = folder_map[folder_id]
                    parent_id = folder.get('parent_id')
                    
                    if parent_id and parent_id in folder_map:
                        # 添加到父文件夹
                        folder_map[parent_id].addChild(folder_item)
                    else:
                        # 添加到根节点
                        self.tree_widget.addTopLevelItem(folder_item)
            
            # 第三步：添加匹配的接口模板到对应文件夹（仅对接口模板名称做模糊搜索）
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
                        self.tree_widget.addTopLevelItem(template_item)
            
            # 展开所有文件夹，确保搜索结果可见
            self.tree_widget.expandAll()

        except Exception as e:
            QMessageBox.warning(self, "搜索失败", f"搜索接口模板失败: {str(e)}")

    def update_template_order(self, template_id, folder_id):
        """更新模板的排序顺序"""
        try:
            # 获取目标文件夹中的所有模板
            if folder_id:
                templates = self.api_service.get_templates_by_folder(folder_id)
            else:
                # 对于根节点，只获取folder_id为None的模板
                all_templates = self.api_service.get_templates_by_project(self.current_project)
                templates = [t for t in all_templates if t.get('folder_id') is None]
            
            # 计算新的排序顺序
            max_sort_order = max([t.get('sort_order', 0) for t in templates] + [0])
            new_sort_order = max_sort_order + 1
            
            # 更新模板的排序顺序
            self.api_service.update_template_order(template_id, new_sort_order)
            
        except Exception as e:
            print(f"更新模板顺序失败: {e}")

    def show_folder_info(self):
        """显示文件夹信息"""
        # 显示提示信息，隐藏编辑器
        self.info_label.show()
        self.tabbed_editor_container.hide()
    
    def on_tab_closed(self):
        """标签页关闭事件处理"""
        # 当所有标签页都关闭时，显示文件夹信息
        self.show_folder_info()
        
        # 设置提示文本
        self.info_label.setText("请先在左侧新增接口或选择对应接口")





    def add_api_folder(self):
        """新增接口文件夹（默认创建一级文件夹）"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择项目")
            return

        # 默认创建一级文件夹（父文件夹ID为None）
        dialog = ApiFolderDialog(self, project_id=self.current_project, parent_folder_id=None)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "文件夹名称不能为空")
                return

            try:
                self.folder_service.create_folder(data)
                self.load_api_tree()
                self.data_changed.emit()
                Toast.success(self, "一级文件夹创建成功")
            except Exception as e:
                Toast.error(self, f"创建文件夹失败: {str(e)}")

    def get_folder_depth(self, folder_id: int) -> int:
        """计算文件夹的层级深度"""
        if not folder_id:
            return 0
            
        depth = 0
        current_id = folder_id
        folders = self.folder_service.get_folders_by_project(self.current_project)
        folder_map = {folder['id']: folder for folder in folders}
        
        while current_id and current_id in folder_map:
            current_folder = folder_map[current_id]
            current_id = current_folder.get('parent_id')
            depth += 1
            
        return depth

    def generate_copy_name(self, original_name: str, folder_id: int = None) -> str:
        """生成唯一的副本名称"""
        # 获取当前项目下的所有模板
        templates = self.api_service.get_templates_by_project(self.current_project)
        
        # 如果指定了文件夹，只考虑该文件夹下的模板
        if folder_id:
            templates = [t for t in templates if t.get('folder_id') == folder_id]
        
        # 查找所有以原始名称开头的副本
        copy_pattern = f"{original_name}_copy"
        existing_copies = []
        
        for template in templates:
            name = template['name']
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

    def add_subfolder(self):
        """新增子文件夹（用于右键菜单）"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择项目")
            return

        # 使用当前选中的文件夹作为父文件夹
        parent_folder_id = None
        if self.current_folder:
            parent_folder_id = self.current_folder['id']
            
            # 检查当前文件夹的层级深度，如果已经是三级或以上，不允许创建子文件夹
            current_depth = self.get_folder_depth(parent_folder_id)
            if current_depth >= 3:
                QMessageBox.warning(self, "提示", "文件夹层级最多允许三级，无法继续创建子文件夹")
                return

        dialog = ApiFolderDialog(self, project_id=self.current_project, parent_folder_id=parent_folder_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "文件夹名称不能为空")
                return

            try:
                self.folder_service.create_folder(data)
                self.load_api_tree()
                self.data_changed.emit()
                Toast.success(self, "子文件夹创建成功")
            except Exception as e:
                Toast.error(self, f"创建子文件夹失败: {str(e)}")

    def add_api_template(self):
        """新增接口模板"""
        if not self.current_project:
            QMessageBox.warning(self, "警告", "请先选择项目")
            return
            
        # 创建空模板数据
        template_data = {
            'project_id': self.current_project,
            'folder_id': self.current_folder['id'] if self.current_folder else None,
            'name': '',
            'method': 'GET',
            'url_path': '',
            'description': '',
            'headers': {},
            'params': {},
            'body': {}
        }
        
        # 使用多标签页编辑器打开新模板
        self.tabbed_editor.open_template(template_data)
        
        # 隐藏提示信息，显示多标签页编辑器
        self.info_label.hide()
        self.tabbed_editor_container.show()
        
    def add_api_template_to_folder(self, folder_data):
        """在指定文件夹中新增接口模板"""
        if not self.current_project:
            QMessageBox.warning(self, "警告", "请先选择项目")
            return
            
        # 创建空模板数据
        template_data = {
            'project_id': self.current_project,
            'folder_id': folder_data['id'],
            'name': '',
            'method': 'GET',
            'url_path': '',
            'description': '',
            'headers': {},
            'params': {},
            'body': {}
        }
        
        # 使用多标签页编辑器打开新模板
        self.tabbed_editor.open_template(template_data)
        
        # 隐藏提示信息，显示多标签页编辑器
        self.info_label.hide()
        self.tabbed_editor_container.show()

    # edit_api_template方法已删除，接口模板编辑功能通过多标签页编辑器实现



    def delete_current_template(self):
        """删除当前选中的接口模板"""
        if self.current_template:
            self.delete_api_template(self.current_template)

    def sync_template_data_in_editor(self, template_id):
        """同步更新编辑页面中的模板数据（在拖拽操作后调用）"""
        try:
            # 从数据库获取最新的模板数据
            latest_template = self.api_service.get_template_by_id(template_id)
            if not latest_template:
                return
            
            # 遍历所有打开的标签页，找到包含该模板的标签页
            for tab_id, tab_data in self.tabbed_editor.tabs.items():
                widget = tab_data['widget']
                current_data = tab_data['data']
                
                # 检查是否是同一个模板
                if 'id' in current_data and current_data['id'] == template_id:
                    # 更新标签页数据
                    tab_data['data'] = latest_template
                    
                    # 更新标签页widget的模板数据
                    widget.template_data = latest_template
                    
                    # 标记为已修改状态，提示用户保存
                    self.tabbed_editor.set_tab_modified(tab_id, True)
                    widget.modified = True
                    widget.modified_signal.emit(True)
                    
                    # 显示提示信息
                    Toast.information(self, "模板位置已更新", f"接口 '{latest_template['name']}' 的位置已更新，请保存以确认更改")
                    break
                    
        except Exception as e:
            print(f"同步编辑页面模板数据失败: {e}")

    def on_template_saved(self, template_data):
        """模板保存回调"""
        try:
            # 检查接口名称是否重复
            folder_id = template_data.get('folder_id')
            template_name = template_data.get('name')
            
            if not template_name:
                QMessageBox.warning(self, "输入错误", "接口名称不能为空")
                return False  # 保存失败
                
            # 检查同一目录下是否存在相同名称的接口模板
            template_id = template_data.get('id')
            project_id = template_data.get('project_id')
            if self.api_service.check_template_name_exists(project_id, folder_id, template_name, template_id):
                QMessageBox.warning(self, "名称重复", f"当前目录下已存在名为 '{template_name}' 的接口模板，请使用不同的名称")
                return False  # 保存失败
            
            save_success = False
            
            if 'id' in template_data:
                # 关键修复：在保存前重新获取最新的模板数据，确保包含最新的位置信息
                latest_template = self.api_service.get_template_by_id(template_data['id'])
                if latest_template:
                    # 保留用户编辑的内容，但使用最新的位置信息
                    template_data['folder_id'] = latest_template.get('folder_id')
                    template_data['sort_order'] = latest_template.get('sort_order', 0)
                
                # 更新现有模板
                print(f"开始更新模板，模板ID: {template_data['id']}")
                print(f"模板数据: {template_data}")
                save_success = self.api_service.update_template(template_data['id'], template_data)
                print(f"更新结果: {save_success}")
                if save_success:
                    Toast.success(self, "接口模板更新成功")
                else:
                    Toast.critical(self, "错误", "接口模板更新失败")
                    print("更新失败，检查模板数据格式和数据库连接")
            else:
                # 创建新模板
                new_template_id = self.api_service.create_template(template_data)
                if new_template_id:
                    save_success = True
                    Toast.success(self, "接口模板创建成功")
                    
                    # 更新template_data，添加新创建的ID
                    template_data['id'] = new_template_id
                    
                    # 更新标签页状态为编辑模式
                    current_index = self.tabbed_editor.tab_widget.currentIndex()
                    if current_index >= 0:
                        # 获取当前标签页ID
                        widget = self.tabbed_editor.tab_widget.widget(current_index)
                        tab_id = None
                        for tid, tab_data in self.tabbed_editor.tabs.items():
                            if tab_data['widget'] == widget:
                                tab_id = tid
                                break
                        
                        if tab_id:
                            # 更新标签页数据
                            self.tabbed_editor.tabs[tab_id]['data'] = template_data
                            
                            # 更新标签页widget的状态
                            widget.template_data = template_data
                            widget.is_edit = True
                else:
                    QMessageBox.critical(self, "错误", "接口模板创建失败")
            
            if save_success:
                # 刷新接口树
                self.load_api_tree()
                self.data_changed.emit()
                
                # 标记标签页为已保存状态
                current_index = self.tabbed_editor.tab_widget.currentIndex()
                if current_index >= 0:
                    # 获取当前标签页ID
                    widget = self.tabbed_editor.tab_widget.widget(current_index)
                    tab_id = None
                    for tid, tab_data in self.tabbed_editor.tabs.items():
                        if tab_data['widget'] == widget:
                            tab_id = tid
                            break
                    
                    if tab_id:
                        # 标记标签页为已保存状态
                        self.tabbed_editor.set_tab_modified(tab_id, False)
                        
                        # 通知标签页widget保存成功
                        widget.modified = False
                        widget.modified_signal.emit(False)
            else:
                # 保存失败，保持标签页的修改状态
                current_index = self.tabbed_editor.tab_widget.currentIndex()
                if current_index >= 0:
                    # 获取当前标签页ID
                    widget = self.tabbed_editor.tab_widget.widget(current_index)
                    tab_id = None
                    for tid, tab_data in self.tabbed_editor.tabs.items():
                        if tab_data['widget'] == widget:
                            tab_id = tid
                            break
                    
                    if tab_id:
                        # 标记标签页为未保存状态
                        self.tabbed_editor.set_tab_modified(tab_id, True)
                        
                        # 通知标签页widget保存失败，保持修改状态
                        widget.modified = True
            
            return save_success
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存接口模板失败: {str(e)}")
            
            # 异常情况下也保持标签页的修改状态
            current_index = self.tabbed_editor.tab_widget.currentIndex()
            if current_index >= 0:
                # 获取当前标签页ID
                widget = self.tabbed_editor.tab_widget.widget(current_index)
                tab_id = None
                for tid, tab_data in self.tabbed_editor.tabs.items():
                    if tab_data['widget'] == widget:
                        tab_id = tid
                        break
                
                if tab_id:
                    # 标记标签页为未保存状态
                    self.tabbed_editor.set_tab_modified(tab_id, True)
                    
                    # 通知标签页widget保存失败，保持修改状态
                    widget.modified = True
            
            return False  # 保存失败



    def delete_api_template(self, template_data):
        """删除接口模板"""
        # 创建自定义按钮的确认对话框
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认删除")
        msg_box.setText(f"确定要删除接口模板 '{template_data['name']}' 吗？")
        msg_box.setIcon(QMessageBox.Question)
        
        # 设置按钮为中文
        confirm_button = msg_box.addButton("确认", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_button)
        
        msg_box.exec_()
        
        reply = QMessageBox.Yes if msg_box.clickedButton() == confirm_button else QMessageBox.No

        if reply == QMessageBox.Yes:
            try:
                # 在删除之前，先检查并关闭对应的编辑标签页
                if hasattr(self, 'tabbed_editor') and self.tabbed_editor:
                    self.tabbed_editor.close_tab_by_template_id(template_data['id'])
                
                self.api_service.delete_template(template_data['id'])
                self.load_api_tree()
                self.data_changed.emit()
                
                # 检查是否还有打开的标签页，如果没有才显示提示信息
                if hasattr(self, 'tabbed_editor') and self.tabbed_editor:
                    if self.tabbed_editor.tab_widget.count() == 0:
                        self.info_label.show()
                else:
                    self.info_label.show()
                
                # 使用Toast提示替代QMessageBox，避免二次点击
                Toast.success(self, "接口模板删除成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除接口模板失败: {str(e)}")





    def show_tree_context_menu(self, position):
        """显示树形结构的右键菜单"""
        item = self.tree_widget.itemAt(position)
        
        from PyQt5.QtWidgets import QMenu, QAction

        menu = QMenu(self)

        if item:
            data = item.data(0, Qt.UserRole)
            if data:
                if data['type'] == 'folder':
                    # 文件夹的右键菜单
                    # 检查文件夹层级，只有三级以下的文件夹才显示"新增子文件夹"选项
                    folder_depth = self.get_folder_depth(data['data']['id'])
                    if folder_depth < 3:
                        add_folder_action = QAction("新增子文件夹", self)
                        add_folder_action.triggered.connect(self.add_subfolder)
                        menu.addAction(add_folder_action)

                    add_template_action = QAction("新增接口", self)
                    add_template_action.triggered.connect(lambda: self.add_api_template_to_folder(data['data']))
                    menu.addAction(add_template_action)
                    
                    # 添加粘贴菜单项
                    if hasattr(self, 'copied_template_data') and self.copied_template_data:
                        paste_action = QAction("粘贴", self)
                        paste_action.triggered.connect(lambda: self.paste_with_edit({'type': 'folder', 'data': data['data']}))
                        menu.addAction(paste_action)

                    menu.addSeparator()

                    edit_action = QAction("重命名", self)
                    edit_action.triggered.connect(lambda: self.edit_api_folder(data['data']))
                    menu.addAction(edit_action)

                    delete_action = QAction("删除", self)
                    delete_action.triggered.connect(lambda: self.delete_api_folder(data['data']))
                    menu.addAction(delete_action)

                else:
                    # 接口模板的右键菜单
                    copy_action = QAction("复制", self)
                    copy_action.triggered.connect(lambda: self.copy_api_template_to_edit(data['data']))
                    menu.addAction(copy_action)

                    menu.addSeparator()

                    delete_action = QAction("删除", self)
                    delete_action.triggered.connect(lambda: self.delete_api_template(data['data']))
                    menu.addAction(delete_action)
        else:
            # 空白区域（根目录）的右键菜单
            if hasattr(self, 'copied_template_data') and self.copied_template_data:
                paste_action = QAction("粘贴", self)
                paste_action.triggered.connect(lambda: self.paste_with_edit({'type': 'root', 'data': None}))
                menu.addAction(paste_action)

        menu.exec_(self.tree_widget.mapToGlobal(position))

    def edit_api_folder(self, folder_data):
        """编辑接口文件夹"""
        dialog = ApiFolderDialog(self, folder_data=folder_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "文件夹名称不能为空")
                return

            try:
                self.folder_service.update_folder(folder_data['id'], data)
                self.load_api_tree()
                self.data_changed.emit()
                Toast.success(self, "文件夹更新成功")
            except Exception as e:
                Toast.error(self, f"更新文件夹失败: {str(e)}")

    def copy_api_template_to_edit(self, template_data):
        """复制接口模板并自动进入编辑页面"""
        # 检查项目是否已选择
        if not self.current_project:
            return
            
        # 检查模板数据是否有效
        if not template_data or 'name' not in template_data:
            return

        # 创建模板副本数据
        template_copy = template_data.copy()
        template_copy.pop('id', None)  # 移除原始ID
        
        # 生成新的副本名称
        try:
            template_copy['name'] = self.generate_copy_name(template_data['name'], template_data.get('folder_id'))
        except Exception as e:
            return
            
        template_copy['project_id'] = self.current_project  # 确保项目ID正确

        # 使用多标签页编辑器打开复制的模板
        try:
            tab_id = self.tabbed_editor.open_template(template_copy)
            
            # 立即将复制的模板标记为已修改状态，这样关闭时会提示保存
            if tab_id in self.tabbed_editor.tabs:
                self.tabbed_editor.set_tab_modified(tab_id, True)
            
            # 隐藏提示信息，显示多标签页编辑器
            self.info_label.hide()
            self.tabbed_editor_container.show()
        except Exception as e:
            pass

    def copy_api_template(self, template_data, target_folder_id=None):
        """复制接口模板到剪贴板"""
        if not self.current_project:
            return

        # 检查模板数据是否有效
        if not template_data or 'name' not in template_data:
            return

        # 保存复制的模板数据到剪贴板，用于粘贴操作
        self.copied_template_data = template_data.copy()
        
        # 如果指定了目标文件夹ID，则设置到副本中
        if target_folder_id is not None:
            self.copied_template_data['folder_id'] = target_folder_id

    def paste_with_edit(self, target_data):
        """粘贴接口模板并自动进入编辑页面"""
        # 检查是否已复制模板数据
        if not hasattr(self, 'copied_template_data') or not self.copied_template_data:
            return
            
        # 根据目标数据类型决定粘贴位置
        if target_data['type'] == 'folder':
            # 粘贴到文件夹
            folder_data = target_data['data']
            
            # 检查文件夹数据是否有效
            if not folder_data or 'id' not in folder_data or 'name' not in folder_data:
                return
                
            # 检查目标文件夹下是否存在同名接口
            original_name = self.copied_template_data['name']
            try:
                if self.api_service.check_template_name_exists(self.current_project, folder_data['id'], original_name):
                    # 存在同名接口，提示用户
                    from PyQt5.QtWidgets import QMessageBox
                    reply = QMessageBox.question(self, "同名接口", 
                                               f"文件夹 '{folder_data['name']}' 下已存在名为 '{original_name}' 的接口。\n是否继续粘贴？",
                                               QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                    if reply == QMessageBox.No:
                        return
            except Exception as e:
                return
                
            # 执行粘贴操作：创建模板副本
            try:
                # 创建模板副本数据
                template_copy = self.copied_template_data.copy()
                template_copy.pop('id', None)  # 移除原始ID
                
                # 生成新的副本名称
                template_copy['name'] = self.generate_copy_name(original_name, folder_data['id'])
                template_copy['project_id'] = self.current_project  # 确保项目ID正确
                template_copy['folder_id'] = folder_data['id']  # 设置目标文件夹ID
                
                # 创建新的模板
                new_template = self.api_service.create_template(template_copy)
                self.load_api_tree()
                self.data_changed.emit()
                
                # 自动打开编辑页面
                self.tabbed_editor.open_template(new_template)
                self.info_label.hide()
                self.tabbed_editor_container.show()
                
            except Exception as e:
                pass
        else:
            # 粘贴到根目录
            # 检查根目录下是否存在同名接口
            original_name = self.copied_template_data['name']
            try:
                if self.api_service.check_template_name_exists(self.current_project, None, original_name):
                    # 存在同名接口，提示用户
                    from PyQt5.QtWidgets import QMessageBox
                    reply = QMessageBox.question(self, "同名接口", 
                                               f"根目录下已存在名为 '{original_name}' 的接口。\n是否继续粘贴？",
                                               QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                    if reply == QMessageBox.No:
                        return
            except Exception as e:
                return
                
            # 执行粘贴操作：创建模板副本
            try:
                # 创建模板副本数据
                template_copy = self.copied_template_data.copy()
                template_copy.pop('id', None)  # 移除原始ID
                
                # 生成新的副本名称
                template_copy['name'] = self.generate_copy_name(original_name, None)
                template_copy['project_id'] = self.current_project  # 确保项目ID正确
                template_copy['folder_id'] = None  # 设置为根目录
                
                # 创建新的模板
                new_template = self.api_service.create_template(template_copy)
                self.load_api_tree()
                self.data_changed.emit()
                
                # 自动打开编辑页面
                self.tabbed_editor.open_template(new_template)
                self.info_label.hide()
                self.tabbed_editor_container.show()
                
            except Exception as e:
                pass

    def delete_selected_folder(self):
        """删除选中的文件夹"""
        if not self.current_folder:
            QMessageBox.warning(self, "提示", "请先选择一个文件夹")
            return
            
        self.delete_api_folder(self.current_folder)

    def delete_api_folder(self, folder_data):
        """删除接口文件夹"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除文件夹 '{folder_data['name']}' 吗？\n此操作将同时删除文件夹下的所有接口模板！",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.folder_service.delete_folder(folder_data['id'])
                self.load_api_tree()
                self.data_changed.emit()
                self.info_label.show()
                # 删除后重置当前选中的文件夹
                self.current_folder = None
                self.delete_folder_btn.setEnabled(False)
                Toast.success(self, "文件夹删除成功")
            except Exception as e:
                Toast.error(self, f"删除文件夹失败: {str(e)}")

    # rename_api_template方法已删除，接口模板重命名功能已移除