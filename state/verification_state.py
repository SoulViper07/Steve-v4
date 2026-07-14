from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class VerificationState:
    status: str = "pending"
    score: float = 0.0
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    issues: List[Dict] = field(default_factory=list)
    quality_score: float = 0.0
    repair_attempts: int = 0
    repair_success: bool = False
