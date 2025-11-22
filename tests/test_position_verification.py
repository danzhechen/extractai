"""Tests for position verification system."""

import pytest
from src.pdf_reader.position_verifier import (
    PositionVerifier,
    OCRToken,
    CHAR_SIMILARITY_MAP
)
from src.pdf_reader.models import BoundingBox, TableDataFrameSpec, ColumnSpec


class TestCharacterSimilarity:
    """Test character confusion detection."""
    
    def test_confusable_pairs(self):
        """Test that common confusable pairs are detected."""
        verifier = PositionVerifier()
        
        # Test common confusions
        assert verifier._is_confusable_pair('0', 'O')
        assert verifier._is_confusable_pair('O', '0')
        assert verifier._is_confusable_pair('1', 'l')
        assert verifier._is_confusable_pair('l', '1')
        assert verifier._is_confusable_pair('5', 'S')
        assert verifier._is_confusable_pair('8', 'B')
        
        # Test non-confusable pairs
        assert not verifier._is_confusable_pair('A', 'B')
        assert not verifier._is_confusable_pair('1', '2')
    
    def test_similarity_calculation(self):
        """Test similarity calculation with character confusion."""
        verifier = PositionVerifier(fuzzy_match_threshold=0.8)
        
        # Exact match
        assert verifier._calculate_similarity("123", "123") == 1.0
        
        # One character confusion (0/O)
        sim = verifier._calculate_similarity("1O3", "103")
        assert sim > 0.8  # Should be boosted due to confusable character
        
        # Multiple confusions (2 out of 3 chars are confusable)
        sim = verifier._calculate_similarity("1OO", "100")
        assert sim > 0.65  # Base similarity is 0.666... with boost
        
        # No confusions, just different
        sim = verifier._calculate_similarity("123", "456")
        assert sim < 0.5


class TestOCRTokenExtraction:
    """Test OCR token extraction."""
    
    def test_extract_with_no_page(self):
        """Test extraction with no pdfplumber page returns empty list."""
        verifier = PositionVerifier()
        tokens = verifier.extract_ocr_tokens(page_image=None, page_obj=None)
        assert tokens == []
    
    def test_extract_with_mock_page(self):
        """Test extraction with mock pdfplumber page."""
        verifier = PositionVerifier()
        
        # Mock pdfplumber page
        class MockPage:
            chars = [
                {'text': '1', 'x0': 10, 'top': 20, 'x1': 15, 'bottom': 25},
                {'text': '2', 'x0': 20, 'top': 20, 'x1': 25, 'bottom': 25},
                {'text': '3', 'x0': 30, 'top': 20, 'x1': 35, 'bottom': 25},
            ]
        
        tokens = verifier.extract_ocr_tokens(page_image=None, page_obj=MockPage())
        
        assert len(tokens) == 3
        assert tokens[0].text == '1'
        assert tokens[1].text == '2'
        assert tokens[2].text == '3'
        assert all(token.confidence == 1.0 for token in tokens)  # PDF text has perfect confidence


