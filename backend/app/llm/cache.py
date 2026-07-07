import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import LLMCacheEntry
from .base import CACHEABLE, JobType, Message


def cache_key(provider: str, model: str, job_type: JobType, messages: list[Message], schema: dict | None) -> str:
    blob = json.dumps(
        {
            "provider": provider,
            "model": model,
            "job": job_type.value,
            "messages": [m.to_dict() for m in messages],
            "schema": schema,
        },
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()


async def cached_complete_json(
    db: Session, choice, job_type: JobType, messages: list[Message], schema: dict, max_tokens: int = 4096
) -> dict:
    """complete_json with a DB cache in front — nothing is generated twice."""
    key = None
    if job_type in CACHEABLE:
        key = cache_key(choice.provider_name, choice.model, job_type, messages, schema)
        hit = db.scalar(select(LLMCacheEntry).where(LLMCacheEntry.cache_key == key))
        if hit is not None:
            return json.loads(hit.response)

    result = await choice.provider.complete_json(messages, choice.model, schema, max_tokens=max_tokens)

    if key is not None:
        db.add(
            LLMCacheEntry(
                cache_key=key,
                job_type=job_type.value,
                provider=choice.provider_name,
                model=choice.model,
                response=json.dumps(result),
            )
        )
        db.commit()
    return result
