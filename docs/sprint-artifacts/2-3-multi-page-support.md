# Story 2.3: Multi-page support in pipeline runner

Status: review

## Story

As a **developer using the pdf-reading-project**,  
I want the **`PipelineRunner` to process multiple pages from a PDF and track which page each table came from**,  
so that **I can extract tables from multi-page documents and maintain page-level context for each extracted table**.

## Acceptance Criteria

1. **Multi-page iteration in `PipelineRunner`**
   - `PipelineRunner.extract_tables` processes all pages in a PDF (or a configured page range) instead of only the first page.
   - Each detected table is associated with its source `page_index` in the `TableGrid` and `TableMetadata`.
   - The `ExtractionResult` aggregates tables from all processed pages into a single result.

2. **Page range configuration**
   - The `PipelineConfig` (or equivalent) supports specifying:
     - A list of page indices (e.g., `[0, 2, 4]`),
     - A page range (e.g., `range(0, 5)` or `"0-4"`),
     - Or `None`/default to process all pages.
   - The pipeline respects this configuration and only processes the specified pages.

3. **Table ID and page tracking**
   - Each `TableGrid` has a unique `table_id` (or equivalent identifier) that distinguishes it from other tables in the same run.
   - The `TableMetadata` (or `TableGrid` directly) includes `page_index` so downstream consumers know which page a table came from.
   - The `ExtractionResult` includes metadata that allows mapping tables back to their source pages.

4. **Tests for multi-page processing**
   - Tests cover:
     - A multi-page PDF where at least two pages contain tables.
     - Configuring a specific page range and verifying only those pages are processed.
     - Verifying that `page_index` is correctly set for each table in the result.
   - Tests run successfully via `pytest`.

5. **Backward compatibility**
   - Single-page PDFs continue to work as before.
   - The default behavior (when no page range is specified) processes all pages, which is compatible with existing single-page workflows.

## Tasks / Subtasks

- [x] T2.3.1: Extend `PipelineConfig` for page selection
  - [x] Add a `page_indices` or `page_range` field to `PipelineConfig` (or equivalent configuration type).
  - [x] Support multiple input formats:
    - [x] `None` or empty list to process all pages.
    - [x] A list of integers (e.g., `[0, 2, 4]`).
    - [x] A range-like specification (e.g., `(0, 5)` or string `"0-4"`).
  - [x] Provide sensible defaults and validation (e.g., reject out-of-range indices).

- [x] T2.3.2: Update `PipelineRunner.extract_tables` for multi-page iteration
  - [x] Modify the pipeline to iterate over all pages (or the configured subset) instead of only page 0.
  - [x] For each page:
    - [x] Render the page using `PdfIngestionService.render_page`.
    - [x] Run detection, extraction, and assembly as before.
    - [x] Associate each resulting `TableGrid` with the current `page_index`.
  - [x] Aggregate all tables from all pages into a single `ExtractionResult`.

- [x] T2.3.3: Implement table ID generation and page tracking
  - [x] Ensure each `TableGrid` has a unique `table_id` (e.g., `f"page_{page_index}_table_{table_index}"` or a UUID).
  - [x] Verify that `TableGrid.page_index` (or equivalent field) is populated correctly.
  - [x] Update `TableMetadata` or `ExtractionResult` to include page-level context if needed.

- [x] T2.3.4: Add tests for multi-page processing
  - [x] Add tests (e.g., `tests/test_multi_page_pipeline.py`) that:
    - [x] Use a multi-page test PDF (or generate one with `reportlab`) containing tables on multiple pages.
    - [x] Run `extract_tables` with default config (all pages) and assert tables from multiple pages are present.
    - [x] Run with a specific page range and verify only those pages are processed.
    - [x] Assert that `page_index` is correct for each table in the result.
  - [x] Ensure existing single-page tests still pass.

- [x] T2.3.5: Update documentation
  - [x] Update `README` or demo documentation to mention multi-page support.
  - [x] Add an example showing how to specify page ranges in the config.

## Dev Notes

- **Architectural alignment**
  - This story corresponds to Phase 2 task T2.3 in `docs/prd.md` Section 13.3 (multi-page support in `PipelineRunner`).
  - Focus on iteration and tracking; do not attempt to handle tables that span across pages in this story (that is a future enhancement).
- **Testing strategy**
  - Use `reportlab` or a small curated multi-page PDF to create test fixtures.
  - Prefer deterministic page indices and table counts for easier test assertions.
- **Future considerations**
  - Later stories may add logic to detect tables that span across page boundaries, but for now, each page is processed independently.

### Project Structure Notes

- Keep the page iteration logic in `PipelineRunner`; avoid spreading page-handling logic into individual detector/extractor components unless necessary.
- Consider adding a small helper function to normalize page range specifications (list vs. range vs. string) to keep the config parsing clean.

### References

- [Source: `docs/prd.md` — Sections 12.2–12.3, 13.3 (T2.3 multi-page support)]
- [Source: `docs/sprint-artifacts/sprint-plan-2025-11-16.md` — Phase 2 scope notes]
- [Related: Story 1.5 (pipeline runner), Story 2.1 (merged cells), Story 2.2 (span-aware assembly)]

## Dev Agent Record

### Context Reference

- `docs/prd.md` Section 13.3 (T2.3 multi-page support)
- `docs/sprint-artifacts/sprint-plan-2025-11-16.md`

### Agent Model Used

Auto (Cursor AI Agent)

### Debug Log References

- Multi-page iteration logic was already present in `PipelineRunner.extract_tables` (lines 59-63), but needed validation and comprehensive tests.
- Fixed `stats.pages_processed` to reflect actual pages processed (was previously set to `document.page_count`).
- Added validation for out-of-range page indices with error messages and automatic filtering.

### Completion Notes List

✅ **Multi-page support implementation complete**

**Key Changes:**
1. **Validation added**: `PipelineRunner.extract_tables` now validates `page_indices` against document bounds, logs errors for out-of-range indices, and filters them automatically.
2. **Stats tracking fixed**: `pages_processed` now correctly reflects the number of pages actually processed (not total document pages).
3. **Comprehensive tests**: Added `tests/test_multi_page_pipeline.py` with 6 test cases covering:
   - Processing all pages by default
   - Processing specific page ranges
   - Handling out-of-range indices gracefully
   - Verifying unique table IDs with page_index
   - Backward compatibility with single-page PDFs
   - Handling empty page ranges
4. **Documentation updated**: Added "Multi-page Support" section to README.md with code examples showing how to process all pages or specific page ranges.

**Implementation Details:**
- Multi-page iteration was already implemented; enhanced with validation and proper stats tracking.
- Table ID format: `p{page_index}_t{table_index}` (e.g., `p0_t0`, `p1_t0`) ensures uniqueness across pages.
- Each `TableMetadata` includes `page_index` for tracking table source pages.
- Out-of-range page indices are logged as errors but don't crash the pipeline; invalid indices are filtered out.

**Backward Compatibility:**
- Single-page processing continues to work as before.
- Default behavior (all pages) is compatible with existing workflows.
- All existing tests pass without modification.

### File List

- `src/pdf_reader/pipeline.py` - Added page_indices validation and fixed stats tracking
- `tests/test_multi_page_pipeline.py` - New comprehensive test suite for multi-page processing
- `README.md` - Added "Multi-page Support" section with examples
- `docs/sprint-artifacts/2-3-multi-page-support.md` - Updated with completion status

