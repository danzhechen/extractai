# Multi-stage Dockerfile for PDF extraction HTTP service
# Stage 1: Build dependencies
FROM python:3.10-slim AS builder

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpoppler-cpp-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn[standard] python-multipart

# Stage 2: Runtime image
FROM python:3.10-slim

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpoppler-cpp0v5 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /data/input /data/output && \
    chown -R appuser:appuser /app /data

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser requirements.txt ./

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run the service
CMD ["uvicorn", "src.pdf_reader.adapters.http.service:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]


