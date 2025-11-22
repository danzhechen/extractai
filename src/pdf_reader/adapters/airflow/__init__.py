"""
Airflow integration for PDF table extraction.

This module provides a custom Airflow operator for running PDF table extraction
as part of Airflow DAGs.

Usage:
    from pdf_reader.adapters.airflow import PdfExtractionOperator
    
    extract = PdfExtractionOperator(
        task_id="extract_tables",
        input_path="{{ params.pdf_path }}",
        output_dir="{{ params.output_dir }}",
        config_path="configs/production.yaml",
    )
"""

from .operators import PdfExtractionOperator

__all__ = ["PdfExtractionOperator"]


