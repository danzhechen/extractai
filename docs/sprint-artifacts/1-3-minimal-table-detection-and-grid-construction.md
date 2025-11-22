# Story 1.3: Minimal table detection and grid construction

Status: review

## Story

As a **developer working with the pdf-reading-project**,  
I want a **minimal `TableRegionDetector` and `GridStructureDetector` that can produce a simple logical grid for bordered tables**,  
so that **downstream components (extraction and assembly) can be exercised on a basic but end-to-end table pipeline**.

## Acceptance Criteria

1. **Table region detection API exists**
   - A `TableRegionDetector` (or equivalent) exists under the `pdf_reader` package.
   - It exposes a function or method that, given a page image and page index, returns one or more `TableRegion` instances.
   - For at least one simple test case, it returns a non-empty list with a region that covers a plausible table area.
2. **Grid structure detection API exists**
   - A `GridStructureDetector` (or equivalent) exists under the `pdf_reader` package.
   - It exposes a function or method that, given a `TableRegion` (and optionally a page image/layout), returns a `TableGrid` constructed with `Cell` objects from `pdf_reader.models`.
   - For the minimal implementation, it is acceptable to construct a grid by evenly splitting the region into `n_rows x n_cols` cells for a known test case.
3. **MVP behavior for a curated simple table**
   - For a curated simple “table” case (e.g., using a synthetic image or known dimensions), `TableRegionDetector` returns a single region and `GridStructureDetector` builds a `TableGrid` with the correct `n_rows`, `n_cols`, and `cells` length.
   - All cells have `row_span = col_span = 1` and non-negative indices.
4. **Tests for detection and grid construction**
   - Tests verify:
     - Region detection returns at least one region with expected page index and bounding box.
     - Grid construction returns a `TableGrid` with expected shape and a `cells` list that respects the invariants from `TableGrid` and `Cell`.
   - Tests run successfully via `pytest`.
5. **No coupling to future complexities**
   - Implementation remains minimal and does not attempt to support merged cells, multi-page tables, or sophisticated image processing; these are deferred to later stories.

## Tasks / Subtasks

- [x] T1: Define minimal detector interfaces
  - [x] Create a module (e.g., `src/pdf_reader/detection.py`) containing:
    - [x] A `TableRegionDetector` class or functions.
    - [x] A `GridStructureDetector` class or functions.
  - [x] Ensure these use the core models (`TableRegion`, `TableGrid`, `Cell`, `BoundingBox`) from `pdf_reader.models`.

- [x] T2: Implement minimal `TableRegionDetector`
  - [x] Implement a method like `detect(page_image, page_index: int)` that:
    - [x] Returns a list with a single `TableRegion` whose `bbox` covers the full page image (or a large central area), as a placeholder for real detection.
    - [x] Sets `page_index` and a reasonable default `confidence` value.

- [x] T3: Implement minimal `GridStructureDetector`
  - [x] Implement a method like `build_grid(region: TableRegion, n_rows: int, n_cols: int)` that:
    - [x] Creates a `TableGrid` with `n_rows`, `n_cols`, and a `table_id`.
    - [x] Populates `cells` by evenly splitting the region’s bounding box into a regular grid, assigning `row_index`, `col_index`, and `row_span = col_span = 1` for each cell.
    - [x] Ensures invariants from `TableGrid.__post_init__` are respected.

- [x] T4: Add tests for detection and grid construction
  - [x] Add tests (e.g., `tests/test_detection.py`) that:
    - [x] Construct a synthetic “page image” (e.g., a blank Pillow image) and call `TableRegionDetector.detect`, asserting one region with expected geometry.
    - [x] Call `GridStructureDetector.build_grid` with a known region and `n_rows`, `n_cols`, asserting:
      - [x] `TableGrid.n_rows` and `n_cols` match inputs.
      - [x] `len(cells)` is `n_rows * n_cols`.
      - [x] All `row_index`/`col_index` values are within range and spans are 1.

- [x] T5: Wire detectors into package namespace
  - [x] Export detector types (e.g., `TableRegionDetector`, `GridStructureDetector`) from the top-level `pdf_reader` package for easy import in future stories.

## Dev Notes

- **Architectural alignment**
  - This story corresponds to Phase 1 tasks T1.1 and T1.2 in `docs/prd.md` Section 13.2 (baseline table region and grid detection).
  - For this sprint, favor a simple, deterministic implementation over image-processing sophistication.
