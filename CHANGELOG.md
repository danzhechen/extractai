# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### 🚀 BREAKING CHANGES: FREE-First LLM Architecture (Nov 2025)

**Migration from Heuristic-First to LLM-First extraction strategy**

#### What Changed

The default extraction strategy has been changed from `heuristic` (CV-based) to `llm_end_to_end` (using FREE Gemini 2.5 Pro) via the new "smart" preset system. This represents a fundamental architectural shift prioritizing accuracy and ease-of-use over zero-cost extraction.

#### Breaking Changes

1. **Default Strategy Changed**
   - **Before**: `extraction_strategy="heuristic"` (OpenCV-based, no API required)
   - **After**: `extraction_strategy="llm_end_to_end"` via `extraction_preset="smart"` (FREE Gemini 2.5 Pro)
   - **Impact**: Existing code without explicit strategy will now default to LLM extraction

2. **API Key Now Required by Default**
   - **Before**: Could run without any API keys using heuristic extraction
   - **After**: Requires `PDF_READER_LLM_API_KEY` environment variable or `llm_api_key` config
   - **Migration**: Set environment variable or use `--preset offline` flag for API-free operation

3. **New Preset System Introduced**
   - `extraction_preset` field added to `PipelineConfig` with default value `"smart"`
   - Presets automatically configure multiple settings for common use cases
   - **Available presets**:
     - `smart` (default): FREE Gemini 2.5 Pro, no auto-escalation
     - `premium`: PAID Gemini 3.0 Pro always, best quality
     - `offline`: Heuristic-only, no API calls

4. **Configuration Defaults Changed**
   - `enable_auto_escalation`: Changed from `bool = False` to `Optional[bool] = None`
   - Preset system now controls default values for several config fields
   - User-provided values override preset defaults

#### Migration Guide

##### For CLI Users

**Before (Heuristic):**
```bash
pdf-reader extract --input document.pdf
```

**After (FREE LLM - RECOMMENDED):**
```bash
# Set API key once
export PDF_READER_LLM_API_KEY="your-gemini-api-key"

# Use default smart preset (FREE)
pdf-reader extract --input document.pdf
```

**To Keep Old Behavior (Offline Heuristics):**
```bash
pdf-reader extract --input document.pdf --preset offline
```

##### For Python API Users

**Before (Heuristic):**
```python
from pdf_reader import PipelineRunner, PipelineConfig

config = PipelineConfig(input_path="document.pdf")
runner = PipelineRunner()
result = runner.extract_tables("document.pdf", config=config)
```

**After (FREE LLM - RECOMMENDED):**
```python
from pdf_reader import PipelineRunner, PipelineConfig
import os

# Set API key
os.environ["PDF_READER_LLM_API_KEY"] = "your-gemini-api-key"

# Use default smart preset (FREE)
config = PipelineConfig(input_path="document.pdf")
runner = PipelineRunner()
result = runner.extract_tables("document.pdf", config=config)
```

**To Keep Old Behavior (Offline Heuristics):**
```python
from pdf_reader import PipelineRunner, PipelineConfig

config = PipelineConfig(
    input_path="document.pdf",
    extraction_preset="offline"  # Force heuristic strategy
)
runner = PipelineRunner()
result = runner.extract_tables("document.pdf", config=config)
```

##### For Test Code

**Add to ALL test fixtures:**
```python
config = PipelineConfig(
    # ... your other config ...
    extraction_preset="offline"  # Avoid requiring API keys in tests
)
```

#### New Features

1. **Preset System**
   - Quick configuration via `--preset` CLI flag or `extraction_preset` config field
   - Three built-in presets: `smart`, `premium`, `offline`
   - Presets automatically configure extraction strategy, models, and behavior

2. **Tiered LLM Strategy**
   - **Primary Model**: Gemini 2.5 Pro (FREE, unlimited)
   - **Escalation Model**: Gemini 3.0 Pro (PAID, premium quality)
   - Conservative escalation: Only with explicit user consent via `enable_auto_escalation=True`

3. **Cost Tracking**
   - New fields in `RunStats`: `llm_calls_primary`, `llm_calls_escalation`, `llm_tokens_input`, `llm_tokens_output`, `estimated_cost_usd`
   - Track token usage and estimate costs per run
   - Models used are recorded in `RunStats.models_used`

4. **Run ID Generation**
   - New field `run_id` in `RunStats` for unique run identification
   - Automatically generated UUID for each pipeline run
   - Supports run manifest generation and tracking

#### Technical Details

**New Configuration Fields:**
- `extraction_preset`: `Literal["smart", "premium", "offline"]` (default: `"smart"`)
- `llm_model_primary`: `str` (default: `"gemini-2.5-pro"`)
- `llm_model_escalation`: `Optional[str]` (default: `"gemini-3.0-pro"`)
- `enable_auto_escalation`: `Optional[bool]` (default: `None`, preset-controlled)

**New RunStats Fields:**
- `run_id`: `str` - Unique identifier for the run
- `llm_calls_primary`: `int` - Calls to primary model
- `llm_calls_escalation`: `int` - Calls to escalation model
- `llm_tokens_input`: `int` - Total input tokens consumed
- `llm_tokens_output`: `int` - Total output tokens consumed
- `estimated_cost_usd`: `float` - Estimated cost in USD
- `models_used`: `Set[str]` - Set of models used during run

#### Why This Change?

1. **FREE Tier Availability**: Gemini 2.5 Pro is now completely FREE with unlimited usage
2. **Superior Accuracy**: LLM extraction significantly outperforms CV-based heuristics
3. **Simpler Setup**: No need to tune CV parameters, thresholds, or detection logic
4. **Better UX**: Most users want accurate results out-of-the-box, not zero-cost at the expense of quality

#### Cost Comparison

| Preset | Strategy | Cost per 1000 Pages | Quality | Use Case |
|--------|----------|---------------------|---------|----------|
| `smart` (default) | FREE Gemini 2.5 Pro | **$0.00** | High | General use, recommended |
| `premium` | PAID Gemini 3.0 Pro | ~$6.25 | Highest | Critical documents, max accuracy |
| `offline` | Heuristic (CV) | **$0.00** | Medium | No API access, simple tables |

#### Getting a FREE API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Set environment variable:
   ```bash
   export PDF_READER_LLM_API_KEY="your-api-key-here"
   ```

#### Backwards Compatibility Notes

- **No automatic migration**: Existing code will attempt LLM extraction and fail without API key
- **Easy opt-out**: Add `extraction_preset="offline"` to restore old behavior
- **Config file compatibility**: Old config files work but will use new defaults
- **Test suite**: Requires updates to specify `extraction_preset="offline"` where no API is available

---

## [0.1.0] - 2025-11-20

### Added
- Initial release with heuristic extraction strategy
- OpenCV-based table detection
- PyMuPDF-based text extraction
- Multi-page support
- Debug artifacts (overlays, HTML reports)
- Structured logging and metrics
- CLI interface
- Configuration system



