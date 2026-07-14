import json
import os
import re
import time
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field

from config.model_config import model_for_stage
from providers.ollama import fetch_response_stream
from .models import ExecutionPlan, ProjectManifest, RequestRoute
from .inspector import ProjectInspector
from .project_memory import ProjectMemory


PLANNER_PROMPT = """You are Steve's Planning Agent. Your job is to produce a complete, structured plan before any code is written.

Analyze the user's request and produce:

1. **Project Overview**: 1-2 sentence summary of what we're building.

2. **Architecture**: Detailed architecture description covering:
   - Frontend structure (HTML/CSS/JS organization)
   - Component tree (every UI component needed)
   - Layout approach (responsive grid, flexbox, CSS Grid)
   - State management (DOM-based, localStorage, etc.)

3. **UI Specification**:
   - Design language (glassmorphism, minimal, neumorphic, etc.)
   - Color approach (describe the palette intention)
   - Typography choices
   - Layout archetype
   - Animation style
   - Responsive breakpoints

4. **File Tree**: Complete list of files to create, organized like:
```
project-name/
├── index.html
├── styles.css
└── script.js
```

5. **Implementation Roadmap**: Step-by-step implementation plan:
   - Step 1: HTML structure (sections: head, navbar, hero, features, footer)
   - Step 2: CSS (variables, reset, layout, components, animations, responsive)
   - Step 3: JavaScript (state, DOM references, event handlers, utilities)

6. **Component Breakdown**: For each file, list the sections to generate individually:
   HTML sections: head, navbar, hero, features, pricing, FAQ, footer
   CSS sections: variables, reset, layout, navbar, hero, cards, animations, responsive
   JS sections: navigation, theme, storage, animations, utilities

7. **Quality Targets**:
   - HTML: minimum {html_lines} lines of meaningful content
   - CSS: minimum {css_lines} lines with custom properties, responsive design, animations
   - JS: minimum {js_lines} lines with state management, event handling, localStorage

8. **Feature Checklist**:
   - [ ] Feature 1
   - [ ] Feature 2
   - ...

Respond with a structured plan. Use markdown headers and bullet points.
"""


def build_plan_prompt(request: str, profile: str = "premium") -> str:
    targets = {
        "quick": (80, 100, 80),
        "standard": (150, 250, 150),
        "premium": (250, 500, 300),
        "cinematic": (400, 1000, 600),
    }
    html_lines, css_lines, js_lines = targets.get(profile, targets["premium"])
    return PLANNER_PROMPT.format(html_lines=html_lines, css_lines=css_lines, js_lines=js_lines) + f"\n\nUser request:\n{request}"


def parse_plan_from_response(response: str) -> Dict:
    plan = {
        "overview": "",
        "architecture": "",
        "ui_spec": "",
        "file_tree": "",
        "implementation_roadmap": "",
        "component_breakdown": "",
        "quality_targets": "",
        "feature_checklist": [],
    }

    sections = {
        "overview": r"(?:Project\s+Overview|Overview)",
        "architecture": r"(?:Architecture|Architectural)",
        "ui_spec": r"(?:UI\s+Specification|UI\s+Spec|Design)",
        "file_tree": r"(?:File\s+Tree|Directory\s+Structure|file\s+tree)",
        "implementation_roadmap": r"(?:Implementation\s+Roadmap|Roadmap|Implementation\s+Plan)",
        "component_breakdown": r"(?:Component\s+Breakdown|Section\s+Breakdown)",
        "quality_targets": r"(?:Quality\s+Targets|Quality)",
        "feature_checklist": r"(?:Feature\s+Checklist|Checklist|Features)",
    }

    current_section = None
    lines = response.split("\n")
    for line in lines:
        lower = line.strip().lower()
        matched = False
        for key, pattern in sections.items():
            if re.search(pattern, lower, re.IGNORECASE):
                current_section = key
                matched = True
                break
        if not matched and current_section and line.strip():
            if current_section == "feature_checklist":
                if re.match(r"^\s*[\-\*]\s*\[[\sx]\]", line):
                    plan["feature_checklist"].append(line.strip())
                elif re.match(r"^\s*[\-\*]\s", line):
                    plan["feature_checklist"].append(line.strip())
            else:
                existing = plan[current_section]
                if existing:
                    plan[current_section] = existing + "\n" + line
                else:
                    plan[current_section] = line

    return plan


def extract_files_from_plan(plan: Dict) -> List[str]:
    files = []
    ft = plan.get("file_tree", "")
    if ft:
        for line in ft.split("\n"):
            m = re.search(r"[\w./\\-]+\.[A-Za-z0-9]{1,8}", line)
            if m:
                files.append(m.group(0).replace("\\", "/"))
    if not files:
        files = ["index.html", "styles.css", "script.js"]
    return files


def extract_components(plan: Dict) -> Dict[str, List[str]]:
    components = {}
    cb = plan.get("component_breakdown", "")
    if cb:
        current_file = ""
        for line in cb.split("\n"):
            m = re.match(r"\s*(HTML|CSS|JS|javascript|styles?)\s*(?:sections?|components?)?:?\s*", line, re.IGNORECASE)
            if m:
                key = m.group(1).lower()
                if key == "html":
                    current_file = "index.html"
                elif key in ("css", "styles"):
                    current_file = "styles.css"
                elif key in ("js", "javascript"):
                    current_file = "script.js"
                else:
                    current_file = ""
                components[current_file] = []
            elif current_file and line.strip():
                parts = re.split(r"[,;]", line)
                for part in parts:
                    part = part.strip().lstrip("-* ")
                    if part and not re.match(r"^(sections?|components?):?\s*", part, re.IGNORECASE):
                        components[current_file].append(part)
    return components


