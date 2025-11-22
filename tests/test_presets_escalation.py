"""Tests for extraction presets and escalation logic."""

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
def cancel_event():
    """Create a cancel event for testing."""
    return threading.Event()


class TestPresetConfiguration:
    """Test preset application logic."""

    def test_smart_preset_default(self):
        """Test that 'smart' preset is the default."""
        config = PipelineConfig()
        assert config.extraction_preset == "smart"

    def test_smart_preset_applies_correctly(self):
        """Test 'smart' preset sets correct values."""
        config = PipelineConfig(extraction_preset="smart")
        assert config.extraction_strategy == "llm_end_to_end"
        assert config.llm_provider == "google"
        assert config.llm_model == "gemini-2.5-pro"
        assert config.llm_model_escalation == "gemini-3.0-pro"
        assert config.enable_auto_escalation is False  # Conservative

    def test_premium_preset_applies_correctly(self):
        """Test 'premium' preset sets correct values."""
        config = PipelineConfig(extraction_preset="premium")
        assert config.extraction_strategy == "llm_end_to_end"
        assert config.llm_provider == "google"
        assert config.llm_model == "gemini-3.0-pro"
        assert config.llm_model_escalation is None  # No escalation needed
        assert config.enable_auto_escalation is False

    def test_offline_preset_applies_correctly(self):
        """Test 'offline' preset sets correct values."""
        config = PipelineConfig(extraction_preset="offline")
        assert config.extraction_strategy == "heuristic"
        assert config.llm_fallback_enabled is False
        assert config.enable_auto_escalation is False

    def test_preset_validation_rejects_invalid(self):
        """Test that invalid presets are rejected."""
        with pytest.raises(ValueError, match="extraction_preset must be one of"):
            PipelineConfig(extraction_preset="invalid")

    def test_preset_override_with_explicit_model(self):
        """Test that explicit model overrides preset defaults."""
        config = PipelineConfig(
            extraction_preset="smart",
            llm_model="gpt-4o"  # Override
        )
        # Preset should apply first, then override
        assert config.extraction_strategy == "llm_end_to_end"
        assert config.llm_model == "gpt-4o"  # User override takes effect


class TestEscalationLogic:
    """Test escalation logic in GeminiEndToEndStrategy."""

    def test_no_escalation_when_disabled(self, sample_page_image, cancel_event):
        """Test that escalation doesn't happen when disabled."""
        config = PipelineConfig(
            extraction_strategy="llm_end_to_end",
            llm_provider="google",
            llm_model="gemini-2.5-pro",
            llm_model_escalation="gemini-3.0-pro",
            llm_api_key="test-key",
            enable_auto_escalation=False,  # Disabled
            llm_consistency_attempts=1,
        )
        
        strategy = GeminiEndToEndStrategy()
        logger = Mock()
        
        # Mock primary model to fail
        with patch.object(strategy, '_call_llm_with_tracking') as mock_call:
            mock_call.side_effect = RuntimeError("Primary model failed")
            
            result = strategy.process_page(0, sample_page_image, config, logger, cancel_event)
            
            # Should fail without escalation
            assert result.page_skipped is True
            assert len(result.errors) > 0
            assert "failed" in result.errors[0].lower()
            
            # Should only call primary model (1 attempt)
            assert mock_call.call_count == 1

    def test_escalation_when_enabled_and_primary_fails(self, sample_page_image, cancel_event):
        """Test that escalation happens when enabled and primary fails."""
        config = PipelineConfig(
            extraction_strategy="llm_end_to_end",
            llm_provider="google",
            llm_model="gemini-2.5-pro",
            llm_model_escalation="gemini-3.0-pro",
            llm_api_key="test-key",
            enable_auto_escalation=True,  # Enabled
            llm_consistency_attempts=1,
        )
        
        strategy = GeminiEndToEndStrategy()
        logger = Mock()
        
        # Mock: primary fails, escalation succeeds
        mock_response = {
            "tables": [{
                "table_id": "table_1",
                "columns": ["A", "B"],
                "rows": [["1", "2"]]
            }]
        }
        
        # Mock the conversion function to avoid needing full data models
        mock_spec = Mock()
        mock_meta = Mock()
        
        with patch.object(strategy, '_call_llm_with_tracking') as mock_call, \
             patch.object(strategy, '_parse_response', return_value=mock_response), \
             patch.object(strategy, '_convert_to_spec', return_value=(mock_spec, mock_meta)):
            
            # First call (primary) fails, second call (escalation) succeeds
            mock_call.side_effect = [
                RuntimeError("Primary failed"),  # Primary attempt
                ("valid json response", 1000, 500)  # Escalation succeeds
            ]
            
            result = strategy.process_page(0, sample_page_image, config, logger, cancel_event)
            
            # Should succeed via escalation
            assert result.page_skipped is False
            assert result.tables_extracted == 1
            assert result.llm_calls_primary == 1
            assert result.llm_calls_escalation == 1
            assert result.model_used == "gemini-3.0-pro"

    def test_escalation_tracks_tokens_correctly(self, sample_page_image, cancel_event):
        """Test that token usage is tracked for escalation calls."""
        config = PipelineConfig(
            extraction_strategy="llm_end_to_end",
            llm_provider="google",
            llm_model="gemini-2.5-pro",
            llm_model_escalation="gemini-3.0-pro",
            llm_api_key="test-key",
            enable_auto_escalation=True,
            llm_consistency_attempts=1,
        )
        
        strategy = GeminiEndToEndStrategy()
        logger = Mock()
        
        mock_response = {
            "tables": [{
                "table_id": "table_1",
                "columns": ["A"],
                "rows": [["1"]]
            }]
        }
        
        mock_spec = Mock()
        mock_meta = Mock()
        
        with patch.object(strategy, '_call_llm_with_tracking') as mock_call, \
             patch.object(strategy, '_parse_response', return_value=mock_response), \
             patch.object(strategy, '_convert_to_spec', return_value=(mock_spec, mock_meta)):
            
            # Primary fails, escalation succeeds with token counts
            mock_call.side_effect = [
                RuntimeError("Primary failed"),
                ("response", 2000, 800)  # input_tokens=2000, output_tokens=800
            ]
            
            result = strategy.process_page(0, sample_page_image, config, logger, cancel_event)
            
            assert result.llm_tokens_input == 2000
            assert result.llm_tokens_output == 800
            assert result.llm_calls_escalation == 1


