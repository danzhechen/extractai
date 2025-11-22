# Installation Guide

This guide covers installation and setup of the PDF table extraction pipeline.

## Prerequisites

- **Python**: 3.8 or higher
- **pip**: Python package manager (usually included with Python)
- **System dependencies**: None required (uses pure Python libraries)

## Installation Methods

### Method 1: From Source (Development)

1. **Clone or download the repository**:
   ```bash
   git clone <repository-url>
   cd pdf-reading-project
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Method 2: Install as Package (Future)

Once the package is published to PyPI:

```bash
pip install pdf-reading-project
```

## System Dependencies

The pipeline uses pure Python libraries and doesn't require system-level dependencies. However:

- **PDF processing**: Uses `pdfplumber` (pure Python)
- **Image processing**: Uses `Pillow` (may require system libraries on some platforms)
- **YAML config**: Uses `pyyaml` (pure Python)

### Optional: System Libraries for Image Processing

On some systems, you may need to install system libraries for Pillow:

**Ubuntu/Debian**:
```bash
sudo apt-get install libjpeg-dev zlib1g-dev libtiff-dev
```

**macOS** (with Homebrew):
```bash
brew install libjpeg zlib libtiff
```

**Windows**: Usually no additional setup needed

## Verification

Test that the installation works:

```bash
# Test CLI
python -m pdf_reader extract --help

# Test Python import
python -c "from pdf_reader import PipelineRunner; print('OK')"
```

## Environment Setup

### Virtual Environment

Using a virtual environment is recommended to avoid dependency conflicts:

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### API Keys (Optional)

If using LLM fallback, set your API key:

**Environment variable** (recommended):
```bash
export PDF_READER_LLM_API_KEY=sk-...
```

**Config file**:
```yaml
# config.yaml
llm_api_key: sk-...
```

**CLI argument**:
```bash
python -m pdf_reader extract --input document.pdf --llm-api-key sk-...
```

**Note**: Environment variables are recommended for security.

## Development Setup

For development work:

1. **Clone repository**:
   ```bash
   git clone <repository-url>
   cd pdf-reading-project
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install in development mode** (optional):
   ```bash
   pip install -e .
   ```

5. **Run tests**:
   ```bash
   pytest
   ```

## Platform-Specific Notes

### Linux

No special requirements. Install dependencies as usual:

```bash
pip install -r requirements.txt
```

### macOS

No special requirements. If you encounter issues with Pillow:

```bash
brew install libjpeg zlib libtiff
pip install --upgrade pillow
```

### Windows

No special requirements. Use PowerShell or Command Prompt:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Troubleshooting Installation

### Import Errors

If you get import errors:

1. **Check Python version**:
   ```bash
   python --version  # Should be 3.8+
   ```

2. **Verify virtual environment is activated**:
   ```bash
   which python  # Should point to venv/bin/python
   ```

3. **Reinstall dependencies**:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

### Pillow Installation Issues

If Pillow fails to install:

1. **Install system libraries** (see above)
2. **Upgrade pip**:
   ```bash
   pip install --upgrade pip
   ```
3. **Reinstall Pillow**:
   ```bash
   pip install --upgrade --force-reinstall pillow
   ```

### YAML Parsing Issues

If YAML config files don't work:

1. **Verify pyyaml is installed**:
   ```bash
   pip install pyyaml
   ```

## Next Steps

After installation:

1. **Try the quick start**: See [Getting Started Guide](guides/getting-started.md)
2. **Read the configuration guide**: See [Configuration Guide](guides/configuration.md)
3. **Explore examples**: See `examples/` directory

## See Also

- [Getting Started Guide](guides/getting-started.md) - Quick start tutorial
- [Configuration Guide](guides/configuration.md) - Configuration options
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions



