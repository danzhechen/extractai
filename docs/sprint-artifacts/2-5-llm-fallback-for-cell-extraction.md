# Story 2.5: LLM fallback for low-confidence cell extraction

Status: review

## Story

As a **developer using the pdf-reading-project**,  
I want the **`CellTextExtractor` to fall back to LLM-based extraction when OCR confidence is low**,  
so that **the system can extract text from difficult cells (fuzzy scans, small fonts, complex layouts) that primary OCR struggles with**.

## Acceptance Criteria

1. **Confidence threshold configuration**
   - `PipelineConfig` (or `CellTextExtractor` config) includes:
     - A configurable `ocr_confidence_threshold` (e.g., 0.0 to 1.0) that determines when to trigger LLM fallback.
     - A boolean flag `llm_fallback_enabled` to enable/disable the fallback feature.
   - Default values are sensible (e.g., threshold 0.5, fallback disabled by default for cost/latency reasons).

2. **LLM fallback logic in `CellTextExtractor`**
   - When OCR returns text with confidence below the threshold (or fails entirely), `CellTextExtractor`:
     - Routes the cell image (or cropped table region) to an LLM-based extraction service.
     - Uses the LLM response as the cell text.
     - Sets `Cell.text_source = "llm_fallback"` (or equivalent) to track provenance.
   - When OCR confidence is above the threshold, normal OCR path is used and `Cell.text_source = "ocr"`.

3. **LLM extraction service interface**
   - A new module or class (e.g., `LLMExtractionService` or `pdf_reader.llm_extraction`) exists that:
     - Provides a simple interface like `extract_text_from_image(image, prompt_hint: Optional[str]) -> str`.
     - Isolates all LLM provider-specific details (API keys, model selection, request formatting) to this module.
     - Can be configured with provider choice (e.g., OpenAI, Anthropic) and model name via config.

4. **Provenance tracking**
   - `Cell.text_source` is consistently set to one of:
     - `"ocr"` for primary OCR extraction.
     - `"embedded"` for embedded text (if supported in earlier stories).
     - `"llm_fallback"` for LLM-based extraction.
   - This provenance is preserved through assembly and available in the final `ExtractionResult`.

5. **Tests for LLM fallback**
   - Tests cover:
     - A cell with low OCR confidence that triggers LLM fallback (using a mock LLM service).
     - A cell with high OCR confidence that uses normal OCR path.
     - Verifying that `text_source` is set correctly in both cases.
   - Tests use mocks for LLM calls to avoid external API dependencies and costs.

6. **Backward compatibility**
   - When `llm_fallback_enabled = False` (default), behavior matches Story 1.4 (OCR-only extraction).
   - Existing tests and workflows continue to work without changes.

## Tasks / Subtasks

- [x] T2.5.1: Design LLM extraction service interface
  - [x] Create a module (e.g., `src/pdf_reader/llm_extraction.py`) with an abstract base class or protocol for LLM extraction.
  - [x] Define a simple interface: `extract_text_from_image(image, context: Optional[str]) -> str`.
  - [x] Document the interface and expected behavior in module docstrings.

- [x] T2.5.2: Implement a concrete LLM extraction service
  - [x] Choose an initial LLM provider (e.g., OpenAI, Anthropic) based on project dependencies or user preference.
  - [x] Implement a concrete class (e.g., `OpenAIExtractionService`) that:
    - [x] Takes API key and model name via constructor or config.
    - [x] Converts cell/table images to a format the LLM can process (e.g., base64-encoded PNG).
    - [x] Constructs a prompt asking the LLM to extract text from the image.
    - [x] Calls the LLM API and returns the extracted text.
  - [x] Handle basic error cases (API failures, rate limits) with clear exceptions or fallback behavior.

- [x] T2.5.3: Add confidence threshold and fallback config
  - [x] Extend `PipelineConfig` (or create `ExtractionConfig`) with:
    - [x] `ocr_confidence_threshold: float` (default 0.5).
    - [x] `llm_fallback_enabled: bool` (default False).
    - [x] `llm_provider: Optional[str]` and `llm_model: Optional[str]` (for provider selection).
  - [x] Add validation to ensure threshold is in valid range [0.0, 1.0].

- [x] T2.5.4: Extend `CellTextExtractor` with fallback logic
  - [x] Review current `CellTextExtractor` implementation from Story 1.4.
  - [x] Add logic to:
    - [x] Check OCR confidence after primary OCR extraction.
    - [x] If confidence < threshold and `llm_fallback_enabled = True`, call `LLMExtractionService.extract_text_from_image`.
    - [x] Set `Cell.text_source` appropriately (`"ocr"` or `"llm_fallback"`).
  - [x] Ensure that when fallback is disabled, behavior is unchanged from Story 1.4.

- [x] T2.5.5: Add provenance tracking
  - [x] Verify that `Cell.text_source` field (from `pdf_reader.models`) is set consistently:
    - [x] `"ocr"` for primary OCR path.
    - [x] `"llm_fallback"` for LLM fallback path.
    - [x] `"embedded"` if embedded text extraction was implemented earlier (optional).
  - [x] Ensure provenance flows through `TableAssembler` and is available in `ExtractionResult` metadata.

- [x] T2.5.6: Add tests for LLM fallback
  - [x] Add tests (e.g., `tests/test_llm_fallback.py`) that:
    - [x] Mock the LLM extraction service to avoid real API calls.
    - [x] Test a cell with low OCR confidence that triggers fallback and verify `text_source = "llm_fallback"`.
    - [x] Test a cell with high OCR confidence that uses OCR and verify `text_source = "ocr"`.
    - [x] Test with `llm_fallback_enabled = False` to verify backward compatibility.
  - [x] Ensure tests run without requiring LLM API keys or external services.

