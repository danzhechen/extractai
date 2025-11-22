# Architecture

This document describes the architecture of the PDF table extraction pipeline, including component design, data flow, and key design decisions.

## Overview

**Updated November 2025**: The system now uses a **dual-strategy architecture** with LLM-first extraction as the default approach.

The PDF table extraction pipeline is a modular system that processes PDF documents to extract structured table data. The system supports two extraction strategies:

1. **LLM End-to-End Strategy** (Default, Recommended): Uses FREE Gemini 2.5 Pro vision model to extract tables directly from page images
2. **Heuristic Strategy** (Offline Fallback): Uses OpenCV line detection + OCR for offline/budget scenarios

Both strategies share common ingestion and export layers but differ in their core extraction approach.

## High-Level Pipeline Flow

### Strategy 1: LLM End-to-End (Default, FREE)

```
PDF Document
    ↓
[PdfIngestionService] → Load PDF, render pages as images
    ↓
[GeminiEndToEndStrategy] → Send image to LLM (Gemini 2.5 Pro - FREE)
    ↓                        ↓ Structured JSON prompt
    ↓                        ↓ Parse JSON response
    ↓                        ↓ Track tokens/cost
    ↓
[TableAssembler] → Convert LLM JSON to TableDataFrameSpec
    ↓
ExtractionResult (tables + metadata + cost stats)
```

**Cost**: ~$0 for typical usage (FREE Gemini 2.5 Pro)  
**Accuracy**: Excellent for 95%+ of tables  
**Speed**: 2-5 seconds per page

### Strategy 2: Heuristic (Offline Fallback, FREE)

```
PDF Document
    ↓
[PdfIngestionService] → Load PDF, render pages as images
    ↓
[TableRegionDetector] → Detect table regions on each page
    ↓
[GridStructureDetector] → Build logical grid structure (OpenCV line detection)
    ↓
[CellTextExtractor] → Extract text from cells (OCR + optional LLM fallback)
    ↓
[TableAssembler] → Convert grid to dataframe-ready representation
    ↓
ExtractionResult (tables + metadata + stats)
```

**Cost**: $0 (no API calls)  
**Accuracy**: Good for clean, bordered tables  
**Speed**: Fast (< 1 second per page)

## Extraction Strategies

### Strategy Selection

Users select a strategy via:
- **Presets**: `--preset {smart|premium|offline}` (CLI)
- **Config**: `extraction_preset: smart` (YAML)
- **Explicit**: `extraction_strategy: llm_end_to_end` (config)

**Preset Mapping**:
- `smart` (default): LLM Strategy with FREE Gemini 2.5 Pro (~$0)
- `premium`: LLM Strategy with PAID Gemini 3.0 Pro (~$1.25/1K pages)
- `offline`: Heuristic Strategy, no API calls ($0)

### Cost Tracking & Reporting

The LLM strategy tracks:
- **Token Usage**: Input/output tokens per page and per run
- **Model Used**: Which model processed each page (primary vs escalation)
- **Estimated Cost**: USD estimate based on current pricing
- **Escalation Count**: How many pages required premium model

Cost fields in `RunStats`:
```python
llm_calls_primary: int        # Calls to free Gemini 2.5 Pro
llm_calls_escalation: int     # Calls to paid Gemini 3.0 Pro
llm_tokens_input: int         # Total input tokens
llm_tokens_output: int        # Total output tokens
estimated_cost_usd: float     # Estimated cost in USD
models_used: List[str]        # Unique models used in this run
```

## Key Components

### 1. PdfIngestionService

**Purpose**: Load PDF documents and render pages as images.

**Responsibilities**:
- Load PDF files from various sources (file path, bytes, etc.)
- Render PDF pages as PIL Images at specified DPI
- Handle PDF loading errors gracefully

**Key Methods**:
- `load_pdf(pdf_input) -> PdfDocument`: Load a PDF document
- `render_page(page_index, dpi) -> Image.Image`: Render a specific page as an image

**Data Models**:
- `PdfDocument`: Lightweight representation of a PDF with page metadata
- `PdfPage`: Represents a single page with dimensions

### 2. TableRegionDetector

**Purpose**: Detect table regions on rendered page images.

**Responsibilities**:
- Analyze page images to identify table regions
- Return bounding boxes for detected tables
- Provide confidence scores for detections

