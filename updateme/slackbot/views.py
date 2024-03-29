import json
from collections import defaultdict
from typing import Tuple, Optional, List

from slack_sdk.models.blocks import DividerBlock, SectionBlock, ButtonElement, ActionsBlock, OverflowMenuElement, \
    Option, HeaderBlock, InputBlock, PlainTextInputElement, StaticSelectElement
from slack_sdk.models.views import View

from updateme.slackbot.blocks import status_update_type_block, status_update_teams_block, \
    status_update_projects_block, status_update_text_block, \
    status_update_preview_back_to_editing_block, status_update_list_blocks, home_page_actions_block, \
    home_page_status_update_filters, status_update_blocks, status_update_link_block, \
    home_page_configuration_actions_block
from updateme.core import dao
from updateme.core.model import StatusUpdate, Project, Team, StatusUpdateSource, Department, StatusUpdateType, \
    StatusUpdateReaction
from updateme.slackbot.utils import es, get_or_create_company_by_body

STATUS_UPDATE_TYPE_BLOCK = "status_update_type_block"
STATUS_UPDATE_MODAL_STATUS_UPDATE_TYPE_ACTION_ID = "status_update_modal__status_update_type_action_id"

STATUS_UPDATE_TEAMS_BLOCK = "status_update_team_block"
STATUS_UPDATE_MODAL_STATUS_UPDATE_TEAMS_ACTION_ID = "status_update_modal__status_update_teams_action_id"

STATUS_UPDATE_PROJECTS_BLOCK = "status_update_projects_block"
STATUS_UPDATE_MODAL_STATUS_UPDATE_PROJECTS_ACTION_ID = "status_update_modal__status_update_projects_action_id"

STATUS_UPDATE_LINK_BLOCK = "status_update_link_block"
STATUS_UPDATE_MODAL_STATUS_UPDATE_LINK_ACTION_ID = "status_update_modal__status_update_link_action_id"

STATUS_UPDATE_TEXT_BLOCK = "status_update_text_block"
STATUS_UPDATE_MODAL_STATUS_UPDATE_TEXT_ACTION_ID = "status_update_modal__status_update_text_action_id"


class PrivateMetadata:
    def __init__(self, status_update_uuid: str = None):
        self.status_update_uuid = status_update_uuid

    def __str__(self):
        return self.as_str()

    def as_str(self):
        return json.dumps({
            "status_update_uuid": self.status_update_uuid
        })

    @classmethod
    def from_str(cls, s: str):
        if not s:
            return PrivateMetadata()
        d = json.loads(s)
        return PrivateMetadata(
            status_update_uuid=d.get("status_update_uuid")
        )


def retrieve_private_metadata_from_view(body) -> PrivateMetadata:
    return PrivateMetadata.from_str(body["view"]["private_metadata"])


def retrieve_status_update_from_view(body) -> StatusUpdate:
    values = body["view"]["state"]["values"]
    user_id = body["user"]["id"]
    user_name = body["user"]["name"]
    private_metadata = retrieve_private_metadata_from_view(body)
    company_uuid = get_or_create_company_by_body(body).uuid

    selected_type = values[STATUS_UPDATE_TYPE_BLOCK][STATUS_UPDATE_MODAL_STATUS_UPDATE_TYPE_ACTION_ID][
        "selected_option"]
    if selected_type is not None:
        selected_type = dao.read_status_update_type(company_uuid=company_uuid, uuid=selected_type["value"])

    teams = []
    selected_teams = values[STATUS_UPDATE_TEAMS_BLOCK][STATUS_UPDATE_MODAL_STATUS_UPDATE_TEAMS_ACTION_ID][
        "selected_options"]
    if selected_teams is not None:
        teams = [dao.read_team(company_uuid=company_uuid, uuid=selected_team["value"])
                 for selected_team in selected_teams]

    projects = []
    selected_projects = values[STATUS_UPDATE_PROJECTS_BLOCK][STATUS_UPDATE_MODAL_STATUS_UPDATE_PROJECTS_ACTION_ID][
        "selected_options"]
    if selected_projects is not None:
        projects = [dao.read_project(company_uuid=company_uuid, uuid=selected_project["value"])
                    for selected_project in selected_projects]

    try:
        link = values[STATUS_UPDATE_LINK_BLOCK][
            STATUS_UPDATE_MODAL_STATUS_UPDATE_LINK_ACTION_ID]["value"]
    except (KeyError, TypeError):
        link = None

    kwargs = dict()
    if private_metadata and private_metadata.status_update_uuid:
        kwargs["uuid"] = private_metadata.status_update_uuid

    slack_team_id = body["team"]["id"]
    try:
        company = dao.read_companies(slack_team_id=slack_team_id)[0]
    except IndexError:
        raise IndexError(f"Can not find company with slack_team_id = {slack_team_id}")

    return StatusUpdate(
        type=selected_type,
        source=StatusUpdateSource.SLACK_DIALOG,
        teams=teams,
        projects=projects,
        text=values[STATUS_UPDATE_TEXT_BLOCK][STATUS_UPDATE_MODAL_STATUS_UPDATE_TEXT_ACTION_ID]["value"],
        link=link,
        author_slack_user_id=user_id,
        author_slack_user_name=user_name,
        company=company,
        **kwargs
    )


