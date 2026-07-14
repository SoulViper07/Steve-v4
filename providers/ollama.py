import json
import time
import requests
from typing import Optional, List, Dict, Tuple, Any

from config.settings import (
    OLLAMA_BASE, MODEL_TEMPERATURE, MODEL_NUM_CTX, MODEL_NUM_PREDICT,
    MODEL_REPEAT_PENALTY, MODEL_TOP_P, MODEL_TOP_K, WARM_KEEP_ALIVE,
    STEVE_WARM_TIMEOUT_MS, PREFERRED_MODEL, ACTIVE_MODEL_PRESET
)
from utils.helpers import HTTP

def _route_profile(route: Any) -> Dict[str, Any]:
    return {
        "temperature": MODEL_TEMPERATURE,
        "num_ctx": MODEL_NUM_CTX,
        "num_predict": MODEL_NUM_PREDICT,
        "repeat_penalty": MODEL_REPEAT_PENALTY,
        "top_p": MODEL_TOP_P,
        "top_k": MODEL_TOP_K,
    }

def ensure_model_installed(model: str) -> Tuple[bool, str]:
    try:
        r = HTTP.post(f"{OLLAMA_BASE}/api/pull", json={"name": model}, stream=True, timeout=600)
        if r.status_code != 200:
            return False, f"Ollama pull failed {r.status_code}"
        for line in r.iter_lines(decode_unicode=True):
            if not line: continue
            try:
                chunk = json.loads(line)
                if chunk.get("status") == "success": return True, "success"
            except: continue
        return True, "installed"
    except Exception as e:
        return False, str(e)

def warm_model(model: str, keep_alive: str = WARM_KEEP_ALIVE, timeout_ms: Optional[int] = None) -> Tuple[bool, float, str]:
    started = time.monotonic()
    timeout_seconds = max(1, (timeout_ms if timeout_ms is not None else STEVE_WARM_TIMEOUT_MS) / 1000)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": ""}],
        "stream": False,
        "keep_alive": keep_alive,
        "options": {"num_predict": 0},
    }
    try:
        r = HTTP.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=timeout_seconds)
        ok = r.status_code == 200
        detail = "ready" if ok else f"HTTP {r.status_code}"
        return ok, round((time.monotonic() - started) * 1000, 1), detail
    except Exception as e:
        return False, round((time.monotonic() - started) * 1000, 1), str(e)

def fetch_response_stream(model: str, messages: List[Dict[str, str]], route: Any):
    """Yields tokens from Ollama in real-time."""
    payload = {
        "model": model, "messages": messages, "stream": True,
        "options": _route_profile(route),
    }
    with HTTP.post(f"{OLLAMA_BASE}/api/chat", json=payload, stream=True, timeout=300) as r:
        if r.status_code != 200: 
            raise RuntimeError(f"Ollama error {r.status_code}")
        for line in r.iter_lines(decode_unicode=True):
            if not line: continue
            try:
                chunk = json.loads(line)
                tok = chunk.get("message",{}).get("content","")
                if tok: yield tok
                if chunk.get("done"): break
            except: continue
