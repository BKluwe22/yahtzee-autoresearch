"""Autoresearch orchestration for the Yahtzee strategy playground.

Exposes the three agents (research / coding / reporting) and a ``main``
entrypoint that runs one end-to-end iteration of the loop:

    research plan -> coding implementation -> evaluation -> report

Each run produces an artifact directory under ``artifacts/evaluation/``
containing the plan, the strategy source snapshot, the evaluation summary,
and the markdown report. The next research invocation reads those reports.
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import sys
import time
from pathlib import Path

from yahtzee_autoresearch_agents.coding import (
    CodingInput,
    CodingOutput,
    run_coding_agent,
)
from yahtzee_autoresearch_agents.report import (
    ReportInput,
    ReportOutput,
    run_reporting_agent,
)
from yahtzee_autoresearch_agents.research import (
    ResearchInput,
    ResearchOutput,
    run_research_agent,
)


__all__ = [
    "CodingInput",
    "CodingOutput",
    "ReportInput",
    "ReportOutput",
    "ResearchInput",
    "ResearchOutput",
    "main",
    "run_coding_agent",
    "run_one_experiment",
    "run_reporting_agent",
    "run_research_agent",
]


def _repo_root() -> Path:
    """Walk up from this file until we find the workspace's ``pyproject.toml``."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / "pyproject.toml").exists() and (parent / "packages").is_dir():
            return parent
    raise RuntimeError(
        "Could not locate workspace root (pyproject.toml with packages/ dir)"
    )


def _strategy_dir(root: Path) -> Path:
    return root / "packages" / "yahtzee-autoresearch-strategy"


def _strategy_file(root: Path) -> Path:
    return (
        _strategy_dir(root)
        / "src"
        / "yahtzee_autoresearch_strategy"
        / "strategy.py"
    )


def _artifacts_root(root: Path) -> Path:
    return root / "artifacts" / "evaluation"


def _load_previous_reports(artifacts_root: Path, top_n: int) -> tuple[str, ...]:
    """Return up to ``top_n`` most-recent experiment reports (newest first)."""
    if not artifacts_root.exists():
        return ()
    reports: list[tuple[float, str]] = []
    for entry in artifacts_root.iterdir():
        report = entry / "report.md"
        if report.is_file():
            reports.append((report.stat().st_mtime, report.read_text(encoding="utf-8")))
    reports.sort(key=lambda pair: pair[0], reverse=True)
    return tuple(text for _, text in reports[:top_n])


def _load_previous_median(artifacts_root: Path) -> tuple[float | None, int | None]:
    """Return (median, n_games) from the most recent ``summary.json`` if any."""
    if not artifacts_root.exists():
        return None, None
    latest: tuple[float, Path] | None = None
    for entry in artifacts_root.iterdir():
        summary = entry / "summary.json"
        if summary.is_file():
            mtime = summary.stat().st_mtime
            if latest is None or mtime > latest[0]:
                latest = (mtime, summary)
    if latest is None:
        return None, None
    data = json.loads(latest[1].read_text(encoding="utf-8"))
    return data.get("median"), data.get("n")


def _evaluate_strategy(n_games: int, seed: int, workers: int | None) -> dict[str, object]:
    """Run the evaluation and return a plain-dict summary."""
    # Deferred import: the evaluator is a separate workspace package and we
    # don't want importing the agents package to pull in simulation code.
    from yahtzee_autoresearch_evaluation import simulate, summarize

    scores = simulate(
        strategy="yahtzee_autoresearch_strategy:act",
        n_games=n_games,
        seed=seed,
        num_workers=workers,
    )
    summary = summarize(scores)
    return dataclasses.asdict(summary)


