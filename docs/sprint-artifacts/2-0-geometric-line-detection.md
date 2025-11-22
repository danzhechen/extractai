# Story 2.0: Geometric line detection and grid construction

Status: review

**Last Updated**: 2025-11-21

## Story

As a **developer working with the pdf-reading-project**,  
I want **the grid structure detector to identify actual table lines and borders from page images**,  
so that **the extracted table structure accurately reflects the visual layout instead of using rough even divisions**.

## Acceptance Criteria

1. **Geometric line detection implemented**
   - `GridStructureDetector` (or a new helper module) detects horizontal and vertical lines from page images using image processing techniques (e.g., OpenCV line detection, Hough transforms, or morphological operations).
   - The detector identifies actual table borders and internal grid lines, not just evenly divided regions.
   - Line detection works for at least curated PDFs with clear, bordered tables.

2. **Grid construction from detected lines**
   - The detector builds `TableGrid` by:
     - Identifying horizontal lines to determine row boundaries.
     - Identifying vertical lines to determine column boundaries.
     - Constructing cells from the intersections of detected lines.
   - Cell bounding boxes (`Cell.bbox`) are derived from actual line positions, not calculated from even division.
   - The resulting grid accurately represents the visual table structure.

3. **Handling of line imperfections**
   - The detector tolerates minor imperfections:
     - Slightly broken or faded lines are still detected.
     - Small gaps in lines (within a configurable threshold) are bridged or inferred.
   - Configuration allows tuning of line detection sensitivity (e.g., minimum line length, gap tolerance).

4. **Backward compatibility**
   - Simple tables without explicit lines can still be processed (fallback to even division or text-alignment heuristics if no lines detected).
   - Existing tests for simple tables continue to pass.
   - The implementation does not break the existing `GridStructureDetector` interface.

5. **Tests for line detection**
   - Tests cover:
     - At least one curated PDF with clear horizontal and vertical table lines.
     - Verification that detected row/column counts match the visual structure.
     - Verification that cell bounding boxes align with actual line positions.
     - Edge cases: tables with missing outer borders, tables with only partial internal lines.

6. **Integration with existing pipeline**
   - Line detection integrates seamlessly with `PipelineRunner`.
   - Debug artifacts (overlay images) show detected lines visually for QA.
   - Performance is acceptable for typical PDFs (e.g., <5s per page for line detection).

## Tasks / Subtasks

- [x] **T2.0.1 — Research and choose line detection approach**
  - [x] Evaluate options: OpenCV (HoughLines, morphological operations), PDF vector primitives (if available), or hybrid approach.
  - [x] Choose an approach that balances accuracy, performance, and maintainability.
  - [x] Document the chosen approach and rationale.

- [x] **T2.0.2 — Implement horizontal line detection**
  - [x] Create a function/module to detect horizontal lines from page images.
  - [x] Handle edge cases: faded lines, broken lines, noise.
  - [x] Return line positions (y-coordinates) with confidence scores if applicable.
  - [x] Add unit tests for horizontal line detection on synthetic or curated images.

- [x] **T2.0.3 — Implement vertical line detection**
  - [x] Create a function/module to detect vertical lines from page images.
  - [x] Handle edge cases similar to horizontal detection.
  - [x] Return line positions (x-coordinates) with confidence scores if applicable.
  - [x] Add unit tests for vertical line detection.

- [x] **T2.0.4 — Build grid from detected lines**
  - [x] Extend or refactor `GridStructureDetector.build_grid()` to:
     - Accept detected horizontal and vertical lines as input.
     - Calculate row boundaries from horizontal lines.
     - Calculate column boundaries from vertical lines.
     - Construct `Cell` objects with bounding boxes from line intersections.
  - [x] Handle cases where lines are missing or incomplete (infer boundaries or use fallback).
  - [x] Ensure cell indices and bounding boxes are correct.

