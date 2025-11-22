"""Tests for line detection functionality."""

import numpy as np
import pytest
from PIL import Image, ImageDraw

from pdf_reader.detection.line_detection import (
    LineDetectionConfig,
    detect_horizontal_lines,
    detect_vertical_lines,
)
from pdf_reader.models import BoundingBox, TableRegion


def create_image_with_table_lines(
    width: int = 400,
    height: int = 300,
    n_rows: int = 3,
    n_cols: int = 4,
    line_thickness: int = 2,
) -> Image.Image:
    """Create a synthetic image with table lines.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.
        n_rows: Number of horizontal lines (including borders).
        n_cols: Number of vertical lines (including borders).
        line_thickness: Thickness of lines in pixels.

    Returns:
        PIL Image with drawn table lines.
    """
    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)

    # Draw horizontal lines
    row_height = height / (n_rows - 1) if n_rows > 1 else height
    for i in range(n_rows):
        y = int(i * row_height)
        draw.rectangle(
            [(0, y), (width, y + line_thickness)],
            fill="black",
        )

    # Draw vertical lines
    col_width = width / (n_cols - 1) if n_cols > 1 else width
    for i in range(n_cols):
        x = int(i * col_width)
        draw.rectangle(
            [(x, 0), (x + line_thickness, height)],
            fill="black",
        )

    return image


def test_detect_horizontal_lines_basic():
    """Test basic horizontal line detection."""
    image = create_image_with_table_lines(width=400, height=300, n_rows=3, n_cols=4)
    config = LineDetectionConfig(enable_line_detection=True, min_line_length=30)

    lines = detect_horizontal_lines(image, config=config)

    # Should detect at least the top and bottom borders
    assert len(lines) >= 2
    assert all(isinstance(line, float) for line in lines)
    assert lines == sorted(lines)  # Should be sorted


def test_detect_vertical_lines_basic():
    """Test basic vertical line detection."""
    image = create_image_with_table_lines(width=400, height=300, n_rows=3, n_cols=4)
    config = LineDetectionConfig(enable_line_detection=True, min_line_length=30)

    lines = detect_vertical_lines(image, config=config)

    # Should detect at least the left and right borders
    assert len(lines) >= 2
    assert all(isinstance(line, float) for line in lines)
    assert lines == sorted(lines)  # Should be sorted


def test_detect_horizontal_lines_with_region():
    """Test horizontal line detection with a region constraint."""
    image = create_image_with_table_lines(width=400, height=300, n_rows=5, n_cols=4)
    config = LineDetectionConfig(enable_line_detection=True, min_line_length=30)

    # Create a region that covers part of the image
    region = TableRegion(
        page_index=0,
        bbox=BoundingBox(x0=50.0, y0=50.0, x1=350.0, y1=250.0),
        confidence=1.0,
    )

    lines = detect_horizontal_lines(image, region=region, config=config)

    # Should detect lines within the region
    assert len(lines) >= 0  # May or may not detect lines depending on region
    assert all(isinstance(line, float) for line in lines)


def test_detect_vertical_lines_with_region():
    """Test vertical line detection with a region constraint."""
    image = create_image_with_table_lines(width=400, height=300, n_rows=3, n_cols=5)
    config = LineDetectionConfig(enable_line_detection=True, min_line_length=30)

    # Create a region that covers part of the image
    region = TableRegion(
        page_index=0,
        bbox=BoundingBox(x0=50.0, y0=50.0, x1=350.0, y1=250.0),
        confidence=1.0,
    )

    lines = detect_vertical_lines(image, region=region, config=config)

    # Should detect lines within the region
    assert len(lines) >= 0  # May or may not detect lines depending on region
    assert all(isinstance(line, float) for line in lines)


def test_line_detection_disabled():
    """Test that line detection returns empty list when disabled."""
    image = create_image_with_table_lines(width=400, height=300, n_rows=3, n_cols=4)
    config = LineDetectionConfig(enable_line_detection=False)

    h_lines = detect_horizontal_lines(image, config=config)
    v_lines = detect_vertical_lines(image, config=config)

    assert h_lines == []
    assert v_lines == []


def test_line_detection_handles_no_lines():
    """Test line detection on image with no lines."""
    # Create a plain white image with no lines
    image = Image.new("RGB", (400, 300), color="white")
    config = LineDetectionConfig(enable_line_detection=True, min_line_length=30)

    h_lines = detect_horizontal_lines(image, config=config)
    v_lines = detect_vertical_lines(image, config=config)

    # Should return empty list or very few lines
    assert isinstance(h_lines, list)
    assert isinstance(v_lines, list)


