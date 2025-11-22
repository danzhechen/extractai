"""
Example Prefect deployment configuration for PDF table extraction.

This script demonstrates how to configure and deploy Prefect flows for PDF extraction.
It includes examples for:
1. Local development and testing
2. Deployment to Prefect Cloud
3. Configuration via Prefect blocks
4. Scheduled execution
5. Event-driven triggers

Prerequisites:
    - Install Prefect: pip install pdf-reader[prefect]
    - Set up Prefect: prefect cloud login (for Cloud deployment)
    - Create Prefect blocks for configuration storage

Usage:
    # Run locally for testing
    python examples/integrations/prefect_deployment.py --mode local
    
    # Deploy to Prefect Cloud
    python examples/integrations/prefect_deployment.py --mode deploy
    
    # Create configuration blocks
    python examples/integrations/prefect_deployment.py --mode setup-blocks
"""

import argparse
from pathlib import Path

try:
    from prefect import flow
    from prefect.blocks.system import JSON
    from prefect.deployments import Deployment
    from prefect.server.schemas.schedules import CronSchedule
    
    from pdf_reader.adapters.prefect import extract_tables_flow, batch_extract_tables_flow
    from pdf_reader.pipeline import PipelineConfig
except ImportError:
    raise ImportError(
        "Prefect is not installed. Install with: pip install pdf-reader[prefect]"
    )


def create_config_block():
    """Create a Prefect JSON block for storing pipeline configuration.
    
    This allows storing configuration centrally and referencing it by name in flows.
    """
    # Production configuration
    prod_config = {
        "dpi": 300,
        "enable_debug_artifacts": False,
        "llm_fallback_enabled": True,
        "llm_provider": "openai",
        "llm_model": "gpt-4o",
        "ocr_confidence_threshold": 0.5,
        "log_level": "INFO",
        "worker_type": "thread",
        "max_workers": 4,
    }
    
    # Create and save block
    json_block = JSON(value=prod_config)
    json_block.save("pdf-extraction-prod-config", overwrite=True)
    
    print("✅ Created Prefect block: pdf-extraction-prod-config")
    
    # Development configuration
    dev_config = {
        "dpi": 200,
        "enable_debug_artifacts": True,
        "generate_overlays": True,
        "generate_html_report": True,
        "debug_output_dir": "debug_output",
        "log_level": "DEBUG",
        "worker_type": "sequential",
    }
    
    dev_json_block = JSON(value=dev_config)
    dev_json_block.save("pdf-extraction-dev-config", overwrite=True)
    
    print("✅ Created Prefect block: pdf-extraction-dev-config")


def run_local_example():
    """Run a local example extraction."""
    print("🚀 Running local extraction example...")
    
    # Example 1: Simple extraction
    result = extract_tables_flow(
        input_path="sample/sample.pdf",
        output_dir="output/prefect_local",
    )
    
    print(f"✅ Extracted {result['tables_extracted']} tables")
    print(f"📁 Output: {result['output_dir']}")
    
    # Example 2: Batch extraction
    pdf_files = [
        "sample/sample.pdf",
        # Add more PDF paths here
    ]
    
    batch_result = batch_extract_tables_flow(
        input_paths=pdf_files,
        output_dir="output/prefect_batch",
    )
    
    print(f"✅ Batch extraction: {batch_result['successful']}/{batch_result['total_files']} successful")


