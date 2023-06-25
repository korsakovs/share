from typing import List, Optional, Tuple


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


def generate_slack_message_url(domain: str, message_ts: str, channel_id: str, thread_ts: str = None) -> str:
    link = f"https://{domain}.slack.com/archives/{channel_id}/p{message_ts.replace('.', '')}"
    if thread_ts:
        link += "?thread_ts=" + thread_ts
    return link


def slack_channel_id_thread_ts_message_ts_from_status_update_link(link: str) \
        -> Optional[Tuple[str, Optional[str], str]]:
    if not link or not link.startswith("https://"):
        return

    link_parts = link.split("/")
    if len(link_parts) != 6:
        return

    domain = link_parts[2]
    if not domain.endswith(".slack.com"):
        return
    if len(domain.split(".")) != 3 or len(domain.split(".")) == 0:
        return

    if link_parts[3] != "archives":
        return

    if not link_parts[4]:
        return

    if "?" in link_parts[5]:
        message_id, query_string = link_parts[5].split("?", 1)
    else:
        message_id, query_string = link_parts[5], None

    if message_id.startswith("p") and len(message_id) > 1:
        message_id = message_id[1:]
        message_id = message_id[:-6] + "." + message_id[-6:]
    else:
        return

    thread_ts = None
    if query_string:
        for query_param in query_string.split("&"):
            if "=" in query_param:
                key, value = query_param.split("=", 1)
                if key == "thread_ts":
                    thread_ts = value

    return link_parts[4], thread_ts, message_id
