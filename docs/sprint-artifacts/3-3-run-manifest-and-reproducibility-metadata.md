# Story 3.3: Run manifest and reproducibility metadata

Status: review

## Story

As a **platform engineer embedding the library into regulated workflows**,  
I want **each extraction run to capture a full manifest of code versions, model/OCR revisions, and config digests**,  
so that **results are auditable, reproducible, and comparable across time**.

## Acceptance Criteria

1. **Run manifest generation**
   - Each `ExtractionResult` contains a `run_manifest` block with:
     - Git commit/dirty flag, version string, and build timestamp.
     - Hash/digest of the effective `PipelineConfig`.
     - Identifiers/versions for OCR engines, LLM providers, detection models.

2. **Table-level provenance**
   - `TableMetadata` embeds the relevant subset of manifest info (e.g., OCR engine version, detector version) plus per-table parameter overrides.
   - Provenance fields surface in both JSON export and HTML debug report.

3. **Manifest export/output**
   - CLI gains `--emit-manifest` option to write a standalone JSON/YAML manifest file alongside tables.
   - Runs automatically archive manifest in `runs/<timestamp>/run_manifest.json`.

4. **Verification & validation**
   - Tests assert manifest presence, schema, and deterministic hashing when config is unchanged.
   - Negative tests cover dirty git states, missing version info, and ensure graceful fallbacks (e.g., "unknown" with warning).

5. **Documentation & playbooks**
   - `docs/guides/reproducibility.md` (or README section) explains how to interpret manifests, compare runs, and pin dependencies.
   - Release checklist references manifest output as required evidence.

## Tasks / Subtasks

- [x] **T3.3.1 — Manifest schema definition**
  - [x] Define dataclasses/TypedDicts for `RunManifest` and `ComponentVersion`.
  - [x] Document JSON schema in `docs/api/`.

- [x] **T3.3.2 — Data collection hooks**
  - [x] Implement utilities to gather git info, dependency versions, and environment metadata (Python version, OS).
  - [x] Extend component constructors to expose `version_id` attributes for manifest inclusion.

- [x] **T3.3.3 — Integration with pipeline output**
  - [x] Persist manifest within `ExtractionResult` and CLI artifacts.
  - [x] Ensure manifest serialization works for both JSON exports and `run_stats.json`.

- [x] **T3.3.4 — Testing & validation**
  - [x] Add unit tests for hashing/digest stability.
  - [x] Add integration test verifying manifest file writes and contents.

- [x] **T3.3.5 — Documentation & tooling**
  - [x] Write reproducibility guide + sample manifest walkthrough.
  - [x] Provide helper script (e.g., `tools/compare_manifests.py`) for diffing runs.

## Implementation Summary

**Completed**: 2025-11-21

### Key Changes:

1. **Manifest Module** (`src/pdf_reader/manifest.py`):
   - `RunManifest` and `ComponentVersion` dataclasses
   - Git info collection (`get_git_info()`)
   - Package version collection (`get_package_versions()`)
   - Config digest computation (SHA256, excludes sensitive fields)
   - Manifest creation, saving, loading, and comparison utilities

2. **Integration** (`src/pdf_reader/pipeline.py`, `src/pdf_reader/models.py`):
   - Added `run_manifest` field to `ExtractionResult`
   - Automatic manifest generation at end of pipeline run
   - Component version tracking for all pipeline components

3. **CLI Support** (`src/pdf_reader/cli.py`):
   - `--emit-manifest` flag to save manifest to file
   - `--manifest-output` flag to specify custom output path
   - Default: `debug_output/run_manifest.json`

4. **Comparison Tool** (`tools/compare_manifests.py`):
   - Command-line tool to compare two manifests
   - Identifies differences in git state, config, packages, components
   - JSON and human-readable output formats

5. **Tests** (`tests/test_manifest.py`):
   - 15 comprehensive unit tests
   - Tests for digest stability, git info collection, manifest comparison
   - Mock-based tests for git subprocess calls

6. **Documentation** (`docs/guides/reproducibility.md`):
   - Complete guide on using manifests for reproducibility
   - Best practices for production runs
   - Troubleshooting common issues
   - Examples of programmatic manifest usage

### Usage Examples:

```bash
# Generate manifest with extraction
python -m pdf_reader extract --input document.pdf --emit-manifest

# Custom manifest path
python -m pdf_reader extract --input document.pdf \
    --emit-manifest \
    --manifest-output runs/$(date +%Y%m%d)/manifest.json

# Compare two manifests
python tools/compare_manifests.py run1/manifest.json run2/manifest.json
```

### Manifest Contents:
- **Run identification**: run_id, timestamp
- **Code version**: git_commit, git_branch, git_dirty, version_string
- **Configuration**: config_digest (SHA256), config_snapshot (sanitized)
- **Environment**: python_version, platform_system, platform_release
- **Components**: List of component versions (detectors, extractors, LLM)
- **Dependencies**: Package versions (pdfplumber, numpy, opencv, etc.)

### Security:
- Sensitive fields (API keys) are excluded from manifests
- Config digest computation excludes sensitive fields
- Config snapshots are sanitized before serialization

## Dev Notes

- Prefer lightweight metadata collection that does not require git to be present in production builds; allow overrides via environment variables.
- Ensure sensitive data (e.g., API keys) never lands in manifests.
- Align manifest terminology with existing `RunStats` to avoid confusion (e.g., `run_id`, `config_digest`).

### References

- Source: `docs/prd.md` — Section 13.6 (T5.3 Versioning & reproducibility)
- Source: `docs/prd.md` — Sections 10 & 11 (success metrics + release plan) emphasizing auditability