def retrieve_status_update_filters_from_view(body) -> Tuple[Optional[Team], Optional[Department], Optional[Project]]:
    values = body["view"]["state"]["values"]["status_updates_filter_block"]
    company_uuid = get_or_create_company_by_body(body).uuid

    team, department, project = None, None, None

    try:
        team_or_department_id = values["home_page_select_team_filter_changed"]["selected_option"]["value"]
        team = dao.read_team(company_uuid=company_uuid, uuid=team_or_department_id)
        if team is None:
            department = dao.read_department(company_uuid=company_uuid, uuid=team_or_department_id)
    except KeyError:
        pass

    try:
        project_id = values["home_page_select_project_filter_changed"]["selected_option"]["value"]
        project = dao.read_project(company_uuid=company_uuid, uuid=project_id)
    except KeyError:
        pass

    return team, department, project


def status_update_dialog_view(status_update_types: List[StatusUpdateType], teams: List[Team], projects: List[Project],
                              state: StatusUpdate = None) -> View:
    return View(
        type="modal",
        callback_id="status_update_preview_button_clicked",
        title="Share Status Update" if state and not state.published else "Update Status Update",
        submit="Preview" if state and not state.published else "Save",
        close="Cancel",
        private_metadata=str(PrivateMetadata(status_update_uuid=None if state is None else state.uuid)),
        blocks=[
            status_update_type_block(status_update_types,
                                     selected_value=None if state is None or state.type is None else state.type,
                                     block_id=STATUS_UPDATE_TYPE_BLOCK,
                                     action_id=STATUS_UPDATE_MODAL_STATUS_UPDATE_TYPE_ACTION_ID),
            DividerBlock(),
            status_update_teams_block(teams,
                                      selected_options=None if state is None else [team for team in state.teams],
                                      block_id=STATUS_UPDATE_TEAMS_BLOCK,
                                      action_id=STATUS_UPDATE_MODAL_STATUS_UPDATE_TEAMS_ACTION_ID),
            status_update_projects_block(projects,
                                         selected_options=None if state is None
                                         else [project for project in state.projects],
                                         block_id=STATUS_UPDATE_PROJECTS_BLOCK,
                                         action_id=STATUS_UPDATE_MODAL_STATUS_UPDATE_PROJECTS_ACTION_ID),
            status_update_link_block(initial_value=None if state is None else state.link,
                                     block_id=STATUS_UPDATE_LINK_BLOCK,
                                     action_id=STATUS_UPDATE_MODAL_STATUS_UPDATE_LINK_ACTION_ID),
            status_update_text_block(initial_value=None if state is None else state.text,
                                     block_id=STATUS_UPDATE_TEXT_BLOCK,
                                     action_id=STATUS_UPDATE_MODAL_STATUS_UPDATE_TEXT_ACTION_ID),
        ]
    )


