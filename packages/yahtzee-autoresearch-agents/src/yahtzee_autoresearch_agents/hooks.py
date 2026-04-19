"""PreToolUse hook that confines filesystem writes to the strategy playground.

The coding agent in the autoresearch loop is allowed to iterate freely on the
strategy package but must not touch any other package (the evaluator and the
common data models are contract surfaces the strategy is measured against —
letting the agent edit them would make the experiment meaningless).

The hook enforces that in two complementary ways:

1. Structured path check for ``Write`` / ``Edit`` / ``NotebookEdit`` — the tool
   input carries the target path, which we resolve and check against the
   allowlisted prefix.
2. Deny-list regex for ``Bash`` — Bash is too expressive to verify reliably,
   so we refuse any command that looks like it could mutate the filesystem.
   The coding agent can still use Bash to run tests; for edits it must use
   the file tools (which are path-gated).
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from claude_agent_sdk import HookContext, HookMatcher, PreToolUseHookInput


_PATH_WRITE_TOOLS: frozenset[str] = frozenset({"Write", "Edit", "NotebookEdit"})

# Anything in this regex triggers a Bash denial. The list is deliberately
# conservative — the coding agent does not need Bash for writes at all.
_BASH_MUTATION_PATTERNS: re.Pattern[str] = re.compile(
    r"(?:"
    # shell redirect (>, >>, >|) — except into /dev/null which is a no-op sink
    r">>?\|?(?!\s*/dev/null\b)"
    # mutating coreutils
    r"|\b(?:rm|mv|cp|ln|chmod|chown|touch|mkdir|rmdir|tee|dd|install)\b"
    # in-place editors
    r"|\bsed\s+-i\b"
    r"|\bperl\s+-i\b"
    # git write operations
    r"|\bgit\s+(?:commit|push|add|rm|mv|reset|restore\s+--|checkout\s+--)\b"
    # package-manager state changes
    r"|\b(?:pip|uv|poetry|pipx|npm|pnpm|yarn|cargo|go)\s+"
    r"(?:install|add|remove|uninstall|sync|update|upgrade|publish)\b"
    # curl/wget writing files
    r"|\b(?:curl|wget)\b[^|]*\s-[a-zA-Z]*[oO]\b"
    r")"
)


def _deny(reason: str) -> dict[str, Any]:
    """Return a hook output that blocks the tool call.

    We emit both the top-level ``decision: "block"`` form (the legacy path
    every CLI version understands) and the PreToolUse-specific
    ``hookSpecificOutput.permissionDecision: "deny"`` form (the modern path
    that carries a dedicated reason field to the model). Setting both is
    redundant-but-safe and ensures the deny is never silently swallowed.
    """
    return {
        "decision": "block",
        "systemMessage": reason,
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }


def _allow() -> dict[str, Any]:
    return {}


def _is_within(target: Path, root: Path) -> bool:
    try:
        target.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def make_strategy_write_guard(strategy_dir: Path) -> HookMatcher:
    """Return a PreToolUse HookMatcher that restricts writes to ``strategy_dir``.

    The returned matcher fires on ``Write``, ``Edit``, ``NotebookEdit``, and
    ``Bash``. File tools are denied if the target path is outside the
    playground. Bash is denied if the command string matches any mutation
    pattern (the coding agent should use Write/Edit for changes — Bash is
    reserved for running the test suite).
    """
    strategy_root = strategy_dir.resolve(strict=False)

    async def guard(
        input_data: PreToolUseHookInput,
        _tool_use_id: str | None,
        _context: HookContext,
    ) -> dict[str, Any]:
        tool = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input") or {}

        if tool in _PATH_WRITE_TOOLS:
            raw = (
                tool_input.get("file_path")
                or tool_input.get("notebook_path")
                or ""
            )
            if not raw:
                return _deny(
                    f"{tool} was called without a path; refusing by default."
                )
            target = Path(raw)
            if not target.is_absolute():
                cwd = input_data.get("cwd") or os.getcwd()
                target = Path(cwd) / target
            if not _is_within(target, strategy_root):
                return _deny(
                    f"{tool} target {target} is outside the strategy "
                    f"playground ({strategy_root}). Writes are only "
                    "permitted inside the yahtzee-autoresearch-strategy "
                    "package."
                )
            return _allow()

        if tool == "Bash":
            command = tool_input.get("command", "") or ""
            if _BASH_MUTATION_PATTERNS.search(command):
                return _deny(
                    "Bash is restricted to read-only / test-execution "
                    "commands. To change a file, use the Write or Edit "
                    f"tool (writes are only allowed under {strategy_root})."
                )
            return _allow()

        return _allow()

    return HookMatcher(
        matcher="Write|Edit|NotebookEdit|Bash",
        hooks=[guard],
    )