**Key Methods**:
- `detect(page_image, page_index) -> List[TableRegion]`: Detect table regions on a page

**Data Models**:
- `TableRegion`: Detected table region with bounding box and confidence

### 3. GridStructureDetector

**Purpose**: Build logical grid structure from detected table regions.

**Responsibilities**:
- Convert table regions into structured grids
- Detect actual table lines using geometric line detection (OpenCV)
- Handle merged cells (row/column spans)
- Create `TableGrid` with cell positions and relationships
- Fall back to even division if line detection fails

**Key Methods**:
- `build_grid(region, n_rows, n_cols, table_id, span_hints, line_detection_config, page_image) -> TableGrid`: Build grid structure

**Line Detection Approach**:
- **Primary Method**: Geometric line detection using OpenCV morphological operations and Hough Line Transform
  - Detects horizontal lines: erosion/dilation with horizontal kernel → HoughLinesP
  - Detects vertical lines: erosion/dilation with vertical kernel → HoughLinesP
  - Merges nearby lines to handle broken/faded lines
  - Constructs grid from line intersections for accurate cell boundaries
- **Fallback Method**: Even division if no lines detected or line detection disabled
  - Divides region evenly into n_rows × n_cols
  - Used for tables without explicit borders or when line detection fails

**Configuration**:
- `enable_line_detection`: Enable/disable geometric line detection (default: True)
- `line_detection_min_length`: Minimum line length in pixels (default: 40)
- `line_detection_gap_tolerance`: Max gap to merge broken lines (default: 5)
- `line_detection_morph_iterations`: Morphological operation iterations (default: 2)
- `line_detection_min_separation`: Minimum separation between distinct lines (default: 5)

**Data Models**:
- `TableGrid`: Logical grid representation with cells
- `Cell`: Individual cell with position, spans, and text
- `LineDetectionConfig`: Configuration for line detection parameters

### 0. Extraction Strategy Components (NEW)

#### GeminiEndToEndStrategy

**Purpose**: Direct LLM-based table extraction (bypasses traditional detection/grid pipeline).

**Responsibilities**:
- Send page image to vision LLM (Gemini or GPT-4o)
- Parse structured JSON response
- Convert to `TableDataFrameSpec`
- Track token usage and cost
- Handle escalation to premium models (if configured)

**Key Methods**:
- `process_page(page_index, page_image, config, logger, cancel_event) -> PageProcessingResult`
- `_call_llm_with_tracking(image, prompt, config, model_override) -> (text, tokens_in, tokens_out)`
- `estimate_cost(tokens_input, tokens_output, model_name) -> float`

**Escalation Logic**:
1. Try primary model (e.g., Gemini 2.5 Pro - FREE)
2. If fails and `enable_auto_escalation=True`, try escalation model (e.g., Gemini 3.0 Pro - PAID)
3. Track which model was used for cost reporting

**API Key Setup**:
- Set environment variable: `export PDF_READER_LLM_API_KEY="YOUR_API_KEY_HERE"`
- See [API Setup Guide](guides/api-setup.md) for details

**Cost Tracking**:
- Tracks tokens per page: `llm_tokens_input`, `llm_tokens_output`
- Estimates cost based on model pricing
- Reports model used: `model_used`

**Data Models**:
- `PageProcessingResult`: Per-page extraction result with cost metrics
- `RunStats`: Aggregate cost tracking across all pages

#### HeuristicExtractionStrategy

**Purpose**: Traditional CV-based extraction (offline, no API required).

**Responsibilities**:
- Coordinate table detection → grid construction → OCR → assembly
- Maintain backward compatibility with original pipeline
- Work completely offline

**Key Methods**:
- `process_page(page_index, page_image, config, logger, cancel_event) -> PageProcessingResult`

**Components Used**:
- `TableRegionDetector`
- `GridStructureDetector`
- `CellTextExtractor`
- `TableAssembler`

### 4. CellTextExtractor (Heuristic Strategy Only)

**Purpose**: Extract text content from table cells.

**Responsibilities**:
- Extract text from cells using OCR (or placeholder)
- Check OCR confidence scores
- Fall back to LLM extraction for low-confidence cells
- Track text source provenance (OCR vs LLM)

**Key Methods**:
- `fill_cell_text(grid, page_image) -> TableGrid`: Populate cell text

