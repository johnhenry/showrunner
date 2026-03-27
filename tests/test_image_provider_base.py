import pytest
from showrunner.providers.image.base import ImageProvider


def test_image_provider_is_abstract():
    with pytest.raises(TypeError):
        ImageProvider()


def test_image_provider_has_generate_method():
    assert hasattr(ImageProvider, "generate")
