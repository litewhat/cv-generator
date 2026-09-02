from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal

from cv_generator.parser import ParseError as ParseError
from cv_generator.parser import from_markdown

type SocialProfileType = Literal["github", "linkedin"]
type NodeContent = Node | str


class ValidationError(Exception):
    """Parsed mapping does not match the content schema."""


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _require_non_empty_str(raw: Mapping[object, object], key: str) -> str:
    if key not in raw:
        raise ValidationError(f"Missing field '{key}'")
    value = raw[key]
    if not isinstance(value, str):
        raise ValidationError(f"Field '{key}' must be a string")
    stripped = value.strip()
    if not stripped:
        raise ValidationError(f"Field '{key}' must be a non-empty string")
    return stripped


@dataclass(frozen=True, slots=True)
class SocialProfile:
    TYPES: ClassVar[frozenset[SocialProfileType]] = frozenset({"github", "linkedin"})

    type: SocialProfileType
    url: str

    @classmethod
    def from_mapping(cls, raw: object) -> SocialProfile:
        if not isinstance(raw, Mapping):
            raise ValidationError("Social profile must be a mapping")
        profile_type = raw.get("type")
        if profile_type not in cls.TYPES:
            raise ValidationError(f"Unsupported social profile type: {profile_type!r}")
        url = raw.get("url")
        if not isinstance(url, str):
            raise ValidationError("Field 'url' must be a string")
        return cls(type=profile_type, url=url)


@dataclass(frozen=True, slots=True)
class Node:
    name: str
    nodes: tuple[NodeContent, ...]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> Node:
        name = _require_non_empty_str(raw, "name")
        return cls(name=name, nodes=_parse_nodes(raw.get("nodes")))


@dataclass(frozen=True, slots=True)
class Content:
    HEADER_FIELDS: ClassVar[tuple[str, ...]] = (
        "name",
        "title",
        "email",
        "phone_number",
        "location",
    )

    name: str
    title: str
    email: str
    phone_number: str
    location: str
    social_profiles: tuple[SocialProfile, ...]
    nodes: tuple[NodeContent, ...]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> Content:
        if not isinstance(raw, Mapping):
            raise ValidationError("Expected a mapping")
        header = {key: _require_non_empty_str(raw, key) for key in cls.HEADER_FIELDS}
        return cls(
            name=header["name"],
            title=header["title"],
            email=header["email"],
            phone_number=header["phone_number"],
            location=header["location"],
            social_profiles=_parse_social_profiles(raw.get("social_profiles")),
            nodes=_parse_nodes(raw.get("nodes")),
        )


@dataclass(frozen=True, slots=True)
class Document:
    source_format: Literal["markdown"]
    content: Content

    @staticmethod
    def parse(
        text: str,
        *,
        format: Literal["markdown"] = "markdown",
    ) -> Document:
        if format != "markdown":
            raise ValueError(f"Unsupported source_format: {format!r}")
        data = from_markdown(text)
        content = Content.from_mapping(data)
        return Document(
            source_format=format,
            content=content,
        )


def _parse_social_profiles(value: object) -> tuple[SocialProfile, ...]:
    if value is None:
        return ()
    if not _is_sequence(value):
        raise ValidationError("Field 'social_profiles' must be a sequence")
    return tuple(SocialProfile.from_mapping(item) for item in value)


def _parse_nodes(value: object) -> tuple[NodeContent, ...]:
    if value is None:
        return ()
    if not _is_sequence(value):
        raise ValidationError("Field 'nodes' must be a sequence")
    return tuple(_parse_node_content(item) for item in value)


def _parse_node_content(value: object) -> NodeContent:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return Node.from_mapping(value)
    raise ValidationError("Node child must be a string or mapping")
