"""
Claude API Client for Analysis Engine

Provides a robust client for interacting with Claude API,
including token management, retry logic, and cost tracking.
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

import anthropic

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Track token usage for cost calculation."""
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def estimated_cost(self) -> float:
        """Estimate cost based on Claude Sonnet 4 pricing."""
        # Sonnet 4 pricing: $3/1M input, $15/1M output
        input_cost = (self.input_tokens / 1_000_000) * 3.0
        output_cost = (self.output_tokens / 1_000_000) * 15.0
        return input_cost + output_cost


@dataclass
class AnalysisResponse:
    """Response from Claude analysis."""
    content: str
    usage: TokenUsage
    model: str
    stop_reason: str
    success: bool = True
    error: Optional[str] = None


class ClaudeClient:
    """
    Async client for Claude API optimized for analysis loops.

    Features:
    - Token usage tracking
    - Retry with exponential backoff
    - Web search and fetch capabilities
    - Cost tracking per analysis
    """

    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 8000
    TEMPERATURE = 0.3

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize Claude client.

        Args:
            api_key: Anthropic API key (defaults to env var)
            model: Model to use (defaults to Sonnet 4)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not provided")

        self.model = model or self.DEFAULT_MODEL
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.async_client = anthropic.AsyncAnthropic(api_key=self.api_key)

        # Track cumulative usage
        self.total_usage = TokenUsage()
        self.call_count = 0

    async def analyze(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = MAX_TOKENS,
        temperature: float = TEMPERATURE,
        tools: Optional[List[Dict]] = None,
    ) -> AnalysisResponse:
        """
        Send analysis prompt to Claude.

        Args:
            prompt: User prompt
            system: System prompt
            max_tokens: Maximum output tokens
            temperature: Sampling temperature
            tools: Optional tools (web_search, web_fetch)

        Returns:
            AnalysisResponse with content and usage
        """
        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if system:
                kwargs["system"] = system

            if tools:
                kwargs["tools"] = tools

            # Make API call
            response = await self.async_client.messages.create(**kwargs)

            # Extract content
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

            # Track usage
            usage = TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
            self.total_usage.input_tokens += usage.input_tokens
            self.total_usage.output_tokens += usage.output_tokens
            self.call_count += 1

            logger.info(
                f"Claude call: {usage.input_tokens} in, {usage.output_tokens} out, "
                f"${usage.estimated_cost:.4f}"
            )

            return AnalysisResponse(
                content=content,
                usage=usage,
                model=self.model,
                stop_reason=response.stop_reason,
            )

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return AnalysisResponse(
                content="",
                usage=TokenUsage(),
                model=self.model,
                stop_reason="error",
                success=False,
                error=str(e),
            )

    async def analyze_with_retry(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_retries: int = 3,
        **kwargs,
    ) -> AnalysisResponse:
        """
        Analyze with retry logic for transient failures.

        Args:
            prompt: User prompt
            system: System prompt
            max_retries: Maximum retry attempts
            **kwargs: Additional arguments for analyze()

        Returns:
            AnalysisResponse
        """
        last_error = None

        for attempt in range(max_retries):
            response = await self.analyze(prompt, system, **kwargs)

            if response.success:
                return response

            last_error = response.error
            wait_time = 2 ** attempt  # Exponential backoff

            logger.warning(
                f"Claude call failed (attempt {attempt + 1}/{max_retries}), "
                f"retrying in {wait_time}s: {response.error}"
            )
            await asyncio.sleep(wait_time)

        return AnalysisResponse(
            content="",
            usage=TokenUsage(),
            model=self.model,
            stop_reason="max_retries",
            success=False,
            error=f"Max retries exceeded. Last error: {last_error}",
        )

    async def web_search(self, query: str) -> List[Dict]:
        """
        Perform web search via Claude's web_search tool.

        Args:
            query: Search query

        Returns:
            List of search results
        """
        tools = [
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 5,
            }
        ]

        response = await self.analyze(
            prompt=f"Search the web for: {query}\n\nReturn the most relevant results.",
            tools=tools,
        )

        # Parse results from response
        # This is a simplified implementation
        return [{"query": query, "results": response.content}]

    async def web_fetch(self, url: str, prompt: str = "Summarize the content.") -> str:
        """
        Fetch and analyze web content.

        Args:
            url: URL to fetch
            prompt: Analysis prompt for the content

        Returns:
            Analyzed content
        """
        tools = [
            {
                "type": "web_search_20250305",
                "name": "web_search",
            }
        ]

        response = await self.analyze(
            prompt=f"Fetch the content from {url} and {prompt}",
            tools=tools,
        )

        return response.content

    def get_total_cost(self) -> float:
        """Get total cost for all calls in this session."""
        return self.total_usage.estimated_cost

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get summary of all API usage."""
        return {
            "total_calls": self.call_count,
            "input_tokens": self.total_usage.input_tokens,
            "output_tokens": self.total_usage.output_tokens,
            "total_tokens": self.total_usage.total_tokens,
            "estimated_cost": self.total_usage.estimated_cost,
        }
