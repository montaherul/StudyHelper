"""
Unit tests for extended Video & Audio Downloader engine and database tracking.
"""

import unittest
import tempfile
import shutil
from pathlib import Path

from video.downloader import video_downloader, find_default_cookies_file
from database.db import DatabaseManager
from utils.time_utils import parse_timestamp_str, seconds_to_hms


class TestDownloaderExtended(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db = DatabaseManager(self.temp_dir / "test_media.db")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_find_default_cookies_file(self):
        """Verifies cookies auto-detection finds cookies.txt in workspace."""
        cookies = find_default_cookies_file()
        self.assertIsNotNone(cookies)
        self.assertTrue(cookies.exists())
        self.assertEqual(cookies.name, "cookies.txt")

    def test_time_parsing_for_clips(self):
        """Verifies start and end timestamp parsing for short-term video clipping."""
        self.assertEqual(parse_timestamp_str("00:01:30"), 90.0)
        self.assertEqual(parse_timestamp_str("01:00:00"), 3600.0)
        self.assertEqual(parse_timestamp_str("00:05:15.5"), 315.5)
        self.assertEqual(parse_timestamp_str("45"), 45.0)

    def test_downloaded_media_db_operations(self):
        """Verifies saving, querying, and deleting downloaded media records."""
        media_id = "test-media-101"
        self.db.save_downloaded_media(
            media_id=media_id,
            title="MIT Linear Algebra Lecture 01",
            url="https://www.youtube.com/watch?v=7UJ4CFRGd-U",
            file_path="C:/Downloads/linear_algebra.mp4",
            file_type="mp4",
            format_name=".mp4",
            duration=3200.0,
            file_size=154200100,
            project_id="proj_test_01"
        )

        # Query all
        all_media = self.db.list_downloaded_media()
        self.assertEqual(len(all_media), 1)
        self.assertEqual(all_media[0]["title"], "MIT Linear Algebra Lecture 01")
        self.assertEqual(all_media[0]["duration"], 3200.0)

        # Query by project
        proj_media = self.db.list_downloaded_media(project_id="proj_test_01")
        self.assertEqual(len(proj_media), 1)

        other_media = self.db.list_downloaded_media(project_id="non_existent")
        self.assertEqual(len(other_media), 0)

        # Delete
        self.db.delete_downloaded_media(media_id)
        self.assertEqual(len(self.db.list_downloaded_media()), 0)

    def test_detect_platform(self):
        """Verifies multi-platform auto-detection across various video hosts."""
        from video.downloader import detect_platform

        yt = detect_platform("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(yt["platform"], "youtube")
        self.assertEqual(yt["name"], "YouTube")

        tiktok = detect_platform("https://www.tiktok.com/@user/video/7123456789")
        self.assertEqual(tiktok["platform"], "tiktok")
        self.assertEqual(tiktok["name"], "TikTok")

        insta = detect_platform("https://www.instagram.com/reel/C3abc123xyz/")
        self.assertEqual(insta["platform"], "instagram")
        self.assertEqual(insta["name"], "Instagram")

        fb = detect_platform("https://fb.watch/abcd1234ef/")
        self.assertEqual(fb["platform"], "facebook")
        self.assertEqual(fb["name"], "Facebook")

        twitter = detect_platform("https://x.com/username/status/1234567890")
        self.assertEqual(twitter["platform"], "twitter")
        self.assertEqual(twitter["name"], "X (Twitter)")

        reddit = detect_platform("https://www.reddit.com/r/videos/comments/xyz123/great_lecture/")
        self.assertEqual(reddit["platform"], "reddit")
        self.assertEqual(reddit["name"], "Reddit")

        direct = detect_platform("https://example.com/streams/physics_lecture.m3u8")
        self.assertEqual(direct["platform"], "direct")
        self.assertEqual(direct["name"], "Direct Stream")

        generic = detect_platform("https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/")
        self.assertEqual(generic["platform"], "generic")
        self.assertEqual(generic["name"], "Web Media")


if __name__ == "__main__":
    unittest.main()
