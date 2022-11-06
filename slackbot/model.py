import uuid

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional

JSON_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(value, JSON_DATE_FORMAT)
    except Exception:
        raise ValueError(f"Can not parse datetime {value}") from None


def _datetime_to_str(d: datetime) -> str:
    return d.strftime(JSON_DATE_FORMAT)


@dataclass
class Team:
    name: str
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    active: bool = True


@dataclass
class Project:
    name: str
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    active: bool = True


@dataclass
class StatusUpdateType:
    name: str
    emoji: str
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    active: bool = True


@dataclass
class StatusUpdateEmoji:
    emoji: str
    meaning: str
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    active: bool = True


@dataclass
class StatusUpdate:
    type: StatusUpdateType
    emoji: StatusUpdateEmoji

    text: str
    published: bool = False

    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)

    teams: List[Team] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
