"""
Token管理服务 - 处理用户会话令牌的创建、验证和过期管理
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from config.database import Database


logger = logging.getLogger(__name__)


class TokenService:
    """Token管理服务"""

    def __init__(self):
        self.db = Database()
        self._cleanup_thread = None
        self._stop_cleanup = False

    def create_session(
        self, user_id: int, expires_hours: int = 24 * 7
    ) -> Optional[str]:
        """
        创建用户会话

        Args:
            user_id: 用户ID
            expires_hours: 过期时间（小时），默认7天

        Returns:
            str: 会话令牌，失败返回None
        """
        try:
            import secrets

            session_token = secrets.token_hex(32)
            expires_at = datetime.now() + timedelta(hours=expires_hours)

            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO user_sessions (user_id, session_token, expires_at)
                        VALUES (%s, %s, %s)
                    """,
                        (user_id, session_token, expires_at),
                    )

                    conn.commit()
                    logger.info(f"会话创建成功: 用户ID {user_id}")
                    return session_token
        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            return None

    def validate_session(self, session_token: str) -> Optional[int]:
        """
        验证会话令牌

        Args:
            session_token: 会话令牌

        Returns:
            int: 用户ID，验证失败返回None
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT user_id, expires_at
                        FROM user_sessions 
                        WHERE session_token = %s
                    """,
                        (session_token,),
                    )

                    session_data = cursor.fetchone()
                    if session_data:
                        user_id = session_data["user_id"]
                        expires_at = session_data["expires_at"]

                        # 检查是否过期
                        if expires_at and datetime.now() < expires_at:
                            logger.info(f"会话验证成功: 用户ID {user_id}")
                            return user_id
                        else:
                            # 删除过期会话
                            self.delete_session(session_token)
                            logger.warning(f"会话已过期: {session_token}")

                    return None
        except Exception as e:
            logger.error(f"验证会话失败: {e}")
            return None

    def delete_session(self, session_token: str) -> bool:
        """删除会话"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM user_sessions 
                        WHERE session_token = %s
                    """,
                        (session_token,),
                    )

                    conn.commit()
                    logger.info(f"会话删除成功: {session_token}")
                    return True
        except Exception as e:
            logger.error(f"删除会话失败: {e}")
            return False

    def delete_user_sessions(self, user_id: int) -> bool:
        """删除用户的所有会话"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM user_sessions 
                        WHERE user_id = %s
                    """,
                        (user_id,),
                    )

                    deleted_count = cursor.rowcount
                    conn.commit()
                    logger.info(
                        f"删除用户会话成功: 用户ID {user_id}, 删除数量: {deleted_count}"
                    )
                    return True
        except Exception as e:
            logger.error(f"删除用户会话失败: {e}")
            return False

    def expire_all_sessions(self) -> int:
        """
        使所有会话过期（标记为过期）

        Returns:
            int: 过期的会话数量
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 设置所有会话的过期时间为当前时间
                    cursor.execute(
                        """
                        UPDATE user_sessions 
                        SET expires_at = CURRENT_TIMESTAMP 
                        WHERE expires_at > CURRENT_TIMESTAMP
                    """
                    )

                    expired_count = cursor.rowcount
                    conn.commit()

                    logger.info(f"所有会话已过期，数量: {expired_count}")
                    return expired_count
        except Exception as e:
            logger.error(f"过期所有会话失败: {e}")
            return 0

    def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话

        Returns:
            int: 清理的会话数量
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM user_sessions 
                        WHERE expires_at < CURRENT_TIMESTAMP
                    """
                    )

                    deleted_count = cursor.rowcount
                    conn.commit()

                    if deleted_count > 0:
                        logger.info(f"清理过期会话成功，数量: {deleted_count}")

                    return deleted_count
        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
            return 0

    def get_active_sessions_count(self) -> int:
        """获取活跃会话数量"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT COUNT(*) as count
                        FROM user_sessions 
                        WHERE expires_at > CURRENT_TIMESTAMP
                    """
                    )

                    result = cursor.fetchone()
                    return result["count"] if result else 0
        except Exception as e:
            logger.error(f"获取活跃会话数量失败: {e}")
            return 0

    def start_weekly_cleanup(self):
        """启动每周清理任务"""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            logger.warning("清理任务已在运行")
            return

        self._stop_cleanup = False
        self._cleanup_thread = threading.Thread(
            target=self._weekly_cleanup_worker, daemon=True
        )
        self._cleanup_thread.start()
        logger.info("每周清理任务已启动")

    def stop_weekly_cleanup(self):
        """停止每周清理任务"""
        self._stop_cleanup = True
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        logger.info("每周清理任务已停止")

    def _weekly_cleanup_worker(self):
        """每周清理任务工作线程"""
        logger.info("每周清理任务工作线程启动")

        while not self._stop_cleanup:
            try:
                now = datetime.now()

                # 检查是否是周一凌晨0点
                if now.weekday() == 0 and now.hour == 0 and now.minute == 0:
                    logger.info("检测到周一凌晨0点，开始过期所有会话")

                    # 过期所有会话
                    expired_count = self.expire_all_sessions()

                    # 清理过期会话
                    cleaned_count = self.cleanup_expired_sessions()

                    logger.info(
                        f"每周清理完成: 过期 {expired_count} 个会话，清理 {cleaned_count} 个过期会话"
                    )

                    # 等待1小时，避免重复执行
                    time.sleep(3600)
                else:
                    # 每分钟检查一次
                    time.sleep(60)

            except Exception as e:
                logger.error(f"每周清理任务执行失败: {e}")
                time.sleep(300)  # 出错后等待5分钟

    def is_monday_midnight(self) -> bool:
        """检查当前时间是否是周一凌晨0点"""
        now = datetime.now()
        return now.weekday() == 0 and now.hour == 0 and now.minute == 0

    def force_weekly_cleanup(self) -> tuple[int, int]:
        """
        强制执行每周清理（手动触发）

        Returns:
            tuple[int, int]: (过期会话数量, 清理会话数量)
        """
        logger.info("手动触发每周清理")

        expired_count = self.expire_all_sessions()
        cleaned_count = self.cleanup_expired_sessions()

        logger.info(
            f"手动清理完成: 过期 {expired_count} 个会话，清理 {cleaned_count} 个过期会话"
        )
        return expired_count, cleaned_count
