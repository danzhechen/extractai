# Getting Started Guide

This guide will help you get started with the PDF table extraction pipeline quickly.

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Install Dependencies

1. **Create a virtual environment** (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**:

```bash
cd pdf-reading-project
pip install -r requirements.txt
```

### Verify Installation

Test that the installation works:

```bash
python -m pdf_reader extract --help
```

You should see the CLI help message.

## Quick Start

### Basic Usage (CLI)

Extract tables from a PDF file:

```bash
python -m pdf_reader extract --input document.pdf
```

This will:
- Process all pages in the PDF
- Detect and extract tables
- Print a summary of results

### Basic Usage (Python)

```python
from pdf_reader import PipelineConfig, PipelineRunner

# Create configuration
config = PipelineConfig(input_path="document.pdf")

# Run pipeline
runner = PipelineRunner()
result = runner.extract_tables("document.pdf", config=config)

# Access results
print(f"Extracted {result.run_stats.tables_extracted} tables")
for table in result.tables:
    for row in table.rows:
        print(row)
```

## Common Use Cases

### Extract from Specific Pages

```bash
# Extract from pages 0, 2, and 4
python -m pdf_reader extract --input document.pdf --pages 0,2,4

# Extract from page range 0-5
python -m pdf_reader extract --input document.pdf --pages 0-5
```

### Enable Debug Artifacts

```bash
python -m pdf_reader extract --input document.pdf --debug
```

This generates:
- Overlay images showing detected tables (`debug_output/page_*_overlay.png`)
- HTML report with extraction summary (`debug_output/extraction_report.html`)

### Use a Config File

1. Create a config file (`my_config.yaml`):

```yaml
dpi: 300
log_level: DEBUG
enable_debug_artifacts: true
```

2. Use it:

```bash
python -m pdf_reader extract --input document.pdf --config my_config.yaml
```

### Enable LLM Fallback

For better accuracy on difficult tables:

```bash
export PDF_READER_LLM_API_KEY=sk-...  # Set API key
python -m pdf_reader extract --input document.pdf \
    --llm-fallback-enabled \
    --ocr-confidence-threshold 0.3
```

### Line Detection: Before and After

The pipeline uses **geometric line detection** to identify actual table borders and grid lines, providing much more accurate cell boundaries than simple even division.

#### Example: Financial Statement Table

**Before (Even Division)**:
```bash
# Disable line detection (uses even division)
python -m pdf_reader extract --input financial_statement.pdf --no-line-detection
```

Result:
- Assumes uniform cell sizes
- Divides table region into equal-sized cells (e.g., 4×4 grid)
- Cell boundaries may not align with actual table structure
- Text from merged header cells gets split incorrectly
- Varying column widths are not respected

**After (Line Detection)**:
```bash
# Enable line detection (default)
python -m pdf_reader extract --input financial_statement.pdf
```

Result:
- Detects actual horizontal and vertical lines from the image
- Creates cells from line intersections (e.g., 3 rows × 5 columns)
- Cell boundaries align precisely with visual table structure
- Merged cells are detected correctly
- Variable column widths are preserved

#### Visual Comparison

Enable debug artifacts to see the difference:

```bash
# With line detection (default)
python -m pdf_reader extract --input document.pdf --debug

# Without line detection
python -m pdf_reader extract --input document.pdf --no-line-detection --debug
```

Compare the overlay images in `debug_output/`:
- **With line detection**: Red/blue lines show detected table borders and grid lines
- **Without line detection**: Uniform grid overlay (even division)

#### When to Use Each Approach

**Use Line Detection (default)** when:
- Tables have visible borders and grid lines
- Cell sizes vary (different column widths, merged cells)
- Accuracy is more important than speed
- Working with well-formatted PDFs

**Use Even Division** when:
- Tables have no visible borders (spacing-based layout)
- All cells are uniform size
- Speed is critical (line detection disabled is ~2x faster)
- Working with simple, regular tables

#### Tuning Line Detection

For poor-quality scans or faded lines:

```bash
python -m pdf_reader extract --input scanned_document.pdf \
    --line-detection-min-length 20 \
    --line-detection-gap-tolerance 10 \
    --line-detection-morph-iterations 3
```

See [Configuration Guide](configuration.md#line-detection-settings) for detailed parameter descriptions.

## Next Steps

- **Learn more**: See [Configuration Guide](configuration.md) for detailed configuration options
- **Debug issues**: See [Debugging Guide](debugging.md) for troubleshooting
- **Extend the system**: See [Extension Guide](extending.md) for customization
- **Understand architecture**: See [Architecture Documentation](../architecture.md)


