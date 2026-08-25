_SCALAR_TYPES = (str, int, float, bool)
_HEADER_SCALARS = ("name", "title", "email", "phone", "location")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    import yaml

    working = text[1:] if text.startswith("\ufeff") else text
    lines = working.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        raise ValueError("Unclosed YAML frontmatter")

    yaml_block = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :])

    if not yaml_block.strip():
        return {}, body

    try:
        loaded = yaml.safe_load(yaml_block)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML frontmatter: {exc}") from exc

    if loaded is None:
        return {}, body
    if not isinstance(loaded, dict):
        raise ValueError("Frontmatter must be a mapping")
    _check_types(loaded)
    return loaded, body


def _is_scalar(value: object) -> bool:
    return isinstance(value, _SCALAR_TYPES)


def _check_types(meta: dict) -> None:
    for key in _HEADER_SCALARS:
        if key not in meta or meta[key] is None:
            continue
        if not _is_scalar(meta[key]):
            raise ValueError(f"Frontmatter field '{key}' must be a scalar")

    if "links" not in meta or meta["links"] is None:
        return
    links = meta["links"]
    if not isinstance(links, dict):
        raise ValueError("Frontmatter field 'links' must be a mapping")
    for label, url in links.items():
        if not _is_scalar(label) or not _is_scalar(url):
            raise ValueError("Frontmatter field 'links' must be a mapping of scalars")
