"""
HTTP service adapter for PDF table extraction.

This module provides a lightweight FastAPI-based HTTP service for running PDF table
extraction as a REST API.

Usage:
    # Start the service
    uvicorn pdf_reader.adapters.http.service:app --host 0.0.0.0 --port 8000
    
    # Or use the CLI
    python -m pdf_reader.adapters.http.service
"""

__all__ = ["app"]


