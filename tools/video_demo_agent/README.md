# Video Demo Agent

A minimal internal agent that wraps [DemoDSL 2.4.1](https://github.com/Fran-cois/demodsl) to generate product demo videos from simple JSON requests.

## What This Tool Does

The Video Demo Agent converts a simple JSON request (title, target URL, demo steps) into a valid DemoDSL YAML configuration and optionally executes it to produce a demo video.

**This is an MVP prototype**, not a full video generation platform. It provides:
- Structured request → YAML config generation
- Safe subprocess wrapper for DemoDSL execution
- Local-only, silent mode by default (no API keys required)
- Conservative defaults suitable for internal demos

## Setup

### 1. Python Requirements

**Python 3.11 or 3.12 required** (DemoDSL constraint)

Check your Python version:
```bash
/opt/anaconda3/bin/python3 --version  # Should show 3.12.7
```

### 2. Install Dependencies

The `.venv` directory is already set up with DemoDSL 2.4.1 installed. To recreate or update:

```bash
cd tools/video_demo_agent
/opt/anaconda3/bin/python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Install Playwright Browsers

DemoDSL uses Playwright for browser automation:

```bash
source .venv/bin/activate
playwright install chromium
```

### 4. System Dependencies

**FFmpeg is required** for video encoding. Verify it's installed:

```bash
ffmpeg -version
```

If not installed: `brew install ffmpeg` (macOS)

## Usage

### Generate Config Only (No Video)

This mode generates the DemoDSL YAML config but does **not** run video generation:

```bash
cd tools/video_demo_agent
source .venv/bin/activate
python agent.py examples/ai_crew_demo_request.json --generate-only
```

**Output**:
- `output/configs/demo_YYYYMMDD_HHMMSS.yaml` - Generated DemoDSL config

### Generate Config + Run Video

This mode generates the YAML **and** executes DemoDSL to produce a video:

```bash
python agent.py examples/ai_crew_demo_request.json --run
```

**Output**:
- `output/configs/demo_YYYYMMDD_HHMMSS.yaml` - Generated config
- `output/videos/demo_YYYYMMDD_HHMMSS.mp4` - Generated video (if successful)

### Validate Generated Config

You can validate the generated YAML without running:

```bash
source .venv/bin/activate
demodsl validate output/configs/demo_20260618_142630.yaml
```

## Request Format

Create a JSON file with this structure:

```json
{
  "title": "My Product Demo",
  "target_url": "https://app.example.com",
  "demo_steps": [
    {
      "action": "navigate",
      "url": "https://app.example.com",
      "narration": "Welcome to our application",
      "wait": 2.0
    },
    {
      "action": "click",
      "selector": "#signup-button",
      "narration": "Click the signup button",
      "wait": 1.0
    }
  ],
  "viewport": {
    "width": 1280,
    "height": 720
  },
  "output_format": "mp4",
  "voice_mode": "silent"
}
```

### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `title` | string | ✅ | - | Demo video title |
| `target_url` | string | ✅ | - | Base URL for the demo |
| `demo_steps` | array | ✅ | - | List of demo actions (see below) |
| `viewport` | object | ❌ | `{width: 1280, height: 720}` | Browser viewport size |
| `output_format` | string | ❌ | `"mp4"` | Video format (`mp4`, `webm`, `gif`) |
| `voice_mode` | string | ❌ | `"silent"` | TTS mode (`silent`, `gtts`) |
| `output_dir` | string | ❌ | `"output"` | Output directory path |

### Demo Step Actions

Each step in `demo_steps` requires an `action` field:

| Action | Required Fields | Optional Fields | Description |
|--------|----------------|-----------------|-------------|
| `navigate` | `url` | `narration`, `wait` | Navigate to URL |
| `click` | `selector` | `narration`, `wait` | Click element |
| `type` | `selector`, `value` | `narration`, `wait` | Type text into input |
| `scroll` | `direction` (`up`/`down`) | `pixels`, `narration`, `wait` | Scroll page |
| `wait_for` | `selector` | `timeout`, `narration` | Wait for element |
| `screenshot` | - | `filename`, `narration`, `wait` | Capture screenshot |

**Common optional fields**:
- `narration` (string): Voice-over text for this step
- `wait` (float): Seconds to wait after action (default: 1.0)
- `selector` (string): CSS selector for element targeting

## Voice Modes

### Silent Mode (Default)

No voice narration. Fastest and most reliable for prototyping:

```json
{
  "voice_mode": "silent"
}
```

### Google TTS Mode

Requires `gtts` Python package (not included by default):

```bash
pip install gtts
```

Then use in request:

```json
{
  "voice_mode": "gtts"
}
```

**Note**: `gtts` requires internet connection and uses Google Translate TTS service.

## Expected Outputs

### Generate-Only Mode

```
output/
  configs/
    demo_20260618_142630.yaml  ← Generated DemoDSL YAML
```

### Run Mode

```
output/
  configs/
    demo_20260618_142630.yaml  ← Generated DemoDSL YAML
  videos/
    demo_20260618_142630.mp4   ← Generated demo video
```

## Known Limitations

1. **MVP Prototype**: This is a minimal viable product, not a production-ready platform
2. **No API Keys**: Silent mode only; paid TTS providers (ElevenLabs, OpenAI) not configured
3. **Local Execution Only**: No cloud deployment, no distributed rendering
4. **Basic Error Handling**: Subprocess errors are captured but not exhaustively handled
5. **No Retry Logic**: Failed steps do not automatically retry
6. **Target URLs**: Must be publicly accessible (or locally running) URLs
7. **Browser Support**: Chrome/Chromium only (Playwright limitation in current setup)
8. **Video Size**: Generated videos can be large; not optimized for web delivery
9. **No Authentication**: Cannot demo sites requiring login (without manual cookie injection)
10. **DemoDSL Constraints**: Inherits all DemoDSL 2.4.1 limitations (see [DemoDSL docs](https://fran-cois.github.io/demodsl))

## Do Not Commit Generated Artifacts

**Important**: The following files should **never** be committed:

❌ `output/configs/*.yaml` (generated configs)
❌ `output/videos/*.mp4` (generated videos)
❌ `.venv/` (virtual environment)
❌ `*.log` (logs)
❌ `__pycache__/` (Python cache)

These are already excluded via `.gitignore` at the repository root.

## Architecture

```
tools/video_demo_agent/
├── video_demo_agent/
│   ├── __init__.py           # Package exports
│   ├── schemas.py            # Pydantic models (VideoDemoRequest, VideoDemoResult)
│   ├── config_generator.py   # Request → DemoDSL YAML converter
│   ├── runner.py             # Subprocess wrapper for demodsl CLI
│   └── agent.py              # Main orchestrator + CLI
├── examples/
│   └── ai_crew_demo_request.json  # Example request
├── output/                   # Generated artifacts (gitignored)
│   ├── configs/
│   └── videos/
├── requirements.txt
└── README.md
```

## Example: AI Crew Demo

See `examples/ai_crew_demo_request.json` for a complete working example that:
1. Navigates to AI Crew organisation page
2. Explains the crew structure
3. Clicks on Hermes, Darwin, and Lili crew members
4. Shows modal behavior
5. Returns to dashboard

Run it:
```bash
python agent.py examples/ai_crew_demo_request.json --generate-only
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'demodsl'"

Activate the virtual environment:
```bash
source .venv/bin/activate
```

### "No module named 'gtts'" (when using voice)

Install gtts:
```bash
pip install gtts
```

Or use silent mode instead:
```json
{"voice_mode": "silent"}
```

### "playwright: command not found"

Install Playwright browsers:
```bash
source .venv/bin/activate
playwright install chromium
```

### "ffmpeg: command not found"

Install FFmpeg:
```bash
brew install ffmpeg  # macOS
```

### Video generation fails silently

Check logs in the console output. Common causes:
- Target URL is not accessible
- CSS selectors don't match page elements
- Browser timeout (increase `wait` values)
- FFmpeg encoding error (check video codec support)

## Development

To extend the agent:

1. **Add new step actions**: Update `schemas.py` DemoStep model
2. **Custom YAML templates**: Modify `config_generator.py`
3. **Enhanced error handling**: Update `runner.py`
4. **New CLI flags**: Add to `agent.py` argument parser

## License

Same as parent repository (ad-agent).
