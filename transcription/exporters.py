"""
Transcript format exporters: TXT (timestamped), SRT (SubRip), VTT (WebVTT), and JSON.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from database.models import TranscriptSegment
from utils.filesystem import ensure_dir
from utils.logger import logger
from utils.time_utils import format_srt_time, format_vtt_time, format_txt_header


class TranscriptExporter:
    """Exports structured transcript segments into industry-standard study files."""

    @staticmethod
    def export_txt(segments: List[TranscriptSegment], output_path: Path | str) -> Path:
        out_p = Path(output_path)
        ensure_dir(out_p.parent)

        lines = []
        for s in segments:
            lines.append(f"{format_txt_header(s.start_time)}")
            lines.append(f"{s.text}\n")

        with open(out_p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info(f"Exported TXT transcript to {out_p}")
        return out_p

    @staticmethod
    def export_srt(segments: List[TranscriptSegment], output_path: Path | str) -> Path:
        out_p = Path(output_path)
        ensure_dir(out_p.parent)

        blocks = []
        for idx, s in enumerate(segments, start=1):
            t_start = format_srt_time(s.start_time)
            t_end = format_srt_time(s.end_time)
            blocks.append(f"{idx}\n{t_start} --> {t_end}\n{s.text}\n")

        with open(out_p, "w", encoding="utf-8") as f:
            f.write("\n".join(blocks))
        logger.info(f"Exported SRT subtitle track to {out_p}")
        return out_p

    @staticmethod
    def export_vtt(segments: List[TranscriptSegment], output_path: Path | str) -> Path:
        out_p = Path(output_path)
        ensure_dir(out_p.parent)

        blocks = ["WEBVTT\n"]
        for idx, s in enumerate(segments, start=1):
            t_start = format_vtt_time(s.start_time)
            t_end = format_vtt_time(s.end_time)
            blocks.append(f"{idx}\n{t_start} --> {t_end}\n{s.text}\n")

        with open(out_p, "w", encoding="utf-8") as f:
            f.write("\n".join(blocks))
        logger.info(f"Exported WebVTT subtitle track to {out_p}")
        return out_p

    @staticmethod
    def export_json(segments: List[TranscriptSegment], output_path: Path | str) -> Path:
        out_p = Path(output_path)
        ensure_dir(out_p.parent)

        payload = [
            {
                "id": s.id,
                "start": s.start_time,
                "end": s.end_time,
                "text": s.text
            }
            for s in segments
        ]
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info(f"Exported JSON segments to {out_p}")
        return out_p

    @classmethod
    def export_all(cls, segments: List[TranscriptSegment], transcript_dir: Path | str) -> Dict[str, Path]:
        t_dir = ensure_dir(transcript_dir)
        return {
            "txt": cls.export_txt(segments, t_dir / "transcript.txt"),
            "srt": cls.export_srt(segments, t_dir / "transcript.srt"),
            "vtt": cls.export_vtt(segments, t_dir / "transcript.vtt"),
            "json": cls.export_json(segments, t_dir / "segments.json")
        }


transcript_exporter = TranscriptExporter()
