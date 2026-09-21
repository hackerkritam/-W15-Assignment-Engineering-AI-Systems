import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from app.provider import AgentDecision
from app.schemas import Source

SearchFn = Callable[[str], list[Source]]
ToolFn = Callable[[str], str]
DecisionFn = Callable[[str, str, list[dict[str, str]]], Awaitable[AgentDecision]]


@dataclass
class AgentRun:
    answer: str
    sources: list[Source] = field(default_factory=list)
    tool_calls: list[str] = field(default_factory=list)
    steps: int = 0
    total_tokens: int = 0
    status: str = "completed"


class AgentRunner:
    """A bounded single-agent loop that chooses the next action from intermediate evidence."""

    def __init__(self, decide: DecisionFn, search: SearchFn, tools: dict[str, ToolFn], max_steps: int = 4):
        self.decide = decide
        self.search = search
        self.tools = tools
        self.max_steps = max_steps

    async def run(self, message: str, use_rag: bool = True) -> AgentRun:
        history: list[dict[str, str]] = []
        sources: list[Source] = []
        tool_calls: list[str] = []
        total_tokens = 0
        context = ""

        for step in range(1, self.max_steps + 1):
            decision = await self.decide(message, context, history)
            total_tokens += decision.prompt_tokens + decision.completion_tokens

            if decision.action == "answer":
                return AgentRun(decision.answer, sources, tool_calls, step, total_tokens)
            if decision.action == "clarify":
                return AgentRun(decision.clarification, sources, tool_calls, step, total_tokens, "clarification")
            if decision.action == "search":
                if not use_rag:
                    history.append({"action": "search", "result": "Search is disabled for this request."})
                    context = "Search is disabled. Decide whether to answer or clarify."
                    continue
                query = decision.query.strip() or message
                results = self.search(query)
                sources.extend(source for source in results if source.document_id not in {item.document_id for item in sources})
                context = "\n\n".join(f"[{source.title}, score={source.score}] {source.content}" for source in results)
                history.append({"action": "search", "query": query, "result": f"{len(results)} sources returned"})
                continue
            if decision.action == "tool":
                tool = self.tools.get(decision.tool_name)
                if tool is None:
                    history.append({"action": "tool", "result": f"Unknown tool: {decision.tool_name}"})
                    context = "The requested tool is unavailable. Choose another action."
                    continue
                try:
                    result = await asyncio.to_thread(tool, decision.argument) if decision.tool_name == "calculate" else await asyncio.to_thread(tool)
                    tool_calls.append(f"{decision.tool_name} -> {result}")
                    history.append({"action": "tool", "tool": decision.tool_name, "result": str(result)})
                    context = f"Tool result from {decision.tool_name}: {result}"
                except Exception as error:
                    history.append({"action": "tool", "tool": decision.tool_name, "result": f"FAILED: {error}"})
                    context = f"Tool {decision.tool_name} failed. Do not claim a result; choose another action or clarify."
                continue
            history.append({"action": "invalid", "result": "Unsupported action"})
            context = "Unsupported action. Return answer, search, tool, or clarify."

        return AgentRun(
            "I could not complete this request within the agent step limit. Please narrow the question or provide more context.",
            sources,
            tool_calls,
            self.max_steps,
            total_tokens,
            "step_limit",
        )
