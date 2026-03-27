# tests/test_faceless_with_images.py
from unittest.mock import MagicMock
from pathlib import Path

from showrunner.formats.faceless_explainer.assets import (
    generate_scene_code,
    generate_all_scene_code,
    generate_scene_images,
    CODEGEN_SYSTEM_PROMPT,
    CODEGEN_IMAGE_ADDENDUM,
)
from showrunner.formats.faceless_explainer import FacelessExplainerFormat
from showrunner.plan import Plan, Scene


def test_image_addendum_references_staticfile():
    """The image prompt addendum tells the LLM to use staticFile."""
    rendered = CODEGEN_IMAGE_ADDENDUM.format(image_filename="hook.png")
    assert 'staticFile("images/hook.png")' in rendered
    assert "Img" in rendered


def test_image_addendum_defers_to_visual():
    """The addendum should tell the LLM to follow visual description for placement."""
    rendered = CODEGEN_IMAGE_ADDENDUM.format(image_filename="hook.png")
    assert "visual description" in rendered.lower()
    assert "default to" in rendered.lower()  # has a fallback


def test_codegen_with_image_filename():
    """When image_filename is provided, system prompt includes image instructions."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '```tsx\nexport default function Hook() { return <div />; }\n```'
    mock_validate = MagicMock(return_value=(True, ""))

    scene = Scene(id="hook", duration=5, narration="Hello", visual="City skyline")
    generate_scene_code(
        scene=scene, style_context="dark", llm=mock_llm,
        validate_fn=mock_validate, width=1080, height=1920,
        image_filename="hook.png",
    )

    call_args = mock_llm.generate.call_args
    system_prompt = call_args.kwargs.get("system") or call_args.args[0]
    assert "hook.png" in system_prompt
    assert "staticFile" in system_prompt
    assert "background" in system_prompt.lower()


def test_codegen_without_image_filename():
    """Without image_filename, system prompt does NOT include image instructions."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '```tsx\nexport default function Hook() { return <div />; }\n```'
    mock_validate = MagicMock(return_value=(True, ""))

    scene = Scene(id="hook", duration=5, narration="Hello", visual="Title card")
    generate_scene_code(
        scene=scene, style_context="dark", llm=mock_llm,
        validate_fn=mock_validate, width=1080, height=1920,
        image_filename=None,
    )

    call_args = mock_llm.generate.call_args
    system_prompt = call_args.kwargs.get("system") or call_args.args[0]
    assert "BACKGROUND IMAGE" not in system_prompt


