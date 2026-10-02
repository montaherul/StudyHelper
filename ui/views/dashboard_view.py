"""
Home Dashboard View for LocalStudy.
Displays quick metrics, recent projects, and fast launcher action cards.
"""

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox
)

from core.project_manager import project_manager
from database.db import db
from database.models import Project
from utils.filesystem import format_bytes


class DashboardView(QWidget):
    """Primary home screen providing overview metrics and project access."""

    # Navigation signals
    navigate_to_project = Signal(str)      # project_id
    navigate_to_screenshots = Signal()
    navigate_to_transcriber = Signal()
    create_new_project_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # Header Title
        title_box = QVBoxLayout()
        header_lbl = QLabel("Lecture Processing Dashboard")
        header_lbl.setProperty("class", "SectionTitle")
        header_lbl.setStyleSheet("font-size: 22px; font-weight: 700; color: #F8FAFC;")
        sub_lbl = QLabel("100% Offline Study Material Generator • No AI APIs • Zero Cloud Uploads")
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 13px;")
        title_box.addWidget(header_lbl)
        title_box.addWidget(sub_lbl)
        layout.addLayout(title_box)

        # Quick Stat Cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        self.card_projects = self._create_stat_card("Total Projects", "0", "#38BDF8")
        self.card_slides = self._create_stat_card("Saved Slides", "0", "#34D399")
        self.card_transcripts = self._create_stat_card("Transcripts", "0", "#A78BFA")
        self.card_storage = self._create_stat_card("Local Storage", "0 MB", "#FBBF24")

        stats_layout.addWidget(self.card_projects)
        stats_layout.addWidget(self.card_slides)
        stats_layout.addWidget(self.card_transcripts)
        stats_layout.addWidget(self.card_storage)
        layout.addLayout(stats_layout)

        # Action Cards (Fast Launchers)
        actions_frame = QFrame()
        actions_frame.setProperty("class", "CardFrame")
        actions_layout = QHBoxLayout(actions_frame)
        actions_layout.setContentsMargins(18, 16, 18, 16)
        actions_layout.setSpacing(14)

        btn_new_proj = QPushButton("+ New Lecture Project")
        btn_new_proj.setProperty("class", "PrimaryBtn")
        btn_new_proj.clicked.connect(self.create_new_project_requested.emit)

        btn_quick_ss = QPushButton("📷 Video → PDF Slides")
        btn_quick_ss.setProperty("class", "SecondaryBtn")
        btn_quick_ss.clicked.connect(self.navigate_to_screenshots.emit)

        btn_quick_stt = QPushButton("🎙️ Audio → Transcript (Whisper)")
        btn_quick_stt.setProperty("class", "SecondaryBtn")
        btn_quick_stt.clicked.connect(self.navigate_to_transcriber.emit)

        actions_layout.addWidget(btn_new_proj)
        actions_layout.addWidget(btn_quick_ss)
        actions_layout.addWidget(btn_quick_stt)
        actions_layout.addStretch()
        layout.addWidget(actions_frame)

        # Recent Projects Section
        recents_header = QHBoxLayout()
        recents_lbl = QLabel("Recent Projects")
        recents_lbl.setStyleSheet("font-size: 16px; font-weight: 600; color: #F8FAFC;")
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setProperty("class", "SecondaryBtn")
        btn_refresh.setFixedWidth(90)
        btn_refresh.clicked.connect(self.refresh)
        recents_header.addWidget(recents_lbl)
        recents_header.addStretch()
        recents_header.addWidget(btn_refresh)
        layout.addLayout(recents_header)

        # Table of Projects
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Lecture Name", "Subject", "Course", "Instructor", "Last Modified", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 120)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_row_double_click)
        layout.addWidget(self.table)

    def _create_stat_card(self, title: str, val: str, accent_color: str) -> QFrame:
        frame = QFrame()
        frame.setProperty("class", "CardFrame")
        l = QVBoxLayout(frame)
        l.setContentsMargins(16, 14, 16, 14)
        l.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; text-transform: uppercase; font-weight: 600;")
        val_lbl = QLabel(val)
        val_lbl.setObjectName("ValLabel")
        val_lbl.setStyleSheet(f"color: {accent_color}; font-size: 24px; font-weight: 700;")

        l.addWidget(t_lbl)
        l.addWidget(val_lbl)
        return frame

    def refresh(self):
        """Reloads metrics and table rows from SQLite database."""
        projects = project_manager.list_recent_projects(limit=30)
        
        # Compute metrics
        self.card_projects.findChild(QLabel, "ValLabel").setText(str(len(projects)))

        total_screenshots = 0
        total_storage = 0
        for p in projects:
            p_dir = Path(p.output_path)
            if p_dir.exists():
                try:
                    for f in p_dir.rglob("*"):
                        if f.is_file():
                            total_storage += f.stat().st_size
                except Exception:
                    pass
            ss = db.get_screenshots(p.id)
            total_screenshots += len(ss)

        self.card_slides.findChild(QLabel, "ValLabel").setText(str(total_screenshots))
        self.card_storage.findChild(QLabel, "ValLabel").setText(format_bytes(total_storage))

        # Populate Table
        self.table.setRowCount(len(projects))
        for row_idx, p in enumerate(projects):
            item_name = QTableWidgetItem(p.name)
            item_name.setData(Qt.UserRole, p.id)
            item_subj = QTableWidgetItem(p.subject or "—")
            item_course = QTableWidgetItem(p.course or "—")
            item_teacher = QTableWidgetItem(p.teacher or "—")
            item_date = QTableWidgetItem(p.updated_at[:16].replace("T", " "))

            self.table.setItem(row_idx, 0, item_name)
            self.table.setItem(row_idx, 1, item_subj)
            self.table.setItem(row_idx, 2, item_course)
            self.table.setItem(row_idx, 3, item_teacher)
            self.table.setItem(row_idx, 4, item_date)

            btn_open = QPushButton("Open")
            btn_open.setProperty("class", "PrimaryBtn")
            btn_open.setFixedHeight(26)
            proj_id = p.id
            btn_open.clicked.connect(lambda checked, pid=proj_id: self.navigate_to_project.emit(pid))
            self.table.setCellWidget(row_idx, 5, btn_open)

    def _on_row_double_click(self, index):
        row = index.row()
        item = self.table.item(row, 0)
        if item:
            pid = item.data(Qt.UserRole)
            if pid:
                self.navigate_to_project.emit(pid)
