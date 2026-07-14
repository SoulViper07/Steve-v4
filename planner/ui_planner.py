import json
from typing import Optional

from .execution_plan import UIPlan, TaskClassification
from ._llm import call_qwen


SYSTEM_PROMPT = """You are Steve's UI Planning Agent.
Your ONLY job is to plan the UI/UX design for a software project.

Based on the user's request and task classification, determine:
- Design language (e.g. minimal, glassmorphism, neumorphic, modern, futuristic, playful, corporate)
- Animations needed (e.g. fade-in, slide, parallax, aurora, particle, hover, transition, scroll-triggered)
- Responsiveness requirements (breakpoints, mobile-first approach)
- Accessibility features (e.g. ARIA labels, keyboard nav, contrast, screen-reader, focus indicators)
- Color scheme description (e.g. dark blue primary, white background, accent teal)
- Typography (e.g. sans-serif system font, monospace for code)
- Layout archetype (e.g. sidebar-nav, centered, full-width, dashboard-grid, single-column)

Output ONLY valid JSON with these fields:
{
  "design_language": "...",
  "animations": ["anim1", "anim2"],
  "responsiveness": "description of responsive approach",
  "accessibility_features": ["feature1", "feature2"],
  "color_scheme": "...",
  "typography": "...",
  "layout_archetype": "..."
}

Never include any text outside the JSON block."""


def plan_ui(request: str, classification: TaskClassification) -> Optional[UIPlan]:
    if not classification.frontend and not classification.full_stack:
        return UIPlan()

    try:
        context = f"""
USER REQUEST:
{request}

TASK CLASSIFICATION:
- Project type: {classification.project_type}
- Category: {classification.category}
- Languages: {', '.join(classification.languages)}
- Frameworks: {', '.join(classification.frameworks)}

Plan the UI/UX design for this project.
"""
        raw = call_qwen(context, system=SYSTEM_PROMPT, temperature=0.5)
        cleaned = _extract_json(raw)
        data = json.loads(cleaned)
        return UIPlan(
            design_language=data.get("design_language", "modern"),
            animations=data.get("animations", []),
            responsiveness=data.get("responsiveness", "yes"),
            accessibility_features=data.get("accessibility_features", []),
            color_scheme=data.get("color_scheme", ""),
            typography=data.get("typography", ""),
            layout_archetype=data.get("layout_archetype", ""),
        )
    except Exception:
        return _fallback()


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


def _fallback() -> UIPlan:
    return UIPlan(
        design_language="modern",
        animations=["fade-in"],
        responsiveness="yes",
        accessibility_features=["keyboard navigation"],
        color_scheme="light background, dark text",
        typography="sans-serif",
        layout_archetype="single-column",
    )
