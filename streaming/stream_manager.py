import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable

from .token_stream import TokenStream, StreamStats
from .progress_tracker import ProgressTracker, FileProgress, SectionProgress
from .output_renderer import OutputRenderer

from generation.incremental_engine import SECTION_PROMPTS
from config.model_config import model_for_stage
from state import get_state_manager, StateManager


class StreamManager:
    def __init__(
        self,
        workdir: Optional[Path] = None,
        state_manager: Optional[StateManager] = None,
        renderer: Optional[OutputRenderer] = None,
    ):
        self._workdir = (workdir or Path.cwd()).resolve()
        self._sm = state_manager or get_state_manager(self._workdir)
        self._renderer = renderer or OutputRenderer()
        self._tracker = ProgressTracker()
        self._token_stream = TokenStream()
        self._aborted = threading.Event()

    @property
    def renderer(self) -> OutputRenderer:
        return self._renderer

    @property
    def tracker(self) -> ProgressTracker:
        return self._tracker

    def abort(self):
        self._aborted.set()
        self._token_stream.abort()

    @property
    def aborted(self) -> bool:
        return self._aborted.is_set()

    def stream_section(
        self,
        file_path: str,
        section: str,
        prompt: str,
        model: Optional[str] = None,
    ) -> Optional[str]:
        if self._aborted.is_set():
            return None

        actual_model = model or model_for_stage("implement")
        self._tracker.start_section(section)
        self._renderer.section_start(file_path, section)
        self._sm.set_model(actual_model, f"generating:{file_path}", f"Generating section {section}")

        result_tokens = []

        def on_token(tok: str):
            if self._aborted.is_set():
                self._token_stream.abort()
                return
            self._tracker.add_token(tok)
            self._renderer.display_tokens(tok)
            result_tokens.append(tok)

        def on_stats(stats: StreamStats):
            if stats.total_tokens > 0:
                self._tracker.complete_section(
                    section,
                    success=not stats.aborted,
                )
                if not stats.aborted and not self._aborted.is_set():
                    sp = self._tracker.section_progress(file_path, section)
                    if sp:
                        self._renderer.section_complete(
                            file_path, section,
                            sp.token_count, sp.char_count, sp.elapsed,
                        )

        try:
            ts = TokenStream()
            all_tokens = []
            for token in ts.stream(
                model=actual_model,
                messages=[{"role": "user", "content": prompt}],
                on_token=on_token,
                on_stats=on_stats,
            ):
                if self._aborted.is_set():
                    ts.abort()
                    break
                all_tokens.append(token)

            if self._aborted.is_set():
                self._tracker.complete_section(section, success=False, error="Aborted")
                self._renderer.section_failed(file_path, section, "Aborted")
                return None

            content = "".join(all_tokens).strip()
            from generation.incremental_engine import SectionGenerator
            cleaner = SectionGenerator()
            content = cleaner._clean_section(content)
            return content

        except Exception as e:
            self._tracker.complete_section(section, success=False, error=str(e))
            self._renderer.section_failed(file_path, section, str(e))
            return None

    def stream_file(
        self,
        file_path: str,
        sections: List[str],
        context: Dict,
        model: Optional[str] = None,
    ) -> bool:
        if self._aborted.is_set():
            return False

        self._tracker.start_file(file_path, len(sections))
        self._sm.set_file(file_path)

        full_path = self._workdir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        file_buffer = []
        all_ok = True
        section_count = 0

        for section in sections:
            if self._aborted.is_set():
                break

            section_prompts = SECTION_PROMPTS.get(file_path, {})
            prompt_template = section_prompts.get(section)
            if not prompt_template:
                continue

            prompt = prompt_template.format(**context)

            content = self.stream_section(
                file_path=file_path,
                section=section,
                prompt=prompt,
                model=model,
            )

            if content:
                file_buffer.append(content)
                section_count += 1
            else:
                all_ok = False

        if file_buffer:
            combined = "\n\n".join(file_buffer)
            full_path.write_text(combined, encoding="utf-8")

            exists_before = full_path.exists() and full_path.stat().st_size > 0
            if exists_before:
                self._renderer.file_updated(file_path, f"{len(combined)} chars, {section_count} sections")
            else:
                self._renderer.file_created(file_path, len(combined), section_count)

            self._sm.mark_generated(file_path)
        else:
            all_ok = False

        self._tracker.complete_file(file_path)

        return all_ok

    def stream_files(
        self,
        files: Dict[str, List[str]],
        context: Dict,
        model: Optional[str] = None,
    ) -> bool:
        self._tracker.reset()
        overall_ok = True

        self._renderer.stage_progress("implementing")

        for file_path, sections in files.items():
            if self._aborted.is_set():
                break
            ok = self.stream_file(file_path, sections, context, model)
            if not ok:
                overall_ok = False

        return overall_ok

    def stream_from_builder(
        self,
        builder,
        file_path: str,
        sections: List[str],
        context: Dict,
    ) -> bool:
        return self.stream_file(file_path, sections, context)
