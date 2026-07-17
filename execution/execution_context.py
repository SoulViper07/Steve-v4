import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ExecutionContext:
    task_id: str = ""
    current_stage: str = ""
    completed_stages: List[str] = field(default_factory=list)
    remaining_stages: List[str] = field(default_factory=list)
    current_file: str = ""
    estimated_progress: float = 0.0
    start_time: float = 0.0
    elapsed_time: float = 0.0
    retry_map: dict = field(default_factory=dict)
    failed_stages: List[str] = field(default_factory=list)
    stage_times: dict = field(default_factory=dict)

    @property
    def total_stages(self) -> int:
        return len(self.completed_stages) + len(self.remaining_stages)

    @property
    def progress_percent(self) -> int:
        total = self.total_stages
        if total == 0:
            return 0
        return int((len(self.completed_stages) / total) * 100)

    def start(self):
        self.start_time = time.time()

    def stage_start(self, name: str):
        self.current_stage = name
        self.stage_times[name] = time.time()

    def stage_complete(self, name: str):
        if name not in self.completed_stages:
            self.completed_stages.append(name)
        if name in self.remaining_stages:
            self.remaining_stages.remove(name)
        elapsed = time.time() - self.stage_times.get(name, time.time())
        self.stage_times[name] = elapsed
        self.elapsed_time = time.time() - self.start_time
        self.estimated_progress = self.progress_percent

    def stage_failed(self, name: str):
        if name not in self.failed_stages:
            self.failed_stages.append(name)
        self.retry_map[name] = self.retry_map.get(name, 0) + 1

    def set_file(self, file_path: str):
        self.current_file = file_path

    def set_remaining(self, stages: List[str]):
        self.remaining_stages = stages

    def summary(self) -> dict:
        return {
            "task_id": self.task_id,
            "current_stage": self.current_stage,
            "completed": list(self.completed_stages),
            "remaining": list(self.remaining_stages),
            "failed": list(self.failed_stages),
            "progress": self.estimated_progress,
            "elapsed": round(self.elapsed_time, 1),
            "retries": dict(self.retry_map),
            "stage_times": {k: round(v, 1) for k, v in self.stage_times.items()},
        }
