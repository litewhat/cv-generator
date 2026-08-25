from importlib.resources import files

from jinja2 import Environment
from markupsafe import Markup


def html_document(content: str, title: str, meta: dict | None = None) -> str:
    template_text = (
        files("cv_generator") / "templates" / "elegant-v1.html.j2"
    ).read_text(encoding="utf-8")
    env = Environment(autoescape=True)
    template = env.from_string(template_text)
    return template.render(
        content=Markup(content),
        title=title,
        meta=meta or {},
    )
