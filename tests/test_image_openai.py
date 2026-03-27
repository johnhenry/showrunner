# tests/test_image_openai.py
from unittest.mock import patch, MagicMock
import base64
import sys

import pytest

from showrunner.providers.image.base import ImageProvider


def test_openai_is_image_provider():
    from showrunner.providers.image.openai import OpenAIImageProvider
    assert issubclass(OpenAIImageProvider, ImageProvider)


def test_openai_requires_api_key():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="API key"):
            from showrunner.providers.image.openai import OpenAIImageProvider
            OpenAIImageProvider(api_key="")


def _make_provider(mock_openai_mod):
    """Create an OpenAIImageProvider with mocked OpenAI client."""
    mock_client = MagicMock()
    mock_openai_mod.OpenAI.return_value = mock_client
    with patch.dict("sys.modules", {"openai": mock_openai_mod}):
        import importlib
        import showrunner.providers.image.openai as mod
        importlib.reload(mod)
        provider = mod.OpenAIImageProvider(api_key="test-key")
    return provider, mock_client


def test_openai_generate_b64(tmp_path):
    fake_b64 = base64.b64encode(b"fake-png-data").decode()

    mock_openai_mod = MagicMock()
    provider, mock_client = _make_provider(mock_openai_mod)

    mock_image = MagicMock()
    mock_image.b64_json = fake_b64
    mock_image.url = None
    mock_client.images.generate.return_value = MagicMock(data=[mock_image])

    output = tmp_path / "test.png"
    result = provider.generate("A sunset", output_path=output)

    assert result == output
    assert output.read_bytes() == b"fake-png-data"


def test_openai_generate_url(tmp_path):
    mock_openai_mod = MagicMock()
    provider, mock_client = _make_provider(mock_openai_mod)

    mock_image = MagicMock()
    mock_image.b64_json = None
    mock_image.url = "https://example.com/image.png"
    mock_client.images.generate.return_value = MagicMock(data=[mock_image])

    import httpx as real_httpx
    mock_resp = MagicMock()
    mock_resp.content = b"downloaded-image"

    with patch.object(real_httpx, "get", return_value=mock_resp):
        output = tmp_path / "test.png"
        result = provider.generate("A sunset", output_path=output)

    assert result == output
    assert output.read_bytes() == b"downloaded-image"


def test_openai_aspect_ratio_mapping(tmp_path):
    fake_b64 = base64.b64encode(b"data").decode()

    mock_openai_mod = MagicMock()
    provider, mock_client = _make_provider(mock_openai_mod)

    mock_image = MagicMock()
    mock_image.b64_json = fake_b64
    mock_image.url = None
    mock_client.images.generate.return_value = MagicMock(data=[mock_image])

    output = tmp_path / "test.png"
    provider.generate("test", aspect_ratio="16:9", output_path=output)

    call_kwargs = mock_client.images.generate.call_args
    assert call_kwargs.kwargs["size"] == "1536x1024"
