"""
Certificate PNG generator using Pillow + DejaVu fonts + qrcode.

Produces a 1200×850 landscape PNG.  Generated on every request (<200ms);
no storage layer needed.  Nginx caches the response for 1 hour.
"""
from __future__ import annotations

import io
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── Asset paths ────────────────────────────────────────────────────────────────
_BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_UPLOADS_BASE = os.path.join(_BACKEND_DIR, "uploads")

_FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_BOLD    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

_LOGO_CANDIDATES = [
    os.path.join(_UPLOADS_BASE, "logo.png"),
    os.path.join(_UPLOADS_BASE, "logo.jpg"),
    os.path.normpath(os.path.join(_BACKEND_DIR, "..", "frontend", "src", "assets", "logo.png")),
]

# ── Colours (RGB tuples) ───────────────────────────────────────────────────────
NAVY   = (15,  23,  42)
INDIGO = (99, 102, 241)
GOLD   = (245, 158, 11)
LIGHT  = (248, 250, 252)
GRAY   = (100, 116, 139)
WHITE  = (255, 255, 255)
BORDER = (203, 213, 225)

W, H = 1200, 850


def _find_logo() -> Optional[str]:
    for p in _LOGO_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def _resolve_org_logo(org_logo_url: Optional[str]) -> Optional[str]:
    if not org_logo_url:
        return None
    for prefix in ("/api/uploads/images/", "/api/uploads/temp/", "images/"):
        if org_logo_url.startswith(prefix):
            rel = org_logo_url[len(prefix):]
            candidate = os.path.join(_UPLOADS_BASE, "images", rel)
            if os.path.exists(candidate):
                return candidate
    # bare relative path
    candidate = os.path.join(_UPLOADS_BASE, "images", org_logo_url.lstrip("/"))
    if os.path.exists(candidate):
        return candidate
    return None


def _load_font(path: str, size: int):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _paste_image(canvas, path: str, x: int, y: int, max_w: int, max_h: int) -> None:
    """Paste an image onto the canvas, scaling to fit within max_w × max_h."""
    from PIL import Image
    try:
        img = Image.open(path).convert("RGBA")
        img.thumbnail((max_w, max_h), Image.LANCZOS)
        canvas.paste(img, (x, y), img)
    except Exception as exc:
        logger.debug("certificate_service: failed to paste image %s: %s", path, exc)


