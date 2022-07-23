import json

from dataclasses import dataclass, asdict
from functools import lru_cache
from typing import List


@dataclass
class Team:
    name: str
    active: bool = True

    def __post_init__(self):
        assert self.name


@dataclass
class Project:
    name: str
    active: bool = True

    def __post_init__(self):
        assert self.name


@dataclass
class StatusUpdateType:
    name: str
    emoji: str
    active: bool = True

    def __post_init__(self):
        assert self.name
        assert self.emoji


@dataclass
class StatusUpdateEmoji:
    emoji: str
    meanings: List[str]
    active: bool = True

    def __post_init__(self):
        assert self.emoji
        assert self.meanings


@dataclass
class StatusUpdate:
    type: str
    emoji: str
    teams: List[str]
    projects: List[str]
    text: str

    def to_text(self) -> str:
        return self.to_json()

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> 'StatusUpdate':
        json_obj = json.loads(json_str)
        return StatusUpdate(
            type=json_obj["type"],
            emoji=json_obj["emoji"],
            teams=json_obj["teams"],
            projects=json_obj["projects"],
            text=json_obj["text"]
        )


class Config:
    TEAMS = [
        Team("Fullstack Team"),
        Team("SDK Team"),
        Team("Frontend Team"),
        Team("Backend Team")
    ]

    PROJECTS = [
        Project("Alpha Project"),
        Project("X-LAB Release"),
        Project("SDK Release 2022")
    ]

    STATUS_UPDATE_EMOJIS = [
        StatusUpdateEmoji("🪪", ["Identification Card", "Document"]),
        StatusUpdateEmoji("🚀", ["Rocket", "Launch"]),
        StatusUpdateEmoji("⚖️", ["Balance Scale", "Decision"]),
        StatusUpdateEmoji("🎆️", ["Fireworks"]),
        StatusUpdateEmoji("🎉", ["Party Popper"]),
        StatusUpdateEmoji("🥳", ["Partying Face"]),
        StatusUpdateEmoji("❓", ["Red Question Mark"]),
        StatusUpdateEmoji("📈", ["Chart Increasing"]),
        StatusUpdateEmoji("📉", ["Chart Decreasing"]),
        StatusUpdateEmoji("🔒", ["Locked"])
    ]

    STATUS_UPDATE_GROUPS = [
        StatusUpdateType("Highlight", "🙂"),
        StatusUpdateType("Lowlight", "🙃"),
        StatusUpdateType("Risk", "❓"),
        StatusUpdateType("Focus", "🎯")
    ]


@lru_cache
def get_config() -> Config:
    return Config()
