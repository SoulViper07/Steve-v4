import os
import re
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class Issue:
    severity: str  # "critical", "major", "minor", "cosmetic"
    category: str  # "html", "css", "js", "structure", "accessibility", "performance"
    message: str
    file: str = ""
    line: int = 0
    suggestion: str = ""

    def blocking(self) -> bool:
        return self.severity == "critical"


@dataclass
class VerificationReport:
    passed: bool = True
    issues: List[Issue] = field(default_factory=list)
    summary: str = ""
    score: float = 1.0
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    cosmetic_count: int = 0

    @property
    def blocked(self) -> bool:
        return self.critical_count > 0

    def add(self, issue: Issue):
        self.issues.append(issue)
        if issue.severity == "critical":
            self.critical_count += 1
        elif issue.severity == "major":
            self.major_count += 1
        elif issue.severity == "minor":
            self.minor_count += 1
        elif issue.severity == "cosmetic":
            self.cosmetic_count += 1

    def summarize(self) -> str:
        parts = []
        if self.passed:
            parts.append("✓ All checks passed")
        if self.critical_count:
            parts.append(f"{self.critical_count} critical")
        if self.major_count:
            parts.append(f"{self.major_count} major")
        if self.minor_count:
            parts.append(f"{self.minor_count} minor")
        if self.cosmetic_count:
            parts.append(f"{self.cosmetic_count} cosmetic")
        if parts:
            return ", ".join(parts)
        return self.summary or "Verification complete"


def verify_web_project(workdir: Path, files: Dict[str, str], request: str = "") -> VerificationReport:
    report = VerificationReport()
    lowered_request = request.lower()

    html = files.get("index.html", "")
    css = files.get("styles.css", "")
    js = files.get("script.js", "")

    if not html:
        report.add(Issue("critical", "structure", "index.html is missing"))
    if not css:
        report.add(Issue("critical", "structure", "styles.css is missing (or empty)"))
    if not js:
        report.add(Issue("critical", "structure", "script.js is missing (or empty)"))

    if html:
        if "<!DOCTYPE html" not in html.upper() and "<!doctype html" not in html.lower():
            report.add(Issue("major", "html", "Missing DOCTYPE declaration"))
        if "</html>" not in html.lower():
            report.add(Issue("critical", "html", "Missing closing </html> tag"))
        if "<head>" not in html.lower():
            report.add(Issue("critical", "html", "Missing <head> section"))
        if "<body" not in html.lower():
            report.add(Issue("critical", "html", "Missing <body> section"))
        if "styles.css" not in html.lower():
            report.add(Issue("minor", "html", "styles.css not linked in HTML"))
        if "script.js" not in html.lower():
            report.add(Issue("minor", "html", "script.js not linked in HTML"))
        if '<meta name="viewport"' not in html.lower():
            report.add(Issue("minor", "html", "Missing viewport meta tag"))
        if "<nav" not in html.lower() and '<header' not in html.lower():
            report.add(Issue("minor", "html", "No navigation element found"))
        if "<main" not in html.lower() and '<section' not in html.lower():
            report.add(Issue("minor", "html", "No main content section found"))
        if "<footer" not in html.lower():
            report.add(Issue("cosmetic", "html", "No footer element"))

    if css:
        if len(css) < 50:
            report.add(Issue("critical", "css", "CSS is too minimal (< 50 chars)"))
        else:
            if ":root" not in css.lower() and "--" not in css:
                report.add(Issue("minor", "css", "No CSS custom properties / design tokens"))
            if "@media" not in css.lower():
                report.add(Issue("minor", "css", "No media queries for responsiveness"))
            if css.count("{") == 0:
                report.add(Issue("critical", "css", "No CSS rule blocks found"))
            if css.count("{") != css.count("}"):
                report.add(Issue("critical", "css", "Unbalanced CSS braces"))
            if "transition" not in css.lower() and "animation" not in css.lower() and "@keyframes" not in css:
                report.add(Issue("cosmetic", "css", "No transitions or animations"))
            if "hover" not in css.lower():
                report.add(Issue("cosmetic", "css", "No hover states"))

    if js:
        if len(js) < 50:
            report.add(Issue("critical", "js", "JavaScript is too minimal (< 50 chars)"))
        else:
            if "function " not in js and "=>" not in js and "const " not in js:
                report.add(Issue("major", "js", "No functions or event handlers found"))
            if "addEventListener" not in js and "onclick" not in js and "onload" not in js:
                report.add(Issue("major", "js", "No event listeners attached"))
            if "localStorage" not in js and "sessionStorage" not in js:
                if any(t in lowered_request for t in ("save", "persist", "remember", "storage", "data")):
                    report.add(Issue("major", "js", "localStorage expected but not found"))
            if "document." not in js:
                report.add(Issue("major", "js", "No DOM interaction detected"))

    report.passed = report.critical_count == 0 and report.major_count == 0
    report.score = max(0.0, 1.0 - (report.critical_count * 0.3 + report.major_count * 0.1 + report.minor_count * 0.05))
    report.summary = report.summarize()
    return report


