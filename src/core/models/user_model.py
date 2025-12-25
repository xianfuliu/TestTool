"""
用户数据模型
"""
from datetime import datetime
from typing import Optional


class User:
    """用户模型"""
    
    def __init__(self, 
                 id: Optional[int] = None,
                 username: str = "",
                 password_hash: str = "",
                 email: str = "",
                 business_line: str = "",
                 is_admin: bool = False,
                 last_login_at: Optional[datetime] = None,
                 created_at: Optional[datetime] = None,
                 updated_at: Optional[datetime] = None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.business_line = business_line
        self.is_admin = is_admin
        self.last_login_at = last_login_at
        self.created_at = created_at
        self.updated_at = updated_at
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'username': self.username,
            'password_hash': self.password_hash,
            'email': self.email,
            'business_line': self.business_line,
            'is_admin': self.is_admin,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """从字典创建用户对象"""
        return cls(
            id=data.get('id'),
            username=data.get('username', ''),
            password_hash=data.get('password_hash', ''),
            email=data.get('email', ''),
            business_line=data.get('business_line', ''),
            is_active=data.get('is_active', True),
            is_admin=data.get('is_admin', False),
            last_login_at=datetime.fromisoformat(data['last_login_at']) if data.get('last_login_at') else None,
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )


class EmailVerificationCode:
    """邮箱验证码模型"""
    
    def __init__(self,
                 id: Optional[int] = None,
                 email: str = "",
                 verification_code: str = "",
                 is_used: bool = False,
                 expires_at: Optional[datetime] = None,
                 created_at: Optional[datetime] = None):
        self.id = id
        self.email = email
        self.verification_code = verification_code
        self.is_used = is_used
        self.expires_at = expires_at
        self.created_at = created_at
    
    def is_valid(self) -> bool:
        """检查验证码是否有效"""
        if self.is_used:
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True


class UserSession:
    """用户会话模型"""
    
    def __init__(self,
                 id: Optional[int] = None,
                 user_id: int = 0,
                 session_token: str = "",
                 expires_at: Optional[datetime] = None,
                 created_at: Optional[datetime] = None):
        self.id = id
        self.user_id = user_id
        self.session_token = session_token
        self.expires_at = expires_at
        self.created_at = created_at
    
    def is_valid(self) -> bool:
        """检查会话是否有效"""
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True