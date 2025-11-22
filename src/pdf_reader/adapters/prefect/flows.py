"""
Prefect flows and tasks for PDF table extraction.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from prefect import flow, task
    from prefect.blocks.system import JSON
    from prefect.runtime import flow_run, task_run
except ImportError:
    raise ImportError(
        "Prefect is not installed. Install with: pip install pdf-reader[prefect] "
        "or pip install prefect>=2.10.0"
    )

from ...pipeline import PipelineConfig
from ..core import AdapterConfig, InputSource, OutputSink, run_extraction

logger = logging.getLogger(__name__)


@task(
    name="extract-pdf-tables",
    description="Extract tables from a PDF document",
    retries=2,
    retry_delay_seconds=60,
    tags=["pdf", "extraction"],
)
def extract_tables_task(
    input_path: str,
    output_dir: str,
    config: Optional[PipelineConfig] = None,
    run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Prefect task for PDF table extraction.
    
    This task wraps the extraction pipeline with Prefect's retry and caching capabilities.
    
    Args:
        input_path: Path to input PDF file
        output_dir: Directory for output artifacts
        config: Optional PipelineConfig instance
        run_id: Optional run identifier
        metadata: Additional run metadata
        
    Returns:
        Dict with extraction summary
        
    Example:
        >>> from prefect import flow
        >>> from pdf_reader.adapters.prefect import extract_tables_task
        >>> 
        >>> @flow
        ... def my_flow():
        ...     result = extract_tables_task(
        ...         input_path="document.pdf",
        ...         output_dir="output/",
        ...     )
        ...     return result
    """
    # Add Prefect context to metadata
    run_metadata = metadata or {}
    
    try:
        run_metadata.update({
            "prefect_flow_run_id": flow_run.id if flow_run else None,
            "prefect_flow_run_name": flow_run.name if flow_run else None,
            "prefect_task_run_id": task_run.id if task_run else None,
            "prefect_task_run_name": task_run.name if task_run else None,
        })
    except Exception as e:
        logger.warning(f"Could not add Prefect context to metadata: {e}")
    
    # Use default config if not provided
    if config is None:
        config = PipelineConfig()
    
    # Create adapter config
    adapter_config = AdapterConfig(
        input_source=InputSource(type="file", location=input_path),
        output_sink=OutputSink(type="filesystem", location=output_dir),
        pipeline_config=config,
        run_id=run_id,
        metadata=run_metadata,
    )
    
    # Run extraction
    result = run_extraction(adapter_config)
    
    # Return summary
    return {
        "tables_extracted": result.stats.tables_extracted,
        "pages_processed": result.stats.pages_processed,
        "elapsed_seconds": result.stats.elapsed_seconds,
        "run_id": adapter_config.run_id,
        "output_dir": str(Path(output_dir) / adapter_config.run_id),
    }


