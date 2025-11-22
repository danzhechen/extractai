# Story 2.7: Debug artifacts and visualization

Status: review

## Story

As a **developer debugging or evaluating the pdf-reading-project**,  
I want the **pipeline to generate optional debug artifacts (overlay images and HTML reports) that visualize detected table structure**,  
so that **I can quickly verify detection accuracy, diagnose issues, and compare extracted tables with the original PDF**.

## Acceptance Criteria

1. **Overlay images with table structure**
   - When debug mode is enabled, the pipeline generates PNG overlay images for each processed page.
   - Overlays show:
     - Table region bounding boxes (drawn on the original page image).
     - Grid lines (row and column boundaries) within each detected table.
     - Cell indices (row/column labels) for each cell.
     - Optional: cell text content or confidence scores as annotations.
   - Overlay images are saved to a configurable output directory (e.g., `debug_output/` or `artifacts/`).

2. **HTML report generation**
   - The pipeline can generate a lightweight HTML report per run that includes:
     - Summary statistics (pages processed, tables detected, extraction metrics).
     - Original page images (or thumbnails) with detected table regions highlighted.
     - Sample extracted tables rendered as HTML tables (showing structure and extracted text).
     - Links to overlay images if they were generated.
   - The HTML report is self-contained (or uses relative paths) and can be opened in a browser.

3. **Configurable debug artifact generation**
   - `PipelineConfig` includes options to control artifact generation:
     - `enable_debug_artifacts: bool` (default False) to enable/disable artifact generation.
     - `debug_output_dir: Optional[str]` (default `"debug_output"`) for artifact output location.
     - `generate_overlays: bool` (default True when debug enabled) to control overlay image generation.
     - `generate_html_report: bool` (default True when debug enabled) to control HTML report generation.
   - Artifacts are only generated when explicitly enabled to avoid cluttering output directories.

4. **Overlay image quality and format**
   - Overlay images preserve the original page image resolution (or render at a reasonable DPI for visualization).
   - Overlays use clear, distinguishable colors and line styles for:
     - Table region boxes (e.g., green rectangles).
     - Grid lines (e.g., blue dashed lines).
     - Cell labels (e.g., small text annotations).
   - Images are saved in PNG format for lossless quality.

5. **HTML report content and structure**
   - The HTML report includes:
     - A header with run metadata (input PDF path, timestamp, config summary).
     - A metrics section showing `RunStats` data (tables detected, pages processed, etc.).
     - A per-page section with:
       - Original page image (or thumbnail).
       - List of detected tables on that page.
       - Links to overlay images if generated.
     - A sample tables section showing a few representative extracted tables as HTML tables.
   - The report uses simple, readable HTML/CSS (no external dependencies required).

6. **Tests for debug artifacts**
   - Tests verify:
     - That overlay images are generated when `enable_debug_artifacts = True`.
     - That overlay images contain expected visual elements (table boxes, grid lines).
     - That HTML reports are generated and contain expected sections.
     - That artifacts are not generated when debug mode is disabled.
   - Tests can verify artifact existence and basic structure without requiring image comparison libraries.

7. **Backward compatibility**
   - When `enable_debug_artifacts = False` (default), no artifacts are generated and behavior matches previous stories.
   - Artifact generation does not affect the core extraction pipeline or `ExtractionResult` structure.

## Tasks / Subtasks

- [x] T2.7.1: Design overlay image generation interface
  - [x] Create a module (e.g., `src/pdf_reader/debug_artifacts.py` or `src/pdf_reader/visualization.py`).
  - [x] Define functions or classes for:
     - [x] Drawing table region bounding boxes on page images.
     - [x] Drawing grid lines (row/column boundaries) within table regions.
     - [x] Annotating cells with indices or text labels.
  - [x] Document the interface and coordinate system (pixel coordinates vs. normalized).

- [x] T2.7.2: Implement overlay image generation
  - [x] Use an image library (e.g., Pillow/PIL) to:
     - [x] Load or receive the original page image.
     - [x] Draw table region bounding boxes (using `TableRegion.bbox`).
     - [x] Draw grid lines for each detected table (using `TableGrid` cell boundaries).
     - [x] Add text annotations for cell indices (row/col) or cell text.
  - [x] Save overlay images to the configured output directory with descriptive filenames (e.g., `page_0_overlay.png`).

