# Workspace Guide

This monorepo contains multiple fantasy sports applications that share common utilities.

## Structure

### Apps (`apps/`)

Each app is a standalone application with its own:
- Source code (`src/`)
- Scripts (`scripts/`)
- Configuration (`config/`)
- Documentation (`docs/`)
- Dependencies (`requirements.txt`, `package.json`)

**Current Apps:**
1. **espn-fantasy-recap** - ESPN Fantasy Football weekly recap generator
2. **keeper-advisor** - Baseball keeper league decision advisor

### Shared Packages (`packages/`)

Common utilities shared across all apps:
- **shared/** - LLM clients, Slack notifications, logging

## Development Workflow

### Setting Up a New App

1. **Create App Directory**
   ```bash
   mkdir -p apps/my-new-app/{src,scripts,config,docs}
   cd apps/my-new-app
   ```

2. **Create package.json**
   ```json
   {
     "name": "@fantasy/my-new-app",
     "version": "0.1.0",
     "private": true
   }
   ```

3. **Create requirements.txt**
   ```txt
   # App-specific dependencies
   -r ../../packages/shared/requirements.txt
   
   # Add your dependencies here
   ```

4. **Import Shared Utilities**
   ```python
   # In your app code
   from shared.llm_client import LLMClient
   from shared.logger import get_logger
   ```

### Python Path Configuration

Apps need access to both their own `src/` and the shared `packages/` directory.

**Option 1: Use sys.path** (Recommended for scripts)
```python
import sys
from pathlib import Path

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent

sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / "packages"))

# Now you can import
from src.my_module import MyClass
from shared.llm_client import LLMClient
```

**Option 2: Set PYTHONPATH** (For servers/daemons)
```bash
export PYTHONPATH="/path/to/workspace/packages:/path/to/app:$PYTHONPATH"
python -m src.api
```

### Shared Utilities

#### LLM Client

```python
from shared.llm_client import LLMClient

# OpenAI
client = LLMClient()
response = client.generate_with_openai(
    system_prompt="You are a helpful assistant",
    user_prompt="Tell me about keeper leagues",
    client=openai_client
)

# Anthropic
response = client.generate_with_anthropic(
    system_prompt="You are a helpful assistant",
    user_prompt="Tell me about keeper leagues",
    client=anthropic_client
)
```

#### Slack Notifications

```python
from shared.slack_notifier import SlackNotifier

notifier = SlackNotifier()
notifier.send_message("Hello from my app!")
```

#### Logging

```python
from shared.logger import get_logger

logger = get_logger(__name__)
logger.info("Application started")
logger.error("Something went wrong")
```

## Testing

Each app should have its own test suite:

```bash
cd apps/my-app
python -m pytest tests/
```

## Deployment

Each app can be deployed independently:

```bash
cd apps/espn-fantasy-recap
./scripts/deploy.sh
```

## Best Practices

1. **Keep apps independent** - Each app should be self-contained
2. **Share common code** - Move reusable code to `packages/shared/`
3. **Document everything** - Each app should have comprehensive docs
4. **Use semantic versioning** - Version apps independently
5. **Test shared code** - Changes to shared packages affect all apps

## Adding New Shared Utilities

1. Add code to `packages/shared/`
2. Update `packages/shared/__init__.py`
3. Document in `packages/shared/README.md`
4. Test with all apps that use it

## Troubleshooting

### Import Errors

If you get `ModuleNotFoundError`:
1. Check your PYTHONPATH includes both app and packages
2. Verify `__init__.py` files exist
3. Check relative import paths

### Dependency Conflicts

If apps have conflicting dependencies:
1. Use virtual environments per app
2. Pin specific versions in requirements.txt
3. Consider moving shared deps to packages/shared/

## Questions?

Open an issue or check app-specific documentation.
