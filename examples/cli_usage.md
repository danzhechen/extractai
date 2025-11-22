# CLI Usage Examples

This document provides common command-line usage examples for the PDF table extraction pipeline.

## Basic Commands

### Extract from all pages

```bash
python -m pdf_reader extract --input document.pdf
```

### Extract from specific pages

```bash
# Comma-separated pages
python -m pdf_reader extract --input document.pdf --pages 0,2,4

# Page range
python -m pdf_reader extract --input document.pdf --pages 0-5
```

### Custom DPI

```bash
python -m pdf_reader extract --input document.pdf --dpi 300
```

## Debug and Logging

### Enable debug artifacts

```bash
python -m pdf_reader extract --input document.pdf --debug
```

This generates:
- Overlay images: `debug_output/page_*_overlay.png`
- HTML report: `debug_output/extraction_report.html`

### Verbose logging

```bash
python -m pdf_reader extract --input document.pdf --log-level DEBUG
```

### Save logs to file

```bash
python -m pdf_reader extract --input document.pdf --log-file pipeline.log
```

### JSON log format

```bash
python -m pdf_reader extract --input document.pdf --log-format json
```

## Configuration Files

### Use a config file

```bash
python -m pdf_reader extract --input document.pdf --config config.yaml
```

### Override config file settings

```bash
# Config file sets dpi=200, but CLI overrides to 300
python -m pdf_reader extract --input document.pdf --config config.yaml --dpi 300
```

## LLM Fallback

### Enable LLM fallback

```bash
# Set API key via environment variable (recommended)
export PDF_READER_LLM_API_KEY=sk-...
python -m pdf_reader extract --input document.pdf --llm-fallback-enabled

# Or set via CLI (less secure)
python -m pdf_reader extract --input document.pdf \
    --llm-fallback-enabled \
    --llm-api-key sk-...
```

### Custom confidence threshold

```bash
python -m pdf_reader extract --input document.pdf \
    --llm-fallback-enabled \
    --ocr-confidence-threshold 0.3
```

## Advanced Examples

### Full configuration example

```bash
python -m pdf_reader extract \
    --input document.pdf \
    --pages 0-10 \
    --dpi 300 \
    --config my_config.yaml \
    --debug \
    --log-level DEBUG \
    --log-file extraction.log \
    --llm-fallback-enabled \
    --ocr-confidence-threshold 0.3
```

### Batch processing

```bash
# Process multiple PDFs
for pdf in *.pdf; do
    python -m pdf_reader extract --input "$pdf" --output "results/${pdf%.pdf}"
done
```

### Extract with custom output

```bash
python -m pdf_reader extract \
    --input document.pdf \
    --debug \
    --debug-output-dir custom_output
```

## Getting Help

View all available options:

```bash
python -m pdf_reader extract --help
```

## See Also

- [Configuration Guide](../docs/guides/configuration.md) - Detailed configuration options
- [Getting Started Guide](../docs/guides/getting-started.md) - Quick start tutorial



