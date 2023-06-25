import itertools
from collections import defaultdict

from datetime import date, timedelta
from email.message import EmailMessage
from typing import List, Dict

from updateme.core.model import StatusUpdate
from updateme.core.utils import join_strings_with_commas
from updateme.email.utils import hsc, slack_markdown_to_html


EMAIL_BG_COLOG = "#eef"
EMAIL_HEADER_TEXT_COLOR = "#fff"
EMAIL_HEADER_BG_COLOR = ""
EMAIL_BLOCK_WIDTH = "700px"
EMAIL_CONTENT_BG_COLOG = "#fff"
FONT_FAMILY = "Arial"
FONT_SIZE = "14px"
FONT_SIZE_SMALL = "11px"


def nice_date(day: date):
    return day.strftime("%A, %B %-d")


def email_header(text: str):
    return f"""
    <div style="background-color:{EMAIL_HEADER_BG_COLOR};padding:10px">
        <h1 style="color:{EMAIL_HEADER_TEXT_COLOR};margin:0px;">{hsc(text)}</h1>
    </div>
"""


def block_header(text: str):
    return f"""
    <div style="margin:0px;padding:0px;">
        <h2>{hsc(text)}</h2>
    </div>
    """


def block_sub_header(text: str):
    return f"""
    <div style="margin:0px;padding:0px;">
        <h3>{hsc(text)}</h3>
    </div>
"""


def status_update_as_html(status_update: StatusUpdate) -> str:
    type_ = status_update.type
    projects = status_update.projects

    if status_update.is_markdown:
        text_str = slack_markdown_to_html(status_update.text)
    else:
        text_str = hsc(status_update.text)

    projects_str = ""
    if status_update.projects:
        projects_str = hsc(join_strings_with_commas([project.name for project in status_update.projects]))

    on_behalf_str = ""
    if status_update.teams:
        on_behalf_str = " on behalf of " \
                        + join_strings_with_commas(["<b>" + hsc(team.name) + "</b>" for team in status_update.teams])\
                        + (" teams" if len(status_update.teams) > 1 else " team")

    attachments_str = ""
    if status_update.images:
        attachments_str = f"""<b>Attachments:</b>
        <ul>
            {"".join(f"<li><a href='{image.url}' target='_blank' style='text-decoration: none;'>"
                     f"{hsc(image.title or image.filename)}</a>" 
                     + (f" - <i>{hsc(image.description)}</i>" if image.description else "") + "</li>"
                     for image in status_update.images)}
        </ul>
"""

    # TODO: Introduce real links and remove this test link
    discuss_link_block = ""
    if status_update.discuss_link:
        link = status_update.discuss_link.replace('"', "%22")
        discuss_link_block = f"""
        <div style="margin:0px;padding:0px;">
            <a href="{link}" style="text-decoration: none;">Discuss...</a>
        </div>"""

    return f"""
    <div style="margin:0px;padding:0px;">
        <table style="margin:0px;padding:0px;width:100%;">
            <tr>
                <td>
                    <div style="padding:5px">
                    {"" if not type_ else f" <b>{hsc(type_.name)}</b> "}
                    {"" if not projects else f"@ {projects_str}"}
                    </div>
                </td>
                <td style="align:right;text-align:right;">
                    {discuss_link_block}
                </td>
            </tr>
        </table>
        <div style="padding:5px">
            <ul>
                <li>
                    {text_str}<br />{attachments_str}
                    <div style="font-size:{FONT_SIZE_SMALL};margin-top:3px">
                        Shared by <b>{hsc(status_update.author_slack_user_name)}</b>{on_behalf_str}
                    </div>        
                </li>
            </ul>
        </div>
    </div>
"""


def status_update_group_as_html(status_updates: List[StatusUpdate], group_by_project: bool = False) -> str:
    if group_by_project:
        result = ""
        project_uuid_name_map: Dict[str, str] = dict()
        status_update_subgroups: Dict[str, List[StatusUpdate]] = defaultdict(list)
        other_projects_status_updates: List[StatusUpdate] = []

        for status_update in status_updates:
            if not status_update.projects:
                other_projects_status_updates.append(status_update)
            for project in status_update.projects:
                project_uuid_name_map[project.uuid] = project.name
                status_update_subgroups[project.uuid].append(status_update)

        for project_uuid in sorted(status_update_subgroups.keys(), key=lambda _uuid: project_uuid_name_map[_uuid]):
            result += block_sub_header(project_uuid_name_map[project_uuid])
            result += status_update_group_as_html(status_update_subgroups[project_uuid], group_by_project=False)

        if other_projects_status_updates:
            result += block_sub_header("Other projects")
            result += status_update_group_as_html(other_projects_status_updates, group_by_project=False)

        return result

    else:
        return f"""
            <div style="margin:0px;padding:0px;">
                {"".join(status_update_as_html(update) for update in status_updates)}
            </div>
"""


def compose_message(status_updates: List[StatusUpdate]) -> EmailMessage:
    msg = EmailMessage()

    updates_html = ""
    grouped_status_updates: Dict[date, List[StatusUpdate]] = dict()

    for day, status_updates_group in itertools.groupby(status_updates, key=lambda s: s.created_at.date()):
        grouped_status_updates[day] = list(status_updates_group)

    day = max(grouped_status_updates.keys())
    while day >= min(grouped_status_updates.keys()):
        updates_html += block_header(nice_date(day))
        if grouped_status_updates.get(day):
            updates_html += status_update_group_as_html(grouped_status_updates.get(day), group_by_project=True)

        day -= timedelta(days=1)

    msg.set_content(f'''
    <!DOCTYPE html>
    <html>
        <body style="background-color:{EMAIL_BG_COLOG};font-size:{FONT_SIZE};">
            <div style="margin:0px auto;max-width:{EMAIL_BLOCK_WIDTH};padding:0px;">
                <div style="height:40px;"></div>
                {email_header("Your digest from Share!")}
                <div style="background-color:{EMAIL_CONTENT_BG_COLOG};padding:10px">
                    {updates_html}
                </div>
                <div style="height:40px;"></div>
            </div>
        </body>
    </html>
    ''', subtype='html')
    return msg
