"""
Timestamp and metadata overlay renderer for extracted lecture screenshots.
Renders high-contrast anti-aliased text badges on captured frames.
"""

from pathlib import Path
from typing import Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from utils.time_utils import seconds_to_hms


class TimestampOverlayRenderer:
    """Renders sleek, unobtrusive timestamp and lecture badges onto image frames."""

    @staticmethod
    def apply_overlay(
        image_input: Image.Image | np.ndarray | str | Path,
        timestamp_seconds: float = 0.0,
        lecture_title: str = "",
        course_name: str = "",
        show_timestamp: bool = False,
        show_title: bool = False,
        font_size: int = 20,
        position: str = "bottom-right",
        force_render: bool = False
    ) -> Image.Image:
        # Convert input to PIL Image
        if isinstance(image_input, (str, Path)):
            img = Image.open(str(image_input)).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            # Convert BGR (cv2) to RGB
            import cv2
            rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
        else:
            img = image_input.copy()

        # Strict requirement: Screenshots must NEVER show title name and time in bottom!
        # Always return 100% clean pristine video frame unless force_render is True
        if not force_render or (not show_timestamp and not show_title):
            return img

        # Compose label text
        tokens = []
        if show_title and lecture_title:
            tokens.append(lecture_title)
        if show_title and course_name:
            tokens.append(f"({course_name})")
        if show_timestamp:
            tokens.append(f"⏱ {seconds_to_hms(timestamp_seconds)}")

        badge_text = "  •  ".join(tokens)
        if not badge_text:
            return img

        # Initialize PIL ImageDraw
        draw = ImageDraw.Draw(img, "RGBA")
        width, height = img.size

        # Dynamically scale font based on image resolution
        base_font_size = max(14, int(font_size * (width / 1280.0)))
        try:
            # Try system or standard font
            font = ImageFont.truetype("arial.ttf", base_font_size)
        except Exception:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", base_font_size)
            except Exception:
                font = ImageFont.load_default()

        # Compute text bounding box
        bbox = draw.textbbox((0, 0), badge_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        pad_x = int(base_font_size * 0.7)
        pad_y = int(base_font_size * 0.4)
        box_w = text_w + (pad_x * 2)
        box_h = text_h + (pad_y * 2)

        margin = int(20 * (width / 1280.0))

        # Determine coordinates
        if position == "bottom-right":
            x0 = width - box_w - margin
            y0 = height - box_h - margin
        elif position == "bottom-left":
            x0 = margin
            y0 = height - box_h - margin
        else:  # top-right
            x0 = width - box_w - margin
            y0 = margin

        x1 = x0 + box_w
        y1 = y0 + box_h
        radius = int(box_h * 0.3)

        # Draw semi-transparent rounded pill background (RGBA: dark slate)
        draw.rounded_rectangle(
            [x0, y0, x1, y1],
            radius=radius,
            fill=(18, 22, 30, 215),
            outline=(70, 85, 110, 180),
            width=1
        )

        # Draw text
        text_x = x0 + pad_x
        text_y = y0 + pad_y - bbox[1]
        draw.text((text_x, text_y), badge_text, fill=(245, 247, 250, 255), font=font)

        return img


overlay_renderer = TimestampOverlayRenderer()
