# PDF Table Extractor with Position Verification

> **AI-powered table extraction from PDFs with intelligent confidence scoring**

Extract tables from PDF documents using state-of-the-art LLM technology (Google Gemini), with optional position verification and consensus voting for accuracy validation.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

### Core Capabilities
- 🤖 **LLM-Powered Extraction** - Uses Google Gemini 2.5 Pro (FREE tier) for accurate table detection
- 📊 **Excel Output** - Clean, formatted Excel files with optional confidence highlighting
- 🎯 **Consensus Voting** - Run extraction multiple times and vote for accuracy
- 🔍 **Position Verification** - Cross-check values with PDF text (for text-based PDFs)
- 🚀 **Parallel Processing** - Speed up extraction with multi-threading
- 📈 **Production Ready** - Comprehensive error handling and logging

### Intelligence Features
- **Confidence Scoring** - Visual highlighting of low-confidence cells (🟢🟡🔴)
- **Character Confusion Detection** - Handles common OCR errors (0/O, 1/l, 5/S, 8/B)
- **Scanned PDF Support** - Works with both text-based and image-based PDFs
- **Adaptive Strategies** - Automatically adjusts based on PDF type

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pdf-reading-project.git
cd pdf-reading-project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Set Up API Key

Get a free Google Gemini API key from: https://makersuite.google.com/app/apikey

```bash
# Set environment variable
export PDF_READER_LLM_API_KEY="your-api-key-here"

# Or create .env file
echo "PDF_READER_LLM_API_KEY=your-api-key-here" > .env
```

### 3. Extract Your First Table

```bash
# Basic extraction
python -m pdf_reader.cli extract \
  --input sample/your-document.pdf \
  --output output/tables.xlsx \
  --preset smart

# Open the Excel file
open output/tables.xlsx
```

**That's it!** Your tables are now in Excel format. 🎉

---

## 📖 Usage

### Command-Line Interface

#### **Basic Extraction**
```bash
python -m pdf_reader.cli extract \
  --input document.pdf \
  --output tables.xlsx
```

#### **With Specific Pages**
```bash
python -m pdf_reader.cli extract \
  --input document.pdf \
  --output tables.xlsx \
  --pages 0-5  # Extract pages 0 through 5
```

#### **Parallel Processing (Faster)**
```bash
python -m pdf_reader.cli extract \
  --input document.pdf \
  --output tables.xlsx \
  --worker-type thread \
  --max-workers 4
```

### Configuration Presets

| Preset | Use Case | Speed | Confidence |
|--------|----------|-------|------------|
| **`smart`** | General use (default) | Fast | None |
| **`premium`** | Best quality | Medium | High |
| **`offline`** | No API calls | Fastest | None |

#### **Using Presets**
```bash
# Default: Fast and free
python -m pdf_reader.cli extract --input doc.pdf --output out.xlsx --preset smart

# Premium: Best quality (uses Gemini 3.0 Pro)
python -m pdf_reader.cli extract --input doc.pdf --output out.xlsx --preset premium

# Offline: Computer vision only (no LLM)
python -m pdf_reader.cli extract --input doc.pdf --output out.xlsx --preset offline
```

---

## 🎯 Working with Scanned PDFs

Most real-world PDFs are scanned images. We provide optimized configs for this:

### **Fast Mode** (No Confidence - Recommended for Exploration)

```bash
python -m pdf_reader.cli extract \
  --input document.pdf \
  --output output.xlsx \
  --config config.scanned_fast.yaml
```

- ⚡ **Fast**: Single LLM pass
- ❌ **No confidence scores**

### **Quality Mode** (With Confidence - For Critical Data)

```bash
python -m pdf_reader.cli extract \
  --input document.pdf \
  --output output.xlsx \
  --config config.scanned_quality.yaml
```

- 🎯 **Accurate**: 3x LLM attempts with voting
- ✅ **Confidence scores**: 🟢🟡🔴 color-coded cells

### **Batch Processing**

```bash
# Fast mode (all sample PDFs)
./run_sample_extraction_v2.sh fast

# Quality mode (with confidence scoring)
./run_sample_extraction_v2.sh quality
```


---

## 📊 Excel Output

### Without Confidence Scoring

```
┌─────────┬─────────┬─────────┐
│  Value  │  Amount │  Total  │
├─────────┼─────────┼─────────┤
│  1,234  │   567   │   890   │
│   100   │   200   │   300   │
└─────────┴─────────┴─────────┘

ℹ️ Note: "Confidence scoring not available"
```

### With Confidence Scoring

```
┌─────────┬─────────┬─────────┐
│  Value  │  Amount │  Total  │
├─────────┼─────────┼─────────┤
│ 1,234🟢 │  567🟢  │  890🟡  │  ← Color-coded
│  100🔴  │  200🟢  │  300🟢  │  ← Red needs review
└─────────┴─────────┴─────────┘

Legend:
🟢 Green (≥0.85): High confidence
🟡 Yellow (0.70-0.84): Review recommended
🔴 Red (<0.70): Verify manually
```

**Features:**
- Click **cell A1** for table metadata
- **Red cells** have comments explaining the issue
- **Legend** below each table

---

## 🔧 Advanced Configuration

### Python API

```python
from pdf_reader.pipeline import PipelineRunner, PipelineConfig

# Configure extraction
config = PipelineConfig(
    extraction_preset="smart",
    llm_consistency_attempts=3,  # Enable consensus
    worker_type="thread",
    max_workers=2
)

# Run extraction
runner = PipelineRunner()
result = runner.extract_tables("document.pdf", config=config)

# Access results
for table, metadata in zip(result.tables, result.metadata):
    print(f"Table {metadata.table_id}: {len(table.rows)} rows")
    if metadata.average_confidence:
        print(f"  Confidence: {metadata.average_confidence:.2f}")
```

### Configuration Files

Create custom configs for your workflow:

```yaml
# my_config.yaml
extraction_preset: smart
llm_model: gemini-2.5-pro
llm_consistency_attempts: 3  # Consensus voting
enable_position_verification: false  # For scanned PDFs
worker_type: thread
max_workers: 2
log_level: INFO
```

Then use it:

```bash
python -m pdf_reader.cli extract \
  --input document.pdf \
  --output tables.xlsx \
  --config my_config.yaml
```

---

## 📚 Documentation

- [**docs/guides/confidence-scoring.md**](docs/guides/confidence-scoring.md) - How confidence scoring works
- [**docs/guides/api-setup.md**](docs/guides/api-setup.md) - API key configuration
- [**docs/architecture.md**](docs/architecture.md) - System architecture overview

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_position_verification.py -v

# Run with coverage
pytest tests/ --cov=src/pdf_reader --cov-report=html
```

---

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'pdf_reader'"

**Solution:** Install the package in development mode
```bash
pip install -e .
```

### Issue: "API key not found"

**Solution:** Set the environment variable
```bash
export PDF_READER_LLM_API_KEY="your-key-here"
```

### Issue: Too many red cells in output

**Explanation:** This is expected with consensus voting! Red cells show where the LLM gave different answers across 3 attempts. Manually verify these cells.

### Issue: Parallel mode crashes

**Solution:** Use sequential mode
```bash
--worker-type sequential
```

See [docs/troubleshooting.md](docs/troubleshooting.md) for more issues and solutions.

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Google Gemini** - For providing free LLM API access
- **pdfplumber** - For excellent PDF parsing
- **OpenCV** - For computer vision capabilities

---

Made with ❤️ for the open-source community
