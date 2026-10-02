"""
Primary Application Window with persistent sidebar navigation for LocalStudy.
Manages global project synchronization and view switching.
"""

from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame,
    QLabel, QPushButton, QStackedWidget, QStatusBar, QMessageBox
)

from config.constants import APP_NAME, APP_SUBTITLE, APP_VERSION
from ui.styles import DARK_THEME_QSS
from ui.views.dashboard_view import DashboardView
from ui.views.project_view import ProjectView, NewProjectDialog
from ui.views.video_downloader_view import VideoDownloaderView
from ui.views.screenshot_view import ScreenshotView
from ui.views.transcriber_view import TranscriberView
from ui.views.transcript_view import TranscriptView
from ui.views.pdf_builder_view import PdfBuilderView
from ui.views.batch_queue_view import BatchQueueView
from ui.views.settings_view import SettingsView


class MainWindow(QMainWindow):
    """Main desktop application window."""

    def __init__(self):
        super().__init__()
        self.active_project_id: Optional[str] = None
        self.setWindowTitle(f"{APP_NAME} — {APP_SUBTITLE} (v{APP_VERSION})")
        self.resize(1200, 800)
        self.setMinimumSize(960, 640)
        self.setStyleSheet(DARK_THEME_QSS)

        self._init_layout()
        self._wire_signals()

    def _init_layout(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left Sidebar Frame
        self.sidebar = QFrame()
        self.sidebar.setObjectName("SidebarFrame")
        self.sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 20)
        sidebar_layout.setSpacing(6)

        # App Brand Header
        logo_box = QVBoxLayout()
        logo_title = QLabel(f"⚡ {APP_NAME}")
        logo_title.setObjectName("AppLogoTitle")
        logo_sub = QLabel("100% Offline Study Suite")
        logo_sub.setObjectName("AppLogoSubtitle")
        logo_box.addWidget(logo_title)
        logo_box.addWidget(logo_sub)
        sidebar_layout.addLayout(logo_box)
        sidebar_layout.addSpacing(18)

        # Nav Buttons
        self.nav_buttons = []

        self.btn_nav_dash = self._create_nav_btn("📊  Dashboard", 0)
        self.btn_nav_proj = self._create_nav_btn("📁  Project Workspace", 1)
        self.btn_nav_down = self._create_nav_btn("🎬  Media Downloader", 2)
        self.btn_nav_ss = self._create_nav_btn("📷  Video Screenshots", 3)
        self.btn_nav_stt = self._create_nav_btn("🎙️  Audio Transcriber", 4)
        self.btn_nav_ts = self._create_nav_btn("📝  Search Transcript", 5)
        self.btn_nav_pdf = self._create_nav_btn("📕  PDF Study Guide", 6)
        self.btn_nav_batch = self._create_nav_btn("⚡  Batch Queue", 7)
        self.btn_nav_set = self._create_nav_btn("⚙️  Settings & Models", 8)

        for btn in [
            self.btn_nav_dash, self.btn_nav_proj, self.btn_nav_down,
            self.btn_nav_ss, self.btn_nav_stt, self.btn_nav_ts,
            self.btn_nav_pdf, self.btn_nav_batch
        ]:
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # Offline Status Badge in Sidebar
        status_box = QFrame()
        status_box.setStyleSheet("background-color: #1E293B; border-radius: 6px; padding: 8px;")
        s_layout = QVBoxLayout(status_box)
        s_layout.setContentsMargins(6, 6, 6, 6)
        s_lbl = QLabel("🟢 Offline Mode Active")
        s_lbl.setStyleSheet("color: #34D399; font-size: 11px; font-weight: 600;")
        s_sub = QLabel("No AI tokens • Local execution")
        s_sub.setStyleSheet("color: #94A3B8; font-size: 10px;")
        s_layout.addWidget(s_lbl)
        s_layout.addWidget(s_sub)
        sidebar_layout.addWidget(status_box)
        sidebar_layout.addSpacing(8)

        sidebar_layout.addWidget(self.btn_nav_set)
        main_layout.addWidget(self.sidebar)

        # Stacked Views Container
        self.stack = QStackedWidget()
        self.view_dashboard = DashboardView()
        self.view_project = ProjectView()
        self.view_downloader = VideoDownloaderView()
        self.view_screenshot = ScreenshotView()
        self.view_transcriber = TranscriberView()
        self.view_transcript = TranscriptView()
        self.view_pdf = PdfBuilderView()
        self.view_batch = BatchQueueView()
        self.view_settings = SettingsView()

        self.stack.addWidget(self.view_dashboard)     # Index 0
        self.stack.addWidget(self.view_project)       # Index 1
        self.stack.addWidget(self.view_downloader)    # Index 2
        self.stack.addWidget(self.view_screenshot)    # Index 3
        self.stack.addWidget(self.view_transcriber)   # Index 4
        self.stack.addWidget(self.view_transcript)    # Index 5
        self.stack.addWidget(self.view_pdf)           # Index 6
        self.stack.addWidget(self.view_batch)         # Index 7
        self.stack.addWidget(self.view_settings)      # Index 8

        main_layout.addWidget(self.stack)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. All media processing runs 100% locally on your machine.")

        # Activate initial view
        self._switch_view(0)

    def _create_nav_btn(self, text: str, view_index: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("class", "NavBtn")
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.clicked.connect(lambda: self._switch_view(view_index))
        self.nav_buttons.append(btn)
        return btn

    def _switch_view(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        # Refresh target view so data and projects are always current
        current_widget = self.stack.currentWidget()
        if hasattr(current_widget, "refresh"):
            current_widget.refresh()

    def _wire_signals(self):
        # Dashboard signals
        self.view_dashboard.navigate_to_project.connect(self._open_project_in_workspace)
        self.view_dashboard.navigate_to_screenshots.connect(lambda: self._switch_view(3))
        self.view_dashboard.navigate_to_transcriber.connect(lambda: self._switch_view(4))
        self.view_dashboard.create_new_project_requested.connect(self._prompt_new_project)

        # Downloader view navigation bridges
        self.view_downloader.send_to_screenshots.connect(self._handle_send_to_screenshots)
        self.view_downloader.send_to_transcriber.connect(self._handle_send_to_transcriber)

        # Project view signals
        self.view_project.trigger_extract_screenshots.connect(self._go_to_screenshots_for_project)
        self.view_project.trigger_transcribe.connect(self._go_to_transcribe_for_project)
        self.view_project.trigger_view_transcript.connect(self._go_to_transcript_for_project)
        self.view_project.trigger_build_pdf.connect(self._go_to_pdf_for_project)
        self.view_project.project_deleted.connect(lambda: self._switch_view(0))

        # PDF view jump back to screenshot extractor
        self.view_pdf.request_extract_slides.connect(self._go_to_screenshots_for_project)

        # Global project synchronization across views
        self.view_screenshot.project_selected.connect(self._sync_active_project)
        self.view_transcriber.project_selected.connect(self._sync_active_project)
        self.view_pdf.project_selected.connect(self._sync_active_project)

    def _handle_send_to_screenshots(self, file_path: str):
        """Pre-loads downloaded video into ScreenshotView and switches to that tab."""
        self.view_screenshot.load_media_file(file_path)
        self._switch_view(3)
        self.status_bar.showMessage(f"Loaded {Path(file_path).name} into Screenshot Studio.")

    def _handle_send_to_transcriber(self, file_path: str):
        """Pre-loads downloaded media into TranscriberView and switches to that tab."""
        self.view_transcriber.load_media_file(file_path)
        self._switch_view(4)
        self.status_bar.showMessage(f"Loaded {Path(file_path).name} into Audio Transcriber.")

    def _sync_active_project(self, project_id: str):
        if not project_id or project_id == self.active_project_id:
            return
        self.active_project_id = project_id
        for view in [
            self.view_downloader, self.view_screenshot,
            self.view_transcriber, self.view_transcript, self.view_pdf
        ]:
            if hasattr(view, "set_active_project"):
                view.blockSignals(True)
                view.set_active_project(project_id)
                view.blockSignals(False)

    def _open_project_in_workspace(self, project_id: str):
        self._sync_active_project(project_id)
        self.view_project.load_project(project_id)
        self._switch_view(1)

    def _prompt_new_project(self):
        dlg = NewProjectDialog(self)
        if dlg.exec() and dlg.created_project:
            pid = dlg.created_project.id
            self._sync_active_project(pid)
            self.view_project.load_project(pid)
            self._switch_view(1)

    def _go_to_screenshots_for_project(self, project_id: str):
        self._sync_active_project(project_id)
        self.view_screenshot.set_active_project(project_id)
        self._switch_view(3)

    def _go_to_transcribe_for_project(self, project_id: str):
        self._sync_active_project(project_id)
        self.view_transcriber.set_active_project(project_id)
        self._switch_view(4)

    def _go_to_transcript_for_project(self, project_id: str):
        self._sync_active_project(project_id)
        self.view_transcript.set_active_project(project_id)
        self._switch_view(5)

    def _go_to_pdf_for_project(self, project_id: str):
        self._sync_active_project(project_id)
        self.view_pdf.set_active_project(project_id)
        self._switch_view(6)
