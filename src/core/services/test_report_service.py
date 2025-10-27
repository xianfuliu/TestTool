import datetime
import json
from config.database import Database
from typing import List, Dict, Any


class TestReportService:
    """测试报告服务类"""

    def __init__(self):
        self.db = Database()

    def get_reports_with_filters(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """根据筛选条件获取测试报告"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 基础查询
                    sql = """
                        SELECT r.*, c.name as case_name, s.name as scheduler_name
                        FROM test_reports r
                        LEFT JOIN test_cases c ON r.case_id = c.id
                        LEFT JOIN test_schedulers s ON r.scheduler_id = s.id
                        WHERE 1=1
                    """
                    params = []

                    # 添加筛选条件
                    if filters:
                        # 时间范围
                        if 'start_date' in filters and 'end_date' in filters:
                            sql += " AND r.created_at BETWEEN %s AND %s"
                            params.extend([filters['start_date'], filters['end_date']])

                        # 状态筛选
                        if 'status' in filters:
                            sql += " AND r.status = %s"
                            params.append(filters['status'])

                        # 用例筛选
                        if 'case_id' in filters and filters['case_id']:
                            sql += " AND r.case_id = %s"
                            params.append(filters['case_id'])

                        # 搜索
                        if 'search' in filters:
                            sql += " AND r.report_name LIKE %s"
                            params.append(f"%{filters['search']}%")

                    sql += " ORDER BY r.created_at DESC"

                    cursor.execute(sql, params)
                    reports = cursor.fetchall()

                    # 处理时间字段
                    for report in reports:
                        for field in ['start_time', 'end_time', 'created_at']:
                            if report.get(field) and isinstance(report[field], str):
                                try:
                                    report[field] = datetime.fromisoformat(report[field].replace('Z', '+00:00'))
                                except (ValueError, AttributeError):
                                    report[field] = None

                    return reports
        except Exception as e:
            print(f"获取测试报告失败: {e}")
            return []

    def get_report_with_details(self, report_id: int) -> Dict[str, Any]:
        """获取报告详情（包含关联信息）"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 获取报告基本信息
                    cursor.execute("""
                        SELECT r.*, c.name as case_name, s.name as scheduler_name
                        FROM test_reports r
                        LEFT JOIN test_cases c ON r.case_id = c.id
                        LEFT JOIN test_schedulers s ON r.scheduler_id = s.id
                        WHERE r.id = %s
                    """, (report_id,))
                    report = cursor.fetchone()

                    if report:
                        # 处理时间字段
                        for field in ['start_time', 'end_time', 'created_at']:
                            if report.get(field) and isinstance(report[field], str):
                                try:
                                    report[field] = datetime.fromisoformat(report[field].replace('Z', '+00:00'))
                                except (ValueError, AttributeError):
                                    report[field] = None

                    return report
        except Exception as e:
            print(f"获取报告详情失败: {e}")
            return {}

    def get_step_results_by_report(self, report_id: int) -> List[Dict[str, Any]]:
        """根据报告ID获取步骤执行结果"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT sr.*, at.name as api_name
                        FROM test_step_results sr
                        LEFT JOIN test_case_steps scs ON sr.step_id = scs.id
                        LEFT JOIN api_templates at ON scs.api_template_id = at.id
                        WHERE sr.report_id = %s
                        ORDER BY sr.step_order
                    """, (report_id,))
                    steps = cursor.fetchall()

                    # 处理JSON字段
                    for step in steps:
                        for field in ['request_data', 'response_data', 'assertions_result', 'variables_snapshot']:
                            if step.get(field):
                                try:
                                    step[field] = json.loads(step[field])
                                except (json.JSONDecodeError, TypeError):
                                    step[field] = {}

                        # 处理时间字段
                        for field in ['start_time', 'end_time', 'created_at']:
                            if step.get(field) and isinstance(step[field], str):
                                try:
                                    step[field] = datetime.fromisoformat(step[field].replace('Z', '+00:00'))
                                except (ValueError, AttributeError):
                                    step[field] = None

                    return steps
        except Exception as e:
            print(f"获取步骤结果失败: {e}")
            return []

    def delete_report(self, report_id: int) -> bool:
        """删除测试报告"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 先删除步骤结果
                    cursor.execute("DELETE FROM test_step_results WHERE report_id = %s", (report_id,))
                    # 再删除报告
                    cursor.execute("DELETE FROM test_reports WHERE id = %s", (report_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除测试报告失败: {e}")
            raise e

    def delete_old_reports(self, days: int) -> int:
        """删除指定天数前的旧报告"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cutoff_date = datetime.now() - datetime.timedelta(days=days)

                    # 获取要删除的报告ID
                    cursor.execute("SELECT id FROM test_reports WHERE created_at < %s", (cutoff_date,))
                    report_ids = [row['id'] for row in cursor.fetchall()]

                    if report_ids:
                        # 删除步骤结果
                        placeholders = ', '.join(['%s'] * len(report_ids))
                        cursor.execute(f"DELETE FROM test_step_results WHERE report_id IN ({placeholders})", report_ids)

                        # 删除报告
                        cursor.execute(f"DELETE FROM test_reports WHERE id IN ({placeholders})", report_ids)

                    conn.commit()
                    return len(report_ids)

        except Exception as e:
            print(f"删除旧报告失败: {e}")
            raise e
