import pymysql
import sys
import os

# 添加项目根目录到Python路径，以便能够导入settings模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.database import DATABASE_CONFIG
from config.database import DB_TABLES as TABLES

class DatabaseComparator:
    """数据库表结构比对工具"""
    
    def __init__(self):
        self.db_config = DATABASE_CONFIG
        
    def get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            database=self.db_config['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def get_table_columns(self, table_name):
        """获取表的实际列信息"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = cursor.fetchall()
                    return {col['Field']: col for col in columns}
        except Exception as e:
            print(f"获取表{table_name}列信息失败: {e}")
            return {}
    
    def parse_ddl_columns(self, ddl_sql):
        """从DDL SQL中解析列定义"""
        columns = {}
        
        # 提取CREATE TABLE语句中的列定义部分
        start_idx = ddl_sql.find('(')
        end_idx = ddl_sql.rfind(')')
        if start_idx == -1 or end_idx == -1:
            return columns
            
        columns_section = ddl_sql[start_idx + 1:end_idx]
        lines = [line.strip() for line in columns_section.split('\n') if line.strip()]
        
        current_column = None
        current_definition = []
        
        for line in lines:
            # 跳过约束和索引行
            if line.startswith('PRIMARY KEY') or line.startswith('FOREIGN KEY') or \
               line.startswith('UNIQUE KEY') or line.startswith('INDEX') or \
               line.startswith('KEY') or line.startswith(') ENGINE='):
                if current_column and current_definition:
                    # 保存当前列定义
                    full_definition = ' '.join(current_definition).strip()
                    if full_definition:
                        # 移除末尾的逗号
                        full_definition = full_definition.rstrip(',')
                        columns[current_column] = full_definition
                    current_column = None
                    current_definition = []
                continue
                
            # 检查是否是列定义开始
            if not line.startswith(' ') and not line.startswith('\t'):
                # 保存当前列定义
                if current_column and current_definition:
                    full_definition = ' '.join(current_definition).strip()
                    if full_definition:
                        # 移除末尾的逗号
                        full_definition = full_definition.rstrip(',')
                        columns[current_column] = full_definition
                
                # 开始新列
                parts = line.split(' ', 1)
                if len(parts) >= 1:
                    current_column = parts[0].strip()
                    current_definition = [parts[1].strip()] if len(parts) > 1 else []
            else:
                # 继续当前列定义
                if current_definition is not None:
                    current_definition.append(line.strip())
        
        # 保存最后一个列定义
        if current_column and current_definition:
            full_definition = ' '.join(current_definition).strip()
            if full_definition:
                # 移除末尾的逗号
                full_definition = full_definition.rstrip(',')
                columns[current_column] = full_definition
            
        return columns
    
    def compare_tables(self):
        """比对所有表的字段差异"""
        missing_fields = {}
        obsolete_fields = {}
        
        for table_name, ddl_sql in TABLES.items():
            print(f"\n=== 比对表: {table_name} ===")
            
            # 检查表是否存在
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                        if not cursor.fetchone():
                            print(f"表 {table_name} 不存在，跳过比对")
                            continue
            except Exception as e:
                print(f"检查表 {table_name} 是否存在失败: {e}")
                continue
            
            # 获取实际列信息
            actual_columns = self.get_table_columns(table_name)
            
            # 解析DDL中的列定义
            ddl_columns = self.parse_ddl_columns(ddl_sql)
            
            # 找出缺失的字段（DDL中有但实际表中没有的字段）
            missing_in_actual = []
            for ddl_column in ddl_columns:
                if ddl_column not in actual_columns:
                    missing_in_actual.append((ddl_column, ddl_columns[ddl_column]))
            
            # 找出过时的字段（实际表中有但DDL中没有的字段）
            obsolete_in_ddl = []
            for actual_column in actual_columns:
                if actual_column not in ddl_columns:
                    obsolete_in_ddl.append(actual_column)
            
            if missing_in_actual:
                missing_fields[table_name] = missing_in_actual
                print(f"表 {table_name} 缺失字段:")
                for column, definition in missing_in_actual:
                    print(f"  - {column}: {definition}")
            
            if obsolete_in_ddl:
                obsolete_fields[table_name] = obsolete_in_ddl
                print(f"表 {table_name} 过时字段:")
                for column in obsolete_in_ddl:
                    print(f"  - {column}")
            
            if not missing_in_actual and not obsolete_in_ddl:
                print(f"表 {table_name} 字段完整")
        
        return missing_fields, obsolete_fields
    
    def generate_update_sql(self, missing_fields, obsolete_fields):
        """生成更新SQL语句"""
        update_sqls = []
        
        # 生成添加缺失字段的SQL
        for table_name, columns in missing_fields.items():
            for column_name, column_definition in columns:
                # 处理AFTER子句
                if 'AFTER' in column_definition:
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
                else:
                    # 尝试找到合适的位置
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
                
                update_sqls.append(sql)
                print(f"生成添加字段SQL: {sql}")
        
        # 生成删除过时字段的SQL
        for table_name, columns in obsolete_fields.items():
            for column_name in columns:
                # 检查是否为步骤统计字段，避免误删其他字段
                if column_name in ['total_steps', 'passed_steps', 'failed_steps', 'error_steps']:
                    sql = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
                    update_sqls.append(sql)
                    print(f"生成删除字段SQL: {sql}")
        
        return update_sqls
    
    def execute_updates(self, update_sqls):
        """执行更新操作"""
        success_count = 0
        total_count = len(update_sqls)
        
        if not update_sqls:
            print("没有需要更新的字段")
            return success_count, total_count
        
        print(f"\n开始执行 {total_count} 个更新操作...")
        
        for sql in update_sqls:
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(sql)
                        conn.commit()
                        print(f"✓ 执行成功: {sql}")
                        success_count += 1
            except Exception as e:
                print(f"✗ 执行失败: {sql}")
                print(f"  错误信息: {e}")
        
        return success_count, total_count

def main():
    """主函数"""
    print("开始比对数据库表结构...")
    
    comparator = DatabaseComparator()
    
    # 比对表结构差异
    missing_fields, obsolete_fields = comparator.compare_tables()
    
    if not missing_fields and not obsolete_fields:
        print("\n所有表字段完整，无需更新")
        return True
    
    print(f"\n=== 发现需要更新的表 ===")
    
    # 生成更新SQL
    update_sqls = comparator.generate_update_sql(missing_fields, obsolete_fields)
    
    # 执行更新
    print("\n开始执行字段更新...")
    success_count, total_count = comparator.execute_updates(update_sqls)
    
    print(f"\n=== 更新结果 ===")
    print(f"成功: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("\n数据库表结构更新完成！")
        success = True
    else:
        print("\n数据库表结构更新失败！")
        success = False
        
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)