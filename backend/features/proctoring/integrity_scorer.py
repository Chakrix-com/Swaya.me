"""
Behavioral biometrics integrity scorer.

Silent score deduction has been removed — integrity score is now driven
entirely by explicit, logged violations (tab switch, copy-paste, fullscreen
exit, etc.) so hosts can always explain a score reduction to a participant.
This class is kept as a stub for potential future use.
"""
from features.proctoring.schemas import BiometricSample


class IntegrityScorer:

    def score(self, sample: BiometricSample, current_score: int) -> int:
        return current_score
