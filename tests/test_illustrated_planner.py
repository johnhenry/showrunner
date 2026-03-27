# tests/test_illustrated_planner.py
from unittest.mock import MagicMock

from showrunner.formats.illustrated.planner import generate_plan, STORYBOARD_SYSTEM_PROMPT
from showrunner.plan import Plan
from showrunner.styles.resolver import resolve_style


def test_generate_plan_returns_plan():
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "title": "Jazz History",
        "totalDuration": 0,
        "scenes": [
            {"id": "origins", "duration": 0, "narration": "Jazz began in New Orleans", "visual": "A smoky jazz club"},
            {"id": "evolution", "duration": 0, "narration": "It evolved", "visual": "Musicians on stage"},
        ],
    }
    style = resolve_style("dramatic-story")
    plan = generate_plan("History of Jazz", style=style, llm=mock_llm)

    assert isinstance(plan, Plan)
    assert plan.title == "Jazz History"
    assert len(plan.scenes) == 2


def test_generate_plan_uses_image_oriented_prompt():
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "title": "T", "totalDuration": 0, "scenes": [],
    }
    style = resolve_style("3b1b-dark")
    generate_plan("test", style=style, llm=mock_llm)

    call_args = mock_llm.generate_json.call_args
    system_prompt = call_args.kwargs.get("system") or call_args.args[0]
    assert "image generation model" in system_prompt.lower()
    assert "video" not in system_prompt.lower() or "not video" in system_prompt.lower()


def test_system_prompt_has_image_instructions():
    assert "image generation" in STORYBOARD_SYSTEM_PROMPT.lower()
    assert "still image" in STORYBOARD_SYSTEM_PROMPT.lower() or "single compelling image" in STORYBOARD_SYSTEM_PROMPT.lower()
    assert "Do NOT mention text overlays" in STORYBOARD_SYSTEM_PROMPT
