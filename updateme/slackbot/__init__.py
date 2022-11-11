import os
import logging

from slack_bolt import App, Ack
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.workflows.step import WorkflowStep, Configure, Update, Complete, Fail
from slack_sdk import WebClient
from slack_sdk.web import SlackResponse

from updateme.core import dao
from updateme.slackbot.utils import get_or_create_slack_user_preferences
from updateme.slackbot.views import status_update_dialog_view, retrieve_status_update_from_view, \
    share_status_update_preview_view, STATUS_UPDATE_MODAL_STATUS_UPDATE_TYPE_ACTION_ID, \
    STATUS_UPDATE_MODAL_STATUS_UPDATE_EMOJI_ACTION_ID, STATUS_UPDATE_MODAL_STATUS_UPDATE_TEAMS_ACTION_ID, \
    STATUS_UPDATE_MODAL_STATUS_UPDATE_PROJECTS_ACTION_ID, retrieve_private_metadata_from_view, \
    home_page_my_updates_view, home_page_company_updates_view, retrieve_status_update_filters_from_view

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
        # user_preferences.active_project_filter = None
        pass
    else:
        user_preferences.active_tab = "company_updates"
    dao.insert_status_update(user_preferences)
    try:
        app.client.views_publish(
            user_id=user_id,
            view=home_page_company_updates_view(
                team=user_preferences.active_team_filter,
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
        team, project = retrieve_status_update_filters_from_view(body)
        user_id = body["user"]["id"]
        user_preferences = get_or_create_slack_user_preferences(user_id)
        user_preferences.active_team_filter = team
        user_preferences.active_project_filter = project
        dao.insert_status_update(user_preferences)
        app.client.views_publish(
            user_id=user_id,
            view=home_page_company_updates_view(team=team, project=project)
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
            view=status_update_dialog_view(state=dao.read_last_unpublished_status_update(body["user"]["id"])),
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
def handle_message_events(body, logger):
    logger.info(body)


def workflow_step_edit_execute(step: dict, client: WebClient, complete: Complete, fail: Fail):
    complete(
        outputs={
            "taskName": step["inputs"]["taskName"]["value"],
            "taskDescription": step["inputs"]["taskDescription"]["value"],
            "taskAuthorEmail": step["inputs"]["taskAuthorEmail"]["value"],
        }
    )
    home_tab_update: SlackResponse = client.views_publish(
        user_id=user_id,
        view={
            "type": "home",
            "title": {"type": "plain_text", "text": "Your tasks!"},
            "blocks": [

            ],
        },
    )
    print("Execute")
    print(step)


def workflow_step_edit_edit(ack: Ack, step, configure: Configure):
    ack()
    configure(blocks=[
        {
            "type": "section",
            "block_id": "intro-section",
            "text": {
                "type": "plain_text",
                "text": "Create a task in one of the listed projects. The link to the task and other details will be available as variable data in later steps.",
                # noqa: E501
            },
        }
    ])


def workflow_step_edit_save(ack: Ack, view: dict, update: Update):
    print("Save")
    print(view)


ws = WorkflowStep(
    callback_id="remind_to_share_updates",
    edit=workflow_step_edit_edit,
    save=workflow_step_edit_save,
    execute=workflow_step_edit_execute,
)

app.step(ws)

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
