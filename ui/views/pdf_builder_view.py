"""
PDF Study Guide Builder View for LocalStudy.
Compiles captured lecture slides and metadata into high-quality printable study PDFs.
Dynamically re-syncs projects and available slides.
"""

import os
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QComboBox, QProgressBar, QMessageBox, QGridLayout, QCheckBox
)

from config.constants import PDF_LAYOUTS, PDF_LAYOUT_2UP
from core.project_manager import project_manager
from database.db import db
from database.models import Project
from pdf.generator import pdf_generator


class PdfCompilerThread(QThread):
    """Background thread compiling ReportLab PDF document."""
    progress_updated = Signal(float, str)
    compilation_finished = Signal(bool, str, str)

    def __init__(
        self,
        project: Project,
        layout: str,
        show_timestamp: bool = True,
        time_only: bool = True,
        cover_project_name_only: bool = True
    ):
        super().__init__()
        self.project = project
        self.layout = layout
        self.show_timestamp = show_timestamp
        self.time_only = time_only
        self.cover_project_name_only = cover_project_name_only

    def run(self):
        try:
            screenshots = db.get_screenshots(self.project.id)
            if not screenshots:
                raise ValueError("Project has no screenshots. Extract slides first.")

            out_pdf = Path(self.project.output_path) / "pdf" / f"{self.project.name}_StudyGuide.pdf"
            pdf_path = pdf_generator.compile_pdf(
                project=self.project,
                screenshots=screenshots,
                output_pdf_path=out_pdf,
                layout=self.layout,
                show_timestamp=self.show_timestamp,
                time_only=self.time_only,
                cover_project_name_only=self.cover_project_name_only,
                progress_callback=lambda pct, msg: self.progress_updated.emit(pct, msg)
            )
            self.compilation_finished.emit(True, str(pdf_path), "")
        except Exception as e:
            self.compilation_finished.emit(False, "", str(e))


