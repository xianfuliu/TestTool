import pymysql
import sys
import os

# 添加项目根目录到Python路径，以便能够导入settings模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.settings import DATABASE_CONFIG

def update_test_cases_table():
    """更新test_cases表，添加加解密相关字段"""
    try:
        db = pymysql.connect(**DATABASE_CONFIG)
        with db.cursor() as cursor:
            # 检查是否已存在enable_encryption字段
            cursor.execute("DESCRIBE test_cases")
            columns = [row[0] for row in cursor.fetchall()]
            
            if 'enable_encryption' in columns:
                print("test_cases表已包含加解密字段，无需更新")
                return True
            
            print("正在为test_cases表添加加解密字段...")
            
            # 添加enable_encryption字段
            cursor.execute("""
                ALTER TABLE test_cases 
                ADD COLUMN enable_encryption BOOLEAN DEFAULT FALSE COMMENT '是否启用加解密'
            """)
            
            # 添加encrypt_url字段
            cursor.execute("""
                ALTER TABLE test_cases 
                ADD COLUMN encrypt_url VARCHAR(500) COMMENT '加密接口URL'
            """)
            
            # 添加decrypt_url字段
            cursor.execute("""
                ALTER TABLE test_cases 
                ADD COLUMN decrypt_url VARCHAR(500) COMMENT '解密接口URL'
            """)
            
            db.commit()
            print("test_cases表更新成功！")
            return True
            
    except Exception as e:
        print(f"更新test_cases表失败: {e}")
        return False
    finally:
        if 'db' in locals():
            db.close()

def update_test_case_steps_table():
    """更新test_case_steps表，添加enable_encryption字段"""
    try:
        db = pymysql.connect(**DATABASE_CONFIG)
        with db.cursor() as cursor:
            # 检查是否已存在enable_encryption字段
            cursor.execute("DESCRIBE test_case_steps")
            columns = [row[0] for row in cursor.fetchall()]
            
            if 'enable_encryption' in columns:
                print("test_case_steps表已包含enable_encryption字段，无需更新")
                return True
            
            print("正在为test_case_steps表添加enable_encryption字段...")
            
            # 添加enable_encryption字段
            cursor.execute("""
                ALTER TABLE test_case_steps 
                ADD COLUMN enable_encryption BOOLEAN DEFAULT NULL COMMENT '是否启用加解密（NULL表示继承全局设置）'
            """)
            
            db.commit()
            print("test_case_steps表更新成功！")
            return True
            
    except Exception as e:
        print(f"更新test_case_steps表失败: {e}")
        return False
    finally:
        if 'db' in locals():
            db.close()

def main():
    """主函数"""
    print("开始更新测试用例表结构，添加加解密字段...")
    
    # 更新test_cases表
    if update_test_cases_table():
        # 更新test_case_steps表
        if update_test_case_steps_table():
            print("数据库表结构更新完成！")
            print("\n更新内容：")
            print("- test_cases表：添加了enable_encryption、encrypt_url、decrypt_url字段")
            print("- test_case_steps表：添加了enable_encryption字段")
        else:
            print("test_case_steps表更新失败！")
            sys.exit(1)
    else:
        print("test_cases表更新失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()