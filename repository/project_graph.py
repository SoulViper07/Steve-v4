from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GraphNode:
    id: str
    name: str
    kind: str  # "file", "folder", "symbol", "dependency"
    path: str = ""
    size: int = 0
    language: str = ""
    children: List[str] = field(default_factory=list)
    parent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    relationship: str  # "contains", "imports", "depends_on", "extends", "implements", "references"
    weight: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProjectGraph:
    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_node(self, node: GraphNode) -> bool:
        if node.id in self._nodes:
            return False
        self._nodes[node.id] = node
        return True

    def add_edge(self, edge: GraphEdge) -> bool:
        if edge.source not in self._nodes or edge.target not in self._nodes:
            return False
        self._edges.append(edge)
        return True

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self._nodes.get(node_id)

    def get_children(self, parent_id: str) -> List[GraphNode]:
        parent = self._nodes.get(parent_id)
        if not parent:
            return []
        return [self._nodes[cid] for cid in parent.children if cid in self._nodes]

    def get_edges(self, node_id: Optional[str] = None) -> List[GraphEdge]:
        if node_id:
            return [e for e in self._edges if e.source == node_id or e.target == node_id]
        return self._edges

    def get_incoming_edges(self, node_id: str) -> List[GraphEdge]:
        return [e for e in self._edges if e.target == node_id]

    def get_outgoing_edges(self, node_id: str) -> List[GraphEdge]:
        return [e for e in self._edges if e.source == node_id]

    def find_path(self, source_id: str, target_id: str) -> List[str]:
        visited: Set[str] = set()
        queue: List[List[str]] = [[source_id]]

        while queue:
            path = queue.pop(0)
            node_id = path[-1]
            if node_id == target_id:
                return path
            if node_id not in visited:
                visited.add(node_id)
                for edge in self.get_outgoing_edges(node_id):
                    if edge.target not in visited:
                        queue.append(path + [edge.target])
        return []

    def find_connected_components(self) -> List[List[str]]:
        visited: Set[str] = set()
        components: List[List[str]] = []

        for node_id in self._nodes:
            if node_id not in visited:
                component = []
                queue = [node_id]
                while queue:
                    current = queue.pop(0)
                    if current not in visited:
                        visited.add(current)
                        component.append(current)
                        for edge in self.get_edges(current):
                            neighbor = edge.source if edge.target == current else edge.target
                            if neighbor not in visited:
                                queue.append(neighbor)
                components.append(component)

        return components

    def build_from_scan(self, file_paths: List[str], dir_paths: List[str],
                        dependencies: Optional[Dict[str, List[str]]] = None):
        self._nodes.clear()
        self._edges.clear()

        root_id = "."
        self.add_node(GraphNode(id=root_id, name=".", kind="folder", path="."))

        for d in sorted(dir_paths):
            node_id = d.replace("\\", "/")
            parts = node_id.split("/")
            name = parts[-1]
            parent_id = "/".join(parts[:-1]) if len(parts) > 1 else root_id

            self.add_node(GraphNode(id=node_id, name=name, kind="folder", path=node_id, parent=parent_id))
            if parent_node := self._nodes.get(parent_id):
                if node_id not in parent_node.children:
                    parent_node.children.append(node_id)
                self.add_edge(GraphEdge(source=parent_id, target=node_id, relationship="contains"))

        for f in file_paths:
            node_id = f.replace("\\", "/")
            parts = node_id.split("/")
            name = parts[-1]
            parent_id = "/".join(parts[:-1]) if len(parts) > 1 else root_id

            ext = Path(name).suffix.lower()
            lang_map = {
                ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
                ".ts": "TypeScript", ".tsx": "TypeScript",
                ".html": "HTML", ".css": "CSS",
                ".json": "JSON", ".md": "Markdown",
            }

            self.add_node(GraphNode(
                id=node_id, name=name, kind="file",
                path=node_id, language=lang_map.get(ext, ""),
                parent=parent_id,
            ))
            if parent_node := self._nodes.get(parent_id):
                if node_id not in parent_node.children:
                    parent_node.children.append(node_id)
                self.add_edge(GraphEdge(source=parent_id, target=node_id, relationship="contains"))

        if dependencies:
            for source, targets in dependencies.items():
                source_id = source.replace("\\", "/")
                for target in targets:
                    target_id = target.replace("\\", "/")
                    self.add_edge(GraphEdge(
                        source=source_id, target=target_id,
                        relationship="depends_on",
                    ))

    @property
    def files(self) -> List[GraphNode]:
        return [n for n in self._nodes.values() if n.kind == "file"]

    @property
    def folders(self) -> List[GraphNode]:
        return [n for n in self._nodes.values() if n.kind == "folder"]

    @property
    def total_nodes(self) -> int:
        return len(self._nodes)

    @property
    def total_edges(self) -> int:
        return len(self._edges)

    def to_dict(self) -> Dict:
        return {
            "nodes": {nid: {"name": n.name, "kind": n.kind, "path": n.path, "language": n.language, "children": n.children}
                      for nid, n in self._nodes.items()},
            "edges": [{"source": e.source, "target": e.target, "relationship": e.relationship} for e in self._edges],
            "stats": {"nodes": self.total_nodes, "files": len(self.files), "folders": len(self.folders), "edges": self.total_edges},
        }

    def clear(self):
        self._nodes.clear()
        self._edges.clear()
