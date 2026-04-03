"""
邮件发送服务
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime
from typing import List, Optional

from src.core.models.email_config_model import EmailConfig


logger = logging.getLogger(__name__)


class EmailService:
    """邮件发送服务"""

    def __init__(self, config: EmailConfig):
        """初始化邮件服务"""
        self.config = config

    def send_test_report_email(
        self,
        recipients: List[str],
        report_data: dict,
        report_id: int,
        scheduler_name: str,
    ) -> bool:
        """
        发送测试报告邮件

        Args:
            recipients: 收件人列表
            report_data: 测试报告数据
            report_id: 报告ID
            scheduler_name: 调度任务名称

        Returns:
            bool: 发送是否成功
        """
        try:
            # 验证配置
            if not self._validate_config():
                logger.error("邮件配置不完整")
                return False

            # 验证收件人
            if not recipients:
                logger.warning("没有收件人，跳过邮件发送")
                return False

            # 创建邮件内容
            subject = self._generate_subject(report_data, scheduler_name)
            html_content = self._generate_html_content(
                report_data, report_id, scheduler_name
            )
            text_content = self._generate_text_content(report_data, scheduler_name)

            # 发送邮件
            return self._send_email(recipients, subject, html_content, text_content)

        except Exception as e:
            logger.error(f"发送测试报告邮件失败: {str(e)}")
            return False

    def _validate_config(self) -> bool:
        """验证邮件配置"""
        required_fields = ["smtp_server", "smtp_port", "smtp_username", "sender_email"]

        for field in required_fields:
            if not getattr(self.config, field):
                logger.error(f"邮件配置缺少必要字段: {field}")
                return False

        return True

    def _generate_subject(self, report_data: dict, scheduler_name: str) -> str:
        """生成邮件主题"""
        status = report_data.get("status", "unknown")
        case_name = report_data.get("case_name", "未知用例")

        status_text = {"success": "成功", "failure": "失败", "error": "错误"}.get(
            status, "未知"
        )

        return f"【{scheduler_name}】测试报告 - {case_name} ({status_text})"

    def _generate_html_content(
        self, report_data: dict, report_id: int, scheduler_name: str
    ) -> str:
        """生成HTML邮件内容"""
        status = report_data.get("status", "unknown")
        case_name = report_data.get("case_name", "未知用例")
        start_time = report_data.get("start_time")
        end_time = report_data.get("end_time")
        duration = report_data.get("duration", 0)

        total_cases = report_data.get("total_cases", 0)
        passed_cases = report_data.get("passed_cases", 0)
        failed_cases = report_data.get("failed_cases", 0)
        error_cases = report_data.get("error_cases", 0)

        status_text = {
            "success": '<span style="color: green; font-weight: bold;">成功</span>',
            "failure": '<span style="color: orange; font-weight: bold;">失败</span>',
            "error": '<span style="color: red; font-weight: bold;">错误</span>',
        }.get(status, '<span style="color: gray; font-weight: bold;">未知</span>')

        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                .status-success {{ color: green; font-weight: bold; }}
                .status-failure {{ color: orange; font-weight: bold; }}
                .status-error {{ color: red; font-weight: bold; }}
                .step-stats {{ display: flex; gap: 20px; margin: 15px 0; }}
                .stat-item {{ padding: 10px; border-radius: 5px; text-align: center; }}
                .stat-passed {{ background-color: #d4edda; color: #155724; }}
                .stat-failed {{ background-color: #f8d7da; color: #721c24; }}
                .stat-error {{ background-color: #f5e6e8; color: #721c24; }}
                .stat-total {{ background-color: #e2e3e5; color: #383d41; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>测试报告通知</h2>
                <p>调度任务: {scheduler_name}</p>
            </div>
            
            <div class="summary">
                <h3>测试用例: {case_name}</h3>
                <p><strong>执行状态:</strong> {status_text}</p>
                <p><strong>开始时间:</strong> {start_time}</p>
                <p><strong>结束时间:</strong> {end_time}</p>
                <p><strong>执行时长:</strong> {duration:.2f} 秒</p>
            </div>
            
            <div class="step-stats">
                <div class="stat-item stat-total">
                    <div>总用例</div>
                    <div style="font-size: 24px; font-weight: bold;">{total_cases}</div>
                </div>
                <div class="stat-item stat-passed">
                    <div>通过</div>
                    <div style="font-size: 24px; font-weight: bold;">{passed_cases}</div>
                </div>
                <div class="stat-item stat-failed">
                    <div>失败</div>
                    <div style="font-size: 24px; font-weight: bold;">{failed_cases}</div>
                </div>
                <div class="stat-item stat-error">
                    <div>错误</div>
                    <div style="font-size: 24px; font-weight: bold;">{error_cases}</div>
                </div>
            </div>
            
            <p>报告ID: {report_id}</p>
            <p>此邮件由测试工具管理自动发送，请勿回复。</p>
        </body>
        </html>
        """

        return html

    def _generate_text_content(self, report_data: dict, scheduler_name: str) -> str:
        """生成纯文本邮件内容"""
        status = report_data.get("status", "unknown")
        case_name = report_data.get("case_name", "未知用例")
        start_time = report_data.get("start_time")
        end_time = report_data.get("end_time")
        duration = report_data.get("duration", 0)

        total_cases = report_data.get("total_cases", 0)
        passed_cases = report_data.get("passed_cases", 0)
        failed_cases = report_data.get("failed_cases", 0)
        error_cases = report_data.get("error_cases", 0)

        status_text = {"success": "成功", "failure": "失败", "error": "错误"}.get(
            status, "未知"
        )

        text = f"""
测试报告通知

调度任务: {scheduler_name}
测试用例: {case_name}
执行状态: {status_text}
开始时间: {start_time}
结束时间: {end_time}
执行时长: {duration:.2f} 秒

用例统计:
- 总用例: {total_cases}
- 通过: {passed_cases}
- 失败: {failed_cases}
- 错误: {error_cases}

此邮件由测试工具管理自动发送，请勿回复。
        """

        return text.strip()

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

            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = Header(subject, "utf-8")
            msg["From"] = Header(
                f"{self.config.sender_name} <{self.config.sender_email}>", "utf-8"
            )
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

                # 修复邮件头格式问题：使用符合RFC5322标准的格式
                # 创建新的邮件对象，使用正确的格式
                msg_fixed = MIMEMultipart("alternative")
                msg_fixed["Subject"] = str(Header(subject, "utf-8"))

                # 修复From头：使用简单的邮箱格式，避免编码问题
                msg_fixed["From"] = self.config.sender_email
                msg_fixed["To"] = ", ".join(recipients)

                # 添加文本和HTML版本
                msg_fixed.attach(MIMEText(text_content, "plain", "utf-8"))
                msg_fixed.attach(MIMEText(html_content, "html", "utf-8"))

                # 发送邮件
                server.send_message(msg_fixed)

                # 关闭连接
                server.quit()

                logger.info(f"测试报告邮件发送成功，收件人: {', '.join(recipients)}")
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

                # 修复邮件头格式问题：使用符合RFC5322标准的格式
                # 创建新的邮件对象，使用正确的格式
                msg_fixed = MIMEMultipart("alternative")
                msg_fixed["Subject"] = str(Header(subject, "utf-8"))

                # 修复From头：使用简单的邮箱格式，避免编码问题
                msg_fixed["From"] = self.config.sender_email
                msg_fixed["To"] = ", ".join(recipients)

                # 添加文本和HTML版本
                msg_fixed.attach(MIMEText(text_content, "plain", "utf-8"))
                msg_fixed.attach(MIMEText(html_content, "html", "utf-8"))

                # 发送邮件
                server.send_message(msg_fixed)

                # 关闭连接
                server.quit()

                logger.info(
                    f"测试报告邮件发送成功(方法2)，收件人: {', '.join(recipients)}"
                )
                return True

        except Exception as e:
            logger.error(f"发送邮件失败: {str(e)}")
            return False

        finally:
            # 恢复原始getfqdn函数
            socket.getfqdn = original_getfqdn
