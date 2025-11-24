# Configuration Guide

This guide explains how to configure the PDF table extraction pipeline using various methods.

## Configuration Sources

The pipeline supports configuration from multiple sources with a clear priority order:

1. **Command-line arguments** (highest priority)
2. **Config files** (YAML/JSON)
3. **Environment variables**
4. **Programmatic defaults** (lowest priority)

## Configuration Methods

### 1. Command-Line Arguments

Use CLI flags for quick configuration:

```bash
python -m pdf_reader extract --input document.pdf \
    --dpi 300 \
    --pages 0-5 \
    --debug \
    --log-level DEBUG
```

See `python -m pdf_reader extract --help` for all available options.

### 2. Config Files

Create a YAML or JSON config file:

**YAML Example** (`config/my_config.yaml`):
```yaml
dpi: 300
log_level: DEBUG
enable_debug_artifacts: true
debug_output_dir: my_debug_output
llm_fallback_enabled: false
```

**JSON Example** (`config.json`):
```json
{
  "dpi": 300,
  "log_level": "DEBUG",
  "enable_debug_artifacts": true,
  "debug_output_dir": "my_debug_output"
}
```

Use the config file:
```bash
python -m pdf_reader extract --input document.pdf --config config/my_config.yaml
```

### 3. Environment Variables

Set environment variables with the `PDF_READER_` prefix:

```bash
export PDF_READER_DPI=300
export PDF_READER_LOG_LEVEL=DEBUG
export PDF_READER_LLM_API_KEY=sk-...  # Recommended for sensitive values
python -m pdf_reader extract --input document.pdf
```

**Available Environment Variables**:
- `PDF_READER_DPI` - Rendering DPI
- `PDF_READER_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `PDF_READER_LLM_API_KEY` - LLM API key (recommended for security)
- `PDF_READER_LLM_FALLBACK_ENABLED` - Enable LLM fallback (true/false)
- `PDF_READER_ENABLE_DEBUG_ARTIFACTS` - Enable debug artifacts (true/false)
- And more (see `config/example.yaml` for full list)

### 4. Programmatic Configuration

Create `PipelineConfig` directly in Python:

```python
from pdf_reader import PipelineConfig

config = PipelineConfig(
    input_path="document.pdf",
    dpi=300,
    log_level="DEBUG",
    enable_debug_artifacts=True,
)
```

Or load from a config file:

```python
from pdf_reader.config_loader import create_config
from pathlib import Path

