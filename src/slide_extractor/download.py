import re
import subprocess
from pathlib import Path


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
        print(f"Video already downloaded: {output_path}")
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

    print(f"Downloading {url} ...")
    subprocess.run(cmd, check=True)
    print(f"Saved to {output_path}")
    return output_path
