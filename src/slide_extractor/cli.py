import argparse
import sys
from pathlib import Path

from slide_extractor.classify import classify_slides
from slide_extractor.compile import compile_pdf
from slide_extractor.deduplicate import deduplicate
from slide_extractor.detect import detect_transitions
from slide_extractor.download import download, extract_video_id
from slide_extractor.extract import extract_frames


def cmd_download(args: argparse.Namespace) -> None:
    output_dir = Path(args.output) if args.output else None
    path = download(args.url, output_dir)
    print(f"Done: {path}")


def cmd_extract(args: argparse.Namespace) -> None:
    video_path = Path(args.video)
    output_dir = Path(args.output) if args.output else None
    frames = extract_frames(video_path, output_dir, fps=args.fps)
    print(f"Done: {len(frames)} frames")


def cmd_detect(args: argparse.Namespace) -> None:
    frames_dir = Path(args.frames_dir)
    output_dir = Path(args.output) if args.output else None
    candidates = detect_transitions(frames_dir, output_dir, threshold=args.threshold)
    print(f"Done: {len(candidates)} candidates")


def cmd_classify(args: argparse.Namespace) -> None:
    candidates_dir = Path(args.candidates_dir)
    output_dir = Path(args.output) if args.output else None
    slides = classify_slides(candidates_dir, output_dir)
    print(f"Done: {len(slides)} slides")


def cmd_dedup(args: argparse.Namespace) -> None:
    slides_dir = Path(args.slides_dir)
    output_dir = Path(args.output) if args.output else None
    result = deduplicate(slides_dir, output_dir, threshold=args.threshold)
    print(f"Done: {len(result)} unique slides")


def cmd_compile(args: argparse.Namespace) -> None:
    slides_dir = Path(args.slides_dir)
    output_path = Path(args.output) if args.output else None
    path = compile_pdf(slides_dir, output_path)
    print(f"Done: {path}")


def cmd_run(args: argparse.Namespace) -> None:
    """Run the full pipeline: download -> extract -> detect -> classify -> dedup -> compile."""
    url = args.url
    video_id = extract_video_id(url)
    base_dir = Path("output") / video_id

    print(f"=== Pipeline for {video_id} ===\n")

    # Step 1: Download
    print("--- Step 1/6: Download ---")
    video_path = download(url, base_dir)
    print()

    # Step 2: Extract frames
    print("--- Step 2/6: Extract frames ---")
    frames_dir = base_dir / "frames"
    extract_frames(video_path, frames_dir, fps=args.fps)
    print()

    # Step 3: Detect transitions
    print("--- Step 3/6: Detect transitions ---")
    candidates_dir = base_dir / "candidates"
    detect_transitions(frames_dir, candidates_dir, threshold=args.detect_threshold)
    print()

    # Step 4: Classify slides
    print("--- Step 4/6: Classify slides ---")
    slides_dir = base_dir / "slides"
    classify_slides(candidates_dir, slides_dir)
    print()

    # Step 5: Deduplicate
    print("--- Step 5/6: Deduplicate ---")
    deduped_dir = base_dir / "slides_deduped"
    deduplicate(slides_dir, deduped_dir, threshold=args.dedup_threshold)
    print()

    # Step 6: Compile PDF
    print("--- Step 6/6: Compile PDF ---")
    pdf_path = base_dir / "slides.pdf"
    compile_pdf(deduped_dir, pdf_path)
    print()

    print(f"=== Done! PDF: {pdf_path} ===")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="slide-extractor",
        description="Extract presentation slides from lecture videos into PDFs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- download ---
    p_dl = subparsers.add_parser("download", help="Download a YouTube video")
    p_dl.add_argument("url", help="YouTube video URL")
    p_dl.add_argument("-o", "--output", help="Output directory")
    p_dl.set_defaults(func=cmd_download)

    # --- extract ---
    p_ex = subparsers.add_parser("extract", help="Extract frames from a video")
    p_ex.add_argument("video", help="Path to video file")
    p_ex.add_argument("-o", "--output", help="Output directory for frames")
    p_ex.add_argument("--fps", type=float, default=1.0, help="Frames per second (default: 1)")
    p_ex.set_defaults(func=cmd_extract)

    # --- detect ---
    p_dt = subparsers.add_parser("detect", help="Detect slide transitions")
    p_dt.add_argument("frames_dir", help="Directory containing extracted frames")
    p_dt.add_argument("-o", "--output", help="Output directory for candidates")
    p_dt.add_argument("--threshold", type=int, default=10, help="Hash distance threshold (default: 10)")
    p_dt.set_defaults(func=cmd_detect)

    # --- classify ---
    p_cl = subparsers.add_parser("classify", help="Classify candidates as slide/not-slide")
    p_cl.add_argument("candidates_dir", help="Directory containing candidate frames")
    p_cl.add_argument("-o", "--output", help="Output directory for slides")
    p_cl.set_defaults(func=cmd_classify)

    # --- dedup ---
    p_dd = subparsers.add_parser("dedup", help="Deduplicate similar slides")
    p_dd.add_argument("slides_dir", help="Directory containing classified slides")
    p_dd.add_argument("-o", "--output", help="Output directory for deduplicated slides")
    p_dd.add_argument("--threshold", type=int, default=5, help="Hash distance threshold (default: 5)")
    p_dd.set_defaults(func=cmd_dedup)

    # --- compile ---
    p_cp = subparsers.add_parser("compile", help="Compile slides into a PDF")
    p_cp.add_argument("slides_dir", help="Directory containing slide images")
    p_cp.add_argument("-o", "--output", help="Output PDF path")
    p_cp.set_defaults(func=cmd_compile)

    # --- run (full pipeline) ---
    p_run = subparsers.add_parser("run", help="Run the full pipeline end-to-end")
    p_run.add_argument("url", help="YouTube video URL")
    p_run.add_argument("--fps", type=float, default=1.0, help="Frame extraction FPS (default: 1)")
    p_run.add_argument("--detect-threshold", type=int, default=10, help="Transition detection threshold (default: 10)")
    p_run.add_argument("--dedup-threshold", type=int, default=5, help="Deduplication threshold (default: 5)")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
