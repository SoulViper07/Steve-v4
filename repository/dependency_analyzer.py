import re
import ast
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class DependencyType(str, Enum):
    IMPORT = "import"
    EXPORT = "export"
    REQUIRE = "require"
    STATIC_ASSET = "static_asset"
    DYNAMIC = "dynamic"
    EXTERNAL = "external"
    INTERNAL = "internal"


@dataclass
class Dependency:
    source: str
    target: str
    type: DependencyType = DependencyType.IMPORT
    line: int = 0
    is_external: bool = False
    resolved_path: str = ""


class DependencyAnalyzer:
    def __init__(self, root_path: str):
        self._root = Path(root_path).resolve()
        self._dependencies: Dict[str, List[Dependency]] = {}

    def analyze_file(self, file_path: str, content: Optional[str] = None) -> List[Dependency]:
        path = Path(file_path)
        ext = path.suffix.lower()
        deps: List[Dependency] = []

        if content is None:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                return deps

        if ext == ".py":
            deps = self._analyze_python(file_path, content)
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            deps = self._analyze_jsts(file_path, content)
        elif ext == ".html":
            deps = self._analyze_html(file_path, content)
        elif ext in (".css", ".scss", ".sass", ".less"):
            deps = self._analyze_css(file_path, content)
        elif ext == ".vue":
            deps = self._analyze_vue(file_path, content)

        self._dependencies[file_path] = deps
        return deps

    def _resolve_module_path(self, source_file: str, module: str) -> Tuple[str, bool]:
        if module.startswith("."):
            source_dir = Path(source_file).parent
            parts = module.split("/")
            target = (source_dir / "/".join(parts)).resolve()
            for ext in (".py", ".js", ".jsx", ".ts", ".tsx", ""):
                candidate = target.with_suffix(ext) if ext else target
                if candidate.exists():
                    return str(candidate.relative_to(self._root)), True
            return module, False
        return module, True

    def _analyze_python(self, file_path: str, content: str) -> List[Dependency]:
        deps: List[Dependency] = []
        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                std_import = re.match(r"^\s*import\s+(\S+)", line)
                if std_import:
                    name = std_import.group(1).split(" as ")[0]
                    resolved, external = self._resolve_module_path(file_path, name)
                    deps.append(Dependency(
                        source=file_path, target=name, type=DependencyType.IMPORT,
                        line=i, is_external=external, resolved_path=resolved,
                    ))
                    continue
                from_import = re.match(r"^\s*from\s+(\S+)\s+import", line)
                if from_import:
                    resolved, external = self._resolve_module_path(file_path, from_import.group(1))
                    deps.append(Dependency(
                        source=file_path, target=from_import.group(1), type=DependencyType.IMPORT,
                        line=i, is_external=external, resolved_path=resolved,
                    ))
            return deps

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    resolved, external = self._resolve_module_path(file_path, alias.name)
                    deps.append(Dependency(
                        source=file_path, target=alias.name, type=DependencyType.IMPORT,
                        line=node.lineno or 0, is_external=external, resolved_path=resolved,
                    ))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                resolved, external = self._resolve_module_path(file_path, module)
                deps.append(Dependency(
                    source=file_path, target=module, type=DependencyType.IMPORT,
                    line=node.lineno or 0, is_external=external, resolved_path=resolved,
                ))

        return deps

    def _analyze_jsts(self, file_path: str, content: str) -> List[Dependency]:
        deps: List[Dependency] = []
        for i, line in enumerate(content.splitlines(), 1):
            import_match = re.match(r"^\s*import\s+(?:\{[^}]*\}|[^;{]+)\s+from\s+['\"](.+)['\"]", line)
            if import_match:
                target = import_match.group(1)
                is_external = not target.startswith(".")
                deps.append(Dependency(
                    source=file_path, target=target, type=DependencyType.IMPORT,
                    line=i, is_external=is_external,
                ))
                continue

            require_match = re.search(r"(?:const|let|var)\s+\w+\s*=\s*require\(['\"](.+)['\"]\)", line)
            if require_match:
                target = require_match.group(1)
                is_external = not target.startswith(".")
                deps.append(Dependency(
                    source=file_path, target=target, type=DependencyType.REQUIRE,
                    line=i, is_external=is_external,
                ))
                continue

            export_match = re.match(r"^\s*export\s+(?:\{[^}]*\}|[^;{]+)\s+from\s+['\"](.+)['\"]", line)
            if export_match:
                target = export_match.group(1)
                is_external = not target.startswith(".")
                deps.append(Dependency(
                    source=file_path, target=target, type=DependencyType.EXPORT,
                    line=i, is_external=is_external,
                ))

        return deps

    def _analyze_html(self, file_path: str, content: str) -> List[Dependency]:
        deps: List[Dependency] = []
        for i, line in enumerate(content.splitlines(), 1):
            script_match = re.search(r'<script[^>]*src=["\']([^"\']+)["\']', line)
            if script_match:
                deps.append(Dependency(
                    source=file_path, target=script_match.group(1),
                    type=DependencyType.STATIC_ASSET, line=i,
                ))
                continue
            link_match = re.search(r'<link[^>]*href=["\']([^"\']+)["\']', line)
            if link_match:
                deps.append(Dependency(
                    source=file_path, target=link_match.group(1),
                    type=DependencyType.STATIC_ASSET, line=i,
                ))
                continue
            img_match = re.search(r'<img[^>]*src=["\']([^"\']+)["\']', line)
            if img_match:
                deps.append(Dependency(
                    source=file_path, target=img_match.group(1),
                    type=DependencyType.STATIC_ASSET, line=i,
                ))
        return deps

    def _analyze_css(self, file_path: str, content: str) -> List[Dependency]:
        deps: List[Dependency] = []
        for i, line in enumerate(content.splitlines(), 1):
            import_match = re.search(r"@import\s+['\"](.+)['\"]", line)
            if import_match:
                deps.append(Dependency(
                    source=file_path, target=import_match.group(1),
                    type=DependencyType.IMPORT, line=i,
                ))
                continue
            url_match = re.search(r"url\(['\"]?(.+?)['\"]?\)", line)
            if url_match and not url_match.group(1).startswith("data:"):
                deps.append(Dependency(
                    source=file_path, target=url_match.group(1),
                    type=DependencyType.STATIC_ASSET, line=i,
                ))
        return deps

    def _analyze_vue(self, file_path: str, content: str) -> List[Dependency]:
        deps = self._analyze_html(file_path, content)
        deps.extend(self._analyze_jsts(file_path, content))
        return deps

    def get_dependencies(self, file_path: Optional[str] = None) -> Dict[str, List[Dependency]]:
        if file_path:
            return {file_path: self._dependencies.get(file_path, [])}
        return self._dependencies

    def get_all_targets(self) -> List[str]:
        targets: Set[str] = set()
        for deps in self._dependencies.values():
            for d in deps:
                targets.add(d.target)
        return sorted(targets)

    def find_unused_imports(self, all_files: List[str]) -> List[Dict]:
        unused: List[Dict] = []
        imported_symbols: Dict[str, List[Tuple[str, int]]] = {}

        for f in all_files:
            deps = self._dependencies.get(f, [])
            for d in deps:
                imported_symbols.setdefault(d.target, []).append((f, d.line))

        all_refs = set()
        for f in all_files:
            try:
                content = Path(self._root / f).read_text(encoding="utf-8", errors="replace")
                for sym in imported_symbols:
                    if sym in content and not any(content.strip().startswith("import") for _ in []):
                        all_refs.add(sym)
            except Exception:
                pass

        for target, locations in imported_symbols.items():
            if target not in all_refs:
                unused.append({"target": target, "locations": locations})
        return unused

    def clear(self):
        self._dependencies.clear()
