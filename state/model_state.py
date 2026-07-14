from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class ModelState:
    current_model: str = ""
    model_history: List[Dict] = field(default_factory=list)

    def push_model(self, model: str, stage: str = "", reason: str = ""):
        self.model_history.append({
            "model": model,
            "stage": stage,
            "reason": reason,
        })
        self.current_model = model
