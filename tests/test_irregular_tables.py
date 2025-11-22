from pathlib import Path

from PIL import Image, ImageDraw

from pdf_reader.detection import GridStructureDetector, TableRegionDetector
from pdf_reader.detection.line_detection import LineDetectionConfig
from pdf_reader.models import BoundingBox, TableRegion


def _create_synthetic_ragged_image(width: int = 400, height: int = 220) -> Image.Image:
    """Create a synthetic image with ragged table text blocks."""

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    # Row 1 - three columns
    draw.rectangle([20, 20, 100, 50], fill="black")
    draw.rectangle([140, 20, 220, 50], fill="black")
    draw.rectangle([260, 20, 360, 50], fill="black")

    # Row 2 - missing middle column
    draw.rectangle([20, 90, 120, 120], fill="black")
    draw.rectangle([260, 90, 360, 120], fill="black")

    # Row 3 - two columns stacked (multi-panel simulation)
    draw.rectangle([20, 160, 150, 190], fill="black")
    draw.rectangle([200, 160, 360, 190], fill="black")

    return image


def test_table_region_detector_detects_multi_panels():
    image = _create_synthetic_ragged_image()
    detector = TableRegionDetector(enable_multi_panel_detection=True)
    regions = detector.detect(image, page_index=0)

    assert len(regions) >= 2
    assert all(isinstance(region, TableRegion) for region in regions)
    assert any(region.section_label for region in regions)


def test_grid_structure_detector_handles_ragged_columns():
    image = _create_synthetic_ragged_image()
    region = TableRegion(
        page_index=0,
        bbox=BoundingBox(x0=0.0, y0=0.0, x1=float(image.width), y1=float(image.height)),
        confidence=1.0,
    )

    detector = GridStructureDetector(
        line_detection_config=LineDetectionConfig(enable_line_detection=False),
        enable_irregular_detection=True,
        ragged_mode="ragged",
    )

    grid = detector.build_grid(
        region=region,
        n_rows=2,
        n_cols=3,
        table_id="t_irregular",
        page_image=image,
    )

    filler_cells = [cell for cell in grid.cells if cell.is_filler]

    assert grid.n_cols >= 3
    assert len(filler_cells) > 0
    assert "ragged_columns" in grid.irregularities
    assert 0.0 < grid.structure_confidence < 1.0

