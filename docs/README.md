# Documentation Index

Welcome to the PDF table extraction pipeline documentation. This index helps you navigate the documentation based on your needs.

## Quick Links

- **[Getting Started Guide](guides/getting-started.md)** - Start here for a quick introduction
- **[Architecture Documentation](architecture.md)** - System design and component overview
- **[Configuration Guide](guides/configuration.md)** - How to configure the pipeline
- **[CLI Usage Examples](../examples/cli_usage.md)** - Command-line examples

## Documentation Structure

### Getting Started

- **[Getting Started Guide](guides/getting-started.md)** - Quick start tutorial
- **[Installation Guide](installation.md)** - Installation and setup instructions

### User Guides

- **[Configuration Guide](guides/configuration.md)** - Configuration options and examples
- **[Debugging Guide](guides/debugging.md)** - How to debug and troubleshoot issues
- **[Troubleshooting and FAQ](troubleshooting.md)** - Common issues and solutions

### Developer Guides

- **[Architecture Documentation](architecture.md)** - System design and components
- **[Extension Guide](guides/extending.md)** - How to extend and customize the pipeline

### Examples

- **[Basic Usage Example](../examples/basic_usage.py)** - Simple extraction example
- **[Advanced Usage Example](../examples/advanced_usage.py)** - Advanced features example
- **[CLI Usage Examples](../examples/cli_usage.md)** - Command-line examples

## Documentation by Use Case

### I want to...

**...get started quickly**
→ [Getting Started Guide](guides/getting-started.md)

**...configure the pipeline**
→ [Configuration Guide](guides/configuration.md)

**...understand how it works**
→ [Architecture Documentation](architecture.md)

**...debug an issue**
→ [Debugging Guide](guides/debugging.md) or [Troubleshooting](troubleshooting.md)

**...extend the system**
→ [Extension Guide](guides/extending.md)

**...see examples**
→ [Examples](../examples/)

## API Reference

For detailed API documentation, see the inline docstrings in the source code:

- `PipelineConfig` - Configuration class
- `PipelineRunner` - Main pipeline orchestrator
- `PdfIngestionService` - PDF loading and rendering
- `TableRegionDetector` - Table detection
- `GridStructureDetector` - Grid construction
- `CellTextExtractor` - Text extraction
- `TableAssembler` - Table assembly

Access docstrings in Python:
```python
from pdf_reader import PipelineConfig
help(PipelineConfig)
```

## Contributing

If you're contributing to the project:

1. Read the [Architecture Documentation](architecture.md) to understand the system
2. Review the [Extension Guide](guides/extending.md) for customization patterns
3. Check existing code docstrings for style and format

## See Also

- [Main README](../README.md) - Project overview and quick reference
- [PRD](../prd.md) - Product requirements document
- [Sprint Artifacts](../sprint-artifacts/) - Development stories and planning



