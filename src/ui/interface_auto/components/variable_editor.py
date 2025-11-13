import os
import json
from typing import Dict, Any
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget,
                             QTableWidgetItem, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QFormLayout, QHeaderView)
from src.utils.interface_utils.variable_manager import VariableManager, VariableValidator, VariableStorage
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelComboBox, NoWheelTabWidget
from src.ui.widgets.toast_tips import Toast


class VariableEditorDialog(QDialog):
    """变量编辑器对话框"""

    def __init__(self, parent=None, variable_data=None, is_global=True):
        super().__init__(parent)
        self.variable_data = variable_data or {}
        self.is_global = is_global
        self.is_edit = bool(variable_data)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑变量" if self.is_edit else "新增变量")
        self.setFixedSize(500, 400)

        layout = QVBoxLayout(self)

        # 变量类型提示
        type_label = QLabel(f"变量类型: {'全局变量' if self.is_global else '局部变量'}")
        type_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(type_label)

        # 表单布局
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入变量名（不支持特殊字符）")
        if self.variable_data:
            self.name_edit.setText(self.variable_data.get('name', ''))

        self.value_edit = QTextEdit()
        self.value_edit.setMaximumHeight(100)
        self.value_edit.setPlaceholderText("请输入变量值（支持JSON格式）")
        if self.variable_data:
            value = self.variable_data.get('value', '')
            if isinstance(value, (dict, list)):
                self.value_edit.setText(json.dumps(value, indent=2, ensure_ascii=False))
            else:
                self.value_edit.setText(str(value))

        self.type_combo = NoWheelComboBox()
        self.type_combo.addItems(["string", "number", "boolean", "list", "dict"])
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        if self.variable_data:
            var_type = self.variable_data.get('type', 'string')
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

    def on_type_changed(self):
        """变量类型变化"""
        var_type = self.type_combo.currentText()
        if var_type == 'json':
            self.value_edit.setPlaceholderText("请输入JSON格式的变量值")
        elif var_type == 'function':
            self.value_edit.setPlaceholderText("请输入函数表达式或代码")
        else:
            self.value_edit.setPlaceholderText("请输入变量值")

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
            'type': var_type,
            'value': value,
            'description': description,
            'scope': 'global' if self.is_global else 'local'
        }

    def parse_value(self, value_text: str, var_type: str) -> Any:
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
            # 解析失败，返回原文本
            return value_text


