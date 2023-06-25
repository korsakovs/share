import uuid

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class StatusUpdateSource(Enum):
    SLACK_DIALOG = 1
    SLACK_MESSAGE = 2


@dataclass
class SlackUserInfo:
    name: str
    is_admin: bool
    is_owner: bool


@dataclass
class Company:
    name: str
    slack_team_id: str
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    deleted: bool = False


@dataclass
class Department:
    name: str
    company: Company
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    deleted: bool = False


@dataclass
class Team:
    name: str
    department: Department
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    deleted: bool = False


@dataclass
class Project:
    name: str
    company: Company
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    deleted: bool = False


@dataclass
class StatusUpdateType:
    name: str
    company: Company
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    deleted: bool = False


@dataclass
class StatusUpdateReaction:
    emoji: str
    name: str
    company: Company
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    deleted: bool = False


@dataclass
class StatusUpdateImage:
    url: str
    filename: str
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = None
    description: str = None


@dataclass
class StatusUpdate:
    text: str
    source: StatusUpdateSource
    company: Company

    type: Optional[StatusUpdateType] = None
    discuss_link: Optional[str] = None

    published: bool = False
    deleted: bool = False

    is_markdown: bool = False
    author_slack_user_id: Optional[str] = None
    author_slack_user_name: Optional[str] = None

    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)

    teams: List[Team] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    images: List[StatusUpdateImage] = field(default_factory=list)


@dataclass
class SlackUserPreferences:
    user_id: str

    active_tab: Optional[str] = None
    active_configuration_tab: Optional[str] = None

    active_team_filter: Optional[Team] = None
    active_department_filter: Optional[Department] = None
    active_project_filter: Optional[Project] = None
