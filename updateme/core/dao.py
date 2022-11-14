import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from sqlalchemy import create_engine, or_, false, true, desc, Enum
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

from sqlalchemy.pool import NullPool

from updateme.core.model import Project, StatusUpdate, StatusUpdateType, Team, StatusUpdateEmoji, \
    SlackUserPreferences, StatusUpdateImage, StatusUpdateSource, StatusUpdateReaction, Department
from updateme.core.config import INITIAL_TEAM_NAMES, INITIAL_PROJECT_NAMES, INITIAL_STATUS_UPDATE_EMOJIS, \
    INITIAL_STATUS_UPDATE_TYPES, INITIAL_REACTIONS


class Dao(ABC):
    @property
    @abstractmethod
    def first_start(self) -> bool: ...

    @abstractmethod
    def insert_status_update(self, status_update: StatusUpdate): ...

    @abstractmethod
    def publish_status_update(self, uuid: str) -> bool: ...

    def read_last_unpublished_status_update(self, author_slack_user_id: str,
                                            no_older_than: timedelta = timedelta(days=2),
                                            source: StatusUpdateSource = None) -> Optional[StatusUpdate]:
        updates = self.read_status_updates(
            created_after=datetime.utcnow() - no_older_than,
            author_slack_user_id=author_slack_user_id,
            published=False,
            source=source
        )
        if updates:
            return max(updates, key=lambda update: update.created_at)

    @abstractmethod
    def read_status_update(self, uuid: str) -> Optional[StatusUpdate]: ...

    @abstractmethod
    def read_status_updates(self, created_after: datetime = None, created_before: datetime = None,
                            from_teams: List[str] = None, from_projects: List[str] = None,
                            with_types: List[str] = None, published: Optional[bool] = True,
                            deleted: Optional[bool] = False, author_slack_user_id: str = None,
                            last_n: int = None, source: StatusUpdateSource = None) -> List[StatusUpdate]: ...

    @abstractmethod
    def insert_team(self, team: Team): ...

    @abstractmethod
    def read_team(self, uuid: str) -> Optional[Team]: ...

    @abstractmethod
    def read_teams(self) -> List[Team]: ...

    @abstractmethod
    def insert_department(self, department: Department): ...

    @abstractmethod
    def read_department(self, uuid: str) -> Optional[Department]: ...

    @abstractmethod
    def read_departments(self) -> List[Department]: ...

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

    @abstractmethod
    def read_slack_user_preferences(self, user_id: str) -> Optional[SlackUserPreferences]: ...

    @abstractmethod
    def insert_slack_user_preferences(self, slack_user_preferences: SlackUserPreferences): ...

    @abstractmethod
    def insert_status_update_reaction(self, status_update_reaction: StatusUpdateReaction): ...

    @abstractmethod
    def read_status_update_reactions(self) -> List[StatusUpdateReaction]: ...


