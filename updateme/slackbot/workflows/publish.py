from slack_bolt import Ack
from slack_bolt.workflows.step import Configure, Update, Complete, Fail
from slack_sdk import WebClient
from slack_sdk.models.blocks import InputBlock, UserMultiSelectElement,  StaticMultiSelectElement, Option

from updateme.core import dao
from updateme.slackbot.utils import teams_selector_option_groups


def publish_updates_wf_step_edit_handler(ack: Ack, step, configure: Configure):
    ack()
    try:
        initial_conversations = step["inputs"]["conversations"]["value"]
    except (TypeError, KeyError):
        initial_conversations = None

    configure(blocks=[
        InputBlock(
            block_id="users_select_block",
            label="Who to remind: Select one or more users / conversations",
            element=UserMultiSelectElement(
                action_id="users_select_element",
                placeholder="Some placeholder",
                initial_conversations=initial_conversations
            )
        ).to_dict(),
        InputBlock(
            block_id="filters_block",
            label="Status update type(s) (optional)",
            element=StaticMultiSelectElement(
                options=[Option(label=t.emoji + " " + t.name, value=t.uuid) for t in dao.read_status_update_types()]
            )
        ).to_dict(),
        InputBlock(
            block_id="teams_block",
            label="Team(s) (optional)",
            element=StaticMultiSelectElement(
                option_groups=teams_selector_option_groups(dao.read_teams(), add_department_as_team=True),
            )
        ).to_dict(),
    ])


def publish_updates_wf_step_save_handler(ack: Ack, view: dict, update: Update):
    pass


def publish_updates_wf_step_execute_handler(step: dict, client: WebClient, complete: Complete, fail: Fail):
    pass
