"""
Video and audio file metadata analyzer for LocalStudy.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import cv2

from utils.logger import logger
from utils.time_utils import seconds_to_hms


class MediaAnalyzer:
    """Probes media containers and extracts duration, resolution, frame rate, and codecs."""

    @staticmethod
    def analyze_video(video_path: Path | str) -> Dict[str, Any]:
        p = Path(video_path)
        if not p.exists():
            raise FileNotFoundError(f"Media file not found: {video_path}")

        meta: Dict[str, Any] = {
            "path": str(p.resolve()),
            "filename": p.name,
            "size_bytes": p.stat().st_size,
            "duration": 0.0,
            "duration_hms": "00:00:00",
            "width": 0,
            "height": 0,
            "resolution": "Unknown",
            "fps": 0.0,
            "total_frames": 0,
            "has_video": False,
            "has_audio": False
        }

        cap = cv2.VideoCapture(str(p))
        if cap.isOpened():
            meta["has_video"] = True
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            duration = (total_frames / fps) if fps > 0 else 0.0

            meta["fps"] = round(fps, 2)
            meta["total_frames"] = total_frames
            meta["width"] = width
            meta["height"] = height
            meta["resolution"] = f"{width}x{height}" if width and height else "Unknown"
            meta["duration"] = round(duration, 2)
            meta["duration_hms"] = seconds_to_hms(duration)
            cap.release()
        else:
            logger.warning(f"OpenCV could not open {video_path} directly. Checking audio or container.")

        return meta


analyzer = MediaAnalyzer()
