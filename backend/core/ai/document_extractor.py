"""
Document text extractor for AI question generation.

Supports PDF, DOCX, TXT files and public URLs.
Returns plain text truncated to MAX_CHARS for safe use as an LLM prompt.
"""
from __future__ import annotations

import io
import ipaddress
import re
import socket
import logging
from typing import Optional
from urllib.parse import urljoin, urlsplit

import httpx
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

MAX_CHARS = 12_000
MIN_CHARS = 100

_SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
}

_URL_FETCH_TIMEOUT = 15.0
_MAX_URL_BYTES = 5 * 1024 * 1024  # 5 MB for URL content
_MAX_REDIRECTS = 5  # cap manual redirect-following (SSRF guard, see below)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _truncate(text: str) -> str:
    text = text.strip()
    if len(text) <= MAX_CHARS:
        return text
    return text[:MAX_CHARS] + "\n[... truncated at 12,000 chars]"


def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean_extracted(text: str) -> str:
    """Remove repeated short lines (page numbers, headers/footers)."""
    lines = text.splitlines()
    from collections import Counter
    short_lines = [l.strip() for l in lines if 0 < len(l.strip()) <= 6]
    repeats = {l for l, c in Counter(short_lines).items() if c >= 3}
    cleaned = [l for l in lines if l.strip() not in repeats]
    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Extractors ─────────────────────────────────────────────────────────────────

def _extract_pdf(data: bytes) -> str:
    try:
        import pypdf
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF extraction unavailable")

    reader = pypdf.PdfReader(io.BytesIO(data))

    if reader.is_encrypted:
        raise HTTPException(status_code=400, detail="PDF is password-protected. Please provide an unlocked PDF.")

    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue

    text = "\n".join(parts)
    if len(text.strip()) < MIN_CHARS:
        raise HTTPException(
            status_code=422,
            detail="No extractable text found. This appears to be a scanned PDF. Try a text-based PDF."
        )
    return _clean_extracted(text)


def _extract_docx(data: bytes) -> str:
    try:
        from docx import Document
    except ImportError:
        raise HTTPException(status_code=500, detail="DOCX extraction unavailable")

    doc = Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    # Also grab table cell text
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    parts.append(cell.text.strip())

    text = "\n".join(parts)
    if len(text.strip()) < MIN_CHARS:
        raise HTTPException(status_code=422, detail="Not enough text extracted from this document.")
    return text


def _extract_txt(data: bytes) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1", errors="replace")
    if len(text.strip()) < MIN_CHARS:
        raise HTTPException(status_code=422, detail="File appears to be empty or too short.")
    return text


# ── SSRF guard ─────────────────────────────────────────────────────────────────
#
# `extract_from_url` fetches an arbitrary, user-supplied URL server-side. Without
# validation this is a classic SSRF: an attacker can point it at cloud instance
# metadata (169.254.169.254), loopback-only internal services, or other hosts on
# the VM's private network and have the response returned straight back to them.
# We resolve the hostname ourselves (not just pattern-match the literal string,
# so a public-looking hostname that resolves to an internal IP is also caught)
# and reject if any resolved address is private/loopback/link-local/reserved/
# multicast. Because a single check up front can be bypassed by a redirect
# (an initially-public, validated URL responding with a 302 to an internal
# target — including DNS-rebinding-style setups), redirects are followed
# manually below with the same validation re-applied on every hop, capped at
# `_MAX_REDIRECTS` hops.

