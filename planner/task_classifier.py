import json
from typing import Optional

from .execution_plan import TaskClassification
from ._llm import call_qwen

SYSTEM_PROMPT = """You are Steve's Task Classification Agent.
Your ONLY job is to classify a user's software request.

Analyze:
- Project type (frontend, backend, full-stack, script, library, api, cli-tool, mobile, desktop, data-pipeline, automation, other)
- Complexity (simple, low, medium, high, critical)
- Category (e.g. landing-page, web-app, dashboard, rest-api, cli-tool, game, data-pipeline, library, automation-script)
- Whether it involves frontend, backend, or both
- Required programming languages
- Required frameworks
- 1-2 sentence description

Output ONLY valid JSON with these fields:
{
  "project_type": "...",
  "complexity": "...",
  "category": "...",
  "frontend": true/false,
  "backend": true/false,
  "full_stack": true/false,
  "languages": ["lang1", "lang2"],
  "frameworks": ["fw1", "fw2"],
  "description": "..."
}

Never include any text outside the JSON block."""


def classify(request: str) -> Optional[TaskClassification]:
    try:
        raw = call_qwen(request, system=SYSTEM_PROMPT)
        cleaned = _extract_json(raw)
        data = json.loads(cleaned)
        return TaskClassification(
            project_type=data.get("project_type", ""),
            complexity=data.get("complexity", "medium"),
            category=data.get("category", ""),
            frontend=data.get("frontend", False),
            backend=data.get("backend", False),
            full_stack=data.get("full_stack", False),
            languages=data.get("languages", []),
            frameworks=data.get("frameworks", []),
            description=data.get("description", ""),
        )
    except Exception:
        return _fallback(request)


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


def _fallback(request: str) -> TaskClassification:
    lowered = request.lower()
    is_frontend = any(t in lowered for t in ("html", "css", "javascript", "frontend", "ui", "landing", "website", "web app"))
    is_backend = any(t in lowered for t in ("api", "backend", "server", "flask", "fastapi", "database"))
    return TaskClassification(
        project_type="full-stack" if is_frontend and is_backend else ("frontend" if is_frontend else "backend" if is_backend else "other"),
        complexity="medium",
        category="web-app" if is_frontend else "api",
        frontend=is_frontend,
        backend=is_backend,
        full_stack=is_frontend and is_backend,
        languages=["html", "css", "javascript"] if is_frontend else ["python"] if is_backend else [],
        frameworks=[],
        description=request[:200],
    )
