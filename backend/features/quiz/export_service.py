"""
Export Service — generate PDF, DOCX, PPTX, XLSX reports for quiz sessions.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from persistence.models.quiz import (
    Quiz, QuizSession, QuizType, Question, QuestionType
)
from features.quiz.answer_service_async import AnswerServiceAsync


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------

@dataclass
class QuestionExport:
    id: int
    text: str
    question_type: str
    options: Optional[List[str]]
    correct_answer_index: Optional[int]
    answer_distribution: List[int]
    total_answers: int
    word_frequencies: Optional[Dict[str, int]] = None   # word cloud only


@dataclass
class LeaderboardEntryExport:
    rank: int
    display_name: str
    score: int
    time_taken_seconds: Optional[float]


@dataclass
class ExportData:
    session_id: int
    quiz_title: str
    quiz_type: str           # "quiz" | "poll"
    total_questions: int
    total_participants: int
    generated_at: datetime
    questions: List[QuestionExport] = field(default_factory=list)
    leaderboard: List[LeaderboardEntryExport] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Colour palette helpers
# ---------------------------------------------------------------------------

_PALETTE_HEX = [
    "#1890ff", "#13c2c2", "#52c41a", "#faad14",
    "#f5222d", "#722ed1", "#eb2f96", "#fa8c16",
]
_CORRECT_HEX = "#52c41a"
_WRONG_HEX   = "#1890ff"


def _hex2rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# ---------------------------------------------------------------------------
# Pillow PNG chart helpers  (used by DOCX)
# ---------------------------------------------------------------------------

def _make_bar_chart_png(
    question_text: str,
    options: List[str],
    distribution: List[int],
    correct_idx: Optional[int],
    width: int = 560,
) -> bytes:
    """Draw a horizontal bar chart PNG using Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return b""

    row_h = 44
    margin_left = 160
    margin_right = 80
    margin_top = 10
    margin_bottom = 10
    height = margin_top + len(options) * row_h + margin_bottom

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    total = sum(distribution) or 1
    bar_area = width - margin_left - margin_right

    for i, (opt, cnt) in enumerate(zip(options, distribution)):
        y = margin_top + i * row_h
        bar_w = int(bar_area * cnt / total)
        color = _CORRECT_HEX if i == correct_idx else _WRONG_HEX
        r, g, b = _hex2rgb(color)

        # bar
        draw.rectangle([margin_left, y + 6, margin_left + max(bar_w, 2), y + row_h - 6],
                       fill=(r, g, b))

        # option label (left)
        label = (opt[:18] + "…") if len(opt) > 20 else opt
        draw.text((4, y + row_h // 2 - 7), label, fill=(0, 0, 0))

        # count + pct (right)
        pct = cnt / total * 100
        draw.text((margin_left + bar_w + 4, y + row_h // 2 - 7),
                  f"{cnt} ({pct:.0f}%)", fill=(80, 80, 80))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_pie_chart_png(
    labels: List[str],
    values: List[int],
    title: str = "",
    size: int = 300,
) -> bytes:
    """Draw a simple pie chart PNG using Pillow."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return b""

    total = sum(values) or 1
    legend_h = 20 * len(labels) + 10
    img = Image.new("RGB", (size, size + legend_h), "white")
    draw = ImageDraw.Draw(img)

    # pie
    cx, cy, r = size // 2, size // 2, size // 2 - 10
    start = -90.0
    colors = [_hex2rgb(c) for c in _PALETTE_HEX]
    for i, (lbl, val) in enumerate(zip(labels, values)):
        sweep = val / total * 360
        draw.pieslice([cx - r, cy - r, cx + r, cy + r],
                      start=start, end=start + sweep,
                      fill=colors[i % len(colors)])
        start += sweep

    # legend
    for i, (lbl, val) in enumerate(zip(labels, values)):
        ly = size + 5 + i * 20
        r2, g2, b2 = colors[i % len(colors)]
        draw.rectangle([5, ly + 3, 17, ly + 15], fill=(r2, g2, b2))
        draw.text((22, ly), f"{lbl} ({val / total * 100:.0f}%)", fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_wc_bar_png(word_freq: Dict[str, int], top: int = 15, width: int = 560) -> bytes:
    """Horizontal bar chart for word cloud top words."""
    items = sorted(word_freq.items(), key=lambda x: -x[1])[:top]
    if not items:
        return b""
    labels = [w for w, _ in items]
    counts = [c for _, c in items]
    return _make_bar_chart_png("", labels, counts, correct_idx=None, width=width)


# ---------------------------------------------------------------------------
# PDF builder (reportlab PLATYPUS + native charts)
# ---------------------------------------------------------------------------

def _build_pdf(data: ExportData) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, KeepTogether, PageBreak
        )
        from reportlab.graphics.shapes import Drawing, Rect, String
        from reportlab.graphics.charts.barcharts import HorizontalBarChart
        from reportlab.graphics.charts.piecharts import Pie
        from reportlab.graphics import renderPDF
    except ImportError:
        raise HTTPException(status_code=501, detail="Export libraries not available")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=22, spaceAfter=6)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=14, spaceBefore=10, spaceAfter=4)
    body = styles["Normal"]
    small = ParagraphStyle("small", parent=body, fontSize=9, textColor=colors.grey)

    # ---- Page 1: summary ----
    story.append(Paragraph(data.quiz_title, title_style))
    story.append(Paragraph(
        f"Session #{data.session_id}  ·  {data.generated_at.strftime('%d %b %Y, %H:%M')}",
        small
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#1890ff"), thickness=2))
    story.append(Spacer(1, 0.4 * cm))

    # KPI row
    kpi_data = [
        [
            Paragraph(f"<b>{data.total_participants}</b><br/>Participants", body),
            Paragraph(f"<b>{data.total_questions}</b><br/>Questions", body),
            Paragraph(f"<b>{data.quiz_type.capitalize()}</b><br/>Type", body),
        ]
    ]
    kpi_tbl = Table(kpi_data, colWidths=["33%", "33%", "34%"])
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#e6f7ff")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#f6ffed")),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#fff7e6")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 0.5 * cm))

    # Overall correct/incorrect pie (quiz type only)
    if data.quiz_type == "quiz":
        total_correct = 0
        total_wrong = 0
        for q in data.questions:
            if q.options and q.correct_answer_index is not None:
                for i, cnt in enumerate(q.answer_distribution):
                    if i == q.correct_answer_index:
                        total_correct += cnt
                    else:
                        total_wrong += cnt

        if total_correct + total_wrong > 0:
            d = Drawing(200, 160)
            pie = Pie()
            pie.x = 50; pie.y = 30; pie.width = 100; pie.height = 100
            pie.data = [total_correct, total_wrong]
            pie.labels = [f"Correct ({total_correct})", f"Wrong ({total_wrong})"]
            pie.slices[0].fillColor = colors.HexColor(_CORRECT_HEX)
            pie.slices[1].fillColor = colors.HexColor("#f5222d")
            d.add(pie)
            story.append(d)
            story.append(Spacer(1, 0.3 * cm))

    # Per-question overview bar chart
    if data.questions:
        q_labels = [f"Q{i+1}" for i in range(len(data.questions))]
        q_counts = [sum(q.answer_distribution) for q in data.questions]
        max_count = max(q_counts) if q_counts else 1

        dw, dh = 400, max(80, len(data.questions) * 18 + 20)
        d2 = Drawing(dw, dh)
        bc = HorizontalBarChart()
        bc.x = 40; bc.y = 10; bc.width = dw - 60; bc.height = dh - 20
        bc.data = [q_counts]
        bc.categoryAxis.categoryNames = q_labels
        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = max(max_count + 2, 5)
        bc.bars[0].fillColor = colors.HexColor(_WRONG_HEX)
        d2.add(bc)
        story.append(Paragraph("<b>Response count per question</b>", body))
        story.append(d2)

    story.append(PageBreak())

    # ---- Per-question pages ----
    for idx, q in enumerate(data.questions):
        total = sum(q.answer_distribution) or 1
        q_items = []

        type_badge = q.question_type.upper()
        q_items.append(Paragraph(f"<b>Q{idx+1}. {q.text}</b>  <font color='grey' size=9>[{type_badge}]</font>", h2))

        if q.options:
            # Horizontal bar chart
            max_v = max(q.answer_distribution) if q.answer_distribution else 1
            dw2, dh2 = 420, max(60, len(q.options) * 26 + 20)
            d3 = Drawing(dw2, dh2)
            bc2 = HorizontalBarChart()
            bc2.x = 40; bc2.y = 5; bc2.width = dw2 - 60; bc2.height = dh2 - 10
            bc2.data = [q.answer_distribution]
            bc2.categoryAxis.categoryNames = [
                (opt[:20] + "…") if len(opt) > 22 else opt
                for opt in q.options
            ]
            bc2.valueAxis.valueMin = 0
            bc2.valueAxis.valueMax = max(max_v + 1, 5)
            # colour each bar individually
            for i in range(len(q.options)):
                color = colors.HexColor(_CORRECT_HEX) if i == q.correct_answer_index else colors.HexColor(_WRONG_HEX)
                bc2.bars[(0, i)].fillColor = color
            d3.add(bc2)
            q_items.append(d3)

            # Data table
            tbl_data = [["Option", "Votes", "%"]]
            for i, (opt, cnt) in enumerate(zip(q.options, q.answer_distribution)):
                marker = " ✓" if i == q.correct_answer_index else ""
                pct = cnt / total * 100
                tbl_data.append([f"{chr(65+i)}. {opt}{marker}", str(cnt), f"{pct:.0f}%"])
            tbl = Table(tbl_data, colWidths=["60%", "20%", "20%"])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1890ff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            q_items.append(tbl)

        elif q.word_frequencies:
            top_words = sorted(q.word_frequencies.items(), key=lambda x: -x[1])[:15]
            w_labels = [w for w, _ in top_words]
            w_counts = [c for _, c in top_words]
            max_wv = max(w_counts) if w_counts else 1
            dw3, dh3 = 420, max(60, len(w_labels) * 24 + 20)
            d4 = Drawing(dw3, dh3)
            bc3 = HorizontalBarChart()
            bc3.x = 60; bc3.y = 5; bc3.width = dw3 - 80; bc3.height = dh3 - 10
            bc3.data = [w_counts]
            bc3.categoryAxis.categoryNames = w_labels
            bc3.valueAxis.valueMin = 0
            bc3.valueAxis.valueMax = max_wv + 1
            bc3.bars[0].fillColor = colors.HexColor("#722ed1")
            d4.add(bc3)
            q_items.append(Paragraph("<b>Top word frequencies</b>", body))
            q_items.append(d4)
        else:
            q_items.append(Paragraph(
                f"<i>Text response question — {sum(q.answer_distribution)} responses received</i>",
                body
            ))

        story.append(KeepTogether(q_items))
        story.append(Spacer(1, 0.6 * cm))

    # ---- Leaderboard page ----
    if data.quiz_type == "quiz" and data.leaderboard:
        story.append(PageBreak())
        story.append(Paragraph("<b>Leaderboard</b>", title_style))
        story.append(Spacer(1, 0.3 * cm))

        # Podium for top 3
        top3 = data.leaderboard[:3]
        if len(top3) >= 1:
            podium_d = Drawing(400, 120)
            heights = [80, 60, 40]
            positions = [120, 20, 220]  # 2nd, 1st, 3rd
            order_idx = [1, 0, 2]  # draw order: 1st center, 2nd left, 3rd right
            podium_colors = [
                colors.HexColor("#FFD700"),
                colors.HexColor("#C0C0C0"),
                colors.HexColor("#CD7F32"),
            ]
            for rank_0 in range(min(3, len(top3))):
                entry = top3[rank_0]
                h = heights[rank_0]
                x = positions[rank_0]
                c = podium_colors[rank_0]
                podium_d.add(Rect(x, 10, 60, h, fillColor=c, strokeColor=colors.white))
                podium_d.add(String(x + 30, 10 + h + 4, entry.display_name[:10],
                                    textAnchor="middle", fontSize=8))
                podium_d.add(String(x + 30, 10 + h // 2,
                                    f"#{entry.rank} ({entry.score})",
                                    textAnchor="middle", fontSize=9, fillColor=colors.black))
            story.append(podium_d)

        # Full table
        lb_data = [["Rank", "Name", "Score", "Time"]]
        rank_colors_map = {1: "#FFD700", 2: "#C0C0C0", 3: "#CD7F32"}
        for e in data.leaderboard:
            time_str = f"{e.time_taken_seconds:.1f}s" if e.time_taken_seconds is not None else "—"
            lb_data.append([str(e.rank), e.display_name, str(e.score), time_str])
        lb_tbl = Table(lb_data, colWidths=["10%", "50%", "20%", "20%"])
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1890ff")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOX", (0, 0), (-1, -1), 0.4, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        for row_i, e in enumerate(data.leaderboard, start=1):
            hex_c = rank_colors_map.get(e.rank)
            if hex_c:
                style_cmds.append(("BACKGROUND", (0, row_i), (-1, row_i), colors.HexColor(hex_c)))
        lb_tbl.setStyle(TableStyle(style_cmds))
        story.append(lb_tbl)

    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# DOCX builder (python-docx + Pillow PNGs)
# ---------------------------------------------------------------------------

def _build_docx(data: ExportData) -> bytes:
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        raise HTTPException(status_code=501, detail="Export libraries not available")

    doc = Document()
    doc.add_heading(data.quiz_title, 0)
    doc.add_paragraph(
        f"Session #{data.session_id}  ·  {data.generated_at.strftime('%d %b %Y, %H:%M')}"
    ).style.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    # Summary table
    tbl = doc.add_table(rows=2, cols=3)
    tbl.style = "Table Grid"
    headers = ["Participants", "Questions", "Type"]
    values  = [str(data.total_participants), str(data.total_questions), data.quiz_type.capitalize()]
    for i, (h, v) in enumerate(zip(headers, values)):
        tbl.cell(0, i).text = h
        tbl.cell(0, i).paragraphs[0].runs[0].bold = True
        tbl.cell(1, i).text = v

    doc.add_paragraph()

    # Correct vs incorrect pie (quiz type)
    if data.quiz_type == "quiz":
        total_correct = sum(
            q.answer_distribution[q.correct_answer_index]
            for q in data.questions
            if q.options and q.correct_answer_index is not None
               and q.correct_answer_index < len(q.answer_distribution)
        )
        total_answers = sum(sum(q.answer_distribution) for q in data.questions if q.options)
        total_wrong = total_answers - total_correct
        if total_correct + total_wrong > 0:
            pie_png = _make_pie_chart_png(
                ["Correct", "Wrong"], [total_correct, total_wrong],
                title="Overall Correct vs Wrong"
            )
            if pie_png:
                doc.add_heading("Overall Results", level=1)
                doc.add_picture(io.BytesIO(pie_png), width=Inches(3))

    # Per-question sections
    doc.add_heading("Question Results", level=1)
    for idx, q in enumerate(data.questions):
        doc.add_heading(f"Q{idx+1}. {q.text}", level=2)
        p = doc.add_paragraph()
        run = p.add_run(f"[{q.question_type.upper()}]  Total answers: {sum(q.answer_distribution)}")
        run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
        run.font.size = Pt(9)

        if q.options:
            chart_png = _make_bar_chart_png(
                q.text, q.options, q.answer_distribution, q.correct_answer_index
            )
            if chart_png:
                doc.add_picture(io.BytesIO(chart_png), width=Inches(5.5))

            # Data table
            tbl2 = doc.add_table(rows=len(q.options) + 1, cols=3)
            tbl2.style = "Table Grid"
            for cell_text, cell in zip(["Option", "Votes", "%"], tbl2.rows[0].cells):
                cell.text = cell_text
                cell.paragraphs[0].runs[0].bold = True
            total = sum(q.answer_distribution) or 1
            for i, (opt, cnt) in enumerate(zip(q.options, q.answer_distribution)):
                row = tbl2.rows[i + 1]
                marker = " ✓" if i == q.correct_answer_index else ""
                row.cells[0].text = f"{chr(65+i)}. {opt}{marker}"
                row.cells[1].text = str(cnt)
                row.cells[2].text = f"{cnt/total*100:.0f}%"

        elif q.word_frequencies:
            wc_png = _make_wc_bar_png(q.word_frequencies)
            if wc_png:
                doc.add_picture(io.BytesIO(wc_png), width=Inches(5.5))
        else:
            doc.add_paragraph(
                f"Text response question — {sum(q.answer_distribution)} responses received"
            ).italic = True

        doc.add_paragraph()

    # Leaderboard
    if data.quiz_type == "quiz" and data.leaderboard:
        doc.add_page_break()
        doc.add_heading("Leaderboard", level=1)
        lb_tbl = doc.add_table(rows=len(data.leaderboard) + 1, cols=4)
        lb_tbl.style = "Table Grid"
        for cell_text, cell in zip(["Rank", "Name", "Score", "Time"], lb_tbl.rows[0].cells):
            cell.text = cell_text
            cell.paragraphs[0].runs[0].bold = True
        for i, e in enumerate(data.leaderboard):
            row = lb_tbl.rows[i + 1]
            time_str = f"{e.time_taken_seconds:.1f}s" if e.time_taken_seconds is not None else "—"
            row.cells[0].text = str(e.rank)
            row.cells[1].text = e.display_name
            row.cells[2].text = str(e.score)
            row.cells[3].text = time_str

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# PPTX builder (python-pptx native charts)
# ---------------------------------------------------------------------------

def _build_pptx(data: ExportData) -> bytes:
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt, Emu
        from pptx.dml.color import RGBColor
        from pptx.enum.chart import XL_CHART_TYPE
        from pptx.chart.data import ChartData
    except ImportError:
        raise HTTPException(status_code=501, detail="Export libraries not available")

    prs = Presentation()
    blank_layout = prs.slide_layouts[6]  # blank
    title_layout = prs.slide_layouts[0]

    W = prs.slide_width
    H = prs.slide_height

    def add_text_box(slide, text, left, top, width, height, bold=False, size=18, color=None):
        txb = slide.shapes.add_textbox(left, top, width, height)
        tf = txb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = bold
        if color:
            run.font.color.rgb = RGBColor(*_hex2rgb(color))
        return txb

    # ---- Slide 1: Title / Summary ----
    slide1 = prs.slides.add_slide(blank_layout)
    add_text_box(slide1, data.quiz_title,
                 Inches(0.5), Inches(0.3), W - Inches(1), Inches(1.2),
                 bold=True, size=28)
    add_text_box(slide1,
                 f"Session #{data.session_id}  ·  {data.generated_at.strftime('%d %b %Y, %H:%M')}",
                 Inches(0.5), Inches(1.4), W - Inches(1), Inches(0.5),
                 size=14, color="#888888")

    # KPI boxes
    kpi_items = [
        (f"{data.total_participants}\nParticipants", "#e6f7ff"),
        (f"{data.total_questions}\nQuestions", "#f6ffed"),
        (f"{data.quiz_type.capitalize()}\nType", "#fff7e6"),
    ]
    box_w = Inches(2.2)
    for i, (txt, bg_hex) in enumerate(kpi_items):
        left = Inches(0.5) + i * (box_w + Inches(0.2))
        txb = slide1.shapes.add_textbox(left, Inches(2.0), box_w, Inches(1.0))
        tf = txb.text_frame
        tf.word_wrap = True
        tf.paragraphs[0].add_run().text = txt

    # Correct vs incorrect pie (quiz type only)
    if data.quiz_type == "quiz":
        total_correct = sum(
            q.answer_distribution[q.correct_answer_index]
            for q in data.questions
            if q.options and q.correct_answer_index is not None
               and q.correct_answer_index < len(q.answer_distribution)
        )
        total_answers = sum(sum(q.answer_distribution) for q in data.questions if q.options)
        total_wrong = total_answers - total_correct
        if total_correct + total_wrong > 0:
            cd = ChartData()
            cd.categories = ["Correct", "Wrong"]
            cd.add_series("Responses", [total_correct, total_wrong])
            chart = slide1.shapes.add_chart(
                XL_CHART_TYPE.PIE,
                Inches(0.5), Inches(3.2), Inches(4), Inches(3),
                cd
            ).chart
            chart.series[0].points[0].format.fill.solid()
            chart.series[0].points[0].format.fill.fore_color.rgb = RGBColor(0x52, 0xc4, 0x1a)
            chart.series[0].points[1].format.fill.solid()
            chart.series[0].points[1].format.fill.fore_color.rgb = RGBColor(0xf5, 0x22, 0x2d)

    # ---- Per-question slides ----
    for idx, q in enumerate(data.questions):
        sl = prs.slides.add_slide(blank_layout)
        add_text_box(sl, f"Q{idx+1}. {q.text}",
                     Inches(0.3), Inches(0.1), W - Inches(0.6), Inches(1.2),
                     bold=True, size=16)

        if q.options and q.answer_distribution:
            cd2 = ChartData()
            cd2.categories = [
                (opt[:30] + "…") if len(opt) > 32 else opt
                for opt in q.options
            ]
            cd2.add_series("Votes", q.answer_distribution)
            chart2 = sl.shapes.add_chart(
                XL_CHART_TYPE.BAR_CLUSTERED,
                Inches(0.3), Inches(1.4), W - Inches(0.6), Inches(4.5),
                cd2
            ).chart
            # Colour correct bar green
            if q.correct_answer_index is not None:
                for i in range(len(q.options)):
                    pt = chart2.series[0].points[i]
                    pt.format.fill.solid()
                    if i == q.correct_answer_index:
                        pt.format.fill.fore_color.rgb = RGBColor(0x52, 0xc4, 0x1a)
                    else:
                        pt.format.fill.fore_color.rgb = RGBColor(0x18, 0x90, 0xff)

        elif q.word_frequencies:
            top_wf = sorted(q.word_frequencies.items(), key=lambda x: -x[1])[:10]
            if top_wf:
                cd3 = ChartData()
                cd3.categories = [w for w, _ in top_wf]
                cd3.add_series("Frequency", [c for _, c in top_wf])
                sl.shapes.add_chart(
                    XL_CHART_TYPE.BAR_CLUSTERED,
                    Inches(0.3), Inches(1.4), W - Inches(0.6), Inches(4.5),
                    cd3
                )
        else:
            add_text_box(sl,
                         f"Text response question — {sum(q.answer_distribution)} responses received",
                         Inches(0.3), Inches(2), W - Inches(0.6), Inches(1),
                         size=14, color="#888888")

    # ---- Leaderboard slide ----
    if data.quiz_type == "quiz" and data.leaderboard:
        sl_lb = prs.slides.add_slide(blank_layout)
        add_text_box(sl_lb, "Leaderboard",
                     Inches(0.3), Inches(0.1), W - Inches(0.6), Inches(0.7),
                     bold=True, size=22)

        top10 = data.leaderboard[:10]
        if top10:
            cd4 = ChartData()
            cd4.categories = [e.display_name for e in top10]
            cd4.add_series("Score", [e.score for e in top10])
            sl_lb.shapes.add_chart(
                XL_CHART_TYPE.BAR_CLUSTERED,
                Inches(0.3), Inches(0.9), W - Inches(0.6), Inches(3.5),
                cd4
            )

        # Table
        rows = min(len(data.leaderboard), 20) + 1
        tbl = sl_lb.shapes.add_table(rows, 4,
                                     Inches(0.3), Inches(4.6),
                                     W - Inches(0.6), Inches(2.8)).table
        gold_fill = RGBColor(0xFF, 0xD7, 0x00)
        silver_fill = RGBColor(0xC0, 0xC0, 0xC0)
        bronze_fill = RGBColor(0xCD, 0x7F, 0x32)
        for j, hdr in enumerate(["Rank", "Name", "Score", "Time"]):
            tbl.cell(0, j).text = hdr
        for row_i, e in enumerate(data.leaderboard[:20]):
            tbl.cell(row_i + 1, 0).text = str(e.rank)
            tbl.cell(row_i + 1, 1).text = e.display_name
            tbl.cell(row_i + 1, 2).text = str(e.score)
            time_str = f"{e.time_taken_seconds:.1f}s" if e.time_taken_seconds is not None else "—"
            tbl.cell(row_i + 1, 3).text = time_str

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# XLSX builder (openpyxl native charts)
# ---------------------------------------------------------------------------

def _build_xlsx(data: ExportData) -> bytes:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.chart import BarChart, PieChart, Reference
        from openpyxl.chart.series import DataPoint
    except ImportError:
        raise HTTPException(status_code=501, detail="Export libraries not available")

    wb = Workbook()

    # ---- Summary sheet ----
    ws_s = wb.active
    ws_s.title = "Summary"
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1890FF")

    ws_s["A1"] = "Quiz Title"
    ws_s["B1"] = data.quiz_title
    ws_s["A2"] = "Session ID"
    ws_s["B2"] = data.session_id
    ws_s["A3"] = "Generated At"
    ws_s["B3"] = data.generated_at.strftime("%Y-%m-%d %H:%M")
    ws_s["A4"] = "Total Participants"
    ws_s["B4"] = data.total_participants
    ws_s["A5"] = "Total Questions"
    ws_s["B5"] = data.total_questions
    ws_s["A6"] = "Quiz Type"
    ws_s["B6"] = data.quiz_type.capitalize()

    for row in range(1, 7):
        ws_s[f"A{row}"].font = Font(bold=True)

    if data.quiz_type == "quiz":
        total_correct = sum(
            q.answer_distribution[q.correct_answer_index]
            for q in data.questions
            if q.options and q.correct_answer_index is not None
               and q.correct_answer_index < len(q.answer_distribution)
        )
        total_answers = sum(sum(q.answer_distribution) for q in data.questions if q.options)
        total_wrong = total_answers - total_correct

        ws_s["A8"] = "Correct Answers"
        ws_s["B8"] = total_correct
        ws_s["A9"] = "Wrong Answers"
        ws_s["B9"] = total_wrong

        if total_correct + total_wrong > 0:
            pc = PieChart()
            pc.title = "Correct vs Wrong"
            labels = Reference(ws_s, min_col=1, min_row=8, max_row=9)
            data_ref = Reference(ws_s, min_col=2, min_row=8, max_row=9)
            pc.add_data(data_ref)
            pc.set_categories(labels)
            pc.width = 10; pc.height = 8
            ws_s.add_chart(pc, "D2")

    # ---- Questions sheet ----
    ws_q = wb.create_sheet("Questions")
    q_headers = ["Q#", "Text", "Type", "Opt A", "Opt B", "Opt C", "Opt D",
                 "Votes A", "Votes B", "Votes C", "Votes D",
                 "% A", "% B", "% C", "% D", "Correct Option"]
    for col, h in enumerate(q_headers, 1):
        cell = ws_q.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill

    for idx, q in enumerate(data.questions):
        r = idx + 2
        total = sum(q.answer_distribution) or 1
        ws_q.cell(r, 1, idx + 1)
        ws_q.cell(r, 2, q.text)
        ws_q.cell(r, 3, q.question_type)
        if q.options:
            for i, opt in enumerate(q.options[:4]):
                ws_q.cell(r, 4 + i, opt)
            for i, cnt in enumerate(q.answer_distribution[:4]):
                ws_q.cell(r, 8 + i, cnt)
                ws_q.cell(r, 12 + i, round(cnt / total * 100, 1))
            if q.correct_answer_index is not None:
                ws_q.cell(r, 16, chr(65 + q.correct_answer_index))

    # Add a bar chart for all questions' vote totals
    if len(data.questions) > 0:
        ws_q.cell(1, 18, "Q")
        ws_q.cell(1, 19, "Total Votes")
        for idx, q in enumerate(data.questions):
            ws_q.cell(idx + 2, 18, f"Q{idx+1}")
            ws_q.cell(idx + 2, 19, sum(q.answer_distribution))

        bc = BarChart()
        bc.type = "bar"
        bc.title = "Responses per Question"
        bc.y_axis.title = "Votes"
        end_row = len(data.questions) + 1
        data_ref = Reference(ws_q, min_col=19, min_row=1, max_row=end_row)
        cats_ref = Reference(ws_q, min_col=18, min_row=2, max_row=end_row)
        bc.add_data(data_ref, titles_from_data=True)
        bc.set_categories(cats_ref)
        bc.width = 15; bc.height = 10
        ws_q.add_chart(bc, "R2")

    # ---- Leaderboard sheet ----
    if data.quiz_type == "quiz":
        ws_lb = wb.create_sheet("Leaderboard")
        lb_headers = ["Rank", "Name", "Score", "Time (s)"]
        for col, h in enumerate(lb_headers, 1):
            cell = ws_lb.cell(row=1, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill

        rank_fills = {
            1: PatternFill("solid", fgColor="FFD700"),
            2: PatternFill("solid", fgColor="C0C0C0"),
            3: PatternFill("solid", fgColor="CD7F32"),
        }
        for i, e in enumerate(data.leaderboard):
            r = i + 2
            ws_lb.cell(r, 1, e.rank)
            ws_lb.cell(r, 2, e.display_name)
            ws_lb.cell(r, 3, e.score)
            ws_lb.cell(r, 4, e.time_taken_seconds if e.time_taken_seconds is not None else "")
            if e.rank in rank_fills:
                for col in range(1, 5):
                    ws_lb.cell(r, col).fill = rank_fills[e.rank]

        if data.leaderboard:
            bc2 = BarChart()
            bc2.type = "bar"
            bc2.title = "Top Participant Scores"
            end_lb = min(len(data.leaderboard), 10) + 1
            data_ref2 = Reference(ws_lb, min_col=3, min_row=1, max_row=end_lb)
            cats_ref2 = Reference(ws_lb, min_col=2, min_row=2, max_row=end_lb)
            bc2.add_data(data_ref2, titles_from_data=True)
            bc2.set_categories(cats_ref2)
            bc2.width = 15; bc2.height = 10
            ws_lb.add_chart(bc2, "F2")

    # ---- Word Cloud sheet ----
    wc_questions = [q for q in data.questions if q.word_frequencies]
    if wc_questions:
        ws_wc = wb.create_sheet("Word Cloud Data")
        for col, h in enumerate(["Question", "Word", "Count", "%"], 1):
            cell = ws_wc.cell(row=1, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill

        row = 2
        for q in wc_questions:
            total_wc = sum(q.word_frequencies.values()) or 1
            for word, cnt in sorted(q.word_frequencies.items(), key=lambda x: -x[1]):
                ws_wc.cell(row, 1, q.text[:60])
                ws_wc.cell(row, 2, word)
                ws_wc.cell(row, 3, cnt)
                ws_wc.cell(row, 4, round(cnt / total_wc * 100, 1))
                row += 1

    # ---- Raw Data sheet ----
    ws_raw = wb.create_sheet("Raw Data")
    raw_headers = ["Q#", "Question Text", "Type", "Option", "Option Index", "Votes", "% of Total"]
    for col, h in enumerate(raw_headers, 1):
        cell = ws_raw.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill

    raw_row = 2
    for idx, q in enumerate(data.questions):
        if q.options:
            total = sum(q.answer_distribution) or 1
            for i, (opt, cnt) in enumerate(zip(q.options, q.answer_distribution)):
                ws_raw.cell(raw_row, 1, idx + 1)
                ws_raw.cell(raw_row, 2, q.text)
                ws_raw.cell(raw_row, 3, q.question_type)
                ws_raw.cell(raw_row, 4, opt)
                ws_raw.cell(raw_row, 5, i)
                ws_raw.cell(raw_row, 6, cnt)
                ws_raw.cell(raw_row, 7, round(cnt / total * 100, 1))
                raw_row += 1

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Main ExportService
# ---------------------------------------------------------------------------

class ExportService:

    async def generate(
        self,
        session_id: int,
        fmt: str,
        db: AsyncSession,
        tenant_id: int,
        answer_service: AnswerServiceAsync,
    ) -> Tuple[bytes, str, str]:
        """
        Generate export file.

        Returns (file_bytes, media_type, filename).
        """
        try:
            data = await self._gather_data(session_id, db, tenant_id, answer_service)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to gather export data: {e}")

        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in data.quiz_title)[:40]
        base_name = f"session_{session_id}_{safe_title}"

        try:
            if fmt == "pdf":
                file_bytes = _build_pdf(data)
                media_type = "application/pdf"
                filename = f"{base_name}.pdf"
            elif fmt == "docx":
                file_bytes = _build_docx(data)
                media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                filename = f"{base_name}.docx"
            elif fmt == "pptx":
                file_bytes = _build_pptx(data)
                media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                filename = f"{base_name}.pptx"
            elif fmt == "xlsx":
                file_bytes = _build_xlsx(data)
                media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                filename = f"{base_name}.xlsx"
            else:
                raise HTTPException(status_code=400, detail="Unsupported format")
        except HTTPException:
            raise
        except ImportError as e:
            raise HTTPException(status_code=501, detail="Export libraries not available")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate export: {e}")

        return file_bytes, media_type, filename

    async def _gather_data(
        self,
        session_id: int,
        db: AsyncSession,
        tenant_id: int,
        answer_service: AnswerServiceAsync,
    ) -> ExportData:
        # Load session with quiz + questions
        result = await db.execute(
            select(QuizSession)
            .filter(QuizSession.id == session_id)
            .options(joinedload(QuizSession.quiz).selectinload(Quiz.questions))
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.quiz.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied")

        quiz = session.quiz
        questions = sorted(quiz.questions, key=lambda q: q.order)

        # Load session results (answer distributions per question)
        session_results = await answer_service.get_session_results(db, session_id)
        results_by_qid = {qr.question_id: qr for qr in session_results.question_results}

        # Load leaderboard
        lb_response = await answer_service.get_leaderboard(db, session_id)
        leaderboard = [
            LeaderboardEntryExport(
                rank=e.rank,
                display_name=e.display_name,
                score=e.score,
                time_taken_seconds=e.time_taken_seconds,
            )
            for e in lb_response.entries
        ]

        # Build question export list
        q_exports = []
        for q in questions:
            qr = results_by_qid.get(q.id)
            dist = qr.answer_distribution if qr else []
            total_ans = qr.total_answers if qr else 0

            wf = None
            if q.question_type == QuestionType.WORD_CLOUD:
                try:
                    wc = await answer_service.get_word_cloud_results(db, session_id, q.id)
                    wf = wc.word_frequencies
                except Exception:
                    wf = {}

            q_exports.append(QuestionExport(
                id=q.id,
                text=q.text,
                question_type=q.question_type.value,
                options=q.options if q.options else None,
                correct_answer_index=q.correct_answer_index,
                answer_distribution=dist,
                total_answers=total_ans,
                word_frequencies=wf,
            ))

        return ExportData(
            session_id=session_id,
            quiz_title=quiz.title,
            quiz_type=quiz.quiz_type.value,
            total_questions=len(questions),
            total_participants=session_results.total_participants,
            generated_at=datetime.utcnow(),
            questions=q_exports,
            leaderboard=leaderboard,
        )
