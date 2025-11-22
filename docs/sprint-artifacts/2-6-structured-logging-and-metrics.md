# Story 2.6: Structured logging and metrics

Status: review

## Story

As a **developer using or debugging the pdf-reading-project**,  
I want the **pipeline to emit structured logs and metrics for each run**,  
so that **I can understand pipeline performance, diagnose issues, and track extraction quality over time**.

## Acceptance Criteria

1. **Structured logging implementation**
   - The pipeline uses structured logging (e.g., JSON logs or structured log entries) instead of plain print statements.
   - Logs include key pipeline stages:
     - PDF loading and page rendering.
     - Table region detection.
     - Grid structure detection.
     - Cell text extraction (OCR and LLM fallback counts).
     - Table assembly.
   - Log entries include timestamps, log levels, and contextual information (page index, table ID, etc.).

2. **Per-run metrics in `RunStats`**
   - `RunStats` (or equivalent) includes comprehensive metrics:
     - `pages_processed: int` (number of pages successfully processed).
     - `tables_detected: int` (total number of tables found).
     - `tables_extracted: int` (number of tables successfully extracted).
     - `average_ocr_confidence: float` (average OCR confidence across all cells, if available).
     - `llm_fallback_count: int` (number of cells that used LLM fallback).
     - `total_cells_extracted: int` (total number of cells with text extracted).
     - Error counts (from Story 2.4): `pages_skipped`, `tables_failed`.
   - Metrics are computed and populated during pipeline execution.

3. **Per-table metrics in `TableMetadata`**
   - `TableMetadata` (or equivalent) includes table-level metrics:
     - `cell_count: int` (number of cells in the table).
     - `cells_with_text: int` (number of cells that have non-empty text).
     - `average_confidence: float` (average OCR/LLM confidence for cells in this table).
     - `extraction_duration_ms: float` (time taken to extract this table, if measurable).
   - These metrics are available in the `ExtractionResult` for downstream analysis.

4. **Logging configuration**
   - Logging can be configured via `PipelineConfig` or environment variables:
     - Log level (DEBUG, INFO, WARNING, ERROR).
     - Output destination (console, file, or both).
     - Structured format (JSON vs. human-readable).
   - Sensible defaults are provided (e.g., INFO level, console output, human-readable format).

5. **Tests for logging and metrics**
   - Tests verify:
     - That structured logs are emitted for key pipeline stages.
     - That `RunStats` contains expected metrics after a successful run.
     - That `TableMetadata` includes table-level metrics.
   - Tests can capture and assert on log output without requiring external log aggregation tools.

6. **Backward compatibility**
   - Existing code and tests continue to work; logging is additive and does not break existing functionality.
   - Logging can be disabled or set to minimal output if needed.

## Tasks / Subtasks

