from typing import Optional

from config.settings import OLLAMA_BASE
from utils.helpers import HTTP

QWEN_MODEL = "qwen3:14b"


def call_qwen(prompt: str, system: str = "", temperature: float = 0.3) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": QWEN_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": 8192,
            "num_predict": 2048,
        },
    }

    r = HTTP.post(
        f"{OLLAMA_BASE}/api/chat",
        json=payload,
        timeout=300,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Ollama error {r.status_code}: {r.text[:200]}")

    data = r.json()
    content = data.get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("Empty response from Ollama")
    return content


def is_qwen_available() -> bool:
    try:
        r = HTTP.post(
            f"{OLLAMA_BASE}/api/chat",
            json={"model": QWEN_MODEL, "messages": [{"role": "user", "content": "ping"}], "stream": False, "options": {"num_predict": 1}},
            timeout=15,
        )
        return r.status_code == 200
    except Exception:
        return False
