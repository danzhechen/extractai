"""
Example HTTP client for PDF table extraction service.

This script demonstrates how to interact with the PDF extraction HTTP service
using Python's requests library.

Prerequisites:
    - Install requests: pip install requests
    - Start the service: uvicorn pdf_reader.adapters.http.service:app

Usage:
    python examples/integrations/http_client_example.py
"""

import json
import time
from pathlib import Path
from typing import Dict, Any

import requests


class PdfExtractionClient:
    """Client for PDF extraction HTTP service."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize client.
        
        Args:
            base_url: Base URL of the extraction service
        """
        self.base_url = base_url.rstrip("/")
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health.
        
        Returns:
            Health check response
        """
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def submit_extraction(
        self,
        pdf_path: str,
        config: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """Submit PDF extraction job.
        
        Args:
            pdf_path: Path to PDF file
            config: Optional pipeline config overrides
            metadata: Optional job metadata
            
        Returns:
            Job ID
        """
        # Prepare files and data
        files = {
            "file": ("document.pdf", open(pdf_path, "rb"), "application/pdf")
        }
        
        data = {}
        if config:
            data["config"] = json.dumps(config)
        if metadata:
            data["metadata"] = json.dumps(metadata)
        
        # Submit job
        response = requests.post(
            f"{self.base_url}/extract",
            files=files,
            data=data if data else None,
        )
        response.raise_for_status()
        
        result = response.json()
        return result["job_id"]
    
    def get_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status response
        """
        response = requests.get(f"{self.base_url}/status/{job_id}")
        response.raise_for_status()
        return response.json()
    
    def get_results(self, job_id: str) -> Dict[str, Any]:
        """Get extraction results.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Extraction results response
        """
        response = requests.get(f"{self.base_url}/results/{job_id}")
        response.raise_for_status()
        return response.json()
    
    def wait_for_completion(
        self,
        job_id: str,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """Wait for job to complete.
        
        Args:
            job_id: Job identifier
            poll_interval: Time between status checks (seconds)
            timeout: Maximum time to wait (seconds)
            
        Returns:
            Final job status
            
        Raises:
            TimeoutError: If job doesn't complete within timeout
        """
        start_time = time.time()
        
        while True:
            # Check timeout
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")
            
            # Get status
            status = self.get_status(job_id)
            
            # Check if completed or failed
            if status["status"] in ("completed", "failed"):
                return status
            
            # Show progress
            print(f"Job {job_id}: {status['status']} ({status['progress']*100:.1f}%)")
            
            # Wait before next check
            time.sleep(poll_interval)
    
    def download_file(self, job_id: str, filename: str, output_path: str) -> None:
        """Download output file.
        
        Args:
            job_id: Job identifier
            filename: File to download (e.g., "tables/table_0.csv")
            output_path: Local path to save file
        """
        response = requests.get(
            f"{self.base_url}/download/{job_id}/{filename}",
            stream=True,
        )
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Downloaded {filename} to {output_path}")


def example_synchronous_extraction():
    """Example: Synchronous extraction with polling."""
    print("=== Example 1: Synchronous Extraction ===\n")
    
    # Initialize client
    client = PdfExtractionClient()
    
    # Check service health
    health = client.health_check()
    print(f"Service status: {health['status']}")
    print(f"Jobs in queue: {health['jobs_queued']}")
    print()
    
    # Submit extraction job
    pdf_path = "sample/sample.pdf"
    config = {
        "dpi": 300,
        "enable_debug_artifacts": True,
    }
    
    print(f"Submitting extraction job for {pdf_path}...")
    job_id = client.submit_extraction(pdf_path, config=config)
    print(f"Job ID: {job_id}\n")
    
    # Wait for completion
    print("Waiting for job to complete...")
    final_status = client.wait_for_completion(job_id)
    print(f"Job completed: {final_status['status']}\n")
    
    # Get results
    results = client.get_results(job_id)
    print(f"Extracted {results['tables_extracted']} tables")
    print(f"Processed {results['pages_processed']} pages")
    print(f"Elapsed time: {results['elapsed_seconds']:.2f}s")
    print(f"Output directory: {results['output_dir']}\n")
    
    # Print table data
    if results.get("tables"):
        for i, table in enumerate(results["tables"]):
            print(f"Table {i}: {len(table['rows'])} rows")


def example_async_extraction():
    """Example: Asynchronous extraction without polling."""
    print("=== Example 2: Asynchronous Extraction ===\n")
    
    client = PdfExtractionClient()
    
    # Submit multiple jobs
    pdf_files = [
        "sample/sample.pdf",
        # Add more PDFs here
    ]
    
    job_ids = []
    for pdf_path in pdf_files:
        job_id = client.submit_extraction(pdf_path)
        job_ids.append(job_id)
        print(f"Submitted job {job_id} for {pdf_path}")
    
    print(f"\n{len(job_ids)} jobs submitted")
    print("Check status later using job IDs\n")
    
    # Later: check status of jobs
    for job_id in job_ids:
        status = client.get_status(job_id)
        print(f"Job {job_id}: {status['status']} ({status['progress']*100:.1f}%)")


def example_download_results():
    """Example: Download extraction results."""
    print("=== Example 3: Download Results ===\n")
    
    client = PdfExtractionClient()
    
    # Submit job
    job_id = client.submit_extraction("sample/sample.pdf")
    print(f"Job ID: {job_id}")
    
    # Wait for completion
    client.wait_for_completion(job_id)
    
    # Download files
    output_dir = Path("downloads") / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Download manifest
    client.download_file(job_id, "manifest.json", str(output_dir / "manifest.json"))
    
    # Download first table
    client.download_file(job_id, "tables/table_0.csv", str(output_dir / "table_0.csv"))
    
    print(f"\nResults downloaded to {output_dir}")


def example_error_handling():
    """Example: Error handling."""
    print("=== Example 4: Error Handling ===\n")
    
    client = PdfExtractionClient()
    
    try:
        # Try to get status of non-existent job
        status = client.get_status("invalid-job-id")
    except requests.exceptions.HTTPError as e:
        print(f"Expected error: {e}")
        print(f"Status code: {e.response.status_code}")
        print(f"Error detail: {e.response.json()}")


def main():
    """Run all examples."""
    examples = [
        ("Synchronous Extraction", example_synchronous_extraction),
        ("Asynchronous Extraction", example_async_extraction),
        ("Download Results", example_download_results),
        ("Error Handling", example_error_handling),
    ]
    
    print("PDF Extraction HTTP Client Examples\n")
    print("Available examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")
    
    choice = input("\nSelect example (1-4, or 'all'): ").strip()
    
    if choice == "all":
        for name, func in examples:
            print(f"\n{'='*60}")
            func()
            print(f"{'='*60}\n")
            input("Press Enter to continue...")
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        _, func = examples[int(choice) - 1]
        func()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()


