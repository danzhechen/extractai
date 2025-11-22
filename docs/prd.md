## Product Requirements Document (PRD) — pdf-reading-project

**Version:** 0.1 (Draft)  
**Owner (PM Agent):** TBD  
**Last Updated:** 2025-11-16  

---

## 1. Product Overview

**Product Name:** pdf-reading-project  
**One-Line Description:**  
FREE, production-grade PDF table extraction powered by Gemini 2.5 Pro LLM, with smart cost optimization and offline fallback.

**Background & Context**  
Current OCR and PDF parsing tools often lose table structure (merged cells, headers, multi-line cells, etc.), forcing users into heavy manual cleanup. This project takes an **LLM-first approach** with FREE Gemini 2.5 Pro as the default, providing high-accuracy extraction at zero cost for typical usage. The system intelligently balances cost, accuracy, and availability through a three-tier strategy: FREE LLM-first extraction, optional paid premium models for complex cases, and heuristic-based offline fallback.

---

## 2. Problem Statement

**Core Problems**
- Existing OCR tools fail to maintain table structure (grid, merged cells, header hierarchy).
- Information is frequently lost or misaligned during extraction (e.g., header/column mismatch, dropped rows/columns).
- Manual correction is time-consuming and error-prone, especially for large or complex reports.

**Why Now**
- Increased reliance on PDF reports (financial, operational, research) for downstream analytics.
- Teams need high-fidelity, structured data quickly, without deep expertise in OCR tuning.

---

## 3. Goals & Non-Goals

**Primary Goals**
- **G1:** Provide **FREE, high-accuracy extraction** for 95%+ of tables using Gemini 2.5 Pro (zero cost).
- **G2:** Preserve the original table structure from PDFs with high fidelity (grid, merged cells, row/column spans).
- **G3:** Ensure **no material information loss** during extraction (cell content, headers, footnotes inside tables).
- **G4:** Produce a **dataframe representation** that closely matches the source table and is ready for downstream analysis.
- **G5:** Enable **smart cost optimization** through tiered extraction strategies (FREE → PAID → Offline).

**Secondary Goals**
- **G6:** Provide a way to visually inspect and compare extracted structure vs. the original table (for QA).
- **G7:** Enable configurable trade-offs between cost, accuracy, and availability (preset system).
- **G8:** Track and report extraction costs transparently (token usage, estimated USD).

**Non-Goals (Initial Release)**
- N1: Full-document layout understanding outside of tables (paragraphs, images, figures).
- N2: Intelligent semantic interpretation of content (e.g., auto-normalizing currencies, units) beyond raw text handling.
- N3: Building a full SaaS product (auth, billing, user management); focus on core extraction engine and developer-friendly interface.

---

## 4. Target Users & Use Cases

**Primary Users**
- **Data/Quant Analysts:** Need to convert PDF tables into clean dataframes for modeling and reporting.
- **Operations / Finance Teams:** Regularly ingest tabular reports from vendors, banks, or partners.
- **Engineers / Tool Builders:** Integrate a reliable PDF table extraction component into internal tools or pipelines.

**Key Use Cases**
- **UC1 — Financial Statements Extraction:**  
  Analyst uploads a PDF with balance sheets and income statements; system outputs structured dataframes preserving multi-level headers and merged cells.
- **UC2 — Vendor/Partner Reports:**  
  Ops team ingests monthly operational PDFs with complex tables (merged cells, footnotes in cells) and needs aligned columns with minimal manual cleanup.
- **UC3 — Research Tables:**  
  Researcher extracts tables from academic PDFs where multi-line cells and irregular column widths exist, expecting a dataframe that mirrors layout.

---

## 5. Scope

**In Scope (v0 / v1)**
- Parsing PDF pages that contain **rectangular, grid-like tables**.
- Detecting:
  - Table boundaries on the page.
  - Row and column boundaries (lines, gaps, and inferred boundaries).
  - Merged cells and row/column spans where reasonably detectable.
- Extracting:
  - Text from each cell using OCR or embedded text.
  - Basic cell-level metadata (row index, column index, spans).
- Output:
  - A structured representation that can be converted into a dataframe (e.g., Pandas) with enough metadata to reconstruct layout.

**Out of Scope (for initial release)**
- Handwritten tables.
- Complex multi-table composites where tables overlap or are nested inside each other.
- Dynamic, interactive UI for end-users (beyond minimal visualization/QA if any).

---

