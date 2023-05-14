import os
import sys
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timedelta

from sqlalchemy import create_engine, or_, false, true, desc, Enum
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import Table
from sqlalchemy.engine import Engine
from sqlalchemy.orm import registry, sessionmaker, Session
from sqlalchemy.orm import relationship
from typing import List, Optional, Generator

from sqlalchemy.pool import NullPool

from updateme.core.model import Company, Project, StatusUpdate, StatusUpdateType, Team, SlackUserPreferences, \
    StatusUpdateImage, StatusUpdateSource, StatusUpdateReaction, Department
from updateme.core.config import TEAM_NAMES, PROJECT_NAMES, STATUS_UPDATE_TYPES, REACTIONS, get_active_dao_type, \
    DaoType


class Dao(ABC):
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
    def delete_status_update(self, uuid: str): ...

    @abstractmethod
    def delete_team_status_updates(self, team_uuid: str): ...

    @abstractmethod
    def insert_team(self, team: Team): ...

    @abstractmethod
    def read_team(self, uuid: str) -> Optional[Team]: ...

    @abstractmethod
    def read_teams(self, team_name: str = None, department_uuid: str = None) -> List[Team]: ...

    @abstractmethod
    def delete_team(self, uuid: str): ...

    @abstractmethod
    def insert_company(self, company: Company): ...

    @abstractmethod
    def read_company(self, uuid: str) -> Optional[Company]: ...

    @abstractmethod
    def read_companies(self, company_name: str = None, slack_team_id: str = None) -> List[Company]: ...

    @abstractmethod
    def insert_department(self, department: Department): ...

    @abstractmethod
    def read_department(self, uuid: str) -> Optional[Department]: ...

    @abstractmethod
    def read_departments(self, department_name: str = None) -> List[Department]: ...

    @abstractmethod
    def delete_department(self, uuid: str): ...

    @abstractmethod
    def insert_project(self, project: Project): ...

    @abstractmethod
    def read_project(self, uuid: str) -> Optional[Project]: ...

    @abstractmethod
    def read_projects(self, project_name: str = None) -> List[Project]: ...

    @abstractmethod
    def delete_project(self, uuid: str): ...

    @abstractmethod
    def insert_status_update_type(self, status_update_type: StatusUpdateType): ...

    @abstractmethod
    def read_status_update_type(self, uuid: str) -> Optional[StatusUpdateType]: ...

    @abstractmethod
    def read_status_update_types(self) -> List[StatusUpdateType]: ...

    @abstractmethod
    def delete_status_update_type(self, uuid: str): ...

    @abstractmethod
    def read_slack_user_preferences(self, user_id: str) -> Optional[SlackUserPreferences]: ...

    @abstractmethod
    def insert_slack_user_preferences(self, slack_user_preferences: SlackUserPreferences): ...

    @abstractmethod
    def insert_status_update_reaction(self, status_update_reaction: StatusUpdateReaction): ...

    @abstractmethod
    def read_status_update_reactions(self) -> List[StatusUpdateReaction]: ...


