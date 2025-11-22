"""
Top-level package for the pdf-reading-project extraction library.

This module exposes the core data models so callers can import them as:

    from pdf_reader.models import TableGrid, Cell
"""

from .models import (  # noqa: F401
    BoundingBox,
    Cell,
    ExtractionResult,
    PdfDocument,
    PdfPage,
    RunStats,
    TableDataFrameSpec,
    TableGrid,
    TableMetadata,
    TableRegion,
)
from .ingestion import PdfIngestionError, PdfIngestionService, PageImage  # noqa: F401
# Import from detection.py file directly (not detection/ package)
import sys
from pathlib import Path
_detection_file = Path(__file__).parent / "detection.py"
if _detection_file.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("pdf_reader.detection_module", _detection_file)
    detection_module = importlib.util.module_from_spec(spec)
    sys.modules["pdf_reader.detection_module"] = detection_module
    spec.loader.exec_module(detection_module)
    GridStructureDetector = detection_module.GridStructureDetector  # noqa: F401
    TableRegionDetector = detection_module.TableRegionDetector  # noqa: F401
else:
    from .detection import (  # noqa: F401
        GridStructureDetector,
        TableRegionDetector,
    )
from .extraction import CellTextExtractor, TableAssembler  # noqa: F401
from .pipeline import PipelineConfig, PipelineRunner  # noqa: F401

__all__ = [
    "BoundingBox",
    "Cell",
    "ExtractionResult",
    "PdfDocument",
    "PdfPage",
    "RunStats",
    "TableDataFrameSpec",
    "TableGrid",
    "TableMetadata",
    "TableRegion",
    "PdfIngestionError",
    "PdfIngestionService",
    "PageImage",
    "TableRegionDetector",
    "GridStructureDetector",
    "CellTextExtractor",
    "TableAssembler",
    "PipelineConfig",
    "PipelineRunner",
]


