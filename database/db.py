"""
SQLite Database manager with FTS5 full-text search support for LocalStudy.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional, Dict, Any, Generator

from config.constants import DEFAULT_BASE_DIR
from database.models import Project, Source, Screenshot, TranscriptSegment, Bookmark, Job
from utils.logger import logger


class DatabaseManager:
    """Manages SQLite operations, migrations, and FTS5 full-text indexing."""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            self.db_dir = DEFAULT_BASE_DIR
            self.db_path = self.db_dir / "localstudy.db"
        else:
            self.db_path = Path(db_path)
            self.db_dir = self.db_path.parent

        self.db_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initializes database tables, indices, and FTS5 search tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    subject TEXT,
                    course TEXT,
                    teacher TEXT,
                    semester TEXT,
                    description TEXT,
                    output_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    source_type TEXT NOT NULL,
                    file_path TEXT,
                    source_url TEXT,
                    duration REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS screenshots (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    timestamp REAL NOT NULL,
                    file_path TEXT NOT NULL,
                    page_number INTEGER DEFAULT 1,
                    is_slide_change INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS transcript_segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    start_time REAL NOT NULL,
                    end_time REAL NOT NULL,
                    text TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS bookmarks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    timestamp REAL NOT NULL,
                    category TEXT DEFAULT 'general',
                    title TEXT NOT NULL,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    progress REAL DEFAULT 0.0,
                    error_message TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS downloaded_media (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    title TEXT NOT NULL,
                    url TEXT,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    format TEXT,
                    duration REAL DEFAULT 0.0,
                    file_size INTEGER DEFAULT 0,
                    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_screenshots_proj_ts ON screenshots(project_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_segments_proj_time ON transcript_segments(project_id, start_time);
                CREATE INDEX IF NOT EXISTS idx_bookmarks_proj_ts ON bookmarks(project_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_downloaded_media_proj ON downloaded_media(project_id);
            """)

            # Try initializing FTS5 virtual table for lightning search
            try:
                cursor.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS transcript_fts USING fts5(
                        project_id UNINDEXED,
                        segment_id UNINDEXED,
                        text,
                        tokenize = 'porter unicode61'
                    );
                """)
            except Exception as e:
                logger.warning(f"FTS5 virtual table creation notice: {e}")

            conn.commit()

    # --- Project Operations ---
    def save_project(self, project: Project) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (id, name, subject, course, teacher, semester, description, output_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    subject=excluded.subject,
                    course=excluded.course,
                    teacher=excluded.teacher,
                    semester=excluded.semester,
                    description=excluded.description,
                    output_path=excluded.output_path,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (project.id, project.name, project.subject, project.course, project.teacher,
                 project.semester, project.description, project.output_path, project.created_at, project.updated_at)
            )
            conn.commit()

    def get_project(self, project_id: str) -> Optional[Project]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not row:
                return None
            return Project(**dict(row))

    def list_projects(self, limit: int = 50) -> List[Project]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
            return [Project(**dict(r)) for r in rows]

    def delete_project(self, project_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()

    # --- Screenshot Operations ---
    def save_screenshots(self, screenshots: List[Screenshot]) -> None:
        if not screenshots:
            return
        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO screenshots (id, project_id, timestamp, file_path, page_number, is_slide_change)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [(s.id, s.project_id, s.timestamp, s.file_path, s.page_number, int(s.is_slide_change)) for s in screenshots]
            )
            conn.commit()

    def get_screenshots(self, project_id: str) -> List[Screenshot]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM screenshots WHERE project_id = ? ORDER BY timestamp ASC", (project_id,)
            ).fetchall()
            return [
                Screenshot(
                    id=r["id"],
                    project_id=r["project_id"],
                    timestamp=r["timestamp"],
                    file_path=r["file_path"],
                    page_number=r["page_number"],
                    is_slide_change=bool(r["is_slide_change"])
                )
                for r in rows
            ]

    # --- Transcript & FTS Operations ---
    def save_transcript_segments(self, segments: List[TranscriptSegment]) -> None:
        if not segments:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Clear old segments for project if overwriting
            project_id = segments[0].project_id
            cursor.execute("DELETE FROM transcript_segments WHERE project_id = ?", (project_id,))
            try:
                cursor.execute("DELETE FROM transcript_fts WHERE project_id = ?", (project_id,))
            except Exception:
                pass

            for seg in segments:
                cursor.execute(
                    "INSERT INTO transcript_segments (project_id, start_time, end_time, text) VALUES (?, ?, ?, ?)",
                    (seg.project_id, seg.start_time, seg.end_time, seg.text)
                )
                seg_id = cursor.lastrowid
                try:
                    cursor.execute(
                        "INSERT INTO transcript_fts (project_id, segment_id, text) VALUES (?, ?, ?)",
                        (seg.project_id, str(seg_id), seg.text)
                    )
                except Exception:
                    pass
            conn.commit()

    def get_transcript_segments(self, project_id: str) -> List[TranscriptSegment]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM transcript_segments WHERE project_id = ? ORDER BY start_time ASC", (project_id,)
            ).fetchall()
            return [TranscriptSegment(**dict(r)) for r in rows]

    def search_transcript(self, project_id: str, query: str) -> List[TranscriptSegment]:
        """Performs full-text search using FTS5, falling back to LIKE if needed."""
        query = query.strip()
        if not query:
            return self.get_transcript_segments(project_id)

        with self._get_connection() as conn:
            # Try FTS5 first
            try:
                # Sanitize FTS query
                safe_fts_query = '"' + query.replace('"', '""') + '"*'
                rows = conn.execute(
                    """
                    SELECT s.* FROM transcript_segments s
                    JOIN transcript_fts f ON s.id = CAST(f.segment_id AS INTEGER)
                    WHERE f.project_id = ? AND transcript_fts MATCH ?
                    ORDER BY s.start_time ASC
                    """,
                    (project_id, safe_fts_query)
                ).fetchall()
                if rows:
                    return [TranscriptSegment(**dict(r)) for r in rows]
            except Exception as e:
                logger.debug(f"FTS5 query fallback to LIKE: {e}")

            # Fallback to LIKE search
            like_query = f"%{query}%"
            rows = conn.execute(
                """
                SELECT * FROM transcript_segments
                WHERE project_id = ? AND text LIKE ?
                ORDER BY start_time ASC
                """,
                (project_id, like_query)
            ).fetchall()
            return [TranscriptSegment(**dict(r)) for r in rows]

    # --- Bookmark Operations ---
    def save_bookmark(self, bookmark: Bookmark) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO bookmarks (id, project_id, timestamp, category, title, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (bookmark.id, bookmark.project_id, bookmark.timestamp, bookmark.category,
                 bookmark.title, bookmark.note, bookmark.created_at)
            )
            conn.commit()

    def get_bookmarks(self, project_id: str) -> List[Bookmark]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM bookmarks WHERE project_id = ? ORDER BY timestamp ASC", (project_id,)
            ).fetchall()
            return [Bookmark(**dict(r)) for r in rows]

    def delete_bookmark(self, bookmark_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
            conn.commit()

    # --- Downloaded Media Catalog Operations ---
    def save_downloaded_media(
        self,
        media_id: str,
        title: str,
        url: str,
        file_path: str,
        file_type: str,
        format_name: str = "",
        duration: float = 0.0,
        file_size: int = 0,
        project_id: Optional[str] = None
    ) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO downloaded_media
                (id, project_id, title, url, file_path, file_type, format, duration, file_size, downloaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (media_id, project_id, title, url, str(file_path), file_type, format_name, duration, file_size)
            )
            conn.commit()

    def list_downloaded_media(self, project_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT * FROM downloaded_media WHERE project_id = ? ORDER BY downloaded_at DESC LIMIT ?",
                    (project_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM downloaded_media ORDER BY downloaded_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [dict(r) for r in rows]

    def delete_downloaded_media(self, media_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM downloaded_media WHERE id = ?", (media_id,))
            conn.commit()


# Global DB instance
db = DatabaseManager()
