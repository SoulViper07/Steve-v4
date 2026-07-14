from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

@dataclass
class RequestRoute:
    mode: str
    actionable: bool
    project_scoped: bool
    file_specific: bool
    help_requested: bool
    plan_requested: bool
    inspect_requested: bool

@dataclass
class ProjectMap:
    root: str
    project_types: List[str] = field(default_factory=list)
    important_files: List[str] = field(default_factory=list)
    ui_files: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    build_files: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    viewmodel_files: List[str] = field(default_factory=list)
    voice_files: List[str] = field(default_factory=list)
    animation_files: List[str] = field(default_factory=list)
    theme_files: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    file_count: int = 0

    def to_block(self) -> str:
        lines = [
            f"Project root: {self.root}",
            f"Project types: {', '.join(self.project_types) if self.project_types else 'unknown'}",
            f"Scanned files: {self.file_count}",
        ]
        sections = [
            ("Important files", self.important_files),
            ("Entry points", self.entry_points),
            ("Build/config", self.build_files + [p for p in self.config_files if p not in self.build_files]),
            ("UI files", self.ui_files),
            ("Theme files", self.theme_files),
            ("ViewModels", self.viewmodel_files),
            ("Voice/STT/TTS", self.voice_files),
            ("Simulation/animation", self.animation_files),
            ("Notes", self.notes),
        ]
        for title, items in sections:
            if items:
                lines.append(f"{title}:")
                unique = sorted(dict.fromkeys(items))
                for item in unique[:12]:
                    lines.append(f"  - {item}")
                if len(unique) > 12:
                    lines.append(f"  - ... ({len(unique) - 12} more)")
        return "\n".join(lines)

@dataclass
class VisualIdentity:
    palette: Dict[str, str]
    typography: str
    ui_style: str
    border_radius: str
    shadows: str
    animation_style: str
    mode: str = "balanced"
    glass: bool = False
    layout_archetype: str = "sidebar-nav"
    section_order: List[str] = field(default_factory=list)
    component_variety: List[str] = field(default_factory=list)
    animation_system: str = "fade"

@dataclass
class ProjectManifest:
    project_root: str = ""
    frontend_root: str = ""
    backend_root: str = ""
    required_files: List[str] = field(default_factory=list)
    verifier_targets: List[str] = field(default_factory=list)
    visual_identity: Optional[VisualIdentity] = None

    def required_rel_to_workdir(self, workdir: Path) -> List[str]:
        root = Path(workdir).resolve()
        out = []
        for item in self.required_files:
            path = Path(item).resolve()
            try:
                out.append(path.relative_to(root).as_posix())
            except ValueError:
                out.append(path.as_posix())
        return out

    def required_rel_to_project(self) -> List[str]:
        if not self.project_root:
            return []
        root = Path(self.project_root).resolve()
        out = []
        for item in self.required_files:
            path = Path(item).resolve()
            try:
                out.append(path.relative_to(root).as_posix())
            except ValueError:
                out.append(path.as_posix())
        return out

@dataclass
class ExecutionPlan:
    request: str
    relevant_files: List[str]
    change_summary: List[str]
    risks: List[str]
    verify_steps: List[str]
    allowed_create_paths: List[str] = field(default_factory=list)
    project_root: str = ""
    quality_profile: str = "premium"
    creation_mode: str = "balanced"
    required_files: List[str] = field(default_factory=list)
    verification_criteria: List[str] = field(default_factory=list)
    manifest: Optional[ProjectManifest] = None

    def to_block(self) -> str:
        parts = [f"Request: {self.request}"]
        if self.project_root:
            parts.append(f"Target project root: {self.project_root}")
        parts.append(f"Quality profile: {self.quality_profile}")
        if self.relevant_files:
            parts.append("Relevant files:")
            parts.extend(f"- {path}" for path in self.relevant_files[:12])
        if self.required_files:
            parts.append("Required files:")
            parts.extend(f"- {path}" for path in self.required_files[:12])
        if self.change_summary:
            parts.append("Planned changes:")
            parts.extend(f"- {item}" for item in self.change_summary[:8])
        if self.risks:
            parts.append("Risks:")
            parts.extend(f"- {item}" for item in self.risks[:6])
        if self.verify_steps:
            parts.append("Verification:")
            parts.extend(f"- {item}" for item in self.verify_steps[:6])
        if self.verification_criteria:
            parts.append("Quality gates:")
            parts.extend(f"- {item}" for item in self.verification_criteria[:8])
        return "\n".join(parts)

@dataclass
class VerificationResult:
    ok: bool
    score: float = 0.0
    summary: str = ""
    errors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    attempted: bool = False

@dataclass
class TaskState:
    step: int = 0
    max_steps: int = 10
    history: List[str] = field(default_factory=list)
    completed: bool = False
    failed: bool = False
    last_error: str = ""

@dataclass
class TurnMetrics:
    route: str = "unknown"
    tokens_in: int = 0
    tokens_out: int = 0
    duration: float = 0.0
    tps: float = 0.0
    latency_first_token: Optional[float] = None
    latency_warm: Optional[float] = None
    total_duration: float = 0.0

def __getattr__(name: str) -> Any:
    if name == "Conversation":
        from core.conversation import Conversation
        return Conversation
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
