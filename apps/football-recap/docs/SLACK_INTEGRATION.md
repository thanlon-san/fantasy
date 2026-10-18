# Slack Integration

**TL;DR:** The weekly recap ships to
**#cx-retention-fantasy-football** (`C05QV3E5J22`) as a Slack **draft**
for review before posting. The Cursor Automation uses the built-in
**Send to Slack** tool — no webhook, no bot token, no Anthropic API key
in cloud.

## Why draft-first

Auto-posting a spicy LLM-generated roast to a league channel is a bad
first bet. The draft flow keeps a human (you) in the loop: the automation
writes the message into your Slack drafts UI, you skim it for anything
mean or off-topic, edit if needed, and hit send.

You can flip to auto-send later once the house voice is calibrated
— it's a one-line change in the automation prompt (swap
`slack_send_message_draft` for `slack_send_message`).

## Setup

1. In your Cursor Automation, enable **Send to Slack** and target channel
   `C05QV3E5J22` (`#cx-retention-fantasy-football`).
2. Configure the automation prompt per [`AUTOMATION_SPEC.md`](AUTOMATION_SPEC.md).
3. Ensure draft mode — review before send, never auto-post on the first run.

Optional: connect Slack MCP in **Cursor → Settings → MCP → Slack** if you
prefer MCP-based draft tools over the built-in Send to Slack action.

## Slack digest GIFs

The compact digest (`output/week-N-slack.md`) puts each week's GIF as a **bare
`https://media.giphy.com/...` URL on its own line** so Slack unfurls it inline.
Markdown image syntax (`![GIF](url)`) does not reliably preview in Slack.

## Manual / fallback path (raw HTTP)

If you want to post a recap manually from a shell without going through
the automation, the shared `SlackNotifier` still works via webhook or
bot token:

```bash
# env vars picked up by packages/shared/slack_notifier.py
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
# or
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_CHANNEL="#cx-retention-fantasy-football"

.venv/bin/python apps/football-recap/scripts/scheduled_recap.py --week 5
```

Without the `--dry-run` flag, this posts the recap directly via
`SlackNotifier.send_recap()`. Keep this path in your back pocket for
"the Cursor Automation is broken and I still need to ship this week's
recap" scenarios; the day-to-day flow should stay on the automation.

## Channel reference

| Name | Purpose | ID |
|------|---------|----|
| `#cx-retention-fantasy-football` | League chat + weekly recap drafts | `C05QV3E5J22` |

Channel is private on the DoorDash workspace; the automation will silently
fail if the Slack MCP account isn't a member.

## Troubleshooting

- **Automation posts nothing** — check that Slack MCP is authenticated in
  Cursor settings. The [automate skill](https://cursor.com/skills/automate)
  hard-stops if it can't authenticate the MCP before opening the editor.
- **Draft never appears in the UI** — Slack drafts are per-user; the
  automation writes to the drafts of whichever Slack account is bound to
  Cursor's Slack MCP. Confirm you're logged in to the same workspace.
- **Rate limiting** — the recap fires once per week; hitting Slack's rate
  limit here would take an unusual test loop. If you're mass-testing,
  target a personal DM (a `D…` channel id in the `slack` action resolves
  to a DM with the automation owner) instead.
