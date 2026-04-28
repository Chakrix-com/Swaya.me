#!/usr/bin/env python3
"""
Image upload regression test.

Covers POST /quizzes/{quiz_id}/upload-image which had zero test coverage.

Two upload modes exist:
  - Temp upload (no question_id): stores in uploads/temp/, returns temp URL
  - Permanent upload (question_id provided): stores in uploads/images/, returns final URL

Tests:
  1. Temp upload with a valid PNG → 200 with image_url
  2. Permanent upload to a real question → 200 with image_url
  3. Upload with wrong file type (txt) → error response (not 500)
  4. Upload to a non-existent quiz → 403 or 404
"""
import io
import os
import struct
import sys
import zlib
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = os.getenv("BASE_URL", "https://test.swaya.me/api/v1").rstrip("/")
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://test.swaya.me").rstrip("/")
EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")


def _make_png() -> bytes:
    """Build a valid 1×1 white PNG using stdlib — no Pillow dependency."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        payload = tag + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    sig  = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))  # 1×1, 8-bit RGB
    idat = chunk(b'IDAT', zlib.compress(b'\x00\xFF\xFF\xFF'))              # filter=None, pixel=white
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend


PNG_1X1 = _make_png()


def fail(msg: str):
    print(f"FAIL: {msg}")
    sys.exit(1)


def check(cond: bool, msg: str):
    if not cond:
        fail(msg)


def main():
    s = requests.Session()
    s.verify = False

    # Login
    r = s.post(f"{BASE_URL}/auth/login",
               json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    check(r.status_code == 200, f"login failed: {r.status_code}")
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    print("OK: login")

    # Create a temporary quiz for testing
    r = s.post(f"{BASE_URL}/quizzes/",
               json={"title": "RegTest Upload Quiz", "description": "auto"}, timeout=20)
    check(r.status_code in (200, 201), f"create quiz failed: {r.status_code}")
    quiz_id = r.json()["id"]
    print(f"OK: created quiz  id={quiz_id}")

    # Add a question (needed for permanent upload test)
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
        "text": "Upload test question?",
        "question_type": "mcq",
        "options": ["A", "B", "C", "D"],
        "correct_answer_index": 0,
        "max_time_seconds": 20,
        "points": 100,
    }, timeout=20)
    check(r.status_code in (200, 201), f"create question failed: {r.status_code}")
    question_id = r.json()["id"]
    print(f"OK: created question  id={question_id}")

    # 1. Temp upload (no question_id) → 200, image_url returned
    r = s.post(
        f"{BASE_URL}/quizzes/{quiz_id}/upload-image",
        files={"file": ("test.png", io.BytesIO(PNG_1X1), "image/png")},
        data={"image_type": "question"},
        timeout=20,
    )
    check(r.status_code == 200, f"temp upload failed: {r.status_code} {r.text[:300]}")
    data = r.json()
    check("image_url" in data, f"temp upload response missing image_url: {data}")
    temp_url = data["image_url"]
    check(bool(temp_url), "image_url is empty")
    print(f"OK: temp image upload  url={temp_url}")

    # Verify the uploaded image is accessible
    img_r = requests.get(f"{APP_BASE_URL}{temp_url}" if temp_url.startswith("/") else temp_url,
                         verify=False, timeout=20)
    check(
        img_r.status_code == 200,
        f"uploaded image not accessible at {temp_url}: {img_r.status_code}"
    )
    print(f"OK: uploaded image is accessible")

    # 2. Permanent upload (with question_id) → 200, image_url returned
    r = s.post(
        f"{BASE_URL}/quizzes/{quiz_id}/upload-image",
        files={"file": ("perm.png", io.BytesIO(PNG_1X1), "image/png")},
        data={"image_type": "question", "question_id": str(question_id)},
        timeout=20,
    )
    check(r.status_code == 200, f"permanent upload failed: {r.status_code} {r.text[:300]}")
    data = r.json()
    check("image_url" in data, f"permanent upload response missing image_url: {data}")
    perm_url = data["image_url"]
    check(bool(perm_url), "permanent image_url is empty")
    print(f"OK: permanent image upload  url={perm_url}")

    # 3. Upload wrong file type → must not 500
    r = s.post(
        f"{BASE_URL}/quizzes/{quiz_id}/upload-image",
        files={"file": ("evil.txt", io.BytesIO(b"not an image"), "text/plain")},
        data={"image_type": "question"},
        timeout=20,
    )
    check(
        r.status_code != 500,
        f"non-image upload returned 500 — unhandled exception"
    )
    check(
        r.status_code in (400, 415, 422),
        f"non-image upload returned unexpected {r.status_code}"
    )
    print(f"OK: non-image upload correctly rejected  status={r.status_code}")

    # 4. Upload to a non-existent quiz → 404
    r = s.post(
        f"{BASE_URL}/quizzes/999999999/upload-image",
        files={"file": ("test.png", io.BytesIO(PNG_1X1), "image/png")},
        data={"image_type": "question"},
        timeout=20,
    )
    check(
        r.status_code in (403, 404),
        f"upload to nonexistent quiz returned {r.status_code}, expected 403/404"
    )
    print(f"OK: upload to non-existent quiz  status={r.status_code}")

    # Cleanup
    s.delete(f"{BASE_URL}/quizzes/{quiz_id}", timeout=20)
    print("OK: cleanup quiz (best-effort)")

    print("\nOK: uploads — all checks passed")


if __name__ == "__main__":
    main()
