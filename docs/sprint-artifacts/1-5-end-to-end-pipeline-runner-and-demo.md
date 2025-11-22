# Story 1.5: End-to-end pipeline runner & demo script

Status: review

## Story

As a **developer or analyst using the pdf-reading-project**,  
I want an **end-to-end `PipelineRunner.extract_tables(pdf_input, config)` and a simple CLI/script demo**,  
so that **I can run a minimal vertical slice on a sample PDF and see extracted tables without wiring components manually**.

## Acceptance Criteria

1. **Pipeline runner API exists**
   - A `PipelineRunner` (or equivalent orchestration component) exists under the `pdf_reader` package.
   - It exposes a function or method such as `extract_tables(pdf_input, config) -> ExtractionResult`.
   - The runner wires together:
     - `PdfIngestionService` (Story 1.2)
     - `TableRegionDetector` (Story 1.3)
     - `GridStructureDetector` (Story 1.3)
     - `CellTextExtractor` (Story 1.4)
     - `TableAssembler` (Story 1.4)

2. **Config surface is defined and usable**
   - A lightweight configuration type exists (e.g., a `dataclass` or dict) capturing key options:
     - Input PDF path or bytes
     - Page range or a single page index
     - DPI (for rendering)
     - Any minimal flags needed by detection/extraction (e.g., default grid size for simple tests).
   - Sensible defaults are provided so that a basic call to `extract_tables("sample.pdf")` works without extensive configuration.

3. **Demo script / CLI command works on a curated PDF**
   - A small script or CLI entrypoint exists (e.g., `python -m pdf_reader.demo --input sample.pdf` or `pdf-reader-demo sample.pdf`).
   - Running the command on at least one curated simple PDF:
     - Does not crash.
     - Produces a human-inspectable output:
       - A printed representation of detected tables (e.g., pretty-printed dataframe-like output), **or**
       - A JSON dump of `ExtractionResult` to stdout or a file.

4. **Basic tests for pipeline wiring**
   - Tests verify:
     - `PipelineRunner.extract_tables` can be called with a synthetic or curated input and returns an `ExtractionResult` with at least one table.
     - The runner correctly propagates errors from ingestion/detection/extraction in a controlled way (e.g., raises a clear exception or returns an `ExtractionResult` with error metadata).
   - Tests run successfully via `pytest`.

5. **Sprint goal alignment**
   - The implemented pipeline and demo satisfy the sprint goal from `sprint-plan-2025-11-16.md`:
     - A simple vertical slice from PDF input to dataframe-ready output for a simple, bordered table.
   - A short note or section exists in `README` or `docs` describing how to run the demo and what to expect.

## Tasks / Subtasks

- [x] T1: Implement `PipelineRunner.extract_tables`
  - [x] Create or extend a module (e.g., `src/pdf_reader/pipeline.py`) containing a `PipelineRunner` class or top-level function.
  - [x] Implement `extract_tables(pdf_input, config) -> ExtractionResult` that:
    - [x] Uses `PdfIngestionService` to load the PDF and render pages.
    - [x] For each selected page, runs `TableRegionDetector` and `GridStructureDetector` to produce `TableGrid` instances.
    - [x] Runs `CellTextExtractor` and `TableAssembler` to produce table outputs for each grid.
    - [x] Aggregates results into a single `ExtractionResult`, including basic `RunStats`.

- [x] T2: Define a minimal configuration surface
  - [x] Add a small `Config` type (e.g., `PipelineConfig` dataclass) that includes:
    - [x] `input_path` (or equivalent)
    - [x] `page_indices` or `page_range`
    - [x] `dpi` and any minimal detection/extraction parameters needed for the curated vertical slice.
  - [x] Provide defaults so that a basic config can be constructed with minimal arguments.

- [x] T3: Implement demo script / CLI entrypoint
  - [x] Add a simple demo module (e.g., `src/pdf_reader/demo.py`) or console_script entrypoint that:
    - [x] Parses a minimal set of arguments (e.g., `--input`, optional `--page`, `--dpi`).
    - [x] Constructs a `PipelineConfig`, calls `PipelineRunner.extract_tables`, and prints a summary of results.
  - [x] Ensure the demo is documented and can be executed from the project root with a straightforward command.

- [x] T4: Add tests for pipeline and demo wiring
  - [x] Add tests (e.g., `tests/test_pipeline_demo.py`) that:
    - [x] Use a small curated or synthetic PDF to run `extract_tables` and assert that at least one table is present in `ExtractionResult`.
    - [ ] Optionally exercise the demo entrypoint in a lightweight way (e.g., via a subprocess or function call) to ensure it can run without crashing.

- [x] T5: Update documentation
  - [x] Add or update a short section in the project `README` or a `docs/` snippet that:
    - [x] Describes the vertical slice demo.
    - [x] Shows an example command and a brief example of expected output.
  - [x] Ensure documentation reflects the current names of the pipeline and demo entrypoints.

## Dev Notes

- **Architectural alignment**
  - This story corresponds to Phase 1 task T1.5 in `docs/prd.md` Section 13.2 and Story S5 in the sprint plan.
  - Keep the runner thin and orchestration-focused; avoid embedding heavy business logic that belongs in ingestion, detection, or extraction components.

- **Error handling**
  - For this sprint, favor clear exceptions and simple logging over complex error recovery.
  - Ensure that obvious misconfigurations (bad path, invalid page index) result in informative errors rather than silent failures.

- **Testing strategy**
  - Lean on the already-tested components (ingestion, detection, extraction, assembly) and focus pipeline tests on end-to-end integration and basic sanity checks.
  - Use small, deterministic sample PDFs or fixtures to keep tests fast.

### Project Structure Notes

- Place the orchestration code in `src/pdf_reader/pipeline.py` (or similar) to act as a clear entrypoint for the library.
- Keep the demo script thin and focused on wiring CLI arguments to `PipelineRunner`.

### References

- [Source: `docs/prd.md` — Sections 12.2–12.3, 13.2 (C7 Orchestrator / PipelineRunner, Phase 1 vertical slice)]
- [Source: `docs/sprint-artifacts/sprint-plan-2025-11-16.md` — Story S5 description and acceptance criteria]

## Dev Agent Record

### Context Reference

- `docs/sprint-artifacts/sprint-plan-2025-11-16.md`
- `docs/prd.md`

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

- Initial plan: Implement `PipelineRunner.extract_tables` in a new `pdf_reader.pipeline` module that wires ingestion, detection, extraction, and assembly into an `ExtractionResult`, add a minimal `PipelineConfig` dataclass, create a simple `demo` module that prints table previews, and write pytest-based integration tests using a small synthetic PDF generated via `reportlab`.

### Completion Notes List
- Implemented `PipelineRunner.extract_tables` in `pdf_reader.pipeline`, wiring ingestion, region/grid detection, text extraction, and table assembly into a single `ExtractionResult` with basic `RunStats`.
- Added `PipelineConfig` to capture input path, page indices, DPI, and simple grid dimensions with sensible defaults for the Sprint 1 vertical slice.
- Created a `pdf_reader.demo` module that provides a CLI (`python -m pdf_reader.demo --input path/to.pdf`) to run the pipeline and print table previews, and added integration tests in `tests/test_pipeline_demo.py` plus updated `README.md` with demo instructions.

### File List

- NEW: `src/pdf_reader/pipeline.py`
- NEW: `src/pdf_reader/demo.py`
- MODIFIED: `src/pdf_reader/__init__.py`
- NEW: `tests/test_pipeline_demo.py`
- NEW: `README.md`

