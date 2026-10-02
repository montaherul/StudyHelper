"""
Universal Media Downloader using yt-dlp & FFmpeg.
Supports video/audio downloads, clipping, and metadata extraction across:
- YouTube (Videos, Shorts, Playlists, Unlisted & Private via cookies)
- TikTok (Videos, Reels, Audio tracks)
- Instagram (Reels, Posts, Stories, IGTV)
- Facebook (Videos, Watch, Reels, Groups)
- X / Twitter (Videos, Clips, Broadcasts)
- Reddit (Videos with audio muxing)
- Vimeo, LinkedIn, Twitch, Bilibili, Dailymotion
- Direct Video Streams (MP4, WebM, HLS m3u8, DASH mpd)
- Universal Web Pages (HTML5 video scraping, embedded iframes)
"""

from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
import yt_dlp
import yt_dlp.utils

from core.job_manager import CancellationToken
from utils.filesystem import ensure_dir, sanitize_filename
from utils.logger import logger
from utils.time_utils import seconds_to_hms, parse_timestamp_str
from video.ffmpeg_finder import get_ffmpeg_path

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)


def find_default_cookies_file() -> Optional[Path]:
    """
    Searches for an existing cookies.txt file in standard locations:
    1. Workspace root: 'd:/OFFline study/cookies.txt'
    2. Current working directory
    3. User home LocalStudy configuration folder (~/.localstudy/cookies.txt)
    """
    candidates = [
        Path.cwd() / "cookies.txt",
        Path(__file__).resolve().parent.parent / "cookies.txt",
        Path.home() / ".localstudy" / "cookies.txt",
        Path.home() / "Downloads" / "cookies.txt",
    ]
    for p in candidates:
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            return p.resolve()
    return None


