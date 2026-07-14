import os
import json
from pathlib import Path

_ROUTING_CONFIG_PATH = Path(__file__).parent / "routing.json"

def _load_routing_config():
    try:
        if _ROUTING_CONFIG_PATH.exists():
            with open(_ROUTING_CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

_routing = _load_routing_config()

_model_map = {
    "default_model": os.environ.get("STEVE_ORCHESTRATOR_MODEL", _routing.get("default_model", "qwen3:14b")),
    "creative_model": os.environ.get("STEVE_CREATIVE_MODEL", _routing.get("creative_model", "mistral-small:latest")),
    "coding_model": os.environ.get("STEVE_CODER_MODEL", _routing.get("coding_model", "qwen2.5-coder:14b")),
    "repair_model": os.environ.get("STEVE_REPAIR_MODEL", _routing.get("repair_model", "qwen2.5-coder:14b")),
    "fast_model": os.environ.get("STEVE_FAST_MODEL", _routing.get("fast_model", "qwen2.5-coder:7b")),
}

def get_routing_config():
    return _routing

def get_model_map():
    return dict(_model_map)

def resolve_model(stage_or_key: str) -> str:
    stage_map = _routing.get("stage_model_map", {})
    key = stage_map.get(stage_or_key, "default_model")
    return _model_map.get(key, _model_map["default_model"])

MODEL_ROLES = {
    "orchestrator": {
        "model": _model_map["default_model"],
        "label": "Orchestrator",
        "tasks": ["plan", "architecture", "verifier_analysis", "repair_strategy"],
        "temperature": float(os.environ.get("STEVE_ORCHESTRATOR_TEMPERATURE", "0.3")),
        "num_ctx": int(os.environ.get("STEVE_ORCHESTRATOR_NUM_CTX", "8192")),
        "num_predict": int(os.environ.get("STEVE_ORCHESTRATOR_NUM_PREDICT", "1200")),
        "repeat_penalty": float(os.environ.get("STEVE_ORCHESTRATOR_REPEAT_PENALTY", "1.08")),
        "top_p": float(os.environ.get("STEVE_ORCHESTRATOR_TOP_P", "0.9")),
        "top_k": int(os.environ.get("STEVE_ORCHESTRATOR_TOP_K", "40")),
    },
    "creative": {
        "model": _model_map["creative_model"],
        "label": "Creative",
        "tasks": ["frontend_ideation", "ui_concept", "visual_identity", "animation_style", "layout_diversity"],
        "temperature": float(os.environ.get("STEVE_CREATIVE_TEMPERATURE", "0.8")),
        "num_ctx": int(os.environ.get("STEVE_CREATIVE_NUM_CTX", "4096")),
        "num_predict": int(os.environ.get("STEVE_CREATIVE_NUM_PREDICT", "800")),
        "repeat_penalty": float(os.environ.get("STEVE_CREATIVE_REPEAT_PENALTY", "1.05")),
        "top_p": float(os.environ.get("STEVE_CREATIVE_TOP_P", "0.95")),
        "top_k": int(os.environ.get("STEVE_CREATIVE_TOP_K", "60")),
    },
    "coder": {
        "model": _model_map["coding_model"],
        "label": "Coder",
        "tasks": ["implement", "code_gen", "patch", "execute", "structured_repair"],
        "temperature": float(os.environ.get("STEVE_CODER_TEMPERATURE", "0.15")),
        "num_ctx": int(os.environ.get("STEVE_CODER_NUM_CTX", "8192")),
        "num_predict": int(os.environ.get("STEVE_CODER_NUM_PREDICT", "1600")),
        "repeat_penalty": float(os.environ.get("STEVE_CODER_REPEAT_PENALTY", "1.08")),
        "top_p": float(os.environ.get("STEVE_CODER_TOP_P", "0.9")),
        "top_k": int(os.environ.get("STEVE_CODER_TOP_K", "40")),
    },
    "fast": {
        "model": _model_map["fast_model"],
        "label": "Fast",
        "tasks": ["small_edit", "fast_fix", "trivial_change"],
        "temperature": float(os.environ.get("STEVE_FAST_TEMPERATURE", "0.1")),
        "num_ctx": int(os.environ.get("STEVE_FAST_NUM_CTX", "4096")),
        "num_predict": int(os.environ.get("STEVE_FAST_NUM_PREDICT", "800")),
        "repeat_penalty": float(os.environ.get("STEVE_FAST_REPEAT_PENALTY", "1.08")),
        "top_p": float(os.environ.get("STEVE_FAST_TOP_P", "0.9")),
        "top_k": int(os.environ.get("STEVE_FAST_TOP_K", "40")),
    },
}

ROLE_ALIASES = {
    "plan": "orchestrator",
    "architecture": "orchestrator",
    "project_decomposition": "orchestrator",
    "architecture_reasoning": "orchestrator",
    "verifier_analysis": "orchestrator",
    "repair_strategy": "orchestrator",
    "frontend_creative": "creative",
    "ui_concept": "creative",
    "visual_identity": "creative",
    "animation_ideas": "creative",
    "animation_style": "creative",
    "layout_diversity": "creative",
    "implement": "coder",
    "code_gen": "coder",
    "patch": "coder",
    "execute": "coder",
    "structured_repair": "coder",
    "small_edit": "fast",
    "fast_fix": "fast",
}

DEFAULT_FALLBACK_MODEL = os.environ.get("STEVE_FALLBACK_MODEL", "qwen2.5-coder:14b")

FALLBACK_CHAIN = [
    "qwen2.5-coder:14b",
    "qwen2.5-coder:7b",
    "deepseek-coder",
    "codellama",
]

AUTO_WARM_SEQUENTIAL = os.environ.get("STEVE_AUTO_WARM", "true").lower() in {"1", "true", "yes", "on"}

def stage_to_role(stage: str) -> str:
    return ROLE_ALIASES.get(stage, "coder")

def role_config(role: str) -> dict:
    return dict(MODEL_ROLES.get(role, MODEL_ROLES["coder"]))

def model_for_stage(stage: str) -> str:
    role_name = stage_to_role(stage)
    return role_config(role_name)["model"]

def options_for_stage(stage: str) -> dict:
    role_name = stage_to_role(stage)
    cfg = role_config(role_name)
    return {
        "temperature": cfg["temperature"],
        "num_ctx": cfg["num_ctx"],
        "num_predict": cfg["num_predict"],
        "repeat_penalty": cfg["repeat_penalty"],
        "top_p": cfg["top_p"],
        "top_k": cfg["top_k"],
    }

def all_configured_models() -> list[str]:
    seen = set()
    models = []
    for role, cfg in MODEL_ROLES.items():
        m = cfg["model"]
        if m not in seen:
            seen.add(m)
            models.append(m)
    return models
