from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from sqlalchemy import create_engine, or_
from sqlalchemy import inspect
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import Table
from sqlalchemy.engine import Engine
from sqlalchemy.orm import registry, sessionmaker
from sqlalchemy.orm import relationship
from typing import List, Optional

from model import Project, StatusUpdate, StatusUpdateType, Team, StatusUpdateEmoji
from slackbot.config import INITIAL_TEAM_NAMES, INITIAL_PROJECT_NAMES, INITIAL_STATUS_UPDATE_EMOJIS, \
    INITIAL_STATUS_UPDATE_TYPES


class Dao(ABC):
    @property
    @abstractmethod
    def cold_start(self) -> bool: ...

    @abstractmethod
    def insert_status_update(self, status_update: StatusUpdate, replace: bool = False): ...

    def replace_status_update(self, status_update: StatusUpdate):
        self.insert_status_update(status_update, replace=True)

    @abstractmethod
    def read_status_update(self, uuid: str) -> Optional[StatusUpdate]: ...

    @abstractmethod
    def read_status_updates(self, created_after: datetime = None, created_before: datetime = None,
                            from_teams: List[str] = None, from_projects: List[str] = None,
                            with_types: List[str] = None): ...

    @abstractmethod
    def insert_team(self, team: Team): ...

    @abstractmethod
    def read_team(self, uuid: str) -> Optional[Team]: ...

    @abstractmethod
    def read_teams(self) -> List[Team]: ...

    @abstractmethod
    def insert_project(self, project: Project): ...

    @abstractmethod
    def read_project(self, uuid: str) -> Optional[Project]: ...

    @abstractmethod
    def read_projects(self) -> List[Project]: ...

    @abstractmethod
    def insert_status_update_type(self, status_update_type: StatusUpdateType): ...

    @abstractmethod
    def read_status_update_type(self, uuid: str) -> Optional[StatusUpdateType]: ...

    @abstractmethod
    def read_status_update_types(self) -> List[StatusUpdateType]: ...

    @abstractmethod
    def insert_status_update_emoji(self, status_update_emoji: StatusUpdateEmoji): ...

    @abstractmethod
    def read_status_update_emoji(self, uuid: str) -> Optional[StatusUpdateEmoji]: ...

    @abstractmethod
    def read_status_update_emojis(self) -> List[StatusUpdateEmoji]: ...


