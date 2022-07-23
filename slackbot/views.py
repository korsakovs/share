from slack_bolt import App
from slack_sdk.models.blocks import DividerBlock, SectionBlock, ActionsBlock, ButtonElement
from slack_sdk.models.views import View

from slackbot.blocks import status_update_type_block, status_update_emoji_block, status_update_teams_block, \
    status_update_projects_block, status_update_text_block, status_update_preview_block, \
    status_update_preview_back_to_editing_block
from slackbot.config import get_config, StatusUpdate


STATUS_UPDATE_TYPE_BLOCK = "status_update_type_block"
STATUS_UPDATE_MODAL_STATUS_UPDATE_TYPE_ACTION_ID = "status_update_modal__status_update_type_action_id"

STATUS_UPDATE_EMOJI_BLOCK = "status_update_emoji_block"
STATUS_UPDATE_MODAL_STATUS_UPDATE_EMOJI_ACTION_ID = "status_update_modal__status_update_emoji_action_id"

STATUS_UPDATE_TEAMS_BLOCK = "status_update_team_block"
STATUS_UPDATE_MODAL_STATUS_UPDATE_TEAMS_ACTION_ID = "status_update_modal__status_update_teams_action_id"

STATUS_UPDATE_PROJECTS_BLOCK = "status_update_projects_block"
STATUS_UPDATE_MODAL_STATUS_UPDATE_PROJECTS_ACTION_ID = "status_update_modal__status_update_projects_action_id"

STATUS_UPDATE_TEXT_BLOCK = "status_update_text_block"
STATUS_UPDATE_MODAL_STATUS_UPDATE_TEXT_ACTION_ID = "status_update_modal__status_update_text_action_id"


def retrieve_status_update_from_view(view_state) -> StatusUpdate:
    values = view_state["values"]
    print(values)

    selected_type = values[STATUS_UPDATE_TYPE_BLOCK][STATUS_UPDATE_MODAL_STATUS_UPDATE_TYPE_ACTION_ID][
        "selected_option"]
    if selected_type is not None:
        selected_type = selected_type["value"]

    selected_emoji = values[STATUS_UPDATE_EMOJI_BLOCK][STATUS_UPDATE_MODAL_STATUS_UPDATE_EMOJI_ACTION_ID][
        "selected_option"]
    if selected_emoji is not None:
        selected_emoji = selected_emoji["value"]

    return StatusUpdate(
        type=selected_type,
        emoji=selected_emoji,
        teams=[option["text"]["text"] for option in values[STATUS_UPDATE_TEAMS_BLOCK][
            STATUS_UPDATE_MODAL_STATUS_UPDATE_TEAMS_ACTION_ID]["selected_options"]],
        projects=[option["text"]["text"] for option in values[STATUS_UPDATE_PROJECTS_BLOCK][
            STATUS_UPDATE_MODAL_STATUS_UPDATE_PROJECTS_ACTION_ID]["selected_options"]],
        text=values[STATUS_UPDATE_TEXT_BLOCK][STATUS_UPDATE_MODAL_STATUS_UPDATE_TEXT_ACTION_ID]["value"]
    )


def status_update_dialog_view(callback_id: str = "status_update_shared_callback", state: StatusUpdate = None) \
        -> View:
    config = get_config()
    return View(
        type="modal",
        callback_id=callback_id,
        title="Share Status Update",
        submit="Preview",
        close="Cancel",
        blocks=[
            DividerBlock(),
            status_update_type_block(config.STATUS_UPDATE_GROUPS,
                                     selected_value=None if state is None else state.type,
                                     block_id=STATUS_UPDATE_TYPE_BLOCK,
                                     action_id=STATUS_UPDATE_MODAL_STATUS_UPDATE_TYPE_ACTION_ID),
            status_update_emoji_block(config.STATUS_UPDATE_EMOJIS,
                                      selected_value=None if state is None else state.emoji,
                                      block_id=STATUS_UPDATE_EMOJI_BLOCK,
                                      action_id=STATUS_UPDATE_MODAL_STATUS_UPDATE_EMOJI_ACTION_ID),
            DividerBlock(),
            status_update_teams_block(config.TEAMS, selected_options=None if state is None else state.teams,
                                      block_id=STATUS_UPDATE_TEAMS_BLOCK,
                                      action_id=STATUS_UPDATE_MODAL_STATUS_UPDATE_TEAMS_ACTION_ID),
            status_update_projects_block(config.PROJECTS, selected_options=None if state is None else state.projects,
                                         block_id=STATUS_UPDATE_PROJECTS_BLOCK,
                                         action_id=STATUS_UPDATE_MODAL_STATUS_UPDATE_PROJECTS_ACTION_ID),
            status_update_text_block(initial_value=None if state is None else state.text,
                                     block_id=STATUS_UPDATE_TEXT_BLOCK,
                                     action_id=STATUS_UPDATE_MODAL_STATUS_UPDATE_TEXT_ACTION_ID),
        ]
    )


def share_status_update_preview_view(update: StatusUpdate,
                                     callback_id: str = "status_update_preview_approved_callback") -> View:
    return View(
        type="modal",
        callback_id=callback_id,
        title="Preview Status Update",
        submit="Share",
        close="Cancel",
        private_metadata=update.to_json(),
        blocks=[
            DividerBlock(),
            status_update_preview_block(update),
            DividerBlock(),
            status_update_preview_back_to_editing_block(),
        ]
    )


def home_page_view():
    return View(
        type="home",
        title="Welcome to Chirik Bot!",
        blocks=[
            ActionsBlock(
                elements=[
                    ButtonElement(
                        text="Share a status update",
                        style="primary",
                        action_id="share_status_update"
                    ),
                    ButtonElement(
                        text="My Updates",
                        action_id="home_page_my_updates_action_id"
                    ),
                    ButtonElement(
                        text="Company Updates",
                        action_id="home_page_company_updates_action_id"
                    ),
                ]
            ),
            DividerBlock(),
        ]
    )
