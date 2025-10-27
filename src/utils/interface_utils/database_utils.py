import pymysql
import sqlite3
from typing import Dict, Any, List, Optional


class DatabaseUtils:
    """数据库工具类"""

    def get_connection(self, config: Dict[str, Any]):
        """获取数据库连接"""
        db_type = config.get('database_type', 'MySQL').lower()

        try:
            if db_type == 'mysql':
                return pymysql.connect(
                    host=config.get('host', 'localhost'),
                    port=config.get('port', 3306),
                    user=config.get('username', ''),
                    password=config.get('password', ''),
                    database=config.get('database', ''),
                    charset=config.get('charset', 'utf8mb4')
                )
            elif db_type == 'sqlite':
                return sqlite3.connect(config.get('database', ':memory:'))
            else:
                raise ValueError(f"不支持的数据库类型: {db_type}")
        except Exception as e:
            raise Exception(f"数据库连接失败: {str(e)}")

    def execute_query(self, config: Dict[str, Any], sql: str, params: tuple = None) -> Dict[str, Any]:
        """执行SQL查询"""
        connection = None
        try:
            connection = self.get_connection(config)
            cursor = connection.cursor()

            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            result_type = config.get('result_type', 'multiple')

            if result_type == 'count':
                result = cursor.fetchone()
                return {'count': result[0] if result else 0}
            elif result_type == 'single':
                result = cursor.fetchone()
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                else:
                    return {}
            else:  # multiple
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in results]

        except Exception as e:
            raise Exception(f"SQL执行失败: {str(e)}")
        finally:
            if connection:
                connection.close()