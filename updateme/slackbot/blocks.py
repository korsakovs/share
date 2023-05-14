from datetime import date
from typing import List, Optional
from slack_sdk.models.blocks import SectionBlock, StaticMultiSelectElement, Option, StaticSelectElement, \
    PlainTextInputElement, InputBlock, ButtonElement, ActionsBlock, TextObject, HeaderBlock, DividerBlock, \
    ContextBlock, MarkdownTextObject, PlainTextObject, OverflowMenuElement, UrlInputElement

from updateme.core.model import StatusUpdateType, Team, Project, StatusUpdate, StatusUpdateReaction, Department
from updateme.slackbot.utils import es, teams_selector_option_groups, join_names_with_commas


def home_page_actions_block(selected: str = "my_updates", show_configuration: bool = False) -> ActionsBlock:
    elements = [
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
    if show_configuration:
        elements.append(ButtonElement(
            text="Configuration",
            style="primary" if selected == "configuration" else None,
            action_id="home_page_configuration_button_clicked"
        ))

    return ActionsBlock(elements=elements)


def home_page_configuration_actions_block(selected: str = "departments") -> ActionsBlock:
    elements = [
        ButtonElement(
            text="Departments",
            style="primary" if selected == "departments" else None,
            action_id="configuration_departments_button_clicked"
        ),
        ButtonElement(
            text="Teams",
            style="primary" if selected == "teams" else None,
            action_id="configuration_teams_button_clicked"
        ),
        ButtonElement(
            text="Projects",
            style="primary" if selected == "projects" else None,
            action_id="configuration_projects_button_clicked"
        ),
        ButtonElement(
            text="Status Types",
            style="primary" if selected == "status_types" else None,
            action_id="configuration_status_types_button_clicked"
        ),
    ]

    return ActionsBlock(elements=elements)


def home_page_status_update_filters(teams: List[Team], projects: List[Project], active_team: Team = None,
                                    active_department: Department = None, active_project: Project = None) \
        -> ActionsBlock:
    all_teams_option = Option(value="__all__", label="All teams")
    all_projects_option = Option(value="__all__", label="All projects")

    team_option_groups = teams_selector_option_groups(teams, add_department_as_team=True, all_teams_value="__all__",
                                                      all_teams_label="All teams")
    active_team_option = all_teams_option
    for option_group in team_option_groups:
        for option in option_group.options:
            if (active_team and active_team.uuid == option.value) \
                    or (active_department and active_department.uuid == option.value):
                active_team_option = option

    active_project_option = all_projects_option if active_project is None \
        or active_project.uuid not in [p.uuid for p in projects] \
        else Option(value=active_project.uuid, label=active_project.name)

    return ActionsBlock(
        block_id="status_updates_filter_block",
        elements=[
            StaticSelectElement(
                action_id="home_page_select_team_filter_changed",
                initial_option=active_team_option,
                option_groups=team_option_groups,
            ),
            StaticSelectElement(
                action_id="home_page_select_project_filter_changed",
                initial_option=active_project_option,
                options=[
                    all_projects_option,
                    *[Option(value=project.uuid, label=project.name) for project in projects],
                ]
            ),
        ]
    )


def status_update_type_block(status_update_groups: List[StatusUpdateType],
                             label: str = "Status Update Type", select_text="Select status update group",
                             selected_value: StatusUpdateType = None, block_id: str = None,
                             action_id: str = None) -> SectionBlock:
    def type_as_option(status_update_type: StatusUpdateType) -> Option:
        return Option(value=status_update_type.uuid, text=f"{status_update_type.emoji} {status_update_type.name}")

    if selected_value and not selected_value.deleted:
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


def status_update_teams_block(status_update_teams: List[Team], label: str = "Pick one or multiple teams",
                              select_text: str = "Select a team(s)", selected_options: List[Team] = None,
                              block_id: str = None, action_id: str = None) -> SectionBlock:
    def team_as_option(team: Team) -> Option:
        return Option(value=team.uuid, text=team.name)

    if selected_options is not None:
        selected_options = [team_as_option(team) for team in selected_options if not team.deleted]

    return SectionBlock(
        block_id=block_id,
        text=label,
        accessory=StaticMultiSelectElement(
            action_id=action_id,
            placeholder=select_text,
            option_groups=teams_selector_option_groups(status_update_teams),
            initial_options=selected_options,
            focus_on_load=False
        )
    )


def status_update_projects_block(status_update_projects: List[Project],
                                 label: str = "Pick zero, one or multiple projects",
                                 select_text: str = "Select a project(s)", selected_options: List[Project] = None,
                                 block_id: str = None, action_id: str = None) -> SectionBlock:
    def project_as_option(project: Project) -> Option:
        return Option(value=project.uuid, text=project.name)

    if selected_options is not None:
        selected_options = [project_as_option(project) for project in selected_options if not project.deleted]

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
            initial_options=selected_options,
            focus_on_load=False
        )
    )


