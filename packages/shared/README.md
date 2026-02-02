# Shared Utilities

Common utilities shared across all fantasy applications.

## Contents

- **`llm_client.py`** - Generic LLM client for OpenAI and Anthropic APIs
- **`slack_notifier.py`** - Slack webhook/bot integration for notifications
- **`logger.py`** - Centralized logging configuration

## Usage

From any app, import shared utilities:

```python
from shared.llm_client import LLMClient
from shared.slack_notifier import SlackNotifier
from shared.logger import get_logger

# Use in your app
logger = get_logger(__name__)
```

## Installation

Install shared dependencies:

```bash
pip install -r requirements.txt
```
