# Debugging Guide

This guide explains how to debug issues with the PDF table extraction pipeline using logs, debug artifacts, and diagnostic tools.

## Debug Artifacts

### Enable Debug Mode

Enable debug artifacts to visualize what the pipeline detected:

```bash
python -m pdf_reader extract --input document.pdf --debug
```

Or in Python:

```python
config = PipelineConfig(
    input_path="document.pdf",
    enable_debug_artifacts=True,
)
```

### Overlay Images

Overlay images show the original page with visual annotations:

- **Green rectangles**: Table region bounding boxes
- **Blue dashed lines**: Grid lines (row/column boundaries)
- **Yellow labels**: Cell indices (R0C0, R0C1, etc.)

**Location**: `debug_output/page_{index}_overlay.png`

**Use cases**:
- Verify table detection accuracy
- Check if grid structure matches the actual table
- Identify detection issues

### HTML Report

The HTML report provides a comprehensive view of the extraction:

- **Run Statistics**: Summary metrics (tables detected, pages processed, etc.)
- **Extracted Tables**: Sample tables rendered as HTML
- **Overlay Links**: Links to overlay images
- **Errors**: Error messages if any occurred

**Location**: `debug_output/extraction_report.html`

**Use cases**:
- Review extraction results
- Check extraction quality
- Identify problematic pages or tables

## Logging

### Log Levels

Configure logging verbosity:

```bash
# Verbose logging (shows all details)
python -m pdf_reader extract --input document.pdf --log-level DEBUG

# Normal logging (default)
python -m pdf_reader extract --input document.pdf --log-level INFO

# Quiet logging (only warnings and errors)
python -m pdf_reader extract --input document.pdf --log-level WARNING
```

### Log Formats

**Human-readable format** (default):
```
2025-01-15 10:30:45 [INFO] pdf_reader.PipelineRunner: Starting table extraction pipeline | input_path=document.pdf
```

**JSON format** (for log aggregation):
```bash
python -m pdf_reader extract --input document.pdf --log-format json
```

Output:
```json
{"timestamp": "2025-01-15 10:30:45", "level": "INFO", "logger": "pdf_reader.PipelineRunner", "message": "Starting table extraction pipeline", "input_path": "document.pdf"}
```

### Log Files

Save logs to a file:

```bash
python -m pdf_reader extract --input document.pdf --log-file pipeline.log
```

Or in config:
```yaml
log_file: pipeline.log
log_level: DEBUG
```

## Common Issues and Solutions

### No Tables Detected

**Symptoms**: `tables_detected: 0` in the summary

**Possible causes**:
1. PDF doesn't contain tables
2. Tables are not in standard format
3. Detection algorithm needs tuning

**Debugging steps**:
1. Enable debug artifacts to see what was detected:
   ```bash
   python -m pdf_reader extract --input document.pdf --debug
   ```
2. Check overlay images to see if table regions were detected
3. Try adjusting DPI (higher DPI may improve detection):
   ```bash
   python -m pdf_reader extract --input document.pdf --dpi 300
   ```
4. Review logs for detection warnings:
   ```bash
   python -m pdf_reader extract --input document.pdf --log-level DEBUG
   ```

### Low OCR Confidence

**Symptoms**: `average_ocr_confidence` is low (< 0.5)

**Possible causes**:
1. Poor image quality
2. Complex fonts or layouts
3. Scanned documents with low resolution

**Solutions**:
1. Increase DPI for better image quality:
   ```bash
   python -m pdf_reader extract --input document.pdf --dpi 300
   ```
2. Enable LLM fallback for low-confidence cells:
   ```bash
   python -m pdf_reader extract --input document.pdf \
       --llm-fallback-enabled \
       --ocr-confidence-threshold 0.3
   ```
3. Check debug artifacts to see which cells have low confidence

### Tables Failed to Extract

**Symptoms**: `tables_failed > 0` in the summary

**Debugging steps**:
1. Check error messages in the summary output
2. Review logs for detailed error information:
   ```bash
   python -m pdf_reader extract --input document.pdf --log-level DEBUG
   ```
3. Check `ExtractionResult.run_stats.errors` for error details:
   ```python
   result = runner.extract_tables("document.pdf")
   for error in result.run_stats.errors:
       print(error)
   ```
4. Review table metadata for failed tables:
   ```python
   for metadata in result.metadata:
       if metadata.status != "success":
           print(f"Table {metadata.table_id} failed: {metadata.error_message}")
   ```

### Memory Issues

**Symptoms**: Out of memory errors when processing large PDFs

**Solutions**:
1. Process pages in smaller batches:
   ```python
   # Process 10 pages at a time
   for start in range(0, total_pages, 10):
       end = min(start + 10, total_pages)
       config = PipelineConfig(page_indices=list(range(start, end)))
       result = runner.extract_tables("document.pdf", config=config)
   ```
2. Reduce DPI (lower DPI uses less memory):
   ```bash
   python -m pdf_reader extract --input document.pdf --dpi 150
   ```
3. Disable debug artifacts (they use additional memory):
   ```bash
   python -m pdf_reader extract --input document.pdf  # debug disabled by default
   ```

### Slow Performance

**Symptoms**: Pipeline takes a long time to process

**Optimization tips**:
1. Process only needed pages:
   ```bash
   python -m pdf_reader extract --input document.pdf --pages 0-5
   ```
2. Use lower DPI (faster but lower quality):
   ```bash
   python -m pdf_reader extract --input document.pdf --dpi 150
   ```
3. Disable debug artifacts:
   ```bash
   # Debug artifacts add overhead
   python -m pdf_reader extract --input document.pdf  # no --debug flag
   ```
4. Use INFO log level instead of DEBUG (less logging overhead):
   ```bash
   python -m pdf_reader extract --input document.pdf --log-level INFO
   ```

## Interpreting Metrics

### RunStats Metrics

**Pages processed**: Number of pages successfully processed
- Lower than expected? Check `pages_skipped` and error messages

**Tables detected**: Total number of tables found
- Zero? Check debug artifacts to see if detection is working

**Tables extracted**: Number of successfully extracted tables
- Lower than `tables_detected`? Check `tables_failed` and error messages

**Average OCR confidence**: Average confidence across all cells
- Low (< 0.5)? Consider enabling LLM fallback or increasing DPI

**LLM fallback count**: Number of cells that used LLM fallback
- High? May indicate OCR quality issues or threshold too low

**Total duration**: Pipeline execution time
- Slow? Try optimizing (see "Slow Performance" section)

### TableMetadata Metrics

**cell_count**: Total cells in the table
**cells_with_text**: Cells with extracted text
- Lower than `cell_count`? Some cells may be empty or failed extraction

**average_confidence**: Average confidence for this table
- Low? This table may have quality issues

**extraction_duration_ms**: Time to extract this table
- High? This table may be complex or have issues

## Diagnostic Workflow

1. **Enable debug mode**:
   ```bash
   python -m pdf_reader extract --input document.pdf --debug --log-level DEBUG
   ```

2. **Review HTML report**: Open `debug_output/extraction_report.html` in a browser

3. **Check overlay images**: Verify table detection accuracy

4. **Review logs**: Look for warnings or errors

5. **Check metrics**: Review `RunStats` for anomalies

6. **Adjust configuration**: Try different settings based on findings

## Getting Help

If you encounter issues:

1. Check this troubleshooting guide
2. Review the [FAQ](../troubleshooting.md#faq)
3. Enable debug artifacts and review the HTML report
4. Check logs with `--log-level DEBUG`
5. Review [Architecture Documentation](../architecture.md) for system understanding