def deploy_to_prefect():
    """Deploy flows to Prefect Cloud or Server."""
    print("🚀 Deploying flows to Prefect...")
    
    # Deployment 1: Single file extraction (on-demand)
    single_deployment = Deployment.build_from_flow(
        flow=extract_tables_flow,
        name="pdf-extraction-on-demand",
        version="1.0.0",
        tags=["pdf", "extraction", "production"],
        description="On-demand PDF table extraction",
        parameters={
            "config_block_name": "pdf-extraction-prod-config",
        },
    )
    
    single_deployment.apply()
    print("✅ Deployed: pdf-extraction-on-demand")
    
    # Deployment 2: Scheduled batch extraction
    batch_deployment = Deployment.build_from_flow(
        flow=batch_extract_tables_flow,
        name="pdf-extraction-daily-batch",
        version="1.0.0",
        schedule=CronSchedule(cron="0 2 * * *"),  # Run daily at 2 AM
        tags=["pdf", "extraction", "batch", "scheduled"],
        description="Daily batch PDF table extraction",
        parameters={
            "output_dir": "/data/output",
            "config_block_name": "pdf-extraction-prod-config",
        },
    )
    
    batch_deployment.apply()
    print("✅ Deployed: pdf-extraction-daily-batch (scheduled daily at 2 AM)")
    
    # Deployment 3: Kubernetes work pool (if configured)
    try:
        k8s_deployment = Deployment.build_from_flow(
            flow=extract_tables_flow,
            name="pdf-extraction-k8s",
            version="1.0.0",
            work_pool_name="kubernetes",
            tags=["pdf", "extraction", "k8s"],
            description="PDF extraction on Kubernetes",
            parameters={
                "config_block_name": "pdf-extraction-prod-config",
            },
        )
        
        k8s_deployment.apply()
        print("✅ Deployed: pdf-extraction-k8s (Kubernetes work pool)")
    except Exception as e:
        print(f"⚠️  Could not deploy to Kubernetes work pool: {e}")
        print("   Create a work pool with: prefect work-pool create kubernetes")


def advanced_examples():
    """Show advanced Prefect integration patterns."""
    
    # Example: Subflow pattern for complex workflows
    @flow(name="pdf-processing-pipeline")
    def processing_pipeline(input_dir: str, output_dir: str):
        """Complex pipeline with pre/post processing."""
        import glob
        
        # Step 1: Find all PDFs
        pdf_files = glob.glob(f"{input_dir}/**/*.pdf", recursive=True)
        print(f"Found {len(pdf_files)} PDF files")
        
        # Step 2: Extract tables (using subflow)
        batch_result = batch_extract_tables_flow(
            input_paths=pdf_files,
            output_dir=output_dir,
            config_block_name="pdf-extraction-prod-config",
        )
        
        # Step 3: Post-processing
        # (could trigger downstream data pipelines, send notifications, etc.)
        
        return batch_result
    
    # Example: Event-driven extraction
    @flow(name="pdf-upload-handler")
    def handle_pdf_upload(file_path: str, metadata: dict):
        """Handle PDF upload event."""
        result = extract_tables_flow(
            input_path=file_path,
            output_dir="output/uploads",
            metadata=metadata,
        )
        
        # Send notification or trigger downstream processing
        # ...
        
        return result
    
    print("📚 Advanced examples defined (see source code)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Prefect deployment examples for PDF extraction"
    )
    parser.add_argument(
        "--mode",
        choices=["local", "deploy", "setup-blocks", "advanced"],
        default="local",
        help="Execution mode",
    )
    
    args = parser.parse_args()
    
    if args.mode == "local":
        run_local_example()
    elif args.mode == "deploy":
        deploy_to_prefect()
    elif args.mode == "setup-blocks":
        create_config_block()
    elif args.mode == "advanced":
        advanced_examples()


if __name__ == "__main__":
    main()


# Additional example: Using Prefect with S3 storage
"""
from prefect_aws import S3Bucket

# Create S3 bucket block for result storage
s3_bucket = S3Bucket(
    bucket_name="my-pdf-results",
    aws_access_key_id="...",
    aws_secret_access_key="...",
)
s3_bucket.save("pdf-results-bucket")

# Use in flow
@flow
def extract_and_upload_to_s3(input_path: str):
    # Extract tables
    result = extract_tables_flow(
        input_path=input_path,
        output_dir="temp/output",
    )
    
    # Upload results to S3
    s3_bucket = S3Bucket.load("pdf-results-bucket")
    s3_bucket.upload_from_path(
        from_path=result['output_dir'],
        to_path=f"extractions/{result['run_id']}/",
    )
    
    return result
"""


# Additional example: Retry and error handling
"""
from prefect import task
from prefect.tasks import task_input_hash
from datetime import timedelta

@task(
    retries=3,
    retry_delay_seconds=60,
    cache_key_fn=task_input_hash,  # Cache successful results
    cache_expiration=timedelta(hours=24),
)
def extract_with_caching(input_path: str):
    result = extract_tables_task(
        input_path=input_path,
        output_dir="output/cached",
    )
    return result

@flow
def resilient_extraction_flow(input_path: str):
    try:
        result = extract_with_caching(input_path)
        return {"status": "success", **result}
    except Exception as e:
        # Log error and return graceful failure
        return {"status": "failed", "error": str(e)}
"""


