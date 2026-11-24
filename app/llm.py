"""
app/llm.py
Provider wrapper for the AapleSeva chat assistant.

Supports two providers, both through their OpenAI-compatible Chat Completions
endpoint so the request shape is identical and no provider SDK is needed:

    groq   -> https://api.groq.com/openai/v1/chat/completions
    gemini -> https://generativelanguage.googleapis.com/v1beta/openai/chat/completions

Keys are read from the environment. Put them in a ``.env`` file (see
``.env.example``); ``load_dotenv()`` below picks it up automatically. The
``.env`` file is gitignored and never committed.

A mock mode (``LLM_MOCK=1``) returns a canned JSON response without touching the
network, so the ``/chat`` endpoint can be developed and demoed without API keys.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is optional but installed
    pass

import requests


_PROVIDER_CONFIG = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "model_env": "GROQ_MODEL",
        "default_model": "llama-3.3-70b-versatile",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "key_env": "GEMINI_API_KEY",
        "model_env": "GEMINI_MODEL",
        "default_model": "gemini-3.5-flash-lite",
    },
}

#: Tuple form for error messages / display.
PROVIDERS = tuple(_PROVIDER_CONFIG)

# HTTP statuses worth retrying: rate limit and transient server/gateway errors.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3


@dataclass
class LLMResponse:
    """The text a provider returned, plus provenance for the API response."""

    text: str
    provider: str
    model: str
    mock: bool = False


class LLMProvider:
    """Call a chat-completions endpoint for one provider."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 60,
    ):
        self.provider = (provider or os.getenv("LLM_PROVIDER") or "groq").lower()
        if self.provider not in _PROVIDER_CONFIG:
            raise ValueError(
                f"unknown provider {self.provider!r}; choose one of {PROVIDERS}"
            )
        cfg = _PROVIDER_CONFIG[self.provider]
        self.base_url = (
            base_url
            or os.getenv(f"{self.provider.upper()}_BASE_URL")
            or cfg["base_url"]
        ).rstrip("/")
        self.model = (
            model
            or os.getenv("LLM_MODEL")
            or os.getenv(cfg["model_env"])
            or cfg["default_model"]
        )
        self.api_key = api_key or os.getenv(cfg["key_env"]) or ""
        self.timeout = timeout
        self.mock = os.getenv("LLM_MOCK", "0").lower() in ("1", "true", "yes")

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 600,
    ) -> LLMResponse:
        """Send ``messages`` to the provider and return its text reply."""
        if self.mock:
            return LLMResponse(
                text=_mock_answer(messages),
                provider=self.provider,
                model=self.model,
                mock=True,
            )
        if not self.api_key:
            raise RuntimeError(
                f"no API key for provider {self.provider!r}. "
                f"Set {self.provider.upper()}_API_KEY in your environment/.env, "
                f"or set LLM_MOCK=1 for offline testing."
            )

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Try the main model first, then an optional fallback model.
        models = [self.model]
        fallback = os.getenv("LLM_FALLBACK_MODEL")
        if fallback and fallback != self.model:
            models.append(fallback)

        last_exc: Exception | None = None
        for model in models:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            # Retry transient failures (rate limit, overload, gateway errors,
            # dropped connections) with exponential backoff: 1s, 2s, 4s.
            for attempt in range(_MAX_RETRIES):
                try:
                    resp = requests.post(
                        url, headers=headers, json=payload, timeout=self.timeout
                    )
                except (requests.ConnectionError, requests.Timeout) as exc:
                    last_exc = exc
                else:
                    if resp.status_code not in _RETRYABLE_STATUS:
                        resp.raise_for_status()
                        text = resp.json()["choices"][0]["message"]["content"]
                        return LLMResponse(text=text, provider=self.provider, model=model)
                    last_exc = requests.HTTPError(
                        f"{resp.status_code} from {self.provider} ({model})",
                        response=resp,
                    )
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(2**attempt)

        raise RuntimeError(
            f"{self.provider} is unavailable after retries "
            f"(tried {', '.join(models)}): {last_exc}"
        )


def get_provider(provider: str | None = None, **kwargs) -> LLMProvider:
    """Factory: build a provider from config/env, with optional overrides."""
    return LLMProvider(provider=provider, **kwargs)


def _mock_answer(messages: list[dict]) -> str:
    """Return a deterministic canned JSON reply for offline development.

    It reflects the last user message so the /chat parse path can be exercised
    end to end without any API key.
    """
    user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break
    snippet = " ".join(user_msg.split())[:90]
    return json.dumps(
        {
            "answer": (
                "[mock] I would answer from the retrieved AapleSeva records. "
                f"Question was: {snippet}"
            ),
            "confidence": "medium",
            "follow_up": (
                "Could you tell me your district or taluka so I can point you "
                "to the right office?"
            ),
        },
        ensure_ascii=False,
    )
