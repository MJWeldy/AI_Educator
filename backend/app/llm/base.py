"""Provider abstraction: everything the app asks of an LLM goes through this
interface, so Ollama (free, local) and Claude (paid, stronger) are swappable
per job type."""

import enum
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol


class JobType(str, enum.Enum):
    hint = "hint"
    explain_mistake = "explain_mistake"
    lesson_text = "lesson_text"
    extra_problems = "extra_problems"
    ingest_structure = "ingest_structure"
    ingest_topics = "ingest_topics"
    topic_mapping = "topic_mapping"
    ingest_lesson = "ingest_lesson"
    ingest_problems = "ingest_problems"


# Job types whose outputs are deterministic-enough to cache in the DB.
CACHEABLE = {
    JobType.lesson_text,
    JobType.extra_problems,
    JobType.ingest_structure,
    JobType.ingest_topics,
    JobType.topic_mapping,
    JobType.ingest_lesson,
    JobType.ingest_problems,
}


class LLMError(Exception):
    pass


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class Message:
    role: str  # system | user | assistant
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class LLMProvider(Protocol):
    name: str

    async def complete(self, messages: list[Message], model: str, max_tokens: int = 2048) -> LLMResponse: ...

    async def complete_json(
        self, messages: list[Message], model: str, schema: dict, max_tokens: int = 4096
    ) -> dict: ...

    def stream(
        self, messages: list[Message], model: str, max_tokens: int = 1024
    ) -> AsyncIterator[str]: ...
