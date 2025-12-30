#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置管理对话框

功能说明：
1. 显示已配置的数据库连接信息列表
2. 支持新增、编辑、删除数据库配置
3. 提供测试连接功能
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QHeaderView, QMessageBox,
                             QLabel, QLineEdit, QSpinBox, QTextEdit, QCheckBox,
                             QFormLayout, QGroupBox, QWidget, QDialogButtonBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

from src.utils.database_config_manager import DatabaseConfigManager


class DatabaseConfigDialog(QDialog):
    """数据库配置管理对话框"""
    
    config_updated = pyqtSignal()  # 配置更新信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = DatabaseConfigManager()
        self.configs = []
        
        self.setWindowTitle("数据库配置管理")
        self.setModal(True)
        self.resize(1000, 600)
        
        self.init_ui()
        self.load_configs()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("数据库配置管理")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title_label)
        
        # 操作按钮区域
        button_layout = QHBoxLayout()
        
        # 新增按钮
        self.add_btn = QPushButton("新增")
        self.add_btn.clicked.connect(self.add_config)
        button_layout.addWidget(self.add_btn)
        
        button_layout.addStretch()
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_configs)
        button_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(button_layout)
        
        # 配置表格
        self.create_config_table()
        layout.addWidget(self.config_table)
        
        # 底部按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def create_config_table(self):
        """创建配置表格"""
        self.config_table = QTableWidget()
        self.config_table.setColumnCount(9)
        self.config_table.setHorizontalHeaderLabels([
            "配置名称", "主机地址", "端口", "用户名", "数据库名", 
            "字符集", "是否默认", "状态", "操作"
        ])
        
        # 设置表格属性
        self.config_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.config_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.config_table.horizontalHeader().setStretchLastSection(True)
        
        # 设置列宽
        header = self.config_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 配置名称
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 主机地址
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 端口
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 用户名
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 数据库名
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 字符集
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 是否默认
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # 状态
        header.setSectionResizeMode(8, QHeaderView.Stretch)           # 操作
        
        # 连接双击事件
        self.config_table.cellDoubleClicked.connect(self.edit_config)
    
    def load_configs(self):
        """加载数据库配置"""
        self.configs = self.config_manager.get_all_configs()
        self.config_table.setRowCount(len(self.configs))
        
        for row, config in enumerate(self.configs):
            # 配置名称
            self.config_table.setItem(row, 0, QTableWidgetItem(config.get('name', '')))
            
            # 主机地址
            self.config_table.setItem(row, 1, QTableWidgetItem(config.get('host', '')))
            
            # 端口
            self.config_table.setItem(row, 2, QTableWidgetItem(str(config.get('port', 3306))))
            
            # 用户名
            self.config_table.setItem(row, 3, QTableWidgetItem(config.get('user', '')))
            
            # 数据库名
            self.config_table.setItem(row, 4, QTableWidgetItem(config.get('database_name', '')))
            
            # 字符集
            self.config_table.setItem(row, 5, QTableWidgetItem(config.get('charset', 'utf8mb4')))
            
            # 是否默认
            default_item = QTableWidgetItem("是" if config.get('is_default') else "否")
            if config.get('is_default'):
                default_item.setBackground(Qt.green)
            self.config_table.setItem(row, 6, default_item)
            
            # 状态
            status_item = QTableWidgetItem("启用" if config.get('enabled') else "禁用")
            status_item.setBackground(Qt.green if config.get('enabled') else Qt.red)
            self.config_table.setItem(row, 7, status_item)
            
            # 操作按钮
            button_widget = self.create_action_buttons(config['id'])
            self.config_table.setCellWidget(row, 8, button_widget)
    
    def create_action_buttons(self, config_id):
        """创建操作按钮"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # 编辑按钮
        edit_btn = QPushButton("编辑")
        edit_btn.setFixedSize(60, 25)
        edit_btn.clicked.connect(lambda: self.edit_config(config_id))
        layout.addWidget(edit_btn)
        
        # 测试连接按钮
        test_btn = QPushButton("测试")
        test_btn.setFixedSize(60, 25)
        test_btn.clicked.connect(lambda: self.test_connection(config_id))
        layout.addWidget(test_btn)
        
        # 删除按钮
        delete_btn = QPushButton("删除")
        delete_btn.setFixedSize(60, 25)
        delete_btn.clicked.connect(lambda: self.delete_config(config_id))
        layout.addWidget(delete_btn)
        
        # 设为默认按钮
        default_btn = QPushButton("设默认")
        default_btn.setFixedSize(60, 25)
        default_btn.clicked.connect(lambda: self.set_default_config(config_id))
        layout.addWidget(default_btn)
        
        layout.addStretch()
        return widget
    
    def add_config(self):
        """新增配置"""
        dialog = DatabaseConfigEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_configs()
            self.config_updated.emit()
    
    def edit_config(self, config_id=None):
        """编辑配置"""
        if config_id is None:
            # 双击编辑
            current_row = self.config_table.currentRow()
            if current_row >= 0:
                config_id = self.configs[current_row]['id']
            else:
                return
        
        config_data = self.config_manager.get_config_by_id(config_id)
        if config_data:
            dialog = DatabaseConfigEditDialog(self, config_data)
            if dialog.exec_() == QDialog.Accepted:
                self.load_configs()
                self.config_updated.emit()
    
    def delete_config(self, config_id):
        """删除配置"""
        config_data = self.config_manager.get_config_by_id(config_id)
        if not config_data:
            return
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除数据库配置 '{config_data['name']}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.config_manager.delete_config(config_id):
                QMessageBox.information(self, "成功", "配置删除成功")
                self.load_configs()
                self.config_updated.emit()
            else:
                QMessageBox.warning(self, "错误", "配置删除失败")
    
    def test_connection(self, config_id):
        """测试连接"""
        config_data = self.config_manager.get_config_by_id(config_id)
        if not config_data:
            return
        
        result = self.config_manager.test_connection(config_data)
        
        if result['success']:
            QMessageBox.information(
                self, "连接测试成功", 
                f"数据库连接测试成功！\n\n"
                f"数据库版本: {result['details'].get('version', '未知')}\n"
                f"数据库大小: {result['details'].get('database_size', 0):,} 字节"
            )
        else:
            QMessageBox.critical(
                self, "连接测试失败", 
                f"数据库连接测试失败！\n\n"
                f"错误信息: {result['message']}"
            )
    
    def set_default_config(self, config_id):
        """设为默认配置"""
        config_data = self.config_manager.get_config_by_id(config_id)
        if not config_data:
            return
        
        if config_data.get('is_default'):
            QMessageBox.information(self, "提示", "该配置已经是默认配置")
            return
        
        reply = QMessageBox.question(
            self, "确认设置", 
            f"确定要将 '{config_data['name']}' 设为默认数据库配置吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.config_manager.set_default_config(config_id):
                QMessageBox.information(self, "成功", "默认配置设置成功")
                self.load_configs()
                self.config_updated.emit()
            else:
                QMessageBox.warning(self, "错误", "默认配置设置失败")


class DatabaseConfigEditDialog(QDialog):
    """数据库配置编辑对话框"""
    
    def __init__(self, parent=None, config_data=None):
        super().__init__(parent)
        self.config_data = config_data
        self.is_edit_mode = config_data is not None
        
        self.setWindowTitle("编辑数据库配置" if self.is_edit_mode else "新增数据库配置")
        self.setModal(True)
        self.resize(500, 400)
        
        self.init_ui()
        
        if self.is_edit_mode:
            self.load_config_data()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 配置表单
        form_group = QGroupBox("数据库配置")
        form_layout = QFormLayout(form_group)
        
        # 配置名称
        self.name_edit = QLineEdit()
        form_layout.addRow("配置名称*:", self.name_edit)
        
        # 主机地址
        self.host_edit = QLineEdit()
        self.host_edit.setText("localhost")
        form_layout.addRow("主机地址*:", self.host_edit)
        
        # 端口
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(3306)
        form_layout.addRow("端口*:", self.port_spin)
        
        # 用户名
        self.user_edit = QLineEdit()
        self.user_edit.setText("root")
        form_layout.addRow("用户名*:", self.user_edit)
        
        # 密码
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("密码*:", self.password_edit)
        
        # 数据库名
        self.database_edit = QLineEdit()
        form_layout.addRow("数据库名*:", self.database_edit)
        
        # 字符集
        self.charset_edit = QLineEdit()
        self.charset_edit.setText("utf8mb4")
        form_layout.addRow("字符集:", self.charset_edit)
        
        # 描述
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        form_layout.addRow("描述:", self.description_edit)
        
        # 选项
        options_layout = QHBoxLayout()
        
        self.default_check = QCheckBox("设为默认配置")
        options_layout.addWidget(self.default_check)
        
        self.enabled_check = QCheckBox("启用配置")
        self.enabled_check.setChecked(True)
        options_layout.addWidget(self.enabled_check)
        
        form_layout.addRow("选项:", options_layout)
        
        layout.addWidget(form_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 测试连接按钮
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_btn)
        
        button_layout.addStretch()
        
        # 确定取消按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
    
    def load_config_data(self):
        """加载配置数据"""
        if not self.config_data:
            return
        
        self.name_edit.setText(self.config_data.get('name', ''))
        self.host_edit.setText(self.config_data.get('host', ''))
        self.port_spin.setValue(self.config_data.get('port', 3306))
        self.user_edit.setText(self.config_data.get('user', ''))
        self.password_edit.setText(self.config_data.get('password', ''))
        self.database_edit.setText(self.config_data.get('database_name', ''))
        self.charset_edit.setText(self.config_data.get('charset', 'utf8mb4'))
        self.description_edit.setText(self.config_data.get('description', ''))
        self.default_check.setChecked(self.config_data.get('is_default', False))
        self.enabled_check.setChecked(self.config_data.get('enabled', True))
    
    def test_connection(self):
        """测试连接"""
        config_data = self.get_form_data()
        
        # 验证必填字段
        if not self.validate_form():
            return
        
        from src.utils.database_config_manager import test_database_connection
        result = test_database_connection(config_data)
        
        if result['success']:
            QMessageBox.information(
                self, "连接测试成功", 
                f"数据库连接测试成功！\n\n"
                f"数据库版本: {result['details'].get('version', '未知')}\n"
                f"数据库大小: {result['details'].get('database_size', 0):,} 字节"
            )
        else:
            QMessageBox.critical(
                self, "连接测试失败", 
                f"数据库连接测试失败！\n\n"
                f"错误信息: {result['message']}"
            )
    
    def get_form_data(self):
        """获取表单数据"""
        return {
            'name': self.name_edit.text().strip(),
            'host': self.host_edit.text().strip(),
            'port': self.port_spin.value(),
            'user': self.user_edit.text().strip(),
            'password': self.password_edit.text(),
            'database_name': self.database_edit.text().strip(),
            'charset': self.charset_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'is_default': self.default_check.isChecked(),
            'enabled': self.enabled_check.isChecked()
        }
    
    def validate_form(self):
        """验证表单"""
        data = self.get_form_data()
        
        if not data['name']:
            QMessageBox.warning(self, "验证错误", "请输入配置名称")
            self.name_edit.setFocus()
            return False
        
        if not data['host']:
            QMessageBox.warning(self, "验证错误", "请输入主机地址")
            self.host_edit.setFocus()
            return False
        
        if not data['user']:
            QMessageBox.warning(self, "验证错误", "请输入用户名")
            self.user_edit.setFocus()
            return False
        
        if not data['password']:
            QMessageBox.warning(self, "验证错误", "请输入密码")
            self.password_edit.setFocus()
            return False
        
        if not data['database_name']:
            QMessageBox.warning(self, "验证错误", "请输入数据库名")
            self.database_edit.setFocus()
            return False
        
        return True
    
    def accept(self):
        """保存配置"""
        if not self.validate_form():
            return
        
        config_data = self.get_form_data()
        manager = DatabaseConfigManager()
        
        try:
            if self.is_edit_mode:
                success = manager.update_config(self.config_data['id'], config_data)
                message = "更新"
            else:
                success = manager.add_config(config_data)
                message = "添加"
            
            if success:
                QMessageBox.information(self, "成功", f"配置{message}成功")
                super().accept()
            else:
                QMessageBox.warning(self, "错误", f"配置{message}失败")
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"操作失败: {str(e)}")


if __name__ == "__main__":
    # 测试代码
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    dialog = DatabaseConfigDialog()
    dialog.show()
    
    sys.exit(app.exec_())