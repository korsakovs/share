import os
from enum import Enum


def _demand_env_variable(name: str) -> str:
    result = os.getenv(name)
    if result is None:
        raise EnvironmentError(f"{name} env variable is not set. Please, set it and relaunch this app.")
    return result


def slack_bot_token() -> str:
    return _demand_env_variable("SLACK_BOT_TOKEN")


def slack_app_token() -> str:
    return _demand_env_variable("SLACK_APP_TOKEN")


class Env(Enum):
    DEV = 1
    PROD = 2


def get_env(default=Env.DEV) -> Env:
    try:
        return Env[os.getenv("UPDATE_ME_ENV", "").upper().strip()]
    except KeyError:
        return default


class DaoType(Enum):
    SQLITE = 1
    POSTGRES = 2


def get_active_dao_type(default=DaoType.SQLITE) -> DaoType:
    try:
        return DaoType[os.getenv("UPDATE_ME_DAO", "").upper().strip()]
    except KeyError:
        return default


TEAM_NAMES = {
    "R&D": [
        "Mobile",
        "Backend",
        "Data Lake"
    ],
    "Research": [
        "Applied Science",
    ],
    "Product Support": [
        "EMEA",
        "APAC",
        "North America"
    ],
    "Analytics": [
        "Product Analytics",
        "Business Analytics"
    ]
}


PROJECT_NAMES = [
    "Alpha Project",
    "SDK Release",
    "ML Pipeline v2",
]


STATUS_UPDATE_EMOJIS = [
    ("🪪", "Document"),
    ("🚀", "Rocket / Launch"),
    ("⚖️", "Decision"),
    ("🎆️", "Fireworks"),
    ("🎉", "Party Popper"),
    ("🥳", "Partying Face"),
    ("❓", "Red Question Mark"),
    ("📈", "Chart Increasing"),
    ("📉", "Chart Decreasing"),
    ("🔒", "Locked")
]


STATUS_UPDATE_TYPES = [
    ("Good news", "🙂"),
    ("Bad news", "🙃"),
    ("Risk", "⚠️"),
    ("Delay", "⏳️"),
    ("Announce", "📢"),
    ("Release", "🎉"),
    ("Launch", "🚀"),
    ("RFC", "📄"),
]

REACTIONS = [
    ("Like", "👍"),
    ("Congrats", "🥳"),
    ("You rock!", "🚀"),
]
