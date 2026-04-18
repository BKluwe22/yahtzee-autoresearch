from __future__ import annotations

from dataclasses import dataclass
from statistics import median as _median
from typing import Sequence


@dataclass(frozen=True, slots=True)
class ScoreSummary:
    n: int
    median: float
    mean: float
    min: int
    max: int
    p10: float
    p25: float
    p75: float
    p90: float
    stdev: float  # sample standard deviation (N-1); 0.0 when n < 2
    iqr: float    # p75 - p25
    mad: float    # median absolute deviation: median(|x - median|)
    range: int    # max - min


def median(scores: Sequence[int]) -> float:
    """Median of a sequence of final scores. The project's optimization target."""
    if not scores:
        raise ValueError("Cannot compute median of an empty sequence")
    return _median(scores)


def _percentile_sorted(sorted_scores: Sequence[int], p: float) -> float:
    """Linear-interpolated percentile over an already-sorted sequence."""
    if not sorted_scores:
        raise ValueError("Cannot compute percentile of an empty sequence")
    if not 0.0 <= p <= 100.0:
        raise ValueError("p must be in [0, 100]")
    n = len(sorted_scores)
    if n == 1:
        return float(sorted_scores[0])
    rank = (p / 100.0) * (n - 1)
    lo = int(rank)
    hi = min(lo + 1, n - 1)
    frac = rank - lo
    return sorted_scores[lo] + (sorted_scores[hi] - sorted_scores[lo]) * frac


def summarize(scores: Sequence[int]) -> ScoreSummary:
    """Build a full summary in one pass after a single sort.

    Sorting dominates for large inputs; computing everything from the sorted
    list avoids walking the sequence multiple times. Variability is reported
    as stdev (parametric), IQR / MAD (robust — pair well with the median
    optimization target), and range.
    """
    if not scores:
        raise ValueError("Cannot summarize an empty sequence")
    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    total = sum(sorted_scores)
    mean = total / n

    median = _percentile_sorted(sorted_scores, 50.0)
    p25 = _percentile_sorted(sorted_scores, 25.0)
    p75 = _percentile_sorted(sorted_scores, 75.0)

    if n >= 2:
        sum_sq_dev = sum((x - mean) * (x - mean) for x in sorted_scores)
        stdev = (sum_sq_dev / (n - 1)) ** 0.5
    else:
        stdev = 0.0

    sorted_abs_devs = sorted(abs(x - median) for x in sorted_scores)
    mad = _percentile_sorted(sorted_abs_devs, 50.0)

    return ScoreSummary(
        n=n,
        median=median,
        mean=mean,
        min=sorted_scores[0],
        max=sorted_scores[-1],
        p10=_percentile_sorted(sorted_scores, 10.0),
        p25=p25,
        p75=p75,
        p90=_percentile_sorted(sorted_scores, 90.0),
        stdev=stdev,
        iqr=p75 - p25,
        mad=mad,
        range=sorted_scores[-1] - sorted_scores[0],
    )


__all__ = ["ScoreSummary", "median", "summarize"]
