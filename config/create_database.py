import pymysql
import sys
import os

# 添加项目根目录到Python路径，以便能够导入settings模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.settings import DATABASE_CONFIG

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

if __name__ == "__main__":
    create_database()