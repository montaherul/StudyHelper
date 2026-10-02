# AGENT INSTRUCTIONS & OPERATIONAL PROTOCOLS
## LocalStudy — Offline Lecture Processing Toolkit

> **System Classification:** Offline-First Desktop Application  
> **Target Framework:** Python 3.11+ / PySide6 (Qt)  
> **Hardware Baseline:** AMD Ryzen 7 5600G (6C/12T), 16GB RAM, Integrated Radeon Graphics  
> **Core Mandate:** **100% Local Inference & Processing. Zero Cloud APIs. Zero Remote Telemetry. Zero Token Billing.**

---

## 1. Prime Directive & Non-Negotiable Constraints

Every agent, developer, or automated assistant contributing to this repository MUST strictly abide by the following operational boundaries:

1. **Zero External AI / LLM APIs:**
   - Under NO circumstances shall any code introduce API clients, HTTP wrappers, or dependencies pointing to OpenAI, Google Cloud Gemini/Vertex, Anthropic Claude, Azure OpenAI, AWS Bedrock, or any hosted inference service.
   - Speech-to-text inference must run **strictly locally** via `faster-whisper` (CTranslate2) or ONNX/Whisper.cpp equivalents executing on the host machine's CPU/GPU.
   - No feature may require an API key, bearer token, credit card, or external authentication token.

2. **100% Air-Gapped & Offline Operability:**
   - Once initial Python dependencies and pre-trained local model weights are acquired, all primary features (video decoding, frame extraction, audio extraction, local transcription, PDF compilation, search, bookmarks, project exports) must function seamlessly without an active internet connection.
   - For remote URL ingestion (e.g. user-authorized web lecture links), network calls must be isolated strictly to the video fetcher module (`yt-dlp` / direct stream puller) with explicit permission handling. The core application must gracefully handle full offline mode.

3. **User Privacy & Data Sovereignty:**
   - No telemetry, analytics, telemetry pings, crash report uploads, or phone-home beacons may be added to any module.
   - User media, transcripts, notes, and metadata reside exclusively within the project directory structure configured by the user on their local filesystem.

4. **Safe Subprocess Execution & System Integrity:**
   - Never invoke shell commands using unsanitized string interpolation or `shell=True` in `subprocess`. Always pass argument arrays: `subprocess.run(["ffmpeg", "-y", "-i", ...], ...)`.
   - Validate and sanitize all user input paths, project folder names, and URL targets to prevent path traversal (`../../`) and command injection.

5. **Responsive, Non-Blocking UI Architecture:**
   - Long-running processes (FFmpeg frame extraction, audio separation, model downloading, Whisper transcription, PDF compilation) must **NEVER** run on the Qt UI thread.
   - All background tasks must inherit from `QRunnable` or `QThread` managed via `QThreadPool`, communicating state and progress through Qt Signals (`pyqtSignal` / `Signal`).

---

## 2. Technical Stack Reference

| Layer | Technology | Rationale & Guidelines |
| :--- | :--- | :--- |
| **Runtime** | Python 3.11 / 3.12 | Optimal performance, broad C-extension compatibility. |
| **GUI Framework** | `PySide6` (Qt 6) | Native cross-platform performance, rich widgets, QThread integration. |
| **Styling** | Custom Qt Style Sheets (QSS) | Dark-mode primary, modern accessible contrast, sleek typography. |
| **Video Processing** | `ffmpeg`, `ffprobe`, `opencv-python` | High-throughput frame extraction, hardware acceleration flags where available. |
| **Audio Processing** | `ffmpeg` | Extraction & resample to 16kHz mono WAV for Whisper. |
| **Transcription** | `faster-whisper` (CTranslate2) | 4x faster than vanilla Whisper, 8-bit quantization (`int8`), optimal for Ryzen 5600G. |
| **PDF Generation** | `reportlab` | High-fidelity canvas control, custom layouts (1, 2, 4-up), table of contents. |
| **Image Processing** | `Pillow` (PIL), `opencv-python` | Aspect-ratio preserving resizing, timestamp overlay drawing. |
| **Database** | `sqlite3` / `SQLAlchemy 2.0` | Zero-configuration local relational persistence, FTS5 full-text search. |
| **Packaging** | `PyInstaller` | Standalone single-directory or single-file Windows executable (`LocalStudy.exe`). |

---

## 3. Repository Architecture & Directory Structure

All agents must adhere to the standardized repository structure:

