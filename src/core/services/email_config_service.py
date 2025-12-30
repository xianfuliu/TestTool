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
        self.db = None
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化数据库连接"""
        try:
            self.db = Database()
            # 测试连接是否可用
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            logger.info("邮件配置服务数据库连接成功")
        except Exception as e:
            logger.warning(f"邮件配置服务数据库连接失败: {str(e)}")
            self.db = None
    
    def get_email_config(self) -> Optional[EmailConfig]:
        """获取邮件配置"""
        # 检查数据库连接是否可用
        if self.db is None:
            logger.warning("数据库连接不可用，无法获取邮件配置")
            return None
            
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT config_value FROM system_config 
                        WHERE config_key = 'email_config'
                    """)
                    
                    result = cursor.fetchone()
                    if result and result['config_value']:
                        # 安全处理JSON数据编码
                        config_json = result['config_value']
                        if isinstance(config_json, bytes):
                            # 如果是字节数据，尝试多种编码
                            try:
                                config_json = config_json.decode('utf-8')
                            except UnicodeDecodeError:
                                try:
                                    config_json = config_json.decode('gbk')
                                except UnicodeDecodeError:
                                    config_json = config_json.decode('latin-1')
                        
                        config_data = json.loads(config_json)
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
                
                # 如果已经是字符串，直接返回
                if isinstance(text, str):
                    # 确保字符串是有效的UTF-8
                    try:
                        text.encode('utf-8')
                        return text
                    except UnicodeEncodeError:
                        # 如果包含非UTF-8字符，尝试修复
                        return text.encode('utf-8', errors='ignore').decode('utf-8')
                
                # 处理字节类型
                if isinstance(text, bytes):
                    # 尝试多种编码解码
                    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'iso-8859-1']
                    for encoding in encodings:
                        try:
                            decoded = text.decode(encoding)
                            # 验证解码后的字符串可以重新编码为UTF-8
                            decoded.encode('utf-8')
                            return decoded
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            continue
                    
                    # 如果所有编码都失败，使用忽略错误的方式
                    return text.decode('utf-8', errors='ignore')
                
                # 处理其他类型
                try:
                    text_str = str(text)
                    # 尝试编码为UTF-8验证
                    text_str.encode('utf-8')
                    return text_str
                except UnicodeEncodeError:
                    # 如果包含非UTF-8字符，尝试修复
                    return str(text).encode('utf-8', errors='ignore').decode('utf-8')
            
            # 安全处理所有字符串
            smtp_server = safe_encode(config.smtp_server)
            smtp_username = safe_encode(config.smtp_username)
            smtp_password = safe_encode(config.smtp_password)
            
            # 测试连接 - 使用ASCII安全的本地主机名
            # 创建SMTP连接，设置ASCII安全的本地主机名
            if config.use_tls:
                server = smtplib.SMTP(smtp_server, config.smtp_port, local_hostname='localhost', timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(smtp_server, config.smtp_port, local_hostname='localhost', timeout=10)
            
            # 登录测试
            server.login(smtp_username, smtp_password)
            
            # 关闭连接
            server.quit()
            
            logger.info("邮件连接测试成功")
            return True
            
        except UnicodeDecodeError as e:
            logger.error(f"邮件连接测试失败：编码错误 - {str(e)}")
            # 安全记录调试信息，避免编码错误
            try:
                safe_server = smtp_server.encode('utf-8', 'ignore').decode('utf-8')
                safe_username = smtp_username.encode('utf-8', 'ignore').decode('utf-8')
                logger.debug(f"编码错误详情 - 服务器: {safe_server}, 用户名: {safe_username}")
            except:
                logger.debug("无法记录编码错误详情")
            return False
        except Exception as e:
            # 处理各种可能的编码错误
            error_msg = str(e)
            if "utf-8" in error_msg.lower() and "codec" in error_msg.lower():
                logger.error(f"邮件连接测试失败：UTF-8编码错误 - {error_msg}")
                # 安全记录调试信息
                try:
                    safe_server = smtp_server.encode('utf-8', 'ignore').decode('utf-8')
                    safe_username = smtp_username.encode('utf-8', 'ignore').decode('utf-8')
                    logger.debug(f"UTF-8编码错误详情 - 服务器: {safe_server}, 用户名: {safe_username}")
                except:
                    logger.debug("无法记录UTF-8编码错误详情")
            elif "ascii" in error_msg.lower() and "codec" in error_msg.lower():
                logger.error(f"邮件连接测试失败：ASCII编码错误 - {error_msg}")
                # 安全记录调试信息
                try:
                    safe_server = smtp_server.encode('utf-8', 'ignore').decode('utf-8')
                    safe_username = smtp_username.encode('utf-8', 'ignore').decode('utf-8')
                    logger.debug(f"ASCII编码错误详情 - 服务器: {safe_server}, 用户名: {safe_username}")
                except:
                    logger.debug("无法记录ASCII编码错误详情")
            else:
                logger.error(f"邮件连接测试失败: {error_msg}")
                # 安全记录调试信息
                try:
                    safe_server = smtp_server.encode('utf-8', 'ignore').decode('utf-8')
                    safe_username = smtp_username.encode('utf-8', 'ignore').decode('utf-8')
                    logger.debug(f"其他错误详情 - 服务器: {safe_server}, 用户名: {safe_username}")
                except:
                    logger.debug("无法记录其他错误详情")
            return False