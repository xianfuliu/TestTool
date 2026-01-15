"""
验证码邮件发送服务
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime
from typing import List

from src.core.models.email_config_model import EmailConfig


logger = logging.getLogger(__name__)


class VerificationEmailService:
    """验证码邮件发送服务"""

    def __init__(self, config: EmailConfig):
        """初始化邮件服务"""
        self.config = config

    def send_verification_code(self, recipient: str, verification_code: str) -> bool:
        """
        发送验证码邮件

        Args:
            recipient: 收件人邮箱
            verification_code: 验证码

        Returns:
            bool: 发送是否成功
        """
        try:
            # 验证配置
            if not self._validate_config():
                logger.error("邮件配置不完整")
                return False

            # 验证收件人
            if not recipient:
                logger.warning("没有收件人，跳过邮件发送")
                return False

            # 创建邮件内容
            subject = self._generate_subject()
            html_content = self._generate_html_content(verification_code)
            text_content = self._generate_text_content(verification_code)

            # 发送邮件
            return self._send_email([recipient], subject, html_content, text_content)

        except Exception as e:
            logger.error(f"发送验证码邮件失败: {str(e)}")
            return False

    def _validate_config(self) -> bool:
        """验证邮件配置"""
        required_fields = ["smtp_server", "smtp_port", "smtp_username", "sender_email"]

        for field in required_fields:
            if not getattr(self.config, field):
                logger.error(f"邮件配置缺少必要字段: {field}")
                return False

        return True

    def _generate_subject(self) -> str:
        """生成邮件主题"""
        return "【测试工具】邮箱验证码"

    def _generate_html_content(self, verification_code: str) -> str:
        """生成HTML邮件内容"""
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 20px; 
                    background-color: #f5f5f5;
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 0 auto; 
                    background-color: white; 
                    padding: 30px; 
                    border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{ 
                    text-align: center; 
                    margin-bottom: 30px; 
                    color: #333;
                }}
                .code-container {{ 
                    background-color: #f8f9fa; 
                    padding: 20px; 
                    border-radius: 5px; 
                    text-align: center; 
                    margin: 20px 0;
                    border: 2px dashed #dee2e6;
                }}
                .verification-code {{ 
                    font-size: 32px; 
                    font-weight: bold; 
                    color: #007bff; 
                    letter-spacing: 5px;
                }}
                .warning {{ 
                    background-color: #fff3cd; 
                    border: 1px solid #ffeaa7; 
                    padding: 15px; 
                    border-radius: 5px; 
                    margin: 20px 0;
                    color: #856404;
                }}
                .footer {{ 
                    margin-top: 30px; 
                    text-align: center; 
                    color: #6c757d; 
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>邮箱验证码</h1>
                    <p>您正在注册测试工具账号，请使用以下验证码完成验证</p>
                </div>
                
                <div class="code-container">
                    <div class="verification-code">{verification_code}</div>
                </div>
                
                <div class="warning">
                    <strong>重要提示：</strong>
                    <ul>
                        <li>此验证码有效期为10分钟</li>
                        <li>请勿将此验证码透露给他人</li>
                        <li>如非本人操作，请忽略此邮件</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p>此邮件由测试工具自动发送，请勿回复。</p>
                    <p>发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _generate_text_content(self, verification_code: str) -> str:
        """生成纯文本邮件内容"""
        text = f"""
邮箱验证码

您正在注册测试工具账号，请使用以下验证码完成验证：

验证码：{verification_code}

重要提示：
- 此验证码有效期为10分钟
- 请勿将此验证码透露给他人
- 如非本人操作，请忽略此邮件

此邮件由测试工具自动发送，请勿回复。
发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """

        return text

    def _send_email(
        self, recipients: List[str], subject: str, html_content: str, text_content: str
    ) -> bool:
        """发送邮件"""
        import os
        import socket

        # 保存原始getfqdn函数
        original_getfqdn = socket.getfqdn

        def patched_getfqdn(name=""):
            """修补的getfqdn函数，返回固定的localhost"""
            return "localhost"

        try:
            # 应用猴子补丁
            socket.getfqdn = patched_getfqdn

            # 创建邮件消息
            msg = MIMEMultipart("alternative")
            msg["Subject"] = str(Header(subject, "utf-8"))

            # 修复From头：使用简单的邮箱格式，避免编码问题
            msg["From"] = self.config.sender_email
            msg["To"] = ", ".join(recipients)

            # 添加文本和HTML版本
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # 方法1: 尝试使用简单的SMTP连接
            try:
                # 直接使用SMTP连接，并显式设置local_hostname参数
                server = smtplib.SMTP(
                    self.config.smtp_server,
                    self.config.smtp_port,
                    local_hostname="localhost",
                    timeout=30,
                )

                # 如果配置了TLS，启动STARTTLS
                if self.config.use_tls:
                    server.starttls()

                # 设置编码处理
                server.set_debuglevel(0)

                # 登录
                server.login(self.config.smtp_username, self.config.smtp_password)

                # 发送邮件
                server.send_message(msg)

                # 关闭连接
                server.quit()

                logger.info(f"验证码邮件发送成功: {recipients}")
                return True

            except Exception as e:
                logger.warning(f"方法1失败: {str(e)}，尝试方法2")

                # 方法2: 使用socket连接绕过主机名解析
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(30)
                sock.connect((self.config.smtp_server, self.config.smtp_port))

                # 创建SMTP对象，使用已有的socket连接
                server = smtplib.SMTP(local_hostname="localhost")
                server.sock = sock

                # 如果配置了TLS，启动STARTTLS
                if self.config.use_tls:
                    server.starttls()

                # 设置编码处理
                server.set_debuglevel(0)

                # 登录
                server.login(self.config.smtp_username, self.config.smtp_password)

                # 发送邮件
                server.send_message(msg)

                # 关闭连接
                server.quit()

                logger.info(f"验证码邮件发送成功(方法2): {recipients}")
                return True

        except Exception as e:
            logger.error(f"发送邮件失败: {str(e)}")
            return False

        finally:
            # 恢复原始getfqdn函数
            socket.getfqdn = original_getfqdn
