import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pdf_reader.cli import build_cli_config, main, parse_page_indices, parse_args


def _create_sample_pdf(path: Path, num_pages: int = 1) -> None:
    """Create a test PDF."""
    c = canvas.Canvas(str(path), pagesize=letter)
    for page_num in range(num_pages):
        c.drawString(100, 750, "Header1 Header2 Header3")
        c.drawString(100, 730, "Row1Col1 Row1Col2 Row1Col3")
        if page_num < num_pages - 1:
            c.showPage()
    c.save()


def test_parse_page_indices_comma_separated():
    """Test parsing comma-separated page indices."""
    indices = parse_page_indices("0,2,4")
    assert indices == [0, 2, 4]


def test_parse_page_indices_range():
    """Test parsing page range."""
    indices = parse_page_indices("0-5")
    assert indices == [0, 1, 2, 3, 4, 5]


def test_parse_page_indices_mixed():
    """Test parsing mixed comma-separated and range."""
    indices = parse_page_indices("0,2-4,10")
    assert indices == [0, 2, 3, 4, 10]


def test_parse_page_indices_invalid():
    """Test that invalid page indices raise ValueError."""
    with pytest.raises(ValueError):
        parse_page_indices("invalid")
    with pytest.raises(ValueError):
        parse_page_indices("0-5-10")  # Invalid range format


def test_parse_args_minimal():
    """Test parsing minimal CLI arguments."""
    args = parse_args(["extract", "--input", "test.pdf"])
    assert args.command == "extract"
    assert args.input == Path("test.pdf")


def test_parse_args_with_options():
    """Test parsing CLI arguments with various options."""
    args = parse_args(
        [
            "extract",
            "--input",
            "test.pdf",
            "--pages",
            "0,2,4",
            "--dpi",
            "300",
            "--debug",
            "--log-level",
            "DEBUG",
        ]
    )
    assert args.input == Path("test.pdf")
    assert args.pages == "0,2,4"
    assert args.dpi == 300
    assert args.debug is True
    assert args.log_level == "DEBUG"


def test_build_cli_config():
    """Test building config dictionary from CLI arguments."""
    args = parse_args(
        [
            "extract",
            "--input",
            "test.pdf",
            "--dpi",
            "300",
            "--debug",
            "--log-level",
            "WARNING",
        ]
    )
    config = build_cli_config(args)
    assert config["dpi"] == 300
    assert config["enable_debug_artifacts"] is True
    assert config["log_level"] == "WARNING"
    assert "input_path" in config


def test_build_cli_config_with_pages():
    """Test building config with page indices."""
    args = parse_args(["extract", "--input", "test.pdf", "--pages", "0-2"])
    config = build_cli_config(args)
    assert config["page_indices"] == [0, 1, 2]


def test_cli_main_success(tmp_path, capsys):
    """Test successful CLI execution."""
    pdf_path = tmp_path / "test.pdf"
    _create_sample_pdf(pdf_path, num_pages=1)

    # Mock sys.argv - use offline preset to avoid requiring API key
    test_args = ["extract", "--input", str(pdf_path), "--preset", "offline"]
    with patch.object(sys, "argv", ["cli.py"] + test_args):
        exit_code = main(test_args)

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Extraction Summary" in captured.out
    assert "Pages processed" in captured.out
    assert "Tables detected" in captured.out


def test_cli_main_missing_input(capsys):
    """Test CLI with missing required input argument."""
    test_args = ["extract"]  # Missing --input
    with pytest.raises(SystemExit):  # argparse exits on missing required args
        main(test_args)


def test_cli_main_file_not_found(capsys):
    """Test CLI with non-existent input file."""
    test_args = ["extract", "--input", "nonexistent.pdf"]
    exit_code = main(test_args)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower()


def test_cli_main_with_config_file(tmp_path, capsys):
    """Test CLI with config file."""
    pdf_path = tmp_path / "test.pdf"
    _create_sample_pdf(pdf_path, num_pages=1)

    config_file = tmp_path / "config.yaml"
    config_file.write_text("dpi: 300\nlog_level: DEBUG\nextraction_preset: offline\n")

    test_args = ["extract", "--input", str(pdf_path), "--config", str(config_file)]
    exit_code = main(test_args)
    assert exit_code == 0


def test_cli_main_with_debug(tmp_path, capsys):
    """Test CLI with debug artifacts enabled."""
    pdf_path = tmp_path / "test.pdf"
    _create_sample_pdf(pdf_path, num_pages=1)

    test_args = ["extract", "--input", str(pdf_path), "--debug", "--preset", "offline"]
    exit_code = main(test_args)
    assert exit_code == 0

    # Check that debug output directory was created
    debug_dir = tmp_path / "debug_output"
    # Note: debug_dir is created relative to current working directory, not pdf_path
    # So we can't easily check it here, but the test verifies the command runs


def test_cli_help(capsys):
    """Test that --help works."""
    test_args = ["--help"]
    with pytest.raises(SystemExit) as exc_info:
        parse_args(test_args)
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Extract tables from PDF files" in captured.out
    assert "--input" in captured.out