- [x] T2.5.7: Update documentation
  - [x] Add notes in `README` or `docs/` describing:
    - [x] How to enable LLM fallback and configure the confidence threshold.
    - [x] Which LLM providers are supported and how to configure API keys.
    - [x] Cost and latency considerations of using LLM fallback.
  - [x] Document the `text_source` provenance field and what values it can have.

## Dev Notes

- **Architectural alignment**
  - This story corresponds to Phase 3 tasks T3.1, T3.2, and T3.3 in `docs/prd.md` Section 13.4 (LLM fallback & advanced extraction).
  - Focus on a clean interface for LLM extraction; keep provider-specific details isolated.
- **Testing strategy**
  - Use mocks for LLM services to avoid API costs and external dependencies in tests.
  - Consider adding integration tests (marked as such) that can be run optionally with real API keys.
- **Cost and latency considerations**
  - LLM calls are slower and more expensive than OCR; the fallback should be opt-in and well-documented.
  - Consider batching or rate limiting in future stories if needed (T3.4), but keep this story focused on the core fallback mechanism.

### Project Structure Notes

- Keep LLM provider code isolated in `pdf_reader/llm_extraction.py` (or a small `llm_extraction/` package if multiple providers are added).
- Consider using environment variables or a config file for API keys rather than hardcoding them.

### References

- [Source: `docs/prd.md` — Sections 12.2–12.3, 13.4 (T3.1–T3.3 LLM fallback tasks)]
- [Source: `docs/sprint-artifacts/sprint-plan-2025-11-16.md` — Phase 3 scope notes]
- [Related: Story 1.4 (cell text extraction), Story 2.4 (error handling)]

## Dev Agent Record

### Context Reference

- `docs/prd.md` Section 13.4 (T3.1-T3.3 LLM fallback tasks)
- `docs/sprint-artifacts/sprint-plan-2025-11-16.md`

### Agent Model Used

Auto (Cursor AI Agent)

### Debug Log References

- Created LLM extraction service interface with abstract base class `LLMExtractionService`
- Implemented `OpenAIExtractionService` using OpenAI's vision API (GPT-4o)
- Added `MockLLMExtractionService` for testing without API calls
- Extended `CellTextExtractor` to check OCR confidence and trigger LLM fallback when below threshold
- Updated `PipelineRunner` to configure extractor with LLM settings from config
- Added validation for `ocr_confidence_threshold` in `PipelineConfig.__post_init__`

### Completion Notes List

✅ **LLM fallback for low-confidence cell extraction implementation complete**

**Key Changes:**
1. **LLM extraction service**: Created `src/pdf_reader/llm_extraction.py` with:
   - Abstract base class `LLMExtractionService` defining the interface
   - `OpenAIExtractionService` implementation using OpenAI's vision API
   - `MockLLMExtractionService` for testing without real API calls
   - Error handling with `LLMExtractionError` exception

2. **Configuration**: Extended `PipelineConfig` with:
   - `ocr_confidence_threshold: float` (default 0.5, validated to [0.0, 1.0])
   - `llm_fallback_enabled: bool` (default False)
   - `llm_provider: Optional[str]` (e.g., "openai")
   - `llm_model: Optional[str]` (e.g., "gpt-4o")
   - `llm_api_key: Optional[str]` (required when fallback enabled)

3. **CellTextExtractor enhancement**: Extended with:
   - `_extract_with_ocr()` method returning (text, confidence) tuple
   - `_extract_with_llm()` method using LLM service for low-confidence cells
   - `fill_cell_text()` now accepts optional `page_image` for LLM context
   - Automatic fallback: uses LLM when confidence < threshold, falls back to OCR if LLM fails
   - Provenance tracking: sets `Cell.text_source` to `"ocr"` or `"llm_fallback"`

4. **Pipeline integration**: Updated `PipelineRunner` to:
   - Create LLM service from config when `llm_fallback_enabled=True`
   - Configure extractor with LLM settings per table
   - Pass `page_image` to `fill_cell_text()` for LLM context

5. **Comprehensive tests**: Added `tests/test_llm_fallback.py` with:
   - Test for OCR path when confidence is high
   - Test for LLM fallback when confidence is low
   - Test for graceful degradation when LLM fails
   - Test for backward compatibility when LLM disabled
   - Test for config validation
   - All tests use mocks to avoid real API calls

6. **Documentation**: Added "LLM Fallback for Low-Confidence Cells" section to README.md with:
   - Code examples for enabling and configuring LLM fallback
   - Configuration options documentation
   - Cost and latency considerations
   - Provenance tracking explanation

**Implementation Details:**
- LLM service interface is provider-agnostic, allowing easy addition of other providers
- OpenAI implementation uses base64-encoded PNG images sent to GPT-4 Vision API
- Confidence threshold is configurable per pipeline run
- LLM fallback is opt-in (disabled by default) to avoid unexpected costs
- Provenance (`text_source`) flows through the entire pipeline and is available in results
- Graceful degradation: if LLM fails, OCR result is used

**Backward Compatibility:**
- When `llm_fallback_enabled=False` (default), behavior matches Story 1.4
- Existing tests and workflows continue to work without changes
- No breaking changes to existing APIs

### File List

- `src/pdf_reader/llm_extraction.py` - New LLM extraction service interface and implementations
- `src/pdf_reader/extraction.py` - Extended CellTextExtractor with LLM fallback logic
- `src/pdf_reader/pipeline.py` - Added LLM config to PipelineConfig and integration in PipelineRunner
- `tests/test_llm_fallback.py` - New comprehensive test suite for LLM fallback
- `README.md` - Added "LLM Fallback for Low-Confidence Cells" section
- `docs/sprint-artifacts/2-5-llm-fallback-for-cell-extraction.md` - Updated with completion status

