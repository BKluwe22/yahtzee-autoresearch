from __future__ import annotations

import pytest

from yahtzee_autoresearch_common import (
    BONUS_YAHTZEE_SCORE,
    Category,
    FULL_HOUSE_SCORE,
    LARGE_STRAIGHT_SCORE,
    SMALL_STRAIGHT_SCORE,
    Scorecard,
    UPPER_BONUS,
    YAHTZEE_SCORE,
    apply_score,
    base_score,
    enumerate_sorted_dice,
    is_yahtzee,
    legal_categories,
    score_for,
    sort_dice,
)


def test_enumeration_counts_252():
    assert sum(1 for _ in enumerate_sorted_dice()) == 252


def test_sort_dice_canonicalises():
    assert sort_dice((3, 1, 4, 1, 5)) == (1, 1, 3, 4, 5)


def test_upper_scores_count_matching_faces():
    dice = (1, 1, 3, 3, 3)
    assert base_score(dice, Category.ONES) == 2
    assert base_score(dice, Category.THREES) == 9
    assert base_score(dice, Category.TWOS) == 0


def test_three_of_a_kind_sums_all_dice_when_triple_present():
    dice = (2, 3, 3, 3, 6)
    assert base_score(dice, Category.THREE_OF_A_KIND) == 17
    assert base_score(dice, Category.FOUR_OF_A_KIND) == 0


def test_four_of_a_kind_requires_four_matching():
    dice = (4, 4, 4, 4, 2)
    assert base_score(dice, Category.FOUR_OF_A_KIND) == 18
    assert base_score(dice, Category.THREE_OF_A_KIND) == 18


def test_full_house_is_25_for_three_plus_two():
    assert base_score((2, 2, 5, 5, 5), Category.FULL_HOUSE) == FULL_HOUSE_SCORE
    assert base_score((1, 2, 3, 4, 5), Category.FULL_HOUSE) == 0


def test_full_house_not_awarded_for_yahtzee_without_joker():
    # A raw Yahtzee does not satisfy 3+2 pattern under strict rules.
    assert base_score((6, 6, 6, 6, 6), Category.FULL_HOUSE) == 0


def test_small_straight_any_four_in_a_row():
    assert base_score((1, 2, 3, 4, 4), Category.SMALL_STRAIGHT) == SMALL_STRAIGHT_SCORE
    assert base_score((2, 3, 4, 5, 5), Category.SMALL_STRAIGHT) == SMALL_STRAIGHT_SCORE
    assert base_score((3, 4, 5, 6, 6), Category.SMALL_STRAIGHT) == SMALL_STRAIGHT_SCORE
    assert base_score((1, 2, 3, 5, 6), Category.SMALL_STRAIGHT) == 0


def test_large_straight_all_five_in_a_row():
    assert base_score((1, 2, 3, 4, 5), Category.LARGE_STRAIGHT) == LARGE_STRAIGHT_SCORE
    assert base_score((2, 3, 4, 5, 6), Category.LARGE_STRAIGHT) == LARGE_STRAIGHT_SCORE
    assert base_score((1, 2, 3, 4, 6), Category.LARGE_STRAIGHT) == 0


def test_large_straight_counts_as_small_straight_too():
    assert base_score((1, 2, 3, 4, 5), Category.SMALL_STRAIGHT) == SMALL_STRAIGHT_SCORE


def test_yahtzee_50_and_chance_sum():
    dice = (5, 5, 5, 5, 5)
    assert base_score(dice, Category.YAHTZEE) == YAHTZEE_SCORE
    assert base_score(dice, Category.CHANCE) == 25
    assert is_yahtzee(dice)


def test_chance_is_sum_for_any_roll():
    assert base_score((1, 2, 3, 4, 5), Category.CHANCE) == 15


def test_apply_score_marks_category_filled():
    sc = Scorecard.empty()
    sc = apply_score(sc, (1, 2, 3, 4, 5), Category.LARGE_STRAIGHT)
    assert sc.is_filled(Category.LARGE_STRAIGHT)
    assert sc.scores[Category.LARGE_STRAIGHT] == LARGE_STRAIGHT_SCORE


def test_apply_score_rejects_double_fill():
    sc = Scorecard.empty().with_score(Category.ONES, 3)
    with pytest.raises(ValueError):
        apply_score(sc, (1, 1, 1, 2, 3), Category.ONES)


