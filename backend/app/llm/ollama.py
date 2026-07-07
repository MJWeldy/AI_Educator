import json
import re
from collections.abc import AsyncIterator

import httpx

from ..config import settings
from .base import LLMError, LLMResponse, Message

THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_think(text: str) -> str:
    """deepseek-r1 wraps its reasoning in <think> tags."""
    return THINK_RE.sub("", text).strip()


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")

    async def _chat(self, payload: dict, timeout: float = 300.0) -> dict:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(f"{self.base_url}/api/chat", json=payload)
                r.raise_for_status()
                return r.json()
        except httpx.HTTPError as e:
            raise LLMError(f"Ollama request failed: {e}") from e

    async def complete(self, messages: list[Message], model: str, max_tokens: int = 2048) -> LLMResponse:
        data = await self._chat(
            {
                "model": model,
                "messages": [m.to_dict() for m in messages],
                "stream": False,
                "options": {"num_predict": max_tokens},
            }
        )
        return LLMResponse(
            text=_strip_think(data.get("message", {}).get("content", "")),
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
        )

    async def complete_json(
        self, messages: list[Message], model: str, schema: dict, max_tokens: int = 4096
    ) -> dict:
        """Constrained decoding via Ollama's `format` param, with one repair retry."""
        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            "format": schema,
            "options": {"num_predict": max_tokens},
        }
        data = await self._chat(payload)
        raw = _strip_think(data.get("message", {}).get("content", ""))
        try:
            return json.loads(raw)
        except json.JSONDecodeError as first_error:
            repair = messages + [
                Message("assistant", raw),
                Message("user", f"That was not valid JSON ({first_error}). Respond again with only valid JSON matching the schema."),
            ]
            payload["messages"] = [m.to_dict() for m in repair]
            data = await self._chat(payload)
            raw = _strip_think(data.get("message", {}).get("content", ""))
            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                raise LLMError(f"Ollama returned invalid JSON twice: {e}") from e

    async def stream(
        self, messages: list[Message], model: str, max_tokens: int = 1024
    ) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
            "options": {"num_predict": max_tokens},
        }
        in_think = False
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        piece = chunk.get("message", {}).get("content", "")
                        # crude <think> filter across chunk boundaries
                        if "<think>" in piece:
                            in_think = True
                            piece = piece.split("<think>")[0]
                        if "</think>" in piece:
                            in_think = False
                            piece = piece.split("</think>")[-1]
                        elif in_think:
                            continue
                        if piece:
                            yield piece
        except httpx.HTTPError as e:
            raise LLMError(f"Ollama stream failed: {e}") from e

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                return [m["name"] for m in r.json().get("models", [])]
        except httpx.HTTPError:
            return []