class SQLAlchemyDao(Dao, ABC):
    _TEAMS_TABLE = "teams"
    _STATUS_UPDATES_TABLE = "status_updates"
    _PROJECTS_TABLE = "projects"
    _STATUS_UPDATE_TYPES_TABLE = "status_update_types"
    _STATUS_UPDATE_EMOJIS_TABLE = "status_update_emojis"

    @abstractmethod
    def _create_engine(self) -> Engine: ...

    @property
    def cold_start(self) -> bool:
        return self._cold_start

    def __init__(self):
        self._engine = self._create_engine()
        self._mapper_registry = registry()
        self._metadata_obj = MetaData(bind=self._engine)
        self._cold_start = False

        self._teams_table = Table(
            self._TEAMS_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("name", String(256), nullable=False),
            Column("active", Boolean, nullable=False),
        )

        self._projects_table = Table(
            self._PROJECTS_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("name", String(256), nullable=False),
            Column("active", Boolean, nullable=False),
        )

        self._status_update_types_table = Table(
            self._STATUS_UPDATE_TYPES_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("name", String(256), nullable=False),
            Column("emoji", String(256)),
            Column("active", Boolean, nullable=False),
        )

        self._status_update_emojis_table = Table(
            self._STATUS_UPDATE_EMOJIS_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("emoji", String(256), nullable=False),
            Column("meaning", String(256), nullable=False),
            Column("active", Boolean, nullable=False),
        )

        self._status_update_table = Table(
            self._STATUS_UPDATES_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("published", Boolean, nullable=False),
            Column("text", Text, nullable=False),
            Column("created_at", DateTime, nullable=False),
            Column("status_update_type_uuid", String(256), ForeignKey(f"{self._STATUS_UPDATE_TYPES_TABLE}.uuid")),
            Column("status_update_emoji_uuid", String(256), ForeignKey(f"{self._STATUS_UPDATE_EMOJIS_TABLE}.uuid")),
        )

        self._status_update_projects_association_table = Table(
            "status_update_projects_association",
            self._metadata_obj,
            Column("status_update_uuid", ForeignKey(f"{self._STATUS_UPDATES_TABLE}.uuid")),
            Column("project_uuid", ForeignKey(f"{self._PROJECTS_TABLE}.uuid")),
        )

        self._status_update_teams_association_table = Table(
            "status_update_teams_association",
            self._metadata_obj,
            Column("status_update_uuid", ForeignKey(f"{self._STATUS_UPDATES_TABLE}.uuid")),
            Column("team_uuid", ForeignKey(f"{self._TEAMS_TABLE}.uuid")),
        )

        self._mapper_registry.map_imperatively(Team, self._teams_table)
        self._mapper_registry.map_imperatively(Project, self._projects_table)
        self._mapper_registry.map_imperatively(StatusUpdateType, self._status_update_types_table)
        self._mapper_registry.map_imperatively(StatusUpdateEmoji, self._status_update_emojis_table)

        self._mapper_registry.map_imperatively(
            StatusUpdate,
            self._status_update_table,
            properties={
                "type": relationship(StatusUpdateType),
                "emoji": relationship(StatusUpdateEmoji),
                "projects": relationship(Project, secondary=self._status_update_projects_association_table,
                                         order_by=self._projects_table.c.name),
                "teams": relationship(Team, secondary=self._status_update_teams_association_table,
                                      order_by=self._teams_table.c.name)
            }
        )

        self._cold_start = not inspect(self._engine).has_table(self._status_update_table.name)
        self._metadata_obj.create_all(checkfirst=True)
        self._session = sessionmaker(bind=self._engine)()

    def _add_and_commit(self, obj):
        self._session.add(obj)
        self._session.commit()

    def insert_status_update(self, status_update: StatusUpdate, replace: bool = False):
        self._add_and_commit(status_update)

    def read_status_update(self, uuid: str) -> Optional[StatusUpdate]:
        return self._session.get(StatusUpdate, uuid)

    def read_status_updates(self, created_after: datetime = None, created_before: datetime = None,
                            from_teams: List[str] = None, from_projects: List[str] = None,
                            with_types: List[str] = None) -> List[StatusUpdate]:
        result = self._session.query(StatusUpdate)

        if created_after:
            result = result.filter(StatusUpdate.created_at >= created_after)

        if created_before:
            result = result.filter(StatusUpdate.created_at <= created_before)

        if from_teams:
            result = result.join(self._status_update_teams_association_table)
            result = result.join(Team)
            result = result.filter(or_(Team.name == team for team in from_teams))

        if from_projects:
            result = result.join(self._status_update_projects_association_table)
            result = result.join(Project)
            result = result.filter(or_(Project.name == project for project in from_projects))

        return result.distinct().all()

    def insert_team(self, team: Team):
        self._add_and_commit(team)

    def read_team(self, uuid: str) -> Optional[Team]:
        return self._session.get(Team, uuid)

    def read_teams(self) -> List[Team]:
        return self._session.query(Team).all()

    def insert_project(self, project: Project):
        self._add_and_commit(project)

    def read_project(self, uuid: str) -> Optional[Project]:
        return self._session.get(Project, uuid)

    def read_projects(self) -> List[Project]:
        return self._session.query(Project).all()

    def insert_status_update_type(self, status_update_type: StatusUpdateType):
        self._add_and_commit(status_update_type)

    def read_status_update_type(self, uuid: str) -> Optional[StatusUpdateType]:
        return self._session.get(StatusUpdateType, uuid)

    def read_status_update_types(self) -> List[StatusUpdateType]:
        return self._session.query(StatusUpdateType).all()

    def insert_status_update_emoji(self, status_update_emoji: StatusUpdateEmoji):
        self._add_and_commit(status_update_emoji)

    def read_status_update_emoji(self, uuid: str) -> Optional[StatusUpdateEmoji]:
        return self._session.get(StatusUpdateEmoji, uuid)

    def read_status_update_emojis(self) -> List[StatusUpdateEmoji]:
        return self._session.query(StatusUpdateEmoji).all()


class SQLiteInMemoryDao(SQLAlchemyDao):
    def _create_engine(self) -> Engine:
        return create_engine("sqlite:///:memory:", echo=True)


class SQLiteDao(SQLAlchemyDao):
    _DB_FILENAME = "update_me.db"

    def _create_engine(self) -> Engine:
        return create_engine(f"sqlite:///{self._DB_FILENAME}", echo=False)


dao = SQLiteDao()

if dao.cold_start:
    for team_name in INITIAL_TEAM_NAMES:
        dao.insert_team(Team(team_name))

    for project_name in INITIAL_PROJECT_NAMES:
        dao.insert_project(Project(project_name))

    for emoji, meaning in INITIAL_STATUS_UPDATE_EMOJIS:
        dao.insert_status_update_emoji(StatusUpdateEmoji(emoji, meaning))

    for name, emoji in INITIAL_STATUS_UPDATE_TYPES:
        dao.insert_status_update_type(StatusUpdateType(name, emoji))


if __name__ == "__main__":
    # Just a simple test
    a = SQLiteInMemoryDao()
    sut = StatusUpdateType("111", "11")
    sue = StatusUpdateEmoji("111", "222")
    su = StatusUpdate(
        sut,
        emoji=sue,
        text="sfsfdf",
        projects=[Project("Test Project1")],
        teams=[Team("Test team 1"), Team("Test team 2")]
    )
    a.insert_status_update(su)
    print(a.read_status_updates(
        created_after=datetime.utcnow() - timedelta(hours=1),
        created_before=datetime.utcnow() + timedelta(hours=1),
        from_teams=["Test team 2", "Test team 1", "Unknown team"],
        from_projects=["Test Project1"]
    ))
    print(a.read_status_update(su.uuid))
