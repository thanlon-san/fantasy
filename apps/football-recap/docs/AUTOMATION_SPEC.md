# Weekly Recap — Cursor Automation Spec

Paste-ready spec for the **Cursor-native** weekly flow: Python fetches and
shapes Yahoo data; **you** (the automation agent) write the recap using
Cursor's model; **Send to Slack** creates a draft for review.

No `ANTHROPIC_API_KEY` required in cloud — only Yahoo OAuth.

---

## Recommended model

| Setting | Recommendation |
|---------|----------------|
| **Default** | **Claude Sonnet** (or the latest Sonnet-tier option in the automation picker) |
| **Premium** | **Claude Opus** if you want maximum roast quality and don't mind slower runs |

Sonnet is the sweet spot for this job: long structured output (all 14 power
rankings, 7 matchups, superlatives, GIF embed), strong instruction
following, and fast enough for a weekly cron. Opus is worth trying for
playoff weeks or if Sonnet ever feels flat.

---

## Draft table

| Draft field | Value |
|-------------|-------|
| Name | `Weekly Fantasy Football Recap` |
| Description | Fetches Yahoo data, writes the weekly roast recap, and drafts it to #cx-retention-fantasy-football for review. |
| Trigger | Schedule — every **Tuesday at 15:00 UTC** (10 AM ET, after MNF). Cron: `0 15 * * 2`. |
| Model | **Claude Sonnet** (recommended) or Claude Opus |
| Tools | **Send to Slack** — draft only, channel `C05QV3E5J22`. League HQ Canvas uses `slack_update_canvas` on `F0BRWD4TTK5`. |
| Instructions | See prompt block below |
| Resolved settings | Repo: `thanlon-san/fantasy` · Branch: `main` · Slack: `#cx-retention-fantasy-football` (`C05QV3E5J22`) · Canvas: `F0BRWD4TTK5` |
| Cloud secrets | `YAHOO_OAUTH_JSON` only — [Cloud Agents dashboard](https://cursor.com/dashboard?tab=cloud-agents) — paste the full oauth2.json body. No Anthropic key. |
| Start state | **Active** once `YAHOO_OAUTH_JSON` and Slack tools are set; use Inactive only while testing. |

---

## Prompt (paste as-is)

```
You generate the weekly Yahoo Fantasy Football recap for league 1324751 and hand it to me as a Slack draft for review.

## Voice & format (read before writing)

Follow every requirement in apps/football-recap/docs/COLUMNIST_PROMPT_V3.md. That file is the only voice source. You are The Commissioner's Ghost (Bill Simmons × The Onion, deadpan, Slack-native, harshness 4/10). Do not invent a weekly costume or PERSONA_SEED. Mandatory sections: Header, League Pulse, Stat of the Week, ALL matchups, ALL teams in power rankings, Week Preview, Closing, GIF embed. Do not skip sections. Do not invent matchups, rankings, or world events — use only the prepared context (week_data + optional CALENDAR_HOOK).

## Steps

Working directory: use the same cwd for steps 1–6. From monorepo root: cd apps/football-recap. Run scripts as ../../.venv/bin/python scripts/<name>.py (venv at repo root). All output/ paths below are apps/football-recap/output/ — do not mix with repo-root output/.

1. Determine WEEK:
- Default (from apps/football-recap cwd): ../../.venv/bin/python -c "from src.constants import get_current_nfl_week; print(get_current_nfl_week())"
- If this prompt specifies a week (e.g. "week 6"), use that instead.
- Kickoff is 2026-09-03 (NFL_SEASON_START_DATE). get_current_nfl_week() is calendar-based; Yahoo current_week may lag by one early in the week. Tuesday cron (after MNF) usually matches the week you want. For manual runs, pass --week explicitly if scores look wrong.
- After prepare (step 2), if week_data has all-zero scores but you expected real box scores, retry once with --week ($WEEK - 1), minimum 1.
- If today is before 2026-09-03, OR Yahoo returns 403 / league not found / no games played: do NOT write a fake recap. Draft a friendly "season hasn't started / Yahoo hasn't opened the league yet" note to C05QV3E5J22, update League HQ via prepare_preseason_canvas.py (step 6 preseason path), and stop.

2. Prepare data (Python — no LLM). Production path — not scheduled_recap.py:
../../.venv/bin/python scripts/prepare_recap_context.py --week $WEEK --no-news
(cwd: apps/football-recap). Writes output/week-$WEEK-context.md, output/week-$WEEK-context.meta.json, output/week-$WEEK-weekdata.json. --no-news is accepted and unused (NewsAPI is never injected). If the script exits non-zero due to OAuth / token / API auth (403, invalid_grant, etc.): do NOT draft to C05QV3E5J22 — players must never see auth or technical errors; stop. If failure is preseason / no games yet (not auth): friendly "season hasn't started" draft to C05QV3E5J22 is OK; then preseason Canvas path in step 6 and stop. Never invent scores or matchups.

3. Read the context file and COLUMNIST_PROMPT_V3.md. Write the full recap to output/week-$WEEK-recap.md (same cwd as finalize_recap.py). Requirements:
- Include every V3 section in order.
- Voice is The Commissioner's Ghost every week. No costume / PERSONA_SEED.
- Use the CLOSING LINE from the context file exactly.
- If CALENDAR_HOOK is present, you may nod to it once. If absent, skip.
- If BIT_OF_THE_WEEK is present, open League Pulse on that game.
- Include the GIF of the Week markdown line from the context (Slack renders Giphy URLs inline).
- Weave in 2–3 Weekly Superlatives from the context as callouts.
- Power Rankings must list ALL teams in THIS exact order from the prepared context. Copy 1:1. Do not reorder or invent ranks.
- Do not invent world events, news, politics, or celebrity scandal.

4. Finalize history:
../../.venv/bin/python scripts/finalize_recap.py --week $WEEK

5. Post a Slack draft (do NOT auto-send):
- Channel: C05QV3E5J22
- Text: bold header "🏈 Week $WEEK Recap — Draft (review before send)", blank line, then the full recap markdown from output/week-$WEEK-recap.md
Use Send to Slack in draft mode so Tyler can review and click Send manually. Never auto-send. Never post to any other channel.

6. Update the existing League HQ Canvas (do not create a new one):
After a successful prepare (weekdata on disk): ../../.venv/bin/python scripts/prepare_league_hq_canvas.py --week $WEEK --no-fetch
--week is required. --no-fetch reads output/week-$WEEK-weekdata.json so you do not hit Yahoo a second time. If that cache is missing, omit --no-fetch (live fetch, then cached fallback). Writes output/league-hq-canvas.md. Then slack_update_canvas on canvas_id F0BRWD4TTK5 (https://doordash.enterprise.slack.com/docs/T03NG2JH1/F0BRWD4TTK5) with that file. Read the canvas first if the tool needs current section IDs. Do not slack_create_canvas — League HQ already exists.
Preseason / Yahoo 403 / no week_data: ../../.venv/bin/python scripts/prepare_preseason_canvas.py (no --week). Writes output/league-hq-canvas.md (14 teams, draft order, placeholder standings). Then slack_update_canvas on F0BRWD4TTK5. Canvas step requires slack_update_canvas on the automation; if unavailable, skip Canvas and still post the recap draft.

## Constraints

- Never auto-post without review. Draft only, channel C05QV3E5J22.
- Do not call external Anthropic/OpenAI APIs — you are the writer.
- Cloud secret is YAHOO_OAUTH_JSON only. No Anthropic key is required.
- If Yahoo OAuth or token refresh fails: do not post to the league channel. Re-authorize offline and update YAHOO_OAUTH_JSON. If the league is not published yet (preseason only, not auth errors), a friendly preseason draft is OK — do not fabricate data.
- Do not fabricate scores, owners, or matchups — only use prepared context.
- Power rankings: copy the prepared list 1:1. Do not reorder.
- Reaction-triggered roasts are deferred — do not implement or run them.
```

---

## Preflight checklist

1. **Yahoo OAuth in cloud secrets**
   - [Cloud Agents dashboard](https://cursor.com/dashboard?tab=cloud-agents) → `YAHOO_OAUTH_JSON` = full JSON from `oauth2.json`
   - Source of truth locally: `apps/baseball-engine/config/oauth2.json`
   - After re-auth (`test_yahoo_oauth.py` or `setup_yahoo.py`), refresh the cloud secret.
   - Local runs prefer `apps/baseball-engine/config/oauth2.json` when present — updating only the cloud secret does not fix local until that file is refreshed (or removed so `YAHOO_OAUTH_JSON` can be written locally).
   - If **400 invalid_grant** on token refresh: refresh token expired or revoked — full browser re-auth required (`apps/baseball-engine/scripts/test_yahoo_oauth.py`), then update both local file and cloud secret.
   - Sync helper (validate file, refresh, compare env, copy for paste):
     ```bash
     cd apps/football-recap
     ../../.venv/bin/python scripts/sync_yahoo_cloud_secret.py
     ../../.venv/bin/python scripts/sync_yahoo_cloud_secret.py --copy
     ```
   - If **403** returns: re-authorize and update the secret; prompt drafts a friendly
     error + preseason Canvas (no fabricated scores).

2. **Slack** — **Send to Slack** (draft) to `C05QV3E5J22`. Canvas needs `slack_update_canvas` on `F0BRWD4TTK5`.

3. **Model** — Claude Sonnet (recommended)

4. **Automation** — Active when secrets + Slack tools are configured

5. **Local smoke test**:
   ```bash
   cd apps/football-recap
   ../../.venv/bin/python scripts/validate_pipeline.py
   ../../.venv/bin/python scripts/prepare_recap_context.py --week 1 --no-news
   ```
   Confirm `apps/football-recap/output/week-1-context.md` has real matchup data.

Local/manual Anthropic fallback (optional, **not** the automation path):
`scheduled_recap.py --week N --dry-run` if `ANTHROPIC_API_KEY` is in `.env`.

---

## Architecture

```
Tuesday cron (0 15 * * 2)
  → prepare_recap_context.py --week $WEEK --no-news
                             Yahoo fetch + context shaping (Python)
  → Cursor agent             Writes recap (Sonnet/Opus, V3 Ghost)
  → finalize_recap.py --week $WEEK
  → Send to Slack (draft)    #cx-retention-fantasy-football (C05QV3E5J22)
  → prepare_league_hq_canvas.py --week $WEEK --no-fetch
  → slack_update_canvas      F0BRWD4TTK5 (existing League HQ)
```

The League HQ Canvas is the living scoreboard (standings, power rankings,
season awards): https://doordash.enterprise.slack.com/docs/T03NG2JH1/F0BRWD4TTK5
The weekly recap is the story; the Canvas is the reference doc.
Reaction-triggered roasts are deferred.

### Team names (auto-refresh)

Live Yahoo `team_name` from `week_data` is the source of truth for recaps
and League HQ. `TEAM_OWNERS` in `src/constants.py` is only a display-name
override for `resolve_owner()`. If a manager renames their team in Yahoo,
the next `prepare_recap_context.py` / `prepare_league_hq_canvas.py` run
picks up the new name automatically — no code change, unless you want a
nicer owner label (add a `TEAM_OWNERS` alias).

`PRESEASON_MANAGERS_2026` is the fallback roster when `week_data` has no
teams (preseason / Yahoo API down). League is locked at 14 managers.
