"""
Dedicated Video & Audio Downloader View for LocalStudy.
Enables offline study preparation from public, unlisted, and private/authenticated YouTube & web URLs.

Features:
- Format sorting: yt-dlp -S ext:mp4:m4a -f "bv*+ba/b"
- Video download in any resolution (4K, 1440p, 1080p, 720p, 480p, 360p)
- Audio extraction (MP3 320k/192k, M4A, WAV, FLAC)
- Short-term video section / time range clipping (start_time to end_time)
- Cookies authentication for unlisted, private, age-restricted, and member-only lectures
- Direct one-click export to Screenshot Extractor and Audio Transcriber
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.request import urlopen, Request

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QFileDialog, QComboBox, QCheckBox, QProgressBar,
    QMessageBox, QRadioButton, QButtonGroup, QGridLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QScrollArea
)

from core.job_manager import CancellationToken
from core.project_manager import project_manager
from database.db import db
from utils.filesystem import format_file_size, sanitize_filename
from utils.logger import logger
from utils.time_utils import seconds_to_hms, parse_timestamp_str
from video.downloader import video_downloader, find_default_cookies_file, detect_platform


class FetchInfoWorkerThread(QThread):
    """Fetches video metadata & available streams without blocking the UI."""
    info_fetched = Signal(bool, dict, str)

    def __init__(self, url: str, cookies_path: Optional[str] = None, cookies_browser: Optional[str] = None):
        super().__init__()
        self.url = url
        self.cookies_path = cookies_path
        self.cookies_browser = cookies_browser

    def run(self):
        try:
            info = video_downloader.get_info(
                url=self.url,
                cookies_path=self.cookies_path,
                cookies_browser=self.cookies_browser
            )
            self.info_fetched.emit(True, info, "")
        except Exception as e:
            self.info_fetched.emit(False, {}, str(e))


class DownloadWorkerThread(QThread):
    """Executes media download, audio extraction, or clipping in the background."""
    progress_updated = Signal(float, str)
    download_finished = Signal(bool, str, dict, str)  # success, file_path, meta, error

    def __init__(
        self,
        url: str,
        output_dir: Path | str,
        filename_prefix: Optional[str],
        mode: str,
        format_preset: str,
        container: str,
        start_time: Optional[str],
        end_time: Optional[str],
        cookies_path: Optional[str],
        cookies_browser: Optional[str],
        cancel_token: CancellationToken,
        video_meta: Optional[dict] = None
    ):
        super().__init__()
        self.url = url
        self.output_dir = output_dir
        self.filename_prefix = filename_prefix
        self.mode = mode
        self.format_preset = format_preset
        self.container = container
        self.start_time = start_time
        self.end_time = end_time
        self.cookies_path = cookies_path
        self.cookies_browser = cookies_browser
        self.cancel_token = cancel_token
        self.video_meta = video_meta or {}

    def run(self):
        try:
            file_path = video_downloader.download_media(
                url=self.url,
                output_dir=self.output_dir,
                filename_prefix=self.filename_prefix,
                mode=self.mode,
                format_preset=self.format_preset,
                container=self.container,
                start_time=self.start_time,
                end_time=self.end_time,
                cookies_path=self.cookies_path,
                cookies_browser=self.cookies_browser,
                progress_callback=lambda pct, msg: self.progress_updated.emit(pct, msg),
                cancel_token=self.cancel_token
            )
            self.download_finished.emit(True, str(file_path), self.video_meta, "")
        except Exception as e:
            self.download_finished.emit(False, "", {}, str(e))


class VideoDownloaderView(QWidget):
    """Dedicated UI View for downloading YouTube & Web video/audio/clips with cookies authentication."""

    # Navigation signals to bridge with Screenshot and Transcriber views
    send_to_screenshots = Signal(str)
    send_to_transcriber = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_meta: Optional[Dict[str, Any]] = None
        self.last_downloaded_file: Optional[Path] = None
        self.info_thread: Optional[FetchInfoWorkerThread] = None
        self.download_thread: Optional[DownloadWorkerThread] = None
        self.cancel_token = CancellationToken()
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scrollable container for flexible responsive layouts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # 1. Header Banner
        header_box = QVBoxLayout()
        h_lbl = QLabel("🎬  Media & Lecture Downloader")
        h_lbl.setStyleSheet("font-size: 20px; font-weight: 700; color: #F8FAFC;")
        s_lbl = QLabel(
            "Download YouTube & educational videos in any format (MP4, MKV, MP3, WAV), "
            "extract short video clips, and authenticate with cookies for private & unlisted content."
        )
        s_lbl.setStyleSheet("color: #94A3B8; font-size: 13px;")
        header_box.addWidget(h_lbl)
        header_box.addWidget(s_lbl)
        layout.addLayout(header_box)

        # 2. URL Input & Probing Card
        url_card = QFrame()
        url_card.setProperty("class", "CardFrame")
        url_layout = QVBoxLayout(url_card)
        url_layout.setSpacing(10)

        # Supported Platform Quick Chips
        chips_header = QHBoxLayout()
        chips_title = QLabel("Supported Platforms:")
        chips_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B;")
        chips_header.addWidget(chips_title)

        for p_name, p_icon in [
            ("YouTube", "🔴"), ("TikTok", "🎵"), ("Instagram", "📸"),
            ("Facebook", "🔵"), ("X / Twitter", "🔲"), ("Reddit", "🟠"),
            ("Vimeo", "🔷"), ("Direct Streams", "⚡")
        ]:
            chip = QLabel(f"{p_icon} {p_name}")
            chip.setStyleSheet(
                "background-color: #0B1120; color: #94A3B8; font-size: 10px; font-weight: 600; "
                "border-radius: 4px; padding: 2px 7px; border: 1px solid #1E293B;"
            )
            chips_header.addWidget(chip)
        chips_header.addStretch()
        url_layout.addLayout(chips_header)

        # Title row with live platform auto-detection badge
        title_row = QHBoxLayout()
        url_title = QLabel("Video, Reel, or Web Stream URL")
        url_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #E2E8F0;")
        title_row.addWidget(url_title)
        title_row.addStretch()

        self.lbl_platform_badge = QLabel("🌐  Auto-Detecting Any Platform")
        self.lbl_platform_badge.setStyleSheet(
            "background-color: #0F172A; color: #38BDF8; font-size: 11px; font-weight: 700; "
            "border-radius: 4px; padding: 3px 9px; border: 1px solid #0284C7;"
        )
        title_row.addWidget(self.lbl_platform_badge)
        url_layout.addLayout(title_row)

        input_row = QHBoxLayout()
        self.in_url = QLineEdit()
        self.in_url.setPlaceholderText("Paste YouTube, TikTok, Instagram, Facebook, X, Reddit, or any video link...")
        self.in_url.textChanged.connect(self._on_url_text_changed)
        self.in_url.returnPressed.connect(self._fetch_info)

        self.btn_paste = QPushButton("📋 Paste")
        self.btn_paste.setProperty("class", "SecondaryBtn")
        self.btn_paste.clicked.connect(self._paste_clipboard)

        self.btn_inspect = QPushButton("🔍 Inspect Stream")
        self.btn_inspect.setProperty("class", "PrimaryBtn")
        self.btn_inspect.clicked.connect(self._fetch_info)

        input_row.addWidget(self.in_url, stretch=1)
        input_row.addWidget(self.btn_paste)
        input_row.addWidget(self.btn_inspect)
        url_layout.addLayout(input_row)

        self.lbl_probe_status = QLabel("Enter a URL and click 'Inspect Stream' to probe formats and metadata.")
        self.lbl_probe_status.setStyleSheet("color: #64748B; font-size: 12px;")
        url_layout.addWidget(self.lbl_probe_status)
        layout.addWidget(url_card)

        # 3. Video Metadata & Preview Card (Initially hidden)
        self.preview_card = QFrame()
        self.preview_card.setProperty("class", "CardFrame")
        self.preview_card.setStyleSheet("background-color: #1E293B; border: 1px solid #38BDF8; border-radius: 8px; padding: 12px;")
        self.preview_card.setVisible(False)
        prev_layout = QHBoxLayout(self.preview_card)
        prev_layout.setSpacing(16)

        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(160, 90)
        self.lbl_thumb.setStyleSheet("background-color: #0F172A; border-radius: 4px;")
        self.lbl_thumb.setAlignment(Qt.AlignCenter)
        prev_layout.addWidget(self.lbl_thumb)

        meta_vbox = QVBoxLayout()
        self.lbl_meta_title = QLabel("Title")
        self.lbl_meta_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #FFFFFF;")
        self.lbl_meta_title.setWordWrap(True)

        meta_badges = QHBoxLayout()
        self.lbl_meta_platform = QLabel("🔴 YouTube")
        self.lbl_meta_platform.setStyleSheet(
            "background-color: #0369A1; color: #FFFFFF; font-size: 11px; font-weight: 700; "
            "border-radius: 3px; padding: 2px 7px;"
        )

        self.lbl_meta_channel = QLabel("Channel: Unknown")
        self.lbl_meta_channel.setStyleSheet("color: #94A3B8; font-size: 12px;")

        self.lbl_meta_duration = QLabel("⏳ 00:00:00")
        self.lbl_meta_duration.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600;")

        self.lbl_meta_privacy = QLabel("🟢 Public")
        self.lbl_meta_privacy.setStyleSheet("color: #34D399; font-size: 12px; font-weight: 600;")

        meta_badges.addWidget(self.lbl_meta_platform)
        meta_badges.addWidget(QLabel("•"))
        meta_badges.addWidget(self.lbl_meta_channel)
        meta_badges.addWidget(QLabel("•"))
        meta_badges.addWidget(self.lbl_meta_duration)
        meta_badges.addWidget(QLabel("•"))
        meta_badges.addWidget(self.lbl_meta_privacy)
        meta_badges.addStretch()

        meta_vbox.addWidget(self.lbl_meta_title)
        meta_vbox.addLayout(meta_badges)
        prev_layout.addLayout(meta_vbox, stretch=1)
        layout.addWidget(self.preview_card)

        # 4. Authentication / Cookies Configuration Card
        auth_card = QFrame()
        auth_card.setProperty("class", "CardFrame")
        auth_layout = QVBoxLayout(auth_card)
        auth_layout.setSpacing(10)

        auth_header = QHBoxLayout()
        self.chk_use_cookies = QCheckBox("🔑 Enable Authentication Cookies (For Unlisted, Private & Members-Only Videos)")
        self.chk_use_cookies.setStyleSheet("font-weight: 600; color: #F1F5F9; font-size: 13px;")
        self.chk_use_cookies.setChecked(True)
        self.chk_use_cookies.toggled.connect(self._on_cookies_toggled)

        self.lbl_cookies_status = QLabel("")
        self.lbl_cookies_status.setStyleSheet("font-size: 11px; font-weight: 600;")

        auth_header.addWidget(self.chk_use_cookies)
        auth_header.addStretch()
        auth_header.addWidget(self.lbl_cookies_status)
        auth_layout.addLayout(auth_header)

        # Cookies input container
        self.cookies_container = QWidget()
        c_layout = QVBoxLayout(self.cookies_container)
        c_layout.setContentsMargins(0, 4, 0, 0)
        c_layout.setSpacing(8)

        cookie_type_box = QHBoxLayout()
        self.radio_cookie_file = QRadioButton("Use cookies.txt file")
        self.radio_cookie_browser = QRadioButton("Extract from Browser")
        self.radio_cookie_file.setChecked(True)

        self.btn_group_cookie = QButtonGroup(self)
        self.btn_group_cookie.addButton(self.radio_cookie_file)
        self.btn_group_cookie.addButton(self.radio_cookie_browser)
        self.radio_cookie_file.toggled.connect(self._on_cookie_method_toggled)

        cookie_type_box.addWidget(self.radio_cookie_file)
        cookie_type_box.addWidget(self.radio_cookie_browser)
        cookie_type_box.addStretch()
        c_layout.addLayout(cookie_type_box)

        # File path row
        self.cookie_file_row = QHBoxLayout()
        self.in_cookie_path = QLineEdit()
        self.in_cookie_path.setPlaceholderText("Path to cookies.txt (Netscape format)...")
        self.in_cookie_path.textChanged.connect(self._verify_cookies_file)

        self.btn_browse_cookie = QPushButton("Browse...")
        self.btn_browse_cookie.setProperty("class", "SecondaryBtn")
        self.btn_browse_cookie.clicked.connect(self._browse_cookies_file)

        self.btn_autodetect_cookie = QPushButton("🔄 Auto-Detect")
        self.btn_autodetect_cookie.setProperty("class", "SecondaryBtn")
        self.btn_autodetect_cookie.clicked.connect(self._autodetect_cookies)

        self.cookie_file_row.addWidget(self.in_cookie_path, stretch=1)
        self.cookie_file_row.addWidget(self.btn_browse_cookie)
        self.cookie_file_row.addWidget(self.btn_autodetect_cookie)
        c_layout.addLayout(self.cookie_file_row)

        # Browser selector row
        self.cookie_browser_row = QHBoxLayout()
        self.cookie_browser_row.addWidget(QLabel("Browser Profile:"))
        self.combo_browser = QComboBox()
        self.combo_browser.addItems(["chrome", "edge", "firefox", "brave", "opera", "vivaldi"])
        self.cookie_browser_row.addWidget(self.combo_browser)
        self.cookie_browser_row.addStretch()
        c_layout.addLayout(self.cookie_browser_row)
        self.cookie_browser_row.setEnabled(False)

        auth_layout.addWidget(self.cookies_container)
        layout.addWidget(auth_card)

        # 5. Download Configuration Tabs (Video / Audio / Clip)
        config_card = QFrame()
        config_card.setProperty("class", "CardFrame")
        cfg_layout = QVBoxLayout(config_card)
        cfg_layout.setSpacing(12)

        cfg_title = QLabel("Download Format & Extraction Mode")
        cfg_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #E2E8F0;")
        cfg_layout.addWidget(cfg_title)

        self.tabs_mode = QTabWidget()
        self.tabs_mode.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #334155; border-radius: 6px; background-color: #0F172A; }
            QTabBar::tab { background: #1E293B; color: #94A3B8; padding: 8px 18px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; }
            QTabBar::tab:selected { background: #0284C7; color: #FFFFFF; font-weight: 600; }
        """)

        # Tab A: Video Download
        tab_video = QWidget()
        v_layout = QGridLayout(tab_video)
        v_layout.setContentsMargins(14, 14, 14, 14)
        v_layout.setSpacing(10)

        v_layout.addWidget(QLabel("Resolution / Preset:"), 0, 0)
        self.combo_video_res = QComboBox()
        self.combo_video_res.addItem("Best MP4 (bv*+ba/b -S ext:mp4:m4a) [Recommended]", "best_mp4")
        self.combo_video_res.addItem("4K Ultra HD (2160p)", "2160p")
        self.combo_video_res.addItem("1440p Quad HD (2K)", "1440p")
        self.combo_video_res.addItem("1080p Full HD (Great for slides)", "1080p")
        self.combo_video_res.addItem("720p HD (Balanced speed/quality)", "720p")
        self.combo_video_res.addItem("480p SD (Data saver)", "480p")
        self.combo_video_res.addItem("360p Low (Minimal bandwidth)", "360p")
        self.combo_video_res.addItem("Best MKV Container", "best_mkv")
        v_layout.addWidget(self.combo_video_res, 0, 1)

        v_layout.addWidget(QLabel("Container Format:"), 1, 0)
        self.combo_video_container = QComboBox()
        self.combo_video_container.addItems(["mp4", "mkv", "webm"])
        v_layout.addWidget(self.combo_video_container, 1, 1)

        self.tabs_mode.addTab(tab_video, "📹 Full Video")

        # Tab B: Audio Only
        tab_audio = QWidget()
        a_layout = QGridLayout(tab_audio)
        a_layout.setContentsMargins(14, 14, 14, 14)
        a_layout.setSpacing(10)

        a_layout.addWidget(QLabel("Audio Format & Quality:"), 0, 0)
        self.combo_audio_preset = QComboBox()
        self.combo_audio_preset.addItem("MP3 — 320 kbps (Extreme Quality)", "mp3_320")
        self.combo_audio_preset.addItem("MP3 — 192 kbps (Standard Study)", "mp3_192")
        self.combo_audio_preset.addItem("M4A / AAC — Native Audio Stream", "m4a")
        self.combo_audio_preset.addItem("WAV — Lossless 16-bit (Zero latency for STT)", "wav")
        self.combo_audio_preset.addItem("FLAC — Lossless Archive", "flac")
        a_layout.addWidget(self.combo_audio_preset, 0, 1)

        self.tabs_mode.addTab(tab_audio, "🎵 Audio Only")

        # Tab C: Short-term Clip / Section
        tab_clip = QWidget()
        c_grid = QGridLayout(tab_clip)
        c_grid.setContentsMargins(14, 14, 14, 14)
        c_grid.setSpacing(10)

        c_grid.addWidget(QLabel("Start Timestamp:"), 0, 0)
        self.in_clip_start = QLineEdit("00:00:00")
        self.in_clip_start.setPlaceholderText("HH:MM:SS or seconds (e.g. 00:01:30)")
        self.in_clip_start.textChanged.connect(self._update_clip_calc)
        c_grid.addWidget(self.in_clip_start, 0, 1)

        c_grid.addWidget(QLabel("End Timestamp:"), 1, 0)
        self.in_clip_end = QLineEdit("00:05:00")
        self.in_clip_end.setPlaceholderText("HH:MM:SS or seconds (e.g. 00:06:00)")
        self.in_clip_end.textChanged.connect(self._update_clip_calc)
        c_grid.addWidget(self.in_clip_end, 1, 1)

        c_grid.addWidget(QLabel("Clip Media Type:"), 2, 0)
        self.combo_clip_type = QComboBox()
        self.combo_clip_type.addItem("Video Clip (MP4)", "video")
        self.combo_clip_type.addItem("Audio Clip (MP3)", "audio")
        c_grid.addWidget(self.combo_clip_type, 2, 1)

        self.lbl_clip_duration = QLabel("Selected Duration: 00:05:00")
        self.lbl_clip_duration.setStyleSheet("color: #38BDF8; font-weight: 600; font-size: 12px;")
        c_grid.addWidget(self.lbl_clip_duration, 3, 1)

        # Quick preset buttons
        quick_row = QHBoxLayout()
        btn_q1 = QPushButton("First 5 Mins")
        btn_q1.setProperty("class", "SecondaryBtn")
        btn_q1.clicked.connect(lambda: self._set_clip_range("00:00:00", "00:05:00"))

        btn_q2 = QPushButton("First 15 Mins")
        btn_q2.setProperty("class", "SecondaryBtn")
        btn_q2.clicked.connect(lambda: self._set_clip_range("00:00:00", "00:15:00"))

        btn_q3 = QPushButton("Reset to Full")
        btn_q3.setProperty("class", "SecondaryBtn")
        btn_q3.clicked.connect(lambda: self._set_clip_range("00:00:00", ""))

        quick_row.addWidget(btn_q1)
        quick_row.addWidget(btn_q2)
        quick_row.addWidget(btn_q3)
        quick_row.addStretch()
        c_grid.addLayout(quick_row, 4, 1)

        self.tabs_mode.addTab(tab_clip, "✂️ Short-term Clip")
        cfg_layout.addWidget(self.tabs_mode)
        layout.addWidget(config_card)

        # 6. Destination & Project Binding Card
        dest_card = QFrame()
        dest_card.setProperty("class", "CardFrame")
        d_layout = QGridLayout(dest_card)
        d_layout.setSpacing(10)

        d_layout.addWidget(QLabel("Save Location:"), 0, 0)
        dest_type_box = QHBoxLayout()
        self.radio_dest_project = QRadioButton("Save to Study Project")
        self.radio_dest_custom = QRadioButton("Custom Folder")
        self.radio_dest_project.setChecked(True)

        self.btn_group_dest = QButtonGroup(self)
        self.btn_group_dest.addButton(self.radio_dest_project)
        self.btn_group_dest.addButton(self.radio_dest_custom)
        self.radio_dest_project.toggled.connect(self._on_dest_type_toggled)

        dest_type_box.addWidget(self.radio_dest_project)
        dest_type_box.addWidget(self.radio_dest_custom)
        dest_type_box.addStretch()
        d_layout.addLayout(dest_type_box, 0, 1)

        # Project dropdown row
        d_layout.addWidget(QLabel("Target Project:"), 1, 0)
        proj_box = QHBoxLayout()
        self.combo_project = QComboBox()
        self.combo_project.currentIndexChanged.connect(self._on_project_changed)

        self.btn_refresh_proj = QPushButton("🔄")
        self.btn_refresh_proj.setFixedWidth(36)
        self.btn_refresh_proj.clicked.connect(self.refresh)

        proj_box.addWidget(self.combo_project, stretch=1)
        proj_box.addWidget(self.btn_refresh_proj)
        d_layout.addLayout(proj_box, 1, 1)

        # Custom folder row
        d_layout.addWidget(QLabel("Directory Path:"), 2, 0)
        cust_box = QHBoxLayout()
        self.in_custom_dir = QLineEdit()
        self.in_custom_dir.setText(str(Path.home() / "Downloads"))

        self.btn_browse_dest = QPushButton("Browse...")
        self.btn_browse_dest.setProperty("class", "SecondaryBtn")
        self.btn_browse_dest.clicked.connect(self._browse_custom_dest)

        cust_box.addWidget(self.in_custom_dir, stretch=1)
        cust_box.addWidget(self.btn_browse_dest)
        d_layout.addLayout(cust_box, 2, 1)

        layout.addWidget(dest_card)

        # 7. Action & Progress Card
        action_card = QFrame()
        action_card.setProperty("class", "CardFrame")
        act_layout = QVBoxLayout(action_card)
        act_layout.setSpacing(10)

        btn_row = QHBoxLayout()
        self.btn_download = QPushButton("⬇️  Start Download")
        self.btn_download.setProperty("class", "PrimaryBtn")
        self.btn_download.setStyleSheet("font-size: 15px; font-weight: 700; padding: 12px 24px;")
        self.btn_download.clicked.connect(self._start_download)

        self.btn_cancel = QPushButton("⛔ Cancel")
        self.btn_cancel.setProperty("class", "DangerBtn")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._cancel_download)

        btn_row.addWidget(self.btn_download, stretch=1)
        btn_row.addWidget(self.btn_cancel)
        act_layout.addLayout(btn_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        act_layout.addWidget(self.progress_bar)

        self.lbl_progress_msg = QLabel("")
        self.lbl_progress_msg.setStyleSheet("color: #94A3B8; font-size: 12px;")
        self.lbl_progress_msg.setVisible(False)
        act_layout.addWidget(self.lbl_progress_msg)
        layout.addWidget(action_card)

        # 8. Post-Download Hub (Appears upon download completion)
        self.hub_card = QFrame()
        self.hub_card.setProperty("class", "CardFrame")
        self.hub_card.setStyleSheet("background-color: #064E3B; border: 1px solid #10B981; border-radius: 8px; padding: 14px;")
        self.hub_card.setVisible(False)
        hub_layout = QVBoxLayout(self.hub_card)

        self.lbl_hub_status = QLabel("🎉 Download Finished Successfully!")
        self.lbl_hub_status.setStyleSheet("font-size: 14px; font-weight: 700; color: #6EE7B7;")
        hub_layout.addWidget(self.lbl_hub_status)

        hub_btns = QHBoxLayout()
        self.btn_hub_ss = QPushButton("📷 Send to Screenshot Extractor")
        self.btn_hub_ss.setProperty("class", "PrimaryBtn")
        self.btn_hub_ss.clicked.connect(self._on_send_to_screenshots)

        self.btn_hub_stt = QPushButton("🎙️ Send to Audio Transcriber")
        self.btn_hub_stt.setProperty("class", "PrimaryBtn")
        self.btn_hub_stt.clicked.connect(self._on_send_to_transcriber)

        self.btn_hub_open = QPushButton("📂 Open Folder")
        self.btn_hub_open.setProperty("class", "SecondaryBtn")
        self.btn_hub_open.clicked.connect(self._open_downloaded_folder)

        self.btn_hub_play = QPushButton("▶️ Play Media")
        self.btn_hub_play.setProperty("class", "SecondaryBtn")
        self.btn_hub_play.clicked.connect(self._play_media)

        hub_btns.addWidget(self.btn_hub_ss)
        hub_btns.addWidget(self.btn_hub_stt)
        hub_btns.addWidget(self.btn_hub_open)
        hub_btns.addWidget(self.btn_hub_play)
        hub_layout.addLayout(hub_btns)
        layout.addWidget(self.hub_card)

        # 9. Recent Downloads Table
        hist_card = QFrame()
        hist_card.setProperty("class", "CardFrame")
        h_layout = QVBoxLayout(hist_card)
        h_layout.setSpacing(10)

        hist_title = QLabel("Recent Downloaded Media")
        hist_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #E2E8F0;")
        h_layout.addWidget(hist_title)

        self.table_history = QTableWidget()
        self.table_history.setColumnCount(6)
        self.table_history.setHorizontalHeaderLabels(["Title", "Type", "Format", "Size", "Duration", "Actions"])
        self.table_history.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_history.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_history.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_history.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_history.setMinimumHeight(160)
        h_layout.addWidget(self.table_history)
        layout.addWidget(hist_card)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Initial cookies auto-detect
        self._autodetect_cookies()

    # --- UI Events & Helpers ---

    def refresh(self):
        """Refreshes project list and download history."""
        curr_id = self.combo_project.currentData()
        self.combo_project.blockSignals(True)
        self.combo_project.clear()

        projects = project_manager.list_all_projects()
        for p in projects:
            self.combo_project.addItem(f"📁 {p.name}", p.id)

        if curr_id:
            idx = self.combo_project.findData(curr_id)
            if idx >= 0:
                self.combo_project.setCurrentIndex(idx)

        self.combo_project.blockSignals(False)
        self._on_dest_type_toggled()
        self._load_history()

    def set_active_project(self, project_id: str):
        """Sets the active project in the destination dropdown."""
        self.refresh()
        idx = self.combo_project.findData(project_id)
        if idx >= 0:
            self.combo_project.setCurrentIndex(idx)

    def _autodetect_cookies(self):
        """Automatically checks for cookies.txt in workspace, home, or downloads."""
        found = find_default_cookies_file()
        if found:
            self.in_cookie_path.setText(str(found))
            self._verify_cookies_file(str(found))
        else:
            self.lbl_cookies_status.setText("⚪ No cookies.txt found (Public videos only)")
            self.lbl_cookies_status.setStyleSheet("color: #94A3B8; font-size: 11px;")

    def _verify_cookies_file(self, path_str: str):
        p = Path(path_str)
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            size_kb = p.stat().st_size / 1024.0
            self.lbl_cookies_status.setText(f"🟢 cookies.txt Active ({size_kb:.1f} KB)")
            self.lbl_cookies_status.setStyleSheet("color: #34D399; font-size: 11px; font-weight: 600;")
        else:
            self.lbl_cookies_status.setText("⚪ No valid cookies file loaded")
            self.lbl_cookies_status.setStyleSheet("color: #94A3B8; font-size: 11px;")

    def _paste_clipboard(self):
        from PySide6.QtWidgets import QApplication
        text = QApplication.clipboard().text().strip()
        if text:
            self.in_url.setText(text)
            self._fetch_info()

    def _on_cookies_toggled(self, checked: bool):
        self.cookies_container.setEnabled(checked)

    def _on_cookie_method_toggled(self):
        is_file = self.radio_cookie_file.isChecked()
        self.in_cookie_path.setEnabled(is_file)
        self.btn_browse_cookie.setEnabled(is_file)
        self.btn_autodetect_cookie.setEnabled(is_file)
        self.combo_browser.setEnabled(not is_file)

    def _browse_cookies_file(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Select Netscape cookies.txt", str(Path.cwd()), "Text Files (*.txt);;All Files (*)"
        )
        if f:
            self.in_cookie_path.setText(f)
            self._verify_cookies_file(f)

    def _on_dest_type_toggled(self):
        to_proj = self.radio_dest_project.isChecked()
        self.combo_project.setEnabled(to_proj)
        self.btn_refresh_proj.setEnabled(to_proj)
        self.in_custom_dir.setEnabled(not to_proj)
        self.btn_browse_dest.setEnabled(not to_proj)

    def _on_project_changed(self):
        self._load_history()

    def _browse_custom_dest(self):
        d = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.in_custom_dir.text())
        if d:
            self.in_custom_dir.setText(d)

    def _on_url_text_changed(self, text: str):
        info = detect_platform(text)
        self.lbl_platform_badge.setText(f"{info['icon']}  {info['tag']}")
        self.lbl_platform_badge.setStyleSheet(
            f"background-color: {info['color']}; color: #FFFFFF; font-size: 11px; font-weight: 700; "
            f"border-radius: 4px; padding: 3px 9px;"
        )
        if text.strip().startswith(("http://", "https://")):
            self.lbl_probe_status.setText(info["tip"])
            self.lbl_probe_status.setStyleSheet("color: #38BDF8; font-size: 12px;")

    def _set_clip_range(self, start_val: str, end_val: str):
        self.in_clip_start.setText(start_val)
        self.in_clip_end.setText(end_val)
        self._update_clip_calc()

    def _update_clip_calc(self):
        s_sec = parse_timestamp_str(self.in_clip_start.text()) or 0.0
        e_sec = parse_timestamp_str(self.in_clip_end.text())
        if e_sec is not None and e_sec > s_sec:
            diff = e_sec - s_sec
            self.lbl_clip_duration.setText(f"Selected Duration: {seconds_to_hms(diff)}")
        else:
            self.lbl_clip_duration.setText("Selected Duration: (ToEnd / Full)")

    # --- Fetch Info & Metadata Probing ---

    def _fetch_info(self):
        url = self.in_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a valid video stream URL.")
            return

        cookies_path = self.in_cookie_path.text().strip() if (self.chk_use_cookies.isChecked() and self.radio_cookie_file.isChecked()) else None
        cookies_browser = self.combo_browser.currentText() if (self.chk_use_cookies.isChecked() and self.radio_cookie_browser.isChecked()) else None

        self.btn_inspect.setEnabled(False)
        self.lbl_probe_status.setText("⏳ Probing media stream metadata and formats across platforms...")
        self.lbl_probe_status.setStyleSheet("color: #38BDF8; font-size: 12px;")

        self.info_thread = FetchInfoWorkerThread(url, cookies_path, cookies_browser)
        self.info_thread.info_fetched.connect(self._on_info_fetched)
        self.info_thread.start()

    @Slot(bool, dict, str)
    def _on_info_fetched(self, success: bool, info: dict, error: str):
        self.btn_inspect.setEnabled(True)
        if not success:
            self.lbl_probe_status.setText(f"❌ Error: {error}")
            self.lbl_probe_status.setStyleSheet("color: #EF4444; font-size: 12px;")
            QMessageBox.critical(self, "Inspection Failed", f"Could not inspect URL:\n\n{error}")
            return

        self.current_meta = info
        self.lbl_probe_status.setText(f"✅ Stream verified: {info.get('title')}")
        self.lbl_probe_status.setStyleSheet("color: #34D399; font-size: 12px;")

        # Populate Preview Card with platform styling
        plat = info.get("platform") or detect_platform(self.in_url.text())
        self.lbl_meta_platform.setText(f"{plat['icon']} {plat['name']}")
        self.lbl_meta_platform.setStyleSheet(
            f"background-color: {plat['color']}; color: #FFFFFF; font-size: 11px; font-weight: 700; "
            f"border-radius: 3px; padding: 2px 7px;"
        )

        self.lbl_meta_title.setText(info.get("title", "Untitled"))
        self.lbl_meta_channel.setText(f"Author / Channel: {info.get('uploader', 'Unknown')}")
        self.lbl_meta_duration.setText(f"⏳ {info.get('duration_hms', '00:00:00')}")

        avail = info.get("availability", "public")
        if avail == "private":
            self.lbl_meta_privacy.setText("🔒 Private (Auth OK)")
            self.lbl_meta_privacy.setStyleSheet("color: #F87171; font-weight: 600; font-size: 12px;")
        elif avail == "unlisted":
            self.lbl_meta_privacy.setText("🟡 Unlisted Video")
            self.lbl_meta_privacy.setStyleSheet("color: #FBBF24; font-weight: 600; font-size: 12px;")
        else:
            self.lbl_meta_privacy.setText("🟢 Public Video")
            self.lbl_meta_privacy.setStyleSheet("color: #34D399; font-weight: 600; font-size: 12px;")

        # Fetch thumbnail preview asynchronously
        thumb_url = info.get("thumbnail")
        if thumb_url:
            self._load_thumbnail_async(thumb_url)

        # Set default clip end to duration
        dur_hms = info.get("duration_hms")
        if dur_hms and not self.in_clip_end.text():
            self.in_clip_end.setText(dur_hms)

        self.preview_card.setVisible(True)

    def _load_thumbnail_async(self, thumb_url: str):
        class ThumbWorker(QThread):
            loaded = Signal(bytes)
            def run(self):
                try:
                    req = Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urlopen(req, timeout=5) as resp:
                        self.loaded.emit(resp.read())
                except Exception:
                    pass

        self._thumb_worker = ThumbWorker()
        self._thumb_worker.loaded.connect(self._set_thumbnail_pixmap)
        self._thumb_worker.start()

    @Slot(bytes)
    def _set_thumbnail_pixmap(self, img_bytes: bytes):
        img = QImage.fromData(img_bytes)
        if not img.isNull():
            pix = QPixmap.fromImage(img).scaled(160, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_thumb.setPixmap(pix)

    # --- Start Download Pipeline ---

    def _start_download(self):
        url = self.in_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a valid video stream URL.")
            return

        # Resolve output destination
        if self.radio_dest_project.isChecked():
            proj_id = self.combo_project.currentData()
            if not proj_id:
                QMessageBox.warning(self, "No Project", "Please create or select a study project first.")
                return
            proj = project_manager.load_project_by_id(proj_id)
            if not proj:
                QMessageBox.warning(self, "Project Not Found", "Selected project could not be found.")
                return
            target_dir = Path(proj.output_path) / "downloads"
            prefix = None  # Uses natural lecture video title %(title).80s.%(ext)s
        else:
            cust_str = self.in_custom_dir.text().strip()
            if not cust_str:
                QMessageBox.warning(self, "Missing Directory", "Please select a custom save directory.")
                return
            target_dir = Path(cust_str)
            prefix = None
            proj_id = None

        # Resolve mode & presets
        tab_idx = self.tabs_mode.currentIndex()
        if tab_idx == 0:
            mode = "video"
            format_preset = self.combo_video_res.currentData()
            container = self.combo_video_container.currentText()
            start_t = None
            end_t = None
        elif tab_idx == 1:
            mode = "audio"
            format_preset = self.combo_audio_preset.currentData()
            container = "mp3"
            start_t = None
            end_t = None
        else:
            mode = "clip"
            clip_type = self.combo_clip_type.currentData()
            format_preset = "best_mp4" if clip_type == "video" else "mp3_192"
            container = "mp4" if clip_type == "video" else "mp3"
            start_t = self.in_clip_start.text().strip() or None
            end_t = self.in_clip_end.text().strip() or None

        cookies_path = self.in_cookie_path.text().strip() if (self.chk_use_cookies.isChecked() and self.radio_cookie_file.isChecked()) else None
        cookies_browser = self.combo_browser.currentText() if (self.chk_use_cookies.isChecked() and self.radio_cookie_browser.isChecked()) else None

        self.cancel_token = CancellationToken()
        self.btn_download.setEnabled(False)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(5)
        self.lbl_progress_msg.setVisible(True)
        self.lbl_progress_msg.setText("Starting download worker...")
        self.hub_card.setVisible(False)

        self.download_thread = DownloadWorkerThread(
            url=url,
            output_dir=target_dir,
            filename_prefix=prefix,
            mode=mode,
            format_preset=format_preset,
            container=container,
            start_time=start_t,
            end_time=end_t,
            cookies_path=cookies_path,
            cookies_browser=cookies_browser,
            cancel_token=self.cancel_token,
            video_meta=self.current_meta
        )
        self.download_thread.progress_updated.connect(self._on_download_progress)
        self.download_thread.download_finished.connect(self._on_download_finished)
        self.download_thread.start()

    def _cancel_download(self):
        self.cancel_token.cancel()
        self.lbl_progress_msg.setText("Cancelling download...")

    @Slot(float, str)
    def _on_download_progress(self, pct: float, msg: str):
        self.progress_bar.setValue(int(pct))
        self.lbl_progress_msg.setText(msg)

    @Slot(bool, str, dict, str)
    def _on_download_finished(self, success: bool, file_path: str, meta: dict, error: str):
        self.btn_download.setEnabled(True)
        self.btn_cancel.setVisible(False)

        if not success:
            self.lbl_progress_msg.setText(f"❌ Failed: {error}")
            QMessageBox.critical(self, "Download Error", f"Download failed:\n\n{error}")
            return

        self.progress_bar.setValue(100)
        self.lbl_progress_msg.setText("✅ Download completed!")
        self.last_downloaded_file = Path(file_path)

        # Record in database
        import uuid
        title = meta.get("title") or self.last_downloaded_file.name
        dur = meta.get("duration", 0.0)
        size = self.last_downloaded_file.stat().st_size if self.last_downloaded_file.exists() else 0
        proj_id = self.combo_project.currentData() if self.radio_dest_project.isChecked() else None

        db.save_downloaded_media(
            media_id=str(uuid.uuid4()),
            title=title,
            url=self.in_url.text().strip(),
            file_path=str(self.last_downloaded_file),
            file_type=self.last_downloaded_file.suffix.replace(".", "").lower(),
            format_name=self.last_downloaded_file.suffix,
            duration=dur,
            file_size=size,
            project_id=proj_id
        )

        # Show Hub Card
        self.lbl_hub_status.setText(f"🎉 Saved: {self.last_downloaded_file.name} ({format_file_size(size)})")
        self.hub_card.setVisible(True)

        self._load_history()

    # --- Quick Action Hub Methods ---

    def _on_send_to_screenshots(self):
        if self.last_downloaded_file and self.last_downloaded_file.exists():
            self.send_to_screenshots.emit(str(self.last_downloaded_file.resolve()))

    def _on_send_to_transcriber(self):
        if self.last_downloaded_file and self.last_downloaded_file.exists():
            self.send_to_transcriber.emit(str(self.last_downloaded_file.resolve()))

    def _open_downloaded_folder(self):
        if self.last_downloaded_file and self.last_downloaded_file.exists():
            folder = str(self.last_downloaded_file.parent.resolve())
            if os.name == "nt":
                os.system(f'explorer /select,"{str(self.last_downloaded_file.resolve())}"')
            else:
                subprocess.Popen(["xdg-open", folder])

    def _play_media(self):
        if self.last_downloaded_file and self.last_downloaded_file.exists():
            os.startfile(str(self.last_downloaded_file.resolve()))

    # --- History Table ---

    def _load_history(self):
        proj_id = self.combo_project.currentData() if self.radio_dest_project.isChecked() else None
        items = db.list_downloaded_media(project_id=proj_id, limit=30)
        self.table_history.setRowCount(len(items))

        for row, item in enumerate(items):
            # Title
            t_item = QTableWidgetItem(item.get("title", "Untitled"))
            t_item.setToolTip(item.get("file_path", ""))
            self.table_history.setItem(row, 0, t_item)

            # Type
            f_type = item.get("file_type", "").upper()
            self.table_history.setItem(row, 1, QTableWidgetItem(f_type))

            # Format
            self.table_history.setItem(row, 2, QTableWidgetItem(item.get("format", "")))

            # Size
            size_str = format_file_size(item.get("file_size", 0))
            self.table_history.setItem(row, 3, QTableWidgetItem(size_str))

            # Duration
            dur_str = seconds_to_hms(item.get("duration", 0.0))
            self.table_history.setItem(row, 4, QTableWidgetItem(dur_str))

            # Action Buttons widget
            act_widget = QWidget()
            a_layout = QHBoxLayout(act_widget)
            a_layout.setContentsMargins(4, 2, 4, 2)
            a_layout.setSpacing(6)

            file_path = item.get("file_path")

            btn_play = QPushButton("▶️")
            btn_play.setToolTip("Play media")
            btn_play.setFixedWidth(28)
            btn_play.clicked.connect(lambda _, p=file_path: os.startfile(p) if Path(p).exists() else None)

            btn_ss = QPushButton("📷")
            btn_ss.setToolTip("Send to Screenshot Extractor")
            btn_ss.setFixedWidth(28)
            btn_ss.clicked.connect(lambda _, p=file_path: self.send_to_screenshots.emit(p))

            btn_stt = QPushButton("🎙️")
            btn_stt.setToolTip("Send to Audio Transcriber")
            btn_stt.setFixedWidth(28)
            btn_stt.clicked.connect(lambda _, p=file_path: self.send_to_transcriber.emit(p))

            a_layout.addWidget(btn_play)
            a_layout.addWidget(btn_ss)
            a_layout.addWidget(btn_stt)
            self.table_history.setCellWidget(row, 5, act_widget)
