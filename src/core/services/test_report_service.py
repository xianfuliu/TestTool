import datetime
import json
from config.database import Database
from typing import List, Dict, Any


class TestReportService:
    """测试报告服务类"""

    def __init__(self):
        self.db = Database()

    def get_reports_with_filters(
        self, filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """根据筛选条件获取测试报告"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 优化查询：只选择需要的字段，添加分页限制
                    sql = """
                        SELECT 
                            r.id, r.scheduler_id, r.case_id, r.project_id, r.report_name,
                            r.status, r.total_cases, r.passed_cases, r.failed_cases, r.error_cases,
                            r.start_time, r.end_time, r.duration, r.log_path, r.created_at,
                            c.name as case_name, s.name as scheduler_name
                        FROM test_reports r
                        LEFT JOIN test_cases c ON r.case_id = c.id
                        LEFT JOIN test_schedulers s ON r.scheduler_id = s.id
                        WHERE 1=1
                    """
                    params = []

                    # 添加筛选条件
                    if filters:
                        # 时间范围
                        if "start_date" in filters and "end_date" in filters:
                            sql += " AND r.created_at BETWEEN %s AND %s"
                            params.extend([filters["start_date"], filters["end_date"]])

                        # 状态筛选
                        if "status" in filters:
                            sql += " AND r.status = %s"
                            params.append(filters["status"])

                        # 用例筛选
                        if "case_id" in filters and filters["case_id"]:
                            sql += " AND r.case_id = %s"
                            params.append(filters["case_id"])

                        # 调度任务筛选
                        if "scheduler_id" in filters and filters["scheduler_id"]:
                            sql += " AND r.scheduler_id = %s"
                            params.append(filters["scheduler_id"])

                        # 项目筛选
                        if "project_id" in filters and filters["project_id"]:
                            sql += " AND r.project_id = %s"
                            params.append(filters["project_id"])

                        # 搜索
                        if "search" in filters:
                            sql += " AND r.report_name LIKE %s"
                            params.append(f"%{filters['search']}%")

                    # 添加分页限制（默认显示最近200条记录）
                    limit = filters.get("limit", 200) if filters else 200
                    sql += " ORDER BY r.created_at DESC LIMIT %s"
                    params.append(limit)

                    cursor.execute(sql, params)
                    reports = cursor.fetchall()

                    # 处理时间字段
                    for report in reports:
                        for field in ["start_time", "end_time", "created_at"]:
                            if report.get(field) and isinstance(report[field], str):
                                try:
                                    report[field] = datetime.fromisoformat(
                                        report[field].replace("Z", "+00:00")
                                    )
                                except (ValueError, AttributeError):
                                    report[field] = None

                    # 将元组转换为列表，以匹配信号期望的类型
                    return list(reports)
        except Exception as e:
            print(f"获取测试报告失败: {e}")
            return []

    def get_reports_with_pagination(
        self, filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """根据筛选条件获取测试报告（带分页）"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 获取总记录数
                    count_sql = "SELECT COUNT(*) as total FROM test_reports r WHERE 1=1"
                    count_params = []

                    # 添加筛选条件
                    if filters:
                        # 时间范围
                        if "start_date" in filters and "end_date" in filters:
                            count_sql += " AND r.created_at BETWEEN %s AND %s"
                            count_params.extend(
                                [filters["start_date"], filters["end_date"]]
                            )

                        # 状态筛选
                        if "status" in filters:
                            count_sql += " AND r.status = %s"
                            count_params.append(filters["status"])

                        # 用例筛选
                        if "case_id" in filters and filters["case_id"]:
                            count_sql += " AND r.case_id = %s"
                            count_params.append(filters["case_id"])

                        # 调度任务筛选
                        if "scheduler_id" in filters and filters["scheduler_id"]:
                            count_sql += " AND r.scheduler_id = %s"
                            count_params.append(filters["scheduler_id"])

                        # 项目筛选
                        if "project_id" in filters and filters["project_id"]:
                            count_sql += " AND r.project_id = %s"
                            count_params.append(filters["project_id"])

                        # 搜索
                        if "search" in filters:
                            count_sql += " AND r.report_name LIKE %s"
                            count_params.append(f"%{filters['search']}%")

                    cursor.execute(count_sql, count_params)
                    total_count = cursor.fetchone()["total"]

                    # 获取分页数据
                    page = filters.get("page", 1) if filters else 1
                    page_size = filters.get("page_size", 20) if filters else 20
                    offset = (page - 1) * page_size

                    sql = """
                        SELECT 
                            r.id, r.scheduler_id, r.case_id, r.project_id, r.report_name,
                            r.status, r.total_cases, r.passed_cases, r.failed_cases, r.error_cases,
                            r.start_time, r.end_time, r.duration, r.log_path, r.created_at,
                            c.name as case_name, s.name as scheduler_name
                        FROM test_reports r
                        LEFT JOIN test_cases c ON r.case_id = c.id
                        LEFT JOIN test_schedulers s ON r.scheduler_id = s.id
                        WHERE 1=1
                    """
                    params = []

                    # 添加筛选条件
                    if filters:
                        # 时间范围
                        if "start_date" in filters and "end_date" in filters:
                            sql += " AND r.created_at BETWEEN %s AND %s"
                            params.extend([filters["start_date"], filters["end_date"]])

                        # 状态筛选
                        if "status" in filters:
                            sql += " AND r.status = %s"
                            params.append(filters["status"])

                        # 用例筛选
                        if "case_id" in filters and filters["case_id"]:
                            sql += " AND r.case_id = %s"
                            params.append(filters["case_id"])

                        # 调度任务筛选
                        if "scheduler_id" in filters and filters["scheduler_id"]:
                            sql += " AND r.scheduler_id = %s"
                            params.append(filters["scheduler_id"])

                        # 项目筛选
                        if "project_id" in filters and filters["project_id"]:
                            sql += " AND r.project_id = %s"
                            params.append(filters["project_id"])

                        # 搜索
                        if "search" in filters:
                            sql += " AND r.report_name LIKE %s"
                            params.append(f"%{filters['search']}%")

                    sql += " ORDER BY r.created_at DESC LIMIT %s OFFSET %s"
                    params.extend([page_size, offset])

                    cursor.execute(sql, params)
                    reports = cursor.fetchall()

                    # 处理时间字段
                    for report in reports:
                        for field in ["start_time", "end_time", "created_at"]:
                            if report.get(field) and isinstance(report[field], str):
                                try:
                                    report[field] = datetime.fromisoformat(
                                        report[field].replace("Z", "+00:00")
                                    )
                                except (ValueError, AttributeError):
                                    report[field] = None

                    # 计算分页信息
                    total_pages = (total_count + page_size - 1) // page_size

                    return {
                        "data": list(reports),
                        "pagination": {
                            "total": total_count,
                            "page": page,
                            "page_size": page_size,
                            "total_pages": total_pages,
                            "has_prev": page > 1,
                            "has_next": page < total_pages,
                        },
                    }
        except Exception as e:
            print(f"获取测试报告（分页）失败: {e}")
            return {
                "data": [],
                "pagination": {
                    "total": 0,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 0,
                    "has_prev": False,
                    "has_next": False,
                },
            }

    def get_report_with_details(self, report_id: int) -> Dict[str, Any]:
        """获取报告详情（包含关联信息）"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 获取报告基本信息 - 添加duration字段查询
                    cursor.execute(
                        """
                        SELECT r.*, c.name as case_name, s.name as scheduler_name, r.duration
                        FROM test_reports r
                        LEFT JOIN test_cases c ON r.case_id = c.id
                        LEFT JOIN test_schedulers s ON r.scheduler_id = s.id
                        WHERE r.id = %s
                    """,
                        (report_id,),
                    )
                    report = cursor.fetchone()

                    if report:
                        # 处理时间字段
                        for field in ["start_time", "end_time", "created_at"]:
                            if report.get(field) and isinstance(report[field], str):
                                try:
                                    report[field] = datetime.fromisoformat(
                                        report[field].replace("Z", "+00:00")
                                    )
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
                    cursor.execute(
                        """
                        SELECT 
                            tsr.*, 
                            tc.name as case_name, tcs.name as step_name, tcs.pre_processing, tcs.post_processing
                        FROM test_step_results tsr
                        LEFT JOIN test_cases tc ON tsr.case_id = tc.id
                        LEFT JOIN test_case_steps tcs ON tsr.step_id = tcs.id
                        WHERE tsr.report_id = %s
                        ORDER BY tsr.step_order ASC
                    """,
                        (report_id,),
                    )
                    results = cursor.fetchall()

                    step_results = []
                    for row in results:
                        step_result = {
                            "id": row["id"],
                            "scheduler_id": row["scheduler_id"],
                            "report_id": row["report_id"],
                            "case_id": row["case_id"],
                            "step_id": row["step_id"],
                            "step_order": row["step_order"],
                            "status": row["status"],
                            "request_data": (
                                json.loads(row["request_data"])
                                if row["request_data"]
                                else {}
                            ),
                            "response_data": (
                                json.loads(row["response_data"])
                                if row["response_data"]
                                else {}
                            ),
                            "execution_logs": (
                                row["execution_logs"] if row["execution_logs"] else ""
                            ),
                            "error_message": row["error_message"],
                            "start_time": row["start_time"],
                            "end_time": row["end_time"],
                            "duration": row["duration"],
                            "case_name": row["case_name"],
                            "step_name": row["step_name"],
                            "pre_processing": (
                                json.loads(row["pre_processing"])
                                if row["pre_processing"]
                                else {}
                            ),
                            "post_processing": (
                                json.loads(row["post_processing"])
                                if row["post_processing"]
                                else {}
                            ),
                        }

                        # 处理时间字段
                        for field in ["start_time", "end_time"]:
                            if step_result.get(field) and isinstance(
                                step_result[field], str
                            ):
                                try:
                                    step_result[field] = (
                                        datetime.datetime.fromisoformat(
                                            step_result[field].replace("Z", "+00:00")
                                        )
                                    )
                                except (ValueError, AttributeError):
                                    step_result[field] = None

                        step_results.append(step_result)

                    return step_results

        except Exception as e:
            print(f"获取步骤结果失败: {e}")
            return []

    def delete_report(self, report_id: int) -> bool:
        """删除测试报告"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 先删除步骤结果
                    cursor.execute(
                        "DELETE FROM test_step_results WHERE report_id = %s",
                        (report_id,),
                    )
                    # 再删除报告
                    cursor.execute(
                        "DELETE FROM test_reports WHERE id = %s", (report_id,)
                    )
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
                    cutoff_date = datetime.datetime.now() - datetime.timedelta(
                        days=days
                    )

                    # 获取要删除的报告ID
                    cursor.execute(
                        "SELECT id FROM test_reports WHERE created_at < %s",
                        (cutoff_date,),
                    )
                    report_ids = [row["id"] for row in cursor.fetchall()]

                    if report_ids:
                        # 删除步骤结果
                        placeholders = ", ".join(["%s"] * len(report_ids))
                        cursor.execute(
                            f"DELETE FROM test_step_results WHERE report_id IN ({placeholders})",
                            report_ids,
                        )

                        # 删除报告
                        cursor.execute(
                            f"DELETE FROM test_reports WHERE id IN ({placeholders})",
                            report_ids,
                        )

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
                    cursor.execute(
                        """
                        SELECT r.*, c.name as case_name, s.name as scheduler_name
                        FROM test_reports r
                        LEFT JOIN test_cases c ON r.case_id = c.id
                        LEFT JOIN test_schedulers s ON r.scheduler_id = s.id
                        WHERE r.scheduler_id = %s
                        ORDER BY r.created_at DESC
                    """,
                        (scheduler_id,),
                    )
                    reports = cursor.fetchall()

                    # 处理时间字段
                    for report in reports:
                        for field in ["start_time", "end_time", "created_at"]:
                            if report.get(field) and isinstance(report[field], str):
                                try:
                                    report[field] = datetime.fromisoformat(
                                        report[field].replace("Z", "+00:00")
                                    )
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
                    if report_data.get("scheduler_id"):
                        # 获取调度名称
                        try:
                            from src.core.services.scheduler_service import (
                                UnifiedSchedulerService,
                            )

                            scheduler_service = UnifiedSchedulerService()
                            scheduler = scheduler_service.get_scheduler_by_id(
                                report_data["scheduler_id"]
                            )
                            if scheduler and scheduler.get("name"):
                                scheduler_name = scheduler["name"]
                        except Exception:
                            scheduler_name = f"调度{report_data['scheduler_id']}"

                    # 使用统一格式：调度名称_时间戳
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    report_name = f"{scheduler_name}_{timestamp}"

                    # 准备插入数据
                    sql = """
                        INSERT INTO test_reports (
                            scheduler_id, case_id, project_id, report_name, status, 
                            total_cases, passed_cases, failed_cases, error_cases,
                            start_time, end_time, duration, log_path
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """

                    # 对于调度级别的报告，case_id 应该为 NULL
                    case_id = report_data.get("case_id")
                    if case_id == 0 or (
                        case_id is None and report_data.get("scheduler_id")
                    ):
                        case_id = None

                    params = (
                        report_data.get("scheduler_id"),
                        case_id,
                        report_data.get("project_id"),
                        report_data.get("report_name", report_name),
                        report_data.get("status", "running"),
                        report_data.get("total_cases", 0),
                        report_data.get("passed_cases", 0),
                        report_data.get("failed_cases", 0),
                        report_data.get("error_cases", 0),
                        report_data.get("start_time"),
                        report_data.get("end_time"),
                        report_data.get("duration", 0.0),
                        report_data.get("log_path", ""),
                    )

                    cursor.execute(sql, params)
                    report_id = cursor.lastrowid
                    conn.commit()

                    return report_id

        except Exception as e:
            print(f"创建测试报告失败: {e}")
            raise e

    def save_step_result(self, report_id: int, step_result: Dict[str, Any]) -> bool:
        """保存步骤执行结果"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        INSERT INTO test_step_results (
                            scheduler_id, report_id, case_id, step_id, step_order, status, request_data, 
                            response_data, execution_logs, error_message,
                            start_time, end_time, duration
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """

                    # 准备数据
                    request_data = json.dumps(
                        step_result.get("request_data", {}), ensure_ascii=False
                    )
                    response_data = json.dumps(
                        step_result.get("response_data", {}), ensure_ascii=False
                    )
                    # 将execution_logs从JSON格式改为文本格式，正确格式化日志内容
                    execution_logs = step_result.get("execution_logs", "")
                    if isinstance(execution_logs, list):
                        # 如果是列表格式，正确转换为文本格式
                        log_lines = []
                        for log in execution_logs:
                            if isinstance(log, dict):
                                # 从字典格式转换为标准格式: [时间戳] 级别: 消息
                                timestamp = log.get("timestamp", "")
                                level = log.get("level", "info").upper()
                                message = log.get("message", "")
                                # 格式化时间戳
                                if timestamp:
                                    try:
                                        from datetime import datetime

                                        dt = datetime.fromisoformat(
                                            timestamp.replace("Z", "+00:00")
                                        )
                                        formatted_timestamp = dt.strftime(
                                            "%Y-%m-%d %H:%M:%S"
                                        )
                                    except (ValueError, AttributeError):
                                        formatted_timestamp = timestamp
                                else:
                                    formatted_timestamp = datetime.now().strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    )

                                log_line = f"[{formatted_timestamp}] {level}: {message}"
                                log_lines.append(log_line)
                            else:
                                log_lines.append(str(log))
                        execution_logs = "\n".join(log_lines)

                    params = (
                        step_result.get("scheduler_id"),
                        report_id,
                        step_result.get("case_id", 0),
                        step_result.get("step_id", 0),
                        step_result.get("step_order", 0),
                        step_result.get("status", "error"),
                        request_data,
                        response_data,
                        execution_logs,
                        step_result.get("error_message", ""),
                        step_result.get("start_time"),
                        step_result.get("end_time"),
                        step_result.get("execution_time", 0.0),
                    )

                    cursor.execute(sql, params)
                    conn.commit()
                    return True

        except Exception as e:
            print(f"保存步骤结果失败: {e}")
            return False

    def update_report(self, report_id: int, update_data: Dict[str, Any]) -> bool:
        """更新测试报告"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 构建更新语句
                    set_clauses = []
                    params = []

                    # 可更新的字段
                    updatable_fields = [
                        "status",
                        "total_cases",
                        "passed_cases",
                        "failed_cases",
                        "error_cases",
                        "end_time",
                        "duration",
                        "log_path",
                    ]

                    for field in updatable_fields:
                        if field in update_data:
                            set_clauses.append(f"{field} = %s")
                            params.append(update_data[field])

                    if not set_clauses:
                        return False  # 没有需要更新的字段

                    # 添加报告ID参数
                    params.append(report_id)

                    sql = f"""
                        UPDATE test_reports 
                        SET {', '.join(set_clauses)}
                        WHERE id = %s
                    """

                    cursor.execute(sql, params)
                    conn.commit()

                    return cursor.rowcount > 0

        except Exception as e:
            print(f"更新测试报告失败: {e}")
            return False
