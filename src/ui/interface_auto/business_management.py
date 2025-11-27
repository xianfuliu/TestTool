import os
import json
import sys
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
                             QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QGroupBox, QFormLayout,
                             QHeaderView, QInputDialog, QCheckBox, QSpinBox,
                             QListWidget, QListWidgetItem, QSplitter, QToolBar,
                             QAction, QToolButton, QMenu, QApplication, QDateTimeEdit,
                             QProgressBar, QFrame, QScrollArea, QGridLayout,
                             QTableWidget, QTableWidgetItem, QListWidget, QAbstractItemView,
                             QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
                             QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QDateTime, QMimeData, QPoint
from PyQt5.QtGui import QIcon, QFont, QColor, QDrag, QPixmap, QCursor
from src.core.services.project_service import ProjectService
from src.core.services.business_service import BusinessService
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelTabWidget



class BusinessGroupDialog(QDialog):
    """业务分组编辑对话框"""

    def __init__(self, parent=None, group_data=None):
        super().__init__(parent)
        self.group_data = group_data or {}
        self.is_edit = bool(group_data)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑业务分组" if self.is_edit else "新增业务分组")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout(self)

        # 表单布局
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入业务分组名称")
        if self.group_data:
            self.name_edit.setText(self.group_data.get('name', ''))

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        self.desc_edit.setPlaceholderText("请输入业务分组描述")
        if self.group_data:
            self.desc_edit.setText(self.group_data.get('description', ''))

        form_layout.addRow("分组名称:", self.name_edit)
        form_layout.addRow("分组描述:", self.desc_edit)

        # 按钮布局
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(button_box)

    def get_data(self):
        return {
            'name': self.name_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip()
        }


class ProjectDialog(QDialog):
    """项目编辑对话框"""

    def __init__(self, parent=None, project_data=None, group_id=None):
        super().__init__(parent)
        self.project_data = project_data or {}
        self.group_id = group_id
        self.is_edit = bool(project_data)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑项目" if self.is_edit else "新增项目")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout(self)

        # 表单布局
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入项目名称")
        if self.project_data:
            self.name_edit.setText(self.project_data.get('name', ''))

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        self.desc_edit.setPlaceholderText("请输入项目描述")
        if self.project_data:
            self.desc_edit.setText(self.project_data.get('description', ''))

        form_layout.addRow("项目名称:", self.name_edit)
        form_layout.addRow("项目描述:", self.desc_edit)

        # 按钮布局
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(button_box)

    def get_data(self):
        return {
            'name': self.name_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip(),
            'group_id': self.group_id or self.project_data.get('group_id')
        }


