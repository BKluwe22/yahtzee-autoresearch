# Overview

Experimenting with how strong of a solitaire Yahtzee strategy an autoresearch loop can discover.

## Packages

### yahtzee-autoresearch-evaluation

Yahtzee evalutation package that the agent will use to test its strategy. This package will be read-only to all agents. The test for how good a strategy is will be based on 1,000,000 simulated games given how much randomness determines the outcome of each individual game. The evaluation metric to optimize for is the the median score across the simulated games.

### yahtzee-autoresearch-strategy

Effectively the agent's playground to develop a strategy and the only package that the coding agent will be allowed to write to. The agent will iterate on the core "decision function" (call it `act`) of Yahtzee. In Yahtzee, there are three decisions per round and 13 rounds per game - so 39 total decisions. The outcome of each decision is either to hold out a subset of the five dice and re-roll or score a category. I have no opinions about the general approach the strategy should take. However, there will be a few constraints. 

Given that each experiment will involve a simulation of 1,000,000 games, I want to have a reasonable wall time on a GH action runner. I will set an arbitrary condition that the `act` runs in <= 100ms. This will be enforced via tests.

### yahtzee-autoresearch-common

Data models, common utils, etc. This will also be read-only for agents.

### yahtzee-autoresearch-agents

Contains "autoresearch" agents:

1. Research agent
Given a set of prior experiments with results, the research agent will instruct the coding agent to make updates to the strategy.

2. Coding agent
Vanilla claude code instance with some hooks to prevent modification of read-only packages

3. Reporting agent
Generates a markdown report of the experiment that the research agent can use to inform future experiment design.


## Loop design

Research Agent:
1. The research agent will read the top-N previous experiment results
2. The research agent will develop an approach / plan to improve the strategy
3. The research agent will pass the plan to the coding agent

Coding Agent:
4. The coding agent will implement the plan
5. Repeat step 4 until all constraints on the strategy enforced by tests are met. Add guardrail to prevent infinte loop.

Evaluation:
6. Once the gate is passed, the 1,000,000 games using the strategy will be simulated with a random, random seed.

Reporting Agent:
7. The reporting agent will analyze the results and create an experiment report that a new instance of the research agent can use to improve the strategy.
