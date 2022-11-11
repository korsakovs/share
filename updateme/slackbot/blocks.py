from typing import List
from slack_sdk.models.blocks import SectionBlock, StaticMultiSelectElement, Option, StaticSelectElement, \
    PlainTextInputElement, InputBlock, ButtonElement, ActionsBlock, TextObject

from updateme.core.model import StatusUpdateType, StatusUpdateEmoji, Team, Project, StatusUpdate


def home_page_actions_block(selected: str = "my_updates") -> ActionsBlock:
    return ActionsBlock(
        elements=[
            ButtonElement(
                text="Share a status update",
                style="danger",
                action_id="share_status_update_button_clicked"
            ),
            ButtonElement(
                text="My Updates",
                style="primary" if selected == "my_updates" else None,
                action_id="home_page_my_updates_button_clicked"
            ),
            ButtonElement(
                text="Company Updates",
                style="primary" if selected == "company_updates" else None,
                action_id="home_page_company_updates_button_clicked"
            ),
        ]
    )


def status_update_type_block(status_update_groups: List[StatusUpdateType],
                             label: str = "Status Update Type", select_text="Select status update group",
                             selected_value: StatusUpdateType = None, block_id: str = None,
                             action_id: str = None) -> SectionBlock:
    def type_as_option(status_update_type: StatusUpdateType) -> Option:
        return Option(value=status_update_type.uuid, text=f"{status_update_type.emoji} {status_update_type.name}")

    if selected_value:
        selected_value = type_as_option(selected_value)

    return SectionBlock(
        block_id=block_id,
        text=label,
        accessory=StaticSelectElement(
            action_id=action_id,
            placeholder=select_text,
            options=[
                type_as_option(status_update_group)
                for status_update_group in status_update_groups if not status_update_group.deleted
            ],
            initial_option=selected_value,
            focus_on_load=False
        )
    )


def status_update_emoji_block(status_update_emojis: List[StatusUpdateEmoji],
                              label: str = "Select emoji for your status update: ", select_text: str = "Select Emoji",
                              selected_value: StatusUpdateEmoji = None, block_id: str = None,
                              action_id: str = None) -> SectionBlock:
    def emoji_as_option(emoji: StatusUpdateEmoji) -> Option:
        return Option(value=emoji.uuid, text=f"{emoji.emoji} : {emoji.meaning}")

    if selected_value is not None:
        selected_value = emoji_as_option(selected_value)

    return SectionBlock(
        block_id=block_id,
        text=label,
        accessory=StaticSelectElement(
            action_id=action_id,
            placeholder=select_text,
            options=[Option(value="<noemoji>", text="no emoji :("), *[
                emoji_as_option(status_update_emoji)
                for status_update_emoji in status_update_emojis if not status_update_emoji.deleted
            ]],
            initial_option=selected_value
        )
    )


def status_update_teams_block(status_update_teams: List[Team], label: str = "Pick one or multiple teams",
                              select_text: str = "Select a team(s)", selected_options: List[Team] = None,
                              block_id: str = None, action_id: str = None) -> SectionBlock:
    def team_as_option(team: Team) -> Option:
        return Option(value=team.uuid, text=team.name)

    if selected_options is not None:
        selected_options = [team_as_option(team) for team in selected_options]

    return SectionBlock(
        block_id=block_id,
        text=label,
        accessory=StaticMultiSelectElement(
            action_id=action_id,
            placeholder=select_text,
            options=[
                team_as_option(team) for team in sorted(status_update_teams, key=lambda team: team.name)
                if not team.deleted
            ],
            initial_options=selected_options
        )
    )


def status_update_projects_block(status_update_projects: List[Project],
                                 label: str = "Pick zero, one or multiple projects",
                                 select_text: str = "Select a project(s)", selected_options: List[Project] = None,
                                 block_id: str = None, action_id: str = None) -> SectionBlock:
    def project_as_option(project: Project) -> Option:
        return Option(value=project.uuid, text=project.name)

    if selected_options is not None:
        selected_options = [project_as_option(project) for project in selected_options]

    return SectionBlock(
        block_id=block_id,
        text=label,
        accessory=StaticMultiSelectElement(
            action_id=action_id,
            placeholder=select_text,
            options=[
                project_as_option(project)
                for project in sorted(status_update_projects, key=lambda project: project.name) if not project.deleted
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


def status_update_preview_block(status_update: StatusUpdate) \
        -> SectionBlock:
    text = " • "
    if status_update.emoji:
        text += status_update.emoji.emoji + " "
    if status_update.projects:
        text += " / ".join(project.name for project in status_update.projects) + " : "
    text += status_update.text.strip()
    if status_update.teams:
        text += "\n\n_" + ", ".join(team.name for team in status_update.teams) + "_"

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
                action_id="status_update_preview_back_to_editing_clicked"
            )
        ]
    )


def status_update_list_blocks(status_updates: List[StatusUpdate]) -> List[SectionBlock]:
    result = []
    for status_update in status_updates:
        title = ""
        if status_update.type:
            title += status_update.type.emoji + f" *{status_update.type.name}*"
        if status_update.projects:
            title += " @ " + ", ".join(project.name for project in status_update.projects)

        text = " • " + status_update.text

        result.append(SectionBlock(
            text=TextObject(
                type="mrkdwn",
                text=title,
                # emoji=True
            )
        ))

        result.append(SectionBlock(
            text=TextObject(
                type="plain_text",
                text=text,
                emoji=True
            )
        ))
    return result
