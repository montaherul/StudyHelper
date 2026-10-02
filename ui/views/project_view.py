"""
Project Workspace and Detail View for LocalStudy.
Enables inspecting generated artifacts, opening folders, and launching processing pipelines.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QListWidget, QListWidgetItem, QMessageBox, QDialog, QLineEdit,
    QTextEdit, QFormLayout, QFileDialog
)

from core.project_manager import project_manager
from database.db import db
from database.models import Project
from utils.filesystem import format_bytes


class NewProjectDialog(QDialog):
    """Modal dialog for creating a structured lecture project."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Lecture Project")
        self.setMinimumWidth(480)
        self.created_project: Optional[Project] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title_lbl = QLabel("New Lecture Project")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #38BDF8;")
        layout.addWidget(title_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        self.in_name = QLineEdit()
        self.in_name.setPlaceholderText("e.g. Computer Networks - TCP Handshake")
        self.in_subj = QLineEdit()
        self.in_subj.setPlaceholderText("e.g. Computer Networks")
        self.in_course = QLineEdit()
        self.in_course.setPlaceholderText("e.g. CSE 321")
        self.in_teacher = QLineEdit()
        self.in_teacher.setPlaceholderText("e.g. Dr. Jane Smith")
        self.in_semester = QLineEdit()
        self.in_semester.setPlaceholderText("e.g. Fall 2026")
        self.in_desc = QTextEdit()
        self.in_desc.setPlaceholderText("Key syllabus topics or exam notes...")
        self.in_desc.setFixedHeight(65)

        form.addRow("Project Name *:", self.in_name)
        form.addRow("Subject:", self.in_subj)
        form.addRow("Course Code:", self.in_course)
        form.addRow("Instructor:", self.in_teacher)
        form.addRow("Semester/Term:", self.in_semester)
        form.addRow("Description:", self.in_desc)
        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "SecondaryBtn")
        btn_cancel.clicked.connect(self.reject)

        btn_create = QPushButton("Create Project")
        btn_create.setProperty("class", "PrimaryBtn")
        btn_create.clicked.connect(self._create)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_create)
        layout.addLayout(btn_box)

    def _create(self):
        name = self.in_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Project name is required.")
            return

        self.created_project = project_manager.create_project(
            name=name,
            subject=self.in_subj.text().strip(),
            course=self.in_course.text().strip(),
            teacher=self.in_teacher.text().strip(),
            semester=self.in_semester.text().strip(),
            description=self.in_desc.toPlainText().strip()
        )
        self.accept()


