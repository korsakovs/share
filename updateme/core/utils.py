from datetime import datetime, timedelta
from functools import lru_cache, wraps
from typing import List


def join_strings_with_commas(names: List[str]) -> str:
    if not names:
        return ""

    if len(names) == 1:
        return names[0]

    if len(names) == 2:
        return f"{names[0]} and {names[1]}"

    return ", ".join(names[:-1]) + ", and " + names[-1]
