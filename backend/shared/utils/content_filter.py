"""
Content filter utility — thin wrapper around better-profanity.
Initialised once at module level so the word list is only loaded once.
"""
import re
from better_profanity import profanity
from shared.exceptions.quiz import ContentFilterError

profanity.load_censor_words()

_HTML_TAG_RE = re.compile(r'<[^>]+>')


def _strip_html(text: str) -> str:
    """Remove HTML tags so code attributes/class names don't trigger false positives."""
    return _HTML_TAG_RE.sub(' ', text)


def check_content(text: str, field_name: str = "text") -> None:
    """Raise ContentFilterError if text contains profanity/offensive content."""
    if text and profanity.contains_profanity(_strip_html(text)):
        raise ContentFilterError(f"{field_name} contains inappropriate language")
