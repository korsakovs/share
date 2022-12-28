from updateme.email.utils import fix_slack_markdown_links


def test_fix_slack_markdown_links():
    for slack_markdown_url, expected_fixed_markdown_url in (
        ("<https://www.google.com/|test>", "[test](https://www.google.com/)"),
        ("<https://www.google.com/search?q=test|test>",
            "[test](https://www.google.com/search?q=test)"),
    ):
        print(fix_slack_markdown_links(slack_markdown_url))
        assert fix_slack_markdown_links(slack_markdown_url) == expected_fixed_markdown_url


