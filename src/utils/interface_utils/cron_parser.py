import re
from datetime import datetime, timedelta
from typing import Optional, List


class CronParser:
    """Cron表达式解析器"""

    def __init__(self):
        self.field_names = ['minute', 'hour', 'day', 'month', 'week', 'year']
        self.month_names = {
            'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
        }
        self.week_names = {
            'SUN': 0, 'MON': 1, 'TUE': 2, 'WED': 3, 'THU': 4, 'FRI': 5, 'SAT': 6
        }

    def validate_cron(self, cron_expr: str) -> bool:
        """验证Cron表达式格式"""
        try:
            parts = cron_expr.strip().split()
            if len(parts) < 5 or len(parts) > 6:
                return False

            # 简化验证，实际应该更严格
            return True
        except:
            return False

    def get_next_run(self, cron_expr: str, base_time: datetime = None) -> Optional[datetime]:
        """获取下次执行时间

        Args:
            cron_expr: Cron表达式
            base_time: 基准时间，默认为当前时间

        Returns:
            下次执行时间，如果表达式无效返回None
        """
        if not base_time:
            base_time = datetime.now()

        if not self.validate_cron(cron_expr):
            return None

        try:
            # 简化的实现，实际应该使用更复杂的算法
            # 这里使用一个简单的实现：每分钟检查一次
            parts = cron_expr.strip().split()

            # 解析各个字段
            minute_field = parts[0] if len(parts) > 0 else '*'
            hour_field = parts[1] if len(parts) > 1 else '*'
            day_field = parts[2] if len(parts) > 2 else '*'
            month_field = parts[3] if len(parts) > 3 else '*'
            week_field = parts[4] if len(parts) > 4 else '*'

            # 从基准时间开始，每次增加1分钟，直到找到匹配的时间
            current_time = base_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
            max_iterations = 100000  # 防止无限循环

            for _ in range(max_iterations):
                if self._match_field(minute_field, current_time.minute) and \
                        self._match_field(hour_field, current_time.hour) and \
                        self._match_field(day_field, current_time.day) and \
                        self._match_field(month_field, current_time.month) and \
                        self._match_field(week_field, current_time.weekday()):
                    return current_time

                current_time += timedelta(minutes=1)

            return None

        except Exception as e:
            print(f"计算下次执行时间失败: {e}")
            return None

    def _match_field(self, field: str, value: int) -> bool:
        """匹配字段值"""
        if field == '*':
            return True
        elif ',' in field:
            parts = field.split(',')
            return any(self._match_field(part.strip(), value) for part in parts)
        elif '-' in field:
            start, end = field.split('-')
            start_val = self._parse_field_value(start.strip())
            end_val = self._parse_field_value(end.strip())
            return start_val <= value <= end_val
        elif '/' in field:
            range_part, step_part = field.split('/')
            step = int(step_part)
            if range_part == '*':
                return value % step == 0
            else:
                # 处理复杂的步长表达式
                pass
        else:
            field_val = self._parse_field_value(field)
            return field_val == value

        return False

    def _parse_field_value(self, field: str) -> int:
        """解析字段值"""
        # 处理月份名称
        if field.upper() in self.month_names:
            return self.month_names[field.upper()]
        # 处理星期名称
        if field.upper() in self.week_names:
            return self.week_names[field.upper()]
        # 处理数字
        try:
            return int(field)
        except ValueError:
            return 0

    def get_previous_run(self, cron_expr: str, base_time: datetime = None) -> Optional[datetime]:
        """获取上次执行时间"""
        if not base_time:
            base_time = datetime.now()

        # 简化的实现
        try:
            next_run = self.get_next_run(cron_expr, base_time - timedelta(days=365))
            if next_run and next_run < base_time:
                return next_run
            return None
        except:
            return None