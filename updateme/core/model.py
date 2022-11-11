import uuid

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Team:
    name: str
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    deleted: bool = False


@dataclass
class Project:
    name: str
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    deleted: bool = False


@dataclass
class StatusUpdateType:
    name: str
    emoji: str
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    deleted: bool = False


@dataclass
class StatusUpdateEmoji:
    emoji: str
    meaning: str
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    deleted: bool = False


@dataclass
class StatusUpdate:
    type: StatusUpdateType
    emoji: StatusUpdateEmoji

    text: str
    published: bool = False
    deleted: bool = False

    author_slack_user_id: Optional[str] = None

    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)

    teams: List[Team] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
