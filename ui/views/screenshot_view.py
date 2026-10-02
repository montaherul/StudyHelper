"""
Video Screenshot & Slide Extraction View for LocalStudy.
Supports both Local Video Files and YouTube / Web URLs.
Includes Auto-Compile PDF pipeline and dynamic project synchronization.
"""

import os
from pathlib import Path
from typing import Optional, List
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QFileDialog, QComboBox, QCheckBox, QSpinBox, QProgressBar,
    QMessageBox, QRadioButton, QButtonGroup, QGridLayout
)

from config.constants import INTERVAL_PRESETS, PDF_LAYOUTS, PDF_LAYOUT_2UP
from core.job_manager import CancellationToken
from core.project_manager import project_manager
from database.db import db
from database.models import Project, Screenshot
from pdf.generator import pdf_generator
from utils.filesystem import estimate_storage_required
from utils.time_utils import seconds_to_hms
from video.analyzer import analyzer
from video.downloader import video_downloader
from video.frame_extractor import frame_extractor


class ExtractionWorkerThread(QThread):
    """Background worker thread executing video download (if URL), frame extraction, and optional auto-PDF."""
    progress_updated = Signal(float, str)
    extraction_finished = Signal(bool, list, str, str)  # success, screenshots, pdf_path, error

    def __init__(
        self,
        source_is_url: bool,
        media_input: str,
        project_id: str,
        interval_seconds: float,
        custom_timestamps: Optional[List[str]],
        smart_slide: bool,
        apply_overlay: bool,
        auto_compile_pdf: bool,
        pdf_layout: str,
        quality: int,
        cancel_token: CancellationToken,
        pdf_show_timestamp: bool = True,
        pdf_time_only: bool = True,
        pdf_cover_name_only: bool = True
    ):
        super().__init__()
        self.source_is_url = source_is_url
        self.media_input = media_input
        self.project_id = project_id
        self.interval_seconds = interval_seconds
        self.custom_timestamps = custom_timestamps
        self.smart_slide = smart_slide
        self.apply_overlay = apply_overlay
        self.auto_compile_pdf = auto_compile_pdf
        self.pdf_layout = pdf_layout
        self.quality = quality
        self.cancel_token = cancel_token
        self.pdf_show_timestamp = pdf_show_timestamp
        self.pdf_time_only = pdf_time_only
        self.pdf_cover_name_only = pdf_cover_name_only

    def run(self):
        try:
            proj = project_manager.load_project_by_id(self.project_id)
            if not proj:
                raise ValueError("Project not found.")

            proj_dir = Path(proj.output_path)
            out_ss_dir = proj_dir / "screenshots"

            # Step 1: Resolve Video File Path
            if self.source_is_url:
                self.progress_updated.emit(5.0, "Downloading video from URL via yt-dlp...")
                source_dir = proj_dir / "source"
                video_file = video_downloader.download_video(
                    url=self.media_input,
                    output_dir=source_dir,
                    filename_prefix=proj.name,
                    progress_callback=lambda pct, msg: self.progress_updated.emit(pct * 0.4, msg),
                    cancel_token=self.cancel_token
                )
            else:
                video_file = Path(self.media_input)
                if not video_file.exists():
                    raise FileNotFoundError(f"Video file does not exist: {self.media_input}")

            if self.cancel_token.is_cancelled():
                raise RuntimeError("Extraction cancelled by user.")

            # Step 2: Extract Frames
            base_pct = 40.0 if self.source_is_url else 5.0
            scale_pct = 0.50 if self.auto_compile_pdf else 0.90

            def on_frame_progress(pct, msg):
                overall = base_pct + (pct * (scale_pct / 100.0) * 100.0 * 0.01 * (100 - base_pct))
                self.progress_updated.emit(overall, msg)

            screenshots = frame_extractor.extract_frames(
                video_path=video_file,
                output_dir=out_ss_dir,
                project_id=self.project_id,
                interval_seconds=self.interval_seconds,
                custom_timestamps=self.custom_timestamps,
                smart_slide_detection=self.smart_slide,
                apply_overlay=self.apply_overlay,
                lecture_title=proj.name,
                course_name=proj.course,
                jpeg_quality=self.quality,
                progress_callback=on_frame_progress,
                cancel_token=self.cancel_token
            )
            # Save screenshots to database
            db.save_screenshots(screenshots)

            if self.cancel_token.is_cancelled():
                raise RuntimeError("Extraction cancelled by user.")

            # Step 3: Auto-compile PDF if enabled
            generated_pdf_path = ""
            if self.auto_compile_pdf and screenshots:
                self.progress_updated.emit(90.0, f"Auto-compiling study PDF ({self.pdf_layout} layout)...")
                out_pdf = proj_dir / "pdf" / f"{proj.name}_StudyGuide.pdf"
                pdf_res = pdf_generator.compile_pdf(
                    project=proj,
                    screenshots=screenshots,
                    output_pdf_path=out_pdf,
                    layout=self.pdf_layout,
                    show_timestamp=self.pdf_show_timestamp,
                    time_only=self.pdf_time_only,
                    cover_project_name_only=self.pdf_cover_name_only,
                    progress_callback=lambda pct, msg: self.progress_updated.emit(90.0 + (pct * 0.1), msg)
                )
                generated_pdf_path = str(pdf_res)

            self.progress_updated.emit(100.0, "Completed!")
            self.extraction_finished.emit(True, screenshots, generated_pdf_path, "")

        except Exception as e:
            self.extraction_finished.emit(False, [], "", str(e))


