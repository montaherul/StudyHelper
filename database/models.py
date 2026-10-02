"""
Data models and representations for LocalStudy.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class Project:
    id: str
    name: str
    subject: str = ""
    course: str = ""
    teacher: str = ""
    semester: str = ""
    description: str = ""
    output_path: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Source:
    id: str
    project_id: str
    source_type: str  # 'local_video', 'local_audio', 'url'
    file_path: str = ""
    source_url: str = ""
    duration: float = 0.0
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Screenshot:
    id: str
    project_id: str
    timestamp: float
    file_path: str
    page_number: int = 1
    is_slide_change: bool = False


@dataclass
class TranscriptSegment:
    id: Optional[int]
    project_id: str
    start_time: float
    end_time: float
    text: str


@dataclass
class Bookmark:
    id: str
    project_id: str
    timestamp: float
    category: str = "general"
    title: str = ""
    note: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Job:
    id: str
    project_id: Optional[str]
    job_type: str
    status: str = "queued"
    progress: float = 0.0
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