```text
localstudy/
├── app.py                      # Main application entry point & Qt Application lifecycle
├── requirements.txt            # Locked Python package specifications
├── setup.py / pyproject.toml   # Project build & packaging specification
├── agent.md                    # Agent instructions, engineering protocols, constraints
├── roadmap.md                  # Milestone tracker, phase breakdown & sprint checklist
├── full_documentation.md       # Comprehensive system specification & manual
│
├── config/
│   ├── __init__.py
│   ├── settings.py             # User preferences, default paths, hardware profiles
│   └── constants.py            # App-wide constants, model lists, default intervals
│
├── core/
│   ├── __init__.py
│   ├── project_manager.py      # Project lifecycle, disk hierarchy, manifest CRUD
│   ├── job_manager.py          # Background worker pool, queueing, pause/resume/cancel
│   ├── hardware_detector.py    # CPU cores, RAM, GPU detection, recommended presets
│   └── events.py               # Application-level event buses and Qt signals
│
├── database/
│   ├── __init__.py
│   ├── connection.py           # SQLite connection pool & session factory
│   ├── schema.sql              # Raw SQL DDL with FTS5 virtual tables
│   ├── models.py               # SQLAlchemy ORM entity definitions
│   └── repositories.py         # Data Access Objects (DAO) for projects, segments, bookmarks
│
├── video/
│   ├── __init__.py
│   ├── analyzer.py             # ffprobe video metadata extractor (duration, fps, resolution)
│   ├── frame_extractor.py      # Fixed interval and smart timestamp frame extraction
│   ├── timestamp_overlay.py    # OpenCV/Pillow text rendering on captured frames
│   └── downloader.py           # yt-dlp wrapper with permission validation & progress hooks
│
├── transcription/
│   ├── __init__.py
│   ├── audio_extractor.py      # FFmpeg 16kHz mono conversion pipeline
│   ├── engine.py               # faster-whisper inference wrapper & quantization manager
│   ├── model_manager.py        # Local model cache, downloader with checksums, offline detector
│   ├── segment_processor.py    # Transcript segment normalization & timestamp formatting
│   └── exporters.py            # TXT, SRT, VTT, and JSON export generators
│
├── pdf/
│   ├── __init__.py
│   ├── generator.py            # ReportLab document compiler & build orchestrator
│   ├── layouts.py              # Page layout engines (1-up, 2-up, 4-up, contact sheet)
│   ├── canvas_builder.py       # Custom canvas for page numbering, headers, and footers
│   └── metadata_page.py        # Lecture summary, TOC, and metadata cover generator
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py          # Primary application window with sidebar navigation
│   ├── styles.py               # Unified QSS theme tokens, dark/light palette
│   ├── views/
│   │   ├── dashboard_view.py       # Home dashboard, recent projects, quick action cards
│   │   ├── project_view.py         # Active project workspace & file explorer
│   │   ├── video_downloader_view.py# Dedicated media downloader (cookies, formats, audio, clips)
│   │   ├── screenshot_view.py      # Screenshot capture config, interval slider, Auto-PDF
│   │   ├── transcriber_view.py     # Transcribe setup, model selector, language dropdown
│   │   ├── transcript_view.py      # Searchable transcript table, synced video player
│   │   ├── pdf_builder_view.py     # PDF layout selector, margin controls, preview
│   │   ├── batch_queue_view.py     # Multi-lecture job queue & progress tracker
│   │   └── settings_view.py        # Hardware profile, local models manager, paths
│   └── components/
│       ├── progress_dialog.py      # Reusable progress bar with cancel/pause hooks
│       ├── video_player.py         # Embedded QtMultimedia / QMediaPlayer widget
│       ├── timestamp_input.py      # Custom widget for time formatting (HH:MM:SS)
│       └── bookmark_card.py        # Interactive bookmark item widget
│
├── utils/
│   ├── __init__.py
│   ├── logger.py               # Rotating file & console logger with timestamps
│   ├── filesystem.py           # Safe path sanitization, disk space calculation
│   ├── time_utils.py           # Milliseconds/seconds to HH:MM:SS,ms converters
│   └── validation.py           # Input schema checkers, URL validators
│
├── tests/
│   ├── test_video.py           # Frame extraction & ffprobe parsing tests
│   ├── test_transcription.py   # Audio extraction & mock Whisper tests
│   ├── test_pdf.py             # PDF layout calculation & compilation tests
│   ├── test_database.py        # SQLite migrations & FTS5 search queries tests
│   └── test_projects.py        # Project directory lifecycle & export tests
│
└── data/
    ├── models/                 # Cached faster-whisper weights (tiny, base, small, etc.)
    └── projects/               # Default directory for student lecture projects
```

