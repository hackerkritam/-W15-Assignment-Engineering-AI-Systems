import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import AgentRunner
from app.provider import AgentDecision
from app.schemas import Source


@dataclass
class Case:
    name: str
    request: str
    decisions: list[AgentDecision]
    tools: dict
    expected_action: str
    failure_injection: str = "none"


class ScriptedModel:
    def __init__(self, decisions):
        self.decisions = iter(decisions)

    async def decide(self, message, context, history):
        return next(self.decisions)


def classify(status: str, answer: str, expected_action: str) -> str:
    if status == "completed" and expected_action in answer.lower():
        return "success"
    if status in {"clarification", "step_limit"}:
        return "soft failure"
    return "hard failure"


async def run_case(case: Case) -> dict:
    model = ScriptedModel(case.decisions)
    source = Source(document_id="eval", title="Evaluation source", content="The answer is 42.", score=1.0)
    runner = AgentRunner(model.decide, lambda query: [source], case.tools, max_steps=4)
    result = await runner.run(case.request)
    status = classify(result.status, result.answer, case.expected_action)
    return {
        "case": case.name,
        "status": status,
        "agent_status": result.status,
        "steps": result.steps,
        "total_tokens": result.total_tokens,
        "tool_calls": result.tool_calls,
        "tool_call_correct": (all("calculate -> 42" in call for call in result.tool_calls) if result.tool_calls else "n/a"),
        "failure_injection": case.failure_injection,
        "answer": result.answer,
    }


async def main():
    cases = [
        Case(
            "cross-source search then answer",
            "What is the answer?",
            [AgentDecision("search", query="answer", prompt_tokens=18, completion_tokens=5), AgentDecision("answer", answer="The answer is 42.", prompt_tokens=22, completion_tokens=8)],
            {},
            "42",
        ),
        Case(
            "tool calculation then answer",
            "Calculate six times seven",
            [AgentDecision("tool", tool_name="calculate", argument="6 * 7", prompt_tokens=18, completion_tokens=6), AgentDecision("answer", answer="The answer is 42.", prompt_tokens=20, completion_tokens=8)],
            {"calculate": lambda expression: "42"},
            "42",
        ),
        Case(
            "failure injection unavailable tool",
            "Use the unavailable weather tool",
            [AgentDecision("tool", tool_name="weather", argument="London"), AgentDecision("clarify", clarification="The weather tool is unavailable.")],
            {},
            "unavailable",
            "tool unavailable",
        ),
        Case(
            "bounded repeated search",
            "Keep researching",
            [AgentDecision("search", query="more") for _ in range(4)],
            {},
            "within the agent step limit",
            "repeated search",
        ),
    ]
    rows = [await run_case(case) for case in cases]
    completed = sum(row["status"] == "success" for row in rows)
    report = {
        "summary": {
            "task_completion_rate": f"{completed}/{len(rows)}",
            "average_steps": round(sum(row["steps"] for row in rows) / len(rows), 2),
            "total_tokens": sum(row["total_tokens"] for row in rows),
            "failure_counts": {kind: sum(row["status"] == kind for row in rows) for kind in ["hard failure", "soft failure", "cascading soft failure"]},
        },
        "cases": rows,
    }
    output = Path("evaluation-results.json")
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown = [
        "# Agent Evaluation Results",
        "",
        f"Task completion rate: **{report['summary']['task_completion_rate']}**",
        f"Average trajectory length: **{report['summary']['average_steps']} steps**",
        f"Total tokens: **{report['summary']['total_tokens']}**",
        "",
        "| Case | Status | Steps | Tokens | Tool calls | Injection |",
        "|---|---|---:|---:|---|---|",
    ]
    for row in rows:
        markdown.append(f"| {row['case']} | {row['status']} | {row['steps']} | {row['total_tokens']} | {', '.join(row['tool_calls']) or '-'} | {row['failure_injection']} |")
    markdown.extend(["", "Failure taxonomy counts: " + json.dumps(report["summary"]["failure_counts"])])
    Path("evaluation-results.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
