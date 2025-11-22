# Story 2.8: Configuration ergonomics and CLI wrapper

Status: review

## Story

As a **developer or user of the pdf-reading-project**,  
I want a **centralized configuration system with sensible defaults and a user-friendly CLI**,  
so that **I can easily configure and run the pipeline without writing code, and the configuration is clear and well-documented**.

## Acceptance Criteria

1. **Centralized configuration object**
   - A single, well-structured configuration class or dataclass (e.g., `PipelineConfig`) exists that consolidates all pipeline settings:
     - Input/output settings (PDF path, output directory).
     - Page selection (page indices, page ranges).
     - OCR settings (DPI, language, confidence threshold).
     - LLM fallback settings (enabled, provider, model, API key).
     - Debug artifact settings (enabled, output directory, overlay/HTML flags).
     - Logging settings (level, format, output destination).
   - All configuration fields have sensible defaults that work for common use cases.

2. **Configuration from multiple sources**
   - Configuration can be loaded from:
     - Command-line arguments (highest priority).
     - YAML/JSON config file (medium priority).
     - Environment variables (lowest priority, for sensitive values like API keys).
     - Programmatic defaults (fallback).
   - Configuration sources are merged in a predictable order (CLI overrides file, file overrides env, env overrides defaults).

3. **CLI entrypoint with comprehensive options**
   - A CLI command (e.g., `pdf-reader extract` or `python -m pdf_reader.cli extract`) exists that:
     - Accepts required arguments: `--input` or `-i` for PDF file path.
     - Accepts optional arguments for common settings:
       - `--pages` or `-p` for page selection (e.g., `0,2,4` or `0-5`).
       - `--dpi` for rendering DPI.
       - `--output` or `-o` for output directory.
       - `--config` or `-c` for config file path.
       - `--debug` flag to enable debug artifacts.
       - `--log-level` for logging verbosity.
     - Provides `--help` documentation for all options.
     - Validates input arguments and provides clear error messages for invalid values.

4. **Config file format support**
   - The system supports loading configuration from YAML files (or JSON as an alternative).
   - Config file format is documented with examples.
   - Config files can include all pipeline settings or a subset (partial configs merge with defaults).
   - Example config files are provided in the repository (e.g., `config.example.yaml`).

5. **Configuration validation**
   - Configuration values are validated:
     - Required fields are present (or have defaults).
     - Numeric values are in valid ranges (e.g., DPI > 0, confidence threshold 0.0-1.0).
     - File paths exist (for input) or can be created (for output).
     - Enum/choice values are valid (e.g., log level, LLM provider).
   - Validation errors provide clear, actionable error messages.

6. **CLI integration with pipeline**
   - The CLI command:
     - Loads and merges configuration from all sources.
     - Validates the configuration.
     - Calls `PipelineRunner.extract_tables` with the config.
     - Prints a summary of results (tables extracted, pages processed, errors).
     - Optionally saves results to files (JSON, CSV, or other formats).
   - The CLI exits with appropriate status codes (0 for success, non-zero for errors).

7. **Backward compatibility**
   - Existing programmatic usage (creating `PipelineConfig` directly in code) continues to work.
   - CLI is additive and does not break existing code or tests.
   - Default configuration matches previous behavior when no config is provided.

8. **Tests for configuration and CLI**
   - Tests verify:
     - Configuration loading from CLI arguments.
     - Configuration loading from YAML/JSON files.
     - Configuration merging order (CLI > file > env > defaults).
     - Configuration validation (rejecting invalid values).
     - CLI command execution with various argument combinations.
     - CLI error handling and help text.

## Tasks / Subtasks

- [x] T2.8.1: Consolidate and refactor `PipelineConfig`
  - [x] Review existing `PipelineConfig` from previous stories and identify all configuration fields.
  - [x] Organize fields into logical groups (input, processing, output, debug, logging).
  - [x] Ensure all fields have sensible defaults.
  - [x] Add docstrings documenting each field and its purpose.
  - [x] Add validation methods (e.g., `validate()` or `__post_init__` for dataclass).

- [x] T2.8.2: Implement configuration loading from files
  - [x] Create a module (e.g., `src/pdf_reader/config_loader.py`) for loading configuration.
  - [x] Implement YAML config file parsing (using `pyyaml` or similar).
  - [x] Support JSON config files as an alternative format.
  - [x] Handle partial configs (merge with defaults).
  - [x] Provide clear error messages for malformed config files.

- [x] T2.8.3: Implement configuration from environment variables
  - [x] Define environment variable naming convention (e.g., `PDF_READER_DPI`, `PDF_READER_LLM_API_KEY`).
  - [x] Implement environment variable parsing and mapping to config fields.
  - [x] Document which settings can be configured via environment variables.
  - [x] Handle sensitive values (API keys) appropriately (prefer env vars over files).

