"""Coding agent: implements a research plan against the strategy package.

The agent is given broad Read/Write/Edit/Glob/Grep/Bash access (it needs to
run pytest), but a PreToolUse hook confines all filesystem writes to the
strategy package. Other packages are read-only contract surfaces.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

from yahtzee_autoresearch_agents._prompt import render
from yahtzee_autoresearch_agents.hooks import make_strategy_write_guard


_CODING_SYSTEM_PROMPT = (
    "You are the coding agent in a Yahtzee autoresearch loop. You implement "
    "a research plan by editing the strategy package and iterating until its "
    "test suite passes. You must only modify files inside the strategy "
    "package — a hook will refuse any write to another package. Do not "
    "commit, push, or install packages."
)

_DEFAULT_ALLOWED_TOOLS: tuple[str, ...] = (
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
)


@dataclass(frozen=True, slots=True)
class CodingInput:
    plan: str
    strategy_dir: Path
    strategy_file: Path
    test_command: str = "uv run pytest tests/yahtzee_autoresearch_strategy -x -q"
    max_fix_attempts: int = 6


@dataclass(frozen=True, slots=True)
class CodingOutput:
    final_message: str
    transcript: list[str] = field(default_factory=list)
    is_error: bool = False
    stop_reason: str | None = None
    num_turns: int | None = None


async def run_coding_agent(
    inputs: CodingInput,
    *,
    cwd: Path,
    model: str | None = None,
    max_turns: int = 40,
    allowed_tools: tuple[str, ...] = _DEFAULT_ALLOWED_TOOLS,
) -> CodingOutput:
    """Run the coding agent with the strategy write-guard hook."""
    prompt = render(
        "coding/prompt.jinja",
        plan=inputs.plan,
        strategy_dir=str(inputs.strategy_dir),
        strategy_file=str(inputs.strategy_file),
        test_command=inputs.test_command,
        max_fix_attempts=inputs.max_fix_attempts,
    )
    guard = make_strategy_write_guard(inputs.strategy_dir)
    options = ClaudeAgentOptions(
        cwd=str(cwd),
        system_prompt=_CODING_SYSTEM_PROMPT,
        allowed_tools=list(allowed_tools),
        # The write-guard hook (not the permission prompt) is the actual
        # guardrail here. `bypassPermissions` lets the loop proceed headlessly
        # so the hook's deny reasons flow back to the model as feedback.
        permission_mode="bypassPermissions",
        # Pin a clean configuration surface — we do not want a developer's
        # local settings.json to quietly relax the coding agent's constraints.
        setting_sources=[],
        hooks={"PreToolUse": [guard]},
        max_turns=max_turns,
        model=model,
    )

    transcript: list[str] = []
    final_message = ""
    is_error = False
    stop_reason: str | None = None
    num_turns: int | None = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            # Mid-stream provider errors (rate_limit, billing_error, ...) are
            # surfaced on the AssistantMessage itself, distinct from the
            # terminal ResultMessage. Flip the error flag so the caller can
            # fail fast instead of silently returning an empty transcript.
            if message.error is not None:
                is_error = True
                final_message = (
                    f"Assistant error: {message.error}. "
                    "See AssistantMessage for details."
                )
            for block in message.content:
                if isinstance(block, TextBlock):
                    transcript.append(block.text)
                    final_message = block.text
        elif isinstance(message, ResultMessage):
            is_error = is_error or message.is_error
            stop_reason = message.stop_reason
            num_turns = message.num_turns
            if message.result:
                final_message = message.result

    return CodingOutput(
        final_message=final_message.strip(),
        transcript=transcript,
        is_error=is_error,
        stop_reason=stop_reason,
        num_turns=num_turns,
    )
