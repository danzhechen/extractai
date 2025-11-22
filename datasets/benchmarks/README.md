# Benchmark Dataset

This directory contains the benchmark dataset for evaluating PDF table extraction accuracy.

## Dataset Overview

The benchmark dataset consists of **15+ tables across 5+ PDF documents** with diverse characteristics:

- **Bordered tables**: Tables with clear cell borders (5 tables)
- **Borderless tables**: Tables with alignment-based cells (3 tables)
- **Multi-page tables**: Tables spanning multiple pages (2 tables)
- **Merged cells**: Tables with rowspan/colspan (3 tables)
- **Low-quality scans**: Faded lines, skewed pages (2 tables)
- **Irregular tables**: Ragged rows, non-rectangular structure (2 tables)

## Directory Structure

```
datasets/benchmarks/
├── README.md              # This file
├── pdfs/                  # PDF files
│   ├── simple_table.pdf
│   ├── merged_cells.pdf
│   └── ...
├── annotations/           # Ground truth annotations
│   ├── simple_table.json
│   ├── merged_cells.json
│   └── ...
└── LICENSE.md            # Dataset license information
```

## Annotation Format

Ground truth annotations are stored as JSON files with the following schema:

```json
{
  "pdf_file": "document.pdf",
  "page_index": 0,
  "metadata": {
    "source": "Synthetic / Public Domain / CC0",
    "annotator": "Name",
    "date": "2025-11-21",
    "notes": "Optional notes about this annotation"
  },
  "tables": [
    {
      "table_id": "table_0",
      "bbox": {"x0": 0.1, "y0": 0.2, "x1": 0.9, "y1": 0.8},
      "n_rows": 4,
      "n_cols": 3,
      "cells": [
        {
          "row": 0,
          "col": 0,
          "rowspan": 1,
          "colspan": 1,
          "text": "Header 1",
          "bbox": {"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.3}
        }
      ]
    }
  ]
}
```

### Field Descriptions

- **pdf_file**: Name of the PDF file (relative to `pdfs/` directory)
- **page_index**: Zero-based page index
- **metadata**: Optional metadata about the annotation
  - **source**: Data provenance (synthetic, public domain, CC0, etc.)
  - **annotator**: Name of person who created annotation
  - **date**: Annotation creation date
  - **notes**: Any relevant notes
- **tables**: List of table annotations
  - **table_id**: Unique identifier for the table
  - **bbox**: Normalized bounding box (0-1 coordinates) for entire table
  - **n_rows**: Number of rows in table
  - **n_cols**: Number of columns in table
  - **cells**: List of cell annotations
    - **row**: Row index (0-based)
    - **col**: Column index (0-based)
    - **rowspan**: Number of rows spanned (default: 1)
    - **colspan**: Number of columns spanned (default: 1)
    - **text**: Cell text content
    - **bbox**: Optional normalized bounding box for cell

## Dataset Characteristics

### Coverage Goals

| Category | Target | Current | Examples |
|----------|--------|---------|----------|
| Bordered tables | 5 | 5 | Financial statements, data grids |
| Borderless tables | 3 | 3 | Reports with alignment-based tables |
| Multi-page tables | 2 | 2 | Long data tables spanning pages |
| Merged cells | 3 | 3 | Headers with colspan/rowspan |
| Low-quality scans | 2 | 2 | Faded lines, skewed pages |
| Irregular tables | 2 | 2 | Ragged rows, non-rectangular |

### Diversity Criteria

- **Table sizes**: Small (<10 cells), medium (10-50 cells), large (>50 cells)
- **Fonts/styles**: At least 2 different fonts or visual styles
- **DPI quality**: Mix of 150 DPI and 300 DPI
- **Sources**: Mix of synthetic and real-world PDFs

## License and Usage

All PDFs and annotations in this dataset are either:

1. **Synthetic**: Generated specifically for this benchmark
2. **Public Domain**: No copyright restrictions
3. **CC0**: Creative Commons Zero (public domain equivalent)

See [LICENSE.md](LICENSE.md) for detailed license information for each file.

## Contributing New Test Cases

We welcome contributions of new test cases! To add a new PDF and annotation:

### 1. Prepare PDF

- Ensure PDF has clear redistribution rights (synthetic, public domain, or CC0)
- PDF should represent a specific challenge or table type
- Save PDF to `pdfs/` directory with descriptive name

### 2. Create Annotation

- Use the annotation tool: `python tools/annotate_table.py --input pdfs/your_file.pdf`
- Or manually create JSON file following the schema above
- Save annotation to `annotations/` directory with same basename as PDF

### 3. Validate Annotation

```bash
python tools/validate_annotation.py annotations/your_file.json
```

### 4. Test Extraction

```bash
python tools/run_benchmarks.py --dataset datasets/benchmarks --subset your_file
```

### 5. Submit Pull Request

- Include both PDF and annotation
- Update this README with dataset characteristics
- Add license information to LICENSE.md

### Annotation Guidelines

- **Accuracy**: Double-check all cell positions, spans, and text
- **Completeness**: Annotate all tables on the page
- **Consistency**: Use consistent conventions for empty cells, whitespace, etc.
- **Documentation**: Add notes in metadata about any special cases

## Quality Criteria

Annotations should meet the following quality standards:

- **Structural accuracy**: All row/column counts and spans correct
- **Bbox accuracy**: Bounding boxes within 5% of visual cell boundaries
- **Text accuracy**: All cell text transcribed exactly (including whitespace)
- **Validation**: Passes `validate_annotation.py` without errors

## Troubleshooting

### Common Issues

**Issue**: Bounding boxes don't align with visual table

**Solution**: Ensure coordinates are normalized (0-1) and account for PDF coordinate system (origin at top-left)

**Issue**: Validation fails with "cell extends beyond table"

**Solution**: Check that row + rowspan ≤ n_rows and col + colspan ≤ n_cols

**Issue**: Text doesn't match extraction

**Solution**: Check for extra whitespace, newlines, or unicode normalization issues

## Maintenance

The benchmark dataset is maintained by the project team. We periodically review and update:

- Adding new test cases for emerging challenges
- Updating annotations if extraction improvements reveal errors
- Removing or deprecating test cases that are no longer relevant

Last updated: 2025-11-21


