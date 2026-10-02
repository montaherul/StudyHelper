"""
Global application constants and choices for LocalStudy.
"""

from pathlib import Path

APP_NAME = "LocalStudy"
APP_SUBTITLE = "Offline Lecture Processing Toolkit"
APP_VERSION = "1.0.0"

# Directories
DEFAULT_BASE_DIR = Path.home() / ".localstudy"
DEFAULT_PROJECTS_DIR = Path.home() / "LocalStudy_Projects"
DEFAULT_MODELS_DIR = DEFAULT_BASE_DIR / "models"
DEFAULT_LOGS_DIR = DEFAULT_BASE_DIR / "logs"

# Supported Media Formats
SUPPORTED_VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v"}
SUPPORTED_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}
ALL_MEDIA_EXTS = SUPPORTED_VIDEO_EXTS | SUPPORTED_AUDIO_EXTS

# Interval Options (in seconds)
INTERVAL_PRESETS = [
    ("1 Second (High Density)", 1),
    ("5 Seconds", 5),
    ("10 Seconds", 10),
    ("15 Seconds", 15),
    ("30 Seconds (Recommended)", 30),
    ("60 Seconds (1 Minute)", 60),
    ("120 Seconds (2 Minutes)", 120),
    ("Custom Interval...", -1)
]

# PDF Layout Options
PDF_LAYOUT_1UP = "1-up"
PDF_LAYOUT_2UP = "2-up"
PDF_LAYOUT_4UP = "4-up"
PDF_LAYOUT_CONTACT = "contact-sheet"

PDF_LAYOUTS = [
    ("1 Slide per Page (Detailed with notes)", PDF_LAYOUT_1UP),
    ("2 Slides per Page (Recommended)", PDF_LAYOUT_2UP),
    ("4 Slides per Page (Compact Handout)", PDF_LAYOUT_4UP),
    ("Contact Sheet (Visual Index)", PDF_LAYOUT_CONTACT)
]

# Whisper Model Tiers
WHISPER_MODELS = [
    {
        "id": "tiny",
        "name": "Tiny (~75 MB)",
        "desc": "Ultra-fast, lowest memory, good for quick checks on low-spec hardware",
        "size_mb": 75,
        "default_device": "cpu"
    },
    {
        "id": "base",
        "name": "Base (~145 MB)",
        "desc": "Fast, modest RAM, standard choice for English and clear speech",
        "size_mb": 145,
        "default_device": "cpu"
    },
    {
        "id": "small",
        "name": "Small (~460 MB) [Recommended]",
        "desc": "Optimal balance of accuracy & speed for multilingual & technical terms",
        "size_mb": 460,
        "default_device": "cpu"
    },
    {
        "id": "medium",
        "name": "Medium (~1.5 GB)",
        "desc": "High accuracy for accented audio and noisy classroom environments",
        "size_mb": 1500,
        "default_device": "cpu"
    },
    {
        "id": "large-v3",
        "name": "Large v3 (~3.1 GB)",
        "desc": "Maximum accuracy, requires higher RAM / dedicated GPU",
        "size_mb": 3100,
        "default_device": "cpu"
    }
]

# Supported Languages for Transcription
LANGUAGE_OPTIONS = [
    ("Auto Detect", None),
    ("English", "en"),
    ("Bengali (বাংলা)", "bn"),
    ("Hindi (हिन्दी)", "hi"),
    ("Urdu (اردو)", "ur"),
    ("Arabic (العربية)", "ar"),
    ("Spanish (Español)", "es"),
    ("French (Français)", "fr"),
    ("German (Deutsch)", "de"),
    ("Chinese (中文)", "zh"),
    ("Japanese (日本語)", "ja")
]

# Bookmark Categories
BOOKMARK_CATEGORIES = [
    ("⭐ Exam Topic", "exam_topic", "#FF9800"),
    ("💡 Core Concept", "concept", "#2196F3"),
    ("❓ Question / Review", "question", "#E91E63"),
    ("📝 Formula / Code", "formula", "#4CAF50"),
    ("📌 General Bookmark", "general", "#9C27B0")
]
