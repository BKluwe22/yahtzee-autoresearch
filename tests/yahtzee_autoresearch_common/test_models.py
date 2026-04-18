from __future__ import annotations

import dataclasses

import pytest

from yahtzee_autoresearch_common import (
    Action,
    BONUS_YAHTZEE_SCORE,
    Category,
    DICE_PER_ROLL,
    FULL_HOUSE_SCORE,
    LARGE_STRAIGHT_SCORE,
    LOWER_CATEGORIES,
    NUM_CATEGORIES,
    NUM_ROUNDS,
    ROLLS_PER_ROUND,
    RerollAction,
    SMALL_STRAIGHT_SCORE,
    ScoreAction,
    Scorecard,
    TurnState,
    UPPER_BONUS,
    UPPER_BONUS_THRESHOLD,
    UPPER_CATEGORIES,
    YAHTZEE_SCORE,
)


# --- Category / constants -------------------------------------------------


def test_category_has_13_members_with_contiguous_values():
    values = [c.value for c in Category]
    assert values == list(range(NUM_CATEGORIES))


def test_upper_and_lower_categories_partition_all_categories():
    assert set(UPPER_CATEGORIES) | set(LOWER_CATEGORIES) == set(Category)
    assert set(UPPER_CATEGORIES) & set(LOWER_CATEGORIES) == set()
    assert len(UPPER_CATEGORIES) == 6
    assert len(LOWER_CATEGORIES) == 7


def test_upper_face_values_align_with_category_index():
    # Category.ONES=0 represents scoring 1s, so face = category.value + 1.
    for face, cat in enumerate(UPPER_CATEGORIES, start=1):
        assert cat.value + 1 == face


def test_scoring_constants_match_rules():
    assert YAHTZEE_SCORE == 50
    assert BONUS_YAHTZEE_SCORE == 100
    assert FULL_HOUSE_SCORE == 25
    assert SMALL_STRAIGHT_SCORE == 30
    assert LARGE_STRAIGHT_SCORE == 40
    assert UPPER_BONUS == 35
    assert UPPER_BONUS_THRESHOLD == 63
    assert DICE_PER_ROLL == 5
    assert NUM_ROUNDS == 13
    assert ROLLS_PER_ROUND == 3


# --- Scorecard -----------------------------------------------------------


def test_empty_scorecard_has_no_scores():
    sc = Scorecard.empty()
    assert sc.scores == (None,) * NUM_CATEGORIES
    assert sc.filled_categories == ()
    assert sc.open_categories == tuple(Category)
    assert sc.round_index == 0
    assert not sc.is_complete
    assert sc.total == 0
    assert sc.upper_subtotal == 0
    assert sc.upper_bonus == 0


def test_is_filled_reflects_category_presence():
    sc = Scorecard.empty().with_score(Category.ONES, 3)
    assert sc.is_filled(Category.ONES)
    assert not sc.is_filled(Category.TWOS)


def test_with_score_is_pure_and_immutable():
    sc = Scorecard.empty()
    sc2 = sc.with_score(Category.CHANCE, 20)
    # Original is unchanged.
    assert sc.scores == (None,) * NUM_CATEGORIES
    assert sc.total == 0
    # New scorecard has the score.
    assert sc2.scores[Category.CHANCE] == 20
    assert sc2 is not sc


def test_with_score_rejects_refilling():
    sc = Scorecard.empty().with_score(Category.FIVES, 15)
    with pytest.raises(ValueError):
        sc.with_score(Category.FIVES, 20)


def test_with_score_accepts_zero_as_a_valid_filled_score():
    sc = Scorecard.empty().with_score(Category.YAHTZEE, 0)
    assert sc.is_filled(Category.YAHTZEE)
    assert sc.scores[Category.YAHTZEE] == 0
    assert Category.YAHTZEE in sc.filled_categories
    assert Category.YAHTZEE not in sc.open_categories


def test_filled_and_open_categories_are_complementary():
    sc = (
        Scorecard.empty()
        .with_score(Category.ONES, 2)
        .with_score(Category.CHANCE, 18)
    )
    filled = set(sc.filled_categories)
    open_ = set(sc.open_categories)
    assert filled == {Category.ONES, Category.CHANCE}
    assert filled.isdisjoint(open_)
    assert filled | open_ == set(Category)


