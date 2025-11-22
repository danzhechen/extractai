"""
Integration adapters for workflow orchestration and service deployment.

This module provides first-class adapters for integrating the PDF table extraction
pipeline with common orchestration frameworks (Airflow, Prefect) and as a lightweight
HTTP service.

Key abstractions:
- AdapterConfig: Unified configuration for adapter input/output
- InputSource: Abstract input source (file, URL, S3, GCS, bytes)
- OutputSink: Abstract output destination (filesystem, S3, GCS, database)

Usage:
    # Airflow
    from pdf_reader.adapters.airflow import PdfExtractionOperator
    
    # Prefect
    from pdf_reader.adapters.prefect import extract_tables_flow
    
    # HTTP Service
    from pdf_reader.adapters.http.service import app
"""

from .core import AdapterConfig, InputSource, OutputSink

__all__ = ["AdapterConfig", "InputSource", "OutputSink"]


