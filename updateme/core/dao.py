import os
import sys
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timedelta

from sqlalchemy import create_engine, and_, or_, false, true, desc, Enum
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
from updateme.core.config import INITIAL_TEAM_NAMES, INITIAL_PROJECT_NAMES, INITIAL_STATUS_UPDATE_TYPES, INITIAL_REACTIONS, get_active_dao_type, \
    DaoType


class Dao(ABC):
    @abstractmethod
    def insert_status_update(self, status_update: StatusUpdate): ...

    @abstractmethod
    def publish_status_update(self, company_uuid: str, uuid: str) -> bool: ...

    def read_last_unpublished_status_update(self, company_uuid: str, author_slack_user_id: str,
                                            no_older_than: timedelta = timedelta(days=2),
                                            source: StatusUpdateSource = None) -> Optional[StatusUpdate]:
        updates = self.read_status_updates(
            company_uuid=company_uuid,
            created_after=datetime.utcnow() - no_older_than,
            author_slack_user_id=author_slack_user_id,
            published=False,
            source=source
        )
        if updates:
            return max(updates, key=lambda update: update.created_at)

    @abstractmethod
    def read_status_update(self, company_uuid: str, uuid: str) -> Optional[StatusUpdate]: ...

    @abstractmethod
    def read_status_updates(self, company_uuid: str, created_after: datetime = None, created_before: datetime = None,
                            from_teams: List[str] = None, from_projects: List[str] = None,
                            with_types: List[str] = None, published: Optional[bool] = True,
                            deleted: Optional[bool] = False, author_slack_user_id: str = None,
                            last_n: int = None, source: StatusUpdateSource = None) -> List[StatusUpdate]: ...

    @abstractmethod
    def delete_status_update(self, company_uuid: str, uuid: str): ...

    @abstractmethod
    def delete_team_status_updates(self, company_uuid: str, team_uuid: str): ...

    @abstractmethod
    def insert_team(self, team: Team): ...

    @abstractmethod
    def read_team(self, company_uuid: str, uuid: str) -> Optional[Team]: ...

    @abstractmethod
    def read_teams(self, company_uuid: str, team_name: str = None, department_uuid: str = None) -> List[Team]: ...

    @abstractmethod
    def delete_team(self, company_uuid: str, uuid: str): ...

    @abstractmethod
    def insert_company(self, company: Company): ...

    @abstractmethod
    def read_company(self, uuid: str) -> Optional[Company]: ...

    @abstractmethod
    def read_companies(self, company_name: str = None, slack_team_id: str = None) -> List[Company]: ...

    @abstractmethod
    def insert_department(self, department: Department): ...

    @abstractmethod
    def read_department(self, company_uuid: str, uuid: str) -> Optional[Department]: ...

    @abstractmethod
    def read_departments(self, company_uuid: str, department_name: str = None) -> List[Department]: ...

    @abstractmethod
    def delete_department(self, company_uuid: str, uuid: str): ...

    @abstractmethod
    def insert_project(self, project: Project): ...

    @abstractmethod
    def read_project(self, company_uuid: str, uuid: str) -> Optional[Project]: ...

    @abstractmethod
    def read_projects(self, company_uuid: str, project_name: str = None) -> List[Project]: ...

    @abstractmethod
    def delete_project(self, company_uuid: str, uuid: str): ...

    @abstractmethod
    def insert_status_update_type(self, status_update_type: StatusUpdateType): ...

    @abstractmethod
    def read_status_update_type(self, company_uuid: str, uuid: str) -> Optional[StatusUpdateType]: ...

    @abstractmethod
    def read_status_update_types(self, company_uuid: str, name: str = None) -> List[StatusUpdateType]: ...

    @abstractmethod
    def delete_status_update_type(self, company_uuid: str, uuid: str): ...

    @abstractmethod
    def read_slack_user_preferences(self, user_id: str) -> Optional[SlackUserPreferences]: ...

    @abstractmethod
    def insert_slack_user_preferences(self, slack_user_preferences: SlackUserPreferences): ...

    @abstractmethod
    def insert_status_update_reaction(self, status_update_reaction: StatusUpdateReaction): ...

    @abstractmethod
    def read_status_update_reactions(self, company_uuid: str) -> List[StatusUpdateReaction]: ...


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
            Column("name", String(256), nullable=False),
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
            Column("link", String(1024), nullable=True),
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

    def publish_status_update(self, company_uuid: str, uuid: str) -> bool:
        status_update = self.read_status_update(company_uuid=company_uuid, uuid=uuid)
        if status_update:
            status_update.published = True
            self._set_obj(status_update)
            return True
        else:
            return False

    def read_status_update(self, company_uuid: str, uuid: str) -> Optional[StatusUpdate]:
        status_update: StatusUpdate = self._get_obj(StatusUpdate, uuid)
        if status_update and status_update.company.uuid == company_uuid:
            return status_update

    def read_status_updates(self, company_uuid: str, created_after: datetime = None, created_before: datetime = None,
                            from_teams: List[str] = None, from_departments: List[str] = None,
                            from_projects: List[str] = None, with_types: List[str] = None,
                            published: Optional[bool] = True, deleted: Optional[bool] = False,
                            author_slack_user_id: str = None, last_n: int = None, source: StatusUpdateSource = None) \
            -> List[StatusUpdate]:
        with self._get_session() as session:
            result = session.query(StatusUpdate).join(Company)
            result = result.filter(Company.uuid == company_uuid)

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

            # noinspection PyTypeChecker
            result = result.order_by(desc(StatusUpdate.created_at))

            if last_n is not None:
                result = result.limit(last_n)

            return result.distinct().all()

    def delete_status_update(self, company_uuid: str, uuid: str):
        with self._get_session() as session:
            session.query(StatusUpdate).join(Company).filter(
                and_(StatusUpdate.uuid == uuid, Company.uuid == company_uuid)).update(
            {
                StatusUpdate.deleted: True
            }, synchronize_session=False)

    def delete_team_status_updates(self, company_uuid: str, team_uuid: str):
        with self._get_session() as session:
            session.query(StatusUpdate).join(Company).filter(Company.uuid == company_uuid).filter(
                StatusUpdate.uuid.in_(
                    session.query(StatusUpdate.uuid)
                        .join(self._status_update_teams_association_table).join(Team).filter(Team.uuid == team_uuid)
                )
            ).update({
                StatusUpdate.deleted: True
            }, synchronize_session=False)

    def insert_team(self, team: Team):
        self._set_obj(team)

    def read_team(self, company_uuid: str, uuid: str) -> Optional[Team]:
        team: Team = self._get_obj(Team, uuid)
        if team and team.department.company.uuid == company_uuid:
            return team

    def read_teams(self, company_uuid: str, team_name: str = None, department_uuid: str = None) -> List[Team]:
        with self._get_session() as session:
            result = session.query(Team).join(Department).join(Company)\
                .filter(Team.deleted == false())\
                .filter(Department.deleted == false())\
                .filter(Company.deleted == false())\
                .filter(Company.uuid == company_uuid)
            if team_name is not None:
                result = result.filter(Team.name == team_name)
            if department_uuid is not None:
                result = result.filter(Department.uuid == department_uuid)
            return result.distinct().all()

    def delete_team(self, company_uuid: str, uuid: str):
        with self._get_session() as session:
            session.query(Team).filter(and_(Team.uuid == uuid, Team.uuid.in_(
                session.query(Team.uuid).join(Department).join(Company).filter(Company.uuid == company_uuid)
            ))).update({
                Team.deleted: True
            })

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

    def read_department(self, company_uuid: str, uuid: str) -> Optional[Department]:
        department: Department = self._get_obj(Department, uuid)
        if department and department.company.uuid == company_uuid:
            return department

    def read_departments(self, company_uuid: str, department_name: str = None) -> List[Department]:
        with self._get_session() as session:
            result = session.query(Department).join(Company).filter(Department.deleted == false())\
                .filter(Company.uuid == company_uuid)
            if department_name is not None:
                result = result.filter(Department.name == department_name)
            return result.all()

    def delete_department(self, company_uuid: str, uuid: str):
        with self._get_session() as session:
            session.query(Department).filter(and_(Department.uuid == uuid, Department.uuid.in_(
                    session.query(Department.uuid).join(Company).filter(Company.uuid == company_uuid)
                ))).update({
                    Department.deleted: True
                }, synchronize_session=False)

    def insert_project(self, project: Project):
        self._set_obj(project)

    def read_project(self, company_uuid: str, uuid: str) -> Optional[Project]:
        project: Project = self._get_obj(Project, uuid)
        if project and project.company.uuid == company_uuid:
            return project

    def read_projects(self, company_uuid: str, project_name: str = None) -> List[Project]:
        with self._get_session() as session:
            result = session.query(Project).join(Company).filter(and_(Project.deleted == false(),
                                                                      Company.uuid == company_uuid))
            if project_name is not None:
                result = result.filter(Project.name == project_name)
            return result.all()

    def delete_project(self, company_uuid: str, uuid: str):
        with self._get_session() as session:
            session.query(Project).filter(and_(Project.uuid == uuid, Project.uuid.in_(
                session.query(Project.uuid).join(Company).filter(Company.uuid == company_uuid)
            ))).update({
                Project.deleted: True
            }, synchronize_session=False)

    def insert_status_update_type(self, status_update_type: StatusUpdateType):
        self._set_obj(status_update_type)

    def read_status_update_type(self, company_uuid: str, uuid: str) -> Optional[StatusUpdateType]:
        status_update_type: StatusUpdateType = self._get_obj(StatusUpdateType, uuid)
        if status_update_type and status_update_type.company.uuid == company_uuid:
            return status_update_type

    def read_status_update_types(self, company_uuid: str, name: str = None) -> List[StatusUpdateType]:
        with self._get_session() as session:
            result = session.query(StatusUpdateType).filter(StatusUpdateType.deleted == false())
            result = result.join(Company).filter(Company.uuid == company_uuid)
            if name:
                result = result.filter(StatusUpdateType.name == name)
            return result.all()

    def delete_status_update_type(self, company_uuid: str, uuid: str):
        with self._get_session() as session:
            session.query(StatusUpdateType).filter(and_(StatusUpdateType.uuid == uuid, StatusUpdateType.uuid.in_(
                session.query(StatusUpdateType.uuid).join(Company).filter(Company.uuid == company_uuid)
            ))).update({
                StatusUpdate.deleted: True
            }, synchronize_session=False)


    def read_slack_user_preferences(self, user_id: str) -> Optional[SlackUserPreferences]:
        return self._get_obj(SlackUserPreferences, user_id)

    def insert_slack_user_preferences(self, slack_user_preferences: SlackUserPreferences):
        self._set_obj(slack_user_preferences)

    def insert_status_update_reaction(self, status_update_reaction: StatusUpdateReaction):
        self._set_obj(status_update_reaction)

    def read_status_update_reactions(self, company_uuid: str) -> List[StatusUpdateReaction]:
        with self._get_session() as session:
            return session.query(StatusUpdateReaction).join(Company)\
                .filter(and_(StatusUpdateReaction.deleted == false(),
                             Company.uuid == company_uuid)).all()


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


