# Shared Utilities

Common Python utilities shared across fantasy sports apps.

## Modules

### `llm_client.py`
Unified interface for LLM providers (Claude, GPT-4).

```python
from packages.shared.llm_client import LLMClient

client = LLMClient()
response = client.generate(prompt="Analyze this player...")
```

### `logger.py`
Standardized logging configuration.

```python
from packages.shared.logger import get_logger

logger = get_logger(__name__)
logger.info("Processing data...")
```

### `slack_notifier.py`
Slack webhook integration for notifications.

```python
from packages.shared.slack_notifier import SlackNotifier

notifier = SlackNotifier()
notifier.send_message("Your recap is ready!")
```

## Installation

These utilities are automatically available when you install the root requirements.txt:

```bash
# From project root
pip install -r requirements.txt
```

## Usage

Import from any Python app in the monorepo:

```python
# From baseball-engine
from packages.shared.llm_client import LLMClient

# From football-recap
from packages.shared.slack_notifier import SlackNotifier
```

## Environment Variables

Required environment variables (set in root `.env`):

```bash
# LLM Providers
ANTHROPIC_API_KEY=your_claude_key
OPENAI_API_KEY=your_openai_key

# Slack (optional)
SLACK_WEBHOOK_URL=your_webhook_url
```

## Development

When adding new shared utilities:

1. Create the module in this directory
2. Update `__init__.py` with exports
3. Add dependencies to `requirements.txt`
4. Document the module in this README
5. Add usage examples

## Apps Using These Utilities

- `apps/baseball-engine` - Baseball analytics CLI
- `apps/football-recap` - ESPN recap generator
- `apps/baseball-api` - FastAPI backend
