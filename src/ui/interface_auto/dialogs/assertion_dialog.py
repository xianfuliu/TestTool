import json
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QComboBox, QPushButton, QGroupBox, QFormLayout,
                             QDialogButtonBox, QMessageBox, QTextEdit, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal
from src.ui.widgets.toast_tips import Toast


class AssertionDialog(QDialog):
    """断言工具配置对话框"""
    
    assertion_saved = pyqtSignal(dict)  # 断言配置保存信号
    
    def __init__(self, parent=None, assertion_data=None):
        super().__init__(parent)
        self.assertion_data = assertion_data or {}
        self.is_edit = bool(assertion_data)
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("编辑断言" if self.is_edit else "新增断言")
        self.setMinimumSize(600, 400)
        
        # 设置对话框样式
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 6px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QDialogButtonBox QPushButton {
                min-width: 80px;
            }
            QComboBox {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 4px;
                min-height: 20px;
            }
            QLineEdit, QTextEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # 断言基本信息组
        basic_group = QGroupBox("断言基本信息")
        basic_layout = QFormLayout(basic_group)
        
        # 名称字段
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入断言名称")
        basic_layout.addRow("名称:", self.name_edit)
        
        # 断言类型
        self.type_combo = QComboBox()
        self.type_combo.addItems(["equal", "contains", "regex", "status_code", "json_path"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        basic_layout.addRow("断言类型:", self.type_combo)
        
        layout.addWidget(basic_group)
        
        # 断言配置组
        self.config_group = QGroupBox("断言配置")
        self.config_layout = QFormLayout(self.config_group)
        
        # 期望值
        self.expected_edit = QLineEdit()
        self.expected_edit.setPlaceholderText("请输入期望值")
        self.config_layout.addRow("期望值:", self.expected_edit)
        
        # 实际值路径（用于JSON路径断言）
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("请输入JSON路径，如: $.data.name")
        self.config_layout.addRow("JSON路径:", self.path_edit)
        
        # 正则表达式
        self.regex_edit = QLineEdit()
        self.regex_edit.setPlaceholderText("请输入正则表达式")
        self.config_layout.addRow("正则表达式:", self.regex_edit)
        
        # 忽略大小写
        self.ignore_case_check = QCheckBox("忽略大小写")
        self.config_layout.addRow("", self.ignore_case_check)
        
        layout.addWidget(self.config_group)
        
        # 描述信息
        desc_group = QGroupBox("描述信息")
        desc_layout = QVBoxLayout(desc_group)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("请输入断言描述（可选）")
        self.desc_edit.setMaximumHeight(80)
        desc_layout.addWidget(self.desc_edit)
        
        layout.addWidget(desc_group)
        
        # 按钮布局
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_save)
        button_box.rejected.connect(self.reject)
        
        # 修改按钮文本
        button_box.button(QDialogButtonBox.Ok).setText("确认")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        
        layout.addWidget(button_box)
        
        # 加载数据
        if self.is_edit:
            self.load_assertion_data()
        
        # 初始显示配置
        self.on_type_changed(self.type_combo.currentText())
    
    def on_type_changed(self, assertion_type):
        """断言类型改变时的处理"""
        # 隐藏所有配置项
        for i in range(self.config_layout.rowCount()):
            item = self.config_layout.itemAt(i, QFormLayout.FieldRole)
            if item and item.widget():
                item.widget().hide()
            
            item = self.config_layout.itemAt(i, QFormLayout.LabelRole)
            if item and item.widget():
                item.widget().hide()
        
        # 根据类型显示相应的配置项
        if assertion_type == "equal":
            self.config_layout.labelForField(self.expected_edit).show()
            self.expected_edit.show()
            self.ignore_case_check.show()
            self.config_group.setTitle("相等断言配置")
        elif assertion_type == "contains":
            self.config_layout.labelForField(self.expected_edit).show()
            self.expected_edit.show()
            self.ignore_case_check.show()
            self.config_group.setTitle("包含断言配置")
        elif assertion_type == "regex":
            self.config_layout.labelForField(self.regex_edit).show()
            self.regex_edit.show()
            self.config_group.setTitle("正则断言配置")
        elif assertion_type == "status_code":
            self.config_layout.labelForField(self.expected_edit).show()
            self.expected_edit.show()
            self.config_group.setTitle("状态码断言配置")
        elif assertion_type == "json_path":
            self.config_layout.labelForField(self.path_edit).show()
            self.path_edit.show()
            self.config_layout.labelForField(self.expected_edit).show()
            self.expected_edit.show()
            self.config_group.setTitle("JSON路径断言配置")
    
    def load_assertion_data(self):
        """加载断言数据"""
        try:
            # 名称
            self.name_edit.setText(self.assertion_data.get('name', ''))
            
            # 类型
            assertion_type = self.assertion_data.get('type', 'equal')
            index = self.type_combo.findText(assertion_type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
            
            # 配置
            config = self.assertion_data.get('config', {})
            self.expected_edit.setText(config.get('expected', ''))
            self.path_edit.setText(config.get('path', ''))
            self.regex_edit.setText(config.get('regex', ''))
            self.ignore_case_check.setChecked(config.get('ignore_case', False))
            
            # 描述
            self.desc_edit.setText(self.assertion_data.get('description', ''))
            
        except Exception as e:
            print(f"加载断言数据失败: {str(e)}")
    
    def on_save(self):
        """保存断言配置"""
        try:
            # 验证数据
            name = self.name_edit.text().strip()
            if not name:
                Toast.error(self, "请输入断言名称")
                return
            
            assertion_type = self.type_combo.currentText()
            
            # 根据类型验证配置
            config = {}
            if assertion_type in ["equal", "contains", "status_code"]:
                expected = self.expected_edit.text().strip()
                if not expected:
                    Toast.error(self, f"请输入期望值")
                    return
                config['expected'] = expected
                config['ignore_case'] = self.ignore_case_check.isChecked()
            
            elif assertion_type == "regex":
                regex = self.regex_edit.text().strip()
                if not regex:
                    Toast.error(self, "请输入正则表达式")
                    return
                config['regex'] = regex
            
            elif assertion_type == "json_path":
                path = self.path_edit.text().strip()
                expected = self.expected_edit.text().strip()
                if not path:
                    Toast.error(self, "请输入JSON路径")
                    return
                if not expected:
                    Toast.error(self, "请输入期望值")
                    return
                config['path'] = path
                config['expected'] = expected
            
            # 构建断言配置
            assertion_config = {
                'name': name,
                'type': assertion_type,
                'config': config,
                'description': self.desc_edit.toPlainText().strip()
            }
            
            # 发送保存信号
            self.assertion_saved.emit(assertion_config)
            
            # 关闭对话框
            self.accept()
            
        except Exception as e:
            print(f"保存断言配置失败: {str(e)}")
            Toast.error(self, f"保存断言配置失败: {str(e)}")
    
    def get_assertion_config(self):
        """获取断言配置"""
        return {
            'name': self.name_edit.text().strip(),
            'type': self.type_combo.currentText(),
            'config': {
                'expected': self.expected_edit.text().strip(),
                'path': self.path_edit.text().strip(),
                'regex': self.regex_edit.text().strip(),
                'ignore_case': self.ignore_case_check.isChecked()
            },
            'description': self.desc_edit.toPlainText().strip()
        }