"""LLM-based text extraction service for low-confidence OCR cases.

This module provides an interface and implementations for using Large Language Models
(LLMs) to extract text from images when primary OCR methods have low confidence.

The service is designed to be provider-agnostic, with concrete implementations
for specific LLM providers (e.g., OpenAI, Anthropic).
"""

from __future__ import annotations

import base64
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from PIL import Image


class LLMExtractionError(Exception):
    """Error raised when LLM extraction fails."""


class LLMExtractionService(ABC):
    """Abstract base class for LLM-based text extraction services.

    This interface allows the pipeline to use different LLM providers
    without coupling to provider-specific implementations.
    """

    @abstractmethod
    def extract_text_from_image(
        self, image: Image.Image, context: Optional[str] = None
    ) -> str:
        """Extract text from an image using an LLM.

        Args:
            image: PIL Image containing the cell or table region to extract text from.
            context: Optional context hint (e.g., "header cell", "numeric value")
                to help the LLM understand what to extract.

        Returns:
            Extracted text string.

        Raises:
            LLMExtractionError: If extraction fails (API error, rate limit, etc.).
        """
        pass


@dataclass
class OpenAIExtractionService(LLMExtractionService):
    """OpenAI-based text extraction service using GPT-4 Vision or similar models.

    This implementation uses OpenAI's vision-capable models to extract text
    from images when OCR confidence is low.

    Example:
        service = OpenAIExtractionService(api_key="sk-...", model="gpt-4o")
        text = service.extract_text_from_image(cell_image, context="table cell")
    """

    api_key: str
    model: str = "gpt-4o"
    max_tokens: int = 300

    def extract_text_from_image(
        self, image: Image.Image, context: Optional[str] = None
    ) -> str:
        """Extract text from an image using OpenAI's vision API.

        Args:
            image: PIL Image to extract text from.
            context: Optional context hint for the LLM.

        Returns:
            Extracted text string.

        Raises:
            LLMExtractionError: If API call fails.
        """
        try:
            import openai
        except ImportError:
            raise LLMExtractionError(
                "OpenAI library not installed. Install with: pip install openai"
            )

        # Convert image to base64-encoded PNG
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # Construct prompt
        prompt = "Extract the text content from this image. Return only the text, without any explanation or formatting."
        if context:
            prompt = f"Extract the text content from this {context} image. Return only the text, without any explanation or formatting."

        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=self.max_tokens,
            )
            extracted_text = response.choices[0].message.content.strip()
            return extracted_text if extracted_text else ""
        except Exception as exc:
            raise LLMExtractionError(f"OpenAI API call failed: {exc}") from exc


@dataclass
class MockLLMExtractionService(LLMExtractionService):
    """Mock LLM extraction service for testing.

    Returns deterministic text based on image size or a provided mapping.
    Useful for testing without making real API calls.
    """

    mock_responses: Optional[dict] = None
    default_response: str = "mock_llm_text"

    def extract_text_from_image(
        self, image: Image.Image, context: Optional[str] = None
    ) -> str:
        """Return mock extracted text for testing."""
        if self.mock_responses:
            # Use image size as a key for deterministic responses
            key = (image.size[0], image.size[1])
            if key in self.mock_responses:
                return self.mock_responses[key]
        return self.default_response



