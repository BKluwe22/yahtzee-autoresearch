from __future__ import annotations

from yahtzee_autoresearch_common import (
    Action,
    Category,
    ScoreAction,
    TurnState,
    score_for,
)


def act(state: TurnState) -> Action:
    """Greedy baseline: always score immediately into the highest-scoring
    open category. Never rerolls. A starting point for the agent to iterate on."""
    best_cat = Category.CHANCE
    best_score = -1
    for cat in state.scorecard.open_categories:
        s = score_for(state.scorecard, state.dice, cat)
        if s > best_score:
            best_score = s
            best_cat = cat
    return ScoreAction(category=best_cat)

