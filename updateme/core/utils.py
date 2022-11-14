from typing import List


def join_strings_with_commas(names: List[str]) -> str:
    if not names:
        return ""

    if len(names) == 1:
        return names[0]

    result = ", ".join(names[:-1])
    if len(names) > 2:
        result += ","
    result += " and " + names[-1]

    return result
