import subprocess
from pathlib import Path

from slide_extractor.console import console


def extract_frames(video_path: Path, output_dir: Path | None = None, fps: float = 1.0) -> list[Path]:
    """Extract frames from a video at the given FPS using ffmpeg.

    Returns a sorted list of extracted frame paths.
    """
    if output_dir is None:
        output_dir = video_path.parent / "frames"

    output_dir.mkdir(parents=True, exist_ok=True)

    pattern = str(output_dir / "frame_%05d.jpg")

    # Check if frames already exist
    existing = sorted(output_dir.glob("frame_*.jpg"))
    if existing:
        console.print(f"Frames already extracted: {len(existing)} frames in {output_dir}")
        return existing

    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vf", f"fps={fps}",
        "-q:v", "2",  # high quality JPEG
        pattern,
        "-hide_banner",
        "-loglevel", "warning",
    ]

    with console.status(f"Extracting frames at {fps} fps ..."):
        subprocess.run(cmd, check=True)

    frames = sorted(output_dir.glob("frame_*.jpg"))
    console.print(f"Extracted [bold]{len(frames)}[/bold] frames to {output_dir}")
    return frames