**Features**:
- Configurable confidence threshold
- Optional LLM fallback for difficult cells
- Provenance tracking (text_source field)

### 5. TableAssembler

**Purpose**: Convert `TableGrid` into a dataframe-ready representation.

**Responsibilities**:
- Resolve cell spans (merged cells)
- Create row/column structure for dataframe output
- Handle span propagation (text from merged cells fills all covered positions)

**Key Methods**:
- `to_dataframe_spec(grid) -> TableDataFrameSpec`: Convert grid to dataframe spec

**Data Models**:
- `TableDataFrameSpec`: Dataframe-oriented representation with rows and columns

### 6. PipelineRunner

**Purpose**: Orchestrate the end-to-end extraction process.

**Responsibilities**:
- Coordinate all pipeline components
- Handle multi-page processing
- Manage error handling and recovery
- Generate debug artifacts (if enabled)
- Collect metrics and statistics
- Configure logging

**Key Methods**:
- `extract_tables(pdf_input, config) -> ExtractionResult`: Run full pipeline

**Features**:
- Multi-page support with page range selection
- Comprehensive error handling (page-level and table-level)
- Structured logging at all stages
- Debug artifact generation (overlay images, HTML reports)
- Metrics collection (per-run and per-table)

## Line Detection Deep Dive

### How Line Detection Works

The geometric line detection system uses computer vision techniques to identify actual table borders and internal grid lines from page images:

**Step 1: Image Preprocessing**
- Convert PIL image to grayscale
- Apply adaptive thresholding to enhance line visibility
- Normalize contrast for consistent detection

**Step 2: Morphological Operations**
- **Horizontal lines**: Apply erosion/dilation with horizontal kernel (e.g., 25×1)
- **Vertical lines**: Apply erosion/dilation with vertical kernel (e.g., 1×25)
- Iterations (default: 2) strengthen line detection while removing noise

**Step 3: Hough Line Transform**
- Use OpenCV's `HoughLinesP` (Probabilistic Hough Transform)
- Detect line segments with configurable minimum length
- Filter lines within the table region bounding box

**Step 4: Line Merging**
- Merge nearby parallel lines (within `min_line_separation` pixels)
- Handle broken/faded lines by bridging small gaps (`gap_tolerance`)
- Remove duplicate lines from overlapping segments

**Step 5: Grid Construction**
- Sort horizontal lines by y-coordinate → row boundaries
- Sort vertical lines by x-coordinate → column boundaries
- Create cells from line intersections
- Calculate accurate bounding boxes for each cell

**Fallback Strategy**:
- If fewer than 2 horizontal or 2 vertical lines detected → fall back to even division
- If line detection disabled → use even division directly
- Ensures backward compatibility with tables lacking explicit borders

### Line Detection vs. Even Division

**Before (Even Division)**:
- Divides table region into equal-sized cells
- Assumes uniform row/column spacing
- May misalign with actual cell boundaries
- Fast but less accurate

**After (Line Detection)**:
- Detects actual table lines from image
- Respects variable row/column widths
- Aligns cell boundaries with visual structure
- Slightly slower but much more accurate

**Example**: A table with merged header cells and varying column widths:
- Even division: Creates uniform 4×4 grid, misaligning with actual cells
- Line detection: Detects 3 horizontal + 5 vertical lines, creating accurate 3×4 grid

## Data Models

### Core Models

**PdfDocument**:
- `pages: List[PdfPage]`: List of pages in the document
- `page_count: int`: Total number of pages

**TableRegion**:
- `page_index: int`: Page where table was detected
- `bbox: BoundingBox`: Bounding box coordinates (normalized 0-1)
- `confidence: float`: Detection confidence score

**TableGrid**:
- `table_id: str`: Unique identifier for the table
- `page_index: int`: Source page index
- `n_rows: int`: Number of rows in grid
- `n_cols: int`: Number of columns in grid
- `cells: List[Cell]`: List of cells in the grid

**Cell**:
- `row_index: int`: Row position (0-based)
- `col_index: int`: Column position (0-based)
- `row_span: int`: Number of rows this cell spans (default: 1)
- `col_span: int`: Number of columns this cell spans (default: 1)
- `bbox: Optional[BoundingBox]`: Cell bounding box
- `text: Optional[str]`: Extracted text content
- `text_confidence: Optional[float]`: OCR confidence score
- `text_source: Optional[TextSource]`: Source of text ("ocr", "llm_fallback", "embedded")