def test_upper_bonus_awarded_above_threshold():
    # 3+6+9+12+15+18 = 63 -> bonus
    sc = Scorecard.empty()
    for face, cat in enumerate(
        [
            Category.ONES,
            Category.TWOS,
            Category.THREES,
            Category.FOURS,
            Category.FIVES,
            Category.SIXES,
        ],
        start=1,
    ):
        sc = sc.with_score(cat, 3 * face)
    assert sc.upper_subtotal == 63
    assert sc.upper_bonus == UPPER_BONUS
    assert sc.total == 63 + UPPER_BONUS


def test_upper_bonus_not_awarded_below_threshold():
    sc = Scorecard.empty().with_score(Category.ONES, 3).with_score(Category.TWOS, 4)
    assert sc.upper_bonus == 0


def test_bonus_yahtzee_writes_100_in_open_lower_categories():
    sc = Scorecard.empty().with_score(Category.YAHTZEE, YAHTZEE_SCORE)
    dice = (3, 3, 3, 3, 3)
    # Any open lower category can take the 100 when the house rule triggers.
    assert score_for(sc, dice, Category.THREE_OF_A_KIND) == BONUS_YAHTZEE_SCORE
    assert score_for(sc, dice, Category.FOUR_OF_A_KIND) == BONUS_YAHTZEE_SCORE
    assert score_for(sc, dice, Category.FULL_HOUSE) == BONUS_YAHTZEE_SCORE
    assert score_for(sc, dice, Category.SMALL_STRAIGHT) == BONUS_YAHTZEE_SCORE
    assert score_for(sc, dice, Category.LARGE_STRAIGHT) == BONUS_YAHTZEE_SCORE
    assert score_for(sc, dice, Category.CHANCE) == BONUS_YAHTZEE_SCORE


def test_bonus_yahtzee_upper_scores_at_face_value_not_100():
    sc = Scorecard.empty().with_score(Category.YAHTZEE, YAHTZEE_SCORE)
    dice = (4, 4, 4, 4, 4)
    # Upper categories are NOT eligible for the 100 — just normal face count.
    assert score_for(sc, dice, Category.FOURS) == 20
    sc2 = apply_score(sc, dice, Category.FOURS)
    assert sc2.scores[Category.FOURS] == 20


def test_bonus_yahtzee_not_triggered_when_prior_yahtzee_was_zero():
    sc = Scorecard.empty().with_score(Category.YAHTZEE, 0)
    dice = (2, 2, 2, 2, 2)
    # No bonus armed; categories score normally.
    assert score_for(sc, dice, Category.THREE_OF_A_KIND) == 10
    assert score_for(sc, dice, Category.FULL_HOUSE) == 0
    assert score_for(sc, dice, Category.CHANCE) == 10


def test_bonus_yahtzee_not_triggered_when_yahtzee_open():
    sc = Scorecard.empty()
    dice = (5, 5, 5, 5, 5)
    # Yahtzee still open -> no bonus, scoring is normal.
    assert score_for(sc, dice, Category.YAHTZEE) == YAHTZEE_SCORE
    assert score_for(sc, dice, Category.CHANCE) == 25
    assert score_for(sc, dice, Category.FULL_HOUSE) == 0


def test_legal_categories_are_simply_open_categories():
    sc = Scorecard.empty().with_score(Category.YAHTZEE, YAHTZEE_SCORE)
    dice = (3, 3, 3, 3, 3)
    # No forcing under the house rule: all remaining open categories are legal.
    assert set(legal_categories(sc)) == set(sc.open_categories)
    apply_score(sc, dice, Category.CHANCE)  # should not raise


def test_scorecard_total_no_separate_yahtzee_bonus_box():
    sc = (
        Scorecard.empty()
        .with_score(Category.CHANCE, 20)
        .with_score(Category.YAHTZEE, YAHTZEE_SCORE)
    )
    sc = apply_score(sc, (6, 6, 6, 6, 6), Category.LARGE_STRAIGHT)
    # Large Straight filled with the 100 house-rule bonus; no extra +100 box.
    assert sc.scores[Category.LARGE_STRAIGHT] == BONUS_YAHTZEE_SCORE
    assert sc.total == 20 + YAHTZEE_SCORE + BONUS_YAHTZEE_SCORE


def test_round_index_matches_filled_count():
    sc = Scorecard.empty()
    assert sc.round_index == 0
    sc = sc.with_score(Category.ONES, 1)
    assert sc.round_index == 1
    assert not sc.is_complete
