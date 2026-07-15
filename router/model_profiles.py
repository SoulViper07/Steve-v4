from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .capabilities import STAGE_CAPABILITIES


@dataclass
class ModelProfile:
    name: str
    short_name: str
    capabilities: List[str]
    strengths: List[str]
    weaknesses: List[str]
    speed: str
    quality: str
    priority: int
    enabled: bool = True
    default_temperature: float = 0.3
    context_window: int = 4096
    aliases: List[str] = field(default_factory=list)


_MODEL_REGISTRY: Dict[str, ModelProfile] = {}

MODEL_PROFILES_DATA = [
    ModelProfile(
        name="qwen3:14b",
        short_name="qwen3",
        capabilities=[
            "planning", "reasoning", "architecture", "task_analysis", "project_decomposition",
        ],
        strengths=["planning", "reasoning", "architecture", "system design"],
        weaknesses=["fast_edits", "small_repairs", "lightweight_coding"],
        speed="medium",
        quality="high",
        priority=1,
        default_temperature=0.3,
        context_window=8192,
        aliases=["qwen3:latest", "qwen3"],
    ),
    ModelProfile(
        name="qwen2.5-coder:14b",
        short_name="qwen2.5-coder",
        capabilities=[
            "code_generation", "refactoring", "bug_fixing", "file_implementation",
        ],
        strengths=["code_generation", "refactoring", "structured output", "bug_fixing"],
        weaknesses=["ui_design", "creative_design", "visual_refinement"],
        speed="medium",
        quality="high",
        priority=2,
        default_temperature=0.15,
        context_window=8192,
        aliases=["qwen2.5-coder:latest", "qwen2.5-coder"],
    ),
    ModelProfile(
        name="mistral-small:latest",
        short_name="mistral-small",
        capabilities=[
            "ui_design", "ux_design", "visual_refinement", "design_language",
        ],
        strengths=["ui_design", "ux_design", "visual_refinement", "creative tasks"],
        weaknesses=["code_generation", "fast_edits", "structured_output"],
        speed="fast",
        quality="high",
        priority=3,
        default_temperature=0.8,
        context_window=4096,
        aliases=["mistral-small", "mistral"],
    ),
    ModelProfile(
        name="qwen2.5-coder:7b",
        short_name="qwen2.5-coder:7b",
        capabilities=[
            "fast_edits", "small_repairs", "lightweight_coding",
        ],
        strengths=["speed", "fast_edits", "lightweight_tasks"],
        weaknesses=["architecture", "planning", "complex_reasoning"],
        speed="very_fast",
        quality="medium",
        priority=4,
        default_temperature=0.1,
        context_window=4096,
        aliases=["qwen2.5-coder:7b"],
    ),
    ModelProfile(
        name="llama3:latest",
        short_name="llama3",
        capabilities=[
            "documentation", "explanation", "general_chat",
        ],
        strengths=["documentation", "explanation", "conversation"],
        weaknesses=["code_generation", "architecture", "structured_output"],
        speed="fast",
        quality="medium",
        priority=5,
        default_temperature=0.5,
        context_window=4096,
        aliases=["llama3", "llama3:8b"],
    ),
    ModelProfile(
        name="deepseek-coder:latest",
        short_name="deepseek-coder",
        capabilities=[
            "fast_edits", "small_repairs", "lightweight_coding",
        ],
        strengths=["speed", "lightweight_coding", "fast_edits"],
        weaknesses=["planning", "architecture", "ui_design", "complex_reasoning"],
        speed="very_fast",
        quality="medium",
        priority=6,
        default_temperature=0.1,
        context_window=4096,
        aliases=["deepseek-coder", "deepseek"],
    ),
]


def _build_registry():
    _MODEL_REGISTRY.clear()
    for profile in MODEL_PROFILES_DATA:
        _MODEL_REGISTRY[profile.name] = profile
        for alias in profile.aliases:
            if alias not in _MODEL_REGISTRY:
                _MODEL_REGISTRY[alias] = profile


_build_registry()


def get_profile(model_name: str) -> Optional[ModelProfile]:
    return _MODEL_REGISTRY.get(model_name)


def get_profile_by_short_name(short_name: str) -> Optional[ModelProfile]:
    for p in MODEL_PROFILES_DATA:
        if p.short_name == short_name:
            return p
    return None


def register_model(profile: ModelProfile):
    _MODEL_REGISTRY[profile.name] = profile
    for alias in profile.aliases:
        if alias not in _MODEL_REGISTRY:
            _MODEL_REGISTRY[alias] = profile
    existing = [p for p in MODEL_PROFILES_DATA if p.name == profile.name]
    if not existing:
        MODEL_PROFILES_DATA.append(profile)


def all_profiles() -> List[ModelProfile]:
    seen = set()
    result = []
    for p in MODEL_PROFILES_DATA:
        if p.name not in seen:
            seen.add(p.name)
            result.append(p)
    return result


def enabled_profiles() -> List[ModelProfile]:
    return [p for p in all_profiles() if p.enabled]


def find_models_for_capability(cap: str) -> List[ModelProfile]:
    return [p for p in enabled_profiles() if cap in p.capabilities]


def find_models_for_capabilities(required_caps: List[str]) -> List[ModelProfile]:
    if not required_caps:
        return enabled_profiles()
    scored = []
    for p in enabled_profiles():
        matching = sum(1 for c in required_caps if c in p.capabilities)
        if matching > 0:
            scored.append((matching, p))
    scored.sort(key=lambda x: (-x[0], x[1].priority))
    return [p for _, p in scored]


def match_models_for_stage(stage: str, mode: str = "balanced") -> List[ModelProfile]:
    required = STAGE_CAPABILITIES.get(stage, [])
    candidates = find_models_for_capabilities(required)

    if mode == "quality":
        quality_order = {"high": 0, "medium": 1, "low": 2}
        candidates.sort(key=lambda p: (
            -sum(1 for c in required if c in p.capabilities) / max(len(required), 1),
            quality_order.get(p.quality, 2),
        ))
    elif mode == "performance":
        speed_order = {"very_fast": 0, "fast": 1, "medium": 2, "slow": 3}
        candidates.sort(key=lambda p: (
            -sum(1 for c in required if c in p.capabilities) / max(len(required), 1),
            speed_order.get(p.speed, 3),
        ))
    else:
        candidates.sort(key=lambda p: (
            -sum(1 for c in required if c in p.capabilities) / max(len(required), 1),
            p.priority,
        ))

    return candidates


def disable_model(model_name_or_alias: str):
    profile = get_profile(model_name_or_alias)
    if profile:
        profile.enabled = False


def enable_model(model_name_or_alias: str):
    profile = get_profile(model_name_or_alias)
    if profile:
        profile.enabled = True


def reset_profiles():
    _build_registry()
