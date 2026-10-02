"""
Interactive Transcript Search & Synchronized Study Viewer for LocalStudy.
Powered by SQLite FTS5 for sub-millisecond keyword lookup.
"""

import os
from pathlib import Path
from typing import Optional, List
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QAbstractItemView, QMessageBox, QDialog, QFormLayout, QTextEdit
)

from core.bookmark_service import bookmark_service
from core.project_manager import project_manager
from database.db import db
from database.models import Project, TranscriptSegment
from utils.time_utils import seconds_to_hms


class AddBookmarkDialog(QDialog):
    """Dialog to create a study bookmark with notes."""

    def __init__(self, project_id: str, timestamp: float, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.timestamp = timestamp
        self.setWindowTitle(f"Add Bookmark at {seconds_to_hms(timestamp)}")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.in_title = QLineEdit()
        self.in_title.setPlaceholderText("e.g. TCP Handshake Explained")
        self.combo_cat = QComboBox()
        self.combo_cat.addItem("⭐ Exam Topic", "exam_topic")
        self.combo_cat.addItem("💡 Core Concept", "concept")
        self.combo_cat.addItem("❓ Question / Clarify", "question")
        self.combo_cat.addItem("📝 Formula / Code", "formula")
        self.combo_cat.addItem("📌 General Bookmark", "general")

        self.in_note = QTextEdit()
        self.in_note.setPlaceholderText("Detailed lecture notes or exam tips...")
        self.in_note.setFixedHeight(80)

        form.addRow("Title *:", self.in_title)
        form.addRow("Category:", self.combo_cat)
        form.addRow("Notes:", self.in_note)
        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "SecondaryBtn")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Save Bookmark")
        btn_save.setProperty("class", "PrimaryBtn")
        btn_save.clicked.connect(self._save)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def _save(self):
        title = self.in_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation", "Bookmark title is required.")
            return

        bookmark_service.add_bookmark(
            project_id=self.project_id,
            timestamp=self.timestamp,
            title=title,
            category=self.combo_cat.currentData(),
            note=self.in_note.toPlainText().strip()
        )
        self.accept()


