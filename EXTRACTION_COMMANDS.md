# Sample PDF Extraction Commands

## 🚀 Quick Start - Process All Sample Files

### **Option 1: Automated Batch Processing** (Recommended)

```bash
cd /Users/JerryChen/proj/cursor/pdf-reading-project

# Run the batch script (processes all 6 PDFs)
./run_sample_extraction.sh
```

**What it does:**
- Processes all 6 sample PDFs (first 4 pages each)
- Creates organized output structure:
  ```
  output/position_verification_test/
  ├── assam-1/
  │   └── assam-1_tables.xlsx
  ├── assam-2/
  │   └── assam-2_tables.xlsx
  ├── bihar-1/
  │   └── bihar-1_tables.xlsx
  ├── bihar-2/
  │   └── bihar-2_tables.xlsx
  ├── bom-51/
  │   └── bom-51_tables.xlsx
  └── hyderabad-51-1/
      └── hyderabad-51-1_tables.xlsx
  ```
- Shows progress for each file
- Excel files have color-coded confidence (🟢🟡🔴)

---

## 📋 Individual Commands for Each Sample

Set API key first:
```bash
export PDF_READER_LLM_API_KEY="YOUR_API_KEY_HERE"
cd /Users/JerryChen/proj/cursor/pdf-reading-project
```

### **1. assam-1.pdf** (2.4 MB)

```bash
python -m pdf_reader.cli extract \
  --input sample/assam-1.pdf \
  --output output/position_verification_test/assam-1/assam-1_tables.xlsx \
  --preset smart \
  --worker-type sequential \
  --pages 0-3
```

### **2. assam-2.pdf** (1.6 MB)

```bash
python -m pdf_reader.cli extract \
  --input sample/assam-2.pdf \
  --output output/position_verification_test/assam-2/assam-2_tables.xlsx \
  --preset smart \
  --worker-type sequential \
  --pages 0-3
```

### **3. bihar-1.pdf** (1.4 MB)

```bash
python -m pdf_reader.cli extract \
  --input sample/bihar-1.pdf \
  --output output/position_verification_test/bihar-1/bihar-1_tables.xlsx \
  --preset smart \
  --worker-type sequential \
  --pages 0-3
```

### **4. bihar-2.pdf** (253 KB - smallest)

```bash
python -m pdf_reader.cli extract \
  --input sample/bihar-2.pdf \
  --output output/position_verification_test/bihar-2/bihar-2_tables.xlsx \
  --preset smart \
  --worker-type sequential \
  --pages 0-3
```

### **5. bom-51.pdf** (3.2 MB)

```bash
python -m pdf_reader.cli extract \
  --input sample/bom-51.pdf \
  --output output/position_verification_test/bom-51/bom-51_tables.xlsx \
  --preset smart \
  --worker-type sequential \
  --pages 0-3
```

### **6. hyderabad-51-1.pdf** (4.1 MB - largest)

```bash
python -m pdf_reader.cli extract \
  --input sample/hyderabad-51-1.pdf \
  --output output/position_verification_test/hyderabad-51-1/hyderabad-51-1_tables.xlsx \
  --preset smart \
  --worker-type sequential \
  --pages 0-3
```

---

## 🔧 Command Options Explained

| Option | Value | Description |
|--------|-------|-------------|
| `--input` | `sample/*.pdf` | Input PDF file path |
| `--output` | `output/.../file.xlsx` | Output Excel file with color coding |
| `--preset` | `smart` | FREE Gemini 2.5 Pro (default) |
| `--worker-type` | `sequential` | Process pages one at a time (stable) |
| `--pages` | `0-3` | Process first 4 pages (0-indexed) |
| `--llm-api-key` | `AIza...` | API key (or use env var) |

---

## 📊 What to Expect in Excel Output

Each Excel file will have:

### **Color-Coded Cells:**
- 🟢 **Green** (≥0.85): High confidence - value verified
- 🟡 **Yellow** (0.70-0.84): Medium confidence - review recommended
- 🔴 **Red** (<0.70): Low confidence - VERIFY THIS VALUE

### **Cell A1 Metadata:**
Click on cell A1 of each table to see:
- Consensus confidence (LLM agreement)
- Position confidence (OCR match)
- Overall confidence
- Number of low-confidence cells

### **Red Cell Comments:**
Hover/click on red cells to see:
```
Low confidence: 0.62
Verify this value
```

### **Legend Below Each Table:**
```
Confidence Legend:
■ Green (≥ 0.85): High confidence
■ Yellow (0.70-0.84): Review recommended  
■ Red (< 0.70): VERIFY THIS VALUE
```

