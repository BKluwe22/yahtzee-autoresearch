from __future__ import annotations

import random

import pytest

from yahtzee_autoresearch_common import (
    Category,
    NUM_CATEGORIES,
    RerollAction,
    ScoreAction,
    TurnState,
)
from yahtzee_autoresearch_evaluation import play_game
from yahtzee_autoresearch_strategy import act as greedy_act


def test_play_game_returns_non_negative_int():
    score = play_game(greedy_act, random.Random(0))
    assert isinstance(score, int)
    assert score >= 0


def test_play_game_is_deterministic_for_the_same_rng_seed():
    a = play_game(greedy_act, random.Random(42))
    b = play_game(greedy_act, random.Random(42))
    assert a == b


def test_play_game_fills_all_13_categories():
    # Use a strategy that tracks how many categories it scores.
    fills: list[Category] = []

    def spying_act(state: TurnState):
        action = greedy_act(state)
        if isinstance(action, ScoreAction):
            fills.append(action.category)
        return action

    play_game(spying_act, random.Random(7))
    assert len(fills) == NUM_CATEGORIES
    assert set(fills) == set(Category)


def test_play_game_raises_if_strategy_never_scores():
    def always_reroll(state: TurnState):
        return RerollAction(reroll_mask=(True, True, True, True, True))

    with pytest.raises(RuntimeError):
        play_game(always_reroll, random.Random(0))


def test_play_game_raises_on_invalid_action_type():
    def bad_act(state: TurnState):
        return "not an action"  # type: ignore[return-value]

    with pytest.raises(TypeError):
        play_game(bad_act, random.Random(0))
