from dataclasses import dataclass
from typing import Literal

type SocialProfileType = Literal["github", "linkedin"]
type NodeContent = Node | str


class ParseError(Exception):
    """Invalid CV source text."""


@dataclass(frozen=True, slots=True)
class SocialProfile:
    type: SocialProfileType
    url: str


@dataclass(frozen=True, slots=True)
class Node:
    name: str
    nodes: tuple[NodeContent, ...]


@dataclass(frozen=True, slots=True)
class Data:
    name: str
    title: str
    email: str
    phone_number: str
    location: str
    social_profiles: tuple[SocialProfile, ...]
    nodes: tuple[NodeContent, ...]


@dataclass(frozen=True, slots=True)
class Document:
    format: Literal["markdown"]
    data: Data

    @staticmethod
    def parse(text: str, *, format: Literal["markdown"] = "markdown") -> Document:
        if format != "markdown":
            raise ValueError(f"Unsupported format: {format!r}")
        from cv_generator.parse_markdown import parse_markdown

        return Document(format=format, data=parse_markdown(text))

def validate_document(data: dict) -> Document:
    pass
