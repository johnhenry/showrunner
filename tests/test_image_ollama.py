# tests/test_image_ollama.py
from unittest.mock import patch, MagicMock
import base64

import pytest

from showrunner.providers.image.base import ImageProvider
from showrunner.providers.image.ollama import OllamaImageProvider


def test_ollama_is_image_provider():
    assert issubclass(OllamaImageProvider, ImageProvider)


def test_ollama_no_api_key_needed():
    provider = OllamaImageProvider()
    assert provider._model == "x/z-image-turbo"
    assert "11434" in provider._host


def test_ollama_generate(tmp_path):
    fake_b64 = base64.b64encode(b"ollama-image-data").decode()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"images": [fake_b64]}

    import httpx
    with patch.object(httpx, "post", return_value=mock_resp):
        provider = OllamaImageProvider(model="x/z-image-turbo")
        output = tmp_path / "test.png"
        result = provider.generate("A cat", output_path=output)

    assert result == output
    assert output.read_bytes() == b"ollama-image-data"


def test_ollama_no_images_raises(tmp_path):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "text only"}

    import httpx
    with patch.object(httpx, "post", return_value=mock_resp):
        provider = OllamaImageProvider()
        with pytest.raises(RuntimeError, match="no images"):
            provider.generate("test", output_path=tmp_path / "test.png")
