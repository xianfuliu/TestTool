"""
认证页面 - 集成登录和注册功能
"""
import sys
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QStackedWidget, QFrame, QMessageBox, QCheckBox)
from PyQt5.QtGui import QFont, QPixmap, QIcon
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtCore import QThread, pyqtSignal

from src.core.services.user_service import UserService
from src.core.services.email_service import EmailService
from src.core.models.email_config_model import EmailConfig
from src.utils.resource_utils import resource_path


class EmailWorker(QThread):
    """邮件发送工作线程"""
    finished = pyqtSignal(bool, str)
    
    def __init__(self, email_service, email, code):
        super().__init__()
        self.email_service = email_service
        self.email = email
        self.code = code
    
    def run(self):
        try:
            # 这里需要根据您的邮件服务实现发送验证码邮件
            # 暂时使用模拟发送
            import time
            time.sleep(2)  # 模拟发送延迟
            
            # 实际发送邮件逻辑需要根据您的邮件服务实现
            # 这里只是示例
            success = True
            message = "验证码发送成功" if success else "验证码发送失败"
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, f"发送失败: {str(e)}")


class AuthPage(QWidget):
    """认证页面"""
    
    login_success = pyqtSignal(object)  # 登录成功信号，传递用户信息
    
    def __init__(self):
        super().__init__()
        self.user_service = UserService()
        self.email_service = None
        self.current_email = ""
        self.verification_code = ""
        self.countdown_timer = QTimer()
        self.countdown_seconds = 60
        
        self.init_ui()
        self.init_connections()
        self.load_saved_credentials()  # 加载保存的凭据
    
    def init_ui(self):
        """初始化UI - 全屏展示，登录注册在右侧"""
        self.setWindowTitle("用户认证")
        
        # 设置全屏显示
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        self.setGeometry(screen_rect)
        
        # 主布局 - 水平分割：左侧品牌区 + 右侧认证区
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧品牌区域
        self.create_brand_section(main_layout)
        
        # 右侧认证区域
        self.create_auth_section(main_layout)
        
        self.setLayout(main_layout)
        
        # 存储认证区域widget引用，用于自适应调整
        self.auth_widget = main_layout.itemAt(1).widget()
        
        # 添加窗口大小变化事件处理
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.adjust_auth_section)
        
        # 设置样式
        self.setStyleSheet("""
            QWidget {
                font-family: "Microsoft YaHei", Arial, sans-serif;
                background-color: #ffffff;
            }
            QLineEdit {
                padding: 12px;
                border: 2px solid #e9ecef;
                border-radius: 6px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
            QPushButton {
                padding: 12px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                background-color: #3498db;
                color: white;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
    
    def create_brand_section(self, main_layout):
        """创建左侧品牌区域"""
        brand_widget = QWidget()
        brand_widget.setStyleSheet("""
            QWidget {
                background-color: #34495e;
            }
        """)
        
        brand_layout = QVBoxLayout()
        brand_layout.setContentsMargins(80, 100, 80, 100)
        brand_layout.setSpacing(30)
        brand_layout.setAlignment(Qt.AlignCenter)
        
        # 应用图标
        try:
            icon_path = resource_path("src/resources/icons/app_icon.png")
            if os.path.exists(icon_path):
                pixmap = QPixmap(icon_path)
                pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label = QLabel()
                icon_label.setPixmap(pixmap)
                icon_label.setAlignment(Qt.AlignCenter)
                icon_label.setStyleSheet("padding: 15px; background: transparent;")
                brand_layout.addWidget(icon_label)
        except Exception:
            # 如果没有图标，创建占位图标
            icon_label = QLabel("⚡")
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setFont(QFont("Microsoft YaHei", 64, QFont.Bold))
            icon_label.setStyleSheet("color: #2c3e50; padding: 20px; background: transparent;")
            brand_layout.addWidget(icon_label)
        
        # 应用标题
        title_label = QLabel("测试工具平台")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 32, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff; margin: 0; padding: 0; letter-spacing: 2px; background: transparent;")
        brand_layout.addWidget(title_label)
        
        brand_widget.setLayout(brand_layout)
        
        # 左侧区域占屏幕宽度的70%
        main_layout.addWidget(brand_widget, 7)
    
    def create_auth_section(self, main_layout):
        """创建右侧认证区域"""
        auth_widget = QWidget()
        auth_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
            }
        """)
        
        auth_layout = QVBoxLayout()
        auth_layout.setContentsMargins(80, 100, 80, 100)
        auth_layout.setSpacing(30)
        
        # 认证区域标题
        auth_title = QLabel("用户认证")
        auth_title.setAlignment(Qt.AlignCenter)
        auth_title.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
        auth_title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        auth_layout.addWidget(auth_title)
        
        # 堆叠窗口 - 登录和注册页面
        self.stacked_widget = QStackedWidget()
        
        # 创建登录页面
        self.login_widget = self.create_login_widget()
        
        # 创建注册页面
        self.register_widget = self.create_register_widget()
        
        self.stacked_widget.addWidget(self.login_widget)
        self.stacked_widget.addWidget(self.register_widget)
        
        # 切换按钮
        switch_layout = QHBoxLayout()
        switch_layout.addStretch()
        
        self.switch_to_register_btn = QPushButton("没有账号？立即注册")
        self.switch_to_register_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #3498db;
                text-decoration: underline;
                font-size: 12px;
                padding: 5px;
            }
            QPushButton:hover {
                color: #2980b9;
            }
        """)
        
        self.switch_to_login_btn = QPushButton("已有账号？立即登录")
        self.switch_to_login_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #3498db;
                text-decoration: underline;
                font-size: 12px;
                padding: 5px;
            }
            QPushButton:hover {
                color: #2980b9;
            }
        """)
        self.switch_to_login_btn.hide()
        
        switch_layout.addWidget(self.switch_to_register_btn)
        switch_layout.addWidget(self.switch_to_login_btn)
        switch_layout.addStretch()
        
        # 添加到认证布局
        auth_layout.addWidget(self.stacked_widget)
        auth_layout.addLayout(switch_layout)
        
        auth_widget.setLayout(auth_layout)
        
        # 右侧区域占屏幕宽度的30%
        main_layout.addWidget(auth_widget, 3)
    
    def create_login_widget(self):
        """创建登录页面 - 自适应高度，窗口足够大时不显示滚动条"""
        # 创建内容widget
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #ffffff;")
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)  # 移除滚动条边距
        
        # 用户名输入
        username_label = QLabel("用户名:")
        username_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        
        # 密码输入
        password_label = QLabel("密码:")
        password_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        
        # 记住我
        self.remember_me = QCheckBox("记住我")
        self.remember_me.setStyleSheet("color: #2c3e50;")
        
        # 登录按钮
        self.login_btn = QPushButton("登录")
        self.login_btn.setMinimumHeight(45)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        
        layout.addWidget(username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.remember_me)
        layout.addWidget(self.login_btn)
        layout.addStretch()
        
        return content_widget
    
    def create_register_widget(self):
        """创建注册页面 - 自适应高度，窗口足够大时不显示滚动条"""
        # 创建内容widget
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #ffffff;")
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)  # 移除滚动条边距
        
        # 用户名输入
        username_label = QLabel("用户名:")
        username_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.reg_username_input = QLineEdit()
        self.reg_username_input.setPlaceholderText("请输入用户名（4-20位字母数字）")
        
        # 密码输入
        password_label = QLabel("密码:")
        password_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.reg_password_input = QLineEdit()
        self.reg_password_input.setPlaceholderText("请输入密码（6-20位）")
        self.reg_password_input.setEchoMode(QLineEdit.Password)
        
        # 确认密码
        confirm_password_label = QLabel("确认密码:")
        confirm_password_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.reg_confirm_password_input = QLineEdit()
        self.reg_confirm_password_input.setPlaceholderText("请再次输入密码")
        self.reg_confirm_password_input.setEchoMode(QLineEdit.Password)
        
        # 邮箱输入
        email_label = QLabel("邮箱:")
        email_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("请输入邮箱地址")
        
        # 验证码区域
        code_label = QLabel("验证码:")
        code_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        code_layout = QHBoxLayout()
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("请输入验证码")
        self.send_code_btn = QPushButton("发送验证码")
        self.send_code_btn.setMinimumHeight(40)
        
        code_layout.addWidget(self.code_input)
        code_layout.addWidget(self.send_code_btn)
        
        # 真实姓名
        real_name_label = QLabel("真实姓名:")
        real_name_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.real_name_input = QLineEdit()
        self.real_name_input.setPlaceholderText("请输入真实姓名（可选）")
        
        # 业务线
        business_line_label = QLabel("业务线:")
        business_line_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.business_line_input = QLineEdit()
        self.business_line_input.setPlaceholderText("请输入业务线（可选）")
        
        # 注册按钮
        self.register_btn = QPushButton("注册")
        self.register_btn.setMinimumHeight(45)
        self.register_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        
        layout.addWidget(username_label)
        layout.addWidget(self.reg_username_input)
        layout.addWidget(password_label)
        layout.addWidget(self.reg_password_input)
        layout.addWidget(confirm_password_label)
        layout.addWidget(self.reg_confirm_password_input)
        layout.addWidget(email_label)
        layout.addWidget(self.email_input)
        layout.addWidget(code_label)
        layout.addLayout(code_layout)
        layout.addWidget(real_name_label)
        layout.addWidget(self.real_name_input)
        layout.addWidget(business_line_label)
        layout.addWidget(self.business_line_input)
        layout.addWidget(self.register_btn)
        layout.addStretch()
        
        return content_widget
    
    def init_connections(self):
        """初始化信号连接"""
        # 页面切换
        self.switch_to_register_btn.clicked.connect(self.show_register_page)
        self.switch_to_login_btn.clicked.connect(self.show_login_page)
        
        # 登录功能
        self.login_btn.clicked.connect(self.handle_login)
        
        # 注册功能
        self.send_code_btn.clicked.connect(self.handle_send_code)
        self.register_btn.clicked.connect(self.handle_register)
        
        # 倒计时定时器
        self.countdown_timer.timeout.connect(self.update_countdown)
    
    def show_register_page(self):
        """显示注册页面"""
        self.stacked_widget.setCurrentIndex(1)
        self.switch_to_register_btn.hide()
        self.switch_to_login_btn.show()
        
        # 确保注册页面滚动到顶部
        if hasattr(self.register_widget, 'verticalScrollBar'):
            self.register_widget.verticalScrollBar().setValue(0)
    
    def show_login_page(self):
        """显示登录页面"""
        self.stacked_widget.setCurrentIndex(0)
        self.switch_to_register_btn.show()
        self.switch_to_login_btn.hide()
        
        # 确保登录页面滚动到顶部
        if hasattr(self.login_widget, 'verticalScrollBar'):
            self.login_widget.verticalScrollBar().setValue(0)
    
    def handle_login(self):
        """处理登录"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "输入错误", "请输入用户名和密码")
            return
        
        # 禁用登录按钮
        self.login_btn.setEnabled(False)
        self.login_btn.setText("登录中...")
        
        # 执行登录
        result = self.user_service.authenticate_user(username, password)
        
        if result:
            # 保存记住密码设置
            self.save_credentials(username, password)
            # 直接发送登录成功信号，Toast提示将在主窗口显示
            self.login_success.emit(result['user'])
        else:
            QMessageBox.warning(self, "登录失败", "用户名或密码错误")
            self.login_btn.setEnabled(True)
            self.login_btn.setText("登录")
    
    def handle_send_code(self):
        """处理发送验证码"""
        email = self.email_input.text().strip()
        
        if not email:
            QMessageBox.warning(self, "输入错误", "请输入邮箱地址")
            return
        
        # 验证邮箱格式
        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "输入错误", "请输入有效的邮箱地址")
            return
        
        # 检查邮箱是否已注册
        if self.user_service.get_user_by_email(email):
            QMessageBox.warning(self, "注册错误", "该邮箱已被注册")
            return
        
        # 生成验证码
        code = self.user_service.generate_verification_code()
        self.verification_code = code
        self.current_email = email
        
        # 保存验证码到数据库
        if not self.user_service.save_verification_code(email, code):
            QMessageBox.warning(self, "发送失败", "验证码保存失败，请重试")
            return
        
        # 发送邮件（异步）
        self.send_verification_email(email, code)
        
        # 开始倒计时
        self.start_countdown()
    
    def send_verification_email(self, email, code):
        """发送验证码邮件"""
        # 这里需要根据您的邮件配置发送邮件
        # 暂时使用模拟发送
        QMessageBox.information(self, "发送成功", f"验证码已发送到 {email}\n验证码: {code}")
        
        # 实际实现应该使用您的邮件服务
        # 示例代码：
        # if self.email_service:
        #     success = self.email_service.send_verification_email(email, code)
        #     if not success:
        #         QMessageBox.warning(self, "发送失败", "验证码发送失败，请检查邮箱配置")
    
    def start_countdown(self):
        """开始倒计时"""
        self.send_code_btn.setEnabled(False)
        self.countdown_seconds = 60
        self.update_countdown_text()
        self.countdown_timer.start(1000)  # 每秒触发
    
    def update_countdown(self):
        """更新倒计时"""
        self.countdown_seconds -= 1
        self.update_countdown_text()
        
        if self.countdown_seconds <= 0:
            self.countdown_timer.stop()
            self.send_code_btn.setEnabled(True)
            self.send_code_btn.setText("发送验证码")
    
    def update_countdown_text(self):
        """更新倒计时文本"""
        self.send_code_btn.setText(f"重新发送({self.countdown_seconds}s)")
    
    def handle_register(self):
        """处理注册"""
        # 获取输入数据
        username = self.reg_username_input.text().strip()
        password = self.reg_password_input.text().strip()
        confirm_password = self.reg_confirm_password_input.text().strip()
        email = self.email_input.text().strip()
        code = self.code_input.text().strip()
        real_name = self.real_name_input.text().strip()
        business_line = self.business_line_input.text().strip()
        
        # 验证输入
        if not all([username, password, confirm_password, email, code]):
            QMessageBox.warning(self, "输入错误", "请填写所有必填字段")
            return
        
        if len(username) < 4 or len(username) > 20:
            QMessageBox.warning(self, "输入错误", "用户名长度应为4-20位")
            return
        
        if len(password) < 6 or len(password) > 20:
            QMessageBox.warning(self, "输入错误", "密码长度应为6-20位")
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, "输入错误", "两次输入的密码不一致")
            return
        
        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "输入错误", "请输入有效的邮箱地址")
            return
        
        # 检查admin用户是否存在
        if not self.user_service.check_admin_user_exists():
            QMessageBox.warning(self, "注册失败", "请联系管理员添加admin用户")
            return
        
        # 禁用注册按钮
        self.register_btn.setEnabled(False)
        self.register_btn.setText("注册中...")
        
        # 执行注册
        success, message = self.user_service.register_user(
            username=username,
            password=password,
            email=email,
            verification_code=code,
            real_name=real_name,
            business_line=business_line
        )
        
        if success:
            QMessageBox.information(self, "注册成功", message)
            # 注册成功后切换到登录页面
            self.show_login_page()
            # 清空注册表单
            self.clear_register_form()
        else:
            QMessageBox.warning(self, "注册失败", message)
        
        # 重新启用注册按钮
        self.register_btn.setEnabled(True)
        self.register_btn.setText("注册")
    
    def clear_register_form(self):
        """清空注册表单"""
        self.reg_username_input.clear()
        self.reg_password_input.clear()
        self.reg_confirm_password_input.clear()
        self.email_input.clear()
        self.code_input.clear()
        self.real_name_input.clear()
        self.business_line_input.clear()
    
    def save_credentials(self, username, password):
        """保存用户名和密码到本地存储"""
        try:
            import json
            import os
            from src.utils.resource_utils import resource_path
            
            # 创建配置目录
            config_dir = resource_path("config")
            os.makedirs(config_dir, exist_ok=True)
            
            # 保存凭据文件路径
            credentials_file = os.path.join(config_dir, "credentials.json")
            
            # 检查是否勾选了记住我
            if self.remember_me.isChecked():
                # 保存用户名和密码（密码需要加密存储）
                credentials_data = {
                    "username": username,
                    "password": password,  # 实际应用中应该加密存储
                    "remember_me": True
                }
            else:
                # 如果不记住密码，只保存用户名
                credentials_data = {
                    "username": username,
                    "remember_me": False
                }
            
            # 写入文件
            with open(credentials_file, 'w', encoding='utf-8') as f:
                json.dump(credentials_data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"保存凭据失败: {e}")
    
    def load_saved_credentials(self):
        """加载保存的用户名和密码"""
        try:
            import json
            import os
            from src.utils.resource_utils import resource_path
            
            # 凭据文件路径
            credentials_file = os.path.join(resource_path("config"), "credentials.json")
            
            if os.path.exists(credentials_file):
                with open(credentials_file, 'r', encoding='utf-8') as f:
                    credentials_data = json.load(f)
                
                # 设置用户名
                if "username" in credentials_data:
                    self.username_input.setText(credentials_data["username"])
                
                # 设置密码和记住我状态
                if credentials_data.get("remember_me", False) and "password" in credentials_data:
                    self.password_input.setText(credentials_data["password"])
                    self.remember_me.setChecked(True)
                else:
                    self.remember_me.setChecked(False)
                    
        except Exception as e:
            print(f"加载保存的凭据失败: {e}")
    
    def clear_saved_credentials(self):
        """清除保存的凭据"""
        try:
            import os
            from src.utils.resource_utils import resource_path
            
            # 凭据文件路径
            credentials_file = os.path.join(resource_path("config"), "credentials.json")
            
            if os.path.exists(credentials_file):
                os.remove(credentials_file)
                
        except Exception as e:
            print(f"清除保存的凭据失败: {e}")
    
    def set_email_service(self, email_service):
        """设置邮件服务"""
        self.email_service = email_service
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 停止定时器
        if self.countdown_timer.isActive():
            self.countdown_timer.stop()
        if hasattr(self, 'resize_timer') and self.resize_timer.isActive():
            self.resize_timer.stop()
        event.accept()
    
    def resizeEvent(self, event):
        """窗口大小变化事件处理"""
        super().resizeEvent(event)
        # 使用定时器延迟调整，避免频繁调整
        if hasattr(self, 'resize_timer'):
            self.resize_timer.start(100)
    
    def adjust_auth_section(self):
        """调整认证区域大小"""
        if hasattr(self, 'auth_widget'):
            # 根据窗口高度动态调整认证区域的高度
            window_height = self.height()
            # 设置最小高度为400，最大高度为窗口高度减去100边距
            auth_height = max(400, window_height - 100)
            self.auth_widget.setMinimumHeight(auth_height)
            self.auth_widget.setMaximumHeight(auth_height)