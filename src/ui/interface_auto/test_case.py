import os
import json
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
                             QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QTabWidget, QGroupBox, QFormLayout, QComboBox,
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
from src.core.services.project_service import ProjectService
from src.core.services.test_case_service import TestCaseService
from src.core.models.interface_models import TestCase, TestCaseStep
from src.ui.interface_auto.components.api_card import ApiCard
from src.ui.interface_auto.components.case_editor import CaseEditor
from src.utils.interface_utils.variable_manager import get_global_variable_manager


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
        tab_widget = QTabWidget()

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

        self.env_combo = QComboBox()
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
        self.case_service = TestCaseService()
        self.api_service = ApiTemplateService()
        self.project_service = ProjectService()
        self.folder_service = CaseFolderService()
        self.current_project = None
        self.current_folder = None
        self.current_case = None
        self.current_case_data = None
        self.init_ui()
        self.load_projects()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 第一栏：用例树
        left_widget = QWidget()
        left_widget.setMaximumWidth(350)
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
        self.add_folder_action.triggered.connect(self.add_case_folder)
        self.add_folder_action.setIcon(self.get_icon("folder_add.png"))

        self.add_case_action = QAction("新建用例", self)
        self.add_case_action.triggered.connect(self.add_test_case)
        self.add_case_action.setIcon(self.get_icon("case_add.png"))

        self.import_action = QAction("导入", self)
        self.import_action.triggered.connect(self.import_cases)
        self.import_action.setIcon(self.get_icon("import.png"))

        self.export_action = QAction("导出", self)
        self.export_action.triggered.connect(self.export_cases)
        self.export_action.setIcon(self.get_icon("export.png"))

        toolbar.addAction(self.add_folder_action)
        toolbar.addAction(self.add_case_action)
        toolbar.addSeparator()
        toolbar.addAction(self.import_action)
        toolbar.addAction(self.export_action)

        left_layout.addWidget(toolbar)

        # 用例树
        self.case_tree = QTreeWidget()
        self.case_tree.setHeaderLabels(["测试用例"])
        self.case_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.case_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        self.case_tree.itemClicked.connect(self.on_tree_item_clicked)

        left_layout.addWidget(self.case_tree)

        # 第二栏：接口模板列表
        middle_widget = QWidget()
        middle_widget.setMaximumWidth(300)
        middle_layout = QVBoxLayout(middle_widget)

        middle_layout.addWidget(QLabel("接口模板"))

        # 接口搜索
        search_layout = QHBoxLayout()
        self.api_search_edit = QLineEdit()
        self.api_search_edit.setPlaceholderText("搜索接口...")
        self.api_search_edit.textChanged.connect(self.filter_api_templates)
        search_layout.addWidget(self.api_search_edit)

        middle_layout.addLayout(search_layout)

        # 接口列表
        self.api_list = DraggableListWidget()
        self.api_list.setDragEnabled(True)

        middle_layout.addWidget(self.api_list)

        # 第三栏：用例编辑区
        self.case_editor = CaseEditor(self)
        self.case_editor.case_saved.connect(self.on_case_saved)
        self.case_editor.case_executed.connect(self.on_case_executed)

        splitter.addWidget(left_widget)
        splitter.addWidget(middle_widget)
        splitter.addWidget(self.case_editor)
        splitter.setSizes([300, 250, 800])

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
                self.load_case_tree()
                self.load_api_templates()

        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"加载项目列表失败: {str(e)}")

    def on_project_changed(self, index):
        """项目选择变化"""
        if index >= 0:
            self.current_project = self.project_combo.currentData()
            self.load_case_tree()
            self.load_api_templates()

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
                case_item.setIcon(0, self.get_icon("case.png"))

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
            QMessageBox.warning(self, "加载失败", f"加载用例树失败: {str(e)}")

    def load_api_templates(self):
        """加载接口模板列表"""
        try:
            if not self.current_project:
                return

            templates = self.api_service.get_templates_by_project(self.current_project)
            self.all_templates = templates
            self.filter_api_templates()

        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"加载接口模板失败: {str(e)}")

    def filter_api_templates(self):
        """过滤接口模板"""
        if not hasattr(self, 'all_templates'):
            return

        search_text = self.api_search_edit.text().lower()
        self.api_list.clear()

        for template in self.all_templates:
            if search_text in template['name'].lower() or search_text in template.get('description', '').lower():
                item = QListWidgetItem(f"{template['method']} {template['name']}")
                item.setData(Qt.UserRole, template)
                item.setToolTip(f"{template['method']} {template['url_path']}\n{template.get('description', '')}")
                self.api_list.addItem(item)

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
            self.case_editor.clear_editor()
        else:
            self.current_case = item_data
            self.current_folder = None
            self.load_case_details(item_data)

    def load_case_details(self, case_data):
        """加载用例详情"""
        try:
            # 获取用例完整数据（包括步骤）
            full_case_data = self.case_service.get_case_with_steps(case_data['id'])
            self.current_case_data = full_case_data
            self.case_editor.load_case(full_case_data)

        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"加载用例详情失败: {str(e)}")

    def on_case_saved(self, case_data):
        """用例保存事件"""
        self.load_case_tree()
        self.data_changed.emit()

    def on_case_executed(self, case_id, result):
        """用例执行事件"""
        # 这里可以处理执行结果，比如更新状态、显示通知等
        print(f"用例 {case_id} 执行完成: {result}")

    def add_case_folder(self):
        """新增用例文件夹"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择项目")
            return

        parent_folder_id = None
        if self.current_folder:
            parent_folder_id = self.current_folder['id']

        dialog = CaseFolderDialog(self, project_id=self.current_project, parent_folder_id=parent_folder_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "文件夹名称不能为空")
                return

            try:
                self.folder_service.create_folder(data)
                self.load_case_tree()
                self.data_changed.emit()
                QMessageBox.information(self, "成功", "文件夹创建成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建文件夹失败: {str(e)}")

    def add_test_case(self):
        """新增测试用例"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择项目")
            return

        folder_id = None
        if self.current_folder:
            folder_id = self.current_folder['id']

        dialog = TestCaseDialog(self, project_id=self.current_project, folder_id=folder_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "用例名称不能为空")
                return

            try:
                case_id = self.case_service.create_case(data)
                self.load_case_tree()
                self.data_changed.emit()

                # 加载新创建的用例
                new_case = self.case_service.get_case_by_id(case_id)
                self.load_case_details(new_case)

                QMessageBox.information(self, "成功", "测试用例创建成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建测试用例失败: {str(e)}")

    def edit_test_case(self, case_data):
        """编辑测试用例"""
        dialog = TestCaseDialog(self, case_data=case_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "用例名称不能为空")
                return

            try:
                self.case_service.update_case(case_data['id'], data)
                self.load_case_tree()
                self.data_changed.emit()

                # 如果当前正在编辑这个用例，刷新详情
                if self.current_case and self.current_case['id'] == case_data['id']:
                    updated_case = self.case_service.get_case_by_id(case_data['id'])
                    self.load_case_details(updated_case)

                QMessageBox.information(self, "成功", "测试用例更新成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新测试用例失败: {str(e)}")

    def delete_test_case(self, case_data):
        """删除测试用例"""
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
                self.case_editor.clear_editor()
                QMessageBox.information(self, "成功", "测试用例删除成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除测试用例失败: {str(e)}")

    def import_cases(self):
        """导入测试用例"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择项目")
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
                QMessageBox.information(self, "导入完成", f"成功导入 {success_count} 个测试用例")

            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"导入测试用例失败: {str(e)}")

    def export_cases(self):
        """导出测试用例"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择项目")
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

                QMessageBox.information(self, "导出成功", f"成功导出 {len(export_data)} 个测试用例")

            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出测试用例失败: {str(e)}")

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
            add_case_action.triggered.connect(self.add_test_case)
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

    def edit_case_folder(self, folder_data):
        """编辑用例文件夹"""
        dialog = CaseFolderDialog(self, folder_data=folder_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "文件夹名称不能为空")
                return

            try:
                self.folder_service.update_folder(folder_data['id'], data)
                self.load_case_tree()
                self.data_changed.emit()
                QMessageBox.information(self, "成功", "文件夹更新成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新文件夹失败: {str(e)}")

    def delete_case_folder(self, folder_data):
        """删除用例文件夹"""
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
                self.case_editor.clear_editor()
                QMessageBox.information(self, "成功", "文件夹删除成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除文件夹失败: {str(e)}")

    def run_test_case(self, case_data):
        """执行测试用例"""
        if not self.current_case_data or self.current_case_data['id'] != case_data['id']:
            # 如果当前没有加载这个用例，先加载
            self.load_case_details(case_data)

        # 触发用例执行
        self.case_editor.execute_case()