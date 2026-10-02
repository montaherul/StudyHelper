"""
Unit tests for ReportLab PDF compilation and layout engines.
"""

import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from database.models import Project, Screenshot
from pdf.generator import pdf_generator


class TestPdfCompilation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

        # Create 4 dummy slide images
        self.screenshots = []
        for i in range(4):
            img = Image.new("RGB", (1280, 720), color=(30 + (i * 20), 40 + (i * 15), 60 + (i * 25)))
            draw = ImageDraw.Draw(img)
            draw.text((100, 100), f"Lecture Slide #{i+1}", fill=(255, 255, 255))
            f_path = self.dir_path / f"slide_{i+1}.jpg"
            img.save(str(f_path), "JPEG")

            self.screenshots.append(
                Screenshot(
                    id=f"ss-{i}",
                    project_id="test-pdf-proj",
                    timestamp=float(i * 30),
                    file_path=str(f_path),
                    page_number=i + 1
                )
            )

        self.project = Project(
            id="test-pdf-proj",
            name="Operating Systems - Scheduling",
            subject="Operating Systems",
            course="CSE 311",
            teacher="Prof. Alan Turing",
            semester="Spring 2026",
            output_path=str(self.dir_path)
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_compile_2up_pdf(self):
        pdf_out = self.dir_path / "test_2up.pdf"
        compiled = pdf_generator.compile_pdf(
            project=self.project,
            screenshots=self.screenshots,
            output_pdf_path=pdf_out,
            layout="2-up"
        )
        self.assertTrue(compiled.exists())
        self.assertGreater(compiled.stat().st_size, 5000)

    def test_compile_1up_pdf(self):
        pdf_out = self.dir_path / "test_1up.pdf"
        compiled = pdf_generator.compile_pdf(
            project=self.project,
            screenshots=self.screenshots,
            output_pdf_path=pdf_out,
            layout="1-up"
        )
        self.assertTrue(compiled.exists())
        self.assertGreater(compiled.stat().st_size, 5000)

    def test_compile_4up_pdf(self):
        pdf_out = self.dir_path / "test_4up.pdf"
        compiled = pdf_generator.compile_pdf(
            project=self.project,
            screenshots=self.screenshots,
            output_pdf_path=pdf_out,
            layout="4-up"
        )
        self.assertTrue(compiled.exists())
        self.assertGreater(compiled.stat().st_size, 5000)

    def test_compile_cover_name_only_and_time_only(self):
        pdf_out = self.dir_path / "test_clean_cover.pdf"
        compiled = pdf_generator.compile_pdf(
            project=self.project,
            screenshots=self.screenshots,
            output_pdf_path=pdf_out,
            layout="2-up",
            show_timestamp=True,
            time_only=True,
            cover_project_name_only=True
        )
        self.assertTrue(compiled.exists())
        self.assertGreater(compiled.stat().st_size, 3000)

    def test_compile_no_timestamps_in_pdf(self):
        pdf_out = self.dir_path / "test_no_ts.pdf"
        compiled = pdf_generator.compile_pdf(
            project=self.project,
            screenshots=self.screenshots,
            output_pdf_path=pdf_out,
            layout="1-up",
            show_timestamp=False,
            time_only=True,
            cover_project_name_only=True
        )
        self.assertTrue(compiled.exists())
        self.assertGreater(compiled.stat().st_size, 3000)


if __name__ == "__main__":
    unittest.main()
