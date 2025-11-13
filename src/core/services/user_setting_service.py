import json
import logging
from config.database import Database
from typing import List, Dict, Any, Optional


# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class UserSettingService:
    """用户设置服务类"""

    def __init__(self):
        self.db = Database()

    def get_user_setting(self, user_id: str, setting_key: str) -> Optional[Dict[str, Any]]:
        """获取用户特定设置"""
        try:
            # 参数验证
            if not user_id or not setting_key:
                logger.warning("获取用户设置失败: user_id或setting_key为空")
                return None

            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, user_id, setting_key, setting_value, created_at, updated_at
                        FROM user_settings 
                        WHERE user_id = %s AND setting_key = %s
                    """, (user_id, setting_key))
                    setting = cursor.fetchone()

                    if setting:
                        # 处理JSON字段
                        if setting.get('setting_value'):
                            try:
                                setting['setting_value'] = json.loads(setting['setting_value'])
                            except (json.JSONDecodeError, TypeError) as e:
                                logger.warning(f"解析用户设置JSON失败: {e}")
                                setting['setting_value'] = {}
                        logger.info(f"成功获取用户设置: user_id={user_id}, setting_key={setting_key}")
                        return setting
                    logger.info(f"未找到用户设置: user_id={user_id}, setting_key={setting_key}")
                    return None
        except Exception as e:
            logger.error(f"获取用户设置失败: {e}")
            return None

    def get_user_settings(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户所有设置"""
        try:
            # 参数验证
            if not user_id:
                logger.warning("获取用户设置列表失败: user_id为空")
                return []

            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, user_id, setting_key, setting_value, created_at, updated_at
                        FROM user_settings 
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                    """, (user_id,))
                    settings = cursor.fetchall()

                    # 处理JSON字段
                    for setting in settings:
                        if setting.get('setting_value'):
                            try:
                                setting['setting_value'] = json.loads(setting['setting_value'])
                            except (json.JSONDecodeError, TypeError) as e:
                                logger.warning(f"解析用户设置JSON失败: {e}")
                                setting['setting_value'] = {}

                    logger.info(f"成功获取用户所有设置: user_id={user_id}, 数量={len(settings)}")
                    return settings
        except Exception as e:
            logger.error(f"获取用户设置列表失败: {e}")
            return []

    def create_user_setting(self, data: Dict[str, Any]) -> int:
        """创建用户设置"""
        try:
            # 参数验证
            if not data.get('user_id') or not data.get('setting_key'):
                logger.warning("创建用户设置失败: 缺少必要的参数")
                return 0

            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 处理JSON字段
                    processed_data = data.copy()
                    if 'setting_value' in processed_data:
                        processed_data['setting_value'] = json.dumps(
                            processed_data['setting_value'], 
                            ensure_ascii=False
                        )
                    else:
                        processed_data['setting_value'] = '{}'

                    cursor.execute("""
                        INSERT INTO user_settings (user_id, setting_key, setting_value)
                        VALUES (%s, %s, %s)
                    """, (
                        processed_data.get('user_id', ''),
                        processed_data.get('setting_key', ''),
                        processed_data.get('setting_value', '{}')
                    ))
                    conn.commit()
                    setting_id = cursor.lastrowid
                    logger.info(f"成功创建用户设置: id={setting_id}, user_id={data.get('user_id')}, setting_key={data.get('setting_key')}")
                    return setting_id
        except Exception as e:
            logger.error(f"创建用户设置失败: {e}")
            return 0

    def update_user_setting(self, user_id: str, setting_key: str, setting_value: Dict[str, Any]) -> bool:
        """更新用户设置"""
        try:
            # 参数验证
            if not user_id or not setting_key:
                logger.warning("更新用户设置失败: user_id或setting_key为空")
                return False

            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 处理JSON字段
                    json_setting_value = json.dumps(setting_value, ensure_ascii=False)

                    cursor.execute("""
                        UPDATE user_settings 
                        SET setting_value = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND setting_key = %s
                    """, (
                        json_setting_value,
                        user_id,
                        setting_key
                    ))
                    conn.commit()
                    success = cursor.rowcount > 0
                    if success:
                        logger.info(f"成功更新用户设置: user_id={user_id}, setting_key={setting_key}")
                    else:
                        logger.warning(f"未找到要更新的用户设置: user_id={user_id}, setting_key={setting_key}")
                    return success
        except Exception as e:
            logger.error(f"更新用户设置失败: {e}")
            return False

    def delete_user_setting(self, user_id: str, setting_key: str) -> bool:
        """删除用户设置"""
        try:
            # 参数验证
            if not user_id or not setting_key:
                logger.warning("删除用户设置失败: user_id或setting_key为空")
                return False

            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM user_settings 
                        WHERE user_id = %s AND setting_key = %s
                    """, (user_id, setting_key))
                    conn.commit()
                    success = cursor.rowcount > 0
                    if success:
                        logger.info(f"成功删除用户设置: user_id={user_id}, setting_key={setting_key}")
                    else:
                        logger.warning(f"未找到要删除的用户设置: user_id={user_id}, setting_key={setting_key}")
                    return success
        except Exception as e:
            logger.error(f"删除用户设置失败: {e}")
            return False