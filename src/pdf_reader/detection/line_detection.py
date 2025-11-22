"""Line detection helpers for identifying table borders and grid lines."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from ..models import BoundingBox, TableRegion

PageImage = Image.Image
logger = logging.getLogger(__name__)


@dataclass
class LineDetectionConfig:
    """Configuration for geometric line detection."""

    enable_line_detection: bool = True
    min_line_length: int = 40
    gap_tolerance: int = 5
    horizontal_kernel_size: Tuple[int, int] = (25, 1)
    vertical_kernel_size: Tuple[int, int] = (1, 25)
    morph_iterations: int = 2
    min_line_separation: int = 5


def _pil_to_cv2(image: PageImage) -> np.ndarray:
    """Convert PIL Image to OpenCV format (numpy array).

    Args:
        image: PIL Image (RGB mode).

    Returns:
        OpenCV image array (BGR format).
    """
    # Convert PIL RGB to numpy array, then to BGR for OpenCV
    img_array = np.array(image)
    if image.mode == "RGB":
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    elif image.mode == "L":
        # Grayscale - convert to BGR
        return cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
    else:
        # Convert to RGB first, then to BGR
        rgb_image = image.convert("RGB")
        img_array = np.array(rgb_image)
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)


def _preprocess_image(image: np.ndarray) -> np.ndarray:
    """Preprocess image for line detection.

    Converts to grayscale and applies thresholding to enhance line visibility.

    Args:
        image: OpenCV image (BGR format).

    Returns:
        Binary image (grayscale, thresholded).
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply adaptive thresholding to handle varying lighting
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    return binary


def _merge_nearby_lines(
    lines: List[float],
    gap_tolerance: float,
    min_line_separation: float,
) -> List[float]:
    """Merge nearby line coordinates and drop near-duplicates."""
    if not lines:
        return []

    sorted_lines = sorted(lines)
    merged = [sorted_lines[0]]

    for line in sorted_lines[1:]:
        # If line is within gap tolerance of the last merged line, merge them
        if line - merged[-1] <= gap_tolerance:
            # Average the positions
            merged[-1] = (merged[-1] + line) / 2.0
        else:
            merged.append(line)

    filtered = [merged[0]]
    for line in merged[1:]:
        if line - filtered[-1] >= min_line_separation:
            filtered.append(line)

    return filtered


def detect_horizontal_lines(
    image: PageImage,
    region: Optional[TableRegion] = None,
    config: Optional[LineDetectionConfig] = None,
) -> List[float]:
    """Detect horizontal lines in a page image.

    Detects horizontal table borders and grid lines using morphological operations.
    Returns y-coordinates of detected lines.

    Args:
        image: PIL Image of the page.
        region: Optional table region to restrict detection. If provided, only detects
            lines within the region and returns coordinates relative to the region.
        config: Line detection configuration. If None, uses defaults.

    Returns:
        Sorted list of pixel y-coordinates where horizontal lines were detected.
    """
    if config is None:
        config = LineDetectionConfig()

    if not config.enable_line_detection:
        return []

    # Convert PIL to OpenCV format
    cv2_image = _pil_to_cv2(image)
    height, width = cv2_image.shape[:2]

    # Extract region if provided
    if region is not None:
        bbox = region.bbox
        # Region bbox is in pixel coordinates
        x0 = int(bbox.x0)
        y0 = int(bbox.y0)
        x1 = int(bbox.x1)
        y1 = int(bbox.y1)
        # Clamp to image bounds
        x0 = max(0, min(x0, width))
        y0 = max(0, min(y0, height))
        x1 = max(0, min(x1, width))
        y1 = max(0, min(y1, height))
        roi = cv2_image[y0:y1, x0:x1]
        region_y0_px = y0
    else:
        roi = cv2_image
        region_y0_px = 0

    # Preprocess
    binary = _preprocess_image(roi)

    # Create horizontal kernel
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, config.horizontal_kernel_size
    )

    # Detect horizontal lines using morphological operations
    horizontal = cv2.erode(binary, kernel, iterations=config.morph_iterations)
    horizontal = cv2.dilate(horizontal, kernel, iterations=config.morph_iterations)

    # Find horizontal lines using HoughLinesP for more precise detection
    lines = cv2.HoughLinesP(
        horizontal,
        rho=1,
        theta=np.pi / 180,
        threshold=100,
        minLineLength=config.min_line_length,
        maxLineGap=config.gap_tolerance,
    )

    y_coords_px: List[float] = []
    if lines is not None:
        for line in lines:
            x1_line, y1_line, x2_line, y2_line = line[0]
            # For horizontal lines, y should be approximately constant
            y_avg = (y1_line + y2_line) / 2.0
            # Convert to absolute pixel coordinates
            y_abs_px = y_avg + region_y0_px
            y_coords_px.append(y_abs_px)

    # Merge nearby lines in pixel space
    merged_px = _merge_nearby_lines(
        y_coords_px, config.gap_tolerance, config.min_line_separation
    )
    return sorted(float(y_px) for y_px in merged_px)


