"""Basic usage example for PDF table extraction.

This example demonstrates the simplest way to extract tables from a PDF.
"""

from pdf_reader import PipelineConfig, PipelineRunner

# Create a simple configuration
config = PipelineConfig(input_path="document.pdf")

# Create and run the pipeline
runner = PipelineRunner()
result = runner.extract_tables("document.pdf", config=config)

# Print summary
print(f"Extracted {result.run_stats.tables_extracted} tables")
print(f"Pages processed: {result.run_stats.pages_processed}")
print(f"Total cells: {result.run_stats.total_cells_extracted}")

# Access extracted tables
for i, table in enumerate(result.tables):
    print(f"\nTable {i+1}:")
    for row in table.rows:
        print(row)



