from __future__ import annotations

import pytest

from yahtzee_autoresearch_evaluation import simulate
from yahtzee_autoresearch_evaluation.evaluator import (
    _resolve_strategy,
    _split_chunks,
)

from yahtzee_autoresearch_strategy import act as greedy_act

STRATEGY_REF = "yahtzee_autoresearch_strategy:act"


def test_simulate_zero_games_returns_empty():
    assert simulate(greedy_act, 0) == []


def test_simulate_rejects_negative_n_games():
    with pytest.raises(ValueError):
        simulate(greedy_act, -1)


def test_simulate_rejects_non_positive_workers():
    with pytest.raises(ValueError):
        simulate(greedy_act, 5, num_workers=0)


def test_simulate_single_worker_returns_requested_count():
    scores = simulate(greedy_act, 10, seed=1, num_workers=1)
    assert len(scores) == 10
    assert all(isinstance(s, int) and s >= 0 for s in scores)


def test_simulate_single_worker_is_deterministic():
    a = simulate(greedy_act, 25, seed=123, num_workers=1)
    b = simulate(greedy_act, 25, seed=123, num_workers=1)
    assert a == b


def test_simulate_different_seeds_produce_different_score_sequences():
    a = simulate(greedy_act, 50, seed=1, num_workers=1)
    b = simulate(greedy_act, 50, seed=2, num_workers=1)
    assert a != b


def test_simulate_multiprocess_matches_requested_count():
    scores = simulate(STRATEGY_REF, 40, seed=7, num_workers=2)
    assert len(scores) == 40
    assert all(s >= 0 for s in scores)


def test_simulate_multiprocess_is_deterministic_per_worker_count():
    # With the same (seed, num_workers), the output is byte-identical.
    a = simulate(STRATEGY_REF, 40, seed=7, num_workers=2)
    b = simulate(STRATEGY_REF, 40, seed=7, num_workers=2)
    assert a == b


def test_simulate_num_workers_clamped_to_n_games():
    # Requesting more workers than games still produces n_games scores.
    scores = simulate(greedy_act, 3, seed=0, num_workers=32)
    assert len(scores) == 3


def test_resolve_strategy_accepts_callables():
    assert _resolve_strategy(greedy_act) is greedy_act


def test_resolve_strategy_accepts_module_path_strings():
    fn = _resolve_strategy(STRATEGY_REF)
    assert fn is greedy_act


@pytest.mark.parametrize(
    "bad_ref",
    [
        "no_colon_here",
        ":missing_module",
        "module:",
    ],
)
def test_resolve_strategy_rejects_malformed_strings(bad_ref: str):
    with pytest.raises(ValueError):
        _resolve_strategy(bad_ref)


def test_resolve_strategy_rejects_unknown_types():
    with pytest.raises(TypeError):
        _resolve_strategy(42)  # type: ignore[arg-type]


def test_split_chunks_partitions_exactly_n_games():
    chunks = _split_chunks(100, 4, base_seed=0)
    total = sum(size for _, size in chunks)
    assert total == 100


def test_split_chunks_distributes_remainder():
    chunks = _split_chunks(10, 3, base_seed=0)
    sizes = sorted(size for _, size in chunks)
    # 10 / 3 = 3 remainder 1 -> sizes {4, 3, 3}.
    assert sizes == [3, 3, 4]


def test_split_chunks_drops_empty_buckets():
    chunks = _split_chunks(2, 4, base_seed=0)
    # Only the workers that actually get at least one game appear.
    assert sum(size for _, size in chunks) == 2
    assert all(size > 0 for _, size in chunks)


def test_split_chunks_assigns_distinct_seeds_per_worker():
    chunks = _split_chunks(100, 4, base_seed=42)
    seeds = [seed for seed, _ in chunks]
    assert len(set(seeds)) == len(seeds)
