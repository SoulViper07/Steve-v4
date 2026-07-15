import os
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field

from .capabilities import get_stage_capabilities, get_category_capabilities
from .model_profiles import (
    ModelProfile, match_models_for_stage, get_profile,
    disable_model as _disable, enable_model as _enable,
    enabled_profiles, all_profiles,
)


@dataclass
class RoutingOverrides:
    always_use: Optional[str] = None
    prefer: Optional[str] = None
    disabled_models: List[str] = field(default_factory=list)
    mode: str = "balanced"


@dataclass
class RoutingRule:
    name: str
    condition: Callable[["RoutingContext"], bool]
    action: Callable[["RoutingContext"], Optional[str]]
    priority: int = 0


@dataclass
class RoutingContext:
    stage: str
    category: str
    request: str
    overrides: RoutingOverrides
    available_models: List[ModelProfile]
    planner_recommendation: Optional[str] = None


_ROUTING_RULES: List[RoutingRule] = []


def _always_use_override(ctx: RoutingContext) -> Optional[str]:
    if ctx.overrides.always_use:
        profile = get_profile(ctx.overrides.always_use)
        if profile and profile.enabled:
            return profile.name
    return None


def _preferred_model(ctx: RoutingContext) -> Optional[str]:
    if ctx.overrides.prefer:
        profile = get_profile(ctx.overrides.prefer)
        if profile and profile.enabled:
            caps = get_stage_capabilities(ctx.stage)
            if any(c in profile.capabilities for c in caps):
                return profile.name
    return None


def _planner_recommendation(ctx: RoutingContext) -> Optional[str]:
    if ctx.planner_recommendation:
        profile = get_profile(ctx.planner_recommendation)
        if profile and profile.enabled:
            return profile.name
    return None


def _capability_match(ctx: RoutingContext) -> Optional[str]:
    matches = match_models_for_stage(ctx.stage, ctx.overrides.mode)
    if matches:
        return matches[0].name
    return None


def _first_available(ctx: RoutingContext) -> Optional[str]:
    for p in ctx.available_models:
        return p.name
    return None


def register_rule(rule: RoutingRule):
    _ROUTING_RULES.append(rule)
    _ROUTING_RULES.sort(key=lambda r: r.priority, reverse=True)


def _init_builtin_rules():
    if _ROUTING_RULES:
        return
    register_rule(RoutingRule(
        name="always_use_override",
        condition=lambda ctx: ctx.overrides.always_use is not None,
        action=_always_use_override,
        priority=100,
    ))
    register_rule(RoutingRule(
        name="preferred_model",
        condition=lambda ctx: ctx.overrides.prefer is not None,
        action=_preferred_model,
        priority=80,
    ))
    register_rule(RoutingRule(
        name="planner_recommendation",
        condition=lambda ctx: ctx.planner_recommendation is not None,
        action=_planner_recommendation,
        priority=60,
    ))
    register_rule(RoutingRule(
        name="capability_match",
        condition=lambda ctx: True,
        action=_capability_match,
        priority=40,
    ))
    register_rule(RoutingRule(
        name="first_available",
        condition=lambda ctx: True,
        action=_first_available,
        priority=0,
    ))


_init_builtin_rules()


def resolve_model(
    stage: str,
    category: str = "",
    request: str = "",
    overrides: Optional[RoutingOverrides] = None,
    planner_recommendation: Optional[str] = None,
) -> Optional[str]:
    ctx = RoutingContext(
        stage=stage,
        category=category,
        request=request,
        overrides=overrides or RoutingOverrides(),
        available_models=enabled_profiles(),
        planner_recommendation=planner_recommendation,
    )

    for rule in _ROUTING_RULES:
        try:
            if rule.condition(ctx):
                result = rule.action(ctx)
                if result:
                    return result
        except Exception:
            continue

    return None


def resolve_pipeline(
    stages: List[str],
    category: str = "",
    request: str = "",
    overrides: Optional[RoutingOverrides] = None,
    planner_recommendations: Optional[Dict[str, str]] = None,
) -> List[Dict[str, str]]:
    steps = []
    for stage in stages:
        rec = (planner_recommendations or {}).get(stage)
        model = resolve_model(
            stage=stage,
            category=category,
            request=request,
            overrides=overrides,
            planner_recommendation=rec,
        )
        steps.append({
            "stage": stage,
            "model": model or "qwen3:14b",
            "planner_recommended": rec or "",
        })
    return steps


def load_overrides_from_env() -> RoutingOverrides:
    overrides = RoutingOverrides()
    always = os.environ.get("STEVE_ROUTER_ALWAYS_USE", "").strip()
    if always:
        overrides.always_use = always
    prefer = os.environ.get("STEVE_ROUTER_PREFER", "").strip()
    if prefer:
        overrides.prefer = prefer
    disabled = os.environ.get("STEVE_ROUTER_DISABLED", "").strip()
    if disabled:
        overrides.disabled_models = [m.strip() for m in disabled.split(",")]
    mode = os.environ.get("STEVE_ROUTER_MODE", "").strip().lower()
    if mode in ("performance", "quality", "balanced"):
        overrides.mode = mode
    return overrides


def apply_disabled_models(overrides: RoutingOverrides):
    for m in overrides.disabled_models:
        _disable(m)


def apply_overrides(overrides: RoutingOverrides):
    apply_disabled_models(overrides)


def set_always_use(model: str):
    os.environ["STEVE_ROUTER_ALWAYS_USE"] = model


def set_prefer(model: str):
    os.environ["STEVE_ROUTER_PREFER"] = model


def set_mode(mode: str):
    if mode in ("performance", "quality", "balanced"):
        os.environ["STEVE_ROUTER_MODE"] = mode


def clear_overrides():
    for key in ["STEVE_ROUTER_ALWAYS_USE", "STEVE_ROUTER_PREFER", "STEVE_ROUTER_DISABLED", "STEVE_ROUTER_MODE"]:
        os.environ.pop(key, None)
