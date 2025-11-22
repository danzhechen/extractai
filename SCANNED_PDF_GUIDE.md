# Guide: Working with Scanned PDFs (Real-World Usage)

## 🎯 **Reality Check**

Most PDFs in the real world are **scanned images**, not text-based documents. This means:

| Feature | Works with Scanned PDFs? |
|---------|--------------------------|
| **LLM Extraction** | ✅ YES - LLM reads images directly |
| **Position Verification** | ❌ NO - Requires native PDF text |
| **Consensus Confidence** | ✅ YES - Run LLM multiple times and vote |

**Bottom Line:** For scanned PDFs, **consensus voting is the only way to get confidence scores**.

---

## 🚀 **Quick Start: Choose Your Mode**

### **Mode 1: FAST** (Default - No Confidence)

**Use when:** Speed and cost are priorities

```bash
cd /Users/JerryChen/proj/cursor/pdf-reading-project
source venv/bin/activate
export PDF_READER_LLM_API_KEY="YOUR_API_KEY_HERE"

# Fast mode (single attempt)
./run_sample_extraction_v2.sh fast
```

**What you get:**
- ⚡ **Fast:** ~40-60 sec per page
- 💰 **Cheap:** $0.50 per 1000 pages
- ❌ **No confidence scores**
- 📊 Excel shows data without color coding

---

### **Mode 2: QUALITY** (With Confidence)

**Use when:** Accuracy is critical, need to verify results

```bash
cd /Users/JerryChen/proj/cursor/pdf-reading-project
source venv/bin/activate
export PDF_READER_LLM_API_KEY="YOUR_API_KEY_HERE"

# Quality mode (consensus voting)
./run_sample_extraction_v2.sh quality
```

**What you get:**
- 🎯 **Accurate:** LLM runs 3x, votes on results
- 💰 **Cost:** $1.50 per 1000 pages (3x)
- ✅ **Confidence scores:** 🟢🟡🔴 color-coded cells
- 📊 Excel highlights low-confidence cells

---

## 📋 **Individual Commands**

### **Fast Mode (Single Attempt)**

```bash
python -m pdf_reader.cli extract \
  --input sample/assam-1.pdf \
  --output output/assam-1_fast.xlsx \
  --config config.scanned_fast.yaml \
  --pages 0-3
```

### **Quality Mode (Consensus)**

```bash
python -m pdf_reader.cli extract \
  --input sample/assam-1.pdf \
  --output output/assam-1_quality.xlsx \
  --config config.scanned_quality.yaml \
  --pages 0-3
```

### **Custom (Manual Control)**

```bash
python -m pdf_reader.cli extract \
  --input sample/assam-1.pdf \
  --output output/assam-1_custom.xlsx \
  --preset smart \
  --llm-consistency-attempts 3 \
  --worker-type sequential \
  --pages 0-3
```

---

## 📊 **Excel Output Comparison**

### **Fast Mode (No Confidence)**

```
Table: table_1
┌─────────┬─────────┬─────────┐
│  Value  │  Amount │  Total  │  
├─────────┼─────────┼─────────┤
│  1,234  │   567   │   890   │  ← No colors
│   100   │   200   │   300   │  ← All cells uncolored
└─────────┴─────────┴─────────┘

ℹ️ Confidence Scoring: Not Available
Single LLM attempt used (no consensus verification)
To enable: Use quality mode or --llm-consistency-attempts 3
```

### **Quality Mode (With Confidence)**

```
Table: table_1
┌─────────┬─────────┬─────────┐
│  Value  │  Amount │  Total  │  
├─────────┼─────────┼─────────┤
│ 1,234🟢 │  567🟢  │  890🟡  │  ← Color-coded
│  100🔴  │  200🟢  │  300🟢  │  ← Red = needs review
└─────────┴─────────┴─────────┘

Confidence Legend:
🟢 High (≥0.85): 3/3 LLMs agree
🟡 Medium (0.70-0.84): 2/3 LLMs agree  
🔴 Low (<0.70): No consensus - VERIFY
```

---

## 💰 **Cost & Performance Comparison**

