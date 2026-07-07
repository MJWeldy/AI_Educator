from collections.abc import AsyncIterator

from .base import LLMError, LLMResponse, Message

DEFAULT_MODEL = "claude-sonnet-4-6"
INGEST_MODEL = "claude-opus-4-8"


def _split(messages: list[Message]) -> tuple[str | None, list[dict]]:
    system = None
    rest = []
    for m in messages:
        if m.role == "system":
            system = m.content
        else:
            rest.append(m.to_dict())
    return system, rest


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str):
        from anthropic import AsyncAnthropic

        self.client = AsyncAnthropic(api_key=api_key)

    async def complete(self, messages: list[Message], model: str, max_tokens: int = 2048) -> LLMResponse:
        import anthropic

        system, msgs = _split(messages)
        try:
            resp = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system or anthropic.NOT_GIVEN,
                messages=msgs,
            )
        except anthropic.AnthropicError as e:
            raise LLMError(f"Anthropic request failed: {e}") from e
        text = "".join(b.text for b in resp.content if b.type == "text")
        return LLMResponse(
            text=text,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )

    async def complete_json(
        self, messages: list[Message], model: str, schema: dict, max_tokens: int = 4096
    ) -> dict:
        """Structured output via forced tool use — the schema becomes the tool's
        input schema, so the API guarantees conforming JSON."""
        import anthropic

        system, msgs = _split(messages)
        try:
            resp = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system or anthropic.NOT_GIVEN,
                messages=msgs,
                tools=[
                    {
                        "name": "emit",
                        "description": "Emit the structured result.",
                        "input_schema": schema,
                    }
                ],
                tool_choice={"type": "tool", "name": "emit"},
            )
        except anthropic.AnthropicError as e:
            raise LLMError(f"Anthropic request failed: {e}") from e
        for block in resp.content:
            if block.type == "tool_use":
                return block.input
        raise LLMError("Anthropic response contained no structured output")

    async def stream(
        self, messages: list[Message], model: str, max_tokens: int = 1024
    ) -> AsyncIterator[str]:
        import anthropic

        system, msgs = _split(messages)
        try:
            async with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system or anthropic.NOT_GIVEN,
                messages=msgs,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.AnthropicError as e:
            raise LLMError(f"Anthropic stream failed: {e}") from e