## 6. Functional Requirements

### 6.1 Input Handling
- **FR1:** The system MUST accept PDFs as input (single or multi-page).
- **FR2:** The system SHOULD support specifying page ranges for extraction.
- **FR3:** The system SHOULD provide basic configuration options:
  - Preferred resolution / DPI.
  - OCR provider/model selection (if multiple are supported).

### 6.2 Structure Detection (Step 1)
- **FR4:** The system MUST detect table regions on a page (bounding boxes).
- **FR5:** The system MUST identify row and column boundaries within each table.
- **FR6:** The system SHOULD identify merged cells and record row/column spans.
- **FR7:** The system MUST produce a machine-readable representation of table structure suitable for programmatic use (e.g., JSON describing grid, spans, and positions).

### 6.3 Data Extraction (Step 2)
- **FR8:** For each detected cell, the system MUST attempt to extract text content via OCR or embedded text.
- **FR9:** The system SHOULD support basic cleaning of extracted text (e.g., trimming whitespace, normalizing line breaks).
- **FR10:** The system MUST map extracted text back to the correct cell in the table structure model.
- **FR11:** If the primary OCR engine fails or returns low-confidence results (threshold TBD), the system SHOULD fall back to the existing LLM-based approach by sending the relevant cell or cropped table image(s) to an LLM for text extraction.

### 6.4 Output & API
- **FR12:** The system MUST provide an API (function/module level is sufficient for v0) to:
  - Accept a PDF file or file path.
  - Return structured table data.
- **FR13:** The system MUST return:
  - A dataframe-ready structure (e.g., list of tables, each as rows/columns).
  - A structure metadata object (spans, positions, confidence scores if available).
- **FR14:** The system SHOULD allow exporting results:
  - As Pandas dataframes (Python context).
  - As JSON for language-agnostic use.

### 6.5 Quality & Verification
- **FR14:** The system SHOULD expose a simple way to compare extracted tables vs. the original (e.g., coordinates overlay or sample HTML rendering) for internal QA.
- **FR15:** The system SHOULD log extraction statistics per run (number of tables detected, pages processed, errors).

---

## 7. Non-Functional Requirements

- **NFR1 — Accuracy:**  
  - Target: ≥90% correct cell-to-cell mapping for typical printed financial/operational tables (TBD: precise eval spec).
- **NFR2 — Performance:**  
  - Reasonable performance on typical-length reports (e.g., ≤30s for a 50-page PDF on baseline hardware; exact target TBD).
- **NFR3 — Reliability:**  
  - The system MUST fail gracefully and report errors (e.g., unsupported PDFs, no tables found) with actionable messages.
- **NFR4 — Extensibility:**  
  - Architecture SHOULD allow swapping/improving the OCR engine and structure detection models without breaking the public interface.
- **NFR5 — Observability:**  
  - Logs SHOULD capture key pipeline stages (input, structure detection, OCR, assembly) for debugging.

---

## 8. Dependencies & Assumptions

**Dependencies**
- OCR engine(s) (e.g., Tesseract or cloud OCR) — exact choice TBD.
- PDF rendering / parsing library for page images and layout cues.

**Assumptions**
- Input PDFs are primarily machine-printed (not handwritten).
- Users are comfortable interacting with a library/tooling interface (CLI or code), not necessarily a full GUI.

---

## 9. Risks & Open Questions

**Risks**
- R1: Highly irregular tables (ragged rows, irregular borders) may reduce structure detection accuracy.
- R2: Poor scan quality (low DPI, skew, blur) can degrade OCR and boundary detection performance.

**Open Questions (for future clarification with stakeholders)**
- OQ1: What are the primary document domains (finance, logistics, research, etc.) and priority order?
- OQ2: What level of UI/visualization, if any, is required for v1?
- OQ3: Are there hard SLAs for latency or throughput?
- OQ4: Do we need built-in anonymization or PII handling?

---

## 10. Success Metrics (Initial Hypotheses)

- **M1:** Percentage of tables where the extracted dataframe schema (rows/columns) matches the source table (visually verified) ≥ X% (TBD).
- **M2:** Reduction in manual cleanup time versus current tools (self-reported by early users).
- **M3:** Number of successful extractions per week by internal teams or pilot users.

---

## 11. Release Plan (High-Level)

