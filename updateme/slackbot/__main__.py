import logging

from typing import Optional

from cachetools import cached, TTLCache
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.workflows.step import WorkflowStep
from slack_sdk import WebClient
from slack_sdk.models.metadata import Metadata

from updateme.core import dao
from updateme.core.config import slack_bot_token, slack_app_token, get_env, Env
from updateme.core.model import StatusUpdateSource, StatusUpdate, SlackUserInfo, Department, Team, Project
from updateme.slackbot.messages import status_update_preview_message, status_update_from_message
from updateme.slackbot.utils import get_or_create_slack_user_preferences
from updateme.slackbot.views import status_update_dialog_view, retrieve_status_update_from_view, \
    share_status_update_preview_view, STATUS_UPDATE_MODAL_STATUS_UPDATE_TYPE_ACTION_ID, \
    STATUS_UPDATE_MODAL_STATUS_UPDATE_TEAMS_ACTION_ID, \
    STATUS_UPDATE_MODAL_STATUS_UPDATE_PROJECTS_ACTION_ID, retrieve_private_metadata_from_view, \
    home_page_my_updates_view, home_page_company_updates_view, retrieve_status_update_filters_from_view, \
    home_page_configuration_departments_view, home_page_configuration_teams_view, \
    home_page_configuration_add_new_department_view, home_page_configuration_delete_department_view, \
    home_page_configuration_add_new_team_view, home_page_configuration_delete_team_view, \
    home_page_configuration_projects_view, home_page_configuration_add_new_project_view, \
    home_page_configuration_delete_project_view
from updateme.slackbot.workflows.email import email_updates_wf_step_edit_handler, email_updates_wf_step_save_handler, \
    email_updates_wf_step_execute_handler
from updateme.slackbot.workflows.publish import publish_updates_wf_step_edit_handler, \
    publish_updates_wf_step_save_handler, publish_updates_wf_step_execute_handler
from updateme.slackbot.workflows.remider import reminder_wf_step_edit_handler, reminder_wf_step_save_handler, \
    reminder_wf_step_execute_handler

logging.basicConfig(level=logging.DEBUG if get_env() == Env.DEV else logging.INFO,
                    format="%(asctime)s %(levelname)s %(module)s - %(thread)d - %(message)s")
app = App(token=slack_bot_token())


@cached(cache=TTLCache(maxsize=1024 * 20, ttl=60 * 60))
def get_user_info(slack_user_id: str) -> Optional[SlackUserInfo]:
    user = app.client.users_info(user=slack_user_id)
    profile = user.data["user"]["profile"]

    name = None

    try:
        name = profile["display_name"]
    except (KeyError, TypeError):
        try:
            name = profile["real_name"]
        except (KeyError, TypeError):
            pass

    if name is None:
        return None

    return SlackUserInfo(
        name=name,
        is_admin=user.data["user"]["is_admin"],
        is_owner=user.data["user"]["is_owner"]
    )


@app.action(STATUS_UPDATE_MODAL_STATUS_UPDATE_TYPE_ACTION_ID)
def status_update_modal_status_type_action_handler(ack):
    ack()


@app.action(STATUS_UPDATE_MODAL_STATUS_UPDATE_TEAMS_ACTION_ID)
def status_update_modal_status_teams_action_handler(ack):
    ack()


@app.action(STATUS_UPDATE_MODAL_STATUS_UPDATE_PROJECTS_ACTION_ID)
def status_update_modal_status_projects_action_handler(ack):
    ack()


