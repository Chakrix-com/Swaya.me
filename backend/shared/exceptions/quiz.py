"""
Custom exceptions for Quiz feature
"""


class QuizNotFoundError(Exception):
    """Quiz not found"""
    pass


class QuestionNotFoundError(Exception):
    """Question not found"""
    pass


class SessionNotFoundError(Exception):
    """Session not found"""
    pass


class ParticipantNotFoundError(Exception):
    """Participant not found"""
    pass


class QuizValidationError(Exception):
    """Quiz validation failed"""
    pass


class InvalidQuizStatusError(Exception):
    """Invalid quiz status for operation"""
    pass


class InvalidSessionStatusError(Exception):
    """Invalid session status for operation"""
    pass


class DuplicateAnswerError(Exception):
    """Answer already submitted"""
    pass


class QuestionNotOpenError(Exception):
    """Question is not open for answers"""
    pass


class TierLimitExceededError(Exception):
    """Tier limit exceeded"""
    pass


class ContentFilterError(Exception):
    """Submitted content failed the profanity/content filter"""
    pass


class ProctoringViolationError(Exception):
    """Proctoring requirement not met or violation detected"""
    pass