- **Phase 0:** Confirm target document types and accuracy benchmarks with stakeholders.  
- **Phase 1:** Implement baseline pipeline (structure detection + OCR + dataframe output) for a narrow set of PDFs.  
- **Phase 2:** Improve robustness (merged cells, spans, multi-page tables) and add QA/verification hooks.  
- **Phase 3:** Prepare for integration into downstream analytics workflows (APIs, packaging, docs).
-
---

## 12. Technical Architecture (Architect View)

### 12.1 Architecture Overview

**Updated November 2025**: The system now uses an **LLM-first architecture** with FREE Gemini 2.5 Pro as the default extraction strategy, while maintaining the original heuristic approach as a fallback.

- **Pattern:** Dual-strategy extraction system with pluggable extraction strategies.
- **Form Factor (v1):** Python library + CLI entrypoint, optimized for batch jobs, embeddable into other services.
- **Key Principles:**
  - **LLM-first**: Leverage FREE advanced vision models (Gemini 2.5 Pro) for highest accuracy at zero cost.
  - **Cost-optimized**: Smart tiered approach (FREE → PAID → Offline) with transparent cost tracking.
  - **Pluggable strategies**: Extraction strategies are swappable behind stable interfaces.
  - **Conservative escalation**: Don't auto-spend user money without explicit consent.
  - **Inspectable outputs**: intermediate artifacts (e.g., debug overlays, cost reports) are first-class.

**High-level data flows (two strategies)**:

**Strategy 1 — LLM End-to-End (Default, FREE)**:
1. **PDF Ingestion** → 2. **Page Rendering** → 3. **LLM Extraction** (Gemini 2.5 Pro) → 4. **JSON Parsing** → 5. **Assembly** → 6. **Export + Cost Report**

**Strategy 2 — Heuristic (Offline Fallback)**:
1. **PDF Ingestion** → 2. **Page Rendering** → 3. **Table Region Detection** → 4. **Grid/Structure Detection** → 5. **OCR + LLM Fallback** → 6. **Assembly** → 7. **Export**

### 12.2 Extraction Strategies (New Architecture)

The system supports two extraction strategies, selected via the `extraction_strategy` config or `--preset` CLI flag:

#### **Strategy A: LLM End-to-End (Default, Recommended)**

**Implementation**: `GeminiEndToEndStrategy`

**Data Flow**:
1. Render page as image (PNG)
2. Send to LLM API (Gemini/GPT-4o) with structured prompt
3. Parse JSON response into `TableDataFrameSpec`
4. Track tokens, cost, model used

**Cost Tiers** (November 2025 pricing):
- **Tier 1 (Primary)**: Gemini 2.5 Pro — **FREE** (default)
  - Cost: $0 per 1M tokens
  - Use for: 95%+ of tables
  - Quality: Excellent
- **Tier 2 (Escalation)**: Gemini 3.0 Pro — **PAID** (~$1.25/1M input, ~$5.00/1M output)
  - Cost: ~$1.25 per 1000 pages
  - Use for: Complex tables where Tier 1 fails
  - Quality: Best (user-validated as "super good")
  - **Conservative**: Only escalate if `enable_auto_escalation=True` (default: False)
- **Tier 3 (Fallback)**: Heuristic strategy — **FREE**
  - Cost: $0 (offline)
  - Use for: No internet / API quota exhausted
  - Quality: Good for clean bordered tables

**Configuration Presets**:
- `smart` (default): Tier 1 primary, Tier 2 escalation disabled (FREE)
- `premium`: Tier 2 always (PAID, best quality)
- `offline`: Tier 3 only (FREE, no API)

**Advantages**:
- ✅ Zero cost for typical usage (FREE Tier 1)
- ✅ Handles complex/irregular tables better than heuristics
- ✅ No need for line detection, OCR tuning
- ✅ Transparent cost tracking

**Disadvantages**:
- ❌ Requires API key and internet connectivity
- ❌ Potentially higher latency than heuristics (2-5 sec/page)
- ❌ Escalation to Tier 2 incurs costs (if enabled)

#### **Strategy B: Heuristic (Offline Fallback)**

**Implementation**: `HeuristicExtractionStrategy` (legacy, still supported)

**Data Flow**:
1. Render page as image
2. Detect table regions (OpenCV morphological operations)
3. Detect grid lines (Hough transforms, line detection)
4. Build grid structure (rows, columns, spans)
5. Extract text via OCR (Tesseract)
6. Optional: LLM fallback for low-confidence cells

