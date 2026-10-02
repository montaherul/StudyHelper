"""
Page layout generators for ReportLab PDF compilation (1-up, 2-up, 4-up, contact sheet).
"""

from pathlib import Path
from typing import List
from reportlab.platypus import Flowable, Image, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from database.models import Screenshot
from utils.time_utils import seconds_to_hms


def create_1up_layout(
    screenshots: List[Screenshot],
    styles,
    show_timestamp: bool = True,
    time_only: bool = True
) -> List[Flowable]:
    """1 Slide per page with large image, optional timestamp header, and student notes area."""
    flowables: List[Flowable] = []
    
    header_style = ParagraphStyle(
        "SlideHeader",
        parent=styles["Normal"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1A202C"),
        fontName="Helvetica-Bold"
    )
    badge_style = ParagraphStyle(
        "SlideTimeOnly",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#2D3748"),
        fontName="Helvetica-Bold"
    )

    for idx, s in enumerate(screenshots, start=1):
        if not Path(s.file_path).exists():
            continue

        flowables.append(PageBreak())
        if show_timestamp:
            t_str = seconds_to_hms(s.timestamp)
            if time_only:
                flowables.append(Paragraph(f"⏱ <b>{t_str}</b>", badge_style))
            else:
                flowables.append(Paragraph(f"Slide #{idx} • Timestamp: <b>{t_str}</b>", header_style))
            flowables.append(Spacer(1, 8))

        # Main Slide Image (max width 500, max height 320)
        img = Image(s.file_path, width=490, height=275)
        flowables.append(img)
        flowables.append(Spacer(1, 14))

        # Student Notes Section
        notes_table = Table(
            [
                [Paragraph("<b>Notes / Key Points:</b>", styles["Normal"])],
                ["\n\n\n\n"]
            ],
            colWidths=[490]
        )
        notes_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        flowables.append(notes_table)

    return flowables


def create_2up_layout(
    screenshots: List[Screenshot],
    styles,
    show_timestamp: bool = True,
    time_only: bool = True
) -> List[Flowable]:
    """2 Slides per page vertically stacked with optional timestamp badge."""
    flowables: List[Flowable] = []

    badge_style = ParagraphStyle(
        "SlideBadge",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2D3748"),
        fontName="Helvetica-Bold"
    )

    # Process pairs of screenshots
    for i in range(0, len(screenshots), 2):
        flowables.append(PageBreak())
        batch = screenshots[i:i+2]

        for sub_idx, s in enumerate(batch):
            if not Path(s.file_path).exists():
                continue

            if show_timestamp:
                t_str = seconds_to_hms(s.timestamp)
                if time_only:
                    flowables.append(Paragraph(f"⏱ <b>{t_str}</b>", badge_style))
                else:
                    slide_num = i + sub_idx + 1
                    flowables.append(Paragraph(f"Slide {slide_num}  •  ⏱ <b>{t_str}</b>", badge_style))
                flowables.append(Spacer(1, 4))

            img = Image(s.file_path, width=490, height=275)
            flowables.append(img)

            if sub_idx == 0 and len(batch) > 1:
                flowables.append(Spacer(1, 16))

    return flowables


def create_4up_layout(
    screenshots: List[Screenshot],
    styles,
    show_timestamp: bool = True,
    time_only: bool = True
) -> List[Flowable]:
    """4 Slides per page in a 2x2 grid with optional timestamp caption."""
    flowables: List[Flowable] = []
    w_img, h_img = 240, 135

    caption_style = ParagraphStyle(
        "GridCaption",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        alignment=1,
        textColor=colors.HexColor("#4A5568")
    )

    for i in range(0, len(screenshots), 4):
        flowables.append(PageBreak())
        batch = screenshots[i:i+4]

        rows = []
        # Row 1 (first 2)
        row1 = []
        for s in batch[:2]:
            if Path(s.file_path).exists():
                cell = [Image(s.file_path, width=w_img, height=h_img)]
                if show_timestamp:
                    cell.extend([
                        Spacer(1, 3),
                        Paragraph(f"⏱ {seconds_to_hms(s.timestamp)}", caption_style)
                    ])
                row1.append(cell)
            else:
                row1.append("")
        while len(row1) < 2:
            row1.append("")
        rows.append(row1)

        # Row 2 (next 2)
        if len(batch) > 2:
            row2 = []
            for s in batch[2:4]:
                if Path(s.file_path).exists():
                    cell = [Image(s.file_path, width=w_img, height=h_img)]
                    if show_timestamp:
                        cell.extend([
                            Spacer(1, 3),
                            Paragraph(f"⏱ {seconds_to_hms(s.timestamp)}", caption_style)
                        ])
                    row2.append(cell)
                else:
                    row2.append("")
            while len(row2) < 2:
                row2.append("")
            rows.append(row2)

        grid_table = Table(rows, colWidths=[245, 245])
        grid_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        flowables.append(grid_table)

    return flowables
