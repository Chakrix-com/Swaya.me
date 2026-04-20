"""
Behavioral biometrics integrity scorer.
"""
import statistics
from features.proctoring.schemas import BiometricSample


def _coefficient_of_variation(values: list[int]) -> float:
    if len(values) < 2:
        return 1.0
    mean = statistics.mean(values)
    if mean == 0:
        return 0.0
    return statistics.stdev(values) / mean


def _path_entropy(mouse_path: list[dict]) -> float:
    if len(mouse_path) < 3:
        return 1.0
    directions = []
    for i in range(1, len(mouse_path)):
        dx = mouse_path[i].get("x", 0) - mouse_path[i-1].get("x", 0)
        dy = mouse_path[i].get("y", 0) - mouse_path[i-1].get("y", 0)
        directions.append((dx, dy))

    unique = len(set(directions))
    return unique / len(directions)


class IntegrityScorer:

    def score(self, sample: BiometricSample, current_score: int) -> int:
        deductions = 0

        if sample.mouse_path:
            entropy = _path_entropy(sample.mouse_path)
            if entropy < 0.2:
                deductions += 15

        if sample.keystroke_intervals:
            cv = _coefficient_of_variation(sample.keystroke_intervals)
            if cv < 0.05:
                deductions += 20

            backspace_ratio = (
                sample.backspace_count / len(sample.keystroke_intervals)
                if sample.keystroke_intervals else 0
            )
            if backspace_ratio < 0.01 and len(sample.keystroke_intervals) > 10:
                deductions += 10

        if sample.time_to_first_interaction_ms > 0 and sample.time_to_first_interaction_ms < 500:
            deductions += 20

        return max(0, current_score - deductions)