**Advantages**:
- ✅ Works offline (no API required)
- ✅ Zero cost (no API calls)
- ✅ Fast for simple tables

**Disadvantages**:
- ❌ Struggles with irregular/complex tables
- ❌ Requires careful tuning (line detection params, OCR settings)
- ❌ Lower accuracy than LLM approach

### 12.3 Core Components

- **C1 — `PdfIngestionService`:**
  - Responsibilities: load PDF from file path/bytes, handle page-range selection, invoke rendering/layout tooling.
  - Interfaces:
    - `load_pdf(input: Union[str, bytes]) -> PdfDocument`
    - `render_page(page_index: int, dpi: int) -> PageImage`

- **C2 — `TableRegionDetector`:**
  - Responsibilities: detect table bounding boxes per page using heuristics and/or ML.
  - Inputs: `PageImage` (and optional vector hints from PDF parser).
  - Outputs: `List[TableRegion]` with coordinates and confidence.

- **C3 — `GridStructureDetector`:**
  - Responsibilities: infer rows, columns, and merged cells for each `TableRegion`.
  - Inputs: `TableRegion`, `PageImage`, optional line/shape primitives from PDF.
  - Outputs: `TableGrid` model:
    - cells (row/col indices),
    - spans (row_span, col_span),
    - geometric metadata (bounding boxes).

- **C4 — `CellTextExtractor`:**
  - Responsibilities: extract text content for each cell via:
    - Primary OCR engine (configurable),
    - Fallback: embedded text extraction where available,
    - Optional LLM fallback when OCR confidence < threshold.
  - Inputs: `TableGrid`, `PageImage`, configuration (OCR provider, DPI, thresholds).
  - Outputs: `TableGrid` enriched with `cell.text`, `cell.confidence`, and provenance tags (`ocr`, `embedded_text`, `llm_fallback`).

- **C5 — `TableAssembler`:**
  - Responsibilities: turn enriched `TableGrid` into a dataframe-ready representation.
  - Outputs:
    - `TableDataFrameSpec` (rows, columns, multi-index headers if needed),
    - `TableMetadata` (spans, positions, confidences, source page/table IDs).

- **C6 — `ExportLayer`:**
  - Responsibilities: provide adapters to:
    - Build Pandas dataframes from `TableDataFrameSpec`,
    - Emit JSON for language-agnostic consumption,
    - Optionally emit debug overlays/HTML preview for QA.

- **C7 — `Orchestrator` / `PipelineRunner`:**
  - Responsibilities: coordinate the end-to-end pipeline:
    - Iterate over pages/tables,
    - Apply configuration (page ranges, DPI, model choice),
    - Collect metrics and logs.
  - Public-facing API:
    - `extract_tables(pdf_input, config) -> ExtractionResult`.

### 12.3 Data Models (Conceptual)

- **`PdfDocument`**
  - `pages: List[PdfPage]`

- **`TableRegion`**
  - `page_index: int`
  - `bbox: BoundingBox`
  - `confidence: float`

- **`TableGrid`**
  - `table_id: str`
  - `page_index: int`
  - `cells: List[Cell]`
  - `n_rows: int`
  - `n_cols: int`

- **`Cell`**
  - `row_index: int`
  - `col_index: int`
  - `row_span: int`
  - `col_span: int`
  - `bbox: BoundingBox`
  - `text: Optional[str]`
  - `text_confidence: Optional[float]`
  - `text_source: Literal["ocr", "embedded", "llm_fallback"]`

- **`TableDataFrameSpec`**
  - `rows: List[List[CellValue]]` (after span resolution)
  - `columns: List[ColumnSpec]]` (may support multi-level headers)
  - `table_metadata_id: str`

- **`ExtractionResult`**
  - `tables: List[TableDataFrameSpec]`
  - `metadata: List[TableMetadata]`
  - `run_stats: RunStats` (counts, errors, durations).

### 12.4 Configuration & Extensibility

- **Configuration Surface (initial):**
  - `dpi: int` (page rendering resolution),
  - `page_ranges: Optional[List[PageRange]]`,
  - `ocr_engine: Literal["tesseract", "cloud_provider_X", "mock"]`,
  - `ocr_language: str`,
  - `llm_fallback_enabled: bool`,
  - `llm_fallback_threshold: float`,
  - `enable_debug_artifacts: bool` (overlays, HTML previews).

