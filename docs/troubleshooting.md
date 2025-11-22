# Troubleshooting and FAQ

This guide addresses common issues, questions, and solutions for the PDF table extraction pipeline.

## Common Issues

### No Tables Detected

**Problem**: Pipeline reports `tables_detected: 0` even though the PDF contains tables.

**Possible Causes**:
- Tables are not in standard format
- Detection algorithm needs tuning
- PDF quality issues

**Solutions**:
1. **Enable debug artifacts** to visualize detection:
   ```bash
   python -m pdf_reader extract --input document.pdf --debug
   ```
   Check `debug_output/page_*_overlay.png` to see if table regions were detected.

2. **Increase DPI** for better image quality:
   ```bash
   python -m pdf_reader extract --input document.pdf --dpi 300
   ```

3. **Check logs** for detection warnings:
   ```bash
   python -m pdf_reader extract --input document.pdf --log-level DEBUG
   ```

4. **Verify PDF structure**: Some PDFs may have tables as images or non-standard formats.

### Low OCR Confidence

**Problem**: `average_ocr_confidence` is consistently low (< 0.5).

**Possible Causes**:
- Poor image quality
- Complex fonts or layouts
- Scanned documents with low resolution

**Solutions**:
1. **Increase DPI**:
   ```bash
   python -m pdf_reader extract --input document.pdf --dpi 300
   ```

2. **Enable LLM fallback**:
   ```bash
   python -m pdf_reader extract --input document.pdf \
       --llm-fallback-enabled \
       --ocr-confidence-threshold 0.3
   ```

3. **Check debug artifacts** to identify problematic cells.

### Tables Failed to Extract

**Problem**: Some tables show `status: "extraction_failed"` in results.

**Solutions**:
1. **Check error messages**:
   ```python
   result = runner.extract_tables("document.pdf")
   for error in result.run_stats.errors:
       print(error)
   ```

2. **Review table metadata**:
   ```python
   for metadata in result.metadata:
       if metadata.status != "success":
           print(f"Table {metadata.table_id}: {metadata.error_message}")
   ```

3. **Enable debug logging**:
   ```bash
   python -m pdf_reader extract --input document.pdf --log-level DEBUG
   ```

### Inaccurate Cell Boundaries

**Problem**: Extracted cells don't align with visual table structure; text is split incorrectly across cells.

**Possible Causes**:
- Line detection not finding actual table borders
- Line detection disabled (using even division fallback)
- Detection parameters not tuned for your PDF quality

**Solutions**:
1. **Verify line detection is enabled**:
   ```bash
   python -m pdf_reader extract --input document.pdf --debug
   ```
   Check logs for messages like:
   - `"Detected N horizontal lines, M vertical lines"` → line detection working
   - `"Falling back to even division"` → line detection failed

2. **Check debug overlays**:
   - Open `debug_output/page_*_overlay.png`
   - Verify detected lines (shown in red/blue) align with actual table borders
   - If lines are missing, tune detection parameters

3. **Tune line detection for poor-quality PDFs**:
   ```bash
   # For faded/broken lines
   python -m pdf_reader extract --input document.pdf \
       --line-detection-min-length 20 \
       --line-detection-gap-tolerance 10 \
       --line-detection-morph-iterations 3
   ```

4. **Tune line detection for high-quality PDFs**:
   ```bash
   # For clean, sharp lines
   python -m pdf_reader extract --input document.pdf \
       --line-detection-min-length 50 \
       --line-detection-morph-iterations 1
   ```

5. **Disable line detection** (use even division):
   ```bash
   python -m pdf_reader extract --input document.pdf \
       --no-line-detection
   ```

### Line Detection Not Finding Lines

**Problem**: Logs show `"Falling back to even division"` even though table has visible borders.

**Possible Causes**:
- Lines too thin or faint
- Detection parameters too strict
- Image quality too low
- Table borders are not actual lines (e.g., CSS borders in HTML-to-PDF)

