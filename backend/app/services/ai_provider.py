"""
AI Provider abstraction — OpenAI only.
"""
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from openai import OpenAI

from app.core.config import settings


class ProviderName(str, Enum):
    OPENAI = "openai"


@dataclass
class AIResponse:
    """Standardized AI response."""
    content: str
    provider: ProviderName
    model: str
    tokens_used: int
    raw_response: Optional[Dict[str, Any]] = None


class AIProviderError(Exception):
    """Custom exception for AI provider errors."""
    pass


class AIProvider:
    """Unified AI provider backed by OpenAI."""

    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY
        self._client = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self.openai_api_key:
                raise AIProviderError("No AI provider configured. Set OPENAI_API_KEY.")
            self._client = OpenAI(api_key=self.openai_api_key)
        return self._client

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.5,
        max_tokens: int = 2000,
        json_mode: bool = False,
        prefer_provider: Optional[ProviderName] = None,
    ) -> AIResponse:
        """Generate a completion using OpenAI."""
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            print(f"  [AI] OpenAI request ({model})...")
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            print(f"  [AI] Success ({model}, {tokens} tokens)")

            return AIResponse(
                content=content,
                provider=ProviderName.OPENAI,
                model=model,
                tokens_used=tokens,
            )
        except Exception as e:
            raise AIProviderError(f"OpenAI request failed: {str(e)}")

    def generate_json(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.5,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """Generate and parse JSON response."""
        response = self.generate(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
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
