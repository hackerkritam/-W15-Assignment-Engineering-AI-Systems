import asyncio
import json
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from app.config import Settings
from app.tools import TOOLS


@dataclass
class ProviderResult:
    answer: str
    tool_calls: list[str]
    provider: str


class LLMProvider:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.api_key or "not-needed", base_url=settings.base_url)
        self.provider_name = "vLLM/local" if "localhost" in settings.base_url or "127.0.0.1" in settings.base_url else "OpenAI-compatible"

    async def complete(self, message: str, context: str) -> ProviderResult:
        system = ("You are ContextPilot, a precise assistant. Answer using the supplied context when relevant. "
                  "If context is insufficient, say so. Return only valid JSON with keys answer and tool_request. "
                  "tool_request is null or an object with name and argument.\n\nCONTEXT:\n" + context)
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
            tool_calls: list[str] = []
            request = payload.get("tool_request")
            if isinstance(request, dict) and request.get("name") in TOOLS:
                argument = request.get("argument", "")
                result = TOOLS[request["name"]](argument) if request["name"] == "calculate" else TOOLS[request["name"]]()
                tool_calls.append(f"{request['name']} -> {result}")
                payload["answer"] = f"{payload.get('answer', '')}\nTool result: {result}"
            return ProviderResult(str(payload.get("answer", "")), tool_calls, self.provider_name)
        except Exception:
            if not self.settings.allow_mock_provider:
                raise
            return ProviderResult(
                "The model provider is unavailable. I can still search your indexed documents, but configure API_KEY or a local vLLM endpoint for generated answers.",
                [],
                "mock-fallback",
            )
