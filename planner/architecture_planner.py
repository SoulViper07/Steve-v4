import json
from typing import Optional

from .execution_plan import ArchitecturePlan, TaskClassification
from ._llm import call_qwen


SYSTEM_PROMPT = """You are Steve's Architecture Planning Agent.
Your ONLY job is to design the architecture for a software project.

Based on the user's request and task classification, determine:
- Folder structure (list of all directories and files to create)
- Components (named UI or logical components needed)
- Pages (if applicable, list of pages/routes)
- API endpoints (if backend, list of endpoints with method and path)
- Database tables (if database needed, list of tables with columns)
- Data flow summary (1-2 sentences)

Output ONLY valid JSON with these fields:
{
  "folder_structure": ["dir/file", "dir/subdir/file2", ...],
  "components": ["Component1", "Component2", ...],
  "pages": ["page1", "page2", ...],
  "api_endpoints": [{"method": "GET", "path": "/api/resource", "description": "..."}],
  "database_tables": [{"name": "table_name", "columns": "col1, col2, col3"}],
  "data_flow_summary": "1-2 sentence summary"
}

Never include any text outside the JSON block."""


def plan_architecture(request: str, classification: TaskClassification) -> Optional[ArchitecturePlan]:
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
- Full stack: {classification.full_stack}
- Languages: {', '.join(classification.languages)}
- Frameworks: {', '.join(classification.frameworks)}

Design the architecture for this project.
"""
        raw = call_qwen(context, system=SYSTEM_PROMPT, temperature=0.35)
        cleaned = _extract_json(raw)
        data = json.loads(cleaned)
        return ArchitecturePlan(
            folder_structure=data.get("folder_structure", []),
            components=data.get("components", []),
            pages=data.get("pages", []),
            api_endpoints=data.get("api_endpoints", []),
            database_tables=data.get("database_tables", []),
            data_flow_summary=data.get("data_flow_summary", ""),
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


def _fallback(request: str) -> ArchitecturePlan:
    lowered = request.lower()
    is_frontend = any(t in lowered for t in ("html", "css", "javascript", "frontend", "landing", "website", "web"))
    if is_frontend:
        return ArchitecturePlan(
            folder_structure=["index.html", "styles.css", "script.js"],
            components=["Navbar", "Hero", "Features", "Footer"],
            pages=["index"],
            data_flow_summary="Single-page frontend application",
        )
    return ArchitecturePlan(
        folder_structure=[],
        components=[],
        data_flow_summary="Project architecture",
    )
