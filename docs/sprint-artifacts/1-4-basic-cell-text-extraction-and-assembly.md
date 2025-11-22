# Story 1.4: Basic cell text extraction and assembly

Status: review

## Story

As a **developer using the pdf-reading-project**,  
I want a **basic `CellTextExtractor` and `TableAssembler` that can turn a `TableGrid` into a dataframe-ready representation**,  
so that **I can exercise an end-to-end path from structure detection through to tabular data without yet relying on full OCR quality**.

## Acceptance Criteria

1. **Cell text extraction API exists**
   - A `CellTextExtractor` (or equivalent) exists under the `pdf_reader` package.
   - It exposes a function or method that, given a `TableGrid`, populates `Cell.text` (and optionally `text_source`) for each cell.
   - For the minimal implementation, it is acceptable to use a deterministic placeholder strategy (e.g., based on row/column indices) for test grids; later stories can replace this with real OCR/embedded-text extraction.
2. **Table assembly API exists**
   - A `TableAssembler` (or equivalent) exists and exposes a method that converts a `TableGrid` (with `Cell.text` populated) into a `TableDataFrameSpec`.
   - The resulting `TableDataFrameSpec.rows` and `.columns` reflect the `n_rows`/`n_cols` of the grid and preserve row/column ordering.
3. **MVP behavior for a simple grid**
   - For a known `TableGrid` test case (e.g., 2x3 grid), `CellTextExtractor` produces non-empty text for each cell.
   - `TableAssembler` produces a `TableDataFrameSpec` where:
     - `rows` has `n_rows` elements, each of length `n_cols`.
     - Values correspond to the expected text for each cell (e.g., `r0c0`, `r0c1`, etc. in the placeholder scheme).
4. **Tests for extraction and assembly**
   - Tests verify:
     - All cells in a test `TableGrid` have text after running `CellTextExtractor`.
     - The assembled `TableDataFrameSpec` has the correct shape and contents.
   - Tests run successfully via `pytest`.
5. **Separation of concerns**
   - Implementation does not depend on `PdfIngestionService` directly; it operates on `TableGrid` and is easy to plug into future pipeline orchestration.

## Tasks / Subtasks

- [x] T1: Implement basic `CellTextExtractor`
  - [x] Create a module (e.g., `src/pdf_reader/extraction.py`) containing a `CellTextExtractor` class or functions.
  - [x] Implement a method that:
    - [x] Accepts a `TableGrid`.
    - [x] Populates `Cell.text` for each cell using a deterministic placeholder (e.g., `f"r{row_index}c{col_index}"`) if no text is already present.
    - [x] Sets `text_source` appropriately (e.g., `"embedded"` or `"ocr"` or `"mock"`).

- [x] T2: Implement basic `TableAssembler`
  - [x] In the same module, create a `TableAssembler` that:
    - [x] Accepts a `TableGrid` and produces a `TableDataFrameSpec`.
    - [x] Orders rows and columns according to `row_index` and `col_index`.
    - [x] Generates simple `ColumnSpec` entries with reasonable default names (e.g., `"col_0"`, `"col_1"`, ...).

- [x] T3: Add tests for extraction and assembly
  - [x] Add tests (e.g., `tests/test_extraction.py`) that:
    - [x] Construct a small `TableGrid` (e.g., 2x2) with empty `Cell.text`.
    - [x] Run `CellTextExtractor` and assert that all `Cell.text` values are non-empty and match the placeholder rule.
    - [x] Run `TableAssembler` and assert that:
      - [x] `rows` has the correct shape.
      - [x] Values in `rows` match the expected text pattern.
      - [x] Column specs have the expected count and names.

- [x] T4: Wire extraction and assembly into package namespace
  - [x] Export `CellTextExtractor` and `TableAssembler` from the top-level `pdf_reader` package for use in future stories.

## Dev Notes

- **Architectural alignment**
  - This story corresponds to Phase 1 task T1.4 in `docs/prd.md` Section 13.2 (TableAssembler and basic text extraction).
  - Real OCR/embedded-text integration can be layered on later; for this sprint we focus on the **structure and dataflow** from `TableGrid` to `TableDataFrameSpec`.