class TestPositionMatching:
    """Test position matching and verification."""
    
    def test_bbox_overlap_calculation(self):
        """Test bounding box overlap calculation (IoU)."""
        verifier = PositionVerifier()
        
        # Perfect overlap
        bbox1 = BoundingBox(0, 0, 10, 10)
        bbox2 = BoundingBox(0, 0, 10, 10)
        assert verifier._calculate_bbox_overlap(bbox1, bbox2) == 1.0
        
        # No overlap
        bbox1 = BoundingBox(0, 0, 10, 10)
        bbox2 = BoundingBox(20, 20, 30, 30)
        assert verifier._calculate_bbox_overlap(bbox1, bbox2) == 0.0
        
        # Partial overlap
        bbox1 = BoundingBox(0, 0, 10, 10)
        bbox2 = BoundingBox(5, 5, 15, 15)
        overlap = verifier._calculate_bbox_overlap(bbox1, bbox2)
        assert 0 < overlap < 1
    
    def test_cell_value_matching_exact(self):
        """Test exact cell value matching."""
        verifier = PositionVerifier()
        
        tokens = [
            OCRToken(text="123", bbox=BoundingBox(0, 0, 10, 10), confidence=0.9)
        ]
        
        match = verifier._match_cell_value(
            cell_value="123",
            cell_row=0,
            cell_col=0,
            cell_bbox=BoundingBox(0, 0, 10, 10),
            tokens=tokens
        )
        
        assert match.is_exact_match
        assert match.position_confidence == 1.0
        assert match.extracted_value == "123"
        assert match.ocr_value == "123"
    
    def test_cell_value_matching_fuzzy(self):
        """Test fuzzy cell value matching with character confusion."""
        verifier = PositionVerifier(fuzzy_match_threshold=0.8)
        
        tokens = [
            OCRToken(text="1O3", bbox=BoundingBox(0, 0, 10, 10), confidence=0.9)
        ]
        
        match = verifier._match_cell_value(
            cell_value="103",  # Extracted value (0)
            cell_row=0,
            cell_col=0,
            cell_bbox=BoundingBox(0, 0, 10, 10),
            tokens=tokens  # OCR value (O instead of 0)
        )
        
        assert not match.is_exact_match
        assert match.is_fuzzy_match  # Should match due to 0/O confusion
        assert match.position_confidence > 0.7
    
    def test_cell_value_matching_no_match(self):
        """Test cell value matching with no match."""
        verifier = PositionVerifier()
        
        tokens = [
            OCRToken(text="999", bbox=BoundingBox(0, 0, 10, 10), confidence=0.9)
        ]
        
        match = verifier._match_cell_value(
            cell_value="123",
            cell_row=0,
            cell_col=0,
            cell_bbox=BoundingBox(0, 0, 10, 10),
            tokens=tokens
        )
        
        assert not match.is_exact_match
        assert not match.is_fuzzy_match
        assert match.position_confidence < 0.7


class TestTableVerification:
    """Test full table verification."""
    
    def test_verify_table_basic(self):
        """Test basic table verification."""
        verifier = PositionVerifier()
        
        # Create a simple 2x2 table
        spec = TableDataFrameSpec(
            rows=[["1", "2"], ["3", "4"]],
            columns=[ColumnSpec(name="A"), ColumnSpec(name="B")],
            table_metadata_id="test_table"
        )
        
        # Create matching OCR tokens
        tokens = [
            OCRToken(text="1", bbox=BoundingBox(0, 0, 5, 5), confidence=0.9),
            OCRToken(text="2", bbox=BoundingBox(5, 0, 10, 5), confidence=0.9),
            OCRToken(text="3", bbox=BoundingBox(0, 5, 5, 10), confidence=0.9),
            OCRToken(text="4", bbox=BoundingBox(5, 5, 10, 10), confidence=0.9),
        ]
        
        table_bbox = BoundingBox(0, 0, 10, 10)
        
        cell_confidences, mismatched_cells, overall_confidence = verifier.verify_table(
            spec, table_bbox, tokens
        )
        
        assert len(cell_confidences) == 2  # 2 rows
        assert len(cell_confidences[0]) == 2  # 2 cols
        assert overall_confidence > 0.5  # Should have reasonable confidence
        assert isinstance(mismatched_cells, list)
    
    def test_verify_table_with_mismatch(self):
        """Test table verification with mismatched values."""
        verifier = PositionVerifier()
        
        # Create a table
        spec = TableDataFrameSpec(
            rows=[["1", "2"], ["3", "999"]],  # 999 doesn't match OCR
            columns=[ColumnSpec(name="A"), ColumnSpec(name="B")],
            table_metadata_id="test_table"
        )
        
        # OCR tokens (4 instead of 999)
        tokens = [
            OCRToken(text="1", bbox=BoundingBox(0, 0, 5, 5), confidence=0.9),
            OCRToken(text="2", bbox=BoundingBox(5, 0, 10, 5), confidence=0.9),
            OCRToken(text="3", bbox=BoundingBox(0, 5, 5, 10), confidence=0.9),
            OCRToken(text="4", bbox=BoundingBox(5, 5, 10, 10), confidence=0.9),
        ]
        
        table_bbox = BoundingBox(0, 0, 10, 10)
        
        cell_confidences, mismatched_cells, overall_confidence = verifier.verify_table(
            spec, table_bbox, tokens
        )
        
        # Cell (1, 1) should have low confidence
        assert cell_confidences[1][1] < 0.7
        assert (1, 1) in mismatched_cells


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

