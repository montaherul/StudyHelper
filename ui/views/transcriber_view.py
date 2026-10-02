"""
Local Speech-to-Text Transcriber View for LocalStudy.
Enables offline transcription via faster-whisper from local files or YouTube URLs.
Exports TXT, SRT, VTT, and JSON with dynamic project synchronization.
"""

from pathlib import Path
from typing import Optional, List
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QFileDialog, QComboBox, QProgressBar, QMessageBox,
    QGridLayout, QPlainTextEdit, QRadioButton, QButtonGroup
)

from config.constants import WHISPER_MODELS, LANGUAGE_OPTIONS
from core.job_manager import CancellationToken
from core.project_manager import project_manager
from database.db import db
from database.models import Project, TranscriptSegment
from transcription.audio_extractor import audio_extractor
from transcription.engine import transcription_engine
from transcription.exporters import transcript_exporter
from video.analyzer import analyzer
from video.downloader import video_downloader


class TranscriberWorkerThread(QThread):
    """Background thread executing audio download (if URL), demuxing, and local Whisper inference."""
    progress_updated = Signal(float, str)
    segment_received = Signal(str, str)
    transcription_finished = Signal(bool, list, str)

    def __init__(
        self,
        source_is_url: bool,
        media_input: str,
        project_id: str,
        output_dir: Path,
        model_size: str,
        language: Optional[str],
        duration: float,
        cancel_token: CancellationToken
    ):
        super().__init__()
        self.source_is_url = source_is_url
        self.media_input = media_input
        self.project_id = project_id
        self.output_dir = output_dir
        self.model_size = model_size
        self.language = language
        self.duration = duration
        self.cancel_token = cancel_token

    def run(self):
        wav_path = self.output_dir / "temp_audio_16k.wav"
        try:
            proj = project_manager.load_project_by_id(self.project_id)
            if not proj:
                raise ValueError("Project not found.")

            # Step 1: Resolve Media Source
            if self.source_is_url:
                self.progress_updated.emit(5.0, "Downloading audio track from URL...")
                source_dir = Path(proj.output_path) / "source"
                media_file = video_downloader.download_video(
                    url=self.media_input,
                    output_dir=source_dir,
                    filename_prefix=proj.name,
                    progress_callback=lambda pct, msg: self.progress_updated.emit(pct * 0.3, msg),
                    cancel_token=self.cancel_token
                )
            else:
                media_file = Path(self.media_input)
                if not media_file.exists():
                    raise FileNotFoundError(f"Media file not found: {self.media_input}")

            if self.cancel_token.is_cancelled():
                raise RuntimeError("Operation cancelled by user.")

            # Step 2: Extract 16kHz WAV
            self.progress_updated.emit(35.0, "Extracting and resampling to 16kHz mono WAV...")
            audio_extractor.extract_16k_mono_wav(
                media_path=media_file,
                output_wav_path=wav_path,
                cancel_token=self.cancel_token
            )

            # Step 3: Transcribe via local faster-whisper
            def on_progress(pct, msg):
                # Scale from 40% to 95%
                scaled = 40.0 + (pct * 0.55)
                self.progress_updated.emit(scaled, msg)

            segments = transcription_engine.transcribe_audio(
                audio_path=wav_path,
                project_id=self.project_id,
                model_size=self.model_size,
                language=self.language,
                duration_seconds=self.duration,
                progress_callback=on_progress,
                cancel_token=self.cancel_token
            )

            # Step 4: Persist and export all formats
            self.progress_updated.emit(96.0, "Writing TXT, SRT, VTT, and indexing search...")
            db.save_transcript_segments(segments)
            transcript_exporter.export_all(segments, self.output_dir)

            # Cleanup temp wav
            if wav_path.exists():
                wav_path.unlink(missing_ok=True)

            self.transcription_finished.emit(True, segments, "")
        except Exception as e:
            if wav_path.exists():
                wav_path.unlink(missing_ok=True)
            self.transcription_finished.emit(False, [], str(e))


