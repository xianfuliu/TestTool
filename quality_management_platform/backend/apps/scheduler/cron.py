from __future__ import annotations

from datetime import datetime, timedelta


MONTH_NAMES = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

WEEK_NAMES = {
    "SUN": 0,
    "MON": 1,
    "TUE": 2,
    "WED": 3,
    "THU": 4,
    "FRI": 5,
    "SAT": 6,
}


class CronExpressionError(ValueError):
    pass


def validate_cron_expression(expression: str) -> None:
    _parse_cron(expression)


def get_next_cron_time(expression: str, base_time: datetime | None = None) -> datetime | None:
    cron = _parse_cron(expression)
    base = base_time or datetime.now()
    current = (base + timedelta(minutes=1)).replace(second=0, microsecond=0)
    deadline = current + timedelta(days=366)

    while current <= deadline:
        if _matches(cron, current):
            return current
        current += timedelta(minutes=1)
    return None


def _parse_cron(expression: str) -> dict[str, set[int] | bool]:
    parts = str(expression or "").strip().split()
    if len(parts) == 6:
        parts = parts[1:]
    if len(parts) != 5:
        raise CronExpressionError("Cron 表达式需要 5 位：分 时 日 月 周")

    minute, hour, day, month, week = parts
    return {
        "minutes": _parse_field(minute, 0, 59),
        "hours": _parse_field(hour, 0, 23),
        "days": _parse_field(day, 1, 31),
        "months": _parse_field(month, 1, 12, MONTH_NAMES),
        "weeks": _parse_field(week, 0, 7, WEEK_NAMES),
        "day_any": day in {"*", "?"},
        "week_any": week in {"*", "?"},
    }


def _parse_field(
    expression: str,
    min_value: int,
    max_value: int,
    aliases: dict[str, int] | None = None,
) -> set[int]:
    text = str(expression or "").strip().upper()
    if text in {"*", "?"}:
        return set(range(min_value, max_value + 1))
    values: set[int] = set()
    for part in text.split(","):
        values.update(_parse_part(part.strip(), min_value, max_value, aliases or {}))
    if not values:
        raise CronExpressionError(f"Cron 字段无有效值：{expression}")
    return values


def _parse_part(part: str, min_value: int, max_value: int, aliases: dict[str, int]) -> set[int]:
    if not part:
        raise CronExpressionError("Cron 字段存在空片段")

    if "/" in part:
        range_part, step_part = part.split("/", 1)
        try:
            step = int(step_part)
        except ValueError as exc:
            raise CronExpressionError(f"Cron 步长不是数字：{part}") from exc
        if step <= 0:
            raise CronExpressionError(f"Cron 步长必须大于 0：{part}")
    else:
        range_part = part
        step = 1

    if range_part in {"*", "?"}:
        start = min_value
        end = max_value
    elif "-" in range_part:
        start_text, end_text = range_part.split("-", 1)
        start = _parse_value(start_text, aliases)
        end = _parse_value(end_text, aliases)
    else:
        start = _parse_value(range_part, aliases)
        end = max_value if "/" in part else start

    if start < min_value or end > max_value or start > end:
        raise CronExpressionError(f"Cron 字段超出范围：{part}")
    return set(range(start, end + 1, step))


def _parse_value(value: str, aliases: dict[str, int]) -> int:
    text = value.strip().upper()
    if text in aliases:
        return aliases[text]
    try:
        return int(text)
    except ValueError as exc:
        raise CronExpressionError(f"Cron 字段无法识别：{value}") from exc


def _matches(cron: dict[str, set[int] | bool], value: datetime) -> bool:
    cron_weekday = (value.weekday() + 1) % 7
    weeks = set(cron["weeks"]) | ({0} if 7 in cron["weeks"] else set())

    day_matches = value.day in cron["days"]
    week_matches = cron_weekday in weeks
    if cron["day_any"] and cron["week_any"]:
        calendar_matches = True
    elif cron["day_any"]:
        calendar_matches = week_matches
    elif cron["week_any"]:
        calendar_matches = day_matches
    else:
        calendar_matches = day_matches and week_matches

    return (
        value.minute in cron["minutes"]
        and value.hour in cron["hours"]
        and value.month in cron["months"]
        and calendar_matches
    )
