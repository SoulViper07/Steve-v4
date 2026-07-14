from pathlib import Path
from typing import List, Dict, Optional, Any

from .models import RequestRoute, ProjectMap, ExecutionPlan
from .file_context import FileContext
from actions.executor import FilesystemExecutor
from utils.logger import SteveDebugLog
from config.settings import (
    SYSTEM_PROMPT, DEFAULT_MODEL, MAX_HISTORY_MESSAGES, 
    MAX_CONTEXT_FILES_PER_TURN, AUTOLOAD_PROJECT_MAX_BYTES,
    ROUTE_PROMPTS, DEFAULT_ROUTE_PROMPT
)
from ui.terminal_renderer import _ok

from .inspector import ProjectInspector
from .planner import Planner

def compact_assistant_message(text: str) -> str:
    """Strip large action tag contents from history to save context tokens."""
    # Placeholder for logic from agent.py
    return text

class Conversation:
    def __init__(self, workdir: Path, manual_model: Optional[str] = None):
        self.manual_model = manual_model
        self.workdir  = Path(workdir).resolve()
        self.messages = [{"role":"system","content":SYSTEM_PROMPT}]
        self.file_ctx = FileContext(self.workdir)
        self.executor = FilesystemExecutor(self.workdir, self.file_ctx)
        self.inspector = ProjectInspector(self.workdir)
        self.planner = Planner(self.workdir)
        self.turn     = 0
        self.active_files: List[str] = []
        self.active_files_pending = False
        self.available_models: List[str] = []
        self.auto_model: str = DEFAULT_MODEL
        self.last_project_map: Optional[ProjectMap] = None
        self.last_plan: Optional[ExecutionPlan] = None
        self.action_mode_active = False
        self.action_mode_route: Optional[RequestRoute] = None
        self.debug_log = SteveDebugLog(self.workdir)

    def begin_new_user_task(self):
        """Clear transient generation state so one task cannot seed the next."""
        self.last_plan = None
        self.action_mode_active = False
        self.action_mode_route = None
        self.executor.reset_project_generation_state()

    def reset_project_generation_state(self):
        self.last_plan = None
        self.last_project_map = None
        self.action_mode_active = False
        self.action_mode_route = None
        self.active_files = []
        self.active_files_pending = False
        self.file_ctx.pending.clear()
        self.file_ctx.recently_modified.clear()
        self.executor.reset_project_generation_state()

    def set_workdir(self, workdir: Path, clear_file_context: bool = False):
        self.workdir = Path(workdir).resolve()
        self.executor.workdir = self.workdir
        self.file_ctx.set_workdir(self.workdir)
        # self.inspector = ProjectInspector(self.workdir)
        # self.planner = Planner(self.workdir)
        self.debug_log = SteveDebugLog(self.workdir)
        if clear_file_context:
            self.file_ctx.clear()
            self.active_files = []
            self.active_files_pending = False
            self.last_project_map = None
            self.last_plan = None

    def add_user(self, text: str):
        self.messages.append({"role":"user","content": text})
        self.turn += 1
        self._trim_history()

    def add_assistant(self, text: str):
        self.messages.append({"role":"assistant","content":compact_assistant_message(text)})
        self._trim_history()

    def build_request_messages(self, route: Optional[RequestRoute] = None, extra_notes: str = ""):
        request_messages = list(self.messages)
        if route is None:
            route = RequestRoute(
                mode="chat", actionable=False,
                project_scoped=False, file_specific=False,
                help_requested=False, plan_requested=False, inspect_requested=False,
            )
        route_mode = getattr(route, 'intent', route.mode)
        request_messages[0] = {"role": "system", "content": self._build_system_prompt(route_mode)}
        if not request_messages or request_messages[-1]["role"] != "user":
            return request_messages
        raw_user = request_messages[-1]["content"]
        fresh_selected = bool(self.file_ctx.pending or self.file_ctx._match_referenced(raw_user))
        carry_files = self.active_files if self.active_files_pending else []
        ctx, selected = self.file_ctx.build_turn_context(raw_user, carry_files)
        self.active_files = selected or self.active_files[:MAX_CONTEXT_FILES_PER_TURN]
        self.active_files_pending = fresh_selected
        cwd_note = f"Working directory: `{self.workdir}`\n"
        plan_note = ""
        if self.last_plan and route_mode in {"plan", "action_project"}:
            plan_note = f"Current execution plan:\n{self.last_plan.to_block()}\n\n"
        extra_block = f"{extra_notes.strip()}\n\n" if extra_notes.strip() else ""
        if ctx:
            content = f"{cwd_note}\n{extra_block}{plan_note}{ctx}\n\nUser request:\n{raw_user}"
        else:
            content = f"{cwd_note}\n{extra_block}{plan_note}User request:\n{raw_user}"
        request_messages[-1] = {"role": "user", "content": content}
        return request_messages

    def _build_system_prompt(self, route: str) -> str:
        route_hint = ROUTE_PROMPTS.get(route)
        if route_hint is None:
            route_hint = DEFAULT_ROUTE_PROMPT
            if route:
                route_hint += f" Unknown route '{route}' received; falling back safely."
        return SYSTEM_PROMPT + "\n\nRoute hint: " + route_hint

    def model_status(self) -> str:
        if self.manual_model:
            return f"manual override: {self.manual_model}"
        suffix = " (default)"
        return f"auto: {self.auto_model}{suffix}"

    def note_active_files(self, paths: List[str]):
        active = []
        for path in paths:
            if path in self.file_ctx.files and path not in active:
                active.append(path)
        if active:
            self.active_files = active[:MAX_CONTEXT_FILES_PER_TURN]
            self.active_files_pending = True

    def _trim_history(self):
        if len(self.messages) <= MAX_HISTORY_MESSAGES + 1:
            return
        self.messages = [self.messages[0]] + self.messages[-MAX_HISTORY_MESSAGES:]

    def reset(self):
        self.messages = [{"role":"system","content":SYSTEM_PROMPT}]; self.turn = 0
        self.active_files = []
        self.active_files_pending = False
        self.action_mode_active = False
        self.action_mode_route = None
        self.last_plan = None
        self.executor.reset_project_generation_state()
        _ok("Conversation cleared.")
