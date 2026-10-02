"""
Bookmark and study note management service for LocalStudy.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from database.db import db
from database.models import Bookmark
from utils.logger import logger


class BookmarkService:
    """Manages creation, filtering, and export of student lecture bookmarks."""

    def __init__(self):
        self.db = db

    def add_bookmark(
        self,
        project_id: str,
        timestamp: float,
        title: str,
        category: str = "general",
        note: str = ""
    ) -> Bookmark:
        bookmark = Bookmark(
            id=str(uuid.uuid4()),
            project_id=project_id,
            timestamp=timestamp,
            category=category,
            title=title,
            note=note,
            created_at=datetime.now().isoformat()
        )
        self.db.save_bookmark(bookmark)
        self.export_project_bookmarks(project_id)
        logger.info(f"Added bookmark '{title}' at {timestamp}s for project {project_id}")
        return bookmark

    def get_project_bookmarks(self, project_id: str) -> List[Bookmark]:
        return self.db.get_bookmarks(project_id)

    def delete_bookmark(self, bookmark_id: str, project_id: str) -> None:
        self.db.delete_bookmark(bookmark_id)
        self.export_project_bookmarks(project_id)

    def export_project_bookmarks(self, project_id: str) -> Optional[Path]:
        """Exports bookmarks into project metadata/bookmarks.json."""
        project = self.db.get_project(project_id)
        if not project:
            return None
        bookmarks = self.db.get_bookmarks(project_id)
        out_dir = Path(project.output_path) / "metadata"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "bookmarks.json"

        data = [
            {
                "id": b.id,
                "timestamp": b.timestamp,
                "category": b.category,
                "title": b.title,
                "note": b.note,
                "created_at": b.created_at
            }
            for b in bookmarks
        ]
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return out_file


bookmark_service = BookmarkService()