class SQLAlchemyDao(Dao, ABC):
    _COMPANIES_TABLE = "companies"
    _TEAMS_TABLE = "teams"
    _DEPARTMENTS_TABLE = "departments"
    _STATUS_UPDATES_TABLE = "status_updates"
    _PROJECTS_TABLE = "projects"
    _STATUS_UPDATE_TYPES_TABLE = "status_update_types"
    _STATUS_UPDATE_REACTIONS_TABLE = "status_update_reactions"
    _STATUS_UPDATE_IMAGES_TABLE = "status_update_images"
    _SLACK_USER_PREFERENCES_TABLE = "slack_user_preferences"

    @abstractmethod
    def _create_engine(self) -> Engine: ...

    def __init__(self):
        self._mapper_registry = registry()
        self._metadata_obj = MetaData()

        self._companies_table = Table(
            self._COMPANIES_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("slack_team_id", String(256), nullable=False, unique=True, index=True),
        )

        self._departments_table = Table(
            self._DEPARTMENTS_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("name", String(256), nullable=False),
            Column("company_uuid", String(256), ForeignKey(f"{self._COMPANIES_TABLE}.uuid"), nullable=False,
                   index=True),
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
            Column("company_uuid", String(256), ForeignKey(f"{self._COMPANIES_TABLE}.uuid"), nullable=False),
            Column("name", String(256), nullable=False),
            Column("deleted", Boolean, nullable=False),
        )

        self._status_update_types_table = Table(
            self._STATUS_UPDATE_TYPES_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("name", String(256), nullable=False),
            Column("company_uuid", String(256), ForeignKey(f"{self._COMPANIES_TABLE}.uuid"), nullable=False),
            Column("emoji", String(256)),
            Column("deleted", Boolean, nullable=False),
        )

        self._status_update_reactions_table = Table(
            self._STATUS_UPDATE_REACTIONS_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("company_uuid", String(256), ForeignKey(f"{self._COMPANIES_TABLE}.uuid"), nullable=False),
            Column("emoji", String(256), nullable=False),
            Column("name", String(256), nullable=False),
            Column("deleted", Boolean, nullable=False),
        )

        self._status_update_table = Table(
            self._STATUS_UPDATES_TABLE,
            self._metadata_obj,
            Column("uuid", String(256), primary_key=True, nullable=False),
            Column("company_uuid", String(256), ForeignKey(f"{self._COMPANIES_TABLE}.uuid"), nullable=False),
            Column("source", Enum(StatusUpdateSource), nullable=False),
            Column("discuss_link", String(1024), nullable=True),
            Column("published", Boolean, nullable=False),
            Column("deleted", Boolean, nullable=False),
            Column("text", Text, nullable=False),
            Column("is_markdown", Boolean, nullable=False),
            Column("author_slack_user_id", String(256), nullable=True),
            Column("author_slack_user_name", String(256), nullable=True),
            Column("created_at", DateTime, nullable=False),
            Column("status_update_type_uuid", String(256), ForeignKey(f"{self._STATUS_UPDATE_TYPES_TABLE}.uuid")),
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
            Column("active_configuration_tab", String(256), nullable=True),
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

        self._mapper_registry.map_imperatively(Company, self._companies_table)
        self._mapper_registry.map_imperatively(Department, self._departments_table, properties={
            "company": relationship(Company)
        })
        self._mapper_registry.map_imperatively(Team, self._teams_table, properties={
            "department": relationship(Department),
            "company": relationship(Company, secondary=self._departments_table)
        })
        self._mapper_registry.map_imperatively(Project, self._projects_table, properties={
            "company": relationship(Company)
        })
        self._mapper_registry.map_imperatively(StatusUpdateType, self._status_update_types_table, properties={
            "company": relationship(Company)
        })
        self._mapper_registry.map_imperatively(StatusUpdateReaction, self._status_update_reactions_table, properties={
            "company": relationship(Company)
        })

        self._mapper_registry.map_imperatively(
            StatusUpdate,
            self._status_update_table,
            properties={
                "company": relationship(Company),
                "type": relationship(StatusUpdateType),
                "projects": relationship(Project, secondary=self._status_update_projects_association_table,
                                         order_by=self._projects_table.c.name),
                "teams": relationship(Team, secondary=self._status_update_teams_association_table,
                                      order_by=self._teams_table.c.name),
                "images": relationship(StatusUpdateImage)
            }
        )

        self._mapper_registry.map_imperatively(StatusUpdateImage, self._status_update_images_table, properties={
            "company": relationship(Company, secondary=self._status_update_table)
        })

        self._mapper_registry.map_imperatively(
            SlackUserPreferences,
            self._slack_user_preferences_table,
            properties={
                "active_team_filter": relationship(Team),
                "active_department_filter": relationship(Department),
                "active_project_filter": relationship(Project)
            }
        )

        self._engine = self._create_engine()
        self._metadata_obj.create_all(bind=self._engine, checkfirst=True)
        self._session_maker = sessionmaker(bind=self._engine)
        self._session = self._session_maker()

    @contextmanager
    def _get_session(self) -> Generator[Session, None, None]:
        """
        with self._session_maker() as session:
            yield session
            session.commit()
        """
        yield self._session
        self._session.commit()

    def _get_obj(self, cls, uuid):
        with self._get_session() as session:
            return session.get(cls, uuid)

    def _set_obj(self, obj):
        with self._get_session() as session:
            session.merge(obj, load=True)

    def insert_status_update(self, status_update: StatusUpdate):
        self._set_obj(status_update)

    def publish_status_update(self, uuid: str) -> bool:
        status_update = self.read_status_update(uuid)
        if status_update:
            status_update.published = True
            self._set_obj(status_update)
            return True
        else:
            return False

    def read_status_update(self, uuid: str) -> Optional[StatusUpdate]:
        return self._get_obj(StatusUpdate, uuid)

    def read_status_updates(self, created_after: datetime = None, created_before: datetime = None,
                            from_teams: List[str] = None, from_departments: List[str] = None,
                            from_projects: List[str] = None, with_types: List[str] = None,
                            published: Optional[bool] = True, deleted: Optional[bool] = False,
                            author_slack_user_id: str = None, last_n: int = None, source: StatusUpdateSource = None) \
            -> List[StatusUpdate]:
        with self._get_session() as session:
            result = session.query(StatusUpdate)

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

            if with_types:
                result = result.filter(or_(StatusUpdate.type == type_ for type_ in with_types))

            if deleted is not None:
                result = result.filter(StatusUpdate.deleted == (true() if deleted else false()))

            if published is not None:
                result = result.filter(StatusUpdate.published == (true() if published else false()))

            if author_slack_user_id is not None:
                result = result.filter(StatusUpdate.author_slack_user_id == author_slack_user_id)

            if source is not None:
                result = result.filter(StatusUpdate.source == source)

            result = result.order_by(desc(StatusUpdate.created_at))

            if last_n is not None:
                result = result.limit(last_n)

            return result.distinct().all()

    def delete_status_update(self, uuid: str):
        with self._get_session() as session:
            session.query(StatusUpdate).filter(StatusUpdate.uuid == uuid).update({
                StatusUpdate.deleted: True
            }, synchronize_session=False)

    def delete_team_status_updates(self, team_uuid: str):
        with self._get_session() as session:
            session.query(StatusUpdate).filter(
                StatusUpdate.uuid.in_(
                    session.query(StatusUpdate.uuid)
                        .join(self._status_update_teams_association_table).join(Team).filter(Team.uuid == team_uuid)
                )
            ).update({
                StatusUpdate.deleted: True
            }, synchronize_session=False)

    def insert_team(self, team: Team):
        self._set_obj(team)

    def read_team(self, uuid: str) -> Optional[Team]:
        return self._get_obj(Team, uuid)

    def read_teams(self, team_name: str = None, department_uuid: str = None) -> List[Team]:
        with self._get_session() as session:
            result = session.query(Team).filter(Team.deleted == false())
            if team_name is not None:
                result = result.filter(Team.name == team_name)
            if department_uuid is not None:
                result = result.join(Department).filter(Department.uuid == department_uuid)
            return result.distinct().all()

    def delete_team(self, uuid: str):
        with self._get_session() as session:
            session.query(Team).filter(Team.uuid == uuid).update({
                Team.deleted: True
            }, synchronize_session=False)

    def insert_company(self, company: Company):
        self._set_obj(company)

    def read_company(self, uuid: str) -> Optional[Company]:
        return self._get_obj(Company, uuid)

    def read_companies(self, company_name: str = None, slack_team_id: str = None) -> List[Company]:
        with self._get_session() as session:
            result = session.query(Company).filter(Company.deleted == false())
            if company_name is not None:
                result = result.filter(Company.name == company_name)
            if slack_team_id is not None:
                result = result.filter(Company.slack_team_id == slack_team_id)
            return result.all()

    def insert_department(self, department: Department):
        self._set_obj(department)

    def read_department(self, uuid: str) -> Optional[Department]:
        return self._get_obj(Department, uuid)

    def read_departments(self, department_name: str = None) -> List[Department]:
        with self._get_session() as session:
            result = session.query(Department).filter(Department.deleted == false())
            if department_name is not None:
                result = result.filter(Department.name == department_name)
            return result.all()

    def delete_department(self, uuid: str):
        with self._get_session() as session:
            session.query(Department).filter(Department.uuid == uuid).update({
                Department.deleted: True
            }, synchronize_session=False)

    def insert_project(self, project: Project):
        self._set_obj(project)

    def read_project(self, uuid: str) -> Optional[Project]:
        return self._get_obj(Project, uuid)

    def read_projects(self, project_name: str = None) -> List[Project]:
        with self._get_session() as session:
            result = session.query(Project).filter(Project.deleted == false())
            if project_name is not None:
                result = result.filter(Project.name == project_name)
            return result.all()

    def delete_project(self, uuid: str):
        with self._get_session() as session:
            session.query(Project).filter(Project.uuid == uuid).update({
                Project.deleted: True
            }, synchronize_session=False)

    def insert_status_update_type(self, status_update_type: StatusUpdateType):
        self._set_obj(status_update_type)

    def read_status_update_type(self, uuid: str) -> Optional[StatusUpdateType]:
        return self._get_obj(StatusUpdateType, uuid)

    def read_status_update_types(self, name: str = None) -> List[StatusUpdateType]:
        with self._get_session() as session:
            result = session.query(StatusUpdateType).filter(StatusUpdateType.deleted == false())
            if name:
                result = result.filter(StatusUpdateType.name == name)
            return result.all()

    def delete_status_update_type(self, uuid: str):
        with self._get_session() as session:
            session.query(StatusUpdateType).filter(StatusUpdateType.uuid == uuid).update({
                StatusUpdateType.deleted: True
            }, synchronize_session=False)


    def read_slack_user_preferences(self, user_id: str) -> Optional[SlackUserPreferences]:
        return self._get_obj(SlackUserPreferences, user_id)

    def insert_slack_user_preferences(self, slack_user_preferences: SlackUserPreferences):
        self._set_obj(slack_user_preferences)

    def insert_status_update_reaction(self, status_update_reaction: StatusUpdateReaction):
        self._set_obj(status_update_reaction)

    def read_status_update_reactions(self) -> List[StatusUpdateReaction]:
        with self._get_session() as session:
            return session.query(StatusUpdateReaction).filter(StatusUpdateReaction.deleted == false()).all()


class SQLiteDao(SQLAlchemyDao):
    _DB_FILENAME = "update_me.db"
    _DB_PYTEST_FILENAME = "pytest_update_me.db"

    @property
    def _db_folder(self):
        return os.path.join(os.path.dirname(__file__), "..", "..", "db")

    @property
    def _db_file(self):
        filename = self._DB_FILENAME if "pytest" not in sys.modules else self._DB_PYTEST_FILENAME
        return os.path.join(self._db_folder, filename)

    def _create_engine(self) -> Engine:
        if not os.path.isdir(self._db_folder):
            os.mkdir(self._db_folder)
        return create_engine(f"sqlite:///{self._db_file}", echo=False, poolclass=NullPool)


class PostgresDao(SQLAlchemyDao):
    CONN_PYTEST_STRING = "postgresql://localhost:5432/shareit_test"
    CONN_STRING = "postgresql://localhost:5432/shareit_prod"

    def _create_engine(self) -> Engine:
        conn_string = self.CONN_STRING if "pytest" not in sys.modules else self.CONN_PYTEST_STRING
        print(conn_string)
        return create_engine(conn_string)


if get_active_dao_type() == DaoType.POSTGRES:
    dao = PostgresDao()
elif get_active_dao_type() == DaoType.SQLITE:
    dao = SQLiteDao()
else:
    raise TypeError(f"DAO {get_active_dao_type().name} is not supported")


def create_initial_data():
    company = Company("Test Company", "test_slack_id")

    for department_name, team_names in TEAM_NAMES.items():
        departments = dao.read_departments(department_name)
        if departments:
            department = departments[0]
        else:
            department = Department(name=department_name, company=company)
            dao.insert_department(department)

        for team_name in team_names:
            for team in dao.read_teams(team_name):
                if team.department.uuid == department.uuid:
                    break
            else:
                team = Team(team_name, department)
                dao.insert_team(team)

    existing_project_names = [p.name for p in dao.read_projects()]
    for project_name in set(PROJECT_NAMES):
        if project_name not in existing_project_names:
            dao.insert_project(Project(project_name, company=company))

    existing_status_update_types = dao.read_status_update_types()
    for name, emoji in STATUS_UPDATE_TYPES:
        for status_update_type_ in existing_status_update_types:
            if status_update_type_.name == name and status_update_type_.emoji == emoji:
                break
        else:
            new_status_update_type = StatusUpdateType(name, emoji, company=company)
            dao.insert_status_update_type(new_status_update_type)
            existing_status_update_types.append(new_status_update_type)

    existing_initial_reactions = dao.read_status_update_reactions()
    for name, emoji in REACTIONS:
        for existing_initial_reaction in existing_initial_reactions:
            if existing_initial_reaction.name == name and existing_initial_reaction.emoji == emoji:
                break
        else:
            new_status_update_reaction = StatusUpdateReaction(emoji, name, company=company)
            dao.insert_status_update_reaction(new_status_update_reaction)
            existing_initial_reactions.append(new_status_update_reaction)


# create_initial_data()
