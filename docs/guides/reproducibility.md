# Reproducibility Guide

This guide explains how to use run manifests for reproducibility tracking, comparing runs, and ensuring auditable results.

## Overview

Every pipeline run can generate a **run manifest** containing complete metadata for reproducibility:
- Git commit, branch, and dirty status
- Configuration digest (SHA256 hash)
- Python version and platform information
- Package versions (pdfplumber, numpy, opencv, etc.)
- Component versions (detectors, extractors, LLM providers)

## Generating Run Manifests

### CLI

Use the `--emit-manifest` flag to save a manifest:

```bash
python -m pdf_reader extract --input document.pdf --emit-manifest
```

By default, the manifest is saved to `debug_output/run_manifest.json`. You can specify a custom path:

```bash
python -m pdf_reader extract --input document.pdf \
    --emit-manifest \
    --manifest-output my_run/manifest.json
```

### Programmatic

Manifests are automatically included in `ExtractionResult`:

```python
from pdf_reader import PipelineRunner, PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(input_path="document.pdf")
result = runner.extract_tables("document.pdf", config=config)

# Access manifest
manifest = result.run_manifest
print(f"Run ID: {manifest.run_id}")
print(f"Git Commit: {manifest.git_commit}")
print(f"Config Digest: {manifest.config_digest}")

# Save manifest
from pdf_reader.manifest import save_manifest
from pathlib import Path

save_manifest(manifest, Path("my_run/manifest.json"))
```

## Manifest Structure

A typical manifest looks like this:

```json
{
  "run_id": "20251121_120000_abc123",
  "timestamp": "2025-11-21T12:00:00Z",
  "git_commit": "abc123def456",
  "git_branch": "main",
  "git_dirty": false,
  "version_string": "1.0.0",
  "config_digest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "config_snapshot": {
    "dpi": 200,
    "extraction_strategy": "heuristic",
    "enable_line_detection": true,
    ...
  },
  "python_version": "3.10.0 (default, Oct  6 2021, 09:00:00)",
  "platform_system": "Linux",
  "platform_release": "5.15.0",
  "components": [
    {
      "name": "TableRegionDetector",
      "version": "1.0",
      "type": "detector",
      "metadata": {"method": "morphological_operations"}
    },
    {
      "name": "GridStructureDetector",
      "version": "1.0",
      "type": "detector",
      "metadata": {
        "line_detection_enabled": true,
        "irregular_detection_enabled": false
      }
    }
  ],
  "package_versions": {
    "pdfplumber": "0.11.0",
    "pillow": "10.0.0",
    "numpy": "1.24.0",
    "opencv-python": "4.8.0",
    ...
  }
}
```

## Comparing Manifests

Use the `compare_manifests.py` tool to identify differences between runs:

```bash
python tools/compare_manifests.py run1/manifest.json run2/manifest.json
```

Output:

```
⚠️  Differences found:

Git Commit:
  Manifest 1: abc123def456
  Manifest 2: def456abc123

Package Versions:
  numpy:
    Manifest 1: 1.24.0
    Manifest 2: 1.25.0
```

### JSON Output

For programmatic analysis:

```bash
python tools/compare_manifests.py manifest1.json manifest2.json --json
```

## Configuration Digests

The **config digest** is a SHA256 hash of the pipeline configuration (excluding sensitive fields like API keys). It provides a quick way to verify if two runs used identical settings.

### Computing Digests

```python
from pdf_reader.manifest import compute_config_digest
from pdf_reader import PipelineConfig

config = PipelineConfig(dpi=200, default_rows=2)
digest = compute_config_digest(config)
print(f"Config digest: {digest}")
```

### Comparing Digests

If two manifests have the same `config_digest`, they used identical configurations (modulo sensitive fields).

## Reproducibility Best Practices

### 1. Always Generate Manifests for Production Runs

```bash
# Good: Manifest saved for audit trail
python -m pdf_reader extract --input document.pdf \
    --emit-manifest \
    --manifest-output runs/$(date +%Y%m%d_%H%M%S)/manifest.json
```

### 2. Pin Dependencies

Use a `requirements.txt` with exact versions:

```
pdfplumber==0.11.0
pillow==10.0.0
numpy==1.24.0
opencv-python==4.8.0
```

### 3. Commit Configuration Files

Store config files in version control:

```yaml
# config/production.yaml
dpi: 300
enable_line_detection: true
llm_fallback_enabled: false
```

### 4. Track Git State

Always run from a clean git state for production:

```bash
# Check for uncommitted changes
git status

# If dirty, commit or stash changes
git commit -am "Update config for production run"
```

### 5. Archive Manifests with Results

Store manifests alongside extraction results:

```
runs/
  20251121_120000/
    manifest.json
    extraction_report.html
    tables/
      table_0.csv
      table_1.csv
```

## Troubleshooting

### Manifest Shows `git_dirty: true`

**Problem**: Uncommitted changes detected.

**Solution**: Commit or stash changes before running:

```bash
git status
git add .
git commit -m "Prepare for production run"
```

### Config Digest Mismatch

**Problem**: Two runs have different config digests despite "identical" settings.

**Possible Causes**:
- Different Python types (e.g., `Path` vs `str`)
- Additional fields in one config
- Different default values

**Solution**: Compare config snapshots in manifests:

```bash
python tools/compare_manifests.py run1/manifest.json run2/manifest.json --verbose
```

### Package Version Differences

**Problem**: Manifests show different package versions.

**Solution**: Use a virtual environment with pinned dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt --no-upgrade
```

### Git Info Missing

**Problem**: Manifest shows `git_commit: null`.

**Possible Causes**:
- Not running from a git repository
- Git not installed
- Running from a Docker container without git

**Solution**: Set version via environment variable:

```bash
export PDF_READER_VERSION="1.0.0-production"
python -m pdf_reader extract --input document.pdf --emit-manifest
```

## Advanced: Programmatic Manifest Comparison

```python
from pdf_reader.manifest import load_manifest, compare_manifests

# Load manifests
manifest1 = load_manifest("run1/manifest.json")
manifest2 = load_manifest("run2/manifest.json")

# Compare
differences = compare_manifests(manifest1, manifest2)

if not differences:
    print("Runs are reproducible!")
else:
    print("Differences found:")
    for key, diff in differences.items():
        print(f"  {key}: {diff}")
```

## See Also

- [Configuration Guide](configuration.md) - How to configure the pipeline
- [Architecture Documentation](../architecture.md) - System design details
- `tools/compare_manifests.py` - Manifest comparison tool