def verify_expected_files(workdir: Path, required_files: List[str]) -> VerificationReport:
    report = VerificationReport()
    for f in required_files:
        path = Path(workdir) / f if not Path(f).is_absolute() else Path(f)
        if not path.exists():
            report.add(Issue("critical", "structure", f"Required file missing: {f}", file=f))
        elif path.stat().st_size < 20:
            report.add(Issue("critical", "structure", f"Required file is too small: {f}", file=f))
    report.passed = report.critical_count == 0
    report.summary = report.summarize()
    return report


def verify_backend_project(workdir: Path, files: Dict[str, str]) -> VerificationReport:
    report = VerificationReport()
    app = files.get("app.py", "")
    req = files.get("requirements.txt", "")

    if not app:
        report.add(Issue("critical", "structure", "app.py is missing"))
    if not req:
        report.add(Issue("major", "structure", "requirements.txt is missing"))

    if app:
        if "flask" not in app.lower() and "fastapi" not in app.lower() and "django" not in app.lower():
            report.add(Issue("major", "structure", "No web framework detected in app.py"))
        if "@app.route" not in app and "app = " not in app.lower() and "FastAPI" not in app:
            report.add(Issue("critical", "structure", "No route or app initialization detected"))

    report.passed = report.critical_count == 0
    report.summary = report.summarize()
    return report


def verify_physical_outputs(workdir: Path, created_paths: List[str]) -> VerificationReport:
    report = VerificationReport()
    for p in created_paths:
        path = Path(workdir) / p
        if not path.exists():
            report.add(Issue("critical", "structure", f"File not found on disk: {p}", file=p))
    report.passed = report.critical_count == 0
    report.summary = report.summarize()
    return report


def quality_review(workdir: Path, files: Dict[str, str]) -> VerificationReport:
    report = VerificationReport()

    html = files.get("index.html", "")
    css = files.get("styles.css", "")
    js = files.get("script.js", "")

    score = 0.0
    checks = 0

    if html:
        checks += 1
        if len(html) >= 300:
            score += 1
        if "<!DOCTYPE" in html:
            score += 1
        if "<nav" in html or '<header' in html:
            score += 1
        if "<main" in html or '<section' in html:
            score += 1
        if '<footer' in html:
            score += 1
        if 'aria-' in html.lower() or 'role=' in html.lower():
            score += 1
        total = checks * 6 if checks > 0 else 1
        html_score = score / total if total > 0 else 0

    css_score = 0.0
    if css:
        checks = 0
        score = 0
        checks += 1
        if len(css) >= 300:
            score += 1
        if ":root" in css or "--" in css:
            score += 1
        if "@media" in css:
            score += 1
        if "transition" in css.lower() or "animation" in css.lower() or "@keyframes" in css:
            score += 1
        if "hover" in css.lower():
            score += 1
        if "grid" in css.lower() or "flex" in css.lower():
            score += 1
        css_score = score / max(checks * 6, 1)

    js_score = 0.0
    if js:
        checks = 0
        score = 0
        checks += 1
        if len(js) >= 300:
            score += 1
        if "addEventListener" in js or "onclick" in js:
            score += 1
        if "localStorage" in js:
            score += 1
        if "function " in js or "=>" in js or "const " in js:
            score += 1
        if "class " in js or "export " in js:
            score += 1
        js_score = score / max(checks * 5, 1)

    report.score = (html_score + css_score + js_score) / 3.0 if 3 > 0 else 0

    if report.score < 0.4:
        report.add(Issue("major", "quality", f"Overall quality score {report.score:.2f} - needs improvement"))
    elif report.score < 0.6:
        report.add(Issue("minor", "quality", f"Quality score {report.score:.2f} - could be better"))
    else:
        report.add(Issue("cosmetic", "quality", f"Quality score {report.score:.2f} - acceptable"))

    report.passed = report.critical_count == 0 and report.score >= 0.3
    report.summary = f"Quality score: {report.score:.2f}, {report.summarize()}"
    return report
