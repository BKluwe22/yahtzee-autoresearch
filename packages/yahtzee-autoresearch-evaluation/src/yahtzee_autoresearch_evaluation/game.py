from __future__ import annotations

import random
from typing import Callable

from yahtzee_autoresearch_common import (
    Action,
    NUM_ROUNDS,
    RerollAction,
    ScoreAction,
    Scorecard,
    TurnState,
    apply_score,
    reroll,
    roll_dice,
)


ActFn = Callable[[TurnState], Action]


def play_game(act: ActFn, rng: random.Random) -> int:
    """Play one full game with `act` and return the final score.

    Each of the 13 rounds grants up to three rolls. The strategy sees a
    `TurnState` and returns either a `RerollAction` (only valid while rolls
    remain) or a `ScoreAction`. On the third roll the strategy must score;
    returning a `RerollAction` then raises.
    """
    sc = Scorecard.empty()
    for _ in range(NUM_ROUNDS):
        dice = roll_dice(rng)
        for rolls_remaining in (2, 1, 0):
            action = act(TurnState(dice=dice, rolls_remaining=rolls_remaining, scorecard=sc))
            if action.__class__ is ScoreAction:
                sc = apply_score(sc, dice, action.category)  # type: ignore[union-attr]
                break
            if rolls_remaining == 0:
                raise RuntimeError(
                    "Strategy returned a RerollAction with no rolls remaining"
                )
            if action.__class__ is not RerollAction:
                raise TypeError(
                    f"act() must return RerollAction or ScoreAction, got {type(action).__name__}"
                )
            dice = reroll(dice, action.reroll_mask, rng)  # type: ignore[union-attr]
    return sc.total


__all__ = ["ActFn", "play_game"]
