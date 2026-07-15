import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class SectionProgress:
    file_path: str
    section_name: str
    status: str = "pending"
    token_count: int = 0
    char_count: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    error: Optional[str] = None

    @property
    def elapsed(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time if self.start_time else 0.0

    @property
    def tokens_per_second(self) -> float:
        if self.elapsed > 0:
            return self.token_count / self.elapsed
        return 0.0


@dataclass
class FileProgress:
    file_path: str
    total_sections: int = 0
    completed_sections: int = 0
    failed_sections: int = 0
    sections: Dict[str, SectionProgress] = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def elapsed(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time if self.start_time else 0.0

    @property
    def percent_complete(self) -> float:
        if self.total_sections == 0:
            return 0.0
        return (self.completed_sections + self.failed_sections) / self.total_sections * 100

    @property
    def is_complete(self) -> bool:
        return (self.completed_sections + self.failed_sections) >= self.total_sections


class ProgressTracker:
    def __init__(self):
        self._files: Dict[str, FileProgress] = {}
        self._current_file: Optional[str] = None
        self._current_section: Optional[str] = None
        self._start_time = time.time()

    def start_file(self, file_path: str, total_sections: int):
        fp = FileProgress(
            file_path=file_path,
            total_sections=total_sections,
            start_time=time.time(),
        )
        self._files[file_path] = fp
        self._current_file = file_path

    def start_section(self, section_name: str):
        if not self._current_file:
            return
        fp = self._files[self._current_file]
        sp = SectionProgress(
            file_path=self._current_file,
            section_name=section_name,
            status="generating",
            start_time=time.time(),
        )
        fp.sections[section_name] = sp
        self._current_section = section_name

    def add_token(self, token: str):
        if not self._current_file or not self._current_section:
            return
        fp = self._files[self._current_file]
        sp = fp.sections.get(self._current_section)
        if sp:
            sp.token_count += 1
            sp.char_count += len(token)

    def complete_section(self, section_name: str, success: bool = True, error: Optional[str] = None):
        if not self._current_file:
            return
        fp = self._files[self._current_file]
        sp = fp.sections.get(section_name)
        if sp:
            sp.status = "done" if success else "failed"
            sp.end_time = time.time()
            sp.error = error
            if success:
                fp.completed_sections += 1
            else:
                fp.failed_sections += 1

    def complete_file(self, file_path: Optional[str] = None):
        target = file_path or self._current_file
        if target and target in self._files:
            self._files[target].end_time = time.time()

    def file_progress(self, file_path: str) -> Optional[FileProgress]:
        return self._files.get(file_path)

    def section_progress(self, file_path: str, section: str) -> Optional[SectionProgress]:
        fp = self._files.get(file_path)
        if fp:
            return fp.sections.get(section)
        return None

    def all_files(self) -> List[FileProgress]:
        return list(self._files.values())

    def summary(self) -> Dict:
        total_sections = sum(f.total_sections for f in self._files.values())
        total_completed = sum(f.completed_sections for f in self._files.values())
        total_failed = sum(f.failed_sections for f in self._files.values())
        total_tokens = sum(
            sp.token_count for f in self._files.values() for sp in f.sections.values()
        )
        total_chars = sum(
            sp.char_count for f in self._files.values() for sp in f.sections.values()
        )
        elapsed = time.time() - self._start_time

        return {
            "files": len(self._files),
            "total_sections": total_sections,
            "completed_sections": total_completed,
            "failed_sections": total_failed,
            "total_tokens": total_tokens,
            "total_chars": total_chars,
            "elapsed_seconds": round(elapsed, 1),
        }

    def reset(self):
        self._files.clear()
        self._current_file = None
        self._current_section = None
        self._start_time = time.time()
