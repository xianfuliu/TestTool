from PyQt5.QtCore import QThread, pyqtSignal
import pymysql
import traceback


class SQLWorker(QThread):
    """SQL 执行工作线程"""
    finished = pyqtSignal(str, str, object)  # 查询配置, 执行信息, 结果数据
    error = pyqtSignal(str, str)  # 查询配置, 错误信息

    def __init__(self, query_name, connection_params, sql):
        super().__init__()
        self.query_name = query_name
        self.connection_params = connection_params
        self.sql = sql

    def run(self):
        try:
            print(f"正在连接数据库配置: {self.connection_params['host']}:{self.connection_params['port']}")
            conn = pymysql.connect(**self.connection_params)
            cursor = conn.cursor()

            print(f"执行SQL: {self.sql}")
            cursor.execute(self.sql)
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

        except Exception as e:
            error_msg = f"数据库配置错误: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.error.emit(self.query_name, error_msg)
