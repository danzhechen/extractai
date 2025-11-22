import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add src to path so we can import our package
sys.path.append(str(Path(__file__).parent.parent / "src"))

from pdf_reader.pipeline import PipelineRunner, PipelineConfig

def main():
    parser = argparse.ArgumentParser(description="Demo Gemini End-to-End Table Extraction")
    parser.add_argument("pdf_path", help="Path to input PDF file")
    parser.add_argument("--api-key", help="Google Gemini or OpenAI API Key", default=os.getenv("PDF_READER_LLM_API_KEY"))
    parser.add_argument("--attempts", type=int, default=1, help="Consistency attempts (default: 1)")
    parser.add_argument("--model", default="gemini-1.5-flash", help="Model name (default: gemini-1.5-flash)")
    
    args = parser.parse_args()
    
    if not args.api_key:
        print("Error: API Key is required. Set PDF_READER_LLM_API_KEY env var or pass --api-key")
        sys.exit(1)

    print(f"🚀 Starting Gemini Extraction Demo")
    print(f"📄 Input: {args.pdf_path}")
    print(f"🤖 Model: {args.model}")
    print(f"🔄 Attempts: {args.attempts}")

    # Configure Pipeline with Gemini Strategy
    config = PipelineConfig(
        input_path=args.pdf_path,
        extraction_strategy="llm_end_to_end",
        llm_api_key=args.api_key,
        llm_model=args.model,
        llm_consistency_attempts=args.attempts,
        llm_provider="google" if "gemini" in args.model else "openai",
        enable_debug_artifacts=True  # Generate HTML report
    )

    runner = PipelineRunner()
    
    try:
        result = runner.extract_tables(args.pdf_path, config=config)
        
        print("\n✅ Extraction Complete!")
        print(f"📊 Tables Found: {len(result.tables)}")
        print(f"⏱️  Total Time: {result.run_stats.total_duration_ms / 1000:.2f}s")
        
        # Print First Few Tables
        for idx, table in enumerate(result.tables):
            print(f"\nTable {idx + 1} (ID: {table.table_metadata_id}):")
            headers = [c.name for c in table.columns]
            print(f"Headers: {headers}")
            print(f"Row Count: {len(table.rows)}")
            if table.rows:
                print(f"First Row: {table.rows[0]}")

        print(f"\n📄 Report generated at: {config.debug_output_dir}/extraction_report.html")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    load_dotenv()
    main()


