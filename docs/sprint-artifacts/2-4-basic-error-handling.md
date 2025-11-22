# Story 2.4: Basic error handling strategy

Status: review

## Story

As a **developer using the pdf-reading-project**,  
I want the **pipeline to gracefully handle errors (invalid PDFs, missing tables, detection failures) and report them in a structured way**,  
so that **the system doesn't crash on edge cases and I can understand what went wrong during extraction**.

## Acceptance Criteria

1. **Graceful error handling for fatal page issues**
   - When a page cannot be rendered or processed (e.g., corrupted PDF page, unsupported format), the pipeline:
     - Skips that page and continues processing other pages.
     - Records the error in `RunStats` or `TableMetadata` with a clear error message.
     - Does not crash the entire pipeline run.

2. **Graceful handling of table detection failures**
   - When table detection fails for a specific page or region (e.g., no tables found, detection timeout), the pipeline:
     - Continues processing other pages/regions.
     - Logs the failure appropriately (e.g., in `RunStats.error_count` or per-page metadata).
     - Returns a partial `ExtractionResult` with successfully extracted tables rather than failing entirely.

3. **Error aggregation in `RunStats`**
   - `RunStats` (or equivalent) includes:
     - A count of pages skipped due to errors.
     - A count of tables that failed detection or extraction.
     - A list or summary of error messages (or at least error types) for debugging.
   - Error information is accessible programmatically and does not require parsing logs.

4. **Structured error reporting in `TableMetadata`**
   - When a table extraction fails, `TableMetadata` (or equivalent) can include:
     - An error flag or status field (e.g., `"success"`, `"detection_failed"`, `"extraction_failed"`).
     - An optional error message or exception details (for debugging).
   - Successful tables continue to have normal metadata without error fields.

5. **Tests for error handling**
   - Tests cover:
     - A PDF with a corrupted or unreadable page (or a mock that simulates a page rendering failure).
     - A PDF where some pages have no tables (detection returns empty).
     - Verifying that `ExtractionResult` includes error counts and that successfully extracted tables are still present.
   - Tests run successfully via `pytest`.

6. **Backward compatibility**
   - PDFs that process successfully without errors continue to work as before.
   - Error handling does not change the structure of `ExtractionResult` for successful runs (error fields are optional or default to zero/empty).

## Tasks / Subtasks

- [x] T2.4.1: Define error handling strategy and error types
  - [x] Document the types of errors to handle:
    - [x] Page rendering failures (corrupted page, unsupported format).
    - [x] Table detection failures (no tables found, detection timeout).
    - [x] Table extraction failures (OCR failure, assembly errors).
  - [x] Decide on error representation (e.g., exception types, error codes, or structured error objects).
  - [x] Document this strategy in Dev Notes.

- [x] T2.4.2: Extend `RunStats` to track errors
  - [x] Add fields to `RunStats` (or create a new error-tracking structure):
    - [x] `pages_skipped: int` (count of pages that failed to process).
    - [x] `tables_failed: int` (count of tables that failed detection or extraction).
    - [x] `errors: List[str]` or `error_summary: Dict[str, int]` (optional list of error messages or counts by error type).
  - [x] Ensure `RunStats` has sensible defaults (e.g., zero counts, empty lists).

- [x] T2.4.3: Add error handling to `PipelineRunner`
  - [x] Wrap page rendering in try/except blocks:
    - [x] Catch rendering failures and skip the page, incrementing `pages_skipped`.
    - [x] Log the error (or add to `RunStats.errors`) with page index and error message.
  - [x] Wrap table detection/extraction in try/except blocks:
    - [x] Catch detection/extraction failures and continue processing other tables.
    - [x] Increment `tables_failed` and optionally record error details.
  - [x] Ensure that partial successes (some tables extracted, some failed) are returned rather than raising exceptions.

- [x] T2.4.4: Add error metadata to `TableMetadata`
  - [x] Add optional error fields to `TableMetadata` (or `TableGrid`):
    - [x] `status: Literal["success", "detection_failed", "extraction_failed"]` (or equivalent).
    - [x] `error_message: Optional[str]` (optional detailed error message for debugging).
  - [x] Ensure successful tables have `status="success"` (or equivalent default).

- [x] T2.4.5: Add tests for error handling
  - [x] Add tests (e.g., `tests/test_error_handling.py`) that:
    - [x] Use a mock or fixture that simulates a page rendering failure and verify the pipeline skips that page and continues.
    - [x] Use a PDF where some pages have no tables and verify detection failures are handled gracefully.
    - [x] Verify that `RunStats` includes correct error counts and that successfully extracted tables are still present in `ExtractionResult`.
    - [x] Ensure backward compatibility: a fully successful run has zero error counts and no error messages.

