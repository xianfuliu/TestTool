#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config.database import Database

def check_global_variables_table():
    """检查global_variables表结构"""
    try:
        db = Database()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DESCRIBE global_variables')
                result = cursor.fetchall()
                
                print('更新后的global_variables表结构:')
                print('-' * 50)
                for row in result:
                    print(f"{row[0]}: {row[1]} ({row[2]})")
                
                # 检查project_id字段是否存在
                fields = [row[0] for row in result]
                if 'project_id' in fields:
                    print('\n✅ project_id字段已成功添加到表中')
                    return True
                else:
                    print('\n❌ project_id字段未添加到表中')
                    return False
                    
    except Exception as e:
        print(f"检查表结构失败: {e}")
        return False

if __name__ == "__main__":
    check_global_variables_table()