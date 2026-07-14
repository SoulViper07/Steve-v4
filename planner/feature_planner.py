import json
from typing import Optional

from .execution_plan import FeaturePlan, TaskClassification
from ._llm import call_qwen


SYSTEM_PROMPT = """You are Steve's Feature and Verification Planning Agent.
Your ONLY job is to plan the features, dependencies, verification strategy, and model recommendations for a software project.

Based on the user's request and task classification, determine:
- Features: list of features with name and description
- Verification strategy: ordered steps to verify the project works
- Dependencies: external libraries, packages, or services needed
- Completion criteria: checklist of what must be true for the project to be complete
- Model recommendations: which AI model to use for each role:
  planner -> always "qwen3:14b"
  designer -> creative model suggestion
  engineer -> coding model suggestion

Output ONLY valid JSON with these fields:
{
  "features": [{"name": "FeatureName", "description": "What it does"}],
  "verification_strategy": ["step1", "step2"],
  "dependencies": ["dep1", "dep2"],
  "completion_criteria": ["criteria1", "criteria2"],
  "model_recommendations": {
    "planner": "qwen3:14b",
    "designer": "mistral-small:latest",
    "engineer": "qwen2.5-coder:14b"
  }
}

Never include any text outside the JSON block."""


def plan_features(request: str, classification: TaskClassification) -> Optional[FeaturePlan]:
    try:
        context = f"""
USER REQUEST:
{request}

TASK CLASSIFICATION:
- Project type: {classification.project_type}
- Complexity: {classification.complexity}
- Category: {classification.category}
- Frontend: {classification.frontend}
- Backend: {classification.backend}
- Languages: {', '.join(classification.languages)}
- Frameworks: {', '.join(classification.frameworks)}

Plan the features and verification approach.
"""
        raw = call_qwen(context, system=SYSTEM_PROMPT, temperature=0.35)
        cleaned = _extract_json(raw)
        data = json.loads(cleaned)
        return FeaturePlan(
            features=data.get("features", []),
            verification_strategy=data.get("verification_strategy", []),
            dependencies=data.get("dependencies", []),
            completion_criteria=data.get("completion_criteria", []),
            model_recommendations=data.get("model_recommendations", {
                "planner": "qwen3:14b",
                "designer": "mistral-small:latest",
                "engineer": "qwen2.5-coder:14b",
            }),
        )
    except Exception:
        return _fallback(request, classification)


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        for line in text.split("\n"):
            if line.startswith("```"):
                text = "\n".join(text.split("\n")[1:])
                break
        if text.endswith("```"):
            text = text[:-3].strip()
        elif "```" in text:
            text = text.split("```")[0].strip()
        return _extract_json(text)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _fallback(request: str, classification: TaskClassification) -> FeaturePlan:
    is_frontend = classification.frontend or classification.full_stack
    if is_frontend:
        return FeaturePlan(
            features=[{"name": "Core UI", "description": "Main user interface"}],
            verification_strategy=[
                "Verify all files exist",
                "Verify HTML structure validity",
                "Verify CSS styling",
                "Verify JavaScript functionality",
            ],
            dependencies=[],
            completion_criteria=[
                "All required files created",
                "UI renders correctly",
                "Interactive features work",
            ],
            model_recommendations={
                "planner": "qwen3:14b",
                "designer": "mistral-small:latest",
                "engineer": "qwen2.5-coder:14b",
            },
        )
    return FeaturePlan(
        features=[{"name": "Core", "description": "Core implementation"}],
        verification_strategy=["Verify all files exist", "Verify functionality"],
        dependencies=[],
        completion_criteria=["All required files created", "Functionality verified"],
        model_recommendations={
            "planner": "qwen3:14b",
            "designer": "mistral-small:latest",
            "engineer": "qwen2.5-coder:14b",
        },
    )
