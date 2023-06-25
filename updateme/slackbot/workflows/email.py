from slack_bolt import Ack
from slack_bolt.workflows.step import Configure, Update, Complete, Fail
from slack_sdk import WebClient
from slack_sdk.models.blocks import InputBlock, EmailInputElement, PlainTextObject, StaticMultiSelectElement, Option

from updateme.core import dao
from updateme.slackbot.utils import teams_selector_option_groups


def email_updates_wf_step_edit_handler(ack: Ack, step, configure: Configure):
    ack()

    try:
        initial_email = step["inputs"]["email"]["value"]
    except (KeyError, TypeError):
        initial_email = None

    status_update_types_options = [Option(label=t.name, value=t.uuid)
                                   for t in dao.read_status_update_types()]
    try:
        initial_status_update_types_uuids = step["inputs"]["status_update_types_uuids"]["value"]
        initial_status_update_types = []
        for option in status_update_types_options:
            if option.value in initial_status_update_types_uuids:
                initial_status_update_types.append(option)
    except (KeyError, TypeError):
        initial_status_update_types = None

    team_selector_groups = teams_selector_option_groups(dao.read_teams(), add_department_as_team=True)
    try:
        initial_teams_uuids = step["inputs"]["teams_uuids"]["value"]
        initial_teams = []
        for option_group in team_selector_groups:
            for option in option_group.options:
                if option.value in initial_teams_uuids:
                    initial_teams.append(option)
    except (KeyError, TypeError):
        initial_teams = None

    project_options = [Option(value=project.uuid, label=project.name) for project in dao.read_projects()]
    try:
        initial_projects_uuid = step["inputs"]["projects_uuids"]["value"]
        initial_projects = []
        for option in project_options:
            if option.value in initial_projects_uuid:
                initial_projects.append(option)
    except (KeyError, TypeError):
        initial_projects = None

    configure(blocks=[
        InputBlock(
            block_id="email_input_block",
            label="Email",
            optional=False,
            element=EmailInputElement(
                initial_value=initial_email,
                action_id="email_input_element",
                placeholder=PlainTextObject(text="Add an email")
            )
        ).to_dict(),
        InputBlock(
            block_id="status_update_types_block",
            label="Status update type(s) (optional)",
            optional=True,
            element=StaticMultiSelectElement(
                action_id="status_update_types_action",
                initial_options=initial_status_update_types,
                options=status_update_types_options
            )
        ).to_dict(),
        InputBlock(
            block_id="teams_block",
            label="Team(s) (optional)",
            optional=True,
            element=StaticMultiSelectElement(
                action_id="teams_action",
                initial_options=initial_teams,
                option_groups=team_selector_groups,
            )
        ).to_dict(),
        InputBlock(
            block_id="projects_block",
            label="Project(s) (optional)",
            optional=True,
            element=StaticMultiSelectElement(
                action_id="projects_action",
                initial_options=initial_projects,
                options=project_options
            )
        ).to_dict(),
    ])


def email_updates_wf_step_save_handler(ack: Ack, view: dict, update: Update):
    ack()
    values = view["state"]["values"]
    email = values["email_input_block"]["email_input_element"]["value"]
    status_update_types_uuids = [option["value"] for option in values["status_update_types_block"][
        "status_update_types_action"]["selected_options"]]
    teams_uuids = [option["value"] for option in values["teams_block"]["teams_action"]["selected_options"]]
    projects_uuids = [option["value"] for option in values["projects_block"]["projects_action"]["selected_options"]]

    inputs = {
        "email": {"value": email},
        "status_update_types_uuids": {"value": status_update_types_uuids},
        "teams_uuids": {"value": teams_uuids},
        "projects_uuids": {"value": projects_uuids}
    }
    update(inputs=inputs, outputs=[])


def email_updates_wf_step_execute_handler(step: dict, client: WebClient, complete: Complete, fail: Fail):
    pass
