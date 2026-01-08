"""Claude API client wrapper with retry logic."""

import asyncio
import logging
from typing import Optional

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)


class ClaudeAPIException(Exception):
    """Exception raised when Claude API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ClaudeClient:
    """Async wrapper for Anthropic Claude API with retry logic."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        max_tokens: int = 4096,
    ):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.CLAUDE_MODEL
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        self._client: Optional[anthropic.AsyncAnthropic] = None

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        """Lazy initialization of the Anthropic client."""
        if self._client is None:
            if not self.api_key:
                raise ClaudeAPIException(
                    "ANTHROPIC_API_KEY is not configured", status_code=503
                )
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def generate_schedule(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """
        Call Claude API to generate a schedule.

        Args:
            system_prompt: System instructions for Claude
            user_prompt: User message with scheduling data

        Returns:
            Claude's response text

        Raises:
            ClaudeAPIException: If API call fails after retries
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                return response.content[0].text

            except anthropic.RateLimitError as e:
                last_error = e
                wait_time = 2 ** (attempt + 1)  # 2, 4, 8 seconds
                logger.warning(
                    f"Rate limited, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(wait_time)

            except anthropic.APIStatusError as e:
                logger.error(f"Claude API error: {e.status_code} - {e.message}")
                raise ClaudeAPIException(
                    f"Claude API error: {e.message}", status_code=e.status_code
                )

            except anthropic.APIConnectionError as e:
                last_error = e
                wait_time = 2 ** (attempt + 1)
                logger.warning(
                    f"Connection error, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(wait_time)

            except Exception as e:
                logger.error(f"Unexpected error calling Claude API: {e}")
                raise ClaudeAPIException(f"Unexpected error: {str(e)}")

        # All retries exhausted
        raise ClaudeAPIException(
            f"Claude API call failed after {self.max_retries} retries: {last_error}"
        )

    async def close(self):
        """Close the underlying HTTP client."""
        if self._client is not None:
            await self._client.close()
            self._client = None
