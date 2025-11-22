"""Position verification module for validating extracted table values against OCR tokens.

This module implements spatial validation by comparing LLM-extracted table values
with OCR tokens at the same positions to detect:
- Value mismatches (wrong number extracted)
- Position mismatches (correct number but wrong cell)
- Character confusion errors (0/O, 1/l, 5/S, 8/B, etc.)
"""

import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
from difflib import SequenceMatcher

from .models import TableDataFrameSpec, BoundingBox, Cell


logger = logging.getLogger(__name__)


# Character similarity map for common OCR confusions
CHAR_SIMILARITY_MAP = {
    '0': ['O', 'o', 'D'],
    'O': ['0', 'o', 'D'],
    'o': ['0', 'O'],
    '1': ['l', 'I', '|', 'i'],
    'l': ['1', 'I', '|', 'i'],
    'I': ['1', 'l', '|', 'i'],
    '5': ['S', 's'],
    'S': ['5', 's'],
    's': ['5', 'S'],
    '8': ['B', '&'],
    'B': ['8'],
    '2': ['Z', 'z'],
    'Z': ['2'],
    '6': ['G', 'b'],
    'G': ['6'],
    '9': ['g', 'q'],
    'g': ['9', 'q'],
    'q': ['9', 'g'],
}


@dataclass
class OCRToken:
    """Represents a single OCR token with position and confidence."""
    text: str
    bbox: BoundingBox  # Bounding box in page coordinates
    confidence: float
    

@dataclass
class CellMatch:
    """Result of matching an extracted cell value with OCR tokens."""
    cell_row: int
    cell_col: int
    extracted_value: str
    ocr_value: str
    position_confidence: float  # 0.0-1.0
    is_exact_match: bool
    is_fuzzy_match: bool
    is_position_match: bool
    similarity_score: float
    matched_tokens: List[OCRToken]
    