def _is_ip_disallowed(ip_str: str) -> bool:
    """True if `ip_str` is not a legitimate public-internet address."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparseable -> fail closed

    # Unwrap IPv4-mapped IPv6 addresses (::ffff:127.0.0.1) so mapped
    # loopback/private addresses are caught by the same IPv4 checks.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped

    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _validate_url_for_ssrf(url: str) -> None:
    """Resolve `url`'s host via DNS and reject if any resolved IP is internal.

    Checks every returned A/AAAA record, not just the first: a hostname can
    have multiple addresses and an attacker only needs one of them to land
    inside the network for SSRF to succeed.
    """
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL.")

    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Could not resolve the provided URL's host.")

    if not addrinfo or any(_is_ip_disallowed(info[4][0]) for info in addrinfo):
        # Deliberately generic message — do not reveal *why* it was
        # rejected (which internal range/service), so this can't be used
        # to fingerprint internal network topology.
        raise HTTPException(status_code=400, detail="This URL cannot be fetched.")


# ── Public API ─────────────────────────────────────────────────────────────────

async def extract_from_file(file: UploadFile) -> tuple[str, str]:
    """
    Extract plain text from an uploaded file.
    Returns (text, source_label).
    Raises HTTPException on unsupported type, password protection, or empty content.
    """
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    filename = file.filename or "file"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Infer type from extension if content-type is generic
    if content_type in ("application/octet-stream", "binary/octet-stream", ""):
        if ext == "pdf":
            content_type = "application/pdf"
        elif ext == "docx":
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext == "txt":
            content_type = "text/plain"

    if content_type not in _SUPPORTED_MIME_TYPES and ext not in ("pdf", "docx", "txt"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. Please upload a PDF, DOCX, or TXT file."
        )

    data = await file.read()

    if content_type == "application/pdf" or ext == "pdf":
        text = _extract_pdf(data)
    elif content_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ) or ext == "docx":
        text = _extract_docx(data)
    else:
        text = _extract_txt(data)

    return _truncate(text), filename


async def extract_from_url(url: str) -> tuple[str, str]:
    """
    Fetch a public URL and extract plain text.
    Returns (text, source_label).
    Raises HTTPException on network errors, access denied, or empty content.
    """
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    # follow_redirects is deliberately OFF here — see the SSRF guard comment
    # above. Each hop is validated (resolved + IP-checked) before it is
    # fetched, and we bail out after _MAX_REDIRECTS hops.
    current_url = url
    resp = None
    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=_URL_FETCH_TIMEOUT,
            headers={"User-Agent": "Swaya.me/1.0 (content-extractor)"},
        ) as client:
            for _ in range(_MAX_REDIRECTS + 1):
                _validate_url_for_ssrf(current_url)
                resp = await client.get(current_url)
                if resp.status_code not in (301, 302, 303, 307, 308):
                    break
                location = resp.headers.get("location")
                if not location:
                    break
                current_url = urljoin(current_url, location)
                if not current_url.startswith(("http://", "https://")):
                    raise HTTPException(status_code=400, detail="This URL cannot be fetched.")
            else:
                raise HTTPException(status_code=400, detail="Too many redirects while fetching this URL.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="URL request timed out. Check the URL and try again.")
    except httpx.RequestError as e:
        # Do not leak the raw exception text to the client: besides being
        # an internal-detail leak, subtly different messages/timings across
        # connect-refused/timeout/DNS-failure outcomes are themselves a
        # blind-SSRF port-scanning primitive when combined with the URL
        # fetch above. Log the real detail server-side only.
        logger.exception("Failed to fetch URL for text extraction (url=%s)", current_url)
        raise HTTPException(status_code=400, detail="Unable to fetch the provided URL.")

    if resp.status_code == 403:
        raise HTTPException(status_code=400, detail="Could not access URL (403 Forbidden). The page may require a login.")
    if resp.status_code == 404:
        raise HTTPException(status_code=400, detail="URL returned 404 Not Found.")
    if resp.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"Could not access URL (HTTP {resp.status_code}).")

    content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()

    # If the URL points directly to a PDF, extract it as such
    if content_type == "application/pdf":
        if len(resp.content) > _MAX_URL_BYTES:
            raise HTTPException(status_code=413, detail="PDF from URL is too large (max 5 MB).")
        text = _extract_pdf(resp.content)
        label = url.split("/")[-1] or url
        return _truncate(text), label

    if "text" not in content_type and "html" not in content_type:
        raise HTTPException(
            status_code=422,
            detail=f"URL returned unsupported content type '{content_type}'. Only HTML pages and PDFs are supported."
        )

    text = _strip_html(resp.text)
    if len(text.strip()) < MIN_CHARS:
        raise HTTPException(status_code=422, detail="Not enough text found at this URL.")

    label = url.split("//", 1)[-1].split("/")[0]  # domain as label
    return _truncate(text), label