- [x] T2.4.6: Update documentation
  - [x] Add a note in `README` or `docs/` describing:
    - [x] That the pipeline handles errors gracefully and continues processing.
    - [x] How to access error information from `RunStats` and `TableMetadata`.
  - [x] Optionally add an example showing how to check for errors in the extraction result.

## Dev Notes

- **Architectural alignment**
  - This story corresponds to Phase 2 task T2.4 in `docs/prd.md` Section 13.3 (introduce basic error handling strategy).
  - Focus on graceful degradation and structured error reporting; avoid complex retry logic or sophisticated error recovery in this story.
- **Testing strategy**
  - Use mocks or fixtures to simulate errors rather than requiring corrupted PDFs in the repo.
  - Prefer deterministic error scenarios (e.g., mock functions that raise exceptions) for easier test maintenance.
- **Future considerations**
  - Later stories may add more sophisticated error recovery (e.g., retries, fallback strategies) or user-configurable error handling policies.

### Project Structure Notes

- Keep error handling logic centralized in `PipelineRunner` where possible; avoid spreading try/except blocks into every component unless necessary for component-level resilience.
- Consider using a small error utility module (e.g., `pdf_reader.errors`) if error types or error formatting logic becomes complex.

### References

- [Source: `docs/prd.md` — Sections 12.2–12.3, 13.3 (T2.4 error handling strategy)]
- [Source: `docs/sprint-artifacts/sprint-plan-2025-11-16.md` — Phase 2 scope notes]
- [Related: Story 1.5 (pipeline runner), Story 2.3 (multi-page support)]

## Dev Agent Record

### Context Reference

- `docs/prd.md` Section 13.3 (T2.4 error handling strategy)
- `docs/sprint-artifacts/sprint-plan-2025-11-16.md`

### Agent Model Used

Auto (Cursor AI Agent)

### Debug Log References

- Enhanced existing error handling in `PipelineRunner.extract_tables` with comprehensive try/except blocks around page rendering, detection, and extraction.
- Added `pages_skipped` and `tables_failed` counters to `RunStats` for structured error tracking.
- Added optional `status` and `error_message` fields to `TableMetadata` for per-table error reporting.
- Failed tables are tracked in metadata but not added to `result.tables` to maintain clean separation.

### Completion Notes List

✅ **Basic error handling strategy implementation complete**

**Key Changes:**
1. **RunStats enhancement**: Added `pages_skipped` and `tables_failed` fields to track error counts alongside existing `errors` list.
2. **TableMetadata enhancement**: Added optional `status` field (Literal["success", "detection_failed", "extraction_failed"]) and `error_message` field for per-table error tracking.
3. **Pipeline error handling**: Enhanced `PipelineRunner.extract_tables` with comprehensive error handling:
   - Page rendering failures: Caught and logged, page skipped, `pages_skipped` incremented
   - Detection failures: Caught and logged, page skipped, `pages_skipped` incremented
   - Extraction failures: Caught and logged, table skipped, `tables_failed` incremented, failed metadata created
4. **Comprehensive tests**: Added `tests/test_error_handling.py` with 7 test cases covering:
   - Page rendering failures
   - Detection failures
   - Extraction failures
   - Pages with no tables (not an error)
   - Backward compatibility (all success)
   - Mixed success/failure scenarios
   - Error status in metadata
5. **Documentation**: Added "Error Handling" section to README.md with code examples showing how to access error information from `RunStats` and `TableMetadata`.

**Error Handling Strategy:**
- **Graceful degradation**: Pipeline continues processing even when individual pages or tables fail
- **Structured reporting**: Error counts and messages available programmatically in `RunStats`
- **Per-table tracking**: Failed tables have `status="extraction_failed"` and `error_message` in metadata
- **Partial results**: Successfully extracted tables are returned even if some fail
- **Backward compatible**: Successful runs have zero error counts and no error messages

**Implementation Details:**
- Page rendering errors: Caught at page level, page skipped, error logged
- Detection errors: Caught at page level, page skipped, error logged
- Extraction errors: Caught at table level, table skipped, failed metadata created for tracking
- Empty detection results: Not treated as errors, just continue to next page
- Failed tables: Metadata created with `status="extraction_failed"` but not added to `result.tables`

### File List

- `src/pdf_reader/models.py` - Added `pages_skipped` and `tables_failed` to `RunStats`, added `status` and `error_message` to `TableMetadata`
- `src/pdf_reader/pipeline.py` - Enhanced error handling with try/except blocks around rendering, detection, and extraction
- `tests/test_error_handling.py` - New comprehensive test suite for error handling scenarios
- `README.md` - Added "Error Handling" section with examples
- `docs/sprint-artifacts/2-4-basic-error-handling.md` - Updated with completion status