---

## 🧪 Test Single File First (Recommended)

Start with the smallest file to verify everything works:

```bash
cd /Users/JerryChen/proj/cursor/pdf-reading-project
export PDF_READER_LLM_API_KEY="YOUR_API_KEY_HERE"

# Test with bihar-2.pdf (253 KB - fastest)
python -m pdf_reader.cli extract \
  --input sample/bihar-2.pdf \
  --output output/test_single.xlsx \
  --preset smart \
  --worker-type sequential \
  --pages 0-1

# Open the Excel file to verify color coding works
open output/test_single.xlsx  # macOS
# or
xdg-open output/test_single.xlsx  # Linux
```

**Expected time:** ~30-60 seconds per page with Gemini 2.5 Pro

---

## 🎯 Advanced Options

### Process ALL Pages (No Limit)

```bash
python -m pdf_reader.cli extract \
  --input sample/assam-1.pdf \
  --output output/assam-1_full.xlsx \
  --preset smart \
  --worker-type sequential
  # Remove --pages flag to process all pages
```

### Enable Consensus for Higher Confidence (3x cost)

```bash
python -m pdf_reader.cli extract \
  --input sample/assam-1.pdf \
  --output output/assam-1_consensus.xlsx \
  --preset smart \
  --worker-type sequential \
  --pages 0-3 \
  --llm-consistency-attempts 3  # Run LLM 3 times per table
```

### Use Premium Model (Gemini 3.0 Pro)

```bash
python -m pdf_reader.cli extract \
  --input sample/assam-1.pdf \
  --output output/assam-1_premium.xlsx \
  --preset premium \
  --worker-type sequential \
  --pages 0-3
```

### Disable Position Verification (Faster, No QA)

Create `config_no_verify.yaml`:
```yaml
enable_position_verification: false
```

Then run:
```bash
python -m pdf_reader.cli extract \
  --input sample/assam-1.pdf \
  --output output/assam-1_no_verify.xlsx \
  --config config_no_verify.yaml \
  --preset smart \
  --pages 0-3
```

---

## 📂 Output Directory Structure

After running batch extraction:

```
output/position_verification_test/
├── assam-1/
│   └── assam-1_tables.xlsx          # 🟢🟡🔴 Color-coded tables
├── assam-2/
│   └── assam-2_tables.xlsx
├── bihar-1/
│   └── bihar-1_tables.xlsx
├── bihar-2/
│   └── bihar-2_tables.xlsx          # Smallest, fastest to test
├── bom-51/
│   └── bom-51_tables.xlsx
└── hyderabad-51-1/
    └── hyderabad-51-1_tables.xlsx   # Largest file
```

---

## ⏱️ Estimated Processing Times

| File | Size | Pages | Estimated Time |
|------|------|-------|----------------|
| bihar-2.pdf | 253 KB | 4 pages | ~2-3 min |
| bihar-1.pdf | 1.4 MB | 4 pages | ~2-3 min |
| assam-2.pdf | 1.6 MB | 4 pages | ~2-3 min |
| assam-1.pdf | 2.4 MB | 4 pages | ~2-3 min |
| bom-51.pdf | 3.2 MB | 4 pages | ~2-3 min |
| hyderabad-51-1.pdf | 4.1 MB | 4 pages | ~2-3 min |
| **Total (all 6)** | ~13 MB | 24 pages | **~15-20 min** |

*Times assume Gemini 2.5 Pro with sequential processing (~30-60s per page)*

---

## 🛠️ Troubleshooting

### Issue: API Key Not Set

```bash
# Set it as environment variable
export PDF_READER_LLM_API_KEY="YOUR_API_KEY_HERE"

# Or pass directly via CLI
--llm-api-key "YOUR_API_KEY_HERE"
```

### Issue: Output Directory Doesn't Exist

```bash
mkdir -p output/position_verification_test/{assam-1,assam-2,bihar-1,bihar-2,bom-51,hyderabad-51-1}
```

### Issue: Too Many Red Cells

Lower the OCR confidence threshold:
```bash
python -m pdf_reader.cli extract \
  --input sample/assam-1.pdf \
  --output output/test.xlsx \
  --preset smart \
  --ocr-confidence-threshold 0.5  # Trust LLM more
```

---

## 📖 Related Documentation

- **`POSITION_VERIFICATION_SUMMARY.md`** - Implementation details
- **`docs/guides/confidence-scoring.md`** - Confidence scoring guide
- **`README.md`** - General usage guide

---

**Ready to extract!** 🚀

Run `./run_sample_extraction.sh` to process all samples or pick individual commands above.

