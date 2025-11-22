from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Sequence


@dataclass
class BoundingBox:
    """Axis-aligned bounding box in page coordinates.

    Coordinates are normalized to [0.0, 1.0] range, where:
    - (0.0, 0.0) is the top-left corner
    - (1.0, 1.0) is the bottom-right corner

    Attributes:
        x0: Left edge (0.0 = left edge of page)
        y0: Top edge (0.0 = top edge of page)
        x1: Right edge (1.0 = right edge of page)
        y1: Bottom edge (1.0 = bottom edge of page)
    """

    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class PdfPage:
    """Represents a single PDF page."""

    index: int
    width: float
    height: float


@dataclass
class PdfDocument:
    """Lightweight representation of a PDF document."""

    pages: List[PdfPage] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.pages)


@dataclass
class TableRegion:
    """Detected table region on a page.

    Represents a rectangular region on a PDF page that contains a table.
    Used by the detection stage to identify where tables are located.

    Attributes:
        page_index: Zero-based index of the page containing this region.
        bbox: Bounding box coordinates (normalized 0-1) defining the table region.
        confidence: Detection confidence score (0.0-1.0). Higher values indicate
            more confident detections.
        section_label: Optional label for multi-panel/section detection (e.g., region name).
    """

    page_index: int
    bbox: BoundingBox
    confidence: float = 1.0
    section_label: Optional[str] = None


TextSource = Literal["ocr", "embedded", "llm_fallback"]


@dataclass
class Cell:
    """Represents a single table cell in the logical grid.

    A cell can span multiple rows and columns (merged cells). The cell's position
    is defined by its top-left corner (row_index, col_index) and span dimensions.
    """

    row_index: int
    col_index: int
    row_span: int = 1
    col_span: int = 1
    bbox: Optional[BoundingBox] = None
    text: Optional[str] = None
    text_confidence: Optional[float] = None
    text_source: Optional[TextSource] = None
    structure_confidence: float = 1.0
    structure_source: Literal["explicit", "inferred", "filler"] = "explicit"
    is_filler: bool = False


@dataclass
class TableGrid:
    """Logical grid representation of a detected table.

    Represents a table as a structured grid of cells. Supports merged cells
    through row_span and col_span attributes on individual cells.

    Attributes:
        table_id: Unique identifier for this table (e.g., "p0_t0" for page 0, table 0).
        page_index: Zero-based index of the source page.
        n_rows: Number of rows in the grid.
        n_cols: Number of columns in the grid.
        cells: List of Cell objects representing all cells in the grid.
            Cells may have row_span > 1 or col_span > 1 for merged cells.

    Raises:
        ValueError: If n_rows or n_cols are non-positive, or if any cell has
            invalid span values.
    """

    table_id: str
    page_index: int
    n_rows: int
    n_cols: int
    cells: List[Cell] = field(default_factory=list)
    irregularities: List[str] = field(default_factory=list)
    structure_confidence: float = 1.0
    section_labels: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.n_rows <= 0 or self.n_cols <= 0:
            raise ValueError("n_rows and n_cols must be positive")
        if any(c.row_span <= 0 or c.col_span <= 0 for c in self.cells):
            raise ValueError("Cell row_span and col_span must be positive")


CellValue = Optional[str]


@dataclass
class ColumnSpec:
    """Specification for a single output column."""

    name: str
    level: int = 0


@dataclass
class TableDataFrameSpec:
    """Dataframe-oriented representation of a table."""

    rows: List[List[CellValue]]
    columns: List[ColumnSpec]
    table_metadata_id: str


TableStatus = Literal["success", "detection_failed", "extraction_failed"]


@dataclass
class TableMetadata:
    """Metadata describing how a dataframe was derived from a TableGrid."""

    table_id: str
    page_index: int
    region: TableRegion
    grid_shape: tuple[int, int]
    status: TableStatus = "success"
    error_message: Optional[str] = None
    cell_count: int = 0
    cells_with_text: int = 0
    average_confidence: float = 0.0
    extraction_duration_ms: float = 0.0
    structure_confidence: float = 1.0
    irregularities: List[str] = field(default_factory=list)
    section_labels: Optional[List[str]] = None
    
    # Position verification metrics (for LLM extraction)
    consensus_confidence: Optional[float] = None  # Agreement across LLM attempts (0.0-1.0)
    position_confidence: Optional[float] = None   # Spatial verification vs OCR (0.0-1.0)
    cell_confidences: Optional[List[List[float]]] = None  # Per-cell confidence matrix [row][col]
    mismatched_cells: Optional[List[tuple[int, int]]] = None  # List of (row, col) with position issues


@dataclass
class RunStats:
    """Aggregate statistics for a pipeline run."""

    run_id: str = ""  # Unique identifier for this run
    pages_processed: int = 0
    tables_detected: int = 0
    tables_extracted: int = 0
    pages_skipped: int = 0
    tables_failed: int = 0
    ocr_calls: int = 0
    llm_fallback_calls: int = 0
    total_cells_extracted: int = 0
    average_ocr_confidence: float = 0.0
    llm_fallback_count: int = 0
    total_duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    worker_type: str = "sequential"
    max_workers_used: int = 1
    queue_high_water_mark: int = 0
    work_units_scheduled: int = 0
    work_units_completed: int = 0
    average_page_duration_ms: float = 0.0
    max_page_duration_ms: float = 0.0
    min_page_duration_ms: float = 0.0
    worker_utilization: float = 0.0
    abort_reason: Optional[str] = None
    # Cost tracking (LLM usage)
    llm_calls_primary: int = 0  # Calls to primary model (e.g., gemini-2.5-pro)
    llm_calls_escalation: int = 0  # Calls to escalation model (e.g., gemini-3.0-pro)
    llm_tokens_input: int = 0  # Total input tokens used
    llm_tokens_output: int = 0  # Total output tokens used
    estimated_cost_usd: float = 0.0  # Estimated cost in USD
    models_used: List[str] = field(default_factory=list)  # List of unique models used


@dataclass
class ExtractionResult:
    """Top-level result object for a pipeline execution.

    Contains all extracted tables, their metadata, and execution statistics.
    This is the primary return value from PipelineRunner.extract_tables().

    Attributes:
        tables: List of extracted tables as TableDataFrameSpec objects.
            Each table is ready for conversion to pandas DataFrame or similar.
        metadata: List of TableMetadata objects corresponding to each table.
            Provides extraction details, metrics, and status information.
        run_stats: RunStats object containing aggregate statistics for the
            entire pipeline execution (pages processed, tables detected, etc.).
        run_manifest: Optional RunManifest containing reproducibility metadata
            (git commit, config digest, component versions, etc.).

    Example:
        >>> result = runner.extract_tables("document.pdf")
        >>> print(f"Extracted {len(result.tables)} tables")
        >>> print(f"Pages processed: {result.run_stats.pages_processed}")
        >>> for table, meta in zip(result.tables, result.metadata):
        ...     if meta.status == "success":
        ...         print(f"Table {meta.table_id}: {len(table.rows)} rows")
    """

    tables: List[TableDataFrameSpec] = field(default_factory=list)
    metadata: List[TableMetadata] = field(default_factory=list)
    run_stats: RunStats = field(default_factory=RunStats)
    run_manifest: Optional[Any] = None  # RunManifest, using Any to avoid circular import

    def add_table(
        self,
        table_spec: TableDataFrameSpec,
        table_metadata: TableMetadata,
    ) -> None:
        self.tables.append(table_spec)
        self.metadata.append(table_metadata)

    @property
    def table_count(self) -> int:
        return len(self.tables)


