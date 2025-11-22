# Story 3.3: Gemini End-to-End Extraction Strategy

**Status**: Draft
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

### 3.2 New Abstraction: `PageExtractionStrategy`
Refactor `PipelineRunner` to delegate the "Page Image -> Tables" logic to a strategy pattern.

*   **`HeuristicStrategy`**: The current implementation (Detect -> Grid -> OCR).
*   **`LLMEndToEndStrategy`**: The new implementation.

### 3.3 `LLMEndToEndService`
A new service class responsible for:
1.  Constructing the prompt (e.g., "Extract all tables from this image as a JSON list of objects with keys 'table_id', 'rows', 'columns'...").
2.  Handling the API call (Gemini/OpenAI).
3.  Parsing the raw string response (handling potential JSON formatting errors).
4.  Mapping the JSON to `TableDataFrameSpec`.

**Note**: In this mode, `TableMetadata` will likely have `grid_shape=(0,0)` or estimated values, and `structure_confidence` will be derived from the LLM's self-reported confidence or set to a placeholder. We lose pixel-perfect bounding boxes for individual cells unless we explicitly (and expensively) ask for them.

## 4. Tasks

### Phase 1: Strategy Refactoring
- [ ] **T3.3.1**: Define `PageExtractionStrategy` interface.
- [ ] **T3.3.2**: Move existing heuristic logic in `PipelineRunner._process_page` into `HeuristicExtractionStrategy`.
- [ ] **T3.3.3**: Update `PipelineConfig` to include `extraction_strategy`.

### Phase 2: Gemini Implementation
- [ ] **T3.3.4**: Implement `GeminiEndToEndStrategy` using Google GenAI SDK (or via existing `LLMExtractionService` infrastructure if adaptable).
- [ ] **T3.3.5**: Design the "System Prompt" to strictly enforce the JSON output schema required for `TableDataFrameSpec`.
- [ ] **T3.3.6**: Implement response parsing and error handling (JSON repair).

### Phase 3: Integration & Testing
- [ ] **T3.3.7**: Wire up the new strategy in `PipelineRunner`.
- [ ] **T3.3.8**: Add unit tests for the new strategy (using Mock LLM responses).
- [ ] **T3.3.9**: Create a demo/example script `examples/gemini_extraction.py`.

## 5. Acceptance Criteria
- [ ] `PipelineRunner` can be configured to use `llm_end_to_end` strategy.
- [ ] When using Gemini strategy, the system produces valid `TableDataFrameSpec` objects.
- [ ] The system gracefully handles LLM refusals or malformed JSON (retries or error reporting).
- [ ] Existing heuristic tests still pass (regression testing).


