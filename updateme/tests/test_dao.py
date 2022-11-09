import pytest
import string

from random import choices

from updateme.core import dao
from updateme.core.model import Project, Team, StatusUpdate


@pytest.fixture
def non_existing_project() -> Project:
    project = Project("test_project_" + "".join(choices(string.ascii_letters, k=16)))
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
def non_existing_team() -> Team:
    team = Team("test_team_" + "".join(choices(string.ascii_letters, k=16)))
    for t_ in dao.read_teams():
        if t_.uuid == team.uuid:
            raise AssertionError("Can not create non-existing team")
    yield team


@pytest.fixture
def existing_team(non_existing_team) -> Project:
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


def test_status_update_insertion():
    status_update = StatusUpdate(
        emoji=dao.read_status_update_emojis()[0],
        text="Some Text",
        type=dao.read_status_update_types()[0]
    )
    dao.insert_status_update(status_update)
    assert status_update.uuid in [su.uuid for su in dao.read_status_updates()]