class ScreenshotView(QWidget):
    """UI for extracting lecture slides from local videos or YouTube URLs with Auto-PDF."""

    project_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_video_meta = None
        self.worker_thread: Optional[ExtractionWorkerThread] = None
        self.cancel_token = CancellationToken()
        self.last_compiled_pdf: Optional[str] = None
        self.last_project_folder: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header_box = QVBoxLayout()
        h_lbl = QLabel("Video Screenshot & Auto-PDF Studio")
        h_lbl.setStyleSheet("font-size: 20px; font-weight: 700; color: #F8FAFC;")
        s_lbl = QLabel("Extract periodic slides from local video files or YouTube URLs and automatically compile ready-to-study PDFs.")
        s_lbl.setStyleSheet("color: #94A3B8; font-size: 13px;")
        header_box.addWidget(h_lbl)
        header_box.addWidget(s_lbl)
        layout.addLayout(header_box)

        # Source Selection Card (Local vs YouTube)
        input_card = QFrame()
        input_card.setProperty("class", "CardFrame")
        input_layout = QVBoxLayout(input_card)
        input_layout.setSpacing(10)

        # Source Type Radio Group
        source_type_box = QHBoxLayout()
        self.radio_local = QRadioButton("📁 Local Video File")
        self.radio_url = QRadioButton("🌐 YouTube / Video URL")
        self.radio_local.setChecked(True)

        self.btn_group_source = QButtonGroup(self)
        self.btn_group_source.addButton(self.radio_local)
        self.btn_group_source.addButton(self.radio_url)
        self.radio_local.toggled.connect(self._on_source_type_toggled)

        source_type_box.addWidget(self.radio_local)
        source_type_box.addWidget(self.radio_url)
        source_type_box.addStretch()
        input_layout.addLayout(source_type_box)

        # Input Row (File / URL)
        self.input_row = QHBoxLayout()
        self.in_source = QLineEdit()
        self.in_source.setPlaceholderText("Select video file (MP4, MKV, AVI, MOV, WebM)...")
        self.in_source.textChanged.connect(self._on_source_input_changed)

        self.btn_browse = QPushButton("Browse Video...")
        self.btn_browse.setProperty("class", "SecondaryBtn")
        self.btn_browse.clicked.connect(self._browse_video)

        self.btn_probe_url = QPushButton("⚡ Fetch URL Info")
        self.btn_probe_url.setProperty("class", "SecondaryBtn")
        self.btn_probe_url.setVisible(False)
        self.btn_probe_url.clicked.connect(self._probe_url)

        self.input_row.addWidget(self.in_source)
        self.input_row.addWidget(self.btn_browse)
        self.input_row.addWidget(self.btn_probe_url)
        input_layout.addLayout(self.input_row)

        self.lbl_video_info = QLabel("No video or URL loaded.")
        self.lbl_video_info.setStyleSheet("color: #64748B; font-size: 12px;")
        input_layout.addWidget(self.lbl_video_info)
        layout.addWidget(input_card)

        # Settings & Auto-PDF Card
        settings_card = QFrame()
        settings_card.setProperty("class", "CardFrame")
        grid = QGridLayout(settings_card)
        grid.setSpacing(12)

        # Target Project
        grid.addWidget(QLabel("Target Project:"), 0, 0)
        proj_row = QHBoxLayout()
        self.combo_project = QComboBox()
        self._populate_projects()
        self.combo_project.currentIndexChanged.connect(self._on_project_combobox_changed)
        proj_row.addWidget(self.combo_project)

        btn_new_proj = QPushButton("+ New")
        btn_new_proj.setProperty("class", "SecondaryBtn")
        btn_new_proj.setFixedWidth(60)
        btn_new_proj.clicked.connect(self._create_quick_project)
        proj_row.addWidget(btn_new_proj)
        grid.addLayout(proj_row, 0, 1, 1, 2)

        # Interval preset
        grid.addWidget(QLabel("Slide Interval:"), 1, 0)
        self.combo_interval = QComboBox()
        for label, val in INTERVAL_PRESETS:
            self.combo_interval.addItem(label, val)
        self.combo_interval.setCurrentIndex(4)  # Default 30s
        self.combo_interval.currentIndexChanged.connect(self._on_interval_changed)
        grid.addWidget(self.combo_interval, 1, 1)

        # Custom seconds spinner
        self.spin_custom_interval = QSpinBox()
        self.spin_custom_interval.setRange(1, 3600)
        self.spin_custom_interval.setValue(30)
        self.spin_custom_interval.setSuffix(" seconds")
        self.spin_custom_interval.setEnabled(False)
        self.spin_custom_interval.valueChanged.connect(self._recalc_storage)
        grid.addWidget(self.spin_custom_interval, 1, 2)

        # Custom Timestamps
        grid.addWidget(QLabel("Custom Timestamps:"), 2, 0)
        self.in_custom_timestamps = QLineEdit()
        self.in_custom_timestamps.setPlaceholderText("Optional: 00:05:30, 00:12:45, 01:02:15 (Leave empty for fixed intervals)")
        self.in_custom_timestamps.textChanged.connect(self._recalc_storage)
        grid.addWidget(self.in_custom_timestamps, 2, 1, 1, 2)

        # Auto-compile PDF section (Checked by default!)
        self.chk_auto_pdf = QCheckBox("⚡ Auto-compile Study PDF immediately after extraction (No extra step needed)")
        self.chk_auto_pdf.setChecked(True)
        self.chk_auto_pdf.setStyleSheet("font-weight: 600; color: #38BDF8;")
        self.chk_auto_pdf.toggled.connect(self._on_auto_pdf_toggled)
        grid.addWidget(self.chk_auto_pdf, 3, 0, 1, 2)

        # PDF Layout dropdown
        self.combo_pdf_layout = QComboBox()
        for label, val in PDF_LAYOUTS:
            self.combo_pdf_layout.addItem(label, val)
        self.combo_pdf_layout.setCurrentIndex(1)  # Default 2-up
        grid.addWidget(self.combo_pdf_layout, 3, 2)

        # PDF Formatting & Clean Screenshot Settings
        self.chk_pdf_cover_name_only = QCheckBox("PDF 1st Page: Show Project Name only (Clean Title)")
        self.chk_pdf_cover_name_only.setChecked(True)
        grid.addWidget(self.chk_pdf_cover_name_only, 4, 0, 1, 2)

        self.chk_pdf_time_only = QCheckBox("PDF Slides: Show timestamp only (⏱ HH:MM:SS)")
        self.chk_pdf_time_only.setChecked(True)
        grid.addWidget(self.chk_pdf_time_only, 4, 2)

        self.chk_smart_slide = QCheckBox("Smart slide-change detection (flag major visual slide transitions)")
        self.chk_smart_slide.setChecked(True)
        grid.addWidget(self.chk_smart_slide, 5, 0, 1, 2)

        self.lbl_clean_ss_notice = QLabel("🛡️ Screenshots saved 100% clean (no burned-in text/badges)")
        self.lbl_clean_ss_notice.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 500;")
        grid.addWidget(self.lbl_clean_ss_notice, 5, 2)

        # Estimated size
        self.lbl_storage_est = QLabel("Estimated output: —")
        self.lbl_storage_est.setStyleSheet("color: #34D399; font-size: 12px; font-weight: 600;")
        grid.addWidget(self.lbl_storage_est, 6, 0, 1, 3)

        layout.addWidget(settings_card)

        # Execution Progress & Action Buttons Card
        exec_card = QFrame()
        exec_card.setProperty("class", "CardFrame")
        exec_layout = QVBoxLayout(exec_card)
        exec_layout.setSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.lbl_progress_status = QLabel("Ready.")
        self.lbl_progress_status.setStyleSheet("color: #94A3B8; font-size: 12px;")

        exec_layout.addWidget(self.progress_bar)
        exec_layout.addWidget(self.lbl_progress_status)

        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("🚀 Extract Slides & Generate Study PDF")
        self.btn_start.setProperty("class", "PrimaryBtn")
        self.btn_start.setFixedHeight(36)
        self.btn_start.clicked.connect(self._start_pipeline)

        self.btn_cancel = QPushButton("⏹ Cancel")
        self.btn_cancel.setProperty("class", "SecondaryBtn")
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_pipeline)

        self.btn_open_pdf_result = QPushButton("👁️ View Study PDF")
        self.btn_open_pdf_result.setProperty("class", "SecondaryBtn")
        self.btn_open_pdf_result.setFixedHeight(36)
        self.btn_open_pdf_result.setVisible(False)
        self.btn_open_pdf_result.clicked.connect(self._open_result_pdf)

        self.btn_open_folder_result = QPushButton("📂 Open Folder")
        self.btn_open_folder_result.setProperty("class", "SecondaryBtn")
        self.btn_open_folder_result.setFixedHeight(36)
        self.btn_open_folder_result.setVisible(False)
        self.btn_open_folder_result.clicked.connect(self._open_result_folder)

        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_open_pdf_result)
        btn_row.addWidget(self.btn_open_folder_result)
        btn_row.addStretch()
        exec_layout.addLayout(btn_row)

        layout.addWidget(exec_card)
        layout.addStretch()

    def refresh(self):
        """Called automatically when view becomes active. Reloads project dropdown dynamically."""
        curr_id = self.combo_project.currentData()
        self._populate_projects()
        if curr_id:
            for idx in range(self.combo_project.count()):
                if self.combo_project.itemData(idx) == curr_id:
                    self.combo_project.setCurrentIndex(idx)
                    break

    def load_media_file(self, file_path: str):
        """Loads a local video file directly into the view and triggers analysis."""
        self.radio_local.setChecked(True)
        self.in_source.setText(str(file_path))
        self._on_source_input_changed(str(file_path))

    def set_active_project(self, project_id: str):
        self._populate_projects()
        for idx in range(self.combo_project.count()):
            if self.combo_project.itemData(idx) == project_id:
                self.combo_project.setCurrentIndex(idx)
                break

    def _populate_projects(self):
        self.combo_project.clear()
        projects = project_manager.list_recent_projects(limit=50)
        for p in projects:
            title = f"{p.name}" + (f" ({p.subject})" if p.subject else "")
            self.combo_project.addItem(title, p.id)

    def _on_project_combobox_changed(self, index):
        pid = self.combo_project.currentData()
        if pid:
            self.project_selected.emit(pid)

    def _create_quick_project(self):
        from ui.views.project_view import NewProjectDialog
        dlg = NewProjectDialog(self)
        if dlg.exec() and dlg.created_project:
            self._populate_projects()
            self.set_active_project(dlg.created_project.id)

    def _on_source_type_toggled(self, is_local):
        if is_local:
            self.in_source.setPlaceholderText("Select video file (MP4, MKV, AVI, MOV, WebM)...")
            self.btn_browse.setVisible(True)
            self.btn_probe_url.setVisible(False)
        else:
            self.in_source.setPlaceholderText("Paste YouTube or educational video URL (https://www.youtube.com/watch?v=...)...")
            self.btn_browse.setVisible(False)
            self.btn_probe_url.setVisible(True)
        self.in_source.clear()
        self.lbl_video_info.setText("No video or URL loaded.")
        self.lbl_video_info.setStyleSheet("color: #64748B; font-size: 12px;")

    def _browse_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.webm *.m4v);;All Files (*.*)"
        )
        if path:
            self.in_source.setText(path)

    def _probe_url(self):
        url = self.in_source.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid video URL.")
            return

        self.lbl_video_info.setText("Probing video information from URL...")
        self.lbl_video_info.setStyleSheet("color: #38BDF8; font-size: 12px;")

        try:
            info = video_downloader.get_info(url)
            dur = info["duration_hms"]
            title = info["title"]
            uploader = info["uploader"]
            self.lbl_video_info.setText(f"✓ Video Identified: {title}  •  Duration: {dur}  •  Channel: {uploader}")
            self.lbl_video_info.setStyleSheet("color: #34D399; font-size: 12px; font-weight: 500;")

            # Auto-suggest project if user hasn't selected a custom one
            if self.combo_project.count() == 0:
                proj = project_manager.create_project(name=title[:50], subject="Online Lecture")
                self._populate_projects()
                self.set_active_project(proj.id)

        except Exception as e:
            self.lbl_video_info.setText(f"Error fetching video information: {e}")
            self.lbl_video_info.setStyleSheet("color: #F87171; font-size: 12px;")

    def _on_source_input_changed(self, text):
        if self.radio_local.isChecked():
            v_path = Path(text)
            if v_path.exists() and v_path.is_file():
                try:
                    self.current_video_meta = analyzer.analyze_video(v_path)
                    dur_str = self.current_video_meta["duration_hms"]
                    res_str = self.current_video_meta["resolution"]
                    fps_val = self.current_video_meta["fps"]
                    self.lbl_video_info.setText(f"✓ Video Loaded: {v_path.name}  •  Duration: {dur_str}  •  {res_str}  •  {fps_val} FPS")
                    self.lbl_video_info.setStyleSheet("color: #34D399; font-size: 12px; font-weight: 500;")
                    self._recalc_storage()
                except Exception as e:
                    self.lbl_video_info.setText(f"Error reading video: {e}")
                    self.lbl_video_info.setStyleSheet("color: #F87171; font-size: 12px;")
            else:
                self.lbl_video_info.setText("No video loaded.")
                self.lbl_video_info.setStyleSheet("color: #64748B; font-size: 12px;")

    def _on_interval_changed(self, index):
        val = self.combo_interval.currentData()
        if val == -1:  # Custom
            self.spin_custom_interval.setEnabled(True)
        else:
            self.spin_custom_interval.setEnabled(False)
            self.spin_custom_interval.setValue(val)
        self._recalc_storage()

    def _on_auto_pdf_toggled(self, checked):
        self.combo_pdf_layout.setEnabled(checked)
        btn_text = "🚀 Extract Slides & Generate Study PDF" if checked else "📷 Extract Slides Only"
        self.btn_start.setText(btn_text)

    def _recalc_storage(self):
        dur = self.current_video_meta["duration"] if self.current_video_meta else 0.0
        if dur <= 0:
            self.lbl_storage_est.setText("Estimated output: —")
            return

        interval = self.spin_custom_interval.value()
        est = estimate_storage_required(dur, interval)
        self.lbl_storage_est.setText(
            f"Estimated output: ~{est['frame_count']} slides ({est['screenshot_str']})  •  PDF: ~{est['pdf_str']}"
        )

    def _start_pipeline(self):
        source_val = self.in_source.text().strip()
        is_url = self.radio_url.isChecked()

        if not source_val:
            QMessageBox.warning(self, "Missing Input", "Please provide a video file or YouTube URL.")
            return

        if not is_url and not Path(source_val).exists():
            QMessageBox.warning(self, "File Not Found", f"Video file not found: {source_val}")
            return

        # Ensure project exists
        if self.combo_project.count() == 0:
            default_name = "Online Lecture" if is_url else Path(source_val).stem.replace("_", " ").title()
            proj = project_manager.create_project(name=default_name)
            self._populate_projects()
            self.set_active_project(proj.id)

        proj_id = self.combo_project.currentData()
        interval = float(self.spin_custom_interval.value())
        custom_ts_text = self.in_custom_timestamps.text().strip()
        custom_ts_list = [x.strip() for x in custom_ts_text.split(",") if x.strip()] if custom_ts_text else None
        layout_choice = self.combo_pdf_layout.currentData()

        self.cancel_token = CancellationToken()
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_open_pdf_result.setVisible(False)
        self.btn_open_folder_result.setVisible(False)
        self.progress_bar.setValue(0)
        self.lbl_progress_status.setText("Starting process...")

        self.worker_thread = ExtractionWorkerThread(
            source_is_url=is_url,
            media_input=source_val,
            project_id=proj_id,
            interval_seconds=interval,
            custom_timestamps=custom_ts_list,
            smart_slide=self.chk_smart_slide.isChecked(),
            apply_overlay=False,  # Zero burned-in overlay: screenshots saved 100% clean
            auto_compile_pdf=self.chk_auto_pdf.isChecked(),
            pdf_layout=layout_choice,
            quality=85,
            cancel_token=self.cancel_token,
            pdf_show_timestamp=True,
            pdf_time_only=self.chk_pdf_time_only.isChecked(),
            pdf_cover_name_only=self.chk_pdf_cover_name_only.isChecked()
        )
        self.worker_thread.progress_updated.connect(self._on_progress)
        self.worker_thread.extraction_finished.connect(self._on_finished)
        self.worker_thread.start()

    def _cancel_pipeline(self):
        self.cancel_token.cancel()
        self.lbl_progress_status.setText("Cancelling operation...")
        self.btn_cancel.setEnabled(False)

    @Slot(float, str)
    def _on_progress(self, pct: float, msg: str):
        self.progress_bar.setValue(int(pct))
        self.lbl_progress_status.setText(msg)

    @Slot(bool, list, str, str)
    def _on_finished(self, success: bool, screenshots: list, pdf_path: str, error: str):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if success:
            self.progress_bar.setValue(100)
            status_text = f"Success! {len(screenshots)} slides extracted."
            if pdf_path:
                status_text += f" Study PDF compiled: {Path(pdf_path).name}"
                self.last_compiled_pdf = pdf_path
                self.btn_open_pdf_result.setVisible(True)

            proj = project_manager.load_project_by_id(self.combo_project.currentData())
            if proj:
                self.last_project_folder = proj.output_path
                self.btn_open_folder_result.setVisible(True)

            self.lbl_progress_status.setText(status_text)
            self.lbl_progress_status.setStyleSheet("color: #34D399; font-size: 12px; font-weight: 600;")

            # Prompt to open
            if pdf_path:
                reply = QMessageBox.question(
                    self,
                    "Process Complete",
                    f"Successfully captured {len(screenshots)} slides and compiled the study PDF!\n\nLocation: {pdf_path}\n\nWould you like to open your study PDF now?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self._open_result_pdf()
            else:
                QMessageBox.information(
                    self,
                    "Extraction Complete",
                    f"Successfully captured {len(screenshots)} slides into your project folder!"
                )
        else:
            self.lbl_progress_status.setText(f"Error: {error}")
            self.lbl_progress_status.setStyleSheet("color: #F87171; font-size: 12px;")
            QMessageBox.critical(self, "Processing Error", f"Operation failed:\n{error}")

    def _open_result_pdf(self):
        if self.last_compiled_pdf and Path(self.last_compiled_pdf).exists():
            os.startfile(self.last_compiled_pdf)

    def _open_result_folder(self):
        if self.last_project_folder and Path(self.last_project_folder).exists():
            os.startfile(self.last_project_folder)