- [x] **T2.0.5 — Add configuration for line detection**
  - [x] Extend `PipelineConfig` (or create detector-specific config) to include:
     - Line detection sensitivity/threshold parameters.
     - Minimum line length.
     - Gap tolerance for broken lines.
     - Enable/disable line detection (fallback to even division).
  - [x] Document configuration options.

- [x] **T2.0.6 — Integration and testing**
  - [x] Integrate line detection into `PipelineRunner.extract_tables()`.
  - [x] Add integration tests with curated PDFs that have clear table lines.
  - [x] Verify that extracted grids match visual structure (row/column counts, cell positions).
  - [x] Ensure debug artifacts show detected lines in overlay images.

- [x] **T2.0.7 — Performance and edge case handling**
  - [x] Profile line detection performance on typical PDFs.
  - [x] Add fallback logic for tables with no detectable lines (e.g., text-alignment heuristics or even division).
  - [x] Test edge cases: very thin lines, heavily scanned/blurry images, tables with only outer borders.
  - [x] Document limitations and known issues.

- [x] **T2.0.8 — Documentation and examples**
  - [x] Update architecture docs to describe line detection approach.
  - [x] Add examples showing before/after: even division vs. line-based detection.
  - [x] Document configuration options and tuning guidance.
  - [x] Update troubleshooting guide with line detection issues.

## Dev Notes

- **Architectural alignment**
  - This story addresses the foundational gap in Phase 2: actual geometric detection before merged cell inference.
  - It corresponds to the deferred part of Phase 1 Task T1.2 (grid structure detection) and enables Phase 2 Task T2.1 (merged cell detection).
  - Line detection should be modular and swappable (e.g., via strategy pattern or dependency injection) to allow future ML-based approaches.

- **Implementation strategy**
  - Start with OpenCV-based morphological operations or Hough line transforms for reliability and performance.
  - Consider PDF vector primitives (lines/rectangles) from the PDF library as a complementary signal if available.
  - Keep the implementation focused on clear, bordered tables initially; irregular tables are handled in Story 3.2.

- **Testing strategy**
  - Use curated PDF fixtures with known table structures (e.g., financial statements, simple data tables).
  - Visual verification: overlay detected lines on original images to validate accuracy.
  - Compare extracted grid dimensions (n_rows, n_cols) with ground truth for test fixtures.

- **Performance considerations**
  - Line detection should be fast enough for interactive use (<5s per page is a reasonable target).
  - Consider caching detected lines if the same page is processed multiple times.
  - Profile and optimize if line detection becomes a bottleneck.

### Project Structure Notes

- Place line detection logic in `src/pdf_reader/detection.py` or a new submodule `src/pdf_reader/detection/line_detection.py`.
- Keep the interface clean: `detect_horizontal_lines(image) -> List[float]` (y-coordinates) and `detect_vertical_lines(image) -> List[float]` (x-coordinates).
- Consider making line detection optional/configurable so users can fall back to even division for speed if needed.

### References

- Source: `docs/prd.md` — Section 13.2 (Phase 1, T1.2 grid structure detection - deferred line detection)
- Source: `docs/prd.md` — Section 13.3 (Phase 2, T2.1 merged cells - requires line detection first)
- Source: `docs/sprint-artifacts/1-3-minimal-table-detection-and-grid-construction.md` — Original story that deferred line detection

## Dev Agent Record

### Context Reference

- `docs/prd.md` Section 13.2 (Phase 1, T1.2 grid structure detection - deferred line detection)
- `docs/sprint-artifacts/sprint-plan-2025-11-16.md`

### Agent Model Used

Auto (Cursor AI Agent)

### Debug Log References

- Created `src/pdf_reader/detection/line_detection.py` with line detection functions using OpenCV morphological operations and HoughLinesP
- Extended `GridStructureDetector` to support line detection with fallback to even division
- Added line detection configuration to `PipelineConfig` and `config_loader.py`
- Integrated line detection into `PipelineRunner._process_page` to pass `page_image` to `build_grid`
- Added comprehensive test suite in `tests/test_line_detection.py` (12 tests) and extended `tests/test_detection.py` (4 new tests)

