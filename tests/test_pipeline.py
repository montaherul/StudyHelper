"""
End-to-End Pipeline integration test.
Generates synthetic video, extracts periodic frames with overlays, and compiles study PDF.
"""

import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np

from core.project_manager import ProjectManager
from database.db import DatabaseManager
from pdf.generator import pdf_generator
from video.frame_extractor import frame_extractor


class TestEndToEndPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.work_dir = Path(self.temp_dir.name)

        # Generate a 3-second synthetic lecture video (640x360 @ 10fps = 30 frames)
        self.video_path = self.work_dir / "synthetic_lecture.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(self.video_path), fourcc, 10.0, (640, 360))

        for frame_idx in range(30):
            # Create slate slide
            img = np.zeros((360, 640, 3), dtype=np.uint8)
            img[:] = (35, 25, 20)  # Dark slate blue background

            # Slide transition every 10 frames (1 second)
            slide_no = (frame_idx // 10) + 1
            cv2.putText(img, f"Computer Networks - Slide {slide_no}", (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(img, f"Frame {frame_idx} | Second: {frame_idx/10:.1f}s", (40, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 200, 255), 1)
            cv2.putText(img, "TCP Three-Way Handshake (SYN -> SYN-ACK -> ACK)", (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            out.write(img)
        out.release()

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_pipeline_extraction_and_pdf(self):
        # 1. Project Creation
        pm = ProjectManager()
        pm.db = DatabaseManager(self.work_dir / "test.db")
        proj = pm.create_project(
            name="Network TCP Test",
            subject="Computer Networks",
            course="CSE 321",
            custom_output_dir=str(self.work_dir)
        )

        # 2. Extract frames every 1.0 second
        out_ss = Path(proj.output_path) / "screenshots"
        screenshots = frame_extractor.extract_frames(
            video_path=self.video_path,
            output_dir=out_ss,
            project_id=proj.id,
            interval_seconds=1.0,
            apply_overlay=False,
            lecture_title=proj.name,
            course_name=proj.course
        )

        self.assertGreaterEqual(len(screenshots), 2)
        for s in screenshots:
            self.assertTrue(Path(s.file_path).exists())

        # 3. PDF Compilation
        out_pdf = Path(proj.output_path) / "pdf" / "lecture_test.pdf"
        compiled = pdf_generator.compile_pdf(
            project=proj,
            screenshots=screenshots,
            output_pdf_path=out_pdf,
            layout="2-up"
        )

        self.assertTrue(compiled.exists())
        self.assertGreater(compiled.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
