import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from streaming.output_renderer import OutputRenderer
from streaming.stream_manager import StreamManager
from state import get_state_manager, StateManager
from ui.terminal_renderer import _info, _ok, _err, _warn, _step, get_pipeline, console
from utils.helpers import get_symbol

from generation.incremental_engine import IncrementalFileBuilder
from verifier.base_verifier import verify_expected_files, verify_web_project, VerificationReport
from repair.repair_engine import RepairEngine


FOLDER_STAGE_TYPE = "folder"
FILE_GEN_TYPES = {"html", "css", "js", "python", "file_gen"}
VERIFY_STAGE_TYPE = "verify"
REPAIR_STAGE_TYPE = "repair"
FINALIZE_STAGE_TYPE = "finalize"


class StageExecutor:
    def __init__(
        self,
        workdir: Path,
        state_manager: Optional[StateManager] = None,
        renderer: Optional[OutputRenderer] = None,
    ):
        self._workdir = workdir
        self._sm = state_manager or get_state_manager(workdir)
        self._renderer = renderer or OutputRenderer()
        self._stream_manager = StreamManager(workdir, state_manager, renderer)
        self._builder = IncrementalFileBuilder(workdir)
        self._repair_engine = RepairEngine(max_attempts=3)
        self._generated_files: Dict[str, str] = {}
        self._pipeline = get_pipeline()

    def execute(self, stage: Any) -> Tuple[bool, str]:
        stage_type = stage.stage_type if hasattr(stage, "stage_type") else ""
        name = stage.name if hasattr(stage, "name") else str(stage)

        handlers = {
            FOLDER_STAGE_TYPE: self._execute_folder,
            "html": self._execute_file_gen,
            "css": self._execute_file_gen,
            "js": self._execute_file_gen,
            "python": self._execute_file_gen,
            "file_gen": self._execute_file_gen,
            VERIFY_STAGE_TYPE: self._execute_verify,
            REPAIR_STAGE_TYPE: self._execute_repair,
            FINALIZE_STAGE_TYPE: self._execute_finalize,
        }

        handler = handlers.get(stage_type)
        if not handler:
            return False, f"No handler for stage type: {stage_type}"

        self._sm.start_stage(name)
        if self._pipeline:
            self._pipeline.add("➻", f"Stage: {name}", "step")

        return handler(stage)

    def _execute_folder(self, stage: Any) -> Tuple[bool, str]:
        folders = stage.context.get("folders", []) if hasattr(stage, "context") else []
        if not folders:
            folders = self._infer_folders()
        if not folders:
            return True, "No folders to create"

        created = 0
        for folder in folders:
            path = self._workdir / folder
            path.mkdir(parents=True, exist_ok=True)
            if self._pipeline:
                self._pipeline.folder_created(folder)
            created += 1

        self._sm.mark_generated("folders")
        return True, f"Created {created} folder(s)"

    def _execute_file_gen(self, stage: Any) -> Tuple[bool, str]:
        file_path = stage.file_path if hasattr(stage, "file_path") and stage.file_path else ""
        if not file_path:
            return True, "No file path specified"
        context = self._build_context()
        sections = self._get_sections_for_file(file_path)
        if not sections:
            return True, f"No section definitions for {file_path}"

        self._sm.set_file(file_path)
        ok = self._builder.build_file(
            file_path, sections, context,
            pipeline=self._pipeline,
            streaming=True,
            renderer=self._renderer,
        )
        if ok:
            content = (self._workdir / file_path).read_text(encoding="utf-8") if (self._workdir / file_path).exists() else ""
            self._generated_files[file_path] = content
            return True, f"Generated {file_path}"
        return False, f"Failed to generate {file_path}"

    def _execute_verify(self, stage: Any) -> Tuple[bool, str]:
        if not self._generated_files:
            return True, "No files to verify"
        report = verify_web_project(self._workdir, self._generated_files)
        if self._pipeline:
            for issue in report.issues:
                self._pipeline.verify(
                    f"[{issue.severity}] {issue.category}",
                    "ok" if not issue.blocking() else "err",
                    issue.message,
                )
        self._sm.mark_verified(
            status="passed" if report.passed else "failed",
            score=report.score,
        )
        if report.passed:
            return True, report.summary
        return False, report.summary

    def _execute_repair(self, stage: Any) -> Tuple[bool, str]:
        file_paths = list(self._generated_files.keys())
        ok, msg = self._repair_engine.repair(file_paths, "Verification failed")
        self._sm.mark_repaired(
            attempt=len(self._repair_engine.attempts),
            success=ok,
        )
        return ok, msg

    def _execute_finalize(self, stage: Any) -> Tuple[bool, str]:
        elapsed = time.time() - self._sm.execution.start_time
        self._sm.finish_task()
        return True, f"Task completed in {elapsed:.1f}s"

    def _build_context(self) -> Dict[str, str]:
        return {
            "project_name": self._sm.task.request.split()[0] if self._sm.task.request else "Project",
            "design": "modern glassmorphism with gradient accents",
            "spec": "professional landing page with responsive design, dark theme support, smooth animations",
        }

    def _get_sections_for_file(self, file_path: str) -> List[str]:
        from generation.incremental_engine import SECTION_PROMPTS
        prompts = SECTION_PROMPTS.get(file_path, {})
        if prompts:
            return list(prompts.keys())
        ext = Path(file_path).suffix.lower()
        if ext in (".html", ".htm"):
            return ["head", "navbar", "hero", "features", "footer"]
        if ext == ".css":
            return ["variables", "layout", "navbar", "hero", "cards", "animations", "responsive"]
        if ext == ".js":
            return ["navigation", "theme", "storage", "animations", "utilities"]
        if ext == ".py":
            return ["imports", "config", "routes", "main"]
        return ["content"]

    def _infer_folders(self) -> List[str]:
        tree = self._sm.project.folder_structure if hasattr(self._sm, "project") else []
        if isinstance(tree, list):
            return [f for f in tree if not Path(f).suffix]
        return []
