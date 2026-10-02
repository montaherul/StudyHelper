"""
Unit tests for SQLite database operations, bookmarks, and FTS5 search.
"""

import tempfile
import unittest
from pathlib import Path

from database.db import DatabaseManager
from database.models import Project, TranscriptSegment, Bookmark


class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "test_localstudy.db"
        self.db = DatabaseManager(self.db_path)

    def tearDown(self):
        del self.db
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_project_crud(self):
        proj = Project(
            id="test-proj-1",
            name="Computer Networks TCP",
            subject="Networks",
            course="CSE321",
            teacher="Dr. Smith",
            output_path="/path/to/proj"
        )
        self.db.save_project(proj)
        loaded = self.db.get_project("test-proj-1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "Computer Networks TCP")

        projects = self.db.list_projects()
        self.assertEqual(len(projects), 1)

        self.db.delete_project("test-proj-1")
        self.assertIsNone(self.db.get_project("test-proj-1"))

    def test_transcript_fts5_search(self):
        proj_id = "test-proj-2"
        # First save project to satisfy foreign key
        proj = Project(id=proj_id, name="TCP Lecture", output_path="/tmp/proj2")
        self.db.save_project(proj)

        segments = [
            TranscriptSegment(id=None, project_id=proj_id, start_time=10.0, end_time=15.0, text="Welcome to the lecture on TCP protocol."),
            TranscriptSegment(id=None, project_id=proj_id, start_time=20.0, end_time=25.0, text="The three-way handshake establishes a reliable connection."),
            TranscriptSegment(id=None, project_id=proj_id, start_time=30.0, end_time=35.0, text="Now let us look at the UDP protocol header.")
        ]
        self.db.save_transcript_segments(segments)

        # Search for 'handshake'
        matches = self.db.search_transcript(proj_id, "handshake")
        self.assertEqual(len(matches), 1)
        self.assertIn("three-way handshake", matches[0].text)

        # Search for 'protocol'
        matches_protocol = self.db.search_transcript(proj_id, "protocol")
        self.assertEqual(len(matches_protocol), 2)

    def test_bookmarks(self):
        proj_id = "test-proj-3"
        # First save project to satisfy foreign key
        proj = Project(id=proj_id, name="Bookmarks Lecture", output_path="/tmp/proj3")
        self.db.save_project(proj)

        bm = Bookmark(
            id="bm-1",
            project_id=proj_id,
            timestamp=45.0,
            category="exam_topic",
            title="Important Handshake Diagram",
            note="Will appear on final exam"
        )
        self.db.save_bookmark(bm)
        bookmarks = self.db.get_bookmarks(proj_id)
        self.assertEqual(len(bookmarks), 1)
        self.assertEqual(bookmarks[0].title, "Important Handshake Diagram")


if __name__ == "__main__":
    unittest.main()
