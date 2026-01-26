import os
import json
import sys
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QLabel,
    QLineEdit,
    QTextEdit,
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QFormLayout,
    QApplication,
    QComboBox,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
from src.core.services.project_service import ProjectService
from src.core.services.business_service import BusinessService
from src.ui.interface_auto.components.no_wheel_widgets import NoWheelTabWidget
from src.ui.widgets.toast_tips import Toast
from src.utils.css_utils import get_combobox_style


class BusinessGroupDialog(QDialog):
    """业务分组编辑对话框"""

    def __init__(self, parent=None, group_data=None):
        super().__init__(parent)
        self.group_data = group_data or {}
        self.is_edit = bool(group_data)
        self.business_service = None
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
            self.name_edit.setText(self.group_data.get("name", ""))

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        self.desc_edit.setPlaceholderText("请输入业务分组描述")
        if self.group_data:
            self.desc_edit.setText(self.group_data.get("description", ""))

        form_layout.addRow("分组名称:", self.name_edit)
        form_layout.addRow("分组描述:", self.desc_edit)

        # 按钮布局
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)

        # 修改按钮文本
        button_box.button(QDialogButtonBox.Ok).setText("确认")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")

        layout.addLayout(form_layout)
        layout.addWidget(button_box)

    def set_business_service(self, business_service):
        """设置业务服务对象"""
        self.business_service = business_service

    def validate_and_accept(self):
        """校验并接受对话框"""
        name = self.name_edit.text().strip()
        if not name:
            Toast.warning(self, "警告", "分组名称不能为空")
            return

        # 检查名称是否重复（排除当前编辑的分组）
        if self.business_service:
            existing_groups = self.business_service.get_all_groups()
            for group in existing_groups:
                if group["name"] == name:
                    # 如果是编辑模式且名称未改变，允许通过
                    if self.is_edit and self.group_data.get("name") == name:
                        self.accept()
                        return
                    else:
                        Toast.warning(
                            self, "警告", f"分组名称 '{name}' 已存在，请使用其他名称"
                        )
                        return

        # 所有校验通过，接受对话框
        self.accept()

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "description": self.desc_edit.toPlainText().strip(),
        }


