"""
变量管理页面
支持项目维度的变量管理，包含系统变量（只读）和全局变量（增删改查）
"""

import os
import json
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
                             QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QGroupBox, QFormLayout, QHeaderView, QInputDialog,
                             QTableWidget, QTableWidgetItem, QSplitter, QFrame,
                             QComboBox)
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
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(button_box)

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

        # 系统变量Tab
        system_tab = QWidget()
        self.setup_system_tab(system_tab)

        # 全局变量Tab
        global_tab = QWidget()
        self.setup_global_tab(global_tab)

        self.tab_widget.addTab(system_tab, "系统变量")
        self.tab_widget.addTab(global_tab, "全局变量")

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

        # 系统变量表格
        self.system_table = QTableWidget()
        self.system_table.setColumnCount(3)
        self.system_table.setHorizontalHeaderLabels(["变量名", "值", "描述"])
        
        # 设置列宽 - 固定初始宽度，用户可以调整
        self.system_table.setColumnWidth(0, 250)  # 变量名列宽
        self.system_table.setColumnWidth(1, 300)  # 值列宽
        self.system_table.setColumnWidth(2, 200)  # 描述列宽
        
        # 允许用户调整列宽，最后一列跟随窗口拉伸
        self.system_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.system_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # 最后一列自动拉伸
        self.system_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.system_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # 参考接口模板的请求头表格样式
        self.system_table.setAlternatingRowColors(True)
        self.system_table.verticalHeader().setVisible(False)  # 隐藏序号列
        self.system_table.setStyleSheet("""
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
        """)
        self.system_table.setMinimumHeight(400)  # 增加表格高度
        self.system_table.verticalHeader().setDefaultSectionSize(50)

        layout.addWidget(self.system_table)

    def setup_global_tab(self, parent):
        """设置全局变量Tab"""
        layout = QVBoxLayout(parent)

        # 全局变量表格
        self.global_table = QTableWidget()
        self.global_table.setColumnCount(4)
        self.global_table.setHorizontalHeaderLabels(["变量名", "类型", "值", "描述"])
        
        # 设置列宽 - 固定初始宽度，用户可以调整
        self.global_table.setColumnWidth(0, 300)  # 变量名列宽
        self.global_table.setColumnWidth(1, 150)   # 类型列宽
        self.global_table.setColumnWidth(2, 400)  # 值列宽
        self.global_table.setColumnWidth(3, 300)  # 描述列宽
        
        # 允许用户调整列宽，最后一列跟随窗口拉伸
        self.global_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.global_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # 最后一列自动拉伸
        self.global_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # 参考接口模板的请求头表格样式
        self.global_table.setAlternatingRowColors(True)
        self.global_table.verticalHeader().setVisible(False)  # 隐藏序号列
        self.global_table.setStyleSheet("""
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
        """)
        self.global_table.setMinimumHeight(400)  # 增加表格高度
        self.global_table.verticalHeader().setDefaultSectionSize(50)

        # 底部按钮布局（左下角）
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()  # 添加弹性空间，将按钮推到右侧
        
        self.add_global_btn = QPushButton("新增")
        self.add_global_btn.clicked.connect(self.add_global_variable)

        self.edit_global_btn = QPushButton("编辑")
        self.edit_global_btn.clicked.connect(self.edit_global_variable)

        self.delete_global_btn = QPushButton("删除")
        self.delete_global_btn.clicked.connect(self.delete_global_variable)

        bottom_layout.addWidget(self.add_global_btn)
        bottom_layout.addWidget(self.edit_global_btn)
        bottom_layout.addWidget(self.delete_global_btn)

        layout.addWidget(self.global_table)
        layout.addLayout(bottom_layout)

    def get_icon(self, icon_name):
        """获取图标"""
        try:
            icon_path = os.path.join("src", "ui", "interface_auto", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
        except:
            pass
        return QIcon()

    def delayed_load_data(self):
        """延迟加载数据"""
        try:
            self.project_service = ProjectService()
            self.variable_service = GlobalVariableService()
            self.load_projects()
        except Exception as e:
            print(f"初始化服务失败: {e}")

    def load_projects(self):
        """加载项目数据"""
        self.project_tree.clear()

        if self.project_service is None:
            return

        try:
            # 加载所有项目
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
        self.system_table.setRowCount(len(system_vars))

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
            self.system_table.setItem(row, 0, QTableWidgetItem(name))

            # 值
            if callable(value):
                value_str = '<动态函数>'
            else:
                value_str = str(value)
            self.system_table.setItem(row, 1, QTableWidgetItem(value_str))

            # 描述
            desc = descriptions.get(name, '系统预定义变量')
            self.system_table.setItem(row, 2, QTableWidgetItem(desc))

        # 移除自动调整列宽，保持固定列宽

    def load_global_variables(self):
        """加载全局变量"""
        if self.variable_service is None or not self.current_project:
            return

        try:
            # 加载当前项目的全局变量
            global_vars = self.variable_service.get_global_variables_by_project(self.current_project['id'])
            self.global_table.setRowCount(len(global_vars))

            for row, var in enumerate(global_vars):
                self.global_table.setItem(row, 0, QTableWidgetItem(var['name']))
                self.global_table.setItem(row, 1, QTableWidgetItem(var.get('variable_type', 'string')))
                
                # 值
                value_str = str(var['value'])
                if len(value_str) > 50:
                    value_str = value_str[:50] + '...'
                self.global_table.setItem(row, 2, QTableWidgetItem(value_str))
                self.global_table.setItem(row, 3, QTableWidgetItem(var.get('description', '')))

            # 移除自动调整列宽，保持固定列宽
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

    def edit_global_variable(self):
        """编辑全局变量"""
        if not self.current_project:
            return

        selected_items = self.global_table.selectedItems()
        if not selected_items:
            Toast.warning(self, "警告", "请先选择一个变量")
            return

        row = selected_items[0].row()
        var_name = self.global_table.item(row, 0).text()

        # 获取变量数据
        try:
            variables = self.variable_service.get_global_variables_by_project(self.current_project['id'])
            variable_data = None
            for var in variables:
                if var['name'] == var_name:
                    variable_data = var
                    break

            if variable_data:
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

    def delete_global_variable(self):
        """删除全局变量"""
        if not self.current_project:
            return

        selected_items = self.global_table.selectedItems()
        if not selected_items:
            Toast.warning(self, "警告", "请先选择一个变量")
            return

        row = selected_items[0].row()
        var_name = self.global_table.item(row, 0).text()

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除变量 '{var_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # 使用支持项目维度的删除方法
                self.variable_service.delete_global_variable_by_name(var_name, self.current_project['id'])
                Toast.success(self, "变量删除成功")
                self.load_global_variables()
                self.data_changed.emit()

            except Exception as e:
                Toast.error(self, f"删除变量失败: {str(e)}")

    def format_datetime(self, dt):
        """格式化日期时间显示"""
        if not dt:
            return ""
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return str(dt)