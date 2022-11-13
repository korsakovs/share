from slack_bolt import Ack
from slack_bolt.workflows.step import Configure, Update, Complete, Fail
from slack_sdk import WebClient
from slack_sdk.models.blocks import InputBlock, EmailInputElement, PlainTextObject, StaticMultiSelectElement, Option

from updateme.core import dao
from updateme.slackbot import teams_selector_option_groups


def email_updates_wf_step_edit_handler(ack: Ack, step, configure: Configure):
    ack()
    configure(blocks=[
        InputBlock(
            block_id="email_input_block",
            label="Email",
            element=EmailInputElement(
                action_id="email_input_element",
                placeholder=PlainTextObject(text="Add an email")
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


def email_updates_wf_step_save_handler(ack: Ack, view: dict, update: Update):
    pass


def email_updates_wf_step_execute_handler(step: dict, client: WebClient, complete: Complete, fail: Fail):
    pass
