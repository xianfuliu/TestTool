import pymysql
import sys
import os

# 添加项目根目录到Python路径，以便能够导入settings模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.settings import DATABASE_CONFIG
from config.database import Database

def check_and_add_column(table_name, column_name, column_definition, index_name=None):
    """检查并添加列到指定表"""
    try:
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # 检查表是否存在
                cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                if not cursor.fetchone():
                    print(f"{table_name}表不存在，需要先创建数据库表")
                    return False
                
                # 检查是否已存在字段
                cursor.execute(f"DESCRIBE {table_name}")
                columns = [row['Field'] for row in cursor.fetchall()]
                
                if column_name in columns:
                    print(f"{table_name}表已包含{column_name}字段，无需更新")
                    return True
                
                # 添加字段
                print(f"正在为{table_name}表添加{column_name}字段...")
                cursor.execute(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN {column_name} {column_definition}
                """)
                
                # 添加索引（如果需要）
                if index_name:
                    cursor.execute(f"""
                        ALTER TABLE {table_name} 
                        ADD INDEX {index_name} ({column_name})
                    """)
                
                conn.commit()
                print(f"{table_name}表更新成功！")
                return True
                
    except Exception as e:
        print(f"更新{table_name}表失败: {e}")
        return False

def update_global_variables_table():
    """更新global_variables表，添加project_id字段"""
    return check_and_add_column(
        'global_variables', 
        'project_id', 
        'INT NOT NULL DEFAULT 0 AFTER id',
        'idx_project_id'
    )

def update_test_schedulers_table():
    """更新test_schedulers表，添加project_id字段"""
    return check_and_add_column(
        'test_schedulers', 
        'project_id', 
        'INT AFTER enabled',
        'idx_project_id'
    )

def update_test_reports_table():
    """更新test_reports表，添加project_id字段"""
    return check_and_add_column(
        'test_reports', 
        'project_id', 
        'INT AFTER case_id',
        'idx_project_id'
    )

def update_test_step_results_table():
    """更新test_step_results表，添加scheduler_id、case_id和execution_logs字段"""
    success = True
    
    # 添加scheduler_id字段
    success = check_and_add_column(
        'test_step_results', 
        'scheduler_id', 
        'INT COMMENT \'调度任务ID\' AFTER id',
        'idx_scheduler_id'
    ) and success
    
    # 添加case_id字段
    success = check_and_add_column(
        'test_step_results', 
        'case_id', 
        'INT NOT NULL COMMENT \'测试用例ID\' AFTER scheduler_id',
        'idx_case_id'
    ) and success
    
    # 添加execution_logs字段
    success = check_and_add_column(
        'test_step_results', 
        'execution_logs', 
        'TEXT COMMENT \'执行日志信息（文本格式）\' AFTER variables_snapshot'
    ) and success
    
    return success

def main():
    """主函数"""
    print("开始更新数据库表结构...")
    
    # 更新所有相关表
    success = True
    success = update_global_variables_table() and success
    success = update_test_schedulers_table() and success
    success = update_test_reports_table() and success
    success = update_test_step_results_table() and success
    
    if success:
        print("数据库表结构更新完成！")
    else:
        print("数据库表结构更新失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()