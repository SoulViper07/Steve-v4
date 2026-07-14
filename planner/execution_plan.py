from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from pathlib import Path
import json


@dataclass
class TaskClassification:
    project_type: str = ""
    complexity: str = "medium"
    category: str = ""
    frontend: bool = False
    backend: bool = False
    full_stack: bool = False
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class ArchitecturePlan:
    folder_structure: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    pages: List[str] = field(default_factory=list)
    api_endpoints: List[Dict[str, str]] = field(default_factory=list)
    database_tables: List[Dict[str, str]] = field(default_factory=list)
    data_flow_summary: str = ""


@dataclass
class UIPlan:
    design_language: str = ""
    animations: List[str] = field(default_factory=list)
    responsiveness: str = "yes"
    accessibility_features: List[str] = field(default_factory=list)
    color_scheme: str = ""
    typography: str = ""
    layout_archetype: str = ""


@dataclass
class FeaturePlan:
    features: List[Dict[str, str]] = field(default_factory=list)
    verification_strategy: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    completion_criteria: List[str] = field(default_factory=list)
    model_recommendations: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExecutionStep:
    order: int = 0
    stage: str = ""
    description: str = ""
    model: str = ""
    estimated_calls: int = 1


@dataclass
class ExecutionRoadmap:
    steps: List[ExecutionStep] = field(default_factory=list)

    @property
    def total_steps(self) -> int:
        return len(self.steps)


@dataclass
class CompletePlan:
    task_id: str = ""
    request: str = ""
    classification: TaskClassification = field(default_factory=TaskClassification)
    architecture: ArchitecturePlan = field(default_factory=ArchitecturePlan)
    ui: UIPlan = field(default_factory=UIPlan)
    features: FeaturePlan = field(default_factory=FeaturePlan)
    execution: ExecutionRoadmap = field(default_factory=ExecutionRoadmap)
    raw_responses: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "request": self.request,
            "classification": asdict(self.classification),
            "architecture": asdict(self.architecture),
            "ui": asdict(self.ui),
            "features": asdict(self.features),
            "execution": {
                "steps": [asdict(s) for s in self.execution.steps],
                "total_steps": self.execution.total_steps,
            },
        }

    def save(self, plans_dir: Path):
        task_dir = plans_dir / self.task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()
        for key, filename in [("classification", "task.json"), ("architecture", "architecture.json")]:
            with open(task_dir / filename, "w", encoding="utf-8") as f:
                json.dump(data.get(key, {}), f, indent=2, ensure_ascii=False)
        execution_data = {
            "ui": data.get("ui", {}),
            "features": data.get("features", {}),
            "execution": data.get("execution", {}),
            "raw_responses": self.raw_responses,
        }
        with open(task_dir / "execution.json", "w", encoding="utf-8") as f:
            json.dump(execution_data, f, indent=2, ensure_ascii=False)