class ProjectView(QWidget):
    """Detailed workspace for a specific lecture project."""

    trigger_extract_screenshots = Signal(str)  # project_id
    trigger_transcribe = Signal(str)           # project_id
    trigger_view_transcript = Signal(str)      # project_id
    trigger_build_pdf = Signal(str)            # project_id
    project_deleted = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_project: Optional[Project] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # Top Bar
        top_bar = QHBoxLayout()
        self.lbl_title = QLabel("Select or Create a Project")
        self.lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #F8FAFC;")
        self.lbl_meta = QLabel("")
        self.lbl_meta.setStyleSheet("color: #94A3B8; font-size: 13px;")

        top_left = QVBoxLayout()
        top_left.addWidget(self.lbl_title)
        top_left.addWidget(self.lbl_meta)
        top_bar.addLayout(top_left)
        top_bar.addStretch()

        self.btn_open_folder = QPushButton("📂 Open Directory")
        self.btn_open_folder.setProperty("class", "SecondaryBtn")
        self.btn_open_folder.clicked.connect(self._open_folder)
        self.btn_open_folder.setEnabled(False)

        self.btn_delete = QPushButton("🗑️ Delete")
        self.btn_delete.setProperty("class", "DangerBtn")
        self.btn_delete.clicked.connect(self._delete_project)
        self.btn_delete.setEnabled(False)

        top_bar.addWidget(self.btn_open_folder)
        top_bar.addWidget(self.btn_delete)
        layout.addLayout(top_bar)

        # Quick Action Buttons Panel
        action_card = QFrame()
        action_card.setProperty("class", "CardFrame")
        action_layout = QHBoxLayout(action_card)
        action_layout.setContentsMargins(14, 12, 14, 12)
        action_layout.setSpacing(12)

        self.btn_extract = QPushButton("📷 Capture Slides")
        self.btn_extract.setProperty("class", "PrimaryBtn")
        self.btn_extract.clicked.connect(lambda: self.active_project and self.trigger_extract_screenshots.emit(self.active_project.id))

        self.btn_transcribe = QPushButton("🎙️ Transcribe Audio")
        self.btn_transcribe.setProperty("class", "PrimaryBtn")
        self.btn_transcribe.clicked.connect(lambda: self.active_project and self.trigger_transcribe.emit(self.active_project.id))

        self.btn_view_ts = QPushButton("📝 Search Transcript")
        self.btn_view_ts.setProperty("class", "SecondaryBtn")
        self.btn_view_ts.clicked.connect(lambda: self.active_project and self.trigger_view_transcript.emit(self.active_project.id))

        self.btn_make_pdf = QPushButton("📕 Study PDF")
        self.btn_make_pdf.setProperty("class", "SecondaryBtn")
        self.btn_make_pdf.clicked.connect(lambda: self.active_project and self.trigger_build_pdf.emit(self.active_project.id))

        for b in [self.btn_extract, self.btn_transcribe, self.btn_view_ts, self.btn_make_pdf]:
            b.setEnabled(False)
            action_layout.addWidget(b)
        action_layout.addStretch()
        layout.addWidget(action_card)

        # Project Artifacts List
        artifacts_lbl = QLabel("Generated Study Materials & Artifacts")
        artifacts_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #F8FAFC;")
        layout.addWidget(artifacts_lbl)

        self.artifacts_list = QListWidget()
        self.artifacts_list.setStyleSheet("font-size: 13px; padding: 6px;")
        self.artifacts_list.itemDoubleClicked.connect(self._on_artifact_double_clicked)
        layout.addWidget(self.artifacts_list)

    def load_project(self, project_id: str):
        proj = project_manager.load_project_by_id(project_id)
        if not proj:
            return

        self.active_project = proj
        self.lbl_title.setText(proj.name)

        tokens = []
        if proj.subject:
            tokens.append(proj.subject)
        if proj.course:
            tokens.append(f"[{proj.course}]")
        if proj.teacher:
            tokens.append(f"Instructor: {proj.teacher}")
        self.lbl_meta.setText("  •  ".join(tokens) or "Local Project")

        self.btn_open_folder.setEnabled(True)
        self.btn_delete.setEnabled(True)
        self.btn_extract.setEnabled(True)
        self.btn_transcribe.setEnabled(True)
        self.btn_view_ts.setEnabled(True)
        self.btn_make_pdf.setEnabled(True)

        self._refresh_artifacts()

    def refresh(self):
        """Called when view is navigated to or updated."""
        if self.active_project:
            self.load_project(self.active_project.id)
        else:
            recents = project_manager.list_recent_projects(limit=1)
            if recents:
                self.load_project(recents[0].id)

    def _refresh_artifacts(self):
        self.artifacts_list.clear()
        if not self.active_project:
            return

        p_dir = Path(self.active_project.output_path)
        if not p_dir.exists():
            return

        # Check PDF
        pdf_dir = p_dir / "pdf"
        if pdf_dir.exists():
            for f in pdf_dir.glob("*.pdf"):
                item = QListWidgetItem(f"📕 Study PDF: {f.name} ({format_bytes(f.stat().st_size)})")
                item.setData(Qt.UserRole, str(f))
                self.artifacts_list.addItem(item)

        # Check Transcripts
        ts_dir = p_dir / "transcript"
        if ts_dir.exists():
            for f in ts_dir.glob("*.*"):
                icon = "📝" if f.suffix == ".txt" else "🎬"
                item = QListWidgetItem(f"{icon} Transcript Track: {f.name} ({format_bytes(f.stat().st_size)})")
                item.setData(Qt.UserRole, str(f))
                self.artifacts_list.addItem(item)

        # Check Screenshots count
        ss_dir = p_dir / "screenshots"
        if ss_dir.exists():
            frames = list(ss_dir.glob("*.jpg"))
            if frames:
                item = QListWidgetItem(f"📷 Extracted Slide Frames: {len(frames)} images in /screenshots/")
                item.setData(Qt.UserRole, str(ss_dir))
                self.artifacts_list.addItem(item)

        # Bookmarks
        bm_file = p_dir / "metadata" / "bookmarks.json"
        if bm_file.exists():
            item = QListWidgetItem("🔖 Saved Lecture Bookmarks: metadata/bookmarks.json")
            item.setData(Qt.UserRole, str(bm_file))
            self.artifacts_list.addItem(item)

        if self.artifacts_list.count() == 0:
            item = QListWidgetItem("No artifacts generated yet. Click 'Capture Slides' or 'Transcribe Audio' above to start.")
            item.setFlags(Qt.NoItemFlags)
            self.artifacts_list.addItem(item)

    def _open_folder(self):
        if not self.active_project:
            return
        folder = Path(self.active_project.output_path)
        if folder.exists():
            os.startfile(str(folder))

    def _on_artifact_double_clicked(self, item: QListWidgetItem):
        f_path = item.data(Qt.UserRole)
        if f_path and Path(f_path).exists():
            os.startfile(str(f_path))

    def _delete_project(self):
        if not self.active_project:
            return
        reply = QMessageBox.question(
            self,
            "Delete Project",
            f"Are you sure you want to delete '{self.active_project.name}'?\n\nThis will remove it from LocalStudy.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            project_manager.delete_project(self.active_project.id, delete_files=False)
            self.active_project = None
            self.project_deleted.emit()
