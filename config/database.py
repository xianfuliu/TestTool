#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库一键部署脚本

功能说明：
1. 包含数据库配置信息
2. 提供数据库连接管理
3. 支持一键创建数据库和表结构
4. 自动插入默认管理员用户

使用方法：
1. 直接运行：python config/database.py
2. 查看帮助：python config/database.py --help
3. 查看状态：python config/database.py --status

注意：
- 请确保MySQL服务正在运行
- 请根据实际情况修改数据库配置
"""

import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime
import json
from typing import Dict, Any, List, Optional
import sys
import os
import hashlib
import time
import argparse

# =============================================================================
# 数据库配置 - 请根据实际情况修改
# =============================================================================

# 数据库配置
DATABASE_CONFIG = {
    'host': '192.168.0.73',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'interface_auto_platform'
}

# =============================================================================
# 数据库表结构定义
# =============================================================================

# 完整的数据库表结构定义
DB_TABLES = {
    'business_groups': '''
        CREATE TABLE IF NOT EXISTS business_groups (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'projects': '''
        CREATE TABLE IF NOT EXISTS projects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            business_group_id INT,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (business_group_id) REFERENCES business_groups(id) ON DELETE SET NULL,
            INDEX idx_business_group_id (business_group_id),
            INDEX idx_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'api_folders': '''
        CREATE TABLE IF NOT EXISTS api_folders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            parent_id INT DEFAULT 0,
            description TEXT,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            INDEX idx_project_id (project_id),
            INDEX idx_parent_id (parent_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'api_templates': '''
        CREATE TABLE IF NOT EXISTS api_templates (
            id INT AUTO_INCREMENT PRIMARY KEY,
            folder_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            method ENUM('GET', 'POST', 'PUT', 'DELETE', 'PATCH') DEFAULT 'GET',
            url VARCHAR(500) NOT NULL,
            headers JSON,
            body JSON,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (folder_id) REFERENCES api_folders(id) ON DELETE CASCADE,
            INDEX idx_folder_id (folder_id),
            INDEX idx_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'case_folders': '''
        CREATE TABLE IF NOT EXISTS case_folders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            parent_id INT DEFAULT 0,
            description TEXT,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            INDEX idx_project_id (project_id),
            INDEX idx_parent_id (parent_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'test_cases': '''
        CREATE TABLE IF NOT EXISTS test_cases (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL,
            folder_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            environment_id INT,
            global_vars JSON,
            enable_encryption BOOLEAN DEFAULT FALSE COMMENT '是否启用加解密',
            encrypt_url VARCHAR(500) COMMENT '加密接口URL',
            decrypt_url VARCHAR(500) COMMENT '解密接口URL',
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (folder_id) REFERENCES case_folders(id) ON DELETE CASCADE,
            INDEX idx_project_id (project_id),
            INDEX idx_folder_id (folder_id),
            INDEX idx_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'test_case_steps': '''
        CREATE TABLE IF NOT EXISTS test_case_steps (
            id INT AUTO_INCREMENT PRIMARY KEY,
            case_id INT NOT NULL,
            step_order INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            api_template_id INT,
            request_data JSON,
            expected_response JSON,
            variables_snapshot JSON,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES test_cases(id) ON DELETE CASCADE,
            FOREIGN KEY (api_template_id) REFERENCES api_templates(id) ON DELETE SET NULL,
            UNIQUE KEY uk_case_step_order (case_id, step_order),
            INDEX idx_case_id (case_id),
            INDEX idx_api_template_id (api_template_id),
            INDEX idx_step_order (step_order)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'test_schedulers': '''
        CREATE TABLE IF NOT EXISTS test_schedulers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            cron_expression VARCHAR(50) NOT NULL,
            enabled BOOLEAN DEFAULT FALSE,
            case_ids JSON COMMENT '测试用例ID列表',
            notify_emails JSON COMMENT '邮件通知列表',
            notify_wechat JSON COMMENT '微信通知配置',
            email_config JSON COMMENT '邮件服务器配置',
            last_run_at TIMESTAMP NULL,
            next_run_at TIMESTAMP NULL,
            project_id INT,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
            INDEX idx_name (name),
            INDEX idx_enabled (enabled),
            INDEX idx_next_run_at (next_run_at),
            INDEX idx_project_id (project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'test_reports': '''
        CREATE TABLE IF NOT EXISTS test_reports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            scheduler_id INT,
            case_id INT NULL,
            project_id INT,
            report_name VARCHAR(200) NOT NULL,
            status ENUM('success', 'failure', 'error', 'running') DEFAULT 'running',
            total_cases INT DEFAULT 0,
            passed_cases INT DEFAULT 0,
            failed_cases INT DEFAULT 0,
            error_cases INT DEFAULT 0,
            start_time TIMESTAMP NULL,
            end_time TIMESTAMP NULL,
            duration FLOAT DEFAULT 0 COMMENT '执行时长(秒)',
            log_path VARCHAR(500) COMMENT '日志文件路径',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scheduler_id) REFERENCES test_schedulers(id) ON DELETE SET NULL,
            FOREIGN KEY (case_id) REFERENCES test_cases(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
            INDEX idx_scheduler_id (scheduler_id),
            INDEX idx_case_id (case_id),
            INDEX idx_project_id (project_id),
            INDEX idx_status (status),
            INDEX idx_created_at_desc (created_at DESC),
            INDEX idx_status_created_at (status, created_at DESC),
            INDEX idx_project_id_created_at (project_id, created_at DESC),
            INDEX idx_scheduler_id_created_at (scheduler_id, created_at DESC),
            INDEX idx_case_id_created_at (case_id, created_at DESC),
            INDEX idx_report_name (report_name),
            INDEX idx_start_time (start_time DESC),
            INDEX idx_end_time (end_time DESC)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'test_step_results': '''
        CREATE TABLE IF NOT EXISTS test_step_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            scheduler_id INT COMMENT '调度任务ID',
            report_id INT NOT NULL,
            case_id INT NOT NULL COMMENT '测试用例ID',
            step_id INT NOT NULL,
            step_order INT NOT NULL,
            status ENUM('success', 'failure', 'error', 'skipped') DEFAULT 'skipped',
            request_data JSON COMMENT '请求数据',
            response_data JSON COMMENT '响应数据',
            execution_logs TEXT COMMENT '执行日志信息（文本格式）',
            error_message TEXT,
            start_time TIMESTAMP NULL,
            end_time TIMESTAMP NULL,
            duration FLOAT DEFAULT 0 COMMENT '执行时长(秒)',
            variables_snapshot JSON COMMENT '变量快照',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scheduler_id) REFERENCES test_schedulers(id) ON DELETE SET NULL,
            FOREIGN KEY (report_id) REFERENCES test_reports(id) ON DELETE CASCADE,
            FOREIGN KEY (case_id) REFERENCES test_cases(id) ON DELETE CASCADE,
            INDEX idx_scheduler_id (scheduler_id),
            INDEX idx_report_id (report_id),
            INDEX idx_case_id (case_id),
            INDEX idx_step_id (step_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'global_tools': '''
        CREATE TABLE IF NOT EXISTS global_tools (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            tool_type ENUM('function', 'script', 'api') DEFAULT 'function',
            implementation TEXT COMMENT '实现代码或配置',
            parameters JSON COMMENT '参数定义',
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'global_variables': '''
        CREATE TABLE IF NOT EXISTS global_variables (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL DEFAULT 0,
            name VARCHAR(100) NOT NULL,
            value TEXT,
            variable_type ENUM('string', 'number', 'boolean', 'json') DEFAULT 'string',
            description TEXT,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_project_name (project_id, name),
            INDEX idx_project_id (project_id),
            INDEX idx_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'environments': '''
        CREATE TABLE IF NOT EXISTS environments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            base_url VARCHAR(500) NOT NULL,
            variables JSON COMMENT '环境变量',
            headers JSON COMMENT '默认请求头',
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            INDEX idx_project_id (project_id),
            INDEX idx_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'distributed_locks': '''
        CREATE TABLE IF NOT EXISTS distributed_locks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            lock_key VARCHAR(100) NOT NULL UNIQUE,
            lock_value VARCHAR(100) NOT NULL,
            expire_time TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_lock_key (lock_key),
            INDEX idx_expire_time (expire_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'user_settings': '''
        CREATE TABLE IF NOT EXISTS user_settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            setting_key VARCHAR(100) NOT NULL,
            setting_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_key (user_id, setting_key),
            INDEX idx_user_id (user_id),
            INDEX idx_setting_key (setting_key)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    # =========================================================================
    # 用户认证相关表
    # =========================================================================
    
    'users': '''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(32) NOT NULL COMMENT 'MD5哈希密码',
            email VARCHAR(100) NOT NULL UNIQUE,
            real_name VARCHAR(50) NOT NULL,
            business_line VARCHAR(50) NOT NULL COMMENT '业务线',
            is_admin BOOLEAN DEFAULT FALSE,
            last_login_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_username (username),
            INDEX idx_email (email),
            INDEX idx_business_line (business_line),
            INDEX idx_is_admin (is_admin)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'email_verification_codes': '''
        CREATE TABLE IF NOT EXISTS email_verification_codes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(100) NOT NULL,
            verification_code VARCHAR(10) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_email (email),
            INDEX idx_expires_at (expires_at),
            INDEX idx_used (used)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'user_sessions': '''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            session_token VARCHAR(64) NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_user_id (user_id),
            INDEX idx_session_token (session_token),
            INDEX idx_expires_at (expires_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    '''
}

# =============================================================================
# 数据库连接管理类
# =============================================================================

class JSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理datetime对象"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class Database:
    """数据库连接管理类"""

    def __init__(self):
        self.config = DATABASE_CONFIG
        self._connection_pool = []
        self._max_pool_size = 5

    def get_connection(self):
        """获取数据库连接（带重连机制）"""
        try:
            conn = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset='utf8mb4',
                cursorclass=DictCursor,
                connect_timeout=30,  # 连接超时30秒
                read_timeout=60,     # 读取超时60秒
                write_timeout=60,    # 写入超时60秒
                autocommit=False     # 关闭自动提交，手动控制事务
            )
            
            # 测试连接是否有效
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            return conn
        except pymysql.Error as e:
            print(f"数据库连接失败: {e}")
            # 等待1秒后重试
            time.sleep(1)
            
            # 重试连接
            return pymysql.connect(
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

    def init_database(self):
        """初始化数据库表结构"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 按依赖顺序创建表
                    for table_name, create_sql in DB_TABLES.items():
                        try:
                            cursor.execute(create_sql)
                            print(f"表 {table_name} 创建成功")
                        except Exception as e:
                            print(f"创建表 {table_name} 失败: {e}")
                    conn.commit()
                    print("数据库初始化完成")
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            raise e