config = create_config(config_file=Path("config/my_config.yaml"))
```

## Configuration Options

### Input/Output Settings

- `input_path`: Path to input PDF file
- `page_indices`: List of page indices to process (None = all pages)
- `output_dir`: Output directory for results (optional)

### Processing Settings

- `dpi`: Rendering DPI (default: 200, higher = better quality but slower)
- `default_rows`: Default number of rows for grid detection (default: 2)
- `default_cols`: Default number of columns for grid detection (default: 3)

### Line Detection Settings

Line detection uses computer vision to identify actual table borders and grid lines from page images, providing more accurate cell boundaries than even division.

- `enable_line_detection`: Enable geometric line detection (default: True)
  - When enabled, detects actual table lines using OpenCV
  - Falls back to even division if no lines detected
  - Set to False to always use even division (faster but less accurate)

- `line_detection_min_length`: Minimum line length in pixels (default: 40)
  - Shorter lines are filtered out as noise
  - Decrease for tables with short line segments
  - Increase to ignore small artifacts

- `line_detection_gap_tolerance`: Maximum gap to merge broken lines (default: 5)
  - Bridges small gaps in faded or broken lines
  - Increase for poor-quality scans
  - Decrease for densely packed tables

- `line_detection_morph_iterations`: Morphological operation iterations (default: 2)
  - Number of erosion/dilation cycles to enhance lines
  - Increase for faint lines (but may introduce noise)
  - Decrease for clean, high-contrast tables

- `line_detection_min_separation`: Minimum separation between distinct lines (default: 5)
  - Prevents duplicate detection of thick lines
  - Increase for tables with thick borders
  - Decrease for tables with thin, closely-spaced lines

**Environment Variables**:
- `PDF_READER_ENABLE_LINE_DETECTION` (true/false)
- `PDF_READER_LINE_DETECTION_MIN_LENGTH` (integer)
- `PDF_READER_LINE_DETECTION_GAP_TOLERANCE` (integer)
- `PDF_READER_LINE_DETECTION_MORPH_ITERATIONS` (integer)
- `PDF_READER_LINE_DETECTION_MIN_SEPARATION` (integer)

### LLM Fallback Settings

- `ocr_confidence_threshold`: Confidence threshold for LLM fallback (0.0-1.0, default: 0.5)
- `llm_fallback_enabled`: Enable LLM fallback (default: False)
- `llm_provider`: LLM provider name (e.g., "openai")
- `llm_model`: LLM model name (e.g., "gpt-4o")
- `llm_api_key`: API key for LLM provider (set via env var for security)

### Logging Settings

- `log_level`: Logging level (DEBUG, INFO, WARNING, ERROR, default: INFO)
- `log_file`: Optional log file path (default: None, console only)
- `log_format`: Log format ("json" or "human", default: "human")

### Debug Artifacts Settings

- `enable_debug_artifacts`: Enable debug visualization (default: False)
- `debug_output_dir`: Directory for debug artifacts (default: "debug_output")
- `generate_overlays`: Generate overlay images (default: True when debug enabled)
- `generate_html_report`: Generate HTML report (default: True when debug enabled)

## Configuration Examples

### Minimal Configuration

```yaml
# config/minimal.yaml
dpi: 200
log_level: INFO
```

### Debug Configuration

```yaml
# config/debug.yaml
dpi: 200
log_level: DEBUG
enable_debug_artifacts: true
debug_output_dir: debug_output
generate_overlays: true
generate_html_report: true
```

### Production Configuration

```yaml
# config/production.yaml
dpi: 200
log_level: WARNING
enable_debug_artifacts: false
llm_fallback_enabled: false
```

### LLM Fallback Configuration

```yaml
# config.llm.yaml
dpi: 200
ocr_confidence_threshold: 0.3
llm_fallback_enabled: true
llm_provider: openai
llm_model: gpt-4o
# llm_api_key: set via PDF_READER_LLM_API_KEY env var
```

### Line Detection Tuning Configuration

```yaml
# config.line-detection.yaml
# For high-quality PDFs with clear borders
enable_line_detection: true
line_detection_min_length: 40
line_detection_gap_tolerance: 5
line_detection_morph_iterations: 2
line_detection_min_separation: 5
```

```yaml
# config.line-detection-aggressive.yaml
# For poor-quality scans or faded lines
enable_line_detection: true
line_detection_min_length: 20          # Detect shorter segments
line_detection_gap_tolerance: 10       # Bridge larger gaps
line_detection_morph_iterations: 3     # More enhancement
line_detection_min_separation: 3       # Closer line spacing
```

```yaml
# config.line-detection-disabled.yaml
# Disable line detection for speed (less accurate)
enable_line_detection: false
```

## Configuration Merging

When multiple sources provide the same setting, the priority order determines which value is used:

**Example**:
- Default: `dpi = 200`
- Environment: `PDF_READER_DPI=250`
- Config file: `dpi: 300`
- CLI: `--dpi 400`

**Result**: `dpi = 400` (CLI has highest priority)

## Best Practices

1. **Use config files** for project-specific settings
2. **Use environment variables** for sensitive values (API keys)
3. **Use CLI arguments** for one-off overrides
4. **Keep defaults sensible** for common use cases
5. **Document your config** with comments in YAML files

## See Also

- `config/example.yaml` - Full example with all options
- `config/minimal.yaml` - Minimal configuration
- `config/debug.yaml` - Debug configuration
- [Architecture Documentation](../architecture.md) - System design details