- **Testing strategy**
  - Use synthetic images and known dimensions to validate grid math instead of depending on real PDFs.
  - Defer OCR and any interaction with `PdfIngestionService` to later stories unless needed for integration experiments.

### Project Structure Notes

- Place detection-related code under `src/pdf_reader/detection.py` to keep the `pdf_reader` namespace coherent.
- Later, more advanced detection implementations (e.g., ML-based or heuristic line detection) can live alongside or behind these minimal interfaces.

### References

- [Source: `docs/prd.md` — Sections 12.2–12.3, 13.2 (TableRegionDetector and GridStructureDetector)]
- [Source: `docs/sprint-artifacts/sprint-plan-2025-11-16.md` — Story S3 description and acceptance criteria]

## Dev Agent Record

### Context Reference

<!-- Optional: add a story-context XML path here if story-context is run for this story -->

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

- Initial plan: Implement `TableRegionDetector` and `GridStructureDetector` in `pdf_reader.detection` with a minimal strategy (single full-page region and equal grid splits), and add pytest tests validating region geometry and grid invariants using synthetic Pillow images.

### Completion Notes List
- Implemented minimal `TableRegionDetector` and `GridStructureDetector` in `pdf_reader.detection`, using a full-page region and equal splits to form an `n_rows x n_cols` grid of `Cell` objects.
- Added tests in `tests/test_detection.py` that validate region geometry and grid invariants using synthetic Pillow images, without depending on real PDFs.
- Exported detector types from the top-level `pdf_reader` package for straightforward use in future stories and integration work.

### File List

- NEW: `src/pdf_reader/detection.py`
- MODIFIED: `src/pdf_reader/__init__.py`
- NEW: `tests/test_detection.py`
# Story 1.3: Minimal table detection and grid construction

Status: drafted

## Story

As a **developer working on the pdf-reading-project**,  
I want a **minimal `TableRegionDetector` and `GridStructureDetector` that work on one or two curated, bordered-table PDFs**,  
so that **the pipeline can detect at least one table and construct a simple grid for downstream text extraction and assembly**.

## Acceptance Criteria

1. **Minimal table region detection implemented**
   - A `TableRegionDetector` implementation exists under the `pdf_reader` package (e.g., in `pdf_reader/detection.py` or similar).
   - It exposes a function or method such as `detect_table_regions(page_image_or_layout) -> List[TableRegion]`.
   - On at least one curated simple PDF with a bordered table, the detector returns at least one `TableRegion` with plausible coordinates and `page_index`.

2. **Minimal grid structure detection implemented**
   - A `GridStructureDetector` implementation exists under the `pdf_reader` package.
   - It exposes a function or method such as `build_grid(region, page_image_or_layout) -> TableGrid`.
   - For the curated simple PDF(s), `TableGrid` has correct `n_rows` and `n_cols` for the primary table and contains `Cell` instances with `row_index`, `col_index`, and `bbox` populated.
   - For this story, assume no merged cells: all cells have `row_span = 1` and `col_span = 1`.

3. **Integration with existing models and ingestion**
   - `TableRegionDetector` and `GridStructureDetector` use the core data models defined in `pdf_reader.models` (`TableRegion`, `TableGrid`, `Cell`).
   - The detection code can consume outputs from the ingestion layer implemented in Story 1.2 (e.g., page image or layout information from `PdfIngestionService`).
   - A simple helper or integration function exists that, given a `PdfDocument` and a rendered page image, runs table region detection followed by grid construction for that page.

4. **Basic tests for detection and grid construction**
   - Tests (e.g., `tests/test_detection.py`) cover:
     - Running table region detection on at least one curated simple PDF page and asserting that at least one region is returned.
     - Running grid construction on a detected region and asserting expected `n_rows`, `n_cols`, and cell counts.
   - Tests run successfully via the project’s preferred test command (e.g., `pytest`).

5. **Constraints and scope explicitly respected**
   - Implementation is intentionally narrow and tuned for one or two curated simple, bordered-table PDFs (no need to robustly handle irregular or merged tables yet).
   - No LLM calls or OCR logic are introduced in this story; focus is purely on geometric table detection and grid structure.

## Tasks / Subtasks

