"""
High-throughput video frame extraction engine with periodic, custom timestamp,
and smart slide-transition detection modes.
"""

from pathlib import Path
from typing import List, Optional, Callable
import cv2
import numpy as np
from PIL import Image

from core.job_manager import CancellationToken
from database.models import Screenshot
from utils.filesystem import ensure_dir
from utils.logger import logger
from utils.time_utils import seconds_to_filename_str, parse_timestamp_str, seconds_to_hms
from video.timestamp_overlay import overlay_renderer


class FrameExtractor:
    """Extracts periodic or target-timestamped lecture frames with optional overlay."""

    @staticmethod
    def extract_frames(
        video_path: Path | str,
        output_dir: Path | str,
        project_id: str,
        interval_seconds: float = 30.0,
        custom_timestamps: Optional[List[str | float]] = None,
        smart_slide_detection: bool = False,
        slide_diff_threshold: float = 0.35,
        apply_overlay: bool = False,
        lecture_title: str = "",
        course_name: str = "",
        jpeg_quality: int = 85,
        max_dimension: Optional[int] = None,  # e.g., 1920 for 1080p
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cancel_token: Optional[CancellationToken] = None
    ) -> List[Screenshot]:
        v_path = Path(video_path)
        out_dir = ensure_dir(output_dir)

        if not v_path.exists():
            raise FileNotFoundError(f"Video file does not exist: {video_path}")

        cap = cv2.VideoCapture(str(v_path.resolve()))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video source with OpenCV: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = (total_frames / fps) if fps > 0 else 0.0

        target_timestamps: List[float] = []

        if custom_timestamps and len(custom_timestamps) > 0:
            for ts in custom_timestamps:
                if isinstance(ts, (int, float)):
                    target_timestamps.append(float(ts))
                elif isinstance(ts, str):
                    parsed = parse_timestamp_str(ts)
                    if parsed is not None:
                        target_timestamps.append(parsed)
            target_timestamps = sorted(list(set(target_timestamps)))
        else:
            # Fixed interval timestamps
            if interval_seconds <= 0:
                interval_seconds = 30.0
            curr_sec = 0.0
            while curr_sec < duration_seconds:
                target_timestamps.append(curr_sec)
                curr_sec += interval_seconds

        total_targets = len(target_timestamps)
        extracted: List[Screenshot] = []
        last_hist = None

        logger.info(f"Extracting {total_targets} frames from {v_path.name} (Duration: {seconds_to_hms(duration_seconds)})")

        try:
            for idx, target_sec in enumerate(target_timestamps):
                if cancel_token and cancel_token.is_cancelled():
                    logger.info("Frame extraction cancelled by user.")
                    break

                target_frame_num = int(target_sec * fps)
                cap.set(cv2.CAP_PROP_POS_MSEC, target_sec * 1000.0)
                ret, frame = cap.read()
                if not ret or frame is None:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_num)
                    ret, frame = cap.read()
                if not ret or frame is None:
                    continue

                # Optional resize / downscale
                h, w = frame.shape[:2]
                if max_dimension and (w > max_dimension or h > max_dimension):
                    scale = max_dimension / max(w, h)
                    frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

                # Smart slide change detection check if enabled
                is_slide_change = False
                if smart_slide_detection:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
                    cv2.normalize(hist, hist)
                    if last_hist is not None:
                        sim = cv2.compareHist(last_hist, hist, cv2.HISTCMP_CORREL)
                        if sim < (1.0 - slide_diff_threshold):
                            is_slide_change = True
                    else:
                        is_slide_change = True
                    last_hist = hist

                # Screenshots must NEVER show title name and time in bottom:
                # Always save 100% pure video frame (overlays belong exclusively to compiled PDF)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)

                # Save file
                filename = f"lecture_{seconds_to_filename_str(target_sec)}.jpg"
                out_path = out_dir / filename
                pil_img.save(str(out_path), "JPEG", quality=jpeg_quality, optimize=True)

                screenshot_record = Screenshot(
                    id=f"{project_id}_{int(target_sec)}",
                    project_id=project_id,
                    timestamp=target_sec,
                    file_path=str(out_path.resolve()),
                    page_number=len(extracted) + 1,
                    is_slide_change=is_slide_change
                )
                extracted.append(screenshot_record)

                if progress_callback:
                    pct = ((idx + 1) / total_targets) * 100.0
                    progress_callback(pct, f"Captured frame {idx+1}/{total_targets} ({seconds_to_hms(target_sec)})")

        finally:
            cap.release()

        logger.info(f"Frame extraction completed. Total captured: {len(extracted)}")
        return extracted


frame_extractor = FrameExtractor()