def detect_platform(url: str) -> Dict[str, Any]:
    """
    Analyzes any URL and auto-detects the host platform, icon, styling tag, and operational tip.
    Supports YouTube, TikTok, Instagram, Facebook, X/Twitter, Reddit, Vimeo, LinkedIn, Twitch,
    Bilibili, direct streams (.mp4, .m3u8, .mpd, etc.), and universal web portals.
    """
    url_lower = url.lower().strip()
    if not url_lower or not url_lower.startswith(("http://", "https://")):
        return {
            "platform": "unknown",
            "name": "Auto-Detecting",
            "icon": "🌐",
            "color": "#64748B",
            "tag": "All Media Platforms Supported",
            "tip": "Paste any video link: YouTube, TikTok, Instagram, Facebook, X/Twitter, Reddit, or web stream."
        }

    # 1. YouTube
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return {
            "platform": "youtube",
            "name": "YouTube",
            "icon": "🔴",
            "color": "#EF4444",
            "tag": "YouTube Video / Short",
            "tip": "Supports up to 4K 60fps merging, unlisted & private video access via cookies."
        }

    # 2. TikTok
    if "tiktok.com" in url_lower:
        return {
            "platform": "tiktok",
            "name": "TikTok",
            "icon": "🎵",
            "color": "#06B6D4",
            "tag": "TikTok Video / Reel",
            "tip": "Direct HD video and original audio extraction without compression."
        }

    # 3. Instagram
    if "instagram.com" in url_lower or "instagr.am" in url_lower:
        return {
            "platform": "instagram",
            "name": "Instagram",
            "icon": "📸",
            "color": "#E1306C",
            "tag": "Instagram Reel / Post",
            "tip": "Public reels download directly; private accounts require cookies.txt."
        }

    # 4. Facebook
    if "facebook.com" in url_lower or "fb.watch" in url_lower or "fb.com" in url_lower:
        return {
            "platform": "facebook",
            "name": "Facebook",
            "icon": "🔵",
            "color": "#1877F2",
            "tag": "Facebook Video / Watch",
            "tip": "High definition video & reel downloads; private groups require cookies.txt."
        }

    # 5. Twitter / X
    if "twitter.com" in url_lower or "x.com" in url_lower or "//t.co/" in url_lower or url_lower.startswith("https://t.co/"):
        return {
            "platform": "twitter",
            "name": "X (Twitter)",
            "icon": "🔲",
            "color": "#94A3B8",
            "tag": "X / Twitter Media",
            "tip": "Extracts highest available bitrate MP4 video stream from tweet."
        }

    # 6. Reddit
    if "reddit.com" in url_lower or "redd.it" in url_lower:
        return {
            "platform": "reddit",
            "name": "Reddit",
            "icon": "🟠",
            "color": "#FF4500",
            "tag": "Reddit Video Post",
            "tip": "Automatically merges separate Reddit video and audio streams into single MP4."
        }

    # 7. Vimeo
    if "vimeo.com" in url_lower:
        return {
            "platform": "vimeo",
            "name": "Vimeo",
            "icon": "🔷",
            "color": "#1AB7EA",
            "tag": "Vimeo Educational Stream",
            "tip": "Downloads master high-definition educational video stream."
        }

    # 8. LinkedIn
    if "linkedin.com" in url_lower:
        return {
            "platform": "linkedin",
            "name": "LinkedIn",
            "icon": "👔",
            "color": "#0A66C2",
            "tag": "LinkedIn Learning / Feed",
            "tip": "Course videos and educational feed streams."
        }

    # 9. Twitch
    if "twitch.tv" in url_lower:
        return {
            "platform": "twitch",
            "name": "Twitch",
            "icon": "🟣",
            "color": "#9146FF",
            "tag": "Twitch Broadcast / Clip",
            "tip": "Stream recordings, highlights, and clip downloads."
        }

    # 10. Bilibili
    if "bilibili.com" in url_lower or "b23.tv" in url_lower:
        return {
            "platform": "bilibili",
            "name": "Bilibili",
            "icon": "📺",
            "color": "#00A1D6",
            "tag": "Bilibili Tutorial",
            "tip": "High quality video and audio tutorials."
        }

    # 11. Direct Media Stream (MP4, HLS, DASH, etc.)
    direct_exts = [".mp4", ".m3u8", ".mpd", ".webm", ".mov", ".flv", ".m4v", ".avi"]
    if any(ext in url_lower for ext in direct_exts):
        return {
            "platform": "direct",
            "name": "Direct Stream",
            "icon": "⚡",
            "color": "#10B981",
            "tag": "Direct HLS / DASH / MP4 Link",
            "tip": "Direct video stream. FFmpeg merges segments automatically into MP4."
        }

    # 12. Universal Web Video Portal
    return {
        "platform": "generic",
        "name": "Web Media",
        "icon": "🌐",
        "color": "#38BDF8",
        "tag": "Universal Web Video",
        "tip": "Scrapes HTML5 video tags, embedded players, and CDN stream manifests."
    }