def detect_vertical_lines(
    image: PageImage,
    region: Optional[TableRegion] = None,
    config: Optional[LineDetectionConfig] = None,
) -> List[float]:
    """Detect vertical lines in a page image.

    Detects vertical table borders and grid lines using morphological operations.
    Returns x-coordinates of detected lines.

    Args:
        image: PIL Image of the page.
        region: Optional table region to restrict detection. If provided, only detects
            lines within the region and returns coordinates relative to the region.
        config: Line detection configuration. If None, uses defaults.

    Returns:
        Sorted list of pixel x-coordinates where vertical lines were detected.
    """
    if config is None:
        config = LineDetectionConfig()

    if not config.enable_line_detection:
        return []

    # Convert PIL to OpenCV format
    cv2_image = _pil_to_cv2(image)
    height, width = cv2_image.shape[:2]

    # Extract region if provided
    if region is not None:
        bbox = region.bbox
        # Region bbox is in pixel coordinates
        x0 = int(bbox.x0)
        y0 = int(bbox.y0)
        x1 = int(bbox.x1)
        y1 = int(bbox.y1)
        # Clamp to image bounds
        x0 = max(0, min(x0, width))
        y0 = max(0, min(y0, height))
        x1 = max(0, min(x1, width))
        y1 = max(0, min(y1, height))
        roi = cv2_image[y0:y1, x0:x1]
        region_x0_px = x0
    else:
        roi = cv2_image
        region_x0_px = 0

    # Preprocess
    binary = _preprocess_image(roi)

    # Create vertical kernel
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, config.vertical_kernel_size)

    # Detect vertical lines using morphological operations
    vertical = cv2.erode(binary, kernel, iterations=config.morph_iterations)
    vertical = cv2.dilate(vertical, kernel, iterations=config.morph_iterations)

    # Find vertical lines using HoughLinesP for more precise detection
    lines = cv2.HoughLinesP(
        vertical,
        rho=1,
        theta=np.pi / 180,
        threshold=100,
        minLineLength=config.min_line_length,
        maxLineGap=config.gap_tolerance,
    )

    x_coords_px: List[float] = []
    if lines is not None:
        for line in lines:
            x1_line, y1_line, x2_line, y2_line = line[0]
            # For vertical lines, x should be approximately constant
            x_avg = (x1_line + x2_line) / 2.0
            # Convert to absolute pixel coordinates
            x_abs_px = x_avg + region_x0_px
            x_coords_px.append(x_abs_px)

    # Merge nearby lines in pixel space
    merged_px = _merge_nearby_lines(
        x_coords_px, config.gap_tolerance, config.min_line_separation
    )
    return sorted(float(x_px) for x_px in merged_px)

