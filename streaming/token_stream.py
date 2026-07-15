import time
import threading
from typing import Optional, List, Dict, Callable, Generator
from dataclasses import dataclass, field

from providers.ollama import fetch_response_stream
from config.model_config import model_for_stage, options_for_stage
from core.models import RequestRoute


@dataclass
class StreamStats:
    total_tokens: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    first_token_time: float = 0.0
    tokens_per_second: float = 0.0
    total_chars: int = 0
    aborted: bool = False

    @property
    def elapsed(self) -> float:
        return (self.end_time or time.time()) - self.start_time

    @property
    def time_to_first_token(self) -> float:
        if self.first_token_time and self.start_time:
            return self.first_token_time - self.start_time
        return 0.0


TokenCallback = Callable[[str], None]
StatsCallback = Callable[[StreamStats], None]


class TokenStream:
    def __init__(self):
        self._abort_event = threading.Event()
        self._stats = StreamStats()

    def abort(self):
        self._abort_event.set()

    @property
    def aborted(self) -> bool:
        return self._abort_event.is_set()

    def stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict] = None,
        on_token: Optional[TokenCallback] = None,
        on_stats: Optional[StatsCallback] = None,
    ) -> Generator[str, None, StreamStats]:
        self._stats = StreamStats(start_time=time.time())
        self._abort_event.clear()

        route = RequestRoute(
            intent="action_simple",
            actionable=True,
            requires_inspection=False,
            requires_plan=False,
            requires_verification=False,
            short_path=True,
            reason="streaming_generation",
        )

        buf = []
        try:
            for token in fetch_response_stream(model, messages, route):
                if self._abort_event.is_set():
                    self._stats.aborted = True
                    break

                self._stats.total_tokens += 1
                self._stats.total_chars += len(token)
                if self._stats.total_tokens == 1:
                    self._stats.first_token_time = time.time()

                if on_token:
                    on_token(token)

                buf.append(token)
                yield token

        except Exception:
            self._stats.aborted = True
        finally:
            self._stats.end_time = time.time()
            elapsed = self._stats.elapsed
            if elapsed > 0 and self._stats.total_tokens > 0:
                self._stats.tokens_per_second = self._stats.total_tokens / elapsed
            if on_stats:
                on_stats(self._stats)

        return self._stats

    def stream_section(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        on_token: Optional[TokenCallback] = None,
        on_stats: Optional[StatsCallback] = None,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        opts = None
        try:
            opts = options_for_stage("implement")
        except Exception:
            pass

        result = []
        for token in self.stream(model, messages, opts, on_token, on_stats):
            result.append(token)

        return "".join(result).strip()


def stream_and_accumulate(
    model: str,
    messages: List[Dict[str, str]],
    on_token: Optional[TokenCallback] = None,
    on_stats: Optional[StatsCallback] = None,
) -> tuple[str, StreamStats]:
    streamer = TokenStream()
    tokens = []
    final_stats = None

    def _on_stats(s: StreamStats):
        nonlocal final_stats
        final_stats = s

    for token in streamer.stream(
        model=model,
        messages=messages,
        on_token=on_token,
        on_stats=_on_stats or on_stats,
    ):
        tokens.append(token)

    return "".join(tokens), final_stats or streamer._stats