- **Extensibility Strategy:**
  - Components (C2–C4) expose abstract base classes / protocols so new detectors/engines can be plugged in without changing `Orchestrator` API.
  - Configuration-driven wiring: new engines are registered under names and selected via config rather than code changes.
  - Data models kept stable; internal implementations may evolve as long as `ExtractionResult` contract holds.

### 12.5 Observability & QA Hooks

- **Logging & Metrics:**
  - Log per-run and per-table stats (pages processed, tables detected, average OCR confidence, number of fallbacks).
  - Emit structured logs (JSON) to make downstream aggregation easier.

- **Debug Artifacts (optional but recommended for internal use):**
  - Per-page PNGs with:
    - Table bounding boxes,
    - Grid lines,
    - Cell labels (row/col indices).
  - Lightweight HTML report for a run:
    - Original page snapshots + overlaid structure,
    - Sample rendered tables from `TableDataFrameSpec`.

### 12.6 Open Technical Questions (Architect-Level)

- **ATQ1:** Which table-structure detection approach should we prioritize for v1 (rule-based on line detection vs. ML-based layout model), given target document domains?
- **ATQ2:** Where should the boundary be between this library and any future UI/annotation tool for manual correction?
- **ATQ3:** How strict should we be about versioning of OCR/LLM providers in outputs (e.g., embedding engine/version into metadata for reproducibility)?
- **ATQ4:** Do we need built-in concurrency/parallelism for multi-page PDFs in v1, or can that be delegated to callers (e.g., multiprocessing wrapper)?

---

## 13. Implementation Roadmap (Engineer-Facing)

This roadmap translates the product goals and architecture into concrete, engineer-friendly phases. It is deliberately biased toward **getting a narrow but robust vertical slice working early**, then expanding coverage and quality.

### 13.1 Phase 0 — Foundations & Scaffolding

**Objectives**
- Establish the repo structure, core abstractions, and a minimal “hello world” pipeline that can run end-to-end on a single simple table page.

**Key Tasks**
- **T0.1:** Set up project structure:
  - Python package layout (e.g., `pdf_reader/` with `ingestion`, `detection`, `extraction`, `assembly`, `export`, `pipeline` modules).
  - Basic dependency management (e.g., `pyproject.toml` or `requirements.txt`).
- **T0.2:** Define core data models as Python classes / dataclasses:
  - `PdfDocument`, `PdfPage`, `TableRegion`, `TableGrid`, `Cell`, `TableDataFrameSpec`, `ExtractionResult`.
- **T0.3:** Implement a thin **`PdfIngestionService`** backed by a battle-tested PDF library (e.g., `pdfplumber`, `PyMuPDF`, or similar):
  - Load PDF from path/bytes.
  - Render a single page as an image at configurable DPI.
- **T0.4:** Implement a minimal **`PipelineRunner.extract_tables(pdf_input, config)`** that:
  - Calls ingestion,
  - Returns a stub `ExtractionResult` (e.g., empty `tables`) and logs basic run stats.

**Exit Criteria**
- Engineers can run a small script or CLI command that:
  - Accepts a PDF path and config,
  - Produces an `ExtractionResult` object (even if empty),
  - Emits basic logs and does not crash on well-formed PDFs.

### 13.2 Phase 1 — Baseline Table Detection & Extraction (Vertical Slice)

**Objectives**
- Deliver a working end-to-end slice on **simple, well-printed tables** (no complex merges), using a straightforward detection strategy.

**Key Tasks**
- **T1.1:** Implement a heuristic **`TableRegionDetector`**:
  - Use rendered page images + PDF vector hints (lines/rectangles) if available.
  - Target: detect rectangular tables with visible borders.
- **T1.2:** Implement a simple **`GridStructureDetector`**:
  - Derive row/column lines from detected borders/lines.
  - Assume no merged cells in this phase; `row_span = col_span = 1`.
- **T1.3:** Implement **`CellTextExtractor`** with primary OCR:
  - Integrate a chosen OCR backend (e.g., Tesseract) with configurable language and DPI.
  - For now, skip LLM fallback; capture OCR confidence scores if available.
- **T1.4:** Implement **`TableAssembler`**:
  - Convert `TableGrid` + `Cell.text` into `TableDataFrameSpec`.
  - Provide a helper to convert into Pandas dataframes.
- **T1.5:** Extend `PipelineRunner`:
  - Traverse pages → table regions → grid → text → assembly.
  - Populate `ExtractionResult` and `RunStats`.

