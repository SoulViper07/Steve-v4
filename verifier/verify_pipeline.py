from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .base_verifier import Issue, VerificationReport, verify_web_project, verify_expected_files, quality_review


CHECK_STRUCTURE = "structure"
CHECK_SYNTAX = "syntax"
CHECK_IMPORTS = "imports"
CHECK_MISSING = "missing_files"
CHECK_EMPTY = "empty_files"
CHECK_HTML = "html"
CHECK_CSS = "css"
CHECK_JS = "javascript"
CHECK_PLANNER = "planner_consistency"
CHECK_EXECUTION = "execution_consistency"
CHECK_WORKSPACE = "workspace_consistency"


@dataclass
class QualityDimension:
    name: str
    score: float
    max_score: float = 100.0

    @property
    def percent(self) -> float:
        return round((self.score / self.max_score) * 100, 1)


@dataclass
class QualityScore:
    dimensions: Dict[str, QualityDimension] = field(default_factory=dict)

    @property
    def overall(self) -> float:
        if not self.dimensions:
            return 0.0
        return round(sum(d.percent for d in self.dimensions.values()) / len(self.dimensions), 1)

    def add(self, name: str, score: float, max_score: float = 100.0):
        self.dimensions[name] = QualityDimension(name=name, score=score, max_score=max_score)

    def summary_lines(self) -> List[str]:
        lines = []
        for name, dim in sorted(self.dimensions.items()):
            bar_len = int(dim.percent / 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            lines.append(f"  {name:20s} {bar} {dim.percent:5.1f}%")
        lines.append(f"  {'─' * 38}")
        lines.append(f"  {'Overall':20s} {'█' * int(self.overall / 10) + '░' * (10 - int(self.overall / 10))} {self.overall:5.1f}%")
        return lines


def _find_import_issues(workdir: Path, files: Dict[str, str]) -> List[Issue]:
    issues: List[Issue] = []
    for path, content in files.items():
        ext = Path(path).suffix.lower()
        if ext == ".html":
            linked = set()
            for match in __import_re(r"""<link[^>]*href=["']([^"']+)["']""", content):
                linked.add(match)
            for match in __import_re(r"""<script[^>]*src=["']([^"']+)["']""", content):
                linked.add(match)
            for ref in linked:
                if not ref.startswith(("http://", "https://", "//")):
                    ref_path = ref.split("?")[0].split("#")[0]
                    if not (workdir / ref_path).exists() and not (workdir / Path(path).parent / ref_path).exists():
                        if ref_path not in files:
                            issues.append(Issue("major", CHECK_IMPORTS, f"Broken import in {path}: {ref}", file=path))
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            for match in __import_re(r"""require\s*\(\s*['"]([^'"]+)['"]""", content):
                if not match.startswith(".") and "/" not in match:
                    continue
                ref = match.split("/")[0]
                if ref not in files and not (workdir / ref).exists():
                    issues.append(Issue("minor", CHECK_IMPORTS, f"Possible broken require in {path}: {match}", file=path))
    return issues


def __import_re(pattern: str, content: str) -> List[str]:
    import re
    return re.findall(pattern, content)


def _find_empty_file_issues(files: Dict[str, str]) -> List[Issue]:
    issues: List[Issue] = []
    for path, content in files.items():
        if not content or len(content.strip()) < 10:
            issues.append(Issue("critical", CHECK_EMPTY, f"File is empty or too small: {path}", file=path))
    return issues


def _find_missing_file_issues(workdir: Path, expected: List[str]) -> List[Issue]:
    issues: List[Issue] = []
    for path in expected:
        if not (workdir / path).exists():
            issues.append(Issue("critical", CHECK_MISSING, f"Required file missing: {path}", file=path))
    return issues


def verify_all(
    workdir: Path,
    files: Dict[str, str],
    expected_files: Optional[List[str]] = None,
) -> VerificationReport:
    report = VerificationReport()

    web_report = verify_web_project(workdir, files)
    for issue in web_report.issues:
        report.add(issue)

    if expected_files:
        missing = _find_missing_file_issues(workdir, expected_files)
        for issue in missing:
            report.add(issue)

    empty = _find_empty_file_issues(files)
    for issue in empty:
        report.add(issue)

    imports = _find_import_issues(workdir, files)
    for issue in imports:
        report.add(issue)

    report.passed = report.critical_count == 0 and report.major_count == 0
    report.score = max(0.0, 1.0 - (report.critical_count * 0.3 + report.major_count * 0.1 + report.minor_count * 0.05))
    report.summary = report.summarize()
    return report


def compute_quality_scores(files: Dict[str, str], request: str = "") -> QualityScore:
    qs = QualityScore()

    html = files.get("index.html", "")
    css = files.get("styles.css", "")
    js = files.get("script.js", "")

    if html:
        score = 0
        checks = 0
        checks += 1
        if "<!DOCTYPE" in html: score += 1
        if "<html" in html: score += 1
        if "<head>" in html: score += 1
        if "<body" in html: score += 1
        if "<meta" in html and "viewport" in html: score += 1
        if "<nav" in html or "<header" in html: score += 1
        if "<main" in html or "<section" in html: score += 1
        if "<footer" in html: score += 1
        if "styles.css" in html: score += 1
        if "script.js" in html: score += 1
        if 'aria-' in html.lower() or 'role=' in html.lower(): score += 1
        if "https://" in html or "http://" in html: score += 1
        max_s = checks * 12 if checks > 0 else 12
        qs.add("Architecture", (score / max_s) * 100)

    if css:
        score = 0
        checks = 0
        checks += 1
        if ":root" in css or "--" in css: score += 1
        if "@media" in css: score += 1
        if "display:" in css: score += 1
        if "grid" in css.lower() or "flex" in css.lower(): score += 1
        if "transition" in css.lower() or "animation" in css.lower(): score += 1
        if "hover" in css.lower(): score += 1
        if "color:" in css: score += 1
        if "font" in css.lower(): score += 1
        if "padding" in css or "margin" in css: score += 1
        max_s = checks * 9 if checks > 0 else 9
        qs.add("UI", (score / max_s) * 100)

    if css:
        score = 0
        if "@media" in css: score += 25
        if "max-width" in css or "min-width" in css: score += 25
        if "%" in css or "vw" in css or "vh" in css: score += 25
        if "grid" in css.lower() or "flex" in css.lower(): score += 25
        qs.add("Responsiveness", float(score))

    if "aria-" in html.lower() or 'role=' in html.lower(): score_a11y = 100
    elif html and ("alt=" in html or "label" in html.lower()): score_a11y = 75
    elif html: score_a11y = 50
    else: score_a11y = 0
    qs.add("Accessibility", float(score_a11y))

    if js:
        score = 0
        checks = 0
        checks += 1
        if "function " in js or "=>" in js: score += 1
        if "const " in js or "let " in js or "var " in js: score += 1
        if "addEventListener" in js or "onclick" in js: score += 1
        if "document." in js: score += 1
        if "class " in js: score += 1
        if "try" in js or "catch" in js: score += 1
        if "localStorage" in js or "fetch" in js: score += 1
        max_s = checks * 7 if checks > 0 else 7
        qs.add("Code Quality", (score / max_s) * 100)
    elif html:
        qs.add("Code Quality", 0.0)

    return qs


def should_repair(report: VerificationReport, threshold: float = 0.5) -> bool:
    return report.score < threshold or report.blocked


def identify_repair_targets(report: VerificationReport) -> List[str]:
    targets = set()
    for issue in report.issues:
        if issue.blocking() or issue.severity == "major":
            if issue.file:
                targets.add(issue.file)
            else:
                targets.add(issue.category)
    return sorted(targets)
