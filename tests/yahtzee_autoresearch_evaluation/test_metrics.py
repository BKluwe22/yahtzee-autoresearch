from __future__ import annotations

import statistics

import pytest

from yahtzee_autoresearch_evaluation import ScoreSummary, median, summarize


def test_median_of_odd_length():
    assert median([10, 20, 30]) == 20


def test_median_of_even_length_interpolates():
    assert median([10, 20, 30, 40]) == 25


def test_median_ignores_order():
    assert median([30, 10, 20]) == 20


def test_median_raises_on_empty():
    with pytest.raises(ValueError):
        median([])


def test_summarize_basic_stats():
    scores = [10, 20, 30, 40, 50]
    s = summarize(scores)
    assert isinstance(s, ScoreSummary)
    assert s.n == 5
    assert s.min == 10
    assert s.max == 50
    assert s.mean == pytest.approx(30.0)
    assert s.median == pytest.approx(30.0)


def test_summarize_percentiles_are_monotonic():
    scores = list(range(1, 1001))
    s = summarize(scores)
    assert s.p10 < s.p25 < s.median < s.p75 < s.p90


def test_summarize_raises_on_empty():
    with pytest.raises(ValueError):
        summarize([])


def test_summary_is_frozen():
    s = summarize([1, 2, 3])
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        s.n = 99  # type: ignore[misc]


def test_summarize_stdev_matches_statistics_module():
    scores = [10, 15, 22, 27, 30, 41, 55]
    s = summarize(scores)
    assert s.stdev == pytest.approx(statistics.stdev(scores))


def test_summarize_stdev_is_zero_when_all_scores_equal():
    s = summarize([50] * 20)
    assert s.stdev == 0.0


def test_summarize_stdev_is_zero_for_single_value():
    s = summarize([77])
    assert s.stdev == 0.0


def test_summarize_iqr_equals_p75_minus_p25():
    scores = list(range(1, 101))
    s = summarize(scores)
    assert s.iqr == pytest.approx(s.p75 - s.p25)


def test_summarize_iqr_is_zero_when_all_scores_equal():
    s = summarize([50] * 20)
    assert s.iqr == 0.0


def test_summarize_mad_equals_median_absolute_deviation():
    scores = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    s = summarize(scores)
    expected = statistics.median(abs(x - s.median) for x in scores)
    assert s.mad == pytest.approx(expected)


def test_summarize_mad_is_zero_when_all_scores_equal():
    s = summarize([42] * 10)
    assert s.mad == 0.0


def test_summarize_range_is_max_minus_min():
    s = summarize([7, 100, 33, 12])
    assert s.range == 100 - 7


def test_summarize_range_is_zero_when_all_scores_equal():
    s = summarize([9] * 5)
    assert s.range == 0


def test_summarize_spread_metrics_are_non_negative():
    scores = [13, 8, 21, 34, 5, 55]
    s = summarize(scores)
    assert s.stdev >= 0
    assert s.iqr >= 0
    assert s.mad >= 0
    assert s.range >= 0
