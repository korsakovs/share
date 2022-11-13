import itertools
from typing import List, Callable

from slack_sdk.models.blocks import OptionGroup, Option

from updateme.core import dao
from updateme.core.model import SlackUserPreferences, Team


def escape_string(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


es = escape_string


def join_names_with_commas(names: List[str], bold: bool = False) -> str:
    if bold:
        names = ["*" + es(name) + "*" for name in names]
    else:
        names = [es(name) for name in names]

    if not names:
        return ""

    if len(names) == 1:
        return names[0]

    result = ", ".join(names[:-1])
    if len(names) > 2:
        result += ","
    result += " and " + names[-1]

    return result


def get_or_create_slack_user_preferences(user_id: str) -> SlackUserPreferences:
    user_preferences = dao.read_slack_user_preferences(user_id)
    if user_preferences is None:
        user_preferences = SlackUserPreferences(user_id, "company_updates")
        dao.insert_slack_user_preferences(user_preferences)

    return user_preferences


def teams_selector_option_groups(teams: List[Team], add_department_as_team: bool = False,
                                 all_teams_value: str = None, all_teams_label: str = "All teams",
                                 entire_department_name_callback: Callable[[str], str] = None) -> List[OptionGroup]:
    result = []

    if all_teams_value and all_teams_label:
        result.append(OptionGroup(label="All teams", options=[Option(label=all_teams_label, value=all_teams_value)]))

    for _, _g_teams in itertools.groupby(teams, key=lambda team_: (team_.department.name, team_.department.uuid)):
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
                                          for team in sorted(grouped_teams, key=lambda t: t.name)]
        ))

    return result