- [ ] T1: Define detection module structure
  - [ ] Create a detection module (e.g., `src/pdf_reader/detection.py` or `src/pdf_reader/detection/__init__.py`) to host `TableRegionDetector` and `GridStructureDetector`.
  - [ ] Ensure detection code imports and uses data models from `pdf_reader.models` (`TableRegion`, `TableGrid`, `Cell`).

- [ ] T2: Implement minimal `TableRegionDetector`
  - [ ] Choose a simple detection strategy appropriate for curated bordered tables (e.g., using PDF line primitives or basic image line detection).
  - [ ] Implement a function or class method `detect_table_regions(page_image_or_layout) -> List[TableRegion]`.
  - [ ] For at least one curated PDF page, return at least one `TableRegion` covering the primary table.

- [ ] T3: Implement minimal `GridStructureDetector`
  - [ ] Implement `build_grid(region, page_image_or_layout) -> TableGrid`.
  - [ ] Derive row and column boundaries for the detected region using the chosen strategy (e.g., horizontal/vertical lines or heuristics over layout).
  - [ ] Populate `TableGrid.n_rows`, `TableGrid.n_cols`, and `cells` with appropriate `row_index`, `col_index`, and `bbox` values.
  - [ ] For this story, set `row_span = col_span = 1` for all cells.

- [ ] T4: Wire detection into a simple integration path
  - [ ] Add a helper function (e.g., in `pdf_reader/pipeline.py` or the detection module) that, given a `PdfDocument` and/or a rendered page image from `PdfIngestionService`, runs table region detection and grid construction for a specified page.
  - [ ] Ensure this helper can be invoked from a test to produce a `TableGrid` for at least one curated PDF.

- [ ] T5: Add tests for detection and grid construction
  - [ ] Add tests (e.g., `tests/test_detection.py`) that:
    - [ ] Use at least one curated simple PDF fixture (or a small synthetic one) to exercise the detection logic.
    - [ ] Assert that at least one `TableRegion` is found for the test page.
    - [ ] Assert that `TableGrid` has expected `n_rows`, `n_cols`, and cell counts for the primary table.
  - [ ] Confirm tests pass via the project’s preferred test command (e.g., `pytest`).

## Dev Notes

- **Architectural alignment**
  - This story corresponds to Phase 1 tasks T1.1 and T1.2 in `docs/prd.md` Section 13.2 (baseline table detection and grid structure).
  - Keep the detection logic narrow and simple, optimized for a small set of known PDFs; generalization and robustness (merged cells, multi-page, irregular tables) are explicitly deferred to later stories.

- **Detection strategy guidance**
  - Prefer a deterministic, easy-to-debug heuristic over a complex ML model at this stage.
  - Example approaches:
    - Use PDF vector primitives (lines/rectangles) from the chosen PDF library to infer table boundaries and grid lines.
    - Or, as a fallback, use basic image processing (e.g., thresholding and line detection) tuned for one curated PDF.
  - Hard-coded assumptions for a small set of fixture PDFs are acceptable in this story, as long as they are isolated and clearly documented in comments.

- **Testing strategy**
  - Use small, version-controlled PDF fixtures under a `tests/fixtures/` directory (or similar) to keep tests fast and reproducible.
  - Focus tests on verifying that detection produces at least one plausible table and an internally consistent grid (row/column counts, cell coverage).

- **Future stories**
  - Merged cell detection, more robust span handling, and multi-page support will be handled in future stories (aligned with Phase 2 in the PRD roadmap).
  - LLM-based extraction and advanced OCR configuration are out of scope here and will be introduced in Phase 3 stories.

### Project Structure Notes

- Place detection-related code under `src/pdf_reader/detection.py` or a small `detection/` subpackage to keep the top-level `pdf_reader` namespace organized.
- Keep interfaces (`TableRegionDetector`, `GridStructureDetector`) small and testable so they can be swapped out or extended in later sprints without breaking callers.

### References

- [Source: `docs/prd.md` — Sections 12.2–12.3, 13.2 (C2 TableRegionDetector, C3 GridStructureDetector, Phase 1 baseline detection)]
- [Source: `docs/sprint-artifacts/sprint-plan-2025-11-16.md` — Story S3 description and acceptance criteria]

## Dev Agent Record

### Context Reference

- `docs/sprint-artifacts/sprint-plan-2025-11-16.md`
- `docs/prd.md`

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List


