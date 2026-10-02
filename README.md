# LocalStudy — Offline Lecture Processing Toolkit

> **100% Local Inference • Zero External AI APIs • Zero Cloud Telemetry • Air-Gapped Operation**

LocalStudy is an offline-first desktop application designed to convert educational videos and audio lectures into structured study materials—periodic screenshot PDFs with timestamp overlays, timestamped transcripts, industry-standard subtitles (SRT, VTT), and an instantly searchable local knowledge base—running entirely on your personal computer.

---

## Key Features

1. **Universal Media & Video Downloader (Any Platform):**
   - Real-time auto-detection for **YouTube**, **TikTok**, **Instagram Reels**, **Facebook Watch**, **X / Twitter**, **Reddit**, **Vimeo**, and **1,700+ media sites**.
   - Direct video stream downloading (**MP4**, **WebM**, **HLS `.m3u8`**, **DASH `.mpd`**) and embedded web page HTML5 video scraping.
   - Authentication support (`cookies.txt` or live browser session) for **private, unlisted, age-restricted, and members-only** lectures.
   - Flexible download modes: **Full Video** (4K, 1080p, 720p, 480p, 360p), **Audio-Only** (MP3 320k/192k, M4A, WAV, FLAC), and **Short-Term Video Clipping** (precise start/end time range).
   - One-click workflow bridges to Screenshot Extractor and Audio Transcriber.
2. **Video Screenshot & Slide Extraction:**
   - Periodic extraction (1s, 5s, 10s, 15s, 30s, 60s, custom seconds).
   - Custom timestamps list mode (`00:05:30, 00:12:45, ...`).
   - Anti-aliased visual overlay banner (Lecture Name, Course, Timestamp `⏱ HH:MM:SS`).
   - Smart slide-change detection using histogram comparison.
3. **Local Speech-to-Text Transcription:**
   - Powered by `faster-whisper` (CTranslate2) running locally with 8-bit quantization (`int8`).
   - Supports `tiny`, `base`, `small` (recommended for multilingual), `medium`, and `large-v3`.
   - Supports English, Bengali (বাংলা), Hindi (हिन्दी), Urdu (اردو), and dozens more languages.
   - Zero token costs, zero cloud API keys, zero rate limits.
4. **Structured Study PDF Compilation:**
   - Formal cover page with Course Code, Instructor, Term, and Lecture Summary.
   - Dynamic `NumberedCanvas` printing running headers and "Page X of Y" pagination.
   - Multi-layout support: **1-Up** (with note-taking lines), **2-Up** (stacked slides), and **4-Up** (handout grid).
5. **Instant Sub-Millisecond Transcript Search & Bookmarks:**
   - SQLite `FTS5` full-text search indexing spoken lecture segments.
   - Lecture-wide keyword lookup in under 10ms.
   - Study bookmarks with categories (`⭐ Exam Topic`, `💡 Core Concept`, `❓ Question`, `📝 Formula`).
6. **Batch Processing Queue:**
   - Queue dozens of lecture media files for unattended sequential processing.
   - Granular progress reporting and responsive cancellation.
7. **Project Management System:**
   - Standardized project folder hierarchy with portable `project.json` manifests and exportable artifacts.

---

## Architecture Overview

```text
                    LocalStudy
                        │
        ┌───────────────┼────────────────┐
        │               │                │
        ▼               ▼                ▼
 Video Processor   Audio Processor   Project Manager
        │               │                │
        ▼               ▼                ▼
 Screenshot        Transcription      Metadata
 Extraction        Engine             Database (SQLite + FTS5)
        │               │                │
        └───────────────┼────────────────┘
                        ▼
                  Study Generator
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
  Study Guides         TXT              SRT / VTT
     (PDF)         Transcript           Subtitles
```

---

## Getting Started

### 1. Requirements
* Python 3.11+
* Windows 10/11, macOS, or Linux

### 2. Installation
```bash
# Clone or navigate to the directory
cd "d:/OFFline study"

# Install dependencies
pip install -r requirements.txt
```

### 3. Launching the Desktop Application (GUI)
```bash
python app.py
```

### 4. Running via Headless CLI
You can also run complete lecture processing from the command line without opening the GUI:
```bash
# Extract frames every 30 seconds and compile a 2-up PDF
python app.py --cli --video "lecture.mp4" --name "Operating Systems" --course "CS301" --interval 30 --layout 2-up

# Extract frames and transcribe audio locally
python app.py --cli --video "networks.mp4" --interval 30 --transcribe --model small --lang bn
```

---

## Running the Automated Test Suite
```bash
python -m unittest discover tests
```

---

## Documentation Links
* [agent.md](agent.md) — Operational protocols, architecture rules, zero-cloud constraints, and engineering guidelines.
* [roadmap.md](roadmap.md) — Phase-by-phase implementation roadmap, sprint tasks, and hardware optimization targets.
* [full_documentation.md](full_documentation.md) — Comprehensive technical manual covering SQLite schema, ReportLab canvas, and developer guides.
