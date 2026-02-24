from pathlib import Path

import img2pdf

from slide_extractor.console import console


def compile_pdf(
    slides_dir: Path,
    output_path: Path | None = None,
) -> Path:
    """Combine slide images into a single PDF, one image per page.

    Returns the path to the generated PDF.
    """
    if output_path is None:
        output_path = slides_dir.parent / "slides.pdf"

    images = sorted(slides_dir.glob("frame_*.jpg"))
    if not images:
        raise FileNotFoundError(f"No slide images found in {slides_dir}")

    console.print(f"Compiling {len(images)} slides into {output_path} ...")
    pdf_bytes = img2pdf.convert([str(p) for p in images])
    output_path.write_bytes(pdf_bytes)
    console.print(f"PDF saved: [bold]{output_path}[/bold]")
    return output_path
