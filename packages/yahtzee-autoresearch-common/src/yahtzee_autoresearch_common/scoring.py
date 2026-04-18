from __future__ import annotations

from .dice import count_faces, enumerate_sorted_dice, sort_dice
from .models import (
    BONUS_YAHTZEE_SCORE,
    Category,
    Dice,
    FULL_HOUSE_SCORE,
    LARGE_STRAIGHT_SCORE,
    LOWER_CATEGORIES,
    SMALL_STRAIGHT_SCORE,
    Scorecard,
    YAHTZEE_SCORE,
)


_LOWER_CATEGORY_SET: frozenset[Category] = frozenset(LOWER_CATEGORIES)


CategoryScores = tuple[int, int, int, int, int, int, int, int, int, int, int, int, int]


_SMALL_STRAIGHT_RUNS: tuple[frozenset[int], ...] = (
    frozenset({1, 2, 3, 4}),
    frozenset({2, 3, 4, 5}),
    frozenset({3, 4, 5, 6}),
)
_LARGE_STRAIGHT_RUNS: tuple[frozenset[int], ...] = (
    frozenset({1, 2, 3, 4, 5}),
    frozenset({2, 3, 4, 5, 6}),
)


def _compute_category_scores(dice: Dice) -> CategoryScores:
    counts = count_faces(dice)
    total = sum(dice)
    max_count = max(counts)
    faces = set(dice)
    return (
        counts[0] * 1,
        counts[1] * 2,
        counts[2] * 3,
        counts[3] * 4,
        counts[4] * 5,
        counts[5] * 6,
        total if max_count >= 3 else 0,
        total if max_count >= 4 else 0,
        FULL_HOUSE_SCORE if (3 in counts and 2 in counts) else 0,
        SMALL_STRAIGHT_SCORE if any(run <= faces for run in _SMALL_STRAIGHT_RUNS) else 0,
        LARGE_STRAIGHT_SCORE if any(run <= faces for run in _LARGE_STRAIGHT_RUNS) else 0,
        YAHTZEE_SCORE if max_count == 5 else 0,
        total,
    )


def _build_tables() -> tuple[dict[Dice, CategoryScores], dict[Dice, bool]]:
    scores: dict[Dice, CategoryScores] = {}
    yahtzees: dict[Dice, bool] = {}
    for d in enumerate_sorted_dice():
        scores[d] = _compute_category_scores(d)
        yahtzees[d] = d[0] == d[4]
    return scores, yahtzees


_SCORE_TABLE, _YAHTZEE_TABLE = _build_tables()


def is_yahtzee(dice: Dice) -> bool:
    """True iff all five dice show the same face."""
    return _YAHTZEE_TABLE[sort_dice(dice)]


def base_score(dice: Dice, category: Category) -> int:
    """Return the raw category score for `dice`, ignoring joker rules and bonuses.

    O(1) lookup.
    """
    return _SCORE_TABLE[sort_dice(dice)][category]


def all_base_scores(dice: Dice) -> CategoryScores:
    """Return raw scores for all 13 categories as a 13-tuple, ignoring joker rules."""
    return _SCORE_TABLE[sort_dice(dice)]


def _is_bonus_yahtzee(scorecard: Scorecard, sorted_dice: Dice) -> bool:
    """House rule trigger: a Yahtzee is rolled and the Yahtzee category was
    already filled with 50. A prior zero does not arm the bonus."""
    return (
        _YAHTZEE_TABLE[sorted_dice]
        and scorecard.scores[Category.YAHTZEE] == YAHTZEE_SCORE
    )


def score_for(scorecard: Scorecard, dice: Dice, category: Category) -> int:
    """Score that would be written to `category` given `scorecard` and `dice`.

    Applies the house rule: when the dice are a Yahtzee and the Yahtzee
    category is already filled with 50, scoring in any open lower-section
    category (excluding Yahtzee itself, which is already filled) writes 100.
    Upper-section categories always score at face value.
    """
    sorted_dice = sort_dice(dice)
    if (
        _is_bonus_yahtzee(scorecard, sorted_dice)
        and category in _LOWER_CATEGORY_SET
        and category != Category.YAHTZEE
    ):
        return BONUS_YAHTZEE_SCORE
    return _SCORE_TABLE[sorted_dice][category]


def legal_categories(scorecard: Scorecard) -> tuple[Category, ...]:
    """Open categories are always legal; the house rule removes any forcing."""
    return scorecard.open_categories


def apply_score(scorecard: Scorecard, dice: Dice, category: Category) -> Scorecard:
    """Return a new scorecard with `category` filled per the rules.

    Raises ValueError if the category is already filled.
    """
    if scorecard.is_filled(category):
        raise ValueError(f"Category {category.name} already filled")
    return scorecard.with_score(category, score_for(scorecard, dice, category))