- [x] T2.7.3: Implement HTML report generation
  - [x] Create a function or class to generate HTML reports:
     - [x] Generate HTML structure with header, metrics section, and per-page sections.
     - [x] Embed or link to page images (thumbnails or full images).
     - [x] Render extracted tables as HTML `<table>` elements with proper structure.
     - [x] Include links to overlay images if they were generated.
  - [x] Save the HTML report to the output directory (e.g., `extraction_report.html`).
  - [x] Use simple, inline CSS for styling (avoid external dependencies).

- [x] T2.7.4: Add debug artifact configuration
  - [x] Extend `PipelineConfig` with:
     - [x] `enable_debug_artifacts: bool` (default False).
     - [x] `debug_output_dir: str` (default `"debug_output"`).
     - [x] `generate_overlays: bool` (default True when debug enabled).
     - [x] `generate_html_report: bool` (default True when debug enabled).
  - [x] Add validation to ensure output directory exists or can be created.

- [x] T2.7.5: Integrate artifact generation into `PipelineRunner`
  - [x] Update `PipelineRunner.extract_tables` to:
     - [x] Check `config.enable_debug_artifacts` flag.
     - [x] Call overlay generation functions after table detection/extraction.
     - [x] Call HTML report generation at the end of the pipeline run.
     - [x] Pass necessary data (page images, `TableGrid` instances, `ExtractionResult`) to artifact generators.
  - [x] Ensure artifact generation does not block or slow down the core extraction pipeline significantly.

- [x] T2.7.6: Add tests for debug artifacts
  - [x] Add tests (e.g., `tests/test_debug_artifacts.py`) that:
     - [x] Run the pipeline with `enable_debug_artifacts = True` on a test PDF.
     - [x] Verify that overlay images are created in the output directory.
     - [x] Verify that overlay images are non-empty and have expected dimensions.
     - [x] Verify that HTML report is generated and contains expected sections (header, metrics, tables).
     - [x] Verify that artifacts are not generated when `enable_debug_artifacts = False`.
  - [x] Clean up generated artifacts in test teardown.

- [x] T2.7.7: Update documentation
  - [x] Add a section in `README` or `docs/` describing:
     - [x] How to enable debug artifacts.
     - [x] What artifacts are generated and where they are saved.
     - [x] How to interpret overlay images and HTML reports.
     - [x] Example commands or code snippets for generating artifacts.
  - [x] Optionally include sample overlay images or HTML report screenshots in documentation.

## Dev Notes

- **Architectural alignment**
  - This story corresponds to Phase 4 task T4.2 in `docs/prd.md` Section 13.5 (debug artifacts).
  - Focus on visualization for QA and debugging; keep artifact generation optional and non-intrusive.
- **Testing strategy**
  - Test artifact existence and basic structure rather than pixel-perfect image comparison (which is brittle).
  - Use small test PDFs to keep artifact generation fast in tests.
- **Performance considerations**
  - Artifact generation should be fast enough for development/debugging use cases but may add overhead; keep it optional.
  - Consider generating artifacts asynchronously or in a separate thread if needed, but start with synchronous generation for simplicity.

### Project Structure Notes

- Keep visualization/artifact code in a dedicated module (e.g., `pdf_reader/debug_artifacts.py` or `pdf_reader/visualization.py`).
- Consider using a lightweight HTML templating approach (e.g., string formatting or a simple template library) for HTML report generation.

### References

- [Source: `docs/prd.md` — Sections 12.2–12.3, 13.5 (T4.2 debug artifacts)]
- [Source: `docs/sprint-artifacts/sprint-plan-2025-11-16.md` — Phase 4 scope notes]
- [Related: Story 2.6 (structured logging), Story 1.5 (pipeline runner)]

## Dev Agent Record

### Context Reference

- `docs/prd.md` Section 13.5 (T4.2 debug artifacts)
- `docs/sprint-artifacts/sprint-plan-2025-11-16.md`

### Agent Model Used

Auto (Cursor AI Agent)

### Debug Log References

