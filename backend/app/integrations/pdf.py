"""Bilingual PDF documents (reports and guides) in English or Arabic.

Arabic is shaped (arabic-reshaper) and reordered for display (python-bidi)
before drawing, set right-aligned in Noto Naskh Arabic. Latin text uses Noto
Sans. Fonts are bundled under app/assets/fonts (SIL Open Font License).
"""

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import arabic_reshaper
from bidi import get_display  # Unicode bidi with isolate support
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_registered = False


def _register() -> None:
    global _registered
    if _registered:
        return
    for name, file in (
        ("Sans", "NotoSans-Regular.ttf"), ("Sans-Bold", "NotoSans-Bold.ttf"),
        ("Naskh", "NotoNaskhArabic-Regular.ttf"), ("Naskh-Bold", "NotoNaskhArabic-Bold.ttf"),
    ):
        pdfmetrics.registerFont(TTFont(name, str(FONTS / file)))
    _registered = True


@dataclass
class Section:
    heading: str
    paragraphs: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    palette: list[str] | None = None  # hex colours drawn as swatches
    rows: list[tuple[str, str]] | None = None  # label/value pairs
    swatches: list[tuple[str, str]] | None = None  # (hex, name): a labelled colour grid


def _text(value: str, rtl: bool) -> str:
    """Paragraph markup for one string. In Arabic, characters the Arabic font
    does not contain (hyphen, %, bullet...) are drawn in the Latin font."""
    if not rtl:
        return escape(value)
    shown = get_display(arabic_reshaper.reshape(value))
    shown = shown.replace("\u2066", "").replace("\u2069", "")  # isolates have done their job
    _register()
    covered = pdfmetrics.getFont("Naskh").face.charToGlyph
    out, run, run_fallback = [], [], None
    for char in shown:
        fallback = ord(char) not in covered and not char.isspace()
        if fallback != run_fallback and run:
            out.append(_run("".join(run), run_fallback))
            run = []
        run_fallback = fallback
        run.append(char)
    if run:
        out.append(_run("".join(run), run_fallback))
    return "".join(out)


def ltr(value: str) -> str:
    """Keep a left-to-right run (a date, a code) in its own order inside Arabic text."""
    return f"\u2066{value}\u2069"


def _run(text: str, fallback: bool) -> str:
    return f'<font name="Sans">{escape(text)}</font>' if fallback else escape(text)


def build(*, title: str, subtitle: str, sections: list[Section], language: str, footer: str) -> bytes:
    _register()
    rtl = language == "ar"
    regular, bold = ("Naskh", "Naskh-Bold") if rtl else ("Sans", "Sans-Bold")
    align = TA_RIGHT if rtl else TA_LEFT
    styles = {
        "title": ParagraphStyle("title", fontName=bold, fontSize=20, leading=28, alignment=align, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", fontName=regular, fontSize=10, leading=15, alignment=align, textColor=colors.HexColor("#6b5b63")),
        "h": ParagraphStyle("h", fontName=bold, fontSize=13, leading=20, alignment=align, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#7a3e5a")),
        "p": ParagraphStyle("p", fontName=regular, fontSize=10.5, leading=16, alignment=align),
        "foot": ParagraphStyle("foot", fontName=regular, fontSize=8, leading=12, alignment=align, textColor=colors.HexColor("#6b5b63")),
        "swatch": ParagraphStyle("swatch", fontName=regular, fontSize=7, leading=9, alignment=1, textColor=colors.HexColor("#4a3a42")),
    }
    story = [Paragraph(_text(title, rtl), styles["title"]), Paragraph(_text(subtitle, rtl), styles["subtitle"]), Spacer(1, 6 * mm)]
    for section in sections:
        story.append(Paragraph(_text(section.heading, rtl), styles["h"]))
        for paragraph in section.paragraphs:
            story.append(Paragraph(_text(paragraph, rtl), styles["p"]))
        for bullet in section.bullets:
            mark = "•"
            story.append(Paragraph(_text(f"{mark} {bullet}", rtl), styles["p"]))
        if section.rows:
            data = [[Paragraph(_text(v, rtl), styles["p"]), Paragraph(_text(k, rtl), styles["p"])] if rtl
                    else [Paragraph(_text(k, rtl), styles["p"]), Paragraph(_text(v, rtl), styles["p"])] for k, v in section.rows]
            table = Table(data, colWidths=[85 * mm, 85 * mm])
            table.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5dde1")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.append(table)
        if section.palette:
            per_row = 9  # fits the A4 text width
            rows = [section.palette[i:i + per_row] for i in range(0, len(section.palette), per_row)]
            cells = [["" for _ in range(per_row)] for _ in rows]
            swatches = Table(cells, colWidths=[18 * mm] * per_row, rowHeights=[12 * mm] * len(rows))
            # Right to left: the first colour sits at the right edge and short rows end on the left.
            place = (lambda i: per_row - 1 - i) if rtl else (lambda i: i)
            swatches.setStyle(TableStyle([("BACKGROUND", (place(i), r), (place(i), r), colors.HexColor(c))
                                          for r, row in enumerate(rows) for i, c in enumerate(row)]))
            swatches.hAlign = "RIGHT" if rtl else "LEFT"
            story += [Spacer(1, 2 * mm), swatches]
        if section.swatches:
            per_row = 6
            items = list(section.swatches)
            grid = [items[i:i + per_row] for i in range(0, len(items), per_row)]
            data, style = [], [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]
            for r, row in enumerate(grid):
                if rtl:
                    row = list(reversed(row))
                data.append(["" for _ in row] + [""] * (per_row - len(row)))
                data.append([Paragraph(_text(name, rtl), styles["swatch"]) for _, name in row] + [""] * (per_row - len(row)))
                style += [("BACKGROUND", (i, 2 * r), (i, 2 * r), colors.HexColor(hex_)) for i, (hex_, _) in enumerate(row)]
            heights = [h for _ in grid for h in (14 * mm, 8 * mm)]
            table = Table(data, colWidths=[28 * mm] * per_row, rowHeights=heights)
            table.setStyle(TableStyle(style))
            table.hAlign = "RIGHT" if rtl else "LEFT"
            story += [Spacer(1, 2 * mm), table]
    story += [Spacer(1, 8 * mm), Paragraph(_text(footer, rtl), styles["foot"])]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm, title=title)
    doc.build(story)
    return buffer.getvalue()
