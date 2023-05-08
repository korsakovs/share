from markdown import markdown


def html_special_chars(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


hsc = html_special_chars


def fix_slack_markdown_links(markdown_str: str):
    # This is ugly and buggy and needs to be improved!
    # The way Slack adds links to the markdown string is not compatible with markdown libraries, so we need to apply
    # a hacky trick to fix this. This trick is not perfect and I doubt that it works perfect for all kind of URLs. We
    # probably need to add some unit tests
    result = []
    url, url_text = "", ""
    skip_until = None
    url_started, url_text_started = False, False
    for pos, ch in enumerate(markdown_str):
        if skip_until and pos < skip_until:
            continue
        if url_started:
            if ch == "|":
                url_text_started = True
            elif ch == "%" and markdown_str[pos:pos+3] == "%7C":
                url_text_started = True
                skip_until = pos + 3
            elif ch == ">":
                result.append(f"[{url_text}]({url})")
                url_started = False
            elif url_text_started:
                url_text += ch
            else:
                url += ch
            continue
        if ch == "<" and markdown_str[pos:pos + 5] == "<http":
            url, url_text = "", ""
            url_started = True
            url_text_started = False
            continue
        result.append(ch)
    return "".join(result)


def slack_markdown_to_html(markdown_str) -> str:
    html_str = markdown(fix_slack_markdown_links(markdown_str))
    if html_str.startswith("<p>") and html_str.endswith("</p>"):
        html_str = html_str[3:-4]
    return html_str
