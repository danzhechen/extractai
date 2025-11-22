# Extension and Customization Guide

This guide explains how to extend the PDF table extraction pipeline with custom implementations.

## Overview

The pipeline is designed for extensibility. You can:
- Implement custom OCR engines
- Add new table detection strategies
- Extend the pipeline with custom processing steps
- Add new output formats

## Architecture Overview

The pipeline uses a modular architecture with clear interfaces:

- **PdfIngestionService**: Load and render PDFs
- **TableRegionDetector**: Detect table regions
- **GridStructureDetector**: Build grid structures
- **CellTextExtractor**: Extract cell text
- **LLMExtractionService**: LLM-based text extraction
- **TableAssembler**: Convert grids to output format

## Implementing Custom OCR Engines

### Extend CellTextExtractor

Create a custom extractor that implements the extraction logic:

```python
from pdf_reader.extraction import CellTextExtractor
from pdf_reader.models import Cell, TableGrid
from PIL import Image

class CustomOCRExtractor(CellTextExtractor):
    """Custom OCR extractor using your preferred OCR engine."""
    
    def __init__(self, ocr_engine_config):
        super().__init__()
        # Initialize your OCR engine
        self.ocr_engine = YourOCREngine(ocr_engine_config)
    
    def _extract_with_ocr(self, cell: Cell, page_image: Image.Image = None) -> tuple[str, float]:
        """Extract text using your OCR engine.
        
        Args:
            cell: Cell to extract text from
            page_image: Full page image for context
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        # Crop cell region from page image
        if page_image and cell.bbox:
            bbox = cell.bbox
            width, height = page_image.size
            x0 = int(bbox.x0 * width)
            y0 = int(bbox.y0 * height)
            x1 = int(bbox.x1 * width)
            y1 = int(bbox.y1 * height)
            cell_image = page_image.crop((x0, y0, x1, y1))
        else:
            cell_image = page_image  # Use full image if no bbox
        
        # Use your OCR engine
        text, confidence = self.ocr_engine.extract_text(cell_image)
        
        return text, confidence
```

**Usage**:
```python
from pdf_reader import PipelineRunner

runner = PipelineRunner()
runner.text_extractor = CustomOCRExtractor(ocr_engine_config={...})
result = runner.extract_tables("document.pdf")
```

## Implementing Custom Table Detectors

### Custom TableRegionDetector

```python
from pdf_reader.detection import TableRegionDetector
from pdf_reader.models import TableRegion
from PIL import Image

class CustomTableDetector(TableRegionDetector):
    """Custom table region detector."""
    
    def detect(self, page_image: Image.Image, page_index: int) -> list[TableRegion]:
        """Detect table regions on a page.
        
        Args:
            page_image: Page image to analyze
            page_index: Index of the page
            
        Returns:
            List of detected table regions
        """
        # Implement your detection algorithm
        regions = []
        
        # Example: Use your detection library
        detected_boxes = your_detection_library.find_tables(page_image)
        
        for bbox in detected_boxes:
            region = TableRegion(
                page_index=page_index,
                bbox=bbox,  # BoundingBox with normalized coordinates (0-1)
                confidence=1.0,  # Detection confidence
            )
            regions.append(region)
        
        return regions
```

**Usage**:
```python
runner = PipelineRunner()
runner.region_detector = CustomTableDetector()
result = runner.extract_tables("document.pdf")
```

### Custom GridStructureDetector

```python
from pdf_reader.detection import GridStructureDetector
from pdf_reader.models import TableGrid, TableRegion, Cell, BoundingBox

class CustomGridDetector(GridStructureDetector):
    """Custom grid structure detector."""
    
    def build_grid(
        self,
        region: TableRegion,
        n_rows: int,
        n_cols: int,
        table_id: str,
        span_hints: dict = None,
    ) -> TableGrid:
        """Build grid structure from table region.
        
        Args:
            region: Detected table region
            n_rows: Expected number of rows
            n_cols: Expected number of columns
            table_id: Unique identifier for the table
            span_hints: Optional hints for merged cells
            
        Returns:
            TableGrid with cell structure
        """
        # Implement your grid detection algorithm
        cells = []
        
        # Example: Create a grid structure
        for row in range(n_rows):
            for col in range(n_cols):
                # Calculate cell bounding box
                cell_bbox = self._calculate_cell_bbox(region, row, col, n_rows, n_cols)
                
                # Check for merged cells (from span_hints)
                row_span = 1
                col_span = 1
                if span_hints:
                    key = (row, col)
                    if key in span_hints:
                        row_span, col_span = span_hints[key]
                
                cell = Cell(
                    row_index=row,
                    col_index=col,
                    row_span=row_span,
                    col_span=col_span,
                    bbox=cell_bbox,
                )
                cells.append(cell)
        
        return TableGrid(
            table_id=table_id,
            page_index=region.page_index,
            n_rows=n_rows,
            n_cols=n_cols,
            cells=cells,
        )
    
    def _calculate_cell_bbox(self, region, row, col, n_rows, n_cols):
        """Calculate bounding box for a cell."""
        # Implement cell bbox calculation
        bbox = region.bbox
        cell_width = (bbox.x1 - bbox.x0) / n_cols
        cell_height = (bbox.y1 - bbox.y0) / n_rows
        
        return BoundingBox(
            x0=bbox.x0 + col * cell_width,
            y0=bbox.y0 + row * cell_height,
            x1=bbox.x0 + (col + 1) * cell_width,
            y1=bbox.y0 + (row + 1) * cell_height,
        )
```

