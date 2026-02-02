# Prompt Architecture Guide

## 🎯 Why Modular Prompts?

### Current State

- **Monolithic:** Single 4,200-token `COLUMNIST_PROMPT.md` file
- **Problem:** All or nothing - can't adjust based on context
- **Cost:** Every request uses full prompt even if sections aren't needed

### Modular Benefits

| Benefit              | Impact                                               |
| -------------------- | ---------------------------------------------------- |
| **Token Efficiency** | Save 30-50% on requests by excluding unused sections |
| **Maintainability**  | Edit one section without touching others             |
| **Debugging**        | Test individual sections independently               |
| **Flexibility**      | Build different prompts for different scenarios      |
| **A/B Testing**      | Easily test prompt variations                        |
| **Version Control**  | Better git diffs (change one file vs entire prompt)  |

---

## 📁 Modular Structure

```
prompts/
├── 00_core_persona.md       # Persona, voice, mission (REQUIRED)
├── 01_structure.md          # Output format, length, ratio (REQUIRED)
├── 02_safety_rails.md       # What not to do (REQUIRED)
├── 03_data_grounding.md     # How to cite stats (REQUIRED)
├── 04_examples.md           # Example roasts (~800 tokens) [OPTIONAL]
├── 05_advanced_stats.md     # Position aggregates, optimal lineup (~600 tokens) [OPTIONAL]
├── 06_trends.md             # Multi-week trends (~400 tokens) [OPTIONAL]
├── 07_memory.md             # Repetition avoidance (~300 tokens) [OPTIONAL]
├── 08_league_context.md     # CRM jargon, league-specific (~200 tokens) [REQUIRED]
└── 09_final_reminder.md     # Go time (~100 tokens) [REQUIRED]
```

**Total:** ~4,200 tokens (full) | ~2,400 tokens (minimal)

---

## 🔧 Usage Examples

### Example 1: Weekly Recap (Full Power)

```python
from prompt_builder import PromptBuilder

builder = PromptBuilder()
prompt = builder.build_columnist_prompt(
    include_examples=True,      # Show example roasts
    include_advanced_stats=True, # Use position aggregates, optimal lineup
    include_trends=True,         # Use multi-week trends
    include_memory=True          # Avoid repeating previous weeks
)
# Result: ~4,200 tokens
```

### Example 2: Quick Summary (Minimal)

```python
prompt = builder.build_columnist_prompt(
    include_examples=False,     # Skip examples to save tokens
    include_advanced_stats=False, # Basic stats only
    include_trends=False,        # Current week only
    include_memory=False         # No memory lookup
)
# Result: ~2,400 tokens (43% savings!)
```

### Example 3: First Week of Season

```python
# No history exists yet, so skip trends and memory
prompt = builder.build_columnist_prompt(
    include_trends=False,  # No previous weeks
    include_memory=False   # No previous recaps
)
# Result: ~3,500 tokens
```

### Example 4: Mid-Season with Established Voice

```python
# Claude already knows the voice, skip examples
prompt = builder.build_columnist_prompt(
    include_examples=False,  # Already established
    include_trends=True,     # Use full trend data
    include_memory=True      # Check previous recaps
)
# Result: ~3,400 tokens
```

---

## 💰 Token Savings Calculator

| Scenario              | Tokens | Cost/1M tokens | Cost Savings    |
| --------------------- | ------ | -------------- | --------------- |
| Full prompt (current) | 4,200  | $0.013         | Baseline        |
| Minimal prompt        | 2,400  | $0.007         | **46% cheaper** |
| Mid-season optimized  | 3,400  | $0.010         | **19% cheaper** |

_With 16 teams × 17 weeks = 272 recaps/season, savings add up!_

---

## 🚀 Migration Path

### Option 1: Keep Current System (Simple)

No changes needed. `COLUMNIST_PROMPT.md` works great as-is.

**Pro:** Zero work  
**Con:** Can't optimize per scenario

### Option 2: Hybrid Approach (Recommended)

Keep monolithic file as backup, add modular system as optional.

```python
# In recap_generator.py
try:
    from prompt_builder import get_columnist_prompt
    prompt = get_columnist_prompt(use_modular=True)  # Try modular
except:
    with open('COLUMNIST_PROMPT.md', 'r') as f:  # Fallback to monolithic
        prompt = f.read()
```

**Pro:** Best of both worlds  
**Con:** Maintain two systems

### Option 3: Full Migration (Advanced)

Split prompt into modules, remove monolithic file.

```bash
python3 split_prompt.py  # Creates prompts/ directory
# Update recap_generator.py to use PromptBuilder
# Remove COLUMNIST_PROMPT.md (or keep as archive)
```

**Pro:** Maximum flexibility and savings  
**Con:** More complex

---

## 🛠️ Quick Start

### Step 1: Create Modular Structure

```bash
python3 split_prompt.py
```

### Step 2: Test It

```bash
python3 prompt_builder.py
```

### Step 3: Integrate (Optional)

```python
# In recap_generator.py, replace:
with open('COLUMNIST_PROMPT.md', 'r') as f:
    prompt = f.read()

# With:
from prompt_builder import get_columnist_prompt
prompt = get_columnist_prompt(
    include_examples=(week <= 3),  # Only first few weeks
    include_trends=(week > 1)       # Skip week 1
)
```

---

## 📊 When to Use What

| Week     | Examples | Advanced Stats | Trends | Memory | Tokens | Why                                  |
| -------- | -------- | -------------- | ------ | ------ | ------ | ------------------------------------ |
| 1        | ✅       | ✅             | ❌     | ❌     | ~3,500 | Establish voice, no history          |
| 2-3      | ✅       | ✅             | ✅     | ✅     | ~4,200 | Build memory, show full capabilities |
| 4+       | ❌       | ✅             | ✅     | ✅     | ~3,400 | Voice established, skip examples     |
| Playoffs | ✅       | ✅             | ✅     | ✅     | ~4,200 | Go all out for finals                |

---

## 🎓 Best Practices

1. **Start simple:** Use monolithic until you need optimization
2. **A/B test:** Compare modular vs monolithic quality
3. **Monitor costs:** Track token usage per recap
4. **Version control:** Each section gets its own commit history
5. **Document changes:** Update this guide when adding sections

---

## 🤔 FAQ

**Q: Will modular prompts reduce quality?**  
A: No! Claude gets the same instructions, just organized differently. Can actually improve quality by reducing noise.

**Q: Is this premature optimization?**  
A: If you're generating 16+ recaps per week, probably not. If you're doing 1-2, monolithic is fine.

**Q: Can I still edit the monolithic file?**  
A: Yes! Use `get_columnist_prompt(use_modular=False)` to use the original file.

**Q: What if I add new data sources?**  
A: Create a new section (e.g., `10_injuries.md`) and add to PromptBuilder.

---

## 📈 Future Enhancements

Possible additions to the modular system:

- **Conditional sections:** Only include CRM jargon for certain weeks
- **Dynamic examples:** Load example roasts from previous recaps
- **League-specific modules:** Different leagues get different prompts
- **Quality scoring:** A/B test sections to optimize for laughs
- **Token budget:** Auto-exclude sections to hit target token count

---

**Bottom line:** Modular prompts are worth it if you're running this regularly. For one-offs, stick with the monolithic file. Your current setup is already excellent! 🎯
