from typing import List

from slack_sdk.models.blocks import Block, HeaderBlock, DividerBlock, SectionBlock, MarkdownTextObject, InputBlock, \
    StaticMultiSelectElement, Option, ActionsBlock, ButtonElement

from updateme.core.model import StatusUpdate, StatusUpdateSource, StatusUpdateImage


def status_update_from_message(body) -> StatusUpdate:
    text = body["event"]["text"]
    files = body["event"].get("files")
    if files:
        # todo: check / update a list of supported file extensions
        images = [file for file in files if file["filetype"] in ("jpg", "png", "gif")]
    else:
        images = []
    return StatusUpdate(
        emoji=None,
        type=None,
        text=text,
        rich_text=True,
        source=StatusUpdateSource.SLACK_MESSAGE,
        images=[StatusUpdateImage(
            url=image["url_private"],
            filename=image["name"],
            title=image["title"],
            description=image.get("alt_txt")
        ) for image in images]
    )


def status_update_preview_message(status_update: StatusUpdate) -> List[Block]:
    text = status_update.text

    if status_update.images:
        text += "\n\n*Attachments*:\n"
        for image in status_update.images:
            description = ""
            if image.description:
                description = f" - {image.description}"
            text += f" • <{image.url}|{image.title or image.filename}>{description}\n"

    return [
        HeaderBlock(text="Status Update Preview"),
        DividerBlock(),
        SectionBlock(
            text=MarkdownTextObject(
                text=text
            )
        ),
        InputBlock(
            label="Pick one or multiple teams",
            element=StaticMultiSelectElement(
                placeholder="Some text",
                options=[
                    Option(value="1111", label="2222")
                ]
            )
        ),
        InputBlock(
            label="Pick one or multiple projects",
            element=StaticMultiSelectElement(
                placeholder="Some text",
                options=[
                    Option(value="1111", label="2222")
                ]
            )
        ),
        ActionsBlock(
            elements=[
                ButtonElement(
                    text="Publish",
                    style="primary"
                ),
                ButtonElement(
                    text="Cancel",
                    style="danger"
                ),
            ]
        )
    ]
