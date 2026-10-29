"""Provider-independent LLM answer generation.

The rest of the application depends only on :func:`generate_answer`; the
concrete provider is selected through ``RAG_LLM_PROVIDER``:

* ``""`` (default) — not configured; generation fails with the safe message
  "AI provider is not configured.".  No fake answer is ever produced.
* ``openai`` — any OpenAI-compatible ``/chat/completions`` endpoint.  Requires
  ``RAG_OPENAI_API_KEY`` (shared with the embedding provider) supplied via the
  environment.

API keys are never hard-coded.  Tests inject a mock provider.
"""

from typing import Optional, Protocol

from app.config.settings import get_settings
from app.services.rag import prompts


class LLMError(Exception):
    """Base class for safe, user-presentable LLM failures."""


class LLMConfigurationError(LLMError):
    """Raised when no usable LLM provider is configured."""


class LLMUnavailableError(LLMError):
    """Raised for transient provider/network failures."""


class LLMProvider(Protocol):
    model_name: str

    def generate(self, system: str, user: str) -> str: ...


class OpenAILLMProvider:
    """OpenAI-compatible chat-completions adapter built on httpx."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model_name: str,
        timeout: float = 30.0,
        temperature: float = 0.0,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name or "gpt-4o-mini"
        self.timeout = timeout
        self.temperature = temperature

    def generate(self, system: str, user: str) -> str:
        import httpx

        try:
            response = httpx.post(
                f"{self.api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "temperature": self.temperature,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
                timeout=self.timeout,
            )
        except Exception as exc:  # network/timeout — never leak internals
            raise LLMUnavailableError("AI service is currently unavailable.") from exc

        if response.status_code == 429 or response.status_code >= 500:
            raise LLMUnavailableError("AI service is currently unavailable.")

        try:
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise LLMError("Unable to generate an AI response right now.") from exc

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Unable to generate an AI response right now.") from exc

        if not content or not str(content).strip():
            raise LLMError("Unable to generate an AI response right now.")
        return str(content).strip()


def get_llm_provider() -> LLMProvider:
    """Resolve the configured LLM provider or raise a safe error."""
    settings = get_settings()
    provider = (settings.rag_llm_provider or "").strip().lower()

    if provider == "openai":
        if not settings.rag_openai_api_key:
            raise LLMConfigurationError("AI provider is not configured.")
        return OpenAILLMProvider(
            api_url=settings.rag_openai_api_url,
            api_key=settings.rag_openai_api_key,
            model_name=settings.rag_llm_model,
            timeout=settings.rag_openai_timeout_seconds,
            temperature=settings.rag_llm_temperature,
        )
    raise LLMConfigurationError("AI provider is not configured.")


def generate_answer(
    query: str,
    context_items: list[dict],
    system_instructions: Optional[str] = None,
    provider: Optional[LLMProvider] = None,
) -> dict:
    """Generate a grounded answer from the supplied context.

    Returns ``{"answer": str, "model": str}``.  Raises a subclass of
    :class:`LLMError` on any failure so the caller can respond safely.
    """
    active = provider or get_llm_provider()
    system = system_instructions or prompts.GROUNDING_SYSTEM_INSTRUCTIONS
    user = prompts.build_user_prompt(query, context_items)
    answer = active.generate(system, user)
    return {"answer": answer, "model": active.model_name}
