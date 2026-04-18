"""Scaffolding tests for the strategy's `act` function.

These tests are intentionally strategy-agnostic: they check only that
`act`

  1. returns a well-formed `RerollAction` or `ScoreAction`,
  2. never selects an illegal category or a reroll when no rolls remain,
  3. completes within the per-call time budget declared in the README.

Strategic quality is out of scope — that's what the evaluation harness
measures.
"""
from __future__ import annotations

import random
import time

import pytest

from yahtzee_autoresearch_common import (
    Action,
    Category,
    DICE_PER_ROLL,
    NUM_ROUNDS,
    RerollAction,
    ScoreAction,
    Scorecard,
    TurnState,
    apply_score,
    legal_categories,
    reroll,
    roll_dice,
)
from yahtzee_autoresearch_strategy import act


ACT_TIME_LIMIT_S: float = 0.100  # Per the README contract.
NUM_FUZZ_GAMES: int = 50


# --- helpers --------------------------------------------------------------


def _assert_reroll_action_wellformed(action: RerollAction) -> None:
    mask = action.reroll_mask
    assert isinstance(mask, tuple), (
        f"RerollAction.reroll_mask must be a tuple, got {type(mask).__name__}"
    )
    assert len(mask) == DICE_PER_ROLL, (
        f"RerollAction.reroll_mask must have {DICE_PER_ROLL} entries, got {len(mask)}"
    )
    # bool only — not 0/1 ints — to match the RerollMask type alias.
    assert all(isinstance(b, bool) for b in mask), (
        f"RerollAction.reroll_mask entries must be bool, got "
        f"{[type(b).__name__ for b in mask]}"
    )


def _assert_score_action_legal(state: TurnState, action: ScoreAction) -> None:
    assert isinstance(action.category, Category), (
        f"ScoreAction.category must be a Category, got "
        f"{type(action.category).__name__}"
    )
    legal = legal_categories(state.scorecard)
    assert action.category in legal, (
        f"act chose illegal category {action.category.name}; legal options: "
        f"{[c.name for c in legal]}"
    )


def _assert_action_legal(state: TurnState, action: Action) -> None:
    """Raise on any contract or legality violation for `action` in `state`."""
    assert isinstance(action, (RerollAction, ScoreAction)), (
        f"act must return RerollAction or ScoreAction, got {type(action).__name__}"
    )
    if isinstance(action, RerollAction):
        assert state.rolls_remaining > 0, (
            "act returned a RerollAction with 0 rolls remaining; must ScoreAction"
        )
        _assert_reroll_action_wellformed(action)
    else:
        _assert_score_action_legal(state, action)


def _timed_act(state: TurnState) -> Action:
    """Call act(state), assert it returns within the per-call time budget."""
    start = time.perf_counter()
    action = act(state)
    elapsed = time.perf_counter() - start
    assert elapsed <= ACT_TIME_LIMIT_S, (
        f"act took {elapsed * 1000:.1f}ms, exceeding the "
        f"{ACT_TIME_LIMIT_S * 1000:.0f}ms per-call limit"
    )
    return action


def _play_validated_game(rng: random.Random) -> None:
    """Play one full game, validating every act() call."""
    sc = Scorecard.empty()
    for _ in range(NUM_ROUNDS):
        dice = roll_dice(rng)
        for rolls_remaining in (2, 1, 0):
            state = TurnState(dice=dice, rolls_remaining=rolls_remaining, scorecard=sc)
            action = _timed_act(state)
            _assert_action_legal(state, action)
            if isinstance(action, ScoreAction):
                sc = apply_score(sc, dice, action.category)
                break
            dice = reroll(dice, action.reroll_mask, rng)


# --- tests ----------------------------------------------------------------


def test_act_returns_legal_actions_across_many_full_games():
    """Fuzz: play NUM_FUZZ_GAMES full games, validating every call."""
    rng = random.Random(0)
    for _ in range(NUM_FUZZ_GAMES):
        _play_validated_game(rng)


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_act_must_score_when_zero_rolls_remain(seed: int):
    """With rolls_remaining=0 and any non-full scorecard, act must return
    a ScoreAction — a RerollAction is categorically illegal."""
    rng = random.Random(seed)
    sc = Scorecard.empty()
    # Partially fill to vary the legal set; stop short of fully filled.
    cats = list(Category)
    rng.shuffle(cats)
    for cat in cats[: rng.randint(0, NUM_ROUNDS - 2)]:
        sc = sc.with_score(cat, rng.randint(0, 30))
    dice = roll_dice(rng)
    state = TurnState(dice=dice, rolls_remaining=0, scorecard=sc)
    action = _timed_act(state)
    assert isinstance(action, ScoreAction), (
        f"Expected ScoreAction with rolls_remaining=0, got {type(action).__name__}"
    )
    _assert_score_action_legal(state, action)


def test_act_scores_into_the_only_open_category_when_game_is_ending():
    """When exactly one category is open, act has no meaningful choice — the
    score action must target that category. This pins down the edge case
    where `legal_categories` returns a singleton."""
    rng = random.Random(123)
    remaining = Category.CHANCE
    sc = Scorecard.empty()
    for cat in Category:
        if cat is remaining:
            continue
        sc = sc.with_score(cat, 0)
    assert legal_categories(sc) == (remaining,)
    for rolls_remaining in (2, 1, 0):
        state = TurnState(
            dice=roll_dice(rng), rolls_remaining=rolls_remaining, scorecard=sc
        )
        action = _timed_act(state)
        _assert_action_legal(state, action)
        if isinstance(action, ScoreAction):
            assert action.category is remaining


def test_act_respects_per_call_time_limit_under_load():
    """Stand-alone timing check so a perf regression surfaces clearly, even
    if the fuzz run above happens not to trip the bound on any single call."""
    rng = random.Random(7)
    sc = Scorecard.empty()
    for _ in range(500):
        dice = roll_dice(rng)
        state = TurnState(
            dice=dice,
            rolls_remaining=rng.choice((0, 1, 2)),
            scorecard=sc,
        )
        _timed_act(state)
