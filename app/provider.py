import asyncio
import json
from dataclasses import dataclass
from typing import Any, Literal

from openai import AsyncOpenAI

from app.config import Settings
from app.tools import TOOLS


@dataclass
class ProviderResult:
    answer: str
    tool_calls: list[str]
    provider: str


@dataclass
class AgentDecision:
    action: Literal["answer", "search", "tool", "clarify"]
    answer: str = ""
    query: str = ""
    tool_name: str = ""
    argument: str = ""
    clarification: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMProvider:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.api_key or "not-needed", base_url=settings.base_url)
        self.provider_name = "vLLM/local" if "localhost" in settings.base_url or "127.0.0.1" in settings.base_url else "OpenAI-compatible"

    async def decide(self, message: str, context: str, history: list[dict[str, str]]) -> AgentDecision:
        recent_history = history[-6:]
        system = (
            "You are ContextPilot's bounded research agent. Decide the next action from the evidence. "
            "Return only valid JSON with exactly one action: answer, search, tool, or clarify. "
            "Use search when evidence is missing or conflicting. Use tool for arithmetic or UTC time. "
            "Ask for clarification instead of guessing. For answer use answer; for search use query; "
            "for tool use tool_name and argument; for clarify use clarification.\n\n"
            f"CURRENT EVIDENCE (capped):\n{context[:self.settings.agent_max_context_chars]}\n\n"
            f"RECENT ACTIONS:\n{json.dumps(recent_history)}"
        )
        try:
            response = None
            for attempt in range(3):
                try:
                    response = await self.client.chat.completions.create(
                        model=self.settings.model,
                        temperature=self.settings.temperature,
                        top_p=self.settings.top_p,
                        max_tokens=self.settings.max_tokens,
                        response_format={"type": "json_object"},
                        messages=[{"role": "system", "content": system}, {"role": "user", "content": message}],
                    )
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.2 * (2 ** attempt))
            payload = json.loads(response.choices[0].message.content or "{}")
            action = payload.get("action")
            if action not in {"answer", "search", "tool", "clarify"}:
                raise ValueError("Model returned an invalid agent action")
            usage = getattr(response, "usage", None)
            return AgentDecision(
                action=action,
                answer=str(payload.get("answer", "")),
                query=str(payload.get("query", "")),
                tool_name=str(payload.get("tool_name", "")),
                argument=str(payload.get("argument", "")),
                clarification=str(payload.get("clarification", "")),
                prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            )
        except Exception:
            if not self.settings.allow_mock_provider:
                raise
            return AgentDecision(
                action="answer",
                answer="The model provider is unavailable. I can still search your indexed documents, but configure API_KEY or a local vLLM endpoint for generated answers.",
            )

    async def complete(self, message: str, context: str) -> ProviderResult:
        decision = await self.decide(message, context, [])
        return ProviderResult(decision.answer, [], self.provider_name if decision.answer else "mock-fallback")