def test_round_index_increments_with_each_fill():
    sc = Scorecard.empty()
    for i, cat in enumerate(Category):
        assert sc.round_index == i
        sc = sc.with_score(cat, 0)
    assert sc.round_index == NUM_CATEGORIES
    assert sc.is_complete


def test_upper_subtotal_sums_upper_only():
    sc = (
        Scorecard.empty()
        .with_score(Category.ONES, 3)
        .with_score(Category.SIXES, 24)
        .with_score(Category.CHANCE, 30)
    )
    assert sc.upper_subtotal == 27
    assert sc.upper_bonus == 0


def test_upper_bonus_triggers_exactly_at_threshold():
    sc = Scorecard.empty()
    # 3+6+9+12+15+18 = 63
    for face, cat in enumerate(UPPER_CATEGORIES, start=1):
        sc = sc.with_score(cat, 3 * face)
    assert sc.upper_subtotal == UPPER_BONUS_THRESHOLD
    assert sc.upper_bonus == UPPER_BONUS


def test_upper_bonus_not_triggered_just_below_threshold():
    sc = Scorecard.empty()
    # Score one less than threshold in the upper section.
    for face, cat in enumerate(UPPER_CATEGORIES, start=1):
        sc = sc.with_score(cat, 3 * face)
    # Swap the SIXES score for one less to drop below threshold.
    new_scores = list(sc.scores)
    new_scores[Category.SIXES] = 17  # 3+6+9+12+15+17 = 62
    sc = Scorecard(scores=tuple(new_scores))
    assert sc.upper_subtotal == 62
    assert sc.upper_bonus == 0


def test_total_includes_upper_bonus():
    sc = Scorecard.empty()
    for face, cat in enumerate(UPPER_CATEGORIES, start=1):
        sc = sc.with_score(cat, 3 * face)
    assert sc.total == UPPER_BONUS_THRESHOLD + UPPER_BONUS


def test_total_sums_all_filled_categories():
    sc = (
        Scorecard.empty()
        .with_score(Category.CHANCE, 24)
        .with_score(Category.YAHTZEE, YAHTZEE_SCORE)
    )
    assert sc.total == 24 + YAHTZEE_SCORE


def test_scorecard_is_frozen():
    sc = Scorecard.empty()
    with pytest.raises(dataclasses.FrozenInstanceError):
        sc.scores = (0,) * NUM_CATEGORIES  # type: ignore[misc]


def test_scorecard_equality_and_hashability():
    a = Scorecard.empty().with_score(Category.ONES, 3)
    b = Scorecard.empty().with_score(Category.ONES, 3)
    assert a == b
    assert hash(a) == hash(b)


# --- Actions -------------------------------------------------------------


def test_reroll_action_stores_mask():
    a = RerollAction(reroll_mask=(True, False, True, False, False))
    assert a.reroll_mask == (True, False, True, False, False)


def test_reroll_action_is_frozen():
    a = RerollAction(reroll_mask=(True,) * DICE_PER_ROLL)
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.reroll_mask = (False,) * DICE_PER_ROLL  # type: ignore[misc]


def test_score_action_stores_category():
    a = ScoreAction(category=Category.LARGE_STRAIGHT)
    assert a.category == Category.LARGE_STRAIGHT


def test_action_union_admits_both_variants():
    actions: list[Action] = [
        RerollAction(reroll_mask=(False,) * DICE_PER_ROLL),
        ScoreAction(category=Category.CHANCE),
    ]
    assert isinstance(actions[0], RerollAction)
    assert isinstance(actions[1], ScoreAction)


# --- TurnState -----------------------------------------------------------


def test_turn_state_holds_snapshot_fields():
    sc = Scorecard.empty()
    ts = TurnState(dice=(1, 2, 3, 4, 5), rolls_remaining=2, scorecard=sc)
    assert ts.dice == (1, 2, 3, 4, 5)
    assert ts.rolls_remaining == 2
    assert ts.scorecard is sc


def test_turn_state_is_frozen():
    ts = TurnState(
        dice=(1, 1, 1, 1, 1),
        rolls_remaining=0,
        scorecard=Scorecard.empty(),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        ts.rolls_remaining = 1  # type: ignore[misc]
