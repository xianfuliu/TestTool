import pymysql
import sys
import os

# 添加项目根目录到Python路径，以便能够导入settings模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.settings import DATABASE_CONFIG
from config.database import Database

def update_global_variables_table():
    """更新global_variables表，添加project_id字段"""
    try:
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # 检查表是否存在
                cursor.execute("SHOW TABLES LIKE 'global_variables'")
                if not cursor.fetchone():
                    print("global_variables表不存在，需要先创建数据库表")
                    return False
                
                # 检查是否已存在project_id字段
                cursor.execute("DESCRIBE global_variables")
                columns = [row['Field'] for row in cursor.fetchall()]
                
                if 'project_id' in columns:
                    print("global_variables表已包含project_id字段，无需更新")
                    return True
                
                # 添加project_id字段
                print("正在为global_variables表添加project_id字段...")
                
                # 先删除原有的唯一约束（如果存在）
                try:
                    cursor.execute("ALTER TABLE global_variables DROP INDEX uk_name")
                except:
                    print("删除原有唯一约束失败（可能不存在），继续执行...")
                
                # 添加project_id字段
                cursor.execute("""
                    ALTER TABLE global_variables 
                    ADD COLUMN project_id INT NOT NULL DEFAULT 0 AFTER id
                """)
                
                # 添加新的唯一约束（基于project_id和name）
                cursor.execute("""
                    ALTER TABLE global_variables 
                    ADD UNIQUE KEY uk_project_name (project_id, name)
                """)
                
                # 添加索引
                cursor.execute("""
                    ALTER TABLE global_variables 
                    ADD INDEX idx_project_id (project_id)
                """)
                
                conn.commit()
                print("global_variables表更新成功！")
                return True
                
    except Exception as e:
        print(f"更新global_variables表失败: {e}")
        return False

def main():
    """主函数"""
    print("开始更新数据库表结构...")
    
    # 更新global_variables表
    if update_global_variables_table():
        print("数据库表结构更新完成！")
    else:
        print("数据库表结构更新失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()