| Mode | LLM Calls | Cost/1K Pages | Time/Page | Confidence |
|------|-----------|---------------|-----------|------------|
| **Fast** | 1x | $0.50 | ~40-60s | ❌ None |
| **Quality** | 3x | $1.50 | ~120-180s | ✅ Yes |

**Example: 100 pages**
- Fast: $0.05, ~1-1.5 hours
- Quality: $0.15, ~3-5 hours

---

## 🎯 **Recommended Workflow**

### **1. Fast Extraction First** (Exploratory)

```bash
# Quick extraction to see what's in the PDFs
./run_sample_extraction_v2.sh fast
```

**Review the results:**
- Check if data looks reasonable
- Identify critical tables that need verification

### **2. Quality Extraction for Critical Data**

```bash
# Re-run only critical PDFs with consensus
python -m pdf_reader.cli extract \
  --input sample/critical_document.pdf \
  --output output/critical_quality.xlsx \
  --config config.scanned_quality.yaml \
  --pages 0-10
```

**Benefits:**
- Save cost on exploratory work
- Apply quality mode only where needed

---

## 🔧 **Configuration Files**

### **config.scanned_fast.yaml** (Default)

```yaml
extraction_preset: smart
llm_model: gemini-2.5-pro  # FREE
llm_consistency_attempts: 1  # Single attempt
enable_position_verification: false  # Disabled for scanned PDFs
worker_type: thread
max_workers: 2
```

### **config.scanned_quality.yaml** (High Accuracy)

```yaml
extraction_preset: smart
llm_model: gemini-2.5-pro  # FREE
llm_consistency_attempts: 3  # Consensus voting
llm_consistency_threshold: 0.8  # 80% agreement required
enable_position_verification: false  # Disabled for scanned PDFs
worker_type: sequential  # More stable
```

---

## ⚙️ **Advanced Options**

### **Adjust Consensus Threshold**

```yaml
llm_consistency_threshold: 0.7  # More lenient (accept 2/3 with 70% match)
# or
llm_consistency_threshold: 1.0  # Strict (require 3/3 exact match)
```

### **Use Premium Model for Critical Documents**

```yaml
llm_model: gemini-3.0-pro  # Better quality (PAID)
llm_model_escalation: null  # No fallback needed
```

### **Parallel Processing for Speed**

```yaml
worker_type: thread
max_workers: 4  # Process 4 pages simultaneously
```

**⚠️ Warning:** Parallel with consensus = 12 concurrent LLM calls! Check API rate limits.

---

## 🐛 **Troubleshooting**

### **Issue: Too many red cells in quality mode**

**Cause:** LLM is inconsistent in number formatting (e.g., "1,234" vs "1234")

**Solution:** This is expected! Red cells show where LLM gave different answers across 3 attempts. Manually verify these cells.

### **Issue: Parallel mode crashes**

**Cause:** Threading bug with OpenCV/PIL

**Solution:** Use sequential mode:
```yaml
worker_type: sequential
```

### **Issue: API rate limits**

**Cause:** Too many concurrent LLM calls

**Solution:** Reduce workers:
```yaml
max_workers: 1  # Or 2
```

---

## 📈 **Best Practices**

1. **Start with fast mode** - Get quick results first
2. **Use quality mode selectively** - Only for critical/financial data
3. **Review red cells** - Always manually verify low-confidence cells
4. **Batch by importance** - Run critical docs separately with quality mode
5. **Monitor costs** - Track your LLM usage

---

## 🎓 **Key Takeaways**

✅ **Scanned PDFs work great** with LLM extraction  
✅ **Consensus is the only confidence option** for scanned PDFs  
✅ **Fast mode is default** - enables/disable confidence as needed  
✅ **Position verification is disabled** - won't work with scanned PDFs  
✅ **Quality costs 3x** - but gives verifiable confidence scores  

---

## 🚀 **Ready to Extract!**

**For most use cases (fast extraction):**
```bash
./run_sample_extraction_v2.sh fast
```

**For critical data (with confidence):**
```bash
./run_sample_extraction_v2.sh quality
```

**That's it!** The system is now optimized for real-world scanned PDFs. 🎉

