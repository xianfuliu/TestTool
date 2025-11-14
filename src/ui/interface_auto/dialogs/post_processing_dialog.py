import json
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QTextEdit, QComboBox, QPushButton, QGroupBox, QFormLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView, QDialogButtonBox,
                             QMessageBox, QTabWidget, QScrollArea, QWidget, QCheckBox,
                             QSpinBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from src.ui.widgets.toast_tips import Toast


class PostProcessingDialog(QDialog):
    """后置处理工具配置对话框"""
    
    processing_saved = pyqtSignal(dict)  # 后置处理配置保存信号
    
    def __init__(self, parent=None, processing_data=None):
        super().__init__(parent)
        self.processing_data = processing_data or {}
        self.is_edit = bool(processing_data)
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("编辑后置处理" if self.is_edit else "新增后置处理")
        self.setMinimumSize(700, 500)
        
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
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #ccc;
                selection-background-color: #e3f2fd;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # 创建Tab页
        tab_widget = QTabWidget()
        
        # 基本信息Tab
        basic_tab = self.create_basic_tab()
        tab_widget.addTab(basic_tab, "基本信息")
        
        # 处理配置Tab
        config_tab = self.create_config_tab()
        tab_widget.addTab(config_tab, "处理配置")
        
        layout.addWidget(tab_widget)
        
        # 按钮布局
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_save)
        button_box.rejected.connect(self.reject)
        
        # 修改按钮文本
        button_box.button(QDialogButtonBox.Ok).setText("确认")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
        
        # 加载数据
        if self.is_edit:
            self.load_processing_data()
    
    def create_basic_tab(self):
        """创建基本信息Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)
        
        # 名称字段
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入后置处理名称")
        basic_layout.addRow("名称:", self.name_edit)
        
        # 处理类型
        self.type_combo = QComboBox()
        self.type_combo.addItems(["数据提取", "数据转换", "数据验证", "数据存储", "自定义脚本"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        basic_layout.addRow("处理类型:", self.type_combo)
        
        # 描述信息
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("请输入后置处理的描述信息")
        self.desc_edit.setMaximumHeight(80)
        basic_layout.addRow("描述:", self.desc_edit)
        
        layout.addWidget(basic_group)
        layout.addStretch()
        
        return tab
    
    def create_config_tab(self):
        """创建处理配置Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 配置组
        config_group = QGroupBox("处理配置")
        config_layout = QVBoxLayout(config_group)
        
        # 配置内容区域
        self.config_widget = QWidget()
        self.config_layout = QVBoxLayout(self.config_widget)
        
        # 默认显示数据提取配置
        self.create_data_extraction_config()
        
        config_layout.addWidget(self.config_widget)
        layout.addWidget(config_group)
        layout.addStretch()
        
        return tab
    
    def on_type_changed(self, type_text):
        """处理类型改变时更新配置界面"""
        # 清空当前配置界面
        for i in reversed(range(self.config_layout.count())):
            widget = self.config_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 根据类型创建对应的配置界面
        if type_text == "数据提取":
            self.create_data_extraction_config()
        elif type_text == "数据转换":
            self.create_data_transformation_config()
        elif type_text == "数据验证":
            self.create_data_validation_config()
        elif type_text == "数据存储":
            self.create_data_storage_config()
        elif type_text == "自定义脚本":
            self.create_custom_script_config()
    
    def create_data_extraction_config(self):
        """创建数据提取配置"""
        # 提取字段配置
        fields_group = QGroupBox("提取字段配置")
        fields_layout = QVBoxLayout(fields_group)
        
        # 字段表格
        self.fields_table = QTableWidget()
        self.fields_table.setColumnCount(2)
        self.fields_table.setHorizontalHeaderLabels(["字段名", "JSONPath表达式"])
        self.fields_table.horizontalHeader().setStretchLastSection(True)
        
        # 添加示例行
        self.add_table_row(self.fields_table, "user_id", "$.data.userId")
        
        add_field_btn = QPushButton("添加字段")
        add_field_btn.clicked.connect(lambda: self.add_table_row(self.fields_table, "", ""))
        
        fields_layout.addWidget(self.fields_table)
        fields_layout.addWidget(add_field_btn)
        
        self.config_layout.addWidget(fields_group)
    
    def create_data_transformation_config(self):
        """创建数据转换配置"""
        # 转换规则配置
        rules_group = QGroupBox("转换规则")
        rules_layout = QVBoxLayout(rules_group)
        
        self.rules_edit = QTextEdit()
        self.rules_edit.setPlaceholderText("请输入数据转换规则，例如：\n• 时间格式转换\n• 数值单位转换\n• 数据格式标准化")
        self.rules_edit.setMaximumHeight(150)
        
        rules_layout.addWidget(QLabel("转换规则:"))
        rules_layout.addWidget(self.rules_edit)
        
        self.config_layout.addWidget(rules_group)
    
    def create_data_validation_config(self):
        """创建数据验证配置"""
        # 验证规则配置
        validation_group = QGroupBox("验证规则")
        validation_layout = QVBoxLayout(validation_group)
        
        self.validation_edit = QTextEdit()
        self.validation_edit.setPlaceholderText("请输入数据验证规则，例如：\n• 必填字段检查\n• 数据类型验证\n• 数值范围检查\n• 格式验证")
        self.validation_edit.setMaximumHeight(150)
        
        validation_layout.addWidget(QLabel("验证规则:"))
        validation_layout.addWidget(self.validation_edit)
        
        self.config_layout.addWidget(validation_group)
    
    def create_data_storage_config(self):
        """创建数据存储配置"""
        # 存储配置
        storage_group = QGroupBox("存储配置")
        storage_layout = QFormLayout(storage_group)
        
        self.storage_type_combo = QComboBox()
        self.storage_type_combo.addItems(["文件存储", "数据库存储", "缓存存储"])
        storage_layout.addRow("存储类型:", self.storage_type_combo)
        
        self.storage_path_edit = QLineEdit()
        self.storage_path_edit.setPlaceholderText("请输入存储路径或连接信息")
        storage_layout.addRow("存储路径:", self.storage_path_edit)
        
        self.config_layout.addWidget(storage_group)
    
    def create_custom_script_config(self):
        """创建自定义脚本配置"""
        # 脚本配置
        script_group = QGroupBox("自定义脚本")
        script_layout = QVBoxLayout(script_group)
        
        self.script_edit = QTextEdit()
        self.script_edit.setPlaceholderText("请输入自定义脚本代码")
        self.script_edit.setMaximumHeight(200)
        
        script_layout.addWidget(QLabel("脚本代码:"))
        script_layout.addWidget(self.script_edit)
        
        self.config_layout.addWidget(script_group)
    
    def add_table_row(self, table, key="", value=""):
        """为表格添加一行"""
        row = table.rowCount()
        table.insertRow(row)
        
        key_item = QTableWidgetItem(key)
        value_item = QTableWidgetItem(value)
        
        table.setItem(row, 0, key_item)
        table.setItem(row, 1, value_item)
    
    def load_processing_data(self):
        """加载后置处理数据"""
        if not self.processing_data:
            return
            
        # 基本信息
        self.name_edit.setText(self.processing_data.get('name', '后置处理'))
        self.type_combo.setCurrentText(self.processing_data.get('type', '数据提取'))
        self.desc_edit.setText(self.processing_data.get('description', ''))
        
        # 根据类型加载配置数据
        self.load_config_data()
    
    def load_config_data(self):
        """加载配置数据"""
        processing_type = self.type_combo.currentText()
        config = self.processing_data.get('config', {})
        
        if processing_type == "数据提取":
            fields = config.get('fields', {})
            self.fields_table.setRowCount(0)
            for field_name, json_path in fields.items():
                self.add_table_row(self.fields_table, field_name, json_path)
        elif processing_type == "数据转换":
            self.rules_edit.setText(config.get('rules', ''))
        elif processing_type == "数据验证":
            self.validation_edit.setText(config.get('validation_rules', ''))
        elif processing_type == "数据存储":
            self.storage_type_combo.setCurrentText(config.get('storage_type', '文件存储'))
            self.storage_path_edit.setText(config.get('storage_path', ''))
        elif processing_type == "自定义脚本":
            self.script_edit.setText(config.get('script', ''))
    
    def get_fields_from_table(self):
        """从表格获取字段配置"""
        fields = {}
        for row in range(self.fields_table.rowCount()):
            field_item = self.fields_table.item(row, 0)
            path_item = self.fields_table.item(row, 1)
            
            if field_item and path_item:
                field_name = field_item.text().strip()
                json_path = path_item.text().strip()
                if field_name and json_path:
                    fields[field_name] = json_path
        return fields
    
    def on_save(self):
        """保存后置处理配置"""
        try:
            # 验证必填字段
            name = self.name_edit.text().strip()
            processing_type = self.type_combo.currentText()
            
            if not name:
                QMessageBox.warning(self, "警告", "请输入后置处理名称")
                return
            
            # 获取配置数据
            config = {}
            if processing_type == "数据提取":
                config['fields'] = self.get_fields_from_table()
            elif processing_type == "数据转换":
                config['rules'] = self.rules_edit.toPlainText().strip()
            elif processing_type == "数据验证":
                config['validation_rules'] = self.validation_edit.toPlainText().strip()
            elif processing_type == "数据存储":
                config['storage_type'] = self.storage_type_combo.currentText()
                config['storage_path'] = self.storage_path_edit.text().strip()
            elif processing_type == "自定义脚本":
                config['script'] = self.script_edit.toPlainText().strip()
            
            # 构建后置处理配置
            processing_config = {
                'type': 'post_processing',
                'name': name,
                'processing_type': processing_type,
                'description': self.desc_edit.toPlainText().strip(),
                'config': config
            }
            
            # 发出保存信号
            self.processing_saved.emit(processing_config)
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def get_post_processing_config(self):
        """获取后置处理配置"""
        processing_type = self.type_combo.currentText()
        
        # 获取配置数据
        config = {}
        if processing_type == "数据提取":
            config['fields'] = self.get_fields_from_table()
        elif processing_type == "数据转换":
            config['rules'] = self.rules_edit.toPlainText().strip()
        elif processing_type == "数据验证":
            config['validation_rules'] = self.validation_edit.toPlainText().strip()
        elif processing_type == "数据存储":
            config['storage_type'] = self.storage_type_combo.currentText()
            config['storage_path'] = self.storage_path_edit.text().strip()
        elif processing_type == "自定义脚本":
            config['script'] = self.script_edit.toPlainText().strip()
        
        return {
            'type': 'post_processing',
            'name': self.name_edit.text().strip(),
            'processing_type': processing_type,
            'description': self.desc_edit.toPlainText().strip(),
            'config': config
        }