- Created `debug_artifacts.py` module with overlay image and HTML report generation functions
- Used PIL/Pillow for image manipulation and drawing
- Implemented coordinate conversion from normalized (0-1) to pixel coordinates
- Used string formatting for HTML generation (no external templating library)

### Completion Notes List

✅ **Debug artifacts and visualization implementation complete**

**Key Changes:**
1. **Debug artifacts module**: Created `src/pdf_reader/debug_artifacts.py` with:
   - `draw_table_overlay()`: Generates PNG overlay images showing table regions (green rectangles), grid lines (blue dashed), and cell indices (yellow labels)
   - `generate_html_report()`: Generates self-contained HTML reports with run statistics, extracted tables, and links to overlay images
   - Uses PIL/Pillow for image manipulation and drawing
   - Handles coordinate conversion from normalized (0-1) to pixel coordinates

2. **Configuration**: Extended `PipelineConfig` with:
   - `enable_debug_artifacts: bool` (default: False)
   - `debug_output_dir: str` (default: "debug_output")
   - `generate_overlays: bool` (default: True when debug enabled)
   - `generate_html_report: bool` (default: True when debug enabled)
   - Output directory is automatically created in `__post_init__` when artifacts are enabled

3. **Pipeline integration**: Updated `PipelineRunner.extract_tables()` to:
   - Track page images, regions, and grids during processing
   - Generate overlay images after each page is processed (if enabled)
   - Generate HTML report at the end of pipeline execution (if enabled)
   - Handle artifact generation errors gracefully (log warnings, don't fail pipeline)

4. **Overlay images**: PNG images with:
   - Green rectangles for table region bounding boxes
   - Blue dashed lines for grid boundaries (row/column separators)
   - Yellow labels with cell indices (R0C0, R0C1, etc.) in top-left corner of each cell
   - Saved as `page_{index}_overlay.png` in debug output directory

5. **HTML reports**: Self-contained HTML files with:
   - Header section (input PDF path, timestamp, configuration summary)
   - Run Statistics section (all metrics from RunStats)
   - Extracted Tables section (tables rendered as HTML tables, grouped by page)
   - Overlay Links section (links to overlay images if generated)
   - Errors section (if any errors occurred)
   - Inline CSS for styling (no external dependencies)
   - Saved as `extraction_report.html` in debug output directory

6. **Comprehensive tests**: Added `tests/test_debug_artifacts.py` with 10 test cases covering:
   - Overlay image generation when enabled/disabled
   - HTML report generation when enabled/disabled
   - HTML report content validation (sections, metrics, tables)
   - Overlay image validation (existence, format, dimensions)
   - Debug output directory creation
   - Backward compatibility (artifacts disabled by default)
   - Direct function testing for `draw_table_overlay()` and `generate_html_report()`

7. **Documentation**: Added "Debug Artifacts and Visualization" section to README.md with:
   - Code examples for enabling debug artifacts
   - Description of overlay images and HTML reports
   - Configuration options
   - Use cases and performance notes

**Implementation Details:**
- Overlay images use PIL ImageDraw for drawing operations
- Grid lines are drawn as dashed lines (5px segments)
- Cell indices are drawn with yellow background for visibility
- HTML reports use simple string formatting (no templating library)
- Artifact generation is synchronous but optional (disabled by default)
- Errors during artifact generation are logged but don't fail the pipeline
- All artifacts are saved to configurable output directory

**Backward Compatibility:**
- Debug artifacts are disabled by default (`enable_debug_artifacts=False`)
- When disabled, no artifacts are generated and behavior matches previous stories
- Artifact generation does not affect core extraction pipeline or `ExtractionResult` structure
- Existing code and tests continue to work without modification

### File List

- `src/pdf_reader/debug_artifacts.py` - New debug artifacts module (overlay images and HTML reports)
- `src/pdf_reader/pipeline.py` - Added debug artifact configuration and integration
- `tests/test_debug_artifacts.py` - New comprehensive test suite for debug artifacts
- `README.md` - Added "Debug Artifacts and Visualization" section
- `docs/sprint-artifacts/2-7-debug-artifacts-and-visualization.md` - Updated with completion status

