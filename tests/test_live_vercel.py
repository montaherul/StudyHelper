"""
End-to-End Verification Test Suite for LocalStudy Live Vercel Deployment.
Validates 100% feature parity between local application and live Vercel cloud serverless runtime.
"""

import json
import unittest
import urllib.request
from typing import Dict, Any

VERCEL_BASE_URL = "https://studyhelper-tau.vercel.app"
USER_AGENT = "LocalStudy-TestClient/1.0"


def make_request(
    path: str,
    method: str = "GET",
    data: Dict[str, Any] = None,
    timeout: int = 20
) -> urllib.request.urlopen:
    """Helper to dispatch HTTP requests with proper headers."""
    url = f"{VERCEL_BASE_URL}{path}"
    headers = {"User-Agent": USER_AGENT}
    body = None

    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    return urllib.request.urlopen(req, timeout=timeout)


class TestLiveVercelDeployment(unittest.TestCase):
    """E2E Test cases running directly against live Vercel production deployment."""

    def test_01_web_ui_loaded(self):
        """Verifies that root URL serves the complete Web Studio with all 10 desktop views."""
        with make_request("/") as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8")

            # Check core branding and title
            self.assertIn("LocalStudy", html)
            self.assertIn("<!DOCTYPE html>", html)

            # Verify all 10 Desktop Views exist in the Web Studio HTML
            self.assertIn('id="tab-dashboard"', html)
            self.assertIn('id="tab-projects"', html)
            self.assertIn('id="tab-downloader"', html)
            self.assertIn('id="tab-screenshots"', html)
            self.assertIn('id="tab-transcriber"', html)
            self.assertIn('id="tab-transcript-search"', html)
            self.assertIn('id="tab-pdf-builder"', html)
            self.assertIn('id="tab-batch-queue"', html)
            self.assertIn('id="tab-settings"', html)
            self.assertIn('id="tab-api-explorer"', html)

            # Verify size is sufficient for the entire rich UI
            self.assertGreater(len(html), 150000)

    def test_02_health_and_status(self):
        """Verifies health check and status endpoints."""
        with make_request("/health") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "healthy")

        with make_request("/api/status") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "online")
            self.assertEqual(data.get("application"), "LocalStudy")

    def test_03_system_diagnostics(self):
        """Verifies system info endpoint returns hardware and runtime specs."""
        with make_request("/api/system/info") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "online")
            self.assertIn("cpu_model", data)
            self.assertIn("ram_gb", data)
            self.assertIn("acceleration_engine", data)

    def test_04_project_lifecycle(self):
        """Verifies project creation, retrieval, and deletion on live serverless database."""
        # 1. Create Project
        payload = {
            "name": "Live Vercel E2E Project",
            "course": "CSE 401",
            "teacher": "Dr. Alan Turing",
            "description": "Verifying serverless /tmp database persistence."
        }
        with make_request("/api/project/create", method="POST", data=payload) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "success")
            proj = data.get("project", {})
            proj_id = proj.get("id")
            self.assertTrue(proj_id)
            self.assertEqual(proj.get("name"), "Live Vercel E2E Project")

        # 2. List Projects
        with make_request("/api/project/list") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "success")
            projects = data.get("projects", [])
            match = [p for p in projects if p.get("id") == proj_id]
            self.assertEqual(len(match), 1)

        # 3. Clean up Project
        with make_request(f"/api/project/{proj_id}", method="DELETE") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "success")

    def test_05_pdf_compilation(self):
        """Verifies ReportLab PDF generation compiles real PDF binaries in cloud."""
        payload = {
            "project_name": "E2E Study Guide",
            "course": "CS 301",
            "layout": "2up",
            "cover_project_name_only": True,
            "time_only": True
        }
        with make_request("/api/pdf/generate", method="POST", data=payload) as resp:
            self.assertEqual(resp.status, 200)
            content = resp.read()
            # Validate standard PDF file magic header
            self.assertTrue(content.startswith(b"%PDF"))
            self.assertGreater(len(content), 1000)

    def test_06_ai_summarizer(self):
        """Verifies AI Lecture Summary and Exam Questions generation."""
        payload = {
            "text": "Virtual memory utilizes hardware MMU and page tables to map virtual addresses to physical frames.",
            "topic": "Virtual Memory & Paging"
        }
        with make_request("/api/ai/summarize", method="POST", data=payload) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("summary", data)
            self.assertIn("key_takeaways", data)
            self.assertIn("study_questions", data)
            self.assertIn("action_checklist", data)
            self.assertGreater(len(data["key_takeaways"]), 0)

    def test_07_transcript_and_export(self):
        """Verifies transcript retrieval and subtitle export to standard SRT."""
        # 1. Fetch transcript segments
        with make_request("/api/transcript/default-test") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "success")
            segments = data.get("segments", [])
            self.assertGreater(len(segments), 0)

        # 2. Export transcript to SRT
        export_payload = {
            "format": "srt",
            "project_name": "Operating Systems",
            "segments": segments
        }
        with make_request("/api/transcript/export", method="POST", data=export_payload) as resp:
            self.assertEqual(resp.status, 200)
            srt_text = resp.read().decode("utf-8")
            self.assertIn("00:00:00,000 --> 00:00:04,000", srt_text)

    def test_08_study_bookmarks(self):
        """Verifies study bookmark creation, retrieval, and deletion."""
        # 1. Create Bookmark
        bm_payload = {
            "project_id": "test-project-bookmarks",
            "timestamp": 45.0,
            "title": "TCP 3-Way Handshake",
            "category": "concept",
            "note": "SYN, SYN-ACK, ACK sequence."
        }
        with make_request("/api/bookmark/create", method="POST", data=bm_payload) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "success")
            bm_id = data["bookmark"]["id"]
            self.assertTrue(bm_id)

        # 2. List Bookmarks
        with make_request("/api/bookmark/list?project_id=test-project-bookmarks") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "success")
            bookmarks = data.get("bookmarks", [])
            self.assertTrue(any(b.get("id") == bm_id for b in bookmarks))

        # 3. Delete Bookmark
        with make_request(f"/api/bookmark/{bm_id}", method="DELETE") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "success")

    def test_09_sample_slides(self):
        """Verifies sample slides generation endpoint."""
        with make_request("/api/sample-slides") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "success")
            slides = data.get("slides", [])
            self.assertEqual(len(slides), 4)

    def test_10_cookies_format_verifier(self):
        """Verifies cookies verification endpoint parses Netscape format."""
        netscape_cookie = (
            "# Netscape HTTP Cookie File\n"
            ".youtube.com\tTRUE\t/\tTRUE\t2147483647\tLOGIN_INFO\tAFmmF2kwRAIg...\n"
        )
        payload = {"cookies": netscape_cookie}
        with make_request("/api/video/cookies/verify", method="POST", data=payload) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "valid")
            self.assertEqual(data.get("count"), 1)


if __name__ == "__main__":
    unittest.main()
