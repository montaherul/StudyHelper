"""
Test Suite for Mobile Responsive Web Studio.
Validates mobile viewport meta, mobile drawer, bottom app bar, responsive CSS rules,
and mobile-friendly interactions.
"""

import unittest
from api.web_ui import get_web_ui_html


class TestMobileResponsiveWebStudio(unittest.TestCase):
    """Test suite verifying full mobile responsiveness in Web Studio."""

    def setUp(self):
        self.html = get_web_ui_html()

    def test_mobile_meta_viewport_and_capabilities(self):
        """Validates mobile viewport meta, theme color, and mobile web app tags."""
        self.assertIn('name="viewport"', self.html)
        self.assertIn('viewport-fit=cover', self.html)
        self.assertIn('name="theme-color"', self.html)
        self.assertIn('name="mobile-web-app-capable"', self.html)
        self.assertIn('name="apple-mobile-web-app-capable"', self.html)
        self.assertIn('name="apple-mobile-web-app-status-bar-style"', self.html)

    def test_mobile_navigation_components_present(self):
        """Verifies hamburger button, backdrop overlay, drawer close, and bottom nav exist."""
        # Mobile Hamburger Button in Topbar
        self.assertIn('id="mobile-menu-btn"', self.html)
        self.assertIn('class="mobile-menu-btn"', self.html)

        # Drawer Backdrop Overlay
        self.assertIn('id="sidebar-backdrop"', self.html)
        self.assertIn('class="drawer-backdrop"', self.html)

        # Drawer Close Button in Sidebar Brand Box
        self.assertIn('class="mobile-drawer-close"', self.html)

        # Mobile Quick Action Bottom Navigation Bar
        self.assertIn('class="mobile-bottom-nav"', self.html)
        self.assertIn('data-tab="dashboard"', self.html)
        self.assertIn('data-tab="projects"', self.html)
        self.assertIn('data-tab="screenshots"', self.html)
        self.assertIn('data-tab="pdf-builder"', self.html)

    def test_mobile_css_media_queries(self):
        """Verifies responsive breakpoints and mobile CSS rules."""
        self.assertIn('@media (max-width: 900px)', self.html)
        self.assertIn('@media (max-width: 768px)', self.html)
        self.assertIn('@media (max-width: 600px)', self.html)

        # Check drawer slide transformation rules
        self.assertIn('transform: translateX(-100%)', self.html)
        self.assertIn('transform: translateX(0)', self.html)

        # Check iOS 16px font-size anti-zoom rule
        self.assertIn('font-size: 16px; /* Prevents auto-zoom on iOS Safari */', self.html)

        # Check safe-area-inset for modern notched phones
        self.assertIn('env(safe-area-inset-bottom', self.html)

    def test_mobile_javascript_drawer_functions(self):
        """Verifies toggleSidebar function and auto-close integration in showTab."""
        self.assertIn('function toggleSidebar(', self.html)
        self.assertIn('sidebar-open', self.html)
        self.assertIn("toggleSidebar(false);", self.html)
        self.assertIn("bottom-nav-item", self.html)

    def test_all_10_desktop_views_preserved(self):
        """Ensures that all 10 core views remain intact with zero regressions."""
        views = [
            'id="tab-dashboard"',
            'id="tab-projects"',
            'id="tab-downloader"',
            'id="tab-screenshots"',
            'id="tab-transcriber"',
            'id="tab-transcript-search"',
            'id="tab-pdf-builder"',
            'id="tab-batch-queue"',
            'id="tab-settings"',
            'id="tab-api-explorer"',
        ]
        for view_id in views:
            self.assertIn(view_id, self.html)


if __name__ == '__main__':
    unittest.main()
