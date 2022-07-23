from typing import List
from slack_sdk.models.blocks import SectionBlock, StaticMultiSelectElement, Option, StaticSelectElement, \
    PlainTextInputElement, InputBlock, ButtonElement, ConfirmObject, ActionsBlock, TextObject

from slackbot.config import StatusUpdateType, StatusUpdateEmoji, Team, Project, StatusUpdate


def status_update_type_block(status_update_groups: List[StatusUpdateType],
                             label: str = "Status Update Type", select_text="Select status update group",
                             selected_value: str = None, block_id: str = None, action_id: str = None) -> SectionBlock:
    if selected_value:
        selected_value = Option(value=selected_value, text=selected_value)

    return SectionBlock(
        block_id=block_id,
        text=label,
        accessory=StaticSelectElement(
            action_id=action_id,
            placeholder=select_text,
            options=[
                Option(value=status_update_group.name, text=status_update_group.name)
                for status_update_group in status_update_groups if status_update_group.active
            ],
            initial_option=selected_value,
            focus_on_load=False
        )
    )


def status_update_emoji_block(status_update_emojis: List[StatusUpdateEmoji],
                              label: str = "Select emoji for your status update: ", select_text: str = "Select Emoji",
                              selected_value: str = None, block_id: str = None, action_id: str = None) -> SectionBlock:
    if selected_value:
        if selected_value == "<noemoji>":
            selected_value = Option(value="<noemoji>", text="no emoji :(")
        else:
            for status_update_emoji in status_update_emojis:
                if status_update_emoji.active and status_update_emoji.emoji == selected_value:
                    selected_value = Option(value=status_update_emoji.emoji,
                                            text=f"{status_update_emoji.emoji} : "
                                                 f"{' / '.join(status_update_emoji.meanings)}")
                    break
            else:
                selected_value = None

    return SectionBlock(
        block_id=block_id,
        text=label,
        accessory=StaticSelectElement(
            action_id=action_id,
            placeholder=select_text,
            options=[Option(value="<noemoji>", text="no emoji :("), *[
                Option(value=status_update_emoji.emoji, text=f"{status_update_emoji.emoji} : "
                                                             f"{' / '.join(status_update_emoji.meanings)}")
                for status_update_emoji in status_update_emojis if status_update_emoji.active
            ]],
            initial_option=selected_value
        )
    )


def status_update_teams_block(status_update_teams: List[Team], label: str = "Pick one or multiple teams",
                              select_text: str = "Select a team(s)", selected_options: List[str] = None,
                              block_id: str = None, action_id: str = None) -> SectionBlock:
    return SectionBlock(
        block_id=block_id,
        text=label,
        accessory=StaticMultiSelectElement(
            action_id=action_id,
            placeholder=select_text,
            options=[
                Option(value=team.name, text=team.name)
                for team in sorted(status_update_teams, key=lambda team: team.name) if team.active
            ],
            initial_options=selected_options
        )
    )


def status_update_projects_block(status_update_projects: List[Project],
                                 label: str = "Pick zero, one or multiple projects",
                                 select_text: str = "Select a project(s)", selected_options: List[str] = None,
                                 block_id: str = None, action_id: str = None) -> SectionBlock:
    return SectionBlock(
        block_id=block_id,
        text=label,
        accessory=StaticMultiSelectElement(
            action_id=action_id,
            placeholder=select_text,
            options=[
                Option(value=project.name, text=project.name)
                for project in sorted(status_update_projects, key=lambda project: project.name) if project.active
            ],
            initial_options=selected_options
        )
    )


def status_update_text_block(label: str = "Status Update", initial_value: str = None, block_id: str = None,
                             action_id: str = None) -> InputBlock:
    return InputBlock(
        block_id=block_id,
        label=label,
        element=PlainTextInputElement(
            action_id=action_id,
            multiline=True,
            initial_value=initial_value,
            max_length=256,
            focus_on_load=True
        )
    )


def status_update_preview_block(status_update: StatusUpdate, action_id="status_update_preview_block_edit_action") \
        -> SectionBlock:
    text = " • "
    if status_update.emoji and status_update.emoji != "<noemoji>":
        text += status_update.emoji + " "
    if status_update.projects:
        text += " / ".join(status_update.projects) + " : "
    text += status_update.text.strip()
    if status_update.teams:
        text += "\n\n_" + ", ".join(status_update.teams) + "_"

    return SectionBlock(
        text=TextObject(
            type="mrkdwn",
            text=text,
            # emoji=True
        )
    )


def status_update_preview_back_to_editing_block() -> ActionsBlock:
    return ActionsBlock(
        elements=[
            ButtonElement(
                text="Back to editing...",
                action_id="status_update_preview_block_edit_action"
            )
        ]
    )
