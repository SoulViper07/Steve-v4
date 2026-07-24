import tempfile
from pathlib import Path

from patcher.diff_engine import DiffEngine, DiffType
from patcher.patch_executor import PatchExecutor
from patcher.live_diff_view import LiveDiffView


class TestDiffEngine:
    def setup_method(self):
        self.engine = DiffEngine()

    def test_empty_diff(self):
        result = self.engine.compute("hello", "hello")
        assert not result.has_changes
        assert result.total_changed == 0

    def test_addition(self):
        result = self.engine.compute("hello", "hello world")
        assert result.has_changes
        assert result.total_added > 0

    def test_removal(self):
        result = self.engine.compute("hello world", "hello")
        assert result.has_changes
        assert result.total_removed > 0

    def test_full_replace(self):
        result = self.engine.compute("abc", "xyz")
        assert result.has_changes

    def test_to_unified_diff(self):
        result = self.engine.compute("line1\nline2\n", "line1\nline3\n")
        unified = result.to_unified_diff()
        assert "+++" in unified
        assert "---" in unified
        assert "@@" in unified

    def test_impact_summary(self):
        result = self.engine.compute("a\nb\nc\n", "a\nx\nc\n")
        assert "hunk" in result.impact_summary
        assert "+" in result.impact_summary or "-" in result.impact_summary


class TestPatchExecutor:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.executor = PatchExecutor(self.tmpdir)

    def test_create_file(self):
        result = self.executor.create("test.txt", "hello")
        assert result.success
        assert result.operation == "create"
        assert (self.tmpdir / "test.txt").exists()

    def test_modify_file(self):
        self.executor.create("test.txt", "hello")
        result = self.executor.modify("test.txt", "hello world")
        assert result.success
        assert result.operation == "modify"
        assert result.diff is not None
        assert result.diff.has_changes

    def test_idempotent_modify(self):
        self.executor.create("test.txt", "hello")
        result = self.executor.modify("test.txt", "hello")
        assert result.success
        assert not result.diff.has_changes

    def test_delete_file(self):
        self.executor.create("test.txt", "hello")
        result = self.executor.delete("test.txt")
        assert result.success
        assert not (self.tmpdir / "test.txt").exists()

    def test_rename_file(self):
        self.executor.create("old.txt", "hello")
        result = self.executor.rename("old.txt", "new.txt")
        assert result.success
        assert not (self.tmpdir / "old.txt").exists()
        assert (self.tmpdir / "new.txt").exists()

    def test_surgical_edit_exact(self):
        self.executor.create("test.txt", "Hello World")
        result = self.executor.apply_surgical("test.txt", "Hello", "Hi")
        assert result.success
        content = (self.tmpdir / "test.txt").read_text(encoding="utf-8")
        assert content == "Hi World"

    def test_restore(self):
        self.executor.create("test.txt", "version1")
        self.executor.modify("test.txt", "version2")
        result = self.executor.restore("test.txt")
        assert result.success
        content = (self.tmpdir / "test.txt").read_text(encoding="utf-8", errors="replace")
        assert content == "version1"

    def test_rollback(self):
        self.executor.create("test.txt", "v1")
        self.executor.modify("test.txt", "v2")
        self.executor.modify("test.txt", "v3")
        result = self.executor.rollback("test.txt")
        assert result.success
        content = (self.tmpdir / "test.txt").read_text(encoding="utf-8", errors="replace")
        assert content == "v2"


class TestLiveDiffView:
    def setup_method(self):
        self.engine = DiffEngine()
        self.view = LiveDiffView()

    def test_display_summary(self):
        diff = self.engine.compute("old content", "new content")
        self.view.display_summary(diff, "test.txt")

    def test_display_batch(self):
        d1 = self.engine.compute("a", "b")
        d2 = self.engine.compute("c", "d")
        self.view.display_batch([d1, d2])
