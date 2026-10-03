"""
Compatibility patch for PyAV 14+ with faster-whisper.
PyAV 14.0+ removed the 'metadata_errors' keyword argument from av.open().
This module intercepts and strips 'metadata_errors' so faster-whisper decodes audio flawlessly.
Safe for serverless environments where av or faster-whisper are not installed.
"""

import sys

# 1. In-memory monkey patch
try:
    import av
    _orig_av_open = av.open

    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)

    av.open = _safe_av_open
except Exception:
    pass


# 2. On-disk patch for site-packages faster_whisper/audio.py if accessible
def apply_disk_patch():
    try:
        import faster_whisper.audio as fa
        import inspect
        from pathlib import Path

        audio_file = Path(inspect.getfile(fa)).resolve()
        if audio_file.exists():
            content = audio_file.read_text(encoding="utf-8")
            target = 'metadata_errors="ignore"'
            if target in content:
                content = content.replace(', metadata_errors="ignore"', "")
                content = content.replace('metadata_errors="ignore"', "")
                audio_file.write_text(content, encoding="utf-8")
    except Exception:
        pass


apply_disk_patch()
