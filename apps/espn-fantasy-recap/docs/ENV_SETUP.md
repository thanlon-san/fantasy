# Environment Variable Setup

## Quick Setup (Recommended)

### 1. Copy the example file
```bash
cp env.example .env
```

### 2. Edit `.env` with your keys
```bash
# Open in your editor
nano .env
# or
code .env
# or
vim .env
```

### 3. Add your Anthropic API key
```env
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

**Get your key:** https://console.anthropic.com/

### 4. That's it!

All scripts will automatically load your key from `.env`:
- ✅ `example_generate_recap.py`
- ✅ `test_claude_model.py`
- ✅ `recap_generator.py`

## File Structure

```
fantasy/
├── .env                 # Your actual keys (NEVER commit!)
├── env.example          # Template (safe to commit)
└── .gitignore           # .env is ignored ✅
```

## Security Notes

- ✅ `.env` is in `.gitignore` - will not be committed to git
- ✅ Never share your `.env` file
- ✅ Never hardcode keys in your scripts
- ✅ If you accidentally commit keys, rotate them immediately

## Optional: Add OpenAI Key

If you want to use GPT models as an alternative:

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-openai-key-here
```

## Optional: Custom API URL

If running the API on a different host/port:

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
API_BASE_URL=http://your-server:8000
```

## Troubleshooting

### "No .env file found"
This is fine! The scripts will work with environment variables too:
```bash
export ANTHROPIC_API_KEY='your-key'
python3 example_generate_recap.py
```

### "API key not found"
Make sure your `.env` file has the correct key name:
- ✅ `ANTHROPIC_API_KEY=sk-ant-...`
- ❌ `ANTHROPIC_KEY=sk-ant-...`
- ❌ `API_KEY=sk-ant-...`

### "Permission denied" when copying
```bash
# Make sure you're in the project directory
cd /path/to/fantasy
cp env.example .env
```

## Alternative: Environment Variables

If you prefer not to use `.env` files:

```bash
# Add to your ~/.zshrc or ~/.bashrc
export ANTHROPIC_API_KEY='sk-ant-your-key-here'

# Or set temporarily
export ANTHROPIC_API_KEY='sk-ant-your-key-here'
python3 example_generate_recap.py
```

The `.env` file method is recommended because:
- Easier to manage
- No need to export every time
- Works across sessions
- Already gitignored

---

**Need help?** See [RECAP_USAGE.md](RECAP_USAGE.md) for more details.

