from pathlib import Path

from verifier.base_verifier import Issue, VerificationReport, verify_web_project, verify_expected_files
from verifier.verify_pipeline import verify_all, compute_quality_scores, should_repair, identify_repair_targets, QualityScore


class TestIssue:
    def test_blocking_critical(self):
        issue = Issue("critical", "html", "Missing DOCTYPE")
        assert issue.blocking()

    def test_non_blocking(self):
        issue = Issue("minor", "css", "No hover states")
        assert not issue.blocking()


class TestVerificationReport:
    def setup_method(self):
        self.report = VerificationReport()

    def test_initial_state(self):
        assert self.report.passed
        assert self.report.score == 1.0

    def test_add_critical(self):
        self.report.add(Issue("critical", "html", "Missing DOCTYPE"))
        assert self.report.critical_count == 1
        assert self.report.blocked

    def test_add_major(self):
        self.report.add(Issue("major", "css", "No framework"))
        assert self.report.major_count == 1

    def test_summarize(self):
        self.report.add(Issue("critical", "html", "Missing DOCTYPE"))
        self.report.add(Issue("minor", "css", "No hover"))
        s = self.report.summarize()
        assert "critical" in s
        assert "minor" in s


class TestVerifyWebProject:
    def test_missing_all(self):
        report = verify_web_project(Path.cwd(), {})
        assert not report.passed
        assert report.critical_count >= 3

    def test_valid_html(self):
        html = """<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width">
<link rel="stylesheet" href="styles.css">
<script src="script.js"></script>
</head><body><nav></nav><main></main><footer></footer></body></html>"""
        files = {"index.html": html, "styles.css": ":root { --primary: #333; } body { margin: 0; font-family: sans-serif; } .container { max-width: 1200px; }", "script.js": "const x = 1; function init() { document.addEventListener('DOMContentLoaded', () => { console.log('ready'); }); } init();"}
        report = verify_web_project(Path.cwd(), files)
        assert report.passed

    def test_incomplete_html(self):
        report = verify_web_project(Path.cwd(), {"index.html": "<html>"})
        assert not report.passed

    def test_empty_css(self):
        report = verify_web_project(Path.cwd(), {"index.html": "<!DOCTYPE html><html><body></body></html>", "styles.css": ""})
        assert not report.passed

    def test_empty_js(self):
        report = verify_web_project(Path.cwd(), {"index.html": "<!DOCTYPE html><html><body></body></html>", "styles.css": ":root{}", "script.js": ""})
        assert not report.passed


class TestVerifyExpectedFiles:
    def test_all_exist(self):
        report = verify_expected_files(Path.cwd(), [])
        assert report.passed

    def test_missing_file(self):
        report = verify_expected_files(Path.cwd(), ["nonexistent_file_xyz.txt"])
        assert not report.passed
        assert report.critical_count >= 1


class TestVerifyAll:
    def test_empty(self):
        report = verify_all(Path.cwd(), {})
        assert not report.passed

    def test_valid_project(self):
        html = """<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width">
<link rel="stylesheet" href="styles.css">
<script src="script.js"></script>
</head><body><nav></nav><main role="main"><section></section></main><footer></footer></body></html>"""
        css = ":root { --primary: #333; } body { margin: 0; } .container { max-width: 1200px; } @media (max-width: 768px) { .grid { display: flex; } }"
        js = "const x = 1; function init() { document.addEventListener('DOMContentLoaded', () => { console.log('ready'); }); } init();"
        files = {"index.html": html, "styles.css": css, "script.js": js}
        (Path.cwd() / "index.html").write_text(html)
        (Path.cwd() / "styles.css").write_text(css)
        (Path.cwd() / "script.js").write_text(js)
        try:
            report = verify_all(Path.cwd(), files, expected_files=["index.html", "styles.css", "script.js"])
            assert report.passed
        finally:
            (Path.cwd() / "index.html").unlink(missing_ok=True)
            (Path.cwd() / "styles.css").unlink(missing_ok=True)
            (Path.cwd() / "script.js").unlink(missing_ok=True)

    def test_import_check(self):
        html = '<!DOCTYPE html><html><head><link rel="stylesheet" href="missing.css"></head><body></body></html>'
        files = {"index.html": html}
        report = verify_all(Path.cwd(), files)
        assert not report.passed

    def test_empty_file(self):
        report = verify_all(Path.cwd(), {"empty.txt": ""})
        assert not report.passed


class TestQualityScore:
    def test_valid_project(self):
        html = """<!DOCTYPE html>
<html lang="en"><head><meta name="viewport" content="width=device-width">
<link rel="stylesheet" href="styles.css">
<script src="script.js"></script>
</head><body><nav></nav><main role="main"><section></section></main><footer></footer></body></html>"""
        css = """:root {--primary: #333;}
@media (max-width: 768px) { .grid { display: flex; } }
.color { color: red; }
.font { font-family: sans-serif; }
.pad { padding: 1rem; }
.trans { transition: all 0.3s; }
.hover:hover { opacity: 0.8; }"""
        js = """const app = () => {
  document.addEventListener('DOMContentLoaded', () => {
    try { localStorage.setItem('key', 'val'); } catch(e) {}
  });
};
class Util { }"""
        files = {"index.html": html, "styles.css": css, "script.js": js}
        qs = compute_quality_scores(files)
        assert qs.overall > 0
        assert "Architecture" in qs.dimensions
        assert "UI" in qs.dimensions
        summary = qs.summary_lines()
        assert len(summary) >= 3
        assert "Overall" in summary[-1]

    def test_empty_project(self):
        qs = compute_quality_scores({})
        assert qs.overall == 0

    def test_should_repair(self):
        report = VerificationReport()
        report.add(Issue("critical", "html", "Missing DOCTYPE"))
        report.score = 0.3
        assert should_repair(report)

    def test_should_not_repair(self):
        report = VerificationReport()
        assert not should_repair(report)

    def test_identify_repair_targets(self):
        report = VerificationReport()
        report.add(Issue("critical", "html", "Missing", file="index.html"))
        report.add(Issue("major", "css", "Missing", file="styles.css"))
        targets = identify_repair_targets(report)
        assert "index.html" in targets
        assert "styles.css" in targets
