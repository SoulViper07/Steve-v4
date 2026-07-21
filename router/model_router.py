import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

from .capabilities import (
    get_stage_role, get_stage_capabilities, get_category_capabilities,
    describe_capabilities, STAGE_ROLES,
)
from .model_profiles import (
    ModelProfile, get_profile, match_models_for_stage,
    enabled_profiles, all_profiles,
)
from .routing_rules import (
    RoutingOverrides, resolve_model, resolve_pipeline,
    load_overrides_from_env, apply_overrides,
)
from .performance import PerformanceTracker, get_tracker

from state import get_state_manager, StateManager
from config.model_config import MODEL_ROLES, model_for_stage, all_configured_models

from ui.terminal_renderer import (
    console, _plain_terminal, _info, _ok, _err, _warn, _step,
    get_pipeline,
)


@dataclass
class RouteStep:
    stage: str
    role: str
    model: str
    reason: str
    capabilities_needed: List[str]
    estimated_duration: str = ""
    planner_recommended: str = ""


@dataclass
class ExecutionPipeline:
    steps: List[RouteStep]
    category: str = ""
    overrides_applied: List[str] = field(default_factory=list)
    total_estimated_time: str = ""

    @property
    def total_steps(self) -> int:
        return len(self.steps)


def _friendly_model_name(model: str) -> str:
    name = model.split(":")[0].split("/")[-1]
    tag = model.split(":")[1] if ":" in model else ""
    return f"{name}:{tag}" if tag else name


def _estimate_duration(stage: str, model_profile: Optional[ModelProfile]) -> str:
    speed_map = {
        "very_fast": "10-20s",
        "fast": "20-40s",
        "medium": "40-90s",
        "slow": "90-180s",
    }
    base = speed_map.get(model_profile.speed if model_profile else "medium", "40-90s")
    stage_multipliers = {
        "plan": (1, 2),
        "architecture": (1, 2),
        "frontend_creative": (1, 2),
        "implement": (3, 5),
        "code_gen": (2, 4),
        "repair_strategy": (1, 1),
        "verifier_analysis": (1, 1),
        "small_edit": (1, 1),
        "implementing": (3, 5),
        "generating_project": (3, 6),
        "generating_docs": (1, 2),
    }
    mult = stage_multipliers.get(stage, (1, 2))
    return f"{mult[0]}-{mult[1]} calls"


_DEFAULT_CATEGORY_STAGES: Dict[str, List[str]] = {}

_PLANNER_ROLE_TO_STAGES: Dict[str, List[str]] = {
    "planner": ["plan", "architecture", "understanding_request", "planning", "planning_architecture", "designing_architecture", "project_decomposition"],
    "designer": ["frontend_creative", "designing_ui", "visual_identity", "animation_ideas", "ui_concept"],
    "engineer": ["implement", "code_gen", "generating_project", "implementing", "implementing_interactions", "implementing_refactor", "editing_file", "patch", "small_edit", "fast_fix", "generating_docs"],
    "verifier": ["verify", "verifying", "verifier_analysis", "final_verification"],
    "repairer": ["repair", "repairing", "repair_strategy"],
    "analyzer": ["analyzing", "analyzing_error"],
    "writer": ["generating_docs", "summary"],
}


