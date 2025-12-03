"""
数据库管理器
"""
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器类"""
    
    def __init__(self):
        """初始化数据库管理器"""
        from config.settings import DATABASE_CONFIG
        self.config = DATABASE_CONFIG
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            conn = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset='utf8mb4',
                cursorclass=DictCursor,
                connect_timeout=30,
                read_timeout=60,
                write_timeout=60,
                autocommit=False
            )
            
            # 测试连接是否有效
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            return conn
            
        except pymysql.Error as e:
            logger.error(f"数据库连接失败: {e}")
            raise e
    
    def execute_query(self, sql, params=None):
        """执行查询并返回结果"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params or ())
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            raise e
    
    def execute_update(self, sql, params=None):
        """执行更新操作"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params or ())
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"执行更新失败: {e}")
            raise e
    
    def execute_insert(self, sql, params=None):
        """执行插入操作并返回插入ID"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params or ())
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"执行插入失败: {e}")
            raise e
    
    def check_table_exists(self, table_name):
        """检查表是否存在"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) as count 
                        FROM information_schema.tables 
                        WHERE table_schema = %s AND table_name = %s
                    """, (self.config['database'], table_name))
                    
                    result = cursor.fetchone()
                    return result['count'] > 0
        except Exception as e:
            logger.error(f"检查表是否存在失败: {e}")
            return False