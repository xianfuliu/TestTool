"""
变量管理页面
支持项目维度的变量管理，包含系统变量（只读）和全局变量（增删改查）
"""

import os
import json
import sys
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
                             QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QGroupBox, QFormLayout, QHeaderView, QInputDialog,
                             QTableWidget, QTableWidgetItem, QSplitter, QFrame,
                             QComboBox, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QDateTime
from PyQt5.QtGui import QIcon, QFont, QColor
from src.core.services.project_service import ProjectService
from src.core.services.global_variable_service import GlobalVariableService
from src.utils.interface_utils.variable_manager import VariableManager
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelTabWidget
from src.ui.widgets.toast_tips import Toast


class VariableDialog(QDialog):
    """变量编辑对话框"""

    def __init__(self, parent=None, variable_data=None, project_id=None):
        super().__init__(parent)
        self.variable_data = variable_data or {}
        self.project_id = project_id
        self.is_edit = bool(variable_data)
        self.parent_variable_management = parent  # 保存父级变量管理对象引用
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑变量" if self.is_edit else "新增变量")
        self.setFixedSize(500, 400)

        layout = QVBoxLayout(self)

        # 表单布局
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入变量名（支持字母、数字、下划线）")
        if self.variable_data:
            self.name_edit.setText(self.variable_data.get('name', ''))

        self.value_edit = QTextEdit()
        self.value_edit.setMaximumHeight(100)
        self.value_edit.setPlaceholderText("请输入变量值")
        if self.variable_data:
            value = self.variable_data.get('value', '')
            if isinstance(value, (dict, list)):
                self.value_edit.setText(json.dumps(value, indent=2, ensure_ascii=False))
            else:
                self.value_edit.setText(str(value))

        self.type_combo = QComboBox()
        self.type_combo.addItems(["string", "number", "boolean", "json"])
        if self.variable_data:
            var_type = self.variable_data.get('variable_type', 'string')
            index = self.type_combo.findText(var_type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("变量描述（可选）")
        if self.variable_data:
            self.desc_edit.setText(self.variable_data.get('description', ''))

        form_layout.addRow("变量名:", self.name_edit)
        form_layout.addRow("变量类型:", self.type_combo)
        form_layout.addRow("变量值:", self.value_edit)
        form_layout.addRow("变量描述:", self.desc_edit)

        # 按钮布局
        button_box = QDialogButtonBox()
        confirm_button = button_box.addButton("确认", QDialogButtonBox.AcceptRole)
        cancel_button = button_box.addButton("取消", QDialogButtonBox.RejectRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(button_box)

    def accept(self):
        """重写accept方法，添加变量名重复校验"""
        # 获取输入的变量名
        name = self.name_edit.text().strip()
        
        # 检查变量名是否为空
        if not name:
            Toast.warning(self, "警告", "变量名不能为空")
            return
        
        # 检查变量名是否重复
        if self.is_variable_name_duplicate(name):
            Toast.warning(self, "警告", "变量名已存在，请修改变量名")
            return
            
        # 调用父类的accept方法关闭对话框
        super().accept()
    
    def is_variable_name_duplicate(self, name):
        """检查变量名是否重复"""
        # 如果是编辑模式且变量名未改变，则不算重复
        if self.is_edit and name == self.variable_data.get('name', ''):
            return False
            
        # 获取父级变量管理对象的服务
        if hasattr(self.parent_variable_management, 'variable_service') and self.parent_variable_management.variable_service:
            variable_service = self.parent_variable_management.variable_service
            try:
                # 检查变量名是否已存在（在同一项目内）
                existing_variable = variable_service.get_global_variable_by_name(name, self.project_id)
                if existing_variable:
                    # 如果是编辑模式，且找到的变量就是正在编辑的变量，则不算重复
                    if self.is_edit and existing_variable.get('id') == self.variable_data.get('id'):
                        return False
                    return True
            except Exception as e:
                print(f"检查变量名重复时出错: {e}")
                return False
        return False

    def get_data(self):
        """获取表单数据"""
        name = self.name_edit.text().strip()
        var_type = self.type_combo.currentText()
        value_text = self.value_edit.toPlainText().strip()
        description = self.desc_edit.text().strip()

        # 解析变量值
        value = self.parse_value(value_text, var_type)

        return {
            'name': name,
            'variable_type': var_type,
            'value': value,
            'description': description,
            'project_id': self.project_id
        }

    def parse_value(self, value_text: str, var_type: str):
        """解析变量值"""
        if not value_text:
            return ''

        try:
            if var_type == 'number':
                if '.' in value_text:
                    return float(value_text)
                else:
                    return int(value_text)
            elif var_type == 'boolean':
                return value_text.lower() in ('true', '1', 'yes', 'y')
            elif var_type == 'json':
                return json.loads(value_text)
            else:
                return value_text
        except (ValueError, json.JSONDecodeError):
            return value_text


class VariableManagement(QWidget):
    """变量管理页面"""
    data_changed = pyqtSignal()  # 数据变化信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.project_service = None
        self.variable_service = None
        self.variable_manager = VariableManager()
        self.current_project = None
        self.current_business_id = None  # 当前选中的业务分组ID
        self.init_ui()
        # 延迟加载数据
        QTimer.singleShot(100, self.delayed_load_data)

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # 左侧：项目树形结构
        left_widget = QWidget()
        left_widget.setMaximumWidth(350)
        left_layout = QVBoxLayout(left_widget)

        # 项目标题
        project_header_layout = QHBoxLayout()
        project_header_layout.addWidget(QLabel("项目列表"))
        project_header_layout.addStretch()

        left_layout.addLayout(project_header_layout)

        # 项目树
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabels(["项目"])
        self.project_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.project_tree.itemClicked.connect(self.on_project_selected)

        left_layout.addWidget(self.project_tree)

        # 右侧：变量管理
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 项目信息标签
        self.project_info_label = QLabel("请选择项目查看变量")
        self.project_info_label.setAlignment(Qt.AlignCenter)
        self.project_info_label.setStyleSheet("color: #666; font-size: 14px; margin: 20px;")

        # 变量管理容器（初始隐藏）
        self.variable_container = QWidget()
        self.variable_container.hide()

        # 创建Tab页
        self.tab_widget = NoWheelTabWidget()

        # 全局变量Tab
        global_tab = QWidget()
        self.setup_global_tab(global_tab)

        # 系统变量Tab
        system_tab = QWidget()
        self.setup_system_tab(system_tab)

        self.tab_widget.addTab(global_tab, "全局变量")
        self.tab_widget.addTab(system_tab, "系统变量")

        right_layout.addWidget(self.project_info_label)
        right_layout.addWidget(self.variable_container)

        # 组装主布局
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget)

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
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)

    def setup_system_tab(self, parent):
        """设置系统变量Tab"""
        layout = QVBoxLayout(parent)

        # 系统变量说明
        info_label = QLabel("系统变量是预定义的变量，无法编辑但可以在任何地方使用")
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)

        # 系统变量树形控件 - 参考定时调度实现
        self.system_tree = QTreeWidget()
        self.system_tree.setColumnCount(4)
        self.system_tree.setHeaderLabels(["序号", "变量名", "值", "描述"])
        
        # 设置固定列宽 - 参考定时调度设计
        self.system_tree.setColumnWidth(0, 100)     # 序号
        self.system_tree.setColumnWidth(1, 450)    # 变量名
        self.system_tree.setColumnWidth(2, 600)    # 值
        
        # 设置列宽调整模式 - 参考定时调度实现
        header = self.system_tree.header()
        header.setSectionResizeMode(QHeaderView.Fixed)  # 其他列固定宽度
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # 描述列自适应拉伸
        header.setStretchLastSection(True)  # 最后一列自动拉伸
        header.setSectionsMovable(False)  # 禁止表头拖拽
        header.setDefaultAlignment(Qt.AlignCenter)  # 表头文本居中
        
        # 设置树形控件属性 - 参考定时调度实现
        self.system_tree.setSelectionBehavior(QTreeWidget.SelectRows)
        self.system_tree.setContextMenuPolicy(Qt.NoContextMenu)  # 禁用右键菜单
        self.system_tree.setRootIsDecorated(False)  # 不显示展开/折叠图标列
        self.system_tree.setAlternatingRowColors(True)
        
        # 设置所有列文本居中 - 参考定时调度实现
        for i in range(self.system_tree.columnCount()):
            self.system_tree.headerItem().setTextAlignment(i, Qt.AlignCenter)
        
        # 设置树形控件样式 - 参考定时调度实现
        self.system_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #f8f9fa;
                alternate-background-color: #ffffff;
                gridline-color: #e9ecef;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                outline: 0;
            }
            QTreeWidget::item {
                padding: 8px 8px;
                border-bottom: 1px solid #e9ecef;
                text-align: center;
                height: 32px;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #495057;
                font-weight: 600;
                font-size: 13px;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid #1976d2;
                min-height: 25px;
                text-align: center;
            }
            QHeaderView::section:hover {
                background-color: #e9ecef;
            }
        """)
        
        # 设置大小策略
        self.system_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.system_tree.setMinimumHeight(400)

        layout.addWidget(self.system_tree)

    def setup_global_tab(self, parent):
        """设置全局变量Tab"""
        layout = QVBoxLayout(parent)

        # 创建顶部按钮布局（左上角）
        top_layout = QHBoxLayout()
        
        self.add_global_btn = QPushButton("新增")
        self.add_global_btn.setFixedSize(80, 28)  # 调整按钮大小以适应文字
        self.add_global_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
                border-color: #3d8b40;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.add_global_btn.setCursor(Qt.PointingHandCursor)
        self.add_global_btn.clicked.connect(self.add_global_variable)

        top_layout.addWidget(self.add_global_btn)
        top_layout.addStretch()  # 添加弹性空间，将按钮推到左侧

        # 全局变量树形控件 - 参考定时调度实现
        self.global_tree = QTreeWidget()
        self.global_tree.setColumnCount(6)
        self.global_tree.setHeaderLabels(["序号", "变量名", "类型", "值", "描述", "操作"])
        
        # 设置固定列宽 - 参考定时调度设计
        self.global_tree.setColumnWidth(0, 80)     # 序号
        self.global_tree.setColumnWidth(1, 300)    # 变量名
        self.global_tree.setColumnWidth(2, 100)    # 类型
        self.global_tree.setColumnWidth(3, 600)    # 值
        self.global_tree.setColumnWidth(4, 200)    # 描述
        # 操作栏宽度设置为自适应内容
        self.global_tree.setColumnWidth(5, 120)    # 操作栏宽度
        
        # 设置列宽调整模式 - 参考定时调度实现
        header = self.global_tree.header()
        header.setSectionResizeMode(QHeaderView.Fixed)  # 其他列固定宽度
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # 操作栏固定宽度
        header.setStretchLastSection(True)  # 最后一列自动拉伸
        header.setSectionsMovable(False)  # 禁止表头拖拽
        header.setDefaultAlignment(Qt.AlignCenter)  # 表头文本居中
        
        # 设置树形控件属性 - 参考定时调度实现
        self.global_tree.setSelectionBehavior(QTreeWidget.SelectRows)
        self.global_tree.setContextMenuPolicy(Qt.NoContextMenu)  # 禁用右键菜单
        self.global_tree.setRootIsDecorated(False)  # 不显示展开/折叠图标列
        self.global_tree.setAlternatingRowColors(True)
        
        # 设置所有列文本居中 - 参考定时调度实现
        for i in range(self.global_tree.columnCount()):
            self.global_tree.headerItem().setTextAlignment(i, Qt.AlignCenter)
        
        # 设置树形控件样式 - 参考定时调度实现
        self.global_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #f8f9fa;
                alternate-background-color: #ffffff;
                gridline-color: #e9ecef;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                outline: 0;
            }
            QTreeWidget::item {
                padding: 8px 8px;
                border-bottom: 1px solid #e9ecef;
                text-align: center;
                height: 32px;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #495057;
                font-weight: 600;
                font-size: 13px;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid #1976d2;
                min-height: 25px;
                text-align: center;
            }
            QHeaderView::section:hover {
                background-color: #e9ecef;
            }
        """)
        
        # 设置大小策略
        self.global_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.global_tree.setMinimumHeight(400)

        # 添加布局到主布局
        layout.addLayout(top_layout)
        layout.addWidget(self.global_tree)

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
        except Exception as e:
            print(f"Error loading icon {icon_name}: {e}")
        return QIcon()

    def delayed_load_data(self):
        """延迟加载数据"""
        try:
            self.project_service = ProjectService()
            self.variable_service = GlobalVariableService()
            self.load_projects()
        except Exception as e:
            print(f"初始化服务失败: {e}")

    def load_projects(self, business_id=None):
        """加载项目数据到树形控件，支持按业务分组过滤
        
        Args:
            business_id: 业务分组ID，为None时加载所有项目
        """
        self.project_tree.clear()

        if self.project_service is None:
            return

        try:
            # 根据业务ID加载项目
            if business_id:
                projects = self.project_service.get_projects_by_group(business_id)
            else:
                projects = self.project_service.get_all_projects()
                
            for project in projects:
                project_item = QTreeWidgetItem(self.project_tree)
                project_item.setText(0, project['name'])
                project_item.setData(0, Qt.UserRole, {'type': 'project', 'data': project})
                project_item.setIcon(0, self.get_icon("project.png"))

        except Exception as e:
            print(f"加载项目数据失败: {e}")

    def on_project_selected(self, item):
        """项目选择事件"""
        data = item.data(0, Qt.UserRole)
        if data and data['type'] == 'project':
            self.current_project = data['data']
            self.show_variable_management()
            self.load_variables()

    def on_business_changed(self, business_id):
        """业务切换事件处理
        
        Args:
            business_id: 新选中的业务分组ID
        """
        # 更新当前业务ID
        self.current_business_id = business_id
        
        # 根据业务ID重新加载项目列表
        self.load_projects(business_id)
        
        # 清空当前选中的项目和变量数据
        self.current_project = None
        self.project_info_label.show()
        self.variable_container.hide()
        
        # 清空变量树形控件
        self.system_tree.clear()
        self.global_tree.clear()
        
        # 更新状态栏信息
        if business_id:
            print(f"变量管理页面：已切换到业务分组 {business_id}")
        else:
            print("变量管理页面：显示所有项目")

    def show_variable_management(self):
        """显示变量管理界面"""
        if self.current_project:
            self.project_info_label.hide()
            self.variable_container.show()
            
            # 更新项目信息 - 只在第一次显示时创建布局
            if self.variable_container.layout() is None:
                variable_container_layout = QVBoxLayout(self.variable_container)
                variable_container_layout.addWidget(self.tab_widget)

    def load_variables(self):
        """加载变量数据"""
        if not self.current_project:
            return

        self.load_system_variables()
        self.load_global_variables()

    def load_system_variables(self):
        """加载系统变量"""
        system_vars = self.variable_manager.system_variables
        self.system_tree.clear()

        descriptions = {
            '${__timestamp}': '当前时间戳',
            '${__datetime}': '当前日期时间',
            '${__date}': '当前日期',
            '${__time}': '当前时间',
            '${__random_int}': '随机整数(1-100)',
            '${__random_float}': '随机浮点数(1-100)',
            '${__random_string}': '随机字符串(8位)',
            '${__random_number}': '随机数字(6位)',
            '${__random_uuid}': '随机UUID',
            '${__project_dir}': '项目目录',
            '${__empty}': '空字符串',
            '${__null}': '空值'
        }

        for row, (name, value) in enumerate(system_vars.items()):
            # 创建树节点
            item = QTreeWidgetItem()
            
            # 序号 - 居中对齐
            item.setText(0, str(row + 1))
            item.setTextAlignment(0, Qt.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # 设置为不可编辑
            
            # 变量名 - 居中对齐
            item.setText(1, name)
            item.setTextAlignment(1, Qt.AlignCenter)

            # 值 - 居中对齐
            if callable(value):
                value_str = '<动态函数>'
            else:
                value_str = str(value)
            item.setText(2, value_str)
            item.setTextAlignment(2, Qt.AlignCenter)

            # 描述 - 居中对齐
            desc = descriptions.get(name, '系统预定义变量')
            item.setText(3, desc)
            item.setTextAlignment(3, Qt.AlignCenter)
            
            # 添加到树形控件
            self.system_tree.addTopLevelItem(item)

    def load_global_variables(self):
        """加载全局变量"""
        if self.variable_service is None or not self.current_project:
            return

        try:
            # 加载当前项目的全局变量
            global_vars = self.variable_service.get_global_variables_by_project(self.current_project['id'])
            self.global_tree.clear()

            for row, var in enumerate(global_vars):
                # 创建树节点
                item = QTreeWidgetItem()
                
                # 序号 - 居中对齐
                item.setText(0, str(row + 1))
                item.setTextAlignment(0, Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # 设置为不可编辑
                
                # 变量名 - 居中对齐
                item.setText(1, var['name'])
                item.setTextAlignment(1, Qt.AlignCenter)
                
                # 类型 - 居中对齐
                item.setText(2, var.get('variable_type', 'string'))
                item.setTextAlignment(2, Qt.AlignCenter)
                
                # 值 - 居中对齐
                value_str = str(var['value'])
                if len(value_str) > 50:
                    value_str = value_str[:50] + '...'
                item.setText(3, value_str)
                item.setTextAlignment(3, Qt.AlignCenter)
                
                # 描述 - 居中对齐
                item.setText(4, var.get('description', ''))
                item.setTextAlignment(4, Qt.AlignCenter)
                
                # 操作栏 - 设置为空，实际按钮通过setItemWidget添加
                item.setText(5, "")
                
                # 创建操作按钮容器 - 严格参考定时调度实现
                operation_widget = QWidget()
                operation_layout = QHBoxLayout(operation_widget)
                operation_layout.setContentsMargins(5, 2, 5, 2)
                operation_layout.setSpacing(3)
                operation_layout.setAlignment(Qt.AlignCenter)
                
                # 编辑按钮
                edit_btn = QPushButton()
                edit_btn.setFixedSize(22, 22)
                edit_btn.setIcon(self.get_icon("edit.png"))
                edit_btn.setToolTip("编辑")
                edit_btn.setStyleSheet("QPushButton { border: none; background: transparent; padding: 0px; } QPushButton:hover { background: #e0e0e0; }")
                # 使用默认参数方式解决lambda闭包问题
                edit_btn.clicked.connect(lambda checked=False, r=row: self.edit_global_variable_by_row(r))
                
                # 删除按钮
                delete_btn = QPushButton()
                delete_btn.setFixedSize(22, 22)
                delete_btn.setIcon(self.get_icon("delete.png"))
                delete_btn.setToolTip("删除")
                delete_btn.setStyleSheet("QPushButton { border: none; background: transparent; padding: 0px; } QPushButton:hover { background: #e0e0e0; }")
                # 使用默认参数方式解决lambda闭包问题
                delete_btn.clicked.connect(lambda checked=False, r=row: self.delete_global_variable_by_row(r))
                
                # 复制按钮
                copy_btn = QPushButton()
                copy_btn.setFixedSize(22, 22)
                copy_btn.setIcon(self.get_icon("copy.png"))
                copy_btn.setToolTip("复制")
                copy_btn.setStyleSheet("QPushButton { border: none; background: transparent; padding: 0px; } QPushButton:hover { background: #e0e0e0; }")
                # 使用默认参数方式解决lambda闭包问题
                copy_btn.clicked.connect(lambda checked=False, r=row: self.copy_global_variable_by_row(r))
                
                operation_layout.addWidget(edit_btn)
                operation_layout.addWidget(delete_btn)
                operation_layout.addWidget(copy_btn)
                
                # 添加到树形控件
                self.global_tree.addTopLevelItem(item)
                
                # 设置操作按钮到第5列（必须在addTopLevelItem之后）
                self.global_tree.setItemWidget(item, 5, operation_widget)
                
                # 确保按钮容器有正确的最小尺寸
                operation_widget.setMinimumHeight(28)
                operation_widget.setMinimumWidth(85)
                
                # 强制刷新视图以确保按钮正确显示
                self.global_tree.viewport().update()
        except Exception as e:
            print(f"加载全局变量失败: {e}")

    def add_global_variable(self):
        """新增全局变量"""
        if not self.current_project:
            Toast.warning(self, "警告", "请先选择项目")
            return

        dialog = VariableDialog(self, project_id=self.current_project['id'])
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            
            # 验证变量名
            if not data['name']:
                Toast.warning(self, "警告", "变量名不能为空")
                return

            try:
                # 保存到数据库
                self.variable_service.create_global_variable(data)
                Toast.success(self, "变量添加成功")
                self.load_global_variables()
                self.data_changed.emit()
            except Exception as e:
                Toast.error(self, f"添加变量失败: {str(e)}")

    def format_datetime(self, dt):
        """格式化日期时间显示"""
        if not dt:
            return ""
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return str(dt)

    def edit_global_variable_by_row(self, row):
        """通过行号编辑全局变量"""
        if not self.current_project:
            return

        try:
            # 获取变量数据
            variables = self.variable_service.get_global_variables_by_project(self.current_project['id'])
            if row < len(variables):
                variable_data = variables[row]
                
                dialog = VariableDialog(self, variable_data, self.current_project['id'])
                if dialog.exec_() == QDialog.Accepted:
                    data = dialog.get_data()
                    
                    # 更新变量
                    self.variable_service.update_global_variable(variable_data['id'], data)
                    Toast.success(self, "变量更新成功")
                    self.load_global_variables()
                    self.data_changed.emit()
        except Exception as e:
            Toast.error(self, f"编辑变量失败: {str(e)}")

    def delete_global_variable_by_row(self, row):
        """通过行号删除全局变量"""
        if not self.current_project:
            return

        try:
            # 获取变量数据
            variables = self.variable_service.get_global_variables_by_project(self.current_project['id'])
            if row < len(variables):
                variable_data = variables[row]
                
                # 创建确认对话框
                msg_box = QMessageBox(QMessageBox.Question, "确认删除",
                                     f"确定要删除变量 '{variable_data['name']}' 吗？")
                
                # 添加确认和取消按钮
                confirm_btn = msg_box.addButton("确认", QMessageBox.YesRole)
                cancel_btn = msg_box.addButton("取消", QMessageBox.NoRole)
                msg_box.setDefaultButton(cancel_btn)
                
                msg_box.exec_()
                
                if msg_box.clickedButton() == confirm_btn:
                    # 使用支持项目维度的删除方法
                    self.variable_service.delete_global_variable_by_name(variable_data['name'], self.current_project['id'])
                    Toast.success(self, "变量删除成功")
                    self.load_global_variables()
                    self.data_changed.emit()
        except Exception as e:
            Toast.error(self, f"删除变量失败: {str(e)}")

    def copy_global_variable_by_row(self, row):
        """通过行号复制全局变量"""
        if not self.current_project:
            return

        try:
            # 获取变量数据
            variables = self.variable_service.get_global_variables_by_project(self.current_project['id'])
            if row < len(variables):
                variable_data = variables[row]
                
                # 创建新变量数据（复制原变量，但修改名称）
                new_variable_data = {
                    'name': f"{variable_data['name']}_copy",
                    'variable_type': variable_data.get('variable_type', 'string'),
                    'value': variable_data['value'],
                    'description': variable_data.get('description', ''),
                    'project_id': self.current_project['id']
                }
                
                # 检查变量名是否重复，如果重复则添加序号
                counter = 1
                original_name = new_variable_data['name']
                while True:
                    try:
                        existing = self.variable_service.get_global_variable_by_name(new_variable_data['name'], self.current_project['id'])
                        if existing:
                            new_variable_data['name'] = f"{original_name}_{counter}"
                            counter += 1
                        else:
                            break
                    except:
                        break
                
                # 保存新变量
                self.variable_service.create_global_variable(new_variable_data)
                Toast.success(self, f"变量复制成功，新变量名为: {new_variable_data['name']}")
                self.load_global_variables()
                self.data_changed.emit()
        except Exception as e:
            Toast.error(self, f"复制变量失败: {str(e)}")