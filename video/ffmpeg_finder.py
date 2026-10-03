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
                # Ensure an actual 'ffmpeg' or 'ffmpeg.exe' exists in the same directory for tools like yt-dlp
                bin_dir = raw_exe.parent
                exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
                standard_exe = bin_dir / exe_name
                if not standard_exe.exists():
                    try:
                        shutil.copy2(raw_exe, standard_exe)
                        if os.name != "nt":
                            import stat
                            os.chmod(standard_exe, os.stat(standard_exe).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
                        logger.info(f"Created standard {exe_name} at {standard_exe}")
                    except Exception as copy_err:
                        logger.debug(f"Could not copy {exe_name} in site-packages (likely read-only serverless): {copy_err}")
                        # Fallback: Copy to writable temp directory (/tmp/localstudy_bin/ffmpeg)
                        try:
                            import tempfile
                            import stat
                            tmp_bin = Path(tempfile.gettempdir()) / "localstudy_bin"
                            tmp_bin.mkdir(parents=True, exist_ok=True)
                            tmp_exe = tmp_bin / exe_name
                            if not tmp_exe.exists():
                                shutil.copy2(raw_exe, tmp_exe)
                                if os.name != "nt":
                                    os.chmod(tmp_exe, os.stat(tmp_exe).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
                            cls._register_ffmpeg(str(tmp_exe))
                            return str(tmp_exe)
                        except Exception as tmp_err:
                            logger.debug(f"Could not copy {exe_name} to temp dir: {tmp_err}")

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
