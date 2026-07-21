import tempfile
from pathlib import Path

from repository.language_detector import LanguageDetector
from repository.framework_detector import FrameworkDetector
from repository.repository_scanner import RepositoryScanner
from repository.symbol_index import SymbolIndex, SymbolKind
from repository.dependency_analyzer import DependencyAnalyzer, DependencyType
from repository.project_graph import ProjectGraph, GraphNode, GraphEdge
from repository.architecture_analyzer import ArchitectureAnalyzer, ArchitectureType


class TestLanguageDetector:
    def setup_method(self):
        self.detector = LanguageDetector()

    def test_detect_python(self):
        assert self.detector.detect("file.py") == "Python"
        assert self.detector.detect("path/to/module.py") == "Python"

    def test_detect_javascript(self):
        assert self.detector.detect("file.js") == "JavaScript"
        assert self.detector.detect("file.jsx") == "JavaScript (React JSX)"

    def test_detect_typescript(self):
        assert self.detector.detect("file.ts") == "TypeScript"
        assert self.detector.detect("file.tsx") == "TypeScript (React TSX)"

    def test_detect_html(self):
        assert self.detector.detect("index.html") == "HTML"

    def test_detect_css(self):
        assert self.detector.detect("style.css") == "CSS"

    def test_detect_unknown(self):
        assert self.detector.detect("file.xyz") is None

    def test_detect_from_path_dockerfile(self):
        assert self.detector.detect_from_path("Dockerfile") == "Dockerfile"

    def test_detect_from_path_makefile(self):
        assert self.detector.detect_from_path("Makefile") == "Makefile"

    def test_analyze_directory(self):
        files = ["a.py", "b.py", "c.js", "d.ts", "e.html"]
        result = self.detector.analyze_directory(files)
        assert "Python" in result
        assert result["Python"].file_count == 2
        assert result["Python"].percentage == 40.0
        assert "JavaScript" in result
        assert result["JavaScript"].file_count == 1
        assert result["JavaScript"].percentage == 20.0

    def test_supported_languages(self):
        langs = self.detector.supported_languages
        assert "Python" in langs
        assert "JavaScript" in langs
        assert "TypeScript" in langs


class TestFrameworkDetector:
    def setup_method(self):
        self.detector = FrameworkDetector()

    def test_detect_react(self):
        files = ["package.json", "App.jsx", "Button.tsx"]
        contents = {"package.json": '{"dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"}}'}
        result = self.detector.detect(files, contents)
        assert "React" in result
        assert result["React"].confidence > 0.3

    def test_detect_django(self):
        files = ["manage.py", "settings.py", "requirements.txt"]
        contents = {"requirements.txt": "django==4.2.0\npsycopg2"}
        result = self.detector.detect(files, contents)
        assert "Django" in result

    def test_detect_flask(self):
        files = ["app.py", "requirements.txt"]
        contents = {"requirements.txt": "flask==2.3.0"}
        result = self.detector.detect(files, contents)
        assert "Flask" in result

    def test_detect_fastapi(self):
        files = ["main.py", "requirements.txt"]
        contents = {"requirements.txt": "fastapi==0.100.0"}
        result = self.detector.detect(files, contents)
        assert "FastAPI" in result

    def test_supported_frameworks(self):
        fws = self.detector.supported_frameworks
        assert "React" in fws
        assert "Django" in fws
        assert "Flask" in fws

    def test_no_framework_detected(self):
        files = ["random.txt"]
        result = self.detector.detect(files)
        assert len(result) == 0


class TestRepositoryScanner:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.scanner = RepositoryScanner()

    def _create_file(self, path: str, content: str = ""):
        full = self.tmpdir / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        return full

    def test_scan_empty_directory(self):
        result = self.scanner.scan(str(self.tmpdir))
        assert result.total_files == 0
        assert result.total_dirs == 0

    def test_scan_basic_files(self):
        self._create_file("main.py", "print('hello')")
        self._create_file("style.css", "body { color: red; }")
        self._create_file("index.html", "<html></html>")
        result = self.scanner.scan(str(self.tmpdir))
        assert result.total_files == 3
        assert "main.py" in result.file_paths

    def test_scan_entry_points(self):
        self._create_file("main.py")
        self._create_file("app.py")
        self._create_file("helper.py")
        result = self.scanner.scan(str(self.tmpdir))
        assert "main.py" in result.entry_points
        assert "app.py" in result.entry_points

    def test_scan_config_files(self):
        self._create_file("package.json", "{}")
        self._create_file("requirements.txt", "")
        result = self.scanner.scan(str(self.tmpdir))
        assert "package.json" in result.config_files
        assert "requirements.txt" in result.config_files

    def test_scan_test_files(self):
        self._create_file("test_main.py")
        self._create_file("main_spec.js")
        result = self.scanner.scan(str(self.tmpdir))
        assert "test_main.py" in result.test_files
        assert "main_spec.js" in result.test_files

    def test_scan_environment_files(self):
        self._create_file(".env", "SECRET=key")
        self._create_file(".env.example", "")
        result = self.scanner.scan(str(self.tmpdir))
        assert ".env" in result.environment_files
        assert ".env.example" in result.environment_files

    def test_scan_asset_files(self):
        self._create_file("data.xml", "<root></root>")
        self._create_file("readme.md", "# Readme")
        result = self.scanner.scan(str(self.tmpdir))
        assert "data.xml" in result.asset_files
        assert "readme.md" in result.asset_files

    def test_scan_excludes_git(self):
        self._create_file(".git/config")
        self._create_file("src/main.py")
        result = self.scanner.scan(str(self.tmpdir))
        assert any("main.py" in p for p in result.file_paths)
        assert not any(".git" in p for p in result.file_paths)

    def test_scan_nested_directories(self):
        self._create_file("src/components/Button.tsx")
        self._create_file("src/utils/helpers.py")
        self._create_file("tests/test_app.py")
        result = self.scanner.scan(str(self.tmpdir))
        assert result.total_dirs > 0
        assert any("Button.tsx" in p for p in result.file_paths)

    def test_scan_summary(self):
        self._create_file("main.py", "x=1\n" * 10)
        result = self.scanner.scan(str(self.tmpdir))
        sm = result.summary
        assert sm["total_files"] == 1
        assert sm["total_lines"] >= 10


