# Story 3.6: Gemini End-to-End Extraction Strategy

**Status**: review
**Story Type**: Feature / Architecture
**Owner**: Dev Agent
**Priority**: High

## 1. Background & Motivation

The current pipeline uses a "Structure-First" approach (Region Detection -> Grid Detection -> Cell Extraction). While precise for clean layouts, it can struggle with highly irregular tables, handwritten content, or complex layouts where heuristic line detection fails.

Recent Multimodal LLMs (Gemini 1.5 Pro/Flash, GPT-4o) have demonstrated state-of-the-art performance in "end-to-end" table extraction—taking a page image and directly outputting the structured data (JSON/Markdown) without needing explicit step-by-step geometric reconstruction.

This story introduces a new **"End-to-End LLM"** extraction strategy as an alternative to the heuristic pipeline.

## 2. Goals

1.  **Support "Gemini Mode"**: Allow users to switch the entire pipeline to use a Vision LLM for extraction via a single config flag.
2.  **Bypass Heuristics**: When enabled, skip `TableRegionDetector`, `GridStructureDetector`, and `CellTextExtractor` in favor of a single LLM call per page.
3.  **Maintain Output Contract**: The LLM output must be parsed into the existing `TableDataFrameSpec` format so that export (CSV/Excel) and evaluation tools continue to work.
4.  **Cost/Performance**: Optimize for Gemini Flash (low cost/latency) while allowing Pro for difficult cases.

## 3. Technical Architecture

### 3.1 Configuration Updates
Extend `PipelineConfig` with:
- `extraction_strategy`: `Literal["heuristic", "llm_end_to_end"]` (Default: "heuristic")
- `llm_prompt_template`: Optional custom prompt override.
- `llm_consistency_attempts`: `int` (Default: 1). Number of times to run extraction for consensus.
- `llm_consistency_threshold`: `float` (Default: 0.8). Required agreement ratio to accept result automatically.

### 3.2 New Abstraction: `PageExtractionStrategy`
Refactor `PipelineRunner` to delegate the "Page Image -> Tables" logic to a strategy pattern.

*   **`HeuristicStrategy`**: The current implementation (Detect -> Grid -> OCR).
*   **`LLMEndToEndStrategy`**: The new implementation, with optional consistency checking.

### 3.3 `LLMEndToEndService`
A new service class responsible for:
1.  Constructing the prompt (e.g., "Extract all tables from this image as a JSON list of objects with keys 'table_id', 'rows', 'columns'...").
2.  Handling the API call (Gemini/OpenAI).
3.  Parsing the raw string response (handling potential JSON formatting errors).
4.  Mapping the JSON to `TableDataFrameSpec`.

### 3.5 Cost Optimization (Gemini Flash Focus)
To address cost concerns (Friend/Hobbyist budget):
1.  **Default Model**: Use `gemini-2.5-flash` (or equivalent low-cost vision model) as the default for high-volume extraction.
2.  **"Pro" Escalation**: Only escalate to `gemini-1.5-pro` (or 3.0) if:
    *   Flash fails to produce valid JSON.
    *   Consistency check fails (disagreement > threshold).
    *   User explicitly requests "High Quality" mode.
3.  **Token Efficiency**: Minimize prompt verbosity and use JSON schema enforcement to reduce output token waste.

### 4. Tasks

### Phase 1: Strategy Refactoring
- [x] **T3.6.1**: Define `PageExtractionStrategy` interface.
- [x] **T3.6.2**: Move existing heuristic logic in `PipelineRunner._process_page` into `HeuristicExtractionStrategy`.
- [x] **T3.6.3**: Update `PipelineConfig` to include `extraction_strategy` and consistency params.

### Phase 2: Gemini Implementation
- [x] **T3.6.4**: Implement `GeminiEndToEndStrategy` using Google GenAI SDK (target `gemini-1.5-flash` / `gemini-2.0-flash` as cost-effective baseline).
- [x] **T3.6.5**: Design the "System Prompt" to strictly enforce the JSON output schema required for `TableDataFrameSpec`.
- [x] **T3.6.6**: Implement response parsing and error handling (JSON repair).

