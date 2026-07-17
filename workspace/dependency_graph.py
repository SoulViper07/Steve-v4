import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


_IMPORT_PATTERNS = {
    ".py": [
        re.compile(r"^\s*import\s+(\S+)", re.MULTILINE),
        re.compile(r"^\s*from\s+(\S+)\s+import", re.MULTILINE),
    ],
    ".js": [
        re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
        re.compile(r"""import\s+.*?\s+from\s+['"]([^'"]+)['"]"""),
        re.compile(r"""import\s+['"]([^'"]+)['"]"""),
    ],
    ".jsx": [
        re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
        re.compile(r"""import\s+.*?\s+from\s+['"]([^'"]+)['"]"""),
        re.compile(r"""import\s+['"]([^'"]+)['"]"""),
    ],
    ".ts": [
        re.compile(r"""import\s+.*?\s+from\s+['"]([^'"]+)['"]"""),
        re.compile(r"""import\s+['"]([^'"]+)['"]"""),
    ],
    ".tsx": [
        re.compile(r"""import\s+.*?\s+from\s+['"]([^'"]+)['"]"""),
        re.compile(r"""import\s+['"]([^'"]+)['"]"""),
    ],
    ".html": [
        re.compile(r"""<link\s+[^>]*href\s*=\s*['"]([^'"]+)['"]"""),
        re.compile(r"""<script\s+[^>]*src\s*=\s*['"]([^'"]+)['"]"""),
        re.compile(r"""<img\s+[^>]*src\s*=\s*['"]([^'"]+)['"]"""),
    ],
    ".css": [
        re.compile(r"""@import\s+['"]([^'"]+)['"]"""),
        re.compile(r"""url\s*\(\s*['"]?([^'")\s]+)['"]?\s*\)"""),
    ],
}


class FileDependencyGraph:
    def __init__(self):
        self._adjacency: Dict[str, Set[str]] = {}
        self._reverse: Dict[str, Set[str]] = {}

    def add_node(self, path: str):
        if path not in self._adjacency:
            self._adjacency[path] = set()
        if path not in self._reverse:
            self._reverse[path] = set()

    def add_dependency(self, source: str, target: str):
        self.add_node(source)
        self.add_node(target)
        self._adjacency[source].add(target)
        self._reverse[target].add(source)

    def dependencies(self, path: str) -> Set[str]:
        return self._adjacency.get(path, set())

    def dependents(self, path: str) -> Set[str]:
        return self._reverse.get(path, set())

    def all_paths(self) -> Set[str]:
        return set(self._adjacency.keys())

    def topological_sort(self) -> List[str]:
        visited: Set[str] = set()
        result: List[str] = []

        def dfs(node: str):
            if node in visited:
                return
            visited.add(node)
            for dep in self._adjacency.get(node, set()):
                dfs(dep)
            result.append(node)

        for node in self._adjacency:
            dfs(node)
        return result

    def is_cyclic(self) -> bool:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for dep in self._adjacency.get(node, set()):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for node in self._adjacency:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def analyze_file(self, path: str, content: str):
        ext = Path(path).suffix.lower()
        patterns = _IMPORT_PATTERNS.get(ext, [])
        self.add_node(path)
        dir_part = Path(path).parent.as_posix()
        for pattern in patterns:
            for match in pattern.finditer(content):
                dep = match.group(1)
                dep = dep.split("/")[-1].split(".")[0]
                if dep:
                    self.add_dependency(path, dep)

    def to_dict(self) -> dict:
        return {
            path: {
                "dependencies": sorted(deps),
                "dependents": sorted(self._reverse.get(path, set())),
            }
            for path, deps in self._adjacency.items()
        }

    def clear(self):
        self._adjacency.clear()
        self._reverse.clear()
