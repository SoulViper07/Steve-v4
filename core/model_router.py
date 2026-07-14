import os
import re
import json
import time
from pathlib import Path
from typing import Optional

from config.model_config import (
    MODEL_ROLES, model_for_stage, options_for_stage,
    stage_to_role, role_config, DEFAULT_FALLBACK_MODEL, FALLBACK_CHAIN,
    get_routing_config, resolve_model, get_model_map,
)
from ui.terminal_renderer import _info, _step, _ok, _warn, _progress, get_pipeline

_route_config = get_routing_config()
_task_categories = _route_config.get("task_categories", {})
_execution_stages = _route_config.get("execution_stages", {})
_stage_model_map = _route_config.get("stage_model_map", {})
_model_map = get_model_map()

_model_name_cache = {}


def _friendly_model_name(model: str) -> str:
    if model in _model_name_cache:
        return _model_name_cache[model]
    name = model.split(":")[0].split("/")[-1]
    tag = model.split(":")[1] if ":" in model else ""
    label = f"{name}:{tag}" if tag else name
    _model_name_cache[model] = label
    return label


def classify_task(user_text: str) -> str:
    lowered = user_text.lower().strip()
    scores = {}
    for cat, cfg in _task_categories.items():
        score = 0
        for kw in cfg.get("keywords", []):
            if kw in lowered:
                score += 1
        if score > 0:
            scores[cat] = score

    has_operational = bool(re.search(r"\b(build|create|generate|make|scaffold|fix|edit|refactor|improve|upgrade|implement|write|develop)\b", lowered))
    has_project_scope = bool(re.search(r"\b(project|app|site|website|frontend|backend|api|server|page|ui|dashboard)\b", lowered))
    asks_question = "?" in lowered
    mentions_path = bool(re.search(r"[\w./\\-]+\.[A-Za-z0-9]{1,8}\b", lowered))

    if scores:
        best = max(scores, key=scores.get)
        if best == "Chat" and has_operational:
            if has_project_scope:
                return "Project Generation"
            if mentions_path:
                return "File Editing"
            return "Programming"
        return best

    if has_operational and has_project_scope:
        return "Project Generation"
    if has_operational and mentions_path:
        return "File Editing"
    if has_operational:
        return "Programming"
    if has_project_scope and asks_question:
        return "Architecture"
    if asks_question:
        return "Research"
    return "Chat"


def get_execution_stages_for_task(category: str) -> list[str]:
    return _execution_stages.get(category, ["implement"])


def select_model_for_stage(stage: str) -> str:
    model_key = _stage_model_map.get(stage, "default_model")
    model = _model_map.get(model_key)
    if model:
        return model
    return model_for_stage(stage)


def _model_switched_banner(old_model: str, new_model: str, reason: str):
    friendly_old = _friendly_model_name(old_model) if old_model else "none"
    friendly_new = _friendly_model_name(new_model)
    _ok(f"Switched model: {friendly_old} -> {friendly_new}")
    _info(f"Reason: {reason}")
    pipeline = get_pipeline()
    if pipeline:
        pipeline.add("🔄", f"Switched: {friendly_old} → {friendly_new} ({reason})", "step")
        pipeline.model_switch(friendly_new, reason)


class TaskStageRouter:
    def __init__(self, manual_model: Optional[str] = None):
        self.manual_model = manual_model
        self.warmed_models: set[str] = set()
        self.current_model: Optional[str] = None
        self.last_switch_reason: str = ""

    def select(self, stage: str, request: str = "", route=None) -> str:
        if self.manual_model:
            return self.manual_model
        return select_model_for_stage(stage)

    def select_with_switch(self, stage: str, request: str = "", route=None) -> str:
        reason_map = {
            "plan": "Architecture planning",
            "architecture": "Architecture planning",
            "project_decomposition": "Task decomposition",
            "frontend_creative": "UI creativity",
            "visual_identity": "Visual identity",
            "animation_ideas": "Animation design",
            "implement": "Code implementation",
            "code_gen": "Code generation",
            "repair_strategy": "Repair strategy",
            "verifier_analysis": "Verification analysis",
            "small_edit": "Small edit",
            "fast_fix": "Fast fix",
        }

        if self.manual_model:
            if self.current_model != self.manual_model:
                self.last_switch_reason = "Manual override"
                self.current_model = self.manual_model
            return self.manual_model

        selected = select_model_for_stage(stage)
        if self.current_model and self.current_model != selected:
            reason = reason_map.get(stage, f"Stage: {stage}")
            _model_switched_banner(self.current_model, selected, reason)

        self.current_model = selected
        self.last_switch_reason = reason_map.get(stage, f"Stage: {stage}")
        return selected

    def select_options(self, stage: str) -> dict:
        return options_for_stage(stage)

    def role_label(self, stage: str) -> str:
        role_name = stage_to_role(stage)
        cfg = role_config(role_name)
        return cfg.get("label", "Coder")

    def warm_models(self, ollama_warm_fn, keep_alive: str = "5m", timeout_ms: int = 60000):
        models_to_warm = []
        for stage in ["plan", "frontend_creative", "implement", "small_edit"]:
            m = select_model_for_stage(stage)
            if m not in models_to_warm:
                models_to_warm.append(m)
        for model in models_to_warm:
            if model not in self.warmed_models:
                ok, elapsed, detail = ollama_warm_fn(model, keep_alive, timeout_ms)
                if ok:
                    self.warmed_models.add(model)
                    _info(f"  Warmed {_friendly_model_name(model)} ({elapsed:.0f}ms)")
                else:
                    _info(f"  Skipped {_friendly_model_name(model)}: {detail}")

    def display_current_model(self, stage: str):
        model = select_model_for_stage(stage)
        friendly = _friendly_model_name(model)
        _step(f"Selected model: {friendly}")


_GLOBAL_ROUTER: Optional[TaskStageRouter] = None


def get_router(manual_model: Optional[str] = None) -> TaskStageRouter:
    global _GLOBAL_ROUTER
    if _GLOBAL_ROUTER is None:
        _GLOBAL_ROUTER = TaskStageRouter(manual_model)
    return _GLOBAL_ROUTER


def reset_router():
    global _GLOBAL_ROUTER
    _GLOBAL_ROUTER = None


CREATIVE_INDICATORS = [
    "creative", "unique", "original", "innovative", "modern", "stunning",
    "beautiful", "elegant", "sleek", "futuristic", "minimalist", "vibrant",
    "eye-catching", "memorable", "distinctive", "fresh", "bold",
    "ui", "ux", "frontend", "design", "layout", "animation", "visual",
    "landing page", "dashboard", "login page", "website", "web app",
]

PLANNING_INDICATORS = [
    "plan", "architecture", "design", "strategy", "approach",
    "how should", "what should", "structure", "organize",
    "refactor", "migrate", "restructure",
]


def detect_stage(request: str, route=None) -> str:
    lowered = request.lower()
    is_creation = bool(re.search(r"\b(build|create|generate|make|scaffold|bootstrap|set up|setup)\b", lowered))
    is_frontend = any(token in lowered for token in CREATIVE_INDICATORS)
    is_planning = any(token in lowered for token in PLANNING_INDICATORS)

    if is_planning and not is_creation:
        return "plan"
    if is_creation and is_frontend:
        return "frontend_creative"
    if is_creation:
        return "plan"
    return "implement"
