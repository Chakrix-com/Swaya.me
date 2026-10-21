"""
Screenshot attachments for global app feedback.

Anyone (logged in or not) can send feedback, so uploads are treated as hostile:
count/size capped, decoded with Pillow, and re-encoded to PNG so only pixel data
is ever stored (no metadata, no polyglot payloads). Files live outside the
public /api/uploads mounts and are only served to super admins.
"""
import io
import uuid
from pathlib import Path
from typing import List

from fastapi import HTTPException, UploadFile
from PIL import Image

from core.config.settings import settings

MAX_ATTACHMENTS = 3
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
MAX_EDGE_PX = 2560
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP", "GIF", "BMP"}


def feedback_dir(feedback_id: int) -> Path:
    return Path(settings.app.uploads_base_dir) / "feedback" / str(feedback_id)


async def read_and_validate(files: List[UploadFile]) -> List[bytes]:
    """Validate every upload before anything is written. Returns PNG bytes per image."""
    if len(files) > MAX_ATTACHMENTS:
        raise HTTPException(status_code=400, detail=f"At most {MAX_ATTACHMENTS} images can be attached")
    out = []
    for f in files:
        raw = await f.read(MAX_ATTACHMENT_BYTES + 1)
        if len(raw) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(status_code=400, detail="Each image must be 5 MB or smaller")
        try:
            with Image.open(io.BytesIO(raw)) as probe:
                fmt = probe.format
                probe.verify()
            if fmt not in ALLOWED_FORMATS:
                raise ValueError(fmt)
            with Image.open(io.BytesIO(raw)) as img:
                img.seek(0)  # first frame only for animated GIF/WebP
                img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
                img.thumbnail((MAX_EDGE_PX, MAX_EDGE_PX))
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
        except HTTPException:
            raise
        except Exception:
            # Includes Pillow's DecompressionBombError
            raise HTTPException(status_code=400, detail="Attachments must be valid images (PNG, JPEG, WebP, GIF or BMP)")
        out.append(buf.getvalue())
    return out


def save(feedback_id: int, images: List[bytes]) -> List[str]:
    d = feedback_dir(feedback_id)
    d.mkdir(parents=True, exist_ok=True)
    names = []
    for data in images:
        name = f"{uuid.uuid4().hex}.png"
        (d / name).write_bytes(data)
        names.append(name)
    return names


def resolve(feedback_id: int, name: str) -> Path:
    """Path of a stored attachment, refusing anything outside its feedback folder."""
    d = feedback_dir(feedback_id).resolve()
    p = (d / name).resolve()
    try:
        p.relative_to(d)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid attachment name")
    if not p.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return p