@flow(
    name="pdf-table-extraction",
    description="Extract tables from PDF documents",
    version="1.0.0",
)
def extract_tables_flow(
    input_path: str,
    output_dir: str,
    config: Optional[PipelineConfig] = None,
    config_block_name: Optional[str] = None,
    run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Prefect flow for PDF table extraction.
    
    This flow orchestrates the PDF table extraction pipeline with optional configuration
    loading from Prefect blocks.
    
    Args:
        input_path: Path to input PDF file
        output_dir: Directory for output artifacts
        config: Optional PipelineConfig instance (takes precedence over config_block_name)
        config_block_name: Optional name of Prefect JSON block containing config
        run_id: Optional run identifier (auto-generated if not provided)
        metadata: Additional run metadata dict
        
    Returns:
        Dict with extraction summary
        
    Example:
        >>> # Run locally
        >>> result = extract_tables_flow(
        ...     input_path="document.pdf",
        ...     output_dir="output/",
        ... )
        >>> 
        >>> # Run with config from Prefect block
        >>> result = extract_tables_flow(
        ...     input_path="document.pdf",
        ...     output_dir="output/",
        ...     config_block_name="pdf-extraction-config",
        ... )
        >>> 
        >>> # Deploy to Prefect Cloud
        >>> extract_tables_flow.deploy(
        ...     name="pdf-extraction-prod",
        ...     work_pool_name="kubernetes",
        ...     parameters={
        ...         "config_block_name": "pdf-extraction-config",
        ...     },
        ... )
    """
    logger.info(f"Starting PDF extraction flow: {input_path}")
    
    # Load config from Prefect block if specified and config not provided
    if config is None and config_block_name:
        logger.info(f"Loading config from Prefect block: {config_block_name}")
        try:
            json_block = JSON.load(config_block_name)
            config_dict = json_block.value
            config = PipelineConfig(**config_dict)
            logger.info(f"Loaded config from block: {config_block_name}")
        except Exception as e:
            logger.warning(f"Could not load config from block {config_block_name}: {e}")
            logger.info("Using default config")
            config = PipelineConfig()
    elif config is None:
        config = PipelineConfig()
    
    # Run extraction task
    result = extract_tables_task(
        input_path=input_path,
        output_dir=output_dir,
        config=config,
        run_id=run_id,
        metadata=metadata,
    )
    
    logger.info(
        f"Extraction complete: {result['tables_extracted']} tables extracted "
        f"in {result['elapsed_seconds']:.2f}s"
    )
    
    return result


@flow(
    name="pdf-batch-extraction",
    description="Batch extract tables from multiple PDF documents",
    version="1.0.0",
)
def batch_extract_tables_flow(
    input_paths: list[str],
    output_dir: str,
    config: Optional[PipelineConfig] = None,
    config_block_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Prefect flow for batch PDF table extraction.
    
    This flow processes multiple PDF files in parallel using Prefect's task concurrency.
    
    Args:
        input_paths: List of paths to input PDF files
        output_dir: Directory for output artifacts
        config: Optional PipelineConfig instance
        config_block_name: Optional name of Prefect JSON block containing config
        metadata: Additional run metadata dict
        
    Returns:
        Dict with batch summary (total files, successful, failed, etc.)
        
    Example:
        >>> result = batch_extract_tables_flow(
        ...     input_paths=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
        ...     output_dir="output/",
        ... )
        >>> print(f"Processed {result['total_files']} files")
    """
    logger.info(f"Starting batch extraction for {len(input_paths)} files")
    
    # Load config if needed
    if config is None and config_block_name:
        try:
            json_block = JSON.load(config_block_name)
            config_dict = json_block.value
            config = PipelineConfig(**config_dict)
        except Exception as e:
            logger.warning(f"Could not load config from block: {e}")
            config = PipelineConfig()
    elif config is None:
        config = PipelineConfig()
    
    # Submit tasks for each PDF (Prefect handles parallelism)
    futures = []
    for pdf_path in input_paths:
        future = extract_tables_task.submit(
            input_path=pdf_path,
            output_dir=output_dir,
            config=config,
            metadata={
                **(metadata or {}),
                "batch_file": pdf_path,
            },
        )
        futures.append((pdf_path, future))
    
    # Collect results
    results = []
    successful = 0
    failed = 0
    
    for pdf_path, future in futures:
        try:
            result = future.result()
            results.append({
                "pdf_path": pdf_path,
                "success": True,
                **result,
            })
            successful += 1
            logger.info(f"Successfully processed {pdf_path}")
        except Exception as e:
            results.append({
                "pdf_path": pdf_path,
                "success": False,
                "error": str(e),
            })
            failed += 1
            logger.error(f"Failed to process {pdf_path}: {e}")
    
    # Prepare summary
    summary = {
        "total_files": len(input_paths),
        "successful": successful,
        "failed": failed,
        "results": results,
    }
    
    logger.info(
        f"Batch extraction complete: {successful}/{len(input_paths)} files successful"
    )
    
    return summary