class ProjectDialog(QDialog):
    """项目编辑对话框"""

    def __init__(self, parent=None, project_data=None, group_id=None):
        super().__init__(parent)
        self.project_data = project_data or {}
        self.group_id = group_id
        self.is_edit = bool(project_data)
        self.project_service = None
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
            self.name_edit.setText(self.project_data.get("name", ""))

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        self.desc_edit.setPlaceholderText("请输入项目描述")
        if self.project_data:
            self.desc_edit.setText(self.project_data.get("description", ""))

        form_layout.addRow("项目名称:", self.name_edit)
        form_layout.addRow("项目描述:", self.desc_edit)

        # 按钮布局
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)

        # 修改按钮文本
        button_box.button(QDialogButtonBox.Ok).setText("确认")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")

        layout.addLayout(form_layout)
        layout.addWidget(button_box)

    def set_project_service(self, project_service):
        """设置项目服务对象"""
        self.project_service = project_service

    def validate_and_accept(self):
        """校验并接受对话框"""
        name = self.name_edit.text().strip()
        if not name:
            Toast.warning(self, "警告", "项目名称不能为空")
            return

        # 检查名称是否重复（排除当前编辑的项目）
        if self.project_service:
            # 获取当前业务分组下的所有项目
            group_id = self.group_id or self.project_data.get("group_id")
            if group_id:
                existing_projects = self.project_service.get_projects_by_group(group_id)
                for project in existing_projects:
                    if project["name"] == name:
                        # 如果是编辑模式且名称未改变，允许通过
                        if self.is_edit and self.project_data.get("name") == name:
                            self.accept()
                            return
                        else:
                            Toast.warning(
                                self,
                                "警告",
                                f"项目名称 '{name}' 已存在，请使用其他名称",
                            )
                            return

        # 所有校验通过，接受对话框
        self.accept()

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "description": self.desc_edit.toPlainText().strip(),
            "group_id": self.group_id or self.project_data.get("group_id"),
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
        left_widget.setMaximumWidth(360)
        left_layout = QVBoxLayout(left_widget)

        # 当前业务标题和下拉框
        group_header_layout = QHBoxLayout()
        group_header_layout.addWidget(QLabel("当前业务"))

        # 业务列表下拉框
        self.business_combo = QComboBox()
        self.business_combo.setMinimumWidth(150)
        self.business_combo.setStyleSheet(get_combobox_style())
        # 暂时不连接业务切换信号，等待所有页面准备好后再连接
        # self.business_combo.currentTextChanged.connect(self.on_business_changed)
        group_header_layout.addWidget(self.business_combo)

        group_header_layout.addStretch()

        self.add_group_btn = QPushButton()
        self.add_group_btn.setIcon(self.get_icon("add.png"))
        self.add_group_btn.setFixedSize(20, 20)  # 减小按钮尺寸
        self.add_group_btn.setToolTip("新增业务")
        self.add_group_btn.clicked.connect(self.add_business_group)
        self.add_group_btn.setStyleSheet(
            """
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
        """
        )

        group_header_layout.addWidget(self.add_group_btn)

        # 业务分组树
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["业务/项目", "操作"])
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        self.tree_widget.itemExpanded.connect(self.on_tree_item_expanded)
        self.tree_widget.itemCollapsed.connect(self.on_tree_item_collapsed)
        # 设置列宽
        self.tree_widget.setColumnWidth(0, 220)  # 名称列
        self.tree_widget.setColumnWidth(1, 80)  # 操作列
        # 隐藏表头
        self.tree_widget.setHeaderHidden(True)

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

        # 操作按钮（已删除，功能移至树形结构中的icon按钮）
        # 保留弹性空间以保持布局平衡
        button_layout = QHBoxLayout()
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

        self.setStyleSheet(
            """
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
        """
        )

    def get_icon(self, icon_name):
        """获取图标"""
        try:
            # 打包后路径处理：尝试从 PyInstaller 临时解压目录加载
            if getattr(sys, "frozen", False):
                # 打包后的可执行文件路径
                base_path = sys._MEIPASS
                # 尝试从打包后的 resources/icons 目录加载
                icon_path = os.path.join(
                    base_path, "src", "resources", "icons", icon_name
                )
                if os.path.exists(icon_path):
                    return QIcon(icon_path)

                # 尝试直接加载图标文件
                icon_path = os.path.join(base_path, icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)

                # 尝试从当前目录加载
                icon_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..",
                    "resources",
                    "icons",
                    icon_name,
                )
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
            return dt.strftime("%Y-%m-%d %H:%M:%S")
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
            if group["name"] == business_name:
                # 发射业务切换信号，传递业务分组ID
                self.business_changed.emit(group["id"])
                break

    def trigger_initial_business_change(self):
        """手动触发初始业务切换"""
        print(f"trigger_initial_business_change调用开始")
        print(f"initial_business_ready状态: {self.initial_business_ready}")
        print(f"business_groups是否存在: {self.business_groups is not None}")
        print(
            f"business_groups长度: {len(self.business_groups) if self.business_groups else 0}"
        )

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
        # 将 business_groups 重置为空列表，而不是调用 clear() 方法
        self.business_groups = []

        # 检查服务对象是否已初始化
        if self.business_service is None or self.project_service is None:
            return

        try:
            # 加载业务分组
            groups = self.business_service.get_all_groups()
            # 将元组转换为列表，确保可以调用 clear() 方法
            self.business_groups = list(groups)  # 存储业务分组列表

            for group in groups:
                # 添加到树形结构
                group_item = QTreeWidgetItem(self.tree_widget)
                group_item.setText(0, group["name"])
                group_item.setData(0, Qt.UserRole, {"type": "group", "data": group})
                group_item.setIcon(0, self.get_icon("group.png"))

                # 为业务分组添加操作按钮
                self.add_operation_buttons(group_item, "group", group)

                # 添加到下拉框
                self.business_combo.addItem(group["name"])

                # 加载该分组下的项目
                projects = self.project_service.get_projects_by_group(group["id"])
                for project in projects:
                    project_item = QTreeWidgetItem(group_item)
                    project_item.setText(0, project["name"])
                    project_item.setData(
                        0, Qt.UserRole, {"type": "project", "data": project}
                    )
                    project_item.setIcon(0, self.get_icon("project.png"))

                    # 为项目添加操作按钮
                    self.add_operation_buttons(project_item, "project", project)

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

            # 初始化时隐藏所有操作按钮
            self.hide_all_operation_buttons_except_current()

    def add_operation_buttons(self, item, item_type, item_data):
        """为树形项目添加操作按钮"""
        # 创建操作按钮容器
        operation_widget = QWidget()
        operation_layout = QHBoxLayout(operation_widget)
        operation_layout.setContentsMargins(0, 0, 0, 0)
        operation_layout.setSpacing(6)  # 增加按钮间距
        operation_layout.setAlignment(Qt.AlignCenter)

        # 为业务分组添加新增项目按钮
        if item_type == "group":
            add_project_btn = QPushButton()
            add_project_btn.setFixedSize(18, 18)
            add_project_btn.setIcon(self.get_icon("add_project.png"))
            add_project_btn.setToolTip("新增项目")
            add_project_btn.setStyleSheet(
                """
                QPushButton {
                    border: none;
                    background: transparent;
                    padding: 0px;
                    border-radius: 2px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 0, 0, 0.1);
                }
                QPushButton:pressed {
                    background-color: rgba(0, 0, 0, 0.2);
                }
            """
            )
            add_project_btn.clicked.connect(lambda: self.add_project(item_data["id"]))
            operation_layout.addWidget(add_project_btn)

        # 编辑按钮
        edit_btn = QPushButton()
        edit_btn.setFixedSize(20, 20)
        edit_btn.setIcon(self.get_icon("edit.png"))
        edit_btn.setToolTip("编辑")
        edit_btn.setStyleSheet(
            """
            QPushButton {
                border: none;
                background: transparent;
                padding: 0px;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 0.2);
            }
        """
        )

        # 删除按钮
        delete_btn = QPushButton()
        delete_btn.setFixedSize(20, 20)
        delete_btn.setIcon(self.get_icon("delete.png"))
        delete_btn.setToolTip("删除")
        delete_btn.setStyleSheet(
            """
            QPushButton {
                border: none;
                background: transparent;
                padding: 0px;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 0.2);
            }
        """
        )

        # 连接按钮事件
        if item_type == "group":
            edit_btn.clicked.connect(lambda: self.edit_business_group(item_data))
            delete_btn.clicked.connect(lambda: self.delete_business_group(item_data))
        else:
            edit_btn.clicked.connect(lambda: self.edit_project(item_data))
            delete_btn.clicked.connect(lambda: self.delete_project(item_data))

        # 添加按钮到布局
        operation_layout.addWidget(edit_btn)
        operation_layout.addWidget(delete_btn)

        # 默认隐藏操作按钮
        operation_widget.setVisible(False)

        # 存储按钮引用，用于后续显示/隐藏控制
        item.setData(0, Qt.UserRole + 1, operation_widget)

        # 设置操作列
        self.tree_widget.setItemWidget(item, 1, operation_widget)

    def on_tree_item_clicked(self, item):
        """树形项目点击事件"""
        # 隐藏所有行的操作按钮
        self.hide_all_operation_buttons_except_current()

        # 显示当前选中行的操作按钮
        operation_widget = item.data(0, Qt.UserRole + 1)
        if operation_widget:
            operation_widget.setVisible(True)

        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type = data["type"]
        item_data = data["data"]

        if item_type == "group":
            self.current_group = item_data
            self.current_project = None
            self.show_group_details(item_data)
        else:
            self.current_project = item_data
            self.current_group = None
            self.show_project_details(item_data)

    def on_tree_item_expanded(self, item):
        """树形项目展开事件"""
        # 使用极短延迟，确保UI更新完成但避免明显闪现
        QTimer.singleShot(5, lambda: self.hide_all_operation_buttons_except_current())

    def on_tree_item_collapsed(self, item):
        """树形项目收起事件"""
        # 使用极短延迟，确保UI更新完成但避免明显闪现
        QTimer.singleShot(5, lambda: self.hide_all_operation_buttons_except_current())

    def hide_all_operation_buttons(self, exclude_current_item=False):
        """隐藏所有行的操作按钮"""
        current_item = self.tree_widget.currentItem()

        # 遍历所有树形项目
        def hide_buttons(item):
            operation_widget = item.data(0, Qt.UserRole + 1)
            if operation_widget:
                # 如果设置了排除当前项，且当前项是当前选中的项，则显示操作按钮；否则隐藏
                if exclude_current_item and item == current_item:
                    operation_widget.setVisible(True)
                else:
                    operation_widget.setVisible(False)

            # 递归处理子项目
            for i in range(item.childCount()):
                hide_buttons(item.child(i))

        # 遍历根项目
        for i in range(self.tree_widget.topLevelItemCount()):
            hide_buttons(self.tree_widget.topLevelItem(i))

    def hide_all_operation_buttons_except_current(self):
        """隐藏所有行的操作按钮，只保留当前选中行的操作按钮"""
        current_item = self.tree_widget.currentItem()

        # 检查当前选中项是否可见（即其所有父节点都是展开状态）
        def is_item_visible(item):
            parent = item.parent()
            while parent:
                if not parent.isExpanded():
                    return False
                parent = parent.parent()
            return True

        # 遍历所有树形项目
        def process_item(item):
            operation_widget = item.data(0, Qt.UserRole + 1)
            if operation_widget:
                # 如果是当前选中项且可见，显示操作按钮；否则隐藏
                if item == current_item and is_item_visible(item):
                    operation_widget.setVisible(True)
                else:
                    operation_widget.setVisible(False)

            # 递归处理子项目
            for i in range(item.childCount()):
                process_item(item.child(i))

        # 遍历根项目
        for i in range(self.tree_widget.topLevelItemCount()):
            process_item(self.tree_widget.topLevelItem(i))

    def update_operation_buttons_visibility(self):
        """更新操作按钮的可见性状态，确保与树形控件的展开状态一致"""
        # 调用现有的按钮隐藏方法，确保操作按钮状态正确
        self.hide_all_operation_buttons_except_current()

    def show_group_details(self, group_data):
        """显示业务分组详情"""
        self.info_label.hide()
        self.detail_container.show()

        # 基本信息
        self.name_label.setText(group_data.get("name", ""))
        self.desc_label.setText(group_data.get("description", ""))

        # 格式化日期时间显示
        created_at = group_data.get("created_at", "")
        updated_at = group_data.get("updated_at", "")

        self.create_time_label.setText(self.format_datetime(created_at))
        self.update_time_label.setText(self.format_datetime(updated_at))

        # 统计信息
        stats = self.business_service.get_group_stats(group_data["id"])
        self.project_count_label.setText(str(stats.get("project_count", 0)))
        self.api_count_label.setText(str(stats.get("api_count", 0)))
        self.case_count_label.setText(str(stats.get("case_count", 0)))

    def show_project_details(self, project_data):
        """显示项目详情"""
        self.info_label.hide()
        self.detail_container.show()

        # 基本信息
        self.name_label.setText(project_data.get("name", ""))
        self.desc_label.setText(project_data.get("description", ""))

        # 格式化日期时间显示
        created_at = project_data.get("created_at", "")
        updated_at = project_data.get("updated_at", "")

        self.create_time_label.setText(self.format_datetime(created_at))
        self.update_time_label.setText(self.format_datetime(updated_at))

        # 统计信息
        stats = self.project_service.get_project_stats(project_data["id"])
        self.project_count_label.setText("-")  # 项目没有子项目
        self.api_count_label.setText(str(stats.get("api_count", 0)))
        self.case_count_label.setText(str(stats.get("case_count", 0)))

    def add_business_group(self):
        """新增业务分组"""
        dialog = BusinessGroupDialog(self)
        dialog.set_business_service(self.business_service)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                self.business_service.create_group(data)
                self.load_data()

                # 发射数据变化信号
                self.data_changed.emit()

                # 如果新增的业务分组是第一个，触发业务切换信号
                if len(self.business_groups) == 1:
                    self.business_changed.emit(self.business_groups[0]["id"])

                Toast.success(self, "业务分组创建成功")
            except Exception as e:
                Toast.error(self, f"创建业务分组失败: {str(e)}")

    def add_project(self, group_id):
        """新增项目"""
        dialog = ProjectDialog(self, group_id=group_id)
        dialog.set_project_service(self.project_service)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                # 保存更新前的展开状态
                expanded_states = self.get_tree_expanded_states()

                # 创建项目
                self.project_service.create_project(data)

                # 重新加载数据但保持展开状态
                self.load_data()
                self.restore_tree_expanded_states(expanded_states)

                # 发射数据变化信号和业务切换信号（传递当前业务ID）
                self.data_changed.emit()
                if group_id:
                    self.business_changed.emit(group_id)
                Toast.success(self, "项目创建成功")
            except Exception as e:
                Toast.error(self, f"创建项目失败: {str(e)}")

    def edit_current_item(self):
        """编辑当前选中的项目"""
        if self.current_group:
            self.edit_business_group(self.current_group)
        elif self.current_project:
            self.edit_project(self.current_project)

    def edit_business_group(self, group_data):
        """编辑业务分组"""
        # 创建对话框时使用数据的副本，避免修改原始数据
        dialog = BusinessGroupDialog(self, group_data.copy())
        dialog.set_business_service(self.business_service)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                # 保存更新前的展开状态
                expanded_states = self.get_tree_expanded_states()

                # 更新业务分组
                self.business_service.update_group(group_data["id"], data)

                # 局部更新树形结构中的对应项
                self.update_business_group_in_tree(group_data["id"], data)

                # 更新原始数据对象，确保下次编辑时显示最新数据
                group_data.update(data)

                # 恢复展开状态
                self.restore_tree_expanded_states(expanded_states)

                # 发射数据变化信号和业务切换信号（传递当前业务ID）
                self.data_changed.emit()
                self.business_changed.emit(group_data["id"])
                Toast.success(self, "业务分组更新成功")
            except Exception as e:
                Toast.error(self, f"更新业务分组失败: {str(e)}")

    def edit_project(self, project_data):
        """编辑项目"""
        # 创建对话框时使用数据的副本，避免修改原始数据
        dialog = ProjectDialog(self, project_data.copy())
        dialog.set_project_service(self.project_service)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                # 保存更新前的展开状态
                expanded_states = self.get_tree_expanded_states()

                # 获取当前项目的业务分组ID
                group_id = project_data.get("group_id")

                # 更新项目
                self.project_service.update_project(project_data["id"], data)

                # 局部更新树形结构中的对应项
                self.update_project_in_tree(project_data["id"], data)

                # 更新原始数据对象，确保下次编辑时显示最新数据
                project_data.update(data)

                # 恢复展开状态
                self.restore_tree_expanded_states(expanded_states)

                # 发射数据变化信号和业务切换信号（传递当前业务ID）
                self.data_changed.emit()
                if group_id:
                    self.business_changed.emit(group_id)
                Toast.success(self, "项目更新成功")
            except Exception as e:
                Toast.error(self, f"更新项目失败: {str(e)}")

    def delete_current_item(self):
        """删除当前选中的项目"""
        if self.current_group:
            self.delete_business_group(self.current_group)
        elif self.current_project:
            self.delete_project(self.current_project)

    def delete_business_group(self, group_data):
        """删除业务分组"""
        msg_box = QMessageBox(
            QMessageBox.Question,
            "确认删除",
            f"确定要删除业务分组 '{group_data['name']}' 吗？\n此操作将同时删除该分组下的所有项目！",
        )
        confirm_button = msg_box.addButton("确认", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_button)
        msg_box.exec_()
        reply = (
            QMessageBox.Yes
            if msg_box.clickedButton() == confirm_button
            else QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # 保存更新前的展开状态
                expanded_states = self.get_tree_expanded_states()

                # 删除业务分组
                self.business_service.delete_group(group_data["id"])

                # 重新加载数据但保持展开状态
                self.load_data()
                self.restore_tree_expanded_states(expanded_states)

                # 发射数据变化信号
                self.data_changed.emit()

                # 如果还有剩余的业务分组，切换到第一个业务分组
                if self.business_groups:
                    self.business_changed.emit(self.business_groups[0]["id"])

                self.info_label.show()
                self.detail_container.hide()
                Toast.success(self, "业务分组删除成功")
            except Exception as e:
                Toast.error(self, f"删除业务分组失败: {str(e)}")

    def delete_project(self, project_data):
        """删除项目"""
        msg_box = QMessageBox(
            QMessageBox.Question,
            "确认删除",
            f"确定要删除项目 '{project_data['name']}' 吗？",
        )
        confirm_button = msg_box.addButton("确认", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_button)
        msg_box.exec_()
        reply = (
            QMessageBox.Yes
            if msg_box.clickedButton() == confirm_button
            else QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # 保存更新前的展开状态
                expanded_states = self.get_tree_expanded_states()

                # 获取当前项目的业务分组ID
                group_id = project_data.get("group_id")

                # 删除项目
                self.project_service.delete_project(project_data["id"])

                # 重新加载数据但保持展开状态
                self.load_data()
                self.restore_tree_expanded_states(expanded_states)

                # 发射数据变化信号和业务切换信号（传递当前业务ID）
                self.data_changed.emit()
                if group_id:
                    self.business_changed.emit(group_id)
                self.info_label.show()
                self.detail_container.hide()
                Toast.success(self, "项目删除成功")
            except Exception as e:
                Toast.error(self, f"删除项目失败: {str(e)}")

    def showEvent(self, event):
        """页面显示事件处理"""
        super().showEvent(event)
        # 页面显示时，先隐藏所有操作按钮，然后重新显示当前选中项的操作按钮
        # 使用QApplication.processEvents()确保UI更新完成后再执行操作
        QApplication.processEvents()

        # 先隐藏所有按钮
        self.hide_all_operation_buttons_except_current()

        # 然后重新显示当前选中项的操作按钮
        current_item = self.tree_widget.currentItem()
        if current_item:
            operation_widget = current_item.data(0, Qt.UserRole + 1)
            if operation_widget:
                operation_widget.setVisible(True)

    def hideEvent(self, event):
        """页面隐藏事件处理"""
        super().hideEvent(event)
        # 页面隐藏时，确保所有操作按钮都隐藏
        self.hide_all_operation_buttons_except_current()

    def get_tree_expanded_states(self):
        """获取树形结构中所有分组的展开状态"""
        expanded_states = {}
        for i in range(self.tree_widget.topLevelItemCount()):
            group_item = self.tree_widget.topLevelItem(i)
            data = group_item.data(0, Qt.UserRole)
            if data and data["type"] == "group":
                group_id = data["data"]["id"]
                expanded_states[group_id] = group_item.isExpanded()
        return expanded_states

    def restore_tree_expanded_states(self, expanded_states):
        """恢复树形结构的展开状态"""
        for i in range(self.tree_widget.topLevelItemCount()):
            group_item = self.tree_widget.topLevelItem(i)
            data = group_item.data(0, Qt.UserRole)
            if data and data["type"] == "group":
                group_id = data["data"]["id"]
                if group_id in expanded_states:
                    group_item.setExpanded(expanded_states[group_id])

    def update_business_group_in_tree(self, group_id, new_data):
        """局部更新树形结构中的业务分组项"""
        for i in range(self.tree_widget.topLevelItemCount()):
            group_item = self.tree_widget.topLevelItem(i)
            data = group_item.data(0, Qt.UserRole)
            if data and data["type"] == "group" and data["data"]["id"] == group_id:
                # 更新分组名称
                group_item.setText(0, new_data["name"])

                # 更新数据
                updated_data = data["data"].copy()
                updated_data.update(new_data)
                group_item.setData(
                    0, Qt.UserRole, {"type": "group", "data": updated_data}
                )

                # 更新下拉框中的名称
                for j in range(self.business_combo.count()):
                    if self.business_combo.itemText(j) == data["data"]["name"]:
                        self.business_combo.setItemText(j, new_data["name"])
                        break

                # 如果当前显示的是该分组的详情，则更新详情显示
                if self.current_group and self.current_group["id"] == group_id:
                    self.current_group = updated_data
                    self.show_group_details(updated_data)

                break

    def update_project_in_tree(self, project_id, new_data):
        """局部更新树形结构中的项目项"""
        # 遍历所有分组和项目
        for i in range(self.tree_widget.topLevelItemCount()):
            group_item = self.tree_widget.topLevelItem(i)

            # 遍历该分组下的所有项目
            for j in range(group_item.childCount()):
                project_item = group_item.child(j)
                data = project_item.data(0, Qt.UserRole)
                if (
                    data
                    and data["type"] == "project"
                    and data["data"]["id"] == project_id
                ):
                    # 更新项目名称
                    project_item.setText(0, new_data["name"])

                    # 更新数据
                    updated_data = data["data"].copy()
                    updated_data.update(new_data)
                    project_item.setData(
                        0, Qt.UserRole, {"type": "project", "data": updated_data}
                    )

                    # 如果当前显示的是该项目的详情，则更新详情显示
                    if (
                        self.current_project
                        and self.current_project["id"] == project_id
                    ):
                        self.current_project = updated_data
                        self.show_project_details(updated_data)

                    return