@app.event("app_home_opened")
def home_page_open_handler(client: WebClient, event, logger):
    user_id = event["user"]
    user_preferences = get_or_create_slack_user_preferences(user_id)
    user_info = get_user_info(user_id)
    is_admin = user_info and (user_info.is_admin or user_info.is_owner)

    if user_preferences.active_tab == "my_updates":
        view = home_page_my_updates_view(user_id, is_admin=is_admin, current_user_slack_id=user_id)
    elif user_preferences.active_tab == "company_updates":
        view = home_page_company_updates_view(
            team=user_preferences.active_team_filter,
            department=user_preferences.active_department_filter,
            project=user_preferences.active_project_filter,
            is_admin=is_admin,
            current_user_slack_id=user_id
        )
    else:
        view = home_page_configuration_departments_view(
            departments=dao.read_departments()
        )

    try:
        client.views_publish(
            user_id=user_id,
            view=view
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("home_page_my_updates_button_clicked")
def home_page_my_updates_button_click_handler(ack, body, logger):
    ack()
    logger.info(body)
    user_id = body["user"]["id"]
    user_preferences = get_or_create_slack_user_preferences(user_id)
    user_preferences.active_tab = "my_updates"
    dao.insert_slack_user_preferences(user_preferences)
    user_info = get_user_info(user_id)
    is_admin = user_info and (user_info.is_admin or user_info.is_owner)
    try:
        app.client.views_publish(
            user_id=user_id,
            view=home_page_my_updates_view(user_id, is_admin=is_admin, current_user_slack_id=user_id)
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("my_updates_status_message_menu_button_clicked")
def my_updates_status_message_menu_button_clicked_handler(ack, body, logger):
    ack()
    logger.info(body)

    selected_option_value = str(body["actions"][0]["selected_option"]["value"])

    if selected_option_value.startswith("edit_"):
        status_update_id = selected_option_value.split("_", maxsplit=1)[1]
        status_update = dao.read_status_update(status_update_id)
        if not status_update:
            logger.error(f"Can not find status update {status_update_id}")
        else:
            try:
                app.client.views_open(
                    trigger_id=body["trigger_id"],
                    view=status_update_dialog_view(state=status_update),
                )
            except Exception as e:
                logger.error(f"Error opening status update model dialog: {e}")
    elif selected_option_value.startswith("delete_"):
        pass
    else:
        pass


@app.action("home_page_company_updates_button_clicked")
def home_page_company_updates_button_click_handler(ack, body, logger):
    ack()
    logger.info(body)
    user_id = body["user"]["id"]
    user_preferences = get_or_create_slack_user_preferences(user_id)
    user_info = get_user_info(user_id)
    if user_preferences.active_tab == "company_updates":
        # Something is wrong in the home_page_status_update_filters function. Even if we pass Nulls
        # instead of team and project - it doesn't reset filters, which creates inconsistency - user sees
        # status updates from all teams and projects, even though one or both of the filters contain some values
        # So, disabling this code for now

        # user_preferences.active_team_filter = None
        # user_preferences.active_department_filter = None
        # user_preferences.active_project_filter = None
        pass
    else:
        user_preferences.active_tab = "company_updates"
        dao.insert_slack_user_preferences(user_preferences)

    try:
        app.client.views_publish(
            user_id=user_id,
            view=home_page_company_updates_view(
                team=user_preferences.active_team_filter,
                department=user_preferences.active_department_filter,
                project=user_preferences.active_project_filter,
                is_admin=user_info is not None and (user_info.is_admin or user_info.is_owner),
                current_user_slack_id=user_id
            )
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("home_page_configuration_button_clicked")
def home_page_configuration_button_clicked_handler(ack, body, logger):
    ack()
    logger.info(body)
    user_id = body["user"]["id"]
    user_preferences = get_or_create_slack_user_preferences(user_id)
    user_preferences.active_tab = "configuration"
    dao.insert_slack_user_preferences(user_preferences)

    try:
        app.client.views_publish(
            user_id=user_id,
            view=home_page_configuration_departments_view(
                departments=dao.read_departments()
            )
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("configuration_departments_button_clicked")
def configuration_departments_button_clicked_handler(ack, body, logger):
    ack()
    logger.info(body)
    user_id = body["user"]["id"]
    user_preferences = get_or_create_slack_user_preferences(user_id)
    user_preferences.active_configuration_tab = "departments"
    dao.insert_slack_user_preferences(user_preferences)

    try:
        app.client.views_publish(
            user_id=user_id,
            view=home_page_configuration_departments_view(
                departments=dao.read_departments()
            )
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("configuration_teams_button_clicked")
def configuration_teams_button_clicked_handler(ack, body, logger):
    ack()
    logger.info(body)
    user_id = body["user"]["id"]
    user_preferences = get_or_create_slack_user_preferences(user_id)
    user_preferences.active_configuration_tab = "teams"
    dao.insert_slack_user_preferences(user_preferences)

    try:
        app.client.views_publish(
            user_id=user_id,
            view=home_page_configuration_teams_view(
                teams=dao.read_teams()
            )
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")

@app.action("configuration_projects_button_clicked")
def home_page_configuration_projects_button_clicked_handler(ack, body, logger):
    ack()
    logger.info(body)
    user_id = body["user"]["id"]
    user_preferences = get_or_create_slack_user_preferences(user_id)
    user_preferences.active_configuration_tab = "projects"
    dao.insert_slack_user_preferences(user_preferences)

    try:
        app.client.views_publish(
            user_id=user_id,
            view=home_page_configuration_projects_view(
                projects=dao.read_projects()
            )
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("configuration_add_new_department_clicked")
def configuration_add_new_department_clicked_handler(ack, body, logger):
    ack()
    logger.info(body)
    try:
        app.client.views_open(
            trigger_id=body["trigger_id"],
            view=home_page_configuration_add_new_department_view(),
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.view("home_page_configuration_new_department_dialog_submitted")
def home_page_configuration_new_department_dialog_submitted_handler(ack, body, logger):
    ack()
    logger.info(body)

    department_name = str(body["view"]["state"]["values"]["home_page_configuration_new_department_dialog_input_block"][
        "home_page_configuration_new_department_dialog_input_action"]["value"]).strip()

    if not department_name:
        raise ValueError("Department name is empty")

    try:
        company = dao.read_companies(slack_team_id=body["team"]["id"])[0]
    except IndexError:
        raise IndexError(f"Can not find a company with id = {body['team']['id']}") from None

    department_uuid = body["view"]["private_metadata"]
    if department_uuid:
        department = dao.read_department(department_uuid)
        if not department:
            logger.error(f"Can not find department {department_uuid}")
        else:
            departments = dao.read_departments(department_name=department_name)
            if departments and departments[0].uuid != department_uuid:
                logger.error("Department with such name already exist")
            else:
                department.name = department_name
    else:
        if not dao.read_departments(department_name=department_name) :
            dao.insert_department(Department(company=company, name=department_name))

    user_id = body["user"]["id"]
    try:
        app.client.views_publish(
            user_id=user_id,
            view=home_page_configuration_departments_view(
                departments=dao.read_departments()
            )
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("configuration_department_menu_clicked")
def configuration_department_menu_clicked_handler(ack, body, logger):
    ack()
    logger.info(body)
    action = str(body['actions'][0]['selected_option']['value'])
    if action.startswith("edit_"):
        department_uuid = action.split("_", maxsplit=1)[1]
        department = dao.read_department(department_uuid)
        if department is None:
            logger.error(f"Can not find department {department_uuid}")
        else:
            app.client.views_open(
                trigger_id=body["trigger_id"],
                view=home_page_configuration_add_new_department_view(
                    department_name=department.name,
                    department_uuid=department.uuid
                ),
            )
    elif action.startswith("delete_"):
        department_uuid = action.split("_", maxsplit=1)[1]
        department = dao.read_department(department_uuid)
        if department is None:
            logger.error(f"Can not find department {department_uuid}")
        else:
            app.client.views_open(
                trigger_id=body["trigger_id"],
                view=home_page_configuration_delete_department_view(
                    department_name=department.name,
                    department_uuid=department.uuid
                )
            )
    else:
        pass


@app.view("home_page_configuration_delete_dialog_submitted")
def home_page_configuration_delete_dialog_submitted_handler(ack, body, logger):
    ack()
    logger.info(body)
    department_uuid = body["view"]["private_metadata"]
    department = dao.read_department(department_uuid)
    if department is None:
        logger.error(f"Can not find department {department_uuid}")
    else:
        for team in dao.read_teams(department_uuid=department.uuid):
            dao.delete_team(team.uuid)
        dao.delete_department(department.uuid)

    try:
        app.client.views_publish(
            user_id=body["user"]["id"],
            view=home_page_configuration_departments_view(
                departments=dao.read_departments()
            )
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")

@app.action("configuration_add_new_team_clicked")
def configuration_add_new_team_clicked_handler(ack, body, logger):
    ack()
    logger.info(body)

    try:
        app.client.views_open(
            trigger_id=body["trigger_id"],
            view=home_page_configuration_add_new_team_view(
                departments=dao.read_departments()
            )
        )
    except Exception as e:
        logger.error(f"Error opening add new team dialog: {e}")


@app.view("home_page_configuration_new_team_dialog_submitted")
def home_page_configuration_new_team_dialog_submitted_handler(ack, body, logger):
    ack()
    logger.info(body)

    team_uuid = body["view"]["private_metadata"]
    team = dao.read_team(team_uuid)

    team_name = body["view"]["state"]["values"]["home_page_configuration_new_team_dialog_input_block"][
        "home_page_configuration_new_team_dialog_input_action"]["value"].strip()

    department_uuid = body["view"]["state"]["values"]["home_page_configuration_new_team_dialog_input_department_block"][
        "home_page_configuration_new_team_dialog_input_department_action"]["selected_option"]["value"]

    department = dao.read_department(department_uuid)
    if not department:
        logger.error(f"Can not find department {department_uuid}")
    else:
        if team:
            team.name = team_name
            team.department = department
        else:
            team = dao.read_teams(team_name=team_name)
            if not team:
                dao.insert_team(Team(
                    name=team_name,
                    department=department
                ))

    try:
        app.client.views_publish(
            user_id=body["user"]["id"],
            view=home_page_configuration_teams_view(
                teams=dao.read_teams()
            )
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("configuration_team_menu_clicked")
def configuration_team_menu_clicked_handler(ack, body, logger):
    ack()
    logger.info(body)

    action = str(body["actions"][0]["selected_option"]["value"])

    if action.startswith("edit_"):
        team_uuid = action.split("_", maxsplit=1)[1]
        team = dao.read_team(team_uuid)
        if not team:
            logger.error(f"Can not find a team {team_uuid}")
        else:
            try:
                app.client.views_open(
                    trigger_id=body["trigger_id"],
                    view=home_page_configuration_add_new_team_view(
                        team_uuid=team.uuid,
                        team_name=team.name,
                        department_uuid=team.department.uuid,
                        departments=dao.read_departments()
                    )
                )
            except Exception as e:
                logger.error(f"Error opening add new team dialog: {e}")
    elif action.startswith("delete_"):
        team_uuid = action.split("_", maxsplit=1)[1]
        team = dao.read_team(team_uuid)
        if not team:
            logger.error(f"Can not find a team {team_uuid}")
        else:
            app.client.views_open(
                trigger_id=body["trigger_id"],
                view=home_page_configuration_delete_team_view(
                    team_name=team.name,
                    team_uuid=team.uuid
                )
            )
    else:
        pass


@app.view("home_page_configuration_delete_team_dialog_submitted")
def home_page_configuration_delete_team_dialog_submitted_handler(ack, body, logger):
    ack()
    logger.info(body)

    team_uuid = body["view"]["private_metadata"]
    team = dao.read_team(team_uuid)
    if team is None:
        logger.error(f"Can not find team {team_uuid}")
    else:
        dao.delete_team(team_uuid)

    try:
        app.client.views_publish(
            user_id=body["user"]["id"],
            view=home_page_configuration_teams_view(
                teams=dao.read_teams()
            )
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("home_page_select_team_filter_changed")
def home_page_select_team_filter_change_handler(ack, body, logger):
    ack()
    logger.info(body)
    try:
        team, department, project = retrieve_status_update_filters_from_view(body)
        user_id = body["user"]["id"]
        user_preferences = get_or_create_slack_user_preferences(user_id)
        user_preferences.active_team_filter = team
        user_preferences.active_department_filter = department
        user_preferences.active_project_filter = project
        dao.insert_status_update(user_preferences)
        user_info = get_user_info(user_id)
        app.client.views_publish(
            user_id=user_id,
            view=home_page_company_updates_view(team=team, department=department, project=project,
                                                is_admin=user_info is not None and (user_info.is_admin
                                                                                    or user_info.is_owner),
                                                current_user_slack_id=user_id)
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("home_page_select_project_filter_changed")
def home_page_select_team_project_change_handler(ack, body, logger):
    home_page_select_team_filter_change_handler(ack, body, logger)


@app.action("configuration_project_menu_clicked")
def configuration_project_menu_clicked_handler(ack, body, logger):
    ack()
    logger.info(body)

    action = str(body["actions"][0]["selected_option"]["value"])

    if action.startswith("edit_"):
        project_uuid = action.split("_", maxsplit=1)[1]
        project = dao.read_project(project_uuid)
        if not project:
            logger.error(f"Can not find a project {project_uuid}")
        else:
            try:
                app.client.views_open(
                    trigger_id=body["trigger_id"],
                    view=home_page_configuration_add_new_project_view(
                        project_name=project.name,
                        project_uuid=project.uuid
                    )
                )
            except Exception as e:
                logger.error(f"Error opening add new project dialog: {e}")
    elif action.startswith("delete_"):
        project_uuid = action.split("_", maxsplit=1)[1]
        project = dao.read_project(project_uuid)
        if not project:
            logger.error(f"Can not find a project {project_uuid}")
        else:
            app.client.views_open(
                trigger_id=body["trigger_id"],
                view=home_page_configuration_delete_project_view(
                    project_name=project.name,
                    project_uuid=project.uuid
                )
            )
    else:
        pass


@app.action("configuration_add_new_project_clicked")
def configuration_add_new_project_clicked_handler(ack, body, logger):
    ack()
    logger.info(body)
    try:
        app.client.views_open(
            trigger_id=body["trigger_id"],
            view=home_page_configuration_add_new_project_view(),
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.view("home_page_configuration_new_project_dialog_submitted")
def home_page_configuration_new_project_dialog_submitted_handler(ack, body, logger):
    ack()
    logger.info(body)

    project_name = str(body["view"]["state"]["values"]["home_page_configuration_new_project_dialog_input_block"][
        "home_page_configuration_new_project_dialog_input_action"]["value"]).strip()

    if not project_name:
        raise ValueError("Project name is empty")

    try:
        company = dao.read_companies(slack_team_id=body["team"]["id"])[0]
    except IndexError:
        raise IndexError(f"Can not find a company with id = {body['team']['id']}") from None

    project_uuid = body["view"]["private_metadata"]
    if project_uuid:
        project = dao.read_project(project_uuid)
        if not project:
            logger.error(f"Can not find project {project_uuid}")
        else:
            projects = dao.read_projects(project_name=project_name)
            if projects and projects[0].uuid != project_uuid:
                logger.error("Project with such name already exist")
            else:
                project.name = project_name
                project.deleted = False
    else:
        if not dao.read_projects(project_name=project_name) :
            dao.insert_department(Project(company=company, name=project_name))

    user_id = body["user"]["id"]
    try:
        app.client.views_publish(
            user_id=user_id,
            view=home_page_configuration_projects_view(
                projects=dao.read_projects()
            )
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.view("home_page_configuration_delete_project_dialog_submitted")
def home_page_configuration_delete_project_dialog_submitted_handler(ack, body, logger):
    ack()
    logger.info(body)

    project_uuid = body["view"]["private_metadata"]
    project = dao.read_project(project_uuid)
    if project is None:
        logger.error(f"Can not find project {project_uuid}")
    else:
        dao.delete_project(project_uuid)

    try:
        app.client.views_publish(
            user_id=body["user"]["id"],
            view=home_page_configuration_projects_view(
                projects=dao.read_projects()
            )
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("share_status_update_button_clicked")
def share_status_update_button_click_handler(ack, body, logger):
    ack()
    try:
        app.client.views_open(
            trigger_id=body["trigger_id"],
            view=status_update_dialog_view(state=dao.read_last_unpublished_status_update(
                author_slack_user_id=body["user"]["id"],
                source=StatusUpdateSource.SLACK_DIALOG
            )),
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.view("status_update_preview_button_clicked")
def status_update_preview_button_click_handler(ack, body, logger):
    ack()
    status_update = retrieve_status_update_from_view(body)
    existing_status_update = dao.read_status_update(status_update.uuid)
    user_info = get_user_info(status_update.author_slack_user_id)
    show_preview = True

    if user_info:
        status_update.author_slack_user_name = user_info.name
    if existing_status_update and existing_status_update.published:
        existing_status_update.teams = status_update.teams
        existing_status_update.projects = status_update.projects
        existing_status_update.type = status_update.type
        existing_status_update.discuss_link = status_update.discuss_link
        existing_status_update.text = status_update.text
        dao.insert_status_update(existing_status_update)
        show_preview = False
    else:
        dao.insert_status_update(status_update)

    if show_preview:
        try:
            app.client.views_open(
                trigger_id=body["trigger_id"],
                view=share_status_update_preview_view(update=status_update),
            )
        except Exception as e:
            logger.error(f"Error publishing home tab: {e}")


@app.action("status_update_preview_back_to_editing_clicked")
def status_update_preview_back_to_editing_click_handler(ack, body, logger):
    ack()
    status_update = dao.read_status_update(retrieve_private_metadata_from_view(body).status_update_uuid)

    try:
        app.client.views_update(
            trigger_id=body["trigger_id"],
            view_id=body["view"]["id"],
            view=status_update_dialog_view(state=status_update),
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.view("status_update_preview_share_button_clicked")
def status_update_preview_share_button_click_handler(ack, body, logger):
    ack()
    dao.publish_status_update(retrieve_private_metadata_from_view(body).status_update_uuid)


@app.event("message")
def message_event_handler(body, logger):
    status_update = status_update_from_message(body)
    user_info = get_user_info(status_update.author_slack_user_id)
    if user_info:
        status_update.author_slack_user_name = user_info.name
    status_update.published = False
    dao.insert_status_update(status_update)

    prefix = ""
    if status_update.projects:
        prefix = ", ".join(project.name for project in status_update.projects) + ": "
    elif status_update.teams:
        prefix = ", ".join(team.name for team in status_update.teams) + ": "

    app.client.chat_postMessage(
        metadata=Metadata(event_type="my_type", event_payload={"status_update_uuid": status_update.uuid}),
        text=prefix + status_update.text,  # This text will be displayed in notifications
        channel=body["event"]["channel"],
        blocks=status_update_preview_message(status_update),
        unfurl_links=False
    )
    # TODO: Delete original message (if possible) !! OR !! Update status update preview on original message update
    # app.client.chat_delete()
    logger.info(body)


@app.action("status_update_message_preview_team_selected")
def status_update_message_preview_team_select_handler(ack, body, logger):
    ack()
    logger.info(body)
    status_update_uuid = body["message"]["metadata"]["event_payload"]["status_update_uuid"]
    slack_team_id = body["team"]["id"]
    try:
        company = dao.read_companies(slack_team_id=slack_team_id)[0]
    except IndexError:
        raise IndexError(f"Can not find a company with team_id = {slack_team_id}") from None
    status_update = dao.read_status_update(status_update_uuid)
    if status_update is None:
        status_update = StatusUpdate(
            source=StatusUpdateSource.SLACK_MESSAGE,
            text=body["message"]["text"],
            published=False,
            company=company
        )
    status_update.teams = [dao.read_team(team["value"]) for team in body["state"]["values"][
        "status_update_preview_teams_list"]["status_update_message_preview_team_selected"]["selected_options"]]
    status_update.projects = [dao.read_project(project["value"]) for project in body["state"]["values"][
        "status_update_preview_projects_list"]["status_update_message_preview_project_selected"]["selected_options"]]
    try:
        status_update_type_uuid = body["state"]["values"]["status_update_preview_status_update_type"][
            "status_update_message_preview_status_update_type_selected"]["selected_option"]["value"]
        status_update.type = dao.read_status_update_type(status_update_type_uuid)
    except TypeError:
        status_update.type = None
    dao.insert_status_update(status_update)

    prefix = ""
    if status_update.projects:
        prefix = ", ".join(project.name for project in status_update.projects) + ": "
    elif status_update.teams:
        prefix = ", ".join(team.name for team in status_update.teams) + ": "

    app.client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text=prefix + status_update.text,
        blocks=status_update_preview_message(status_update)
    )


@app.action("status_update_message_preview_project_selected")
def status_update_message_preview_project_select_handler(ack, body, logger):
    status_update_message_preview_team_select_handler(ack, body, logger)


@app.action("status_update_message_preview_status_update_type_selected")
def status_update_message_preview_status_update_type_select_handler(ack, body, logger):
    status_update_message_preview_team_select_handler(ack, body, logger)


@app.action("status_update_message_preview_publish_button_clicked")
def status_update_message_preview_publish_button_click_handler(ack, body, logger):
    status_update_uuid = body["message"]["metadata"]["event_payload"]["status_update_uuid"]
    status_update = dao.read_status_update(status_update_uuid)
    status_update.published = True
    try:
        discuss_link = body["state"]["values"]["status_update_preview_discuss_link"][
            "status_update_message_preview_discuss_link_updated"]["value"]
    except (KeyError, TypeError):
        discuss_link = None
    status_update.discuss_link = discuss_link
    dao.insert_status_update(status_update)
    status_update_message_preview_team_select_handler(ack, body, logger)


@app.action("status_update_message_preview_cancel_button_clicked")
def status_update_message_preview_cancel_button_click_handler(ack, body, logger):
    status_update_uuid = body["message"]["metadata"]["event_payload"]["status_update_uuid"]
    status_update = dao.read_status_update(status_update_uuid)
    status_update.deleted = True
    dao.insert_status_update(status_update)
    status_update_message_preview_team_select_handler(ack, body, logger)


app.step(WorkflowStep(
    callback_id="remind_to_share_updates",
    edit=reminder_wf_step_edit_handler,
    save=reminder_wf_step_save_handler,
    execute=reminder_wf_step_execute_handler,
))

app.step(WorkflowStep(
    callback_id="publish_status_updates_report",
    edit=publish_updates_wf_step_edit_handler,
    save=publish_updates_wf_step_save_handler,
    execute=publish_updates_wf_step_execute_handler,
))

app.step(WorkflowStep(
    callback_id="email_status_updates_report",
    edit=email_updates_wf_step_edit_handler,
    save=email_updates_wf_step_save_handler,
    execute=email_updates_wf_step_execute_handler,
))

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    handler = SocketModeHandler(app, slack_app_token())
    handler.start()
