"""
Coding-challenge grading job — the scheduled (not request-handler) pipeline that
runs after /submit: stop/start power-cycle, hidden-test injection, test execution,
transcript/timeline harvest, AI-judged scoring, and cleanup.
"""
import logging

logger = logging.getLogger(__name__)


async def run_grading_job(submission_id: int) -> None:
    """Placeholder — real harvest+scoring pipeline lands in the next commit (6.6a/6.6b).
    /submit (6.5) needs a real, importable function to schedule against right now."""
    raise NotImplementedError("run_grading_job not yet implemented (lands in 6.6a/6.6b)")