def share_status_update_preview_view(update: StatusUpdate) -> View:
    return View(
        type="modal",
        callback_id="status_update_preview_share_button_clicked",
        title="Preview Status Update",
        submit="Share",
        close="Cancel",
        private_metadata=str(PrivateMetadata(status_update_uuid=update.uuid)),
        blocks=[
            DividerBlock(),
            *status_update_blocks(update, display_edit_buttons=False),
            DividerBlock(),
            status_update_preview_back_to_editing_block(),
        ]
    )


def home_page_my_updates_view(status_updates: List[StatusUpdate], status_update_reactions: List[StatusUpdateReaction],
                              is_admin: bool = False, current_user_slack_id: str = None):
    return View(
        type="home",
        title="Welcome to Chirik Bot!",
        blocks=[
            home_page_actions_block(selected="my_updates", show_configuration=is_admin),
            DividerBlock(),
            *status_update_list_blocks(status_updates,
                                       status_update_reactions,
                                       current_user_slack_id=current_user_slack_id,
                                       accessory_action_id="my_updates_status_message_menu_button_clicked")
        ]
    )


def home_page_my_updates_delete_status_update_view(status_update_uuid: str, status_update_text: str):
    return View(
        type="modal",
        callback_id="home_page_my_updates_delete_status_update_dialog_submitted",
        title="Delete status update?",
        submit="Delete",
        close="Cancel",
        private_metadata=status_update_uuid,
        blocks=[
            SectionBlock(
                text="Are you sure you want to delete status update: " + es(status_update_text) + "?"
            ),
        ]
    )



def home_page_company_updates_view(status_updates: List[StatusUpdate],
                                   status_update_reactions: List[StatusUpdateReaction], teams: List[Team],
                                   projects: List[Project], team: Team = None, department: Department = None,
                                   project: Project = None,
                                   is_admin: bool = False, current_user_slack_id: str = None):
    return View(
        type="home",
        title="Welcome to Chirik Bot!",
        blocks=[
            home_page_actions_block(selected="company_updates", show_configuration=is_admin),
            DividerBlock(),
            home_page_status_update_filters(
                teams=teams,
                projects=projects,
                active_team=team,
                active_department=department,
                active_project=project
            ),
            DividerBlock(),
            *status_update_list_blocks(status_updates,
                                       status_update_reactions,
                                       current_user_slack_id=current_user_slack_id,
                                       accessory_action_id="company_updates_status_message_menu_button_clicked")
        ]
    )


def home_page_company_updates_delete_status_update_view(status_update_uuid: str, status_update_text: str):
    return View(
        type="modal",
        callback_id="home_page_company_updates_delete_status_update_dialog_submitted",
        title="Delete status update?",
        submit="Delete",
        close="Cancel",
        private_metadata=status_update_uuid,
        blocks=[
            SectionBlock(
                text="Are you sure you want to delete status update: " + es(status_update_text) + "?"
            ),
        ]
    )



def home_page_configuration_departments_view(departments: List[Department]):
    department_blocks = [
        SectionBlock(
            text=department.name,
            accessory=OverflowMenuElement(action_id="configuration_department_menu_clicked",
            options=[
                Option(value="edit_" + department.uuid, text="Edit..."),
                Option(value="delete_" + department.uuid, text="Delete..."),
            ])
        ) for department in sorted(departments, key=lambda d: str(d.name).lower())
    ]

    return View(
        type="home",
        title="Welcome to Chirik Bot!",
        blocks=[
            home_page_actions_block(selected="configuration", show_configuration=True),
            DividerBlock(),
            home_page_configuration_actions_block(),
            DividerBlock(),
            *department_blocks,
            ActionsBlock(elements=[
                ButtonElement(
                    text="Add new department...",
                    action_id="configuration_add_new_department_clicked"
                )
            ])
        ]
    )


def home_page_configuration_add_new_department_view(department_name: str = None, department_uuid: str = None):
    return View(
        type="modal",
        callback_id="home_page_configuration_new_department_dialog_submitted",
        title="Add new department" if department_uuid is None else "Edit department",
        submit="Add" if department_uuid is None else "Save",
        close="Cancel",
        private_metadata=department_uuid,
        blocks=[
            InputBlock(
                block_id="home_page_configuration_new_department_dialog_input_block",
                label="Department name",
                optional=False,
                element=PlainTextInputElement(
                    action_id="home_page_configuration_new_department_dialog_input_action",
                    placeholder="Department name",
                    max_length=64,
                    focus_on_load=True,
                    initial_value=department_name
                )
            )
        ]
    )