---

## 4. Coding Standards & Agent Guidelines

### 4.1. Concurrency & Qt Threading Rules
1. **Never block the GUI thread:** Long loops, file I/O over 10MB, FFmpeg calls, and ML inference must run in a separate `QThread` or `QRunnable`.
2. **Signal-Slot Communication:** Worker threads must NEVER directly touch Qt UI widgets. Communicate exclusively using Qt signals:
   ```python
   class ExtractionWorker(QRunnable):
       class Signals(QObject):
           progress = Signal(int, str)  # percent, status message
           finished = Signal(dict)       # result payload
           error = Signal(str)          # human-readable error description
   ```
3. **Cancellation Token:** Every worker must check an atomic `is_cancelled` flag between iterations (e.g. after every extracted frame or transcription segment) to immediately cease execution when requested by the user.

### 4.2. Subprocess & FFmpeg Execution
1. Always resolve the FFmpeg executable path dynamically (bundled binary, environment PATH, or configured setting).
2. Avoid shell parsing vulnerabilities:
   ```python
   # STRICTLY FORBIDDEN:
   # subprocess.run(f"ffmpeg -i {filepath} ...", shell=True)

   # MANDATORY:
   cmd = [
       ffmpeg_path,
       "-y",
       "-ss", str(timestamp_seconds),
       "-i", str(input_video_path),
       "-vframes", "1",
       "-q:v", "2",
       str(output_image_path)
   ]
   subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
   ```

### 4.3. Audio & Transcription Best Practices
1. **Audio Pre-processing:** Always extract and convert video audio to 16,000 Hz, 16-bit mono PCM (`pcm_s16le`) WAV before feeding to `faster-whisper`. This reduces inference overhead by up to 50%.
2. **Compute Type Selection:**
   - On CPU (e.g. AMD Ryzen 5600G): Default to `compute_type="int8"` with `cpu_threads=4` to keep UI fluid.
   - If CUDA is detected: Allow `float16` or `int8_float16`.
3. **Bangla & Multi-lingual Support:**
   - Expose explicit language selection (`"bn"` for Bangla, `"en"` for English, `"hi"` for Hindi, etc.) alongside auto-detection.
   - For mixed Bangla-English technical lectures, recommend Whisper `small` or `medium` for optimal phoneme resolution.

### 4.4. PDF Generation Architecture
1. Use ReportLab's `SimpleDocTemplate` and flowables for dynamic content, combined with `NumberedCanvas` for exact page counts ("Page X of Y").
2. Protect against memory exhaustion when handling hundreds of high-resolution images:
   - Calculate scaled bounding boxes before creating ReportLab `Image` objects.
   - Release intermediate image buffers immediately.
3. Support selectable layouts:
   - **1-Up:** 1 screenshot per page with detailed title, timestamp, and notes section.
   - **2-Up:** 2 screenshots stacked vertically with timestamp badges.
   - **4-Up:** 2x2 grid for slide decks and high-volume lectures.
   - **Contact Sheet:** Compact multi-column grid for visual skimming.

### 4.5. Data Persistence & Full-Text Search (FTS)
1. Use SQLite with `PRAGMA foreign_keys = ON;` and `PRAGMA journal_mode = WAL;`.
2. Transcripts must be indexed in an `FTS5` virtual table to enable instantaneous sub-millisecond keyword queries across 4-hour lectures.
3. Keep the file system and SQLite database in continuous synchronization: every saved frame or segment writes to both disk and database within a single transaction.

---

## 5. Agent Verification & Definition of Done

Before marking any subtask or feature as complete, the agent must verify:
- [ ] Code runs without syntax errors under Python 3.11+.
- [ ] No remote API tokens or AI cloud SDKs are imported or required.
- [ ] Error states return human-friendly alerts rather than raw tracebacks.
- [ ] Unit tests pass for the modified modules.
- [ ] Output artifacts (images, PDFs, SRT, VTT, TXT) comply with naming conventions (`lecture_00h00m00s.jpg`, etc.).
- [ ] Resource cleanup is verified (temporary WAVs deleted if user selects auto-cleanup).
- [ ] UI remains responsive (>60 FPS) during background batch jobs.
