"""
Example Airflow DAG for PDF table extraction.

This DAG demonstrates how to use the PdfExtractionOperator in an Airflow workflow.
It includes:
1. PDF extraction with dynamic parameters
2. XCom for passing results between tasks
3. Sensor pattern for waiting on upstream file generation
4. Error handling and retry logic

Prerequisites:
    - Install Airflow: pip install pdf-reader[airflow]
    - Set up Airflow: airflow db init
    - Copy this file to $AIRFLOW_HOME/dags/
    - Create config file: configs/production.yaml

Usage:
    # Trigger DAG with parameters
    airflow dags trigger pdf_extraction_pipeline \\
        --conf '{"pdf_path": "/path/to/document.pdf", "output_dir": "/path/to/output"}'
    
    # View DAG in Airflow UI
    airflow webserver --port 8080
"""

from datetime import datetime, timedelta
from pathlib import Path

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
    from airflow.sensors.filesystem import FileSensor
    from pdf_reader.adapters.airflow import PdfExtractionOperator
except ImportError:
    raise ImportError(
        "Airflow is not installed. Install with: pip install pdf-reader[airflow]"
    )

# Default arguments for all tasks
default_args = {
    "owner": "data-team",
    "depends_on_past": False,
    "email": ["alerts@example.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}

# Define DAG
with DAG(
    dag_id="pdf_extraction_pipeline",
    default_args=default_args,
    description="Extract tables from PDF documents",
    schedule_interval=None,  # Manual trigger or external trigger
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["pdf", "extraction", "tables"],
    params={
        "pdf_path": "/data/input/document.pdf",
        "output_dir": "/data/output",
        "dpi": 300,
        "enable_debug": False,
    },
) as dag:
    
    # Task 1: Wait for PDF file to be available (optional)
    # Useful if upstream process generates the PDF
    wait_for_pdf = FileSensor(
        task_id="wait_for_pdf",
        filepath="{{ params.pdf_path }}",
        poke_interval=30,  # Check every 30 seconds
        timeout=3600,  # Timeout after 1 hour
        mode="poke",
    )
    
    # Task 2: Extract tables from PDF
    extract_tables = PdfExtractionOperator(
        task_id="extract_tables",
        input_path="{{ params.pdf_path }}",
        output_dir="{{ params.output_dir }}",
        config_path="configs/production.yaml",
        pipeline_config={
            "dpi": "{{ params.dpi }}",
            "enable_debug_artifacts": "{{ params.enable_debug }}",
        },
        metadata={
            "team": "analytics",
            "project": "pdf-extraction",
        },
    )
    
    # Task 3: Post-process results (example)
    def post_process_results(**context):
        """Post-process extraction results from XCom."""
        ti = context["task_instance"]
        
        # Get extraction summary from XCom
        summary = ti.xcom_pull(
            task_ids="extract_tables",
            key="extraction_summary"
        )
        
        print(f"Extraction summary: {summary}")
        print(f"Extracted {summary['tables_extracted']} tables")
        print(f"Output directory: {summary['output_dir']}")
        
        # Example: Send notification, update database, trigger downstream pipeline, etc.
        # ...
        
        return summary
    
    post_process = PythonOperator(
        task_id="post_process",
        python_callable=post_process_results,
        provide_context=True,
    )
    
    # Task 4: Cleanup temporary files (example)
    def cleanup_temp_files(**context):
        """Clean up temporary processing files."""
        ti = context["task_instance"]
        summary = ti.xcom_pull(
            task_ids="extract_tables",
            key="extraction_summary"
        )
        
        # Example: Remove debug artifacts if not needed
        # output_dir = Path(summary['output_dir'])
        # debug_dir = output_dir / "debug"
        # if debug_dir.exists():
        #     shutil.rmtree(debug_dir)
        
        print("Cleanup complete")
    
    cleanup = PythonOperator(
        task_id="cleanup",
        python_callable=cleanup_temp_files,
        provide_context=True,
        trigger_rule="all_done",  # Run even if upstream tasks fail
    )
    
    # Define task dependencies
    wait_for_pdf >> extract_tables >> post_process >> cleanup


# Alternative DAG: Batch processing multiple PDFs
with DAG(
    dag_id="pdf_extraction_batch",
    default_args=default_args,
    description="Batch extract tables from multiple PDF documents",
    schedule_interval="0 2 * * *",  # Run daily at 2 AM
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["pdf", "extraction", "batch"],
) as batch_dag:
    
    from airflow.operators.python import BranchPythonOperator
    from airflow.operators.dummy import DummyOperator
    import glob
    
    def find_pdfs(**context):
        """Find all PDFs in input directory."""
        input_dir = "/data/input/"
        pdf_files = glob.glob(f"{input_dir}/**/*.pdf", recursive=True)
        
        # Push list of files to XCom
        context["task_instance"].xcom_push(key="pdf_files", value=pdf_files)
        
        if pdf_files:
            print(f"Found {len(pdf_files)} PDF files")
            return "process_pdfs"
        else:
            print("No PDF files found")
            return "skip_processing"
    
    find_task = BranchPythonOperator(
        task_id="find_pdfs",
        python_callable=find_pdfs,
        provide_context=True,
    )
    
    skip_task = DummyOperator(task_id="skip_processing")
    
    # Process each PDF (in practice, use dynamic task mapping for parallel processing)
    def process_pdf_batch(**context):
        """Process all PDFs in batch."""
        ti = context["task_instance"]
        pdf_files = ti.xcom_pull(task_ids="find_pdfs", key="pdf_files")
        
        from pdf_reader.adapters.core import AdapterConfig, InputSource, OutputSink, run_extraction
        from pdf_reader.pipeline import PipelineConfig
        
        results = []
        for pdf_file in pdf_files:
            try:
                adapter_config = AdapterConfig(
                    input_source=InputSource(type="file", location=pdf_file),
                    output_sink=OutputSink(type="filesystem", location="/data/output"),
                    pipeline_config=PipelineConfig(dpi=200),
                )
                
                result = run_extraction(adapter_config)
                results.append({
                    "pdf_file": pdf_file,
                    "tables_extracted": result.stats.tables_extracted,
                    "success": True,
                })
            except Exception as e:
                print(f"Error processing {pdf_file}: {e}")
                results.append({
                    "pdf_file": pdf_file,
                    "error": str(e),
                    "success": False,
                })
        
        # Push results to XCom
        context["task_instance"].xcom_push(key="batch_results", value=results)
        
        return results
    
    process_task = PythonOperator(
        task_id="process_pdfs",
        python_callable=process_pdf_batch,
        provide_context=True,
    )
    
    end_task = DummyOperator(
        task_id="end",
        trigger_rule="none_failed_min_one_success",
    )
    
    # Define task dependencies
    find_task >> [skip_task, process_task] >> end_task