def test_generate_all_scene_code_passes_image_filenames():
    """When scene_images is provided, each scene gets its image filename."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '```tsx\nexport default function S() { return <div />; }\n```'

    written = {}

    def write_fn(scene_id, code):
        written[scene_id] = code
        return Path(f"/tmp/{scene_id}.tsx")

    plan = Plan(
        title="Test", total_duration=10,
        scenes=[
            Scene(id="s1", duration=5, narration="N", visual="V1"),
            Scene(id="s2", duration=5, narration="N", visual="V2"),
        ],
    )

    scene_images = {
        "s1": Path("/work/public/images/s1.png"),
        # s2 has no image
    }

    generate_all_scene_code(
        plan=plan, style_context="test", llm=mock_llm,
        write_fn=write_fn, validate_fn=lambda c: (True, ""),
        scene_images=scene_images,
    )

    assert len(written) == 2
    # Check that s1's call included image context, s2's didn't
    calls = mock_llm.generate.call_args_list
    s1_system = calls[0].kwargs.get("system") or calls[0].args[0]
    s2_system = calls[1].kwargs.get("system") or calls[1].args[0]
    assert "s1.png" in s1_system
    assert "BACKGROUND IMAGE" not in s2_system


def _make_fake_image_provider():
    mock = MagicMock()

    def fake_generate(prompt, *, size, aspect_ratio, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-image")
        return output_path

    mock.generate.side_effect = fake_generate
    return mock


def test_generate_scene_images(tmp_path):
    plan = Plan(
        title="Test", total_duration=10,
        scenes=[
            Scene(id="hook", duration=5, narration="N", visual="A cityscape"),
            Scene(id="main", duration=5, narration="N", visual="A forest"),
        ],
    )
    provider = _make_fake_image_provider()
    images = generate_scene_images(
        plan, image=provider, output_dir=tmp_path,
        width=1080, height=1920,
    )

    assert len(images) == 2
    assert "hook" in images
    assert "main" in images
    assert images["hook"].exists()
    assert provider.generate.call_count == 2
    # Check it used 9:16 ratio (height > width)
    call_kwargs = provider.generate.call_args_list[0]
    assert call_kwargs.kwargs["aspect_ratio"] == "9:16"
    assert call_kwargs.kwargs["size"] == "1080x1920"


def test_generate_scene_images_parallel(tmp_path):
    plan = Plan(
        title="Test", total_duration=10,
        scenes=[
            Scene(id="s1", duration=5, narration="N", visual="V1"),
            Scene(id="s2", duration=5, narration="N", visual="V2"),
        ],
    )
    provider = _make_fake_image_provider()
    images = generate_scene_images(
        plan, image=provider, output_dir=tmp_path,
        width=1920, height=1080, parallel=True,
    )

    assert len(images) == 2
    assert provider.generate.call_count == 2


def test_format_generate_assets_with_images(tmp_path):
    """Full format integration: with_images generates images then TSX."""
    fmt = FacelessExplainerFormat()
    fmt._aspect_ratio = "9:16"
    fmt._voice = "af_heart"
    fmt._speed = 1.0
    fmt._parallel = False
    fmt._with_images = True

    plan = Plan(
        title="Test", total_duration=5,
        scenes=[Scene(id="hook", duration=5, narration="Hello", visual="A sunset")],
    )

    mock_llm = MagicMock()
    mock_llm.generate.return_value = '```tsx\nexport default function Hook() { return <div />; }\n```'
    mock_tts = MagicMock()
    mock_tts.synthesize.return_value = MagicMock(duration=3.0)
    mock_image = _make_fake_image_provider()

    # Setup work dir structure
    (tmp_path / "public" / "audio").mkdir(parents=True)
    (tmp_path / "src" / "scenes").mkdir(parents=True)

    providers = {"llm": mock_llm, "tts": mock_tts, "image": mock_image}
    assets = fmt.generate_assets(plan, providers, tmp_path)

    # Image was generated
    assert "scene_images" in assets
    assert "hook" in assets["scene_images"]
    assert (tmp_path / "public" / "images" / "hook.png").exists()

    # TSX was generated with image context
    system_prompt = mock_llm.generate.call_args.kwargs.get("system") or mock_llm.generate.call_args.args[0]
    assert "hook.png" in system_prompt

    # Scene code was written
    assert (tmp_path / "src" / "scenes" / "Hook.tsx").exists()


def test_format_generate_assets_without_images(tmp_path):
    """Without with_images, no image generation occurs."""
    fmt = FacelessExplainerFormat()
    fmt._aspect_ratio = "9:16"
    fmt._voice = "af_heart"
    fmt._speed = 1.0
    fmt._parallel = False
    fmt._with_images = False

    plan = Plan(
        title="Test", total_duration=5,
        scenes=[Scene(id="hook", duration=5, narration="Hello", visual="Title card")],
    )

    mock_llm = MagicMock()
    mock_llm.generate.return_value = '```tsx\nexport default function Hook() { return <div />; }\n```'
    mock_tts = MagicMock()
    mock_tts.synthesize.return_value = MagicMock(duration=3.0)

    (tmp_path / "public" / "audio").mkdir(parents=True)
    (tmp_path / "src" / "scenes").mkdir(parents=True)

    providers = {"llm": mock_llm, "tts": mock_tts}
    assets = fmt.generate_assets(plan, providers, tmp_path)

    assert assets["scene_images"] == {}
    # TSX prompt should NOT have image instructions
    system_prompt = mock_llm.generate.call_args.kwargs.get("system") or mock_llm.generate.call_args.args[0]
    assert "SCENE IMAGE AVAILABLE" not in system_prompt


def _touch_image(path, content=b"fake-image"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_format_with_user_images_dir(tmp_path):
    """User-provided images are loaded and passed to codegen."""
    fmt = FacelessExplainerFormat()
    fmt._aspect_ratio = "9:16"
    fmt._voice = "af_heart"
    fmt._speed = 1.0
    fmt._parallel = False
    fmt._with_images = True

    # Create user images
    user_dir = tmp_path / "user_images"
    _touch_image(user_dir / "hook.png")
    fmt._images_dir = user_dir

    plan = Plan(
        title="Test", total_duration=5,
        scenes=[Scene(id="hook", duration=5, narration="Hello", visual="A sunset")],
    )

    mock_llm = MagicMock()
    mock_llm.generate.return_value = '```tsx\nexport default function Hook() { return <div />; }\n```'
    mock_tts = MagicMock()
    mock_tts.synthesize.return_value = MagicMock(duration=3.0)

    (tmp_path / "work" / "public" / "audio").mkdir(parents=True)
    (tmp_path / "work" / "src" / "scenes").mkdir(parents=True)

    # No image provider needed — user images are sufficient
    providers = {"llm": mock_llm, "tts": mock_tts}
    assets = fmt.generate_assets(plan, providers, tmp_path / "work")

    assert "hook" in assets["scene_images"]
    # TSX was generated with image context
    system_prompt = mock_llm.generate.call_args.kwargs.get("system") or mock_llm.generate.call_args.args[0]
    assert "hook.png" in system_prompt


def test_format_mixed_user_and_ai_images(tmp_path):
    """User images for some scenes, AI-generated for the rest."""
    fmt = FacelessExplainerFormat()
    fmt._aspect_ratio = "9:16"
    fmt._voice = "af_heart"
    fmt._speed = 1.0
    fmt._parallel = False
    fmt._with_images = True

    user_dir = tmp_path / "user_images"
    _touch_image(user_dir / "hook.png")
    fmt._images_dir = user_dir

    plan = Plan(
        title="Test", total_duration=10,
        scenes=[
            Scene(id="hook", duration=5, narration="Hello", visual="A sunset"),
            Scene(id="main", duration=5, narration="World", visual="A forest"),
        ],
    )

    mock_llm = MagicMock()
    mock_llm.generate.return_value = '```tsx\nexport default function S() { return <div />; }\n```'
    mock_tts = MagicMock()
    mock_tts.synthesize.return_value = MagicMock(duration=3.0)
    mock_image = _make_fake_image_provider()

    (tmp_path / "work" / "public" / "audio").mkdir(parents=True)
    (tmp_path / "work" / "src" / "scenes").mkdir(parents=True)

    providers = {"llm": mock_llm, "tts": mock_tts, "image": mock_image}
    assets = fmt.generate_assets(plan, providers, tmp_path / "work")

    # Both scenes have images
    assert "hook" in assets["scene_images"]
    assert "main" in assets["scene_images"]
    # AI only generated for "main" (hook was user-provided)
    assert mock_image.generate.call_count == 1