def create_initial_data(company: Company):
    for department_name, team_names in INITIAL_TEAM_NAMES.items():
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

    existing_project_names = [p.name for p in dao.read_projects(company_uuid=company.uuid)]
    for project_name in set(INITIAL_PROJECT_NAMES):
        if project_name not in existing_project_names:
            dao.insert_project(Project(project_name, company=company))

    existing_status_update_types = dao.read_status_update_types(company_uuid=company.uuid)
    for name in INITIAL_STATUS_UPDATE_TYPES:
        for status_update_type_ in existing_status_update_types:
            if status_update_type_.name == name:
                break
        else:
            new_status_update_type = StatusUpdateType(name=name, company=company)
            dao.insert_status_update_type(new_status_update_type)
            existing_status_update_types.append(new_status_update_type)

    existing_initial_reactions = dao.read_status_update_reactions(company_uuid=company.uuid)
    for name, emoji in INITIAL_REACTIONS:
        for existing_initial_reaction in existing_initial_reactions:
            if existing_initial_reaction.name == name and existing_initial_reaction.emoji == emoji:
                break
        else:
            new_status_update_reaction = StatusUpdateReaction(emoji, name, company=company)
            dao.insert_status_update_reaction(new_status_update_reaction)
            existing_initial_reactions.append(new_status_update_reaction)
