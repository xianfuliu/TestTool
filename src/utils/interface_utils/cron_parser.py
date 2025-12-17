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
            if len(parts) < 5 or len(parts) > 7:
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
            parts = cron_expr.strip().split()

            # 支持7字段格式（包含秒字段和年字段）
            if len(parts) == 7:
                # 7字段格式：秒 分钟 小时 日 月 星期 年
                second_field = parts[0]
                minute_field = parts[1]
                hour_field = parts[2]
                day_field = parts[3]
                month_field = parts[4]
                week_field = parts[5]
                year_field = parts[6]
            elif len(parts) == 6:
                # 6字段格式：秒 分钟 小时 日 月 星期
                second_field = parts[0]
                minute_field = parts[1]
                hour_field = parts[2]
                day_field = parts[3]
                month_field = parts[4]
                week_field = parts[5]
                year_field = '*'  # 默认年字段为*
            else:
                # 5字段格式：分钟 小时 日 月 星期
                second_field = '0'  # 默认秒为0
                minute_field = parts[0] if len(parts) > 0 else '*'
                hour_field = parts[1] if len(parts) > 1 else '*'
                day_field = parts[2] if len(parts) > 2 else '*'
                month_field = parts[3] if len(parts) > 3 else '*'
                week_field = parts[4] if len(parts) > 4 else '*'
                year_field = '*'  # 默认年字段为*

            # 使用更高效的算法：从当前时间开始，逐级查找下一个匹配的时间
            current_time = base_time.replace(microsecond=0) + timedelta(seconds=1)
            max_iterations = 1000  # 防止无限循环，最多检查1000天

            for _ in range(max_iterations):
                # 检查年字段
                if not self._match_field(year_field, current_time.year):
                    # 年份不匹配，跳到下一年
                    current_time = current_time.replace(
                        year=current_time.year + 1,
                        month=1, day=1, hour=0, minute=0, second=0
                    )
                    continue
                
                # 检查月字段
                if not self._match_field(month_field, current_time.month):
                    # 月份不匹配，跳到下个月
                    next_month = current_time.month + 1
                    if next_month > 12:
                        current_time = current_time.replace(
                            year=current_time.year + 1,
                            month=1, day=1, hour=0, minute=0, second=0
                        )
                    else:
                        current_time = current_time.replace(
                            month=next_month, day=1, hour=0, minute=0, second=0
                        )
                    continue
                
                # 检查日和周字段（日和周互斥）
                if day_field != '?' and week_field != '?':
                    # 如果日字段和周字段都指定了具体值，优先使用日字段
                    if not self._match_field(day_field, current_time.day):
                        # 日期不匹配，跳到下一天
                        current_time = current_time.replace(
                            day=current_time.day + 1, hour=0, minute=0, second=0
                        )
                        continue
                elif day_field != '?':
                    # 只使用日字段
                    if not self._match_field(day_field, current_time.day):
                        current_time = current_time.replace(
                            day=current_time.day + 1, hour=0, minute=0, second=0
                        )
                        continue
                elif week_field != '?':
                    # 只使用周字段
                    if not self._match_field(week_field, current_time.weekday()):
                        # 周几不匹配，跳到下一周
                        days_to_add = 7 - current_time.weekday()
                        current_time = current_time + timedelta(days=days_to_add)
                        current_time = current_time.replace(hour=0, minute=0, second=0)
                        continue
                
                # 检查小时字段
                if not self._match_field(hour_field, current_time.hour):
                    # 小时不匹配，跳到下一小时
                    next_hour = current_time.hour + 1
                    if next_hour > 23:
                        current_time = current_time.replace(
                            day=current_time.day + 1, hour=0, minute=0, second=0
                        )
                    else:
                        current_time = current_time.replace(
                            hour=next_hour, minute=0, second=0
                        )
                    continue
                
                # 检查分钟字段
                if not self._match_field(minute_field, current_time.minute):
                    # 分钟不匹配，跳到下一分钟
                    next_minute = current_time.minute + 1
                    if next_minute > 59:
                        current_time = current_time.replace(
                            hour=current_time.hour + 1, minute=0, second=0
                        )
                    else:
                        current_time = current_time.replace(minute=next_minute, second=0)
                    continue
                
                # 检查秒字段
                if not self._match_field(second_field, current_time.second):
                    # 秒不匹配，跳到下一秒
                    next_second = current_time.second + 1
                    if next_second > 59:
                        current_time = current_time.replace(
                            minute=current_time.minute + 1, second=0
                        )
                    else:
                        current_time = current_time.replace(second=next_second)
                    continue
                
                # 所有字段都匹配，返回当前时间
                return current_time

            return None

        except Exception as e:
            print(f"计算下次执行时间失败: {e}")
            return None

    def _match_field(self, field: str, value: int) -> bool:
        """匹配字段值"""
        if field == '*' or field == '?':
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
            if range_part == '*' or range_part == '?':
                # 对于分钟字段，需要处理跨小时的正确步长计算
                # 例如：从0分钟开始，每50分钟执行一次，应该匹配：0, 50, 100(60+40), 150(120+30)...
                # 正确的计算应该是：value % step == 0
                return value % step == 0
            else:
                # 处理复杂的步长表达式，如 "0-59/5"
                if '-' in range_part:
                    range_start, range_end = range_part.split('-')
                    start_val = self._parse_field_value(range_start.strip())
                    end_val = self._parse_field_value(range_end.strip())
                    # 修正步长计算逻辑
                    if start_val <= value <= end_val:
                        # 计算从起始值开始的偏移量
                        offset = value - start_val
                        return offset >= 0 and offset % step == 0
                    return False
                else:
                    # 处理单个值的步长，如 "0/5"
                    start_val = self._parse_field_value(range_part.strip())
                    # 修正步长计算逻辑
                    if value >= start_val:
                        # 计算从起始值开始的偏移量
                        offset = value - start_val
                        return offset % step == 0
                    return False
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