def home_page_configuration_delete_department_view(department_name: str = None, department_uuid: str = None):
    return View(
        type="modal",
        callback_id="home_page_configuration_delete_dialog_submitted",
        title="Delete department?",
        submit="Delete",
        close="Cancel",
        private_metadata=department_uuid,
        blocks=[
            SectionBlock(
                text="Are you sure you want to delete department " + es(department_name) +
                     "? All teams from this department will be also deleted."
            ),
        ]
    )


def home_page_configuration_teams_view(teams: List[Team]):
    teams_blocks = [
    ]

    teams_dict = defaultdict(list)
    for team in sorted(teams, key=lambda t: t.name.lower()):
        teams_dict[team.department.name].append(team)

    for department_name in sorted(teams_dict.keys(), key=lambda dn: dn.lower()):
        teams_blocks.append(
            HeaderBlock(text=department_name)
        )
        for team in teams_dict[department_name]:
            teams_blocks.append(
                SectionBlock(
                    text=team.name,
                    accessory=OverflowMenuElement(action_id="configuration_team_menu_clicked", options=[
                        Option(value="edit_" + team.uuid, text="Edit..."),
                        Option(value="delete_" + team.uuid, text="Delete..."),
                    ])
                )
            )
        teams_blocks.append(DividerBlock())

    return View(
        type="home",
        title="Welcome to Chirik Bot!",
        blocks=[
            home_page_actions_block(selected="configuration", show_configuration=True),
            DividerBlock(),
            home_page_configuration_actions_block(selected="teams"),
            DividerBlock(),
            *teams_blocks,
            ActionsBlock(elements=[
                ButtonElement(
                    text="Add new team...",
                    action_id="configuration_add_new_team_clicked"
                )
            ])
        ]
    )

def home_page_configuration_add_new_team_view(departments: List[Department], team_name: str = None,
                                              team_uuid: str = None, department_uuid: str = None):
    initial_department_option = None
    for department in departments:
        if department.uuid == department_uuid:
            initial_department_option = Option(
                value=department.uuid,
                label=department.name,
                text=department.name
            )

    return View(
        type="modal",
        callback_id="home_page_configuration_new_team_dialog_submitted",
        title="Add new team" if not team_uuid else "Edit team",
        submit="Add" if not team_uuid else "Save",
        close="Cancel",
        private_metadata=team_uuid,
        blocks=[
            InputBlock(
                block_id="home_page_configuration_new_team_dialog_input_block",
                label="Team name",
                optional=False,
                element=PlainTextInputElement(
                    action_id="home_page_configuration_new_team_dialog_input_action",
                    placeholder="Team name",
                    max_length=64,
                    focus_on_load=True,
                    initial_value=team_name
                )
            ),
            InputBlock(
                block_id="home_page_configuration_new_team_dialog_input_department_block",
                label="Department",
                optional=False,
                element=StaticSelectElement(
                    action_id="home_page_configuration_new_team_dialog_input_department_action",
                    initial_option=initial_department_option,
                    options=[
                        Option(
                            value=department.uuid,
                            label=department.name,
                            text=department.name
                        ) for department in sorted(departments, key=lambda d: str(d.name).lower())
                    ]
                )
            )
        ]
    )

def home_page_configuration_delete_team_view(team_name: str, team_uuid: str):
    return View(
        type="modal",
        callback_id="home_page_configuration_delete_team_dialog_submitted",
        title="Delete team?",
        submit="Delete",
        close="Cancel",
        private_metadata=team_uuid,
        blocks=[
            SectionBlock(
                text="Are you sure you want to delete team " + es(team_name) + "?"
            ),
        ]
    )