- **Testing strategy**
  - Use synthetic `TableGrid` instances built directly in tests to avoid relying on full PDF ingestion and detection.
  - Keep the placeholder strategy explicit in tests so future OCR-based implementations can extend/replace behavior without breaking expectations.

### Project Structure Notes

- Place extraction and assembly code under `src/pdf_reader/extraction.py` to parallel `ingestion.py` and `detection.py`.
- Later stories can extend this module with OCR/backends and LLM fallbacks while keeping the `TableAssembler` output stable.

### References

- [Source: `docs/prd.md` — Sections 12.2–12.3, 13.2 (CellTextExtractor and TableAssembler)]
- [Source: `docs/sprint-artifacts/sprint-plan-2025-11-16.md` — Story S4 description and acceptance criteria]

## Dev Agent Record

### Context Reference

<!-- Optional: add a story-context XML path here if story-context is run for this story -->

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

- Initial plan: Implement `CellTextExtractor` and `TableAssembler` in `pdf_reader.extraction` using deterministic placeholder text for a minimal 2xN grid, and add pytest tests to validate shape and content of `TableDataFrameSpec` without integrating real OCR yet.

### Completion Notes List
- Implemented `CellTextExtractor` and `TableAssembler` in `pdf_reader.extraction`, using deterministic placeholder text to populate cells and assembling `TableDataFrameSpec` with simple column specs.
- Added tests in `tests/test_extraction.py` that validate placeholder text assignment and the shape/content of the assembled dataframe specification using synthetic `TableGrid` instances.
- Exported extraction and assembly types from the top-level `pdf_reader` package to support future pipeline wiring and integration stories.

### File List

- NEW: `src/pdf_reader/extraction.py`
- MODIFIED: `src/pdf_reader/__init__.py`
- NEW: `tests/test_extraction.py`
# Story 1.4: Basic cell text extraction and assembly

Status: drafted

## Story

As a **developer working with the pdf-reading-project**,  
I want a **minimal `CellTextExtractor` and `TableAssembler` that can produce dataframe-ready output from a simple grid**,  
so that **I can exercise a basic end-to-end pipeline from detection through text extraction and table assembly for simple tables**.

## Acceptance Criteria

1. **Cell text extraction API exists**
   - A `CellTextExtractor` (or equivalent) exists under the `pdf_reader` package.
   - It exposes a function or method that, given a `TableGrid` and a page image (or a suitable input), returns a `TableGrid` with `Cell.text` populated.
   - For the minimal implementation, it is acceptable to:
     - Use embedded text from a synthetic or curated test case, or
     - Stub text extraction with deterministic placeholder values, as long as the contract and data flow are clear.

2. **Table assembly API exists**
   - A `TableAssembler` (or equivalent) exists under the `pdf_reader` package.
   - It exposes a function or method that, given a `TableGrid` with `Cell.text` populated, returns a `TableDataFrameSpec` (and optionally a Pandas DataFrame).
   - For simple rectangular grids (no merged cells), the resulting rows and columns match the logical grid shape and preserve cell text placement.

3. **MVP behavior for a curated simple table**
   - Given a `TableGrid` produced by the minimal grid detector from Story 1.3 (or a synthetic grid), `CellTextExtractor` and `TableAssembler` can:
     - Produce non-empty cell text for each cell (from OCR, embedded text, or stubs).
     - Produce a `TableDataFrameSpec` whose row/column counts and ordering match the input grid.
   - All cells involved have `row_span = col_span = 1`, and assembly does not attempt to handle merged cells.

4. **Tests for text extraction and assembly**
   - Tests verify:
     - `CellTextExtractor` returns a grid with `Cell.text` populated for all cells in a small synthetic or curated grid.
     - `TableAssembler` produces a `TableDataFrameSpec` (and/or DataFrame) with expected shape and values.
   - Tests run successfully via `pytest`.

5. **No coupling to advanced features**
   - Implementation does not introduce LLM fallbacks, complex OCR configuration, or merged-cell handling; these are deferred to later stories.
   - Public interfaces are designed so that more advanced extraction strategies can be plugged in later without breaking callers.

