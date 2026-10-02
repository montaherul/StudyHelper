"""
Unit tests for time conversion and formatting utilities.
"""

import unittest
from utils.time_utils import (
    seconds_to_hms,
    seconds_to_filename_str,
    parse_timestamp_str,
    format_srt_time,
    format_vtt_time,
    format_txt_header
)


class TestTimeUtils(unittest.TestCase):

    def test_seconds_to_hms(self):
        self.assertEqual(seconds_to_hms(0), "00:00:00")
        self.assertEqual(seconds_to_hms(65), "00:01:05")
        self.assertEqual(seconds_to_hms(3665), "01:01:05")
        self.assertEqual(seconds_to_hms(3665.5, include_ms=True), "01:01:05.500")

    def test_seconds_to_filename_str(self):
        self.assertEqual(seconds_to_filename_str(0), "00h00m00s")
        self.assertEqual(seconds_to_filename_str(90), "00h01m30s")
        self.assertEqual(seconds_to_filename_str(5420), "01h30m20s")

    def test_parse_timestamp_str(self):
        self.assertEqual(parse_timestamp_str("00:05:30"), 330.0)
        self.assertEqual(parse_timestamp_str("5:30"), 330.0)
        self.assertEqual(parse_timestamp_str("01:00:00"), 3600.0)
        self.assertEqual(parse_timestamp_str("120"), 120.0)
        self.assertIsNone(parse_timestamp_str("invalid_time"))

    def test_format_subtitles(self):
        self.assertEqual(format_srt_time(65.25), "00:01:05,250")
        self.assertEqual(format_vtt_time(65.25), "00:01:05.250")
        self.assertEqual(format_txt_header(65), "[00:01:05]")


if __name__ == "__main__":
    unittest.main()
