"""Research agent: proposes the next strategy experiment.

Reads the previous experiment reports and the current strategy source, asks
the model for a focused plan, and returns it as plain text. No filesystem
writes; the agent does not need any tools that mutate state.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

from yahtzee_autoresearch_agents._prompt import render


_RESEARCH_SYSTEM_PROMPT = (
    "You are the research agent in a Yahtzee autoresearch loop. You analyze "
    "prior experiment reports and propose one concrete, testable change to "
    "the strategy's `act` function that should lift the median score over "
    "1,000,000 simulated games. You do not write code — you write a plan "
    "that a coding agent will implement."
)


@dataclass(frozen=True, slots=True)
class ResearchInput:
    strategy_source: str
    previous_reports: tuple[str, ...] = ()
    baseline_median: float | None = None
    baseline_n_games: int | None = None


@dataclass(frozen=True, slots=True)
class ResearchOutput:
    plan: str


async def run_research_agent(
    inputs: ResearchInput,
    *,
    cwd: Path,
    model: str | None = None,
    max_turns: int = 3,
) -> ResearchOutput:
    """Run the research agent and return its plan."""
    prompt = render(
        "research/prompt.jinja",
        strategy_source=inputs.strategy_source,
        previous_reports=list(inputs.previous_reports),
        baseline_median=inputs.baseline_median,
        baseline_n_games=inputs.baseline_n_games,
    )
    options = ClaudeAgentOptions(
        cwd=str(cwd),
        system_prompt=_RESEARCH_SYSTEM_PROMPT,
        allowed_tools=[],
        disallowed_tools=["Bash", "Write", "Edit", "NotebookEdit"],
        # Pin a clean tool surface so ambient user/project/local settings can't
        # quietly widen or narrow what this agent can do between runs.
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

    plan = (final_result or "\n".join(text_chunks)).strip()
    if not plan:
        raise RuntimeError(
            "Research agent produced no plan. Check model access and prompt."
        )
    return ResearchOutput(plan=plan)
