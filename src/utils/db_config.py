#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置工具

提供统一的数据库配置读取和连接管理功能
"""

import pymysql
from pymysql.cursors import DictCursor
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入数据库配置
try:
    from config.database import DATABASE_CONFIG
except ImportError:
    # 如果导入失败，使用默认配置
    DATABASE_CONFIG = {
        'host': '192.168.0.73',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'database': 'test_platform'
    }


class DBConfig:
    """数据库配置管理类"""
    
    @staticmethod
    def get_config():
        """获取数据库配置"""
        return DATABASE_CONFIG.copy()
    
    @staticmethod
    def get_connection():
        """获取数据库连接"""
        try:
            conn = pymysql.connect(
                host=DATABASE_CONFIG['host'],
                port=DATABASE_CONFIG['port'],
                user=DATABASE_CONFIG['user'],
                password=DATABASE_CONFIG['password'],
                database=DATABASE_CONFIG['database'],
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
            print(f"数据库连接失败: {e}")
            return None
    
    @staticmethod
    def get_connection_without_db():
        """获取不指定数据库的连接（用于创建数据库）"""
        config_without_db = DATABASE_CONFIG.copy()
        config_without_db.pop('database', None)
        
        try:
            conn = pymysql.connect(
                host=config_without_db['host'],
                port=config_without_db['port'],
                user=config_without_db['user'],
                password=config_without_db['password'],
                charset='utf8mb4',
                cursorclass=DictCursor,
                connect_timeout=30,
                read_timeout=60,
                write_timeout=60,
                autocommit=True
            )
            
            # 测试连接是否有效
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            return conn
        except pymysql.Error as e:
            print(f"数据库连接失败: {e}")
            return None
    
    @staticmethod
    def test_connection():
        """测试数据库连接"""
        conn = DBConfig.get_connection()
        if conn:
            conn.close()
            return True
        return False
    
    @staticmethod
    def get_database_name():
        """获取数据库名称"""
        return DATABASE_CONFIG.get('database', 'test_platform')


# 提供全局函数方便使用
def get_db_config():
    """获取数据库配置"""
    return DBConfig.get_config()


def get_db_connection():
    """获取数据库连接"""
    return DBConfig.get_connection()


def test_db_connection():
    """测试数据库连接"""
    return DBConfig.test_connection()


def get_db_name():
    """获取数据库名称"""
    return DBConfig.get_database_name()