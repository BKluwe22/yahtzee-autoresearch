"""Run a Yahtzee evaluation against the strategy.

By default evaluates the strategy exported as `act` from the
`yahtzee_autoresearch_strategy` package — that is the contract the coding
agent is expected to fulfill.

Usage:
    uv run python scripts/run_evaluation.py
    uv run python scripts/run_evaluation.py --n-games 1000000 --seed 42
    uv run python scripts/run_evaluation.py --strategy some.module:act --workers 4
"""
from __future__ import annotations

import argparse
import sys
import time

from yahtzee_autoresearch_evaluation import simulate, summarize


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate many Yahtzee games against a strategy and print summary stats."
    )
    parser.add_argument(
        "--n-games",
        type=int,
        help="Number of games to simulate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Base RNG seed.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Process pool size. Default: os.cpu_count(). Pass 1 to run inline.",
    )
    return parser.parse_args(argv)


def _format_summary(summary, elapsed: float, n_games: int) -> str:
    throughput = n_games / elapsed if elapsed > 0 else float("inf")
    return (
        f"games      : {summary.n:,}\n"
        f"elapsed    : {elapsed:.2f}s  ({throughput:,.0f} games/s)\n"
        f"median     : {summary.median:.1f}   <- optimization target\n"
        f"mean       : {summary.mean:.2f}\n"
        f"min / max  : {summary.min} / {summary.max}  (range {summary.range})\n"
        f"p10 / p25  : {summary.p10:.1f} / {summary.p25:.1f}\n"
        f"p75 / p90  : {summary.p75:.1f} / {summary.p90:.1f}\n"
        f"stdev      : {summary.stdev:.2f}\n"
        f"iqr        : {summary.iqr:.1f}   (p75 - p25)\n"
        f"mad        : {summary.mad:.1f}   (median |x - median|)"
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.n_games <= 0:
        print("n-games must be positive", file=sys.stderr)
        return 2

    print(
        f"Evaluating yahtzee_autoresearch_strategy:act over {args.n_games:,} games "
        f"(seed={args.seed}, workers={args.workers if args.workers is not None else 'auto'})..."
    )

    start = time.perf_counter()
    scores = simulate(
        strategy="yahtzee_autoresearch_strategy:act",
        n_games=args.n_games,
        seed=args.seed,
        num_workers=args.workers,
    )
    elapsed = time.perf_counter() - start

    summary = summarize(scores)
    print(_format_summary(summary, elapsed, args.n_games))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
