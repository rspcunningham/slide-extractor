import base64
from pathlib import Path

from slide_extractor.env import load_dotenv

load_dotenv()

import anthropic

from slide_extractor.console import console
from slide_extractor.download import get_video_metadata


def _encode_image(path: Path) -> str:
    return base64.standard_b64encode(path.read_bytes()).decode()


def _format_duration(seconds: int) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def summarize_lecture(
    url: str,
    slides_dir: Path,
    output_path: Path | None = None,
) -> Path:
    """Generate a markdown summary of a lecture using video metadata and slides.

    Fetches metadata via yt-dlp, picks representative slides, and uses Claude
    to generate a concise summary. Writes summary.md to the output path.

    Returns the path to the generated summary file.
    """
    if output_path is None:
        output_path = slides_dir.parent / "summary.md"

    if output_path.exists():
        console.print(f"Summary already exists: {output_path}")
        return output_path

    # Fetch video metadata
    with console.status("Fetching video metadata ..."):
        meta = get_video_metadata(url)

    title = meta.get("title", "Unknown")
    description = meta.get("description", "")
    duration = meta.get("duration", 0)
    uploader = meta.get("uploader", "Unknown")
    upload_date = meta.get("upload_date", "")

    # Format upload date (YYYYMMDD -> YYYY-MM-DD)
    if len(upload_date) == 8:
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

    # Pick ~5 evenly-spaced slides as representative images
    slides = sorted(slides_dir.glob("frame_*.jpg"))
    if not slides:
        console.print("[yellow]No slides found for summary generation[/yellow]")
        # Write a minimal summary without slide analysis
        md = f"# {title}\n\n"
        md += f"- **Video**: [{url}]({url})\n"
        md += f"- **Duration**: {_format_duration(duration)}\n"
        md += f"- **Uploader**: {uploader}\n"
        md += f"- **Date**: {upload_date}\n"
        output_path.write_text(md)
        return output_path

    n_samples = min(5, len(slides))
    step = max(1, len(slides) // n_samples)
    sample_slides = [slides[i * step] for i in range(n_samples)]

    # Build prompt with representative slides
    content: list[dict] = []
    for i, slide_path in enumerate(sample_slides):
        content.append({"type": "text", "text": f"Slide {i + 1}:"})
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": _encode_image(slide_path),
            },
        })

    content.append({
        "type": "text",
        "text": (
            f"This is a lecture titled \"{title}\" by {uploader}. "
            f"Above are {n_samples} representative slides from the presentation. "
            "Write a concise summary of the lecture topics in 3-5 bullet points. "
            "Focus on the key concepts and themes covered. "
            "Reply with just the bullet points, no preamble."
        ),
    })

    client = anthropic.Anthropic()

    with console.status("Generating lecture summary ..."):
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": content}],
        )

    summary_text = resp.content[0].text.strip()

    # Write summary.md
    md = f"# {title}\n\n"
    md += f"- **Video**: [{url}]({url})\n"
    md += f"- **Duration**: {_format_duration(duration)}\n"
    md += f"- **Uploader**: {uploader}\n"
    md += f"- **Date**: {upload_date}\n\n"
    md += f"## Summary\n\n{summary_text}\n"

    output_path.write_text(md)
    console.print(f"Summary saved: [bold]{output_path}[/bold]")
    return output_path
