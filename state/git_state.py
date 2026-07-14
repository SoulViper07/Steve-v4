from dataclasses import dataclass, field
from typing import List


@dataclass
class GitState:
    status: str = ""
    branch: str = ""
    modified_count: int = 0
    untracked_count: int = 0
    commit_status: str = ""
    last_commit_hash: str = ""
    last_commit_message: str = ""
    checkpoints: List[str] = field(default_factory=list)
