import json

from slack_sdk.models.blocks import DividerBlock, ActionsBlock, ButtonElement
from slack_sdk.models.views import View

from updateme.slackbot.blocks import status_update_type_block, status_update_emoji_block, status_update_teams_block, \
    status_update_projects_block, status_update_text_block, status_update_preview_block, \
    status_update_preview_back_to_editing_block
from updateme.core import dao
from updateme.core.model import StatusUpdate

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
    private_metadata = retrieve_private_metadata_from_view(body)

    selected_type = values[STATUS_UPDATE_TYPE_BLOCK][STATUS_UPDATE_MODAL_STATUS_UPDATE_TYPE_ACTION_ID][
        "selected_option"]
    if selected_type is not None:
        selected_type = dao.read_status_update_type(selected_type["value"])

    selected_emoji = values[STATUS_UPDATE_EMOJI_BLOCK][STATUS_UPDATE_MODAL_STATUS_UPDATE_EMOJI_ACTION_ID][
        "selected_option"]
    if selected_emoji is not None:
        selected_emoji = dao.read_status_update_emoji(selected_emoji["value"])

    teams = []
    selected_teams = values[STATUS_UPDATE_TEAMS_BLOCK][STATUS_UPDATE_MODAL_STATUS_UPDATE_TEAMS_ACTION_ID][
        "selected_options"]
    if selected_teams is not None:
        teams = [dao.read_team(selected_team["value"]) for selected_team in selected_teams]

    projects = []
    selected_projects = values[STATUS_UPDATE_PROJECTS_BLOCK][STATUS_UPDATE_MODAL_STATUS_UPDATE_PROJECTS_ACTION_ID][
        "selected_options"]
    if selected_projects is not None:
        projects = [dao.read_project(selected_project["value"]) for selected_project in selected_projects]

    kwargs = dict()
    if private_metadata and private_metadata.status_update_uuid:
        kwargs["uuid"] = private_metadata.status_update_uuid

    return StatusUpdate(
        type=selected_type,
        emoji=selected_emoji,
        teams=teams,
        projects=projects,
        text=values[STATUS_UPDATE_TEXT_BLOCK][STATUS_UPDATE_MODAL_STATUS_UPDATE_TEXT_ACTION_ID]["value"],
        author_slack_user_id=user_id,
        **kwargs
    )


def status_update_dialog_view(state: StatusUpdate = None) -> View:
    return View(
        type="modal",
        callback_id="status_update_preview_button_clicked",
        title="Share Status Update",
        submit="Preview",
        close="Cancel",
        private_metadata=str(PrivateMetadata(status_update_uuid=None if state is None else state.uuid)),
        blocks=[
            DividerBlock(),
            status_update_type_block(dao.read_status_update_types(),
                                     selected_value=None if state is None or state.type is None else state.type,
                                     block_id=STATUS_UPDATE_TYPE_BLOCK,
                                     action_id=STATUS_UPDATE_MODAL_STATUS_UPDATE_TYPE_ACTION_ID),
            status_update_emoji_block(dao.read_status_update_emojis(),
                                      selected_value=None if state is None or state.emoji is None else state.emoji,
                                      block_id=STATUS_UPDATE_EMOJI_BLOCK,
                                      action_id=STATUS_UPDATE_MODAL_STATUS_UPDATE_EMOJI_ACTION_ID),
            DividerBlock(),
            status_update_teams_block(dao.read_teams(),
                                      selected_options=None if state is None else [team for team in state.teams],
                                      block_id=STATUS_UPDATE_TEAMS_BLOCK,
                                      action_id=STATUS_UPDATE_MODAL_STATUS_UPDATE_TEAMS_ACTION_ID),
            status_update_projects_block(dao.read_projects(),
                                         selected_options=None if state is None
                                         else [project for project in state.projects],
                                         block_id=STATUS_UPDATE_PROJECTS_BLOCK,
                                         action_id=STATUS_UPDATE_MODAL_STATUS_UPDATE_PROJECTS_ACTION_ID),
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
                        action_id="share_status_update_button_clicked"
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