class VideoDownloader:
    """Extracts metadata and downloads videos/audio/clips from any video platform or web stream."""

    @staticmethod
    def get_info(
        url: str,
        cookies_path: Optional[Path | str] = None,
        cookies_browser: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetches detailed video metadata, platform info, and available streams without downloading.
        Works across YouTube, TikTok, Instagram, Facebook, X, Reddit, Vimeo, direct streams, etc.
        """
        ffmpeg_bin = get_ffmpeg_path()
        ffmpeg_dir = str(Path(ffmpeg_bin).parent) if Path(ffmpeg_bin).exists() else None

        ydl_opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
            "user_agent": DEFAULT_USER_AGENT,
            "nocheckcertificate": True,
            "socket_timeout": 30,
            "geo_bypass": True,
            "http_headers": {
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-Fetch-Mode": "navigate",
            },
        }

        if ffmpeg_dir:
            ydl_opts["ffmpeg_location"] = str(Path(ffmpeg_dir).resolve())

        # Resolve cookies
        resolved_cookies = cookies_path or find_default_cookies_file()
        if resolved_cookies and Path(resolved_cookies).exists():
            ydl_opts["cookiefile"] = str(Path(resolved_cookies).resolve())
        elif cookies_browser:
            ydl_opts["cookiesfrombrowser"] = (cookies_browser,)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                err_str = str(e)
                if "Private" in err_str or "Sign in" in err_str or "login" in err_str.lower() or "checkpoint" in err_str.lower():
                    raise RuntimeError(
                        f"Authentication required: This content is private, restricted, or requires login.\n"
                        f"Please provide your cookies.txt or select your browser above.\nDetails: {err_str}"
                    )
                raise RuntimeError(f"Could not retrieve video stream: {err_str}")

            if not info:
                raise ValueError("Could not extract video information from the provided URL.")

            duration = float(info.get("duration") or 0.0)
            formats_raw = info.get("formats", [])

            # Extract distinct resolution options
            available_resolutions = set()
            for f in formats_raw:
                h = f.get("height")
                if h and isinstance(h, int):
                    available_resolutions.add(h)
            sorted_res = sorted(list(available_resolutions), reverse=True)

            # Determine privacy badge
            availability = info.get("availability") or "public"
            if info.get("is_private"):
                availability = "private"
            elif info.get("is_unlisted") or info.get("view_count") is None:
                availability = "unlisted"

            title_val = info.get("title") or info.get("description") or "Untitled Media"
            if len(title_val) > 100:
                title_val = title_val[:100]

            uploader_val = (
                info.get("uploader")
                or info.get("channel")
                or info.get("creator")
                or info.get("uploader_id")
                or "Unknown Creator"
            )

            platform_meta = detect_platform(url)

            return {
                "id": info.get("id", ""),
                "title": title_val,
                "duration": duration,
                "duration_hms": seconds_to_hms(duration) if duration > 0 else "Live / Unknown",
                "uploader": uploader_val,
                "description": (info.get("description") or "")[:500],
                "thumbnail": info.get("thumbnail") or "",
                "view_count": info.get("view_count", 0),
                "url": url,
                "upload_date": info.get("upload_date", ""),
                "availability": availability,
                "available_resolutions": sorted_res,
                "cookies_used": bool(resolved_cookies or cookies_browser),
                "platform": platform_meta,
            }

    @staticmethod
    def download_media(
        url: str,
        output_dir: Path | str,
        filename_prefix: Optional[str] = None,
        mode: str = "video",                    # 'video', 'audio', 'clip'
        format_preset: str = "best_mp4",        # 'best_mp4', '1080p', '720p', '480p', '360p', 'best_mkv', 'mp3_320', 'mp3_192', 'm4a', 'wav', 'flac'
        container: str = "mp4",                 # 'mp4', 'mkv', 'webm', 'mp3', 'wav', 'm4a'
        start_time: Optional[float | str] = None,
        end_time: Optional[float | str] = None,
        cookies_path: Optional[Path | str] = None,
        cookies_browser: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cancel_token: Optional[CancellationToken] = None
    ) -> Path:
        """
        Downloads media across any platform (YouTube, TikTok, Instagram, Facebook, Web URLs).
        Supports format sorting, progressive MP4 fallback, audio extraction, and time range clipping.
        """
        out_dir = ensure_dir(output_dir)
        ffmpeg_bin = get_ffmpeg_path()
        ffmpeg_dir = str(Path(ffmpeg_bin).parent) if Path(ffmpeg_bin).exists() else None

        if cancel_token and cancel_token.is_cancelled():
            raise RuntimeError("Download cancelled before starting.")

        # Clean up any stale partial or temporary files in the directory
        try:
            for stale in out_dir.glob("*.temp.*"):
                if stale.is_file():
                    stale.unlink(missing_ok=True)
            for stale in out_dir.glob("*.part"):
                if stale.is_file() and (stale.stat().st_size == 0):
                    stale.unlink(missing_ok=True)
        except Exception:
            pass

        downloaded_file_path = [None]

        def progress_hook(d):
            if cancel_token and cancel_token.is_cancelled():
                raise RuntimeError("Download cancelled by user.")

            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                speed = d.get("speed") or 0
                pct = (downloaded / total * 100.0) if total > 0 else 0.0
                speed_mb = (speed / (1024 * 1024)) if speed else 0.0
                eta_str = d.get("_eta_str", "")

                downloaded_mb = downloaded / (1024 * 1024)
                total_mb = total / (1024 * 1024) if total > 0 else 0.0

                msg = f"Downloading: {pct:.1f}% ({speed_mb:.1f} MB/s) — {downloaded_mb:.1f}/{total_mb:.1f} MB"
                if eta_str:
                    msg += f" • ETA: {eta_str}"

                if progress_callback:
                    progress_callback(min(95.0, pct), msg)

            elif status == "finished":
                filename_res = d.get("filename")
                if filename_res and not (".temp" in filename_res or filename_res.endswith(".part")):
                    downloaded_file_path[0] = filename_res
                if progress_callback:
                    progress_callback(97.0, "Stream downloaded. Processing & merging with FFmpeg...")

        # Base output naming template
        is_clip = (mode == "clip")
        if filename_prefix:
            safe_prefix = sanitize_filename(filename_prefix)
            suffix = "_clip" if is_clip else ""
            out_tmpl = str(out_dir / f"{safe_prefix}{suffix}_%(title).60s.%(ext)s")
        else:
            suffix = "_clip" if is_clip else ""
            out_tmpl = str(out_dir / f"%(title).80s{suffix}.%(ext)s")

        ydl_opts: Dict[str, Any] = {
            "outtmpl": out_tmpl,
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
            "windowsfilenames": True,
            "overwrites": True,
            "user_agent": DEFAULT_USER_AGENT,
            "nocheckcertificate": True,
            "socket_timeout": 30,
            "geo_bypass": True,
            "http_headers": {
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-Fetch-Mode": "navigate",
            },
        }

        if ffmpeg_dir:
            ydl_opts["ffmpeg_location"] = str(Path(ffmpeg_dir).resolve())

        # Cookies configuration (Crucial for Instagram, Facebook, TikTok, private YouTube)
        resolved_cookies = cookies_path or find_default_cookies_file()
        if resolved_cookies and Path(resolved_cookies).exists():
            ydl_opts["cookiefile"] = str(Path(resolved_cookies).resolve())
            logger.info(f"Using cookies file: {resolved_cookies}")
        elif cookies_browser:
            ydl_opts["cookiesfrombrowser"] = (cookies_browser,)
            logger.info(f"Using cookies from browser: {cookies_browser}")

        # Configure Mode & Formats with universal multi-platform fallback
        target_container = container.lower() if container else "mp4"

        if mode == "audio":
            # Universal audio extraction (works on YouTube, TikTok, Instagram, FB, etc.)
            ydl_opts["format"] = "bestaudio/best"
            target_codec = "mp3"
            quality = "192"

            if format_preset == "mp3_320":
                target_codec = "mp3"
                quality = "320"
            elif format_preset == "mp3_192":
                target_codec = "mp3"
                quality = "192"
            elif format_preset in ("m4a", "aac"):
                target_codec = "m4a"
                quality = "0"
            elif format_preset == "wav":
                target_codec = "wav"
                quality = "0"
            elif format_preset == "flac":
                target_codec = "flac"
                quality = "0"

            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": target_codec,
                "preferredquality": quality,
            }]

        elif target_container == "webm":
            # WebM container with universal fallbacks
            ydl_opts["merge_output_format"] = "webm"
            ydl_opts["format_sort"] = ["ext:webm:webm", "res", "fps"]
            ydl_opts["format"] = "bv*[ext=webm]+ba[ext=webm]/bv*+ba[acodec^=opus]/best[ext=webm]/best/b"

        elif target_container == "mkv":
            # Matroska accepts any audio/video combination without transcoding
            ydl_opts["merge_output_format"] = "mkv"
            ydl_opts["format"] = "bv*+ba/best/b"

        else:
            # MP4 Mode (Default)
            # Universal format specification: handles separate DASH streams (YouTube)
            # as well as unified progressive MP4 streams (TikTok, Instagram, Facebook, Reddit, Direct links)
            ydl_opts["merge_output_format"] = "mp4"
            ydl_opts["format_sort"] = ["ext:mp4:m4a", "res", "fps"]

            if format_preset == "best_mp4":
                ydl_opts["format"] = "bv*[ext=mp4]+ba[ext=m4a]/bv*[ext=mp4]+ba/bv*+ba/best[ext=mp4]/best/b"
            elif format_preset in ("2160p", "4k"):
                ydl_opts["format"] = "bv*[height<=2160][ext=mp4]+ba[ext=m4a]/bv*[height<=2160]+ba/best[height<=2160][ext=mp4]/best[height<=2160]/best/b"
            elif format_preset in ("1440p", "2k"):
                ydl_opts["format"] = "bv*[height<=1440][ext=mp4]+ba[ext=m4a]/bv*[height<=1440]+ba/best[height<=1440][ext=mp4]/best[height<=1440]/best/b"
            elif format_preset == "1080p":
                ydl_opts["format"] = "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/best[height<=1080][ext=mp4]/best[height<=1080]/best/b"
            elif format_preset == "720p":
                ydl_opts["format"] = "bv*[height<=720][ext=mp4]+ba[ext=m4a]/bv*[height<=720]+ba/best[height<=720][ext=mp4]/best[height<=720]/best/b"
            elif format_preset == "480p":
                ydl_opts["format"] = "bv*[height<=480][ext=mp4]+ba[ext=m4a]/bv*[height<=480]+ba/best[height<=480][ext=mp4]/best[height<=480]/best/b"
            elif format_preset == "360p":
                ydl_opts["format"] = "bv*[height<=360][ext=mp4]+ba[ext=m4a]/bv*[height<=360]+ba/best[height<=360][ext=mp4]/best[height<=360]/best/b"
            else:
                ydl_opts["format"] = "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/best[ext=mp4]/best/b"

        # Clip / Short-term section slicing support
        start_sec = None
        end_sec = None
        if start_time is not None:
            start_sec = parse_timestamp_str(str(start_time)) if isinstance(start_time, str) else float(start_time)
        if end_time is not None:
            end_sec = parse_timestamp_str(str(end_time)) if isinstance(end_time, str) else float(end_time)

        if (start_sec is not None and start_sec > 0) or (end_sec is not None and end_sec > 0):
            s = start_sec if start_sec is not None else 0.0
            e = end_sec if end_sec is not None else float("inf")
            logger.info(f"Configuring download section range: {s}s -> {e}s")
            ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(s, e)])
            ydl_opts["force_keyframes_at_cuts"] = True

        if progress_callback:
            progress_callback(5.0, "Resolving video stream metadata across platform...")

        platform_info = detect_platform(url)
        logger.info(f"Starting download: Platform={platform_info['name']} URL={url} Mode={mode} Preset={format_preset}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res_code = ydl.download([url])
            if res_code != 0:
                raise RuntimeError(f"Download failed with exit code {res_code}")

        # Locate the downloaded file (Strictly ignoring temporary files)
        downloaded = downloaded_file_path[0]
        if downloaded and Path(downloaded).exists() and not (".temp" in Path(downloaded).name or Path(downloaded).name.endswith(".part")):
            final_path = Path(downloaded)
        else:
            # Check potential extensions based on mode, excluding .temp and .part
            ext_candidates = ["*.mp4", "*.mkv", "*.webm", "*.mp3", "*.m4a", "*.wav", "*.flac"]
            found = []
            for ext in ext_candidates:
                for f in out_dir.glob(ext):
                    if not (f.name.endswith(".temp") or ".temp." in f.name or f.name.endswith(".part") or f.name.endswith(".ytdl")):
                        found.append(f)
            candidates = sorted(found, key=lambda f: f.stat().st_mtime, reverse=True)
            if candidates:
                final_path = candidates[0]
            else:
                raise FileNotFoundError(f"Could not locate completed downloaded file in {out_dir}")

        if progress_callback:
            progress_callback(100.0, f"Downloaded: {final_path.name}")

        try:
            logger.info(f"Media successfully downloaded: {final_path} ({final_path.stat().st_size} bytes)")
        except Exception:
            pass

        return final_path

    @staticmethod
    def download_video(
        url: str,
        output_dir: Path | str,
        filename_prefix: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cancel_token: Optional[CancellationToken] = None,
        cookies_path: Optional[Path | str] = None
    ) -> Path:
        """
        Backwards-compatible video download interface.
        Applies optimal MP4 sorting (-S ext:mp4:m4a -f "bv*+ba/b") and automatic cookie resolution.
        """
        return VideoDownloader.download_media(
            url=url,
            output_dir=output_dir,
            filename_prefix=filename_prefix,
            mode="video",
            format_preset="best_mp4",
            container="mp4",
            cookies_path=cookies_path,
            progress_callback=progress_callback,
            cancel_token=cancel_token
        )


video_downloader = VideoDownloader()
