"""
邮件配置服务
"""
import json
import logging
from typing import Optional

from src.core.models.email_config_model import EmailConfig
from config.database import Database


logger = logging.getLogger(__name__)


class EmailConfigService:
    """邮件配置服务"""
    
    def __init__(self):
        """初始化邮件配置服务"""
        self.db = Database()
    
    def get_email_config(self) -> Optional[EmailConfig]:
        """获取邮件配置"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT config_value FROM system_config 
                        WHERE config_key = 'email_config'
                    """)
                    
                    result = cursor.fetchone()
                    if result and result['config_value']:
                        config_data = json.loads(result['config_value'])
                        return EmailConfig.from_dict(config_data)
                    
                    return None
                    
        except Exception as e:
            logger.error(f"获取邮件配置失败: {str(e)}")
            return None
    
    def save_email_config(self, config: EmailConfig) -> bool:
        """保存邮件配置"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查配置是否存在
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM system_config 
                        WHERE config_key = 'email_config'
                    """)
                    
                    result = cursor.fetchone()
                    config_json = json.dumps(config.to_dict())
                    
                    if result['count'] > 0:
                        # 更新配置
                        cursor.execute("""
                            UPDATE system_config 
                            SET config_value = %s, updated_at = NOW()
                            WHERE config_key = 'email_config'
                        """, (config_json,))
                    else:
                        # 插入新配置
                        cursor.execute("""
                            INSERT INTO system_config (config_key, config_value, created_at, updated_at)
                            VALUES ('email_config', %s, NOW(), NOW())
                        """, (config_json,))
                    
                    conn.commit()
                    logger.info("邮件配置保存成功")
                    return True
                    
        except Exception as e:
            logger.error(f"保存邮件配置失败: {str(e)}")
            return False
    
    def validate_email_config(self, config: EmailConfig) -> bool:
        """验证邮件配置"""
        required_fields = ['smtp_server', 'smtp_port', 'smtp_username', 'sender_email']
        
        for field in required_fields:
            if not getattr(config, field):
                logger.error(f"邮件配置缺少必要字段: {field}")
                return False
        
        # 验证端口范围
        if not (1 <= config.smtp_port <= 65535):
            logger.error(f"SMTP端口无效: {config.smtp_port}")
            return False
        
        return True
    
    def test_email_connection(self, config: EmailConfig) -> bool:
        """测试邮件连接"""
        try:
            import smtplib
            
            # 验证配置
            if not self.validate_email_config(config):
                return False
            
            # 处理编码问题 - 确保所有字符串都是有效的UTF-8
            def safe_encode(text):
                """安全编码处理"""
                if text is None:
                    return ""
                try:
                    # 先尝试直接使用
                    return str(text)
                except UnicodeDecodeError:
                    # 如果出现解码错误，尝试使用不同的编码
                    try:
                        return text.encode('latin-1').decode('utf-8')
                    except:
                        try:
                            return text.encode('utf-8', errors='ignore').decode('utf-8')
                        except:
                            return str(text).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            
            # 安全处理所有字符串
            smtp_server = safe_encode(config.smtp_server)
            smtp_username = safe_encode(config.smtp_username)
            smtp_password = safe_encode(config.smtp_password)
            
            # 测试连接
            if config.use_tls:
                server = smtplib.SMTP(smtp_server, config.smtp_port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(smtp_server, config.smtp_port, timeout=10)
            
            # 登录测试（确保编码正确）
            server.login(smtp_username, smtp_password)
            
            # 关闭连接
            server.quit()
            
            logger.info("邮件连接测试成功")
            return True
            
        except UnicodeDecodeError as e:
            logger.error(f"邮件连接测试失败：编码错误 - {str(e)}")
            return False
        except Exception as e:
            # 处理各种可能的编码错误
            error_msg = str(e)
            if "utf-8" in error_msg.lower() and "codec" in error_msg.lower():
                logger.error(f"邮件连接测试失败：UTF-8编码错误 - {error_msg}")
            elif "ascii" in error_msg.lower() and "codec" in error_msg.lower():
                logger.error(f"邮件连接测试失败：ASCII编码错误 - {error_msg}")
            else:
                logger.error(f"邮件连接测试失败: {error_msg}")
            return False