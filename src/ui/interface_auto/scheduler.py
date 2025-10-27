import os
import json
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
                             QTabWidget, QGroupBox, QFormLayout, QComboBox,
                             QHeaderView, QInputDialog, QCheckBox, QSpinBox,
                             QListWidget, QListWidgetItem, QSplitter, QToolBar,
                             QAction, QToolButton, QMenu, QApplication, QDateTimeEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QDateTime
from PyQt5.QtGui import QIcon, QFont, QColor
from src.core.services.scheduler_service import SchedulerService
from src.core.services.test_case_service import TestCaseService
from src.core.models.interface_models import TestScheduler
from src.utils.interface_utils.cron_parser import CronParser


class SchedulerDialog(QDialog):
    """调度编辑对话框"""

    def __init__(self, parent=None, scheduler_data=None):
        super().__init__(parent)
        self.scheduler_data = scheduler_data or {}
        self.is_edit = bool(scheduler_data)
        self.test_case_service = TestCaseService()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑调度" if self.is_edit else "新增调度")
        self.setMinimumSize(700, 600)

        layout = QVBoxLayout(self)

        # 创建Tab页
        tab_widget = QTabWidget()

        # 基本信息Tab
        basic_tab = QWidget()
        self.setup_basic_tab(basic_tab)

        # 调度配置Tab
        schedule_tab = QWidget()
        self.setup_schedule_tab(schedule_tab)

        # 通知配置Tab
        notify_tab = QWidget()
        self.setup_notify_tab(notify_tab)

        tab_widget.addTab(basic_tab, "基本信息")
        tab_widget.addTab(schedule_tab, "调度配置")
        tab_widget.addTab(notify_tab, "通知配置")

        # 按钮布局
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(tab_widget)
        layout.addWidget(button_box)

        # 加载数据
        if self.is_edit:
            self.load_scheduler_data()

    def setup_basic_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 基本信息表单
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入调度名称")

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setPlaceholderText("请输入调度描述")

        self.enabled_check = QCheckBox("启用调度")
        self.enabled_check.setChecked(True)

        form_layout.addRow("调度名称:", self.name_edit)
        form_layout.addRow("调度描述:", self.desc_edit)
        form_layout.addRow("", self.enabled_check)

        # 测试用例选择
        case_group = QGroupBox("选择测试用例")
        case_layout = QVBoxLayout(case_group)

        # 用例列表
        self.case_list = QListWidget()
        self.case_list.setSelectionMode(QListWidget.MultiSelection)

        # 加载测试用例
        self.load_test_cases()

        case_layout.addWidget(QLabel("可多选测试用例:"))
        case_layout.addWidget(self.case_list)

        layout.addLayout(form_layout)
        layout.addWidget(case_group)

    def setup_schedule_tab(self, parent):
        layout = QVBoxLayout(parent)

        # Cron表达式配置
        cron_group = QGroupBox("Cron表达式配置")
        cron_layout = QVBoxLayout(cron_group)

        # Cron表达式输入
        cron_input_layout = QHBoxLayout()
        self.cron_edit = QLineEdit()
        self.cron_edit.setPlaceholderText("例如: 0 0 12 * * ? (每天12点执行)")
        cron_input_layout.addWidget(QLabel("Cron表达式:"))
        cron_input_layout.addWidget(self.cron_edit)

        # Cron表达式帮助
        help_btn = QPushButton("Cron帮助")
        help_btn.clicked.connect(self.show_cron_help)
        cron_input_layout.addWidget(help_btn)

        # 常用Cron表达式
        common_cron_layout = QHBoxLayout()
        common_cron_layout.addWidget(QLabel("常用表达式:"))

        common_crons = {
            "每分钟": "* * * * *",
            "每小时": "0 * * * *",
            "每天12点": "0 0 12 * * ?",
            "每周一9点": "0 0 9 ? * MON",
            "每月1号": "0 0 0 1 * ?"
        }

        self.common_cron_combo = QComboBox()
        for name, expr in common_crons.items():
            self.common_cron_combo.addItem(name, expr)
        self.common_cron_combo.currentIndexChanged.connect(self.on_common_cron_selected)
        common_cron_layout.addWidget(self.common_cron_combo)
        common_cron_layout.addStretch()

        # 下次执行时间预览
        self.next_run_label = QLabel("下次执行时间: 未计算")
        self.next_run_label.setStyleSheet("color: #666; font-style: italic;")

        # 计算下次执行时间按钮
        calc_btn = QPushButton("计算下次执行时间")
        calc_btn.clicked.connect(self.calculate_next_run)

        cron_layout.addLayout(cron_input_layout)
        cron_layout.addLayout(common_cron_layout)
        cron_layout.addWidget(self.next_run_label)
        cron_layout.addWidget(calc_btn)

        # 简单调度配置
        simple_group = QGroupBox("简单调度配置")
        simple_layout = QFormLayout(simple_group)

        self.simple_type_combo = QComboBox()
        self.simple_type_combo.addItems(["每天", "每周", "每月"])
        self.simple_type_combo.currentIndexChanged.connect(self.on_simple_type_changed)

        self.simple_time_edit = QDateTimeEdit()
        self.simple_time_edit.setDisplayFormat("HH:mm:ss")
        self.simple_time_edit.setTime(QDateTime.currentDateTime().time())

        self.simple_day_combo = QComboBox()
        self.simple_day_combo.addItems(["周一", "周二", "周三", "周四", "周五", "周六", "周日"])

        self.simple_date_spin = QSpinBox()
        self.simple_date_spin.setRange(1, 31)
        self.simple_date_spin.setValue(1)

        simple_layout.addRow("执行类型:", self.simple_type_combo)
        simple_layout.addRow("执行时间:", self.simple_time_edit)
        simple_layout.addRow("执行日期:", self.simple_day_combo)

        # 应用简单配置按钮
        apply_simple_btn = QPushButton("应用简单配置")
        apply_simple_btn.clicked.connect(self.apply_simple_config)

        simple_layout.addRow("", apply_simple_btn)

        layout.addWidget(cron_group)
        layout.addWidget(simple_group)

    def setup_notify_tab(self, parent):
        layout = QVBoxLayout(parent)

        # 邮件通知配置
        email_group = QGroupBox("邮件通知")
        email_layout = QVBoxLayout(email_group)

        self.email_enabled_check = QCheckBox("启用邮件通知")
        email_layout.addWidget(self.email_enabled_check)

        # 收件人列表
        email_recipient_layout = QHBoxLayout()
        email_recipient_layout.addWidget(QLabel("收件人:"))
        self.email_recipient_edit = QLineEdit()
        self.email_recipient_edit.setPlaceholderText("多个邮箱用逗号分隔")
        email_recipient_layout.addWidget(self.email_recipient_edit)

        email_layout.addLayout(email_recipient_layout)

        # 微信通知配置
        wechat_group = QGroupBox("企业微信通知")
        wechat_layout = QVBoxLayout(wechat_group)

        self.wechat_enabled_check = QCheckBox("启用企业微信通知")
        wechat_layout.addWidget(self.wechat_enabled_check)

        # Webhook配置
        wechat_webhook_layout = QFormLayout()
        self.wechat_webhook_edit = QLineEdit()
        self.wechat_webhook_edit.setPlaceholderText("输入企业微信机器人Webhook URL")
        wechat_webhook_layout.addRow("Webhook URL:", self.wechat_webhook_edit)

        wechat_layout.addLayout(wechat_webhook_layout)

        layout.addWidget(email_group)
        layout.addWidget(wechat_group)
        layout.addStretch()

    def load_test_cases(self):
        """加载测试用例列表"""
        try:
            cases = self.test_case_service.get_all_cases()
            for case in cases:
                item = QListWidgetItem(case['name'])
                item.setData(Qt.UserRole, case['id'])
                self.case_list.addItem(item)
        except Exception as e:
            print(f"加载测试用例失败: {e}")

    def load_scheduler_data(self):
        """加载调度数据到表单"""
        if not self.scheduler_data:
            return

        # 基本信息
        self.name_edit.setText(self.scheduler_data.get('name', ''))
        self.desc_edit.setText(self.scheduler_data.get('description', ''))
        self.enabled_check.setChecked(self.scheduler_data.get('enabled', True))

        # 测试用例选择
        case_ids = self.scheduler_data.get('case_ids', [])
        for i in range(self.case_list.count()):
            item = self.case_list.item(i)
            if item.data(Qt.UserRole) in case_ids:
                item.setSelected(True)

        # Cron表达式
        self.cron_edit.setText(self.scheduler_data.get('cron_expression', ''))

        # 通知配置
        notify_emails = self.scheduler_data.get('notify_emails', [])
        self.email_recipient_edit.setText(','.join(notify_emails))

        notify_wechat = self.scheduler_data.get('notify_wechat', {})
        self.wechat_webhook_edit.setText(notify_wechat.get('webhook', ''))

    def get_data(self):
        """获取表单数据"""
        # 基本信息
        data = {
            'name': self.name_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip(),
            'enabled': self.enabled_check.isChecked(),
            'cron_expression': self.cron_edit.text().strip()
        }

        # 测试用例ID列表
        case_ids = []
        for item in self.case_list.selectedItems():
            case_ids.append(item.data(Qt.UserRole))
        data['case_ids'] = case_ids

        # 通知配置
        email_recipients = self.email_recipient_edit.text().strip()
        if email_recipients:
            data['notify_emails'] = [email.strip() for email in email_recipients.split(',')]
        else:
            data['notify_emails'] = []

        wechat_webhook = self.wechat_webhook_edit.text().strip()
        if wechat_webhook:
            data['notify_wechat'] = {
                'webhook': wechat_webhook,
                'enabled': True
            }
        else:
            data['notify_wechat'] = {}

        return data

    def on_common_cron_selected(self, index):
        """常用Cron表达式选择"""
        if index > 0:
            cron_expr = self.common_cron_combo.currentData()
            self.cron_edit.setText(cron_expr)
            self.calculate_next_run()

    def on_simple_type_changed(self, index):
        """简单调度类型变化"""
        # 显示/隐藏相关控件
        pass

    def apply_simple_config(self):
        """应用简单配置"""
        schedule_type = self.simple_type_combo.currentText()
        time_str = self.simple_time_edit.time().toString("HH:mm:ss")

        if schedule_type == "每天":
            cron_expr = f"0 {time_str.split(':')[1]} {time_str.split(':')[0]} * * ?"
        elif schedule_type == "每周":
            day_map = {"周一": "MON", "周二": "TUE", "周三": "WED", "周四": "THU",
                       "周五": "FRI", "周六": "SAT", "周日": "SUN"}
            day = day_map.get(self.simple_day_combo.currentText(), "MON")
            cron_expr = f"0 {time_str.split(':')[1]} {time_str.split(':')[0]} ? * {day}"
        else:  # 每月
            day = self.simple_date_spin.value()
            cron_expr = f"0 {time_str.split(':')[1]} {time_str.split(':')[0]} {day} * ?"

        self.cron_edit.setText(cron_expr)
        self.calculate_next_run()

    def calculate_next_run(self):
        """计算下次执行时间"""
        cron_expr = self.cron_edit.text().strip()
        if not cron_expr:
            return

        try:
            parser = CronParser()
            next_run = parser.get_next_run(cron_expr)
            if next_run:
                self.next_run_label.setText(f"下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                self.next_run_label.setText("下次执行时间: 表达式无效")
        except Exception as e:
            self.next_run_label.setText(f"下次执行时间: 计算错误 - {str(e)}")

    def show_cron_help(self):
        """显示Cron表达式帮助"""
        help_text = """
Cron表达式格式: 
   秒 分 时 日 月 周 [年]

各字段含义:
   秒 (0-59)
   分 (0-59) 
   时 (0-23)
   日 (1-31)
   月 (1-12 或 JAN-DEC)
   周 (0-7 或 SUN-SAT, 0和7都代表周日)
   年 (可选, 1970-2099)

特殊字符:
   * : 所有值
   ? : 不指定值 (用于日和周字段)
   - : 范围 (如: 1-5)
   , : 多个值 (如: 1,3,5)
   / : 步长 (如: 0/15 表示从0开始每15分钟)
   L : 最后 (如: 月最后一天)
   W : 工作日
   # : 第几个 (如: 6#3 表示第3个周五)

示例:
   0 0 12 * * ?       每天12点
   0 0 9 ? * MON      每周一9点
   0 0 0 1 * ?        每月1号
   0 0/30 * * * ?     每30分钟
   0 0 9-17 * * MON-FRI 工作日的9点到17点每小时
        """
        QMessageBox.information(self, "Cron表达式帮助", help_text)


class SchedulerManager(QWidget):
    """调度管理页面"""
    data_changed = pyqtSignal()  # 数据变化信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.scheduler_service = SchedulerService()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_next_run_times)
        self.timer.start(60000)  # 每分钟更新一次
        self.init_ui()
        self.load_schedulers()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 工具栏
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))

        self.add_action = QAction("新增调度", self)
        self.add_action.triggered.connect(self.add_scheduler)
        self.add_action.setIcon(self.get_icon("add.png"))

        self.edit_action = QAction("编辑", self)
        self.edit_action.triggered.connect(self.edit_selected_scheduler)
        self.edit_action.setIcon(self.get_icon("edit.png"))

        self.delete_action = QAction("删除", self)
        self.delete_action.triggered.connect(self.delete_selected_scheduler)
        self.delete_action.setIcon(self.get_icon("delete.png"))

        self.run_action = QAction("立即执行", self)
        self.run_action.triggered.connect(self.run_selected_scheduler)
        self.run_action.setIcon(self.get_icon("play.png"))

        self.enable_action = QAction("启用/禁用", self)
        self.enable_action.triggered.connect(self.toggle_selected_scheduler)
        self.enable_action.setIcon(self.get_icon("toggle.png"))

        self.refresh_action = QAction("刷新", self)
        self.refresh_action.triggered.connect(self.load_schedulers)
        self.refresh_action.setIcon(self.get_icon("refresh.png"))

        toolbar.addAction(self.add_action)
        toolbar.addAction(self.edit_action)
        toolbar.addAction(self.delete_action)
        toolbar.addSeparator()
        toolbar.addAction(self.run_action)
        toolbar.addAction(self.enable_action)
        toolbar.addSeparator()
        toolbar.addAction(self.refresh_action)

        main_layout.addWidget(toolbar)

        # 调度列表表格
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(7)
        self.table_widget.setHorizontalHeaderLabels([
            "调度名称", "状态", "Cron表达式", "用例数量", "上次执行", "下次执行", "创建时间"
        ])
        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_table_context_menu)
        self.table_widget.doubleClicked.connect(self.edit_selected_scheduler)

        main_layout.addWidget(self.table_widget)

        # 状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        main_layout.addLayout(status_layout)

        self.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
            }
        """)

    def get_icon(self, icon_name):
        """获取图标"""
        try:
            icon_path = os.path.join("src", "ui", "interface_auto", "icons", icon_name)
            if os.path.exists(icon_path):
                return QIcon(icon_path)
        except:
            pass
        return QIcon()

    def load_schedulers(self):
        """加载调度列表"""
        try:
            schedulers = self.scheduler_service.get_all_schedulers()
            self.table_widget.setRowCount(len(schedulers))

            for row, scheduler in enumerate(schedulers):
                # 调度名称
                name_item = QTableWidgetItem(scheduler['name'])
                name_item.setData(Qt.UserRole, scheduler['id'])
                self.table_widget.setItem(row, 0, name_item)

                # 状态
                status_item = QTableWidgetItem("启用" if scheduler['enabled'] else "禁用")
                status_item.setForeground(QColor("green") if scheduler['enabled'] else QColor("red"))
                self.table_widget.setItem(row, 1, status_item)

                # Cron表达式
                self.table_widget.setItem(row, 2, QTableWidgetItem(scheduler['cron_expression']))

                # 用例数量
                case_ids = scheduler.get('case_ids', [])
                case_count = len(case_ids) if isinstance(case_ids, list) else 0
                self.table_widget.setItem(row, 3, QTableWidgetItem(str(case_count)))

                # 上次执行时间
                last_run = scheduler.get('last_run_at')
                last_run_text = last_run.strftime('%Y-%m-%d %H:%M:%S') if last_run else "从未执行"
                self.table_widget.setItem(row, 4, QTableWidgetItem(last_run_text))

                # 下次执行时间
                next_run = scheduler.get('next_run_at')
                next_run_text = next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else "未计算"
                next_run_item = QTableWidgetItem(next_run_text)
                if next_run and next_run < datetime.now():
                    next_run_item.setForeground(QColor("orange"))
                self.table_widget.setItem(row, 5, next_run_item)

                # 创建时间
                created_at = scheduler.get('created_at')
                created_text = created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else ""
                self.table_widget.setItem(row, 6, QTableWidgetItem(created_text))

            # 调整列宽
            self.table_widget.resizeColumnsToContents()
            self.status_label.setText(f"共 {len(schedulers)} 个调度任务")

        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"加载调度列表失败: {str(e)}")
            self.status_label.setText("加载失败")

    def update_next_run_times(self):
        """更新下次执行时间显示"""
        for row in range(self.table_widget.rowCount()):
            next_run_item = self.table_widget.item(row, 5)
            if next_run_item:
                next_run_text = next_run_item.text()
                # 这里可以重新计算下次执行时间
                # 简化处理：只是更新颜色
                pass

    def get_selected_scheduler_id(self):
        """获取选中的调度ID"""
        selected_items = self.table_widget.selectedItems()
        if selected_items:
            return selected_items[0].data(Qt.UserRole)
        return None

    def get_selected_scheduler_data(self):
        """获取选中的调度数据"""
        scheduler_id = self.get_selected_scheduler_id()
        if scheduler_id:
            return self.scheduler_service.get_scheduler_by_id(scheduler_id)
        return None

    def add_scheduler(self):
        """新增调度"""
        dialog = SchedulerDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "调度名称不能为空")
                return
            if not data['cron_expression']:
                QMessageBox.warning(self, "输入错误", "Cron表达式不能为空")
                return
            if not data['case_ids']:
                QMessageBox.warning(self, "输入错误", "请选择至少一个测试用例")
                return

            try:
                # 验证Cron表达式
                parser = CronParser()
                if not parser.validate_cron(data['cron_expression']):
                    QMessageBox.warning(self, "输入错误", "Cron表达式格式不正确")
                    return

                self.scheduler_service.create_scheduler(data)
                self.load_schedulers()
                self.data_changed.emit()
                QMessageBox.information(self, "成功", "调度创建成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建调度失败: {str(e)}")

    def edit_selected_scheduler(self):
        """编辑选中的调度"""
        scheduler_data = self.get_selected_scheduler_data()
        if not scheduler_data:
            QMessageBox.warning(self, "提示", "请先选择一个调度")
            return

        dialog = SchedulerDialog(self, scheduler_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "输入错误", "调度名称不能为空")
                return
            if not data['cron_expression']:
                QMessageBox.warning(self, "输入错误", "Cron表达式不能为空")
                return
            if not data['case_ids']:
                QMessageBox.warning(self, "输入错误", "请选择至少一个测试用例")
                return

            try:
                # 验证Cron表达式
                parser = CronParser()
                if not parser.validate_cron(data['cron_expression']):
                    QMessageBox.warning(self, "输入错误", "Cron表达式格式不正确")
                    return

                self.scheduler_service.update_scheduler(scheduler_data['id'], data)
                self.load_schedulers()
                self.data_changed.emit()
                QMessageBox.information(self, "成功", "调度更新成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新调度失败: {str(e)}")

    def delete_selected_scheduler(self):
        """删除选中的调度"""
        scheduler_data = self.get_selected_scheduler_data()
        if not scheduler_data:
            QMessageBox.warning(self, "提示", "请先选择一个调度")
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除调度 '{scheduler_data['name']}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.scheduler_service.delete_scheduler(scheduler_data['id'])
                self.load_schedulers()
                self.data_changed.emit()
                QMessageBox.information(self, "成功", "调度删除成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除调度失败: {str(e)}")

    def run_selected_scheduler(self):
        """立即执行选中的调度"""
        scheduler_data = self.get_selected_scheduler_data()
        if not scheduler_data:
            QMessageBox.warning(self, "提示", "请先选择一个调度")
            return

        try:
            # 这里调用调度执行服务
            # 简化实现，只是显示提示
            QMessageBox.information(self, "提示", f"开始执行调度: {scheduler_data['name']}")

            # 更新上次执行时间
            self.scheduler_service.update_last_run(scheduler_data['id'])
            self.load_schedulers()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行调度失败: {str(e)}")

    def toggle_selected_scheduler(self):
        """启用/禁用选中的调度"""
        scheduler_data = self.get_selected_scheduler_data()
        if not scheduler_data:
            QMessageBox.warning(self, "提示", "请先选择一个调度")
            return

        new_status = not scheduler_data['enabled']
        status_text = "启用" if new_status else "禁用"

        try:
            self.scheduler_service.update_scheduler_status(scheduler_data['id'], new_status)
            self.load_schedulers()
            self.data_changed.emit()
            QMessageBox.information(self, "成功", f"调度已{status_text}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"{status_text}调度失败: {str(e)}")

    def show_table_context_menu(self, position):
        """显示表格右键菜单"""
        item = self.table_widget.itemAt(position)
        if not item:
            return

        from PyQt5.QtWidgets import QMenu, QAction

        menu = QMenu(self)

        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(self.edit_selected_scheduler)
        menu.addAction(edit_action)

        run_action = QAction("立即执行", self)
        run_action.triggered.connect(self.run_selected_scheduler)
        menu.addAction(run_action)

        toggle_action = QAction("启用/禁用", self)
        toggle_action.triggered.connect(self.toggle_selected_scheduler)
        menu.addAction(toggle_action)

        menu.addSeparator()

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.delete_selected_scheduler)
        menu.addAction(delete_action)

        menu.exec_(self.table_widget.mapToGlobal(position))