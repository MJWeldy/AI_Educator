import json

import pytest
from sqlalchemy import select

from app.llm import router
from app.llm.base import JobType, LLMResponse, Message
from app.llm.cache import cached_complete_json
from app.models import LLMCacheEntry, Topic


class FakeProvider:
    name = "fake"

    def __init__(self, json_result=None):
        self.json_result = json_result or {"ok": True}
        self.calls = 0

    async def complete(self, messages, model, max_tokens=2048):
        self.calls += 1
        return LLMResponse(text="fake text")

    async def complete_json(self, messages, model, schema, max_tokens=4096):
        self.calls += 1
        return self.json_result

    async def stream(self, messages, model, max_tokens=1024):
        self.calls += 1
        for piece in ["fake ", "stream"]:
            yield piece


def fake_choice(json_result=None):
    provider = FakeProvider(json_result)
    return router.Choice(provider=provider, provider_name="fake", model="fake-model")


async def test_cache_hit_and_miss(db):
    choice = fake_choice({"value": 42})
    messages = [Message("user", "hello")]
    schema = {"type": "object"}

    out1 = await cached_complete_json(db, choice, JobType.lesson_text, messages, schema)
    out2 = await cached_complete_json(db, choice, JobType.lesson_text, messages, schema)
    assert out1 == out2 == {"value": 42}
    assert choice.provider.calls == 1, "second call must be served from cache"

    rows = db.scalars(select(LLMCacheEntry)).all()
    assert len(rows) == 1
    assert json.loads(rows[0].response) == {"value": 42}


async def test_uncacheable_jobs_bypass(db):
    choice = fake_choice()
    messages = [Message("user", "hint please")]
    await cached_complete_json(db, choice, JobType.hint, messages, {})
    await cached_complete_json(db, choice, JobType.hint, messages, {})
    assert choice.provider.calls == 2
    assert db.scalars(select(LLMCacheEntry)).all() == []


def test_router_defaults_to_ollama(db):
    choice = router.resolve(db, JobType.hint)
    assert choice.provider_name == "ollama"
    assert choice.model == router.DEFAULT_OLLAMA_MODEL


def test_router_ingestion_requires_key(db):
    router.set_setting(db, "llm.overrides", {"ingest_topics": {"provider": "anthropic"}})
    db.commit()
    with pytest.raises(Exception, match="no API key"):
        router.resolve(db, JobType.ingest_topics)


def test_router_hint_falls_back_without_key(db):
    router.set_setting(db, "llm.default_provider", "anthropic")
    db.commit()
    choice = router.resolve(db, JobType.hint)
    assert choice.provider_name == "ollama", "interactive jobs degrade gracefully"


async def test_generate_lesson_with_fake_provider(seeded_db, monkeypatch):
    from app.content import llm_content

    payload = {
        "content_md": "A lesson about things. $x + 1$",
        "worked_examples": [
            {"problem_md": "p1", "solution_md": "s1"},
            {"problem_md": "p2", "solution_md": "s2"},
        ],
    }
    monkeypatch.setattr(llm_content.router, "resolve", lambda db, jt: fake_choice(payload))

    # rounding-estimation has no seed lesson.
    topic = seeded_db.scalar(select(Topic).where(Topic.slug == "rounding-estimation"))
    lesson = await llm_content.generate_lesson(seeded_db, topic)
    assert lesson.source == "llm"
    assert lesson.content_md.startswith("A lesson")
    assert len(lesson.worked_examples) == 2

    # Second call returns the stored row without regenerating.
    again = await llm_content.generate_lesson(seeded_db, topic)
    assert again.id == lesson.id
