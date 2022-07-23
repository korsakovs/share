# import pprint  # Delete me

import os
import logging

from slack_bolt import App, Ack
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.workflows.step import WorkflowStep, Configure, Update, Complete, Fail
from slack_sdk import WebClient
from slack_sdk.web import SlackResponse

from slackbot.config import StatusUpdate
from slackbot.views import status_update_dialog_view, retrieve_status_update_from_view, \
    share_status_update_preview_view, home_page_view, STATUS_UPDATE_MODAL_STATUS_UPDATE_TYPE_ACTION_ID, \
    STATUS_UPDATE_MODAL_STATUS_UPDATE_EMOJI_ACTION_ID, STATUS_UPDATE_MODAL_STATUS_UPDATE_TEAMS_ACTION_ID, \
    STATUS_UPDATE_MODAL_STATUS_UPDATE_PROJECTS_ACTION_ID

logging.basicConfig(level=logging.DEBUG)
app = App(token=os.environ["SLACK_BOT_TOKEN"])


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
def handle_app_home_opened_events(client: WebClient, event, logger):
    try:
        client.views_publish(
            user_id=event["user"],
            view=home_page_view()
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("share_status_update")
def share_status_update_handler(ack, body, logger):
    ack()
    try:
        app.client.views_open(
            trigger_id=body["trigger_id"],
            view=status_update_dialog_view()
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.view("status_update_shared_callback")
def handle_view_events(ack, body, logger):
    ack()
    status_update = retrieve_status_update_from_view(body["view"]["state"])

    try:
        app.client.views_open(
            trigger_id=body["trigger_id"],
            view=share_status_update_preview_view(update=status_update),
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("status_update_preview_block_edit_action")
def share_status_update_preview_edit_event(ack, body, logger):
    ack()
    status_update = StatusUpdate.from_json(body["view"]["private_metadata"])

    try:
        app.client.views_update(
            trigger_id=body["trigger_id"],
            view_id=body["view"]["id"],
            view=status_update_dialog_view(state=status_update),
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


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