class TestCostEstimation:
    """Test cost estimation logic."""

    def test_gemini_25_pro_is_free(self):
        """Test that Gemini 2.5 Pro returns zero cost."""
        cost = GeminiEndToEndStrategy.estimate_cost(
            tokens_input=10000,
            tokens_output=5000,
            model_name="gemini-2.5-pro"
        )
        assert cost == 0.0

    def test_gemini_25_flash_is_free(self):
        """Test that Gemini 2.5 Flash returns zero cost."""
        cost = GeminiEndToEndStrategy.estimate_cost(
            tokens_input=10000,
            tokens_output=5000,
            model_name="gemini-2.5-flash"
        )
        assert cost == 0.0

    def test_gemini_30_pro_has_cost(self):
        """Test that Gemini 3.0 Pro has non-zero cost."""
        cost = GeminiEndToEndStrategy.estimate_cost(
            tokens_input=1_000_000,  # 1M tokens
            tokens_output=1_000_000,
            model_name="gemini-3.0-pro"
        )
        # Should be ~$1.25 input + $5.00 output = $6.25 per 1M tokens
        assert cost > 6.0
        assert cost < 7.0

    def test_gpt4o_has_cost(self):
        """Test that GPT-4o has expected cost."""
        cost = GeminiEndToEndStrategy.estimate_cost(
            tokens_input=1_000_000,
            tokens_output=1_000_000,
            model_name="gpt-4o"
        )
        # Should be ~$2.50 input + $10.00 output = $12.50 per 1M tokens
        assert cost > 12.0
        assert cost < 13.0

    def test_flash_models_are_cheap(self):
        """Test that Flash models have low cost."""
        cost = GeminiEndToEndStrategy.estimate_cost(
            tokens_input=1_000_000,
            tokens_output=1_000_000,
            model_name="gemini-1.5-flash"
        )
        # Should be ~$0.075 input + $0.30 output = $0.375 per 1M tokens
        assert cost < 0.5

    def test_zero_tokens_zero_cost(self):
        """Test that zero tokens returns zero cost."""
        cost = GeminiEndToEndStrategy.estimate_cost(
            tokens_input=0,
            tokens_output=0,
            model_name="gpt-4o"
        )
        assert cost == 0.0


class TestModelTracking:
    """Test that model usage is tracked correctly."""

    def test_primary_model_tracked(self, sample_page_image, cancel_event):
        """Test that primary model is tracked when used."""
        config = PipelineConfig(
            extraction_strategy="llm_end_to_end",
            llm_provider="google",
            llm_model="gemini-2.5-pro",
            llm_api_key="test-key",
            llm_consistency_attempts=1,
        )
        
        strategy = GeminiEndToEndStrategy()
        logger = Mock()
        
        mock_response = {
            "tables": [{
                "table_id": "table_1",
                "columns": ["A"],
                "rows": [["1"]]
            }]
        }
        
        with patch.object(strategy, '_call_llm_with_tracking', return_value=("response", 1000, 500)), \
             patch.object(strategy, '_parse_response', return_value=mock_response):
            
            result = strategy.process_page(0, sample_page_image, config, logger, cancel_event)
            
            assert result.model_used == "gemini-2.5-pro"
            assert result.llm_calls_primary == 1
            assert result.llm_calls_escalation == 0

    def test_escalation_model_tracked(self, sample_page_image, cancel_event):
        """Test that escalation model is tracked when used."""
        config = PipelineConfig(
            extraction_strategy="llm_end_to_end",
            llm_provider="google",
            llm_model="gemini-2.5-pro",
            llm_model_escalation="gemini-3.0-pro",
            llm_api_key="test-key",
            enable_auto_escalation=True,
            llm_consistency_attempts=1,
        )
        
        strategy = GeminiEndToEndStrategy()
        logger = Mock()
        
        mock_response = {
            "tables": [{
                "table_id": "table_1",
                "columns": ["A"],
                "rows": [["1"]]
            }]
        }
        
        mock_spec = Mock()
        mock_meta = Mock()
        
        with patch.object(strategy, '_call_llm_with_tracking') as mock_call, \
             patch.object(strategy, '_parse_response', return_value=mock_response), \
             patch.object(strategy, '_convert_to_spec', return_value=(mock_spec, mock_meta)):
            
            # Primary fails, escalation succeeds
            mock_call.side_effect = [
                RuntimeError("Failed"),
                ("response", 1000, 500)
            ]
            
            result = strategy.process_page(0, sample_page_image, config, logger, cancel_event)
            
            assert result.model_used == "gemini-3.0-pro"
            assert result.llm_calls_primary == 1
            assert result.llm_calls_escalation == 1