**ExtractionResult**:
- `tables: List[TableDataFrameSpec]`: Extracted tables
- `metadata: List[TableMetadata]`: Table metadata
- `run_stats: RunStats`: Pipeline execution statistics

**RunStats**:
- `pages_processed: int`: Pages successfully processed
- `tables_detected: int`: Total tables found
- `tables_extracted: int`: Successfully extracted tables
- `pages_skipped: int`: Pages that failed
- `tables_failed: int`: Tables that failed extraction
- `total_cells_extracted: int`: Total cells with text
- `average_ocr_confidence: float`: Average confidence across all cells
- `llm_fallback_count: int`: Number of LLM fallback calls
- `total_duration_ms: float`: Total execution time
- `errors: List[str]`: Error messages

**TableMetadata**:
- `table_id: str`: Table identifier
- `page_index: int`: Source page
- `region: TableRegion`: Detection region
- `grid_shape: tuple[int, int]`: Grid dimensions
- `status: TableStatus`: Extraction status ("success", "detection_failed", "extraction_failed")
- `error_message: Optional[str]`: Error details if failed
- `cell_count: int`: Total cells in table
- `cells_with_text: int`: Cells with extracted text
- `average_confidence: float`: Average confidence for this table
- `extraction_duration_ms: float`: Time to extract this table

## Configuration System

The pipeline uses a centralized `PipelineConfig` that supports multiple configuration sources:

**Priority Order** (highest to lowest):
1. Command-line arguments
2. Config file (YAML/JSON)
3. Environment variables
4. Programmatic defaults

**Configuration Groups**:
- **Input/Output**: `input_path`, `page_indices`, `output_dir`
- **Processing**: `dpi`, `default_rows`, `default_cols`
- **LLM Fallback**: `ocr_confidence_threshold`, `llm_fallback_enabled`, `llm_provider`, `llm_model`, `llm_api_key`
- **Logging**: `log_level`, `log_file`, `log_format`
- **Debug Artifacts**: `enable_debug_artifacts`, `debug_output_dir`, `generate_overlays`, `generate_html_report`

## Error Handling Strategy

The pipeline implements graceful error handling at multiple levels:

1. **Page-level errors**: Pages that fail to render or detect are skipped, with errors recorded
2. **Table-level errors**: Tables that fail extraction are tracked with status and error messages
3. **Partial results**: Successfully extracted tables are returned even if some pages/tables fail
4. **Structured reporting**: Error counts and messages are available in `RunStats`

## Logging and Observability

- **Structured logging**: JSON or human-readable format with contextual information
- **Log levels**: DEBUG, INFO, WARNING, ERROR
- **Metrics**: Per-run and per-table metrics for performance analysis
- **Debug artifacts**: Optional overlay images and HTML reports for visualization

## Extension Points

The pipeline is designed for extensibility:

1. **Custom OCR engines**: Implement `CellTextExtractor` interface
2. **Custom detectors**: Implement `TableRegionDetector` or `GridStructureDetector`
3. **Custom LLM providers**: Implement `LLMExtractionService` interface
4. **Custom output formats**: Extend `TableAssembler` or create new exporters

See `docs/guides/extending.md` for detailed extension guides.

## Design Decisions

1. **Modular architecture**: Components are loosely coupled and can be swapped independently
2. **Data-driven design**: Clear data models flow through the pipeline
3. **Span-aware grids**: Support for merged cells from the start
4. **Optional LLM fallback**: Opt-in feature to avoid unexpected costs
5. **Comprehensive error handling**: Failures don't crash the entire pipeline
6. **Structured logging**: Built-in observability for debugging and monitoring
7. **Configuration flexibility**: Multiple configuration sources for different use cases

## Performance Considerations

- **Page-by-page processing**: Memory efficient for large documents
- **Optional debug artifacts**: Can be disabled for production performance
- **LLM fallback**: Only used when needed (low confidence threshold)
- **Synchronous execution**: Simple and predictable, can be made async in future

## Future Extensions

Potential future enhancements:
- Async/parallel processing for multiple pages
- Additional OCR engine support (Tesseract, etc.)
- More sophisticated table detection algorithms
- Support for complex table structures (nested tables, rotated tables)
- Additional output formats (Excel, CSV, etc.)