- [x] T2.6.1: Set up structured logging infrastructure
  - [x] Choose a logging library (e.g., Python's `logging` module with JSON formatter, or `structlog`).
  - [x] Create a logging configuration module or helper (e.g., `pdf_reader.logging_config`).
  - [x] Set up loggers for key components (`PipelineRunner`, `TableRegionDetector`, `CellTextExtractor`, etc.).
  - [x] Configure structured output format (JSON or key-value pairs).

- [x] T2.6.2: Add logging to key pipeline stages
  - [x] Add log entries at pipeline entry/exit points:
    - [x] Start of `PipelineRunner.extract_tables` (log input PDF path, config summary).
    - [x] After PDF loading (log page count).
    - [x] Per-page processing (log page index, rendering time).
    - [x] Per-table detection (log table ID, region coordinates).
    - [x] Per-table extraction (log cell count, extraction method counts).
    - [x] End of pipeline (log summary metrics).
  - [x] Include relevant context in log entries (page index, table ID, durations, etc.).

- [x] T2.6.3: Extend `RunStats` with comprehensive metrics
  - [x] Review current `RunStats` from Story 2.4 (error handling).
  - [x] Add new metrics fields:
    - [x] `pages_processed: int`.
    - [x] `tables_detected: int`.
    - [x] `tables_extracted: int`.
    - [x] `average_ocr_confidence: float` (computed from all cells).
    - [x] `llm_fallback_count: int`.
    - [x] `total_cells_extracted: int`.
    - [x] `total_duration_ms: float` (optional, total pipeline execution time).
  - [x] Update `PipelineRunner` to compute and populate these metrics during execution.

- [x] T2.6.4: Add table-level metrics to `TableMetadata`
  - [x] Extend `TableMetadata` (or `TableGrid`) with:
    - [x] `cell_count: int`.
    - [x] `cells_with_text: int`.
    - [x] `average_confidence: float`.
    - [x] `extraction_duration_ms: float` (optional).
  - [x] Compute these metrics during table extraction and assembly.

- [x] T2.6.5: Add logging configuration to `PipelineConfig`
  - [x] Extend `PipelineConfig` with optional logging settings:
    - [x] `log_level: str` (default "INFO").
    - [x] `log_file: Optional[str]` (optional file path for log output).
    - [x] `log_format: Literal["json", "human"]` (default "human").
  - [x] Apply logging configuration at pipeline startup.

- [x] T2.6.6: Add tests for logging and metrics
  - [x] Add tests (e.g., `tests/test_logging_metrics.py`) that:
    - [x] Run the pipeline on a test PDF and capture log output.
    - [x] Assert that expected log entries are present (e.g., "Processing page 0", "Table detected").
    - [x] Verify that `RunStats` contains non-zero metrics after a successful run.
    - [x] Verify that `TableMetadata` includes table-level metrics.
    - [x] Test different log levels and formats.

- [x] T2.6.7: Update documentation
  - [x] Add a section in `README` or `docs/` describing:
    - [x] How to configure logging (log level, output destination, format).
    - [x] What metrics are available in `RunStats` and `TableMetadata`.
    - [x] How to access and use structured logs for debugging.
  - [x] Optionally add an example showing how to parse JSON logs or extract metrics programmatically.

## Dev Notes

- **Architectural alignment**
  - This story corresponds to Phase 4 task T4.1 in `docs/prd.md` Section 13.5 (structured logging).
  - Focus on making logs useful for debugging and performance analysis; avoid excessive verbosity.
- **Testing strategy**
  - Use log capture utilities (e.g., `pytest`'s `caplog` fixture) to test log output without writing to files.
  - Prefer testing log structure and presence over exact message text to avoid brittle tests.
- **Future considerations**
  - Later stories may add log aggregation, dashboards, or more sophisticated metrics collection, but this story provides the foundation.

### Project Structure Notes

- Keep logging configuration centralized (e.g., `pdf_reader/logging_config.py` or a `logging` submodule).
- Consider using a logging utility module to provide consistent log formatting and context injection across components.

### References

- [Source: `docs/prd.md` — Sections 12.2–12.3, 13.5 (T4.1 structured logging)]
- [Source: `docs/sprint-artifacts/sprint-plan-2025-11-16.md` — Phase 4 scope notes]
- [Related: Story 2.4 (error handling), Story 2.5 (LLM fallback)]

## Dev Agent Record

### Context Reference

- `docs/prd.md` Section 13.5 (T4.1 structured logging)
- `docs/sprint-artifacts/sprint-plan-2025-11-16.md`

### Agent Model Used

Auto (Cursor AI Agent)

### Debug Log References

- Created structured logging infrastructure using Python's `logging` module with custom formatters
- Added `log_with_context()` helper function to include contextual fields in log entries
- Integrated logging throughout `PipelineRunner.extract_tables()` at key stages
- Computed metrics during pipeline execution and populated `RunStats` and `TableMetadata`
- Used `time.time()` for duration tracking at pipeline and table levels

### Completion Notes List

✅ **Structured logging and metrics implementation complete**

**Key Changes:**
1. **Logging infrastructure**: Created `src/pdf_reader/logging_config.py` with:
   - `StructuredFormatter` for JSON log output
   - `HumanReadableFormatter` for human-readable log output with context
   - `setup_logging()` function to configure logging with level, file, and format
   - `get_logger()` function to get component-specific loggers
   - `log_with_context()` helper to add contextual fields to log entries

2. **Pipeline logging**: Added comprehensive logging to `PipelineRunner.extract_tables()`:
   - Pipeline start (input path, config summary)
   - PDF loading (page count)
   - Per-page processing (page index, rendering time)
   - Table region detection (region count)
   - Table extraction (cell count, confidence, LLM fallback count, duration)
   - Pipeline completion (summary metrics)

3. **RunStats enhancement**: Extended with:
   - `tables_extracted`: Number of successfully extracted tables
   - `total_cells_extracted`: Total cells with extracted text
   - `average_ocr_confidence`: Average confidence across all cells
   - `llm_fallback_count`: Number of cells using LLM fallback
   - `total_duration_ms`: Total pipeline execution time

4. **TableMetadata enhancement**: Extended with:
   - `cell_count`: Total number of cells in table
   - `cells_with_text`: Number of cells with non-empty text
   - `average_confidence`: Average confidence for cells in this table
   - `extraction_duration_ms`: Time taken to extract this table

5. **Logging configuration**: Added to `PipelineConfig`:
   - `log_level`: Logging level string (default: "INFO")
   - `log_file`: Optional file path for log output (default: None)
   - `log_format`: Format type, "json" or "human" (default: "human")

6. **Comprehensive tests**: Added `tests/test_logging_metrics.py` with:
   - Tests for log message presence at key stages
   - Tests for RunStats metrics computation
   - Tests for TableMetadata metrics
   - Tests for logging configuration (JSON format, file output, log levels)
   - Tests for metrics computation accuracy

7. **Documentation**: Added "Structured Logging and Metrics" section to README.md with:
   - Code examples for configuring logging
   - Documentation of all RunStats and TableMetadata metrics
   - Explanation of logging features and configuration options

**Implementation Details:**
- Logging uses Python's standard `logging` module with custom formatters
- Structured logs include contextual information (page index, table ID, durations, metrics)
- Metrics are computed during pipeline execution and aggregated at run level
- Table-level metrics are computed per table during extraction
- Logging is configured at pipeline startup based on `PipelineConfig`
- All metrics have sensible defaults (0 for counts, 0.0 for averages/durations)

**Backward Compatibility:**
- Logging is additive and does not break existing functionality
- Default logging configuration (INFO level, human-readable, console) is non-intrusive
- Existing tests continue to work without modification
- Metrics fields have default values, so existing code doesn't break

### File List

- `src/pdf_reader/logging_config.py` - New structured logging infrastructure
- `src/pdf_reader/models.py` - Extended RunStats and TableMetadata with metrics fields
- `src/pdf_reader/pipeline.py` - Added logging throughout pipeline and metrics computation
- `tests/test_logging_metrics.py` - New comprehensive test suite for logging and metrics
- `README.md` - Added "Structured Logging and Metrics" section
- `docs/sprint-artifacts/2-6-structured-logging-and-metrics.md` - Updated with completion status

