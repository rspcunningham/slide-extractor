import argparse
import subprocess
import sys
from pathlib import Path

from slide_extractor.classify import classify_slides
from slide_extractor.compile import compile_pdf
from slide_extractor.console import console
from slide_extractor.deduplicate import deduplicate
from slide_extractor.detect import detect_transitions
from slide_extractor.download import (
    download,
    enumerate_playlist,
    extract_playlist_id,
    extract_video_id,
    is_playlist,
)
from slide_extractor.extract import extract_frames
from slide_extractor.index import generate_index
from slide_extractor.summarize import summarize_lecture


def _auto_open(path: Path) -> None:
    """Open a file with the system default application (macOS only)."""
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)])


def cmd_download(args: argparse.Namespace) -> None:
    output_dir = Path(args.output) if args.output else None
    path = download(args.url, output_dir)
    console.print(f"Done: {path}")


def cmd_extract(args: argparse.Namespace) -> None:
    video_path = Path(args.video)
    output_dir = Path(args.output) if args.output else None
    frames = extract_frames(video_path, output_dir, fps=args.fps)
    console.print(f"Done: {len(frames)} frames")


def cmd_detect(args: argparse.Namespace) -> None:
    frames_dir = Path(args.frames_dir)
    output_dir = Path(args.output) if args.output else None
    candidates = detect_transitions(frames_dir, output_dir, threshold=args.threshold)
    console.print(f"Done: {len(candidates)} candidates")


def cmd_classify(args: argparse.Namespace) -> None:
    candidates_dir = Path(args.candidates_dir)
    output_dir = Path(args.output) if args.output else None
    slides = classify_slides(candidates_dir, output_dir)
    console.print(f"Done: {len(slides)} slides")


def cmd_dedup(args: argparse.Namespace) -> None:
    slides_dir = Path(args.slides_dir)
    output_dir = Path(args.output) if args.output else None
    result = deduplicate(slides_dir, output_dir, threshold=args.threshold)
    console.print(f"Done: {len(result)} unique slides")


def cmd_compile(args: argparse.Namespace) -> None:
    slides_dir = Path(args.slides_dir)
    output_path = Path(args.output) if args.output else None
    path = compile_pdf(slides_dir, output_path)
    console.print(f"Done: {path}")


def cmd_summarize(args: argparse.Namespace) -> None:
    slides_dir = Path(args.slides_dir)
    output_path = Path(args.output) if args.output else None
    path = summarize_lecture(args.url, slides_dir, output_path)
    console.print(f"Done: {path}")


def _run_single_video(
    url: str,
    base_dir: Path,
    fps: float,
    detect_threshold: int,
    dedup_threshold: int,
) -> Path:
    """Run the full pipeline for a single video. Returns the PDF path."""
    # Step 1: Download
    console.rule("[bold]Step 1/7: Download[/bold]")
    video_path = download(url, base_dir)

    # Step 2: Extract frames
    console.rule("[bold]Step 2/7: Extract frames[/bold]")
    frames_dir = base_dir / "frames"
    extract_frames(video_path, frames_dir, fps=fps)

    # Step 3: Detect transitions
    console.rule("[bold]Step 3/7: Detect transitions[/bold]")
    candidates_dir = base_dir / "candidates"
    detect_transitions(frames_dir, candidates_dir, threshold=detect_threshold)

    # Step 4: Classify slides
    console.rule("[bold]Step 4/7: Classify slides[/bold]")
    slides_dir = base_dir / "slides"
    classify_slides(candidates_dir, slides_dir)

    # Step 5: Deduplicate
    console.rule("[bold]Step 5/7: Deduplicate[/bold]")
    deduped_dir = base_dir / "slides_deduped"
    deduplicate(slides_dir, deduped_dir, threshold=dedup_threshold)

    # Step 6: Compile PDF
    console.rule("[bold]Step 6/7: Compile PDF[/bold]")
    pdf_path = base_dir / "slides.pdf"
    compile_pdf(deduped_dir, pdf_path)

    # Step 7: Summarize
    console.rule("[bold]Step 7/7: Summarize[/bold]")
    summarize_lecture(url, deduped_dir, base_dir / "summary.md")

    return pdf_path


def cmd_run(args: argparse.Namespace) -> None:
    """Run the full pipeline: download -> extract -> detect -> classify -> dedup -> compile -> summarize."""
    url = args.url
    should_open = not args.no_open

    if is_playlist(url):
        playlist_id = extract_playlist_id(url)
        base_dir = Path("output") / playlist_id

        console.rule(f"[bold green]Playlist: {playlist_id}[/bold green]", style="green")
        videos = enumerate_playlist(url)

        video_records: list[dict] = []

        for i, video in enumerate(videos, 1):
            console.rule(
                f"[bold cyan]Video {i}/{len(videos)}: {video['title']}[/bold cyan]",
                style="cyan",
            )
            video_dir = base_dir / video["id"]

            try:
                _run_single_video(
                    video["url"],
                    video_dir,
                    fps=args.fps,
                    detect_threshold=args.detect_threshold,
                    dedup_threshold=args.dedup_threshold,
                )
                video_records.append({
                    "video_id": video["id"],
                    "title": video["title"],
                    "url": video["url"],
                })
            except Exception as e:
                console.print(f"[red]Error processing {video['title']}: {e}[/red]")
                continue

        # Generate course index
        if video_records:
            console.rule("[bold green]Course Index[/bold green]", style="green")
            # Use first video's metadata for playlist title (yt-dlp flat-playlist
            # doesn't return playlist title easily, so we use a sensible fallback)
            playlist_title = f"Course ({len(video_records)} lectures)"
            index_path = generate_index(base_dir, playlist_title, video_records)
            console.print(f"\n[bold green]Done! Index: {index_path}[/bold green]")

            if should_open:
                _auto_open(index_path)
    else:
        video_id = extract_video_id(url)
        base_dir = Path("output") / video_id

        console.rule(f"[bold green]Pipeline: {video_id}[/bold green]", style="green")

        pdf_path = _run_single_video(
            url,
            base_dir,
            fps=args.fps,
            detect_threshold=args.detect_threshold,
            dedup_threshold=args.dedup_threshold,
        )

        console.print(f"\n[bold green]Done! PDF: {pdf_path}[/bold green]")

        if should_open:
            _auto_open(pdf_path)


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

    # --- summarize ---
    p_sm = subparsers.add_parser("summarize", help="Generate a lecture summary")
    p_sm.add_argument("url", help="YouTube video URL")
    p_sm.add_argument("slides_dir", help="Directory containing slide images")
    p_sm.add_argument("-o", "--output", help="Output summary path")
    p_sm.set_defaults(func=cmd_summarize)

    # --- run (full pipeline) ---
    p_run = subparsers.add_parser("run", help="Run the full pipeline end-to-end")
    p_run.add_argument("url", help="YouTube video or playlist URL")
    p_run.add_argument("--fps", type=float, default=1.0, help="Frame extraction FPS (default: 1)")
    p_run.add_argument("--detect-threshold", type=int, default=10, help="Transition detection threshold (default: 10)")
    p_run.add_argument("--dedup-threshold", type=int, default=5, help="Deduplication threshold (default: 5)")
    p_run.add_argument("--no-open", action="store_true", help="Don't auto-open the output when done")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
