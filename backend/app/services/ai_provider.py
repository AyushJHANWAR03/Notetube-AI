"""
AI Provider abstraction with Groq primary and OpenAI fallback.

Groq provides ultra-fast inference (~10x faster than OpenAI) at lower cost.
OpenAI serves as a reliable fallback when Groq is unavailable or rate-limited.
"""
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import httpx
from openai import OpenAI

from app.core.config import settings


class ProviderName(str, Enum):
    GROQ = "groq"
    OPENAI = "openai"


@dataclass
class AIResponse:
    """Standardized AI response across providers."""
    content: str
    provider: ProviderName
    model: str
    tokens_used: int
    raw_response: Optional[Dict[str, Any]] = None


class AIProviderError(Exception):
    """Custom exception for AI provider errors."""
    pass


class GroqProvider:
    """Groq provider for ultra-fast LLM inference."""

    BASE_URL = "https://api.groq.com/openai/v1"

    # Model mappings - map our model names to Groq equivalents
    MODEL_MAP = {
        "gpt-4o-mini": "llama-3.3-70b-versatile",  # Best for structured output
        "gpt-3.5-turbo": "llama-3.1-8b-instant",   # Fast, cheap for simple tasks
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=120.0
            )
        return self._client

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.5,
        max_tokens: int = 2000,
        json_mode: bool = False
    ) -> AIResponse:
        """Generate completion using Groq API."""
        groq_model = self.MODEL_MAP.get(model, "llama-3.3-70b-versatile")

        payload = {
            "model": groq_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)

            return AIResponse(
                content=content,
                provider=ProviderName.GROQ,
                model=groq_model,
                tokens_used=tokens,
                raw_response=data
            )
        except httpx.HTTPStatusError as e:
            raise AIProviderError(f"Groq API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise AIProviderError(f"Groq request failed: {str(e)}")


class OpenAIProvider:
    """OpenAI provider as fallback."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.5,
        max_tokens: int = 2000,
        json_mode: bool = False
    ) -> AIResponse:
        """Generate completion using OpenAI API."""
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0

            return AIResponse(
                content=content,
                provider=ProviderName.OPENAI,
                model=model,
                tokens_used=tokens
            )
        except Exception as e:
            raise AIProviderError(f"OpenAI request failed: {str(e)}")


class AIProvider:
    """
    Unified AI provider with automatic fallback.

    Primary: Groq (fast, cheap)
    Fallback: OpenAI (reliable)
    """

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        self.groq_api_key = groq_api_key or getattr(settings, 'GROQ_API_KEY', None)
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY

        self._groq = None
        self._openai = None

    @property
    def groq(self) -> Optional[GroqProvider]:
        if self._groq is None and self.groq_api_key:
            self._groq = GroqProvider(self.groq_api_key)
        return self._groq

    @property
    def openai(self) -> Optional[OpenAIProvider]:
        if self._openai is None and self.openai_api_key:
            self._openai = OpenAIProvider(self.openai_api_key)
        return self._openai

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.5,
        max_tokens: int = 2000,
        json_mode: bool = False,
        prefer_provider: Optional[ProviderName] = None
    ) -> AIResponse:
        """
        Generate completion with automatic fallback.

        Tries Groq first (if available), falls back to OpenAI on failure.
        """
        providers_to_try = []

        if prefer_provider == ProviderName.OPENAI:
            if self.openai:
                providers_to_try.append(("openai", self.openai))
            if self.groq:
                providers_to_try.append(("groq", self.groq))
        else:
            # Default: Groq first, OpenAI fallback
            if self.groq:
                providers_to_try.append(("groq", self.groq))
            if self.openai:
                providers_to_try.append(("openai", self.openai))

        if not providers_to_try:
            raise AIProviderError("No AI providers configured. Set GROQ_API_KEY or OPENAI_API_KEY.")

        last_error = None
        for provider_name, provider in providers_to_try:
            try:
                print(f"  [AI] Trying {provider_name}...")
                result = provider.generate(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode
                )
                print(f"  [AI] Success with {provider_name} ({result.model})")
                return result
            except AIProviderError as e:
                print(f"  [AI] {provider_name} failed: {e}")
                last_error = e
                continue

        raise AIProviderError(f"All providers failed. Last error: {last_error}")

    def generate_json(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.5,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """Generate and parse JSON response."""
        response = self.generate(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True
        )

        content = response.content.strip()

        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        return json.loads(content)


# Global instance for easy access
_ai_provider: Optional[AIProvider] = None


def get_ai_provider() -> AIProvider:
    """Get or create the global AI provider instance."""
    global _ai_provider
    if _ai_provider is None:
        _ai_provider = AIProvider()
    return _ai_provider
