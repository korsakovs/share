from typing import List


def join_strings_with_commas(names: List[str]) -> str:
    if not names:
        return ""

    if len(names) == 1:
        return names[0]

    if len(names) == 2:
        return f"{names[0]} and {names[1]}"

    return ", ".join(names[:-1]) + ", and " + names[-1]


def encode_link_in_slack_message(link: str) -> str:
    if not (link.startswith("http://") or link.startswith("https://")):
        link = "http://" + link
    return link.replace("<", "%3C").replace(">", "%3E").replace("|","%7C")
