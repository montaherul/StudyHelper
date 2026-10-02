# IMPLEMENTATION ROADMAP
## LocalStudy — Offline Lecture Processing Toolkit

> **Product Vision:** A robust, local-first desktop suite that converts educational video and audio into structured study PDFs, timestamped transcripts, and searchable knowledge bases—with zero cloud dependencies, zero AI APIs, and complete privacy.

---

## High-Level Milestone Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             LOCALSTUDY ROADMAP                              │
├─────────────────┬─────────────────┬─────────────────┬───────────────────────┤
│ PHASE 1 (MVP)   │ PHASE 2         │ PHASE 3         │ PHASE 4 & 5           │
│ Video to PDF    │ Audio to STT    │ Projects, DB    │ Sync, Batch & Package │
│ Pipeline        │ Pipeline        │ & Search        │ Distribution          │
│ (Weeks 1-2)     │ (Weeks 3-4)     │ (Weeks 5-6)     │ (Weeks 7-9)           │
├─────────────────┼─────────────────┼─────────────────┼───────────────────────┤
│ • PySide6 UI    │ • FFmpeg Audio  │ • SQLite Schema │ • Video+Transcript    │
│ • OpenCV Frames │ • faster-whisper│ • FTS5 Search   │   Sync Player         │
│ • Timestamp Ovl │ • Model Cache   │ • Bookmarks     │ • Batch Queue         │
│ • ReportLab PDF │ • TXT/SRT/VTT   │ • Recents List  │ • PyInstaller .exe    │
└─────────────────┴─────────────────┴─────────────────┴───────────────────────┘
```

---

## Phase 1: MVP — Core Foundation & Video-to-PDF Pipeline
**Objective:** Deliver an end-to-end working application that ingests local video, captures periodic screenshots with timestamp overlays, and compiles them into a clean, formatted study PDF.

### Sprint 1.1: Project Scaffolding & PySide6 UI Shell
- [ ] Initialize Python virtual environment and configure `requirements.txt` (`PySide6`, `opencv-python`, `pillow`, `reportlab`, `ffmpeg-python`).
- [ ] Build the main application window (`ui/main_window.py`) with a modern dark theme sidebar:
  - Dashboard
  - Video Screenshots
  - Audio Transcriber
  - Study PDFs
  - Settings
- [ ] Implement responsive layout containers and standard navigation switching via `QStackedWidget`.
- [ ] Implement global logging service (`utils/logger.py`) routing structured logs to console and rotating log file.

### Sprint 1.2: Video Ingestion & Frame Extraction Engine
- [ ] Create video metadata analyzer (`video/analyzer.py`) using `ffprobe`/`opencv` to extract duration, frame count, resolution, and FPS.
- [ ] Build `video/frame_extractor.py`:
  - **Fixed-interval extraction:** Extract frame every $N$ seconds (1s, 5s, 10s, 15s, 30s, 60s, custom).
  - **Custom timestamp mode:** Allow users to input comma- or newline-separated timestamps (e.g. `00:05:30, 00:12:45`).
- [ ] Implement timestamp overlay renderer (`video/timestamp_overlay.py`):
  - Configurable font size, color, background banner (semi-transparent black pill).
  - Configurable text tokens: Lecture Title, Timestamp (`HH:MM:SS`), Project Name.
- [ ] Implement non-blocking background extraction worker using `QRunnable` + `QThreadPool` with granular progress reporting and atomic cancellation.

### Sprint 1.3: ReportLab PDF Compilation Engine
- [ ] Build `pdf/generator.py` using ReportLab:
  - Generate clean cover page with Project Title, Course Code, Instructor, Date, and Duration.
  - Generate Lecture Metadata page with summary metrics (total screenshots, capture interval).
- [ ] Implement multi-layout support in `pdf/layouts.py`:
  - **1-Up Layout:** Single high-res frame per page with timestamp banner and note-taking space.
  - **2-Up Layout:** Two frames stacked vertically with clean divider lines.
  - **4-Up Layout:** 2x2 grid for slide decks and concise printing.
- [ ] Implement custom `NumberedCanvas` (`pdf/canvas_builder.py`) for dynamic "Page X of Y" numbering and running headers.
- [ ] Implement visual PDF generation progress dialog with cancel hook and auto-open file prompt upon completion.

### Phase 1 Acceptance Criteria:
- Load a 60-minute MP4 video.
- Extract frames every 30 seconds (~120 frames) in under 60 seconds on Ryzen 5600G.
- Compile into a clean 1-up, 2-up, or 4-up PDF with correct timestamps and metadata.
- UI maintains 60 FPS without freezing during processing.

---

## Phase 2: Audio Extraction & Local Transcription Pipeline
**Objective:** Integrate completely offline local speech-to-text using `faster-whisper`, generating timestamped TXT, SRT, and VTT files with zero external API calls.

### Sprint 2.1: Audio Extraction & Preprocessing
- [ ] Create `transcription/audio_extractor.py` leveraging FFmpeg:
  - Extract audio stream from input video/audio containers (MP4, MKV, MP3, M4A, WAV, AAC, FLAC).
  - Resample and downmix to 16,000 Hz, 16-bit mono PCM WAV (`pcm_s16le`).
- [ ] Create audio duration and volume normalization utility.

### Sprint 2.2: Local Whisper Model Manager
- [ ] Create `transcription/model_manager.py`:
  - Manage local model weight directory (`data/models/`).
  - Support model sizes: `tiny`, `base`, `small`, `medium`, `large-v3`.
  - Built-in downloader with progress bar and SHA256 integrity verification (downloads once, runs forever offline).
  - Status indicator in Settings: "Installed", "Available for Download", "Disk Size".

### Sprint 2.3: Transcription Inference Engine
- [ ] Build `transcription/engine.py` wrapping `faster-whisper.WhisperModel`:
  - Auto-configure optimal compute type (`int8` for CPU, `float16` for CUDA).
  - CPU thread allocation (default: 4 threads on 6-core Ryzen 5600G to preserve OS responsiveness).
  - Language selection: `auto-detect`, `English`, `Bangla (bn)`, `Hindi (hi)`, `Urdu (ur)`, etc.
- [ ] Create `transcription/segment_processor.py`:
  - Stream transcribed segments in real-time to the UI.
  - Clean repetitive hallucinations, strip trailing whitespace, normalize punctuation.

### Sprint 2.4: Subtitle & Transcript Exporters
- [ ] Build `transcription/exporters.py`:
  - **Timestamped TXT:** Formatted blocks with `[HH:MM:SS]` headers.
  - **SRT Subtitles:** Compliant SubRip format with standard sequence numbers and millisecond timestamps.
  - **WebVTT Subtitles:** Standard W3C `.vtt` format for browser and media player compatibility.
  - **Structured JSON:** Machine-readable segments array (`id`, `start`, `end`, `text`).

### Phase 2 Acceptance Criteria:
- Transcribe a 15-minute lecture audio file offline using Whisper `base` or `small`.
- Export valid `.txt`, `.srt`, and `.vtt` files that open properly in standard video players (VLC/MPV).
- Verify accurate transcription of Bangla and English technical terms without internet connectivity.

---

## Phase 3: Project System, SQLite Database, Transcript Search & Bookmarks
**Objective:** Transform individual processing scripts into an integrated project management and lecture knowledge base system with SQLite FTS5 search.

### Sprint 3.1: SQLite Database & Project Architecture
- [ ] Design and initialize local SQLite schema (`database/schema.sql`):
  - Tables: `projects`, `sources`, `screenshots`, `transcript_segments`, `bookmarks`, `jobs`.
  - Virtual FTS5 table: `transcript_fts` indexed on `project_id`, `start_time`, `end_time`, `text`.
- [ ] Build `core/project_manager.py`:
  - Standardized project directory generator:
    ```text
    Project_Name/
    ├── project.json
    ├── source/
    ├── screenshots/
    ├── transcript/
    ├── pdf/
    ├── metadata/
    └── logs/
    ```
  - Auto-save project state, metadata, and timestamps to disk and SQLite concurrently.

### Sprint 3.2: Transcript Viewer & Sub-millisecond Search
- [ ] Build `ui/views/transcript_view.py`:
  - Virtual scrolling list view displaying timestamped speech segments.
  - Instant search bar connected to SQLite FTS5 query engine.
  - Keyword highlighting across search results with instant count indicator.
  - Segment click action triggering timestamp copy or player jump.

### Sprint 3.3: Manual Bookmarking & Exam Notes System
- [ ] Build bookmark management module (`core/bookmark_service.py`):
  - Bookmark creation dialog: Timestamp (`HH:MM:SS`), Category tag (e.g. `⭐ Exam Topic`, `💡 Core Concept`, `❓ Question`), Title, and Detailed Note.
  - Persist bookmarks in SQLite and export to `bookmarks.json`.
  - Dedicated "Bookmarks" panel with quick-jump navigation.

### Phase 3 Acceptance Criteria:
- Create, open, save, and delete projects from the Dashboard.
- Search for a specific keyword in a 2-hour lecture transcript and receive matching segments in <50ms.
- Add bookmarks and verify they persist across application restarts.

---

## Phase 4: Batch Processing, Queue Management & Media Synchronization
**Objective:** Enable multi-lecture batch processing, fault-tolerant job control, and synchronized video-transcript-screenshot playback.

### Sprint 4.1: Batch Job Queue & Background Execution Manager
- [ ] Build `core/job_manager.py` with multi-step pipeline orchestration:
  - States: `QUEUED`, `PROCESSING`, `PAUSED`, `COMPLETED`, `FAILED`, `CANCELLED`.
  - Step transitions: Download/Load → Frame Extract → Audio Extract → Transcribe → Compile PDF.
- [ ] Build `ui/views/batch_queue_view.py`:
  - Drag-and-drop multiple video/audio files or paste list of URLs.
  - Re-order queue, pause current queue, cancel individual jobs.
  - Global progress bar and estimated completion time (ETA) calculator.

### Sprint 4.2: Fault Tolerance, Pause/Resume & Error Handling
- [ ] Implement checkpoint recovery:
  - If frame extraction halts at 60%, resume from the last recorded frame index rather than restarting from 0.
  - If transcription halts, resume from the last completed audio chunk.
- [ ] Implement friendly error boundary dialogs for common edge cases:
  - Missing FFmpeg binary with auto-download or path selector.
  - Low disk space warning (< 2 GB available).
  - Corrupted media stream detection with detailed recovery recommendations.

### Sprint 4.3: Synchronized Tri-View Player (Video + Transcript + Screenshots)
- [ ] Implement embedded video player using `QtMultimedia` (`QMediaPlayer` + `QVideoWidget`):
  - Play, pause, seek slider, speed controls (0.75x, 1.0x, 1.25x, 1.5x, 2.0x).
- [ ] Bidirectional synchronization:
  - Clicking a transcript segment seeks the video to `start_time`.
  - Seeking the video highlights the active transcript segment and displays the closest captured slide screenshot.

### Phase 4 Acceptance Criteria:
- Queue 5 lecture videos and process them consecutively without memory leaks or crashes.
- Interrupted jobs successfully resume from disk checkpoints without data loss.
- Synchronized playback correctly tracks transcript lines in real-time during video playback.

---

## Phase 5: Advanced Features, Packaging & Distribution
**Objective:** Deliver an optimized, self-contained Windows executable with optional local OCR, global lecture search, and full data export/import capabilities.

### Sprint 5.1: Local Slide OCR (Optional Non-AI / Offline)
- [ ] Integrate local OCR engine (`pytesseract` or offline PaddleOCR CPU):
  - Extract text directly from slide screenshots.
  - Index extracted slide text into SQLite FTS5 table `slide_text_fts`.
- [ ] Unified Search: Query both spoken words (transcripts) and slide visual text in a single search bar.

### Sprint 5.2: Global Cross-Project Lecture Knowledge Base
- [ ] Implement global search dialog accessible from anywhere (`Ctrl + Shift + F`):
  - Search across all saved projects in the user's database.
  - View results grouped by Subject / Course / Lecture Date.
  - Instant 1-click jump to open the target project at the exact timestamp.

### Sprint 5.3: Project Bundling, Export & Import
- [ ] Build project bundler (`utils/bundler.py`):
  - Export complete lecture package into a single `.studybundle` (compressed ZIP).
  - Package contains: `lecture.pdf`, `transcript.txt`, `transcript.srt`, `bookmarks.json`, `metadata.json`, and optimized screenshot thumbnails.
- [ ] Build 1-click import feature to unpack and re-register projects on another machine.

### Sprint 5.4: Hardware Profiler & Auto-Tuning
- [ ] Build `core/hardware_detector.py`:
  - Detect CPU architecture, physical/logical core counts, available RAM, and GPU capabilities.
  - Recommend default settings based on detected hardware:
    - *Under 8GB RAM:* Whisper `tiny`, int8 quantization, 2 threads.
    - *8GB - 16GB RAM (Ryzen 5600G):* Whisper `base`/`small`, int8 quantization, 4 threads, 720p screenshots.
    - *32GB+ RAM / Dedicated GPU:* Whisper `medium`/`large`, float16 quantization, 1080p screenshots.

### Sprint 5.5: Standalone Packaging & Distribution
- [ ] Configure PyInstaller build specification (`localstudy.spec`):
  - Bundle PySide6 binaries, Qt plugins, FFmpeg/ffprobe executables, ReportLab assets, and icons.
  - Exclude unnecessary test suites and heavy documentation to minimize package size.
- [ ] Build automated release pipeline producing standalone `LocalStudy.exe` installer / portable zip.

---

## Hardware Optimization Matrix (AMD Ryzen 7 5600G Benchmark Target)

| Component | Default Configuration | Memory Footprint | Processing Speed Target |
| :--- | :--- | :--- | :--- |
| **Video Analyzer** | `ffprobe` JSON parser | < 50 MB RAM | Instant (< 1s per hour of video) |
| **Screenshot Extraction** | OpenCV frame stepping / FFmpeg seek | 150 - 300 MB RAM | ~0.3s per extracted frame |
| **Whisper Base (int8)** | CTranslate2, 4 CPU threads | ~400 MB RAM | ~3.5x real-time speed |
| **Whisper Small (int8)**| CTranslate2, 4 CPU threads | ~900 MB RAM | ~1.8x real-time speed |
| **PDF Compilation** | ReportLab 2-up / 4-up | 200 - 500 MB RAM | ~2-5s for 150-page PDF |
| **SQLite FTS5 Query** | In-memory cache + WAL disk | < 25 MB RAM | < 10ms for 100k words |

---

## Risk Management & Mitigation Strategies

| Identified Risk | Severity | Mitigation Strategy |
| :--- | :--- | :--- |
| **Disk Space Exhaustion** | High | Real-time disk space estimator before extraction; automatic cleanup prompt for raw intermediate frames; JPEG quality compression slider. |
| **FFmpeg Missing on User Machine** | High | Bundle static FFmpeg binaries with PyInstaller; include fallback path configuration in Settings. |
| **Whisper Memory Spike on Long Lectures** | Medium | Process audio in 30-minute chunks with memory cleanup between batches; enforce `int8` quantization. |
| **Bangla / Mixed English Accuracy** | Medium | Allow user to select `small` or `medium` models for non-English lectures; provide post-transcription inline text editor. |
| **UI Freeze on Heavy I/O** | High | Strict enforcement of QRunnable worker pools; zero blocking disk I/O on Qt UI thread. |
