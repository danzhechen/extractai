# Confidence Scoring and Position Verification Guide

## Overview

The PDF Reader implements a comprehensive **two-phase confidence scoring system** to ensure table extraction accuracy:

1. **Consensus Confidence**: Agreement across multiple LLM extraction attempts
2. **Position Verification**: Spatial validation against OCR tokens from the original PDF

This dual-verification approach catches both **value errors** (wrong numbers) and **position errors** (correct numbers in wrong cells).

---

## How It Works

### Phase 1: Consensus-Based Confidence (LLM Agreement)

When `llm_consistency_attempts > 1`, the system runs multiple LLM extractions and votes on cell values:

```python
config = PipelineConfig(
    llm_consistency_attempts=3,  # Run extraction 3 times
    llm_consistency_threshold=0.8  # Require 80% agreement
)
```

**Confidence Calculation:**
- **3/3 LLMs agree** → confidence = **1.0** (perfect consensus)
- **2/3 LLMs agree** → confidence = **0.67** (majority consensus)
- **1/3 agree (no consensus)** → confidence = **0.33** (low consensus)

### Phase 2: Position Verification (OCR Cross-Check)

After LLM extraction, the system:
1. Extracts OCR tokens from the original PDF (via pdfplumber)
2. Estimates cell bounding boxes based on table structure
3. Matches each extracted value with OCR tokens at the same position
4. Calculates position confidence based on match quality

**Position Confidence:**
- **Exact match** → confidence = **1.0** (value + position correct)
- **Fuzzy match** (see below) → confidence = **0.8-0.95** (likely correct despite OCR differences)
- **No OCR tokens found** → confidence = **0.3** (empty cell or OCR failure)
- **Value mismatch** → confidence = **0.4** (position error or extraction error)

---

## Character Confusion Detection

The system handles common OCR confusions using a similarity map:

| Character | Commonly Confused With |
|-----------|------------------------|
| `0` | `O`, `o`, `D` |
| `1` | `l`, `I`, `\|`, `i` |
| `5` | `S`, `s` |
| `8` | `B`, `&` |
| `2` | `Z`, `z` |
| `6` | `G`, `b` |
| `9` | `g`, `q` |

**Example:** If LLM extracts `103` but OCR reads `1O3`, the system recognizes the `0`/`O` confusion and still assigns high confidence (~0.9).

---

## Combined Confidence Score

When both consensus and position verification are available, the final confidence is:

```
combined_confidence = (consensus_confidence + position_confidence) / 2.0
```

**Example:**
- Consensus: 3/3 LLMs agree → `1.0`
- Position: Exact OCR match → `1.0`
- **Combined:** `(1.0 + 1.0) / 2 = 1.0` ✅

**Example 2:**
- Consensus: 2/3 LLMs agree → `0.67`
- Position: Fuzzy match (0/O confusion) → `0.85`
- **Combined:** `(0.67 + 0.85) / 2 = 0.76` ⚠️

---

## Configuration Options

### Enable/Disable Position Verification

```yaml
# config.yaml
enable_position_verification: true  # Default: true
position_verification_threshold: 0.7  # Warn below this threshold
```

```python
# Python API
config = PipelineConfig(
    enable_position_verification=True,
    position_verification_threshold=0.7
)
```

### Adjust Fuzzy Matching Sensitivity

Position verification uses two key thresholds:

1. **OCR Confidence Threshold** (`ocr_confidence_threshold`): Minimum OCR confidence to trust (default: 0.7)
2. **Fuzzy Match Threshold**: Minimum similarity for fuzzy match (hardcoded: 0.8)

```python
config = PipelineConfig(
    ocr_confidence_threshold=0.7  # If OCR confidence < 0.7, trust LLM more
)
```

---

## Excel Output with Confidence Highlighting

The Excel output automatically highlights cells based on confidence:

### Color Legend

- 🟢 **Green** (≥ 0.85): High confidence - value likely correct
- 🟡 **Yellow** (0.70-0.84): Medium confidence - review recommended
- 🔴 **Red** (< 0.70): Low confidence - verification required

### Cell Comments

- **Low-confidence cells** (< 0.70) have comments: `"Low confidence: 0.62\nVerify this value"`
- **Table metadata** in cell A1: Consensus confidence, position confidence, overall confidence

### Example Output