class PdfBuilderView(QWidget):
    """UI for building and exporting lecture study PDFs."""

    request_extract_slides = Signal(str)  # project_id
    project_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_project: Optional[Project] = None
        self.last_generated_pdf: Optional[str] = None
        self.worker_thread: Optional[PdfCompilerThread] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        header_box = QVBoxLayout()
        h_lbl = QLabel("Study PDF Generator")
        h_lbl.setStyleSheet("font-size: 20px; font-weight: 700; color: #F8FAFC;")
        s_lbl = QLabel("Compile captured lecture frames into structured, printable study guides with custom covers, pagination, and multi-slide layouts.")
        s_lbl.setStyleSheet("color: #94A3B8; font-size: 13px;")
        header_box.addWidget(h_lbl)
        header_box.addWidget(s_lbl)
        layout.addLayout(header_box)

        # Configuration Card
        config_card = QFrame()
        config_card.setProperty("class", "CardFrame")
        grid = QGridLayout(config_card)
        grid.setSpacing(14)

        # Target Project Row
        grid.addWidget(QLabel("Target Project:"), 0, 0)
        proj_row = QHBoxLayout()
        self.combo_project = QComboBox()
        self._populate_projects()
        self.combo_project.currentIndexChanged.connect(self._on_project_changed)
        proj_row.addWidget(self.combo_project)

        btn_new_proj = QPushButton("+ New Project")
        btn_new_proj.setProperty("class", "SecondaryBtn")
        btn_new_proj.setFixedWidth(110)
        btn_new_proj.clicked.connect(self._create_quick_project)
        proj_row.addWidget(btn_new_proj)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setProperty("class", "SecondaryBtn")
        btn_refresh.setFixedWidth(90)
        btn_refresh.clicked.connect(self.refresh)
        proj_row.addWidget(btn_refresh)

        grid.addLayout(proj_row, 0, 1, 1, 2)

        # Slide Count Info
        self.lbl_slide_info = QLabel("Slides: 0 captured")
        self.lbl_slide_info.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600;")
        grid.addWidget(self.lbl_slide_info, 1, 0)

        self.btn_capture_slides = QPushButton("📷 Capture Slides for this Project")
        self.btn_capture_slides.setProperty("class", "SecondaryBtn")
        self.btn_capture_slides.clicked.connect(self._jump_to_capture_slides)
        grid.addWidget(self.btn_capture_slides, 1, 1)

        # Layout Preset
        grid.addWidget(QLabel("PDF Layout:"), 2, 0)
        self.combo_layout = QComboBox()
        for label, val in PDF_LAYOUTS:
            self.combo_layout.addItem(label, val)
        self.combo_layout.setCurrentIndex(1)  # Default 2-up
        grid.addWidget(self.combo_layout, 2, 1, 1, 2)

        # PDF Formatting & Cover options
        self.chk_cover_name_only = QCheckBox("1st Page: Show Project Name only (Clean Title)")
        self.chk_cover_name_only.setChecked(True)
        grid.addWidget(self.chk_cover_name_only, 3, 0, 1, 2)

        self.chk_time_only = QCheckBox("Slides: Show timestamp only (⏱ HH:MM:SS)")
        self.chk_time_only.setChecked(True)
        grid.addWidget(self.chk_time_only, 3, 2)

        self.chk_show_timestamp = QCheckBox("Include timestamps under slides")
        self.chk_show_timestamp.setChecked(True)
        self.chk_show_timestamp.toggled.connect(self.chk_time_only.setEnabled)
        grid.addWidget(self.chk_show_timestamp, 4, 0, 1, 2)

        layout.addWidget(config_card)

        # Execution & Actions Card
        exec_card = QFrame()
        exec_card.setProperty("class", "CardFrame")
        exec_layout = QVBoxLayout(exec_card)
        exec_layout.setSpacing(12)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.lbl_status = QLabel("Ready to compile PDF.")
        self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 12px;")

        exec_layout.addWidget(self.progress_bar)
        exec_layout.addWidget(self.lbl_status)

        btn_row = QHBoxLayout()
        self.btn_compile = QPushButton("📕 Generate Study PDF")
        self.btn_compile.setProperty("class", "PrimaryBtn")
        self.btn_compile.setFixedHeight(36)
        self.btn_compile.clicked.connect(self._start_compilation)

        self.btn_open_pdf = QPushButton("👁️ Open PDF")
        self.btn_open_pdf.setProperty("class", "SecondaryBtn")
        self.btn_open_pdf.setFixedHeight(36)
        self.btn_open_pdf.setEnabled(False)
        self.btn_open_pdf.clicked.connect(self._open_pdf)

        self.btn_open_folder = QPushButton("📂 Open Folder")
        self.btn_open_folder.setProperty("class", "SecondaryBtn")
        self.btn_open_folder.setFixedHeight(36)
        self.btn_open_folder.setEnabled(False)
        self.btn_open_folder.clicked.connect(self._open_folder)

        btn_row.addWidget(self.btn_compile)
        btn_row.addWidget(self.btn_open_pdf)
        btn_row.addWidget(self.btn_open_folder)
        btn_row.addStretch()
        exec_layout.addLayout(btn_row)

        layout.addWidget(exec_card)
        layout.addStretch()

    def refresh(self):
        """Called automatically when view is navigated to or updated."""
        curr_id = self.combo_project.currentData()
        self._populate_projects()
        if curr_id:
            for idx in range(self.combo_project.count()):
                if self.combo_project.itemData(idx) == curr_id:
                    self.combo_project.setCurrentIndex(idx)
                    break
        if self.combo_project.count() > 0:
            self._on_project_changed(self.combo_project.currentIndex())
        else:
            self.lbl_slide_info.setText("No projects available. Click '+ New Project' to create one.")
            self.btn_compile.setEnabled(False)
            self.btn_open_pdf.setEnabled(False)
            self.btn_open_folder.setEnabled(False)

    def set_active_project(self, project_id: str):
        self._populate_projects()
        for idx in range(self.combo_project.count()):
            if self.combo_project.itemData(idx) == project_id:
                self.combo_project.setCurrentIndex(idx)
                break
        self._on_project_changed(self.combo_project.currentIndex())

    def _populate_projects(self):
        self.combo_project.clear()
        projects = project_manager.list_recent_projects(limit=50)
        for p in projects:
            title = f"{p.name}" + (f" ({p.subject})" if p.subject else "")
            self.combo_project.addItem(title, p.id)

    def _create_quick_project(self):
        from ui.views.project_view import NewProjectDialog
        dlg = NewProjectDialog(self)
        if dlg.exec() and dlg.created_project:
            self._populate_projects()
            self.set_active_project(dlg.created_project.id)

    def _jump_to_capture_slides(self):
        pid = self.combo_project.currentData()
        if pid:
            self.request_extract_slides.emit(pid)

    def _on_project_changed(self, index):
        if self.combo_project.count() == 0:
            return
        proj_id = self.combo_project.currentData()
        if not proj_id:
            return

        self.project_selected.emit(proj_id)
        self.active_project = project_manager.load_project_by_id(proj_id)
        if self.active_project:
            ss = db.get_screenshots(self.active_project.id)
            ss_count = len(ss)
            if ss_count > 0:
                self.lbl_slide_info.setText(f"✓ Slides: {ss_count} captured (Ready to compile PDF)")
                self.lbl_slide_info.setStyleSheet("color: #34D399; font-size: 12px; font-weight: 600;")
                self.btn_compile.setEnabled(True)
            else:
                self.lbl_slide_info.setText("⚠ No slides captured yet for this project.")
                self.lbl_slide_info.setStyleSheet("color: #FBBF24; font-size: 12px; font-weight: 500;")
                self.btn_compile.setEnabled(False)

            self.btn_open_folder.setEnabled(True)

            # Check existing PDF
            pdf_dir = Path(self.active_project.output_path) / "pdf"
            pdfs = list(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []
            if pdfs:
                self.last_generated_pdf = str(pdfs[0])
                self.btn_open_pdf.setEnabled(True)
                self.lbl_status.setText(f"Existing PDF: {pdfs[0].name}")
            else:
                self.btn_open_pdf.setEnabled(False)
                self.lbl_status.setText("Ready to compile PDF.")

    def _start_compilation(self):
        if not self.active_project:
            QMessageBox.warning(self, "No Project", "Please select a project first.")
            return

        screenshots = db.get_screenshots(self.active_project.id)
        if not screenshots:
            QMessageBox.warning(
                self,
                "No Screenshots",
                "This project has no screenshots yet.\n\nClick 'Capture Slides for this Project' to extract frames first."
            )
            return

        layout_choice = self.combo_layout.currentData()
        self.btn_compile.setEnabled(False)
        self.btn_open_pdf.setEnabled(False)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Compiling PDF...")

        self.worker_thread = PdfCompilerThread(
            project=self.active_project,
            layout=layout_choice,
            show_timestamp=self.chk_show_timestamp.isChecked(),
            time_only=self.chk_time_only.isChecked(),
            cover_project_name_only=self.chk_cover_name_only.isChecked()
        )
        self.worker_thread.progress_updated.connect(self._on_progress)
        self.worker_thread.compilation_finished.connect(self._on_finished)
        self.worker_thread.start()

    @Slot(float, str)
    def _on_progress(self, pct: float, msg: str):
        self.progress_bar.setValue(int(pct))
        self.lbl_status.setText(msg)

    @Slot(bool, str, str)
    def _on_finished(self, success: bool, pdf_path: str, error: str):
        self.btn_compile.setEnabled(True)
        if success:
            self.last_generated_pdf = pdf_path
            self.btn_open_pdf.setEnabled(True)
            self.progress_bar.setValue(100)
            self.lbl_status.setText(f"Completed! Saved to: {Path(pdf_path).name}")
            self.lbl_status.setStyleSheet("color: #34D399; font-size: 12px; font-weight: 600;")
            reply = QMessageBox.question(
                self,
                "PDF Generated",
                f"Study PDF compiled successfully!\n\nLocation: {pdf_path}\n\nWould you like to open it now?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._open_pdf()
        else:
            self.lbl_status.setText(f"Error: {error}")
            self.lbl_status.setStyleSheet("color: #F87171; font-size: 12px;")
            QMessageBox.critical(self, "Compilation Error", f"Failed to compile PDF:\n{error}")

    def _open_pdf(self):
        if self.last_generated_pdf and Path(self.last_generated_pdf).exists():
            os.startfile(self.last_compiled_pdf if hasattr(self, 'last_compiled_pdf') and self.last_compiled_pdf else self.last_generated_pdf)

    def _open_folder(self):
        if self.active_project and Path(self.active_project.output_path).exists():
            os.startfile(self.active_project.output_path)
