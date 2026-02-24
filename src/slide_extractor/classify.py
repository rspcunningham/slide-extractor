import base64
import json
import shutil
from pathlib import Path

from slide_extractor.env import load_dotenv

load_dotenv()

import anthropic
from rich.progress import track

from slide_extractor.console import console

SYSTEM_PROMPT = (
    "You classify frames extracted from lecture videos. Your job is to identify "
    "frames where a presentation slide fills the ENTIRE frame (full-screen slide "
    "capture). Reject any frame where you can see the lecture hall, the professor, "
    "a podium, a whiteboard, walls, or any physical environment — even if a slide "
    "is partially visible in the background. Only accept frames that are purely "
    "the slide content with no surrounding room visible."
)

# How many images to send per API request
BATCH_SIZE = 10


def _encode_image(path: Path) -> str:
    return base64.standard_b64encode(path.read_bytes()).decode()


def _classify_batch(client: anthropic.Anthropic, paths: list[Path]) -> list[bool]:
    """Classify a batch of images. Returns a list of bools (True = slide)."""
    content: list[dict] = []
    for i, p in enumerate(paths):
        content.append({
            "type": "text",
            "text": f"Image {i + 1}:",
        })
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": _encode_image(p),
            },
        })

    content.append({
        "type": "text",
        "text": (
            f"For each of the {len(paths)} images above: is the slide filling the "
            "ENTIRE frame (full-screen capture), or can you see any part of the "
            "lecture hall, professor, podium, or room? Reply with SLIDE or NOT_SLIDE "
            "for each image, one per line. No other text."
        ),
    })

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    lines = resp.content[0].text.strip().splitlines()
    results: list[bool] = []
    for line in lines:
        results.append("SLIDE" in line.upper() and "NOT_SLIDE" not in line.upper())

    # Pad or truncate if model returned unexpected count
    while len(results) < len(paths):
        results.append(False)
    return results[: len(paths)]


def _load_manifest(manifest_path: Path) -> dict[str, str]:
    """Load the classification manifest from disk."""
    if manifest_path.exists():
        return json.loads(manifest_path.read_text())
    return {}


def _save_manifest(manifest_path: Path, manifest: dict[str, str]) -> None:
    """Write the classification manifest to disk."""
    manifest_path.write_text(json.dumps(manifest, indent=2))


def classify_slides(
    candidates_dir: Path,
    output_dir: Path | None = None,
) -> list[Path]:
    """Classify candidate frames as slide / not-slide using Claude vision.

    Uses a manifest file (manifest.json) for resume support — if the process
    is interrupted, re-running will skip already-classified batches.

    Copies slides to output_dir. Returns list of slide paths.
    """
    if output_dir is None:
        output_dir = candidates_dir.parent / "slides"

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"

    candidates = sorted(candidates_dir.glob("frame_*.jpg"))
    if not candidates:
        console.print("No candidate frames found.")
        return []

    # Load existing manifest for resume support
    manifest = _load_manifest(manifest_path)

    # Check if all candidates are already classified
    remaining = [c for c in candidates if c.name not in manifest]

    if not remaining:
        slides = [output_dir / c.name for c in candidates if manifest.get(c.name) == "SLIDE"]
        slides = [s for s in slides if s.exists()]
        console.print(f"All candidates already classified: {len(slides)} slides in {output_dir}")
        return sorted(slides)

    if manifest:
        console.print(f"Resuming classification: {len(manifest)} already done, {len(remaining)} remaining")

    client = anthropic.Anthropic()

    # Process remaining candidates in batches
    batches = [remaining[i : i + BATCH_SIZE] for i in range(0, len(remaining), BATCH_SIZE)]

    for batch in track(batches, description="Classifying", console=console):
        results = _classify_batch(client, batch)
        for path, is_slide in zip(batch, results):
            label = "SLIDE" if is_slide else "NOT_SLIDE"
            manifest[path.name] = label
            if is_slide:
                dst = output_dir / path.name
                shutil.copy2(path, dst)

        # Flush manifest after each batch for resume safety
        _save_manifest(manifest_path, manifest)

    slides = sorted(
        [output_dir / c.name for c in candidates if manifest.get(c.name) == "SLIDE" and (output_dir / c.name).exists()]
    )
    console.print(f"Classified [bold]{len(slides)}[/bold] slides out of {len(candidates)} candidates -> {output_dir}")
    return slides