async def run_one_experiment(
    *,
    n_games: int,
    seed: int,
    workers: int | None,
    top_n_reports: int,
    model: str | None,
    coding_max_turns: int,
    experiment_id: str | None = None,
) -> Path:
    """Run research -> coding -> evaluation -> report, once. Returns the artifact dir."""
    root = _repo_root()
    strategy_dir = _strategy_dir(root)
    strategy_file = _strategy_file(root)
    artifacts_root = _artifacts_root(root)

    experiment_id = experiment_id or time.strftime("%Y%m%d-%H%M%S")
    artifact_dir = artifacts_root / experiment_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    previous_reports = _load_previous_reports(artifacts_root, top_n_reports)
    baseline_median, baseline_n_games = _load_previous_median(artifacts_root)
    strategy_source_before = strategy_file.read_text(encoding="utf-8")

    print(f"[{experiment_id}] running research agent...", file=sys.stderr)
    research_out: ResearchOutput = await run_research_agent(
        ResearchInput(
            strategy_source=strategy_source_before,
            previous_reports=previous_reports,
            baseline_median=baseline_median,
            baseline_n_games=baseline_n_games,
        ),
        cwd=root,
        model=model,
    )
    (artifact_dir / "plan.md").write_text(research_out.plan, encoding="utf-8")

    print(f"[{experiment_id}] running coding agent...", file=sys.stderr)
    coding_out: CodingOutput = await run_coding_agent(
        CodingInput(
            plan=research_out.plan,
            strategy_dir=strategy_dir,
            strategy_file=strategy_file,
        ),
        cwd=root,
        model=model,
        max_turns=coding_max_turns,
    )
    (artifact_dir / "coding_final_message.txt").write_text(
        coding_out.final_message, encoding="utf-8"
    )
    if coding_out.is_error:
        raise RuntimeError(
            f"Coding agent errored (stop_reason={coding_out.stop_reason}): "
            f"{coding_out.final_message[:500]}"
        )

    strategy_source_after = strategy_file.read_text(encoding="utf-8")
    (artifact_dir / "strategy.py").write_text(strategy_source_after, encoding="utf-8")

    print(
        f"[{experiment_id}] evaluating over {n_games:,} games "
        f"(seed={seed}, workers={workers})...",
        file=sys.stderr,
    )
    summary = _evaluate_strategy(n_games=n_games, seed=seed, workers=workers)
    (artifact_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(f"[{experiment_id}] running reporting agent...", file=sys.stderr)
    report_out: ReportOutput = await run_reporting_agent(
        ReportInput(
            experiment_id=experiment_id,
            plan=research_out.plan,
            strategy_source=strategy_source_after,
            summary=summary,
            baseline_median=baseline_median,
        ),
        cwd=root,
        model=model,
    )
    (artifact_dir / "report.md").write_text(report_out.markdown, encoding="utf-8")

    print(f"[{experiment_id}] done. artifact dir: {artifact_dir}", file=sys.stderr)
    return artifact_dir


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one iteration of the Yahtzee autoresearch loop: research "
            "-> coding -> evaluation -> report."
        ),
    )
    parser.add_argument(
        "--n-games",
        type=int,
        default=1_000_000,
        help="Games to simulate for the evaluation step (default: 1,000,000).",
    )
    parser.add_argument("--seed", type=int, default=0, help="Evaluation RNG seed.")
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Evaluation process pool size. Default: os.cpu_count().",
    )
    parser.add_argument(
        "--top-n-reports",
        type=int,
        default=5,
        help="How many prior reports to feed to the research agent.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model alias (sonnet/opus/haiku) or full model ID for all agents.",
    )
    parser.add_argument(
        "--coding-max-turns",
        type=int,
        default=40,
        help="Max turns for the coding agent's test-iterate loop.",
    )
    parser.add_argument(
        "--experiment-id",
        type=str,
        default=None,
        help="Override the generated timestamp-based experiment id.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        asyncio.run(
            run_one_experiment(
                n_games=args.n_games,
                seed=args.seed,
                workers=args.workers,
                top_n_reports=args.top_n_reports,
                model=args.model,
                coding_max_turns=args.coding_max_turns,
                experiment_id=args.experiment_id,
            )
        )
    except Exception as exc:  # surface the top-level failure mode to the shell
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
