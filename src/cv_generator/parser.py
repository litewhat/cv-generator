import re

import yaml


class ParseError(Exception):
    """Invalid CV source text."""


def from_markdown(text: str) -> dict[str, object]:
    working = text[1:] if text.startswith("\ufeff") else text
    meta, body = _split_frontmatter(working)
    result = _apply_aliases(meta)
    result["nodes"] = _parse_body(body)
    return result


def _split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        raise ParseError("Unclosed YAML frontmatter")
    yaml_block = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :])
    if not yaml_block.strip():
        return {}, body
    try:
        loaded = yaml.safe_load(yaml_block)
    except yaml.YAMLError as exc:
        raise ParseError(f"Invalid YAML frontmatter: {exc}") from exc
    if loaded is None:
        return {}, body
    if not isinstance(loaded, dict):
        raise ParseError("Frontmatter must be a mapping")
    return loaded, body


def _apply_aliases(meta: dict[str, object]) -> dict[str, object]:
    result = dict(meta)
    if "phone" in result:
        result["phone_number"] = result.pop("phone")
    if "links" in result:
        result["social_profiles"] = _normalize_links(result.pop("links"))
    return result


def _normalize_links(links: object) -> object:
    if links is None or links == {}:
        return []
    if isinstance(links, dict):
        return [{"type": key, "url": value} for key, value in links.items()]
    return links


_ATX_START = re.compile(r"^(#{1,6})(?:\s|$)")
_ATX_LINE = re.compile(r"^(#{1,6})(?:[ \t]+(.*))?$")
_CLOSING_HASHES = re.compile(r"[ \t]+#+$")
_LIST_ITEM = re.compile(r"^[ \t]*(?:[-*+]|\d+\.)[ \t]+(.*)$")
_FENCE = re.compile(r"^([ \t]*)(```+|~~~+)")


def _parse_body(body: str) -> list[object]:
    root: list[object] = []
    stack: list[tuple[int, str, list[object]]] = []

    def close_until(level: int) -> None:
        while stack and stack[-1][0] >= level:
            _level, name, children = stack.pop()
            node = {"name": name, "nodes": children}
            if stack:
                stack[-1][2].append(node)
            else:
                root.append(node)

    def _is_fence_leaf(text: str) -> bool:
        stripped = text.lstrip()
        return stripped.startswith("```") or stripped.startswith("~~~")

    def _is_thematic_leaf(text: str) -> bool:
        return text.strip() == "---"

    prev_kind: str | None = None
    for kind, payload in _iter_blocks(body.splitlines()):
        if kind == "heading":
            level, name = payload
            if name == "":
                raise ParseError("Empty heading name")
            close_until(level)
            stack.append((level, name, []))
            prev_kind = "heading"
        elif kind == "list":
            if stack:
                stack[-1][2].append(payload)
            else:
                root.append(payload)
            prev_kind = "list"
        else:
            leaf = payload
            is_paragraph = not _is_fence_leaf(leaf) and not _is_thematic_leaf(leaf)
            if is_paragraph and prev_kind == "list" and len(stack) > 1:
                _level, name, children = stack.pop()
                node = {"name": name, "nodes": children}
                if stack:
                    stack[-1][2].append(node)
                else:
                    root.append(node)
            if stack:
                stack[-1][2].append(leaf)
            else:
                root.append(leaf)
            prev_kind = "leaf"
    close_until(0)
    return root


def _heading_name(line: str) -> tuple[int, str] | None:
    if not _ATX_START.match(line):
        return None
    match = _ATX_LINE.match(line)
    if match is None:
        return None
    level = len(match.group(1))
    rest = match.group(2) or ""
    name = _CLOSING_HASHES.sub("", rest).strip()
    return level, name


def _iter_blocks(lines: list[str]):
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        fence = _FENCE.match(line)
        if fence is not None:
            marker_char = fence.group(2)[0]
            marker_len = len(fence.group(2))
            chunk = [line]
            i += 1
            while i < n:
                chunk.append(lines[i])
                closer = _FENCE.match(lines[i])
                if (
                    closer is not None
                    and closer.group(2)[0] == marker_char
                    and len(closer.group(2)) >= marker_len
                ):
                    i += 1
                    break
                i += 1
            yield "leaf", "\n".join(chunk)
            continue

        heading = _heading_name(line)
        if heading is not None:
            yield "heading", heading
            i += 1
            continue

        list_item = _LIST_ITEM.match(line)
        if list_item is not None:
            yield "list", line
            i += 1
            continue

        chunk = [line]
        i += 1
        while i < n and lines[i].strip():
            if (
                _FENCE.match(lines[i]) is not None
                or _heading_name(lines[i]) is not None
                or _LIST_ITEM.match(lines[i]) is not None
            ):
                break
            chunk.append(lines[i])
            i += 1
        yield "leaf", "\n".join(chunk)
