from slack_bolt import Ack
from slack_bolt.workflows.step import Configure, Update, Complete, Fail
from slack_sdk import WebClient
from slack_sdk.models.blocks import InputBlock, UserMultiSelectElement, PlainTextInputElement, PlainTextObject


def reminder_wf_step_edit_handler(ack: Ack, step, configure: Configure):
    ack()
    try:
        initial_users = step["inputs"]["users"]["value"]
    except (TypeError, KeyError):
        initial_users = None
    try:
        initial_text = step["inputs"]["text"]["value"]
    except (TypeError, KeyError):
        initial_text = "Hello there! Could you please share your statue updates today?"
    configure(blocks=[
        InputBlock(
            block_id="users_select_block",
            label="Who to remind: Select one or more users / conversations",
            element=UserMultiSelectElement(
                action_id="users_select_element",
                placeholder="Some placeholder",
                initial_users=initial_users
            )
        ).to_dict(),
        InputBlock(
            block_id="text_input_block",
            label="Text",
            element=PlainTextInputElement(
                action_id="text_input_element",
                placeholder=PlainTextObject(text="Add a message what will be sent to these channels / users"),
                initial_value=initial_text
            )
        ).to_dict(),
    ])


def reminder_wf_step_save_handler(ack: Ack, view: dict, update: Update):
    ack()
    values = view["state"]["values"]
    users = values["users_select_block"]["users_select_element"]["selected_users"]
    text = values["text_input_block"]["text_input_element"]["value"]

    inputs = {
        "users": {"value": users},
        "text": {"value": text}
    }
    update(inputs=inputs, outputs=[])


def reminder_wf_step_execute_handler(step: dict, client: WebClient, complete: Complete, fail: Fail):
    try:
        users = step["inputs"]["users"]["value"]
    except (TypeError, KeyError):
        users = []
    try:
        text = step["inputs"]["text"]["value"]
    except (TypeError, KeyError):
        text = None
    if text:
        for user in users:
            client.chat_postMessage(
                channel=user,
                text=text
            )
    complete(
        outputs={}
    )
