"""Tests for Gemini End-to-End extraction strategy."""

import json
import threading
from unittest.mock import Mock, patch, MagicMock

import pytest
from PIL import Image

from pdf_reader.pipeline import PipelineConfig, PageProcessingResult
from pdf_reader.strategies import GeminiEndToEndStrategy


@pytest.fixture
def sample_page_image():
    """Create a sample page image for testing."""
    return Image.new("RGB", (800, 600), color="white")


@pytest.fixture
def sample_config():
    """Create a sample pipeline config for testing."""
    return PipelineConfig(
        extraction_strategy="llm_end_to_end",
        llm_provider="google",
        llm_model="gemini-1.5-flash",
        llm_api_key="test-api-key",
        llm_consistency_attempts=1,
        llm_consistency_threshold=0.8,
        extraction_preset="offline",
    )


@pytest.fixture
def sample_llm_response():
    """Sample LLM response JSON."""
    return {
        "tables": [
            {
                "table_id": "table_1",
                "columns": ["Name", "Age", "City"],
                "rows": [
                    ["Alice", "30", "NYC"],
                    ["Bob", "25", "LA"],
                    ["Charlie", "35", "SF"],
                ],
            }
        ]
    }


def test_gemini_strategy_initialization():
    """Test that GeminiEndToEndStrategy can be initialized."""
    strategy = GeminiEndToEndStrategy()
    assert strategy is not None


def test_gemini_strategy_prompt_generation():
    """Test that the strategy generates a valid prompt."""
    strategy = GeminiEndToEndStrategy()
    prompt = strategy._get_prompt()
    
    assert "extract" in prompt.lower()
    assert "json" in prompt.lower()
    assert "tables" in prompt.lower()


def test_gemini_strategy_json_parsing(sample_llm_response):
    """Test JSON parsing from LLM response."""
    strategy = GeminiEndToEndStrategy()
    
    # Test clean JSON
    json_str = json.dumps(sample_llm_response)
    parsed = strategy._parse_response(json_str)
    assert parsed == sample_llm_response
    
    # Test JSON with markdown code blocks
    markdown_json = f"```json\n{json_str}\n```"
    parsed = strategy._parse_response(markdown_json)
    assert parsed == sample_llm_response
    
    # Test JSON with just code blocks
    code_block_json = f"```\n{json_str}\n```"
    parsed = strategy._parse_response(code_block_json)
    assert parsed == sample_llm_response


def test_gemini_strategy_consensus_single_result(sample_llm_response):
    """Test consensus logic with a single result."""
    strategy = GeminiEndToEndStrategy()
    
    results = [sample_llm_response]
    consensus = strategy._consensus_vote(results, threshold=0.8)
    
    assert len(consensus) == 1
    assert consensus[0]["table_id"] == "table_1"
    assert len(consensus[0]["rows"]) == 3


def test_gemini_strategy_consensus_multiple_results(sample_llm_response):
    """Test consensus logic with multiple identical results."""
    strategy = GeminiEndToEndStrategy()
    
    # Three identical results
    results = [sample_llm_response, sample_llm_response, sample_llm_response]
    consensus = strategy._consensus_vote(results, threshold=0.8)
    
    assert len(consensus) == 1
    assert consensus[0]["table_id"] == "table_1"
    assert len(consensus[0]["rows"]) == 3


def test_gemini_strategy_consensus_voting():
    """Test consensus voting with divergent results."""
    strategy = GeminiEndToEndStrategy()
    
    result1 = {
        "tables": [
            {
                "table_id": "table_1",
                "columns": ["A", "B"],
                "rows": [["1", "2"], ["3", "4"]],
            }
        ]
    }
    
    result2 = {
        "tables": [
            {
                "table_id": "table_1",
                "columns": ["A", "B"],
                "rows": [["1", "2"], ["3", "5"]],  # Different value in last cell
            }
        ]
    }
    
    result3 = {
        "tables": [
            {
                "table_id": "table_1",
                "columns": ["A", "B"],
                "rows": [["1", "2"], ["3", "4"]],  # Matches result1
            }
        ]
    }
    
    results = [result1, result2, result3]
    consensus = strategy._consensus_vote(results, threshold=0.8)
    
    # Should vote for "4" (2 votes) over "5" (1 vote)
    assert consensus[0]["rows"][1][1] == "4"


def test_gemini_strategy_convert_to_spec(sample_llm_response):
    """Test conversion from JSON to TableDataFrameSpec."""
    strategy = GeminiEndToEndStrategy()
    
    table_data = sample_llm_response["tables"][0]
    spec, metadata = strategy._convert_to_spec(table_data, page_index=0)
    
    assert spec.table_metadata_id == "table_1"
    assert len(spec.rows) == 3
    assert len(spec.columns) == 3
    assert spec.columns[0].name == "Name"
    
    assert metadata.table_id == "table_1"
    assert metadata.page_index == 0
    assert metadata.grid_shape == (3, 3)
    assert metadata.status == "success"
    assert "llm_extracted" in metadata.irregularities