def home_page_configuration_projects_view(projects: List[Project]):
    projects_blocks = []

    for project in sorted(projects, key=lambda p: str(p.name).lower()):
        projects_blocks.append(
            SectionBlock(
                text=project.name,
                accessory=OverflowMenuElement(action_id="configuration_project_menu_clicked", options=[
                    Option(value="edit_" + project.uuid, text="Edit..."),
                    Option(value="delete_" + project.uuid, text="Delete..."),
                ])
            )
        )

    return View(
        type="home",
        title="Welcome to Chirik Bot!",
        blocks=[
            home_page_actions_block(selected="configuration", show_configuration=True),
            DividerBlock(),
            home_page_configuration_actions_block(selected="projects"),
            DividerBlock(),
            *projects_blocks,
            ActionsBlock(elements=[
                ButtonElement(
                    text="Add new project...",
                    action_id="configuration_add_new_project_clicked"
                )
            ])
        ]
    )

def home_page_configuration_add_new_project_view(project_name: str = None, project_uuid: str = None):
    return View(
        type="modal",
        callback_id="home_page_configuration_new_project_dialog_submitted",
        title="Add new project" if project_uuid is None else "Edit project",
        submit="Add" if project_uuid is None else "Save",
        close="Cancel",
        private_metadata=project_uuid,
        blocks=[
            InputBlock(
                block_id="home_page_configuration_new_project_dialog_input_block",
                label="Project name",
                optional=False,
                element=PlainTextInputElement(
                    action_id="home_page_configuration_new_project_dialog_input_action",
                    placeholder="Project name",
                    max_length=64,
                    focus_on_load=True,
                    initial_value=project_name
                )
            )
        ]
    )


def home_page_configuration_delete_project_view(project_name: str, project_uuid: str):
    return View(
        type="modal",
        callback_id="home_page_configuration_delete_project_dialog_submitted",
        title="Delete project?",
        submit="Delete",
        close="Cancel",
        private_metadata=project_uuid,
        blocks=[
            SectionBlock(
                text="Are you sure you want to delete project " + es(project_name) + "?"
            ),
        ]
    )


def home_page_configuration_status_types_view(status_types: List[StatusUpdateType]):
    status_types_blocks = []

    for status_type in sorted(status_types, key=lambda p: str(p.name).lower()):
        status_types_blocks.append(
            SectionBlock(
                text=status_type.name,
                accessory=OverflowMenuElement(action_id="configuration_status_type_menu_clicked", options=[
                    Option(value="edit_" + status_type.uuid, text="Edit..."),
                    Option(value="delete_" + status_type.uuid, text="Delete..."),
                ])
            )
        )

    return View(
        type="home",
        title="Welcome to Chirik Bot!",
        blocks=[
            home_page_actions_block(selected="configuration", show_configuration=True),
            DividerBlock(),
            home_page_configuration_actions_block(selected="status_types"),
            DividerBlock(),
            *status_types_blocks,
            ActionsBlock(elements=[
                ButtonElement(
                    text="Add new status type...",
                    action_id="configuration_add_new_status_type_clicked"
                )
            ])
        ]
    )



def home_page_configuration_add_new_status_update_type_view(status_update_type_name: str = None,
                                                            status_update_type_uuid: str = None):
    return View(
        type="modal",
        callback_id="home_page_configuration_new_status_update_type_dialog_submitted",
        title="Add status update type" if status_update_type_uuid is None else "Edit status update type",
        submit="Add" if status_update_type_uuid is None else "Save",
        close="Cancel",
        private_metadata=status_update_type_uuid,
        blocks=[
            InputBlock(
                block_id="home_page_configuration_new_status_update_type_dialog_name_input_block",
                label="Status update name",
                optional=False,
                element=PlainTextInputElement(
                    action_id="home_page_configuration_new_status_update_type_dialog_name_input_action",
                    placeholder="Status update name",
                    max_length=64,
                    focus_on_load=True,
                    initial_value=status_update_type_name
                )
            )
        ]
    )


def home_page_configuration_delete_status_update_type_view(status_update_type_name: str, status_update_type_uuid: str):
    return View(
        type="modal",
        callback_id="home_page_configuration_delete_status_update_type_dialog_submitted",
        title="Delete status type?",
        submit="Delete",
        close="Cancel",
        private_metadata=status_update_type_uuid,
        blocks=[
            SectionBlock(
                text="Are you sure you want to delete status update type "
                     + es(status_update_type_name) + "?"
            ),
        ]
    )
