# Mismatch

A 2–4 player parlor game designed by the InterAI-Protocol multi-agent
team across five rounds (2026-04-27).

**Designed by:** Trident (concept) · polished and validated by Pharos
with input from Lodestar, Forge, Lumen, and SpinDrift.

---

## Players
2–4

## Items
- One standard 52-card deck
- Paper and pen (scoring)
- One coin (starting-player toss)

## Setup
Shuffle the deck. Deal cards face-up in a grid based on player count:

- **2 players:** 16 cards (4 × 4)
- **3 players:** 21 cards (3 × 7)
- **4 players:** 24 cards (4 × 6)

Flip the coin: the player who wins the toss goes first. Play proceeds
clockwise.

## Play
On your turn, name two face-up cards from the grid, then remove both.
Reveal them to all players, score the pair (see below), and place both
cards in a shared discard pile. They do not return to the grid.

**End-of-grid rule:** If only 2 cards remain and they share a rank,
remove them with no score change. The game ends immediately.

Play continues clockwise until every card has been removed.

## Scoring
- **Non-matching pair** (different ranks): **+1 point.**
- **Matching pair** (same rank, regardless of suit): **−5 points.**

Record each player's running total on paper.

## Winning
When the grid is empty, the player with the highest score wins. If two
or more players are tied for highest, they share the win.

## Variant — Weighted Mismatch
For experienced players who want higher stakes: when you pick up a
non-matching pair, score **+1 point for each rank of difference**
between the two cards (Ace = 1, 2–10 = face value, Jack = 11, Queen
= 12, King = 13). Matching pairs still score −5. This variant rewards
players who track which ranks remain and maximize the spread of their
picks.

---

## Design notes

Mismatch inverts the core mechanic of Memory (Concentration). Where
Memory rewards finding pairs, Mismatch penalizes them — turning a
recall task into one of calculated risk and pattern disruption.

### Selection process
- **Round 1** produced 5 candidate games from the team (Bid & Bluff,
  Quick Flip & Grab, Mismatch, Steady Countdown, Coin Chase).
- **Round 2** selected Mismatch unanimously (4-for-4 among voting
  agents) using a six-criterion rubric: engagement, accessibility,
  replayability, conflict resolution, material constraints, and a
  skill-vs-luck balance criterion added mid-round.
- **Round 3** polished the rules — pinned grid sizes per player count,
  resolved a confused "Aces=1, face cards=10" sentence into a clean
  Weighted variant, specified turn order and tiebreaker.
- **Round 4** stress-tested the rules via playtest and surfaced a
  forced-match endgame bug (when the last 2 cards share a rank, the
  active player has no agency to avoid the −5).
- **Round 5** (this card) applied the patch and shipped v2.

### Patch decisions in v2

| # | Patch | Verdict | Reason |
|---|-------|---------|--------|
| 1 | End-of-grid rule for forced-match | Applied | Eliminates zero-agency −5 decided by turn order, not skill |
| 2 | Removed redundant "return cards to box" line | Applied | Grid sizes already specify exact card counts |
| 3 | Kept tiebreaker rule | Rejected deletion | Seven words prevent a real mid-demo argument; explicit is better than implied |
| 4 | "Name … then remove" instead of "pick up" | Applied | Verbal commitment closes the "I hadn't committed yet" stress-argument |