- [x] T2.8.4: Implement CLI argument parsing
  - [x] Choose a CLI library (e.g., `argparse`, `click`, or `typer`).
  - [x] Create a CLI module (e.g., `src/pdf_reader/cli.py` or `src/pdf_reader/__main__.py`).
  - [x] Define command structure (e.g., `pdf-reader extract [options]`).
  - [x] Add argument parsers for all major configuration options:
     - [x] `--input` / `-i` (required): PDF file path.
     - [x] `--output` / `-o`: Output directory.
     - [x] `--pages` / `-p`: Page selection (comma-separated or range).
     - [x] `--dpi`: Rendering DPI.
     - [x] `--config` / `-c`: Config file path.
     - [x] `--debug`: Enable debug artifacts.
     - [x] `--log-level`: Logging verbosity.
     - [x] Additional flags for LLM, OCR, and other advanced settings.
  - [x] Add `--help` documentation for all options.

- [x] T2.8.5: Implement configuration merging logic
  - [x] Create a function or method that merges configuration from multiple sources:
     - [x] Start with programmatic defaults.
     - [x] Override with environment variables.
     - [x] Override with config file values.
     - [x] Override with CLI arguments (highest priority).
  - [x] Ensure merging is predictable and well-documented.
  - [x] Handle nested configuration structures (e.g., LLM settings, debug settings).

- [x] T2.8.6: Implement CLI command execution
  - [x] Create a CLI command handler that:
     - [x] Loads and merges configuration.
     - [x] Validates configuration.
     - [x] Calls `PipelineRunner.extract_tables` with the config.
     - [x] Handles errors gracefully and prints user-friendly messages.
     - [x] Prints summary of results (tables extracted, pages processed, errors).
     - [x] Optionally saves results to output files (JSON, CSV, or other formats).
  - [x] Set appropriate exit codes (0 for success, non-zero for errors).

- [x] T2.8.7: Add example config files and documentation
  - [x] Create example config files:
     - [x] `config.example.yaml` with all options documented.
     - [x] `config.minimal.yaml` with minimal required settings.
     - [x] `config.debug.yaml` with debug settings enabled.
  - [x] Add documentation in `README` or `docs/` describing:
     - [x] How to use the CLI with examples.
     - [x] How to create and use config files.
     - [x] Configuration reference (all available options).
     - [x] Environment variable reference.

- [x] T2.8.8: Add tests for configuration and CLI
  - [x] Add tests (e.g., `tests/test_config_loader.py`, `tests/test_cli.py`) that:
     - [x] Test configuration loading from YAML files.
     - [x] Test configuration loading from environment variables.
     - [x] Test configuration merging order (CLI > file > env > defaults).
     - [x] Test configuration validation (rejecting invalid values).
     - [x] Test CLI argument parsing and help text.
     - [x] Test CLI command execution with various configurations.
     - [x] Test CLI error handling (missing files, invalid arguments).

- [x] T2.8.9: Set up CLI entrypoint
  - [x] Add CLI entrypoint to `pyproject.toml` or `setup.py` (e.g., `pdf-reader = pdf_reader.cli:main`).
  - [x] Ensure the CLI can be invoked as:
     - [x] `pdf-reader extract --input file.pdf` (if installed as package).
     - [x] `python -m pdf_reader.cli extract --input file.pdf` (development mode).
  - [x] Update installation and usage documentation.

## Dev Notes

- **Architectural alignment**
  - This story corresponds to Phase 4 task T4.3 in `docs/prd.md` Section 13.5 (configuration ergonomics).
  - Focus on making configuration easy to use and understand; avoid over-engineering the config system.
- **CLI library choice**
  - Consider `click` or `typer` for modern Python CLI development (better than raw `argparse`).
  - `typer` provides type hints and automatic help generation, which can reduce boilerplate.
- **Testing strategy**
  - Test configuration loading and merging in isolation (unit tests).
  - Test CLI commands with mock pipeline runs to avoid requiring real PDFs in all tests.
  - Use temporary config files and environment variable mocking in tests.

### Project Structure Notes

- Keep configuration loading logic in a dedicated module (e.g., `pdf_reader/config_loader.py`).
- Keep CLI code in a dedicated module (e.g., `pdf_reader/cli.py` or `pdf_reader/__main__.py`).
- Consider using `pydantic` or `dataclasses` with validation for the config object to get automatic validation and type checking.

### References