class PositionVerifier:
    """Verifies table extraction accuracy by comparing with OCR tokens."""
    
    def __init__(
        self, 
        ocr_confidence_threshold: float = 0.7,
        fuzzy_match_threshold: float = 0.8,
        position_tolerance: float = 0.1  # 10% bbox overlap tolerance
    ):
        """Initialize position verifier.
        
        Args:
            ocr_confidence_threshold: Minimum OCR confidence to trust (0.0-1.0)
            fuzzy_match_threshold: Minimum similarity for fuzzy match (0.0-1.0)
            position_tolerance: Spatial overlap tolerance for position matching
        """
        self.ocr_confidence_threshold = ocr_confidence_threshold
        self.fuzzy_match_threshold = fuzzy_match_threshold
        self.position_tolerance = position_tolerance
    
    def extract_ocr_tokens(self, page_image, page_obj=None) -> List[OCRToken]:
        """Extract OCR tokens with positions from a page image or pdfplumber page.
        
        Args:
            page_image: PIL Image of the page (not currently used, kept for API compatibility)
            page_obj: pdfplumber page object (if available, provides better OCR)
            
        Returns:
            List of OCRToken objects with text, bbox, and confidence
            
        Note:
            This method prioritizes pdfplumber's character extraction (which includes
            position data) over image-based OCR. If pdfplumber page is not available,
            it returns empty list (pytesseract integration could be added in future).
        """
        tokens = []
        
        if page_obj is not None:
            try:
                # Use pdfplumber's character extraction
                # pdfplumber extracts characters with exact positions from PDF
                chars = page_obj.chars
                
                # Group characters into words/tokens
                # For simplicity, we'll treat each character as a token
                # A more sophisticated approach would group into words
                for char in chars:
                    # pdfplumber uses (x0, top, x1, bottom) format
                    # BoundingBox uses (x0, y0, x1, y1) format
                    bbox = BoundingBox(
                        x0=float(char['x0']),
                        y0=float(char['top']),
                        x1=float(char['x1']),
                        y1=float(char['bottom'])
                    )
                    
                    # pdfplumber doesn't provide OCR confidence (it's native PDF text)
                    # so we use 1.0 for native PDF text (very reliable)
                    confidence = 1.0
                    
                    tokens.append(OCRToken(
                        text=char['text'],
                        bbox=bbox,
                        confidence=confidence
                    ))
                
                logger.debug(f"Extracted {len(tokens)} character tokens from pdfplumber")
                
            except Exception as e:
                logger.warning(f"Failed to extract OCR tokens from pdfplumber: {e}")
                return []
        else:
            # Fallback: Could use pytesseract on page_image here
            # For now, return empty list
            logger.debug("No pdfplumber page available, skipping OCR token extraction")
            return []
        
        return tokens
        
    def verify_table(
        self,
        table_spec: TableDataFrameSpec,
        table_bbox: BoundingBox,
        ocr_tokens: List[OCRToken]
    ) -> Tuple[List[List[float]], List[Tuple[int, int]], float]:
        """Verify extracted table against OCR tokens.
        
        Args:
            table_spec: Extracted table specification
            table_bbox: Estimated bounding box of the table
            ocr_tokens: OCR tokens from the page
            
        Returns:
            Tuple of:
            - cell_confidences: Per-cell confidence matrix (0.0-1.0)
            - mismatched_cells: List of (row_idx, col_idx) with low confidence
            - overall_confidence: Overall table position confidence
        """
        n_rows = len(table_spec.rows)
        n_cols = len(table_spec.columns)
        
        # Initialize confidence matrix
        cell_confidences = [[0.0 for _ in range(n_cols)] for _ in range(n_rows)]
        mismatched_cells = []
        
        # Estimate cell bounding boxes based on table bbox and grid structure
        cell_bboxes = self._estimate_cell_bboxes(table_bbox, n_rows, n_cols)
        
        # Match each cell with OCR tokens
        all_matches = []
        for r_idx, row in enumerate(table_spec.rows):
            for c_idx, cell_value in enumerate(row):
                cell_bbox = cell_bboxes[r_idx][c_idx]
                
                # Find OCR tokens within this cell's bbox
                tokens_in_cell = self._find_tokens_in_bbox(ocr_tokens, cell_bbox)
                
                # Match cell value with tokens
                match = self._match_cell_value(
                    cell_value=str(cell_value),
                    cell_row=r_idx,
                    cell_col=c_idx,
                    cell_bbox=cell_bbox,
                    tokens=tokens_in_cell
                )
                
                all_matches.append(match)
                cell_confidences[r_idx][c_idx] = match.position_confidence
                
                # Flag low-confidence cells
                if match.position_confidence < 0.7:
                    mismatched_cells.append((r_idx, c_idx))
                    
                    # Log warning for mismatched cells
                    logger.warning(
                        f"Cell ({r_idx},{c_idx}) mismatch: "
                        f"extracted='{match.extracted_value}' vs OCR='{match.ocr_value}' "
                        f"(confidence={match.position_confidence:.2f})"
                    )
        
        # Calculate overall confidence
        total_confidence = sum(sum(row) for row in cell_confidences)
        total_cells = n_rows * n_cols
        overall_confidence = total_confidence / total_cells if total_cells > 0 else 0.0
        
        logger.info(
            f"Position verification complete: "
            f"overall_confidence={overall_confidence:.2f}, "
            f"mismatched_cells={len(mismatched_cells)}/{total_cells}"
        )
        
        return cell_confidences, mismatched_cells, overall_confidence
    
    def _estimate_cell_bboxes(
        self,
        table_bbox: BoundingBox,
        n_rows: int,
        n_cols: int
    ) -> List[List[BoundingBox]]:
        """Estimate cell bounding boxes by dividing table bbox into grid."""
        cell_width = (table_bbox.x1 - table_bbox.x0) / n_cols
        cell_height = (table_bbox.y1 - table_bbox.y0) / n_rows
        
        cell_bboxes = []
        for r_idx in range(n_rows):
            row_bboxes = []
            for c_idx in range(n_cols):
                x0 = table_bbox.x0 + c_idx * cell_width
                y0 = table_bbox.y0 + r_idx * cell_height
                x1 = x0 + cell_width
                y1 = y0 + cell_height
                
                row_bboxes.append(BoundingBox(x0, y0, x1, y1))
            
            cell_bboxes.append(row_bboxes)
        
        return cell_bboxes
    
    def _find_tokens_in_bbox(
        self,
        tokens: List[OCRToken],
        bbox: BoundingBox
    ) -> List[OCRToken]:
        """Find all OCR tokens within a bounding box."""
        matching_tokens = []
        
        for token in tokens:
            # Check if token bbox overlaps with cell bbox
            overlap = self._calculate_bbox_overlap(token.bbox, bbox)
            if overlap > self.position_tolerance:
                matching_tokens.append(token)
        
        return matching_tokens
    
    def _calculate_bbox_overlap(
        self,
        bbox1: BoundingBox,
        bbox2: BoundingBox
    ) -> float:
        """Calculate overlap ratio between two bounding boxes (IoU)."""
        # Calculate intersection
        x_left = max(bbox1.x0, bbox2.x0)
        y_top = max(bbox1.y0, bbox2.y0)
        x_right = min(bbox1.x1, bbox2.x1)
        y_bottom = min(bbox1.y1, bbox2.y1)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0  # No overlap
        
        intersection = (x_right - x_left) * (y_bottom - y_top)
        
        # Calculate union
        area1 = (bbox1.x1 - bbox1.x0) * (bbox1.y1 - bbox1.y0)
        area2 = (bbox2.x1 - bbox2.x0) * (bbox2.y1 - bbox2.y0)
        union = area1 + area2 - intersection
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _match_cell_value(
        self,
        cell_value: str,
        cell_row: int,
        cell_col: int,
        cell_bbox: BoundingBox,
        tokens: List[OCRToken]
    ) -> CellMatch:
        """Match a cell value with OCR tokens at the same position."""
        # Concatenate OCR tokens into a single string
        ocr_text = " ".join(token.text for token in tokens).strip()
        cell_value = str(cell_value).strip()
        
        # Check for exact match
        is_exact_match = (cell_value == ocr_text)
        
        # Check for fuzzy match with character similarity
        is_fuzzy_match = False
        similarity_score = 0.0
        
        if not is_exact_match and cell_value and ocr_text:
            # Calculate similarity
            similarity_score = self._calculate_similarity(cell_value, ocr_text)
            is_fuzzy_match = (similarity_score >= self.fuzzy_match_threshold)
        
        # Determine position confidence
        if not tokens:
            # No OCR tokens found in this cell - low confidence
            position_confidence = 0.3
            is_position_match = False
        elif is_exact_match:
            # Exact match - high confidence
            position_confidence = 1.0
            is_position_match = True
        elif is_fuzzy_match:
            # Fuzzy match - medium-high confidence based on similarity
            position_confidence = similarity_score
            is_position_match = True
        else:
            # No match - low confidence
            # But not zero - maybe OCR failed
            position_confidence = 0.4
            is_position_match = False
        
        # Adjust confidence based on OCR token confidence
        if tokens:
            avg_ocr_conf = sum(t.confidence for t in tokens) / len(tokens)
            if avg_ocr_conf < self.ocr_confidence_threshold:
                # Low OCR confidence - trust LLM more
                position_confidence = max(position_confidence, 0.6)
        
        return CellMatch(
            cell_row=cell_row,
            cell_col=cell_col,
            extracted_value=cell_value,
            ocr_value=ocr_text,
            position_confidence=position_confidence,
            is_exact_match=is_exact_match,
            is_fuzzy_match=is_fuzzy_match,
            is_position_match=is_position_match,
            similarity_score=similarity_score,
            matched_tokens=tokens
        )
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings with character confusion handling.
        
        Uses a combination of:
        1. Sequence matching (edit distance)
        2. Character similarity map for common OCR confusions
        """
        if not str1 or not str2:
            return 0.0
        
        # Normalize strings (remove whitespace, lowercase)
        s1 = str1.replace(" ", "").lower()
        s2 = str2.replace(" ", "").lower()
        
        if s1 == s2:
            return 1.0
        
        # Calculate base similarity using SequenceMatcher
        base_similarity = SequenceMatcher(None, s1, s2).ratio()
        
        # Boost similarity if differences are only in confusable characters
        if len(s1) == len(s2):
            confusable_mismatches = 0
            total_mismatches = 0
            
            for c1, c2 in zip(s1, s2):
                if c1 != c2:
                    total_mismatches += 1
                    # Check if this is a known confusable pair
                    if self._is_confusable_pair(c1, c2):
                        confusable_mismatches += 1
            
            if total_mismatches > 0:
                confusable_ratio = confusable_mismatches / total_mismatches
                # Boost base similarity by confusable ratio
                boosted_similarity = base_similarity + (1.0 - base_similarity) * confusable_ratio * 0.5
                return min(boosted_similarity, 1.0)
        
        return base_similarity
    
    def _is_confusable_pair(self, char1: str, char2: str) -> bool:
        """Check if two characters are commonly confused in OCR."""
        # Check both original and uppercase versions
        for c1, c2 in [(char1, char2), (char1.upper(), char2.upper())]:
            # Check if char1 can be confused with char2
            if c1 in CHAR_SIMILARITY_MAP:
                if c2 in CHAR_SIMILARITY_MAP[c1]:
                    return True
            
            # Check if char2 can be confused with char1
            if c2 in CHAR_SIMILARITY_MAP:
                if c1 in CHAR_SIMILARITY_MAP[c2]:
                    return True
        
        return False