class VariableManagerDialog(QDialog):
    """变量管理器对话框"""

    def __init__(self, parent=None, project_id=0):
        super().__init__(parent)
        self.project_id = project_id
        self.variable_manager = VariableManager()
        self.variable_storage = VariableStorage()
        self.init_ui()
        self.load_variables()

    def init_ui(self):
        self.setWindowTitle("变量管理器")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # 创建Tab页
        tab_widget = NoWheelTabWidget()

        # 全局变量Tab
        global_tab = QWidget()
        self.setup_global_tab(global_tab)

        # 局部变量Tab
        local_tab = QWidget()
        self.setup_local_tab(local_tab)

        # 系统变量Tab
        system_tab = QWidget()
        self.setup_system_tab(system_tab)

        tab_widget.addTab(global_tab, "全局变量")
        tab_widget.addTab(local_tab, "局部变量")
        tab_widget.addTab(system_tab, "系统变量")

        layout.addWidget(tab_widget)

    def setup_global_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 全局变量说明
        info_label = QLabel("全局变量是可在所有测试用例中使用的变量，仅支持查看")
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)

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
        self.global_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 参考变量管理的表格样式
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

        layout.addWidget(self.global_table)

    def setup_local_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 局部变量说明
        info_label = QLabel("局部变量是仅在当前测试用例中使用的变量，仅支持查看")
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)

        # 局部变量表格
        self.local_table = QTableWidget()
        self.local_table.setColumnCount(4)
        self.local_table.setHorizontalHeaderLabels(["变量名", "类型", "值", "描述"])
        
        # 设置列宽 - 固定初始宽度，用户可以调整
        self.local_table.setColumnWidth(0, 300)  # 变量名列宽
        self.local_table.setColumnWidth(1, 150)   # 类型列宽
        self.local_table.setColumnWidth(2, 400)  # 值列宽
        self.local_table.setColumnWidth(3, 300)  # 描述列宽
        
        # 允许用户调整列宽，最后一列跟随窗口拉伸
        self.local_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.local_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # 最后一列自动拉伸
        self.local_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.local_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 参考变量管理的表格样式
        self.local_table.setAlternatingRowColors(True)
        self.local_table.verticalHeader().setVisible(False)  # 隐藏序号列
        self.local_table.setStyleSheet("""
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
        self.local_table.setMinimumHeight(400)  # 增加表格高度
        self.local_table.verticalHeader().setDefaultSectionSize(50)

        layout.addWidget(self.local_table)

    def setup_system_tab(self, parent):
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
        
        # 参考变量管理的表格样式
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

        # 加载系统变量
        self.load_system_variables()



    def load_variables(self):
        """加载变量"""
        self.load_global_variables()
        self.load_local_variables()

    def load_global_variables(self):
        """加载全局变量"""
        try:
            # 从数据库加载全局变量
            from src.core.services.global_variable_service import get_global_variable_service
            service = get_global_variable_service()
            global_vars = service.get_global_variables_by_project(self.project_id)
            
            # 同步到内存管理器
            var_dict = {}
            for var in global_vars:
                var_dict[var['name']] = var['value']
            self.variable_manager.set_global_variables(var_dict)
            
            # 显示在表格中
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

        except Exception as e:
            print(f"加载全局变量失败: {e}")
            # 降级处理：使用内存中的变量
            global_vars = self.variable_manager.global_variables
            self.global_table.setRowCount(len(global_vars))

            for row, (name, value) in enumerate(global_vars.items()):
                self.global_table.setItem(row, 0, QTableWidgetItem(name))
                self.global_table.setItem(row, 1, QTableWidgetItem(type(value).__name__))
                
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:50] + '...'
                self.global_table.setItem(row, 2, QTableWidgetItem(value_str))
                self.global_table.setItem(row, 3, QTableWidgetItem(''))

    def load_local_variables(self):
        """加载局部变量"""
        local_vars = self.variable_manager.local_variables
        self.local_table.setRowCount(len(local_vars))

        for row, (name, value) in enumerate(local_vars.items()):
            self.local_table.setItem(row, 0, QTableWidgetItem(name))

            # 类型
            var_type = type(value).__name__
            self.local_table.setItem(row, 1, QTableWidgetItem(var_type))

            # 值
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:50] + '...'
            self.local_table.setItem(row, 2, QTableWidgetItem(value_str))
            self.local_table.setItem(row, 3, QTableWidgetItem(''))  # 描述

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
            desc = descriptions.get(name, '系统变量')
            self.system_table.setItem(row, 2, QTableWidgetItem(desc))

    def add_global_variable(self):
        """新增全局变量"""
        dialog = VariableEditorDialog(self, is_global=True)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            is_valid, error_msg = self.validate_variable_data(data)

            if is_valid:
                # 同时保存到数据库和内存
                try:
                    from src.core.services.global_variable_service import get_global_variable_service
                    service = get_global_variable_service()
                    service.create_global_variable(data)
                    
                    # 同步到内存管理器
                    self.variable_manager.set_global_variables({data['name']: data['value']})
                    self.load_global_variables()
                except Exception as e:
                    Toast.error(self, f"保存全局变量失败: {str(e)}")
            else:
                Toast.warning(self, error_msg)

    def edit_global_variable(self):
        """编辑全局变量"""
        selected_items = self.global_table.selectedItems()
        if not selected_items:
            Toast.warning(self, "请先选择一个全局变量")
            return

        row = selected_items[0].row()
        var_name = self.global_table.item(row, 0).text()
        var_value = self.variable_manager.global_variables.get(var_name)

        variable_data = {
            'name': var_name,
            'value': var_value,
            'type': type(var_value).__name__
        }

        dialog = VariableEditorDialog(self, variable_data, is_global=True)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            is_valid, error_msg = self.validate_variable_data(data)

            if is_valid:
                # 同时更新数据库和内存
                try:
                    from src.core.services.global_variable_service import get_global_variable_service
                    service = get_global_variable_service()
                    
                    # 获取变量ID
                    var_info = service.get_global_variable_by_name(var_name)
                    if var_info:
                        # 更新数据库
                        service.update_global_variable(var_info['id'], data)
                        
                        # 更新内存管理器
                        del self.variable_manager.global_variables[var_name]
                        self.variable_manager.set_global_variables({data['name']: data['value']})
                        self.load_global_variables()
                    else:
                        Toast.error(self, "找不到要编辑的全局变量")
                except Exception as e:
                    Toast.error(self, f"更新全局变量失败: {str(e)}")
            else:
                Toast.warning(self, error_msg)

    def delete_global_variable(self):
        """删除全局变量"""
        selected_items = self.global_table.selectedItems()
        if not selected_items:
            Toast.warning(self, "请先选择一个全局变量")
            return

        row = selected_items[0].row()
        var_name = self.global_table.item(row, 0).text()

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除全局变量 '{var_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 同时从数据库和内存中删除
            try:
                from src.core.services.global_variable_service import get_global_variable_service
                service = get_global_variable_service()
                service.delete_global_variable_by_name(var_name)
                
                del self.variable_manager.global_variables[var_name]
                self.load_global_variables()
            except Exception as e:
                Toast.error(self, f"删除全局变量失败: {str(e)}")

    def clear_global_variables(self):
        """清空全局变量"""
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有全局变量吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 同时清空数据库和内存中的全局变量
            try:
                from src.core.services.global_variable_service import get_global_variable_service
                service = get_global_variable_service()
                
                # 获取所有变量并逐个删除
                all_vars = service.get_all_global_variables()
                for var in all_vars:
                    service.delete_global_variable(var['id'])
                
                self.variable_manager.clear_global_variables()
                self.load_global_variables()
            except Exception as e:
                Toast.error(self, f"清空全局变量失败: {str(e)}")

    def add_local_variable(self):
        """新增局部变量"""
        dialog = VariableEditorDialog(self, is_global=False)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            is_valid, error_msg = self.validate_variable_data(data)

            if is_valid:
                self.variable_manager.set_local_variables({data['name']: data['value']})
                self.load_local_variables()
            else:
                Toast.warning(self, error_msg)

    def edit_local_variable(self):
        """编辑局部变量"""
        selected_items = self.local_table.selectedItems()
        if not selected_items:
            Toast.warning(self, "请先选择一个局部变量")
            return

        row = selected_items[0].row()
        var_name = self.local_table.item(row, 0).text()
        var_value = self.variable_manager.local_variables.get(var_name)

        variable_data = {
            'name': var_name,
            'value': var_value,
            'type': type(var_value).__name__
        }

        dialog = VariableEditorDialog(self, variable_data, is_global=False)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            is_valid, error_msg = self.validate_variable_data(data)

            if is_valid:
                # 删除旧变量，添加新变量
                del self.variable_manager.local_variables[var_name]
                self.variable_manager.set_local_variables({data['name']: data['value']})
                self.load_local_variables()
            else:
                Toast.warning(self, error_msg)

    def delete_local_variable(self):
        """删除局部变量"""
        selected_items = self.local_table.selectedItems()
        if not selected_items:
            Toast.warning(self, "请先选择一个局部变量")
            return

        row = selected_items[0].row()
        var_name = self.local_table.item(row, 0).text()

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除局部变量 '{var_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            del self.variable_manager.local_variables[var_name]
            self.load_local_variables()

    def clear_local_variables(self):
        """清空局部变量"""
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有局部变量吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.variable_manager.clear_local_variables()
            self.load_local_variables()

    def validate_variable_data(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """验证变量数据"""
        # 验证变量名
        is_valid, error_msg = VariableValidator.validate_variable_name(data['name'])
        if not is_valid:
            return False, error_msg

        # 验证变量值
        is_valid, error_msg = VariableValidator.validate_variable_value(data['value'])
        if not is_valid:
            return False, error_msg

        return True, ""