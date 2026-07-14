from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class TaskState:
    request: str = ""
    task_id: str = ""
    category: str = ""
    project_type: str = ""
    complexity: str = ""
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    classification_raw: Dict = field(default_factory=dict)
    planner_progress: str = ""
    architecture_summary: str = ""
    feature_summary: str = ""
