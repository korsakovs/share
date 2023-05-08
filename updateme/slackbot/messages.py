from typing import List

from slack_sdk.models.blocks import Block, HeaderBlock, DividerBlock, ActionsBlock, ButtonElement, SectionBlock, \
    MarkdownTextObject

from updateme.core import dao
from updateme.core.model import StatusUpdate, StatusUpdateSource, StatusUpdateImage
from updateme.slackbot.blocks import status_update_blocks, status_update_teams_block, status_update_projects_block, \
    status_update_type_block, status_update_discuss_link_block


def status_update_from_message(body) -> StatusUpdate:
    text = body["event"]["text"]
    files = body["event"].get("files")
    if files:
        # todo: check / update a list of supported file extensions
        images = [file for file in files if file["filetype"] in ("jpg", "png", "gif")]
    else:
        images = []
    try:
        company = dao.read_companies(slack_team_id=body["team_id"])[0]
    except IndexError:
        raise IndexError(f"Can not find company with slack_team_id = {body['team_id']}") from None
    return StatusUpdate(
        text=text,
        company=company,
        is_markdown=True,
        source=StatusUpdateSource.SLACK_MESSAGE,
        author_slack_user_id=body["event"]["user"],
        author_slack_user_name=None,
        images=[StatusUpdateImage(
            url=image["url_private"],
            filename=image["name"],
            title=image["title"],
            description=image.get("alt_txt")
        ) for image in images]
    )


def status_update_preview_message(status_update: StatusUpdate) -> List[Block]:
    suffix_block = ActionsBlock(
        elements=[
            ButtonElement(
                action_id="status_update_message_preview_publish_button_clicked",
                text="Share!",
                style="primary"
            ),
            ButtonElement(
                action_id="status_update_message_preview_cancel_button_clicked",
                text="Cancel",
                style="danger"
            ),
        ]
    )

    input_blocks = [
        status_update_type_block(
            block_id="status_update_preview_status_update_type",
            action_id="status_update_message_preview_status_update_type_selected",
            status_update_groups=dao.read_status_update_types(),
            selected_value=status_update.type
        ),
        status_update_teams_block(
            block_id="status_update_preview_teams_list",
            action_id="status_update_message_preview_team_selected",
            status_update_teams=dao.read_teams(),
            selected_options=status_update.teams
        ),
        status_update_projects_block(
            block_id="status_update_preview_projects_list",
            action_id="status_update_message_preview_project_selected",
            status_update_projects=dao.read_projects(),
            selected_options=status_update.projects
        ),
        status_update_discuss_link_block(
            block_id="status_update_preview_discuss_link",
            action_id="status_update_message_preview_discuss_link_updated",
            initial_value=status_update.discuss_link
        ),
    ]
    if status_update.deleted:
        input_blocks = []
        suffix_block = SectionBlock(text=MarkdownTextObject(text="*Discarded*"))
    elif status_update.published:
        input_blocks = []
        suffix_block = SectionBlock(text=MarkdownTextObject(text="*Shared!*"))

    return [
        HeaderBlock(text="Status Update Preview"),
        DividerBlock(),
        *status_update_blocks(status_update, display_edit_buttons=False),
        DividerBlock(),
        *input_blocks,
        suffix_block
    ]
