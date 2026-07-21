import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ArchitectureType(str, Enum):
    MVC = "mvc"
    MONOLITH = "monolith"
    SPA = "spa"
    API = "api"
    CLI = "cli"
    MICROSERVICE = "microservice"
    LIBRARY = "library"
    PACKAGE = "package"
    PLUGIN = "plugin"
    UNKNOWN = "unknown"


ARCHITECTURE_PATTERNS: Dict[ArchitectureType, Dict] = {
    ArchitectureType.MVC: {
        "folders": {"controllers", "models", "views", "routes", "middleware"},
        "files": {"routes.php", "urls.py", "router.js"},
        "patterns": [
            r"class\s+\w+Controller",
            r"def\s+\w+\(self,\s*request",
            r"@route\(", r"@app\.route\(",
            r"router\.(get|post|put|delete)\(",
            r"path\(\s*['\"]",
        ],
    },
    ArchitectureType.SPA: {
        "folders": {"components", "pages", "views", "store", "state", "hooks", "containers"},
        "files": {"App.js", "App.jsx", "App.tsx", "App.vue", "main.js", "index.js"},
        "patterns": [
            r"import\s+\w+\s+from\s+['\"]react",
            r"import\s+\w+\s+from\s+['\"]vue",
            r"Vue\.createApp", r"ReactDOM\.render",
            r"new\s+Vue\(", r"createRouter",
            r"BrowserRouter", r"createStore", r"defineComponent",
        ],
        "extensions": {".vue", ".svelte", ".jsx", ".tsx"},
    },
    ArchitectureType.API: {
        "files": {"api.py", "api.js", "routes.py", "router.js", "urls.py"},
        "folders": {"api", "routes", "endpoints", "handlers"},
        "patterns": [
            r"@app\.(get|post|put|delete|patch)\(",
            r"router\.(get|post|put|delete|patch)\(",
            r"FastAPI\(\)", r"Flask\(__name__\)",
            r"class\s+\w+\(Resource\)",
            r"@api\.route\(", r"@viewset\.route",
            r"openapi", r"swagger", r"@router\.",
        ],
    },
    ArchitectureType.CLI: {
        "files": {"cli.py", "main.py", "agent.py", "cli.js", "index.js"},
        "patterns": [
            r"argparse", r"ArgumentParser",
            r"click\.(command|group|option|argument)",
            r"typer\.(run|command)",
            r"import\s+argparse",
            r"sys\.argv", r"commander",
            r"yargs", r"process\.argv",
            r"def\s+main\(\)",
            r'if\s+__name__\s*==\s*["\']__main__["\']',
        ],
    },
    ArchitectureType.MICROSERVICE: {
        "files": {"docker-compose.yml", "docker-compose.yaml", "service.py", "gateway.py"},
        "folders": {"services", "gateway", "deploy", "k8s", "kubernetes"},
        "patterns": [
            r"docker-compose", r"FROM\s+\w+:\w+",
            r"services:", r"microservice",
            r"eureka", r"consul", r"service\s+discovery",
            r"message\s+queue", r"rabbitmq", r"kafka",
            r"grpc", r"protobuf",
        ],
    },
    ArchitectureType.LIBRARY: {
        "files": {"setup.py", "setup.cfg", "pyproject.toml", "package.json"},
        "patterns": [
            r"setup\(name\s*=",
            r'"name"\s*:\s*"@',
            r"packages\s*=",
            r"entry_points\s*=",
            r'"main"\s*:',
            r"module\.exports",
            r"export\s+default",
        ],
    },
    ArchitectureType.PACKAGE: {
        "files": {"__init__.py", "setup.py", "pyproject.toml", "index.js", "package.json"},
        "folders": {"src", "dist", "lib"},
        "patterns": [
            r"__init__\.py",
            r'"main"\s*:',
            r"module\.exports",
            r"export\s*\{",
        ],
    },
    ArchitectureType.PLUGIN: {
        "files": {"plugin.py", "plugin.js", "manifest.json"},
        "folders": {"plugins", "extensions", "addons"},
        "patterns": [
            r"class\s+\w+Plugin",
            r"register\(", r"hooks\s*=",
            r"manifest\.json",
            r'"type"\s*:\s*"plugin"',
        ],
    },
    ArchitectureType.MONOLITH: {
        "folders": {"app", "src", "lib", "public"},
        "patterns": [
            r"from\s+app\s+import",
            r"from\s+src\s+import",
            r"index\.html",
        ],
    },
}


