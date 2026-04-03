import os
import sys
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QDialogButtonBox,
    QWidget,
    QScrollArea,
    QFrame,
)
from PyQt5.QtCore import pyqtSignal, QSize
from PyQt5.QtGui import QIcon
from src.ui.widgets.toast_tips import Toast
from src.utils.css_utils import get_combobox_style


class AssertionDialog(QDialog):
    """断言工具配置对话框 - 新版支持多行断言配置"""

    assertion_saved = pyqtSignal(dict)  # 断言配置保存信号

    # 断言符号选项
    ASSERTION_SYMBOLS = {
        "equal": "=",
        "not_equal": "!=",
        "contains": "~",
        "not_contains": "!~",
        "greater": ">",
        "less": "<",
        "greater_equal": "≥",
        "less_equal": "≤",
    }

    def __init__(self, parent=None, assertion_data=None):
        super().__init__(parent)
        self.assertion_data = assertion_data or {}
        self.is_edit = bool(assertion_data)
        self.assertion_rows = []  # 存储断言行控件
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("编辑断言" if self.is_edit else "新增断言")
        self.setMinimumSize(800, 500)

        # 设置断言图标
        self.setWindowIcon(self.get_icon("assrt.png"))

        # 设置对话框样式
        self.setStyleSheet(
            """
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
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
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
            .assertion-row {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px;
                margin: 4px 0;
                background-color: #fafafa;
            }
            .assertion-row:hover {
                background-color: #f0f0f0;
            }
        """
        )

        layout = QVBoxLayout(self)

        # 名称字段 - 直接添加到主布局，不分组
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入断言名称")
        name_layout.addWidget(self.name_edit)
        name_layout.addStretch()
        layout.addLayout(name_layout)

        # 断言配置区域 - 去掉分组标题和边框
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        config_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距

        # 创建滚动区域
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
        else:
            # 默认添加一行断言
            self.add_assertion_row()

        # 确保第一行从顶部开始显示，不居中
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
            if getattr(sys, "frozen", False):
                meipass_path = os.path.join(
                    sys._MEIPASS, "src", "resources", "icons", icon_name
                )
                if os.path.exists(meipass_path):
                    return QIcon(meipass_path)

            # 如果所有路径都失败，返回空图标
            print(f"图标加载失败: {icon_name}")
            return QIcon()

        except Exception as e:
            print(f"图标加载异常 {icon_name}: {e}")
            return QIcon()

    def add_assertion_row(self, insert_after_row=None):
        """添加一行断言配置"""
        row_widget = QWidget()
        row_widget.setObjectName("assertion-row")
        row_widget.setStyleSheet(
            """
            QWidget#assertion-row {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px;
                margin: 4px 0;
                background-color: #fafafa;
            }
            QWidget#assertion-row:hover {
                background-color: #f0f0f0;
            }
        """
        )

        row_layout = QHBoxLayout(row_widget)
        row_layout.setSpacing(10)

        # 添加按钮 - 使用图标
        add_button = QPushButton()
        add_button.setFixedSize(22, 22)
        # 使用add.png图标
        add_button.setIcon(self.get_icon("add.png"))
        add_button.setIconSize(QSize(14, 14))
        add_button.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #e8f5e8;
                border-radius: 3px;
            }
        """
        )

        # 断言字段输入框
        field_edit = QLineEdit()
        field_edit.setPlaceholderText("支持${变量名}或jsonpath")
        field_edit.setMinimumWidth(200)

        # 断言符号选择下拉框
        symbol_combo = QComboBox()
        symbol_combo.setStyleSheet(get_combobox_style())
        for symbol_key, symbol_text in self.ASSERTION_SYMBOLS.items():
            symbol_combo.addItem(symbol_text, symbol_key)
        symbol_combo.setCurrentText("=")  # 默认选择"="

        # 预期值输入框
        expected_edit = QLineEdit()
        expected_edit.setPlaceholderText("预期值（可为空）")
        expected_edit.setMinimumWidth(150)

        # 删除按钮 - 使用图标
        delete_button = QPushButton()
        delete_button.setFixedSize(22, 22)
        # 使用sub.png图标
        delete_button.setIcon(self.get_icon("sub.png"))
        delete_button.setIconSize(QSize(14, 14))
        delete_button.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #ffebee;
                border-radius: 3px;
            }
        """
        )

        # 存储行信息
        row_data = {
            "widget": row_widget,
            "field_edit": field_edit,
            "symbol_combo": symbol_combo,
            "expected_edit": expected_edit,
            "add_button": add_button,
            "delete_button": delete_button,
        }

        # 连接按钮事件 - 传递当前行信息以便在正确位置插入
        add_button.clicked.connect(
            lambda checked, row=row_data: self.add_assertion_row(row)
        )
        delete_button.clicked.connect(lambda: self.remove_assertion_row(row_data))

        # 添加到布局 - 添加按钮在删除按钮旁边
        row_layout.addWidget(field_edit)
        row_layout.addWidget(symbol_combo)
        row_layout.addWidget(expected_edit)
        row_layout.addWidget(add_button)
        row_layout.addWidget(delete_button)

        # 确定插入位置
        if insert_after_row is None:
            # 默认添加到末尾
            self.scroll_layout.addWidget(row_widget)
            self.assertion_rows.append(row_data)
        else:
            # 在当前行下方插入新行
            insert_index = self.assertion_rows.index(insert_after_row) + 1
            self.scroll_layout.insertWidget(insert_index, row_widget)
            self.assertion_rows.insert(insert_index, row_data)

    def remove_assertion_row(self, row_data):
        """删除一行断言配置"""
        if len(self.assertion_rows) <= 1:
            Toast.info(self, "至少需要保留一行断言配置")
            return

        # 从布局中移除
        self.scroll_layout.removeWidget(row_data["widget"])
        row_data["widget"].deleteLater()

        # 从列表中移除
        self.assertion_rows.remove(row_data)

    def load_assertion_data(self):
        """加载断言数据 - 支持新旧两种格式"""
        try:
            if not self.assertion_data:
                return

            # 判断数据格式：新格式包含type字段，旧格式直接包含name和assertions
            if "type" in self.assertion_data:
                # 新格式：{'type': 'assertion_type', 'config': {...}}
                config = self.assertion_data.get("config", {})
                name = config.get("name", "")
                assertions = config.get("assertions", [])
            else:
                # 旧格式：{'name': '名称', 'assertions': [...]}
                name = self.assertion_data.get("name", "")
                assertions = self.assertion_data.get("assertions", [])

            # 名称
            self.name_edit.setText(name)

            # 清除现有行
            for row_data in self.assertion_rows:
                self.scroll_layout.removeWidget(row_data["widget"])
                row_data["widget"].deleteLater()
            self.assertion_rows.clear()

            # 加载断言行
            if assertions:
                for assertion in assertions:
                    self.add_assertion_row()
                    row_data = self.assertion_rows[-1]

                    # 填充数据
                    row_data["field_edit"].setText(assertion.get("field", ""))

                    symbol = assertion.get("symbol", "equal")
                    symbol_text = self.ASSERTION_SYMBOLS.get(symbol, "=")
                    index = row_data["symbol_combo"].findText(symbol_text)
                    if index >= 0:
                        row_data["symbol_combo"].setCurrentIndex(index)

                    # 期望值：保持原值，包括None（显示为空字符串）
                    expected = assertion.get("expected")
                    row_data["expected_edit"].setText(
                        expected if expected is not None else ""
                    )
            else:
                # 如果没有数据，添加默认行
                self.add_assertion_row()

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

            # 验证断言行
            assertions = []
            for row_data in self.assertion_rows:
                field = row_data["field_edit"].text().strip()
                if not field:
                    Toast.error(self, "断言字段不能为空")
                    return

                symbol_text = row_data["symbol_combo"].currentText()
                symbol = row_data["symbol_combo"].currentData()
                expected = row_data["expected_edit"].text().strip()
                # 如果期望值为空字符串，设置为None
                if expected == "":
                    expected = None

                assertions.append(
                    {
                        "field": field,
                        "symbol": symbol,
                        "symbol_text": symbol_text,
                        "expected": expected,
                    }
                )

            # 构建断言配置 - 使用新的字段路径提取断言类型
            # 所有符号都映射到同一个断言类型，实际比较逻辑在断言执行时处理
            assertion_config = {
                "type": "field_path_assertion",  # 新的断言类型，支持字段路径提取和变量替换
                "config": {"name": name, "enabled": True, "assertions": assertions},
            }

            # 发送保存信号
            self.assertion_saved.emit(assertion_config)

            # 关闭对话框
            self.accept()

        except Exception as e:
            print(f"保存断言配置失败: {str(e)}")
            Toast.error(self, f"保存断言配置失败: {str(e)}")

    def save_assertion_data(self):
        """保存断言数据"""
        try:
            # 名称
            self.assertion_data["name"] = self.name_edit.text().strip()

            # 断言配置
            assertions = []
            for row_data in self.assertion_rows:
                field = row_data["field_edit"].text().strip()
                symbol = row_data["symbol_combo"].currentData()
                expected = row_data["expected_edit"].text().strip()
                # 如果期望值为空字符串，设置为None
                if expected == "":
                    expected = None

                assertions.append(
                    {"field": field, "symbol": symbol, "expected": expected}
                )

            self.assertion_data["assertions"] = assertions

            return True

        except Exception as e:
            print(f"保存断言数据失败: {str(e)}")
            return False
