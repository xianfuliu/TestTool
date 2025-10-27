import json
from config.database import Database
from typing import List, Dict, Any


class SchedulerService:
    """调度服务类"""

    def __init__(self):
        self.db = Database()

    def get_all_schedulers(self) -> List[Dict[str, Any]]:
        """获取所有调度"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, description, cron_expression, enabled, 
                               case_ids, notify_emails, notify_wechat, 
                               last_run_at, next_run_at, created_by, created_at, updated_at
                        FROM test_schedulers 
                        ORDER BY created_at DESC
                    """)
                    schedulers = cursor.fetchall()

                    # 处理JSON字段
                    for scheduler in schedulers:
                        for field in ['case_ids', 'notify_emails', 'notify_wechat']:
                            if scheduler.get(field):
                                scheduler[field] = json.loads(scheduler[field])
                            else:
                                scheduler[field] = []

                    return schedulers
        except Exception as e:
            print(f"获取调度列表失败: {e}")
            return []

    def get_scheduler_by_id(self, scheduler_id: int) -> Dict[str, Any]:
        """根据ID获取调度"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, description, cron_expression, enabled, 
                               case_ids, notify_emails, notify_wechat, 
                               last_run_at, next_run_at, created_by, created_at, updated_at
                        FROM test_schedulers 
                        WHERE id = %s
                    """, (scheduler_id,))
                    scheduler = cursor.fetchone()

                    if scheduler:
                        # 处理JSON字段
                        for field in ['case_ids', 'notify_emails', 'notify_wechat']:
                            if scheduler.get(field):
                                scheduler[field] = json.loads(scheduler[field])
                            else:
                                scheduler[field] = []

                    return scheduler
        except Exception as e:
            print(f"获取调度失败: {e}")
            return {}

    def create_scheduler(self, data: Dict[str, Any]) -> int:
        """创建调度"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 处理JSON字段
                    json_fields = ['case_ids', 'notify_emails', 'notify_wechat']
                    processed_data = data.copy()
                    for field in json_fields:
                        if field in processed_data:
                            processed_data[field] = json.dumps(processed_data[field], ensure_ascii=False)
                        else:
                            processed_data[field] = '[]'

                    # 计算下次执行时间
                    next_run_at = None
                    try:
                        from src.utils.interface_utils.cron_parser import CronParser
                        parser = CronParser()
                        next_run = parser.get_next_run(processed_data['cron_expression'])
                        if next_run:
                            next_run_at = next_run
                    except Exception as e:
                        print(f"计算下次执行时间失败: {e}")

                    cursor.execute("""
                        INSERT INTO test_schedulers (name, description, cron_expression, enabled, 
                                                   case_ids, notify_emails, notify_wechat, next_run_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        processed_data['name'],
                        processed_data.get('description', ''),
                        processed_data['cron_expression'],
                        processed_data.get('enabled', True),
                        processed_data.get('case_ids', '[]'),
                        processed_data.get('notify_emails', '[]'),
                        processed_data.get('notify_wechat', '{}'),
                        next_run_at
                    ))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"创建调度失败: {e}")
            raise e

    def update_scheduler(self, scheduler_id: int, data: Dict[str, Any]) -> bool:
        """更新调度"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 处理JSON字段
                    json_fields = ['case_ids', 'notify_emails', 'notify_wechat']
                    processed_data = data.copy()
                    for field in json_fields:
                        if field in processed_data:
                            processed_data[field] = json.dumps(processed_data[field], ensure_ascii=False)
                        else:
                            processed_data[field] = '[]'

                    # 计算下次执行时间
                    next_run_at = None
                    try:
                        from src.utils.interface_utils.cron_parser import CronParser
                        parser = CronParser()
                        next_run = parser.get_next_run(processed_data['cron_expression'])
                        if next_run:
                            next_run_at = next_run
                    except Exception as e:
                        print(f"计算下次执行时间失败: {e}")

                    cursor.execute("""
                        UPDATE test_schedulers 
                        SET name = %s, description = %s, cron_expression = %s, enabled = %s,
                            case_ids = %s, notify_emails = %s, notify_wechat = %s, next_run_at = %s
                        WHERE id = %s
                    """, (
                        processed_data['name'],
                        processed_data.get('description', ''),
                        processed_data['cron_expression'],
                        processed_data.get('enabled', True),
                        processed_data.get('case_ids', '[]'),
                        processed_data.get('notify_emails', '[]'),
                        processed_data.get('notify_wechat', '{}'),
                        next_run_at,
                        scheduler_id
                    ))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新调度失败: {e}")
            raise e

    def delete_scheduler(self, scheduler_id: int) -> bool:
        """删除调度"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM test_schedulers WHERE id = %s", (scheduler_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除调度失败: {e}")
            raise e

    def update_scheduler_status(self, scheduler_id: int, enabled: bool) -> bool:
        """更新调度状态"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE test_schedulers 
                        SET enabled = %s 
                        WHERE id = %s
                    """, (enabled, scheduler_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新调度状态失败: {e}")
            raise e

    def update_last_run(self, scheduler_id: int) -> bool:
        """更新上次执行时间"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE test_schedulers 
                        SET last_run_at = NOW() 
                        WHERE id = %s
                    """, (scheduler_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新上次执行时间失败: {e}")
            raise e
