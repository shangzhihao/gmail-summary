"""OpenAI-compatible API client wrapper."""

from __future__ import annotations

from collections.abc import Iterable

from openai import AsyncOpenAI, OpenAI
from tenacity import (
    AsyncRetrying,
    RetryError,
    Retrying,
    stop_after_attempt,
    wait_exponential,
)

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3-max"


class OpenAIClient:
    """Client responsible for interacting with an OpenAI-compatible LLM."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
    ) -> None:
        """Instantiate the OpenAI-compatible client."""
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def summarize(
        self, messages: Iterable[dict[str, str]], *, max_tokens: int, temperature: float
    ) -> str:
        """Create a chat completion and return the summary text."""
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=8),
                reraise=True,
            ):
                with attempt:
                    return self._summarize_once(
                        list(messages),
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
            raise RuntimeError("LLM summarization failed after retries.")
        except RetryError as error:  # pragma: no cover - defensive
            raise RuntimeError("LLM summarization failed after retries.") from error

    def _summarize_once(
        self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float
    ) -> str:
        """Issue a single request to the OpenAI-compatible API."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body={"enable_thinking": False},
        )
        choice = response.choices[0]
        content = choice.message.content
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            return " ".join(
                part["text"] for part in content if isinstance(part, dict)
            ).strip()

        raise RuntimeError("Unexpected response format from the LLM API.")

    async def summarize_async(
        self,
        messages: Iterable[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Create a chat completion asynchronously and return the summary text."""
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=8),
                reraise=True,
            ):
                with attempt:
                    return await self._summarize_once_async(
                        list(messages),
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
            raise RuntimeError("LLM summarization failed after retries.")
        except RetryError as error:  # pragma: no cover - defensive
            raise RuntimeError("LLM summarization failed after retries.") from error

    async def _summarize_once_async(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Issue a single async request to the OpenAI-compatible API."""
        response = await self._async_client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body={"enable_thinking": False},
        )
        choice = response.choices[0]
        content = choice.message.content
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            return " ".join(
                part["text"] for part in content if isinstance(part, dict)
            ).strip()

        raise RuntimeError("Unexpected response format from the LLM API.")
