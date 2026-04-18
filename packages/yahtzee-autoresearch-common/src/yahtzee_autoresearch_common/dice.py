from __future__ import annotations

import random
from itertools import combinations_with_replacement
from typing import Iterable

from .models import DICE_PER_ROLL, Dice, RerollMask


FaceCounts = tuple[int, int, int, int, int, int]


def sort_dice(dice: Iterable[int]) -> Dice:
    """Return dice as a sorted (ascending) 5-tuple.

    All scoring code assumes dice are in this canonical form.
    """
    sorted_values = tuple(sorted(dice))
    if len(sorted_values) != DICE_PER_ROLL:
        raise ValueError(
            f"Expected {DICE_PER_ROLL} dice, got {len(sorted_values)}"
        )
    return sorted_values  # type: ignore[return-value]


def count_faces(dice: Iterable[int]) -> FaceCounts:
    """Return a 6-tuple of counts indexed by face - 1 (so index 0 = count of 1s)."""
    c = [0, 0, 0, 0, 0, 0]
    for v in dice:
        c[v - 1] += 1
    return (c[0], c[1], c[2], c[3], c[4], c[5])


def roll_dice(rng: random.Random, n: int = DICE_PER_ROLL) -> Dice:
    """Roll n fresh dice and return them sorted ascending."""
    values = sorted(rng.randint(1, 6) for _ in range(n))
    return tuple(values)  # type: ignore[return-value]


def reroll(dice: Dice, reroll_mask: RerollMask, rng: random.Random) -> Dice:
    """Reroll each die where `reroll_mask` is True and return sorted dice.

    Positions in `reroll_mask` align with positions in the (sorted) `dice`.
    """
    new_values = [
        rng.randint(1, 6) if flag else d
        for d, flag in zip(dice, reroll_mask)
    ]
    new_values.sort()
    return tuple(new_values)  # type: ignore[return-value]


def enumerate_sorted_dice() -> Iterable[Dice]:
    """Yield every distinct sorted dice combination (252 of them)."""
    return combinations_with_replacement(range(1, 7), DICE_PER_ROLL)  # type: ignore[return-value]


__all__ = [
    "FaceCounts",
    "sort_dice",
    "count_faces",
    "roll_dice",
    "reroll",
    "enumerate_sorted_dice",
]
