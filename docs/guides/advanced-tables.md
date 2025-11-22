# Advanced Tables & Irregular Structures

This guide explains how to configure the pipeline to handle partially bordered tables, ragged rows/columns, and stacked multi-panel layouts. Use these features when working with messy operational PDFs that do not follow perfect grid layouts.

## Enabling Irregular Structure Detection

Set the following options (via `PipelineConfig`, CLI flags, or config files) to enable the new heuristics:

| Config Field | CLI Flag | Description |
|--------------|----------|-------------|
| `enable_irregular_structure_detection` | `--enable-irregular-detection` | Turns on whitespace clustering + text density heuristics. |
| `ragged_mode` (`"strict"` or `"ragged"`) | `--ragged-mode` | `"strict"` aggressively pads missing cells for compatibility. `"ragged"` keeps filler cells with provenance metadata. |
| `ragged_fill_value` | `--ragged-fill-value` | Optional filler token for missing cells (e.g., `"__MISSING__"`). |
| `enable_section_detection` | `--section-detection` | Detects stacked panels and assigns `section_label` metadata. |

Example CLI invocation:

```bash
pdf-reader extract \
  --input irregular.pdf \
  --enable-irregular-detection \
  --ragged-mode ragged \
  --ragged-fill-value "__MISSING__" \
  --section-detection
```

## What Changes with Irregular Detection?

### Detection & Grid Construction

- **Whitespace clustering**: When inner lines are missing, the detector clusters text bounding boxes to infer row/column boundaries.
- **Ragged support**: Rows can expose different column counts. Missing positions are normalized using filler cells so downstream consumers still receive rectangular data.
- **Section labels**: Multi-panel/stacked tables generate one `TableRegion` per panel with a `section_label`. `TableGrid.section_labels` and `TableMetadata.section_labels` echo these labels.

### Metadata & Provenance

New metadata fields surface structural quality:

- `TableMetadata.structure_confidence`: ratio of explicit vs. inferred cells.
- `TableMetadata.irregularities`: e.g., `["ragged_columns", "partial_borders"]`.
- `Cell.is_filler`, `Cell.structure_source`: highlight filler/inferred cells.

Both the CLI summary and HTML report list detected irregularities so QA teams can review suspicious tables quickly.

### Debug Artifacts

Overlay images now color code inferred structures:

- **Blue** — explicit/line-aligned cells
- **Purple** — inferred cells
- **Orange** — filler cells generated to pad ragged rows

Section labels are annotated directly on each detected panel.

## Limitations & Tips

- Heuristics rely on rendered text contrast. Extremely noisy scans may still require manual review.
- If you only need classic fully bordered tables, keep `enable_irregular_structure_detection=False` for faster processing.
- `ragged_mode="strict"` is recommended when downstream systems cannot handle filler markers (all missing cells become empty strings/`None`).
- Use `ragged_fill_value` to insert consistent placeholder tokens for analytics pipelines that require explicit values.

## Troubleshooting

| Symptom | Possible Cause | Remedy |
|---------|----------------|--------|
| Too many filler cells | Text density too low or DPI too small | Increase `dpi`, keep `ragged_mode="strict"`, or provide span hints. |
| Section labels missing | Panels too close vertically | Increase page DPI or add manual hints by splitting PDF pages. |
| Overlay shows misaligned boxes | Under/over detection due to noise | Run sequential mode and capture debug artifacts to fine-tune thresholds. |

For additional customization, refer to `GridStructureDetector` parameters in `pdf_reader/detection.py`.