@patch("pdf_reader.strategies.genai")
def test_gemini_strategy_call_google_genai(mock_genai, sample_page_image, sample_config, sample_llm_response):
    """Test calling Google GenAI API."""
    strategy = GeminiEndToEndStrategy()
    
    # Mock the GenAI response
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(sample_llm_response)
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model
    
    # Convert image to bytes
    import io
    img_byte_arr = io.BytesIO()
    sample_page_image.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()
    
    prompt = "Test prompt"
    response_text = strategy._call_google_genai(img_bytes, prompt, sample_config)
    
    assert response_text == json.dumps(sample_llm_response)
    mock_genai.configure.assert_called_once_with(api_key="test-api-key")
    mock_genai.GenerativeModel.assert_called_once_with("gemini-1.5-flash")


@patch("pdf_reader.strategies.openai")
def test_gemini_strategy_call_openai_style(mock_openai, sample_page_image, sample_llm_response):
    """Test calling OpenAI-style API."""
    strategy = GeminiEndToEndStrategy()
    
    config = PipelineConfig(
        extraction_strategy="llm_end_to_end",
        llm_provider="openai",
        llm_model="gpt-4o",
        llm_api_key="test-api-key",
        extraction_preset="offline",
    )
    
    # Mock the OpenAI response
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = json.dumps(sample_llm_response)
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.OpenAI.return_value = mock_client
    
    # Convert image to bytes
    import io
    img_byte_arr = io.BytesIO()
    sample_page_image.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()
    
    prompt = "Test prompt"
    response_text = strategy._call_openai_style(img_bytes, prompt, config)
    
    assert response_text == json.dumps(sample_llm_response)
    mock_openai.OpenAI.assert_called_once_with(api_key="test-api-key")


@patch.object(GeminiEndToEndStrategy, "_call_llm")
def test_gemini_strategy_process_page_success(
    mock_call_llm, sample_page_image, sample_config, sample_llm_response
):
    """Test successful page processing with Gemini strategy."""
    strategy = GeminiEndToEndStrategy()
    
    # Mock LLM call to return valid JSON
    mock_call_llm.return_value = json.dumps(sample_llm_response)
    
    logger = Mock()
    cancel_event = threading.Event()
    
    result = strategy.process_page(
        page_index=0,
        page_image=sample_page_image,
        config=sample_config,
        logger=logger,
        cancel_event=cancel_event,
    )
    
    assert isinstance(result, PageProcessingResult)
    assert result.page_index == 0
    assert result.tables_extracted == 1
    assert result.tables_detected == 1
    assert len(result.tables) == 1
    assert len(result.metadata) == 1
    assert result.metadata[0].table_id == "table_1"


@patch.object(GeminiEndToEndStrategy, "_call_llm")
def test_gemini_strategy_process_page_with_consistency(
    mock_call_llm, sample_page_image, sample_llm_response
):
    """Test page processing with consistency checking."""
    strategy = GeminiEndToEndStrategy()
    
    config = PipelineConfig(
        extraction_strategy="llm_end_to_end",
        llm_api_key="test-api-key",
        llm_consistency_attempts=3,
        llm_consistency_threshold=0.8,
        extraction_preset="offline",
    )
    
    # Mock LLM to return valid JSON for all attempts
    mock_call_llm.return_value = json.dumps(sample_llm_response)
    
    logger = Mock()
    cancel_event = threading.Event()
    
    result = strategy.process_page(
        page_index=0,
        page_image=sample_page_image,
        config=config,
        logger=logger,
        cancel_event=cancel_event,
    )
    
    assert result.tables_extracted == 1
    assert mock_call_llm.call_count == 3  # Called 3 times for consistency


@patch.object(GeminiEndToEndStrategy, "_call_llm")
def test_gemini_strategy_process_page_failure(mock_call_llm, sample_page_image, sample_config):
    """Test page processing when LLM calls fail."""
    strategy = GeminiEndToEndStrategy()
    
    # Mock LLM to raise an exception
    mock_call_llm.side_effect = Exception("API Error")
    
    logger = Mock()
    cancel_event = threading.Event()
    
    result = strategy.process_page(
        page_index=0,
        page_image=sample_page_image,
        config=sample_config,
        logger=logger,
        cancel_event=cancel_event,
    )
    
    assert result.page_skipped is True
    assert len(result.errors) > 0
    assert "Gemini extraction failed" in result.errors[0]


def test_gemini_strategy_no_api_key(sample_page_image):
    """Test that strategy fails gracefully without API key."""
    strategy = GeminiEndToEndStrategy()
    
    config = PipelineConfig(
        extraction_strategy="llm_end_to_end",
        llm_api_key=None,  # No API key,
        extraction_preset="offline",
    )
    
    logger = Mock()
    cancel_event = threading.Event()
    
    result = strategy.process_page(
        page_index=0,
        page_image=sample_page_image,
        config=config,
        logger=logger,
        cancel_event=cancel_event,
    )
    
    assert result.page_skipped is True
    assert "API key required" in result.errors[0]


def test_gemini_strategy_cancellation(sample_page_image, sample_config):
    """Test that strategy respects cancellation event."""
    strategy = GeminiEndToEndStrategy()
    
    logger = Mock()
    cancel_event = threading.Event()
    cancel_event.set()  # Cancel immediately
    
    with patch.object(strategy, "_call_llm"):
        result = strategy.process_page(
            page_index=0,
            page_image=sample_page_image,
            config=sample_config,
            logger=logger,
            cancel_event=cancel_event,
        )
    
    # Should complete but with no LLM calls made
    assert isinstance(result, PageProcessingResult)


