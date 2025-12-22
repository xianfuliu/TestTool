"""
Session管理服务 - 处理本地session.json文件的读写和验证
"""
import json
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from src.utils.resource_utils import resource_path

logger = logging.getLogger(__name__)


class SessionService:
    """Session管理服务"""
    
    def __init__(self):
        self.session_file = resource_path("config/session.json")
    
    def save_session(self, user_data: Dict[str, Any], session_token: str) -> bool:
        """
        保存session信息到文件
        
        Args:
            user_data: 用户数据
            session_token: 会话令牌
            
        Returns:
            bool: 保存是否成功
        """
        try:
            session_data = {
                "user_id": user_data.get('id'),
                "username": user_data.get('username'),
                "email": user_data.get('email'),
                "session_token": session_token,
                "is_admin": user_data.get('is_admin', 0),
                "saved_at": datetime.now().isoformat()
            }
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Session保存成功: 用户 {user_data.get('username')}")
            return True
            
        except Exception as e:
            logger.error(f"保存Session失败: {e}")
            return False
    
    def load_session(self) -> Optional[Dict[str, Any]]:
        """
        从文件加载session信息
        
        Returns:
            dict: session数据，文件不存在或格式错误返回None
        """
        try:
            if not os.path.exists(self.session_file):
                return None
                
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # 验证必要字段
            required_fields = ['user_id', 'username', 'session_token', 'saved_at']
            if not all(field in session_data for field in required_fields):
                logger.warning("Session文件格式错误，缺少必要字段")
                return None
                
            logger.info(f"Session加载成功: 用户 {session_data.get('username')}")
            return session_data
            
        except Exception as e:
            logger.error(f"加载Session失败: {e}")
            return None
    
    def delete_session(self) -> bool:
        """删除session文件"""
        try:
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
                logger.info("Session文件已删除")
                return True
            return False
        except Exception as e:
            logger.error(f"删除Session失败: {e}")
            return False
    
    def validate_session(self, token_service) -> Optional[Dict[str, Any]]:
        """
        验证session是否有效
        
        Args:
            token_service: TokenService实例
            
        Returns:
            dict: 有效的用户数据，验证失败返回None
        """
        session_data = self.load_session()
        if not session_data:
            return None
        
        # 验证session token
        session_token = session_data.get('session_token')
        user_id = token_service.validate_session(session_token)
        
        if user_id and user_id == session_data.get('user_id'):
            # session有效，返回用户数据
            return session_data
        else:
            # session无效，删除session文件
            self.delete_session()
            logger.warning("Session验证失败，已删除无效session")
            return None