from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class RepositoryState:
    is_indexed: bool = False
    total_files: int = 0
    total_dirs: int = 0
    total_symbols: int = 0
    total_lines: int = 0
    languages: Dict[str, Any] = field(default_factory=dict)
    frameworks: Dict[str, Any] = field(default_factory=dict)
    architecture_type: str = ""
    architecture_confidence: float = 0.0
    architecture_description: str = ""
    entry_points: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    assets: List[str] = field(default_factory=list)
    dependency_count: int = 0
    duplicate_functions: int = 0
    summary: str = ""
    scanned_at: str = ""
