from PyQt5.QtCore import QThread, pyqtSignal
import pymysql
import traceback
from src.utils.template_processor import TemplateProcessor


# 修改 sql_worker.py 中的 SQLWorker 类
class SQLWorker(QThread):
    """SQL 执行工作线程"""
    finished = pyqtSignal(str, str, object)  # 查询配置, 执行信息, 结果数据
    error = pyqtSignal(str, str)  # 查询配置, 错误信息

    def __init__(self, query_name, connection_params, sql, variable_pool=None):
        super().__init__()
        self.query_name = query_name
        self.connection_params = connection_params
        self.sql = sql
        self.variable_pool = variable_pool or {}

    def run(self):
        try:
            # 在执行前替换SQL中的变量
            processed_sql = self.replace_sql_variables(self.sql)

            print(f"正在连接数据库配置: {self.connection_params['host']}:{self.connection_params['port']}")
            conn = pymysql.connect(**self.connection_params)
            cursor = conn.cursor()

            print(f"执行SQL: {processed_sql}")
            cursor.execute(processed_sql)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            # 将结果转换为字典列表
            result_data = []
            for row in results:
                row_dict = {}
                for i, col in enumerate(columns):
                    # 处理特殊类型，如datetime
                    if hasattr(row[i], 'isoformat'):
                        row_dict[col] = row[i].isoformat()
                    else:
                        row_dict[col] = row[i]
                result_data.append(row_dict)

            print(f"查询成功，返回 {len(results)} 行数据")
            self.finished.emit(self.query_name, f"查询成功，返回 {len(results)} 行数据", result_data)

            cursor.close()
            conn.close()
            print(f"已断开连接")

        except Exception as e:
            error_msg = f"数据库配置错误: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.error.emit(self.query_name, error_msg)

    def replace_sql_variables(self, sql):
        """替换SQL中的变量占位符"""
        import re

        def replace_match(match):
            var_name = match.group(1)
            # 从变量池中获取值
            if var_name in self.variable_pool:
                value = self.variable_pool[var_name]
                # 对字符串值添加引号
                if isinstance(value, str):
                    return f"'{value}'"
                else:
                    return str(value)
            else:
                # 变量不存在，返回原始占位符
                return match.group(0)

        # 替换 {variable} 格式的变量
        processed_sql = re.sub(r'\{(\w+)\}', replace_match, sql)
        return processed_sql
