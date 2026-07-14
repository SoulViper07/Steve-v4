import os
import re
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from .models import ExecutionPlan, ProjectManifest, VerificationResult, TurnMetrics, RequestRoute
from .planner import Planner
from .inspector import ProjectInspector
from .model_router import classify_task, get_execution_stages_for_task, _friendly_model_name
from .project_memory import ProjectMemory
from config.model_config import model_for_stage, options_for_stage
from generation.incremental_engine import IncrementalFileBuilder
from generation.identity import _generate_visual_identity, VisualIdentity
from providers.ollama import fetch_response_stream
from verifier.base_verifier import (
    verify_web_project, verify_expected_files,
    verify_backend_project, verify_physical_outputs,
    quality_review, VerificationReport,
)
from actions.executor import FilesystemExecutor
from planner import PlanningEngine
from state import get_state_manager
from ui.terminal_renderer import (
    console, _plain_terminal, _rich_terminal, _clean_mode,
    _info, _ok, _err, _warn, _step, WormLoader, TimedActivity,
    get_pipeline, create_pipeline, clear_pipeline, set_pipeline,
)


def run_pipeline(
    conv,
    user_input: str,
    route: RequestRoute,
    echo: bool = True,
) -> Tuple[str, bool]:
    pipeline = get_pipeline() or create_pipeline()
    start_time = time.monotonic()
    workdir = conv.workdir if hasattr(conv, 'workdir') else Path.cwd()
    memory = ProjectMemory(workdir)
    sm = get_state_manager(workdir)
    sm.clear()

    pipeline.add("🧠", "Understanding request...", "step")

    category = classify_task(user_input)
    pipeline.add("📋", f"Categorizing: {category}", "step")

    sm.initialize_task(user_input, task_id="", category=category)

    # ── Stage 1: High-Level Planning ──
    sm.start_stage("plan")
    planning_engine = PlanningEngine(workdir, state_manager=sm)
    complete_plan = planning_engine.plan(user_input)
    if complete_plan:
        cl = complete_plan.classification
        sm.update_task_classification(
            project_type=cl.project_type,
            complexity=cl.complexity,
            category=cl.category,
            languages=cl.languages,
            frameworks=cl.frameworks,
        )
        pipeline.add("  ✓", f"{cl.project_type} / {cl.complexity} / {cl.category}", "ok")
        if complete_plan.architecture.components:
            sm.update_architecture(
                components=complete_plan.architecture.components,
                folder_structure=complete_plan.architecture.folder_structure,
                summary=complete_plan.architecture.data_flow_summary,
            )
            pipeline.add("  ✓", f"{len(complete_plan.architecture.components)} components, {len(complete_plan.architecture.folder_structure)} files", "ok")
        if complete_plan.features.features:
            pipeline.add("  ✓", f"{len(complete_plan.features.features)} features planned", "ok")
        if complete_plan.execution.steps:
            pipeline.add("  ✓", f"{complete_plan.execution.total_steps} execution steps", "ok")
    sm.finish_stage("plan")

    # ── Stage 2: Detailed Planning ──
    sm.start_stage("detailed_planning")
    pipeline.add("📐", "Detailed breakdown: qwen3:14b", "step")
    planner = Planner(workdir, memory)
    plan_dict, exec_plan = planner.plan(user_input)
    sm.set_project(exec_plan.project_root)
    pipeline.add("  ✓", "Architecture planned", "ok")
    pipeline.add("  ✓", f"Files: {', '.join(exec_plan.required_files[:5])}", "ok")
    sm.finish_stage("detailed_planning")

    files_to_generate = {f: [] for f in exec_plan.required_files}
    components = plan_dict.get("component_breakdown", "")
    if components:
        current_file = ""
        for line in components.split("\n"):
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
                if current_file not in files_to_generate:
                    files_to_generate[current_file] = []
            elif current_file and line.strip():
                parts = re.split(r"[,;]", line)
                for part in parts:
                    part = part.strip().lstrip("-* ")
                    if part and not re.match(r"^(sections?|components?):?\s*", part, re.IGNORECASE):
                        files_to_generate[current_file].append(part)

    # Default fallback sections
    default_sections = {
        "index.html": ["head", "navbar", "hero", "features", "footer"],
        "styles.css": ["variables", "layout", "navbar", "hero", "cards", "animations", "responsive"],
        "script.js": ["navigation", "theme", "storage", "animations", "utilities"],
    }
    for f in files_to_generate:
        if not files_to_generate[f]:
            files_to_generate[f] = default_sections.get(f, ["content"])

    pipeline.add("  ✓", f"{sum(len(v) for v in files_to_generate.values())} components identified", "ok")
    pipeline.add_decision(f"Architecture: {plan_dict.get('architecture', 'N/A')[:80]}")

    # ── Stage 3: Visual Identity / UI Design ──
    sm.start_stage("design")
    project_name = exec_plan.project_root or "project"
    is_frontend = any(f.endswith((".html", ".css", ".js")) for f in exec_plan.required_files)

    if is_frontend:
        pipeline.add("🎨", "Designing UI: mistral-small", "step")
        sm.set_model("mistral-small:latest", stage="design", reason="UI design")
        visual_identity = _generate_visual_identity(user_input, "balanced")
        pipeline.add("  ✓", f"Palette: {list(visual_identity.palette.values())[:4]}", "ok")
        pipeline.add("  ✓", f"Typography: {visual_identity.typography}", "ok")
        pipeline.add("  ✓", f"Layout: {visual_identity.layout_archetype}", "ok")
        pipeline.add("  ✓", f"Animation: {visual_identity.animation_system}", "ok")
        pipeline.add_decision(f"Layout: {visual_identity.layout_archetype}")
        pipeline.add_decision(f"Animation: {visual_identity.animation_system}")

        if memory:
            memory.set_ui_spec({
                "palette": visual_identity.palette,
                "typography": visual_identity.typography,
                "layout": visual_identity.layout_archetype,
                "animations": visual_identity.animation_system,
                "style": visual_identity.ui_style,
                "glass": visual_identity.glass,
                "border_radius": visual_identity.border_radius,
                "shadows": visual_identity.shadows,
            })
            memory.save_all()
    else:
        visual_identity = None
    sm.finish_stage("design")

    # ── Stage 4: Incremental Implementation ──
    sm.start_stage("implement")
    sm.set_model("qwen2.5-coder:14b", stage="implement", reason="Code generation")
    pipeline.add("💻", "Implementing: qwen2.5-coder:14b", "step")
    pipeline.start_progress(sum(len(v) for v in files_to_generate.values()), "Sections")

    design_context = {
        "project_name": project_name,
        "spec": plan_dict.get("ui_spec", plan_dict.get("architecture", "")),
        "design": str(visual_identity.__dict__) if visual_identity else "modern",
    }

    file_builder = IncrementalFileBuilder(workdir, memory)
    section_count = 0
    build_ok = True

    for file_path, sections in files_to_generate.items():
        section_count += len(sections)
        sm.set_file(file_path)
        pipeline.update_progress(section_count, f"Building {file_path}")
        ok = file_builder.build_file(file_path, sections, design_context, pipeline)
        if ok:
            sm.mark_generated(file_path)
        else:
            build_ok = False
            sm.add_warning(f"Partial failure in {file_path}")
            pipeline.add("  ⚠", f"Partial failure in {file_path}", "warn")

    pipeline.stop_progress()

    if build_ok:
        pipeline.add("✅", "All files generated successfully", "ok")
    else:
        pipeline.add("⚠", "Some files had generation issues", "warn")
    sm.finish_stage("implement")

    # ── Stage 5: Verification ──
    sm.start_stage("verify")
    pipeline.add("🔍", "Verifying implementation...", "step")

    file_contents = {}
    for f in exec_plan.required_files:
        path = workdir / f
        if path.exists():
            file_contents[f] = path.read_text(encoding="utf-8", errors="replace")

    ver_report = VerificationReport(passed=True)
    existence = verify_expected_files(workdir, exec_plan.required_files)
    if existence.critical_count > 0:
        ver_report = existence
        sm.update_verification(critical=existence.critical_count, issues=[{"severity": i.severity, "category": i.category, "message": i.message} for i in existence.issues])
        for iss in existence.issues:
            pipeline.verify("Structure", iss.severity, iss.message)

    if is_frontend and ver_report.passed:
        web = verify_web_project(workdir, file_contents, user_input)
        for iss in web.issues:
            severity = "ok" if iss.severity in ("cosmetic",) else ("warn" if iss.severity in ("minor",) else "err")
            pipeline.verify(f"[{iss.severity}] {iss.category}", severity, iss.message)
        ver_report = web

    if ver_report.passed:
        sm.mark_verified("passed", 1.0)
        pipeline.add("  ✅", "Verification passed", "ok")
    elif ver_report.critical_count > 0:
        sm.mark_verified("failed")
        pipeline.add("  ❌", f"{ver_report.critical_count} critical issues found", "err")
    else:
        sm.mark_verified("partial")
        pipeline.add("  ⚠", f"Non-critical issues: {ver_report.major_count} major, {ver_report.minor_count} minor", "warn")

    if memory:
        memory.set_verification({
            "passed": ver_report.passed,
            "critical": ver_report.critical_count,
            "major": ver_report.major_count,
            "minor": ver_report.minor_count,
            "issues": [(i.severity, i.category, i.message) for i in ver_report.issues],
        })
        memory.save_all()
    sm.finish_stage("verify")

    # ── Stage 6: Quality Review ──
    sm.start_stage("quality")
    if is_frontend:
        pipeline.add("⭐", "Performing quality review...", "step")
        qr = quality_review(workdir, file_contents)
        sm.update_verification(quality=qr.score)
        pipeline.add(f"  📊", f"Quality score: {qr.score:.2f}", "info")
        for iss in qr.issues:
            level = "ok" if iss.severity == "cosmetic" else ("warn" if iss.severity == "minor" else "err")
            pipeline.verify(f"[{iss.severity}] {iss.category}", level, iss.message)

        if qr.score < 0.5 and qr.critical_count == 0:
            sm.mark_repaired(attempt=1, success=False)
            pipeline.add("🔄", f"Quality below threshold ({qr.score:.2f}), performing refinement pass...", "warn")
            pipeline.start_progress(3, "Refinement")

            refinement_targets = []
            if qr.score < 0.5:
                if file_contents.get("styles.css", "") and len(file_contents["styles.css"]) < 300:
                    refinement_targets.append(("styles.css", ["animations", "responsive"]))
                if file_contents.get("script.js", "") and len(file_contents["script.js"]) < 200:
                    refinement_targets.append(("script.js", ["animations", "utilities"]))

            for idx, (rf, rs) in enumerate(refinement_targets):
                pipeline.update_progress(idx + 1, f"Refining {rf}")
                file_builder.build_file(rf, rs, design_context, pipeline)

            pipeline.stop_progress()
            sm.mark_repaired(attempt=1, success=True)
            pipeline.add("✅", "Refinement complete", "ok")

    sm.finish_stage("quality")

    # ── Stage 7: Completion ──
    sm.finish_task()
    elapsed = time.monotonic() - start_time
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)
    time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

    pipeline.add("🎉", f"Project completed in {time_str}", "ok")

    if echo and not _clean_mode():
        pipeline.render_timeline()
        pipeline.render_report()

    summary = f"Project '{project_name}' completed in {time_str}. "
    if ver_report.passed:
        summary += "Verification passed."
    else:
        summary += f"{ver_report.critical_count} critical, {ver_report.major_count} major issues."

    return summary, ver_report.passed


def execute_stage_sequence(conv, route, user_input, category, stages):
    return run_pipeline(conv, user_input, route)


def display_execution_stages(category, stages):
    pass