def status_update_discuss_link_block(label: str = "Link to a discussion", initial_value: str = None,
                                     block_id: str = None, action_id: str = None) -> InputBlock:
    return InputBlock(
        block_id=block_id,
        label=label,
        optional=True,
        element=PlainTextInputElement(
            placeholder="https://",
            action_id=action_id,
            initial_value=initial_value,
            focus_on_load=False
        )
    )


def status_update_text_block(label: str = "Status Update", initial_value: str = None, block_id: str = None,
                             action_id: str = None) -> InputBlock:
    return InputBlock(
        block_id=block_id,
        label=label,
        optional=False,
        element=PlainTextInputElement(
            action_id=action_id,
            multiline=True,
            initial_value=initial_value,
            max_length=256,
            focus_on_load=True
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


def status_update_blocks(status_update: StatusUpdate, status_update_reactions: List[StatusUpdateReaction] = None,
                         display_edit_buttons: bool = False, accessory_action_id: str = None) \
        -> List[SectionBlock]:
    result = []
    title = ""
    if status_update.type:
        title += status_update.type.emoji + f" *{status_update.type.name}*"
    if status_update.projects:
        title += " @ " + ", ".join(project.name for project in status_update.projects)

    text = " • "
    text += status_update.text

    attachments_text = ""
    if status_update.images:
        attachments_text += "\n\n*Attachments*:\n"
        for image in status_update.images:
            description = ""
            if image.description:
                description = f" - {image.description}"
            attachments_text += f" • <{image.url}|{image.title or image.filename}>{description}\n"

    if title:
        result.append(SectionBlock(
            text=TextObject(
                type="mrkdwn",
                text=es(title),
                # emoji=True
            )
        ))

    if status_update.is_markdown:
        text_object = MarkdownTextObject(text=text)
    else:
        text_object = PlainTextObject(text=text)

    menu_options = []

    if status_update_reactions:
        menu_options.extend([Option(label=reaction.emoji + " " + reaction.name, value=reaction.uuid)
                             for reaction in status_update_reactions])

    if display_edit_buttons:
        menu_options.extend([
            Option(label="Edit...", value="edit_" + status_update.uuid),
            Option(label="Delete...", value="delete_" + status_update.uuid)
        ])

    if accessory_action_id and menu_options:
        accessory = OverflowMenuElement(
            action_id=accessory_action_id,
            options=menu_options
        )
    else:
        accessory = None

    result.append(SectionBlock(
        text=text_object,
        accessory=accessory
    ))

    if attachments_text:
        result.append(SectionBlock(
            text=TextObject(
                type="mrkdwn",
                text=attachments_text,
                # emoji=True
            )
        ))

    published_by_text = ""
    if status_update.author_slack_user_id:
        published_by_text += f"Shared by <@{es(status_update.author_slack_user_id)}>"
        if status_update.teams:
            published_by_text += " on behalf of "
    elif status_update.teams:
        published_by_text += "From "

    if status_update.teams:
        published_by_text += join_names_with_commas([team.name for team in status_update.teams], bold=True)
        published_by_text += " team"
        if len(status_update.teams) > 1:
            published_by_text += "s"

    if published_by_text:
        result.append(ContextBlock(
            elements=[
                TextObject(
                    type="mrkdwn",
                    text=published_by_text
                )
            ]
        ))

    return result


def status_update_list_blocks(status_updates: List[StatusUpdate],
                              status_update_reactions: List[StatusUpdateReaction] = None,
                              current_user_slack_id: str = None,
                              accessory_action_id: str = None) -> List[SectionBlock]:
    result = []
    last_date: Optional[date] = None
    for status_update in status_updates:
        if last_date is None or status_update.created_at.date() != last_date:
            last_date = status_update.created_at.date()
            result.append(HeaderBlock(
                text=last_date.strftime("%A, %B %-d")
            ))
            result.append(DividerBlock())

        result.extend(
            status_update_blocks(
                status_update,
                status_update_reactions,
                display_edit_buttons=status_update.author_slack_user_id == current_user_slack_id,
                accessory_action_id=accessory_action_id
            )
        )
        result.append(DividerBlock())
    return result
