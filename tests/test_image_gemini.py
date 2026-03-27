# tests/test_image_gemini.py
from unittest.mock import patch, MagicMock
import sys

import pytest

from showrunner.providers.image.base import ImageProvider


def test_gemini_is_image_provider():
    from showrunner.providers.image.gemini import GeminiImageProvider
    assert issubclass(GeminiImageProvider, ImageProvider)


def test_gemini_requires_api_key():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="API key"):
            from showrunner.providers.image.gemini import GeminiImageProvider
            GeminiImageProvider(api_key="")


def _make_provider_and_call(tmp_path, generated_images):
    """Create a GeminiImageProvider with fully mocked google.genai, call generate."""
    mock_genai = MagicMock()
    mock_types = MagicMock()
    mock_google = MagicMock()
    mock_google.genai = mock_genai
    mock_genai.types = mock_types

    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client
    mock_client.models.generate_images.return_value = MagicMock(
        generated_images=generated_images
    )

    # Keep mocks in sys.modules for both __init__ and generate()
    with patch.dict("sys.modules", {
        "google": mock_google,
        "google.genai": mock_genai,
        "google.genai.types": mock_types,
    }):
        import importlib
        import showrunner.providers.image.gemini as mod
        importlib.reload(mod)
        provider = mod.GeminiImageProvider(api_key="test-key")

        output = tmp_path / "test.png"
        return provider, output


def test_gemini_generate(tmp_path):
    mock_image = MagicMock()
    mock_image.image.image_bytes = b"gemini-png-data"

    mock_genai = MagicMock()
    mock_types = MagicMock()
    mock_google = MagicMock()
    mock_google.genai = mock_genai
    mock_genai.types = mock_types

    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client
    mock_client.models.generate_images.return_value = MagicMock(
        generated_images=[mock_image]
    )

    with patch.dict("sys.modules", {
        "google": mock_google,
        "google.genai": mock_genai,
        "google.genai.types": mock_types,
    }):
        import importlib
        import showrunner.providers.image.gemini as mod
        importlib.reload(mod)
        provider = mod.GeminiImageProvider(api_key="test-key")

        output = tmp_path / "test.png"
        result = provider.generate("A mountain", output_path=output)

    assert result == output
    assert output.read_bytes() == b"gemini-png-data"


def test_gemini_no_images_raises(tmp_path):
    mock_genai = MagicMock()
    mock_types = MagicMock()
    mock_google = MagicMock()
    mock_google.genai = mock_genai
    mock_genai.types = mock_types

    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client
    mock_client.models.generate_images.return_value = MagicMock(generated_images=[])

    with patch.dict("sys.modules", {
        "google": mock_google,
        "google.genai": mock_genai,
        "google.genai.types": mock_types,
    }):
        import importlib
        import showrunner.providers.image.gemini as mod
        importlib.reload(mod)
        provider = mod.GeminiImageProvider(api_key="test-key")

        with pytest.raises(RuntimeError, match="no images"):
            provider.generate("test", output_path=tmp_path / "test.png")
