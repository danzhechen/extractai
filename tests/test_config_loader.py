import json
import os
from pathlib import Path

import pytest
import yaml

from pdf_reader.config_loader import (
    create_config,
    load_config_from_env,
    load_config_from_file,
    merge_configs,
)
from pdf_reader.pipeline import PipelineConfig


def test_load_config_from_yaml_file(tmp_path):
    """Test loading configuration from a YAML file."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "dpi": 300,
        "log_level": "DEBUG",
        "enable_debug_artifacts": True,
    }
    config_file.write_text(yaml.dump(config_data))

    loaded = load_config_from_file(config_file)
    assert loaded["dpi"] == 300
    assert loaded["log_level"] == "DEBUG"
    assert loaded["enable_debug_artifacts"] is True


def test_load_config_from_json_file(tmp_path):
    """Test loading configuration from a JSON file."""
    config_file = tmp_path / "config.json"
    config_data = {
        "dpi": 250,
        "log_level": "WARNING",
    }
    config_file.write_text(json.dumps(config_data))

    loaded = load_config_from_file(config_file)
    assert loaded["dpi"] == 250
    assert loaded["log_level"] == "WARNING"


def test_load_config_from_file_not_found(tmp_path):
    """Test that loading a non-existent file raises FileNotFoundError."""
    config_file = tmp_path / "nonexistent.yaml"
    with pytest.raises(FileNotFoundError):
        load_config_from_file(config_file)


def test_load_config_from_file_invalid_yaml(tmp_path):
    """Test that invalid YAML raises ValueError."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("invalid: yaml: content: [")
    with pytest.raises(ValueError, match="Invalid YAML"):
        load_config_from_file(config_file)


def test_load_config_from_env():
    """Test loading configuration from environment variables."""
    # Set environment variables
    os.environ["PDF_READER_DPI"] = "300"
    os.environ["PDF_READER_LOG_LEVEL"] = "DEBUG"
    os.environ["PDF_READER_LLM_FALLBACK_ENABLED"] = "true"
    os.environ["PDF_READER_ENABLE_DEBUG_ARTIFACTS"] = "1"

    try:
        loaded = load_config_from_env()
        assert loaded["dpi"] == 300
        assert loaded["log_level"] == "DEBUG"
        assert loaded["llm_fallback_enabled"] is True
        assert loaded["enable_debug_artifacts"] is True
    finally:
        # Clean up
        for key in ["PDF_READER_DPI", "PDF_READER_LOG_LEVEL", "PDF_READER_LLM_FALLBACK_ENABLED", "PDF_READER_ENABLE_DEBUG_ARTIFACTS"]:
            os.environ.pop(key, None)


def test_load_config_from_env_boolean_values():
    """Test that boolean environment variables are parsed correctly."""
    test_cases = [
        ("true", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
        ("off", False),
    ]

    for value, expected in test_cases:
        os.environ["PDF_READER_LLM_FALLBACK_ENABLED"] = value
        try:
            loaded = load_config_from_env()
            assert loaded["llm_fallback_enabled"] == expected, f"Failed for value: {value}"
        finally:
            os.environ.pop("PDF_READER_LLM_FALLBACK_ENABLED", None)


def test_merge_configs_priority_order():
    """Test that configuration merging respects priority order."""
    defaults = {"dpi": 200, "log_level": "INFO"}
    env_config = {"dpi": 250, "log_level": "WARNING"}
    file_config = {"dpi": 300}
    cli_config = {"dpi": 400}

    merged = merge_configs(defaults, env_config, file_config, cli_config)

    # CLI should win (highest priority)
    assert merged["dpi"] == 400
    # File should override env for dpi, but env should win for log_level
    # Actually, file overrides env, so log_level should be from file (not present) or env
    # Wait, the merge order is: defaults -> env -> file -> cli
    # So log_level should be from env (WARNING) since file doesn't have it
    assert merged["log_level"] == "WARNING"


def test_create_config_from_defaults():
    """Test creating config with only defaults."""
    config = create_config()
    assert isinstance(config, PipelineConfig)
    assert config.dpi == 200  # Default value
    assert config.log_level == "INFO"


def test_create_config_from_file(tmp_path):
    """Test creating config from a file."""
    config_file = tmp_path / "config.yaml"
    config_data = {"dpi": 300, "log_level": "DEBUG"}
    config_file.write_text(yaml.dump(config_data))

    config = create_config(config_file=config_file)
    assert config.dpi == 300
    assert config.log_level == "DEBUG"


def test_create_config_from_cli_overrides():
    """Test creating config with CLI overrides."""
    cli_overrides = {"dpi": 400, "log_level": "ERROR"}
    config = create_config(cli_overrides=cli_overrides)
    assert config.dpi == 400
    assert config.log_level == "ERROR"


def test_create_config_merging_all_sources(tmp_path):
    """Test that config merging works with all sources."""
    # Set environment variable
    os.environ["PDF_READER_DPI"] = "250"

    # Create config file
    config_file = tmp_path / "config.yaml"
    config_data = {"dpi": 300, "log_level": "WARNING"}
    config_file.write_text(yaml.dump(config_data))

    # CLI overrides
    cli_overrides = {"dpi": 400}

    try:
        config = create_config(config_file=config_file, cli_overrides=cli_overrides)
        # CLI should win for dpi
        assert config.dpi == 400
        # File should win for log_level (env doesn't set it)
        assert config.log_level == "WARNING"
    finally:
        os.environ.pop("PDF_READER_DPI", None)


def test_create_config_with_input_path(tmp_path):
    """Test creating config with input_path."""
    pdf_path = tmp_path / "test.pdf"
    pdf_path.touch()

    cli_overrides = {"input_path": str(pdf_path)}
    config = create_config(cli_overrides=cli_overrides)
    assert config.input_path == pdf_path