**Exit Criteria**
- On a curated set of **simple single-page PDFs**, the pipeline:
  - Detects tables and returns non-empty dataframes,
  - Preserves row/column counts and ordering,
  - Runs within a reasonable time on a laptop for small files.

### 13.3 Phase 2 — Merged Cells, Spans & Multi-Page Robustness

**Objectives**
- Handle **merged cells** and more realistic tables; improve robustness across multiple pages.

**Key Tasks**
- **T2.1:** Enhance **`GridStructureDetector`**:
  - Detect missing internal lines and infer merged cells.
  - Populate `row_span` and `col_span` correctly.
- **T2.2:** Update **`TableAssembler`** to respect spans:
  - Resolve merged cells into dataframe-friendly output (e.g., propagate text across spanned cells or use a standard representation).
- **T2.3:** Multi-page support in **`PipelineRunner`**:
  - Iterate over all pages (or configured ranges),
  - Track `table_id` and `page_index` for each table.
- **T2.4:** Introduce basic error handling strategy:
  - Gracefully skip pages/tables with fatal issues,
  - Aggregate errors into `RunStats` / `TableMetadata`.

**Exit Criteria**
- On a broader validation set that includes merged cells and multi-page PDFs:
  - Majority of tables have correctly detected row/column counts and merged spans.
  - The system produces intelligible dataframes even when some spans are ambiguous, without hard crashes.

### 13.4 Phase 3 — LLM Fallback & Advanced Extraction

**Objectives**
- Improve text extraction quality and resilience using LLM-based fallbacks and more nuanced OCR strategies.

**Key Tasks**
- **T3.1:** Extend **`CellTextExtractor`** with fallback logic:
  - Define a clear confidence threshold for “low confidence” OCR outputs.
  - Route those cells (or cropped table/region images) to an LLM-based extraction function where configured.
- **T3.2:** Design LLM invocation boundary:
  - Centralize LLM calls behind a small interface (e.g., `LLMExtractionService`).
  - Keep all provider-specific details isolated to one module.
- **T3.3:** Add provenance tracking:
  - Ensure `Cell.text_source` (`"ocr"`, `"embedded"`, `"llm_fallback"`) is set consistently.
- **T3.4:** Introduce rate limiting / batching considerations for LLM calls (if needed).

**Exit Criteria**
- On “hard” cells (fuzzy scans, small fonts), the system:
  - Falls back to LLM where configured,
  - Shows measurable improvement in text accuracy on a test set,
  - Maintains acceptable latency/cost characteristics for expected usage.

### 13.5 Phase 4 — QA, Observability & Developer Experience

**Objectives**
- Make the system easier to debug, evaluate, and integrate into other workflows.

**Key Tasks**
- **T4.1:** Implement structured logging:
  - Log per-run and per-table metrics (pages processed, tables detected, average OCR confidence, number of fallbacks, errors).
- **T4.2:** Implement debug artifacts:
  - Optional overlay images (PNG) with table regions, grid lines, and cell indices.
  - Lightweight HTML report per run that surfaces a few representative tables.
- **T4.3:** Improve configuration ergonomics:
  - Central config object/type with sensible defaults.
  - CLI wrapper (e.g., `pdf-reader extract --input file.pdf --config config.yaml`).
- **T4.4:** Documentation:
  - Developer-facing docs for architecture, key interfaces, and examples.

**Exit Criteria**
- Engineers and power users can:
  - Run the pipeline via CLI or code with clear configuration options,
  - Quickly inspect where things went wrong via logs and artifacts,
  - Understand how to swap in new detectors/OCR engines using docs.

### 13.6 Phase 5 — Hardening & Extension (Post-v1 Options)

**Objectives**
- Prepare for broader adoption and potential integration into larger systems.

**Key Tasks (Candidate Backlog)**
- **T5.1:** Concurrency support:
  - Optional parallel processing for multi-page PDFs (within process or via a simple multiprocessing wrapper).
- **T5.2:** Advanced table types:
  - Better support for ragged tables, multi-panel tables, or partially bordered tables.
- **T5.3:** Versioning & reproducibility:
  - Embed engine versions and configuration summaries into `TableMetadata`.
- **T5.4:** Integration adapters:
  - Example integrations (e.g., Airflow/Prefect tasks, simple HTTP wrapper) if needed by stakeholders.

**Exit Criteria**
- The project is ready to be:
  - Integrated as a stable library in internal pipelines,
  - Extended with additional models/engines without breaking existing integrations.
