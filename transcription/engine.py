"""
Local speech-to-text inference engine using faster-whisper.
Runs 100% offline with zero external APIs, utilizing int8 quantization.
"""

from pathlib import Path
from typing import List, Optional, Callable
import os

from core.hardware_detector import HardwareDetector
from core.job_manager import CancellationToken
from database.models import TranscriptSegment
from transcription.model_manager import model_manager
from utils.logger import logger
from utils.time_utils import seconds_to_hms
import utils.av_patch


class TranscriptionEngine:
    """Orchestrates local faster-whisper inference with cancellation and progress reporting."""

    def __init__(self):
        self._current_model = None
        self._loaded_model_id: Optional[str] = None

    def load_model(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        cpu_threads: int = 4
    ):
        """Loads or reuses a cached faster-whisper model instance."""
        from faster_whisper import WhisperModel

        if self._current_model is not None and self._loaded_model_id == model_size:
            return self._current_model

        logger.info(f"Loading faster-whisper model '{model_size}' (device={device}, compute_type={compute_type}, threads={cpu_threads})")

        # Resolve local download path if cached
        model_dir = model_manager.models_dir / model_size
        model_source = str(model_dir) if model_dir.exists() else model_size

        self._current_model = WhisperModel(
            model_source,
            device=device,
            compute_type=compute_type,
            cpu_threads=cpu_threads,
            download_root=str(model_manager.models_dir)
        )
        self._loaded_model_id = model_size
        return self._current_model

    def transcribe_audio(
        self,
        audio_path: Path | str,
        project_id: str,
        model_size: str = "base",
        language: Optional[str] = None,
        duration_seconds: float = 0.0,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cancel_token: Optional[CancellationToken] = None
    ) -> List[TranscriptSegment]:
        in_path = Path(audio_path).resolve()
        if not in_path.exists():
            raise FileNotFoundError(f"Audio file not found: {in_path}")

        # Auto-tune hardware parameters
        hw_preset = HardwareDetector.get_recommended_settings()
        device = hw_preset["device"]
        compute_type = hw_preset["compute_type"]
        cpu_threads = hw_preset["cpu_threads"]

        if progress_callback:
            progress_callback(5.0, f"Initializing local transcription model '{model_size}'...")

        model = self.load_model(
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=cpu_threads
        )

        if cancel_token and cancel_token.is_cancelled():
            raise RuntimeError("Transcription cancelled by user.")

        logger.info(f"Starting inference on {in_path.name} (Lang: {language or 'auto'}, Model: {model_size})")
        if progress_callback:
            progress_callback(15.0, "Transcribing speech segments locally...")

        segments_generator, info = model.transcribe(
            str(in_path),
            language=language,
            beam_size=5,
            vad_filter=True,  # Voice activity detection to trim silence
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        detected_lang = info.language
        lang_prob = info.language_probability
        audio_duration = duration_seconds or info.duration or 1.0

        logger.info(f"Detected speech language: {detected_lang} (Confidence: {lang_prob:.2f})")

        results: List[TranscriptSegment] = []

        for seg in segments_generator:
            if cancel_token and cancel_token.is_cancelled():
                logger.info("Local transcription aborted by user.")
                break

            clean_text = seg.text.strip()
            if not clean_text:
                continue

            record = TranscriptSegment(
                id=None,
                project_id=project_id,
                start_time=round(seg.start, 2),
                end_time=round(seg.end, 2),
                text=clean_text
            )
            results.append(record)

            if progress_callback and audio_duration > 0:
                # Progress scaled from 15% to 95%
                processed_pct = min(1.0, seg.end / audio_duration)
                overall_pct = 15.0 + (processed_pct * 80.0)
                progress_callback(
                    overall_pct,
                    f"Transcribed up to {seconds_to_hms(seg.end)}: '{clean_text[:40]}...'"
                )

        if progress_callback:
            progress_callback(100.0, f"Transcription completed. {len(results)} segments generated.")

        logger.info(f"Local transcription completed. Total segments: {len(results)}")
        return results


transcription_engine = TranscriptionEngine()
