"""Storyboard generation for illustrated (still image) format."""

from __future__ import annotations

from showrunner.plan import Plan
from showrunner.styles.resolver import ResolvedStyle


STORYBOARD_SYSTEM_PROMPT = """You are a creative director for illustrated visual content. You produce storyboards where each scene becomes a single still image (or panel in a multi-panel layout).

OUTPUT FORMAT: Return a JSON object:
{
  "title": "Project Title",
  "totalDuration": 0,
  "scenes": [
    {
      "id": "<snake_case_id>",
      "duration": 0,
      "narration": "<caption or narration text — 1-2 sentences>",
      "visual": "<image generation prompt — describe the image>",
      "transition": "none"
    }
  ]
}

IMAGE PROMPT RULES (these are prompts for an AI image generation model):
- Describe a single compelling image per scene
- Include: subject, composition, setting, lighting, color palette, mood
- Photography terms: wide shot, close-up, medium shot, bird's-eye view, eye-level, low angle
- Lighting: golden hour, dramatic side-light, soft diffused, neon, natural, chiaroscuro
- Style terms: photorealistic, illustration, watercolor, oil painting, digital art, line art
- Composition: rule of thirds, centered, leading lines, framing, negative space
- Keep each prompt to 2-4 sentences — specific and visually rich
- Do NOT mention text overlays, UI elements, or animations
- Do NOT reference code or programming concepts

STORYBOARD RULES:
- 4-12 scenes depending on topic complexity
- Duration is set to 0 (still images, not video)
- Each scene should tell a distinct visual beat of the story
- Narration should be concise captions (1-2 sentences)
- First scene: hook — the most visually striking image
- Last scene: memorable conclusion or call to action
- Vary composition and shot types across scenes for visual rhythm
- Consider how images flow together as a sequence

CONTENT APPROACH:
- Think like a book illustrator or storyboard artist
- Each image should stand alone as a compelling visual
- Narration complements the image, doesn't describe it
- Build a visual arc: establish → develop → climax → resolve"""


STORYBOARD_USER_TEMPLATE = """Create a storyboard for an illustrated series about:

TOPIC: {topic}

STYLE CONTEXT:
{style_context}

Remember: the "visual" field is a prompt for an AI image generation model. Describe images, not video or animation.

Return ONLY the JSON storyboard."""


def generate_plan(
    topic: str,
    *,
    style: ResolvedStyle,
    llm: object,
    config: dict | None = None,
) -> Plan:
    """Generate an illustrated storyboard optimized for image generation."""
    style_context = style.to_prompt_context()
    prompt = STORYBOARD_USER_TEMPLATE.format(topic=topic, style_context=style_context)

    storyboard_dict = llm.generate_json(
        system=STORYBOARD_SYSTEM_PROMPT,
        prompt=prompt,
        max_tokens=4096,
    )

    return Plan.from_dict(storyboard_dict)
