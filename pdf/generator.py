"""
ReportLab PDF compiler for generating structured study guides and lecture slide packs.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
)

from config.constants import PDF_LAYOUT_1UP, PDF_LAYOUT_2UP, PDF_LAYOUT_4UP
from database.models import Project, Screenshot
from pdf.canvas_builder import NumberedCanvas
from pdf.layouts import create_1up_layout, create_2up_layout, create_4up_layout
from utils.filesystem import ensure_dir
from utils.logger import logger


class PdfGenerator:
    """Compiles lecture screenshots and metadata into formatted study guide PDFs."""

    @staticmethod
    def compile_pdf(
        project: Project,
        screenshots: List[Screenshot],
        output_pdf_path: Path | str,
        layout: str = PDF_LAYOUT_2UP,
        show_timestamp: bool = True,
        time_only: bool = True,
        cover_project_name_only: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        out_path = Path(output_pdf_path).resolve()
        ensure_dir(out_path.parent)

        if not screenshots:
            raise ValueError("Cannot compile PDF without screenshots.")

        if progress_callback:
            progress_callback(10.0, "Preparing lecture document structure...")

        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()

        story = []

        # ================= COVER PAGE =================
        if cover_project_name_only:
            # 1st page shows ONLY the Project Name in clean, elegant typography
            clean_title_style = ParagraphStyle(
                "CleanCoverTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=32,
                leading=40,
                alignment=1,  # Centered
                textColor=colors.HexColor("#0F172A")
            )

            story.append(Spacer(1, 220))
            story.append(Paragraph(project.name, clean_title_style))
            story.append(Spacer(1, 16))
            story.append(HRFlowable(
                width="36%",
                thickness=2.5,
                color=colors.HexColor("#38BDF8"),
                spaceBefore=10,
                spaceAfter=20,
                hAlign="CENTER"
            ))
            # No metadata table or extra information revealing anything
        else:
            # Full metadata cover page
            title_style = ParagraphStyle(
                "CoverTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=26,
                leading=32,
                textColor=colors.HexColor("#1A202C")
            )
            subtitle_style = ParagraphStyle(
                "CoverSubtitle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=15,
                leading=20,
                textColor=colors.HexColor("#4A5568")
            )
            meta_label_style = ParagraphStyle(
                "MetaLabel",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#2D3748")
            )
            meta_val_style = ParagraphStyle(
                "MetaVal",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#4A5568")
            )

            story.append(Spacer(1, 40))
            story.append(Paragraph(project.name, title_style))
            story.append(Spacer(1, 10))

            subtitle_tokens = []
            if project.subject:
                subtitle_tokens.append(project.subject)
            if project.course:
                subtitle_tokens.append(f"[{project.course}]")
            subtitle_text = " • ".join(subtitle_tokens) if subtitle_tokens else "Lecture Study Guide"
            story.append(Paragraph(subtitle_text, subtitle_style))
            story.append(Spacer(1, 20))

            story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#3182CE"), spaceBefore=5, spaceAfter=25))

            # Metadata Table
            meta_data = [
                [Paragraph("Course / Subject:", meta_label_style), Paragraph(project.subject or "—", meta_val_style)],
                [Paragraph("Course Code:", meta_label_style), Paragraph(project.course or "—", meta_val_style)],
                [Paragraph("Instructor:", meta_label_style), Paragraph(project.teacher or "—", meta_val_style)],
                [Paragraph("Academic Term:", meta_label_style), Paragraph(project.semester or "—", meta_val_style)],
                [Paragraph("Total Slides / Frames:", meta_label_style), Paragraph(f"{len(screenshots)} captured slides", meta_val_style)],
                [Paragraph("Compilation Date:", meta_label_style), Paragraph(datetime.now().strftime("%B %d, %Y (%H:%M)"), meta_val_style)],
                [Paragraph("Engine:", meta_label_style), Paragraph("LocalStudy Offline Engine (Zero Cloud APIs)", meta_val_style)]
            ]

            if project.description:
                meta_data.append([
                    Paragraph("Description:", meta_label_style),
                    Paragraph(project.description, meta_val_style)
                ])

            meta_table = Table(meta_data, colWidths=[150, 340])
            meta_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EDF2F7")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]))
            story.append(meta_table)

        if progress_callback:
            progress_callback(40.0, f"Assembling {len(screenshots)} slides with '{layout}' layout...")

        # ================= SLIDES CONTENT =================
        if layout == PDF_LAYOUT_1UP:
            story.extend(create_1up_layout(screenshots, styles, show_timestamp=show_timestamp, time_only=time_only))
        elif layout == PDF_LAYOUT_4UP:
            story.extend(create_4up_layout(screenshots, styles, show_timestamp=show_timestamp, time_only=time_only))
        else:
            # Default 2-up
            story.extend(create_2up_layout(screenshots, styles, show_timestamp=show_timestamp, time_only=time_only))

        if progress_callback:
            progress_callback(75.0, "Rendering PDF canvas and page numbers...")

        # Configure canvas: when cover_project_name_only is True, do not print project name on subsequent page headers
        canvas_maker = NumberedCanvas
        canvas_maker.doc_title = f"{project.name} - Lecture Study Pack"
        canvas_maker.show_header = not cover_project_name_only

        doc.build(story, canvasmaker=canvas_maker)

        if progress_callback:
            progress_callback(100.0, f"PDF compiled successfully ({out_path.name}).")

        logger.info(f"PDF generated: {out_path} ({len(screenshots)} slides)")
        return out_path


pdf_generator = PdfGenerator()
