"""
High-performance audio extraction and 16kHz mono PCM resampling using FFmpeg.
"""

import subprocess
from pathlib import Path
from typing import Optional, Callable

from core.job_manager import CancellationToken
from utils.filesystem import ensure_dir
from utils.logger import logger
from video.ffmpeg_finder import get_ffmpeg_path


class AudioExtractor:
    """Extracts and normalizes audio streams from media containers to 16kHz mono WAV."""

    @staticmethod
    def extract_16k_mono_wav(
        media_path: Path | str,
        output_wav_path: Path | str,
        cancel_token: Optional[CancellationToken] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        in_path = Path(media_path).resolve()
        out_path = Path(output_wav_path).resolve()

        if not in_path.exists():
            raise FileNotFoundError(f"Input media file does not exist: {in_path}")

        ensure_dir(out_path.parent)

        if cancel_token and cancel_token.is_cancelled():
            raise RuntimeError("Operation cancelled before audio extraction started.")

        if progress_callback:
            progress_callback(10.0, "Extracting audio track with FFmpeg...")

        ffmpeg_bin = get_ffmpeg_path()

        # Command: Extract audio, downmix to mono (-ac 1), resample to 16kHz (-ar 16000), 16-bit PCM
        cmd = [
            ffmpeg_bin,
            "-y",                     # Overwrite output
            "-i", str(in_path),       # Input file
            "-vn",                    # Disable video recording
            "-acodec", "pcm_s16le",   # Uncompressed 16-bit PCM
            "-ar", "16000",           # 16 kHz sample rate (optimal for Whisper)
            "-ac", "1",               # Mono channel
            str(out_path)
        ]

        logger.info(f"Running audio extraction command: {' '.join(cmd[:6])} ...")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Monitor process with cancellation check
        while process.poll() is None:
            if cancel_token and cancel_token.is_cancelled():
                process.terminate()
                process.wait(timeout=3)
                if out_path.exists():
                    out_path.unlink(missing_ok=True)
                raise RuntimeError("Audio extraction cancelled by user.")

        stdout, stderr = process.communicate()
        if process.returncode != 0:
            logger.error(f"FFmpeg audio extraction failed: {stderr}")
            raise RuntimeError(f"FFmpeg error: {stderr[:300]}")

        if not out_path.exists() or out_path.stat().st_size == 0:
            raise RuntimeError("FFmpeg succeeded but output audio file is empty or missing.")

        if progress_callback:
            progress_callback(100.0, "Audio extraction complete (16kHz WAV).")

        logger.info(f"Successfully extracted 16kHz WAV to {out_path} ({out_path.stat().st_size} bytes)")
        return out_path


audio_extractor = AudioExtractor()
