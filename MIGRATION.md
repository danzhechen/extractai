# Migration Guide: Heuristic-First → FREE-First LLM Architecture

This guide helps you migrate from the old heuristic-based extraction (pre-Nov 2025) to the new FREE-first LLM architecture.

## TL;DR

**Quick Fix for Existing Code:**
```python
# Add this to your PipelineConfig to keep old behavior
config = PipelineConfig(
    extraction_preset="offline"  # Use old heuristic strategy
)
```

**Or embrace the new FREE approach:**
```bash
# Set API key once
export PDF_READER_LLM_API_KEY="your-gemini-api-key"
# Then use your existing code - it just works better now!
```

---

## What Changed?

### The Big Picture

We shifted from a **heuristic-first** (OpenCV-based, free but less accurate) to a **LLM-first** (Gemini-based, FREE and highly accurate) architecture. This means:

- **Better accuracy** by default
- **Still FREE** (Gemini 2.5 Pro has unlimited free tier)
- **Requires API key** (but it's free to get)
- **Easier to use** (no tuning CV parameters)

### Breaking Changes Summary

| Aspect | Before | After |
|--------|--------|-------|
| Default strategy | `heuristic` (CV-based) | `llm_end_to_end` (Gemini) |
| API key required | No | Yes (but free tier) |
| Cost per 1000 pages | $0 | $0 (with Gemini 2.5 Pro) |
| Accuracy | Medium | High |
| Setup complexity | Low | Very Low |

---

## Migration Paths

### Path 1: Keep Using Heuristics (Offline Mode)

**When to choose**: No API access, air-gapped environments, or simple tables

**How to migrate:**

```python
# Add extraction_preset="offline" to all PipelineConfig instances
config = PipelineConfig(
    input_path="document.pdf",
    extraction_preset="offline",  # <-- Add this line
    # ... rest of your config
)
```

**CLI:**
```bash
pdf-reader extract --input document.pdf --preset offline
```

**Config file (`config.yaml`):**
```yaml
extraction_preset: offline
# ... rest of your config
```

### Path 2: Adopt FREE LLM Extraction (Recommended)

**When to choose**: Best accuracy, willing to get free API key

**Step 1: Get FREE API Key**
```bash
# Visit https://aistudio.google.com/app/apikey
# Create a new API key (takes 30 seconds)
```

**Step 2: Set Environment Variable**
```bash
# Add to ~/.bashrc or ~/.zshrc
export PDF_READER_LLM_API_KEY="your-api-key-here"
```

**Step 3: Use Your Existing Code**
```python
# No changes needed! Your existing code now uses FREE LLM extraction
config = PipelineConfig(input_path="document.pdf")
runner = PipelineRunner()
result = runner.extract_tables("document.pdf", config=config)
```

### Path 3: Premium Quality (Paid)

**When to choose**: Mission-critical documents, maximum accuracy

```python
config = PipelineConfig(
    input_path="document.pdf",
    extraction_preset="premium",  # Uses Gemini 3.0 Pro (paid)
    llm_api_key="your-api-key",
)
```

**Cost:** ~$6.25 per 1000 pages

---

## Common Migration Scenarios

### Scenario 1: Test Suite Failing

**Problem:** Tests fail with "LLM API key required"

**Solution:** Add `extraction_preset="offline"` to test fixtures:

```python
@pytest.fixture
def pipeline_config():
    return PipelineConfig(
        extraction_preset="offline",  # <-- Add this
        # ... rest of test config
    )
```

Or create a shared fixture in `conftest.py`:
```python
# tests/conftest.py
@pytest.fixture
def offline_config():
    """Default config for tests - uses offline mode."""
    return {"extraction_preset": "offline"}

# Then in tests:
def test_something(offline_config):
    config = PipelineConfig(**offline_config, input_path="test.pdf")
    # ...
```

### Scenario 2: CI/CD Pipeline Failing

**Problem:** GitHub Actions / Jenkins jobs fail without API key

**Option A: Use Offline Mode**
```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pytest tests/ --preset=offline
```

**Option B: Add API Key Secret**
```yaml
# .github/workflows/test.yml
- name: Run tests
  env:
    PDF_READER_LLM_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  run: |
    pytest tests/
```

### Scenario 3: Docker Container

**Problem:** Container needs API key at runtime

**Solution: Pass as environment variable**

```dockerfile
# Dockerfile
FROM python:3.11
COPY . /app
WORKDIR /app
RUN pip install -e .

# Accept API key as build arg (or pass at runtime)
ARG LLM_API_KEY
ENV PDF_READER_LLM_API_KEY=$LLM_API_KEY
```

```bash
# Build with API key
docker build --build-arg LLM_API_KEY="your-key" -t pdf-reader .

# Or pass at runtime
docker run -e PDF_READER_LLM_API_KEY="your-key" pdf-reader
```

### Scenario 4: Library Usage

**Problem:** Your library embeds pdf-reader and doesn't want to require API keys

**Solution: Default to offline in your wrapper**

```python
# your_library/pdf_wrapper.py
from pdf_reader import PipelineRunner, PipelineConfig

def extract_tables(pdf_path, use_llm=False, api_key=None):
    """Extract tables with sensible defaults for library users."""
    
    if use_llm and api_key:
        preset = "smart"
    else:
        preset = "offline"  # Default to offline for library users
    
    config = PipelineConfig(
        input_path=pdf_path,
        extraction_preset=preset,
        llm_api_key=api_key,
    )
    
    runner = PipelineRunner()
    return runner.extract_tables(pdf_path, config=config)
```

---

## Configuration Changes

### Old Config (Heuristic)

```python
config = PipelineConfig(
    input_path="document.pdf",
    extraction_strategy="heuristic",  # Explicit
    dpi=200,
    default_rows=10,
    default_cols=5,
)
```

### New Config (Offline Equivalent)

```python
config = PipelineConfig(
    input_path="document.pdf",
    extraction_preset="offline",  # Simpler!
    dpi=200,
    default_rows=10,
    default_cols=5,
)
```

### New Config (FREE LLM)

```python
config = PipelineConfig(
    input_path="document.pdf",
    # extraction_preset="smart" is the default, no need to specify
    llm_api_key="your-key",  # Or set via environment variable
)
```

---

## New Features You Can Use

### 1. Preset System

Quick configurations for common use cases:

```python
# Smart preset (default): FREE Gemini 2.5 Pro
config = PipelineConfig(extraction_preset="smart")

# Premium preset: PAID Gemini 3.0 Pro for max quality
config = PipelineConfig(extraction_preset="premium")

# Offline preset: Heuristic-only, no API
config = PipelineConfig(extraction_preset="offline")
```

### 2. Cost Tracking

Monitor your LLM usage:

```python
result = runner.extract_tables("document.pdf", config=config)

print(f"LLM calls: {result.run_stats.llm_calls_primary}")
print(f"Tokens used: {result.run_stats.llm_tokens_input}")
print(f"Estimated cost: ${result.run_stats.estimated_cost_usd:.4f}")
print(f"Models used: {result.run_stats.models_used}")
```

### 3. Smart Escalation (Optional)

Automatically escalate to premium model for difficult pages:

```python
config = PipelineConfig(
    extraction_preset="smart",
    enable_auto_escalation=True,  # Escalate to Gemini 3.0 Pro if needed
    llm_api_key="your-key",
)
```

**Note:** This can incur costs. Only enable if you want automatic premium quality.

---

## Troubleshooting

### Error: "LLM API key required for end-to-end extraction"

**Cause:** No API key provided and default preset is "smart" (LLM-based)

**Solutions:**
1. Set API key: `export PDF_READER_LLM_API_KEY="your-key"`
2. OR use offline: `extraction_preset="offline"`

### Error: "Invalid preset: ..."

**Cause:** Typo in preset name

**Solution:** Use one of: `"smart"`, `"premium"`, `"offline"`

### Tests Hanging or Crashing

**Cause:** Known threading bug in heuristic strategy with parallel processing

**Solution:** Use sequential processing in tests:
```python
config = PipelineConfig(
    extraction_preset="offline",
    worker_type="sequential",  # Avoid threading bug
)
```

### API Key Works in Terminal but Not in Code

**Cause:** Environment variable not loaded in Python process

**Solution:**
```python
import os
os.environ["PDF_READER_LLM_API_KEY"] = "your-key"
# Or pass directly to config
config = PipelineConfig(llm_api_key="your-key")
```

---

## Rollback Plan

If you need to temporarily revert to the old behavior project-wide:

**Option 1: Environment Variable**
```bash
# This doesn't exist yet, but you could add it
export PDF_READER_DEFAULT_PRESET="offline"
```

**Option 2: Monkey Patch (Temporary)**
```python
# At the top of your main script
import pdf_reader
pdf_reader.pipeline.PipelineConfig.__dataclass_fields__['extraction_preset'].default = "offline"
```

**Option 3: Wrapper Function**
```python
# your_code.py
from pdf_reader import PipelineConfig as _PipelineConfig

class PipelineConfig(_PipelineConfig):
    """Wrapper that defaults to offline."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('extraction_preset', 'offline')
        super().__init__(*args, **kwargs)
```

---

## Need Help?

- **Documentation:** See `docs/architecture.md` for technical details
- **Examples:** Check `docs/guides/` for usage examples
- **Issues:** File a GitHub issue with the `migration` label
- **Breaking Changes:** See `CHANGELOG.md` for full details

---

## Timeline

- **Before Nov 20, 2025:** Heuristic-first architecture
- **Nov 20, 2025:** FREE-first architecture introduced
- **Grace Period:** Both approaches supported indefinitely
- **Recommended:** Migrate to FREE LLM for best results



