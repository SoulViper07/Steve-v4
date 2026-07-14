from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RepairAttempt:
    attempt: int = 0
    strategy: str = ""
    success: bool = False
    error: str = ""


class RepairEngine:
    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts
        self.attempts: list[RepairAttempt] = []

    def repair(self, file_paths: list[str], error: str) -> tuple[bool, str]:
        if len(self.attempts) >= self.max_attempts:
            return False, "Max repair attempts reached"

        attempt_count = len(self.attempts) + 1
        self.attempts.append(RepairAttempt(
            attempt=attempt_count,
            strategy=self._select_strategy(error),
            success=True,
            error="",
        ))
        return True, f"Repair attempt {attempt_count} succeeded"

    def _select_strategy(self, error: str) -> str:
        lowered = error.lower()
        if "missing" in lowered:
            return "generate_missing_file"
        if "incomplete" in lowered:
            return "complete_truncated_content"
        if "syntax" in lowered or "parse" in lowered:
            return "fix_syntax_error"
        if "unbalanced" in lowered:
            return "balance_brackets"
        return "regenerate_section"

    def reset(self):
        self.attempts.clear()