def _text_width(draw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _draw_centred(draw, y: int, text: str, font, color) -> None:
    tw = _text_width(draw, text, font)
    draw.text(((W - tw) // 2, y), text, font=font, fill=color)


def generate_certificate_png(
    participant_name: str,
    quiz_title: str,
    score_pct: int,
    issued_at: datetime,
    org_name: str,
    certificate_token: str,
    org_logo_path: Optional[str] = None,
) -> bytes:
    """
    Render a 1200×850 landscape certificate PNG and return the raw bytes.
    """
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)

    # ── Fonts ──────────────────────────────────────────────────────────────────
    f_small   = _load_font(_FONT_REGULAR, 14)
    f_body    = _load_font(_FONT_REGULAR, 18)
    f_label   = _load_font(_FONT_REGULAR, 20)
    f_sub     = _load_font(_FONT_BOLD, 22)
    f_title   = _load_font(_FONT_BOLD, 26)
    f_heading = _load_font(_FONT_BOLD, 34)

    # ── Top indigo bar ─────────────────────────────────────────────────────────
    draw.rectangle([(0, 0), (W, 85)], fill=INDIGO)
    # Gold accent stripe
    draw.rectangle([(0, 85), (W, 92)], fill=GOLD)

    # ── Light body background ──────────────────────────────────────────────────
    draw.rectangle([(60, 110), (W - 60, H - 70)], fill=LIGHT)
    # Indigo border
    draw.rectangle([(60, 110), (W - 60, H - 70)], outline=INDIGO, width=2)

    # ── Bottom indigo bar ──────────────────────────────────────────────────────
    draw.rectangle([(0, H - 65), (W, H)], fill=INDIGO)
    footer_font = _load_font(_FONT_REGULAR, 13)
    _draw_centred(draw, H - 40, "swaya.me  ·  Live Quizzes, Polls & Assessments", footer_font, WHITE)

    # ── Swaya.me logo (top-left of top bar) ────────────────────────────────────
    logo_path = _find_logo()
    if logo_path:
        _paste_image(img, logo_path, 28, 14, 160, 58)
    else:
        draw.text((28, 26), "Swaya.me", font=_load_font(_FONT_BOLD, 22), fill=WHITE)

    # ── Org logo (top-right, inside top bar) ───────────────────────────────────
    if org_logo_path and os.path.exists(org_logo_path):
        _paste_image(img, org_logo_path, W - 190, 14, 160, 58)

    # ── "CERTIFICATE OF COMPLETION" ────────────────────────────────────────────
    _draw_centred(draw, 135, "CERTIFICATE OF COMPLETION", f_heading, NAVY)

    # Gold underline
    heading_w = _text_width(draw, "CERTIFICATE OF COMPLETION", f_heading)
    cx = W // 2
    draw.line([(cx - heading_w // 2, 178), (cx + heading_w // 2, 178)], fill=GOLD, width=3)

    # ── "This certifies that" ──────────────────────────────────────────────────
    _draw_centred(draw, 205, "This certifies that", f_label, GRAY)

    # ── Participant name ───────────────────────────────────────────────────────
    name = participant_name.strip() or "Participant"
    # Auto-shrink font if name is very long
    name_font_size = 48
    name_font = _load_font(_FONT_BOLD, name_font_size)
    while _text_width(draw, name, name_font) > W - 160 and name_font_size > 24:
        name_font_size -= 2
        name_font = _load_font(_FONT_BOLD, name_font_size)

    _draw_centred(draw, 260, name, name_font, NAVY)

    # Indigo underline beneath name
    nw = _text_width(draw, name, name_font)
    draw.line([(cx - nw // 2, 260 + name_font_size + 6), (cx + nw // 2, 260 + name_font_size + 6)],
              fill=INDIGO, width=2)

    # ── "has successfully completed" ──────────────────────────────────────────
    _draw_centred(draw, 355, "has successfully completed", f_label, GRAY)

    # ── Quiz title ─────────────────────────────────────────────────────────────
    title = quiz_title.strip() or "Assessment"
    title_display = f'"{title}"'
    if _text_width(draw, title_display, f_title) > W - 140:
        title = title[:68] + "…"
        title_display = f'"{title}"'
    _draw_centred(draw, 400, title_display, f_title, NAVY)

    # ── Score + Date ───────────────────────────────────────────────────────────
    date_str = issued_at.strftime("%d %B %Y")
    _draw_centred(draw, 460, f"Score: {score_pct}%  ·  Date: {date_str}", f_body, GRAY)

    # ── QR code (bottom-right, inside light box) ──────────────────────────────
    QR_SIZE = 115
    QR_X = W - 75 - QR_SIZE   # 1010
    QR_Y = H - 85 - QR_SIZE   # 650

    try:
        import qrcode as _qrcode
        verify_url = f"https://swaya.me/cert/{certificate_token}"
        qr = _qrcode.QRCode(version=None, box_size=4, border=2,
                             error_correction=_qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(verify_url)
        qr.make(fit=True)
        qr_pil = qr.make_image(fill_color=NAVY, back_color=WHITE).get_image()
        qr_pil = qr_pil.resize((QR_SIZE, QR_SIZE), resample=0)  # NEAREST for crisp pixels
        img.paste(qr_pil.convert("RGB"), (QR_X, QR_Y))

        # "Scan to verify" label under QR
        scan_font = _load_font(_FONT_REGULAR, 11)
        scan_text = "Scan to verify"
        stw = _text_width(draw, scan_text, scan_font)
        draw.text((QR_X + (QR_SIZE - stw) // 2, QR_Y + QR_SIZE + 4), scan_text,
                  font=scan_font, fill=GRAY)
    except Exception as exc:
        logger.warning("certificate_service: QR generation failed: %s", exc)
        # Fall back to text URL if qrcode fails
        verify_text = f"Verify at: swaya.me/cert/{certificate_token}"
        _draw_centred(draw, H - 98, verify_text, f_small, INDIGO)

    # ── Footer separator (clipped left of QR code) ─────────────────────────────
    draw.line([(100, H - 130), (QR_X - 20, H - 130)], fill=BORDER, width=1)

    # ── Issued by ─────────────────────────────────────────────────────────────
    issued_text = f"Issued by: {org_name}"
    itw = _text_width(draw, issued_text, f_body)
    left_cx = (QR_X - 20 + 100) // 2  # centre of the left section
    draw.text((left_cx - itw // 2, H - 122), issued_text, font=f_body, fill=GRAY)

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()
