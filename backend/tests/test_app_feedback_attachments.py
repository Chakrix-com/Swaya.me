"""Feedback screenshot validation: hostile uploads must be refused, real images re-encoded."""
import asyncio
import io

import pytest
from fastapi import HTTPException
from PIL import Image

from features.app_feedback import attachments


class FakeUpload:
    def __init__(self, data: bytes):
        self._data = data

    async def read(self, n=-1):
        return self._data if n < 0 else self._data[:n]


def _png(w=40, h=30, mode="RGB"):
    buf = io.BytesIO()
    Image.new(mode, (w, h), "red").save(buf, format="PNG")
    return buf.getvalue()


def _run(files):
    return asyncio.run(attachments.read_and_validate([FakeUpload(f) for f in files]))


def test_valid_image_is_reencoded_as_png():
    jpeg = io.BytesIO()
    Image.new("RGB", (50, 50), "blue").save(jpeg, format="JPEG")
    (out,) = _run([jpeg.getvalue()])
    assert out.startswith(b"\x89PNG")


def test_large_image_is_downscaled():
    (out,) = _run([_png(4000, 1000)])
    assert max(Image.open(io.BytesIO(out)).size) <= attachments.MAX_EDGE_PX


def test_too_many_files_refused():
    with pytest.raises(HTTPException) as e:
        _run([_png()] * (attachments.MAX_ATTACHMENTS + 1))
    assert e.value.status_code == 400


def test_oversized_file_refused():
    with pytest.raises(HTTPException):
        _run([b"\x89PNG" + b"0" * (attachments.MAX_ATTACHMENT_BYTES + 10)])


@pytest.mark.parametrize("data", [b"<script>alert(1)</script>", b"%PDF-1.4 not an image", b""])
def test_non_images_refused(data):
    with pytest.raises(HTTPException) as e:
        _run([data])
    assert e.value.status_code == 400


def test_resolve_blocks_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(attachments.settings.app, "uploads_base_dir", str(tmp_path))
    with pytest.raises(HTTPException) as e:
        attachments.resolve(1, "../../etc/passwd")
    assert e.value.status_code == 400
