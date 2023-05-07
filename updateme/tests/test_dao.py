import pytest
import string

from random import choices

from updateme.core import dao
from updateme.core.model import Project, Team, StatusUpdate, StatusUpdateSource, Department, Company


@pytest.fixture
def non_existing_project(existing_company) -> Project:
    project = Project("test_project_" + "".join(choices(string.ascii_letters, k=16)), company=existing_company)
    for p_ in dao.read_projects():
        if p_.uuid == project.uuid:
            raise AssertionError("Can not create non-existing project")
    yield project


@pytest.fixture
def existing_project(non_existing_project) -> Project:
    dao.insert_project(non_existing_project)
    for p_ in dao.read_projects():
        if p_.uuid == non_existing_project.uuid:
            break
    else:
        raise AssertionError("Can not create existing project")
    yield non_existing_project


@pytest.fixture
def non_existing_company_slack_team_id() -> str:
    slack_team_id = "test_slack_team_id_" + "".join(choices(string.ascii_letters, k=16))
    if dao.read_companies(slack_team_id=slack_team_id):
        raise AssertionError("Can not create non-existing test_slack_team_id")
    yield slack_team_id


@pytest.fixture
def non_existing_company(non_existing_company_slack_team_id) -> Team:
    company = Company("test_company_" + "".join(choices(string.ascii_letters, k=16)),
                      slack_team_id=non_existing_company_slack_team_id)
    for c_ in dao.read_companies():
        if c_.uuid == company.uuid:
            raise AssertionError("Can not create non-existing company")
    yield company


@pytest.fixture
def existing_company(non_existing_company) -> Company:
    dao.insert_company(non_existing_company)
    for d_ in dao.read_companies():
        if d_.uuid == non_existing_company.uuid:
            break
    else:
        raise AssertionError("Can not create existing company")
    yield non_existing_company


@pytest.fixture
def non_existing_department(existing_company) -> Team:
    department = Department("test_department_" + "".join(choices(string.ascii_letters, k=16)), company=existing_company)
    for d_ in dao.read_departments():
        if d_.uuid == department.uuid:
            raise AssertionError("Can not create non-existing department")
    yield department


@pytest.fixture
def existing_department(non_existing_department) -> Department:
    dao.insert_department(non_existing_department)
    for d_ in dao.read_departments():
        if d_.uuid == non_existing_department.uuid:
            break
    else:
        raise AssertionError("Can not create existing department")
    yield non_existing_department


@pytest.fixture
def non_existing_team(existing_department) -> Team:
    team = Team("test_team_" + "".join(choices(string.ascii_letters, k=16)), department=existing_department)
    for t_ in dao.read_teams():
        if t_.uuid == team.uuid:
            raise AssertionError("Can not create non-existing team")
    yield team


@pytest.fixture
def existing_team(non_existing_team) -> Team:
    dao.insert_team(non_existing_team)
    for t_ in dao.read_teams():
        if t_.uuid == non_existing_team.uuid:
            break
    else:
        raise AssertionError("Can not create existing team")
    yield non_existing_team


def test_project_insertion(non_existing_project):
    dao.insert_project(non_existing_project)
    assert non_existing_project.uuid in sorted([p_.uuid for p_ in dao.read_projects()])


def test_team_insertion(non_existing_team):
    dao.insert_team(non_existing_team)
    assert non_existing_team.uuid in sorted([t_.uuid for t_ in dao.read_teams()])


def test_status_update_insertion(existing_company):
    status_update = StatusUpdate(
        source=StatusUpdateSource.SLACK_DIALOG,
        text="Some Text",
        type=dao.read_status_update_types()[0],
        company=existing_company
    )
    dao.insert_status_update(status_update)
    assert status_update.uuid not in [su.uuid for su in dao.read_status_updates()]
    assert status_update.uuid not in [su.uuid for su in dao.read_status_updates(published=True)]
    assert status_update.uuid in [su.uuid for su in dao.read_status_updates(published=None)]
    assert status_update.uuid in [su.uuid for su in dao.read_status_updates(published=False)]
