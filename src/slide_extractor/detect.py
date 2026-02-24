import shutil
from pathlib import Path

import imagehash
from PIL import Image


def _phash(path: Path) -> imagehash.ImageHash:
    return imagehash.phash(Image.open(path))


def detect_transitions(
    frames_dir: Path,
    output_dir: Path | None = None,
    threshold: int = 10,
) -> list[Path]:
    """Detect scene transitions in a sequence of frames using perceptual hashing.

    For each group of consecutive similar frames, keeps the LAST frame before
    the next big transition. This naturally captures the final state of
    progressive slide builds (e.g., bullet points appearing one by one).

    Returns a sorted list of candidate frame paths copied to output_dir.
    """
    if output_dir is None:
        output_dir = frames_dir.parent / "candidates"

    output_dir.mkdir(parents=True, exist_ok=True)

    existing = sorted(output_dir.glob("frame_*.jpg"))
    if existing:
        print(f"Candidates already detected: {len(existing)} in {output_dir}")
        return existing

    frames = sorted(frames_dir.glob("frame_*.jpg"))
    if not frames:
        print("No frames found.")
        return []

    print(f"Computing perceptual hashes for {len(frames)} frames ...")
    hashes = [_phash(f) for f in frames]

    # Walk through frames. When we detect a big jump between frame[i] and
    # frame[i+1], we emit frame[i] as the "last frame of the previous scene".
    candidates: list[Path] = []

    for i in range(len(frames) - 1):
        dist = hashes[i] - hashes[i + 1]
        if dist > threshold:
            # Big change: keep frame[i] (last of the old scene)
            candidates.append(frames[i])

    # Always keep the very last frame (final slide)
    candidates.append(frames[-1])

    # Copy candidates to output dir
    result: list[Path] = []
    for src in candidates:
        dst = output_dir / src.name
        shutil.copy2(src, dst)
        result.append(dst)

    print(f"Detected {len(result)} transitions -> {output_dir}")
    return result
