"""Chooses (provider, model) per job type from settings.

Shipped defaults: Ollama with gpt-oss:20b for everything. Saving an Anthropic
key lets the user flip ingestion-grade jobs to Claude in Settings; those
overrides live in the `llm.overrides` setting as {job_type: {provider, model}}.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..models import SettingRow
from . import anthropic_provider
from .base import JobType, LLMError, LLMProvider
from .ollama import OllamaProvider

DEFAULT_OLLAMA_MODEL = "gpt-oss:20b"
INGEST_JOBS = {
    JobType.ingest_structure,
    JobType.ingest_topics,
    JobType.topic_mapping,
    JobType.ingest_lesson,
    JobType.ingest_problems,
}


def get_setting(db: Session, key: str, default=None):
    row = db.get(SettingRow, key)
    return row.value if row is not None else default


def set_setting(db: Session, key: str, value) -> None:
    row = db.get(SettingRow, key)
    if row is None:
        db.add(SettingRow(key=key, value=value))
    else:
        row.value = value


@dataclass
class Choice:
    provider: LLMProvider
    provider_name: str
    model: str


def resolve(db: Session, job_type: JobType) -> Choice:
    overrides = get_setting(db, "llm.overrides", {}) or {}
    override = overrides.get(job_type.value, {})
    provider_name = override.get("provider") or get_setting(db, "llm.default_provider", "ollama")
    if provider_name == "anthropic":
        api_key = get_setting(db, "llm.anthropic_api_key")
        if not api_key:
            if job_type in INGEST_JOBS:
                raise LLMError("Claude is selected for this job but no API key is saved")
            provider_name = "ollama"  # graceful fallback for interactive jobs only
        else:
            model = override.get("model") or get_setting(
                db,
                "llm.anthropic_model",
                anthropic_provider.INGEST_MODEL if job_type in INGEST_JOBS else anthropic_provider.DEFAULT_MODEL,
            )
            return Choice(anthropic_provider.AnthropicProvider(api_key), "anthropic", model)
    model = override.get("model") or get_setting(db, "llm.ollama_model", DEFAULT_OLLAMA_MODEL)
    return Choice(OllamaProvider(), "ollama", model)
