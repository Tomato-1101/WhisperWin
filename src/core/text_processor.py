"""LLM-based text post-processing for transcription results."""

import os
from typing import Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)

# Lazy imports for SDK availability
_groq_available: bool = False
_cerebras_available: bool = False

try:
    from groq import Groq
    _groq_available = True
except ImportError:
    Groq = None

try:
    from cerebras.cloud.sdk import Cerebras
    _cerebras_available = True
except ImportError:
    Cerebras = None


class TextProcessor:
    """
    LLM-based text post-processor.

    Transforms transcribed text using fast inference APIs (Groq/Cerebras).
    """

    def __init__(
        self,
        provider: str = "groq",
        model: str = "llama-3.3-70b-versatile",
        system_prompt: str = "",
        timeout: float = 5.0,
        fallback_on_error: bool = True,
    ) -> None:
        self.provider = provider
        self.model = model
        self.system_prompt = system_prompt
        self.timeout = timeout
        self.fallback_on_error = fallback_on_error

        self._groq_client: Optional[Groq] = None
        self._cerebras_client: Optional[Cerebras] = None

    def is_available(self) -> bool:
        """Check if the configured provider is available."""
        if self.provider == "groq":
            return _groq_available and bool(os.environ.get("GROQ_API_KEY"))
        elif self.provider == "cerebras":
            return _cerebras_available and bool(os.environ.get("CEREBRAS_API_KEY"))
        return False

    def _get_groq_client(self) -> "Groq":
        """Get or create Groq client."""
        if self._groq_client is None:
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError("GROQ_API_KEY not set")
            self._groq_client = Groq(api_key=api_key, timeout=self.timeout)
        return self._groq_client

    def _get_cerebras_client(self) -> "Cerebras":
        """Get or create Cerebras client."""
        if self._cerebras_client is None:
            api_key = os.environ.get("CEREBRAS_API_KEY")
            if not api_key:
                raise RuntimeError("CEREBRAS_API_KEY not set")
            self._cerebras_client = Cerebras(api_key=api_key, timeout=self.timeout)
        return self._cerebras_client

    def process(self, text: str) -> str:
        """
        Process text using LLM.

        Args:
            text: Input text to transform

        Returns:
            Transformed text, or original text on error (if fallback enabled)
        """
        if not text or not text.strip():
            return text

        if not self.is_available():
            logger.warning(f"LLM provider {self.provider} not available")
            return text if self.fallback_on_error else ""

        try:
            if self.provider == "groq":
                return self._process_with_groq(text)
            elif self.provider == "cerebras":
                return self._process_with_cerebras(text)
            else:
                logger.error(f"Unknown provider: {self.provider}")
                return text if self.fallback_on_error else ""
        except Exception as e:
            logger.error(f"LLM processing error: {e}")
            return text if self.fallback_on_error else ""

    def _process_with_groq(self, text: str) -> str:
        """Process text using Groq API."""
        client = self._get_groq_client()

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            max_tokens=len(text) * 3,
        )

        result = response.choices[0].message.content.strip()
        logger.debug(f"LLM transform: '{text}' -> '{result}'")
        return result

    def _process_with_cerebras(self, text: str) -> str:
        """Process text using Cerebras API."""
        client = self._get_cerebras_client()

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            max_tokens=len(text) * 3,
        )

        result = response.choices[0].message.content.strip()
        logger.debug(f"LLM transform: '{text}' -> '{result}'")
        return result
