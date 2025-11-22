# Story 1.1: Project scaffolding & core data models

Status: review

## Story

As a **developer working on the pdf-reading-project**,  
I want a **proper Python package structure and core data models defined for the PDF table extraction pipeline**,  
so that **future sprints can implement ingestion, detection, extraction, and export on top of a clean, extensible architecture**.

## Acceptance Criteria

1. **Core package layout exists**
   - A top-level Python package (e.g., `pdf_reader`) exists under `src/` with submodules (or placeholders) for `models` and `pipeline`.
   - The project can be imported in a Python REPL or script using `from pdf_reader.models import TableGrid` without import errors.
2. **Core data models are implemented**
   - Dataclasses (or equivalent) exist for the conceptual models in the PRD: `PdfDocument`, `PdfPage`, `TableRegion`, `TableGrid`, `Cell`, `TableDataFrameSpec`, `ExtractionResult`, and `RunStats`.
   - Models capture at least the fields described in PRD Section 12.3 (IDs, indices, spans, bounding boxes, text fields, and basic metadata).
3. **Basic type and structure validation**
   - A small set of unit tests instantiates each core model with sample data and asserts key properties (e.g., row/column counts in `TableGrid`, spans >= 1, non-empty `tables` list in `ExtractionResult`).
   - Running the tests (e.g., `pytest` or `python -m unittest`) for this project passes without errors for the newly added tests.
4. **Minimal dependency and configuration setup**
   - `pdf-reading-project/requirements.txt` is updated, if needed, to include any new runtime dependencies required by these models (if any; pure dataclasses may not add dependencies).
   - A short note in `docs/sprint-artifacts/sprint-plan-2025-11-16.md` or `README` remains accurate with respect to the new package/module names.

## Tasks / Subtasks

- [ ] T1: Create package structure for core models
  - [x] Create `src/pdf_reader/__init__.py` and ensure it is recognized as a package.
  - [x] Create `src/pdf_reader/models.py` (or a `models/` package) to hold core dataclasses.
  - [x] Ensure project-level tooling (e.g., tests, imports) can reference `pdf_reader` from the project root.

- [ ] T2: Implement core data model classes
  - [x] Implement `PdfDocument` and `PdfPage` with minimal fields to support future ingestion (e.g., list of pages, page index).
  - [x] Implement `TableRegion`, `TableGrid`, and `Cell` with fields aligned to PRD Section 12.3 (indices, spans, bounding boxes, text, confidence, source).
  - [x] Implement `TableDataFrameSpec`, `ExtractionResult`, and `RunStats` to support downstream pipeline and metrics.

- [ ] T3: Add unit tests for data models
  - [x] Create a tests module (e.g., `tests/test_models.py`) if not present for this project.
  - [x] Add tests that construct example instances of each data model and assert basic invariants (e.g., `n_rows * n_cols >= len(cells)` for `TableGrid`).
  - [x] Ensure the tests run successfully via the project’s preferred test command (e.g., `pytest`).

- [ ] T4: Align dependencies and docs
  - [x] Review `pdf-reading-project/requirements.txt` and update only if additional dependencies are truly required.
  - [ ] Confirm that sprint plan documentation referencing core models and package layout remains accurate, updating phrasing only if necessary.

## Dev Notes

- **Architectural alignment**
  - This story corresponds to Phase 0 tasks T0.1 and T0.2 in `docs/prd.md` Section 13.1 (Foundations & Scaffolding).
  - Focus on data structures only; do not implement PDF ingestion, detection, or OCR logic in this story.
- **Testing strategy**
  - Keep tests lightweight and focused on structure and types rather than behavior that belongs to later stories.
  - Prefer simple assertions and construction tests over complex fixtures at this stage.
- **Future stories**
  - `PdfIngestionService`, `TableRegionDetector`, `GridStructureDetector`, `CellTextExtractor`, `TableAssembler`, and `PipelineRunner` will be implemented in separate stories (e.g., S2–S5 in the sprint plan).

### Project Structure Notes

- Place the `src/` directory at the project root (`pdf-reading-project/src/`) so that imports are consistent with other Python projects in this repo.
- If additional subpackages are needed later (e.g., `ingestion`, `detection`), they should live under `pdf_reader/` to keep a flat, predictable namespace.

### References

- [Source: `docs/prd.md` — Sections 12.2–12.3, 13.1 (C1–C7 components and data models)]
- [Source: `docs/sprint-artifacts/sprint-plan-2025-11-16.md` — Story S1 description and acceptance criteria]

## Dev Agent Record

### Context Reference

<!-- Story context XML will be added here by the story-context workflow if/when generated -->

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

- Initial plan: Implement core dataclasses in `src/pdf_reader/models.py`, add package scaffold via `src/pdf_reader/__init__.py`, and create `tests/test_models.py` to validate basic invariants. No external runtime dependencies expected beyond standard library.

### Completion Notes List

- Core data model layer implemented as pure dataclasses in `pdf_reader.models`, aligned with PRD Section 12.3.
- Basic pytest configuration added so the package can be tested via `pytest` with `src/` on the Python path.
- All new model tests pass, validating structural invariants without introducing external runtime dependencies.

### File List

- NEW: `src/pdf_reader/__init__.py`
- NEW: `src/pdf_reader/models.py`
- NEW: `tests/test_models.py`
- NEW: `pytest.ini`
