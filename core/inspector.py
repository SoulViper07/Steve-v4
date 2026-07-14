from pathlib import Path
from typing import List, Set, Tuple

from .models import ProjectMap
from .file_context import _is_excluded_path_part

class ProjectInspector:
    IMPORTANT_NAMES = {
        "package.json", "requirements.txt", "pyproject.toml", "Cargo.toml",
        "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts",
        "AndroidManifest.xml", "MainActivity.kt", "MainActivity.java", "manage.py",
    }

    def __init__(self, workdir: Path):
        self.workdir = Path(workdir).resolve()

    def _iter_files(self):
        for path in self.workdir.rglob("*"):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(self.workdir)
            except ValueError:
                continue
            if any(_is_excluded_path_part(part) for part in rel.parts[:-1]):
                continue
            yield path, rel.as_posix()

    def scan(self) -> ProjectMap:
        important_files = []
        ui_files = []
        config_files = []
        build_files = []
        entry_points = []
        viewmodel_files = []
        voice_files = []
        animation_files = []
        theme_files = []
        notes = []
        project_types: Set[str] = set()
        scanned = 0

        for path, rel in self._iter_files():
            scanned += 1
            lower = rel.lower()
            name = path.name.lower()
            if name in {"package.json"}:
                project_types.add("Node")
                config_files.append(rel)
            if name in {"requirements.txt", "pyproject.toml"}:
                project_types.add("Python")
                config_files.append(rel)
            if name in {"build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "gradle.properties"}:
                project_types.add("Gradle")
                build_files.append(rel)
            if lower.endswith("androidmanifest.xml") or "src/main/androidmanifest.xml" in lower:
                project_types.add("Android")
                important_files.append(rel)
            if "compose" in lower or name.endswith(".kt"):
                if "android" in project_types or "src/main" in lower:
                    project_types.add("Kotlin")
            if "mainactivity.kt" in lower or "mainactivity.java" in lower or name in {"main.py", "app.py", "index.html", "main.js", "main.ts", "manage.py"}:
                entry_points.append(rel)
            if any(token in lower for token in ("ui/", "/ui", "screen", "component", "page", "layout", "compose")) and path.suffix.lower() in {".kt", ".tsx", ".jsx", ".js", ".ts", ".html", ".css"}:
                ui_files.append(rel)
            if "theme" in lower and path.suffix.lower() in {".kt", ".xml", ".css"}:
                theme_files.append(rel)
            if "viewmodel" in lower:
                viewmodel_files.append(rel)
            if any(token in lower for token in ("voice", "stt", "tts", "speech", "recognizer")):
                voice_files.append(rel)
            if any(token in lower for token in ("anim", "animation", "simulat", "motion", "physics")):
                animation_files.append(rel)
            if name in self.IMPORTANT_NAMES or any(token in lower for token in ("readme", "manifest", "mainactivity", "settings.gradle", "build.gradle", "app/build.gradle", "app/build.gradle.kts")):
                important_files.append(rel)
            if path.suffix.lower() in {".json", ".toml", ".yaml", ".yml", ".properties", ".xml"}:
                config_files.append(rel)

        if (self.workdir / ".git").is_dir():
            project_types.add("Git repo")
        if any(path.endswith(".kt") for path in ui_files + important_files + entry_points + theme_files):
            project_types.add("Android/Jetpack Compose")
        if not project_types:
            notes.append("No known project manifest found; routing will rely on filenames and loaded context.")
        if theme_files:
            notes.append("Theme-related files detected.")
        if voice_files:
            notes.append("Voice/STT/TTS related files detected.")
        if animation_files:
            notes.append("Animation or simulation related files detected.")

        return ProjectMap(
            root=str(self.workdir),
            project_types=sorted(project_types),
            important_files=sorted(dict.fromkeys(important_files))[:20],
            ui_files=sorted(dict.fromkeys(ui_files))[:20],
            config_files=sorted(dict.fromkeys(config_files))[:20],
            build_files=sorted(dict.fromkeys(build_files))[:20],
            entry_points=sorted(dict.fromkeys(entry_points))[:20],
            viewmodel_files=sorted(dict.fromkeys(viewmodel_files))[:20],
            voice_files=sorted(dict.fromkeys(voice_files))[:20],
            animation_files=sorted(dict.fromkeys(animation_files))[:20],
            theme_files=sorted(dict.fromkeys(theme_files))[:20],
            notes=notes[:8],
            file_count=scanned,
        )
