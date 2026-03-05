"""
公共数据库工具类
用于统一管理数据库连接和配置
"""

import pymysql
from pymysql.cursors import DictCursor
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """数据库配置类"""
    
    # 默认数据库配置
    DEFAULT_CONFIG = {
        "host": "47.106.192.83",
        "port": 3306,
        "user": "xvdba", 
        "password": "xvdba@2022",
        "database": "cfloan_biz",
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False
    }
    
    # 征信前置操作专用配置
    CREDIT_PRE_OPERATION_CONFIG = {
        "host": "rm-bp1ah1feb2dt774376o.mysql.rds.aliyuncs.com",
        "port": 3306,
        "user": "indiv_auth_test", 
        "password": "QnMvOBVnVNMviOi8",
        "database": "indiv_auth",
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化数据库配置
        
        Args:
            config: 自定义配置，会覆盖默认配置
        """
        self._config = self.DEFAULT_CONFIG.copy()
        if config:
            self._config.update(config)
    
    def get_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return self._config.copy()
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新数据库配置"""
        self._config.update(config)
    
    def get_connection_string(self) -> str:
        """获取连接字符串（用于调试）"""
        return f"mysql://{self._config['user']}:****@{self._config['host']}:{self._config['port']}/{self._config['database']}"


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        初始化数据库管理器
        
        Args:
            config: 数据库配置，如果为None则使用默认配置
        """
        self._config = config or DatabaseConfig()
        self._connection_pool = {}
    
    def get_connection(self) -> pymysql.connections.Connection:
        """
        获取数据库连接
        
        Returns:
            pymysql.connections.Connection: 数据库连接对象
            
        Raises:
            pymysql.Error: 数据库连接错误
        """
        try:
            connection = pymysql.connect(**self._config.get_config())
            logger.debug(f"数据库连接成功: {self._config.get_connection_string()}")
            return connection
        except pymysql.Error as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def execute_query(self, sql: str, params: Optional[tuple] = None) -> list:
        """
        执行查询语句
        
        Args:
            sql: SQL查询语句
            params: 查询参数
            
        Returns:
            list: 查询结果列表
        """
        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        finally:
            connection.close()
    
    def execute_update(self, sql: str, params: Optional[tuple] = None) -> int:
        """
        执行更新语句
        
        Args:
            sql: SQL更新语句
            params: 更新参数
            
        Returns:
            int: 影响的行数
        """
        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                affected_rows = cursor.execute(sql, params)
                connection.commit()
                return affected_rows
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()
    
    def execute_transaction(self, operations: list) -> bool:
        """
        执行事务操作
        
        Args:
            operations: 操作列表，每个元素为(sql, params)元组
            
        Returns:
            bool: 事务是否成功
        """
        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                for sql, params in operations:
                    cursor.execute(sql, params)
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            logger.error(f"事务执行失败: {e}")
            return False
        finally:
            connection.close()
    
    def check_table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
            
        Returns:
            bool: 表是否存在
        """
        sql = """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = %s
        """
        try:
            result = self.execute_query(sql, (self._config.get_config()["database"], table_name))
            return result[0]["count"] > 0
        except Exception:
            return False
    
    def get_table_info(self, table_name: str) -> list:
        """
        获取表结构信息
        
        Args:
            table_name: 表名
            
        Returns:
            list: 表结构信息
        """
        sql = """
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default, 
                column_key
            FROM information_schema.columns 
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
        return self.execute_query(sql, (self._config.get_config()["database"], table_name))


# 全局数据库管理器实例
default_database_manager = DatabaseManager()


def get_database_manager(config: Optional[Dict[str, Any]] = None) -> DatabaseManager:
    """
    获取数据库管理器实例
    
    Args:
        config: 自定义配置
        
    Returns:
        DatabaseManager: 数据库管理器实例
    """
    if config:
        return DatabaseManager(DatabaseConfig(config))
    return default_database_manager


def execute_safe_query(sql: str, params: Optional[tuple] = None, default_return=None):
    """
    安全执行查询，避免异常
    
    Args:
        sql: SQL查询语句
        params: 查询参数
        default_return: 异常时的默认返回值
        
    Returns:
        查询结果或默认值
    """
    try:
        return default_database_manager.execute_query(sql, params)
    except Exception as e:
        logger.warning(f"安全查询执行失败: {e}")
        return default_return


def execute_safe_update(sql: str, params: Optional[tuple] = None, default_return=0) -> int:
    """
    安全执行更新，避免异常
    
    Args:
        sql: SQL更新语句
        params: 更新参数
        default_return: 异常时的默认返回值
        
    Returns:
        int: 影响的行数或默认值
    """
    try:
        return default_database_manager.execute_update(sql, params)
    except Exception as e:
        logger.warning(f"安全更新执行失败: {e}")
        return default_return