import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from .repository_scanner import RepositoryScanner, ScanResult
from .project_graph import ProjectGraph
from .symbol_index import SymbolIndex, SymbolKind, SymbolEntry
from .dependency_analyzer import DependencyAnalyzer
from .language_detector import LanguageDetector
from .framework_detector import FrameworkDetector, FrameworkInfo
from .architecture_analyzer import ArchitectureAnalyzer, ArchitectureSummary


@dataclass
class RepositoryContext:
    scanned_at: str = ""
    total_files: int = 0
    total_dirs: int = 0
    total_symbols: int = 0
    languages: Dict[str, Any] = field(default_factory=dict)
    frameworks: Dict[str, Any] = field(default_factory=dict)
    architecture: Optional[ArchitectureSummary] = None
    entry_points: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    assets: List[str] = field(default_factory=list)
    environment_files: List[str] = field(default_factory=list)
    package_manager_files: List[str] = field(default_factory=list)
    dependency_count: int = 0
    duplicate_functions: int = 0
    duration_ms: float = 0.0
    summary: str = ""


class RepositoryManager:
    def __init__(self, root_path: str):
        self._root = Path(root_path).resolve()
        self._scanner = RepositoryScanner()
        self._graph = ProjectGraph()
        self._symbol_index = SymbolIndex()
        self._lang_detector = LanguageDetector()
        self._fw_detector = FrameworkDetector()
        self._arch_analyzer = ArchitectureAnalyzer()
        self._dep_analyzer = DependencyAnalyzer(str(self._root))
        self._scan_result: Optional[ScanResult] = None
        self._context: Optional[RepositoryContext] = None
        self._is_indexed = False

    @property
    def is_indexed(self) -> bool:
        return self._is_indexed

    @property
    def context(self) -> Optional[RepositoryContext]:
        return self._context

    @property
    def graph(self) -> ProjectGraph:
        return self._graph

    @property
    def symbol_index(self) -> SymbolIndex:
        return self._symbol_index

    @property
    def dependency_analyzer(self) -> DependencyAnalyzer:
        return self._dep_analyzer

    @property
    def scan_result(self) -> Optional[ScanResult]:
        return self._scan_result

    def index(self) -> RepositoryContext:
        start = time.time()

        result = self._scanner.scan(str(self._root))
        self._scan_result = result

        self._graph.build_from_scan(
            result.file_paths, result.dir_paths,
        )

        for f in result.file_paths:
            try:
                fp = self._root / f
                if fp.exists() and fp.is_file():
                    content = fp.read_text(encoding="utf-8", errors="replace")
                    self._symbol_index.index_file(str(fp), content)
                    self._dep_analyzer.analyze_file(str(fp), content)
            except Exception:
                pass

        file_contents = {}
        for f in result.file_paths[:200]:
            try:
                fp = self._root / f
                if fp.exists() and fp.is_file():
                    file_contents[f] = fp.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

        languages = self._lang_detector.analyze_directory(result.file_paths)
        frameworks = self._fw_detector.detect(result.file_paths, file_contents)
        architecture = self._arch_analyzer.analyze(
            result.file_paths, result.dir_paths, file_contents,
        )

        dup_funcs = self._symbol_index.find_duplicate_functions()

        ctx = RepositoryContext(
            scanned_at=datetime.now().isoformat(),
            total_files=result.total_files,
            total_dirs=result.total_dirs,
            total_symbols=self._symbol_index.total_symbols,
            languages={name: {"file_count": info.file_count, "percentage": info.percentage}
                       for name, info in languages.items()},
            frameworks={name: {"confidence": info.confidence, "detected_by": info.detected_by}
                        for name, info in frameworks.items()},
            architecture=architecture,
            entry_points=result.entry_points,
            config_files=result.config_files,
            test_files=result.test_files,
            assets=result.asset_files,
            environment_files=result.environment_files,
            package_manager_files=result.package_manager_files,
            dependency_count=len(self._dep_analyzer.get_all_targets()),
            duplicate_functions=len(dup_funcs),
            duration_ms=round((time.time() - start) * 1000, 2),
        )

        summary_parts = []
        if languages:
            top_langs = sorted(languages.items(), key=lambda x: -x[1].percentage)[:3]
            lang_str = ", ".join(f"{name} ({info.percentage}%)" for name, info in top_langs)
            summary_parts.append(f"Languages: {lang_str}")
        if frameworks:
            top_fws = sorted(frameworks.items(), key=lambda x: -x[1].confidence)[:3]
            fw_str = ", ".join(name for name, _ in top_fws)
            summary_parts.append(f"Frameworks: {fw_str}")
        if architecture and architecture.primary_type.value != "unknown":
            summary_parts.append(f"Architecture: {architecture.primary_type.value}")
        summary_parts.append(f"Symbols: {ctx.total_symbols}")
        ctx.summary = " | ".join(summary_parts)

        self._context = ctx
        self._is_indexed = True
        return ctx

    def reindex(self) -> RepositoryContext:
        self._graph.clear()
        self._symbol_index.clear()
        self._dep_analyzer.clear()
        self._is_indexed = False
        return self.index()

    def search(self, query: str) -> Dict[str, Any]:
        q = query.lower()
        results = {
            "symbols": [],
            "files": [],
            "functions": [],
            "classes": [],
        }

        symbols = self._symbol_index.find_symbols_by_name(query)
        for sym in symbols:
            entry = {
                "name": sym.name,
                "kind": sym.kind.value,
                "file": sym.file_path,
                "line": sym.line,
                "parent": sym.parent,
            }
            results["symbols"].append(entry)
            if sym.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
                results["functions"].append(entry)
            if sym.kind == SymbolKind.CLASS:
                results["classes"].append(entry)

        if self._scan_result:
            for f in self._scan_result.file_paths:
                if q in f.lower():
                    results["files"].append(f)

        return results

    def find_api_routes(self) -> List[Dict[str, Any]]:
        routes = []
        if not self._scan_result:
            return routes

        for f in self._scan_result.file_paths:
            try:
                fp = self._root / f
                if not fp.exists():
                    continue
                content = fp.read_text(encoding="utf-8", errors="replace")
                ext = fp.suffix.lower()
                for i, line in enumerate(content.splitlines(), 1):
                    if ext == ".py":
                        match = re.search(r'@(?:app|router|api)\.(get|post|put|delete|patch)\([\'"]([^\'"]+)', line)
                    elif ext in (".js", ".jsx", ".ts", ".tsx"):
                        match = re.search(r'\.(get|post|put|delete|patch)\([\'"]([^\'"]+)', line)
                    else:
                        match = None
                    if match:
                        routes.append({
                            "method": match.group(1).upper(),
                            "path": match.group(2),
                            "file": f,
                            "line": i,
                        })
            except Exception:
                pass
        return routes

    def find_unused_code(self) -> List[Dict[str, Any]]:
        unused = self._dep_analyzer.find_unused_imports(
            self._scan_result.file_paths if self._scan_result else []
        )
        return unused

    def summary_dict(self) -> Dict[str, Any]:
        if not self._context:
            return {"indexed": False}
        return {
            "indexed": self._is_indexed,
            "total_files": self._context.total_files,
            "total_dirs": self._context.total_dirs,
            "total_symbols": self._context.total_symbols,
            "languages": list(self._context.languages.keys()),
            "frameworks": list(self._context.frameworks.keys()),
            "architecture": self._context.architecture.primary_type.value if self._context.architecture else "unknown",
            "entry_points": len(self._context.entry_points),
            "config_files": len(self._context.config_files),
            "test_files": len(self._context.test_files),
            "dependencies": self._context.dependency_count,
            "duplicate_functions": self._context.duplicate_functions,
            "duration_ms": self._context.duration_ms,
            "summary": self._context.summary,
        }


import re


__all__ = ["RepositoryManager", "RepositoryContext"]
