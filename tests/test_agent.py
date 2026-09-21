import asyncio

from app.agent import AgentRunner
from app.provider import AgentDecision
from app.schemas import Source


class ScriptedModel:
    def __init__(self, decisions):
        self.decisions = iter(decisions)

    async def decide(self, message, context, history):
        return next(self.decisions)


def test_agent_searches_then_answers():
    source = Source(document_id="doc-1", title="Policy", content="The refund window is 30 days.", score=0.91)
    model = ScriptedModel([
        AgentDecision(action="search", query="refund window", prompt_tokens=10, completion_tokens=3),
        AgentDecision(action="answer", answer="The refund window is 30 days.", prompt_tokens=12, completion_tokens=7),
    ])
    runner = AgentRunner(model.decide, lambda query: [source], {}, max_steps=4)

    result = asyncio.run(runner.run("What is the refund window?"))

    assert result.answer == "The refund window is 30 days."
    assert result.steps == 2
    assert result.total_tokens == 32
    assert result.sources == [source]


def test_agent_uses_tool_then_answers():
    model = ScriptedModel([
        AgentDecision(action="tool", tool_name="calculate", argument="6 * 7"),
        AgentDecision(action="answer", answer="The result is 42."),
    ])
    runner = AgentRunner(model.decide, lambda query: [], {"calculate": lambda expression: "42"}, max_steps=4)

    result = asyncio.run(runner.run("Calculate 6 times 7", use_rag=False))

    assert result.answer == "The result is 42."
    assert result.tool_calls == ["calculate -> 42"]
    assert result.steps == 2


def test_agent_can_clarify():
    model = ScriptedModel([AgentDecision(action="clarify", clarification="Which country should I compare?")])
    runner = AgentRunner(model.decide, lambda query: [], {}, max_steps=4)

    result = asyncio.run(runner.run("Compare tax rules", use_rag=False))

    assert result.status == "clarification"
    assert result.answer == "Which country should I compare?"
    assert result.steps == 1


def test_agent_stops_after_step_limit():
    model = ScriptedModel([AgentDecision(action="search", query="more evidence") for _ in range(4)])
    runner = AgentRunner(model.decide, lambda query: [], {}, max_steps=4)

    result = asyncio.run(runner.run("Keep searching"))

    assert result.status == "step_limit"
    assert result.steps == 4
