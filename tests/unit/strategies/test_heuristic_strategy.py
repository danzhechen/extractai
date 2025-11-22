import unittest
from unittest.mock import MagicMock, patch
import threading
import time
from PIL import Image

from pdf_reader.strategies import HeuristicExtractionStrategy
from pdf_reader.pipeline import PipelineConfig, PageProcessingResult
from pdf_reader.models import TableRegion, TableGrid, BoundingBox, TableDataFrameSpec

class TestHeuristicExtractionStrategy(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_cancel_event = threading.Event()
        self.page_image = Image.new('RGB', (100, 100), color='white')
        self.config = PipelineConfig()
        
        # Mock components
        self.region_detector = MagicMock()
        self.grid_detector = MagicMock()
        self.text_extractor = MagicMock()
        self.assembler = MagicMock()
        
        self.strategy = HeuristicExtractionStrategy(
            self.region_detector,
            self.grid_detector,
            self.text_extractor,
            self.assembler
        )

    @patch('pdf_reader.strategies.GridStructureDetector')
    def test_process_page_success(self, mock_grid_class):
        """Test standard successful heuristic extraction."""
        # Setup mocks
        region = TableRegion(page_index=0, bbox=BoundingBox(0,0,1,1))
        self.region_detector.detect.return_value = [region]
        
        grid = TableGrid(table_id="t1", page_index=0, n_rows=2, n_cols=2)
        mock_grid_instance = MagicMock()
        mock_grid_instance.build_grid.return_value = grid
        mock_grid_class.return_value = mock_grid_instance
        
        # Mock text extractor to not modify grid (it modifies in place)
        self.text_extractor.fill_cell_text = MagicMock()
        
        spec = TableDataFrameSpec(rows=[], columns=[], table_metadata_id="t1")
        self.assembler.to_dataframe_spec.return_value = spec
        
        # Execute
        result = self.strategy.process_page(
            0, self.page_image, self.config, self.mock_logger, self.mock_cancel_event
        )
        
        # Verify
        self.assertEqual(len(result.tables), 1)
        self.region_detector.detect.assert_called_once()
        mock_grid_instance.build_grid.assert_called_once()
        self.text_extractor.fill_cell_text.assert_called_once()

    def test_process_page_no_tables(self):
        """Test when no tables are detected."""
        self.region_detector.detect.return_value = []
        
        result = self.strategy.process_page(
            0, self.page_image, self.config, self.mock_logger, self.mock_cancel_event
        )
        
        self.assertEqual(len(result.tables), 0)
        self.assertFalse(result.page_skipped)

    def test_process_page_cancellation(self):
        """Test early cancellation."""
        self.mock_cancel_event.set()
        
        result = self.strategy.process_page(
            0, self.page_image, self.config, self.mock_logger, self.mock_cancel_event
        )
        
        self.assertTrue(result.page_skipped)
        self.assertIn("cancelled", result.errors[0])

if __name__ == '__main__':
    unittest.main()

