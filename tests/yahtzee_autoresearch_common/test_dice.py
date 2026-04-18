from __future__ import annotations

import random

import pytest

from yahtzee_autoresearch_common import (
    DICE_PER_ROLL,
    count_faces,
    enumerate_sorted_dice,
    reroll,
    roll_dice,
    sort_dice,
)


def test_sort_dice_returns_ascending_tuple():
    assert sort_dice((5, 1, 4, 1, 3)) == (1, 1, 3, 4, 5)


def test_sort_dice_accepts_any_iterable():
    assert sort_dice(iter([6, 2, 2, 1, 6])) == (1, 2, 2, 6, 6)


def test_sort_dice_returns_a_tuple():
    result = sort_dice([1, 2, 3, 4, 5])
    assert isinstance(result, tuple)
    assert len(result) == DICE_PER_ROLL


def test_sort_dice_rejects_wrong_length():
    with pytest.raises(ValueError):
        sort_dice((1, 2, 3))
    with pytest.raises(ValueError):
        sort_dice((1, 2, 3, 4, 5, 6))


def test_sort_dice_is_idempotent_on_already_sorted_input():
    d = (1, 2, 3, 4, 5)
    assert sort_dice(d) == d


def test_count_faces_counts_each_face():
    assert count_faces((1, 1, 3, 3, 3)) == (2, 0, 3, 0, 0, 0)
    assert count_faces((1, 2, 3, 4, 5)) == (1, 1, 1, 1, 1, 0)
    assert count_faces((6, 6, 6, 6, 6)) == (0, 0, 0, 0, 0, 5)


def test_count_faces_sum_equals_number_of_dice():
    dice = (2, 3, 3, 5, 6)
    counts = count_faces(dice)
    assert sum(counts) == len(dice)


def test_count_faces_handles_any_iterable():
    assert count_faces(iter([4, 4, 4, 1, 1])) == (2, 0, 0, 3, 0, 0)


def test_roll_dice_returns_sorted_5_tuple_by_default():
    rng = random.Random(0)
    d = roll_dice(rng)
    assert isinstance(d, tuple)
    assert len(d) == DICE_PER_ROLL
    assert list(d) == sorted(d)


def test_roll_dice_values_are_in_valid_face_range():
    rng = random.Random(42)
    for _ in range(200):
        for v in roll_dice(rng):
            assert 1 <= v <= 6


def test_roll_dice_respects_n_argument():
    rng = random.Random(0)
    d = roll_dice(rng, n=3)
    assert len(d) == 3
    assert list(d) == sorted(d)


def test_roll_dice_is_deterministic_for_seeded_rng():
    a = roll_dice(random.Random(1234))
    b = roll_dice(random.Random(1234))
    assert a == b


def test_reroll_keeps_dice_where_mask_is_false():
    rng = random.Random(0)
    dice = (1, 2, 3, 4, 5)
    mask = (False, False, True, True, True)
    new = reroll(dice, mask, rng)
    # Positions 0 and 1 (values 1, 2) are kept; they must still appear in output.
    kept_multiset = sorted([1, 2])
    combined = sorted(new)
    assert all(k in combined for k in kept_multiset)


def test_reroll_all_false_returns_same_dice():
    rng = random.Random(0)
    dice = (2, 3, 4, 5, 6)
    assert reroll(dice, (False,) * DICE_PER_ROLL, rng) == dice


def test_reroll_all_true_is_equivalent_to_a_fresh_roll():
    rng_a = random.Random(999)
    rng_b = random.Random(999)
    assert reroll(
        (1, 1, 1, 1, 1), (True,) * DICE_PER_ROLL, rng_a
    ) == roll_dice(rng_b)


def test_reroll_output_is_sorted():
    rng = random.Random(7)
    for _ in range(50):
        out = reroll((6, 6, 6, 6, 6), (True, True, True, True, True), rng)
        assert list(out) == sorted(out)
        assert len(out) == DICE_PER_ROLL


def test_enumerate_sorted_dice_yields_252_tuples():
    dice_list = list(enumerate_sorted_dice())
    assert len(dice_list) == 252


def test_enumerate_sorted_dice_yields_only_sorted_tuples_in_valid_range():
    for d in enumerate_sorted_dice():
        assert len(d) == DICE_PER_ROLL
        assert list(d) == sorted(d)
        assert all(1 <= v <= 6 for v in d)


def test_enumerate_sorted_dice_has_no_duplicates():
    dice_list = list(enumerate_sorted_dice())
    assert len(set(dice_list)) == len(dice_list)


def test_enumerate_sorted_dice_covers_every_canonical_roll():
    seen = set(enumerate_sorted_dice())
    # A few representative rolls must be in the enumeration.
    for d in [(1, 1, 1, 1, 1), (1, 2, 3, 4, 5), (2, 3, 4, 5, 6), (6, 6, 6, 6, 6)]:
        assert d in seen