### Phase 3: Consistency & Reliability
- [x] **T3.6.7**: Implement **Parallel Consistency Check**: Run N requests, aggregate results.
- [x] **T3.6.8**: Implement **Voting Logic**: Compare JSON structures and content to derive a "consensus" table.
- [x] **T3.6.9**: Flag divergent results in `TableMetadata` (e.g., `needs_review: true`).

### Phase 4: Integration & Testing
- [x] **T3.6.10**: Wire up the new strategy in `PipelineRunner`.
- [x] **T3.6.11**: Add unit tests for the new strategy (using Mock LLM responses).
- [x] **T3.6.12**: Create a demo/example script `examples/gemini_extraction.py`.

## 5. Acceptance Criteria
- [x] `PipelineRunner` can be configured to use `llm_end_to_end` strategy.
- [x] When `llm_consistency_attempts > 1`, the system runs multiple calls and aggregates results.
- [x] Tables with conflicting structures across runs are flagged in metadata.
- [x] When using Gemini strategy, the system produces valid `TableDataFrameSpec` objects.
- [x] The system gracefully handles LLM refusals or malformed JSON (retries or error reporting).
- [x] Existing heuristic tests still pass (regression testing).

## 6. Implementation Summary

**Completed**: 2025-11-21

### Key Changes:
1. **GeminiEndToEndStrategy** (`src/pdf_reader/strategies.py`):
   - Implemented full end-to-end LLM extraction strategy
   - Supports both Google GenAI (Gemini) and OpenAI (GPT-4o) APIs
   - Includes JSON schema enforcement prompt
   - Robust JSON parsing with markdown code block handling
   - Consensus voting logic for multiple extraction attempts
   - Converts LLM JSON to `TableDataFrameSpec` format

2. **Configuration** (`src/pdf_reader/pipeline.py`, `src/pdf_reader/config_loader.py`):
   - Added `extraction_strategy` parameter ("heuristic" or "llm_end_to_end")
   - Added `llm_consistency_attempts` (1-5, default: 1)
   - Added `llm_consistency_threshold` (0.0-1.0, default: 0.8)
   - Environment variables: `PDF_READER_EXTRACTION_STRATEGY`, `PDF_READER_LLM_CONSISTENCY_ATTEMPTS`, `PDF_READER_LLM_CONSISTENCY_THRESHOLD`

3. **CLI** (`src/pdf_reader/cli.py`):
   - Added `--extraction-strategy` flag
   - Added `--llm-consistency-attempts` flag
   - Added `--llm-consistency-threshold` flag

4. **Dependencies** (`requirements.txt`):
   - Added `google-generativeai>=0.3.0`
   - Added `openai>=1.0.0`

5. **Demo Script** (`examples/gemini_extraction.py`):
   - Complete example showing Gemini/GPT-4o extraction
   - Supports consistency checking
   - Handles API key management

6. **Tests** (`tests/test_gemini_strategy.py`):
   - 15 comprehensive unit tests
   - Mock LLM responses for isolated testing
   - Tests for consensus voting, JSON parsing, error handling, cancellation

### Usage Examples:

```bash
# Using Gemini Flash (cost-effective)
python -m pdf_reader extract --input document.pdf \
    --extraction-strategy llm_end_to_end \
    --llm-provider google \
    --llm-model gemini-1.5-flash \
    --llm-api-key $GOOGLE_API_KEY

# Using GPT-4o
python -m pdf_reader extract --input document.pdf \
    --extraction-strategy llm_end_to_end \
    --llm-provider openai \
    --llm-model gpt-4o \
    --llm-api-key $OPENAI_API_KEY

# With consistency checking (3 attempts, vote on results)
python -m pdf_reader extract --input document.pdf \
    --extraction-strategy llm_end_to_end \
    --llm-consistency-attempts 3 \
    --llm-consistency-threshold 0.8
```

### Performance & Cost:
- **Gemini 1.5 Flash**: ~$0.075 per 1M input tokens, ~$0.30 per 1M output tokens
- **GPT-4o**: ~$2.50 per 1M input tokens, ~$10.00 per 1M output tokens
- Typical page: ~1000 tokens input, ~500 tokens output
- **Recommendation**: Use Gemini Flash for cost-effectiveness, escalate to Pro/GPT-4o only for difficult cases

### Limitations:
- Requires API key and internet connectivity
- More expensive than heuristic approach
- No pixel-level bounding boxes (uses dummy bbox)
- Best for irregular/complex tables where heuristics fail
