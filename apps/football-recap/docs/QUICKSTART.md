# Football Recap — Quickstart

Get from zero to your first Yahoo-backed recap context in about 10 minutes.

## 1. Prerequisites

- Python 3.13 (repo uses `.venv` at the workspace root)
- Yahoo OAuth token (`oauth2.json` or `YAHOO_OAUTH_JSON`)
- Cursor Desktop with **Send to Slack** enabled on your automation
- **Optional:** Anthropic API key — only for local full recap via
  `scheduled_recap.py`, not for the production automation

## 2. Install (root workspace)

```bash
cd /Users/tyler.hanlon/Documents/GitHub/fantasy
source .venv/bin/activate
pip install -r requirements.txt
pip install -r packages/shared/requirements.txt
```

## 3. Configure Yahoo access

Football looks for a Yahoo OAuth token in this order:

1. `apps/football-recap/config/oauth2.json`
2. `apps/baseball-engine/config/oauth2.json` (shared)
3. `YAHOO_OAUTH_JSON` env var

**For the Cursor Automation:** add `YAHOO_OAUTH_JSON` in the
[Cloud Agents dashboard](https://cursor.com/dashboard?tab=cloud-agents)
(paste the full JSON body).

After re-auth locally, refresh tokens and compare to your shell env:

```bash
.venv/bin/python apps/football-recap/scripts/sync_yahoo_cloud_secret.py --copy
```

## 4. First smoke test (no network)

```bash
.venv/bin/python apps/football-recap/scripts/validate_pipeline.py
```

Expected: all green checks.

## 5. Prepare context (Yahoo pull)

```bash
.venv/bin/python apps/football-recap/scripts/prepare_recap_context.py \
  --week 1
```

Writes `output/week-1-context.md` — this is what the automation agent
reads before writing the recap.

## 6. Wire up the Cursor Automation

Open the Agents Window and configure per [`AUTOMATION_SPEC.md`](AUTOMATION_SPEC.md):

- **Trigger:** Weekly Tuesday, 10 AM ET (`0 15 * * 2`)
- **Model:** Claude Sonnet (recommended)
- **Tools:** Send to Slack → `#cx-retention-fantasy-football`
- **Prompt:** paste from AUTOMATION_SPEC.md

## 7. Optional — local full recap (Anthropic API)

Only if you want to generate without Cursor:

```bash
cp apps/football-recap/config/env.example .env
# Set ANTHROPIC_API_KEY in .env

.venv/bin/python apps/football-recap/scripts/scheduled_recap.py \
  --week 1 --dry-run
```

## Troubleshooting

- **`No Yahoo OAuth token found`** — configure one of the three paths in §3.
- **`Yahoo OAuth token refresh failed`** — re-run OAuth in baseball-engine
  and refresh the cloud secret.
- **Empty / wrong owner display** — `TEAM_OWNERS` in `src/constants.py` is a display-name override only. Live Yahoo `team_name` comes from `week_data`; a rename in Yahoo is picked up on the next prepare/canvas run. Add a `TEAM_OWNERS` alias only if you want a nicer owner label than the Yahoo manager nickname.
- **Automation can't fetch Yahoo** — confirm `YAHOO_OAUTH_JSON` is set in
  Cloud Agents dashboard (`.env` is gitignored and won't exist in cloud).

## Where to look next

- [`AUTOMATION_SPEC.md`](AUTOMATION_SPEC.md) — full automation prompt + model pick
- [`COLUMNIST_PROMPT_V3.md`](COLUMNIST_PROMPT_V3.md) — voice and section requirements
- [`SLACK_INTEGRATION.md`](SLACK_INTEGRATION.md) — Slack draft flow
