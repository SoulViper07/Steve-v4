import tempfile
from pathlib import Path

from workspace.path_resolver import PathResolver
from workspace.file_tracker import FileTracker
from workspace.file_manager import FileManager
from workspace.change_detector import ChangeDetector, CHANGE_ADDED, CHANGE_MODIFIED, CHANGE_DELETED
from workspace.project_tree import ProjectScanner
from workspace.dependency_graph import FileDependencyGraph


class TestPathResolver:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.resolver = PathResolver(self.tmpdir)

    def test_absolute(self):
        result = self.resolver.absolute("test.txt")
        assert str(result) == str(self.tmpdir / "test.txt")

    def test_relative(self):
        result = self.resolver.relative(self.tmpdir / "sub" / "file.txt")
        assert result == "sub/file.txt"

    def test_is_inside(self):
        assert self.resolver.is_inside(self.tmpdir / "file.txt")
        assert not self.resolver.is_inside(Path(tempfile.mkdtemp()) / "x.txt")

    def test_exists(self):
        f = self.tmpdir / "test.txt"
        f.write_text("hello")
        assert self.resolver.exists("test.txt")
        assert not self.resolver.exists("missing.txt")

    def test_ensure_dir(self):
        p = self.resolver.ensure_dir("a/b/c")
        assert p.exists()
        assert p.is_dir()

    def test_is_excluded(self):
        excluded = self.tmpdir / ".git" / "config"
        included = self.tmpdir / "src" / "main.py"
        excluded.parent.mkdir(parents=True, exist_ok=True)
        excluded.touch()
        included.parent.mkdir(parents=True, exist_ok=True)
        included.touch()
        assert self.resolver.is_excluded(excluded)
        assert not self.resolver.is_excluded(included)


class TestFileTracker:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.tracker = FileTracker()

    def test_track_file(self):
        f = self.tmpdir / "hello.py"
        f.write_text("print('hello')")
        entry = self.tracker.track(f, self.tmpdir)
        assert entry.path == "hello.py"
        assert entry.language == "python"
        assert entry.size > 0

    def test_untrack_file(self):
        f = self.tmpdir / "test.py"
        f.write_text("x = 1")
        self.tracker.track(f, self.tmpdir)
        self.tracker.untrack("test.py")
        assert self.tracker.get("test.py") is None

    def test_stats(self):
        f1 = self.tmpdir / "a.py"
        f2 = self.tmpdir / "b.js"
        f1.write_text("x")
        f2.write_text("y")
        self.tracker.track(f1, self.tmpdir)
        self.tracker.track(f2, self.tmpdir)
        stats = self.tracker.stats()
        assert stats["total"] == 2
        assert "python" in stats["languages"]
        assert "javascript" in stats["languages"]

    def test_by_language(self):
        f = self.tmpdir / "test.py"
        f.write_text("x")
        self.tracker.track(f, self.tmpdir)
        entries = self.tracker.by_language("python")
        assert len(entries) == 1


class TestFileManager:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.resolver = PathResolver(self.tmpdir)
        self.tracker = FileTracker()
        self.manager = FileManager(self.resolver, self.tracker)

    def test_create_file(self):
        ok, msg = self.manager.create("test.txt", "hello world")
        assert ok
        assert (self.tmpdir / "test.txt").exists()
        assert (self.tmpdir / "test.txt").read_text(encoding="utf-8") == "hello world"

    def test_read_file(self):
        self.manager.create("test.txt", "hello")
        content = self.manager.read("test.txt")
        assert content == "hello"

    def test_update_file(self):
        self.manager.create("test.txt", "v1")
        self.manager.update("test.txt", "v2")
        content = self.manager.read("test.txt")
        assert content == "v2"

    def test_delete_file(self):
        self.manager.create("test.txt", "hello")
        ok, msg = self.manager.delete("test.txt")
        assert ok
        assert not (self.tmpdir / "test.txt").exists()

    def test_smart_write_identical(self):
        self.manager.create("test.txt", "hello")
        ok, msg = self.manager.smart_write("test.txt", "hello")
        assert "identical" in msg.lower()

    def test_surgical_edit_exact(self):
        self.manager.create("test.txt", "Hello World")
        ok, msg, strategy = self.manager.apply_surgical_edit("test.txt", "Hello", "Hi")
        assert ok
        assert strategy == "exact"
        assert self.manager.read("test.txt") == "Hi World"

    def test_surgical_edit_fuzzy(self):
        self.manager.create("test.txt", "Hello  World")
        ok, msg, strategy = self.manager.apply_surgical_edit("test.txt", "Hello World", "Hi World")
        assert ok

    def test_rename(self):
        self.manager.create("old.txt", "hello")
        ok, msg = self.manager.rename("old.txt", "new.txt")
        assert ok
        assert not (self.tmpdir / "old.txt").exists()
        assert (self.tmpdir / "new.txt").exists()

    def test_move(self):
        self.manager.create("src.txt", "hello")
        ok, msg = self.manager.move("src.txt", "dst.txt")
        assert ok


