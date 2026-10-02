"""
Batch Processing Queue View for LocalStudy.
Enables sequential unattended processing of multiple lecture videos/audios.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QProgressBar,
    QMessageBox, QAbstractItemView
)

from core.job_manager import CancellationToken
from core.project_manager import project_manager
from database.db import db
from pdf.generator import pdf_generator
from transcription.audio_extractor import audio_extractor
from transcription.engine import transcription_engine
from transcription.exporters import transcript_exporter
from video.frame_extractor import frame_extractor


class BatchWorkerThread(QThread):
    """Executes queue items sequentially."""
    item_progress = Signal(int, float, str)  # row_idx, pct, msg
    item_status = Signal(int, str)           # row_idx, status_text
    queue_completed = Signal()

    def __init__(self, queue_items: List[Dict[str, Any]], cancel_token: CancellationToken):
        super().__init__()
        self.queue_items = queue_items
        self.cancel_token = cancel_token

    def run(self):
        for row_idx, item in enumerate(self.queue_items):
            if self.cancel_token.is_cancelled():
                self.item_status.emit(row_idx, "Cancelled")
                continue

            if item["status"] == "Completed":
                continue

            file_path = Path(item["path"])
            name = item["name"]

            try:
                self.item_status.emit(row_idx, "Creating Project...")
                proj = project_manager.create_project(name=name)

                # 1. Frame Extraction (every 30s)
                self.item_status.emit(row_idx, "Extracting Slides (Clean)...")
                out_ss = Path(proj.output_path) / "screenshots"
                screenshots = frame_extractor.extract_frames(
                    video_path=file_path,
                    output_dir=out_ss,
                    project_id=proj.id,
                    interval_seconds=30.0,
                    apply_overlay=False,
                    lecture_title=proj.name,
                    progress_callback=lambda pct, msg: self.item_progress.emit(row_idx, pct * 0.4, msg),
                    cancel_token=self.cancel_token
                )
                db.save_screenshots(screenshots)

                if self.cancel_token.is_cancelled():
                    self.item_status.emit(row_idx, "Cancelled")
                    break

                # 2. Compile PDF
                if screenshots:
                    self.item_status.emit(row_idx, "Compiling PDF...")
                    out_pdf = Path(proj.output_path) / "pdf" / f"{proj.name}_StudyGuide.pdf"
                    pdf_generator.compile_pdf(
                        project=proj,
                        screenshots=screenshots,
                        output_pdf_path=out_pdf,
                        layout="2-up",
                        show_timestamp=True,
                        time_only=True,
                        cover_project_name_only=True,
                        progress_callback=lambda pct, msg: self.item_progress.emit(row_idx, 40.0 + (pct * 0.2), msg)
                    )

                # 3. Transcribe Audio
                self.item_status.emit(row_idx, "Transcribing Audio...")
                wav_path = Path(proj.output_path) / "transcript" / "temp_audio.wav"
                try:
                    audio_extractor.extract_16k_mono_wav(
                        media_path=file_path,
                        output_wav_path=wav_path,
                        cancel_token=self.cancel_token
                    )
                    segments = transcription_engine.transcribe_audio(
                        audio_path=wav_path,
                        project_id=proj.id,
                        model_size="base",
                        progress_callback=lambda pct, msg: self.item_progress.emit(row_idx, 60.0 + (pct * 0.4), msg),
                        cancel_token=self.cancel_token
                    )
                    db.save_transcript_segments(segments)
                    transcript_exporter.export_all(segments, Path(proj.output_path) / "transcript")
                    if wav_path.exists():
                        wav_path.unlink(missing_ok=True)
                except Exception as audio_err:
                    pass  # Non-fatal if video had no audio track

                self.item_status.emit(row_idx, "Completed")
                self.item_progress.emit(row_idx, 100.0, "Completed")

            except Exception as e:
                self.item_status.emit(row_idx, f"Error: {e}")

        self.queue_completed.emit()


class BatchQueueView(QWidget):
    """UI for managing and executing batch processing jobs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.queue_data: List[Dict[str, Any]] = []
        self.worker_thread: Optional[BatchWorkerThread] = None
        self.cancel_token = CancellationToken()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header_box = QVBoxLayout()
        h_lbl = QLabel("Batch Processing Queue")
        h_lbl.setStyleSheet("font-size: 20px; font-weight: 700; color: #F8FAFC;")
        s_lbl = QLabel("Queue multiple lecture videos for automated extraction, transcription, and PDF creation.")
        s_lbl.setStyleSheet("color: #94A3B8; font-size: 13px;")
        header_box.addWidget(h_lbl)
        header_box.addWidget(s_lbl)
        layout.addLayout(header_box)

        # Action Buttons Bar
        btn_bar = QHBoxLayout()
        btn_add = QPushButton("➕ Add Video Files...")
        btn_add.setProperty("class", "SecondaryBtn")
        btn_add.clicked.connect(self._add_files)

        self.btn_start = QPushButton("▶ Process All in Queue")
        self.btn_start.setProperty("class", "PrimaryBtn")
        self.btn_start.clicked.connect(self._start_queue)

        self.btn_cancel = QPushButton("⏹ Cancel Processing")
        self.btn_cancel.setProperty("class", "SecondaryBtn")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_queue)

        btn_clear = QPushButton("Clear Completed")
        btn_clear.setProperty("class", "SecondaryBtn")
        btn_clear.clicked.connect(self._clear_completed)

        btn_bar.addWidget(btn_add)
        btn_bar.addWidget(self.btn_start)
        btn_bar.addWidget(self.btn_cancel)
        btn_bar.addWidget(btn_clear)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        # Queue Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Lecture Name", "File Path", "Status", "Progress"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 140)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Lecture Media Files",
            "",
            "Media Files (*.mp4 *.mkv *.avi *.mov *.webm *.mp3 *.m4a);;All Files (*.*)"
        )
        for f in files:
            p = Path(f)
            self.queue_data.append({
                "name": p.stem.replace("_", " ").title(),
                "path": str(p),
                "status": "Queued",
                "progress": 0.0
            })
        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(len(self.queue_data))
        for idx, item in enumerate(self.queue_data):
            self.table.setItem(idx, 0, QTableWidgetItem(item["name"]))
            self.table.setItem(idx, 1, QTableWidgetItem(item["path"]))
            self.table.setItem(idx, 2, QTableWidgetItem(item["status"]))

            pbar = QProgressBar()
            pbar.setValue(int(item["progress"]))
            self.table.setCellWidget(idx, 3, pbar)

    def _start_queue(self):
        if not self.queue_data:
            QMessageBox.information(self, "Queue Empty", "Add some media files to the queue first.")
            return

        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.cancel_token = CancellationToken()

        self.worker_thread = BatchWorkerThread(self.queue_data, self.cancel_token)
        self.worker_thread.item_progress.connect(self._on_item_progress)
        self.worker_thread.item_status.connect(self._on_item_status)
        self.worker_thread.queue_completed.connect(self._on_queue_completed)
        self.worker_thread.start()

    def _cancel_queue(self):
        self.cancel_token.cancel()
        self.btn_cancel.setEnabled(False)

    @Slot(int, float, str)
    def _on_item_progress(self, row: int, pct: float, msg: str):
        if row < len(self.queue_data):
            self.queue_data[row]["progress"] = pct
            w = self.table.cellWidget(row, 3)
            if isinstance(w, QProgressBar):
                w.setValue(int(pct))

    @Slot(int, str)
    def _on_item_status(self, row: int, status: str):
        if row < len(self.queue_data):
            self.queue_data[row]["status"] = status
            item = self.table.item(row, 2)
            if item:
                item.setText(status)

    @Slot()
    def _on_queue_completed(self):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        QMessageBox.information(self, "Batch Complete", "Batch processing queue has completed!")

    def _clear_completed(self):
        self.queue_data = [x for x in self.queue_data if x["status"] != "Completed"]
        self._refresh_table()