## Implementing Custom LLM Providers

### Custom LLMExtractionService

```python
from pdf_reader.llm_extraction import LLMExtractionService, LLMExtractionError
from PIL import Image

class CustomLLMService(LLMExtractionService):
    """Custom LLM extraction service."""
    
    def __init__(self, api_key: str, model: str = "your-model"):
        self.api_key = api_key
        self.model = model
        # Initialize your LLM client
    
    def extract_text_from_image(
        self, image: Image.Image, context: str = None
    ) -> str:
        """Extract text from an image using your LLM.
        
        Args:
            image: The cropped image of the cell or table region
            context: Optional text context or prompt hint
            
        Returns:
            The extracted text string
            
        Raises:
            LLMExtractionError: If the LLM API call fails
        """
        try:
            # Convert image to format your LLM expects
            image_data = self._prepare_image(image)
            
            # Call your LLM API
            response = self._call_llm_api(image_data, context)
            
            return response.text
        except Exception as e:
            raise LLMExtractionError(f"LLM extraction failed: {e}")
    
    def _prepare_image(self, image: Image.Image):
        """Prepare image for LLM API."""
        # Convert to base64, bytes, or format your API expects
        # Implementation depends on your LLM provider
        pass
    
    def _call_llm_api(self, image_data, context: str):
        """Call your LLM API."""
        # Implementation depends on your LLM provider
        pass
```

**Usage**:
```python
from pdf_reader import PipelineConfig, PipelineRunner

config = PipelineConfig(
    input_path="document.pdf",
    llm_fallback_enabled=True,
    llm_provider="custom",
)

runner = PipelineRunner()
# Create custom LLM service
custom_llm = CustomLLMService(api_key="your-key", model="your-model")

# Configure extractor with custom LLM
from pdf_reader.extraction import CellTextExtractor
extractor = CellTextExtractor(
    llm_fallback_enabled=True,
    llm_service=custom_llm,
)
runner.text_extractor = extractor

result = runner.extract_tables("document.pdf", config=config)
```

## Adding Custom Processing Steps

### Extend PipelineRunner

You can extend `PipelineRunner` to add custom processing:

```python
from pdf_reader.pipeline import PipelineRunner
from pdf_reader.models import ExtractionResult

class CustomPipelineRunner(PipelineRunner):
    """Extended pipeline with custom processing."""
    
    def extract_tables(self, pdf_input, config=None):
        """Run pipeline with custom preprocessing."""
        # Custom preprocessing
        preprocessed_input = self._preprocess(pdf_input)
        
        # Run standard pipeline
        result = super().extract_tables(preprocessed_input, config)
        
        # Custom postprocessing
        result = self._postprocess(result)
        
        return result
    
    def _preprocess(self, pdf_input):
        """Custom preprocessing step."""
        # Implement your preprocessing
        return pdf_input
    
    def _postprocess(self, result: ExtractionResult):
        """Custom postprocessing step."""
        # Implement your postprocessing
        # e.g., filter tables, transform data, etc.
        return result
```

## Adding Custom Output Formats

### Custom Exporter

```python
from pdf_reader.models import ExtractionResult

class CustomExporter:
    """Export extraction results to custom format."""
    
    def export(self, result: ExtractionResult, output_path: str):
        """Export results to custom format.
        
        Args:
            result: ExtractionResult from pipeline
            output_path: Path to save exported data
        """
        # Implement your export logic
        # e.g., Excel, CSV, database, etc.
        pass
```

**Usage**:
```python
result = runner.extract_tables("document.pdf")
exporter = CustomExporter()
exporter.export(result, "output.xlsx")
```

## Integration Examples

### Using Custom Components Together

```python
from pdf_reader import PipelineConfig, PipelineRunner

# Create custom components
custom_detector = CustomTableDetector()
custom_extractor = CustomOCRExtractor(ocr_engine_config={...})
custom_llm = CustomLLMService(api_key="...")

# Configure pipeline
config = PipelineConfig(
    input_path="document.pdf",
    llm_fallback_enabled=True,
)

runner = PipelineRunner()
runner.region_detector = custom_detector
runner.text_extractor = custom_extractor
runner.text_extractor.llm_service = custom_llm

# Run pipeline
result = runner.extract_tables("document.pdf", config=config)
```

## Best Practices

1. **Follow existing interfaces**: Implement the same methods and signatures
2. **Handle errors gracefully**: Raise appropriate exceptions
3. **Provide confidence scores**: When possible, include confidence metrics
4. **Test your implementations**: Write tests for custom components
5. **Document your extensions**: Add docstrings explaining your implementation

## See Also

- [Architecture Documentation](../architecture.md) - System design details
- [API Reference](../api/) - Detailed interface documentation
- Source code in `src/pdf_reader/` - Reference implementations



