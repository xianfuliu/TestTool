"""测试用例多标签页编辑器"""

import os
from PyQt5.QtCore import pyqtSignal, Qt, QDataStream, QIODevice
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, 
    QLineEdit, QTextEdit, QComboBox, QPushButton, QFormLayout,
    QGroupBox, QMessageBox, QDialogButtonBox, QSplitter, QMenu
)
from PyQt5.QtGui import QIcon

from src.ui.widgets.toast_tips import Toast


class CaseTabWidget(QWidget):
    """测试用例标签页组件"""
    
    modified_signal = pyqtSignal(bool)  # 修改状态信号
    saved = pyqtSignal(dict)  # 保存信号
    
    def __init__(self, case_data=None, project_id=None, folder_id=None):
        super().__init__()
        self.case_data = case_data or {}
        self.project_id = project_id
        self.folder_id = folder_id
        self.is_edit = bool(case_data)
        self.modified = False
        
        self.init_ui()
        
        # 如果是编辑模式，加载数据
        if self.is_edit:
            self.load_case_data()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建分割器，实现可调整大小的布局
        splitter = QSplitter(Qt.Vertical)
        
        # 用例信息区域（上半部分）
        case_info_widget = QWidget()
        self.setup_case_info_tab(case_info_widget)
        
        # 测试步骤区域（下半部分）
        steps_widget = QWidget()
        self.setup_steps_tab(steps_widget)
        
        splitter.addWidget(case_info_widget)
        splitter.addWidget(steps_widget)
        
        # 设置分割器比例（用例信息占40%，测试步骤占60%）
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_case)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel)
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def setup_case_info_tab(self, parent):
        """设置用例信息区域"""
        layout = QVBoxLayout(parent)
        layout.setSpacing(10)
        
        # 基础信息区域
        basic_group = QGroupBox("基础信息")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        
        # 用例名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入用例名称")
        self.name_edit.textChanged.connect(self.on_content_changed)
        basic_layout.addRow("用例名称:", self.name_edit)
        
        # 用例描述
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setPlaceholderText("请输入用例描述")
        self.description_edit.textChanged.connect(self.on_content_changed)
        basic_layout.addRow("用例描述:", self.description_edit)
        
        # 环境选择
        self.env_combo = QComboBox()
        self.env_combo.addItem("测试环境")
        self.env_combo.addItem("预发布环境")
        self.env_combo.addItem("生产环境")
        self.env_combo.currentTextChanged.connect(self.on_content_changed)
        basic_layout.addRow("环境:", self.env_combo)
        
        layout.addWidget(basic_group)
        
        # 全局变量区域
        global_var_group = QGroupBox("全局变量")
        global_var_layout = QVBoxLayout(global_var_group)
        
        self.global_var_edit = QTextEdit()
        self.global_var_edit.setMaximumHeight(100)
        self.global_var_edit.setPlaceholderText("请输入全局变量，格式：变量名=变量值，每行一个")
        self.global_var_edit.textChanged.connect(self.on_content_changed)
        global_var_layout.addWidget(self.global_var_edit)
        
        layout.addWidget(global_var_group)
        
        # 执行日志按钮
        log_btn_layout = QHBoxLayout()
        self.log_btn = QPushButton("执行日志")
        self.log_btn.clicked.connect(self.show_execution_logs)
        log_btn_layout.addStretch()
        log_btn_layout.addWidget(self.log_btn)
        
        layout.addLayout(log_btn_layout)
        layout.addStretch()
    
    def setup_steps_tab(self, parent):
        """设置测试步骤区域"""
        layout = QVBoxLayout(parent)
        layout.setSpacing(5)
        
        # 测试步骤区域
        steps_group = QGroupBox("测试步骤")
        steps_layout = QVBoxLayout(steps_group)
        
        # 添加步骤按钮
        add_step_btn = QPushButton("添加步骤")
        add_step_btn.clicked.connect(self.add_test_step)
        steps_layout.addWidget(add_step_btn)
        
        # 步骤列表区域（支持拖拽的文本编辑框）
        self.steps_edit = QTextEdit()
        self.steps_edit.setPlaceholderText("测试步骤将在这里显示和编辑\n\n支持从接口模板列表拖拽接口到此区域")
        self.steps_edit.textChanged.connect(self.on_content_changed)
        
        # 启用拖拽功能
        self.steps_edit.setAcceptDrops(True)
        self.steps_edit.dragEnterEvent = self.drag_enter_event
        self.steps_edit.dragMoveEvent = self.drag_move_event
        self.steps_edit.dropEvent = self.drop_event
        
        steps_layout.addWidget(self.steps_edit)
        
        layout.addWidget(steps_group)
        layout.addStretch()
    
    def on_content_changed(self):
        """内容变化时标记为已修改"""
        if not self.modified:
            self.modified = True
            self.modified_signal.emit(True)
    
    def load_case_data(self):
        """加载用例数据"""
        if not self.case_data:
            return
        
        # 加载基础信息
        self.name_edit.setText(self.case_data.get('name', ''))
        self.description_edit.setPlainText(self.case_data.get('description', ''))
        
        # 加载环境
        env = self.case_data.get('environment', '测试环境')
        index = self.env_combo.findText(env)
        if index >= 0:
            self.env_combo.setCurrentIndex(index)
        
        # 加载全局变量
        global_vars = self.case_data.get('global_variables', '')
        if isinstance(global_vars, tuple):
            global_vars = str(global_vars)
        self.global_var_edit.setPlainText(str(global_vars))
        
        # 加载测试步骤
        steps = self.case_data.get('steps', '')
        if isinstance(steps, tuple):
            steps = str(steps)
        self.steps_edit.setPlainText(str(steps))
        
        # 重置修改状态
        self.modified = False
        self.modified_signal.emit(False)
    
    def save_case(self):
        """保存用例"""
        # 收集数据
        case_data = {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'environment': self.env_combo.currentText(),
            'global_variables': self.global_var_edit.toPlainText().strip(),
            'steps': self.steps_edit.toPlainText().strip(),
            'project_id': self.project_id,
            'folder_id': self.folder_id
        }
        
        # 验证数据
        if not case_data['name']:
            Toast.warning(self, "用例名称不能为空")
            return
        
        # 如果是编辑模式，添加ID
        if self.is_edit and 'id' in self.case_data:
            case_data['id'] = self.case_data['id']
        
        # 发送保存信号
        self.saved.emit(case_data)
        
        # 标记为已保存
        self.modified = False
        self.modified_signal.emit(False)
    
    def cancel(self):
        """取消编辑"""
        if self.modified:
            # 对于确认对话框，暂时保留QMessageBox.question，因为Toast不支持确认对话框
            reply = QMessageBox.question(
                self, "确认取消",
                "有未保存的修改，确定要取消吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # 关闭标签页
        self.close()
    
    def show_execution_logs(self):
        """显示执行日志"""
        Toast.info(self, "执行日志功能将在后续版本中实现")
    
    def drag_enter_event(self, event):
        """拖拽进入事件"""
        # 检查拖拽数据是否包含接口模板信息
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def drag_move_event(self, event):
        """拖拽移动事件"""
        # 检查拖拽数据是否包含接口模板信息
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def drop_event(self, event):
        """拖拽放置事件"""
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            # 解析拖拽数据
            mime_data = event.mimeData()
            item_data = self.parse_drag_data(mime_data)
            
            if item_data and item_data.get('type') == 'template':
                # 添加接口模板到测试步骤
                self.add_api_template_to_steps(item_data['data'])
                event.acceptProposedAction()
                return
        
        event.ignore()
    
    def parse_drag_data(self, mime_data):
        """解析拖拽数据"""
        try:
            # 解析QAbstractItemModel数据
            data = mime_data.data("application/x-qabstractitemmodeldatalist")
            stream = QDataStream(data, QIODevice.ReadOnly)
            
            # 读取拖拽数据
            while not stream.atEnd():
                row = stream.readInt32()
                column = stream.readInt32()
                
                # 读取数据项
                item_count = stream.readInt32()
                for i in range(item_count):
                    role = stream.readInt32()
                    value = stream.readQVariant()
                    
                    # 如果是用户角色数据，尝试解析JSON
                    if role == Qt.UserRole:
                        try:
                            import json
                            item_data = json.loads(value)
                            return item_data
                        except:
                            pass
            
            return None
        except Exception as e:
            print(f"解析拖拽数据失败: {str(e)}")
            return None
    
    def add_api_template_to_steps(self, template_data):
        """添加接口模板到测试步骤"""
        try:
            # 获取当前步骤文本
            current_steps = self.steps_edit.toPlainText().strip()
            
            # 创建步骤描述
            step_description = f"""
步骤名称: {template_data.get('name', '未命名接口')}
接口方法: {template_data.get('method', 'GET')}
接口路径: {template_data.get('url_path', '')}
描述: {template_data.get('description', '')}

请求参数:
{template_data.get('request_params', '')}

请求头:
{template_data.get('request_headers', '')}

请求体:
{template_data.get('request_body', '')}

预期结果:
{template_data.get('expected_result', '')}

---
"""
            
            # 添加到步骤中
            if current_steps:
                new_steps = current_steps + "\n" + step_description
            else:
                new_steps = step_description
            
            self.steps_edit.setPlainText(new_steps)
            
            # 标记为已修改
            if not self.modified:
                self.modified = True
                self.modified_signal.emit(True)
                
        except Exception as e:
            Toast.error(self, f"添加接口模板到测试步骤失败: {str(e)}")
    
    def add_test_step(self):
        """添加测试步骤"""
        Toast.info(self, "添加测试步骤功能将在后续版本中实现")


class TabbedCaseEditor(QWidget):
    """测试用例多标签页编辑器"""
    
    tab_closed = pyqtSignal()  # 标签页关闭信号
    saved = pyqtSignal(dict)    # 保存信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabs = {}  # 存储标签页数据
        self.current_tab_id = None
        
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.tab_changed)
        
        # 设置tab右键菜单
        self.tab_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self.show_tab_context_menu)
        
        layout.addWidget(self.tab_widget)
    
    def open_case(self, case_data=None, project_id=None, folder_id=None):
        """打开或创建用例编辑标签页"""
        # 生成标签页ID
        tab_id = self.generate_tab_id(case_data)
        
        # 如果标签页已存在，切换到该标签页
        if tab_id in self.tabs:
            index = self.tab_widget.indexOf(self.tabs[tab_id]['widget'])
            self.tab_widget.setCurrentIndex(index)
            return tab_id
        
        # 创建新的标签页
        editor_widget = CaseTabWidget(case_data, project_id, folder_id)
        
        # 连接信号
        editor_widget.modified_signal.connect(lambda modified: self.set_tab_modified(tab_id, modified))
        editor_widget.saved.connect(lambda data: self.case_saved(tab_id, data))
        
        # 添加到标签页
        tab_name = case_data.get('name', '新增用例') if case_data else '新增用例'
        index = self.tab_widget.addTab(editor_widget, tab_name)
        
        # 存储标签页数据
        self.tabs[tab_id] = {
            'widget': editor_widget,
            'data': case_data or {},
            'modified': False,
            'tab_name': tab_name
        }
        
        # 设置当前标签页
        self.tab_widget.setCurrentIndex(index)
        self.current_tab_id = tab_id
        
        return tab_id
    
    def generate_tab_id(self, case_data):
        """生成标签页唯一ID"""
        if case_data and 'id' in case_data:
            return f"case_{case_data['id']}"
        else:
            return f"new_case_{len(self.tabs)}"
    
    def close_tab(self, index, from_close_button=True):
        """关闭标签页"""
        widget = self.tab_widget.widget(index)
        
        # 查找对应的标签页ID
        tab_id = None
        for tid, tab_data in self.tabs.items():
            if tab_data['widget'] == widget:
                tab_id = tid
                break
        
        if tab_id is None:
            self.tab_widget.removeTab(index)
            # 检查是否还有标签页，如果没有则发出关闭信号
            if self.tab_widget.count() == 0:
                self.tab_closed.emit()
            return
        
        # 检查是否有未保存的修改
        if self.tabs[tab_id]['modified']:
            # 显示保存确认弹窗
            tab_name = self.tabs[tab_id]['tab_name']
            
            # 创建自定义消息框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('保存确认')
            msg_box.setText(f'标签页 "{tab_name}" 有未保存的修改，请选择操作：')
            
            # 添加自定义按钮
            save_btn = msg_box.addButton('保存', QMessageBox.AcceptRole)
            ignore_btn = msg_box.addButton('忽略', QMessageBox.DestructiveRole)
            cancel_btn = msg_box.addButton('取消', QMessageBox.RejectRole)
            
            # 设置默认按钮
            msg_box.setDefaultButton(save_btn)
            
            msg_box.exec_()
            
            clicked_button = msg_box.clickedButton()
            
            if clicked_button == save_btn:
                # 保存用例
                self.tabs[tab_id]['widget'].save_case()
                # 保存完成后，标记标签页为已保存状态
                self.set_tab_modified(tab_id, False)
                
                # 保存后关闭标签页
                self.tab_widget.removeTab(index)
                del self.tabs[tab_id]
                # 检查是否还有标签页，如果没有则发出关闭信号
                if self.tab_widget.count() == 0:
                    self.tab_closed.emit()
            elif clicked_button == ignore_btn:
                # 忽略修改，直接关闭
                self.tab_widget.removeTab(index)
                del self.tabs[tab_id]
                # 检查是否还有标签页，如果没有则发出关闭信号
                if self.tab_widget.count() == 0:
                    self.tab_closed.emit()
            else:
                # 取消关闭
                return
        else:
            # 没有修改，直接关闭
            self.tab_widget.removeTab(index)
            del self.tabs[tab_id]
            # 检查是否还有标签页，如果没有则发出关闭信号
            if self.tab_widget.count() == 0:
                self.tab_closed.emit()
    
    def show_tab_context_menu(self, pos):
        """显示tab右键菜单"""
        # 获取点击位置的tab索引
        index = self.tab_widget.tabBar().tabAt(pos)
        if index == -1:
            return
            
        # 创建右键菜单
        menu = QMenu(self)
        
        # 添加菜单项
        close_current_action = menu.addAction("关闭当前")
        close_others_action = menu.addAction("关闭其他")
        close_all_action = menu.addAction("关闭全部")
        
        # 连接菜单项信号
        close_current_action.triggered.connect(lambda: self.close_current_tab(index))
        close_others_action.triggered.connect(lambda: self.close_other_tabs(index))
        close_all_action.triggered.connect(self.close_all_tabs)
        
        # 显示菜单
        menu.exec_(self.tab_widget.mapToGlobal(pos))
    
    def close_current_tab(self, index):
        """关闭当前标签页"""
        self.close_tab(index, from_close_button=False)
    
    def close_other_tabs(self, current_index):
        """关闭其他标签页"""
        # 获取所有标签页索引
        tab_count = self.tab_widget.count()
        if tab_count <= 1:
            return
            
        # 从后往前关闭标签页（避免索引变化问题）
        for i in range(tab_count - 1, -1, -1):
            if i != current_index:
                self.close_tab(i, from_close_button=False)
    
    def close_all_tabs(self):
        """关闭全部标签页"""
        # 从后往前关闭所有标签页
        tab_count = self.tab_widget.count()
        for i in range(tab_count - 1, -1, -1):
            self.close_tab(i, from_close_button=False)
    
    def tab_changed(self, index):
        """标签页切换事件"""
        if index == -1:
            self.current_tab_id = None
            return
        
        widget = self.tab_widget.widget(index)
        
        # 查找对应的标签页ID
        for tab_id, tab_data in self.tabs.items():
            if tab_data['widget'] == widget:
                self.current_tab_id = tab_id
                break
    
    def set_tab_modified(self, tab_id, modified):
        """设置标签页修改状态"""
        if tab_id in self.tabs:
            self.tabs[tab_id]['modified'] = modified
            
            # 更新标签页标题（添加*号表示修改）
            tab_name = self.tabs[tab_id]['tab_name']
            if modified:
                tab_name = f"*{tab_name}"
            
            # 查找标签页索引
            for i in range(self.tab_widget.count()):
                if self.tab_widget.widget(i) == self.tabs[tab_id]['widget']:
                    self.tab_widget.setTabText(i, tab_name)
                    break
    
    def case_saved(self, tab_id, case_data):
        """用例保存回调"""
        if tab_id in self.tabs:
            # 更新标签页数据
            self.tabs[tab_id]['data'] = case_data
            
            # 更新标签页名称
            tab_name = case_data.get('name', '新增用例')
            self.tabs[tab_id]['tab_name'] = tab_name
            
            # 更新标签页标题
            for i in range(self.tab_widget.count()):
                if self.tab_widget.widget(i) == self.tabs[tab_id]['widget']:
                    self.tab_widget.setTabText(i, tab_name)
                    break
            
            # 发出保存信号，让外部处理实际的保存逻辑
            self.saved.emit(case_data)