class SQLAlchemyDao(Dao, ABC):
    _TEAMS_TABLE = "teams"
    _DEPARTMENTS_TABLE = "departments"
    _STATUS_UPDATES_TABLE = "status_updates"
    _PROJECTS_TABLE = "projects"
    _STATUS_UPDATE_TYPES_TABLE = "status_update_types"
    _STATUS_UPDATE_EMOJIS_TABLE = "status_update_emojis"
    _STATUS_UPDATE_REACTIONS_TABLE = "status_update_reactions"
    _STATUS_UPDATE_IMAGES_TABLE = "status_update_images"
    _SLACK_USER_PREFERENCES_TABLE = "slack_user_preferences"

    @abstractmethod
    def _create_engine(self) -> Engine: ...

    @property
    def first_start(self) -> bool:
        return self._first_start

    def __init__(self):
        self._engine = self._create_engine()
        self._mapper_registry = registry()
        self._metadata_obj = MetaData(bind=self._engine)
        self._first_start = False

        self._departments_table = Table(
            self._DEPARTMENTS_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("name", String(256), nullable=False),
            Column("deleted", Boolean, nullable=False),
        )

        self._teams_table = Table(
            self._TEAMS_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("name", String(256), nullable=False),
            Column("department_uuid", String(256), ForeignKey(f"{self._DEPARTMENTS_TABLE}.uuid"), nullable=False),
            Column("deleted", Boolean, nullable=False),
        )

        self._projects_table = Table(
            self._PROJECTS_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("name", String(256), nullable=False),
            Column("deleted", Boolean, nullable=False),
        )

        self._status_update_types_table = Table(
            self._STATUS_UPDATE_TYPES_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("name", String(256), nullable=False),
            Column("emoji", String(256)),
            Column("deleted", Boolean, nullable=False),
        )

        self._status_update_emojis_table = Table(
            self._STATUS_UPDATE_EMOJIS_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("emoji", String(256), nullable=False),
            Column("meaning", String(256), nullable=False),
            Column("deleted", Boolean, nullable=False),
        )

        self._status_update_reactions_table = Table(
            self._STATUS_UPDATE_REACTIONS_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("emoji", String(256), nullable=False),
            Column("name", String(256), nullable=False),
            Column("deleted", Boolean, nullable=False),
        )

        self._status_update_table = Table(
            self._STATUS_UPDATES_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("source", Enum(StatusUpdateSource), nullable=False),
            Column("published", Boolean, nullable=False),
            Column("deleted", Boolean, nullable=False),
            Column("text", Text, nullable=False),
            Column("is_markdown", Boolean, nullable=False),
            Column("author_slack_user_id", String(256), nullable=True),
            Column("author_slack_user_name", String(256), nullable=True),
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

        self._slack_user_preferences_table = Table(
            self._SLACK_USER_PREFERENCES_TABLE,
            self._metadata_obj,
            Column("user_id", String(256), primary_key=True, nullable=False),
            Column("active_tab", String(256), nullable=True),
            Column("active_team_filter__team_uuid", String(256), ForeignKey(f"{self._TEAMS_TABLE}.uuid"),
                   nullable=True),
            Column("active_department_filter__department_uuid", String(256),
                   ForeignKey(f"{self._DEPARTMENTS_TABLE}.uuid"), nullable=True),
            Column("active_project_filter__project_uuid", String(256), ForeignKey(f"{self._PROJECTS_TABLE}.uuid"),
                   nullable=True),
        )

        self._status_update_images_table = Table(
            self._STATUS_UPDATE_IMAGES_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("status_update_uuid", String(256), ForeignKey(f"{self._STATUS_UPDATES_TABLE}.uuid"), nullable=False),
            Column("url", String(1024), nullable=False),
            Column("filename", String(1024), nullable=False),
            Column("title", String(1024), nullable=True),
            Column("description", String(1024), nullable=True),
        )

        self._mapper_registry.map_imperatively(Department, self._departments_table)
        self._mapper_registry.map_imperatively(Team, self._teams_table, properties={
            "department": relationship(Department)
        })
        self._mapper_registry.map_imperatively(Project, self._projects_table)
        self._mapper_registry.map_imperatively(StatusUpdateType, self._status_update_types_table)
        self._mapper_registry.map_imperatively(StatusUpdateEmoji, self._status_update_emojis_table)
        self._mapper_registry.map_imperatively(StatusUpdateReaction, self._status_update_reactions_table)
        self._mapper_registry.map_imperatively(StatusUpdateImage, self._status_update_images_table)

        self._mapper_registry.map_imperatively(
            StatusUpdate,
            self._status_update_table,
            properties={
                "type": relationship(StatusUpdateType),
                "emoji": relationship(StatusUpdateEmoji),
                "projects": relationship(Project, secondary=self._status_update_projects_association_table,
                                         order_by=self._projects_table.c.name),
                "teams": relationship(Team, secondary=self._status_update_teams_association_table,
                                      order_by=self._teams_table.c.name),
                "images": relationship(StatusUpdateImage)
            }
        )

        self._mapper_registry.map_imperatively(
            SlackUserPreferences,
            self._slack_user_preferences_table,
            properties={
                "active_team_filter": relationship(Team),
                "active_department_filter": relationship(Department),
                "active_project_filter": relationship(Project)
            }
        )

        self._first_start = not inspect(self._engine).has_table(self._status_update_table.name)
        self._metadata_obj.create_all(checkfirst=True)
        self._session = sessionmaker(bind=self._engine)()

    def _merge_and_commit(self, obj):
        # self._session.add(obj)
        self._session.merge(obj, load=True)
        self._session.commit()

    def insert_status_update(self, status_update: StatusUpdate):
        self._merge_and_commit(status_update)

    def publish_status_update(self, uuid: str) -> bool:
        status_update = self.read_status_update(uuid)
        if status_update:
            status_update.published = True
            self._session.commit()
            return True
        else:
            return False

    def read_status_update(self, uuid: str) -> Optional[StatusUpdate]:
        return self._session.get(StatusUpdate, uuid)

    def read_status_updates(self, created_after: datetime = None, created_before: datetime = None,
                            from_teams: List[str] = None, from_departments: List[str] = None,
                            from_projects: List[str] = None, with_types: List[str] = None,
                            published: Optional[bool] = True, deleted: Optional[bool] = False,
                            author_slack_user_id: str = None, last_n: int = None, source: StatusUpdateSource = None) \
            -> List[StatusUpdate]:
        result = self._session.query(StatusUpdate)

        if created_after:
            result = result.filter(StatusUpdate.created_at >= created_after)

        if created_before:
            result = result.filter(StatusUpdate.created_at <= created_before)

        if from_teams:
            result = result.join(self._status_update_teams_association_table)
            result = result.join(Team)
            result = result.filter(or_(Team.uuid == team for team in from_teams))

        if from_departments:
            result = result.join(self._status_update_teams_association_table)
            result = result.join(Team)
            result = result.join(Department)
            result = result.filter(or_(Department.uuid == department for department in from_departments))

        if from_projects:
            result = result.join(self._status_update_projects_association_table)
            result = result.join(Project)
            result = result.filter(or_(Project.uuid == project for project in from_projects))

        if deleted is not None:
            result = result.filter(StatusUpdate.deleted == (true() if deleted else false()))

        if published is not None:
            result = result.filter(StatusUpdate.published == (true() if published else false()))

        if author_slack_user_id is not None:
            result = result.filter(StatusUpdate.author_slack_user_id == author_slack_user_id)

        if source is not None:
            result = result.filter(StatusUpdate.source == source)

        if last_n is not None:
            result = result.order_by(desc(StatusUpdate.created_at)).limit(last_n)

        return result.distinct().all()

    def insert_team(self, team: Team):
        self._merge_and_commit(team)

    def read_team(self, uuid: str) -> Optional[Team]:
        return self._session.get(Team, uuid)

    def read_teams(self) -> List[Team]:
        return self._session.query(Team).filter(Team.deleted == false()).all()

    def insert_department(self, department: Department):
        self._merge_and_commit(department)

    def read_department(self, uuid: str) -> Optional[Department]:
        return self._session.get(Department, uuid)

    def read_departments(self) -> List[Department]:
        return self._session.query(Department).filter(Department.deleted == false()).all()

    def insert_project(self, project: Project):
        self._merge_and_commit(project)

    def read_project(self, uuid: str) -> Optional[Project]:
        return self._session.get(Project, uuid)

    def read_projects(self) -> List[Project]:
        return self._session.query(Project).filter(Project.deleted == false()).all()

    def insert_status_update_type(self, status_update_type: StatusUpdateType):
        self._merge_and_commit(status_update_type)

    def read_status_update_type(self, uuid: str) -> Optional[StatusUpdateType]:
        return self._session.get(StatusUpdateType, uuid)

    def read_status_update_types(self) -> List[StatusUpdateType]:
        return self._session.query(StatusUpdateType).filter(StatusUpdateType.deleted == false()).all()

    def insert_status_update_emoji(self, status_update_emoji: StatusUpdateEmoji):
        self._merge_and_commit(status_update_emoji)

    def read_status_update_emoji(self, uuid: str) -> Optional[StatusUpdateEmoji]:
        return self._session.get(StatusUpdateEmoji, uuid)

    def read_status_update_emojis(self) -> List[StatusUpdateEmoji]:
        return self._session.query(StatusUpdateEmoji).filter(StatusUpdateEmoji.deleted == false()).all()

    def read_slack_user_preferences(self, user_id: str) -> Optional[SlackUserPreferences]:
        return self._session.get(SlackUserPreferences, user_id)

    def insert_slack_user_preferences(self, slack_user_preferences: SlackUserPreferences):
        self._merge_and_commit(slack_user_preferences)

    def insert_status_update_reaction(self, status_update_reaction: StatusUpdateReaction):
        self._merge_and_commit(status_update_reaction)

    def read_status_update_reactions(self) -> List[StatusUpdateReaction]:
        return self._session.query(StatusUpdateReaction).filter(StatusUpdateReaction.deleted == false()).all()


class SQLiteInMemoryDao(SQLAlchemyDao):
    def _create_engine(self) -> Engine:
        return create_engine("sqlite:///:memory:", echo=True)


class SQLiteDao(SQLAlchemyDao):
    _DB_FILENAME = "update_me.db"
    _DB_PYTEST_FILENAME = "pytest_update_me.db"

    @property
    def db_folder(self):
        return os.path.join(os.path.dirname(__file__), "..", "..", "db")

    @property
    def db_file(self):
        filename = self._DB_FILENAME if "pytest" not in sys.modules else self._DB_PYTEST_FILENAME
        return os.path.join(self.db_folder, filename)

    def _create_engine(self) -> Engine:
        if not os.path.isdir(self.db_folder):
            os.mkdir(self.db_folder)
        return create_engine(f"sqlite:///{self.db_file}", echo=False, poolclass=NullPool)


dao = SQLiteDao()

if dao.first_start:
    for department_name, team_names in INITIAL_TEAM_NAMES.items():
        department_ = Department(department_name)
        dao.insert_department(department_)
        for team_name in team_names:
            dao.insert_team(Team(team_name, department_))

    for project_name in INITIAL_PROJECT_NAMES:
        dao.insert_project(Project(project_name))

    for emoji, meaning in INITIAL_STATUS_UPDATE_EMOJIS:
        dao.insert_status_update_emoji(StatusUpdateEmoji(emoji, meaning))

    for name, emoji in INITIAL_STATUS_UPDATE_TYPES:
        dao.insert_status_update_type(StatusUpdateType(name, emoji))

    for name, emoji in INITIAL_REACTIONS:
        dao.insert_status_update_reaction(StatusUpdateReaction(emoji, name))