# =============================================================================
# 数据库部署功能
# =============================================================================

def create_database():
    """创建数据库"""
    # 复制配置但不指定数据库名，用于连接到MySQL服务器
    config_without_db = DATABASE_CONFIG.copy()
    database_name = config_without_db.pop('database')
    
    try:
        # 连接到MySQL服务器（不指定数据库）
        connection = pymysql.connect(**config_without_db)
        
        with connection.cursor() as cursor:
            # 创建数据库
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"数据库 {database_name} 创建成功")
            
            # 显示所有数据库
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            print("当前所有数据库:")
            for db in databases:
                print(f"  - {db[0]}")
        
        connection.commit()
        connection.close()
        print("数据库创建完成")
        
    except Exception as e:
        print(f"创建数据库失败: {e}")
        raise e


def create_tables():
    """创建数据库表结构并插入默认数据"""
    try:
        # 连接到数据库
        connection = pymysql.connect(**DATABASE_CONFIG)
        
        with connection.cursor() as cursor:
            print("开始创建数据库表...")
            
            # 创建所有表
            for table_name, create_sql in DB_TABLES.items():
                try:
                    cursor.execute(create_sql)
                    print(f"✓ {table_name}表创建成功")
                except Exception as e:
                    print(f"❌ 创建{table_name}表失败: {e}")
            
            # 插入默认的admin用户
            print("\n开始插入默认admin用户...")
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            existing_admin = cursor.fetchone()
            
            if existing_admin:
                print("⚠ admin用户已存在，跳过插入")
            else:
                # 生成admin密码的MD5哈希
                password = "admin"
                password_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
                
                # 插入admin用户
                sql = """
                    INSERT INTO users (username, password_hash, email, real_name, business_line, is_admin)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(sql, (
                    'admin',
                    password_hash,
                    'admin@example.com',
                    '系统管理员',
                    '技术部',
                    True  # 设置为管理员
                ))
                
                # 验证插入结果
                cursor.execute("SELECT id, username, is_admin FROM users WHERE username = 'admin'")
                admin_user = cursor.fetchone()
                
                if admin_user:
                    print(f"✅ admin用户插入成功")
                    print(f"   用户ID: {admin_user[0]}")
                    print(f"   用户名: {admin_user[1]}")
                    print(f"   管理员: {'是' if admin_user[2] else '否'}")
                    print(f"   密码: admin (MD5哈希存储)")
                else:
                    print("❌ admin用户插入失败")
            
            # 显示所有表
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print("\n当前数据库中的所有表:")
            for table in tables:
                print(f"  - {table[0]}")
        
        connection.commit()
        connection.close()
        print("\n数据库表创建完成")
        
    except Exception as e:
        print(f"创建数据库表失败: {e}")
        raise e


def deploy_database():
    """一键部署数据库 - 创建数据库和表结构"""
    
    print("=" * 60)
    print("开始数据库一键部署流程")
    print("=" * 60)
    
    try:
        # 第一步：创建数据库
        print("\n[步骤1] 创建数据库...")
        create_database()
        print("✅ 数据库创建完成")
        
        # 等待1秒，确保数据库已创建
        time.sleep(1)
        
        # 第二步：创建表结构和插入默认数据
        print("\n[步骤2] 创建表结构和插入默认数据...")
        create_tables()
        print("✅ 表结构创建完成")
        
        # 第三步：验证部署结果
        print("\n[步骤3] 验证部署结果...")
        
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # 检查表是否存在
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                
                print(f"✅ 数据库表数量: {len(tables)}")
                print("已创建的表:")
                for table in tables:
                    # 处理不同的游标类型
                    if isinstance(table, dict):
                        table_name = list(table.values())[0]
                    else:
                        table_name = table[0]
                    print(f"  - {table_name}")
                
                # 检查admin用户是否存在
                cursor.execute("SELECT username, email, is_admin FROM users WHERE username = 'admin'")
                admin_user = cursor.fetchone()
                
                if admin_user:
                    print(f"✅ 默认admin用户已创建")
                    # 处理不同的游标类型
                    if isinstance(admin_user, dict):
                        username = admin_user.get('username', '未知')
                        email = admin_user.get('email', '未知')
                        is_admin = admin_user.get('is_admin', False)
                    else:
                        username = admin_user[0] if len(admin_user) > 0 else '未知'
                        email = admin_user[1] if len(admin_user) > 1 else '未知'
                        is_admin = admin_user[2] if len(admin_user) > 2 else False
                    
                    print(f"   用户名: {username}")
                    print(f"   邮箱: {email}")
                    print(f"   管理员: {'是' if is_admin else '否'}")
                else:
                    print("❌ admin用户创建失败")
        
        print("\n" + "=" * 60)
        print("✅ 数据库一键部署完成！")
        print("=" * 60)
        
        # 显示部署完成后的使用说明
        print("\n📋 部署完成后的使用说明:")
        print("1. 默认管理员账号: admin")
        print("2. 默认管理员密码: admin")
        print("3. 请及时修改默认密码")
        print("4. 应用程序可以正常启动使用了")
        
    except Exception as e:
        print(f"❌ 数据库部署失败: {e}")
        print("\n💡 故障排除建议:")
        print("1. 检查MySQL服务是否正在运行")
        print("2. 检查数据库配置是否正确")
        print("3. 检查数据库连接权限")
        sys.exit(1)


def check_deployment_status():
    """检查数据库部署状态"""
    
    print("=" * 60)
    print("检查数据库部署状态")
    print("=" * 60)
    
    try:
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # 检查表是否存在
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                
                print(f"📊 数据库表数量: {len(tables)}")
                print("当前存在的表:")
                for table in tables:
                    # 处理不同的游标类型
                    if isinstance(table, dict):
                        table_name = list(table.values())[0]
                    else:
                        table_name = table[0]
                    print(f"  - {table_name}")
                
                # 检查admin用户是否存在
                cursor.execute("SELECT username, email, is_admin FROM users WHERE username = 'admin'")
                admin_user = cursor.fetchone()
                
                if admin_user:
                    print(f"✅ admin用户状态: 正常")
                    # 处理不同的游标类型
                    if isinstance(admin_user, dict):
                        username = admin_user.get('username', '未知')
                        email = admin_user.get('email', '未知')
                        is_admin = admin_user.get('is_admin', False)
                    else:
                        username = admin_user[0] if len(admin_user) > 0 else '未知'
                        email = admin_user[1] if len(admin_user) > 1 else '未知'
                        is_admin = admin_user[2] if len(admin_user) > 2 else False
                    
                    print(f"   用户名: {username}")
                    print(f"   邮箱: {email}")
                    print(f"   管理员: {'是' if is_admin else '否'}")
                else:
                    print("❌ admin用户状态: 不存在")
                
                # 检查关键表是否存在
                required_tables = ['users', 'email_verification_codes', 'user_sessions']
                missing_tables = []
                
                # 构建现有表名列表
                existing_tables = []
                for table in tables:
                    if isinstance(table, dict):
                        existing_tables.append(list(table.values())[0])
                    else:
                        existing_tables.append(table[0])
                
                for table in required_tables:
                    if table not in existing_tables:
                        missing_tables.append(table)
                
                if missing_tables:
                    print(f"❌ 缺失的表: {', '.join(missing_tables)}")
                    print("建议重新运行部署脚本")
                else:
                    print("✅ 所有必需表都存在")
        
    except Exception as e:
        print(f"❌ 检查部署状态失败: {e}")
        import traceback
        traceback.print_exc()
        print("数据库可能尚未部署或配置有误")


def show_usage():
    """显示使用说明"""
    
    print("=" * 60)
    print("数据库一键部署脚本使用说明")
    print("=" * 60)
    print("\n这是一个完整的数据库部署脚本，包含：")
    print("1. 数据库配置信息")
    print("2. 数据库连接管理")
    print("3. 一键创建数据库和表结构")
    print("4. 自动插入默认管理员用户")
    print("\n使用方法:")
    print("  python config/database.py [选项]")
    print("\n选项:")
    print("  deploy        - 执行完整的数据库部署（默认）")
    print("  status        - 检查当前部署状态")
    print("  help          - 显示此帮助信息")
    print("\n示例:")
    print("  python config/database.py deploy")
    print("  python config/database.py status")
    print("  python config/database.py help")
    print("\n注意:")
    print("  1. 确保MySQL服务正在运行")
    print("  2. 请根据实际情况修改数据库配置")
    print("  3. 部署完成后请及时修改默认管理员密码")

# =============================================================================
# 主程序入口
# =============================================================================

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='数据库一键部署脚本')
    parser.add_argument('command', nargs='?', default='deploy', 
                       choices=['deploy', 'status', 'help'],
                       help='要执行的命令 (deploy: 部署, status: 检查状态, help: 帮助)')
    
    args = parser.parse_args()
    
    # 根据命令执行相应操作
    if args.command == 'deploy':
        deploy_database()
    elif args.command == 'status':
        check_deployment_status()
    elif args.command == 'help':
        show_usage()
    else:
        print(f"❌ 未知命令: {args.command}")
        show_usage()
        sys.exit(1)