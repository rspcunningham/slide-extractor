import shutil
from pathlib import Path

import imagehash
import numpy as np
from PIL import Image, ImageFilter
from rich.progress import track

from slide_extractor.console import console


def _phash(path: Path) -> imagehash.ImageHash:
    return imagehash.phash(Image.open(path))


def _sharpness(path: Path) -> float:
    """Estimate image sharpness using variance of a Laplacian-like filter."""
    img = Image.open(path).convert("L")
    # Pillow doesn't have a Laplacian, but FIND_EDGES is close enough
    edges = img.filter(ImageFilter.FIND_EDGES)
    return float(np.array(edges).var())


def deduplicate(
    slides_dir: Path,
    output_dir: Path | None = None,
    threshold: int = 5,
) -> list[Path]:
    """Remove duplicate slides by grouping perceptually similar images.

    From each group of similar slides, keeps the sharpest version.
    Preserves chronological order based on frame number.

    Returns list of deduplicated slide paths (in output_dir).
    """
    if output_dir is None:
        output_dir = slides_dir.parent / "slides_deduped"

    output_dir.mkdir(parents=True, exist_ok=True)

    existing = sorted(output_dir.glob("frame_*.jpg"))
    if existing:
        console.print(f"Already deduplicated: {len(existing)} in {output_dir}")
        return existing

    slides = sorted(slides_dir.glob("frame_*.jpg"))
    if not slides:
        console.print("No slides to deduplicate.")
        return []

    hashes = [_phash(s) for s in track(slides, description="Hashing slides", console=console)]

    # Group slides by similarity using union-find
    parent = list(range(len(slides)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(len(slides)):
        for j in range(i + 1, len(slides)):
            if hashes[i] - hashes[j] <= threshold:
                union(i, j)

    # Collect groups
    groups: dict[int, list[int]] = {}
    for i in range(len(slides)):
        root = find(i)
        groups.setdefault(root, []).append(i)

    # From each group, pick the sharpest slide
    kept: list[Path] = []
    for indices in groups.values():
        best_idx = max(indices, key=lambda i: _sharpness(slides[i]))
        kept.append(slides[best_idx])

    # Sort by original frame number to preserve chronological order
    kept.sort(key=lambda p: p.name)

    # Copy to output
    result: list[Path] = []
    for src in kept:
        dst = output_dir / src.name
        shutil.copy2(src, dst)
        result.append(dst)

    console.print(f"Deduplicated {len(slides)} -> [bold]{len(result)}[/bold] unique slides -> {output_dir}")
    return result
