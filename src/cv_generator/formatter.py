from __future__ import annotations

import re
from importlib.resources import files

from jinja2 import Environment
from markupsafe import Markup, escape

from cv_generator.document import Document, Node, NodeContent
from lib.convert import markdown_to_html

_TABLE_DELIMITER = re.compile(
    r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$"
)
_SINGLE_P = re.compile(r"^\s*<p>(.*)</p>\s*$", re.DOTALL)


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


def _kind(child: NodeContent) -> str:
    if isinstance(child, Node):
        return "node"
    stripped_start = child.lstrip()
    if stripped_start.startswith("```") or stripped_start.startswith("~~~"):
        return "fence"
    if child.strip() == "---":
        return "hr"
    if any(_TABLE_DELIMITER.match(line) for line in child.splitlines()):
        return "table"
    return "plain"


def _unwrap_single_p(fragment: str) -> str:
    match = _SINGLE_P.match(fragment)
    if match is not None:
        return match.group(1)
    return fragment


def _render_children(children: tuple[NodeContent, ...], depth: int) -> str:
    parts: list[str] = []
    pending: list[str] = []

    def flush() -> None:
        if not pending:
            return
        if depth == 0:
            parts.extend(markdown_to_html(leaf) for leaf in pending)
        else:
            items = [
                f"<li>{_unwrap_single_p(markdown_to_html(leaf))}</li>"
                for leaf in pending
            ]
            parts.append("<ul>" + "".join(items) + "</ul>")
        pending.clear()

    for child in children:
        kind = _kind(child)
        if kind == "plain":
            pending.append(child)
            continue
        flush()
        if kind == "node":
            assert isinstance(child, Node)
            parts.append(_render_node(child, depth + 1))
        else:
            assert isinstance(child, str)
            parts.append(markdown_to_html(child))
    flush()
    return "".join(parts)


def _render_node(node: Node, depth: int) -> str:
    level = min(depth, 6)
    heading = f"<h{level}>{escape(node.name)}</h{level}>"
    return heading + _render_children(node.nodes, depth)