class BusinessManagement(QWidget):
    """业务管理页面"""
    data_changed = pyqtSignal()  # 数据变化信号
    business_changed = pyqtSignal(int)  # 业务切换信号，参数为业务分组ID

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.business_service = None
        self.project_service = None
        self.current_group = None
        self.current_project = None
        self.business_groups = []  # 存储业务分组列表
        self.initial_business_ready = False  # 初始业务切换状态
        self.init_ui()
        # 延迟加载数据，避免启动时数据库连接失败导致弹窗
        QTimer.singleShot(100, self.delayed_load_data)

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # 左侧：树形结构
        left_widget = QWidget()
        left_widget.setMaximumWidth(350)
        left_layout = QVBoxLayout(left_widget)

        # 当前业务标题和下拉框
        group_header_layout = QHBoxLayout()
        group_header_layout.addWidget(QLabel("当前业务"))
        
        # 业务列表下拉框
        self.business_combo = QComboBox()
        self.business_combo.setMinimumWidth(150)
        self.business_combo.setStyleSheet("""
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
        # 暂时不连接业务切换信号，等待所有页面准备好后再连接
        # self.business_combo.currentTextChanged.connect(self.on_business_changed)
        group_header_layout.addWidget(self.business_combo)
        
        group_header_layout.addStretch()
        
        self.add_group_btn = QPushButton()
        self.add_group_btn.setIcon(self.get_icon("add.png"))
        self.add_group_btn.setFixedSize(20, 20)  # 减小按钮尺寸
        self.add_group_btn.setToolTip("新增分组")
        self.add_group_btn.clicked.connect(self.add_business_group)
        self.add_group_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                padding: 0px;
                margin: 0px;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 0.2);
            }
        """)
        
        group_header_layout.addWidget(self.add_group_btn)

        # 业务分组树
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["业务分组/项目"])
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_tree_context_menu)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)

        # 右侧：详细信息
        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)



        # 分组/项目信息标签
        self.info_label = QLabel("请选择业务分组或项目查看详细信息")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #666; font-size: 14px; margin: 20px;")

        # 详细信息容器（初始隐藏）
        self.detail_container = QWidget()
        self.detail_container.hide()

        detail_tabs = NoWheelTabWidget()

        # 基本信息Tab
        basic_info_tab = QWidget()
        basic_layout = QFormLayout(basic_info_tab)

        self.name_label = QLabel()
        self.desc_label = QLabel()
        self.create_time_label = QLabel()
        self.update_time_label = QLabel()

        basic_layout.addRow("名称:", self.name_label)
        basic_layout.addRow("描述:", self.desc_label)
        basic_layout.addRow("创建时间:", self.create_time_label)
        basic_layout.addRow("更新时间:", self.update_time_label)

        # 统计信息Tab
        stats_tab = QWidget()
        stats_layout = QFormLayout(stats_tab)

        self.project_count_label = QLabel()
        self.api_count_label = QLabel()
        self.case_count_label = QLabel()

        stats_layout.addRow("项目数量:", self.project_count_label)
        stats_layout.addRow("接口数量:", self.api_count_label)
        stats_layout.addRow("用例数量:", self.case_count_label)

        detail_tabs.addTab(basic_info_tab, "基本信息")
        detail_tabs.addTab(stats_tab, "统计信息")

        # 操作按钮
        button_layout = QHBoxLayout()
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.clicked.connect(self.edit_current_item)
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.delete_current_item)

        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addStretch()

        detail_container_layout = QVBoxLayout(self.detail_container)
        detail_container_layout.addWidget(detail_tabs)
        detail_container_layout.addLayout(button_layout)

        detail_layout.addWidget(self.info_label)
        detail_layout.addWidget(self.detail_container)

        # 组装左侧布局
        left_layout.addLayout(group_header_layout)
        left_layout.addWidget(self.tree_widget)

        # 添加到主布局
        main_layout.addWidget(left_widget)
        main_layout.addWidget(self.detail_widget)

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
            QLabel {
                padding: 2px;
            }
        """)

    def get_icon(self, icon_name):
        """获取图标"""
        try:
            # 打包后路径处理：尝试从 PyInstaller 临时解压目录加载
            if getattr(sys, 'frozen', False):
                # 打包后的可执行文件路径
                base_path = sys._MEIPASS
                # 尝试从打包后的 resources/icons 目录加载
                icon_path = os.path.join(base_path, "src", "resources", "icons", icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
                
                # 尝试直接加载图标文件
                icon_path = os.path.join(base_path, icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
                
                # 尝试从当前目录加载
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "icons", icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
            
            # 开发环境：尝试从 ui/interface_auto/icons 目录加载
            icon_path = os.path.join("src", "ui", "interface_auto", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
            
            # 尝试从 resources/icons 目录加载
            icon_path = os.path.join("src", "resources", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
        except:
            pass
        return QIcon()

    def format_datetime(self, dt):
        """格式化日期时间显示"""
        if not dt:
            return ""
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return str(dt)

    def delayed_load_data(self):
        """延迟加载数据，初始化服务对象"""
        try:
            self.business_service = BusinessService()
            self.project_service = ProjectService()
            self.load_data()
        except Exception as e:
            print(f"初始化服务失败: {e}")
            # 静默处理，不显示弹窗

    def on_business_changed(self, business_name):
        """业务切换事件处理"""
        if not business_name:
            return
            
        # 根据业务名称查找对应的业务分组ID
        for group in self.business_groups:
            if group['name'] == business_name:
                # 发射业务切换信号，传递业务分组ID
                self.business_changed.emit(group['id'])
                break
    
    def trigger_initial_business_change(self):
        """手动触发初始业务切换"""
        print(f"trigger_initial_business_change调用开始")
        print(f"initial_business_ready状态: {self.initial_business_ready}")
        print(f"business_groups是否存在: {self.business_groups is not None}")
        print(f"business_groups长度: {len(self.business_groups) if self.business_groups else 0}")
        
        if self.initial_business_ready and self.business_groups:
            current_text = self.business_combo.currentText()
            print(f"下拉框当前文本: '{current_text}'")
            if current_text:
                print(f"触发初始业务切换: {current_text}")
                
                # 重新连接业务切换信号
                self.business_combo.currentTextChanged.connect(self.on_business_changed)
                
                # 触发业务切换
                self.on_business_changed(current_text)
                self.initial_business_ready = False  # 重置状态
                print("业务切换完成，initial_business_ready已重置为False")
        else:
            print("条件不满足，跳过业务切换")
            print(f"initial_business_ready: {self.initial_business_ready}")
            print(f"business_groups: {self.business_groups}")
            
        print("trigger_initial_business_change调用结束")

    def load_data(self):
        """加载业务分组和项目数据"""
        self.tree_widget.clear()
        
        # 清空并重新填充下拉框
        self.business_combo.clear()
        self.business_groups.clear()

        # 检查服务对象是否已初始化
        if self.business_service is None or self.project_service is None:
            return

        try:
            # 加载业务分组
            groups = self.business_service.get_all_groups()
            self.business_groups = groups  # 存储业务分组列表
            
            for group in groups:
                # 添加到树形结构
                group_item = QTreeWidgetItem(self.tree_widget)
                group_item.setText(0, group['name'])
                group_item.setData(0, Qt.UserRole, {'type': 'group', 'data': group})
                group_item.setIcon(0, self.get_icon("group.png"))
                
                # 添加到下拉框
                self.business_combo.addItem(group['name'])

                # 加载该分组下的项目
                projects = self.project_service.get_projects_by_group(group['id'])
                for project in projects:
                    project_item = QTreeWidgetItem(group_item)
                    project_item.setText(0, project['name'])
                    project_item.setData(0, Qt.UserRole, {'type': 'project', 'data': project})
                    project_item.setIcon(0, self.get_icon("project.png"))

                group_item.setExpanded(True)

        except Exception as e:
            print(f"加载业务数据失败: {str(e)}")
            # 静默处理，不显示弹窗
        finally:
            # 数据加载完成后，如果存在业务分组，设置下拉框但延迟触发业务切换信号
            if self.business_groups:
                # 设置下拉框当前索引为0（第一个业务）
                self.business_combo.setCurrentIndex(0)
                # 延迟触发业务切换信号，等待所有页面都创建完成
                self.initial_business_ready = True
                print("业务数据加载完成，等待手动触发初始业务切换")

    def on_tree_item_clicked(self, item):
        """树形项目点击事件"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type = data['type']
        item_data = data['data']

        if item_type == 'group':
            self.current_group = item_data
            self.current_project = None
            self.show_group_details(item_data)
        else:
            self.current_project = item_data
            self.current_group = None
            self.show_project_details(item_data)

    def show_group_details(self, group_data):
        """显示业务分组详情"""
        self.info_label.hide()
        self.detail_container.show()

        # 基本信息
        self.name_label.setText(group_data.get('name', ''))
        self.desc_label.setText(group_data.get('description', ''))

        # 格式化日期时间显示
        created_at = group_data.get('created_at', '')
        updated_at = group_data.get('updated_at', '')

        self.create_time_label.setText(self.format_datetime(created_at))
        self.update_time_label.setText(self.format_datetime(updated_at))

        # 统计信息
        stats = self.business_service.get_group_stats(group_data['id'])
        self.project_count_label.setText(str(stats.get('project_count', 0)))
        self.api_count_label.setText(str(stats.get('api_count', 0)))
        self.case_count_label.setText(str(stats.get('case_count', 0)))

    def show_project_details(self, project_data):
        """显示项目详情"""
        self.info_label.hide()
        self.detail_container.show()

        # 基本信息
        self.name_label.setText(project_data.get('name', ''))
        self.desc_label.setText(project_data.get('description', ''))

        # 格式化日期时间显示
        created_at = project_data.get('created_at', '')
        updated_at = project_data.get('updated_at', '')

        self.create_time_label.setText(self.format_datetime(created_at))
        self.update_time_label.setText(self.format_datetime(updated_at))

        # 统计信息
        stats = self.project_service.get_project_stats(project_data['id'])
        self.project_count_label.setText("-")  # 项目没有子项目
        self.api_count_label.setText(str(stats.get('api_count', 0)))
        self.case_count_label.setText(str(stats.get('case_count', 0)))

    def add_business_group(self):
        """新增业务分组"""
        dialog = BusinessGroupDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "分组名称不能为空")
                return

            try:
                self.business_service.create_group(data)
                self.load_data()
                self.data_changed.emit()
                QMessageBox.information(self, "成功", "业务分组创建成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建业务分组失败: {str(e)}")

    def add_project(self, group_id):
        """新增项目"""
        dialog = ProjectDialog(self, group_id=group_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "项目名称不能为空")
                return

            try:
                self.project_service.create_project(data)
                self.load_data()
                self.data_changed.emit()
                QMessageBox.information(self, "成功", "项目创建成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建项目失败: {str(e)}")

    def edit_current_item(self):
        """编辑当前选中的项目"""
        if self.current_group:
            self.edit_business_group(self.current_group)
        elif self.current_project:
            self.edit_project(self.current_project)

    def edit_business_group(self, group_data):
        """编辑业务分组"""
        dialog = BusinessGroupDialog(self, group_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "分组名称不能为空")
                return

            try:
                self.business_service.update_group(group_data['id'], data)
                self.load_data()
                self.data_changed.emit()
                QMessageBox.information(self, "成功", "业务分组更新成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新业务分组失败: {str(e)}")

    def edit_project(self, project_data):
        """编辑项目"""
        dialog = ProjectDialog(self, project_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "项目名称不能为空")
                return

            try:
                self.project_service.update_project(project_data['id'], data)
                self.load_data()
                self.data_changed.emit()
                QMessageBox.information(self, "成功", "项目更新成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新项目失败: {str(e)}")

    def delete_current_item(self):
        """删除当前选中的项目"""
        if self.current_group:
            self.delete_business_group(self.current_group)
        elif self.current_project:
            self.delete_project(self.current_project)

    def delete_business_group(self, group_data):
        """删除业务分组"""
        msg_box = QMessageBox(QMessageBox.Question, "确认删除", 
                            f"确定要删除业务分组 '{group_data['name']}' 吗？\n此操作将同时删除该分组下的所有项目！")
        confirm_button = msg_box.addButton("确认", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_button)
        msg_box.exec_()
        reply = QMessageBox.Yes if msg_box.clickedButton() == confirm_button else QMessageBox.No

        if reply == QMessageBox.Yes:
            try:
                self.business_service.delete_group(group_data['id'])
                self.load_data()
                self.data_changed.emit()
                self.info_label.show()
                self.detail_container.hide()
                QMessageBox.information(self, "成功", "业务分组删除成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除业务分组失败: {str(e)}")

    def delete_project(self, project_data):
        """删除项目"""
        msg_box = QMessageBox(QMessageBox.Question, "确认删除", 
                            f"确定要删除项目 '{project_data['name']}' 吗？")
        confirm_button = msg_box.addButton("确认", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_button)
        msg_box.exec_()
        reply = QMessageBox.Yes if msg_box.clickedButton() == confirm_button else QMessageBox.No

        if reply == QMessageBox.Yes:
            try:
                self.project_service.delete_project(project_data['id'])
                self.load_data()
                self.data_changed.emit()
                self.info_label.show()
                self.detail_container.hide()
                QMessageBox.information(self, "成功", "项目删除成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除项目失败: {str(e)}")

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

        if data['type'] == 'group':
            # 业务分组的右键菜单
            add_project_action = QAction("新增项目", self)
            add_project_action.triggered.connect(lambda: self.add_project(data['data']['id']))
            menu.addAction(add_project_action)

            menu.addSeparator()

            edit_action = QAction("编辑", self)
            edit_action.triggered.connect(lambda: self.edit_business_group(data['data']))
            menu.addAction(edit_action)

            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda: self.delete_business_group(data['data']))
            menu.addAction(delete_action)

        else:
            # 项目的右键菜单
            edit_action = QAction("编辑", self)
            edit_action.triggered.connect(lambda: self.edit_project(data['data']))
            menu.addAction(edit_action)

            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda: self.delete_project(data['data']))
            menu.addAction(delete_action)

        menu.exec_(self.tree_widget.mapToGlobal(position))