@dataclass
class ArchitectureSummary:
    primary_type: ArchitectureType = ArchitectureType.UNKNOWN
    secondary_types: List[ArchitectureType] = field(default_factory=list)
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    folder_structure: List[str] = field(default_factory=list)
    description: str = ""


class ArchitectureAnalyzer:
    def __init__(self):
        self._patterns = ARCHITECTURE_PATTERNS

    def analyze(self, file_paths: List[str], dir_paths: List[str],
                file_contents: Optional[Dict[str, str]] = None) -> ArchitectureSummary:
        scores: Dict[ArchitectureType, float] = {}
        evidence: Dict[ArchitectureType, List[str]] = {}
        file_set = {Path(p).name for p in file_paths}
        dir_set = set(dir_paths)

        for arch_type, rules in self._patterns.items():
            score = 0.0
            arch_evidence: List[str] = []
            folders = rules.get("folders", set())
            files = rules.get("files", set())
            patterns = rules.get("patterns", [])
            extensions = rules.get("extensions", set())

            for folder in folders:
                for d in dir_set:
                    if folder in d.lower().split("/"):
                        score += 0.15
                        arch_evidence.append(f"Folder match: {d}")

            for fname in files:
                if fname in file_set:
                    score += 0.15
                    arch_evidence.append(f"File match: {fname}")

            if patterns and file_contents:
                for fpath, content in file_contents.items():
                    for pat in patterns:
                        if re.search(pat, content):
                            score += 0.1
                            arch_evidence.append(f"Pattern '{pat}' in {Path(fpath).name}")

            if extensions:
                found_exts = {Path(p).suffix.lower() for p in file_paths}
                overlap = extensions & found_exts
                if overlap:
                    score += 0.1 * len(overlap)
                    for ext in overlap:
                        arch_evidence.append(f"Extension: {ext}")

            if score > 0:
                scores[arch_type] = min(score, 1.0)
                evidence[arch_type] = arch_evidence[:5]

        if not scores:
            return ArchitectureSummary()

        sorted_types = sorted(scores.items(), key=lambda x: -x[1])
        primary = sorted_types[0][0]
        confidence = sorted_types[0][1]
        secondary = [t for t, s in sorted_types[1:] if s >= 0.3]

        components = self._detect_components(file_paths, dir_paths)
        folder_structure = self._extract_structure(dir_paths)

        descriptions = {
            ArchitectureType.MVC: f"MVC framework with {len(components)} components",
            ArchitectureType.SPA: f"Single-page application with {len(components)} components",
            ArchitectureType.API: f"API service with {len(components)} endpoints/handlers",
            ArchitectureType.CLI: f"Command-line interface application",
            ArchitectureType.MICROSERVICE: f"Microservice architecture with {len(components)} services",
            ArchitectureType.LIBRARY: f"Shared library with {len(components)} modules",
            ArchitectureType.PACKAGE: f"Distributable package",
            ArchitectureType.PLUGIN: f"Plugin/extension system",
            ArchitectureType.MONOLITH: f"Monolithic application with {len(components)} modules",
            ArchitectureType.UNKNOWN: "Unknown architecture",
        }

        return ArchitectureSummary(
            primary_type=primary,
            secondary_types=secondary,
            confidence=confidence,
            evidence=evidence.get(primary, []),
            components=components,
            folder_structure=folder_structure,
            description=descriptions.get(primary, ""),
        )

    def _detect_components(self, file_paths: List[str], dir_paths: List[str]) -> List[str]:
        components: List[str] = []
        top_dirs = set()
        for d in dir_paths:
            parts = d.replace("\\", "/").split("/")
            if parts:
                top_dirs.add(parts[0])
        for d in sorted(top_dirs):
            if d not in (".steve", ".git", "__pycache__", "node_modules"):
                components.append(d)
        return components

    def _extract_structure(self, dir_paths: List[str]) -> List[str]:
        return sorted(set(
            "/".join(d.replace("\\", "/").split("/")[:2]) for d in dir_paths
        ))