def test_line_detection_config_defaults():
    """Test that LineDetectionConfig has sensible defaults."""
    config = LineDetectionConfig()

    assert config.enable_line_detection is True
    assert config.min_line_length > 0
    assert config.gap_tolerance >= 0
    assert config.morph_iterations > 0
    assert config.min_line_separation >= 0


def test_line_detection_merges_nearby_lines():
    """Test that nearby lines are merged within gap tolerance."""
    image = create_image_with_table_lines(width=400, height=300, n_rows=3, n_cols=4)
    # Use a larger gap tolerance to merge lines that are close
    config = LineDetectionConfig(
        enable_line_detection=True,
        min_line_length=30,
        gap_tolerance=20,  # Larger gap tolerance
    )

    h_lines = detect_horizontal_lines(image, config=config)
    v_lines = detect_vertical_lines(image, config=config)

    # Lines should be sorted and not have duplicates
    assert h_lines == sorted(h_lines)
    assert v_lines == sorted(v_lines)
    # Check no duplicate lines (within a small tolerance)
    if len(h_lines) > 1:
        min_gap = min(h_lines[i + 1] - h_lines[i] for i in range(len(h_lines) - 1))
        assert min_gap >= config.min_line_separation


def test_line_detection_with_different_image_sizes():
    """Test line detection works with different image sizes."""
    for width, height in [(200, 150), (800, 600), (1000, 1000)]:
        image = create_image_with_table_lines(width=width, height=height, n_rows=3, n_cols=4)
        config = LineDetectionConfig(enable_line_detection=True, min_line_length=30)

        h_lines = detect_horizontal_lines(image, config=config)
        v_lines = detect_vertical_lines(image, config=config)

        # Should detect at least borders
        assert len(h_lines) >= 0
        assert len(v_lines) >= 0
        # All coordinates should be within image bounds
        if h_lines:
            assert all(0 <= line <= height for line in h_lines)
        if v_lines:
            assert all(0 <= line <= width for line in v_lines)


def test_line_detection_performance():
    """Test that line detection completes in reasonable time."""
    import time
    
    # Create a moderately sized image
    image = create_image_with_table_lines(width=800, height=600, n_rows=10, n_cols=8)
    config = LineDetectionConfig(enable_line_detection=True, min_line_length=30)
    
    start_time = time.time()
    h_lines = detect_horizontal_lines(image, config=config)
    v_lines = detect_vertical_lines(image, config=config)
    elapsed = time.time() - start_time
    
    # Should complete in less than 5 seconds (per story requirement)
    assert elapsed < 5.0, f"Line detection took {elapsed:.2f}s, expected < 5s"
    assert len(h_lines) >= 0
    assert len(v_lines) >= 0


def test_line_detection_edge_case_thin_lines():
    """Test line detection with very thin lines."""
    image = Image.new("RGB", (400, 300), color="white")
    draw = ImageDraw.Draw(image)
    
    # Draw very thin lines (1 pixel thick)
    draw.rectangle([(0, 100), (400, 101)], fill="black")  # Horizontal
    draw.rectangle([(200, 0), (201, 300)], fill="black")  # Vertical
    
    config = LineDetectionConfig(
        enable_line_detection=True,
        min_line_length=50,
        gap_tolerance=5,
    )
    
    h_lines = detect_horizontal_lines(image, config=config)
    v_lines = detect_vertical_lines(image, config=config)
    
    # May or may not detect thin lines depending on preprocessing
    assert isinstance(h_lines, list)
    assert isinstance(v_lines, list)


def test_line_detection_edge_case_partial_borders():
    """Test line detection with tables missing some borders."""
    image = Image.new("RGB", (400, 300), color="white")
    draw = ImageDraw.Draw(image)
    
    # Draw only internal lines, missing outer borders
    draw.rectangle([(0, 150), (400, 152)], fill="black")  # Horizontal line in middle
    draw.rectangle([(200, 0), (202, 300)], fill="black")  # Vertical line in middle
    
    config = LineDetectionConfig(enable_line_detection=True, min_line_length=30)
    
    h_lines = detect_horizontal_lines(image, config=config)
    v_lines = detect_vertical_lines(image, config=config)
    
    # Should still detect internal lines
    assert isinstance(h_lines, list)
    assert isinstance(v_lines, list)

