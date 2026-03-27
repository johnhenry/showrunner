# CLAUDE.md — Showrunner

AI-powered video generation framework. `pip install showrunner`.

## Architecture

```
src/showrunner/
├── __init__.py          # Public API: Pipeline, Plan, Format, Feedback
├── pipeline.py          # Orchestrator: plan → assets → compose → render
├── plan.py              # Plan + Scene dataclasses (storyboard model)
├── config.py            # .showrunner.yaml loading + CLI override merging
├── feedback.py          # Feedback dataclass for plan/asset revision
├── images.py            # User-provided image matching + loading
├── formats/
│   ├── base.py          # Format ABC (plan, generate_assets, compose, revise)
│   ├── registry.py      # Entry point discovery via importlib.metadata
│   ├── faceless_explainer/  # Remotion + React animated explainers
│   │   ├── planner.py       # LLM → storyboard JSON
│   │   ├── assets.py        # LLM → TSX scene code + TTS narration + optional images
│   │   └── composer.py      # Generates Root.tsx for Remotion timeline
│   ├── ai_video/            # AI video clips + FFmpeg
│   │   ├── planner.py       # LLM → storyboard with video gen prompts
│   │   └── assets.py        # VideoProvider clips + TTS narration
│   └── illustrated/         # Still images → PDF/PNG
│       ├── planner.py       # LLM → storyboard with image gen prompts
│       ├── assets.py        # ImageProvider → generated images
│       ├── composer.py      # Single-image or multi-panel page layouts
│       └── text_overlay.py  # Caption overlay via PIL
├── providers/
│   ├── llm/             # LLMProvider ABC → anthropic, openai
│   ├── tts/             # TTSProvider ABC → kokoro, elevenlabs
│   ├── image/           # ImageProvider ABC → openai, gemini, ollama
│   ├── video/           # VideoProvider ABC → gemini, minimax
│   └── render/          # RenderProvider ABC → remotion, ffmpeg, pillow
│       └── template/    # Embedded Remotion TypeScript project
├── styles/
│   ├── resolver.py      # ResolvedStyle + preset loading
│   └── presets/         # 7 JSON presets (3b1b-dark, bold-neon, etc.)
└── cli/
    └── main.py          # Click CLI (create, formats, styles, voices, init)
```

## Pipeline Flow

```
Topic + Style
  → format.plan()           — LLM generates storyboard (Plan with Scenes)
  → format.generate_assets() — TTS audio + scene code/video clips/images
  → format.compose()        — Build Remotion Root.tsx, FFmpeg concat, or page layout
  → render.render()         — Remotion CLI, FFmpeg, or Pillow → final output
```

## Three Built-in Formats

| Format | Render | Visual Field | Use Case |
|--------|--------|-------------|----------|
| `faceless-explainer` | Remotion (React/TSX) | Animation code description | Educational, explainer |
| `ai-video` | FFmpeg (clip concat) | Video generation prompt | Cinematic, storytelling |
| `illustrated` | Pillow (PDF/PNG) | Image generation prompt | Storyboards, graphic content |

All formats use the same `Plan`/`Scene` model — `Scene.visual` is interpreted differently by each format's planner prompt.

## Image Support

Images can enhance any format via two mechanisms:

- **`--with-images`**: AI-generates a background image per scene via ImageProvider. For `faceless-explainer`, images are composited under Remotion animations. For `illustrated`, this is the default behavior.
- **`--images ./dir/`**: Uses existing user-provided images. Files match to scenes by filename (e.g. `hook.png` → scene `hook`) or by sort order. Can combine with `--with-images` to AI-generate for unmatched scenes only.

The `Scene.visual` field controls how images are used in each scene (full-bleed background, inset, Ken Burns, etc.).

## Provider System

Providers are swappable via config. Each has an ABC in `providers/<type>/base.py`:

- **LLM**: `generate(system, prompt)`, `generate_json(system, prompt)` — anthropic (default), openai
- **TTS**: `synthesize(text, output_path, voice, speed)` → `AudioFile` — kokoro (default, local), elevenlabs
- **Image**: `generate(prompt, size, aspect_ratio, output_path)` → `Path` — openai (gpt-image-1), gemini (Imagen 3), ollama (Z-Image Turbo/FLUX.2)
- **Video**: `generate(prompt, duration, aspect_ratio, output_path)`, `poll(id)` — gemini (Veo 3.1), minimax
- **Render**: `setup(work_dir)`, `render(work_dir, output_path)`, `preview(work_dir)` — remotion (default), ffmpeg, pillow

Pipeline instantiates providers in `_create_providers()` via lazy imports based on config.

## Format Plugin System

Formats register via Python entry points (`showrunner.formats` group in pyproject.toml). The registry discovers them at runtime. External packages can add formats by declaring the entry point.

A Format subclass must implement: `plan()`, `generate_assets()`, `compose()`, `revise()`.

## Data Models

- **`Plan`**: title, total_duration, scenes list. Serializes to camelCase JSON (Remotion compat). `from_dict()` accepts both camelCase and snake_case.
- **`Scene`**: id, duration, narration, visual, transition
- **`Feedback`**: level (plan/asset/composition), scene_id, text, edits dict
- **`ResolvedStyle`**: colors, typography, animation dicts + `to_prompt_context()` for LLM prompts
- **`Config`**: default_format, default_style, providers dict, provider_config dict. Loaded from `.showrunner.yaml`.

## Development

```bash
pip install -e ".[dev]"       # Install with dev deps
pip install -e ".[pillow]"    # For illustrated format / Pillow render
python -m pytest tests/ -v    # Run tests
ruff check src/ tests/        # Lint
```

Tests use `unittest.mock` extensively — providers are mocked, no real API calls in tests.

## Git Conventions

- Commit messages: `feat:`, `fix:`, `test:`, `docs:`, `chore:` prefixes
- No Co-authored-by lines
- `.showrunner.yaml` is gitignored (user-specific config)

## Key Files for Common Tasks

| Task | Files |
|------|-------|
| Add a new video provider | `providers/video/base.py` (interface), new file in `providers/video/`, wire in `pipeline.py:_create_providers()`, add optional dep in `pyproject.toml` |
| Add a new image provider | `providers/image/base.py` (interface), new file in `providers/image/`, wire in `pipeline.py:_create_providers()` |
| Add a new format | New dir in `formats/`, implement Format ABC, add entry point in `pyproject.toml` |
| Add a new TTS provider | `providers/tts/base.py` (interface), new file, wire in pipeline |
| Add a new render provider | `providers/render/base.py` (interface), new file, wire in pipeline |
| Add a style preset | New JSON in `styles/presets/`, follows existing schema (colors, typography, animation) |
| Modify the CLI | `cli/main.py` — Click commands |
| Change the storyboard format | `plan.py` — Plan/Scene dataclasses |
| Change image matching logic | `images.py` — `load_user_images()` and `_find_scene_match()` |
