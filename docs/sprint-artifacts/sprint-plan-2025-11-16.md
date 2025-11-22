## Sprint Plan — pdf-reading-project

**Sprint Name:** Sprint 1 — Vertical Slice Foundations  
**Dates:** 2025-11-16 → 2025-11-18 (2 days, solo)  
**Owner:** Jerry (solo dev)  

---

## 1. Sprint Goal

**Build a minimal but working end-to-end pipeline that takes a simple PDF with a bordered table and returns dataframe-ready table data using a clear, modular architecture.**

Success means:
- You can run a single command/function like `extract_tables(pdf_path, config)` on a simple PDF.
- The pipeline executes ingestion → (stub or simple) detection → assembly and returns a structured result (even if detection is very naive).
- The codebase structure and core data models match the PRD architecture enough to be extended in later sprints.

---

## 2. Scope & Focus

**In scope for this sprint:**
- Phase 0 foundations and the **simplest** slice of Phase 1, tuned for a 2-day solo effort:
  - Repo/package scaffolding.
  - Core data models (`PdfDocument`, `TableRegion`, `TableGrid`, `Cell`, `ExtractionResult`, etc.).
  - `PdfIngestionService` that can load a PDF and render a page.
  - `PipelineRunner.extract_tables(...)` with a trivial or heuristic table detector for simple, bordered tables.
  - Basic conversion of detected cells into a dataframe-friendly structure (even if spans are all 1x1).
  - A tiny script/CLI or notebook that runs the vertical slice on one or two sample PDFs.

**Explicitly out of scope this sprint (but in roadmap):**
- Complex merged-cell handling and multi-page robustness.
- LLM fallbacks and advanced OCR configuration.
- Observability/QA overlays, HTML reports, and CI setup.

---

## 3. Sprint Backlog (Stories)

### Story S1 — Project scaffolding & core models

- **Type:** Tech story  
- **Description:** Set up the Python package structure and implement the core data models required by the architecture.  
- **Key Tasks:**
  - Create a `src/` package for the library (e.g., `pdf_reader/` with submodules like `ingestion`, `models`, `pipeline`).
  - Implement basic dataclasses for:
    - `PdfDocument`, `PdfPage`
    - `TableRegion`, `TableGrid`, `Cell`
    - `ExtractionResult`, `RunStats`
  - Add `requirements.txt` (or update project-level one) with the minimum dependencies (PDF library of choice).
- **Acceptance Criteria:**
  - Code imports cleanly (e.g., `from pdf_reader.models import TableGrid` works).
  - Simple unit or smoke tests can instantiate the core models without errors.

---

### Story S2 — PDF ingestion and page rendering

- **Type:** Tech story  
- **Description:** Implement `PdfIngestionService` to load PDFs and render pages as images at a configurable DPI.  
- **Key Tasks:**
  - Integrate a PDF library (e.g., `pdfplumber` or `PyMuPDF`) for loading PDFs.
  - Implement methods:
    - `load_pdf(input: Union[str, bytes]) -> PdfDocument`
    - `render_page(page_index: int, dpi: int) -> PageImage` (type alias or small wrapper).
  - Handle basic errors: missing file, invalid PDF, out-of-range page index.
- **Acceptance Criteria:**
  - Given a simple test PDF, `PdfIngestionService` can:
    - Load the document.
    - Render at least the first page to an image object.
  - Failures produce informative exceptions or error messages (no silent crashes).

---

### Story S3 — Minimal table detection and grid construction

- **Type:** Tech story  
- **Description:** Implement a very simple `TableRegionDetector` and `GridStructureDetector` sufficient for one or two curated, bordered-table PDFs.  
- **Key Tasks:**
  - Choose a minimal detection strategy (e.g., use PDF lines/rectangles or simple image-based line detection).
  - Implement:
    - `TableRegionDetector.detect(page_image_or_layout) -> List[TableRegion]`
    - `GridStructureDetector.build_grid(region, page_image_or_layout) -> TableGrid`
  - Assume no merged cells: set `row_span = col_span = 1` for all cells.
- **Acceptance Criteria:**
  - On a curated simple PDF, at least one `TableRegion` is detected.
  - `TableGrid` has correct row/column counts for that table.
  - Data structures line up with what `TableAssembler` will need.

---

### Story S4 — Basic cell text extraction and assembly

- **Type:** Tech story  
- **Description:** Implement a minimal `CellTextExtractor` and `TableAssembler` to produce dataframe-ready output for the simple case.  
- **Key Tasks:**
  - Integrate a basic OCR path or embedded text extraction (whichever is simpler to get working quickly).
  - Implement:
    - `CellTextExtractor` that fills `Cell.text` for each cell in `TableGrid`.
    - `TableAssembler` that converts `TableGrid` into `TableDataFrameSpec` and optionally a Pandas dataframe.
  - Keep configuration surface small (e.g., DPI, OCR language).
- **Acceptance Criteria:**
  - For the curated test PDF, the pipeline produces at least one non-empty dataframe.
  - Rows and columns in the dataframe visually match the original table layout for the simple case.

---

### Story S5 — End-to-end pipeline runner & demo script

- **Type:** Integration story  
- **Description:** Wire components into `PipelineRunner.extract_tables(pdf_input, config)` and provide a simple script/CLI to run the pipeline.  
- **Key Tasks:**
  - Implement `PipelineRunner` that connects:
    - `PdfIngestionService` → `TableRegionDetector` → `GridStructureDetector` → `CellTextExtractor` → `TableAssembler`.
  - Define a lightweight `config` object or dict.
  - Add a script or CLI entrypoint (e.g., `python -m pdf_reader.demo --input sample.pdf`).
- **Acceptance Criteria:**
  - Running the demo command on the curated test PDF:
    - Does not crash.
    - Produces a printed/serialized representation of extracted tables (e.g., dataframe preview or JSON).
  - Sprint goal statement is satisfied: you have a minimal working vertical slice for simple tables.

---

## 4. Rough Timeboxing (2-Day Solo Sprint)

- **Day 1 (approx.):**
  - Morning: Story S1 (scaffolding & models).
  - Afternoon: Story S2 (ingestion) and start of S3 (basic detection).
- **Day 2 (approx.):**
  - Morning: Finish S3 and implement S4 (text extraction + assembly).
  - Afternoon: Story S5 (pipeline wiring + demo script), quick manual test, and small README notes.

You can flex order as needed; the key is to preserve the sprint goal of a working vertical slice.

---

## 5. Risks & Mitigations (for this sprint)

- **Risk:** PDF library or OCR setup takes longer than expected.  
  - **Mitigation:** Start with the simplest library you are comfortable with; if OCR is slow to configure, temporarily stub text extraction or use embedded text PDFs for the demo.

- **Risk:** Table detection heuristics take too long to tune.  
  - **Mitigation:** Hardcode assumptions for one or two curated PDFs (e.g., known table location) to keep momentum; generalize in later sprints.

- **Risk:** Scope creep (e.g., trying to support merged cells or multi-page tables immediately).  
  - **Mitigation:** Defer complex spans and multi-page handling explicitly to the next sprint; treat them as follow-up stories.

---

## 6. Definition of Done (Sprint-Level)

The sprint is **Done** when:
- A simple demo command/function successfully runs the vertical slice on at least one curated PDF with a simple table.
- The code structure matches the main components outlined in the PRD (even if some implementations are naive).
- You have a short note in the repo (e.g., in `README` or a `docs/` snippet) explaining how to run the demo.




