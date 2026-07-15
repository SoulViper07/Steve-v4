from typing import List, Optional, Dict
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
from state import get_state_manager
from ui.terminal_renderer import _info, _ok, _err, _step, _warn
from router import IntelligentRouter, RoutingOverrides, get_router


class PlanningEngine:
    def __init__(self, workdir: Path, state_manager=None):
        self.workdir = workdir
        self.plans_dir = workdir / ".steve" / "plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self._sm = state_manager or get_state_manager(workdir)

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
        self._sm.update_task_classification(
            project_type=classification.project_type,
            complexity=classification.complexity,
            category=classification.category,
            languages=classification.languages,
            frameworks=classification.frameworks,
        )
        _ok(f"{classification.project_type} / {classification.complexity} / {classification.category}")

        _step("Planning architecture...")
        architecture = plan_architecture(request, classification)
        if architecture:
            self._sm.update_architecture(
                components=architecture.components,
                folder_structure=architecture.folder_structure,
                summary=architecture.data_flow_summary,
            )
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
        self._sm.save()
        _ok("Plan completed.")
        return plan

    def _build_execution_roadmap(
        self,
        classification: TaskClassification,
        features: Optional[FeaturePlan],
    ) -> ExecutionRoadmap:
        router = get_router(self.workdir)
        model_recs = features.model_recommendations if features else {}
        category = classification.category or "Programming"

        router_pipeline = router.build_pipeline(
            request=classification.description or "",
            category=category,
            planner_recommendations=model_recs,
        )

        steps = []
        order = 0
        stage_descriptions = {
            "plan": "Plan architecture and design",
            "architecture": "Design system architecture",
            "project_decomposition": "Decompose project into components",
            "frontend_creative": "Generate visual identity and UI design",
            "visual_identity": "Design visual identity and design language",
            "designing_ui": "Design user interface and experience",
            "implement": "Implement all project files",
            "code_gen": "Generate code from specifications",
            "implementing": "Build implementation",
            "implementing_refactor": "Refactor existing code",
            "implementing_interactions": "Implement interactive features",
            "generating_project": "Generate project scaffold and files",
            "generating_docs": "Generate documentation",
            "verify": "Verify correctness and quality",
            "verifying": "Verify file existence, content, and functionality",
            "verifier_analysis": "Analyze verification results",
            "repair": "Fix issues found during verification",
            "repairing": "Repair and fix defects",
            "repair_strategy": "Plan repair approach",
            "small_edit": "Apply targeted edit",
            "fast_fix": "Apply quick fix",
            "editing_file": "Edit source file",
            "analyzing": "Analyze problem and identify root cause",
            "analyzing_error": "Analyze error and traceback",
            "designing_architecture": "Design system architecture",
            "understanding_request": "Analyze and understand request",
            "planning": "Plan execution approach",
            "chat": "Engage in conversation",
            "researching": "Research and gather information",
            "summary": "Summarize completed work",
            "quality": "Perform quality review and refinement",
        }

        for route_step in router_pipeline.steps:
            desc = stage_descriptions.get(route_step.stage, f"Execute {route_step.stage}")
            steps.append(ExecutionStep(
                order=order,
                stage=route_step.stage,
                description=desc,
                model=route_step.model,
                estimated_calls=3 if route_step.stage in ("implement", "implementing", "generating_project", "code_gen") else 1,
            ))
            order += 1

        if not steps:
            steps.append(ExecutionStep(
                order=0, stage="implement",
                description="Implement based on plan",
                model="qwen2.5-coder:14b", estimated_calls=3,
            ))

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