class TestSymbolIndex:
    def setup_method(self):
        self.index = SymbolIndex()

    def test_index_python_functions(self):
        content = """
def hello():
    pass

def greet(name):
    return f"Hello {name}"
"""
        symbols = self.index.index_file("test.py", content)
        funcs = [s for s in symbols if s.kind == SymbolKind.FUNCTION]
        assert len(funcs) == 2
        assert funcs[0].name == "hello"
        assert funcs[1].name == "greet"

    def test_index_python_classes(self):
        content = """
class MyClass:
    def method_one(self):
        pass

    def method_two(self):
        pass
"""
        symbols = self.index.index_file("test.py", content)
        classes = [s for s in symbols if s.kind == SymbolKind.CLASS]
        methods = [s for s in symbols if s.kind == SymbolKind.METHOD]
        assert len(classes) == 1
        assert classes[0].name == "MyClass"
        assert len(methods) == 2

    def test_index_python_constants(self):
        content = """
MAX_SIZE = 100
DEFAULT_NAME = "steve"
counter = 0
"""
        symbols = self.index.index_file("test.py", content)
        consts = [s for s in symbols if s.kind == SymbolKind.CONSTANT]
        assert len(consts) == 2
        assert consts[0].name == "MAX_SIZE"

    def test_index_javascript_functions(self):
        content = """
function hello() {
    return "world";
}
const greet = (name) => `Hello ${name}`;
"""
        symbols = self.index.index_file("test.js", content)
        funcs = [s for s in symbols if s.kind == SymbolKind.FUNCTION]
        assert len(funcs) >= 2

    def test_index_typescript_interfaces(self):
        content = """
interface User {
    name: string;
    age: number;
}
type Callback = (err: Error) => void;
"""
        symbols = self.index.index_file("test.ts", content)
        interfaces = [s for s in symbols if s.kind == SymbolKind.INTERFACE]
        types = [s for s in symbols if s.kind == SymbolKind.TYPE]
        assert len(interfaces) == 1
        assert interfaces[0].name == "User"
        assert len(types) == 1
        assert types[0].name == "Callback"

    def test_find_symbol(self):
        self.index.index_file("test.py", "def my_func(): pass")
        found = self.index.find_symbol("my_func")
        assert found is not None
        assert found.name == "my_func"

    def test_find_symbols_by_name(self):
        self.index.index_file("test.py", "def calculate(): pass\ndef calculator(): pass")
        found = self.index.find_symbols_by_name("calc")
        assert len(found) == 2

    def test_duplicate_functions(self):
        self.index.index_file("a.py", "def dup(): pass")
        self.index.index_file("b.py", "def dup(): pass")
        dups = self.index.find_duplicate_functions()
        assert len(dups) >= 1
        assert dups[0]["name"] == "dup"

    def test_total_symbols(self):
        self.index.index_file("a.py", "def foo(): pass\nclass Bar: pass")
        assert self.index.total_symbols >= 2

    def test_clear(self):
        self.index.index_file("test.py", "def f(): pass")
        assert self.index.total_symbols > 0
        self.index.clear()
        assert self.index.total_symbols == 0

    def test_html_ids_and_classes(self):
        content = '<div id="app" class="container main"></div>'
        symbols = self.index.index_file("index.html", content)
        assert len(symbols) >= 2

    def test_css_selectors(self):
        content = """
.container { color: red; }
#header { font-size: 2em; }
--primary-color: blue;
"""
        symbols = self.index.index_file("style.css", content)
        assert len(symbols) >= 3