class TestChangeDetector:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.resolver = PathResolver(self.tmpdir)
        self.tracker = FileTracker()
        self.detector = ChangeDetector(self.tracker)

    def test_no_changes(self):
        changes = self.detector.detect(set())
        assert len(changes) == 0

    def test_added_file(self):
        f = self.tmpdir / "new.txt"
        f.write_text("hello")
        self.tracker.track(f, self.tmpdir)
        self.detector.snapshot()
        f2 = self.tmpdir / "added.txt"
        f2.write_text("world")
        self.tracker.track(f2, self.tmpdir)
        changes = self.detector.detect(set(self.tracker.all_files))
        assert any(c.change_type == CHANGE_ADDED for c in changes)

    def test_modified_file(self):
        f = self.tmpdir / "test.txt"
        f.write_text("v1")
        self.tracker.track(f, self.tmpdir)
        self.detector.snapshot()
        f.write_text("v2")
        self.tracker.track(f, self.tmpdir)
        changes = self.detector.detect(set(self.tracker.all_files))
        assert any(c.change_type == CHANGE_MODIFIED for c in changes)

    def test_deleted_file(self):
        f = self.tmpdir / "test.txt"
        f.write_text("hello")
        self.tracker.track(f, self.tmpdir)
        self.detector.snapshot()
        self.tracker.untrack("test.txt")
        changes = self.detector.detect(set(self.tracker.all_files))
        assert any(c.change_type == CHANGE_DELETED for c in changes)


class TestProjectScanner:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.scanner = ProjectScanner()

    def test_scan_empty(self):
        tree = self.scanner.scan(self.tmpdir)
        assert tree.total_files == 0

    def test_scan_with_files(self):
        (self.tmpdir / "file1.txt").write_text("hello")
        (self.tmpdir / "file2.py").write_text("x = 1")
        tree = self.scanner.scan(self.tmpdir)
        assert tree.total_files == 2
        assert len(tree.flat_list) == 2

    def test_excluded_dir(self):
        (self.tmpdir / ".git" / "config").parent.mkdir(parents=True, exist_ok=True)
        (self.tmpdir / ".git" / "config").write_text("[core]")
        (self.tmpdir / "src" / "main.py").parent.mkdir(parents=True, exist_ok=True)
        (self.tmpdir / "src" / "main.py").write_text("print('hello')")
        tree = self.scanner.scan(self.tmpdir)
        assert tree.total_files == 1
        assert "src/main.py" in tree.flat_list

    def test_excluded_ext(self):
        (self.tmpdir / "file.pyc").write_text("x")
        (self.tmpdir / "file.py").write_text("x = 1")
        tree = self.scanner.scan(self.tmpdir)
        assert tree.total_files == 1
        assert "file.py" in tree.flat_list


class TestDependencyGraph:
    def setup_method(self):
        self.graph = FileDependencyGraph()

    def test_add_node(self):
        self.graph.add_node("test.py")
        assert "test.py" in self.graph.all_paths()

    def test_add_dependency(self):
        self.graph.add_dependency("main.py", "utils.py")
        assert "utils.py" in self.graph.dependencies("main.py")
        assert "main.py" in self.graph.dependents("utils.py")

    def test_topological_sort(self):
        self.graph.add_dependency("main.py", "utils.py")
        self.graph.add_dependency("utils.py", "lib.py")
        order = self.graph.topological_sort()
        assert order.index("lib.py") < order.index("utils.py")
        assert order.index("utils.py") < order.index("main.py")

    def test_is_cyclic(self):
        self.graph.add_dependency("a", "b")
        self.graph.add_dependency("b", "c")
        self.graph.add_dependency("c", "a")
        assert self.graph.is_cyclic()

    def test_not_cyclic(self):
        self.graph.add_dependency("a", "b")
        self.graph.add_dependency("b", "c")
        assert not self.graph.is_cyclic()