## Tasks / Subtasks

- [ ] T1: Define minimal extraction and assembly interfaces
  - [ ] Create or extend a module (e.g., `src/pdf_reader/extraction.py` or `src/pdf_reader/pipeline.py`) to host:
    - [ ] A `CellTextExtractor` class or functions.
    - [ ] A `TableAssembler` class or functions.
  - [ ] Ensure these use existing models from `pdf_reader.models` (`TableGrid`, `Cell`, `TableDataFrameSpec`).

- [ ] T2: Implement minimal `CellTextExtractor`
  - [ ] Implement a method like `extract_cell_texts(table_grid, page_image_or_source)` that:
    - [ ] Iterates over `Cell` instances in a `TableGrid`.
    - [ ] Populates `Cell.text` and optionally `text_confidence` and `text_source`.
    - [ ] For this story, may use:
      - [ ] A simple, deterministic stub (e.g., `f"r{row}_c{col}"`) for each cell, **or**
      - [ ] A minimal OCR/embedded-text path for one curated test case, if convenient.

- [ ] T3: Implement minimal `TableAssembler`
  - [ ] Implement a method like `assemble_table(table_grid) -> TableDataFrameSpec` (and optionally a helper `to_dataframe(spec)` that returns a Pandas DataFrame).
  - [ ] Ensure:
    - [ ] The resulting structure has `rows` and `columns` consistent with `table_grid.n_rows` and `n_cols`.
    - [ ] Each `Cell.text` appears in the correct position in the assembled structure.
    - [ ] For this story, no special handling is required for merged cells; treat each cell as a 1x1 entry.

- [ ] T4: Add tests for extraction and assembly
  - [ ] Add tests (e.g., `tests/test_extraction_and_assembly.py`) that:
    - [ ] Construct a small synthetic `TableGrid` (e.g., 2x3) with known coordinates and empty `text`.
    - [ ] Run `CellTextExtractor` and assert that all `Cell.text` fields are populated as expected.
    - [ ] Run `TableAssembler` and assert that:
      - [ ] The resulting `TableDataFrameSpec` has the expected shape.
      - [ ] Cell values are in the expected row/column positions.
    - [ ] Optionally, if a DataFrame helper is implemented, assert that the DataFrame matches the expected values.

- [ ] T5: Wire extraction and assembly into the pipeline surface
  - [ ] Ensure extraction and assembly functions are importable from the `pdf_reader` package (directly or via a `pipeline` module).
  - [ ] Optionally add a simple integration helper that:
    - [ ] Takes a `TableGrid`, runs cell text extraction, and returns an assembled table structure for use in the vertical slice.

## Dev Notes

- **Architectural alignment**
  - This story corresponds to Phase 1 tasks T1.3 and T1.4 in `docs/prd.md` Section 13.2 (basic cell text extraction and table assembly).
  - Keep the implementation narrow and focused on making the pipeline usable end-to-end for simple tables, not robust for all document types.

- **Extraction strategy guidance**
  - Using stubs or simple deterministic text is acceptable at this stage if OCR setup would slow down the sprint.
  - If you choose to integrate a basic OCR path, keep configuration surface small (e.g., DPI, language) and lean on existing ingestion outputs.

- **Testing strategy**
  - Favor synthetic `TableGrid` instances over real PDFs to validate logic quickly and deterministically.
  - Keep tests focused on invariants (shape, placement, non-empty text) rather than OCR quality.

### Project Structure Notes

- Place extraction-related code under `src/pdf_reader/extraction.py` (or similar) to keep concerns separated from ingestion and detection.
- Ensure public functions are small, composable, and easy to call from a future `PipelineRunner`.

### References

- [Source: `docs/prd.md` — Sections 12.2–12.3, 13.2 (C4 CellTextExtractor, C5 TableAssembler, Phase 1 baseline extraction/assembly)]
- [Source: `docs/sprint-artifacts/sprint-plan-2025-11-16.md` — Story S4 description and acceptance criteria]

## Dev Agent Record

### Context Reference

- `docs/sprint-artifacts/sprint-plan-2025-11-16.md`
- `docs/prd.md`

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List


