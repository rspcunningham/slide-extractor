from pathlib import Path

from slide_extractor.console import console


def generate_index(
    base_dir: Path,
    playlist_title: str,
    videos: list[dict],
) -> Path:
    """Generate a top-level index.md for a playlist of processed lectures.

    Args:
        base_dir: Playlist output directory (e.g., output/<playlist-id>/).
        playlist_title: Title of the playlist/course.
        videos: List of dicts with keys: video_id, title, url.
            Each video's output is expected at base_dir/<video_id>/.

    Returns the path to the generated index file.
    """
    index_path = base_dir / "index.md"

    md = f"# {playlist_title}\n\n"

    for i, video in enumerate(videos, 1):
        video_id = video["video_id"]
        title = video["title"]
        url = video["url"]
        video_dir = base_dir / video_id

        md += f"## {i}. {title}\n\n"
        md += f"[Video]({url})"

        # Link to PDF if it exists
        pdf_path = video_dir / "slides.pdf"
        if pdf_path.exists():
            rel_pdf = pdf_path.relative_to(base_dir)
            md += f" | [Slides]({rel_pdf})"

        # Link to summary if it exists
        summary_path = video_dir / "summary.md"
        if summary_path.exists():
            rel_summary = summary_path.relative_to(base_dir)
            md += f" | [Summary]({rel_summary})"

        md += "\n\n"

        # Include summary bullet points inline if available
        if summary_path.exists():
            summary_text = summary_path.read_text()
            # Extract bullet points (lines starting with - or *)
            bullets = [
                line for line in summary_text.splitlines()
                if line.strip().startswith(("- ", "* ")) and not line.strip().startswith("- **")
            ]
            if bullets:
                for bullet in bullets:
                    md += f"{bullet}\n"
                md += "\n"

    index_path.write_text(md)
    console.print(f"Course index saved: [bold]{index_path}[/bold]")
    return index_path
