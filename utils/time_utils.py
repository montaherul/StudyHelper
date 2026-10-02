"""
Time conversion and formatting utilities for LocalStudy.
Converts between seconds, timestamp strings, filename tokens, SRT, and VTT formats.
"""

import re
from typing import Optional


def seconds_to_hms(seconds: float, include_ms: bool = False) -> str:
    """Converts a float number of seconds to HH:MM:SS or HH:MM:SS.mmm format."""
    if seconds < 0:
        seconds = 0.0

    total_secs = int(seconds)
    hours = total_secs // 3600
    minutes = (total_secs % 3600) // 60
    secs = total_secs % 60

    if include_ms:
        millis = int(round((seconds - total_secs) * 1000))
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def seconds_to_filename_str(seconds: float) -> str:
    """Converts seconds into safe filename format: {HH}h{MM}m{SS}s."""
    total_secs = int(seconds)
    hours = total_secs // 3600
    minutes = (total_secs % 3600) // 60
    secs = total_secs % 60
    return f"{hours:02d}h{minutes:02d}m{secs:02d}s"


def parse_timestamp_str(time_str: str) -> Optional[float]:
    """
    Parses a timestamp string in various formats to seconds.
    Supported:
      - 'HH:MM:SS' or 'H:MM:SS'
      - 'MM:SS' or 'M:SS'
      - 'HH:MM:SS.mmm' or 'MM:SS,mmm'
      - Plain seconds: '125', '125.5'
    """
    time_str = time_str.strip().replace(",", ".")
    if not time_str:
        return None

    # Check for simple float seconds
    try:
        val = float(time_str)
        return max(0.0, val)
    except ValueError:
        pass

    # Colon-separated format: [HH:]MM:SS[.mmm]
    parts = time_str.split(":")
    try:
        if len(parts) == 3:
            h = float(parts[0])
            m = float(parts[1])
            s = float(parts[2])
            return max(0.0, h * 3600 + m * 60 + s)
        elif len(parts) == 2:
            m = float(parts[0])
            s = float(parts[1])
            return max(0.0, m * 60 + s)
    except ValueError:
        return None

    return None


def format_srt_time(seconds: float) -> str:
    """Converts seconds to SRT time format: HH:MM:SS,mmm."""
    if seconds < 0:
        seconds = 0.0
    total_secs = int(seconds)
    hours = total_secs // 3600
    minutes = (total_secs % 3600) // 60
    secs = total_secs % 60
    millis = int(round((seconds - total_secs) * 1000))
    if millis >= 1000:
        secs += 1
        millis -= 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_vtt_time(seconds: float) -> str:
    """Converts seconds to WebVTT time format: HH:MM:SS.mmm."""
    if seconds < 0:
        seconds = 0.0
    total_secs = int(seconds)
    hours = total_secs // 3600
    minutes = (total_secs % 3600) // 60
    secs = total_secs % 60
    millis = int(round((seconds - total_secs) * 1000))
    if millis >= 1000:
        secs += 1
        millis -= 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def format_txt_header(seconds: float) -> str:
    """Formats timestamp header for TXT transcripts: [HH:MM:SS]."""
    return f"[{seconds_to_hms(seconds)}]"