class TranscriptView(QWidget):
    """Searchable lecture transcript viewer with FTS5 search and bookmarking."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_project: Optional[Project] = None
        self.segments: List[TranscriptSegment] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header Box
        header_box = QVBoxLayout()
        h_lbl = QLabel("Searchable Lecture Transcript")
        h_lbl.setStyleSheet("font-size: 20px; font-weight: 700; color: #F8FAFC;")
        s_lbl = QLabel("Search spoken words instantly with SQLite FTS5. Bookmark key exam topics and jump to timestamps.")
        s_lbl.setStyleSheet("color: #94A3B8; font-size: 13px;")
        header_box.addWidget(h_lbl)
        header_box.addWidget(s_lbl)
        layout.addLayout(header_box)

        # Search & Project Bar
        search_card = QFrame()
        search_card.setProperty("class", "CardFrame")
        search_layout = QHBoxLayout(search_card)
        search_layout.setContentsMargins(12, 10, 12, 10)
        search_layout.setSpacing(12)

        self.combo_project = QComboBox()
        self.combo_project.setFixedWidth(240)
        self._populate_projects()
        self.combo_project.currentIndexChanged.connect(self._on_project_changed)
        search_layout.addWidget(self.combo_project)

        self.in_search = QLineEdit()
        self.in_search.setPlaceholderText("🔍 Type keyword (e.g. 'handshake', 'OSI model', 'normalization')...")
        self.in_search.textChanged.connect(self._on_search_query_changed)
        search_layout.addWidget(self.in_search)

        btn_clear = QPushButton("Clear")
        btn_clear.setProperty("class", "SecondaryBtn")
        btn_clear.setFixedWidth(70)
        btn_clear.clicked.connect(lambda: self.in_search.clear())
        search_layout.addWidget(btn_clear)

        layout.addWidget(search_card)

        # Result Count & Quick Export Links
        bar = QHBoxLayout()
        self.lbl_count = QLabel("0 segments found")
        self.lbl_count.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")
        bar.addWidget(self.lbl_count)
        bar.addStretch()

        self.btn_open_txt = QPushButton("📄 Open TXT")
        self.btn_open_txt.setProperty("class", "SecondaryBtn")
        self.btn_open_txt.clicked.connect(lambda: self._open_transcript_file("transcript.txt"))

        self.btn_open_srt = QPushButton("🎬 Open SRT")
        self.btn_open_srt.setProperty("class", "SecondaryBtn")
        self.btn_open_srt.clicked.connect(lambda: self._open_transcript_file("transcript.srt"))

        bar.addWidget(self.btn_open_txt)
        bar.addWidget(self.btn_open_srt)
        layout.addLayout(bar)

        # Transcript Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Spoken Transcript", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 110)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 120)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

    def refresh(self):
        """Called automatically when view becomes visible to update project dropdown."""
        curr_id = self.combo_project.currentData()
        self._populate_projects()
        if curr_id:
            for idx in range(self.combo_project.count()):
                if self.combo_project.itemData(idx) == curr_id:
                    self.combo_project.setCurrentIndex(idx)
                    break
        if self.combo_project.count() > 0:
            self._load_current_project()

    def set_active_project(self, project_id: str):
        self._populate_projects()
        for idx in range(self.combo_project.count()):
            if self.combo_project.itemData(idx) == project_id:
                self.combo_project.setCurrentIndex(idx)
                break
        self._load_current_project()

    def _populate_projects(self):
        self.combo_project.clear()
        projects = project_manager.list_recent_projects(limit=50)
        for p in projects:
            self.combo_project.addItem(f"{p.name}", p.id)

    def _on_project_changed(self, index):
        self._load_current_project()

    def _load_current_project(self):
        if self.combo_project.count() == 0:
            return
        proj_id = self.combo_project.currentData()
        self.active_project = project_manager.load_project_by_id(proj_id)
        self._on_search_query_changed(self.in_search.text())

    def _on_search_query_changed(self, query: str):
        if not self.active_project:
            self.table.setRowCount(0)
            self.lbl_count.setText("No project loaded")
            return

        query = query.strip()
        if query:
            results = db.search_transcript(self.active_project.id, query)
        else:
            results = db.get_transcript_segments(self.active_project.id)

        self.segments = results
        self.lbl_count.setText(f"Showing {len(results)} segments" + (f" for '{query}'" if query else ""))
        self._populate_table(results)

    def _populate_table(self, segments: List[TranscriptSegment]):
        self.table.setRowCount(len(segments))
        for row, s in enumerate(segments):
            t_str = seconds_to_hms(s.start_time)
            item_ts = QTableWidgetItem(f"⏱ {t_str}")
            item_ts.setTextAlignment(Qt.AlignCenter)
            item_ts.setForeground(Qt.GlobalColor.cyan)

            item_text = QTableWidgetItem(s.text)

            self.table.setItem(row, 0, item_ts)
            self.table.setItem(row, 1, item_text)

            btn_bm = QPushButton("⭐ Bookmark")
            btn_bm.setProperty("class", "SecondaryBtn")
            btn_bm.setFixedHeight(24)
            ts_val = s.start_time
            pid = self.active_project.id
            btn_bm.clicked.connect(lambda ch, t=ts_val, p=pid: self._add_bookmark(p, t))
            self.table.setCellWidget(row, 2, btn_bm)

    def _add_bookmark(self, project_id: str, timestamp: float):
        dlg = AddBookmarkDialog(project_id, timestamp, self)
        if dlg.exec():
            QMessageBox.information(self, "Bookmark Added", f"Bookmark saved at {seconds_to_hms(timestamp)}!")

    def _open_transcript_file(self, filename: str):
        if not self.active_project:
            return
        f = Path(self.active_project.output_path) / "transcript" / filename
        if f.exists():
            os.startfile(str(f))
        else:
            QMessageBox.information(self, "File Not Found", f"{filename} has not been generated for this project yet.")
