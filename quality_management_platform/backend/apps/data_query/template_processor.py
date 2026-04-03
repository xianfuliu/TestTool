from __future__ import annotations

import random
import re
import string
from datetime import datetime


def process_template(template: str) -> str:
    result = template
    replacements = {
        "{dateTime}": datetime.now().strftime("%Y%m%d%H%M%S"),
        "{date}": datetime.now().strftime("%Y%m%d"),
        "{time}": datetime.now().strftime("%H%M%S"),
    }
    for key, value in replacements.items():
        result = result.replace(key, value)

    for match in re.findall(r"\{random:digits:(\d+)\}", result):
        result = result.replace(
            f"{{random:digits:{match}}}",
            "".join(random.choices(string.digits, k=int(match))),
        )
    return result
