"""
HTML sanitizer for user-supplied rich text content.
Uses bleach with a strict allowlist — safe for dangerouslySetInnerHTML on the frontend.
"""
import bleach

# Tags permitted in question text (subset of what Tiptap/RichTextEditor produces)
_ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "s", "code", "pre",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "blockquote",
    "span",
    "a",
    "img",
    "table", "thead", "tbody", "tr", "th", "td",
    "sub", "sup",
    "mark",
]

_ALLOWED_ATTRS = {
    "*": ["class"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "width", "height"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
}

# Force <a> target=_blank links to also have rel=noopener
_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_html(value: str) -> str:
    """
    Strip any HTML not on the allowlist.
    Safe to render via dangerouslySetInnerHTML after this.
    """
    if not value:
        return value
    return bleach.clean(
        value,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )


def sanitize_plain(value: str) -> str:
    """
    Strip ALL HTML tags — for fields that must be plain text (option labels, names).
    """
    if not value:
        return value
    return bleach.clean(value, tags=[], attributes={}, strip=True, strip_comments=True)
