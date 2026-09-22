# 🏈 Football Recap

Weekly Yahoo Fantasy Football recap generator in one house voice:
**The Commissioner's Ghost** (Bill Simmons × The Onion, Slack-native).
Python fetches league data and shapes a rich prompt context; the
**Cursor Automation** agent writes the recap and drafts it to Slack
for review.

## Architecture

```
Yahoo Fantasy API (shared OAuth2 at packages/shared/yahoo/)
  → prepare_recap_context.py       # fetch + shape (Python, no LLM)
  → output/week-N-context.md       # data bundle for the agent
  → Cursor Automation agent        # writes recap (Sonnet / Opus)
  → finalize_recap.py              # updates recap_history.json
  → Slack draft in #cx-retention-fantasy-football
  → prepare_league_hq_canvas.py    # refresh the League HQ Slack Canvas
```

Runs as a **Cursor Automation** (weekly Tuesday cron). No FastAPI server,
no local cron, no Anthropic API key in cloud. See
[`docs/AUTOMATION_SPEC.md`](docs/AUTOMATION_SPEC.md).

## Quick start

1. **Yahoo OAuth token.** One token covers all your Yahoo fantasy games.
   For the automation, set `YAHOO_OAUTH_JSON` in the
   [Cloud Agents dashboard](https://cursor.com/dashboard?tab=cloud-agents).
   Locally, reuse `apps/baseball-engine/config/oauth2.json` or set the same
   env var in `.env`.

2. **Sanity check (no network).**
   ```bash
   .venv/bin/python apps/football-recap/scripts/validate_pipeline.py
   ```

3. **Prepare context (Yahoo pull).**
   ```bash
   .venv/bin/python apps/football-recap/scripts/prepare_recap_context.py \
     --week 1
   ```
   Writes `output/week-1-context.md`.

4. **Wire up the Cursor Automation.** Open the Agents Window, enable
   **Send to Slack**, pick **Claude Sonnet**, and paste the prompt from
   [`docs/AUTOMATION_SPEC.md`](docs/AUTOMATION_SPEC.md).

5. **Optional local full recap** (needs `ANTHROPIC_API_KEY` in `.env`):
   ```bash
   .venv/bin/python apps/football-recap/scripts/scheduled_recap.py \
     --week 1 --dry-run
   ```

## Configuration

- [`config/config.example.json`](config/config.example.json) — league id
  (1324751), season year (2026), sport (`nfl`). Copy to `config.json` to
  customize.
- [`config/env.example`](config/env.example) — every environment variable
  the pipeline understands.

## Layout

```
apps/football-recap/
├── config/                        Yahoo config + example env
├── docs/
│   ├── AUTOMATION_SPEC.md         Weekly Cursor Automation
│   ├── API_INTEGRATIONS.md        Fun/data-source ideas backlog
│   ├── COLUMNIST_PROMPT_V3.md     House voice (The Commissioner's Ghost)
│   └── SLACK_INTEGRATION.md       Slack draft flow, OAuth setup
├── prompts/                       Modular prompt fragments
├── scripts/
│   ├── prepare_recap_context.py   Production: Yahoo fetch + context bundle
│   ├── finalize_recap.py          Production: update recap_history.json
│   ├── prepare_league_hq_canvas.py Weekly League HQ Canvas (needs Yahoo data)
│   ├── prepare_preseason_canvas.py Preseason Canvas (no Yahoo fetch)
│   ├── scheduled_recap.py         Optional local run (Anthropic API)
│   ├── validate_pipeline.py       Synthetic E2E integration check
│   ├── example_generate_recap.py  Ad-hoc single-week generation
│   ├── compare_models.py          A/B test Claude vs GPT
│   ├── sync_history_from_output.py Repair recap_history.json from output/
│   └── christmas_eve_recap.py     Seasonal one-off
├── tests/                         Unit tests (unittest; ``python3 -m unittest``)
└── src/
    ├── yahoo_fetcher.py           Yahoo API + in-process data shaping
    ├── fetch_league_data.py       Config loader + fetcher factory
    ├── context_builder.py         Prompt context from week_data
    ├── recap_generator.py         Orchestrates fetch → LLM → save
    ├── canvas_builder.py          League HQ Slack Canvas markdown
    ├── season_leaderboard.py      Season awards (Bench Whisperer, etc.)
    ├── llm_client.py              Anthropic / OpenAI wrappers
    ├── constants.py               Owner map, thresholds, season dates
    ├── ownership_stats.py         Sleeper ownership signals for roasts
    ├── prompt_builder.py          Loads V3 only
    ├── safe_calendar.py           Allowlist holiday / NFL-week hooks
    └── trend_tracker.py           Multi-week streak tracking
```

## What's new in 2026

- **Migrated from ESPN → Yahoo** (league 1324751). The shared Yahoo OAuth2
  client at `packages/shared/yahoo/` is used by both baseball and football.
- **Retired the local FastAPI + web UI.** Everything runs in-process; the
  Cursor Automation is the only production entrypoint.
- **De-duplicated shared utilities.** Slack/logger imports now come from
  `packages/shared/`.
- **Cursor-native automation.** Python shapes data; the automation agent
  writes the recap (Sonnet recommended). No Anthropic key in cloud.
- **Engagement layer:** Weekly Superlatives + GIF of the Week in every recap.
- **League HQ Canvas:** persistent Slack Canvas in
  `#cx-retention-fantasy-football` — standings, power rankings, and
  season awards (Bench Whisperer, Iron Stomach, etc.), updated after
  each recap. Preseason preview uses known managers + empty tables
  until Yahoo API access is restored. Reaction-triggered roasts are
  deferred.
- **Tests.** `apps/football-recap/tests/` covers the Yahoo fetcher helpers,
  the superlatives thresholds, the GIF picker priority, and the full context
  builder shape — run with:

  ```bash
  .venv/bin/python -m unittest discover -s apps/football-recap/tests -t apps/football-recap
  ```

## Related

- Baseball counterpart: [`../baseball-engine`](../baseball-engine)
- Shared Yahoo client: [`packages/shared/yahoo`](../../packages/shared/yahoo)
- Shared Slack notifier + LLM client: [`packages/shared`](../../packages/shared)
