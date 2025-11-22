"""Detection module for table region and grid structure detection."""

# Import from parent detection.py file
import sys
from pathlib import Path
_detection_file = Path(__file__).parent.parent / "detection.py"
if _detection_file.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("pdf_reader.detection_module", _detection_file)
    detection_module = importlib.util.module_from_spec(spec)
    sys.modules["pdf_reader.detection_module"] = detection_module
    spec.loader.exec_module(detection_module)
    GridStructureDetector = detection_module.GridStructureDetector
    TableRegionDetector = detection_module.TableRegionDetector
else:
    # Fallback if detection.py doesn't exist
    raise ImportError("detection.py file not found")
from .line_detection import (
    LineDetectionConfig,
    detect_horizontal_lines,
    detect_vertical_lines,
)

__all__ = [
    "GridStructureDetector",
    "TableRegionDetector",
    "LineDetectionConfig",
    "detect_horizontal_lines",
    "detect_vertical_lines",
]