### Completion Notes List

✅ **Geometric line detection implementation complete**

**Key Changes:**
1. **Line Detection Module**: Created `src/pdf_reader/detection/line_detection.py` with:
   - `LineDetectionConfig` dataclass for configuration
   - `detect_horizontal_lines()` and `detect_vertical_lines()` functions
   - Uses OpenCV morphological operations (erosion/dilation) + HoughLinesP for precise detection
   - Handles broken/faded lines with gap tolerance and line merging
   - Returns pixel coordinates matching existing BoundingBox convention

2. **GridStructureDetector Enhancement**: Extended to support line detection:
   - Added optional `line_detection_config` parameter
   - Added optional `page_image` parameter to `build_grid()`
   - New `_build_grid_from_lines()` method constructs cells from detected line intersections
   - Falls back to `_build_grid_even_division()` if line detection fails or is disabled
   - Maintains backward compatibility (works without page_image)

3. **Configuration**: Added line detection settings to `PipelineConfig`:
   - `enable_line_detection: bool = True` (default enabled)
   - `line_detection_min_length: int = 50` (minimum line length in pixels)
   - `line_detection_gap_tolerance: int = 10` (max gap to merge lines)
   - `line_detection_morph_iterations: int = 3` (morphological operation iterations)
   - Integrated into config loader for YAML/JSON files and environment variables

4. **Pipeline Integration**: Updated `PipelineRunner`:
   - Creates `LineDetectionConfig` from `PipelineConfig` in `_process_page()`
   - Configures `GridStructureDetector` with line detection config
   - Passes `page_image` to `build_grid()` for line detection

5. **Testing**: Comprehensive test coverage:
   - `tests/test_line_detection.py`: 12 unit tests covering:
     - Basic horizontal/vertical line detection
     - Region-constrained detection
     - Disabled detection
     - Edge cases (no lines, thin lines, partial borders)
     - Performance (<5s requirement)
     - Different image sizes
   - `tests/test_detection.py`: 4 new integration tests covering:
     - Line detection with GridStructureDetector
     - Fallback to even division
     - Disabled line detection
     - Backward compatibility

6. **Dependencies**: Added `opencv-python>=4.8.0` to `requirements.txt`

**Performance**: Line detection completes in <1s for typical images (800x600), well under the 5s requirement.

**Limitations & Known Issues**:
- Line detection works best with clear, bordered tables
- Very thin lines (<2 pixels) may not be detected reliably
- Heavily scanned/blurry images may require tuning of detection parameters
- Tables without explicit lines fall back to even division (as designed)
- Irregular tables (non-rectangular cells) are handled in Story 3.2

**Backward Compatibility**: ✅ Maintained - existing code without `page_image` parameter continues to work with even division fallback.

**Documentation Updates (T2.0.8)**:
1. **Architecture Documentation** (`docs/architecture.md`):
   - Added detailed "Line Detection Deep Dive" section explaining the 5-step process
   - Updated `GridStructureDetector` section with line detection responsibilities and configuration
   - Added before/after comparison of line detection vs. even division

2. **Configuration Guide** (`docs/guides/configuration.md`):
   - Added comprehensive "Line Detection Settings" section with all 5 parameters
   - Documented environment variables for line detection
   - Added 3 example configurations: standard, aggressive (poor scans), and disabled

3. **Getting Started Guide** (`docs/guides/getting-started.md`):
   - Added "Line Detection: Before and After" section with practical examples
   - Included visual comparison guidance using debug artifacts
   - Added decision guide: when to use line detection vs. even division
   - Included tuning examples for poor-quality PDFs

4. **Troubleshooting Guide** (`docs/troubleshooting.md`):
   - Added "Inaccurate Cell Boundaries" section with line detection diagnostics
   - Added "Line Detection Not Finding Lines" section with parameter tuning
   - Added "Line Detection Too Slow" section with performance optimization
   - Included CLI examples for common line detection issues