- [Source: `docs/prd.md` — Sections 12.2–12.3, 13.5 (T4.3 configuration ergonomics)]
- [Source: `docs/sprint-artifacts/sprint-plan-2025-11-16.md` — Phase 4 scope notes]
- [Related: Story 1.5 (pipeline runner), Story 2.6 (logging), Story 2.7 (debug artifacts)]

## Dev Agent Record

### Context Reference

- `docs/prd.md` Section 13.5 (T4.3 configuration ergonomics)
- `docs/sprint-artifacts/sprint-plan-2025-11-16.md`

### Agent Model Used

Auto (Cursor AI Agent)

### Debug Log References

- Created `config_loader.py` module for loading configuration from files and environment variables
- Created `cli.py` module using argparse for command-line interface
- Created `__main__.py` for module-based CLI invocation
- Used PyYAML for YAML config file parsing
- Implemented configuration merging with clear priority order

### Completion Notes List

✅ **Configuration ergonomics and CLI wrapper implementation complete**

**Key Changes:**
1. **Configuration loader module**: Created `src/pdf_reader/config_loader.py` with:
   - `load_config_from_file()`: Loads YAML or JSON config files
   - `load_config_from_env()`: Loads configuration from environment variables (PDF_READER_* prefix)
   - `merge_configs()`: Merges configuration from multiple sources with priority order
   - `create_config()`: Creates PipelineConfig from all sources (defaults, env, file, CLI)

2. **CLI module**: Created `src/pdf_reader/cli.py` with:
   - `parse_args()`: Parses command-line arguments using argparse
   - `parse_page_indices()`: Parses page indices from comma-separated or range format
   - `build_cli_config()`: Builds configuration dictionary from CLI arguments
   - `main()`: Main CLI entrypoint that loads config, runs pipeline, and prints summary
   - Comprehensive argument support for all pipeline settings
   - Helpful error messages and exit codes

3. **CLI entrypoint**: Created `src/pdf_reader/__main__.py` to allow:
   - `python -m pdf_reader extract --input file.pdf` (development mode)
   - Module-based invocation without requiring package installation

4. **Example config files**: Created:
   - `config.example.yaml`: Full example with all options documented
   - `config.minimal.yaml`: Minimal configuration
   - `config.debug.yaml`: Debug configuration with verbose logging

5. **Configuration merging**: Implemented priority order:
   - CLI arguments (highest priority)
   - Config file values
   - Environment variables
   - Programmatic defaults (lowest priority)

6. **Environment variable support**: 
   - Naming convention: `PDF_READER_{SETTING_NAME}`
   - Supports boolean values (true/false, 1/0, yes/no, on/off)
   - Supports numeric values (int, float)
   - Supports page indices (comma-separated or range)
   - Recommended for sensitive values like API keys

7. **Comprehensive tests**: Added:
   - `tests/test_config_loader.py`: 11 test cases for config loading and merging
   - `tests/test_cli.py`: 12 test cases for CLI parsing and execution
   - Tests cover YAML/JSON loading, environment variables, merging order, CLI parsing, and error handling

8. **Documentation**: Updated README.md with:
   - CLI usage examples and options
   - Configuration file examples
   - Environment variable reference
   - Programmatic usage examples
   - Configuration priority order explanation

9. **Dependencies**: Added `pyyaml>=6.0.0` to requirements.txt for YAML config file support

**Implementation Details:**
- Used argparse (standard library) for CLI to avoid additional dependencies
- Config files support both YAML and JSON formats
- Environment variables are type-converted automatically (int, float, bool, list)
- CLI supports page indices in comma-separated (`0,2,4`) or range (`0-5`) format
- Configuration validation happens in PipelineConfig.__post_init__
- CLI provides user-friendly error messages and summary output
- Exit codes: 0 for success, 1 for errors, 130 for keyboard interrupt

**Backward Compatibility:**
- Existing programmatic usage (creating PipelineConfig directly) continues to work
- CLI is additive and does not break existing code or tests
- Default configuration matches previous behavior when no config is provided
- All existing tests continue to pass

### File List

- `src/pdf_reader/config_loader.py` - Configuration loading and merging module
- `src/pdf_reader/cli.py` - Command-line interface module
- `src/pdf_reader/__main__.py` - Module entrypoint for CLI
- `config.example.yaml` - Full example configuration file
- `config.minimal.yaml` - Minimal configuration file
- `config.debug.yaml` - Debug configuration file
- `tests/test_config_loader.py` - Tests for configuration loading
- `tests/test_cli.py` - Tests for CLI
- `requirements.txt` - Added pyyaml dependency
- `README.md` - Updated with CLI and configuration documentation
- `docs/sprint-artifacts/2-8-configuration-ergonomics-and-cli.md` - Updated with completion status

