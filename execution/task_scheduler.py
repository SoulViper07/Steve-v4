from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class AtomicStage:
    name: str
    stage_type: str
    description: str = ""
    file_path: str = ""
    model: str = ""
    dependencies: List[str] = field(default_factory=list)
    estimated_calls: int = 1
    context: dict = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 2


STAGE_TYPE_MAP = {
    "folder": "folder",
    "html": "file_gen",
    "css": "file_gen",
    "js": "file_gen",
    "python": "file_gen",
    "verify": "verify",
    "repair": "repair",
    "finalize": "finalize",
}

STAGE_DESCRIPTIONS = {
    "folder": "Create project folder structure",
    "html": "Generate HTML markup",
    "css": "Generate CSS styles",
    "js": "Generate JavaScript",
    "python": "Generate Python code",
    "verify": "Verify generated files",
    "repair": "Repair verification failures",
    "finalize": "Finalize and commit",
}


def _infer_stage_type(name: str) -> str:
    lowered = name.lower()
    if lowered in ("folder", "folders", "directory", "directories", "mkdir"):
        return "folder"
    if lowered in ("html", "index.html", "index"):
        return "html"
    if lowered in ("css", "styles.css", "style.css", "styles"):
        return "css"
    if lowered in ("js", "javascript", "script.js", "script"):
        return "js"
    if lowered in ("py", "python", "app.py", "main.py"):
        return "python"
    if lowered in ("verify", "verification", "validate", "check"):
        return "verify"
    if lowered in ("repair", "fix", "recover"):
        return "repair"
    if lowered in ("finalize", "commit", "finish", "done"):
        return "finalize"
    return "file_gen"


FILE_TO_STAGE_TYPE = {
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".js": "js",
    ".py": "python",
    ".json": "file_gen",
    ".md": "file_gen",
    ".yml": "file_gen",
    ".yaml": "file_gen",
    ".toml": "file_gen",
    ".env": "file_gen",
    ".gitignore": "file_gen",
    ".txt": "file_gen",
}


def _file_type(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return FILE_TO_STAGE_TYPE.get(ext, "file_gen")


class TaskScheduler:
    def __init__(self):
        self._stages: List[AtomicStage] = []

    @property
    def stages(self) -> List[AtomicStage]:
        return list(self._stages)

    def schedule_from_plan(self, plan: dict, models: Dict[str, str]) -> List[AtomicStage]:
        self._stages = []
        folder_structure = plan.get("architecture", {}).get("folder_structure", [])
        if isinstance(folder_structure, list) and folder_structure:
            self._add_folder_stage(folder_structure)
        files = plan.get("features", {}).get("files", {})
        if not files and folder_structure:
            files = self._infer_files_from_structure(folder_structure)
        stage_names = set()
        for file_path in files:
            stage_type = _file_type(file_path)
            stage_name = f"{stage_type}:{Path(file_path).name}"
            if stage_name in stage_names:
                continue
            stage_names.add(stage_name)
            deps = ["folder"] if any(f != file_path for f in files) else []
            model = models.get(stage_type, models.get("implement", ""))
            self._add_stage(
                name=stage_name,
                stage_type=stage_type,
                description=f"Generate {Path(file_path).name}",
                file_path=file_path,
                model=model,
                deps=deps,
                context={"file_path": file_path},
            )
        self._add_stage(
            name="verify",
            stage_type="verify",
            description="Verify all generated files",
            deps=[s.name for s in self._stages if s.stage_type in ("html", "css", "js", "python", "file_gen")],
        )
        self._add_stage(
            name="finalize",
            stage_type="finalize",
            description="Finalize and commit",
            deps=["verify"],
        )
        return self._stages

    def schedule_atomic(self, stage_names: List[str], models: Dict[str, str]) -> List[AtomicStage]:
        self._stages = []
        for name in stage_names:
            stage_type = _infer_stage_type(name)
            model = models.get(stage_type, models.get("implement", ""))
            deps = []
            if stage_type in ("html", "css", "js", "python", "file_gen"):
                deps = ["folder"]
            elif stage_type == "verify":
                deps = ["html", "css", "js", "python", "file_gen"]
            elif stage_type == "finalize":
                deps = ["verify"]
            self._add_stage(
                name=name,
                stage_type=stage_type,
                description=STAGE_DESCRIPTIONS.get(stage_type, f"Execute {name}"),
                model=model,
                deps=deps,
            )
        return self._stages

    def _add_folder_stage(self, folders: List[str]):
        self._add_stage(
            name="folder",
            stage_type="folder",
            description=f"Create {len(folders)} folders",
            context={"folders": folders},
        )

    def _add_stage(
        self,
        name: str,
        stage_type: str,
        description: str = "",
        file_path: str = "",
        model: str = "",
        deps: Optional[List[str]] = None,
        context: Optional[dict] = None,
    ):
        self._stages.append(AtomicStage(
            name=name,
            stage_type=stage_type,
            description=description,
            file_path=file_path,
            model=model,
            dependencies=deps or [],
            context=context or {},
        ))

    def _infer_files_from_structure(self, folder_structure: List[str]) -> Dict[str, List[str]]:
        files = {}
        has_html = any(f.endswith((".html", ".htm")) or "index.html" in f for f in folder_structure)
        has_css = any(f.endswith(".css") or "styles.css" in f for f in folder_structure)
        has_js = any(f.endswith(".js") or "script.js" in f for f in folder_structure)
        if has_html:
            files["index.html"] = ["head", "navbar", "hero", "features", "footer"]
        if has_css:
            files["styles.css"] = ["variables", "layout", "navbar", "hero", "cards", "animations", "responsive"]
        if has_js:
            files["script.js"] = ["navigation", "theme", "storage", "animations", "utilities"]
        return files

    def clear(self):
        self._stages.clear()
