"""Reporting agent: turns an evaluation result into a markdown experiment report.

The markdown is returned as text — the caller decides where to persist it.
The agent does not use filesystem tools, so no write-guard is needed here.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

from yahtzee_autoresearch_agents._prompt import render


_REPORT_SYSTEM_PROMPT = (
    "You are the reporting agent in a Yahtzee autoresearch loop. You "
    "produce a concise, data-grounded markdown report of a just-finished "
    "experiment. The next research agent will rely on this report as its "
    "main source of context — prioritize honest, specific analysis over "
    "flattering prose."
)


@dataclass(frozen=True, slots=True)
class ReportInput:
    experiment_id: str
    plan: str
    strategy_source: str
    # A mapping matching ``yahtzee_autoresearch_evaluation.ScoreSummary``'s
    # public fields (n, median, mean, p10/p25/p75/p90, min, max, stdev, ...).
    # A plain dict keeps the agents package decoupled from the evaluation
    # package's import surface.
    summary: dict[str, Any]
    baseline_median: float | None = None


@dataclass(frozen=True, slots=True)
class ReportOutput:
    markdown: str


async def run_reporting_agent(
    inputs: ReportInput,
    *,
    cwd: Path,
    model: str | None = None,
    max_turns: int = 3,
) -> ReportOutput:
    """Run the reporting agent and return the rendered markdown."""
    prompt = render(
        "report/prompt.jinja",
        experiment_id=inputs.experiment_id,
        plan=inputs.plan,
        strategy_source=inputs.strategy_source,
        summary=inputs.summary,
        baseline_median=inputs.baseline_median,
    )
    options = ClaudeAgentOptions(
        cwd=str(cwd),
        system_prompt=_REPORT_SYSTEM_PROMPT,
        allowed_tools=[],
        disallowed_tools=["Bash", "Write", "Edit", "NotebookEdit"],
        setting_sources=[],
        permission_mode="default",
        max_turns=max_turns,
        model=model,
    )

    text_chunks: list[str] = []
    final_result: str | None = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_chunks.append(block.text)
        elif isinstance(message, ResultMessage):
            final_result = message.result

    markdown = (final_result or "\n".join(text_chunks)).strip()
    if not markdown:
        raise RuntimeError(
            "Reporting agent produced no output. Check model access and prompt."
        )
    return ReportOutput(markdown=markdown)