def _map_planner_recs(planner_recommendations: Optional[Dict[str, str]]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if not planner_recommendations:
        return result
    for role, model in planner_recommendations.items():
        stages = _PLANNER_ROLE_TO_STAGES.get(role, [])
        for stage in stages:
            if stage not in result:
                result[stage] = model
    return result


def _load_category_stages():
    if _DEFAULT_CATEGORY_STAGES:
        return
    try:
        from config.model_config import get_routing_config
        rc = get_routing_config()
        stages_map = rc.get("execution_stages", {})
        for cat, stages in stages_map.items():
            _DEFAULT_CATEGORY_STAGES[cat] = stages
    except Exception:
        pass
    if not _DEFAULT_CATEGORY_STAGES:
        _DEFAULT_CATEGORY_STAGES.update({
            "Chat": ["chat"],
            "Programming": ["plan", "implement", "verify"],
            "Frontend UI": ["plan", "designing_ui", "implement", "verify"],
            "Backend": ["plan", "implement", "verify"],
            "Bug Fix": ["analyzing", "repairing", "verify"],
            "Debugging": ["analyzing_error", "verify"],
            "Refactor": ["plan", "implementing_refactor", "verify"],
            "Architecture": ["designing_architecture", "verify"],
            "Documentation": ["generating_docs", "verify"],
            "Project Generation": ["plan", "designing_ui", "generating_project", "implementing", "verify", "repair"],
            "File Editing": ["editing_file", "verify"],
            "Research": ["researching"],
            "Planning": ["plan"],
        })


class IntelligentRouter:
    def __init__(
        self,
        workdir: Optional[Path] = None,
        state_manager: Optional[StateManager] = None,
        overrides: Optional[RoutingOverrides] = None,
    ):
        self._workdir = (workdir or Path.cwd()).resolve()
        self._sm = state_manager or get_state_manager(self._workdir)
        self._tracker: Optional[PerformanceTracker] = None
        self._overrides = overrides or load_overrides_from_env()
        apply_overrides(self._overrides)
        _load_category_stages()
        self._repo_context: Optional[Dict] = None

    def set_repository_context(self, repo_summary: Dict):
        self._repo_context = repo_summary

    @property
    def repo_context(self) -> Optional[Dict]:
        return self._repo_context

    @property
    def tracker(self) -> PerformanceTracker:
        if self._tracker is None:
            self._tracker = get_tracker(self._workdir)
        return self._tracker

    def classify(self, request: str) -> str:
        try:
            from core.model_router import classify_task
            return classify_task(request)
        except Exception:
            lowered = request.lower().strip()
            _load_category_stages()
            scores = {}
            try:
                from config.model_config import get_routing_config
                rc = get_routing_config()
                for cat, cfg in rc.get("task_categories", {}).items():
                    score = sum(1 for kw in cfg.get("keywords", []) if kw in lowered)
                    if score > 0:
                        scores[cat] = score
            except Exception:
                pass
            if scores:
                return max(scores, key=scores.get)
            import re
            has_operational = bool(re.search(r"\b(build|create|generate|make|fix|refactor|implement|write|develop)\b", lowered))
            if has_operational:
                return "Programming"
            return "Chat"

    def get_stages_for_category(self, category: str) -> List[str]:
        _load_category_stages()
        return _DEFAULT_CATEGORY_STAGES.get(category, ["implement", "verify"])

    def select_model(
        self,
        stage: str,
        category: str = "",
        request: str = "",
        planner_recommendation: Optional[str] = None,
    ) -> Tuple[str, str]:
        model = resolve_model(
            stage=stage,
            category=category,
            request=request,
            overrides=self._overrides,
            planner_recommendation=planner_recommendation,
        )
        if not model:
            try:
                model = model_for_stage(stage)
            except Exception:
                model = "qwen3:14b"

        profile = get_profile(model)
        caps = get_stage_capabilities(stage)
        matched = [c for c in caps if profile and c in profile.capabilities] if profile else caps[:2]
        reason_parts = []
        if matched:
            reason_parts.append(f"Capabilities: {describe_capabilities(matched)}")
        if profile:
            reason_parts.append(f"Speed: {profile.speed}, Quality: {profile.quality}")
        reason = "; ".join(reason_parts) if reason_parts else "Capability-based routing"

        return model, reason

    def build_pipeline(
        self,
        request: str,
        category: Optional[str] = None,
        planner_recommendations: Optional[Dict[str, str]] = None,
    ) -> ExecutionPipeline:
        if category is None:
            category = self.classify(request)

        stage_recs = _map_planner_recs(planner_recommendations)
        combined_recs = dict(stage_recs)
        if planner_recommendations:
            combined_recs.update(planner_recommendations)

        stages = self.get_stages_for_category(category)
        overrides_applied = []

        if self._overrides.always_use:
            overrides_applied.append(f"Always use: {self._overrides.always_use}")
        if self._overrides.prefer:
            overrides_applied.append(f"Prefer: {self._overrides.prefer}")
        if self._overrides.disabled_models:
            overrides_applied.append(f"Disabled: {', '.join(self._overrides.disabled_models)}")
        if self._overrides.mode != "balanced":
            overrides_applied.append(f"Mode: {self._overrides.mode}")

        steps = []
        for stage in stages:
            rec = combined_recs.get(stage)
            model, reason = self.select_model(
                stage=stage,
                category=category,
                request=request,
                planner_recommendation=rec,
            )
            role = get_stage_role(stage)
            profile = get_profile(model)
            caps = get_stage_capabilities(stage)

            steps.append(RouteStep(
                stage=stage,
                role=role,
                model=model,
                reason=reason,
                capabilities_needed=caps,
                estimated_duration=_estimate_duration(stage, profile),
                planner_recommended=rec or "",
            ))

        total_est = f"{len(steps)} steps"
        return ExecutionPipeline(
            steps=steps,
            category=category,
            overrides_applied=overrides_applied,
            total_estimated_time=total_est,
        )

    def display_pipeline(self, pipeline: ExecutionPipeline):
        _step("Routing analysis...")
        if pipeline.category:
            _ok(f"Category: {pipeline.category}")

        if pipeline.overrides_applied:
            for o in pipeline.overrides_applied:
                _info(f"Override: {o}")

        role_model_map: Dict[str, str] = {}
        seen_roles: List[str] = []
        for step in pipeline.steps:
            if step.role not in role_model_map:
                role_model_map[step.role] = step.model
                seen_roles.append(step.role)

        _step("Route selected:")
        if _plain_terminal():
            for i, step in enumerate(pipeline.steps):
                friendly = _friendly_model_name(step.model)
                self._sm.set_model(step.model, step.stage, step.reason)
                print(f"  {step.role:>12}  \u2193  {friendly:30s}  [{step.stage}]")
                if step.capabilities_needed:
                    caps_str = describe_capabilities(step.capabilities_needed)
                    print(f"  {'':>12}     {'':30s}  ({caps_str})")
                if i < len(pipeline.steps) - 1:
                    print(f"  {'':>12}     {'':30s}")
        else:
            pipeline_display = get_pipeline()
            for i, step in enumerate(pipeline.steps):
                friendly = _friendly_model_name(step.model)
                self._sm.set_model(step.model, step.stage, step.reason)
                caps_str = describe_capabilities(step.capabilities_needed)
                label = f"{friendly}  [{caps_str}]" if caps_str else friendly

                if pipeline_display:
                    pipeline_display.model_switch(step.model, step.reason, step.stage)

                console.print(f"  [bold]{step.role:>12}[/bold] [dim]\u2192[/dim] [green]{friendly}[/green]")
                if caps_str:
                    console.print(f"  {'':>12}  [dim]({caps_str})[/dim]")
                if i < len(pipeline.steps) - 1:
                    console.print()

        _ok(f"Pipeline: {pipeline.total_steps} stage(s)")

    def display_compact_routing(self, pipeline: ExecutionPipeline):
        if _plain_terminal():
            self.display_pipeline(pipeline)
            return
        seen = {}
        for step in pipeline.steps:
            if step.role not in seen:
                seen[step.role] = step.model
        lines = []
        for role, model in seen.items():
            friendly = _friendly_model_name(model)
            lines.append(f"    {role:>12} \u2192 {friendly}")
        if lines:
            console.print(f"  [bold]Routing:[/bold]")
            for line in lines:
                console.print(f"  {line}")

    def select_and_display(
        self,
        request: str,
        category: Optional[str] = None,
        planner_recommendations: Optional[Dict[str, str]] = None,
    ) -> ExecutionPipeline:
        pipeline = self.build_pipeline(request, category, planner_recommendations)
        self.display_pipeline(pipeline)
        return pipeline

    def confirm_or_override(
        self,
        planner_recommendations: Dict[str, str],
        category: str,
        request: str,
    ) -> ExecutionPipeline:
        pipeline = self.build_pipeline(
            request=request,
            category=category,
            planner_recommendations=planner_recommendations,
        )
        overrides_made = []
        for step in pipeline.steps:
            if step.planner_recommended and step.model != step.planner_recommended:
                overrides_made.append(
                    f"{step.role}: {_friendly_model_name(step.planner_recommended)} \u2192 {_friendly_model_name(step.model)}"
                )
        if overrides_made:
            _info("Router overrides Planner recommendation:")
            for o in overrides_made:
                _info(f"  {o}")
        else:
            _ok("Router confirms Planner recommendation")
        return pipeline

    def get_pipeline_for_task(
        self,
        task_request: str,
        planner_recs: Optional[Dict[str, str]] = None,
    ) -> ExecutionPipeline:
        return self.select_and_display(
            request=task_request,
            planner_recommendations=planner_recs,
        )


_GLOBAL_ROUTER: Optional[IntelligentRouter] = None


def get_router(
    workdir: Optional[Path] = None,
    overrides: Optional[RoutingOverrides] = None,
) -> IntelligentRouter:
    global _GLOBAL_ROUTER
    if _GLOBAL_ROUTER is None:
        _GLOBAL_ROUTER = IntelligentRouter(workdir, overrides=overrides)
    return _GLOBAL_ROUTER


def reset_router():
    global _GLOBAL_ROUTER
    _GLOBAL_ROUTER = None


def route_task(
    request: str,
    workdir: Optional[Path] = None,
    overrides: Optional[RoutingOverrides] = None,
) -> ExecutionPipeline:
    router = get_router(workdir, overrides)
    return router.get_pipeline_for_task(request)