class TranscriberView(QWidget):
    """UI for offline speech-to-text conversion."""

    project_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_project: Optional[Project] = None
        self.worker_thread: Optional[TranscriberWorkerThread] = None
        self.cancel_token = CancellationToken()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header_box = QVBoxLayout()
        h_lbl = QLabel("Local Audio Transcriber (Whisper STT)")
        h_lbl.setStyleSheet("font-size: 20px; font-weight: 700; color: #F8FAFC;")
        s_lbl = QLabel("100% On-Device speech recognition with faster-whisper. Transcribe local audio/video or YouTube URLs directly.")
        s_lbl.setStyleSheet("color: #94A3B8; font-size: 13px;")
        header_box.addWidget(h_lbl)
        header_box.addWidget(s_lbl)
        layout.addLayout(header_box)

        # Media Input Card
        input_card = QFrame()
        input_card.setProperty("class", "CardFrame")
        input_layout = QVBoxLayout(input_card)
        input_layout.setSpacing(10)

        # Source Radio Group
        source_box = QHBoxLayout()
        self.radio_local = QRadioButton("📁 Local Audio / Video File")
        self.radio_url = QRadioButton("🌐 YouTube / Web URL")
        self.radio_local.setChecked(True)

        self.btn_group_source = QButtonGroup(self)
        self.btn_group_source.addButton(self.radio_local)
        self.btn_group_source.addButton(self.radio_url)
        self.radio_local.toggled.connect(self._on_source_type_toggled)

        source_box.addWidget(self.radio_local)
        source_box.addWidget(self.radio_url)
        source_box.addStretch()
        input_layout.addLayout(source_box)

        file_row = QHBoxLayout()
        self.in_media_path = QLineEdit()
        self.in_media_path.setPlaceholderText("Select video or audio file (MP4, MKV, MP3, WAV, M4A, AAC, FLAC)...")

        self.btn_browse = QPushButton("Browse Media...")
        self.btn_browse.setProperty("class", "SecondaryBtn")
        self.btn_browse.clicked.connect(self._browse_media)

        self.btn_probe_url = QPushButton("⚡ Fetch URL Info")
        self.btn_probe_url.setProperty("class", "SecondaryBtn")
        self.btn_probe_url.setVisible(False)
        self.btn_probe_url.clicked.connect(self._probe_url)

        file_row.addWidget(self.in_media_path)
        file_row.addWidget(self.btn_browse)
        file_row.addWidget(self.btn_probe_url)
        input_layout.addLayout(file_row)

        self.lbl_media_info = QLabel("No media loaded.")
        self.lbl_media_info.setStyleSheet("color: #64748B; font-size: 12px;")
        input_layout.addWidget(self.lbl_media_info)
        layout.addWidget(input_card)

        # Settings Card
        settings_card = QFrame()
        settings_card.setProperty("class", "CardFrame")
        grid = QGridLayout(settings_card)
        grid.setSpacing(12)

        # Target Project
        grid.addWidget(QLabel("Target Project:"), 0, 0)
        proj_row = QHBoxLayout()
        self.combo_project = QComboBox()
        self._populate_projects()
        self.combo_project.currentIndexChanged.connect(self._on_project_changed)
        proj_row.addWidget(self.combo_project)

        btn_new_proj = QPushButton("+ New")
        btn_new_proj.setProperty("class", "SecondaryBtn")
        btn_new_proj.setFixedWidth(60)
        btn_new_proj.clicked.connect(self._create_quick_project)
        proj_row.addWidget(btn_new_proj)

        grid.addLayout(proj_row, 0, 1, 1, 2)

        # Model Selector
        grid.addWidget(QLabel("Whisper Model Tier:"), 1, 0)
        self.combo_model = QComboBox()
        for m in WHISPER_MODELS:
            self.combo_model.addItem(f"{m['name']} — {m['desc']}", m["id"])
        self.combo_model.setCurrentIndex(2)  # Default small
        grid.addWidget(self.combo_model, 1, 1, 1, 2)

        # Language Selector
        grid.addWidget(QLabel("Spoken Language:"), 2, 0)
        self.combo_language = QComboBox()
        for label, code in LANGUAGE_OPTIONS:
            self.combo_language.addItem(label, code)
        grid.addWidget(self.combo_language, 2, 1, 1, 2)

        layout.addWidget(settings_card)

        # Log & Progress Card
        exec_card = QFrame()
        exec_card.setProperty("class", "CardFrame")
        exec_layout = QVBoxLayout(exec_card)
        exec_layout.setSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.lbl_status = QLabel("Ready.")
        self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 12px;")

        exec_layout.addWidget(self.progress_bar)
        exec_layout.addWidget(self.lbl_status)

        # Live Transcript Preview Area
        self.txt_preview = QPlainTextEdit()
        self.txt_preview.setReadOnly(True)
        self.txt_preview.setPlaceholderText("Live transcript segments will stream here during processing...")
        self.txt_preview.setFixedHeight(120)
        exec_layout.addWidget(self.txt_preview)

        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("🎙️ Start Local Transcription")
        self.btn_start.setProperty("class", "PrimaryBtn")
        self.btn_start.setFixedHeight(34)
        self.btn_start.clicked.connect(self._start_transcription)

        self.btn_cancel = QPushButton("⏹ Cancel")
        self.btn_cancel.setProperty("class", "SecondaryBtn")
        self.btn_cancel.setFixedHeight(34)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_transcription)

        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_cancel)
        exec_layout.addLayout(btn_row)

        layout.addWidget(exec_card)
        layout.addStretch()

    def refresh(self):
        """Called automatically when view becomes visible to update project dropdown."""
        curr_id = self.combo_project.currentData()
        self._populate_projects()
        if curr_id:
            for idx in range(self.combo_project.count()):
                if self.combo_project.itemData(idx) == curr_id:
                    self.combo_project.setCurrentIndex(idx)
                    break

    def load_media_file(self, file_path: str):
        """Loads a local media file directly into the transcriber view."""
        self.radio_local.setChecked(True)
        self.in_media_path.setText(str(file_path))
        p = Path(file_path)
        try:
            meta = analyzer.analyze_video(p)
            dur = meta["duration_hms"]
            self.lbl_media_info.setText(f"✓ Media Loaded: {p.name}  •  Duration: {dur}")
            self.lbl_media_info.setStyleSheet("color: #34D399; font-size: 12px; font-weight: 500;")
        except Exception:
            self.lbl_media_info.setText(f"✓ File Selected: {p.name}")

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

    def _on_project_changed(self, index):
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
            self.in_media_path.setPlaceholderText("Select video or audio file (MP4, MKV, MP3, WAV, M4A, AAC, FLAC)...")
            self.btn_browse.setVisible(True)
            self.btn_probe_url.setVisible(False)
        else:
            self.in_media_path.setPlaceholderText("Paste YouTube or educational video URL...")
            self.btn_browse.setVisible(False)
            self.btn_probe_url.setVisible(True)
        self.in_media_path.clear()
        self.lbl_media_info.setText("No media loaded.")

    def _browse_media(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Media File",
            "",
            "Audio/Video Files (*.mp4 *.mkv *.mp3 *.wav *.m4a *.aac *.flac *.webm);;All Files (*.*)"
        )
        if path:
            self.in_media_path.setText(path)
            p = Path(path)
            try:
                meta = analyzer.analyze_video(p)
                dur = meta["duration_hms"]
                self.lbl_media_info.setText(f"✓ Media Loaded: {p.name}  •  Duration: {dur}")
                self.lbl_media_info.setStyleSheet("color: #34D399; font-size: 12px; font-weight: 500;")
            except Exception:
                self.lbl_media_info.setText(f"✓ File Selected: {p.name}")

    def _probe_url(self):
        url = self.in_media_path.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid video URL.")
            return

        self.lbl_media_info.setText("Probing video information from URL...")
        try:
            info = video_downloader.get_info(url)
            self.lbl_media_info.setText(f"✓ Video Identified: {info['title']}  •  Duration: {info['duration_hms']}")
            self.lbl_media_info.setStyleSheet("color: #34D399; font-size: 12px; font-weight: 500;")
            if self.combo_project.count() == 0:
                proj = project_manager.create_project(name=info["title"][:50], subject="Online Lecture")
                self._populate_projects()
                self.set_active_project(proj.id)
        except Exception as e:
            self.lbl_media_info.setText(f"Error fetching URL: {e}")
            self.lbl_media_info.setStyleSheet("color: #F87171; font-size: 12px;")

    def _start_transcription(self):
        source_val = self.in_media_path.text().strip()
        is_url = self.radio_url.isChecked()

        if not source_val:
            QMessageBox.warning(self, "Invalid Input", "Please provide a media file or video URL.")
            return

        if not is_url and not Path(source_val).exists():
            QMessageBox.warning(self, "File Not Found", f"Media file not found: {source_val}")
            return

        if self.combo_project.count() == 0:
            default_name = "Online Lecture" if is_url else Path(source_val).stem.replace("_", " ").title()
            proj = project_manager.create_project(name=default_name)
            self._populate_projects()
            self.set_active_project(proj.id)

        proj_id = self.combo_project.currentData()
        proj = project_manager.load_project_by_id(proj_id)
        if not proj:
            QMessageBox.warning(self, "Error", "Selected project could not be loaded.")
            return

        model_id = self.combo_model.currentData()
        lang_code = self.combo_language.currentData()
        out_dir = Path(proj.output_path) / "transcript"

        duration = 0.0
        if not is_url:
            try:
                meta = analyzer.analyze_video(Path(source_val))
                duration = meta.get("duration", 0.0)
            except Exception:
                pass

        self.cancel_token = CancellationToken()
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.txt_preview.clear()
        self.lbl_status.setText("Initializing transcription engine...")

        self.worker_thread = TranscriberWorkerThread(
            source_is_url=is_url,
            media_input=source_val,
            project_id=proj_id,
            output_dir=out_dir,
            model_size=model_id,
            language=lang_code,
            duration=duration,
            cancel_token=self.cancel_token
        )
        self.worker_thread.progress_updated.connect(self._on_progress)
        self.worker_thread.transcription_finished.connect(self._on_finished)
        self.worker_thread.start()

    def _cancel_transcription(self):
        self.cancel_token.cancel()
        self.lbl_status.setText("Cancelling transcription...")
        self.btn_cancel.setEnabled(False)

    @Slot(float, str)
    def _on_progress(self, pct: float, msg: str):
        self.progress_bar.setValue(int(pct))
        self.lbl_status.setText(msg)
        if "Transcribed up to" in msg:
            self.txt_preview.appendPlainText(msg)

    @Slot(bool, list, str)
    def _on_finished(self, success: bool, segments: list, error: str):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if success:
            self.progress_bar.setValue(100)
            self.lbl_status.setText(f"Completed! {len(segments)} segments generated.")
            QMessageBox.information(
                self,
                "Transcription Complete",
                f"Successfully transcribed {len(segments)} speech segments!\n\nGenerated files:\n• transcript.txt\n• transcript.srt\n• transcript.vtt\n• segments.json\n\nSegments are indexed for instant search."
            )
        else:
            self.lbl_status.setText(f"Error: {error}")
            QMessageBox.critical(self, "Transcription Error", f"Transcription failed:\n{error}")
