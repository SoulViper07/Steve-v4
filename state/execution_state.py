from dataclasses import dataclass, field
from typing import List


@dataclass
class ExecutionState:
    task_id: str = ""
    current_stage: str = ""
    stages_completed: List[str] = field(default_factory=list)
    current_activity: str = ""
    start_time: float = 0.0
    elapsed_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
