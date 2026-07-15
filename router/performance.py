import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict


@dataclass
class ModelPerformanceEntry:
    model: str
    stage: str
    task_category: str
    response_time_ms: float
    success: bool = True
    quality_score: float = 0.0
    timestamp: float = 0.0


@dataclass
class ModelPerformanceStats:
    total_calls: int = 0
    avg_response_time_ms: float = 0.0
    success_rate: float = 1.0
    avg_quality_score: float = 0.0
    stage_success: Dict[str, float] = field(default_factory=dict)
    stage_speed: Dict[str, float] = field(default_factory=dict)


class PerformanceTracker:
    def __init__(self, workdir: Optional[Path] = None):
        self._workdir = (workdir or Path.cwd()).resolve()
        self._data_dir = self._workdir / ".steve" / "router"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._entries: List[ModelPerformanceEntry] = []
        self._stats: Dict[str, ModelPerformanceStats] = {}
        self._load()

    def _path(self) -> Path:
        return self._data_dir / "performance.json"

    def _load(self):
        path = self._path()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                for e in data.get("entries", []):
                    self._entries.append(ModelPerformanceEntry(**e))
                for model, s in data.get("stats", {}).items():
                    self._stats[model] = ModelPerformanceStats(**s)
            except Exception:
                pass

    def _save(self):
        path = self._path()
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps({
                    "entries": [asdict(e) for e in self._entries[-1000:]],
                    "stats": {m: asdict(s) for m, s in self._stats.items()},
                }, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            tmp.replace(path)
        except Exception:
            pass

    def record(
        self,
        model: str,
        stage: str,
        task_category: str,
        response_time_ms: float,
        success: bool = True,
        quality_score: float = 0.0,
    ):
        entry = ModelPerformanceEntry(
            model=model,
            stage=stage,
            task_category=task_category,
            response_time_ms=response_time_ms,
            success=success,
            quality_score=quality_score,
            timestamp=time.time(),
        )
        self._entries.append(entry)
        self._update_stats(entry)
        self._save()

    def _update_stats(self, entry: ModelPerformanceEntry):
        if entry.model not in self._stats:
            self._stats[entry.model] = ModelPerformanceStats()
        s = self._stats[entry.model]
        old_total = s.total_calls
        s.total_calls += 1
        s.avg_response_time_ms = (
            (s.avg_response_time_ms * old_total + entry.response_time_ms)
            / s.total_calls
        )
        s.success_rate = (
            (s.success_rate * old_total + (1.0 if entry.success else 0.0))
            / s.total_calls
        )
        s.avg_quality_score = (
            (s.avg_quality_score * old_total + entry.quality_score)
            / s.total_calls
        )
        stage_key = f"{entry.stage}/{entry.task_category}"
        if stage_key not in s.stage_success:
            s.stage_success[stage_key] = 1.0 if entry.success else 0.0
            s.stage_speed[stage_key] = entry.response_time_ms
        else:
            count = sum(1 for e in self._entries if e.model == entry.model and e.stage == entry.stage and e.task_category == entry.task_category)
            old = count - 1
            s.stage_success[stage_key] = (
                (s.stage_success[stage_key] * old + (1.0 if entry.success else 0.0))
                / count
            )
            s.stage_speed[stage_key] = (
                (s.stage_speed[stage_key] * old + entry.response_time_ms)
                / count
            )

    def get_stats(self, model: str) -> Optional[ModelPerformanceStats]:
        return self._stats.get(model)

    def all_stats(self) -> Dict[str, ModelPerformanceStats]:
        return dict(self._stats)

    def fastest_model_for_stage(self, stage: str) -> Optional[str]:
        best_model = None
        best_speed = float("inf")
        for model, s in self._stats.items():
            for stage_key, speed in s.stage_speed.items():
                if stage_key.startswith(f"{stage}/") and speed < best_speed:
                    best_speed = speed
                    best_model = model
        return best_model

    def most_reliable_model_for_stage(self, stage: str) -> Optional[str]:
        best_model = None
        best_rate = -1.0
        for model, s in self._stats.items():
            for stage_key, rate in s.stage_success.items():
                if stage_key.startswith(f"{stage}/") and rate > best_rate:
                    best_rate = rate
                    best_model = model
        return best_model

    def best_model_for_category(self, category: str) -> Optional[str]:
        best_model = None
        best_quality = -1.0
        for model, s in self._stats.items():
            combined = 0.0
            count = 0
            for stage_key, quality in s.stage_success.items():
                if f"/{category}" in stage_key:
                    combined += quality
                    count += 1
            if count > 0:
                avg = combined / count
                if avg > best_quality:
                    best_quality = avg
                    best_model = model
        return best_model

    def clear(self):
        self._entries.clear()
        self._stats.clear()
        self._save()


_GLOBAL_TRACKER: Optional[PerformanceTracker] = None


def get_tracker(workdir: Optional[Path] = None) -> PerformanceTracker:
    global _GLOBAL_TRACKER
    if _GLOBAL_TRACKER is None:
        _GLOBAL_TRACKER = PerformanceTracker(workdir)
    return _GLOBAL_TRACKER


def reset_tracker():
    global _GLOBAL_TRACKER
    _GLOBAL_TRACKER = None
