# Fantasy Baseball Dashboard — Phase 3 Build Plan (In-Season Dominance)

This document outlines the next evolution of the 2balls Fantasy Baseball intelligence system. While Phase 1 & 2 focused on the Draft and baseline daily operations, Phase 3 focuses on advanced in-season roster management, predictive analytics, and exploiting daily/weekly edge cases.

---

## 1. The "Vulture Save" & Bullpen Fatigue Monitor

**The Goal:** Maximize the "Closer Stacking" strategy by exploiting bullpen fatigue to steal saves off the waiver wire.

**How it works:**
1. Use the `statsapi` (MLB Stats API) to pull daily pitch counts and appearances for all MLB relievers.
2. Calculate a "Fatigue Score" (e.g., pitched 3 consecutive days, or >45 pitches in last 3 days).
3. Map fatigued closers to their team's primary setup man (using the `ELITE_SETUP_MEN` list or RosterResource).
4. **Dashboard Output:** A daily "Bullpen Alert" widget: *"Emmanuel Clase is fatigued (3 straight days). Add Hunter Gaddis for a likely vulture save today."*

---

## 2. Rest-of-Season (ROS) Projections Engine

**The Goal:** Stop reacting to small sample sizes in April/May and start acquiring players based on what they *will* do.

**How it works:**
1. Build a scraper for FanGraphs (Steamer or ZiPS ROS projections).
2. Create a `/season/buy-low` endpoint that compares a player's current Yahoo rank/stats against their ROS projected value.
3. Combine this with the existing `BreakoutDetector` (Statcast data). 
4. **Dashboard Output:** A "Trade Targets / Buy Low" page highlighting players whose underlying metrics and ROS projections are elite, but whose surface-level Yahoo stats look terrible.

---

## 3. Category-Impact Trade Analyzer

**The Goal:** Evaluate trades based on *your* specific league standings, not generic player values.

**How it works:**
1. Create a `/season/trade-analyzer?give=PlayerA&get=PlayerB` endpoint.
2. The engine simulates removing Player A from your roster and adding Player B.
3. It recalculates your projected weekly totals for all 12 categories.
4. It compares those new totals against the rest of the league's averages.
5. **Dashboard Output:** *"This trade drops you from 3rd to 7th in HRs, but moves you from 9th to 2nd in SBs. Net weekly win probability: +8%."*

---

## 4. Weather & Park Factor Lineup Optimizer

**The Goal:** Squeeze extra stats out of your bench bats by playing the environment.

**How it works:**
1. Integrate a free weather API (e.g., OpenWeatherMap) and a static JSON of MLB Park Factors (e.g., Coors Field = 1.15 HR boost, T-Mobile Park = 0.85 HR penalty).
2. Update `lineup_optimizer.py` to adjust daily player projections based on the stadium they are playing in and the wind direction/speed.
3. **Dashboard Output:** The daily lineup recommendation includes notes: *"Started over [Player B] due to +15mph wind blowing out at Wrigley Field."*

---

## 5. Two-Start Pitcher Streamer (The K-Chaser)

**The Goal:** Since the strategy punts QS/W to focus on ratios, Strikeouts (K) must be manufactured efficiently.

**How it works:**
1. Update `daily_matchups.py` to look ahead to *next* week's MLB schedule.
2. Identify all SPs scheduled to make two starts.
3. Filter out highly-rostered players to find waiver-wire streamers.
4. Score the matchups based on the opponent's team strikeout rate (e.g., facing the White Sox and A's is a massive boost).
5. **Dashboard Output:** A "Look Ahead" widget that appears on Fridays/Saturdays: *"Pick up [Pitcher X] now — he has a two-start week against high-strikeout teams starting Monday."*

---

## 6. Minor League Prospect Stash Monitor

**The Goal:** Beat your league-mates to the next Jackson Holliday or Paul Skenes.

**How it works:**
1. Maintain a list of top 25 fantasy-relevant prospects in the minors.
2. Use the MiLB API to track their last 14 days of performance (OPS, K-BB%, Velocity).
3. **Dashboard Output:** A "Prospect Watch" tracker that alerts you when a top prospect is on a massive hot streak and rumors of a call-up are swirling.