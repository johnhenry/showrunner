# Showrunner

AI-powered video generation framework. Create animated social media videos from text topics with pluggable formats and providers.

https://github.com/user-attachments/assets/977e15ef-d08e-45a9-800b-60943c16dba9


## Quick Start

```bash
pip install showrunner
```

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Remotion video rendering)
- An Anthropic API key (`ANTHROPIC_API_KEY` environment variable)

### Generate a video

```bash
showrunner create "Why do cats purr?"
```

### Customize

```bash
showrunner create "The history of the internet" \
  --style bold-neon \
  --aspect-ratio 16:9 \
  --captions \
  --watermark "@mychannel"
```

### With AI-generated images

Generate background images for each scene using an image provider:

```bash
showrunner create "The solar system" --with-images
```

### With your own images

Point to a directory of images to use as scene backgrounds:

```bash
showrunner create "Product tour" --images ./assets/
```

Images match to scenes by filename (e.g. `hook.png` → scene `hook`) or by sort order. Combine both flags to AI-generate images only for scenes without a matching user image:

```bash
showrunner create "Product tour" --images ./assets/ --with-images
```

### Generate still images (PDF/PNG)

```bash
# Single image per scene → PDF
showrunner create "History of jazz" --format illustrated

# Multi-panel pages with captions
showrunner create "Ocean life" --format illustrated --layout panels --text-overlay

# PNG sequence output
showrunner create "Solar system" --format illustrated --image-output png
```

### Available commands

```bash
showrunner create "topic"     # Generate a video
showrunner styles             # List style presets
showrunner formats            # List output formats
showrunner voices             # List TTS voices
showrunner providers          # Show configured providers
showrunner init               # Create config file
```

## Configuration

Create `.showrunner.yaml` in your project:

```yaml
default_format: faceless-explainer
default_style: 3b1b-dark

providers:
  llm: anthropic
  tts: kokoro
  render: remotion
  image: openai          # for --with-images or illustrated format

anthropic:
  model: claude-sonnet-4-5-20250929

openai:
  image_model: gpt-image-1   # or dall-e-3
  image_quality: auto

kokoro:
  voice: af_heart
  speed: 1.0

output:
  aspect_ratio: "9:16"
  captions: false
```

CLI arguments override config file values.

## Style Presets

| Preset | Description |
|--------|-------------|
| `3b1b-dark` | Navy/blue/gold, math education |
| `bold-neon` | Black/cyan/pink, gaming/tech |
| `clean-corporate` | White/blue, professional |
| `dramatic-story` | Black/gold/red, cinematic |
| `pastel-gradient` | Lavender/purple, wellness |
| `tech-startup` | Dark/indigo/pink, SaaS |
| `warm-minimal` | Cream/brown, lifestyle |

Custom style overrides:

```bash
showrunner create "topic" --style 3b1b-dark --override "use green accents, faster pacing"
```

## As a Library

```python
from showrunner import Pipeline

pipeline = Pipeline(format_name="faceless-explainer")
video_path = pipeline.run(
    "Why do cats purr?",
    style="3b1b-dark",
    captions=True,
)
```

### Dry run (plan only, no render)

```python
plan = pipeline.run("topic", dry_run=True)
print(plan.to_json())
```

## Creating Format Plugins

Formats are Python packages that register via entry points:

```python
from showrunner import Format, Plan, Feedback
from pathlib import Path

class MyFormat(Format):
    name = "my-format"
    description = "My custom video format"
    required_providers = ["llm", "tts", "render"]

    def plan(self, topic, style, config, llm):
        ...

    def generate_assets(self, plan, providers, work_dir):
        ...

    def compose(self, plan, assets, work_dir, **kwargs):
        ...

    def revise(self, plan, feedback, llm):
        ...
```

Register in your package's `pyproject.toml`:

```toml
[project.entry-points."showrunner.formats"]
my-format = "my_package:MyFormat"
```

Then it's automatically available:

```bash
showrunner create "topic" --format my-format
```

## Providers

### LLM
- **anthropic** (default) — Claude via Anthropic API
- **openai** — GPT via OpenAI API

### TTS
- **kokoro** (default) — Free local TTS (82M params, Apache 2.0)
- **elevenlabs** — Cloud TTS (paid API)

### Image
- **openai** — gpt-image-1 / DALL-E 3
- **gemini** — Google Imagen 3
- **ollama** — Local image generation (Z-Image Turbo, FLUX.2; macOS only currently)

### Video
- **gemini** — Google Veo 3.1
- **minimax** — Minimax video generation API

### Render
- **remotion** (default) — React-based programmatic video
- **ffmpeg** — Video clip concatenation with audio mixing
- **pillow** — Still image assembly to PDF/PNG (used by `illustrated` format)

## License

MIT
