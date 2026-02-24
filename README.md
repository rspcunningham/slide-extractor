# slide-extractor

Extract presentation slides from lecture videos into annotatable PDFs.

Takes a YouTube lecture video and produces a PDF with one page per unique slide — essentially reverse-engineering the slide deck from the recording.

## How it works

1. **Download** the video via yt-dlp
2. **Extract frames** at 1 fps using ffmpeg
3. **Detect transitions** by comparing perceptual hashes of consecutive frames
4. **Classify** each candidate frame as slide vs. non-slide using Claude's vision API (filters out professor/room shots)
5. **Deduplicate** similar slides, keeping the sharpest version of each
6. **Compile** the final set into a single PDF

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [ffmpeg](https://ffmpeg.org/) installed and on PATH
- An [Anthropic API key](https://console.anthropic.com/)

## Setup

```bash
git clone <repo> && cd lectures
uv sync
```

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

Run the full pipeline:

```bash
uv run slide-extractor run "https://www.youtube.com/watch?v=VIDEO_ID"
```

Output lands in `output/<video-id>/slides.pdf`.

### Options

```
--fps 1.0              Frame extraction rate (default: 1)
--detect-threshold 10  Sensitivity for scene change detection (lower = more candidates)
--dedup-threshold 5    Similarity threshold for deduplication (lower = stricter)
```

### Individual steps

Each stage can be run independently for debugging or re-processing:

```bash
uv run slide-extractor download <youtube-url>
uv run slide-extractor extract <video-path>
uv run slide-extractor detect <frames-dir>
uv run slide-extractor classify <candidates-dir>
uv run slide-extractor dedup <slides-dir>
uv run slide-extractor compile <slides-dir>
```

Each step caches its output. To re-run a step, delete its output directory first.

## Cost

This tool consumes tokens from Anthropic. The API cost is roughly $0.50 per hour of video.