**Solutions**:
1. **Increase DPI** for better line visibility:
   ```bash
   python -m pdf_reader extract --input document.pdf --dpi 300
   ```

2. **Relax detection parameters**:
   ```bash
   python -m pdf_reader extract --input document.pdf \
       --line-detection-min-length 20 \
       --line-detection-gap-tolerance 10 \
       --line-detection-morph-iterations 3 \
       --line-detection-min-separation 3
   ```

3. **Check debug overlays**:
   - Look for partial line detection (some lines found but not enough)
   - Adjust parameters based on what's detected vs. what's visible

4. **Verify table has actual lines**:
   - Some PDFs use spacing/alignment without actual border lines
   - For such tables, disable line detection and use even division

### Line Detection Too Slow

**Problem**: Line detection takes too long per page (>5 seconds).

**Solutions**:
1. **Reduce DPI**:
   ```bash
   python -m pdf_reader extract --input document.pdf --dpi 150
   ```

2. **Reduce morphological iterations**:
   ```bash
   python -m pdf_reader extract --input document.pdf \
       --line-detection-morph-iterations 1
   ```

3. **Disable line detection** for speed:
   ```bash
   python -m pdf_reader extract --input document.pdf --no-line-detection
   ```

4. **Process pages in parallel** (if not already):
   ```bash
   python -m pdf_reader extract --input document.pdf --worker-type thread
   ```

### Memory Issues

**Problem**: Out of memory errors when processing large PDFs.

**Solutions**:
1. **Process pages in batches**:
   ```python
   # Process 10 pages at a time
   for start in range(0, total_pages, 10):
       end = min(start + 10, total_pages)
       config = PipelineConfig(page_indices=list(range(start, end)))
       result = runner.extract_tables("document.pdf", config=config)
   ```

2. **Reduce DPI**:
   ```bash
   python -m pdf_reader extract --input document.pdf --dpi 150
   ```

3. **Disable debug artifacts**:
   ```bash
   # Debug artifacts use additional memory
   python -m pdf_reader extract --input document.pdf  # no --debug
   ```

### Slow Performance

**Problem**: Pipeline takes a long time to process documents.

**Optimization Tips**:
1. **Process only needed pages**:
   ```bash
   python -m pdf_reader extract --input document.pdf --pages 0-5
   ```

2. **Use lower DPI** (faster but lower quality):
   ```bash
   python -m pdf_reader extract --input document.pdf --dpi 150
   ```

3. **Disable debug artifacts**:
   ```bash
   # No --debug flag
   python -m pdf_reader extract --input document.pdf
   ```

4. **Use INFO log level** instead of DEBUG:
   ```bash
   python -m pdf_reader extract --input document.pdf --log-level INFO
   ```

### Configuration Not Applied

**Problem**: Configuration changes don't seem to take effect.

**Check Priority Order**:
1. CLI arguments override everything
2. Config file overrides environment variables
3. Environment variables override defaults

**Solution**: Check what's overriding your setting:
```bash
# Check environment variables
env | grep PDF_READER

# Check CLI arguments
python -m pdf_reader extract --input document.pdf --help
```

## FAQ

### What PDF types are supported?

The pipeline works with standard PDF files. It supports:
- Text-based PDFs (best results)
- Scanned PDFs (may require higher DPI or LLM fallback)
- Multi-page documents
- PDFs with embedded tables

**Limitations**:
- Tables as images (not text) may have lower accuracy
- Complex layouts (rotated tables, nested tables) may not be fully supported
- Very large PDFs may require batch processing

### What table formats are supported?

The pipeline supports:
- Standard grid tables (rows and columns)
- Tables with merged cells (row/column spans)
- Multi-page tables (tables spanning multiple pages are treated as separate tables per page)

**Not yet supported**:
- Nested tables
- Rotated tables
- Tables with complex formatting

### What are the accuracy expectations?

