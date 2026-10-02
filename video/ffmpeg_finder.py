"""
FFmpeg and ffprobe binary resolver for LocalStudy.
Discovers and configures bundled static binaries from imageio-ffmpeg or system PATH,
guaranteeing an exact ffmpeg.exe binary and setting PATH for external tools (e.g. yt-dlp).
"""

import os
import shutil
from pathlib import Path
from typing import Optional

from utils.logger import logger


class FFmpegResolver:
    """Discovers, normalizes, and resolves the active FFmpeg binary."""

    _cached_ffmpeg: Optional[str] = None

    @classmethod
    def get_ffmpeg_executable(cls) -> str:
        """Returns path to a working ffmpeg binary and ensures PATH environment is populated."""
        if cls._cached_ffmpeg and Path(cls._cached_ffmpeg).exists():
            return cls._cached_ffmpeg

        # 1. Check local workspace bin/ffmpeg.exe
        workspace_bin = Path("bin/ffmpeg.exe").resolve()
        if workspace_bin.exists():
            cls._register_ffmpeg(str(workspace_bin))
            return str(workspace_bin)

        # 2. Check bundled imageio-ffmpeg
        try:
            import imageio_ffmpeg
            raw_exe = Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve()
            if raw_exe.exists():
                # Ensure an actual 'ffmpeg.exe' exists in the same directory for tools like yt-dlp
                bin_dir = raw_exe.parent
                standard_exe = bin_dir / "ffmpeg.exe"
                if not standard_exe.exists():
                    try:
                        shutil.copy2(raw_exe, standard_exe)
                        logger.info(f"Created standard ffmpeg.exe at {standard_exe}")
                    except Exception as copy_err:
                        logger.debug(f"Could not copy ffmpeg.exe in site-packages: {copy_err}")

                target = standard_exe if standard_exe.exists() else raw_exe
                cls._register_ffmpeg(str(target))
                return str(target)
        except Exception as e:
            logger.debug(f"imageio-ffmpeg resolver notice: {e}")

        # 3. Check system PATH
        path_exe = shutil.which("ffmpeg")
        if path_exe:
            cls._register_ffmpeg(path_exe)
            return path_exe

        # 4. Check common fallback locations
        candidates = [
            Path.home() / ".localstudy" / "bin" / "ffmpeg.exe",
            Path("C:/ffmpeg/bin/ffmpeg.exe")
        ]
        for c in candidates:
            if c.exists():
                resolved = str(c.resolve())
                cls._register_ffmpeg(resolved)
                return resolved

        logger.warning("No FFmpeg executable could be resolved!")
        return "ffmpeg"

    @classmethod
    def _register_ffmpeg(cls, exe_path: str) -> None:
        cls._cached_ffmpeg = exe_path
        bin_dir = str(Path(exe_path).parent.resolve())
        # Prepend to PATH so subprocesses, yt-dlp, and C extensions find it natively
        current_path = os.environ.get("PATH", "")
        if bin_dir not in current_path.split(os.pathsep):
            os.environ["PATH"] = bin_dir + os.pathsep + current_path
            logger.info(f"Added FFmpeg directory to PATH: {bin_dir}")


def get_ffmpeg_path() -> str:
    return FFmpegResolver.get_ffmpeg_executable()
