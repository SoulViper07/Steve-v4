from typing import Dict, List, Optional

CAPABILITY_TAXONOMY: Dict[str, Dict] = {
    "planning": {
        "label": "Planning",
        "description": "Task decomposition, project planning, roadmap creation",
    },
    "reasoning": {
        "label": "Reasoning",
        "description": "Logical reasoning, problem analysis, decision making",
    },
    "architecture": {
        "label": "Architecture",
        "description": "System design, component structure, data flow",
    },
    "task_analysis": {
        "label": "Task Analysis",
        "description": "Understanding requirements, identifying subtasks",
    },
    "project_decomposition": {
        "label": "Project Decomposition",
        "description": "Breaking large projects into manageable pieces",
    },
    "code_generation": {
        "label": "Code Generation",
        "description": "Writing new code from specifications",
    },
    "refactoring": {
        "label": "Refactoring",
        "description": "Improving existing code structure without changing behavior",
    },
    "bug_fixing": {
        "label": "Bug Fixing",
        "description": "Identifying and fixing defects",
    },
    "file_implementation": {
        "label": "File Implementation",
        "description": "Creating complete file implementations",
    },
    "ui_design": {
        "label": "UI Design",
        "description": "User interface layout, styling, component design",
    },
    "ux_design": {
        "label": "UX Design",
        "description": "User experience, interaction design, usability",
    },
    "visual_refinement": {
        "label": "Visual Refinement",
        "description": "Polishing visuals, animations, responsive design",
    },
    "design_language": {
        "label": "Design Language",
        "description": "Design systems, color schemes, typography, brand consistency",
    },
    "documentation": {
        "label": "Documentation",
        "description": "Writing docs, README, API docs, inline comments",
    },
    "explanation": {
        "label": "Explanation",
        "description": "Explaining code, concepts, architecture decisions",
    },
    "general_chat": {
        "label": "General Chat",
        "description": "General conversation, questions, brainstorming",
    },
    "fast_edits": {
        "label": "Fast Edits",
        "description": "Quick, targeted edits with minimal latency",
    },
    "small_repairs": {
        "label": "Small Repairs",
        "description": "Small bug fixes, minor adjustments",
    },
    "lightweight_coding": {
        "label": "Lightweight Coding",
        "description": "Simple coding tasks, scripts, utility functions",
    },
}

STAGE_CAPABILITIES: Dict[str, List[str]] = {
    "plan": ["planning", "reasoning", "architecture"],
    "architecture": ["architecture", "reasoning", "planning"],
    "project_decomposition": ["project_decomposition", "task_analysis"],
    "frontend_creative": ["ui_design", "ux_design", "visual_refinement"],
    "visual_identity": ["design_language", "visual_refinement"],
    "animation_ideas": ["visual_refinement", "ui_design"],
    "implement": ["code_generation", "file_implementation"],
    "code_gen": ["code_generation"],
    "patch": ["bug_fixing", "small_repairs"],
    "repair_strategy": ["reasoning", "bug_fixing"],
    "verifier_analysis": ["reasoning", "task_analysis"],
    "small_edit": ["fast_edits"],
    "fast_fix": ["fast_edits", "small_repairs"],
    "implementing_refactor": ["refactoring", "code_generation"],
    "generating_docs": ["documentation"],
    "chat": ["general_chat", "explanation"],
    "researching": ["explanation", "reasoning"],
    "designing_ui": ["ui_design", "visual_refinement"],
    "designing_architecture": ["architecture", "reasoning"],
    "generating_project": ["code_generation", "file_implementation"],
    "implementing": ["code_generation", "file_implementation"],
    "understanding_request": ["task_analysis", "reasoning"],
    "editing_file": ["fast_edits", "code_generation"],
    "analyzing": ["reasoning", "task_analysis"],
    "analyzing_error": ["reasoning", "bug_fixing"],
    "repairing": ["bug_fixing", "small_repairs"],
    "verifying": ["reasoning", "task_analysis"],
    "final_verification": ["reasoning"],
    "summary": ["explanation", "documentation"],
}

STAGE_ROLES: Dict[str, str] = {
    "plan": "Planner",
    "architecture": "Architect",
    "project_decomposition": "Planner",
    "frontend_creative": "Designer",
    "visual_identity": "Designer",
    "animation_ideas": "Designer",
    "implement": "Engineer",
    "code_gen": "Engineer",
    "patch": "Engineer",
    "structured_repair": "Engineer",
    "repair_strategy": "Strategist",
    "verifier_analysis": "Verifier",
    "small_edit": "Engineer",
    "fast_fix": "Engineer",
    "planning": "Planner",
    "planning_architecture": "Architect",
    "designing_architecture": "Architect",
    "designing_ui": "Designer",
    "generating_project": "Engineer",
    "implementing": "Engineer",
    "implementing_interactions": "Engineer",
    "implementing_refactor": "Engineer",
    "editing_file": "Engineer",
    "generating_docs": "Writer",
    "analyzing": "Analyzer",
    "analyzing_error": "Analyzer",
    "repairing": "Repairer",
    "verifying": "Verifier",
    "final_verification": "Verifier",
    "researching": "Researcher",
    "chat": "Assistant",
    "summary": "Writer",
}

TASK_CATEGORY_CAPABILITIES: Dict[str, List[str]] = {
    "Chat": ["general_chat", "explanation"],
    "Programming": ["task_analysis", "planning", "code_generation", "file_implementation"],
    "Frontend UI": ["task_analysis", "ui_design", "visual_refinement", "code_generation"],
    "Backend": ["task_analysis", "architecture", "code_generation"],
    "Bug Fix": ["task_analysis", "reasoning", "bug_fixing", "small_repairs"],
    "Debugging": ["reasoning", "task_analysis", "bug_fixing"],
    "Refactor": ["task_analysis", "refactoring", "code_generation"],
    "Architecture": ["task_analysis", "architecture", "reasoning"],
    "Documentation": ["documentation", "explanation"],
    "Project Generation": ["task_analysis", "planning", "architecture", "ui_design", "code_generation", "file_implementation"],
    "File Editing": ["task_analysis", "fast_edits", "code_generation"],
    "Research": ["reasoning", "explanation"],
    "Planning": ["planning", "reasoning", "architecture"],
}


def get_capability_label(cap: str) -> str:
    info = CAPABILITY_TAXONOMY.get(cap)
    return info["label"] if info else cap.replace("_", " ").title()


def get_stage_capabilities(stage: str) -> List[str]:
    return STAGE_CAPABILITIES.get(stage, [])


def get_stage_role(stage: str) -> str:
    return STAGE_ROLES.get(stage, "Agent")


def get_category_capabilities(category: str) -> List[str]:
    return TASK_CATEGORY_CAPABILITIES.get(category, [])


def describe_capabilities(caps: List[str]) -> str:
    labels = [get_capability_label(c) for c in caps]
    return ", ".join(labels[:4])