**Accuracy depends on**:
- PDF quality (text-based vs scanned)
- Table structure complexity
- OCR confidence (for scanned documents)
- LLM fallback usage (improves accuracy for difficult cases)

**Typical accuracy**:
- Text-based PDFs: High accuracy (>90% for well-structured tables)
- Scanned PDFs: Moderate accuracy (60-80% depending on scan quality)
- With LLM fallback: Improved accuracy for low-confidence cells

### How do I improve accuracy?

1. **Use higher DPI** for better image quality:
   ```bash
   python -m pdf_reader extract --input document.pdf --dpi 300
   ```

2. **Enable LLM fallback** for difficult cases:
   ```bash
   python -m pdf_reader extract --input document.pdf \
       --llm-fallback-enabled \
       --ocr-confidence-threshold 0.3
   ```

3. **Review debug artifacts** to identify issues:
   ```bash
   python -m pdf_reader extract --input document.pdf --debug
   ```

4. **Adjust confidence threshold** based on your needs:
   - Lower threshold (e.g., 0.3) = more LLM fallback, higher accuracy, higher cost
   - Higher threshold (e.g., 0.7) = less LLM fallback, lower cost, may miss some cells

### What are the cost and latency considerations for LLM fallback?

**Cost**:
- LLM API calls cost money (varies by provider)
- Cost depends on number of low-confidence cells
- Typical cost: $0.01-0.10 per page (depending on table complexity)

**Latency**:
- LLM calls add 1-5 seconds per cell (depending on provider)
- Can significantly slow down processing for many low-confidence cells

**Recommendations**:
- Use LLM fallback only when needed
- Set appropriate confidence threshold (0.3-0.5 is typical)
- Monitor API usage and costs
- Consider batch processing for large documents

### How do I interpret error messages?

**Page-level errors**:
- `Page {index}: {error}`: Page failed to render or detect
- Check if page is corrupted or has issues
- Review `pages_skipped` count

**Table-level errors**:
- `Table {id} extraction failed: {error}`: Table extraction failed
- Check `tables_failed` count
- Review table metadata for error details

**Common error types**:
- `PdfIngestionError`: PDF loading or rendering issue
- `ValueError`: Invalid configuration or data
- `LLMExtractionError`: LLM API call failed

### How do I use debug artifacts for diagnosis?

1. **Enable debug mode**:
   ```bash
   python -m pdf_reader extract --input document.pdf --debug
   ```

2. **Review overlay images** (`debug_output/page_*_overlay.png`):
   - Green rectangles show detected table regions
   - Blue lines show grid structure
   - Yellow labels show cell indices

3. **Review HTML report** (`debug_output/extraction_report.html`):
   - Summary statistics
   - Extracted tables
   - Error messages

4. **Compare with original PDF** to identify detection issues

### Performance Tuning Tips

1. **DPI selection**:
   - Lower DPI (150): Faster, lower quality
   - Higher DPI (300): Slower, better quality
   - Default (200): Good balance

2. **Page selection**:
   - Process only needed pages
   - Use `--pages` to limit processing

3. **Debug artifacts**:
   - Disable in production (`--debug` flag)
   - Enable only when needed

4. **Logging**:
   - Use INFO level in production
   - Use DEBUG only for troubleshooting

5. **LLM fallback**:
   - Use only when needed
   - Set appropriate confidence threshold
   - Consider batch processing for large documents

## Getting Help

If you encounter issues not covered here:

1. **Check logs** with `--log-level DEBUG`
2. **Enable debug artifacts** and review HTML report
3. **Review architecture documentation**: See [Architecture Documentation](architecture.md)
4. **Check extension guide**: See [Extension Guide](guides/extending.md) for customization options

## See Also

- [Debugging Guide](guides/debugging.md) - Detailed debugging workflow
- [Configuration Guide](guides/configuration.md) - Configuration options
- [Architecture Documentation](architecture.md) - System design details


