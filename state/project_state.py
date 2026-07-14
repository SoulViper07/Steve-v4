from dataclasses import dataclass, field
from typing import List


@dataclass
class ProjectState:
    project_root: str = ""
    project_tree: List[str] = field(default_factory=list)
    generated_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    current_file: str = ""
    current_component: str = ""
    components: List[str] = field(default_factory=list)
    folder_structure: List[str] = field(default_factory=list)