class TestDependencyAnalyzer:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.analyzer = DependencyAnalyzer(str(self.tmpdir))

    def test_analyze_python_imports(self):
        content = "import os\nfrom pathlib import Path\nimport sys as system\n"
        deps = self.analyzer.analyze_file("test.py", content)
        assert len(deps) == 3
        assert deps[0].target == "os"
        assert deps[1].target == "pathlib"
        assert deps[0].type == DependencyType.IMPORT

    def test_analyze_javascript_imports(self):
        content = """import React from 'react'
import { useState } from 'react'
const fs = require('fs')
"""
        deps = self.analyzer.analyze_file("test.js", content)
        assert len(deps) >= 2

    def test_analyze_html_assets(self):
        content = """<script src="app.js"></script>
<link href="style.css" rel="stylesheet">
<img src="logo.png">
"""
        deps = self.analyzer.analyze_file("index.html", content)
        assert len(deps) == 3

    def test_analyze_css_imports(self):
        content = """@import 'base.css';
@import url('theme.css');
.hero { background: url('bg.jpg'); }
"""
        deps = self.analyzer.analyze_file("style.css", content)
        assert len(deps) == 3

    def test_get_dependencies(self):
        self.analyzer.analyze_file("test.py", "import os")
        deps = self.analyzer.get_dependencies("test.py")
        assert "test.py" in deps

    def test_clear(self):
        self.analyzer.analyze_file("test.py", "import os")
        self.analyzer.clear()
        assert len(self.analyzer.get_dependencies()) == 0


class TestProjectGraph:
    def setup_method(self):
        self.graph = ProjectGraph()

    def test_add_node(self):
        node = GraphNode(id="src/main.py", name="main.py", kind="file", path="src/main.py")
        assert self.graph.add_node(node)
        assert not self.graph.add_node(node)

    def test_add_edge(self):
        n1 = GraphNode(id="a.py", name="a.py", kind="file")
        n2 = GraphNode(id="b.py", name="b.py", kind="file")
        self.graph.add_node(n1)
        self.graph.add_node(n2)
        edge = GraphEdge(source="a.py", target="b.py", relationship="imports")
        assert self.graph.add_edge(edge)

    def test_get_node(self):
        node = GraphNode(id="test.py", name="test.py", kind="file")
        self.graph.add_node(node)
        assert self.graph.get_node("test.py") is node
        assert self.graph.get_node("missing") is None

    def test_build_from_scan(self):
        files = ["src/main.py", "src/utils/helper.py", "tests/test_main.py"]
        dirs = ["src", "src/utils", "tests"]
        self.graph.build_from_scan(files, dirs)
        assert self.graph.total_nodes > 0
        assert len(self.graph.files) == 3
        assert len(self.graph.folders) >= 3

    def test_connected_components(self):
        n1 = GraphNode(id="a", name="a", kind="file")
        n2 = GraphNode(id="b", name="b", kind="file")
        n3 = GraphNode(id="c", name="c", kind="file")
        self.graph.add_node(n1)
        self.graph.add_node(n2)
        self.graph.add_node(n3)
        self.graph.add_edge(GraphEdge(source="a", target="b", relationship="imports"))
        components = self.graph.find_connected_components()
        assert len(components) >= 2

    def test_clear(self):
        self.graph.add_node(GraphNode(id="a", name="a", kind="file"))
        self.graph.clear()
        assert self.graph.total_nodes == 0


class TestArchitectureAnalyzer:
    def setup_method(self):
        self.analyzer = ArchitectureAnalyzer()

    def test_detect_cli(self):
        files = ["cli.py", "main.py", "utils.py"]
        contents = {
            "cli.py": "import argparse\nparser = argparse.ArgumentParser()\ndef main():\n    pass\nif __name__ == '__main__':\n    main()",
        }
        result = self.analyzer.analyze(files, ["src", "tests"], contents)
        assert result.primary_type == ArchitectureType.CLI
        assert result.confidence > 0

    def test_detect_api(self):
        files = ["app.py", "routes.py"]
        contents = {
            "app.py": "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/')\nasync def root():\n    return {'hello': 'world'}",
        }
        result = self.analyzer.analyze(files, ["api", "routes"], contents)
        assert result.primary_type == ArchitectureType.API

    def test_detect_spa(self):
        files = ["App.jsx", "index.js", "components/Navbar.jsx"]
        contents = {
            "App.jsx": "import React from 'react'\nimport { BrowserRouter } from 'react-router-dom'",
        }
        result = self.analyzer.analyze(files, ["components", "pages", "store"], contents)
        assert result.primary_type == ArchitectureType.SPA

    def test_detect_unknown(self):
        files = ["random.txt"]
        result = self.analyzer.analyze(files, [])
        assert result.primary_type == ArchitectureType.UNKNOWN

    def test_detect_mvc(self):
        files = ["controllers/user.py", "models/user.py", "views/profile.html"]
        contents = {
            "controllers/user.py": "class UserController:\n    def index(self, request):\n        pass",
        }
        result = self.analyzer.analyze(files, ["controllers", "models", "views"], contents)
        assert result.primary_type == ArchitectureType.MVC