def auto_detect_components(request: str) -> Dict[str, List[str]]:
    lowered = request.lower()
    is_simple = len(request) < 80
    if is_simple:
        return {
            "index.html": ["head", "navbar", "hero", "features", "footer"],
            "styles.css": ["variables", "reset", "layout", "navbar", "hero", "cards", "responsive"],
            "script.js": ["navigation", "theme", "animations", "storage"],
        }
    has_many_sections = any(t in lowered for t in ("landing", "site", "page", "dashboard"))
    if has_many_sections:
        return {
            "index.html": ["head", "navbar", "hero", "features", "pricing", "FAQ", "testimonials", "contact", "footer"],
            "styles.css": ["variables", "reset", "layout", "navbar", "hero", "cards", "sections", "animations", "responsive", "utilities"],
            "script.js": ["navigation", "theme", "storage", "animations", "scroll", "intersection_observer", "utilities"],
        }
    return {
        "index.html": ["head", "navbar", "hero", "features", "footer"],
        "styles.css": ["variables", "reset", "layout", "navbar", "hero", "cards", "animations", "responsive"],
        "script.js": ["navigation", "theme", "storage", "animations", "utilities"],
    }


class Planner:
    def __init__(self, workdir: Path, memory: Optional[ProjectMemory] = None):
        self.workdir = workdir
        self.memory = memory

    def plan(self, request: str, project_map=None) -> Tuple[Dict, ExecutionPlan]:
        profile = self._detect_quality(request)
        prompt = build_plan_prompt(request, profile)

        planner_model = model_for_stage("plan")
        messages = [{"role": "user", "content": prompt}]

        response = ""
        try:
            route = RequestRoute(
                intent="plan",
                actionable=False,
                requires_inspection=False,
                requires_plan=False,
                requires_verification=False,
                short_path=True,
                reason="planning",
            )
            for token in fetch_response_stream(planner_model, messages, route):
                response += token
        except Exception as e:
            response = self._fallback_plan(request, profile)

        plan = parse_plan_from_response(response)
        files = extract_files_from_plan(plan)
        components = extract_components(plan) or auto_detect_components(request)

        if self.memory:
            self.memory.set_plan(response)
            self.memory.set_architecture({"architecture": plan.get("architecture", ""), "file_tree": plan.get("file_tree", "")})
            self.memory.set_ui_spec({"ui_spec": plan.get("ui_spec", ""), "components": components})
            self.memory.set_todo({f"{f}>{s}": {"done": False} for f, secs in components.items() for s in secs})
            self.memory.set_progress({"stage": "planning", "pct": 0})
            self.memory.save_all()

        project_root = self._infer_project_root(request)
        exec_plan = ExecutionPlan(
            request=request,
            relevant_files=files,
            change_summary=[plan.get("overview", ""), plan.get("architecture", "")[:200]],
            risks=[],
            verify_steps=["Validate file existence", "Validate content quality", "Validate functionality"],
            project_root=project_root,
            quality_profile=profile,
            required_files=files,
            manifest=ProjectManifest(
                project_root=project_root,
                required_files=files,
            ),
        )

        return plan, exec_plan

    def _detect_quality(self, request: str) -> str:
        lowered = request.lower()
        if "cinematic" in lowered:
            return "cinematic"
        if any(t in lowered for t in ("premium", "professional", "production-ready", "modern ui", "enterprise")):
            return "premium"
        if any(t in lowered for t in ("quick", "simple", "basic", "minimal")):
            return "quick"
        return "standard"

    def _infer_project_root(self, request: str) -> str:
        m = re.search(r"(?:called|named)\s+[`'\"]?([A-Za-z][\w-]+)[`'\"]?", request)
        if m:
            return m.group(1).lower().replace(" ", "-")
        m = re.search(r"(?:project|app|site)\s+[`'\"]?([A-Za-z][\w-]+)[`'\"]?", request, re.IGNORECASE)
        if m:
            return m.group(1).lower().replace(" ", "-")
        first_word = request.strip().split()[0] if request.strip() else "project"
        return first_word.lower().replace(" ", "-")

    def _fallback_plan(self, request: str, profile: str) -> str:
        return f"""# Project Plan

## Overview
{request}

## Architecture
Frontend web application with HTML, CSS, and JavaScript.

## UI Specification
Modern, responsive design with a clean layout.

## File Tree
```
index.html
styles.css
script.js
```

## Implementation Roadmap
1. HTML structure
2. CSS styling
3. JavaScript functionality

## Component Breakdown
HTML: head, navbar, hero, features, footer
CSS: variables, reset, layout, navbar, hero, cards, responsive
JS: navigation, theme, storage, animations

## Quality Targets
Premium quality with responsive design and animations.

## Feature Checklist
- [ ] Responsive layout
- [ ] Modern UI
- [ ] Interactive features
"""
