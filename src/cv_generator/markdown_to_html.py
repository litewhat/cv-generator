import markdown

_EXTENSIONS = ["fenced_code", "tables", "sane_lists"]


def markdown_to_html(markdown_text: str) -> str:
    return markdown.markdown(markdown_text, extensions=_EXTENSIONS)
