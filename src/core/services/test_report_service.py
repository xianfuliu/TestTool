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

                        # 调度任务筛选
                        if 'scheduler_id' in filters and filters['scheduler_id']:
                            sql += " AND r.scheduler_id = %s"
                            params.append(filters['scheduler_id'])

                        # 项目筛选
                        if 'project_id' in filters and filters['project_id']:
                            sql += " AND r.project_id = %s"
                            params.append(filters['project_id'])

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
                    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)

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

    def get_reports_by_scheduler_id(self, scheduler_id: int) -> List[Dict[str, Any]]:
        """根据调度ID获取执行记录"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT r.*, c.name as case_name, s.name as scheduler_name
                        FROM test_reports r
                        LEFT JOIN test_cases c ON r.case_id = c.id
                        LEFT JOIN test_schedulers s ON r.scheduler_id = s.id
                        WHERE r.scheduler_id = %s
                        ORDER BY r.created_at DESC
                    """, (scheduler_id,))
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
            print(f"根据调度ID获取执行记录失败: {e}")
            return []

    def create_report(self, report_data: Dict[str, Any]) -> int:
        """创建测试报告"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 生成统一格式的报告名称：调度名称_时间戳
                    scheduler_name = "手动执行"  # 默认值
                    if report_data.get('scheduler_id'):
                        # 获取调度名称
                        try:
                            from src.core.services.scheduler_service import UnifiedSchedulerService
                            scheduler_service = UnifiedSchedulerService()
                            scheduler = scheduler_service.get_scheduler_by_id(report_data['scheduler_id'])
                            if scheduler and scheduler.get('name'):
                                scheduler_name = scheduler['name']
                        except Exception:
                            scheduler_name = f"调度{report_data['scheduler_id']}"
                    
                    # 使用统一格式：调度名称_时间戳
                    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                    report_name = f"{scheduler_name}_{timestamp}"
                    
                    # 准备插入数据
                    sql = """
                        INSERT INTO test_reports (
                            scheduler_id, case_id, project_id, report_name, status, 
                            total_steps, passed_steps, failed_steps, error_steps,
                            start_time, end_time, duration, log_path
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    params = (
                        report_data.get('scheduler_id'),
                        report_data.get('case_id', 0),
                        report_data.get('project_id'),
                        report_data.get('report_name', report_name),
                        report_data.get('status', 'running'),
                        report_data.get('total_steps', 0),
                        report_data.get('passed_steps', 0),
                        report_data.get('failed_steps', 0),
                        report_data.get('error_steps', 0),
                        report_data.get('start_time'),
                        report_data.get('end_time'),
                        report_data.get('duration', 0.0),
                        report_data.get('log_path', '')
                    )
                    
                    cursor.execute(sql, params)
                    report_id = cursor.lastrowid
                    conn.commit()
                    
                    return report_id
                    
        except Exception as e:
            print(f"创建测试报告失败: {e}")
            raise e
