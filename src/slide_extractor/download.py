import json
import re
import subprocess
from pathlib import Path

from slide_extractor.console import console


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from: {url}")


def extract_playlist_id(url: str) -> str | None:
    """Extract playlist ID from a YouTube URL, or None if not a playlist."""
    match = re.search(r"[?&]list=([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None


def is_playlist(url: str) -> bool:
    """Check if a YouTube URL points to a playlist."""
    return extract_playlist_id(url) is not None


def enumerate_playlist(url: str) -> list[dict]:
    """List all videos in a playlist without downloading them.

    Returns a list of dicts with keys: id, url, title.
    """
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        url,
    ]

    console.print(f"Fetching playlist info ...")
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    videos = []
    for line in result.stdout.strip().splitlines():
        data = json.loads(line)
        video_id = data.get("id", "")
        videos.append({
            "id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": data.get("title", video_id),
        })
    console.print(f"Found [bold]{len(videos)}[/bold] videos in playlist")
    return videos


def get_video_metadata(url: str) -> dict:
    """Fetch video metadata (title, description, duration, etc.) without downloading."""
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-playlist",
        "--no-warnings",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def download(url: str, output_dir: Path | None = None) -> Path:
    """Download a YouTube video using yt-dlp.

    Returns the path to the downloaded video file.
    """
    video_id = extract_video_id(url)

    if output_dir is None:
        output_dir = Path("output") / video_id

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "video.mp4"

    if output_path.exists():
        console.print(f"Video already downloaded: {output_path}")
        return output_path

    cmd = [
        "yt-dlp",
        # Best video up to 1080p, no audio needed
        "-f", "bestvideo[height<=1080][ext=mp4]/bestvideo[height<=1080]/best[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", str(output_path),
        "--no-playlist",
        url,
    ]

    with console.status(f"Downloading [bold]{url}[/bold] ..."):
        subprocess.run(cmd, check=True)
    console.print(f"Saved to {output_path}")
    return output_path
