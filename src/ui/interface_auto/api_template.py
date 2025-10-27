import os
import json
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
                             QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QTabWidget, QGroupBox, QFormLayout, QComboBox,
                             QHeaderView, QInputDialog, QTableWidget, QTableWidgetItem,
                             QSplitter, QToolBar, QAction, QToolButton, QMenu,
                             QFileDialog, QApplication, QScrollArea, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QMimeData
from PyQt5.QtGui import QIcon, QFont, QDrag, QPixmap, QColor
from src.core.services.api_folder_service import ApiFolderService
from src.core.services.api_template_service import ApiTemplateService
from src.core.services.project_service import ProjectService
from src.core.models.interface_models import ApiTemplate, ApiFolder


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
        tab_widget = QTabWidget()

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

        # 请求方法选择
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("请求方法:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
        method_layout.addWidget(self.method_combo)
        method_layout.addStretch()

        # URL路径
        url_layout = QFormLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("例如: /api/v1/users")
        url_layout.addRow("URL路径:", self.url_edit)

        # Headers配置
        headers_group = QGroupBox("请求头(Headers)")
        headers_layout = QVBoxLayout(headers_group)
        self.headers_table = QTableWidget()
        self.headers_table.setColumnCount(2)
        self.headers_table.setHorizontalHeaderLabels(["Header名称", "Header值"])
        self.headers_table.horizontalHeader().setStretchLastSection(True)
        headers_layout.addWidget(self.headers_table)

        # 参数配置
        params_group = QGroupBox("查询参数(Query Parameters)")
        params_layout = QVBoxLayout(params_group)
        self.params_table = QTableWidget()
        self.params_table.setColumnCount(2)
        self.params_table.setHorizontalHeaderLabels(["参数名", "参数值"])
        self.params_table.horizontalHeader().setStretchLastSection(True)
        params_layout.addWidget(self.params_table)

        # 请求体配置
        body_group = QGroupBox("请求体(Body)")
        body_layout = QVBoxLayout(body_group)
        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText('请输入JSON格式的请求体，例如: {"key": "value"}')
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


class ApiTemplateManager(QWidget):
    """接口模板管理页面"""
    data_changed = pyqtSignal()  # 数据变化信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.api_service = ApiTemplateService()
        self.project_service = ProjectService()
        self.folder_service = ApiFolderService()
        self.current_project = None
        self.current_folder = None
        self.current_template = None
        self.init_ui()
        self.load_projects()

    def refresh_project_list(self):
        """刷新项目下拉列表"""
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
            QMessageBox.warning(self, "刷新失败", f"刷新项目列表失败: {str(e)}")

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：项目选择和接口树
        left_widget = QWidget()
        left_widget.setMaximumWidth(400)
        left_layout = QVBoxLayout(left_widget)

        # 项目选择
        project_layout = QHBoxLayout()
        project_layout.addWidget(QLabel("选择项目:"))
        self.project_combo = QComboBox()
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        project_layout.addWidget(self.project_combo)
        left_layout.addLayout(project_layout)

        # 工具栏
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))

        self.add_folder_action = QAction("新建文件夹", self)
        self.add_folder_action.triggered.connect(self.add_api_folder)
        self.add_folder_action.setIcon(self.get_icon("folder_add.png"))

        self.add_template_action = QAction("新建接口", self)
        self.add_template_action.triggered.connect(self.add_api_template)
        self.add_template_action.setIcon(self.get_icon("api_add.png"))

        self.import_action = QAction("导入", self)
        self.import_action.triggered.connect(self.import_templates)
        self.import_action.setIcon(self.get_icon("import.png"))

        self.export_action = QAction("导出", self)
        self.export_action.triggered.connect(self.export_templates)
        self.export_action.setIcon(self.get_icon("export.png"))

        toolbar.addAction(self.add_folder_action)
        toolbar.addAction(self.add_template_action)
        toolbar.addSeparator()
        toolbar.addAction(self.import_action)
        toolbar.addAction(self.export_action)

        left_layout.addWidget(toolbar)

        # 接口树
        self.tree_widget = DraggableTreeWidget()
        self.tree_widget.setHeaderLabels(["接口模板"])
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_tree_context_menu)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        self.tree_widget.itemDoubleClicked.connect(self.on_tree_item_double_clicked)

        left_layout.addWidget(self.tree_widget)

        # 右侧：接口详情
        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)

        # 初始提示
        self.info_label = QLabel("请选择接口模板查看或编辑详细信息")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #666; font-size: 14px; margin: 20px;")
        detail_layout.addWidget(self.info_label)

        # 详情容器（初始隐藏）
        self.detail_container = QWidget()
        self.detail_container.hide()
        detail_container_layout = QVBoxLayout(self.detail_container)

        # 接口基本信息
        basic_info_group = QGroupBox("接口信息")
        basic_layout = QFormLayout(basic_info_group)

        self.template_name_label = QLabel()
        self.template_method_label = QLabel()
        self.template_url_label = QLabel()
        self.template_desc_label = QLabel()
        self.template_desc_label.setWordWrap(True)

        basic_layout.addRow("接口名称:", self.template_name_label)
        basic_layout.addRow("请求方法:", self.template_method_label)
        basic_layout.addRow("URL路径:", self.template_url_label)
        basic_layout.addRow("接口描述:", self.template_desc_label)

        # 请求详情
        request_group = QGroupBox("请求详情")
        request_layout = QVBoxLayout(request_group)

        self.request_tabs = QTabWidget()

        # Headers Tab
        headers_tab = QWidget()
        headers_layout = QVBoxLayout(headers_tab)
        self.headers_table = QTableWidget()
        self.headers_table.setColumnCount(2)
        self.headers_table.setHorizontalHeaderLabels(["Header名称", "Header值"])
        self.headers_table.horizontalHeader().setStretchLastSection(True)
        headers_layout.addWidget(self.headers_table)

        # 参数 Tab
        params_tab = QWidget()
        params_layout = QVBoxLayout(params_tab)
        self.params_table = QTableWidget()
        self.params_table.setColumnCount(2)
        self.params_table.setHorizontalHeaderLabels(["参数名", "参数值"])
        self.params_table.horizontalHeader().setStretchLastSection(True)
        params_layout.addWidget(self.params_table)

        # 请求体 Tab
        body_tab = QWidget()
        body_layout = QVBoxLayout(body_tab)
        self.body_text = QTextEdit()
        self.body_text.setReadOnly(True)
        body_layout.addWidget(self.body_text)

        self.request_tabs.addTab(headers_tab, "Headers")
        self.request_tabs.addTab(params_tab, "参数")
        self.request_tabs.addTab(body_tab, "请求体")

        request_layout.addWidget(self.request_tabs)

        # 操作按钮
        button_layout = QHBoxLayout()
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.clicked.connect(self.edit_current_template)
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.delete_current_template)
        self.test_btn = QPushButton("测试接口")
        self.test_btn.clicked.connect(self.test_current_template)

        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.test_btn)
        button_layout.addStretch()

        detail_container_layout.addWidget(basic_info_group)
        detail_container_layout.addWidget(request_group)
        detail_container_layout.addLayout(button_layout)

        detail_layout.addWidget(self.detail_container)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.detail_widget)
        splitter.setSizes([300, 700])

        main_layout.addWidget(splitter)

        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
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

    def get_icon(self, icon_name):
        """获取图标"""
        try:
            icon_path = os.path.join("src", "ui", "interface_auto", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
        except:
            pass
        return QIcon()

    def load_projects(self):
        """加载项目列表"""
        try:
            projects = self.project_service.get_all_projects()
            self.project_combo.clear()
            for project in projects:
                self.project_combo.addItem(project['name'], project['id'])

            if projects:
                self.current_project = projects[0]['id']
                self.load_api_tree()

        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"加载项目列表失败: {str(e)}")

    def on_project_changed(self, index):
        """项目选择变化"""
        if index >= 0:
            self.current_project = self.project_combo.currentData()
            self.load_api_tree()

    def load_api_tree(self):
        """加载接口树"""
        self.tree_widget.clear()

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
                template_item.setIcon(0, self.get_icon("api.png"))

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
            QMessageBox.warning(self, "加载失败", f"加载接口树失败: {str(e)}")

    def on_tree_item_clicked(self, item):
        """树形项目点击事件"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type = data['type']
        item_data = data['data']

        if item_type == 'folder':
            self.current_folder = item_data
            self.current_template = None
            self.show_folder_info()
        else:
            self.current_template = item_data
            self.current_folder = None
            self.show_template_details(item_data)

    def on_tree_item_double_clicked(self, item):
        """树形项目双击事件"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        if data['type'] == 'template':
            self.edit_api_template(data['data'])

    def show_folder_info(self):
        """显示文件夹信息"""
        self.info_label.hide()
        self.detail_container.show()

        # 清空详情显示
        self.template_name_label.setText("")
        self.template_method_label.setText("")
        self.template_url_label.setText("")
        self.template_desc_label.setText("")
        self.headers_table.setRowCount(0)
        self.params_table.setRowCount(0)
        self.body_text.clear()

        # 隐藏测试按钮
        self.test_btn.hide()

    def show_template_details(self, template_data):
        """显示接口模板详情"""
        self.info_label.hide()
        self.detail_container.show()
        self.test_btn.show()

        # 基本信息
        self.template_name_label.setText(template_data.get('name', ''))
        self.template_method_label.setText(template_data.get('method', ''))
        self.template_url_label.setText(template_data.get('url_path', ''))
        self.template_desc_label.setText(template_data.get('description', ''))

        # Headers
        headers = template_data.get('headers', {})
        self.headers_table.setRowCount(len(headers))
        for i, (key, value) in enumerate(headers.items()):
            self.headers_table.setItem(i, 0, QTableWidgetItem(key))
            self.headers_table.setItem(i, 1, QTableWidgetItem(str(value)))

        # 参数
        params = template_data.get('params', {})
        self.params_table.setRowCount(len(params))
        for i, (key, value) in enumerate(params.items()):
            self.params_table.setItem(i, 0, QTableWidgetItem(key))
            self.params_table.setItem(i, 1, QTableWidgetItem(str(value)))

        # 请求体
        body = template_data.get('body', {})
        if body:
            self.body_text.setText(json.dumps(body, indent=2, ensure_ascii=False))
        else:
            self.body_text.clear()

    def add_api_folder(self):
        """新增接口文件夹"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择项目")
            return

        parent_folder_id = None
        if self.current_folder:
            parent_folder_id = self.current_folder['id']

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
                QMessageBox.information(self, "成功", "文件夹创建成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建文件夹失败: {str(e)}")

    def add_api_template(self):
        """新增接口模板"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择项目")
            return

        folder_id = None
        if self.current_folder:
            folder_id = self.current_folder['id']

        dialog = ApiTemplateDialog(self, project_id=self.current_project, folder_id=folder_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "接口名称不能为空")
                return
            if not data['url_path']:
                QMessageBox.warning(self, "输入错误", "URL路径不能为空")
                return

            try:
                self.api_service.create_template(data)
                self.load_api_tree()
                self.data_changed.emit()
                QMessageBox.information(self, "成功", "接口模板创建成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建接口模板失败: {str(e)}")

    def edit_api_template(self, template_data):
        """编辑接口模板"""
        dialog = ApiTemplateDialog(self, template_data=template_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "接口名称不能为空")
                return
            if not data['url_path']:
                QMessageBox.warning(self, "输入错误", "URL路径不能为空")
                return

            try:
                self.api_service.update_template(template_data['id'], data)
                self.load_api_tree()
                self.data_changed.emit()

                # 如果当前正在查看这个模板，刷新详情
                if self.current_template and self.current_template['id'] == template_data['id']:
                    updated_template = self.api_service.get_template_by_id(template_data['id'])
                    self.show_template_details(updated_template)

                QMessageBox.information(self, "成功", "接口模板更新成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新接口模板失败: {str(e)}")

    def edit_current_template(self):
        """编辑当前选中的接口模板"""
        if self.current_template:
            self.edit_api_template(self.current_template)

    def delete_current_template(self):
        """删除当前选中的接口模板"""
        if self.current_template:
            self.delete_api_template(self.current_template)

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
                self.load_api_tree()
                self.data_changed.emit()
                self.info_label.show()
                self.detail_container.hide()
                QMessageBox.information(self, "成功", "接口模板删除成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除接口模板失败: {str(e)}")

    def test_current_template(self):
        """测试当前接口模板"""
        if not self.current_template:
            return

        # 这里可以调用请求引擎进行接口测试
        QMessageBox.information(self, "提示", "接口测试功能正在开发中...")

    def import_templates(self):
        """导入接口模板"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择项目")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择导入文件", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    templates_data = json.load(f)

                # 批量导入接口模板
                success_count = 0
                for template_data in templates_data:
                    try:
                        template_data['project_id'] = self.current_project
                        self.api_service.create_template(template_data)
                        success_count += 1
                    except Exception as e:
                        print(f"导入接口失败: {e}")

                self.load_api_tree()
                self.data_changed.emit()
                QMessageBox.information(self, "导入完成", f"成功导入 {success_count} 个接口模板")

            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"导入接口模板失败: {str(e)}")

    def export_templates(self):
        """导出接口模板"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择项目")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择导出位置", "api_templates.json", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                templates = self.api_service.get_templates_by_project(self.current_project)

                # 准备导出数据
                export_data = []
                for template in templates:
                    # 移除数据库相关字段
                    template_copy = template.copy()
                    for field in ['id', 'project_id', 'folder_id', 'created_at', 'updated_at']:
                        template_copy.pop(field, None)
                    export_data.append(template_copy)

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                QMessageBox.information(self, "导出成功", f"成功导出 {len(export_data)} 个接口模板")

            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出接口模板失败: {str(e)}")

    def show_tree_context_menu(self, position):
        """显示树形结构的右键菜单"""
        item = self.tree_widget.itemAt(position)
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

            add_template_action = QAction("新建接口", self)
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

            test_action = QAction("测试", self)
            test_action.triggered.connect(self.test_current_template)
            menu.addAction(test_action)

            menu.addSeparator()

            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda: self.delete_api_template(data['data']))
            menu.addAction(delete_action)

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
                QMessageBox.information(self, "成功", "文件夹更新成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新文件夹失败: {str(e)}")

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
                self.detail_container.hide()
                QMessageBox.information(self, "成功", "文件夹删除成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除文件夹失败: {str(e)}")