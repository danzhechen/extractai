"""
Prefect integration for PDF table extraction.

This module provides Prefect flows and tasks for running PDF table extraction
as part of Prefect 2.x workflows.

Usage:
    from pdf_reader.adapters.prefect import extract_tables_flow
    
    # Run locally
    result = extract_tables_flow(
        input_path="document.pdf",
        output_dir="output/",
    )
    
    # Deploy to Prefect Cloud
    extract_tables_flow.deploy(
        name="pdf-extraction-prod",
        work_pool_name="kubernetes",
    )
"""

from .flows import extract_tables_flow, extract_tables_task

__all__ = ["extract_tables_flow", "extract_tables_task"]


