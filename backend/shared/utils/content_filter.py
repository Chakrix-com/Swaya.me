"""
Content filter utility — thin wrapper around better-profanity.
Initialised once at module level so the word list is only loaded once.
"""
from better_profanity import profanity
from shared.exceptions.quiz import ContentFilterError

profanity.load_censor_words()


def check_content(text: str, field_name: str = "text") -> None:
    """Raise ContentFilterError if text contains profanity/offensive content."""
    if text and profanity.contains_profanity(text):
        raise ContentFilterError(f"{field_name} contains inappropriate language")
