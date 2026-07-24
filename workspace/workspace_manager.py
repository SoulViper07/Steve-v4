import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from state import get_state_manager, StateManager
from ui.terminal_renderer import _info, _ok, _err, _warn, _step, get_pipeline

from .path_resolver import PathResolver
from .file_tracker import FileTracker, FileIndexEntry
from .file_manager import FileManager
from .project_tree import ProjectScanner, ProjectTree
from .change_detector import ChangeDetector, FileChange, CHANGE_ADDED, CHANGE_MODIFIED, CHANGE_DELETED, CHANGE_MOVED
from .dependency_graph import FileDependencyGraph


WORKSPACE_INTELLIGENCE_VERSION = "1.0.0"


class WorkspaceManager:
    def __init__(
        self,
        workdir: Optional[Path] = None,
        state_manager: Optional[StateManager] = None,
    ):
        self._workdir = (workdir or Path.cwd()).resolve()
        self._sm = state_manager or get_state_manager(self._workdir)
        self._resolver = PathResolver(self._workdir)
        self._tracker = FileTracker()
        self._file_manager = FileManager(self._resolver, self._tracker)
        self._scanner = ProjectScanner()
        self._change_detector = ChangeDetector(self._tracker)
        self._dep_graph = FileDependencyGraph()
        self._initialized = False
        self._scan_history: List[dict] = []

    @property
    def resolver(self) -> PathResolver:
        return self._resolver

    @property
    def tracker(self) -> FileTracker:
        return self._tracker

    @property
    def file_manager(self) -> FileManager:
        return self._file_manager

    @property
    def dep_graph(self) -> FileDependencyGraph:
        return self._dep_graph

    def initialize(self) -> Tuple[bool, str]:
        if not self._workdir.is_dir():
            return False, f"Directory not found: {self._workdir}"
        self._sm.set_project(str(self._workdir))
        self._initialized = True
        path = self._workdir / ".steve"
        path.mkdir(parents=True, exist_ok=True)
        return True, f"Workspace initialized at {self._workdir}"

    def scan(self, recursive: bool = True) -> ProjectTree:
        tree = self._scanner.scan(self._workdir, recursive=recursive)
        self._tracker.clear()
        for path_str in tree.flat_list:
            abs_path = self._workdir / path_str
            self._tracker.track(abs_path, self._workdir)
        self._sm.set_project(str(self._workdir), tree.flat_list)
        self._change_detector.snapshot()
        self._analyze_dependencies(tree.flat_list)
        self._scan_history.append({
            "timestamp": time.time(),
            "file_count": tree.total_files,
            "dir_count": tree.total_dirs,
            "total_size": tree.total_size,
        })
        return tree

    def _analyze_dependencies(self, file_list: List[str]):
        self._dep_graph.clear()
        for path_str in file_list:
            abs_path = self._workdir / path_str
            if abs_path.is_file() and abs_path.stat().st_size < 1048576:
                try:
                    content = abs_path.read_text(encoding="utf-8", errors="replace")
                    self._dep_graph.analyze_file(path_str, content)
                except Exception:
                    self._dep_graph.add_node(path_str)
            else:
                self._dep_graph.add_node(path_str)

    def create_project(self, folder_structure: List[str]) -> int:
        created = 0
        for folder in folder_structure:
            path = self._resolver.absolute(folder)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                get_pipeline() and get_pipeline().folder_created(folder)
                created += 1
        return created

    def load_project(self) -> ProjectTree:
        return self.scan()

    def write_file(self, path: str, content: str) -> Tuple[bool, str]:
        abs_path = self._resolver.absolute(path)
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        existed = abs_path.exists()
        ok, msg = self._file_manager.smart_write(path, content)
        if ok:
            self._tracker.track(abs_path, self._resolver.root)
            if existed:
                self._tracker.mark_modified(path)
                self._sm.mark_modified(path)
            else:
                self._tracker.mark_generated(path)
                self._sm.mark_generated(path)
            self._dep_graph.analyze_file(path, content)
        return ok, msg

    def read_file(self, path: str) -> Optional[str]:
        return self._file_manager.read(path)

    def delete_file(self, path: str) -> Tuple[bool, str]:
        ok, msg = self._file_manager.delete(path)
        if ok:
            self._tracker.untrack(path)
        return ok, msg

    def rename_file(self, old_path: str, new_path: str) -> Tuple[bool, str]:
        ok, msg = self._file_manager.rename(old_path, new_path)
        if ok:
            self._dep_graph.add_node(new_path)
        return ok, msg

    def backup_file(self, path: str) -> Optional[str]:
        return self._file_manager.backup(path)

    def restore_file(self, backup_path: str) -> Tuple[bool, str]:
        return self._file_manager.restore(backup_path)

    def apply_edit(self, path: str, find: str, replace: str) -> Tuple[bool, str, str]:
        ok, msg, strategy = self._file_manager.apply_surgical_edit(path, find, replace)
        if ok:
            abs_path = self._resolver.absolute(path)
            self._tracker.track(abs_path, self._resolver.root)
            self._tracker.mark_modified(path)
            content = self._file_manager.read(path)
            if content is not None:
                self._dep_graph.analyze_file(path, content)
        return ok, msg, strategy

    def detect_changes(self) -> List[FileChange]:
        current_paths = set(self._tracker.all_files)
        changes = self._change_detector.detect(current_paths)
        return changes

    def detect_languages(self) -> Dict[str, int]:
        return self._tracker.stats()["languages"]

    def detect_framework(self) -> str:
        return self._tracker.detect_framework()

    def detect_config_files(self) -> List[str]:
        config_names = {
            "package.json", "requirements.txt", "pyproject.toml", "setup.py",
            "Cargo.toml", "go.mod", "Gemfile", "pom.xml", "build.gradle",
            "composer.json", "Makefile", "Dockerfile", "docker-compose.yml",
            ".env", ".env.example", "tsconfig.json", "webpack.config.js",
            "vite.config.ts", "next.config.js", "tailwind.config.js",
            ".prettierrc", ".eslintrc", ".eslintrc.json", ".stylelintrc",
            ".gitignore", ".gitattributes", "Dockerfile", "docker-compose.yml",
        }
        found = []
        for name in config_names:
            if (self._workdir / name).exists():
                found.append(name)
        return found

    def get_file_info(self, path: str) -> Optional[FileIndexEntry]:
        return self._tracker.get(path)

    def index_stats(self) -> dict:
        return self._tracker.stats()

    def intelligence_report(self) -> dict:
        stats = self.index_stats()
        return {
            "version": WORKSPACE_INTELLIGENCE_VERSION,
            "workspace": str(self._workdir),
            "files": stats,
            "framework": self.detect_framework(),
            "languages": self.detect_languages(),
            "config_files": self.detect_config_files(),
            "dependency_graph_nodes": len(self._dep_graph.all_paths()),
            "scans_performed": len(self._scan_history),
            "total_size_kb": round(stats.get("total", 0) * 0.5, 1),
        }

    def verify_consistency(self) -> List[str]:
        issues = []
        for path_str in self._tracker.all_files:
            abs_path = self._workdir / path_str
            if not abs_path.exists():
                issues.append(f"Indexed file missing: {path_str}")
        for entry in self._tracker.index.values():
            if entry.generation_status == "generated" and entry.verification_status == "unknown":
                issues.append(f"Generated file not verified: {entry.path}")
        return issues

    def display_scan_results(self, tree: ProjectTree):
        stats = self._tracker.stats()
        framework = self._tracker.detect_framework()
        configs = self.detect_config_files()
        _ok(f"Workspace scanned: {stats['total']} files")
        if stats["languages"]:
            lang_str = ", ".join(f"{lang}: {count}" for lang, count in stats["languages"].items())
            _info(f"Languages: {lang_str}")
        if framework:
            _info(f"Framework: {framework}")
        if configs:
            _info(f"Config files: {len(configs)} detected")
        pipeline = get_pipeline()
        if pipeline:
            pipeline.add("📂", f"Workspace indexed: {stats['total']} files, {len(stats['languages'])} languages", "ok")
            if framework:
                pipeline.add("🔧", f"Framework detected: {framework}", "info")

    def display_changes(self, changes: List[FileChange]):
        if not changes:
            _ok("No changes detected")
            return
        pipeline = get_pipeline()
        for change in changes:
            if change.change_type == CHANGE_ADDED:
                msg = f"+ {change.path}"
                pipeline and pipeline.add("  +", msg, "ok")
            elif change.change_type == CHANGE_MODIFIED:
                msg = f"~ {change.path}"
                pipeline and pipeline.add("  ~", msg, "step")
            elif change.change_type == CHANGE_DELETED:
                msg = f"- {change.path}"
                pipeline and pipeline.add("  -", msg, "warn")
            elif change.change_type == CHANGE_MOVED:
                msg = f"{change.old_path} -> {change.path}"
                pipeline and pipeline.add("  ↻", msg, "step")
        _info(self._change_detector.summary())
