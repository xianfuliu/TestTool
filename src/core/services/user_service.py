"""
用户服务类
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from config.database import Database
from src.core.models.user_model import User, EmailVerificationCode, UserSession
from src.core.services.token_service import TokenService
from src.core.services.session_service import SessionService


logger = logging.getLogger(__name__)


class UserService:
    """用户服务类"""

    def __init__(self):
        self.db = Database()
        self.token_service = TokenService()
        self.session_service = SessionService()

    def hash_password(self, password: str) -> str:
        """对密码进行MD5哈希"""
        return hashlib.md5(password.encode("utf-8")).hexdigest()

    def verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        return self.hash_password(password) == password_hash

    def generate_verification_code(self, length: int = 6) -> str:
        """生成验证码"""
        return "".join(secrets.choice("0123456789") for _ in range(length))

    def generate_session_token(self) -> str:
        """生成会话令牌"""
        return secrets.token_hex(32)

    def check_admin_user_exists(self) -> bool:
        """检查是否存在admin用户"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM users WHERE username = 'admin' AND is_admin = TRUE"
                    )
                    return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"检查admin用户失败: {e}")
            return False

    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, username, password_hash, email, business_line, 
                               is_admin, last_login_at, created_at, updated_at
                        FROM users 
                        WHERE username = %s
                    """,
                        (username,),
                    )
                    user_data = cursor.fetchone()

                    if user_data:
                        return User(**user_data)
                    return None
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, username, password_hash, email, business_line, 
                               is_admin, last_login_at, created_at, updated_at
                        FROM users 
                        WHERE email = %s
                    """,
                        (email,),
                    )
                    user_data = cursor.fetchone()

                    if user_data:
                        return User(**user_data)
                    return None
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据用户ID获取用户"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, username, password_hash, email, business_line, 
                               is_admin, last_login_at, created_at, updated_at
                        FROM users 
                        WHERE id = %s
                    """,
                        (user_id,),
                    )
                    user_data = cursor.fetchone()

                    if user_data:
                        return User(**user_data)
                    return None
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
            return None

    def create_user(self, user_data: Dict[str, Any]) -> Optional[User]:
        """创建用户"""
        try:
            # 检查用户名是否已存在
            if self.get_user_by_username(user_data["username"]):
                logger.warning(f"用户名已存在: {user_data['username']}")
                return None

            # 检查邮箱是否已存在
            if self.get_user_by_email(user_data["email"]):
                logger.warning(f"邮箱已存在: {user_data['email']}")
                return None

            # 对密码进行哈希
            password_hash = self.hash_password(user_data["password"])

            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO users (username, password_hash, email, business_line, is_admin)
                        VALUES (%s, %s, %s, %s, %s)
                    """,
                        (
                            user_data["username"],
                            password_hash,
                            user_data["email"],
                            user_data.get("business_line", ""),
                            user_data.get("is_admin", False),
                        ),
                    )
                    conn.commit()

                    user_id = cursor.lastrowid
                    logger.info(f"用户创建成功: {user_data['username']}, ID: {user_id}")

                    # 返回创建的用户
                    return self.get_user_by_username(user_data["username"])
        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            return None

    def authenticate_user(
        self, username: str, password: str, create_session: bool = True
    ) -> Optional[dict]:
        """用户认证"""
        try:
            user = self.get_user_by_username(username)
            if not user:
                logger.warning(f"用户不存在: {username}")
                return None

            if not self.verify_password(password, user.password_hash):
                logger.warning(f"密码错误: {username}")
                return None

            # 更新最后登录时间
            self.update_last_login(user.id)

            # 创建会话令牌（如果需要）
            session_token = None
            if create_session:
                session = self.create_session(
                    user.id, expires_hours=24 * 7
                )  # 7天有效期
                if session:
                    session_token = session.session_token

            logger.info(f"用户认证成功: {username}")

            # 保存session信息到文件
            if session_token:
                user_dict = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_admin": user.is_admin,
                    "business_line": user.business_line,
                }
                self.session_service.save_session(user_dict, session_token)

            # 返回用户信息和会话令牌
            return {"user": user, "session_token": session_token}
        except Exception as e:
            logger.error(f"用户认证失败: {e}")
            return None

    def update_last_login(self, user_id: int) -> bool:
        """更新最后登录时间"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE users 
                        SET last_login_at = CURRENT_TIMESTAMP 
                        WHERE id = %s
                    """,
                        (user_id,),
                    )
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"更新最后登录时间失败: {e}")
            return False

    def save_verification_code(
        self, email: str, code: str, expires_minutes: int = 10
    ) -> bool:
        """保存验证码"""
        try:
            expires_at = datetime.now() + timedelta(minutes=expires_minutes)

            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 先标记该邮箱的旧验证码为已使用
                    cursor.execute(
                        """
                        UPDATE email_verification_codes 
                        SET used = TRUE 
                        WHERE email = %s AND used = FALSE
                    """,
                        (email,),
                    )

                    # 插入新验证码
                    cursor.execute(
                        """
                        INSERT INTO email_verification_codes (email, verification_code, expires_at)
                        VALUES (%s, %s, %s)
                    """,
                        (email, code, expires_at),
                    )

                    conn.commit()
                    logger.info(f"验证码保存成功: {email}")
                    return True
        except Exception as e:
            logger.error(f"保存验证码失败: {e}")
            return False

    def verify_email_code(self, email: str, code: str) -> bool:
        """验证邮箱验证码"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, email, verification_code, used as is_used, expires_at, created_at
                        FROM email_verification_codes 
                        WHERE email = %s AND verification_code = %s AND used = FALSE
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """,
                        (email, code),
                    )

                    code_data = cursor.fetchone()
                    if not code_data:
                        logger.warning(f"验证码不存在或已使用: {email}")
                        return False

                    verification_code = EmailVerificationCode(**code_data)

                    if not verification_code.is_valid():
                        logger.warning(f"验证码已过期: {email}")
                        return False

                    # 标记验证码为已使用
                    cursor.execute(
                        """
                        UPDATE email_verification_codes 
                        SET used = TRUE 
                        WHERE id = %s
                    """,
                        (verification_code.id,),
                    )

                    conn.commit()
                    logger.info(f"验证码验证成功: {email}")
                    return True
        except Exception as e:
            logger.error(f"验证验证码失败: {e}")
            return False

    def register_user(
        self,
        username: str,
        password: str,
        email: str,
        verification_code: str,
        business_line: str,
    ) -> tuple[bool, str]:
        """
        注册用户

        Args:
            username: 用户名
            password: 密码
            email: 邮箱
            verification_code: 验证码
            business_line: 业务线

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        try:
            # 检查admin用户是否存在
            if not self.check_admin_user_exists():
                return False, "请联系管理员添加admin用户"

            # 验证邮箱验证码
            if not self.verify_email_code(email, verification_code):
                return False, "验证码错误或已过期"

            # 检查用户名是否已存在
            if self.get_user_by_username(username):
                return False, "用户名已存在"

            # 检查邮箱是否已存在
            if self.get_user_by_email(email):
                return False, "邮箱已存在"

            # 创建用户
            user_data = {
                "username": username,
                "password": password,
                "email": email,
                "business_line": business_line,
                "is_admin": False,
            }

            user = self.create_user(user_data)
            if user:
                return True, f"用户 {username} 注册成功"
            else:
                return False, "用户创建失败"

        except Exception as e:
            logger.error(f"用户注册失败: {e}")
            return False, f"注册失败: {str(e)}"

    def create_session(
        self, user_id: int, expires_hours: int = 24 * 7
    ) -> Optional[UserSession]:
        """创建用户会话"""
        try:
            session_token = self.token_service.create_session(user_id, expires_hours)
            if session_token:
                # 获取会话信息
                return self.get_session_by_token(session_token)
            return None
        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            return None

    def get_session_by_token(self, session_token: str) -> Optional[UserSession]:
        """根据令牌获取会话"""
        try:
            user_id = self.token_service.validate_session(session_token)
            if user_id:
                with self.db.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT id, user_id, session_token, expires_at, created_at
                            FROM user_sessions 
                            WHERE session_token = %s
                        """,
                            (session_token,),
                        )

                        session_data = cursor.fetchone()
                        if session_data:
                            return UserSession(**session_data)
            return None
        except Exception as e:
            logger.error(f"获取会话失败: {e}")
            return None

    def delete_session(self, session_token: str) -> bool:
        """删除会话"""
        return self.token_service.delete_session(session_token)

    def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        return self.token_service.cleanup_expired_sessions()
