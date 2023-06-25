import itertools
from threading import Lock
from typing import List, Callable, Optional

from slack_sdk.models.blocks import OptionGroup, Option

from updateme.core import dao
from updateme.core.dao import create_initial_data
from updateme.core.model import SlackUserPreferences, Team, Company
from updateme.core.utils import join_strings_with_commas


CREATE_COMPANY_LOCK = Lock()


def escape_string(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


es = escape_string


def join_names_with_commas(names: List[str], bold: bool = False) -> str:
    if bold:
        names = ["*" + es(name) + "*" for name in names]
    else:
        names = [es(name) for name in names]

    return join_strings_with_commas(names)


def get_or_create_slack_user_preferences(user_id: str) -> SlackUserPreferences:
    user_preferences = dao.read_slack_user_preferences(user_id)
    if user_preferences is None:
        user_preferences = SlackUserPreferences(user_id, "company_updates")
        dao.insert_slack_user_preferences(user_preferences)

    return user_preferences


def get_or_create_company_by_body(body) -> Company:
    try:
        slack_team_id = body["team"]["id"]
    except KeyError:
        slack_team_id = body["team_id"]
    companies = dao.read_companies(slack_team_id=slack_team_id)
    try:
        return companies[0]
    except IndexError:
        with CREATE_COMPANY_LOCK:
            try:
                return dao.read_companies(slack_team_id=body["team"]["id"])[0]
            except IndexError:
                company = Company(slack_team_id=body["team"]["id"], name=body["team"]["domain"])
                dao.insert_company(company)
                create_initial_data(company)
                if not company.name and body["team"]["domain"]:
                    # It could be that the company was created in the get_or_create_company_by_event function, where
                    # we didn't know the company name
                    company.name = body["team"]["domain"]
                return company


def get_or_create_company_by_event(event) -> Optional[Company]:
    try:
        companies = dao.read_companies(slack_team_id=event["view"]["team_id"])
    except KeyError:
        return None

    try:
        return companies[0]
    except IndexError:
        with CREATE_COMPANY_LOCK:
            try:
                return dao.read_companies(slack_team_id=event["view"]["team_id"])[0]
            except IndexError:
                company = Company(slack_team_id=event["view"]["team_id"], name="")
                # dao.insert_company(Company(slack_team_id=event["view"]["team_id"], name=""))
                create_initial_data(company)
                return company


def teams_selector_option_groups(teams: List[Team], add_department_as_team: bool = False,
                                 all_teams_value: str = None, all_teams_label: str = "All teams",
                                 entire_department_name_callback: Callable[[str], str] = None) -> List[OptionGroup]:
    result = []

    if all_teams_value and all_teams_label:
        result.append(OptionGroup(label=all_teams_label,
                                  options=[Option(label=all_teams_label, value=all_teams_value)]))

    for _, _g_teams in itertools.groupby(
            sorted(teams, key=lambda t: str(t.department.name).lower()), key=lambda team_: team_.department.uuid):
        grouped_teams = list(_g_teams)
        department = grouped_teams[0].department
        department_as_team = []
        if add_department_as_team:
            if entire_department_name_callback:
                department_as_team_name = entire_department_name_callback(department.name)
            else:
                department_as_team_name = f"Entire {department.name}"
            department_as_team = [Option(label=department_as_team_name, value=department.uuid)]
        result.append(OptionGroup(
            label=department.name,
            options=department_as_team + [Option(label=team.name, value=team.uuid)
                                          for team in sorted(grouped_teams, key=lambda t: str(t.name).lower())]
        ))

    return result
