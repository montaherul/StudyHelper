"""
Application Settings & Hardware Profiler View for LocalStudy.
Enables offline model management and hardware tuning.
"""

from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QSpinBox, QGridLayout, QProgressBar
)

from config.settings import settings
from core.hardware_detector import HardwareDetector
from transcription.model_manager import model_manager


class ModelDownloadThread(QThread):
    progress = Signal(float, str)
    finished = Signal(bool, str)

    def __init__(self, model_id: str):
        super().__init__()
        self.model_id = model_id

    def run(self):
        try:
            model_manager.download_model(
                self.model_id,
                progress_callback=lambda pct, msg: self.progress.emit(pct, msg)
            )
            self.finished.emit(True, f"Model '{self.model_id}' successfully downloaded!")
        except Exception as e:
            self.finished.emit(False, str(e))


class SettingsView(QWidget):
    """Configuration and local model management view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.download_thread: Optional[ModelDownloadThread] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        header_box = QVBoxLayout()
        h_lbl = QLabel("System Settings & Model Manager")
        h_lbl.setStyleSheet("font-size: 20px; font-weight: 700; color: #F8FAFC;")
        s_lbl = QLabel("Manage offline AI models, configure directory paths, and inspect hardware performance profile.")
        s_lbl.setStyleSheet("color: #94A3B8; font-size: 13px;")
        header_box.addWidget(h_lbl)
        header_box.addWidget(s_lbl)
        layout.addLayout(header_box)

        # Hardware Profile Card
        hw = HardwareDetector.get_hardware_info()
        hw_card = QFrame()
        hw_card.setProperty("class", "CardFrame")
        hw_layout = QGridLayout(hw_card)
        hw_layout.setSpacing(10)

        hw_title = QLabel("🖥️ Detected Hardware & Auto-Tuning Profile")
        hw_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #38BDF8;")
        hw_layout.addWidget(hw_title, 0, 0, 1, 2)

        hw_layout.addWidget(QLabel("Processor (CPU):"), 1, 0)
        hw_layout.addWidget(QLabel(f"<b>{hw['cpu_model']}</b> ({hw['cpu_threads']} Threads)"), 1, 1)

        hw_layout.addWidget(QLabel("System Memory (RAM):"), 2, 0)
        hw_layout.addWidget(QLabel(f"<b>{hw['ram_gb']} GB RAM</b>"), 2, 1)

        hw_layout.addWidget(QLabel("Acceleration Engine:"), 3, 0)
        accel_text = "NVIDIA CUDA GPU" if hw['has_cuda'] else "AMD / CPU int8 CTranslate2 (Optimized)"
        hw_layout.addWidget(QLabel(f"<b>{accel_text}</b>"), 3, 1)

        layout.addWidget(hw_card)

        # Model Manager Card
        model_card = QFrame()
        model_card.setProperty("class", "CardFrame")
        model_layout = QVBoxLayout(model_card)
        model_layout.setSpacing(10)

        m_title = QLabel("🧠 Offline Whisper Models (Download Once, Run Forever Offline)")
        m_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #34D399;")
        model_layout.addWidget(m_title)

        self.model_table = QTableWidget()
        self.model_table.setColumnCount(4)
        self.model_table.setHorizontalHeaderLabels(["Model Tier", "Description", "Status", "Action"])
        self.model_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.model_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.model_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.model_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.model_table.setColumnWidth(3, 130)
        self.model_table.setFixedHeight(180)
        model_layout.addWidget(self.model_table)

        self.model_progress = QProgressBar()
        self.model_progress.setValue(0)
        self.model_progress.setVisible(False)
        self.lbl_download_status = QLabel("")
        self.lbl_download_status.setStyleSheet("color: #38BDF8; font-size: 12px;")
        model_layout.addWidget(self.model_progress)
        model_layout.addWidget(self.lbl_download_status)

        layout.addWidget(model_card)

        # Storage Directories Card
        dir_card = QFrame()
        dir_card.setProperty("class", "CardFrame")
        dir_layout = QGridLayout(dir_card)
        dir_layout.setSpacing(12)

        d_title = QLabel("📁 Storage & Directories")
        d_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FBBF24;")
        dir_layout.addWidget(d_title, 0, 0, 1, 3)

        dir_layout.addWidget(QLabel("Default Projects Directory:"), 1, 0)
        self.in_proj_dir = QLineEdit(settings.get("projects_dir"))
        btn_browse_proj = QPushButton("Browse...")
        btn_browse_proj.setProperty("class", "SecondaryBtn")
        btn_browse_proj.clicked.connect(self._browse_projects_dir)
        dir_layout.addWidget(self.in_proj_dir, 1, 1)
        dir_layout.addWidget(btn_browse_proj, 1, 2)

        dir_layout.addWidget(QLabel("CPU Worker Threads:"), 2, 0)
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 32)
        self.spin_threads.setValue(settings.get("cpu_threads", 4))
        dir_layout.addWidget(self.spin_threads, 2, 1)

        btn_save = QPushButton("💾 Save Preferences")
        btn_save.setProperty("class", "PrimaryBtn")
        btn_save.setFixedWidth(160)
        btn_save.clicked.connect(self._save_settings)
        dir_layout.addWidget(btn_save, 3, 0)

        layout.addWidget(dir_card)
        layout.addStretch()

        self._refresh_models()

    def _refresh_models(self):
        models = model_manager.get_models_status()
        self.model_table.setRowCount(len(models))

        for idx, m in enumerate(models):
            self.model_table.setItem(idx, 0, QTableWidgetItem(m["name"]))
            self.model_table.setItem(idx, 1, QTableWidgetItem(m["description"]))

            status_str = f"✓ Installed ({m['size_on_disk_str']})" if m["installed"] else "Not Downloaded"
            item_st = QTableWidgetItem(status_str)
            item_st.setForeground(Qt.GlobalColor.green if m["installed"] else Qt.GlobalColor.gray)
            self.model_table.setItem(idx, 2, item_st)

            btn_dl = QPushButton("⬇️ Download" if not m["installed"] else "Re-download")
            btn_dl.setProperty("class", "SecondaryBtn")
            btn_dl.setFixedHeight(24)
            m_id = m["id"]
            btn_dl.clicked.connect(lambda ch, mid=m_id: self._download_model(mid))
            self.model_table.setCellWidget(idx, 3, btn_dl)

    def _download_model(self, model_id: str):
        self.model_progress.setVisible(True)
        self.model_progress.setValue(10)
        self.lbl_download_status.setText(f"Connecting to download '{model_id}' weights...")

        self.download_thread = ModelDownloadThread(model_id)
        self.download_thread.progress.connect(self._on_model_progress)
        self.download_thread.finished.connect(self._on_model_finished)
        self.download_thread.start()

    @Slot(float, str)
    def _on_model_progress(self, pct: float, msg: str):
        self.model_progress.setValue(int(pct))
        self.lbl_download_status.setText(msg)

    @Slot(bool, str)
    def _on_model_finished(self, success: bool, msg: str):
        self._refresh_models()
        self.model_progress.setVisible(False)
        self.lbl_download_status.setText("")
        if success:
            QMessageBox.information(self, "Model Ready", msg)
        else:
            QMessageBox.critical(self, "Download Error", f"Failed to download model:\n{msg}")

    def _browse_projects_dir(self):
        p = QFileDialog.getExistingDirectory(self, "Select Projects Base Directory", self.in_proj_dir.text())
        if p:
            self.in_proj_dir.setText(p)

    def _save_settings(self):
        settings.set("projects_dir", self.in_proj_dir.text().strip())
        settings.set("cpu_threads", self.spin_threads.value())
        settings.save()
        QMessageBox.information(self, "Saved", "Settings saved successfully!")
