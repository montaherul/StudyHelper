"""
Unit tests verifying clean screenshot captures (no burnt-in overlays)
and PDF formatting (1st page shows project name only, slides show time only as config).
"""

import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from pypdf import PdfReader

from database.models import Project, Screenshot
from pdf.generator import pdf_generator
from video.frame_extractor import frame_extractor


class TestCleanScreenshotAndPdf(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.work_dir = Path(self.temp_dir.name)

        # Create a synthetic 1-second video with a uniform solid color
        self.video_path = self.work_dir / "clean_test.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(self.video_path), fourcc, 10.0, (640, 360))
        for _ in range(10):
            # Pure solid green frame
            frame = np.full((360, 640, 3), (0, 180, 0), dtype=np.uint8)
            out.write(frame)
        out.release()

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_screenshot_has_zero_overlay(self):
        """Verify extracted screenshot image files have zero burned-in text/pill badge."""
        out_ss = self.work_dir / "screenshots"
        screenshots = frame_extractor.extract_frames(
            video_path=self.video_path,
            output_dir=out_ss,
            project_id="clean_proj_1",
            interval_seconds=1.0,
            apply_overlay=False,  # default is False
            lecture_title="SECRET_LECTURE_NAME_NEVER_REVEAL",
            course_name="SECRET_COURSE"
        )
        self.assertGreater(len(screenshots), 0)
        ss_file = Path(screenshots[0].file_path)
        self.assertTrue(ss_file.exists())

        # Load image and verify pixel consistency (solid color should not have dark pill badge)
        img = Image.open(str(ss_file))
        arr = np.array(img)
        # Check bottom-right area where pill badge used to be drawn
        bottom_right_slice = arr[300:350, 450:630]
        # In a pure green frame with no badge, green channel is dominant, red & blue near 0
        self.assertGreater(np.mean(bottom_right_slice[:, :, 1]), 150)
        self.assertLess(np.mean(bottom_right_slice[:, :, 0]), 20)

    def test_pdf_first_page_shows_project_name_only(self):
        """Verify PDF 1st page contains project name and no metadata table, and subsequent pages omit title."""
        # Create a sample screenshot
        img_path = self.work_dir / "slide.jpg"
        img = Image.new("RGB", (640, 360), color=(50, 60, 70))
        img.save(str(img_path), "JPEG")

        proj = Project(
            id="proj_clean",
            name="Quantum Computing 101",
            subject="Physics",
            course="PHYS 401",
            teacher="Dr. Richard Feynman",
            semester="Fall 2026",
            description="Confidential Lecture Notes",
            output_path=str(self.work_dir)
        )
        screenshots = [
            Screenshot(
                id="ss-1",
                project_id=proj.id,
                timestamp=125.0,  # 00:02:05
                file_path=str(img_path),
                page_number=1
            )
        ]

        pdf_path = self.work_dir / "Quantum_clean.pdf"
        pdf_generator.compile_pdf(
            project=proj,
            screenshots=screenshots,
            output_pdf_path=pdf_path,
            layout="2-up",
            show_timestamp=True,
            time_only=True,
            cover_project_name_only=True
        )
        self.assertTrue(pdf_path.exists())

        # Read PDF content using pypdf
        reader = PdfReader(str(pdf_path))
        self.assertGreaterEqual(len(reader.pages), 2)

        # Page 1: Cover Page
        page1_text = reader.pages[0].extract_text()
        self.assertIn("Quantum Computing 101", page1_text)
        # Should NOT contain metadata table labels
        self.assertNotIn("Dr. Richard Feynman", page1_text)
        self.assertNotIn("PHYS 401", page1_text)
        self.assertNotIn("Confidential Lecture Notes", page1_text)
        self.assertNotIn("LocalStudy Offline Engine", page1_text)

        # Page 2: Slides Page
        page2_text = reader.pages[1].extract_text()
        # Should show timestamp (time only)
        self.assertIn("00:02:05", page2_text)
        # Should NOT repeat the project name in running header
        self.assertNotIn("Quantum Computing 101", page2_text)


if __name__ == "__main__":
    unittest.main()
