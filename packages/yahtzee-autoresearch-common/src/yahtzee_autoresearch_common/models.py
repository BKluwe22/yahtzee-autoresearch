from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Category(IntEnum):
    ONES = 0
    TWOS = 1
    THREES = 2
    FOURS = 3
    FIVES = 4
    SIXES = 5
    THREE_OF_A_KIND = 6
    FOUR_OF_A_KIND = 7
    FULL_HOUSE = 8
    SMALL_STRAIGHT = 9
    LARGE_STRAIGHT = 10
    YAHTZEE = 11
    CHANCE = 12


NUM_CATEGORIES: int = 13
DICE_PER_ROLL: int = 5
FACES: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
NUM_ROUNDS: int = 13
ROLLS_PER_ROUND: int = 3

UPPER_CATEGORIES: tuple[Category, ...] = (
    Category.ONES,
    Category.TWOS,
    Category.THREES,
    Category.FOURS,
    Category.FIVES,
    Category.SIXES,
)
LOWER_CATEGORIES: tuple[Category, ...] = (
    Category.THREE_OF_A_KIND,
    Category.FOUR_OF_A_KIND,
    Category.FULL_HOUSE,
    Category.SMALL_STRAIGHT,
    Category.LARGE_STRAIGHT,
    Category.YAHTZEE,
    Category.CHANCE,
)

UPPER_BONUS_THRESHOLD: int = 63
UPPER_BONUS: int = 35
YAHTZEE_SCORE: int = 50
BONUS_YAHTZEE_SCORE: int = 100
FULL_HOUSE_SCORE: int = 25
SMALL_STRAIGHT_SCORE: int = 30
LARGE_STRAIGHT_SCORE: int = 40

Dice = tuple[int, int, int, int, int]
RerollMask = tuple[bool, bool, bool, bool, bool]


@dataclass(frozen=True, slots=True)
class Scorecard:
    scores: tuple[int | None, ...]

    @classmethod
    def empty(cls) -> "Scorecard":
        return cls(scores=(None,) * NUM_CATEGORIES)

    def is_filled(self, category: Category) -> bool:
        return self.scores[category] is not None

    @property
    def filled_categories(self) -> tuple[Category, ...]:
        return tuple(Category(i) for i, s in enumerate(self.scores) if s is not None)

    @property
    def open_categories(self) -> tuple[Category, ...]:
        return tuple(Category(i) for i, s in enumerate(self.scores) if s is None)

    @property
    def upper_subtotal(self) -> int:
        return sum((self.scores[c] or 0) for c in UPPER_CATEGORIES)

    @property
    def upper_bonus(self) -> int:
        return UPPER_BONUS if self.upper_subtotal >= UPPER_BONUS_THRESHOLD else 0

    @property
    def total(self) -> int:
        base = sum(s for s in self.scores if s is not None)
        return base + self.upper_bonus

    @property
    def round_index(self) -> int:
        return sum(1 for s in self.scores if s is not None)

    @property
    def is_complete(self) -> bool:
        return all(s is not None for s in self.scores)

    def with_score(self, category: Category, score: int) -> "Scorecard":
        if self.scores[category] is not None:
            raise ValueError(f"Category {category.name} already filled")
        new_scores = list(self.scores)
        new_scores[category] = score
        return Scorecard(scores=tuple(new_scores))


@dataclass(frozen=True, slots=True)
class RerollAction:
    """Reroll the dice at positions where mask is True. Mask aligns with the
    current (sorted, ascending) dice tuple."""

    reroll_mask: RerollMask


@dataclass(frozen=True, slots=True)
class ScoreAction:
    """Commit the current dice to the given category."""

    category: Category


Action = RerollAction | ScoreAction


@dataclass(frozen=True, slots=True)
class TurnState:
    """Snapshot handed to a strategy's `act` function.

    `rolls_remaining` is the number of rerolls still available after the
    current dice: 2 after the first roll, 1 after the second, 0 after the
    third (at which point the strategy must return a `ScoreAction`).
    """

    dice: Dice
    rolls_remaining: int
    scorecard: Scorecard

