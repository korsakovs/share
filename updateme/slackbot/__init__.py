import os
import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.workflows.step import WorkflowStep
from slack_sdk import WebClient
from slack_sdk.models.metadata import Metadata

from updateme.core import dao
from updateme.core.model import StatusUpdateSource, StatusUpdate
from updateme.slackbot.messages import status_update_preview_message, status_update_from_message
from updateme.slackbot.utils import get_or_create_slack_user_preferences, teams_selector_option_groups
from updateme.slackbot.views import status_update_dialog_view, retrieve_status_update_from_view, \
    share_status_update_preview_view, STATUS_UPDATE_MODAL_STATUS_UPDATE_TYPE_ACTION_ID, \
    STATUS_UPDATE_MODAL_STATUS_UPDATE_EMOJI_ACTION_ID, STATUS_UPDATE_MODAL_STATUS_UPDATE_TEAMS_ACTION_ID, \
    STATUS_UPDATE_MODAL_STATUS_UPDATE_PROJECTS_ACTION_ID, retrieve_private_metadata_from_view, \
    home_page_my_updates_view, home_page_company_updates_view, retrieve_status_update_filters_from_view
from updateme.slackbot.workflows.email import email_updates_wf_step_edit_handler, email_updates_wf_step_save_handler, \
    email_updates_wf_step_execute_handler
from updateme.slackbot.workflows.publish import publish_updates_wf_step_edit_handler, \
    publish_updates_wf_step_save_handler, publish_updates_wf_step_execute_handler
from updateme.slackbot.workflows.remider import reminder_wf_step_edit_handler, reminder_wf_step_save_handler, \
    reminder_wf_step_execute_handler

logging.basicConfig(level=logging.DEBUG)
app = App(token=os.getenv("SLACK_BOT_TOKEN", "<wrong_token>"))


@app.action(STATUS_UPDATE_MODAL_STATUS_UPDATE_TYPE_ACTION_ID)
def status_update_modal_status_type_action_handler(ack):
    ack()


@app.action(STATUS_UPDATE_MODAL_STATUS_UPDATE_EMOJI_ACTION_ID)
def status_update_modal_status_emoji_action_handler(ack):
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

    if user_preferences.active_tab == "my_updates":
        view = home_page_my_updates_view(user_id)
    else:
        view = home_page_company_updates_view(
            team=user_preferences.active_team_filter,
            department=user_preferences.active_department_filter,
            project=user_preferences.active_project_filter
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
    dao.insert_status_update(user_preferences)
    try:
        app.client.views_publish(
            user_id=user_id,
            view=home_page_my_updates_view(user_id)
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("home_page_company_updates_button_clicked")
def home_page_company_updates_button_click_handler(ack, body, logger):
    ack()
    logger.info(body)
    user_id = body["user"]["id"]
    user_preferences = get_or_create_slack_user_preferences(user_id)
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
                project=user_preferences.active_project_filter
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
        app.client.views_publish(
            user_id=user_id,
            view=home_page_company_updates_view(team=team, department=department, project=project)
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("home_page_select_project_filter_changed")
def home_page_select_team_project_change_handler(ack, body, logger):
    home_page_select_team_filter_change_handler(ack, body, logger)


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
    dao.insert_status_update(status_update)

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
        blocks=status_update_preview_message(status_update)
    )
    # TODO: Delete original message (if possible) !! OR !! Update status update preview on original message update
    # app.client.chat_delete()
    logger.info(body)


@app.action("status_update_message_preview_team_selected")
def status_update_message_preview_team_select_handler(ack, body, logger):
    ack()
    logger.info(body)
    status_update_uuid = body["message"]["metadata"]["event_payload"]["status_update_uuid"]
    status_update = dao.read_status_update(status_update_uuid)
    if status_update is None:
        status_update = StatusUpdate(
            source=StatusUpdateSource.SLACK_MESSAGE,
            text=body["message"]["text"],
            published=False,
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
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
