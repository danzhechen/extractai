# Story 1.2: PDF ingestion and page rendering

Status: review

## Story

As a **developer using the pdf-reading-project**,  
I want a **`PdfIngestionService` that can load PDFs and render pages as images at a configurable DPI**,  
so that **downstream components (table detection, grid construction, and extraction) have a reliable source of page images and basic document structure**.

## Acceptance Criteria

1. **PDF loading API is implemented**
   - A `PdfIngestionService` (or equivalent module/class) exists under the `pdf_reader` package.
   - It exposes a function or method `load_pdf(input: Union[str, bytes]) -> PdfDocument` that returns a `PdfDocument` built from the core models in `pdf_reader.models`.
   - `PdfDocument.pages` contains `PdfPage` instances with correct `index`, `width`, and `height` for each page.
2. **Page rendering API is implemented**
   - `PdfIngestionService` exposes a function or method `render_page(page_index: int, dpi: int) -> PageImage` (or a small wrapper type) that returns an image-like object suitable for downstream processing.
   - Rendering uses a configurable DPI parameter and produces consistent output for a given `page_index` and `dpi`.
3. **Basic error handling**
   - Attempting to load a non-existent or invalid PDF raises a clear, descriptive error rather than failing silently.
   - Requesting an out-of-range `page_index` for `render_page` raises a clear error (or returns a well-defined failure result).
4. **Tests for ingestion and rendering**
   - Unit or integration tests cover:
     - Successful load and render for at least one small sample PDF in the repo (or a synthetic fixture).
     - Error conditions for missing file and out-of-range `page_index`.
   - Tests run successfully via the project’s preferred test command (e.g., `pytest`).
5. **Minimal dependencies and configuration**
   - PDF library choice (e.g., `pdfplumber` or `PyMuPDF`) is wired through `requirements.txt` if not already present.
   - Any new configuration (e.g., default DPI) has a reasonable default and is documented briefly in code comments or a docstring.

## Tasks / Subtasks

- [x] T1: Choose and integrate a PDF library
  - [x] Review existing dependencies (`pdfplumber` already listed in `requirements.txt`) and confirm it is suitable for loading PDFs and accessing page dimensions.
  - [x] If needed, adjust imports or minimal configuration to use the chosen library.

- [x] T2: Implement `PdfIngestionService.load_pdf`
  - [x] Create a module (e.g., `src/pdf_reader/ingestion.py`) with a `PdfIngestionService` class or functions.
  - [x] Implement `load_pdf(input: Union[str, bytes]) -> PdfDocument` that:
    - [x] Loads the PDF from a file path or bytes.
    - [x] Constructs a `PdfDocument` with a `PdfPage` for each page, populating `index`, `width`, and `height`.
    - [x] Handles basic IO errors and invalid PDF formats with descriptive exceptions.

- [x] T3: Implement `PdfIngestionService.render_page`
  - [x] Implement `render_page(page_index: int, dpi: int) -> PageImage` that:
    - [x] Validates `page_index` is in range for the loaded document.
    - [x] Renders the page at the requested DPI using the chosen PDF library.
    - [x] Returns an image-like object compatible with future table detection (e.g., a Pillow `Image`).
  - [x] Add a reasonable default DPI (e.g., 200–300) in a constant or configuration field.

- [x] T4: Add tests for ingestion and rendering
  - [x] Add tests (e.g., `tests/test_ingestion.py`) that:
    - [x] Load a known simple PDF fixture and assert that `PdfDocument.page_count` and page sizes are as expected.
    - [x] Render page 0 at a test DPI and assert that the result is non-null and has expected dimensions or type.
    - [x] Verify that invalid paths and out-of-range `page_index` raise the expected exceptions.

- [x] T5: Update docs and configuration
  - [x] Confirm `requirements.txt` includes the chosen PDF library (currently `pdfplumber`) and no redundant dependencies are added.
  - [ ] Optionally add a short note to the sprint plan or README referencing `PdfIngestionService` as the ingestion entrypoint.

## Dev Notes

- **Architectural alignment**
  - This story corresponds to Phase 0 task T0.3 in `docs/prd.md` Section 13.1 (implement a thin `PdfIngestionService` backed by a PDF library).
  - Keep the ingestion layer thin and focused on I/O and basic geometry; do not implement table detection or OCR in this story.
- **Testing strategy**
  - Prefer fast, deterministic tests using small local PDF fixtures.
  - If no fixture exists yet, add a minimal 1–2 page PDF under a `tests/fixtures/` directory for ingestion tests.
- **Future dependencies**
  - Downstream stories (S3–S5) will depend on `PdfIngestionService` for consistent page images and document structure; design its API to be stable and testable.

### Project Structure Notes

- Place ingestion-related code under `src/pdf_reader/ingestion.py` (or a small `ingestion/` package) to keep the top-level `pdf_reader` namespace organized.
- Avoid hard-coding file paths in the ingestion code; use function arguments and configuration where needed.

### References

- [Source: `docs/prd.md` — Sections 12.2–12.3, 13.1 (C1 PdfIngestionService and ingestion tasks)]
- [Source: `docs/sprint-artifacts/sprint-plan-2025-11-16.md` — Story S2 description and acceptance criteria]

## Dev Agent Record

### Context Reference

- `docs/sprint-artifacts/stories/1-2-pdf-ingestion-and-page-rendering.context.xml`

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

- Initial plan: Implement a thin `PdfIngestionService` in `pdf_reader.ingestion` backed by `pdfplumber`, use Pillow images as `PageImage`, and add pytest-based tests that generate a tiny PDF fixture at runtime using `reportlab` to avoid checking binary fixtures into the repo.

### Completion Notes List
- Implemented `PdfIngestionService` in `pdf_reader.ingestion` using `pdfplumber` for loading PDFs and Pillow images for page rendering, with a configurable default DPI.
- Added pytest-based ingestion tests that generate a tiny PDF at runtime via `reportlab`, covering successful load/render plus missing-file and out-of-range page-index errors.
- Updated `requirements.txt` to include `reportlab` and exported ingestion types (`PdfIngestionService`, `PdfIngestionError`, `PageImage`) from the top-level `pdf_reader` package.

### File List

- NEW: `src/pdf_reader/ingestion.py`
- MODIFIED: `src/pdf_reader/__init__.py`
- NEW: `tests/test_ingestion.py`
- MODIFIED: `requirements.txt`

