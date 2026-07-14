from typing import List, Optional
import uuid
import time
from pathlib import Path

from .execution_plan import (
    TaskClassification,
    ArchitecturePlan,
    UIPlan,
    FeaturePlan,
    ExecutionRoadmap,
    ExecutionStep,
    CompletePlan,
)
from .task_classifier import classify
from .architecture_planner import plan_architecture
from .ui_planner import plan_ui
from .feature_planner import plan_features
from ._llm import is_qwen_available
from ui.terminal_renderer import _info, _ok, _err, _step, _warn


class PlanningEngine:
    def __init__(self, workdir: Path):
        self.workdir = workdir
        self.plans_dir = workdir / ".steve" / "plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)

    def plan(self, request: str) -> Optional[CompletePlan]:
        if not is_qwen_available():
            _warn(f"qwen3:14b is not available. Check Ollama.")
            return self._minimum_viable_plan(request)

        task_id = uuid.uuid4().hex[:12]

        _step("Analyzing request...")
        classification = classify(request)
        if not classification:
            _err("Failed to classify task.")
            return None
        _ok(f"{classification.project_type} / {classification.complexity} / {classification.category}")

        _step("Planning architecture...")
        architecture = plan_architecture(request, classification)
        if architecture:
            comp_count = len(architecture.components)
            file_count = len(architecture.folder_structure)
            _ok(f"{comp_count} components, {file_count} files")

        _step("Planning UI...")
        ui = plan_ui(request, classification)
        if ui and ui.design_language:
            anims = ", ".join(ui.animations[:3])
            _ok(f"{ui.design_language} / {anims}")

        _step("Planning execution...")
        features = plan_features(request, classification)
        if features:
            feat_count = len(features.features)
            _ok(f"{feat_count} features, {len(features.verification_strategy)} verification steps")

        _step("Planning verification...")
        execution = self._build_execution_roadmap(classification, features)
        _ok(f"{execution.total_steps} execution steps")

        plan = CompletePlan(
            task_id=task_id,
            request=request,
            classification=classification or TaskClassification(),
            architecture=architecture or ArchitecturePlan(),
            ui=ui or UIPlan(),
            features=features or FeaturePlan(),
            execution=execution,
            raw_responses={},
        )

        plan.save(self.plans_dir)
        _ok("Plan completed.")
        return plan

    def _build_execution_roadmap(
        self,
        classification: TaskClassification,
        features: Optional[FeaturePlan],
    ) -> ExecutionRoadmap:
        steps = []
        order = 0

        steps.append(ExecutionStep(
            order=order, stage="plan", description="Plan architecture and design",
            model="qwen3:14b", estimated_calls=1,
        ))
        order += 1

        is_frontend = classification.frontend or classification.full_stack
        is_backend = classification.backend or classification.full_stack

        if is_frontend:
            steps.append(ExecutionStep(
                order=order, stage="design",
                description="Generate visual identity and UI design",
                model="mistral-small:latest", estimated_calls=1,
            ))
            order += 1

        steps.append(ExecutionStep(
            order=order, stage="implement",
            description=("Implement all project files" if is_frontend else "Implement backend code"),
            model="qwen2.5-coder:14b", estimated_calls=3,
        ))
        order += 1

        steps.append(ExecutionStep(
            order=order, stage="verify",
            description="Verify file existence, content quality, and functionality",
            model="qwen3:14b", estimated_calls=1,
        ))
        order += 1

        steps.append(ExecutionStep(
            order=order, stage="repair",
            description="Fix any issues found during verification (if needed)",
            model="qwen2.5-coder:14b", estimated_calls=2,
        ))
        order += 1

        steps.append(ExecutionStep(
            order=order, stage="quality",
            description="Perform quality review and refinement pass",
            model="qwen3:14b", estimated_calls=1,
        ))
        order += 1

        return ExecutionRoadmap(steps=steps)

    def _minimum_viable_plan(self, request: str) -> CompletePlan:
        task_id = uuid.uuid4().hex[:12]
        classification = TaskClassification(
            project_type="unknown",
            complexity="medium",
            category="general",
            description=request[:200],
        )
        architecture = None
        ui = None
        features = None
        execution = self._build_execution_roadmap(classification, features)

        plan = CompletePlan(
            task_id=task_id,
            request=request,
            classification=classification,
            architecture=ArchitecturePlan(),
            ui=UIPlan(),
            features=FeaturePlan(),
            execution=execution,
        )
        plan.save(self.plans_dir)
        return plan
