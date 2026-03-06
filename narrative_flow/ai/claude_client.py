"""Claude API client for AI-powered narrative analysis."""

import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import anthropic
from anthropic import Anthropic
import logging
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class ClaudeConfig:
    """Configuration for Claude API client."""
    api_key: str
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60


class ClaudeClient:
    """Client for interacting with Claude API."""

    def __init__(self, config: Optional[ClaudeConfig] = None):
        """Initialize Claude client.

        Args:
            config: Configuration for Claude client. If not provided,
                   will try to get API key from environment.
        """
        if config is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable is required. "
                    "Set it with: export ANTHROPIC_API_KEY='your-key-here'"
                )
            config = ClaudeConfig(api_key=api_key)

        self.config = config
        self.client = Anthropic(
            api_key=self.config.api_key,
            timeout=self.config.timeout
        )
        self.executor = ThreadPoolExecutor(max_workers=1)

    def _make_request(self, system_prompt: str, user_prompt: str) -> str:
        """Make synchronous request to Claude API."""
        try:
            message = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Claude API request failed: {e}")
            raise

    async def analyze(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> str:
        """Async wrapper for Claude API analysis.

        Args:
            system_prompt: System instructions for Claude
            user_prompt: User message with data to analyze

        Returns:
            Claude's response text
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._make_request,
            system_prompt,
            user_prompt
        )

    async def analyze_narrative_data(
        self,
        social_data: List[Dict[str, Any]],
        onchain_data: Dict[str, Any],
        price_data: Dict[str, Any],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze narrative data and generate insights.

        Args:
            social_data: List of social mentions with sentiment
            onchain_data: On-chain metrics by narrative
            price_data: Price movements by narrative
            context: Additional context for analysis

        Returns:
            Structured analysis with insights
        """
        system_prompt = """You are an expert crypto market analyst specializing in narrative analysis.
        Your job is to analyze social sentiment, on-chain data, and price movements to identify:
        1. Emerging narratives before price moves
        2. Narrative momentum shifts
        3. Market catalysts driving narratives
        4. Actionable trading signals

        Be specific, quantitative, and actionable in your analysis.
        Focus on divergences between social buzz and price action.
        Identify early opportunities and late-stage risks."""

        # Format data for Claude
        user_prompt = self._format_narrative_prompt(
            social_data, onchain_data, price_data, context
        )

        response = await self.analyze(system_prompt, user_prompt)

        # Parse structured response
        return self._parse_narrative_response(response)

    def _format_narrative_prompt(
        self,
        social_data: List[Dict[str, Any]],
        onchain_data: Dict[str, Any],
        price_data: Dict[str, Any],
        context: Optional[str] = None
    ) -> str:
        """Format data into a prompt for Claude."""
        prompt = f"""Analyze the following crypto narrative data from {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}:

## Social Sentiment Data (Last 24 Hours)
{json.dumps(social_data[:50], indent=2)}  # Limit to top 50 mentions

## On-Chain Metrics by Narrative
{json.dumps(onchain_data, indent=2)}

## Price Movements by Narrative
{json.dumps(price_data, indent=2)}
"""

        if context:
            prompt += f"\n## Additional Context\n{context}\n"

        prompt += """
Please provide a structured analysis including:
1. Top 3 emerging narratives with early entry signals
2. Top 3 overheated narratives showing exit signals
3. Key catalysts driving narrative changes today
4. Specific tokens showing divergence (social buzz vs price)
5. Market regime assessment for each narrative
6. Actionable recommendations

Format your response as JSON with these keys:
- emerging_narratives: List of narratives with entry signals
- overheated_narratives: List of narratives with exit signals
- catalysts: List of identified market catalysts
- divergences: List of tokens with price/sentiment divergence
- market_regime: Dict of narrative -> lifecycle stage
- recommendations: List of actionable trading ideas
- summary: Brief executive summary (2-3 sentences)
"""
        return prompt

    def _parse_narrative_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's response into structured data."""
        try:
            # Try to extract JSON from response
            # Claude might wrap JSON in markdown code blocks
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                # Try to find JSON object in response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start != -1 and json_end != 0:
                    json_str = response[json_start:json_end]
                else:
                    # Fallback: return raw text in wrapper
                    return {
                        "raw_analysis": response,
                        "parse_error": "Could not extract JSON from response"
                    }

            return json.loads(json_str)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Return structured fallback
            return {
                "raw_analysis": response,
                "parse_error": str(e)
            }

    async def generate_briefing(
        self,
        analysis_data: Dict[str, Any],
        previous_briefing: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a narrative briefing from analysis data.

        Args:
            analysis_data: Analyzed narrative data
            previous_briefing: Previous briefing for comparison

        Returns:
            Structured briefing with multiple formats
        """
        system_prompt = """You are a crypto market briefing writer.
        Create concise, actionable briefings that highlight:
        - What's new and important today
        - Key narrative rotations
        - Specific opportunities and risks
        - Clear action items for traders

        Keep it punchy, specific, and focused on alpha.
        No fluff, just signal."""

        user_prompt = f"""Create a market briefing from this analysis:

{json.dumps(analysis_data, indent=2)}
"""

        if previous_briefing:
            user_prompt += f"""
Previous briefing for comparison (highlight changes):
{json.dumps(previous_briefing.get('summary', ''), indent=2)}
"""

        user_prompt += """
Generate a briefing with:
1. Executive summary (2-3 sentences)
2. Key narrative changes (what's different today)
3. Top opportunities (specific and actionable)
4. Risk warnings (what to avoid)
5. Market outlook (next 24-48 hours)

Provide output in both:
- Markdown format (for Telegram/display)
- JSON format (for API/frontend)
"""

        response = await self.analyze(system_prompt, user_prompt)
        return self._parse_briefing_response(response)

    def _parse_briefing_response(self, response: str) -> Dict[str, Any]:
        """Parse briefing response into multiple formats."""
        # Extract markdown and JSON sections
        briefing = {
            "timestamp": datetime.utcnow().isoformat(),
            "markdown": "",
            "json": {},
            "raw": response
        }

        # Try to extract markdown section
        if "# " in response or "## " in response:
            # Find markdown content
            md_lines = []
            in_json = False
            for line in response.split('\n'):
                if '```' in line:
                    in_json = not in_json
                elif not in_json and line.strip():
                    md_lines.append(line)
            briefing["markdown"] = '\n'.join(md_lines)

        # Try to extract JSON
        try:
            json_data = self._parse_narrative_response(response)
            if "parse_error" not in json_data:
                briefing["json"] = json_data
        except:
            pass

        return briefing

    async def close(self):
        """Clean up resources."""
        self.executor.shutdown(wait=True)