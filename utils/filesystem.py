"""
Filesystem and storage utilities for LocalStudy.
Handles safe path sanitization, free disk space inspection, and size formatting.
"""

import os
import re
import shutil
from pathlib import Path


def sanitize_filename(name: str, replacement: str = "_") -> str:
    """Removes or replaces invalid filename characters for cross-platform safety."""
    if not name:
        return "untitled_lecture"
    # Remove characters that are illegal on Windows, Linux, and macOS
    sanitized = re.sub(r'[\\/*?:"<>|]', replacement, name)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized or "untitled_lecture"


def get_free_disk_space_bytes(path: Path | str) -> int:
    """Returns the free disk space in bytes for the drive containing path."""
    p = Path(path).resolve()
    # Check parents until an existing directory is found
    while not p.exists() and p != p.parent:
        p = p.parent
    try:
        usage = shutil.disk_usage(str(p))
        return usage.free
    except Exception:
        return 0


def format_bytes(bytes_count: int | float) -> str:
    """Converts a raw byte count to human-readable string (KB, MB, GB, TB)."""
    units = ["B", "KB", "MB", "GB", "TB"]
    val = float(bytes_count)
    unit_idx = 0
    while val >= 1024.0 and unit_idx < len(units) - 1:
        val /= 1024.0
        unit_idx += 1
    return f"{val:.1f} {units[unit_idx]}"


# Alias for format_bytes
format_file_size = format_bytes


def estimate_storage_required(duration_secs: float, interval_secs: float, avg_frame_kb: int = 150) -> dict:
    """
    Estimates required disk space for screenshots, PDF, and transcript.
    Returns dictionary with component sizes in bytes and human-formatted strings.
    """
    if interval_secs <= 0:
        interval_secs = 30.0

    frame_count = max(1, int(duration_secs / interval_secs))
    screenshot_bytes = frame_count * (avg_frame_kb * 1024)
    # PDF is roughly 60% of total image weights with compression + overhead
    pdf_bytes = int(screenshot_bytes * 0.6) + (2 * 1024 * 1024)
    # Transcript is small (~2KB per minute)
    transcript_bytes = int((duration_secs / 60.0) * 2048) + 10240
    total_bytes = screenshot_bytes + pdf_bytes + transcript_bytes

    return {
        "frame_count": frame_count,
        "screenshot_bytes": screenshot_bytes,
        "pdf_bytes": pdf_bytes,
        "transcript_bytes": transcript_bytes,
        "total_bytes": total_bytes,
        "screenshot_str": format_bytes(screenshot_bytes),
        "pdf_str": format_bytes(pdf_bytes),
        "transcript_str": format_bytes(transcript_bytes),
        "total_str": format_bytes(total_bytes)
    }


def ensure_dir(path: Path | str) -> Path:
    """Ensures that a directory exists, creating all missing parents."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
