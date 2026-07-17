from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple


class DependencyGraph:
    def __init__(self):
        self._nodes: Dict[str, Set[str]] = {}
        self._dependents: Dict[str, Set[str]] = defaultdict(set)

    def add_node(self, name: str, dependencies: Optional[List[str]] = None):
        if name not in self._nodes:
            self._nodes[name] = set()
        if dependencies:
            for dep in dependencies:
                if dep not in self._nodes:
                    self._nodes[dep] = set()
                self._nodes[name].add(dep)
                self._dependents[dep].add(name)

    def dependencies(self, name: str) -> Set[str]:
        return self._nodes.get(name, set())

    def dependents(self, name: str) -> Set[str]:
        return self._dependents.get(name, set())

    def all_nodes(self) -> Set[str]:
        return set(self._nodes.keys())

    def is_ready(self, name: str, completed: Set[str]) -> bool:
        deps = self._nodes.get(name, set())
        return deps.issubset(completed)

    def ready_nodes(self, completed: Set[str]) -> List[str]:
        return [
            n for n in self._nodes
            if n not in completed and self.is_ready(n, completed)
        ]

    def topological_sort(self) -> List[str]:
        in_degree: Dict[str, int] = {}
        for node in self._nodes:
            in_degree[node] = 0
        for node, deps in self._nodes.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[node] = in_degree.get(node, 0) + 1
        queue = deque([n for n, d in in_degree.items() if d == 0])
        result = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for dependent in self._dependents.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        return result

    def stages_by_level(self) -> List[List[str]]:
        levels = []
        completed: Set[str] = set()
        remaining = set(self._nodes.keys())
        while remaining:
            ready = [n for n in remaining if self.is_ready(n, completed)]
            if not ready:
                break
            levels.append(ready)
            completed.update(ready)
            remaining -= set(ready)
        if remaining:
            levels.append(list(remaining))
        return levels

    def is_cyclic(self) -> bool:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for dep in self._nodes.get(node, set()):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for node in self._nodes:
            if node not in visited:
                if dfs(node):
                    return True
        return False


class DependencyManager:
    def __init__(self):
        self._graph = DependencyGraph()

    @property
    def graph(self) -> DependencyGraph:
        return self._graph

    def build_stage_graph(self, stages: List[dict]):
        for stage in stages:
            name = stage["name"]
            deps = stage.get("dependencies", [])
            self._graph.add_node(name, deps)

    def execution_order(self) -> List[str]:
        return self._graph.topological_sort()

    def parallel_levels(self) -> List[List[str]]:
        return self._graph.stages_by_level()

    def validate(self) -> Tuple[bool, str]:
        if self._graph.is_cyclic():
            return False, "Dependency graph contains cycles"
        for level in self._graph.stages_by_level():
            if not level:
                return False, "Unreachable stages detected"
        return True, "Dependency graph is valid"
