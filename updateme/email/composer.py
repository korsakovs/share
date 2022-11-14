import itertools

from datetime import date, timedelta
from email.message import EmailMessage
from markdown import markdown
from typing import List, Dict

from updateme.core.model import StatusUpdate
from updateme.core.utils import join_strings_with_commas


def hsc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def day_as_html(day: date):
    return f"""
        <div class="share-day-header" style="margin:0px;padding:0px;background-color:#fff;">
            <h2>{day.strftime("%A, %B %-d")}</h2>
        </div>
"""


def status_update_as_html(status_update: StatusUpdate) -> str:
    def fix_links(m: str):
        # This is ugly and buggy and needs to be improved!
        result = []
        url, url_text = "", ""
        url_started, url_text_started = False, False
        for pos, ch in enumerate(m):
            if url_started:
                if ch == "|":
                    url_text_started = True
                elif ch == ">":
                    result.append(f"[{url_text}]({url})")
                    url_started = False
                elif url_text_started:
                    url_text += ch
                else:
                    url += ch
                continue
            if ch == "<" and m[pos:pos+5] == "<http":
                url, url_text = "", ""
                url_started = True
                url_text_started = False
                continue
            result.append(ch)
        return "".join(result)
    type_ = status_update.type
    projects = status_update.projects

    if status_update.is_markdown:
        text_str = markdown(fix_links(status_update.text))[3:-4]
        if text_str.startswith("<p>"):
            text_str = text_str[3:]
        if text_str.endswith("</p>"):
            text_str = text_str[-4:]
    else:
        text_str = hsc(status_update.text)

    projects_str = ""
    if status_update.projects:
        projects_str = join_strings_with_commas([hsc(project.name) for project in status_update.projects])

    on_behalf_str = ""
    if status_update.teams:
        on_behalf_str = " on behalf of " \
                        + join_strings_with_commas(["<b>" + hsc(team.name) + "</b>" for team in status_update.teams])\
                        + (" teams" if len(status_update.teams) > 1 else " team")

    attachments_str = ""
    if status_update.images:
        attachments_str = f"""<b>Attachments:</b>
        <ul>
            {"".join(f"<li><a href='{image.url}' target='_blank'>{hsc(image.title or image.filename)}</a>" 
                     + (f" - <i>{hsc(image.description)}</i>" if image.description else "") + "</li>"
                     for image in status_update.images)}
        </ul>
"""

    # Adding a title
    return f"""
    <div style="margin:0px;padding:0px;">
        <div style="padding:5px">
        {"" if not type_ else type_.emoji + f" <b>{type_.name}</b> "}
        {"" if not projects else f"@ {projects_str}"}
        </div>
        <div style="padding:5px">
            <ul>
                <li>
                    {text_str}<br />{attachments_str}
                    <sub>Shared by <b>{hsc(status_update.author_slack_user_name)}</b>{on_behalf_str}</sub>        
                </li>
            </ul>
        </div>
    </div>
"""


def status_update_group_as_html(status_updates: List[StatusUpdate]) -> str:
    return f"""
        <div class="share-status-update-group" style="margin:0px;padding:0px;">
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
        updates_html += day_as_html(day)
        if grouped_status_updates.get(day):
            updates_html += status_update_group_as_html(grouped_status_updates.get(day))

        day -= timedelta(days=1)

    msg.set_content(f'''
    <!DOCTYPE html>
    <html>
        <body style="background-color:#eef;">
            <div style="margin:0px auto;max-width:600px;padding:0px;">
                <div style="height:20px;"></div>
                <div style="background-color:#66f;padding:10px">
                    <h1 style="color:#fff;margin:0px;">Your digest from Share!</h1>
                </div>
                <div class="share-status-updates-content" style="background-color:#fff;padding:10px">
                    {updates_html}
                </div>
                <div style="height:20px;"></div>
            </div>
        </body>
    </html>
    ''', subtype='html')
    return msg
