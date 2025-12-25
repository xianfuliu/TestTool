"""
全局邮箱配置对话框
"""
import os
import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QSpinBox, QCheckBox, QPushButton, 
                             QDialogButtonBox, QGroupBox, QLabel, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from src.core.models.email_config_model import EmailConfig
from src.core.services.email_config_service import EmailConfigService
from src.ui.widgets.toast_tips import Toast


class GlobalEmailConfigDialog(QDialog):
    """全局邮箱配置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.email_config_service = EmailConfigService()
        self.init_ui()
        self.load_email_config()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("全局邮箱配置")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 邮箱配置组
        email_group = QGroupBox("SMTP服务器配置")
        email_layout = QVBoxLayout(email_group)
        
        # SMTP服务器配置表单
        smtp_layout = QFormLayout()
        smtp_layout.setLabelAlignment(Qt.AlignLeft)
        smtp_layout.setFormAlignment(Qt.AlignLeft)
        
        self.smtp_server_edit = QLineEdit()
        self.smtp_server_edit.setPlaceholderText("例如：smtp.qq.com")
        smtp_layout.addRow("SMTP服务器:", self.smtp_server_edit)
        
        self.smtp_port_edit = QSpinBox()
        self.smtp_port_edit.setRange(1, 65535)
        self.smtp_port_edit.setValue(587)
        self.smtp_port_edit.setFixedWidth(100)
        smtp_layout.addRow("SMTP端口:", self.smtp_port_edit)
        
        self.smtp_ssl_check = QCheckBox("使用SSL/TLS")
        self.smtp_ssl_check.setChecked(True)
        smtp_layout.addRow("安全连接:", self.smtp_ssl_check)
        
        self.sender_email_edit = QLineEdit()
        self.sender_email_edit.setPlaceholderText("发件人邮箱地址")
        smtp_layout.addRow("发件人邮箱:", self.sender_email_edit)
        
        self.sender_password_edit = QLineEdit()
        self.sender_password_edit.setPlaceholderText("发件人邮箱密码或授权码")
        self.sender_password_edit.setEchoMode(QLineEdit.Password)
        smtp_layout.addRow("邮箱密码:", self.sender_password_edit)
        
        self.sender_name_edit = QLineEdit()
        self.sender_name_edit.setPlaceholderText("发件人名称（可选）")
        smtp_layout.addRow("发件人名称:", self.sender_name_edit)
        
        email_layout.addLayout(smtp_layout)
        
        # 测试连接按钮
        test_button_layout = QHBoxLayout()
        self.test_email_connection_btn = QPushButton("测试发送邮件")
        self.test_email_connection_btn.setFixedWidth(120)
        self.test_email_connection_btn.clicked.connect(self.test_email_connection)
        test_button_layout.addWidget(self.test_email_connection_btn)
        test_button_layout.addStretch()
        email_layout.addLayout(test_button_layout)
        
        # 说明文本
        info_label = QLabel("注意：此配置将作为系统全局邮箱配置，定时调度任务将使用此配置发送邮件。")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 12px; margin-top: 10px;")
        email_layout.addWidget(info_label)
        
        layout.addWidget(email_group)
        layout.addStretch()
        
        # 按钮区域
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        
        # 修改按钮文本为中文
        button_box.button(QDialogButtonBox.Ok).setText("保存")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        
        layout.addWidget(button_box)
        
    def load_email_config(self):
        """加载邮箱配置"""
        try:
            config = self.email_config_service.get_email_config()
            if config:
                self.smtp_server_edit.setText(config.smtp_server)
                self.smtp_port_edit.setValue(config.smtp_port)
                self.smtp_ssl_check.setChecked(config.use_tls)
                self.sender_email_edit.setText(config.sender_email)
                self.sender_password_edit.setText(config.smtp_password)
                self.sender_name_edit.setText(config.sender_name)
        except Exception as e:
            print(f"加载邮箱配置失败: {e}")
            
    def get_email_config(self):
        """获取邮箱配置对象"""
        return EmailConfig(
            smtp_server=self.smtp_server_edit.text().strip(),
            smtp_port=self.smtp_port_edit.value(),
            smtp_username=self.sender_email_edit.text().strip(),
            smtp_password=self.sender_password_edit.text().strip(),
            use_tls=self.smtp_ssl_check.isChecked(),
            sender_name=self.sender_name_edit.text().strip(),
            sender_email=self.sender_email_edit.text().strip()
        )
        
    def validate_and_accept(self):
        """验证并保存配置"""
        try:
            # 验证必填字段
            if not self.smtp_server_edit.text().strip():
                Toast.warning(self, "验证失败", "请输入SMTP服务器地址")
                return
                
            if not self.sender_email_edit.text().strip():
                Toast.warning(self, "验证失败", "请输入发件人邮箱地址")
                return
                
            if not self.sender_password_edit.text().strip():
                Toast.warning(self, "验证失败", "请输入邮箱密码或授权码")
                return
                
            # 保存配置
            config = self.get_email_config()
            success = self.email_config_service.save_email_config(config)
            
            if success:
                Toast.success(self, "保存成功", "邮箱配置已保存")
                self.accept()
            else:
                Toast.critical(self, "保存失败", "邮箱配置保存失败")
                
        except Exception as e:
            Toast.critical(self, "错误", f"保存邮箱配置时发生错误：{str(e)}")
            
    def test_email_connection(self):
        """测试邮件连接配置"""
        try:
            # 检查是否填写了必要的配置
            if not self.smtp_server_edit.text().strip():
                Toast.warning(self, "警告", "请输入SMTP服务器地址")
                return
            
            if not self.sender_email_edit.text().strip():
                Toast.warning(self, "警告", "请输入发件人邮箱地址")
                return
            
            if not self.sender_password_edit.text().strip():
                Toast.warning(self, "警告", "请输入邮箱密码或授权码")
                return
            
            # 创建邮件配置对象
            email_config = self.get_email_config()
            
            # 测试连接
            success = self.email_config_service.test_email_connection(email_config)
            
            if success:
                Toast.information(self, "测试成功", "邮件连接测试成功！")
            else:
                Toast.critical(self, "测试失败", "邮件连接测试失败，请检查配置信息")
                
        except Exception as e:
            Toast.critical(self, "错误", f"测试邮件连接时发生错误：{str(e)}")