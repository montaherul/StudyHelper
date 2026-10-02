"""
LocalStudy — Offline Lecture Processing Toolkit
Main Application Entry Point (Desktop GUI & CLI).

100% Local Inference • Zero External AI APIs • Zero Cloud Telemetry
"""

import sys
import argparse
from pathlib import Path

# Ensure root directory is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.constants import APP_NAME, APP_VERSION
from utils.logger import logger
from video.ffmpeg_finder import get_ffmpeg_path
import utils.av_patch

# Ensure FFmpeg is resolved and placed on PATH immediately
get_ffmpeg_path()


def run_gui():
    """Launches the PySide6 desktop user interface."""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from ui.main_window import MainWindow

    # Enable High-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setFont(QFont("Segoe UI", 10))

    window = MainWindow()
    window.show()

    logger.info(f"{APP_NAME} v{APP_VERSION} initialized successfully.")
    sys.exit(app.exec())


def run_cli(args):
    """Executes headless command-line processing pipeline."""
    from core.project_manager import project_manager
    from database.db import db
    from video.frame_extractor import frame_extractor
    from pdf.generator import pdf_generator
    from transcription.audio_extractor import audio_extractor
    from transcription.engine import transcription_engine
    from transcription.exporters import transcript_exporter
    from video.downloader import video_downloader

    raw_input = args.video.strip()
    is_url = raw_input.startswith("http://") or raw_input.startswith("https://")

    if not is_url:
        video_path = Path(raw_input).resolve()
        if not video_path.exists():
            print(f"Error: Video file not found: {video_path}")
            sys.exit(1)
        proj_name = args.name or video_path.stem.replace("_", " ").title()
    else:
        proj_name = args.name or "Online Lecture"

    print(f"=== {APP_NAME} Headless CLI ===")
    print(f"Source: {raw_input}")
    print(f"Project Name: {proj_name}")

    proj = project_manager.create_project(
        name=proj_name,
        subject=args.subject or "",
        course=args.course or ""
    )

    if is_url:
        print("\n[0/3] Downloading video from URL via yt-dlp...")
        source_dir = Path(proj.output_path) / "source"
        video_path = video_downloader.download_video(
            url=raw_input,
            output_dir=source_dir,
            filename_prefix=proj.name,
            progress_callback=lambda pct, msg: print(f"\r  -> Progress: {pct:.1f}% ({msg})", end="")
        )
        print(f"\n  [OK] Downloaded: {video_path.name}")

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # 1. Screenshot Extraction
    print(f"\n[1/3] Extracting slides every {args.interval} seconds (Clean raw captures)...")
    out_ss = Path(proj.output_path) / "screenshots"
    screenshots = frame_extractor.extract_frames(
        video_path=video_path,
        output_dir=out_ss,
        project_id=proj.id,
        interval_seconds=float(args.interval),
        apply_overlay=False,
        lecture_title=proj.name,
        course_name=proj.course,
        progress_callback=lambda pct, msg: print(f"\r  -> Progress: {pct:.1f}% ({msg})", end="")
    )
    db.save_screenshots(screenshots)
    print(f"\n  [OK] Captured {len(screenshots)} slides (Clean, no burned-in text).")

    # 2. PDF Compilation
    if screenshots:
        print(f"\n[2/3] Compiling study PDF ({args.layout} layout)...")
        out_pdf = Path(proj.output_path) / "pdf" / f"{proj.name}_StudyGuide.pdf"
        pdf_path = pdf_generator.compile_pdf(
            project=proj,
            screenshots=screenshots,
            output_pdf_path=out_pdf,
            layout=args.layout,
            show_timestamp=True,
            time_only=True,
            cover_project_name_only=True,
            progress_callback=lambda pct, msg: print(f"\r  -> Progress: {pct:.1f}% ({msg})", end="")
        )
        print(f"\n  [OK] Generated PDF: {pdf_path}")

    # 3. Audio Transcription (if requested)
    if args.transcribe:
        print(f"\n[3/3] Extracting audio and running local faster-whisper ({args.model})...")
        wav_path = Path(proj.output_path) / "transcript" / "temp_audio.wav"
        audio_extractor.extract_16k_mono_wav(video_path, wav_path)
        segments = transcription_engine.transcribe_audio(
            audio_path=wav_path,
            project_id=proj.id,
            model_size=args.model,
            language=args.lang,
            progress_callback=lambda pct, msg: print(f"\r  -> Progress: {pct:.1f}% ({msg})", end="")
        )
        db.save_transcript_segments(segments)
        transcript_exporter.export_all(segments, Path(proj.output_path) / "transcript")
        if wav_path.exists():
            wav_path.unlink(missing_ok=True)
        print(f"\n  [OK] Transcribed {len(segments)} segments into TXT, SRT, VTT, and JSON.")

    print(f"\n=== Processing Complete! ===")
    print(f"All study materials saved to: {proj.output_path}")


def main():
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} — Offline Lecture Processing Toolkit"
    )
    parser.add_argument("--cli", action="store_true", help="Run in headless CLI mode instead of GUI")
    parser.add_argument("--video", type=str, help="Path to lecture video file (CLI mode)")
    parser.add_argument("--name", type=str, help="Project name (CLI mode)")
    parser.add_argument("--subject", type=str, help="Subject/topic name (CLI mode)")
    parser.add_argument("--course", type=str, help="Course code e.g. CSE-321 (CLI mode)")
    parser.add_argument("--interval", type=int, default=30, help="Screenshot interval in seconds (default: 30)")
    parser.add_argument("--layout", type=str, default="2-up", choices=["1-up", "2-up", "4-up"], help="PDF layout")
    parser.add_argument("--transcribe", action="store_true", help="Perform offline speech transcription")
    parser.add_argument("--model", type=str, default="base", help="Whisper model tier (tiny, base, small, medium)")
    parser.add_argument("--lang", type=str, default=None, help="Language code e.g. en, bn, hi (default: auto)")

    args = parser.parse_args()

    if args.cli:
        if not args.video:
            print("Error: --video path is required when using --cli mode.")
            sys.exit(1)
        run_cli(args)
    else:
        run_gui()


if __name__ == "__main__":
    main()
