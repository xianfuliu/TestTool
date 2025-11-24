import os
import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QComboBox, QPushButton, QDialogButtonBox,
                             QWidget, QScrollArea, QFrame)
from PyQt5.QtCore import pyqtSignal, QSize
from PyQt5.QtGui import QIcon
from src.ui.widgets.toast_tips import Toast


class ParameterExtractionDialog(QDialog):
    """参数提取工具配置对话框 - 完全参考断言弹窗设计"""
    
    extraction_saved = pyqtSignal(dict)  # 参数提取配置保存信号
    
    def __init__(self, parent=None, extraction_data=None):
        super().__init__(parent)
        self.extraction_data = extraction_data or {}
        self.is_edit = bool(extraction_data)
        self.extraction_rows = []  # 存储参数提取行控件
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("编辑参数提取" if self.is_edit else "新增参数提取")
        self.setMinimumSize(800, 500)
        
        # 设置参数提取图标
        self.setWindowIcon(self.get_icon("extraction.png"))
        
        # 设置对话框样式 - 完全参考断言弹窗
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 6px;
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
            QLineEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 4px;
            }
            .extraction-row {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px;
                margin: 4px 0;
                background-color: #fafafa;
            }
            .extraction-row:hover {
                background-color: #f0f0f0;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # 名称字段 - 完全参考断言弹窗布局
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入参数提取名称")
        name_layout.addWidget(self.name_edit)
        name_layout.addStretch()
        layout.addLayout(name_layout)
        
        # 参数提取配置区域 - 完全参考断言弹窗设计
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        config_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 创建滚动区域 - 参考断言弹窗
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(300)
        scroll_area.setFrameShape(QFrame.NoFrame)  # 移除边框
        
        # 滚动区域内容
        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        scroll_area.setWidget(scroll_content)
        config_layout.addWidget(scroll_area)
        
        layout.addWidget(config_widget)
        
        # 按钮布局 - 完全参考断言弹窗
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_save)
        button_box.rejected.connect(self.reject)
        
        # 修改按钮文本
        button_box.button(QDialogButtonBox.Ok).setText("确认")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        
        layout.addWidget(button_box)
        
        # 加载数据 - 完全参考断言弹窗逻辑
        if self.is_edit:
            self.load_extraction_data()
        else:
            # 默认添加一行参数提取配置
            self.add_extraction_row()
            # 设置默认名称：参数提取
            self.name_edit.setText("参数提取")
            
        # 确保第一行从顶部开始显示，不居中 - 参考断言弹窗
        self.scroll_layout.addStretch()
    
    def get_icon(self, icon_name):
        """获取图标，支持PyInstaller打包路径处理"""
        try:
            # 尝试从开发环境路径加载
            dev_path = os.path.join("src", "resources", "icons", icon_name)
            if os.path.exists(dev_path):
                return QIcon(dev_path)
            
            # 尝试从exe打包后路径加载
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            exe_path = os.path.join(exe_dir, "src", "resources", "icons", icon_name)
            if os.path.exists(exe_path):
                return QIcon(exe_path)
            
            # 尝试相对路径
            relative_path = os.path.join("src", "resources", "icons", icon_name)
            if os.path.exists(relative_path):
                return QIcon(relative_path)
            
            # 尝试sys._MEIPASS临时解压路径（PyInstaller打包时）
            if getattr(sys, 'frozen', False):
                meipass_path = os.path.join(sys._MEIPASS, "src", "resources", "icons", icon_name)
                if os.path.exists(meipass_path):
                    return QIcon(meipass_path)
            
            # 如果所有路径都失败，返回空图标
            print(f"图标加载失败: {icon_name}")
            return QIcon()
            
        except Exception as e:
            print(f"图标加载异常 {icon_name}: {e}")
            return QIcon()
    
    def add_extraction_row(self, insert_after_row=None):
        """添加一行参数提取配置 - 完全参考断言弹窗交互逻辑"""
        row_widget = QWidget()
        row_widget.setObjectName("extraction-row")
        row_widget.setStyleSheet("""
            QWidget#extraction-row {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px;
                margin: 4px 0;
                background-color: #fafafa;
            }
            QWidget#extraction-row:hover {
                background-color: #f0f0f0;
            }
        """)
        
        row_layout = QHBoxLayout(row_widget)
        row_layout.setSpacing(10)
        
        # 添加按钮 - 完全参考断言弹窗设计
        add_button = QPushButton()
        add_button.setFixedSize(22, 22)
        add_button.setIcon(self.get_icon("add.png"))
        add_button.setIconSize(QSize(14, 14))
        add_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #e8f5e8;
                border-radius: 3px;
            }
        """)
        
        # 变量名称输入框 - 参考断言弹窗布局
        variable_edit = QLineEdit()
        variable_edit.setPlaceholderText("变量名称")
        variable_edit.setMinimumWidth(150)
        
        # 提取路径输入框 - 参考断言弹窗布局
        path_edit = QLineEdit()
        path_edit.setPlaceholderText("JSONPath表达式")
        path_edit.setMinimumWidth(200)
        
        # 删除按钮 - 完全参考断言弹窗设计
        delete_button = QPushButton()
        delete_button.setFixedSize(22, 22)
        delete_button.setIcon(self.get_icon("sub.png"))
        delete_button.setIconSize(QSize(14, 14))
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #ffebee;
                border-radius: 3px;
            }
        """)
        
        # 存储行信息 - 参考断言弹窗数据结构
        row_data = {
            'widget': row_widget,
            'variable_edit': variable_edit,
            'path_edit': path_edit,
            'add_button': add_button,
            'delete_button': delete_button
        }
        
        # 连接按钮事件 - 完全参考断言弹窗交互逻辑
        add_button.clicked.connect(lambda checked, row=row_data: self.add_extraction_row(row))
        delete_button.clicked.connect(lambda: self.remove_extraction_row(row_data))
        
        # 添加到布局 - 参考断言弹窗布局顺序
        row_layout.addWidget(variable_edit)
        row_layout.addWidget(path_edit)
        row_layout.addWidget(add_button)
        row_layout.addWidget(delete_button)
        
        # 确定插入位置 - 完全参考断言弹窗逻辑
        if insert_after_row is None:
            # 默认添加到末尾
            self.scroll_layout.addWidget(row_widget)
            self.extraction_rows.append(row_data)
        else:
            # 在当前行下方插入新行
            insert_index = self.extraction_rows.index(insert_after_row) + 1
            self.scroll_layout.insertWidget(insert_index, row_widget)
            self.extraction_rows.insert(insert_index, row_data)
    
    def remove_extraction_row(self, row_data):
        """删除一行参数提取配置 - 完全参考断言弹窗交互逻辑"""
        if len(self.extraction_rows) <= 1:
            # 至少保留一行 - 参考断言弹窗限制逻辑
            return
        
        # 从布局中移除 - 参考断言弹窗移除逻辑
        self.scroll_layout.removeWidget(row_data['widget'])
        row_data['widget'].deleteLater()
        
        # 从列表中移除 - 参考断言弹窗数据管理
        self.extraction_rows.remove(row_data)
    
    def load_extraction_data(self):
        """加载参数提取数据 - 完全参考断言弹窗数据处理逻辑"""
        if not self.extraction_data:
            return
            
        # 处理新的数据结构（包含type和config字段）
        config_data = self.extraction_data
        if 'config' in self.extraction_data:
            config_data = self.extraction_data['config']
            
        # 基本信息 - 参考断言弹窗数据加载逻辑
        if 'name' in config_data:
            self.name_edit.setText(config_data['name'])
            
        # 参数提取配置 - 参考断言弹窗数据加载逻辑
        if 'extractions' in config_data:
            # 先清空现有行 - 参考断言弹窗数据清理逻辑
            for row_data in self.extraction_rows[:]:
                self.remove_extraction_row(row_data)
                
            # 加载提取配置 - 参考断言弹窗数据加载逻辑
            for extraction in config_data['extractions']:
                self.add_extraction_row()
                last_row = self.extraction_rows[-1]
                
                if 'variable_name' in extraction:
                    last_row['variable_edit'].setText(extraction['variable_name'])
                if 'json_path' in extraction:
                    last_row['path_edit'].setText(extraction['json_path'])
        else:
            # 如果没有提取配置数据，默认添加一行 - 参考断言弹窗默认行为
            self.add_extraction_row()
    
    def save_extraction_data(self):
        """保存参数提取配置数据 - 完全参考断言弹窗数据验证和保存逻辑"""
        extractions = []
        
        for row_data in self.extraction_rows:
            variable_name = row_data['variable_edit'].text().strip()
            json_path = row_data['path_edit'].text().strip()
            
            # 只保存非空配置 - 参考断言弹窗数据验证逻辑
            if variable_name or json_path:
                extractions.append({
                    'variable_name': variable_name,
                    'json_path': json_path
                })
        
        return extractions
    
    def on_save(self):
        """保存按钮点击事件 - 完全参考断言弹窗验证和保存逻辑"""
        name = self.name_edit.text().strip()
        if not name:
            Toast.info(self, "请输入参数提取工具名称")
            return
        
        extraction_data = self.save_extraction_data()
        
        # 验证至少有一个有效的参数提取配置 - 参考断言弹窗验证逻辑
        if not extraction_data:
            Toast.info(self, "请至少配置一个参数提取项")
            return
        
        # 验证每个配置项 - 参考断言弹窗数据验证逻辑
        for extraction in extraction_data:
            if not extraction['variable_name']:
                Toast.info(self, "请为每个参数提取项设置变量名称")
                return
            if not extraction['json_path']:
                Toast.info(self, "请为每个参数提取项设置JSONPath表达式")
                return
        
        # 构建参数提取配置 - 参考断言弹窗数据结构
        extraction_config = {
            'type': 'parameter_extraction',  # 参数提取类型
            'config': {
                'name': name,
                'enabled': True,
                'extractions': extraction_data
            }
        }
        
        self.extraction_data = extraction_config
        self.extraction_saved.emit(extraction_config)
        self.accept()