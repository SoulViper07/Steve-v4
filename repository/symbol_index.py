import re
import ast
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum


class SymbolKind(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    INTERFACE = "interface"
    TYPE = "type"
    MODULE = "module"
    EXPORT = "export"
    IMPORT = "import"
    DECORATOR = "decorator"
    PROPERTY = "property"
    ENUM = "enum"
    PARAMETER = "parameter"


@dataclass
class SymbolEntry:
    name: str
    kind: SymbolKind
    file_path: str
    line: int = 0
    column: int = 0
    end_line: int = 0
    parent: Optional[str] = None
    signature: str = ""
    docstring: str = ""
    modifiers: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)


class SymbolIndex:
    def __init__(self):
        self._symbols: Dict[str, List[SymbolEntry]] = {}
        self._global_symbols: Dict[str, SymbolEntry] = {}

    def index_file(self, file_path: str, content: Optional[str] = None) -> List[SymbolEntry]:
        path = Path(file_path)
        ext = path.suffix.lower()
        symbols: List[SymbolEntry] = []

        if content is None:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                return symbols

        if ext == ".py":
            symbols = self._index_python(file_path, content)
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            symbols = self._index_jsts(file_path, content, ext)
        elif ext == ".vue":
            symbols = self._index_jsts(file_path, content, ext)
        elif ext == ".html":
            symbols = self._index_html(file_path, content)
        elif ext in (".css", ".scss", ".sass", ".less"):
            symbols = self._index_css(file_path, content)

        self._symbols[file_path] = symbols
        for sym in symbols:
            self._global_symbols[f"{sym.file_path}:{sym.name}"] = sym

        return symbols

    def _index_python(self, file_path: str, content: str) -> List[SymbolEntry]:
        symbols: List[SymbolEntry] = []
        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            return self._index_python_regex(file_path, content)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                sym = SymbolEntry(
                    name=node.name,
                    kind=SymbolKind.FUNCTION,
                    file_path=file_path,
                    line=node.lineno or 0,
                    end_line=node.end_lineno or 0,
                    signature=f"def {node.name}(...)",
                    modifiers=["async"] if hasattr(node, "decorator_list") and any(
                        isinstance(d, ast.Name) and d.id == "staticmethod" for d in getattr(node, "decorator_list", [])
                    ) else [],
                )
                symbols.append(sym)

            elif isinstance(node, ast.AsyncFunctionDef):
                sym = SymbolEntry(
                    name=node.name,
                    kind=SymbolKind.FUNCTION,
                    file_path=file_path,
                    line=node.lineno or 0,
                    end_line=node.end_lineno or 0,
                    signature=f"async def {node.name}(...)",
                    modifiers=["async"],
                )
                symbols.append(sym)

            elif isinstance(node, ast.ClassDef):
                bases = ", ".join(
                    base.id if isinstance(base, ast.Name) else "?"
                    for base in node.bases if isinstance(base, ast.Name)
                )
                sym = SymbolEntry(
                    name=node.name,
                    kind=SymbolKind.CLASS,
                    file_path=file_path,
                    line=node.lineno or 0,
                    end_line=node.end_lineno or 0,
                    signature=f"class {node.name}({bases})" if bases else f"class {node.name}",
                )
                symbols.append(sym)

                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method = SymbolEntry(
                            name=item.name,
                            kind=SymbolKind.METHOD,
                            file_path=file_path,
                            line=item.lineno or 0,
                            end_line=item.end_lineno or 0,
                            parent=node.name,
                            signature=f"{'async ' if isinstance(item, ast.AsyncFunctionDef) else ''}def {item.name}(...)",
                        )
                        symbols.append(method)

            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        symbols.append(SymbolEntry(
                            name=target.id,
                            kind=SymbolKind.CONSTANT,
                            file_path=file_path,
                            line=node.lineno or 0,
                            column=target.col_offset or 0,
                        ))

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    symbols.append(SymbolEntry(
                        name=alias.name,
                        kind=SymbolKind.IMPORT,
                        file_path=file_path,
                        line=node.lineno or 0,
                    ))

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    symbols.append(SymbolEntry(
                        name=f"{module}.{alias.name}",
                        kind=SymbolKind.IMPORT,
                        file_path=file_path,
                        line=node.lineno or 0,
                    ))

        return symbols

    def _index_python_regex(self, file_path: str, content: str) -> List[SymbolEntry]:
        symbols: List[SymbolEntry] = []
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            class_match = re.match(r"^class\s+(\w+)", stripped)
            if class_match:
                symbols.append(SymbolEntry(
                    name=class_match.group(1),
                    kind=SymbolKind.CLASS,
                    file_path=file_path,
                    line=i,
                ))
                continue
            func_match = re.match(r"^(?:async\s+)?def\s+(\w+)\s*\(", stripped)
            if func_match:
                parent = ""
                for s in reversed(symbols):
                    if s.kind == SymbolKind.CLASS and s.end_line >= i:
                        parent = s.name
                        break
                symbols.append(SymbolEntry(
                    name=func_match.group(1),
                    kind=SymbolKind.METHOD if parent else SymbolKind.FUNCTION,
                    file_path=file_path,
                    line=i,
                    parent=parent or None,
                ))
                continue
            const_match = re.match(r"^([A-Z][A-Z0-9_]+)\s*=", stripped)
            if const_match:
                symbols.append(SymbolEntry(
                    name=const_match.group(1),
                    kind=SymbolKind.CONSTANT,
                    file_path=file_path,
                    line=i,
                ))
        return symbols

    def _index_jsts(self, file_path: str, content: str, ext: str) -> List[SymbolEntry]:
        symbols: List[SymbolEntry] = []
        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            class_match = re.match(r"^(?:export\s+)?(?:default\s+)?class\s+(\w+)", stripped)
            if class_match:
                symbols.append(SymbolEntry(
                    name=class_match.group(1),
                    kind=SymbolKind.CLASS,
                    file_path=file_path,
                    line=i,
                ))
                continue

            func_match = re.match(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*\(", stripped)
            if func_match:
                symbols.append(SymbolEntry(
                    name=func_match.group(1),
                    kind=SymbolKind.FUNCTION,
                    file_path=file_path,
                    line=i,
                ))
                continue

            arrow_match = re.match(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(?.*\)?\s*=>", stripped)
            if arrow_match:
                symbols.append(SymbolEntry(
                    name=arrow_match.group(1),
                    kind=SymbolKind.FUNCTION,
                    file_path=file_path,
                    line=i,
                ))
                continue

            const_match = re.match(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=", stripped)
            if const_match:
                kind = SymbolKind.CONSTANT if const_match.group(1).isupper() else SymbolKind.VARIABLE
                symbols.append(SymbolEntry(
                    name=const_match.group(1),
                    kind=kind,
                    file_path=file_path,
                    line=i,
                ))
                continue

            export_match = re.match(r"^export\s+(?:default\s+)?(?:function|class|const|let|var|interface|type)\s+(\w+)", stripped)
            if export_match:
                symbols.append(SymbolEntry(
                    name=export_match.group(1),
                    kind=SymbolKind.EXPORT,
                    file_path=file_path,
                    line=i,
                ))
                continue

            interface_match = re.match(r"^(?:export\s+)?interface\s+(\w+)", stripped) if ext in (".ts", ".tsx") else None
            if interface_match:
                symbols.append(SymbolEntry(
                    name=interface_match.group(1),
                    kind=SymbolKind.INTERFACE,
                    file_path=file_path,
                    line=i,
                ))
                continue

            type_match = re.match(r"^(?:export\s+)?type\s+(\w+)", stripped) if ext in (".ts", ".tsx") else None
            if type_match:
                symbols.append(SymbolEntry(
                    name=type_match.group(1),
                    kind=SymbolKind.TYPE,
                    file_path=file_path,
                    line=i,
                ))
                continue

            import_match = re.match(r"^(?:import\s+.*\s+from\s+['\"](.+)['\"]|const\s+\w+\s*=\s*require\(['\"](.+)['\"]\))", stripped)
            if import_match:
                name = import_match.group(1) or import_match.group(2)
                symbols.append(SymbolEntry(
                    name=name or "",
                    kind=SymbolKind.IMPORT,
                    file_path=file_path,
                    line=i,
                ))

        return symbols

    def _index_html(self, file_path: str, content: str) -> List[SymbolEntry]:
        symbols: List[SymbolEntry] = []
        for i, line in enumerate(content.splitlines(), 1):
            id_match = re.search(r'id="([^"]+)"', line)
            if id_match:
                symbols.append(SymbolEntry(
                    name=id_match.group(1),
                    kind=SymbolKind.VARIABLE,
                    file_path=file_path,
                    line=i,
                ))
            class_match = re.search(r'class="([^"]+)"', line)
            if class_match:
                for cls in class_match.group(1).split():
                    symbols.append(SymbolEntry(
                        name=cls,
                        kind=SymbolKind.VARIABLE,
                        file_path=file_path,
                        line=i,
                    ))
        return symbols

    def _index_css(self, file_path: str, content: str) -> List[SymbolEntry]:
        symbols: List[SymbolEntry] = []
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            class_sel = re.match(r"^\.([\w-]+)\s*\{", stripped)
            if class_sel:
                symbols.append(SymbolEntry(
                    name=class_sel.group(1),
                    kind=SymbolKind.VARIABLE,
                    file_path=file_path,
                    line=i,
                ))
                continue
            id_sel = re.match(r"^#([\w-]+)\s*\{", stripped)
            if id_sel:
                symbols.append(SymbolEntry(
                    name=id_sel.group(1),
                    kind=SymbolKind.VARIABLE,
                    file_path=file_path,
                    line=i,
                ))
                continue
            var_decl = re.match(r"^--([\w-]+)\s*:", stripped)
            if var_decl:
                symbols.append(SymbolEntry(
                    name=var_decl.group(1),
                    kind=SymbolKind.VARIABLE,
                    file_path=file_path,
                    line=i,
                ))
        return symbols

    def get_symbols(self, file_path: Optional[str] = None) -> List[SymbolEntry]:
        if file_path:
            return self._symbols.get(file_path, [])
        result = []
        for symbols in self._symbols.values():
            result.extend(symbols)
        return result

    def find_symbol(self, name: str) -> Optional[SymbolEntry]:
        for path, symbols in self._symbols.items():
            for sym in symbols:
                if sym.name == name:
                    return sym
        return None

    def find_symbols_by_kind(self, kind: SymbolKind) -> List[SymbolEntry]:
        result = []
        for symbols in self._symbols.values():
            for sym in symbols:
                if sym.kind == kind:
                    result.append(sym)
        return result

    def find_symbols_by_name(self, query: str) -> List[SymbolEntry]:
        q = query.lower()
        result = []
        for symbols in self._symbols.values():
            for sym in symbols:
                if q in sym.name.lower():
                    result.append(sym)
        return result

    def find_duplicate_functions(self) -> List[Dict[str, Any]]:
        funcs: Dict[str, List[SymbolEntry]] = {}
        for symbols in self._symbols.values():
            for sym in symbols:
                if sym.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
                    funcs.setdefault(sym.name, []).append(sym)
        return [
            {"name": name, "count": len(entries), "locations": [(e.file_path, e.line) for e in entries]}
            for name, entries in funcs.items() if len(entries) > 1
        ]

    @property
    def total_symbols(self) -> int:
        count = 0
        for symbols in self._symbols.values():
            count += len(symbols)
        return count

    def clear(self):
        self._symbols.clear()
        self._global_symbols.clear()
