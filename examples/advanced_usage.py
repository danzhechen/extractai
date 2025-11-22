"""Advanced usage example for PDF table extraction.

This example demonstrates:
- Multi-page extraction
- Custom configuration
- LLM fallback
- Accessing metadata and metrics
"""

from pathlib import Path

from pdf_reader import PipelineConfig, PipelineRunner

# Create advanced configuration
config = PipelineConfig(
    input_path="document.pdf",
    page_indices=[0, 2, 4],  # Process specific pages
    dpi=300,  # Higher DPI for better quality
    enable_debug_artifacts=True,  # Generate debug visualization
    debug_output_dir="my_debug_output",
    llm_fallback_enabled=True,  # Enable LLM fallback
    ocr_confidence_threshold=0.3,  # Use LLM for low-confidence cells
    log_level="DEBUG",  # Verbose logging
)

# Note: Set LLM API key via environment variable for security
# export PDF_READER_LLM_API_KEY=sk-...

# Create and run the pipeline
runner = PipelineRunner()
result = runner.extract_tables("document.pdf", config=config)

# Access run statistics
stats = result.run_stats
print("=" * 60)
print("Extraction Summary")
print("=" * 60)
print(f"Pages processed: {stats.pages_processed}")
print(f"Pages skipped: {stats.pages_skipped}")
print(f"Tables detected: {stats.tables_detected}")
print(f"Tables extracted: {stats.tables_extracted}")
print(f"Tables failed: {stats.tables_failed}")
print(f"Total cells extracted: {stats.total_cells_extracted}")
print(f"Average OCR confidence: {stats.average_ocr_confidence:.2f}")
print(f"LLM fallback calls: {stats.llm_fallback_count}")
print(f"Total duration: {stats.total_duration_ms:.2f} ms")

# Access table metadata
print("\n" + "=" * 60)
print("Table Details")
print("=" * 60)
for metadata in result.metadata:
    if metadata.status == "success":
        print(f"\nTable {metadata.table_id}:")
        print(f"  Page: {metadata.page_index}")
        print(f"  Cells: {metadata.cell_count}")
        print(f"  Cells with text: {metadata.cells_with_text}")
        print(f"  Average confidence: {metadata.average_confidence:.2f}")
        print(f"  Extraction time: {metadata.extraction_duration_ms:.2f} ms")
    else:
        print(f"\nTable {metadata.table_id} (FAILED):")
        print(f"  Error: {metadata.error_message}")

# Access extracted table data
print("\n" + "=" * 60)
print("Extracted Tables")
print("=" * 60)
for i, (table, metadata) in enumerate(zip(result.tables, result.metadata)):
    if metadata.status == "success":
        print(f"\nTable {i+1} ({metadata.table_id}):")
        print(f"Columns: {[col.name for col in table.columns]}")
        for row_idx, row in enumerate(table.rows):
            print(f"Row {row_idx}: {row}")

# Check for errors
if stats.errors:
    print("\n" + "=" * 60)
    print("Errors")
    print("=" * 60)
    for error in stats.errors:
        print(f"  - {error}")

# Debug artifacts are saved to config.debug_output_dir
if config.enable_debug_artifacts:
    print(f"\nDebug artifacts saved to: {config.debug_output_dir}")