```
┌─────────┬─────────┬─────────┐
│ A1 📋  │    B    │    C    │  ← Cell A1 has table metadata comment
├─────────┼─────────┼─────────┤
│  123 🟢 │  456 🟢 │  789 🟡 │  ← 789 has medium confidence
├─────────┼─────────┼─────────┤
│  100 🔴 │  200 🟢 │  300 🟢 │  ← 100 has low confidence + comment
└─────────┴─────────┴─────────┘

Legend (below table):
■ Green: High confidence (≥ 0.85)
■ Yellow: Medium confidence (0.70-0.84)
■ Red: Low confidence (< 0.70) - VERIFY
```

---

## Troubleshooting

### Issue: All Cells Showing Low Confidence

**Possible Causes:**
1. **Position verification disabled** → Enable it:
   ```python
   config.enable_position_verification = True
   ```

2. **No pdfplumber page available** → Check that PDF is loaded correctly
   
3. **OCR tokens not extracting** → Verify PDF contains text (not scanned image)

### Issue: Too Many False Positives (Red Cells)

**Solution:** Adjust fuzzy match threshold or OCR confidence threshold:

```python
config = PipelineConfig(
    ocr_confidence_threshold=0.5  # Trust LLM more (was 0.7)
)
```

### Issue: Character Confusion Not Detected

**Solution:** Add custom confusion pairs to `CHAR_SIMILARITY_MAP` in `position_verifier.py`:

```python
CHAR_SIMILARITY_MAP = {
    ...
    '7': ['/'],  # Add custom confusion
    ...
}
```

---

## API Reference

### PositionVerifier

```python
from pdf_reader.position_verifier import PositionVerifier, OCRToken

verifier = PositionVerifier(
    ocr_confidence_threshold=0.7,  # Min OCR confidence
    fuzzy_match_threshold=0.8,     # Min similarity for fuzzy match
    position_tolerance=0.1          # 10% bbox overlap tolerance
)

# Extract OCR tokens
tokens = verifier.extract_ocr_tokens(page_image, page_obj=pdfplumber_page)

# Verify table
cell_confidences, mismatched_cells, overall_confidence = verifier.verify_table(
    table_spec=table_spec,
    table_bbox=BoundingBox(0, 0, 500, 300),
    ocr_tokens=tokens
)
```

### TableMetadata Confidence Fields

```python
from pdf_reader.models import TableMetadata

meta = TableMetadata(
    ...
    consensus_confidence=0.95,      # LLM agreement score
    position_confidence=0.88,       # OCR match score
    cell_confidences=[[1.0, 0.8], [0.9, 0.7]],  # Per-cell matrix
    mismatched_cells=[(1, 1)]      # Low-confidence cell positions
)
```

---

## Best Practices

1. **Always use consensus extraction** (`llm_consistency_attempts=3`) for critical data
2. **Enable position verification** for financial/numerical data
3. **Review yellow/red cells** in Excel output before using data
4. **Lower OCR threshold** (e.g., 0.5) if PDFs have poor OCR quality
5. **Add custom confusion pairs** for domain-specific character sets

---

## Performance Impact

| Feature | Cost Impact | Latency Impact |
|---------|-------------|----------------|
| Consensus (3 attempts) | **+200%** (3x LLM calls) | **+200%** (3x duration) |
| Position Verification | **$0** (free OCR) | **+5-10%** (token extraction) |

**Recommendation:** Use `llm_consistency_attempts=1` with position verification for fast, cost-effective extraction with good accuracy.

---

## Examples

### High-Confidence Extraction (Ideal)

```
Extracted: "1,234.56"
OCR:       "1,234.56"
Consensus: 3/3 (1.0)
Position:  Exact match (1.0)
Combined:  1.0 ✅
```

### Medium-Confidence (Character Confusion)

```
Extracted: "1O34"
OCR:       "1034"
Consensus: 3/3 (1.0)
Position:  Fuzzy match (0.85) ← 0/O confusion
Combined:  0.925 🟢
```

### Low-Confidence (Position Mismatch)

```
Extracted: "999"
OCR:       "123"
Consensus: 2/3 (0.67)
Position:  Value mismatch (0.4)
Combined:  0.535 🔴 ← VERIFY!
```

---

## Related Documentation

- [Architecture Overview](../architecture.md) - System design
- [API Setup Guide](./api-setup.md) - LLM API configuration
- [Troubleshooting Guide](../troubleshooting.md) - Common issues

---

**Last Updated:** November 2025  
**Version:** 1.0.0

