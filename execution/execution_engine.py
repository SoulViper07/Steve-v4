import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable

from state import get_state_manager, StateManager
from streaming.output_renderer import OutputRenderer
from streaming.progress_tracker import ProgressTracker
from ui.terminal_renderer import (
    console, _plain_terminal, _info, _ok, _err, _warn, _step,
    create_pipeline, clear_pipeline, get_pipeline, get_symbol,
    PipelineDisplay,
)
from router import get_router, IntelligentRouter, ExecutionPipeline
from planner.execution_plan import CompletePlan

from .execution_context import ExecutionContext
from .dependency_manager import DependencyManager
from .task_scheduler import TaskScheduler, AtomicStage
from .stage_executor import StageExecutor


BAR_WIDTH = 20


def _render_progress_bar(pct: int, label: str = ""):
    filled = int(pct / 100 * BAR_WIDTH)
    bar = "█" * filled + "░" * (BAR_WIDTH - filled)
    label_part = f"  {label[:35]}" if label else ""
    if _plain_terminal():
        print(f"\r  [{bar}] {pct:3d}%{label_part}", end="")
    else:
        console.print(f"  [cyan]{bar}[/cyan] [bold]{pct:3d}%[/bold]{label_part}")
    if pct == 100:
        if _plain_terminal():
            print()


class ExecutionEngine:
    def __init__(
        self,
        workdir: Optional[Path] = None,
        state_manager: Optional[StateManager] = None,
        renderer: Optional[OutputRenderer] = None,
    ):
        self._workdir = (workdir or Path.cwd()).resolve()
        self._sm = state_manager or get_state_manager(self._workdir)
        self._renderer = renderer or OutputRenderer()
        self._scheduler = TaskScheduler()
        self._dep_manager = DependencyManager()
        self._context = ExecutionContext()
        self._executor = StageExecutor(self._workdir, self._sm, self._renderer)
        self._pipeline: Optional[PipelineDisplay] = None
        self._aborted = threading.Event()
        self._repo_context: Optional[Dict] = None

    def set_repository_context(self, repo_summary: Dict):
        self._repo_context = repo_summary

    @property
    def context(self) -> ExecutionContext:
        return self._context

    def abort(self):
        self._aborted.set()

    def execute_plan(
        self,
        plan: CompletePlan,
        models: Optional[Dict[str, str]] = None,
        stream: bool = True,
    ) -> Tuple[bool, str]:
        self._pipeline = create_pipeline()
        self._aborted.clear()
        self._context = ExecutionContext()
        self._context.task_id = plan.task_id
        self._context.start()

        model_map = models or {}
        if not model_map:
            router = get_router(self._workdir)
            router_pipeline = router.build_pipeline(
                request=plan.request,
                category=plan.classification.category if hasattr(plan, "classification") else "",
            )
            for step in router_pipeline.steps:
                model_map[step.stage] = step.model

        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else {}
        stages = self._scheduler.schedule_from_plan(plan_dict, model_map)
        if not stages:
            stages = self._scheduler.schedule_atomic(
                [s.stage for s in plan.execution.steps] if hasattr(plan, "execution") else [],
                model_map,
            )

        dep_map = []
        for stage in stages:
            dep_map.append({
                "name": stage.name,
                "dependencies": stage.dependencies,
            })
        self._dep_manager.build_stage_graph(dep_map)

        valid, msg = self._dep_manager.validate()
        if not valid:
            clear_pipeline()
            return False, f"Invalid dependency graph: {msg}"

        execution_order = self._dep_manager.execution_order()
        ordered_stages = {s.name: s for s in stages}
        self._context.set_remaining(execution_order)
        total = len(execution_order)
        overall_ok = True

        if self._pipeline:
            self._pipeline.add("⚡", f"Execution Engine: {total} atomic stages", "step")

        for idx, stage_name in enumerate(execution_order):
            if self._aborted.is_set():
                _warn("Execution aborted by user")
                break

            stage = ordered_stages.get(stage_name)
            if not stage:
                continue

            self._context.stage_start(stage_name)
            self._renderer.stage_progress(stage_name)
            _render_progress_bar(
                int((idx / total) * 100),
                f"[{idx + 1}/{total}] {stage.description or stage_name}",
            )

            if self._pipeline:
                self._pipeline.add("➻", f"Executing: {stage.description or stage_name}", "step")

            ok, msg = self._executor.execute(stage)

            if ok:
                self._context.stage_complete(stage_name)
                if self._pipeline:
                    self._pipeline.add("✓", f"{stage.description or stage_name} — {msg}", "ok")
                _ok(f"{stage.description or stage_name}: {msg}")
            else:
                self._context.stage_failed(stage_name)
                if self._pipeline:
                    self._pipeline.add("✗", f"{stage.description or stage_name} failed: {msg}", "err")
                _err(f"{stage.description or stage_name} failed: {msg}")

                retry_ok = self._retry_stage(stage, ordered_stages)
                if retry_ok:
                    self._context.stage_complete(stage_name)
                    if self._pipeline:
                        self._pipeline.add("✓", f"{stage.description or stage_name} — recovered after retry", "ok")
                    _ok(f"{stage.description or stage_name} recovered after retry")
                else:
                    overall_ok = False

        _render_progress_bar(100, "Complete")

        self._sm.execution.elapsed_time = self._context.elapsed_time
        self._sm.finish_task()

        if overall_ok:
            total_elapsed = round(self._context.elapsed_time, 1)
            msg = f"Execution completed in {total_elapsed}s — {len(self._context.completed_stages)} stages"
            if self._pipeline:
                self._pipeline.add("✅", msg, "ok")
            _ok(msg)
            if self._pipeline:
                self._pipeline.render_timeline()
                if self._pipeline.state.git_activities:
                    self._pipeline.render_git_block()
                self._pipeline.render_report()
            clear_pipeline()
            return True, msg

        failed = ", ".join(self._context.failed_stages)
        msg = f"Execution completed with failures: {failed}"
        _err(msg)
        if self._pipeline:
            self._pipeline.add("⚠", msg, "err")
            self._pipeline.render_timeline()
            self._pipeline.render_report()
        clear_pipeline()
        return False, msg

    def _retry_stage(self, stage: AtomicStage, all_stages: Dict[str, AtomicStage]) -> bool:
        max_retries = getattr(stage, "max_retries", 2)
        for attempt in range(max_retries):
            if self._aborted.is_set():
                return False
            if self._pipeline:
                self._pipeline.add("🔧", f"Retry {attempt + 1}/{max_retries}: {stage.name}", "warn")
            _warn(f"Retry {attempt + 1}/{max_retries} for {stage.name}")
            ok, msg = self._executor.execute(stage)
            if ok:
                return True
        return False

    def execute_atomic(
        self,
        stage_name: str,
        stage_type: str,
        models: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str]:
        model_map = models or {}
        stages = self._scheduler.schedule_atomic([stage_name], model_map)
        if not stages:
            return False, f"Unknown stage: {stage_name}"
        return self._executor.execute(stages[0])
