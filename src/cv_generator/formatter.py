from __future__ import annotations

import re
from importlib.resources import files

from jinja2 import Environment
from markupsafe import Markup, escape

from cv_generator.document import Document, Node, NodeContent
from lib.convert import markdown_to_html

_LIST_ITEM = re.compile(r"^[ \t]*(?:[-*+]|\d+\.)[ \t]+(.*)$")


def to_html(document: Document) -> str:
    content = document.content
    body = _render_children(content.nodes, depth=0)
    template_text = (
        files("cv_generator") / "templates" / "elegant-v1.html.j2"
    ).read_text(encoding="utf-8")
    env = Environment(autoescape=True)
    template = env.from_string(template_text)
    return template.render(
        name=content.name,
        title=content.title,
        email=content.email,
        phone_number=content.phone_number,
        location=content.location,
        social_profiles=content.social_profiles,
        content=Markup(body),
    )


def _render_children(children: tuple[NodeContent, ...], depth: int) -> str:
    parts: list[str] = []
    pending_list: list[str] = []

    def flush_list() -> None:
        if not pending_list:
            return
        parts.append(markdown_to_html("\n".join(pending_list)))
        pending_list.clear()

    for child in children:
        if isinstance(child, Node):
            flush_list()
            parts.append(_render_node(child, depth + 1))
        elif _LIST_ITEM.match(child):
            pending_list.append(child)
        else:
            flush_list()
            parts.append(markdown_to_html(child))
    flush_list()
    return "".join(parts)


def _render_node(node: Node, depth: int) -> str:
    level = min(depth, 6)
    heading = f"<h{level}>{escape(node.name)}</h{level}>"
    return heading + _render_children(node.nodes, depth)
