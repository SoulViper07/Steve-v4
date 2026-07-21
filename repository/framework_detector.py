import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field


FRAMEWORK_PATTERNS: Dict[str, Dict] = {
    "React": {
        "files": ["package.json"],
        "patterns": [r'"react"\s*:', r'"react-dom"\s*:'],
        "extensions": {".jsx", ".tsx"},
    },
    "Vue": {
        "files": ["package.json"],
        "patterns": [r'"vue"\s*:'],
        "extensions": {".vue"},
    },
    "Svelte": {
        "files": ["package.json"],
        "patterns": [r'"svelte"\s*:'],
        "extensions": {".svelte"},
    },
    "Angular": {
        "files": ["package.json", "angular.json"],
        "patterns": [r'"@angular/core"\s*:'],
    },
    "Next.js": {
        "files": ["package.json"],
        "patterns": [r'"next"\s*:'],
        "files_hint": ["next.config.js", "next.config.mjs", "next.config.ts"],
    },
    "Nuxt": {
        "files": ["package.json"],
        "patterns": [r'"nuxt"\s*:'],
    },
    "Express": {
        "files": ["package.json"],
        "patterns": [r'"express"\s*:'],
    },
    "Fastify": {
        "files": ["package.json"],
        "patterns": [r'"fastify"\s*:'],
    },
    "Django": {
        "files": ["requirements.txt", "Pipfile", "pyproject.toml", "setup.py", "setup.cfg"],
        "patterns": [r'django', r'Django'],
        "files_hint": ["manage.py", "django_project/", "wsgi.py"],
    },
    "Flask": {
        "files": ["requirements.txt", "Pipfile", "pyproject.toml", "setup.py", "setup.cfg"],
        "patterns": [r'flask', r'Flask'],
        "files_hint": ["app.py", "application.py", "wsgi.py"],
    },
    "FastAPI": {
        "files": ["requirements.txt", "Pipfile", "pyproject.toml", "setup.py", "setup.cfg"],
        "patterns": [r'fastapi', r'FastAPI'],
    },
    "Tailwind CSS": {
        "files": ["package.json", "tailwind.config.js", "tailwind.config.ts", "postcss.config.js"],
        "patterns": [r'"tailwindcss"\s*:'],
    },
    "Bootstrap": {
        "files": ["package.json", "requirements.txt"],
        "patterns": [r'"bootstrap"\s*:', r'bootstrap'],
    },
    "Spring Boot": {
        "files": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "patterns": [r'org\.springframework\.boot', r'spring-boot'],
    },
    "Ruby on Rails": {
        "files": ["Gemfile", "Gemfile.lock"],
        "patterns": [r'rails', r'"rails"'],
        "files_hint": ["config/routes.rb", "app/controllers/", "app/models/"],
    },
    "Laravel": {
        "files": ["composer.json"],
        "patterns": [r'"laravel/framework"\s*:'],
        "files_hint": ["artisan"],
    },
    "ASP.NET": {
        "files": ["*.csproj", "Startup.cs", "Program.cs"],
        "patterns": [r'Microsoft\.AspNetCore', r'Microsoft\.NET\.Sdk'],
    },
    "Electron": {
        "files": ["package.json"],
        "patterns": [r'"electron"\s*:'],
    },
    "React Native": {
        "files": ["package.json"],
        "patterns": [r'"react-native"\s*:'],
    },
    "Flutter": {
        "files": ["pubspec.yaml"],
        "patterns": [r'flutter:'],
        "extensions": {".dart"},
    },
    "Tauri": {
        "files": ["package.json", "Cargo.toml", "tauri.conf.json"],
        "patterns": [r'"@tauri-apps/api"', r'tauri'],
    },
    "Pyramid": {
        "files": ["setup.py", "setup.cfg", "requirements.txt"],
        "patterns": [r'pyramid'],
    },
    "Dash": {
        "files": ["requirements.txt", "setup.py"],
        "patterns": [r'dash'],
    },
    "Streamlit": {
        "files": ["requirements.txt"],
        "patterns": [r'streamlit'],
    },
    "Gatsby": {
        "files": ["package.json"],
        "patterns": [r'"gatsby"\s*:'],
    },
    "Remix": {
        "files": ["package.json", "remix.config.js"],
        "patterns": [r'"@remix-run/react"\s*:'],
    },
}


@dataclass
class FrameworkInfo:
    name: str
    confidence: float = 0.0
    detected_by: List[str] = field(default_factory=list)
    version: str = ""


class FrameworkDetector:
    def __init__(self):
        self._patterns = FRAMEWORK_PATTERNS

    def detect(self, file_paths: List[str], file_contents: Optional[Dict[str, str]] = None) -> Dict[str, FrameworkInfo]:
        results: Dict[str, FrameworkInfo] = {}
        file_set = {Path(fp).name for fp in file_paths}
        path_set = set(file_paths)

        for framework, rules in self._patterns.items():
            score = 0.0
            evidence: List[str] = []

            required_files = rules.get("files", [])
            for rf in required_files:
                if "*" in rf:
                    import fnmatch
                    matched = any(fnmatch.fnmatch(p, rf) for p in path_set)
                    if matched:
                        score += 0.3
                        evidence.append(f"Matched pattern: {rf}")
                elif rf in file_set:
                    score += 0.3
                    evidence.append(f"Found: {rf}")

            hint_files = rules.get("files_hint", [])
            for hf in hint_files:
                if hf in file_set or any(hf.rstrip("/") in p for p in file_paths):
                    score += 0.2
                    evidence.append(f"Found: {hf}")

            patterns = rules.get("patterns", [])
            if patterns and file_contents:
                for path, content in file_contents.items():
                    for pat in patterns:
                        if re.search(pat, content, re.IGNORECASE):
                            score += 0.2
                            evidence.append(f"Pattern '{pat}' matched in {Path(path).name}")

            extensions = rules.get("extensions", set())
            if extensions:
                found_exts = {Path(p).suffix.lower() for p in file_paths}
                overlap = extensions & found_exts
                if overlap:
                    score += 0.1 * len(overlap)
                    for ext in overlap:
                        evidence.append(f"Extension: {ext}")

            if score >= 0.3:
                confidence = min(score, 1.0)
                results[framework] = FrameworkInfo(
                    name=framework,
                    confidence=confidence,
                    detected_by=evidence[:5],
                )

        return dict(sorted(results.items(), key=lambda x: -x[1].confidence))

    @property
    def supported_frameworks(self) -> List[str]:
        return sorted(self._patterns.keys())
