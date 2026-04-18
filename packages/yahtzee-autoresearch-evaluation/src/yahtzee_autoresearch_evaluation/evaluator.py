from __future__ import annotations

import os
import random
from concurrent.futures import ProcessPoolExecutor
from importlib import import_module
from typing import Callable

from yahtzee_autoresearch_common import Action, TurnState

from .game import ActFn, play_game


StrategyRef = str | ActFn

_WORKER_SEED_STRIDE = 10_000_019  # a large prime to decorrelate per-worker seeds


def _resolve_strategy(ref: StrategyRef) -> ActFn:
    """Turn a callable or a `'module:attr'` string into an act function.

    Strings are the recommended form when crossing process boundaries — they
    re-import inside each worker rather than relying on pickling a closure or
    lambda (which breaks on Windows/macOS `spawn` start methods)."""
    if callable(ref):
        return ref
    if isinstance(ref, str):
        module_name, _, attr = ref.partition(":")
        if not module_name or not attr:
            raise ValueError(
                f"Strategy string must look like 'module.path:attr', got {ref!r}"
            )
        return getattr(import_module(module_name), attr)
    raise TypeError(f"Expected callable or 'module:attr' string, got {type(ref).__name__}")


def _play_chunk(args: tuple[StrategyRef, int, int]) -> list[int]:
    """Worker entrypoint: play `n_games` with the given strategy and seed."""
    strategy_ref, seed, n_games = args
    act = _resolve_strategy(strategy_ref)
    rng = random.Random(seed)
    return [play_game(act, rng) for _ in range(n_games)]


def _split_chunks(
    n_games: int,
    num_workers: int,
    base_seed: int,
) -> list[tuple[int, int]]:
    """Split `n_games` into `num_workers` (seed, size) pairs."""
    if num_workers <= 0:
        raise ValueError("num_workers must be positive")
    base, extra = divmod(n_games, num_workers)
    chunks: list[tuple[int, int]] = []
    for i in range(num_workers):
        size = base + (1 if i < extra else 0)
        if size == 0:
            continue
        chunks.append((base_seed + i * _WORKER_SEED_STRIDE, size))
    return chunks


def simulate(
    strategy: StrategyRef,
    n_games: int,
    *,
    seed: int = 0,
    num_workers: int | None = None,
) -> list[int]:
    """Play `n_games` with `strategy` and return every final score.

    Parameters
    ----------
    strategy:
        Either an `act(TurnState) -> Action` callable, or a `'module:attr'`
        string. The string form is strongly preferred when `num_workers > 1`
        because each worker re-imports the strategy; callables must be
        picklable, which excludes lambdas, closures, and locally-defined
        functions on spawn-based platforms (Windows, macOS).
    n_games:
        Total number of games to simulate (>= 0).
    seed:
        Base seed. Every worker derives its own seed from this.
    num_workers:
        Process pool size. Defaults to `os.cpu_count()`. With 1 worker (or
        `num_workers=1`) the simulation runs inline, skipping the pool and
        its pickling overhead — the right choice on a single-vCPU runner.
    """
    if n_games < 0:
        raise ValueError("n_games must be non-negative")
    if n_games == 0:
        return []

    if num_workers is None:
        num_workers = os.cpu_count() or 1
    if num_workers < 1:
        raise ValueError("num_workers must be positive")
    num_workers = min(num_workers, n_games)

    chunks = _split_chunks(n_games, num_workers, seed)

    if num_workers == 1:
        return _play_chunk((strategy, chunks[0][0], chunks[0][1]))

    args = [(strategy, chunk_seed, chunk_size) for chunk_seed, chunk_size in chunks]
    scores: list[int] = []
    with ProcessPoolExecutor(max_workers=num_workers) as pool:
        for chunk_scores in pool.map(_play_chunk, args):
            scores.extend(chunk_scores)
    return scores


__all__ = ["StrategyRef", "simulate"]
