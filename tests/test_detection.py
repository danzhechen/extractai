from PIL import Image, ImageDraw

from pdf_reader.detection import GridStructureDetector, TableRegionDetector
from pdf_reader.detection.line_detection import LineDetectionConfig
from pdf_reader.models import BoundingBox, TableRegion


def test_table_region_detector_returns_full_page_region():
    # Create a synthetic page image
    width, height = 400, 200
    image = Image.new("RGB", (width, height), color="white")

    detector = TableRegionDetector()
    regions = detector.detect(image, page_index=2)

    assert len(regions) == 1
    region = regions[0]

    assert region.page_index == 2
    assert region.bbox.x0 == 0.0
    assert region.bbox.y0 == 0.0
    assert region.bbox.x1 == float(width)
    assert region.bbox.y1 == float(height)
    assert region.confidence == 1.0


def test_grid_structure_detector_builds_expected_grid():
    bbox = BoundingBox(x0=0.0, y0=0.0, x1=100.0, y1=50.0)
    region = TableRegion(page_index=0, bbox=bbox, confidence=1.0)

    detector = GridStructureDetector()
    grid = detector.build_grid(region, n_rows=2, n_cols=3, table_id="simple-table")

    assert grid.table_id == "simple-table"
    assert grid.page_index == 0
    assert grid.n_rows == 2
    assert grid.n_cols == 3

    # Expect 2 x 3 = 6 cells
    assert len(grid.cells) == 6

    # Check indices and spans
    for cell in grid.cells:
        assert 0 <= cell.row_index < grid.n_rows
        assert 0 <= cell.col_index < grid.n_cols
        assert cell.row_span == 1
        assert cell.col_span == 1
        assert cell.bbox is not None
        assert cell.bbox.x1 > cell.bbox.x0
        assert cell.bbox.y1 > cell.bbox.y0


def create_image_with_table(width: int = 400, height: int = 300, n_rows: int = 3, n_cols: int = 4) -> Image.Image:
    """Create a synthetic image with a table grid."""
    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)
    
    # Draw horizontal lines
    row_height = height / (n_rows - 1) if n_rows > 1 else height
    for i in range(n_rows):
        y = int(i * row_height)
        draw.rectangle([(0, y), (width, y + 2)], fill="black")
    
    # Draw vertical lines
    col_width = width / (n_cols - 1) if n_cols > 1 else width
    for i in range(n_cols):
        x = int(i * col_width)
        draw.rectangle([(x, 0), (x + 2, height)], fill="black")
    
    return image


def test_grid_structure_detector_with_line_detection():
    """Test that GridStructureDetector can use line detection when page_image is provided."""
    # Create an image with clear table lines
    image = create_image_with_table(width=400, height=300, n_rows=3, n_cols=4)
    bbox = BoundingBox(x0=0.0, y0=0.0, x1=400.0, y1=300.0)
    region = TableRegion(page_index=0, bbox=bbox, confidence=1.0)
    
    config = LineDetectionConfig(enable_line_detection=True, min_line_length=30)
    detector = GridStructureDetector(line_detection_config=config)
    
    # Build grid with line detection
    grid = detector.build_grid(
        region=region,
        n_rows=2,  # Fallback values
        n_cols=3,   # Fallback values
        table_id="line-detected-table",
        page_image=image,
    )
    
    assert grid.table_id == "line-detected-table"
    assert grid.page_index == 0
    # Grid dimensions should be determined by detected lines (3 rows, 4 cols from the image)
    # or fall back to provided values if detection fails
    assert grid.n_rows > 0
    assert grid.n_cols > 0
    assert len(grid.cells) == grid.n_rows * grid.n_cols
    
    # Check that cells have valid bounding boxes
    for cell in grid.cells:
        assert cell.bbox is not None
        assert cell.bbox.x1 > cell.bbox.x0
        assert cell.bbox.y1 > cell.bbox.y0
        assert 0 <= cell.row_index < grid.n_rows
        assert 0 <= cell.col_index < grid.n_cols


def test_grid_structure_detector_fallback_to_even_division():
    """Test that GridStructureDetector falls back to even division when line detection fails."""
    # Create a plain image with no lines
    image = Image.new("RGB", (400, 300), color="white")
    bbox = BoundingBox(x0=0.0, y0=0.0, x1=400.0, y1=300.0)
    region = TableRegion(page_index=0, bbox=bbox, confidence=1.0)
    
    config = LineDetectionConfig(enable_line_detection=True, min_line_length=30)
    detector = GridStructureDetector(line_detection_config=config)
    
    # Build grid - should fall back to even division since no lines detected
    grid = detector.build_grid(
        region=region,
        n_rows=2,
        n_cols=3,
        table_id="fallback-table",
        page_image=image,
    )
    
    assert grid.table_id == "fallback-table"
    assert grid.n_rows == 2
    assert grid.n_cols == 3
    assert len(grid.cells) == 6
    
    # Check that cells are evenly divided
    cell_width = (bbox.x1 - bbox.x0) / 3
    cell_height = (bbox.y1 - bbox.y0) / 2
    
    for cell in grid.cells:
        expected_x0 = bbox.x0 + cell.col_index * cell_width
        expected_y0 = bbox.y0 + cell.row_index * cell_height
        # Allow small floating point differences
        assert abs(cell.bbox.x0 - expected_x0) < 0.1
        assert abs(cell.bbox.y0 - expected_y0) < 0.1


def test_grid_structure_detector_line_detection_disabled():
    """Test that GridStructureDetector uses even division when line detection is disabled."""
    # Create an image with lines, but disable line detection
    image = create_image_with_table(width=400, height=300, n_rows=3, n_cols=4)
    bbox = BoundingBox(x0=0.0, y0=0.0, x1=400.0, y1=300.0)
    region = TableRegion(page_index=0, bbox=bbox, confidence=1.0)
    
    config = LineDetectionConfig(enable_line_detection=False)
    detector = GridStructureDetector(line_detection_config=config)
    
    # Build grid - should use even division since line detection is disabled
    grid = detector.build_grid(
        region=region,
        n_rows=2,
        n_cols=3,
        table_id="even-division-table",
        page_image=image,
    )
    
    assert grid.table_id == "even-division-table"
    assert grid.n_rows == 2
    assert grid.n_cols == 3
    assert len(grid.cells) == 6


def test_grid_structure_detector_backward_compatibility():
    """Test that existing code without page_image still works (backward compatibility)."""
    bbox = BoundingBox(x0=0.0, y0=0.0, x1=100.0, y1=50.0)
    region = TableRegion(page_index=0, bbox=bbox, confidence=1.0)
    
    # Detector with line detection enabled
    config = LineDetectionConfig(enable_line_detection=True)
    detector = GridStructureDetector(line_detection_config=config)
    
    # Build grid without page_image - should fall back to even division
    grid = detector.build_grid(region, n_rows=2, n_cols=3, table_id="backward-compat")
    
    assert grid.table_id == "backward-compat"
    assert grid.n_rows == 2
    assert grid.n_cols == 3
    assert len(grid.cells) == 6


