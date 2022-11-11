from updateme.core import dao
from updateme.core.model import SlackUserPreferences


def escape_string(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


es = escape_string


def get_or_create_slack_user_preferences(user_id: str) -> SlackUserPreferences:
    user_preferences = dao.read_slack_user_preferences(user_id)
    if user_preferences is None:
        user_preferences = SlackUserPreferences(user_id, "company_updates")
        dao.insert_status_update(user_preferences)

    return user_preferences
