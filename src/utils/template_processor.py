import re
import random
import string
from datetime import datetime


class TemplateProcessor:
    """模板处理器 - 处理日期时间、随机数等复杂占位符"""

    @staticmethod
    def process_template(template_str):
        """
        处理模板字符串中的复杂占位符
        """
        result = template_str

        # 处理日期时间 {dateTime} - 使用当前日期时间
        if "{dateTime}" in result:
            current_datetime = datetime.now().strftime("%Y%m%d%H%M%S")
            result = result.replace("{dateTime}", current_datetime)

        # 处理日期 {date} - 使用当前日期
        if "{date}" in result:
            current_date = datetime.now().strftime("%Y%m%d")
            result = result.replace("{date}", current_date)

        # 处理日期 {time} - 使用当前时间
        if "{time}" in result:
            current_time = datetime.now().strftime("%H%M%S")
            result = result.replace("{time}", current_time)

        # 处理自定义格式的日期时间 {dateTime:format}
        if "{dateTime:" in result:
            matches = re.findall(r'\{dateTime:([^}]+)\}', result)
            for match in matches:
                formatted_datetime = datetime.now().strftime(match)
                result = result.replace(f"{{dateTime:{match}}}", formatted_datetime)

        # 处理自定义格式的日期 {date:format}
        if "{date:" in result:
            matches = re.findall(r'\{date:([^}]+)\}', result)
            for match in matches:
                formatted_date = datetime.now().strftime(match)
                result = result.replace(f"{{date:{match}}}", formatted_date)

        # 处理随机数字 {random:digits:N}
        if "{random:digits:" in result:
            matches = re.findall(r'\{random:digits:(\d+)\}', result)
            for match in matches:
                length = int(match)
                random_digits = ''.join(random.choices(string.digits, k=length))
                result = result.replace(f"{{random:digits:{match}}}", random_digits)

        # 处理随机字母 {random:string:N}
        if "{random:string:" in result:
            matches = re.findall(r'\{random:string:(\d+)\}', result)
            for match in matches:
                length = int(match)
                random_string = ''.join(random.choices(string.ascii_letters, k=length))
                result = result.replace(f"{{random:string:{match}}}", random_string)

        # 处理随机字母数字 {random:alphanum:N}
        if "{random:alphanum:" in result:
            matches = re.findall(r'\{random:alphanum:(\d+)\}', result)
            for match in matches:
                length = int(match)
                random_alphanum = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
                result = result.replace(f"{{random:alphanum:{match}}}", random_alphanum)

        return result
